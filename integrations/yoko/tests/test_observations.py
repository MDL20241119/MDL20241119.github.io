import copy
import json
import secrets
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode
from app.core import Core,DomainError,iso
from app.db import ROOT,initialize
from tests.test_p3 import Fixture
from tests import test_catalog as catalog

FIXTURE=json.loads((ROOT/'fixtures/synthetic-observations.json').read_text())

class ObservationFixture(Fixture):
    def setUp(self):
        super().setUp();self.now=self.core.clock();self.core.clock=lambda:self.now
        self.ride=self.driver('accept',self.create())
        self.run=self.sql('SELECT run_id FROM rides WHERE id=?',(self.ride['id'],))[0][0]
    def configure(self,**kw):return self.execute(self.prepare('observation_configure',{**FIXTURE['source'],**kw},'admin-a1'),'admin-a1')
    def report(self,**kw):return {'id':'test-delay-1','status':'active','delay_minutes':5,'delay_reason':'traffic','started_at':iso(self.now-20),'closed_at':None,'closed_reason':None,'effective_end':iso(self.now+200),**kw}
    def data(self,**kw):return {'vehicle_id':'vehicle-a1','run_id':self.run,'source_id':FIXTURE['source']['source_id'],'observed_at':iso(self.now),'location':copy.deepcopy(FIXTURE['location']),'delays':[],**kw}
    def publish(self,**kw):return self.execute(self.prepare('observation_publish',self.data(**kw),'admin-a1'),'admin-a1')['value']
    def read(self,kind='locations',actor='rider-a1',standard=False,**params):return self.core.observations.read(actor,kind,params,standard=standard)
    def cancel(self):return self.execute(self.prepare('cancel',{'ride_id':self.ride['id']}))

