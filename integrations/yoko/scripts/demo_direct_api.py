"""Run an isolated synthetic owner -> direct client -> driver/admin -> MLIT flow.

No external URL, credentials or production DB can be supplied. Tokens stay in
memory. All operations use real HTTP; the temporary server/DB are removed.
"""
import http.client
import json
import secrets
import sys
import tempfile
import threading
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from app.db import initialize
from app.server import LocalServer

def run():
    checks=[]
    with tempfile.TemporaryDirectory() as directory:
        db=Path(directory)/'demo.sqlite3';initialize(db)
        server=LocalServer(('127.0.0.1',0),db,enable_mlit=True)
        thread=threading.Thread(target=lambda:server.serve_forever(poll_interval=.01),daemon=True);thread.start()
        def request(method,path,data=None,session=None,grant=None,extra=None):
            headers={}
            if data is not None:headers['Content-Type']='application/json'
            if session:headers.update({'Cookie':session['cookie'],'X-CSRF-Token':session['csrf'],'X-Requested-With':'YokoLocal'})
            if grant:headers.update({'Authorization':'Bearer '+grant['access_token'],'X-Client-ID':grant['client_id']})
            headers.update(extra or {})
            conn=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=5)
            conn.request(method,path,json.dumps(data) if data is not None else None,headers)
            response=conn.getresponse();result=json.loads(response.read());status=response.status
            cookie=response.getheader('Set-Cookie');conn.close()
            if status!=200:raise RuntimeError(f'{method} {path}: {status}, {result}')
            return result,cookie
        def post(path,data,session=None,grant=None):return request('POST',path,data,session,grant)[0]
        def get(path,session=None,grant=None):return request('GET',path,session=session,grant=grant)[0]
        def login(actor):
            data,cookie=request('POST','/api/session',{'username':actor,'password':'local-test-only'},extra={'X-Requested-With':'YokoLocal'})
            return {'cookie':cookie.split(';')[0],'csrf':data['csrf']}
        def approve(owner,kind,data):
            draft=post('/api/drafts/'+kind,data,owner);op=secrets.token_hex(16)
            operation={'operation_id':op,'idempotency_key':op,'kind':kind,'payload':{'draft_id':draft['id'],'details':draft['details']}}
            grant=post('/api/client-grants',{'client_id':'synthetic-direct-client','scopes':['mobility:read','mobility:execute'],'expires_in':300,'operation':operation},owner)
            return operation,grant
        def execute(op,grant):return post('/direct/v1/actions/'+op['kind'],{k:v for k,v in op.items() if k!='kind'},grant=grant)
        def passed(name):checks.append(name);print('PASS '+name,flush=True)
        try:
            rider,driver,admin=[login(x) for x in ['rider-a1','driver-a1','admin-a1']]
            requested={'service_id':'service-a','origin_stop_id':'stop-a','destination_stop_id':'stop-b','passengers':1}
            operation,grant=approve(rider,'request',requested)
            first=execute(operation,grant);ride=first['current']
            assert ride['status']=='requested'
            passed('本人の個別承認を受け、通常クライアントが依頼を保存')
            assert execute(operation,grant)['replayed'] is True
            assert get('/direct/v1/operations/'+operation['operation_id'],grant=grant)['current']['id']==ride['id']
            assert get('/direct/v1/rides',grant=grant)['total']==1
            passed('同じ操作の再送と結果照合で予約を重複させない')
            for action,state in [('accept','assigned'),('arrive','arrived'),('board','onboard'),('complete','completed')]:
                op=secrets.token_hex(16)
                ride=post('/api/actions/'+action,{'operation_id':op,'idempotency_key':op,'payload':{'ride_id':ride['id'],'version':ride['version'],'stopped':True}},driver)['current']
                assert ride['status']==state
                assert get('/api/rides/'+ride['id'],admin)['status']==state
            passed('ドライバーの引受・到着・乗車・降車を管理者と共有')
            standard=get('/passengers/rider-a1/reservations',grant=grant)
            assert standard['reservations'][0]['status']=='completed'
            passed('同じ予約を国交省形式の一覧で確認')
            operation,grant=approve(rider,'request',requested);ride=execute(operation,grant)['current']
            operation,grant=approve(rider,'change',{'ride_id':ride['id'],**requested,'passengers':2})
            ride=execute(operation,grant)['current'];assert ride['passengers']==2
            passed('承認した人数変更を共通Coreで反映')
            operation,grant=approve(rider,'cancel',{'ride_id':ride['id']})
            item=next(x for x in get('/passengers/rider-a1/reservations',grant=grant)['reservations'] if x['id']==ride['id'])
            body={k:item[k] for k in ['passenger_id','service_id','pickup','dropoff','passenger_count','accessibility_feature_count']};body['status']='cancelled'
            result,_=request('PUT','/reservations/'+ride['id'],body,grant=grant,extra={'X-Operation-ID':operation['operation_id'],'Idempotency-Key':operation['idempotency_key']})
            assert result['status']=='cancelled';assert execute(operation,grant)['replayed']
            passed('国交省形式で取消し、通常APIで再送しても一度だけ処理')
            return {'status':'PASS','checked_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'ISOLATED_SYNTHETIC_REAL_HTTP_CLIENT','checks':checks,'external_partner_tested':False,'production_conformance':False}
        finally:
            server.shutdown();server.server_close();thread.join(2)

if __name__=='__main__':
    report=run()
    output=ROOT/'artifacts/test-results/direct-client-demo.json'
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f'{len(report["checks"])}項目合格。実車・外部サービスへの接続はありません。')
