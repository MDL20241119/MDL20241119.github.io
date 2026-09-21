"""Reproduce offered-run search and standard booking with synthetic data and real loopback HTTP.

The isolated database is deleted on exit. No input URL, production DB, payment,
real user, external terms fetch or token output is supported.
"""
import http.client
import json
import secrets
import sys
import tempfile
import threading
from datetime import datetime,timezone,timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from app.db import initialize
from app.server import LocalServer
from scripts.export_local_openapi import build
from openapi_schema_validator import OAS31Validator

def run():
    fixture=json.loads((ROOT/'fixtures/synthetic-catalog.json').read_text());checks=[];spec=build()
    route=json.loads((ROOT/'fixtures/synthetic-booking.json').read_text())['routes'][0]
    with tempfile.TemporaryDirectory() as folder:
        db=Path(folder)/'booking.sqlite3';initialize(db)
        server=LocalServer(('127.0.0.1',0),db,enable_mlit=True)
        thread=threading.Thread(target=lambda:server.serve_forever(poll_interval=.01),daemon=True);thread.start()
        def call(path,method='GET',body=None,session=None,grant=None,operation=None,status=200):
            headers={}
            if body is not None:headers['Content-Type']='application/json'
            if session:headers.update({'Cookie':session['cookie'],'X-CSRF-Token':session['csrf'],'X-Requested-With':'YokoLocal'})
            if path=='/api/session':headers['X-Requested-With']='YokoLocal'
            if grant:headers.update({'Authorization':'Bearer '+grant['access_token'],'X-Client-ID':grant['client_id']})
            if operation:headers.update({'X-Operation-ID':operation['operation_id'],'Idempotency-Key':operation['idempotency_key']})
            conn=http.client.HTTPConnection('127.0.0.1',server.server_address[1],timeout=5)
            conn.request(method,path,json.dumps(body) if body is not None else None,headers)
            response=conn.getresponse();raw=response.read();value=json.loads(raw) if raw else None
            cookie=response.getheader('Set-Cookie');code=response.status;conn.close()
            assert code==status,(method,path,code,value)
            match=server.mlit.contract.match(method,path.split('?')[0])
            if match:server.mlit.contract.response(match,code,value)
            else:
                template=path.split('?')[0]
                if template.startswith('/direct/v1/operations/'):template='/direct/v1/operations/{id}'
                pointer='#/paths/'+template.replace('~','~0').replace('/','~1')+'/'+method.lower()
                if body is not None and code<400:
                    OAS31Validator({**spec,'$ref':pointer+'/requestBody/content/application~1json/schema'},format_checker=OAS31Validator.FORMAT_CHECKER).validate(body)
                OAS31Validator({**spec,'$ref':pointer+f'/responses/{code}/content/application~1json/schema'},format_checker=OAS31Validator.FORMAT_CHECKER).validate(value)
            return (value,cookie) if path=='/api/session' else value
        def login(actor):
            value,cookie=call('/api/session','POST',{'username':actor,'password':'local-test-only'})
            return {'cookie':cookie.split(';')[0],'csrf':value['csrf']}
        def grant_for(session,operation=None):
            return call('/api/client-grants','POST',{'client_id':'synthetic-booking-client','scopes':['mobility:read']+(['mobility:execute'] if operation else []),'expires_in':300,'operation':operation},session)
        def approve(session,kind,data):
            draft=call('/api/drafts/'+kind,'POST',data,session);key=secrets.token_hex(16)
            op={'kind':kind,'operation_id':key,'idempotency_key':key,'payload':{'draft_id':draft['id'],'details':draft['details']}}
            return op,grant_for(session,op)
        def direct(op,grant):
            return call('/direct/v1/actions/'+op['kind'],'POST',{k:v for k,v in op.items() if k!='kind'},grant=grant)
        def configure(kind,data):
            op,grant=approve(admin,kind,data);return direct(op,grant)['current']['value']
        def standard(kind,data,path,method='POST',status=200):
            op,grant=approve(rider,kind,data)
            return call(path,method,None if method=='DELETE' else data,grant=grant,operation=op,status=status),op,grant
        def passed(label):checks.append(label);print('PASS '+label,flush=True)
        try:
            rider,admin,driver=login('rider-a1'),login('admin-a1'),login('driver-a1')
            configure('service_configure',fixture['service'])
            for stop in fixture['stops']:configure('stop_configure',stop)
            configure('route_configure',route)
            term=configure('terms_publish',fixture['terms'])
            standard('profile_create',fixture['profile'],'/passengers',status=201)
            standard('agreements_register',{'agreements':[{'terms_id':term['id'],'agreed_at':datetime.now(timezone.utc).isoformat()}]},'/passengers/rider-a1/agreements')
            read=grant_for(rider)
            passed('管理者の架空設定、本人の登録・最新規約同意を実HTTPで保存')
            def open_offer():
                data={'service_id':'service-a','origin_stop_id':'stop-a','destination_stop_id':'stop-b','pickup_at':(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat(),'vehicle_name':'架空の予約実演車両','stopped':True}
                op,grant=approve(driver,'offer_open',data)
                return direct(op,grant)['current']['value']
            offer=open_offer()
            assert offer['reserved']==0 and offer['accepting']
            passed('ドライバーの停車確認・計画便提示を保存し、表示時の確保席は0')
            def search():
                query={'service_ids':['service-a'],'preferred_time':{'type':'pickup','datetime':datetime.now(timezone.utc).isoformat()},'pickup':{'type':'fixed_stop','stop_id':'stop-a'},'dropoff':{'type':'fixed_stop','stop_id':'stop-b'},'passenger_count':[{'passenger_type_id':'mdl-synthetic-general','count':1}],'accessibility_feature_count':[]}
                return call('/reservations/candidates','POST',query,grant=read)['candidates'][0]
            candidate=search()
            assert candidate['reservation_request']['pickup']['datetime']==offer['pickup_at']
            assert call('/api/snapshot',session=driver)['offers'][0]['reserved']==0
            passed('標準候補応答を原本スキーマで検証し、検索では席を確保しない')
            def book(candidate):
                body={'passenger_id':'rider-a1',**candidate['reservation_request']}
                op,grant=approve(rider,'book',{'candidate_id':body['candidate_id']})
                result=call('/reservations','POST',body,grant=grant,operation=op,status=201)
                assert result['status']=='confirmed'
                assert call('/reservations','POST',body,grant=grant,operation=op,status=201)==result
                assert direct(op,grant)['replayed']
                return result,op,grant
            booked,op,grant=book(candidate)
            snapshot=call('/api/snapshot',session=admin)
            assert len(snapshot['rides'])==1 and snapshot['offers'][0]['reserved']==1
            assert call('/passengers/rider-a1/reservations',grant=read)['reservations'][0]==booked
            passed('本人の期限付き個別承認から201を返し、標準・直接APIの再送でも予約と確保席は1')
            current=direct(op,grant)['current']
            for kind in ['arrive','board','complete']:
                key=secrets.token_hex(16)
                current=call('/api/actions/'+kind,'POST',{'operation_id':key,'idempotency_key':key,'payload':{'ride_id':current['id'],'version':current['version'],'stopped':True}},session=driver)['current']
            assert current['status']=='completed'
            assert call('/api/snapshot',session=admin)['offers']==[]
            receipt=call('/direct/v1/operations/'+op['operation_id'],grant=read)
            assert receipt['result']['status']=='assigned' and receipt['current']['status']=='completed'
            passed('3者に共通の到着・乗車・降車を記録し、席の解放と元の結果・現在状態を照合')
            open_offer();second,_,_=book(search())
            cancel,cancel_grant=approve(rider,'cancel',{'ride_id':second['id']})
            body={k:second[k] for k in ('passenger_id','service_id','pickup','dropoff','passenger_count','accessibility_feature_count')}
            body['status']='cancelled'
            for _ in range(2):
                result=call('/reservations/'+second['id'],'PUT',body,grant=cancel_grant,operation=cancel)
                assert result['status']=='cancelled'
            assert call('/api/snapshot',session=admin)['offers']==[]
            passed('別の予約を本人確認後に標準PUTで取り消し、再送しても席は一度だけ解放')
            return {'status':'PASS','checked_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'ISOLATED_SYNTHETIC_REAL_HTTP_BOOKING_WITH_OAS30_AND_OAS31_VALIDATION','checks':checks,'external_partner_tested':False,'production_conformance':False,'times_are':'EXPLICIT_SYNTHETIC_PLANS_NOT_LIVE_OBSERVATIONS','public_feed_created':False}
        finally:
            server.shutdown();server.server_close();thread.join(2)

if __name__=='__main__':
    report=run();(ROOT/'artifacts/test-results/booking-client-demo.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f'{len(report["checks"])}項目合格。すべて架空データ・一時環境です。')
