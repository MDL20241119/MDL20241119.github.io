import copy
import json
import secrets
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from app.core import Core,DomainError
from app.db import ROOT,initialize
from tests.test_p3 import Fixture,REQUEST
from tests import test_catalog as catalog

FIXTURE=json.loads((ROOT/'fixtures/synthetic-payment.json').read_text())

class PaymentFixture(Fixture):
    def setUp(self):
        super().setUp();self.now=self.core.clock();self.core.clock=lambda:self.now
        self.sql("UPDATE services SET fare_json=? WHERE id='service-a'",(json.dumps(FIXTURE['fare']),))
    def ride(self,actor='rider-a1'):
        ride=self.driver('accept',self.create(actor));return self.core.get_ride(actor,ride['id'])
    def payment(self,ride,status='uncollected',amount=820,actor='admin-a1'):
        return self.prepare('payment_update',{'ride_id':ride['id'],'amount':amount,'payment_status':status},actor)
    def record(self,ride,status='uncollected',amount=820):return self.execute(self.payment(ride,status,amount),'admin-a1')['value']
    def read(self,ride,actor='rider-a1'):return self.core.payments.read(actor,ride['id'])
    def cancel(self,ride):return self.execute(self.prepare('cancel',{'ride_id':ride['id']}))

class PaymentTests(PaymentFixture):
    def test_missing_payment_is_not_zero_or_uncollected(self):
        ride=self.ride();self.denied('PAYMENT_NOT_RECORDED',self.read,ride)
        self.assertIsNone(ride['payment']['record']);self.assertEqual(ride['payment']['expected_amount'],820)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM payments'),[(0,)])
    def test_admin_records_one_ledger_and_preserves_creation_time(self):
        ride=self.ride();first=self.record(ride);self.now+=1;second=self.record(ride,'received')
        self.assertEqual(first['record']['id'],ride['id']);self.assertEqual(second['record']['version'],2)
        self.assertEqual(first['record']['created_at'],second['record']['created_at'])
        self.assertNotEqual(first['record']['updated_at'],second['record']['updated_at'])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM payments'),[(1,)])
        self.assertEqual(self.read(ride),second)
        self.assertEqual(self.core.snapshot('admin-a1')['rides'][0]['payment'],second)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM catalog_events WHERE kind='payment_update'"),[(2,)])
    def test_rider_driver_and_foreign_admin_cannot_write_or_read_across_boundary(self):
        ride=self.ride();self.record(ride)
        for actor in ['rider-a1','driver-a1','rider-a2']:self.denied('FORBIDDEN',self.payment,ride,actor=actor)
        for actor in ['rider-a2','rider-b1']:self.denied('NOT_FOUND',self.read,ride,actor)
        self.denied('FORBIDDEN',self.read,ride,'driver-a1')
        self.assertNotIn('payment',self.core.snapshot('driver-a1')['rides'][0])
        self.sql("UPDATE users SET role='admin' WHERE id='rider-b1'")
        self.denied('NOT_FOUND',self.payment,ride,actor='rider-b1')
    def test_amount_type_bounds_and_arbitrary_status_or_fields_are_rejected(self):
        ride=self.ride()
        for value in [-1,True,1.2,'820',2147483648,None]:self.denied('INVALID_PAYMENT_AMOUNT',self.payment,ride,amount=value)
        for status in [None,[],{},'refunded']:self.denied('INVALID_PAYMENT_STATUS',self.payment,ride,status)
        self.denied('INVALID_INPUT',self.prepare,'payment_update',{'ride_id':ride['id'],'amount':820,'payment_status':'received','confirmed':True},'admin-a1')
        self.assertEqual(self.sql('SELECT COUNT(*) FROM payments'),[(0,)])
    def test_unconfirmed_unknown_fare_and_inconsistent_amount_are_not_recorded(self):
        ride=self.create();self.denied('PAYMENT_RESERVATION_NOT_CONFIRMED',self.payment,ride)
        ride=self.driver('accept',ride)
        self.denied('PAYMENT_AMOUNT_MISMATCH',self.payment,ride,amount=0)
        self.denied('PAYMENT_EXCLUSION_UNSUPPORTED',self.payment,ride,'excluded',0)
        self.denied('PAYMENT_STATUS_MISMATCH',self.payment,ride,'cancelled',0)
        self.sql('UPDATE rides SET fare_json=? WHERE id=?',(json.dumps({'amount':None,'currency':'JPY'}),ride['id']))
        self.denied('FARE_NOT_CONFIGURED',self.payment,ride)
    def test_explicit_zero_fare_can_be_excluded_without_inventing_payment(self):
        self.sql("UPDATE services SET fare_json=?",(json.dumps({**FIXTURE['fare'],'amount':0}),))
        ride=self.ride();self.assertIsNone(ride['payment']['record'])
        value=self.record(ride,'excluded',0);self.assertEqual(value['record']['payment_status'],'excluded')
        self.assertFalse(value['review_required'])
    def test_integer_upper_boundary_is_saved_exactly(self):
        self.sql("UPDATE services SET fare_json=?",(json.dumps({**FIXTURE['fare'],'amount':2147483647}),))
        ride=self.ride();value=self.record(ride,amount=2147483647)
        self.assertEqual(value['record']['amount'],2147483647)
    def test_same_operation_race_and_new_content_conflict_do_not_duplicate_record(self):
        ride=self.ride();op=self.payment(ride);barrier=threading.Barrier(2)
        def run():barrier.wait(3);return self.execute(op,'admin-a1')
        with ThreadPoolExecutor(2) as pool:
            jobs=[pool.submit(run) for _ in range(2)];self.assertEqual(jobs[0].result(),jobs[1].result())
        self.assertEqual(self.sql('SELECT version FROM payments'),[(1,)])
        altered=copy.deepcopy(op);altered['payload']['details']['input']['payment_status']='received'
        self.denied('IDEMPOTENCY_CONFLICT',self.execute,altered,'admin-a1')
        self.assertEqual(self.sql("SELECT COUNT(*) FROM catalog_operations WHERE kind='payment_update'"),[(1,)])
    def test_two_approved_updates_compete_for_one_version(self):
        ride=self.ride();ops=[self.payment(ride),self.payment(ride,'received')];barrier=threading.Barrier(2)
        def run(op):
            barrier.wait(3)
            try:self.execute(op,'admin-a1');return 'ok'
            except DomainError as e:return e.code
        with ThreadPoolExecutor(2) as pool:
            results=[pool.submit(run,op) for op in ops];values=[r.result() for r in results]
        self.assertEqual(values.count('ok'),1)
        self.assertIn(next(v for v in values if v!='ok'),('STALE_PAYMENT','PAYMENT_SETTLEMENT_REVIEW_REQUIRED'))
        self.assertEqual(self.sql('SELECT version FROM payments'),[(1,)])
    def test_reservation_change_after_approval_requires_new_confirmation(self):
        ride=self.ride();op=self.payment(ride)
        self.execute(self.prepare('change',{'ride_id':ride['id'],**REQUEST,'passengers':2}))
        self.denied('STALE_PAYMENT',self.execute,op,'admin-a1')
        self.assertEqual(self.sql('SELECT COUNT(*) FROM payments'),[(0,)])
    def test_cancellation_after_approval_cannot_record_received(self):
        ride=self.ride();op=self.payment(ride,'received');self.cancel(ride)
        self.denied('PAYMENT_STATUS_MISMATCH',self.execute,op,'admin-a1')
        self.assertEqual(self.sql('SELECT COUNT(*) FROM payments'),[(0,)])
    def test_uncollected_cancel_preserves_ledger_until_admin_confirms_zero_cancel_fee(self):
        ride=self.ride();self.record(ride);cancelled=self.cancel(ride)
        self.assertEqual(cancelled['payment']['record']['amount'],820)
        self.assertEqual(cancelled['payment']['review_reason'],'cancellation_update_required')
        result=self.record(ride,'cancelled',0)
        self.assertFalse(result['review_required']);self.assertEqual(result['record']['amount'],0)
        self.assertEqual(self.sql('SELECT reserved FROM runs'),[(0,)])
    def test_received_cancel_preserves_money_and_never_claims_refund(self):
        ride=self.ride();first=self.record(ride,'received');self.cancel(ride)
        current=self.read(ride);self.assertEqual(current['record'],first['record'])
        self.assertEqual(current['review_reason'],'refund_review_required')
        for status in ['cancelled','excluded','uncollected']:self.denied('PAYMENT_SETTLEMENT_REVIEW_REQUIRED',self.payment,ride,status,0)
        self.assertEqual(self.sql('SELECT amount,payment_status FROM payments'),[(820,'received')])
    def test_payment_and_cancel_race_always_preserves_truthful_record(self):
        ride=self.ride();pay=self.payment(ride,'received');cancel=self.prepare('cancel',{'ride_id':ride['id']});barrier=threading.Barrier(2)
        def run(op,actor):
            barrier.wait(3)
            try:self.execute(op,actor);return 'ok'
            except DomainError as e:return e.code
        with ThreadPoolExecutor(2) as pool:
            a=pool.submit(run,pay,'admin-a1');b=pool.submit(run,cancel,'rider-a1');paid,cancelled=a.result(),b.result()
        self.assertEqual(cancelled,'ok');view=self.core.get_ride('rider-a1',ride['id'])
        self.assertEqual(view['status'],'cancelled');self.assertEqual(self.sql('SELECT reserved FROM runs'),[(0,)])
        if paid=='ok':self.assertEqual(view['payment']['review_reason'],'refund_review_required')
        else:self.assertEqual(paid,'PAYMENT_STATUS_MISMATCH');self.assertIsNone(view['payment']['record'])
    def test_price_change_after_received_is_blocked_but_equal_price_count_change_works(self):
        ride=self.ride();self.record(ride,'received')
        change={'ride_id':ride['id'],**REQUEST,'passengers':2}
        self.execute(self.prepare('change',change));self.assertEqual(self.sql('SELECT reserved FROM runs'),[(2,)])
        self.sql("UPDATE services SET fare_json=? WHERE id='service-a'",(json.dumps({**FIXTURE['fare'],'amount':1000}),))
        self.denied('PAYMENT_SETTLEMENT_REVIEW_REQUIRED',self.prepare,'change',change)
        self.assertEqual(self.read(ride)['record']['amount'],820)
    def test_uncollected_price_change_requires_explicit_ledger_update(self):
        ride=self.ride();self.record(ride)
        self.sql("UPDATE services SET fare_json=? WHERE id='service-a'",(json.dumps({**FIXTURE['fare'],'amount':1000}),))
        self.execute(self.prepare('change',{'ride_id':ride['id'],**REQUEST,'passengers':2}))
        self.assertEqual(self.read(ride)['review_reason'],'fare_update_required')
        self.assertFalse(self.record(ride,amount=1000)['review_required'])
    def test_outbox_failure_rolls_back_payment_receipt_and_confirmation(self):
        ride=self.ride();op=self.payment(ride)
        self.sql("CREATE TRIGGER fail_payment BEFORE INSERT ON catalog_outbox BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.execute(op,'admin-a1')
        self.assertEqual(self.sql('SELECT COUNT(*) FROM payments'),[(0,)])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM catalog_operations'),[(0,)])
        self.assertEqual(self.sql('SELECT consumed FROM drafts WHERE id=?',(op['payload']['draft_id'],)),[(0,)])
        self.sql('DROP TRIGGER fail_payment');self.execute(op,'admin-a1')
    def test_grant_expiry_revocation_and_role_loss_are_checked_in_transaction(self):
        ride=self.ride();op=self.payment(ride);grant=self.grant(op,'admin-a1');context=self.authz(grant)
        self.grants.revoke('admin-a1',grant['grant_id']);self.denied('INVALID_GRANT',self.execute,op,'admin-a1',authorization=context)
        grant=self.grant(op,'admin-a1');context=self.authz(grant);self.now+=301
        self.denied('INVALID_GRANT',self.execute,op,'admin-a1',authorization=context)
        self.denied('CONFIRMATION_EXPIRED',self.execute,op,'admin-a1')
        op=self.payment(ride);self.sql("UPDATE users SET role='driver' WHERE id='admin-a1'")
        self.denied('FORBIDDEN',self.execute,op,'admin-a1')
    def test_original_receipt_and_current_record_remain_distinct_after_update_cancel_restart(self):
        ride=self.ride();op=self.payment(ride);first=self.execute(op,'admin-a1');self.record(ride,'received');self.cancel(ride)
        restarted=Core(self.path,clock=self.core.clock);result=restarted.operation('admin-a1',op['operation_id'])
        self.assertEqual(result['result'],first);self.assertEqual(result['current']['value']['record']['payment_status'],'received')
        self.assertEqual(result['current']['value']['review_reason'],'refund_review_required')
    def test_profile_deletion_retains_minimal_payment_history_and_operations(self):
        self.execute(self.prepare('profile_create',{'first_name':'試験','last_name':'架空'}))
        ride=self.ride();op=self.payment(ride,'received');self.execute(op,'admin-a1')
        for kind in ['arrive','board','complete']:ride=self.driver(kind,ride)
        self.execute(self.prepare('profile_delete',{}))
        self.assertEqual(self.sql('SELECT COUNT(*) FROM passengers'),[(0,)])
        self.assertEqual(self.read(ride)['record']['amount'],820)
        self.assertEqual(self.core.operation('admin-a1',op['operation_id'])['current']['resource_type'],'payment')
    def test_schema_four_migration_preserves_ride_without_fabricating_payments(self):
        ride=self.ride();grant=self.grant();self.sql('DROP TABLE payments')
        self.sql("UPDATE meta SET value='4' WHERE key='schema_version'");initialize(self.path)
        self.assertEqual(self.sql("SELECT value FROM meta WHERE key='schema_version'"),[('8',)])
        self.assertEqual(self.core.get_ride('rider-a1',ride['id'],self.authz(grant))['status'],'assigned')
        self.assertEqual(self.sql('SELECT COUNT(*) FROM payments'),[(0,)])
        self.assertEqual(self.record(ride)['record']['amount'],820)

class PaymentHTTPTests(PaymentFixture):
    start=catalog.CatalogHTTPTests.start;stop=catalog.CatalogHTTPTests.stop;request=catalog.CatalogHTTPTests.request
    login=catalog.CatalogHTTPTests.login;client_write=catalog.CatalogHTTPTests.client_write;update_headers=catalog.CatalogHTTPTests.update_headers
    def setUp(self):
        super().setUp();self.start();self.server.core.clock=self.core.clock;self.addCleanup(self.stop)
    def payment_path(self,ride):return '/reservations/'+ride['id']+'/payment'
    def write(self,ride,status='uncollected',amount=820):
        op=self.payment(ride,status,amount);grant=self.grant(op,'admin-a1')
        code,result=self.request(self.payment_path(ride),'PUT',{'amount':amount,'payment_status':status},grant,headers=self.update_headers(op))
        self.assertEqual(code,200,result);return result,op,grant
    def test_standard_get_put_and_mdl_read_use_persisted_data_and_original_replay(self):
        ride=self.ride();read=self.grant();self.assertEqual(self.request(self.payment_path(ride),grant=read)[0],404)
        session=self.login('admin-a1');data={'ride_id':ride['id'],'amount':820,'payment_status':'uncollected'}
        code,draft=self.request('/api/drafts/payment_update','POST',data,session=session);self.assertEqual(code,200,draft)
        key=secrets.token_hex(16);op={'kind':'payment_update','operation_id':key,'idempotency_key':key,'payload':{'draft_id':draft['id'],'details':draft['details']}}
        code,grant=self.request('/api/client-grants','POST',{'client_id':'payment-http','scopes':['mobility:read','mobility:execute'],'expires_in':300,'operation':op},session=session);self.assertEqual(code,200,grant)
        body={k:data[k] for k in ('amount','payment_status')}
        code,first=self.request(self.payment_path(ride),'PUT',body,grant,headers=self.update_headers(op));self.assertEqual(code,200,first)
        self.assertEqual(first['id'],ride['id']);self.assertNotIn('version',first)
        self.assertEqual(self.request(self.payment_path(ride),grant=read),(200,first))
        self.assertEqual(self.request('/direct/v1/payments/'+ride['id'],grant=read)[1]['record']['amount'],820)
        self.assertEqual(self.request('/api/payments/'+ride['id'],session=self.login())[1]['record']['payment_status'],'uncollected')
        self.write(ride,'received');self.cancel(ride)
        self.assertEqual(self.request(self.payment_path(ride),'PUT',body,grant,headers=self.update_headers(op)),(200,first))
        code,replay=self.client_write(op,grant);self.assertEqual(code,200,replay);self.assertTrue(replay['replayed'])
        self.assertEqual(replay['current']['value']['review_reason'],'refund_review_required')
        self.assertEqual(self.request(self.payment_path(ride),grant=read)[1]['payment_status'],'received')
    def test_standard_requires_exact_admin_approval_path_and_body(self):
        ride=self.ride();other=self.ride('rider-a2');op=self.payment(ride);grant=self.grant(op,'admin-a1')
        body={'amount':820,'payment_status':'uncollected'}
        self.assertEqual(self.request(self.payment_path(ride),'PUT',body,self.grant(actor='admin-a1'),headers=self.update_headers(op))[0],403)
        self.assertEqual(self.request(self.payment_path(other),'PUT',body,grant,headers=self.update_headers(op))[0],403)
        self.assertEqual(self.request(self.payment_path(other),'PUT',{**body,'ride_id':ride['id']},grant,headers=self.update_headers(op))[0],400)
        self.assertEqual(self.request(self.payment_path(ride),'PUT',{**body,'payment_status':'received'},grant,headers=self.update_headers(op))[0],403)
        self.assertEqual(self.request(self.payment_path(ride),'PUT',body,grant,headers={})[0],403)
        self.assertEqual(self.request('/api/drafts/payment_update','POST',{'ride_id':ride['id'],**body},session=self.login())[0],403)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM payments'),[(0,)])
    def test_standard_read_denies_other_rider_driver_and_foreign_tenant(self):
        ride=self.ride();self.record(ride)
        for actor,expected in [('rider-a2',404),('rider-b1',404),('driver-a1',403)]:
            self.assertEqual(self.request(self.payment_path(ride),grant=self.grant(actor=actor))[0],expected)
        self.assertEqual(self.request(self.payment_path(ride),grant=self.grant(actor='admin-a1'))[0],200)
    def test_invalid_types_extra_fields_and_get_query_use_declared_problem_responses(self):
        ride=self.ride();op=self.payment(ride);grant=self.grant(op,'admin-a1');base={'amount':820,'payment_status':'uncollected'}
        for body in [{**base,'amount':True},{**base,'amount':-1},{**base,'amount':2147483648},{**base,'payment_status':'refunded'},{**base,'card_number':'synthetic-extra-field'}]:
            self.assertEqual(self.request(self.payment_path(ride),'PUT',body,grant,headers=self.update_headers(op))[0],400)
        code,problem=self.request(self.payment_path(ride)+'?unknown=1',grant=grant)
        self.assertEqual((code,problem['title']),(500,'INVALID_QUERY'))
        self.assertEqual(self.sql('SELECT COUNT(*) FROM payments'),[(0,)])
    def test_standard_cancelled_and_excluded_success_states(self):
        ride=self.ride();self.write(ride);self.cancel(ride)
        result,op,grant=self.write(ride,'cancelled',0);self.assertEqual(result['amount'],0)
        self.assertEqual(self.client_write(op,grant)[1]['current']['value']['record']['payment_status'],'cancelled')
        self.sql("UPDATE services SET fare_json=?",(json.dumps({**FIXTURE['fare'],'amount':0}),))
        free=self.ride();result,_,_=self.write(free,'excluded',0)
        self.assertEqual(result['payment_status'],'excluded')
    def test_real_lost_put_response_reconciles_after_restart_with_one_ledger_update(self):
        import socket,time
        ride=self.ride();op=self.payment(ride,'received');grant=self.grant(op,'admin-a1');body=json.dumps({'amount':820,'payment_status':'received'}).encode()
        wire=(f"PUT {self.payment_path(ride)} HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\nAuthorization: Bearer {grant['access_token']}\r\nX-Client-ID: {grant['client_id']}\r\nX-Operation-ID: {op['operation_id']}\r\nIdempotency-Key: {op['idempotency_key']}\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n").encode()+body
        sock=socket.create_connection(('127.0.0.1',self.port));sock.sendall(wire);sock.shutdown(socket.SHUT_WR);sock.close()
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            code,receipt=self.request('/direct/v1/operations/'+op['operation_id'],grant=grant)
            if code==200:break
            time.sleep(.01)
        self.assertEqual(code,200,receipt);self.stop();self.start();self.server.core.clock=self.core.clock
        code,result=self.client_write(op,grant);self.assertEqual(code,200,result);self.assertTrue(result['replayed'])
        self.assertEqual(self.sql('SELECT amount,version FROM payments'),[(820,1)])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM catalog_operations WHERE kind='payment_update'"),[(1,)])
