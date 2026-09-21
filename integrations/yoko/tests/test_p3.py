"""P3: business changes, real HTTP clients, immutable official contract, denial paths."""
import copy
import hashlib
import http.client
import json
import secrets
import shutil
import socket
import sqlite3
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from app.core import Core, DomainError
from app.db import initialize, connect
from app.delegation import Grants
from app.mlit import STATE, PASSENGER_TYPE, SUPPORTED, BLOCKERS, reservation
from app.mlit_contract import Contract, SOURCE, SOURCE_SHA256
from app.server import LocalServer
from tests.test_core import REQUEST

class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=tempfile.TemporaryDirectory()
        cls.template=Path(cls.base.name)/'base.sqlite3'
        initialize(cls.template)
    @classmethod
    def tearDownClass(cls):cls.base.cleanup()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'test.sqlite3';shutil.copyfile(self.template,self.path)
        self.core=Core(self.path);self.grants=Grants(self.core)
    def sql(self,statement,args=()):
        db=connect(self.path)
        try:return [tuple(x) for x in db.execute(statement,args)]
        finally:db.close()
    def prepare(self,kind,data,actor='rider-a1'):
        draft=self.core.prepare(actor,kind,data);op=secrets.token_hex(16)
        return {'operation_id':op,'idempotency_key':op,'kind':kind,'payload':{'draft_id':draft['id'],'details':draft['details']}}
    def execute(self,op,actor='rider-a1',authorization=None):
        return self.core.mutate(actor,op['operation_id'],op['idempotency_key'],op['kind'],op['payload'],authorization)['current']
    def create(self,actor='rider-a1',count=1):return self.execute(self.prepare('request',{**REQUEST,'passengers':count},actor),actor)
    def driver(self,kind,ride,actor='driver-a1'):
        op=secrets.token_hex(16)
        return self.core.mutate(actor,op,op,kind,{'ride_id':ride['id'],'version':ride['version'],'stopped':True})['current']
    def grant(self,operation=None,actor='rider-a1'):
        return self.grants.issue(actor,{'client_id':'client-test','scopes':['mobility:read']+(['mobility:execute'] if operation else []),'expires_in':300,'operation':operation})
    def authz(self,grant):return self.grants.resolve('Bearer '+grant['access_token'],grant['client_id'])[1]
    def denied(self,code,fn,*args,**kwargs):
        with self.assertRaises(DomainError) as error:fn(*args,**kwargs)
        self.assertEqual(error.exception.code,code)

