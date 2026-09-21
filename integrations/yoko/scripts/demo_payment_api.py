"""Reproduce the synthetic payment-information ledger with synthetic data and real loopback HTTP.

The isolated database is deleted on exit. No input URL, production DB, payment,
real user, external terms fetch or token output is supported.
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
from scripts.configure_payment_demo import create as initialize
from app.server import LocalServer
from scripts.export_local_openapi import build
from openapi_schema_validator import OAS31Validator

def run():
    checks=[];spec=build()
    with tempfile.TemporaryDirectory() as folder:
        db=Path(folder)/'payments.sqlite3';initialize(db)
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
                for prefix in ('/api/payments/','/direct/v1/payments/'):
                    if template.startswith(prefix):template=prefix+'{id}'
                pointer='#/paths/'+template.replace('~','~0').replace('/','~1')+'/'+method.lower()
                if body is not None and code<400:
                    OAS31Validator({**spec,'$ref':pointer+'/requestBody/content/application~1json/schema'},format_checker=OAS31Validator.FORMAT_CHECKER).validate(body)
                OAS31Validator({**spec,'$ref':pointer+f'/responses/{code}/content/application~1json/schema'},format_checker=OAS31Validator.FORMAT_CHECKER).validate(value)
            return (value,cookie) if path=='/api/session' else value
        def login(actor):
            value,cookie=call('/api/session','POST',{'username':actor,'password':'local-test-only'})
            return {'cookie':cookie.split(';')[0],'csrf':value['csrf']}
        def grant_for(session,operation=None):
            return call('/api/client-grants','POST',{'client_id':'synthetic-payment-client','scopes':['mobility:read']+(['mobility:execute'] if operation else []),'expires_in':300,'operation':operation},session)
        def approve(session,kind,data):
            draft=call('/api/drafts/'+kind,'POST',data,session);key=secrets.token_hex(16)
            op={'kind':kind,'operation_id':key,'idempotency_key':key,'payload':{'draft_id':draft['id'],'details':draft['details']}}
            return op,grant_for(session,op)
        def direct(op,grant):
            return call('/direct/v1/actions/'+op['kind'],'POST',{k:v for k,v in op.items() if k!='kind'},grant=grant)
        def passed(label):checks.append(label);print('PASS '+label,flush=True)
        try:
            rider,admin,driver=login('rider-a1'),login('admin-a1'),login('driver-a1')
            read=grant_for(rider);admin_read=grant_for(admin)
            request={'service_id':'service-a','origin_stop_id':'stop-a','destination_stop_id':'stop-b','passengers':1}
            op,grant=approve(rider,'request',request);ride=direct(op,grant)['current'];key=secrets.token_hex(16)
            ride=call('/api/actions/accept','POST',{'operation_id':key,'idempotency_key':key,'payload':{'ride_id':ride['id'],'version':ride['version'],'stopped':True}},session=driver)['current']
            payment_path='/reservations/'+ride['id']+'/payment'
            assert call(payment_path,grant=read,status=404)['title']=='PAYMENT_NOT_RECORDED'
            assert call('/api/snapshot',session=admin)['rides'][0]['payment']['record'] is None
            passed('明示した架空の820円で予約・引受し、決済情報の未登録を404で区別')
            def record(status):
                data={'ride_id':ride['id'],'amount':820,'payment_status':status}
                operation,authorization=approve(admin,'payment_update',data)
                value=call(payment_path,'PUT',{'amount':820,'payment_status':status},grant=authorization,operation=operation)
                return value,operation,authorization
            first,first_op,first_grant=record('uncollected')
            assert first['id']==ride['id'] and first['amount']==820
            assert call(payment_path,grant=read)==first
            assert call(payment_path,grant=admin_read)==first
            assert call('/direct/v1/payments/'+ride['id'],grant=read)['record']['version']==1
            passed('管理者の確認・個別委任から標準PUTで未収を保存し、本人と管理者が標準GETで照会')
            second,_,_=record('received')
            assert second['created_at']==first['created_at']
            assert call(payment_path,'PUT',{'amount':820,'payment_status':'uncollected'},grant=first_grant,operation=first_op)==first
            replay=direct(first_op,first_grant)
            assert replay['replayed'] and replay['result']['value']['record']['payment_status']=='uncollected'
            assert replay['current']['value']['record']['payment_status']=='received' and replay['current']['value']['record']['version']==2
            passed('受領済みへの更新後、古い標準PUTと直接APIの再送は初回結果を返し、現在の受領記録を維持')
            denied={'ride_id':ride['id'],'amount':820,'payment_status':'received'}
            assert call('/api/drafts/payment_update','POST',denied,session=rider,status=403)['error']['code']=='FORBIDDEN'
            other=grant_for(login('rider-a2'))
            call(payment_path,grant=other,status=404)
            call(payment_path,grant=grant_for(driver),status=403)
            passed('本人による自己申告の受領登録、他利用者の照会、ドライバーの決済情報照会を拒否')
            cancel,cancel_grant=approve(rider,'cancel',{'ride_id':ride['id']})
            direct(cancel,cancel_grant)
            current=call('/direct/v1/payments/'+ride['id'],grant=admin_read)
            assert current['record']['amount']==820 and current['record']['payment_status']=='received'
            assert current['review_reason']=='refund_review_required' and current['expected_amount']==0
            call('/api/drafts/payment_update','POST',{'ride_id':ride['id'],'amount':0,'payment_status':'cancelled'},session=admin,status=409)
            assert call(payment_path,grant=read)['payment_status']=='received'
            passed('予約取消後も受領820円を保持し、返金確認を表示。未実装の返金を完了扱いにしない')
            return {'status':'PASS','checked_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'ISOLATED_SYNTHETIC_REAL_HTTP_PAYMENT_INFORMATION_WITH_OAS30_AND_OAS31_VALIDATION','checks':checks,'fixture':'fixtures/synthetic-payment.json','external_partner_tested':False,'production_conformance':False,'charges_executed':False,'refunds_executed':False,'payment_provider_connected':False}
        finally:
            server.shutdown();server.server_close();thread.join(2)

if __name__=='__main__':
    report=run();(ROOT/'artifacts/test-results/payment-client-demo.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f'{len(report["checks"])}項目合格。架空の決済情報台帳のみ。実際の請求・返金はありません。')
