"""Reproduce the catalog slice with synthetic data and real loopback HTTP.

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
from app.db import initialize
from app.server import LocalServer
from scripts.export_local_openapi import build
from openapi_schema_validator import OAS31Validator

def run():
    fixture=json.loads((ROOT/'fixtures/synthetic-catalog.json').read_text());checks=[];spec=build()
    with tempfile.TemporaryDirectory() as folder:
        db=Path(folder)/'catalog.sqlite3';initialize(db)
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
            return call('/api/client-grants','POST',{'client_id':'synthetic-catalog-client','scopes':['mobility:read']+(['mobility:execute'] if operation else []),'expires_in':300,'operation':operation},session)
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
            rider,admin=login('rider-a1'),login('admin-a1');read=grant_for(rider)
            assert call('/services',grant=read,status=500)['title']=='SERVICE_MASTER_INCOMPLETE'
            configure('service_configure',fixture['service'])
            for stop in fixture['stops']:configure('stop_configure',stop)
            term=configure('terms_publish',fixture['terms'])
            assert call('/services',grant=read)['total']==1
            assert call('/services/service-a',grant=read)['access_scope']=='registered_user_only'
            assert call('/stops?location=139.5,35.5&radius=500',grant=read)['total']==2
            passed('未設定を拒否し、管理者が承認した架空の営業日・座標を標準形式で照会')
            person,created,_=standard('profile_create',fixture['profile'],'/passengers',status=201)
            assert person['id']=='rider-a1'
            standard('profile_update',{'first_name':'更新試験','last_name':'架空'},'/passengers/rider-a1','PUT')
            assert 'email' not in call('/passengers/rider-a1',grant=read)
            assert call('/passengers/rider-a1/services',grant=read)['total']==1
            passed('本人の登録・取得・全項目置換・利用可能サービスを原本契約で検証')
            request={'service_id':'service-a','origin_stop_id':'stop-a','destination_stop_id':'stop-b','passengers':1}
            assert call('/api/drafts/request','POST',request,rider,status=409)['error']['code']=='AGREEMENT_REQUIRED'
            assert call('/terms',grant=read)['terms'][0]['id']==term['id']
            data={'agreements':[{'terms_id':term['id'],'agreed_at':datetime.now(timezone.utc).isoformat()}]}
            result,op,grant=standard('agreements_register',data,'/passengers/rider-a1/agreements')
            assert result['agreements'][0]['status']=='created' and direct(op,grant)['replayed']
            assert len(call('/passengers/rider-a1/agreements',grant=read)['agreements'])==1
            call('/api/drafts/request','POST',request,rider)
            passed('最新規約への同意を依頼条件に適用し、入口を替えた再送でも一度だけ保存')
            newer=configure('terms_publish',{**fixture['terms'],'url':'https://example.invalid/yoko/terms/v2'})
            assert newer['id']!=term['id']
            assert call('/api/drafts/request','POST',request,rider,status=409)['error']['code']=='AGREEMENT_REQUIRED'
            data={'agreements':[{'terms_id':newer['id'],'agreed_at':datetime.now(timezone.utc).isoformat()}]}
            standard('agreements_register',data,'/passengers/rider-a1/agreements')
            assert len(call('/passengers/rider-a1/agreements',grant=read)['agreements'])==2
            passed('規約の新版は別IDとなり、旧同意を残して再同意を要求')
            result,deleted,_=standard('profile_delete',{},'/passengers/rider-a1','DELETE',204)
            assert result is None
            call('/passengers/rider-a1',grant=read,status=401)
            rider=login('rider-a1');read=grant_for(rider)
            call('/passengers/rider-a1',grant=read,status=404)
            call('/passengers/rider-a1/agreements',grant=read,status=404)
            receipt=call('/direct/v1/operations/'+created['operation_id'],grant=read)
            assert receipt['result'] is None and receipt['current']['redacted']
            assert call('/direct/v1/operations/'+deleted['operation_id'],grant=read)['current']['deleted']
            passed('削除は本文なし204、既存委任失効、取得404、個人情報を消した操作照合')
            return {'status':'PASS','checked_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'ISOLATED_SYNTHETIC_REAL_HTTP_CATALOG_WITH_OAS30_AND_OAS31_VALIDATION','checks':checks,'external_partner_tested':False,'production_conformance':False,'public_feed_created':False}
        finally:
            server.shutdown();server.server_close();thread.join(2)

if __name__=='__main__':
    report=run();(ROOT/'artifacts/test-results/catalog-client-demo.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f'{len(report["checks"])}項目合格。すべて架空データ・一時環境です。')
