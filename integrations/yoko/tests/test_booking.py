import copy
import json
import secrets
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo
from app.core import Core,DomainError,iso
from app.db import ROOT,initialize
from app.mlit import reservation_request,reservation,PASSENGER_TYPE
from tests.test_p3 import Fixture
from tests import test_catalog as catalog

CONFIG=json.loads((ROOT/'fixtures/synthetic-catalog.json').read_text())
ROUTE=json.loads((ROOT/'fixtures/synthetic-booking.json').read_text())['routes'][0]

class BookingFixture(Fixture):
    def setUp(self):
        super().setUp();self.now=self.core.clock();self.core.clock=lambda:self.now
        self.command('service_configure',copy.deepcopy(CONFIG['service']),'admin-a1')
        for stop in CONFIG['stops']:self.command('stop_configure',copy.deepcopy(stop),'admin-a1')
        for actor in ['rider-a1','rider-a2']:self.command('profile_create',copy.deepcopy(CONFIG['profile']),actor)
    def command(self,kind,data,actor='rider-a1'):return self.execute(self.prepare(kind,data,actor),actor)
    def route(self):return self.command('route_configure',copy.deepcopy(ROUTE),'admin-a1')
    def offer(self,actor='driver-a1',**changes):
        return self.command('offer_open',{'service_id':'service-a','origin_stop_id':'stop-a','destination_stop_id':'stop-b','pickup_at':iso(self.now+600),'vehicle_name':'架空試験車両','stopped':True,**changes},actor)['value']
    def search_body(self,**changes):return {'service_id':'service-a','origin_stop_id':'stop-a','destination_stop_id':'stop-b','passengers':1,'preferred_pickup_at':iso(self.now),'vehicle_id':None,**changes}
    def search(self,actor='rider-a1',**changes):return self.core.booking.search(actor,self.search_body(**changes))
    def candidate(self,actor='rider-a1',**changes):return self.search(actor,**changes)['candidates'][0]
    def ready(self):self.route();return self.offer()
    def booking(self,candidate=None,actor='rider-a1'):
        return self.prepare('book',{'candidate_id':(candidate or self.candidate(actor))['id']},actor)