class ObservationTests(ObservationFixture):
    def test_unconfigured_missing_and_explicit_empty_are_distinct(self):
        self.assertEqual(self.read()['observations'][0]['location_status'],'not_configured')
        self.denied('VEHICLE_OBSERVATIONS_NOT_ACQUIRED',self.read,standard=True)
        self.configure();self.assertEqual(self.read()['observations'][0]['location_status'],'not_acquired')
        self.publish(location=None,delays=None)
        self.denied('DELAY_OBSERVATIONS_NOT_ACQUIRED',self.read,'delays',standard=True)
        self.now+=1;self.publish()
        self.assertEqual(self.read('delays',standard=True)['operation_delays'],[])
        self.assertEqual(self.read('delays')['observations'][0]['delay_assessment'],'no_active_delay_reported')
    def test_shared_persistent_position_timestamp_and_unknown_delay_minutes(self):
        self.configure();self.publish(delays=[self.report(delay_minutes=None)])
        for who in ['rider-a1','driver-a1','admin-a1']:
            value=self.read(actor=who,standard=True,vehicle_ids=['vehicle-a1'])['vehicle_locations'][0]
            self.assertEqual(value['location'],FIXTURE['location']);self.assertEqual(value['timestamp'],iso(self.now))
        delay=self.read('delays',standard=True)['operation_delays'][0];self.assertNotIn('delay_minutes',delay)
        restarted=Core(self.path,clock=self.core.clock);self.assertEqual(restarted.get_ride('rider-a1',self.ride['id'])['vehicle_location'],FIXTURE['location'])
        self.assertIsNone(restarted.get_ride('rider-a1',self.ride['id'])['eta'])
    def test_freshness_is_independent_and_exact_boundary_expires(self):
        self.configure();self.publish()
        self.now+=60
        self.assertEqual(self.read()['observations'][0]['location_status'],'stale');self.assertEqual(self.read()['vehicle_locations'],[])
        self.assertEqual(self.read('delays',standard=True)['total'],0)
        self.now+=240
        self.assertEqual(self.read('delays')['observations'][0]['delay_status'],'stale')
        self.denied('DELAY_OBSERVATIONS_NOT_ACQUIRED',self.read,'delays',standard=True)
    def test_submicrosecond_clock_roundtrip_does_not_reject_present_observation(self):
        self.now=int(self.now)+0.1234567
        self.configure();self.publish()
        self.assertEqual(self.read(standard=True)['vehicle_locations'][0]['timestamp'],iso(self.now))
        self.now+=60;self.assertEqual(self.read()['observations'][0]['location_status'],'stale')
    def test_incident_expiry_is_not_resolution_or_no_delay(self):
        self.configure();r=self.report(effective_end=iso(self.now+5));self.publish(delays=[r]);self.now+=5
        self.assertEqual(self.read('delays')['observations'][0]['delay_status'],'expired')
        self.assertEqual(self.read('delays')['observations'][0]['delay_assessment'],'unknown')
        self.assertEqual(self.read('delays')['operation_delays'],[])
        self.denied('UNRESOLVED_DELAY_OMITTED',self.publish)
        self.assertEqual(self.sql("SELECT json_extract(data_json,'$.status') FROM observation_delays"),[('active',)])
    def test_missing_snapshot_preserves_incident_and_cannot_clear_it(self):
        self.configure();r=self.report();self.publish(delays=[r]);self.now+=1;self.publish(location=None,delays=None)
        self.assertEqual(self.read('delays')['observations'][0]['delay_status'],'not_acquired')
        self.now+=1;self.denied('UNRESOLVED_DELAY_OMITTED',self.publish)
        self.publish(delays=[{**r,'status':'resolved','closed_at':iso(self.now),'closed_reason':'resolved'}])
        self.assertEqual(self.read('delays',standard=True)['total'],0)
        self.assertEqual(self.read('delays',standard=True,status=['resolved'])['total'],1)
    def test_resolved_incident_identity_cannot_be_reopened_or_retimed(self):
        self.configure();r=self.report();self.publish(delays=[r]);self.now+=1
        closed={**r,'status':'resolved','closed_at':iso(self.now),'closed_reason':'resolved'};self.publish(delays=[closed]);self.now+=1
        self.denied('DELAY_STATE_CONFLICT',self.publish,delays=[r])
        self.denied('DELAY_STATE_CONFLICT',self.publish,delays=[{**closed,'started_at':iso(self.now-1)}])
        self.publish();self.assertEqual(self.read('delays',standard=True,status=['resolved'])['total'],1)
    def test_rider_and_driver_cannot_import_or_change_sources(self):
        for who in ['rider-a1','driver-a1','driver-a2','rider-b1']:
            self.denied('FORBIDDEN',self.prepare,'observation_configure',FIXTURE['source'],who)
        self.configure()
        for who in ['rider-a1','driver-a1']:self.denied('FORBIDDEN',self.prepare,'observation_publish',self.data(),who)
    def test_other_owner_driver_and_tenant_have_no_coordinates_or_vehicle_existence(self):
        self.configure();self.publish()
        for who in ['rider-a2','driver-a2','rider-b1']:
            self.denied('FORBIDDEN',self.read,actor=who,vehicle_ids=['vehicle-a1'])
            self.assertNotIn('139.70012',json.dumps(self.core.snapshot(who)))
        self.denied('FORBIDDEN',self.read,vehicle_ids=['vehicle-a1'],service_ids=['service-b'])
        self.sql("UPDATE users SET role='admin' WHERE id='rider-b1'")
        self.denied('FORBIDDEN',self.prepare,'observation_configure',FIXTURE['source'],'rider-b1')
    def test_cancel_revokes_location_access_even_with_existing_read_grant(self):
        self.configure();self.publish();grant=self.grant();context=self.authz(grant);self.cancel()
        self.denied('FORBIDDEN',self.core.observations.read,'rider-a1','locations',{'vehicle_ids':['vehicle-a1']},context)
        view=self.core.get_ride('rider-a1',self.ride['id']);self.assertIsNone(view['observation']);self.assertIsNone(view['vehicle_location'])
        self.assertEqual(self.read()['availability'],'no_authorized_vehicles')
    def test_new_run_does_not_inherit_old_coordinates_or_incidents(self):
        self.configure();self.publish(delays=[self.report()]);self.cancel()
        ride=self.driver('accept',self.create());new_run=self.sql('SELECT run_id FROM rides WHERE id=?',(ride['id'],))[0][0]
        self.assertNotEqual(self.run,new_run);self.assertEqual(ride['observation']['location_status'],'not_acquired')
        self.now+=1;self.denied('RUN_MISMATCH',self.publish)
        self.run=new_run;self.publish();self.assertEqual(self.read('delays',standard=True)['total'],0)
    def test_source_disable_change_and_vehicle_stop_hide_values(self):
        self.configure();self.publish();self.configure(enabled=False)
        self.assertEqual(self.read()['observations'][0]['location_status'],'stopped');self.now+=1
        self.denied('OBSERVATION_STOPPED',self.publish);self.configure()
        self.assertEqual(self.read()['observations'][0]['location_status'],'source_changed')
        self.publish();self.sql("UPDATE vehicles SET active=0 WHERE id='vehicle-a1'")
        self.assertEqual(self.read()['vehicle_locations'],[])
    def test_source_and_run_rechecked_after_confirmation(self):
        self.configure();op=self.prepare('observation_publish',self.data(),'admin-a1');self.configure(label='変更した架空の取得元')
        self.denied('STALE_CATALOG',self.execute,op,'admin-a1')
        op=self.prepare('observation_publish',self.data(),'admin-a1');self.cancel()
        self.denied('RUN_MISMATCH',self.execute,op,'admin-a1')
    def test_coordinates_invalid_types_bounds_extra_fields_and_future_time(self):
        self.configure()
        for point in [{'type':'Point','coordinates':[181,35]},{'type':'Point','coordinates':[139,91]},{'type':'Point','coordinates':[True,35]},{'type':'Point','coordinates':[float('nan'),35]},{'type':'Point','coordinates':[35,139]}]:
            self.denied('INVALID_COORDINATES',self.publish,location=point)
        self.denied('INVALID_INPUT',self.publish,location={**FIXTURE['location'],'rider_id':'not-allowed'})
        self.denied('FUTURE_OBSERVATION',self.publish,observed_at=iso(self.now+1))
        self.denied('INVALID_DATETIME',self.publish,observed_at='2026-09-19T12:00:00')
        self.denied('SOURCE_MISMATCH',self.publish,source_id='untrusted')
        self.denied('INVALID_INPUT',self.prepare,'observation_publish',{**self.data(),'url':'https://example.invalid'},'admin-a1')
    def test_invalid_delay_state_periods_counts_and_free_text_are_rejected(self):
        self.configure()
        for amount in [True,-1,1.5,'5',2147483648]:self.denied('INVALID_DELAY_MINUTES',self.publish,delays=[self.report(delay_minutes=amount)])
        for changes in [{'status':'unknown'},{'delay_reason':'unknown'},{'closed_at':iso(self.now)},{'status':'resolved','closed_reason':'bogus','closed_at':iso(self.now)}]:
            self.denied('INVALID_DELAYS',self.publish,delays=[self.report(**changes)])
        for changes in [{'started_at':iso(self.now+1)},{'effective_end':iso(self.now)}]:self.denied('INVALID_OBSERVATION_PERIOD',self.publish,delays=[self.report(**changes)])
        self.denied('INVALID_DELAYS',self.publish,delays=[self.report(),self.report()])
        self.denied('INVALID_INPUT',self.publish,delays=[self.report(delay_reason_detail='private text')])
    def test_old_and_equal_timestamps_cannot_overwrite_new_snapshot(self):
        self.configure();self.publish();self.now+=1;self.publish(location=None)
        for at in [self.now,self.now-1]:self.denied('OUT_OF_ORDER_OBSERVATION',self.publish,observed_at=iso(at))
        self.assertEqual(self.sql('SELECT version FROM observation_snapshots'),[(2,)])
    def test_same_operation_race_and_payload_conflict(self):
        self.configure();op=self.prepare('observation_publish',self.data(),'admin-a1');barrier=threading.Barrier(2)
        def run():barrier.wait(3);return self.execute(op,'admin-a1')
        with ThreadPoolExecutor(2) as pool:
            jobs=[pool.submit(run) for _ in range(2)];self.assertEqual(jobs[0].result(),jobs[1].result())
        self.assertEqual(self.sql('SELECT version FROM observation_snapshots'),[(1,)])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM catalog_events WHERE kind='observation_publish'"),[(1,)])
        bad=copy.deepcopy(op);bad['payload']['details']['input']['location']=None
        self.denied('IDEMPOTENCY_CONFLICT',self.execute,bad,'admin-a1')
    def test_competing_different_approvals_cannot_overwrite_unseen_update(self):
        self.configure();ops=[self.prepare('observation_publish',self.data(location=point),'admin-a1') for point in [None,FIXTURE['location']]];barrier=threading.Barrier(2)
        def run(op):
            barrier.wait(3)
            try:self.execute(op,'admin-a1');return 'ok'
            except DomainError as e:return e.code
        with ThreadPoolExecutor(2) as pool:
            jobs=[pool.submit(run,op) for op in ops];results=[j.result() for j in jobs]
        self.assertCountEqual(results,['ok','OUT_OF_ORDER_OBSERVATION'])
        self.assertEqual(self.sql('SELECT version FROM observation_snapshots'),[(1,)])
    def test_outbox_failure_rolls_back_position_delays_and_consumed_approval(self):
        self.configure();op=self.prepare('observation_publish',self.data(delays=[self.report()]),'admin-a1')
        self.sql("CREATE TRIGGER fail_observation BEFORE INSERT ON catalog_outbox BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):self.execute(op,'admin-a1')
        self.assertEqual(self.sql('SELECT COUNT(*) FROM observation_snapshots'),[(0,)]);self.assertEqual(self.sql('SELECT COUNT(*) FROM observation_delays'),[(0,)])
        self.assertEqual(self.sql('SELECT consumed FROM drafts WHERE id=?',(op['payload']['draft_id'],)),[(0,)])
        self.sql('DROP TRIGGER fail_observation');self.execute(op,'admin-a1')
    def test_expired_revoked_grants_and_role_loss(self):
        self.configure();op=self.prepare('observation_publish',self.data(),'admin-a1');g=self.grant(op,'admin-a1');ctx=self.authz(g)
        self.grants.revoke('admin-a1',g['grant_id']);self.denied('INVALID_GRANT',self.execute,op,'admin-a1',authorization=ctx)
        g=self.grant(op,'admin-a1');ctx=self.authz(g);self.now+=301;self.denied('INVALID_GRANT',self.execute,op,'admin-a1',authorization=ctx)
        self.denied('CONFIRMATION_EXPIRED',self.execute,op,'admin-a1')
        op=self.prepare('observation_publish',self.data(),'admin-a1');self.sql("UPDATE users SET role='driver' WHERE id='admin-a1'")
        self.denied('FORBIDDEN',self.execute,op,'admin-a1')
    def test_first_receipt_is_historical_and_current_expires_after_restart(self):
        self.configure();op=self.prepare('observation_publish',self.data(),'admin-a1');first=self.execute(op,'admin-a1');self.now+=61
        c=Core(self.path,clock=self.core.clock);result=c.operation('admin-a1',op['operation_id'])
        self.assertEqual(result['result'],first);self.assertEqual(result['current']['value']['location_status'],'stale')
        self.assertIsNone(result['current']['value']['location'])
    def test_schema_five_migrates_without_auto_loading_observations(self):
        self.sql('DROP TABLE observation_delays');self.sql('DROP TABLE observation_snapshots');self.sql('DROP TABLE observation_sources')
        self.sql("UPDATE meta SET value='5' WHERE key='schema_version'");initialize(self.path)
        self.assertEqual(self.sql("SELECT value FROM meta WHERE key='schema_version'"),[('8',)])
        self.assertEqual(self.core.get_ride('rider-a1',self.ride['id'])['status'],'assigned')
        self.assertEqual(self.sql('SELECT COUNT(*) FROM observation_sources'),[(0,)])
    def test_explicit_demo_loader_preserves_an_existing_db_and_uses_core_audit(self):
        from scripts.configure_observation_demo import create
        path=self.path.parent/'demo.sqlite3';create(path);core=Core(path)
        snap=core.snapshot('rider-a1');self.assertEqual(snap['rides'][0]['observation']['delay_assessment'],'delayed')
        with core.db() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM catalog_events WHERE kind='observation_publish'").fetchone()[0],1)
        with self.assertRaises(ValueError):create(path)
        self.assertEqual(core.snapshot('rider-a1')['rides'][0]['id'],snap['rides'][0]['id'])
    def test_filters_pagination_and_default_day_are_applied_before_total(self):
        self.configure();a=self.report(id='delay-a');b=self.report(id='delay-b',started_at=iso(self.now-90000));self.publish(delays=[a,b])
        self.assertEqual(self.read('delays',standard=True)['total'],1)
        all_params={'started_at_from':iso(self.now-100000),'status':['active','resolved']}
        page=self.read('delays',standard=True,offset=1,limit=1,**all_params)
        self.assertEqual(page['total'],2);self.assertEqual(page['operation_delays'][0]['id'],'delay-b')
        self.assertEqual(self.read('delays',standard=True,started_at_from=iso(self.now-20),started_at_to=iso(self.now-20))['total'],1)
        self.assertNotIn('delays',self.read('delays',**all_params)['observations'][0])
        self.denied('INVALID_QUERY',self.read,'delays',started_at_to=iso(self.now))
        self.denied('INVALID_QUERY',self.read,'delays',started_at_from=iso(self.now),started_at_to=iso(self.now-1))
    def test_partial_fleet_coverage_does_not_return_false_complete_standard_page(self):
        self.configure();self.publish()
        self.denied('VEHICLE_OBSERVATIONS_NOT_ACQUIRED',self.read,actor='admin-a1',standard=True)
        self.assertEqual(self.read(actor='admin-a1')['availability'],'incomplete')
        self.assertEqual(self.read(actor='admin-a1',standard=True,vehicle_ids=['vehicle-a1'],service_ids=['service-a'])['total'],1)

class ObservationHTTPTests(ObservationFixture):
    start=catalog.CatalogHTTPTests.start;stop=catalog.CatalogHTTPTests.stop;request=catalog.CatalogHTTPTests.request
    login=catalog.CatalogHTTPTests.login;client_write=catalog.CatalogHTTPTests.client_write;update_headers=catalog.CatalogHTTPTests.update_headers
    def setUp(self):
        super().setUp();self.start();self.server.core.clock=self.core.clock;self.addCleanup(self.stop)
    def approved_http(self,kind,data):
        session=self.login('admin-a1');code,draft=self.request('/api/drafts/'+kind,'POST',data,session=session);self.assertEqual(code,200,draft)
        key=secrets.token_hex(16);op={'kind':kind,'operation_id':key,'idempotency_key':key,'payload':{'draft_id':draft['id'],'details':draft['details']}}
        code,g=self.request('/api/client-grants','POST',{'client_id':'observation-http','scopes':['mobility:read','mobility:execute'],'expires_in':300,'operation':op},session=session);self.assertEqual(code,200,g)
        code,result=self.client_write(op,g);self.assertEqual(code,200,result);return op,g,result
    def test_both_standard_operations_and_mdl_views_use_saved_approved_observations(self):
        self.approved_http('observation_configure',FIXTURE['source']);self.approved_http('observation_publish',self.data(delays=[self.report()]))
        grant=self.grant()
        for path,key in [('/vehicle-locations','vehicle_locations'),('/operation-delays','operation_delays')]:
            status,data=self.request(path,grant=grant);self.assertEqual(status,200,data);self.assertEqual(data['total'],1)
            status,direct=self.request('/direct/v1'+path,grant=grant);self.assertEqual(status,200,direct);self.assertEqual(direct[key],data[key]);self.assertEqual(direct['basis'],'synthetic_test_only')
        code,snapshot=self.request('/api/snapshot',session=self.login());self.assertEqual(code,200,snapshot);self.assertEqual(snapshot['rides'][0]['observation']['delay_assessment'],'delayed')
    def test_query_validation_unknown_types_and_explicit_cross_tenant_denial(self):
        self.configure();self.publish(delays=[self.report()]);g=self.grant()
        for query in ['limit=0','offset=-1','limit=true','vehicle_ids=','vehicle_ids=a&vehicle_ids=b','fake=1']:
            for prefix in ['', '/direct/v1']:
                self.assertEqual(self.request(prefix+'/vehicle-locations?'+query,grant=g)[0],400,query)
        for query in ['status=other','started_at_to=2026-01-01T00%3A00%3A00Z','started_at_from=bad']:
            self.assertEqual(self.request('/operation-delays?'+query,grant=g)[0],400,query)
        self.assertEqual(self.request('/vehicle-locations?vehicle_ids=vehicle-a1&service_ids=service-b',grant=g)[0],403)
    def test_standard_missing_stale_and_expired_data_do_not_become_empty_success(self):
        g=self.grant();self.assertEqual(self.request('/vehicle-locations',grant=g)[0],500)
        self.configure();self.publish(delays=[self.report(effective_end=iso(self.now+2))]);self.now+=2
        self.assertEqual(self.request('/operation-delays',grant=g)[0],500)
        self.assertEqual(self.request('/direct/v1/operation-delays',grant=g)[1]['observations'][0]['delay_status'],'expired')
        self.now+=60;self.assertEqual(self.request('/vehicle-locations',grant=g)[0],500)
        self.assertEqual(self.request('/direct/v1/vehicle-locations',grant=g)[1]['vehicle_locations'],[])
    def test_filter_defaults_bounds_and_paging_validate_original_contract(self):
        self.configure();self.publish(delays=[self.report(id='delay-a'),self.report(id='delay-b')]);g=self.grant()
        for prefix in ['', '/direct/v1']:
            code,data=self.request(prefix+'/operation-delays?vehicle_ids=vehicle-a1&service_ids=service-a&status=active,resolved&offset=1&limit=1',grant=g)
            self.assertEqual(code,200,data);self.assertEqual(data['total'],2);self.assertEqual(data['operation_delays'][0]['id'],'delay-b')
        query=urlencode({'started_at_from':iso(self.now-20),'started_at_to':iso(self.now-20)})
        self.assertEqual(self.request('/operation-delays?'+query,grant=g)[1]['total'],2)
    def test_read_grants_do_not_allow_import_and_approvals_bind_source_run_and_values(self):
        self.configure();op=self.prepare('observation_publish',self.data(),'admin-a1');g=self.grant(op,'admin-a1')
        self.assertEqual(self.client_write(op,self.grant(actor='admin-a1'))[0],403)
        wrong=copy.deepcopy(op);wrong['payload']['details']['input']['location']=None
        self.assertEqual(self.client_write(wrong,g)[0],403)
        self.assertEqual(self.client_write(op,g)[0],200)
        self.grants.revoke('admin-a1',g['grant_id']);self.assertEqual(self.client_write(op,g)[0],401)
    def test_cancel_and_role_change_revoke_reads_over_http(self):
        self.configure();self.publish();g=self.grant();self.cancel()
        self.assertEqual(self.request('/vehicle-locations?vehicle_ids=vehicle-a1',grant=g)[0],403)
        for who in ['rider-a2','rider-b1','driver-a2']:
            self.assertEqual(self.request('/operation-delays?vehicle_ids=vehicle-a1',grant=self.grant(actor=who))[0],403)
    def test_response_loss_restart_and_replay_do_not_duplicate_observation(self):
        import http.client
        self.configure();op=self.prepare('observation_publish',self.data(delays=[self.report()]),'admin-a1');g=self.grant(op,'admin-a1')
        body={k:op[k] for k in ['operation_id','idempotency_key','payload']}
        conn=http.client.HTTPConnection('127.0.0.1',self.port);conn.request('POST','/direct/v1/actions/observation_publish',json.dumps(body),{'Content-Type':'application/json','Authorization':'Bearer '+g['access_token'],'X-Client-ID':g['client_id']})
        response=conn.getresponse();self.assertEqual(response.status,200);response.close();conn.close()
        self.stop();self.start();self.server.core.clock=self.core.clock
        code,result=self.request('/direct/v1/operations/'+op['operation_id'],grant=g);self.assertEqual(code,200,result)
        code,replay=self.client_write(op,g);self.assertEqual(code,200,replay);self.assertTrue(replay['replayed'])
        self.assertEqual(self.sql('SELECT version FROM observation_snapshots'),[(1,)]);self.assertEqual(self.sql('SELECT COUNT(*) FROM observation_delays'),[(1,)])
