"""Independent real HTTP exercise of explicitly synthetic observation contracts."""
import http.client
import json
import secrets
import sys
import tempfile
import threading
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from app.core import iso
from app.db import initialize
from app.server import LocalServer
from scripts.export_local_openapi import build
from openapi_schema_validator import OAS31Validator

def run():
    checks=[];spec=build();fixture=json.loads((ROOT/'fixtures/synthetic-observations.json').read_text())
    with tempfile.TemporaryDirectory() as folder:
        db=Path(folder)/'observations.sqlite3';initialize(db)
        server=LocalServer(('127.0.0.1',0),db,enable_mlit=True)
        thread=threading.Thread(target=lambda:server.serve_forever(poll_interval=.01),daemon=True);thread.start()
        def call(path,method='GET',body=None,session=None,grant=None,status=200):
            headers={}
            if body is not None:headers['Content-Type']='application/json'
            if session:headers.update({'Cookie':session['cookie'],'X-CSRF-Token':session['csrf'],'X-Requested-With':'YokoLocal'})
            if path=='/api/session':headers['X-Requested-With']='YokoLocal'
            if grant:headers.update({'Authorization':'Bearer '+grant['access_token'],'X-Client-ID':grant['client_id']})
            conn=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=5)
            conn.request(method,path,json.dumps(body) if body is not None else None,headers)
            response=conn.getresponse();value=json.loads(response.read());cookie=response.getheader('Set-Cookie');code=response.status;conn.close()
            assert code==status,(path,code,value)
            match=server.mlit.contract.match(method,path.split('?')[0])
            if match:
                if code<400:server.mlit.contract.request(match,path.partition('?')[2],body)
                server.mlit.contract.response(match,code,value)
            else:
                template=path.split('?')[0]
                if template.startswith('/direct/v1/operations/'):template='/direct/v1/operations/{id}'
                pointer='#/paths/'+template.replace('~','~0').replace('/','~1')+'/'+method.lower()
                if body is not None and code<400:OAS31Validator({**spec,'$ref':pointer+'/requestBody/content/application~1json/schema'},format_checker=OAS31Validator.FORMAT_CHECKER).validate(body)
                OAS31Validator({**spec,'$ref':pointer+f'/responses/{code}/content/application~1json/schema'},format_checker=OAS31Validator.FORMAT_CHECKER).validate(value)
            return (value,cookie) if path=='/api/session' else value
        def login(actor):
            value,cookie=call('/api/session','POST',{'username':actor,'password':'local-test-only'})
            return {'cookie':cookie.split(';')[0],'csrf':value['csrf']}
        def grant_for(session,op=None):return call('/api/client-grants','POST',{'client_id':'synthetic-observation-client','scopes':['mobility:read']+(['mobility:execute'] if op else []),'expires_in':300,'operation':op},session)
        def command(session,kind,data):
            draft=call('/api/drafts/'+kind,'POST',data,session);key=secrets.token_hex(16)
            op={'kind':kind,'operation_id':key,'idempotency_key':key,'payload':{'draft_id':draft['id'],'details':draft['details']}};grant=grant_for(session,op)
            result=call('/direct/v1/actions/'+kind,'POST',{k:v for k,v in op.items() if k!='kind'},grant=grant)
            return result,op,grant
        def passed(label):checks.append(label);print('PASS '+label,flush=True)
        try:
            rider,admin,driver=login('rider-a1'),login('admin-a1'),login('driver-a1');read=grant_for(rider)
            ride,_,_=command(rider,'request',{'service_id':'service-a','origin_stop_id':'stop-a','destination_stop_id':'stop-b','passengers':1});ride=ride['current'];key=secrets.token_hex(16)
            ride=call('/api/actions/accept','POST',{'operation_id':key,'idempotency_key':key,'payload':{'ride_id':ride['id'],'version':ride['version'],'stopped':True}},session=driver)['current']
            assert call('/vehicle-locations',grant=read,status=500)['title']=='VEHICLE_OBSERVATIONS_NOT_ACQUIRED'
            assert call('/direct/v1/operation-delays',grant=read)['availability']=='incomplete'
            passed('引受済みでも観測未取得は成功した空リストや遅延なしにならない')
            command(admin,'observation_configure',fixture['source']);now=time.time()
            data={'vehicle_id':'vehicle-a1','run_id':ride['observation']['run_id'],'source_id':fixture['source']['source_id'],'observed_at':iso(now-61),'location':fixture['location'],'delays':[]}
            first,op,grant=command(admin,'observation_publish',data)
            assert call('/direct/v1/vehicle-locations',grant=read)['observations'][0]['location_status']=='stale'
            call('/vehicle-locations',grant=read,status=500)
            assert call('/operation-delays',grant=read)['total']==0
            passed('61秒前の架空位置は期限切れ、取得済みの空の遅延一覧は観測時点の報告なしとして区別')
            now=time.time();report={'id':'http-demo-delay','status':'active','delay_minutes':5,'delay_reason':'traffic','started_at':iso(now),'closed_at':None,'closed_reason':None,'effective_end':iso(now+300)}
            data.update(observed_at=iso(now),delays=[report]);command(admin,'observation_publish',data)
            position=call('/vehicle-locations',grant=read);delays=call('/operation-delays',grant=read)
            assert position['vehicle_locations'][0]['location']==fixture['location'] and delays['operation_delays'][0]['delay_minutes']==5
            assert call('/direct/v1/vehicle-locations',grant=read)['vehicle_locations']==position['vehicle_locations']
            assert call('/api/snapshot',session=driver)['rides'][0]['observation']['delay_assessment']=='delayed'
            passed('管理者が承認した架空位置と5分遅延を保存し、標準API・直接API・担当画面で共有')
            replay=call('/direct/v1/actions/observation_publish','POST',{k:v for k,v in op.items() if k!='kind'},grant=grant)
            assert replay['replayed'] and replay['result']==first['result'] and replay['current']['value']['version']==2
            call('/vehicle-locations?vehicle_ids=vehicle-a1',grant=grant_for(login('rider-a2')),status=403)
            call('/api/drafts/observation_publish','POST',data,session=driver,status=403)
            passed('再送は初回結果と現在状態を分け、他利用者の位置照会と運転者による観測更新を拒否')
            now=time.time();data.update(observed_at=iso(now),delays=[{**report,'status':'resolved','closed_at':iso(now),'closed_reason':'resolved'}]);command(admin,'observation_publish',data)
            assert call('/operation-delays',grant=read)['total']==0
            assert call('/operation-delays?status=resolved',grant=read)['operation_delays'][0]['status']=='resolved'
            command(admin,'observation_configure',{**fixture['source'],'enabled':False})
            call('/vehicle-locations',grant=read,status=500)
            assert call('/direct/v1/vehicle-locations',grant=read)['observations'][0]['location_status']=='stopped'
            passed('解消は別の明示記録で反映し、取得元を停止すると現在情報の提供も停止')
            command(rider,'cancel',{'ride_id':ride['id']})
            call('/vehicle-locations?vehicle_ids=vehicle-a1',grant=read,status=403)
            assert call('/api/snapshot',session=rider)['rides'][0]['observation'] is None
            passed('予約取消後は既存の読取委任でも車両位置にアクセスできない')
            return {'status':'PASS','checked_at_utc':iso(),'scope':'SYNTHETIC_REAL_HTTP_OBSERVATIONS_WITH_OAS30_AND_OAS31_VALIDATION','checks':checks,'fixture':'fixtures/synthetic-observations.json','live_source_connected':False,'external_partner_tested':False,'production_conformance':False,'public_feed_created':False}
        finally:server.shutdown();server.server_close();thread.join(2)

if __name__=='__main__':
    report=run();(ROOT/'artifacts/test-results/observation-client-demo.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f'{len(report["checks"])}項目合格。架空の観測試験であり、実GPS・実遅延・到着予測ではありません。')
