import copy
import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from app.core import DomainError,iso
from app.db import ROOT,connect,initialize
from tests.test_core import REQUEST
from tests.test_p3 import Fixture
from tests import test_p3 as p3
from zoneinfo import ZoneInfo

FIXTURE=json.loads((ROOT/'fixtures/synthetic-catalog.json').read_text())

class CatalogTests(Fixture):
    def command(self,kind,data,actor='rider-a1'):
        return self.execute(self.prepare(kind,data,actor),actor)
    def register(self):return self.command('profile_create',copy.deepcopy(FIXTURE['profile']))
    def publish(self,**kwargs):return self.command('terms_publish',{**FIXTURE['terms'],**kwargs},'admin-a1')['value']
    def agree(self,term):return self.command('agreements_register',{'agreements':[{'terms_id':term['id'],'agreed_at':iso(self.core.clock())}]})
    def configure(self,data=None):return self.command('service_configure',data or copy.deepcopy(FIXTURE['service']),'admin-a1')
    def test_profile_requires_names_and_update_replaces_omitted_personal_fields(self):
        for body in [{},{'first_name':'片方のみ'},{'first_name':'テスト','last_name':'架空','home_address':{'location':{'coordinates':[139,35]}}}]:
            self.denied('NAME_REQUIRED' if 'last_name' not in body else 'INVALID_INPUT',self.prepare,'profile_create',body)
        first=self.register()['value'];self.assertEqual(first['id'],'rider-a1')
        self.denied('PROFILE_EXISTS',self.register)
        self.command('profile_update',{'first_name':'カナ','last_name':'変更'})
        current=self.core.catalog.read('rider-a1','passenger','rider-a1')
        self.assertNotIn('email',current);self.assertEqual(current['last_name'],'変更')
        self.denied('FORBIDDEN',self.core.catalog.read,'rider-a2','passenger','rider-a1')
        self.denied('FORBIDDEN',self.core.catalog.read,'admin-a1','passenger','rider-a1')
    def test_physically_delete_profile_agreements_and_cached_personal_data(self):
        op=self.prepare('profile_create',copy.deepcopy(FIXTURE['profile']));self.execute(op);term=self.publish();self.agree(term)
        self.grant();self.prepare('profile_update',{'first_name':'消去対象','last_name':'架空'})
        delete=self.prepare('profile_delete',{});self.execute(delete)
        for table in ['passengers','agreements','drafts','client_grants']:
            where=" WHERE actor_id='rider-a1'" if table in ('drafts','client_grants') else ''
            self.assertEqual(self.sql('SELECT COUNT(*) FROM '+table+where),[(0,)],table)
        self.denied('NOT_FOUND',self.core.catalog.read,'rider-a1','passenger','rider-a1')
        self.denied('NOT_FOUND',self.core.catalog.read,'rider-a1','agreements','rider-a1')
        receipt=self.core.operation('rider-a1',op['operation_id'])
        self.assertIsNone(receipt['result']);self.assertTrue(receipt['current']['redacted'])
        self.assertNotIn('rider@example.invalid',json.dumps(self.sql('SELECT result_json FROM catalog_operations')))
        self.denied('RESULT_ERASED',self.execute,op)
    def test_delete_does_not_cancel_or_remove_active_reservations(self):
        self.register();ride=self.create()
        self.denied('ACTIVE_RESERVATIONS',self.prepare,'profile_delete',{})
        self.assertEqual(self.core.get_ride('rider-a1',ride['id'])['status'],'requested')
        self.command('cancel',{'ride_id':ride['id']});self.command('profile_delete',{})
        self.assertEqual(self.core.get_ride('rider-a1',ride['id'])['status'],'cancelled')
        self.denied('PROFILE_REQUIRED',self.create)
        self.register();self.assertEqual(self.create()['status'],'requested')
    def test_updated_terms_get_new_id_and_need_new_agreement(self):
        self.register();term=self.publish();self.agree(term)
        draft=self.prepare('request',REQUEST)
        newer=self.publish(url='https://example.invalid/yoko/terms/v2')
        self.assertNotEqual(term['id'],newer['id'])
        self.assertEqual(self.core.catalog.read('rider-a1','terms')['terms'][0]['id'],newer['id'])
        self.denied('AGREEMENT_REQUIRED',self.execute,draft)
        self.assertEqual(len(self.core.catalog.read('rider-a1','agreements','rider-a1')['agreements']),1)
        self.agree(newer)
        self.denied('TERMS_CHANGED',self.execute,draft)
        self.assertEqual(self.create()['status'],'requested')
    def test_duplicate_agreement_preserves_original_time_and_no_side_effect_repeat(self):
        self.register();term=self.publish();first=self.agree(term)['value']['agreements'][0]
        second=self.agree(term)['value']['agreements'][0]
        self.assertEqual((first['status'],second['status']),('created','already_agreed'))
        self.assertEqual(first['agreed_at'],second['agreed_at'])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM agreements'),[(1,)])
    def test_other_tenant_cannot_agree_or_configure_and_future_consent_is_rejected(self):
        self.register();term=self.publish()
        self.command('profile_create',{'first_name':'別','last_name':'架空'},'rider-b1')
        self.denied('NOT_FOUND',self.prepare,'agreements_register',{'agreements':[{'terms_id':term['id'],'agreed_at':iso()}]},'rider-b1')
        self.denied('INVALID_AGREED_AT',self.prepare,'agreements_register',{'agreements':[{'terms_id':term['id'],'agreed_at':'2999-01-01T00:00:00Z'}]})
        self.denied('FORBIDDEN',self.prepare,'service_configure',FIXTURE['service'])
    def test_catalog_commands_share_keys_with_ride_operations(self):
        op=self.prepare('profile_create',copy.deepcopy(FIXTURE['profile']));self.execute(op)
        ride=self.prepare('request',REQUEST);ride['operation_id']=op['operation_id'];ride['idempotency_key']=op['idempotency_key']
        self.denied('IDEMPOTENCY_CONFLICT',self.execute,ride)
        ride=self.prepare('request',REQUEST);self.execute(ride)
        change=self.prepare('profile_update',copy.deepcopy(FIXTURE['profile']));change['operation_id']=ride['operation_id'];change['idempotency_key']=ride['idempotency_key']
        self.denied('IDEMPOTENCY_CONFLICT',self.execute,change)
    def test_concurrent_profile_updates_cannot_overwrite_newer_approval(self):
        self.register();one=self.prepare('profile_update',{'first_name':'一','last_name':'架空'});two=self.prepare('profile_update',{'first_name':'二','last_name':'架空'})
        barrier=threading.Barrier(2)
        def run(op):
            barrier.wait(3)
            try:self.execute(op);return 'ok'
            except DomainError as error:return error.code
        with ThreadPoolExecutor(2) as pool:
            jobs=[pool.submit(run,op) for op in [one,two]]
            self.assertCountEqual([j.result() for j in jobs],['ok','STALE_CATALOG'])
    def test_catalog_rollback_and_fake_outbox_retry(self):
        op=self.prepare('profile_create',copy.deepcopy(FIXTURE['profile']))
        self.sql("CREATE TRIGGER catalog_fail BEFORE INSERT ON catalog_outbox BEGIN SELECT RAISE(ABORT,'test failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.execute(op)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM passengers'),[(0,)])
        self.sql('DROP TRIGGER catalog_fail');self.execute(op)
        self.assertEqual(self.core.snapshot('admin-a1')['outbox_pending'],1)
        self.core.deliver_fake(True);self.assertEqual(self.sql('SELECT COUNT(*) FROM catalog_fake_inbox'),[(0,)])
        self.core.deliver_fake();self.core.deliver_fake()
        self.assertEqual(self.sql('SELECT COUNT(*) FROM catalog_fake_inbox'),[(1,)])
        self.assertEqual(self.core.snapshot('admin-a1')['outbox_pending'],0)
    def test_service_hours_terms_and_registration_apply_to_same_request_core(self):
        self.configure();self.denied('PROFILE_REQUIRED',self.create);self.register();self.create()
        config=copy.deepcopy(FIXTURE['service'])
        config['operating_hours']={k:[] for k in config['operating_hours']}
        self.configure(config);self.denied('SERVICE_CLOSED',self.create)
        today=datetime.fromtimestamp(self.core.clock(),timezone.utc).astimezone(ZoneInfo('Asia/Tokyo')).date().isoformat()
        config['special_operating_hours']=[{'date':today,'time_slots':[{'start_time_offset_sec':0,'end_time_offset_sec':86400}]}]
        self.configure(config);self.assertEqual(self.create()['status'],'requested')
    def test_service_filters_pagination_and_qualification_are_real(self):
        config=copy.deepcopy(FIXTURE['service']);config['cities']=[{'prefecture_code':'99','prefecture_name':'架空県','municipalities':[{'code':'99001','name':'架空市'}]}]
        self.configure(config);self.register()
        page=self.core.catalog.read('rider-a1','services',params={'municipality_code':'99001','limit':1})
        self.assertEqual(page['total'],1);self.assertEqual(len(page['services']),1)
        self.assertEqual(self.core.catalog.read('rider-a1','services',params={'municipality_code':'99002'})['total'],0)
        config['cities'].append({'prefecture_code':'98','prefecture_name':'別架空県','municipalities':[{'code':'98001','name':'別架空市'}]})
        self.configure(config)
        self.assertEqual(self.core.catalog.read('rider-a1','services',params={'prefecture_code':'99','municipality_code':'98001'})['total'],0)
        self.sql("UPDATE users SET eligible=0 WHERE id='rider-a1'")
        self.assertEqual(self.core.catalog.read('rider-a1','eligible_services','rider-a1')['total'],0)
        self.assertEqual(self.core.catalog.read('rider-b1','services')['total'],0)
    def test_stops_stay_unknown_until_explicitly_configured_and_radius_is_applied(self):
        self.denied('STOP_COORDINATES_NOT_CONFIGURED',self.core.catalog.read,'rider-a1','stops')
        for stop in FIXTURE['stops']:self.command('stop_configure',copy.deepcopy(stop),'admin-a1')
        page=self.core.catalog.read('rider-a1','stops',params={'location':'139.5,35.5','radius':500,'limit':1})
        self.assertEqual((page['total'],len(page['stops'])),(2,1))
        expired={**FIXTURE['stops'][0],'start_datetime':'2020-01-01T00:00:00Z','end_datetime':'2021-01-01T00:00:00Z'}
        self.command('stop_configure',expired,'admin-a1');self.denied('INVALID_STOP',self.create)
    def test_consent_rechecks_terms_after_prepare_and_delete_rechecks_active_ride(self):
        self.register();term=self.publish()
        consent=self.prepare('agreements_register',{'agreements':[{'terms_id':term['id'],'agreed_at':iso()}]})
        new=self.publish(url='https://example.invalid/yoko/terms/new')
        self.denied('TERMS_REPLACED',self.execute,consent)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM agreements'),[(0,)])
        self.agree(new)
        deletion=self.prepare('profile_delete',{});ride=self.create()
        self.denied('ACTIVE_RESERVATIONS',self.execute,deletion)
        self.assertEqual(self.core.catalog.read('rider-a1','passenger','rider-a1')['id'],'rider-a1')
        self.assertEqual(self.core.get_ride('rider-a1',ride['id'])['status'],'requested')
    def test_overnight_hours_and_explicit_holiday_calendar_apply_in_tokyo(self):
        self.core.clock=lambda:datetime(2026,9,20,1,0,tzinfo=ZoneInfo('Asia/Tokyo')).timestamp()
        config=copy.deepcopy(FIXTURE['service'])
        config['operating_hours']={k:[] for k in config['operating_hours']}
        config['operating_hours']['saturday']=[{'start_time_offset_sec':23*3600,'end_time_offset_sec':26*3600}]
        self.configure(config);self.register();self.assertEqual(self.create()['status'],'requested')
        config['holiday_dates']=['2026-09-19'];self.configure(config)
        self.denied('SERVICE_CLOSED',self.create)
        config['special_operating_hours']=[{'date':'2026-09-19','time_slots':config['operating_hours']['saturday']}]
        self.configure(config);self.assertEqual(self.create()['status'],'requested')
    def test_version_two_migration_keeps_ride_and_grant_without_inventing_profiles(self):
        ride=self.create();grant=self.grant()
        for table in ['catalog_fake_inbox','catalog_outbox','catalog_events','catalog_operations','agreements','terms','passengers','passenger_versions','stop_profiles','service_profiles']:
            self.sql('DROP TABLE '+table)
        self.sql("UPDATE meta SET value='2' WHERE key='schema_version'")
        initialize(self.path)
        self.assertEqual(self.sql("SELECT value FROM meta WHERE key='schema_version'"),[('8',)])
        self.assertEqual(self.core.get_ride('rider-a1',ride['id'],self.authz(grant))['status'],'requested')
        self.assertEqual(self.sql('SELECT COUNT(*) FROM passengers'),[(0,)])
        self.assertEqual(self.register()['value']['id'],'rider-a1')

# Borrow only HTTP fixture helpers, not inherited test methods.
class CatalogHTTPTests(Fixture):
    start=p3.ClientHTTPTests.start;stop=p3.ClientHTTPTests.stop;login=p3.ClientHTTPTests.login;client_write=p3.ClientHTTPTests.client_write;update_headers=p3.ClientHTTPTests.update_headers
    def setUp(self):super().setUp();self.start();self.addCleanup(self.stop)
    def request(self,path,method='GET',body=None,grant=None,session=None,headers=None):
        import http.client
        conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5);h={}
        if grant:h.update({'Authorization':'Bearer '+grant['access_token'],'X-Client-ID':grant['client_id']})
        if session:h.update({'Cookie':session[0],'X-CSRF-Token':session[1],'X-Requested-With':'YokoLocal'})
        if body is not None:h['Content-Type']='application/json'
        h.update(headers or {});conn.request(method,path,json.dumps(body) if body is not None else None,h)
        response=conn.getresponse();raw=response.read();code=response.status;data=json.loads(raw) if raw else None;conn.close()
        match=self.contract.match(method,path.split('?')[0])
        if match:self.contract.response(match,code,data)
        if path.startswith(('/api/','/direct/')):
            from openapi_schema_validator import OAS31Validator
            from scripts.export_local_openapi import build
            spec=build();template=path.split('?')[0]
            if template.startswith('/direct/v1/operations/'):template='/direct/v1/operations/{id}'
            for prefix in ('/api/payments/','/direct/v1/payments/'):
                if template.startswith(prefix):template=prefix+'{id}'
            pointer='#/paths/'+template.replace('~','~0').replace('/','~1')+'/'+method.lower()
            if body is not None and code<400:
                OAS31Validator({**spec,'$ref':pointer+'/requestBody/content/application~1json/schema'},format_checker=OAS31Validator.FORMAT_CHECKER).validate(body)
            OAS31Validator({**spec,'$ref':pointer+f'/responses/{code}/content/application~1json/schema'},format_checker=OAS31Validator.FORMAT_CHECKER).validate(data)
        return code,data
    def write(self,kind,body,path,method='POST',actor='rider-a1'):
        operation=self.prepare(kind,body,actor);grant=self.grant(operation,actor)
        return self.request(path,method,None if method=='DELETE' else body,grant,headers=self.update_headers(operation))
    def admin(self,kind,data):
        operation=self.prepare(kind,data,'admin-a1');grant=self.grant(operation,'admin-a1');code,result=self.client_write(operation,grant)
        self.assertEqual(code,200,result);return result['result']['value']
    def test_all_eleven_added_standard_operations_success_over_real_http(self):
        code,person=self.write('profile_create',copy.deepcopy(FIXTURE['profile']),'/passengers');self.assertEqual(code,201,person)
        grant=self.grant();self.assertEqual(self.request('/passengers/rider-a1',grant=grant)[1]['email'],'rider@example.invalid')
        body={'first_name':'更新','last_name':'架空'};self.assertEqual(self.write('profile_update',body,'/passengers/rider-a1','PUT')[0],200)
        term=self.admin('terms_publish',copy.deepcopy(FIXTURE['terms']))
        self.assertEqual(self.request('/terms',grant=grant)[1]['terms'][0]['id'],term['id'])
        consent={'agreements':[{'terms_id':term['id'],'agreed_at':iso()}]}
        code,result=self.write('agreements_register',consent,'/passengers/rider-a1/agreements');self.assertEqual(code,200,result)
        self.assertEqual(self.request('/passengers/rider-a1/agreements',grant=grant)[1]['agreements'][0]['terms_id'],term['id'])
        self.admin('service_configure',copy.deepcopy(FIXTURE['service']))
        for path in ['/services','/services/service-a','/passengers/rider-a1/services']:
            self.assertEqual(self.request(path,grant=grant)[0],200,path)
        for stop in FIXTURE['stops']:self.admin('stop_configure',copy.deepcopy(stop))
        self.assertEqual(self.request('/stops',grant=grant)[1]['total'],3)
        self.assertEqual(self.write('profile_delete',{},'/passengers/rider-a1','DELETE'),(204,None))
        self.assertEqual(self.request('/passengers/rider-a1',grant=grant)[0],401)
        new=self.grant()
        for path in ['/passengers/rider-a1','/passengers/rider-a1/agreements']:
            self.assertEqual(self.request(path,grant=new)[0],404,path)
    def test_exact_approval_and_object_authorization_for_profile_update(self):
        self.write('profile_create',copy.deepcopy(FIXTURE['profile']),'/passengers')
        body={'first_name':'更新','last_name':'架空'};operation=self.prepare('profile_update',body);grant=self.grant(operation)
        self.assertEqual(self.request('/passengers/rider-a1','PUT',{**body,'first_name':'改ざん'},grant,headers=self.update_headers(operation))[0],403)
        self.assertEqual(self.request('/passengers/rider-a2','PUT',body,grant,headers=self.update_headers(operation))[0],403)
        code,result=self.request('/passengers/rider-a1','PUT',body,grant,headers=self.update_headers(operation));self.assertEqual(code,200,result)
        self.assertTrue(self.client_write(operation,grant)[1]['replayed'])
        self.assertEqual(self.core.operation('rider-a1',operation['operation_id'])['result']['value'],result)
    def test_service_terms_have_separate_scope_and_existing_agreements_survive_replacement(self):
        self.write('profile_create',copy.deepcopy(FIXTURE['profile']),'/passengers')
        a=self.admin('terms_publish',copy.deepcopy(FIXTURE['terms']))
        b=self.admin('terms_publish',{**FIXTURE['terms'],'service_id':'service-a','category':'service'})
        self.admin('service_configure',copy.deepcopy(FIXTURE['service']))
        data={'agreements':[{'terms_id':t['id'],'agreed_at':iso()} for t in [a,b]]}
        self.assertEqual(self.write('agreements_register',data,'/passengers/rider-a1/agreements')[0],200)
        grant=self.grant();self.assertEqual(len(self.request('/terms',grant=grant)[1]['terms']),1)
        agreements=self.request('/passengers/rider-a1/agreements?service_id=service-a',grant=grant)[1]['agreements']
        self.assertEqual([x['terms_id'] for x in agreements],[b['id']])
        self.assertEqual(self.request('/services/service-a',grant=grant)[1]['service_terms'][0]['id'],b['id'])
    def test_missing_master_and_unimplemented_operations_are_distinct(self):
        grant=self.grant()
        for path,code in [('/services','SERVICE_MASTER_INCOMPLETE'),('/stops','STOP_COORDINATES_NOT_CONFIGURED'),('/vehicle-locations','VEHICLE_OBSERVATIONS_NOT_ACQUIRED')]:
            status,error=self.request(path,grant=grant);self.assertEqual((status,error['title']),(500,code))