class BusinessChangeTests(Fixture):
    def change(self,ride,count,**extra):return self.prepare('change',{'ride_id':ride['id'],**REQUEST,'passengers':count,**extra})
    def test_change_before_assignment_updates_route_and_audit(self):
        ride=self.create();operation=self.change(ride,2,destination_stop_id='stop-c')
        updated=self.execute(operation)
        self.assertEqual((updated['status'],updated['passengers'],updated['destination_stop_id']),('requested',2,'stop-c'))
        self.assertEqual(updated['version'],2)
        self.assertEqual(self.sql('SELECT kind FROM events ORDER BY version'),[('request',),('change',)])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM outbox'),[(2,)])
        self.assertEqual(self.execute(operation)['id'],ride['id'])
    def test_assigned_count_changes_reserve_and_release_seats(self):
        ride=self.driver('accept',self.create())
        ride=self.execute(self.change(ride,3))
        self.assertEqual(self.sql('SELECT reserved FROM runs'),[(3,)])
        ride=self.execute(self.change(ride,1))
        self.assertEqual(self.sql('SELECT reserved FROM runs'),[(1,)])
        self.denied('ROUTE_CHANGE_UNSUPPORTED',self.change,ride,1,destination_stop_id='stop-c')
    def test_two_increases_compete_for_last_seat_atomically(self):
        first=self.driver('accept',self.create())
        second=self.driver('accept',self.create('rider-a2'))
        a=self.change(first,2)
        b=self.prepare('change',{'ride_id':second['id'],**REQUEST,'passengers':2},'rider-a2')
        barrier=threading.Barrier(2)
        def run(op,actor):
            barrier.wait(3)
            try:self.execute(op,actor);return 'ok'
            except DomainError as error:return error.code
        with ThreadPoolExecutor(2) as pool:
            jobs=[pool.submit(run,a,'rider-a1'),pool.submit(run,b,'rider-a2')]
            self.assertCountEqual([x.result() for x in jobs],['ok','CAPACITY_FULL'])
        self.assertEqual(self.sql('SELECT reserved FROM runs'),[(3,)])
    def test_change_rechecks_price_eligibility_version_and_arrival(self):
        for changed,error in [('fare','TERMS_CHANGED'),('eligibility','INELIGIBLE'),('version','STALE_VERSION')]:
            with self.subTest(changed=changed):
                ride=self.create();op=self.change(ride,2)
                if changed=='fare':self.sql("UPDATE services SET revision=revision+1")
                elif changed=='eligibility':self.sql("UPDATE users SET eligible=0 WHERE id='rider-a1'")
                else:self.driver('accept',ride)
                self.denied(error,self.execute,op)
                self.sql("UPDATE users SET eligible=1 WHERE id='rider-a1'")
        ride=self.driver('arrive',self.driver('accept',self.create(),actor='driver-a2'),actor='driver-a2')
        self.denied('INVALID_STATE',self.change,ride,2)
    def test_change_rollback_includes_capacity_event_and_operation(self):
        ride=self.driver('accept',self.create());op=self.change(ride,2)
        self.sql("CREATE TRIGGER fail_change BEFORE INSERT ON outbox BEGIN SELECT RAISE(ABORT,'test outbox failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.execute(op)
        self.assertEqual(self.core.get_ride('rider-a1',ride['id'])['passengers'],1)
        self.assertEqual(self.sql('SELECT reserved FROM runs'),[(1,)])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM operations WHERE operation_id=?',(op['operation_id'],)),[(0,)])
    def test_migration_and_backup_revoke_delegation(self):
        from scripts.backup_local import backup
        ride=self.create();self.grant()
        target=Path(self.temp.name)/'copy.sqlite3';backup(self.path,target)
        copied=connect(target)
        try:self.assertEqual(copied.execute('SELECT COUNT(*) FROM client_grants').fetchone()[0],0)
        finally:copied.close()
        self.sql('DROP TABLE client_grants');self.sql("UPDATE meta SET value='1' WHERE key='schema_version'")
        initialize(self.path)
        self.assertEqual(self.sql("SELECT value FROM meta WHERE key='schema_version'"),[('8',)])
        self.assertEqual(self.core.get_ride('rider-a1',ride['id'])['id'],ride['id'])
    def test_pagination_filters_before_page_and_total(self):
        self.create('rider-a2');mine=[self.create()['id'] for _ in range(3)]
        page=self.core.list_rides('rider-a1',1,1)
        self.assertEqual((page['total'],len(page['rides'])),(3,1))
        self.assertIn(page['rides'][0]['id'],mine)
        self.assertEqual(self.core.list_rides('rider-b1')['total'],0)
        self.denied('INVALID_PAGINATION',self.core.list_rides,'rider-a1',True,1)

class DelegationTests(Fixture):
    def test_single_approval_shared_with_web_and_direct_replay(self):
        operation=self.prepare('request',REQUEST);grant=self.grant(operation);context=self.authz(grant)
        first=self.execute(operation)
        replay=self.execute(operation,authorization=context)
        self.assertEqual(first,replay)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'),[(1,)])
        changed=copy.deepcopy(operation);changed['operation_id']='different-operation'
        self.denied('APPROVAL_MISMATCH',self.execute,changed,authorization=context)
    def test_revoke_is_checked_again_in_core_transaction(self):
        op=self.prepare('request',REQUEST);grant=self.grant(op);context=self.authz(grant)
        self.grants.revoke('rider-a1',grant['grant_id'])
        self.denied('INVALID_GRANT',self.execute,op,authorization=context)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'),[(0,)])
    def test_expiry_audience_client_and_scope_are_enforced(self):
        op=self.prepare('request',REQUEST);grant=self.grant();context=self.authz(grant)
        self.denied('INSUFFICIENT_SCOPE',self.execute,op,authorization=context)
        self.denied('GRANT_TARGET_MISMATCH',self.grants.resolve,'Bearer '+grant['access_token'],'another-client')
        self.sql("UPDATE client_grants SET audience='wrong-service'")
        self.denied('GRANT_TARGET_MISMATCH',self.authz,grant)
        self.sql("UPDATE client_grants SET audience='yoko-local-mobility',expires_at=0")
        self.denied('INVALID_GRANT',self.authz,grant)
    def test_confirmation_cannot_be_claimed_or_changed_by_client(self):
        op=self.prepare('request',REQUEST)
        self.denied('INVALID_CONFIRMATION',self.grant,op,'rider-a2')
        altered=copy.deepcopy(op);altered['payload']['details']['passengers']=2
        self.denied('CONFIRMATION_CHANGED',self.grant,altered)
        for invalid in ([],{},None):
            self.denied('INVALID_APPROVAL',self.grant,{**op,'kind':invalid})
        op['payload']={'confirmed':True}
        self.denied('INVALID_INPUT',self.grant,op)
    def test_inactive_user_revokes_existing_grant_and_no_raw_token_in_db(self):
        grant=self.grant();context=self.authz(grant)
        self.assertNotIn(grant['access_token'],self.path.read_bytes().decode(errors='ignore'))
        self.sql("UPDATE users SET active=0 WHERE id='rider-a1'")
        self.denied('INVALID_GRANT',self.grants.resolve,'Bearer '+grant['access_token'],'client-test')
        self.denied('UNAUTHENTICATED',self.core.list_rides,'rider-a1',authorization=context)

class ClientHTTPTests(Fixture):
    def setUp(self):
        super().setUp()
        self.start();self.addCleanup(self.stop)
    def start(self):
        self.server=LocalServer(('127.0.0.1',0),self.path,enable_mlit=True)
        self.port=self.server.server_address[1];self.contract=self.server.mlit.contract
        self.thread=threading.Thread(target=lambda:self.server.serve_forever(poll_interval=.01),daemon=True);self.thread.start()
    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join(2)
    def request(self,path,method='GET',body=None,grant=None,session=None,headers=None):
        conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5);h={}
        if grant:h.update({'Authorization':'Bearer '+grant['access_token'],'X-Client-ID':grant['client_id']})
        if session:h.update({'Cookie':session[0],'X-CSRF-Token':session[1],'X-Requested-With':'YokoLocal'})
        if body is not None:h['Content-Type']='application/json'
        h.update(headers or {})
        conn.request(method,path,json.dumps(body) if body is not None else None,h)
        response=conn.getresponse();code=response.status;data=json.loads(response.read());conn.close()
        matched=self.contract.match(method,path.split('?')[0])
        if matched:self.contract.response(matched,code,data)
        return code,data
    def login(self,actor='rider-a1'):
        token,data=self.server.auth.login(actor,'local-test-only');return 'yoko_session='+token,data['csrf']
    def client_write(self,operation,grant):
        return self.request('/direct/v1/actions/'+operation['kind'],'POST',{k:v for k,v in operation.items() if k!='kind'},grant)
    def standard_body(self,ride,status='cancelled'):
        data=reservation(ride)
        return {**{k:data[k] for k in ['passenger_id','service_id','pickup','dropoff','passenger_count','accessibility_feature_count']},'status':status}
    def update_headers(self,op):return {'X-Operation-ID':op['operation_id'],'Idempotency-Key':op['idempotency_key']}
    def test_http_owner_authorizes_then_client_executes_without_llm(self):
        session=self.login()
        code,draft=self.request('/api/drafts/request','POST',REQUEST,session=session);self.assertEqual(code,200)
        op=secrets.token_hex(16);operation={'kind':'request','operation_id':op,'idempotency_key':op,'payload':{'draft_id':draft['id'],'details':draft['details']}}
        code,grant=self.request('/api/client-grants','POST',{'client_id':'test-direct-client','scopes':['mobility:read','mobility:execute'],'expires_in':300,'operation':operation},session=session)
        self.assertEqual(code,200)
        code,result=self.client_write(operation,grant);self.assertEqual(code,200,result)
        self.assertEqual(result['current']['status'],'requested')
        self.assertEqual(self.core.get_ride('admin-a1',result['current']['id'])['id'],result['current']['id'])
        self.assertEqual(self.request('/api/drafts/request','POST',REQUEST,grant=grant)[0],403)
        self.assertEqual(self.request('/direct/v1/rides',session=session)[0],401)
        self.assertEqual(self.request('/direct/v1/rides',grant=grant)[1]['total'],1)
    def test_mdl_contract_validates_actual_grant_action_and_page(self):
        from openapi_schema_validator import OAS31Validator
        from scripts.export_local_openapi import build
        spec=build();operation=self.prepare('request',REQUEST)
        data={'client_id':'contract-client','scopes':['mobility:read','mobility:execute'],'expires_in':300,'operation':operation}
        code,grant=self.request('/api/client-grants','POST',data,session=self.login())
        self.assertEqual(code,200)
        responses=[('/api/client-grants','post',grant)]
        code,result=self.client_write(operation,grant);self.assertEqual(code,200)
        responses.append(('/direct/v1/actions/request','post',result))
        responses.append(('/direct/v1/rides','get',self.request('/direct/v1/rides',grant=grant)[1]))
        for path,method,value in responses:
            escaped=path.replace('~','~0').replace('/','~1')
            pointer=f'#/paths/{escaped}/{method}/responses/200/content/application~1json/schema'
            OAS31Validator({**spec,'$ref':pointer},format_checker=OAS31Validator.FORMAT_CHECKER).validate(value)
    def test_actual_lost_response_reconciles_after_server_restart(self):
        operation=self.prepare('request',REQUEST);grant=self.grant(operation)
        body=json.dumps({k:v for k,v in operation.items() if k!='kind'}).encode()
        wire=(f"POST /direct/v1/actions/request HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\nAuthorization: Bearer {grant['access_token']}\r\nX-Client-ID: {grant['client_id']}\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n").encode()+body
        sock=socket.create_connection(('127.0.0.1',self.port));sock.sendall(wire);sock.shutdown(socket.SHUT_WR);sock.close()
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            code,result=self.request('/direct/v1/operations/'+operation['operation_id'],grant=grant)
            if code==200:break
            time.sleep(.01)
        self.assertEqual(code,200,result)
        self.stop();self.start()
        code,replay=self.client_write(operation,grant)
        self.assertEqual(code,200,replay);self.assertTrue(replay['replayed'])
        self.assertEqual(result['current']['id'],replay['current']['id'])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'),[(1,)])
    def test_standard_list_maps_every_state_without_inventing_coordinates(self):
        ride=self.create();grant=self.grant()
        for action,state in [(None,'tentative'),('accept','confirmed'),('arrive','confirmed'),('board','in_transit'),('complete','completed')]:
            if action:ride=self.driver(action,ride)
            code,result=self.request('/passengers/rider-a1/reservations',grant=grant)
            self.assertEqual(code,200,result);item=result['reservations'][0]
            self.assertEqual(item['status'],state)
            self.assertNotIn('datetime',item['pickup']);self.assertNotIn('location',item['pickup'])
            self.assertEqual(item['fare']['total'],0)
    def test_standard_change_cancel_and_cross_protocol_replay(self):
        ride=self.driver('accept',self.create())
        ride=self.core.get_ride('rider-a1',ride['id'])
        operation=self.prepare('change',{'ride_id':ride['id'],**REQUEST,'passengers':2});grant=self.grant(operation)
        body=self.standard_body({**ride,'passengers':2},'confirmed')
        code,result=self.request('/reservations/'+ride['id'],'PUT',body,grant,headers=self.update_headers(operation))
        self.assertEqual(code,200,result);self.assertEqual(result['passenger_count'][0]['count'],2)
        self.assertTrue(self.client_write(operation,grant)[1]['replayed'])
        ride=self.core.get_ride('rider-a1',ride['id'])
        operation=self.prepare('cancel',{'ride_id':ride['id']});grant=self.grant(operation)
        body=self.standard_body(ride)
        code,result=self.request('/reservations/'+ride['id'],'PUT',body,grant,headers=self.update_headers(operation))
        self.assertEqual((code,result['status']),(200,'cancelled'))
        self.assertEqual(self.request('/reservations/'+ride['id'],'PUT',body,grant,headers=self.update_headers(operation))[1],result)
        self.assertTrue(self.client_write(operation,grant)[1]['replayed'])
        self.assertEqual(self.sql('SELECT reserved FROM runs'),[(0,)])
    def test_standard_cannot_change_approval_target_fields_or_promote_status(self):
        ride=self.create();other=self.create('rider-a2')
        op=self.prepare('cancel',{'ride_id':ride['id']});grant=self.grant(op);body=self.standard_body(ride)
        for altered in [{**body,'status':'confirmed'},{**body,'passenger_id':'rider-a2'},{**body,'confirmed':True},{**body,'passenger_count':[{'passenger_type_id':PASSENGER_TYPE,'count':2}]}]:
            code,result=self.request('/reservations/'+ride['id'],'PUT',altered,grant,headers=self.update_headers(op))
            self.assertEqual(code,403,result)
        self.assertEqual(self.request('/reservations/'+other['id'],'PUT',body,grant,headers=self.update_headers(op))[0],403)
        self.assertEqual(self.request('/reservations/'+ride['id'],'PUT',body,grant)[0],403)
        self.assertEqual(self.core.get_ride('rider-a1',ride['id'])['status'],'requested')
    def test_standard_authorization_pagination_filters_and_invalid_inputs(self):
        for _ in range(3):self.create()
        self.create('rider-a2');grant=self.grant()
        code,page=self.request('/passengers/rider-a1/reservations?limit=1&offset=1&status=tentative',grant=grant)
        self.assertEqual((code,page['total'],len(page['reservations'])),(200,3,1))
        self.assertEqual(self.request('/passengers/rider-a2/reservations',grant=grant)[0],403)
        self.assertEqual(self.request('/passengers/rider-a1/reservations?status=no_show',grant=grant)[1]['total'],0)
        for query in ['limit=0','limit=101','offset=-1','status=assigned','limit=2&limit=3','tenant_id=test-b','pickup_date_from=garbage']:
            self.assertEqual(self.request('/passengers/rider-a1/reservations?'+query,grant=grant)[0],400,query)
        code,problem=self.request('/passengers/rider-a1/reservations?pickup_date_from=2026-09-19',grant=grant)
        self.assertEqual((code,problem['title']),(500,'PICKUP_TIME_NOT_ACQUIRED'))
        self.assertEqual(self.request('/passengers/driver-a1/reservations',grant=self.grant(actor='driver-a1'))[0],403)
    def test_all_19_operations_require_auth_and_remaining_operations_fail_explicitly(self):
        self.assertEqual(len(self.contract.operations),19)
        self.assertEqual(set(BLOCKERS)|SUPPORTED,{op['operationId'] for _,_,_,op in self.contract.operations})
        candidate={'service_ids':['service-a'],'preferred_time':{'type':'pickup','datetime':'2026-09-19T10:00:00+09:00'},'pickup':{'type':'fixed_stop','stop_id':'stop-a'},'dropoff':{'type':'fixed_stop','stop_id':'stop-b'},'passenger_count':[{'passenger_type_id':PASSENGER_TYPE,'count':1}],'accessibility_feature_count':[]}
        registration={'passenger_id':'rider-a1','candidate_id':'nonexistent-candidate','service_id':'service-a',**{k:candidate[k] for k in ['passenger_count','accessibility_feature_count']}}
        for field in ['pickup','dropoff']:registration[field]={**candidate[field],'location':{'type':'Point','coordinates':[0,0]},'datetime':'2026-09-19T10:00:00+09:00'}
        bodies={'postPassengers':{},'putPassengersId':{},'postPassengersIdAgreements':{'agreements':[{'terms_id':'synthetic-terms','agreed_at':'2026-09-19T00:00:00Z'}]},'postReservationsCandidates':candidate,'postReservations':registration,'putReservationsIdPayment':{'amount':0,'payment_status':'uncollected'}}
        grant=self.grant()
        for method,template,_,op in self.contract.operations:
            with self.subTest(operation=op['operationId']):
                path=template.replace('{id}','rider-a1')
                self.assertEqual(self.request(path,method)[0],401)
                if op['operationId'] in SUPPORTED:continue
                code,result=self.request(path,method,bodies.get(op['operationId']),grant)
                self.assertEqual((code,result['title']),(500,BLOCKERS[op['operationId']]))
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'),[(0,)])
    def test_standard_request_and_response_validate_against_unchanged_source(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),SOURCE_SHA256)
        matched=self.contract.match('GET','/passengers/rider-a1/reservations')
        self.denied('RESPONSE_CONTRACT_ERROR',self.contract.response,matched,200,{'reservations':[]})
        malformed=self.standard_body(self.create());malformed['passenger_count'][0]['count']=True
        code,result=self.request('/reservations/unused','PUT',malformed,self.grant())
        self.assertEqual((code,result['title']),(400,'SCHEMA_INVALID'))
    def test_client_cannot_read_other_owner_or_execute_after_expiry(self):
        mine=self.create();other=self.create('rider-a2');op=self.prepare('cancel',{'ride_id':mine['id']});grant=self.grant(op)
        self.assertEqual(self.request('/direct/v1/rides/'+other['id'],grant=grant)[0],404)
        self.sql('UPDATE client_grants SET expires_at=0')
        self.assertEqual(self.client_write(op,grant)[0],401)
        self.assertEqual(self.core.get_ride('rider-a1',mine['id'])['status'],'requested')
    def test_standard_guard_and_errors_keep_source_contract(self):
        grant=self.grant()
        code,result=self.request('/services',grant=grant,headers={'Origin':'https://evil.example'})
        self.assertEqual((code,result['title']),(403,'ORIGIN_REJECTED'))
        code,result=self.request('/services?unknown=1',grant=grant)
        self.assertEqual((code,result['title']),(400,'INVALID_QUERY'))