class BookingTests(BookingFixture):
    def test_unknown_configuration_no_plan_and_no_seat_are_distinct(self):
        self.denied('ROUTE_TIMING_NOT_CONFIGURED',self.search)
        self.route();self.assertEqual(self.search()['no_candidate_reason'],'no_operation_plans')
        self.offer();self.execute(self.booking(self.candidate(passengers=3)))
        result=self.search();self.assertEqual((result['no_candidate_reason'],result['availability_reason']),('no_candidate','capacity_full'))
    def test_search_does_not_reserve_or_create_rides_and_uses_driver_plan(self):
        offer=self.ready();a=self.candidate();b=self.candidate()
        self.assertNotEqual(a['id'],b['id']);self.assertEqual(a['pickup_at'],offer['pickup_at'])
        self.assertEqual(a['dropoff_at'],iso(self.now+1200));self.assertEqual(a['expires_at'],iso(self.now+120))
        self.assertEqual(self.sql('SELECT reserved FROM runs'),[(0,)])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'),[(0,)])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(0,)])
    def test_missing_coordinates_and_fare_do_not_become_empty_results_or_zero_fare(self):
        self.route();self.sql("DELETE FROM stop_profiles WHERE stop_id='stop-a'")
        self.denied('STOP_COORDINATES_NOT_CONFIGURED',self.search)
        self.command('stop_configure',copy.deepcopy(CONFIG['stops'][0]),'admin-a1')
        self.sql("UPDATE services SET fare_json=? WHERE id='service-a'",(json.dumps({'amount':None,'currency':'JPY'}),))
        self.denied('FARE_NOT_CONFIGURED',self.search)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM candidates'),[(0,)])
    def test_schema_three_migration_keeps_profiles_consent_rides_and_grants(self):
        term=self.command('terms_publish',copy.deepcopy(CONFIG['terms']),'admin-a1')['value']
        self.command('agreements_register',{'agreements':[{'terms_id':term['id'],'agreed_at':iso(self.now)}]})
        ride=self.create();grant=self.grant();profile=self.core.catalog.read('rider-a1','passenger','rider-a1')
        for table in ['ride_bookings','candidates','run_offers','route_policies']:self.sql('DROP TABLE '+table)
        self.sql("UPDATE meta SET value='3' WHERE key='schema_version'")
        initialize(self.path)
        self.assertEqual(self.sql("SELECT value FROM meta WHERE key='schema_version'"),[('8',)])
        self.assertEqual(self.core.get_ride('rider-a1',ride['id'],self.authz(grant))['status'],'requested')
        self.assertEqual(self.core.catalog.read('rider-a1','passenger','rider-a1'),profile)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM agreements'),[(1,)])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM route_policies'),[(0,)])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM candidates'),[(0,)])
        self.ready();self.assertEqual(self.execute(self.booking())['status'],'assigned')
    def test_driver_offer_requires_role_stop_and_free_vehicle(self):
        self.route();self.denied('STOP_REQUIRED',self.offer,stopped=False)
        self.denied('FORBIDDEN',self.offer,'rider-a1')
        self.denied('INVALID_PICKUP_TIME',self.offer,pickup_at=iso(self.now-1))
        self.denied('INVALID_PICKUP_TIME',self.offer,pickup_at=iso(self.now+7201))
        self.offer();self.denied('VEHICLE_BUSY',self.offer)
    def test_malformed_search_identifiers_are_rejected_before_database_binding(self):
        self.ready()
        for field in ('service_id','origin_stop_id','destination_stop_id','vehicle_id'):
            for value in ([],{},42):self.denied('INVALID_TEXT',self.search,**{field:value})
        self.denied('INVALID_PASSENGERS',self.search,passengers=True)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM candidates'),[(0,)])
    def test_book_is_assigned_and_shared_with_driver_then_completes(self):
        self.ready();c=self.candidate();ride=self.execute(self.booking(c))
        self.assertEqual((ride['status'],ride['reservation_status'],ride['assignment_status']),('assigned','confirmed','assigned'))
        self.assertIsNone(ride['eta']);self.assertIsNone(ride['vehicle_location'])
        self.assertEqual(ride['booking']['pickup_location'],CONFIG['stops'][0]['location'])
        self.assertEqual(self.core.snapshot('admin-a1')['counts']['assigned'],1)
        for action in ['arrive','board','complete']:ride=self.driver(action,ride)
        self.assertEqual(ride['status'],'completed');self.assertEqual(self.sql('SELECT reserved,active FROM runs'),[(0,0)])
    def test_candidate_expiry_and_draft_expiry_are_server_enforced(self):
        self.ready();c=self.candidate();op=self.booking(c);self.now+=121
        self.denied('CANDIDATE_EXPIRED',self.booking,c)
        self.denied('CONFIRMATION_EXPIRED',self.execute,op)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'),[(0,)])
    def test_changed_fare_profile_and_qualification_invalidate_approval(self):
        self.ready();op=self.booking();self.sql("UPDATE users SET eligible=0 WHERE id='rider-a1'")
        self.denied('INELIGIBLE',self.execute,op);self.sql("UPDATE users SET eligible=1 WHERE id='rider-a1'")
        self.sql("UPDATE services SET fare_json=?",(json.dumps({'amount':100,'currency':'JPY','basis':'synthetic_test_only'}),))
        self.denied('CANDIDATE_CHANGED',self.execute,op)
        op=self.booking();self.command('profile_update',{'first_name':'変更','last_name':'架空'})
        self.denied('CANDIDATE_CHANGED',self.execute,op)
    def test_terms_and_route_updates_require_new_candidate_and_driver_offer(self):
        offer=self.ready();op=self.booking()
        self.command('terms_publish',copy.deepcopy(CONFIG['terms']),'admin-a1')
        self.denied('AGREEMENT_REQUIRED',self.execute,op)
        terms=self.core.catalog.read('rider-a1','terms')['terms']
        self.command('agreements_register',{'agreements':[{'terms_id':terms[0]['id'],'agreed_at':iso(self.now)}]})
        self.denied('CANDIDATE_CHANGED',self.execute,op)
        self.denied('OFFER_SETTINGS_CHANGED',self.search)
        self.command('offer_close',{'offer_id':offer['id'],'stopped':True},'driver-a1')
        self.offer();op=self.booking();self.command('route_configure',{**ROUTE,'travel_seconds':660},'admin-a1')
        self.denied('CANDIDATE_CHANGED',self.execute,op)
    def test_two_riders_cannot_book_the_last_seat(self):
        self.sql("UPDATE vehicles SET capacity=1 WHERE driver_id='driver-a1'");self.ready()
        ops=[(a,self.booking(actor=a)) for a in ['rider-a1','rider-a2']];barrier=threading.Barrier(2)
        def run(actor,op):
            barrier.wait(3)
            try:self.execute(op,actor);return 'ok'
            except DomainError as error:return error.code
        with ThreadPoolExecutor(2) as pool:
            jobs=[pool.submit(run,a,o) for a,o in ops];self.assertCountEqual([j.result() for j in jobs],['ok','CAPACITY_FULL'])
        self.assertEqual(self.sql('SELECT reserved FROM runs'),[(1,)])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'),[(1,)])
    def test_one_candidate_cannot_be_reused_with_new_key(self):
        self.ready();c=self.candidate();one=self.booking(c);two=self.booking(c);self.execute(one)
        self.denied('CANDIDATE_USED',self.execute,two)
        self.assertEqual(self.execute(one)['id'],self.core.operation('rider-a1',one['operation_id'])['current']['id'])
    def test_same_operation_race_and_historical_receipt(self):
        self.ready();op=self.booking();barrier=threading.Barrier(2)
        def run():barrier.wait(3);return self.execute(op)
        with ThreadPoolExecutor(2) as pool:
            jobs=[pool.submit(run) for _ in range(2)];results=[j.result() for j in jobs]
        self.assertEqual(results[0]['id'],results[1]['id']);self.assertEqual(self.sql('SELECT reserved FROM runs'),[(1,)])
        ride=results[0]
        for action in ['arrive','board','complete']:ride=self.driver(action,ride)
        receipt=self.core.operation('rider-a1',op['operation_id']);self.assertEqual((receipt['result']['status'],receipt['current']['status']),('assigned','completed'))
    def test_outbox_failure_rolls_back_seat_candidate_ride_and_draft(self):
        self.ready();op=self.booking()
        self.sql("CREATE TRIGGER fail_book BEFORE INSERT ON outbox BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.execute(op)
        self.assertEqual(self.sql('SELECT reserved FROM runs'),[(0,)])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'),[(0,)])
        self.assertEqual(self.sql('SELECT used_ride_id FROM candidates'),[(None,)])
        self.assertEqual(self.sql('SELECT consumed FROM drafts WHERE id=?',(op['payload']['draft_id'],)),[(0,)])
        self.sql('DROP TRIGGER fail_book');self.execute(op)
    def test_withdrawal_blocks_new_booking_but_preserves_booked_rider(self):
        offer=self.ready();one=self.booking();two=self.booking(actor='rider-a2');ride=self.execute(one)
        self.command('offer_close',{'offer_id':offer['id'],'stopped':True},'driver-a1')
        self.denied('OFFER_CLOSED',self.execute,two,'rider-a2')
        for action in ['arrive','board','complete']:ride=self.driver(action,ride)
        self.assertEqual(ride['status'],'completed')
    def test_booked_changes_and_cancel_use_same_capacity_and_preserve_times(self):
        self.ready();ride=self.execute(self.booking());before=ride['booking']
        ride=self.command('change',{'ride_id':ride['id'],'service_id':'service-a','origin_stop_id':'stop-a','destination_stop_id':'stop-b','passengers':3})
        self.assertEqual(ride['booking'],before);self.assertEqual(self.sql('SELECT reserved FROM runs'),[(3,)])
        op=self.prepare('cancel',{'ride_id':ride['id']});self.execute(op);self.execute(op)
        self.assertEqual(self.sql('SELECT reserved,active FROM runs'),[(0,0)])
    def test_no_cross_owner_candidate_or_offer_and_legacy_cannot_use_reserved_plan(self):
        offer=self.ready();c=self.candidate()
        self.denied('CANDIDATE_NOT_FOUND',self.booking,c,'rider-a2')
        self.denied('NOT_FOUND',self.prepare,'offer_close',{'offer_id':offer['id'],'stopped':True},'driver-a2')
        ride=self.create();self.denied('RUN_UNAVAILABLE',self.driver,'accept',ride)
        self.denied('NOT_FOUND',self.search,vehicle_id='foreign-vehicle')
        self.denied('FORBIDDEN',self.core.booking.search,'driver-a1',self.search_body())
    def test_overnight_plan_and_closing_hours_are_checked_for_whole_trip(self):
        self.now=datetime(2026,9,19,23,45,tzinfo=ZoneInfo('Asia/Tokyo')).timestamp();self.route()
        offer=self.offer(pickup_at=iso(self.now+600));self.assertEqual(offer['dropoff_at'],iso(self.now+1200))
        self.command('offer_close',{'offer_id':offer['id'],'stopped':True},'driver-a1')
        config=copy.deepcopy(CONFIG['service']);config['operating_hours']['sunday']=[]
        self.command('service_configure',config,'admin-a1')
        self.denied('SERVICE_CLOSED',self.offer,pickup_at=iso(self.now+600))
    def test_profile_delete_removes_unbooked_candidates_and_old_grant_cannot_execute(self):
        self.ready();op=self.booking();grant=self.grant(op);authorization=self.authz(grant)
        self.command('profile_delete',{})
        self.assertEqual(self.sql('SELECT COUNT(*) FROM candidates'),[(0,)])
        self.denied('INVALID_GRANT',self.execute,op,authorization=authorization)

class BookingHTTPTests(BookingFixture):
    start=catalog.CatalogHTTPTests.start;stop=catalog.CatalogHTTPTests.stop;request=catalog.CatalogHTTPTests.request
    login=catalog.CatalogHTTPTests.login;client_write=catalog.CatalogHTTPTests.client_write;update_headers=catalog.CatalogHTTPTests.update_headers
    def setUp(self):
        super().setUp();self.ready();self.start();self.server.core.clock=self.core.clock;self.addCleanup(self.stop)
    def query(self):
        return {'service_ids':['service-a'],'preferred_time':{'type':'pickup','datetime':iso(self.now)},'pickup':{'type':'fixed_stop','stop_id':'stop-a'},'dropoff':{'type':'fixed_stop','stop_id':'stop-b'},'passenger_count':[{'passenger_type_id':PASSENGER_TYPE,'count':1}],'accessibility_feature_count':[]}
    def test_standard_search_confirm_book_201_and_cross_protocol_replay(self):
        read=self.grant();code,result=self.request('/reservations/candidates','POST',self.query(),read);self.assertEqual(code,200,result)
        candidate=result['candidates'][0];body={'passenger_id':'rider-a1',**candidate['reservation_request']}
        code,draft=self.request('/api/drafts/book','POST',{'candidate_id':body['candidate_id']},session=self.login());self.assertEqual(code,200,draft)
        key=secrets.token_hex(16);op={'operation_id':key,'idempotency_key':key,'kind':'book','payload':{'draft_id':draft['id'],'details':draft['details']}}
        code,grant=self.request('/api/client-grants','POST',{'client_id':'test-booking','scopes':['mobility:read','mobility:execute'],'expires_in':300,'operation':op},session=self.login());self.assertEqual(code,200,grant)
        code,booked=self.request('/reservations','POST',body,grant,headers=self.update_headers(op));self.assertEqual(code,201,booked)
        self.assertEqual(booked['status'],'confirmed');self.assertEqual(booked['pickup']['datetime'],body['pickup']['datetime'])
        self.assertEqual(self.request('/reservations','POST',body,grant,headers=self.update_headers(op)),(201,booked))
        self.assertTrue(self.client_write(op,grant)[1]['replayed'])
        self.assertEqual(self.request('/passengers/rider-a1/reservations',grant=read)[1]['reservations'][0],booked)
    def test_standard_binding_and_read_only_grant_cannot_book(self):
        c=self.candidate();op=self.booking(c);grant=self.grant(op);body=reservation_request(c,'rider-a1')
        self.assertEqual(self.request('/reservations','POST',body,self.grant(),headers=self.update_headers(op))[0],403)
        variants=[{**body,'passenger_id':'rider-a2'},{**body,'vehicle_id':'vehicle-other'},{**body,'pickup':{**body['pickup'],'datetime':iso(self.now+700)}},{**body,'candidate_id':'candidate-other'},{**body,'confirmed':True}]
        for changed in variants:self.assertEqual(self.request('/reservations','POST',changed,grant,headers=self.update_headers(op))[0],403)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'),[(0,)])
    def test_standard_booked_count_change_and_cancel_preserve_plan_and_release_once(self):
        op=self.booking();ride=self.execute(op);original=ride['booking']
        change=self.prepare('change',{'ride_id':ride['id'],'service_id':'service-a','origin_stop_id':'stop-a','destination_stop_id':'stop-b','passengers':3})
        expected=reservation({**ride,**change['payload']['details']})
        fields=('passenger_id','service_id','pickup','dropoff','passenger_count','accessibility_feature_count','status')
        body={k:expected[k] for k in fields};grant=self.grant(change)
        code,result=self.request('/reservations/'+ride['id'],'PUT',body,grant,headers=self.update_headers(change))
        self.assertEqual(code,200,result);self.assertEqual(result['passenger_count'][0]['count'],3)
        self.assertEqual(result['pickup']['datetime'],original['pickup_at']);self.assertEqual(self.sql('SELECT reserved FROM runs'),[(3,)])
        self.assertEqual(self.request('/reservations/'+ride['id'],'PUT',body,grant,headers=self.update_headers(change)),(200,result))
        cancel=self.prepare('cancel',{'ride_id':ride['id']});grant=self.grant(cancel)
        body={**{k:result[k] for k in fields},'status':'cancelled'}
        for _ in range(2):
            code,cancelled=self.request('/reservations/'+ride['id'],'PUT',body,grant,headers=self.update_headers(cancel))
            self.assertEqual(code,200,cancelled);self.assertEqual(cancelled['status'],'cancelled')
            self.assertEqual(cancelled['dropoff']['datetime'],original['dropoff_at'])
        self.assertEqual(self.sql('SELECT reserved,active FROM runs'),[(0,0)])
    def test_direct_search_and_approval_expiry_and_revocation(self):
        grant=self.grant();code,result=self.request('/direct/v1/candidates','POST',self.search_body(),grant)
        self.assertEqual(code,200,result);op=self.booking(result['candidates'][0]);execution=self.grant(op)
        self.grants.revoke('rider-a1',execution['grant_id'])
        self.assertEqual(self.client_write(op,execution)[0],401)
        expiring=self.grant(op)
        self.now+=121
        self.assertEqual(self.request('/reservations','POST',reservation_request(op['payload']['details'],'rider-a1'),expiring,headers=self.update_headers(op))[0],401)
        self.denied('CONFIRMATION_EXPIRED',self.execute,op)
    def test_lost_booking_response_reconciles_after_restart_without_second_seat(self):
        import socket,time
        op=self.booking();grant=self.grant(op)
        body=json.dumps(reservation_request(op['payload']['details'],'rider-a1')).encode()
        wire=(f"POST /reservations HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\nAuthorization: Bearer {grant['access_token']}\r\nX-Client-ID: {grant['client_id']}\r\nX-Operation-ID: {op['operation_id']}\r\nIdempotency-Key: {op['idempotency_key']}\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\nConnection: close\r\n\r\n").encode()+body
        sock=socket.create_connection(('127.0.0.1',self.port));sock.sendall(wire);sock.shutdown(socket.SHUT_WR);sock.close()
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            code,receipt=self.request('/direct/v1/operations/'+op['operation_id'],grant=grant)
            if code==200:break
            time.sleep(.01)
        self.assertEqual(code,200,receipt)
        self.stop();self.start();self.server.core.clock=self.core.clock
        code,replayed=self.client_write(op,grant);self.assertEqual(code,200,replayed)
        self.assertTrue(replayed['replayed']);self.assertEqual(replayed['current']['id'],receipt['current']['id'])
        self.assertEqual(self.sql('SELECT reserved FROM runs'),[(1,)])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'),[(1,)])
    def test_unsupported_times_locations_and_counts_fail_explicitly(self):
        grant=self.grant();base=self.query()
        cases=[{**base,'preferred_time':{'type':'dropoff','datetime':iso(self.now)}},{**base,'preferred_time':{'type':'pickup','datetime':iso(self.now+3600)}},
            {**base,'service_ids':['service-a','another-service']},{**base,'pickup':{'type':'custom_location','location':CONFIG['stops'][0]['location']}},
            {**base,'accessibility_feature_count':[{'accessibility_feature_type':'wheelchair','count':1}]}]
        for body in cases:self.assertEqual(self.request('/reservations/candidates','POST',body,grant)[0],400)
