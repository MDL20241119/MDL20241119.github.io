"""SDK/HTTP end-to-end acceptance and backup recovery with synthetic data only."""
import asyncio
import json
import secrets
import sys
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx
from a2a.client.client import ClientConfig
from a2a.client.client_factory import create_client
from a2a.types import a2a_pb2 as p
from google.protobuf.json_format import MessageToDict, ParseDict
from app.agent_tasks import operation_reference
from app.core import Core
from app.db import initialize
from app.server import LocalServer
from scripts.a2a_test_support import running_a2a, rpc, http, send_params
from scripts.mcp_test_support import running_mcp, rpc as mcp_rpc
from scripts.backup_local import backup


def run():
    checks, evidence = [], {}
    def passed(label):
        checks.append(label); print('PASS '+label, flush=True)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder)/'agents.sqlite3'; initialize(path)
        web = LocalServer(('127.0.0.1',0),path)
        thread = threading.Thread(target=lambda:web.serve_forever(poll_interval=.01),daemon=True);thread.start()
        port = web.server_address[1]
        def call(url,body=None,session=None,grant=None,status=200):
            headers={'X-Requested-With':'YokoLocal'}
            if session: headers.update({'Cookie':session['cookie'],'X-CSRF-Token':session['csrf']})
            if grant: headers.update({'Authorization':'Bearer '+grant['access_token'],'X-Client-ID':grant['client_id']})
            code,value,hdr=http(port,url,'POST' if body is not None else 'GET',body,headers)
            assert code==status,(url,code,value.get('error'))
            if url=='/api/session':
                cookie=next(v for k,v in hdr.items() if k.lower()=='set-cookie')
                return {'cookie':cookie.split(';')[0],'csrf':value['csrf']}
            return value
        def login(actor):return call('/api/session',{'username':actor,'password':'local-test-only'})
        def grant(session,operation=None):
            return call('/api/client-grants',{'client_id':'synthetic-a2a-client','scopes':['mobility:read']+(['mobility:execute'] if operation else []),'expires_in':300,'operation':operation},session)
        def approve(kind,data):
            draft=call('/api/drafts/'+kind,data,rider);key=secrets.token_hex(16)
            op={'operation_id':key,'idempotency_key':key,'kind':kind,'payload':{'draft_id':draft['id'],'details':draft['details']}}
            return op,grant(rider,op)
        def driver_action(kind,ride):
            # Driver actions read their authoritative screen API version; the
            # agent artifact is a ProtoJSON Value snapshot, not a new approval.
            ride=call('/api/rides/'+ride['id'],session=driver)
            key=secrets.token_hex(16)
            return call('/api/actions/'+kind,{'operation_id':key,'idempotency_key':key,'payload':{'ride_id':ride['id'],'version':ride['version'],'stopped':True}},driver)['current']
        async def sdk_send(a2a_port,authorization,value,task_id=''):
            async with httpx.AsyncClient(headers={'Authorization':'Bearer '+authorization['access_token'],'X-Client-ID':authorization['client_id']},trust_env=False) as hc:
                client=await create_client(f'http://127.0.0.1:{a2a_port}',ClientConfig(streaming=False,httpx_client=hc))
                request=ParseDict(send_params(value,secrets.token_hex(16),task_id),p.SendMessageRequest())
                events=[event async for event in client.send_message(request)]
                result=events[0].task
                assert result.id
                return MessageToDict(result)
        def data(task):return task['artifacts'][0]['parts'][0]['data']
        try:
            rider,driver,admin,other=[login(x) for x in ('rider-a1','driver-a1','admin-a1','rider-a2')]
            read=grant(rider); request={'service_id':'service-a','origin_stop_id':'stop-a','destination_stop_id':'stop-b','passengers':2}
            with running_a2a(Core(path)) as (ap,_),running_mcp(Core(path)) as (mp,_):
                pending=asyncio.run(sdk_send(ap,read,{'action':'execute'}))
                assert pending['status']['state']=='TASK_STATE_INPUT_REQUIRED'
                assert call('/api/snapshot',session=rider)['rides']==[]
                passed('公式A2A SDK 1.1.4で接続し、本人確認前はTaskが入力待ちとなり依頼を保存しない')
                operation,write=approve('request',request)
                completed=asyncio.run(sdk_send(ap,write,operation_reference(operation),pending['id']))
                ride=data(completed)['current']
                assert completed['status']['state']=='TASK_STATE_COMPLETED' and ride['status']=='requested'
                evidence['request_task']={'id':completed['id'],'state':completed['status']['state'],'ride_status':ride['status']}
                passed('本人の個別承認で同じTaskを再開。Task処理完了と予約の引受待ちを区別して保存')
                replay=call('/direct/v1/actions/request',{k:v for k,v in operation.items() if k!='kind'},grant=write)
                mcp=mcp_rpc(mp,write,'tools/call',{'name':'yoko_execute_approved_operation','arguments':{'operation':operation}})[1]
                assert replay['replayed'] and mcp['result']['structuredContent']['data']['replayed']
                with Core(path).db() as db:assert db.execute('SELECT count(*) FROM events WHERE ride_id=?',(ride['id'],)).fetchone()[0]==1
                passed('A2Aで保存した操作を直接APIとMCPへ再送しても依頼・イベントは1件')
                code,denied,_=rpc(ap,grant(other),'GetTask',{'id':completed['id']})
                assert denied['error']['code']==-32001
                cancelled=rpc(ap,read,'CancelTask',{'id':completed['id']})[1]
                assert cancelled['error']['code']==-32002
                assert call('/api/rides/'+ride['id'],session=admin)['status']=='requested'
                passed('別利用者のTask取得と完了Taskの取消を拒否し、予約を維持')
                changed_op,write=approve('change',{'ride_id':ride['id'],**request,'passengers':1})
                changed=asyncio.run(sdk_send(ap,write,operation_reference(changed_op)))
                ride=data(changed)['current'];assert ride['passengers']==1
                for kind in ('accept','arrive','board','complete'):ride=driver_action(kind,ride)
                result=asyncio.run(sdk_send(ap,read,{'action':'read_reservation','reservation_id':ride['id']}))
                direct=call('/direct/v1/rides/'+ride['id'],grant=read)
                admin_view=call('/api/rides/'+ride['id'],session=admin)
                mcp=mcp_rpc(mp,read,'tools/call',{'name':'yoko_get_my_reservation','arguments':{'reservation_id':ride['id']}})[1]
                assert data(result)['current']['status']==direct['status']==admin_view['status']==mcp['result']['structuredContent']['data']['status']=='completed'
                passed('A2Aで人数変更後、ドライバーが引受・到着・乗車・降車。4入口で同じ完了状態を確認')
                operation,write=approve('request',request)
                active=data(asyncio.run(sdk_send(ap,write,operation_reference(operation))))['current']
                waiting=asyncio.run(sdk_send(ap,read,{'action':'execute'}))
                canceled=rpc(ap,read,'CancelTask',{'id':waiting['id']})[1]['result']
                assert canceled['status']['state']=='TASK_STATE_CANCELED'
                assert call('/api/rides/'+active['id'],session=rider)['status']=='requested'
                cancel_op,write=approve('cancel',{'ride_id':active['id']})
                canceled=asyncio.run(sdk_send(ap,write,operation_reference(cancel_op)))
                assert data(canceled)['current']['status']=='cancelled'
                passed('入力待ちTaskの取消は予約を変えず、予約取消は別の個別承認で実行')
                call('/api/client-grants/revoke',{'grant_id':write['grant_id']},rider)
                assert rpc(ap,write,'GetTask',{'id':canceled['id']})[0]==401
                assert rpc(ap,read,'GetTask',{'id':canceled['id']})[1]['result']['status']['state']=='TASK_STATE_COMPLETED'
                passed('実行委任を失効させた後、本人の有効な読取委任で同じTaskの結果を照合')
                context=completed['contextId']
                listing=rpc(ap,read,'ListTasks',{'contextId':context,'pageSize':1,'historyLength':0})[1]['result']
                assert listing['totalSize']==1 and not listing['tasks'][0].get('history') and not listing['tasks'][0].get('artifacts')
                passed('本人のcontextに限定した一覧・履歴省略・成果物省略を確認')
                pending=asyncio.run(sdk_send(ap,read,{'action':'execute'}))
                destination=Path(folder)/'restored.sqlite3';backup(path,destination)
            passed('MCP・A2Aの停止後も通常APIから完了済み予約を照会できる')
            assert call('/api/rides/'+ride['id'],session=rider)['status']=='completed'
            with running_a2a(Core(path)) as (ap,_):
                assert rpc(ap,read,'GetTask',{'id':pending['id']})[1]['result']['status']['state']=='TASK_STATE_INPUT_REQUIRED'
            passed('同じDBでA2Aサーバーを再起動して未完了Taskを再取得')
            # Switch the real web server to the restored DB. New login/approval
            # is obtained by its normal session+CSRF endpoints, not SQL grants.
            web.shutdown();web.server_close();thread.join(2)
            web=LocalServer(('127.0.0.1',0),destination)
            thread=threading.Thread(target=lambda:web.serve_forever(poll_interval=.01),daemon=True);thread.start();port=web.server_address[1]
            call('/api/me',session=rider,status=401)
            with running_a2a(Core(destination)) as (ap,_):
                assert rpc(ap,read,'GetTask',{'id':pending['id']})[0]==401
                rider=login('rider-a1');fresh=grant(rider)
                assert rpc(ap,fresh,'GetTask',{'id':pending['id']})[1]['result']['status']['state']=='TASK_STATE_INPUT_REQUIRED'
                op,write=approve('request',{**request,'destination_stop_id':'stop-c'})
                resumed=asyncio.run(sdk_send(ap,write,operation_reference(op),pending['id']))
                assert resumed['status']['state']=='TASK_STATE_COMPLETED'
                assert call('/api/rides/'+ride['id'],session=rider)['status']=='completed'
                with Core(destination).db() as db:
                    assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
                    evidence['restored']={'schema_version':db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0],
                        'rides':db.execute('SELECT count(*) FROM rides').fetchone()[0], 'tasks':db.execute('SELECT count(*) FROM agent_tasks').fetchone()[0]}
            passed('SQLiteバックアップを復旧し、旧Cookie・旧委任を拒否。再ログイン・再承認で未完了Taskを再開')
        finally:
            web.shutdown();web.server_close();thread.join(2)
    return {'status':'PASS','checked_at_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'SYNTHETIC_LOOPBACK_REAL_HTTP_OFFICIAL_A2A_SDK_CROSS_ADAPTER_AND_RESTORE',
        'sdk':{'name':'a2a-sdk','version':'1.1.4','protocol':'1.0'},'checks':checks,'evidence':evidence,
        'remote_agent_tested':False,'card_signatures_verified':False,'oauth_conformance':False,
        'rendered_browser_tested':False,'production_conformance':False}


if __name__=='__main__':
    report=run()
    (ROOT/'artifacts/test-results/a2a-client-demo.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f'{len(report["checks"])}項目合格。外部公開・実車・実課金は含みません。')
