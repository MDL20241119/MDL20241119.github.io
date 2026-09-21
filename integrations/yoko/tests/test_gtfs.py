"""GTFS privacy/authorization denials, calendar business parity and bad-feed checks."""
import copy
import csv
import io
import json
import tempfile
import unittest
import zipfile
from datetime import datetime,timedelta
from pathlib import Path
from app.core import Core,DomainError,iso,packed
from app.db import ROOT
from app.gtfs import zip_bytes
from app.gtfs_validation import validate
from app.transport_data import gtfs_time_to_api
from scripts.demo_gtfs import setup
from scripts.export_gtfs import export
from scripts.validate_gtfs import summarize,verify_jar
from tests.test_p3 import Fixture

CONFIG=json.loads((ROOT/'fixtures/synthetic-gtfs.json').read_text())

def rows(files,name):return list(csv.DictReader(io.StringIO(files[name+'.txt'].decode())))

def replace_rows(files,name,items):
    result=copy.copy(files);fieldnames=list(rows(files,name)[0])
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fieldnames,lineterminator='\r\n')
    writer.writeheader();writer.writerows(items);result[name+'.txt']=stream.getvalue().encode();return result

class GtfsTests(Fixture):
    def setUp(self):
        super().setUp();self.core=Core(self.path,clock=lambda:datetime.fromisoformat('2026-09-19T12:00:00+09:00').timestamp())
        setup(self.core);self.config=copy.deepcopy(CONFIG)
        self.sql("UPDATE services SET fare_json=?",(packed({'amount':820,'currency':'JPY','basis':'synthetic_test_only'}),))
    def feed(self):return self.core.gtfs.export('admin-a1',self.config)
    def command(self,kind,data,actor='admin-a1'):return self.execute(self.prepare(kind,data,actor),actor)
    def profile(self):return json.loads(self.sql('SELECT data_json FROM service_profiles')[0][0])
    def test_fixed_stop_flex_fare_readings_and_coordinates(self):
        feed=self.feed();files=feed['files'];self.assertEqual(validate(feed['archive'])['errors'],[])
        self.assertEqual(rows(files,'stops')[0],{'stop_id':'synthetic-A','stop_name':'テスト乗降場所A','stop_lat':'35.500000','stop_lon':'139.500000','location_type':'0'})
        self.assertEqual(rows(files,'fare_attributes')[0]['price'],'820')
        self.assertEqual(rows(files,'booking_rules')[0]['booking_type'],'0')
        for r in rows(files,'stop_times'):
            self.assertNotIn('arrival_time',r);self.assertNotIn('departure_time',r);self.assertNotIn('location_id',r)
        self.assertNotIn('locations.geojson',files)
    def test_fully_deterministic_feed_and_public_ids_survive_restart(self):
        before=self.feed();after=Core(self.path).gtfs.export('admin-a1',self.config)
        self.assertEqual(before['archive'],after['archive'])
        self.assertEqual(before['report']['stop_mapping'],{'stop-a':'synthetic-A','stop-b':'synthetic-B'})
        with zipfile.ZipFile(io.BytesIO(before['archive'])) as z:
            self.assertIsNone(z.testzip());self.assertEqual(z.namelist(),sorted(z.namelist()))
    def test_holiday_override_and_overnight_service_day(self):
        files=self.feed()['files'];cal=rows(files,'calendar_dates')
        self.assertNotIn('20260923',{r['date'] for r in cal})
        self.assertNotIn('20270101',{r['date'] for r in cal})
        overnight={r['trip_id'] for r in rows(files,'stop_times') if r['end_pickup_drop_off_window']=='25:59:59'}
        self.assertEqual(len(overnight),2)
        for trip in rows(files,'trips'):
            if trip['trip_id'] in overnight:self.assertEqual([r['date'] for r in cal if r['service_id']==trip['service_id']],['20261231'])
        self.assertEqual(gtfs_time_to_api('20261231','25:59:59'),'2027-01-01T01:59:59+09:00')
        profile=self.profile();profile['special_operating_hours'].append({'date':'2026-09-23','time_slots':[{'start_time_offset_sec':10*3600,'end_time_offset_sec':12*3600}]})
        self.command('service_configure',profile)
        self.assertIn('20260923',{r['date'] for r in rows(self.feed()['files'],'calendar_dates')})
    def assert_window_parity(self):
        files=self.feed()['files'];trips=rows(files,'trips');times=rows(files,'stop_times');cal=rows(files,'calendar_dates')
        mapping={v['route_id']:v['route_policy_id'] for v in self.feed()['report']['route_mapping']}
        with self.core.db() as db:
            actor=self.core.actor(db,'admin-a1')
            for trip in trips:
                route=db.execute('SELECT * FROM route_policies WHERE id=?',(mapping[trip['route_id']],)).fetchone()
                context,service=self.core.booking.context(db,actor,dict(route))
                points=sorted([r for r in times if r['trip_id']==trip['trip_id']],key=lambda r:r['stop_sequence'])
                dates=[r['date'] for r in cal if r['service_id']==trip['service_id']]
                for date in (dates[0],dates[-1]):
                    for edge in ('start_pickup_drop_off_window','end_pickup_drop_off_window'):
                        pickup=datetime.fromisoformat(gtfs_time_to_api(date,points[0][edge])).timestamp()
                        dropoff=datetime.fromisoformat(gtfs_time_to_api(date,points[1][edge])).timestamp()
                        self.assertEqual(dropoff-pickup,600)
                        self.core.booking.interval(db,service,context,pickup,dropoff)
    def test_exported_window_edges_are_accepted_by_planned_ride_core(self):
        self.assert_window_parity()
    def test_adjacent_day_windows_and_fractional_end_remain_inside_core(self):
        profile=self.profile();profile['operating_hours']={k:[{'start_time_offset_sec':0,'end_time_offset_sec':86400}] for k in profile['operating_hours']};profile['holiday_dates']=[];profile['special_operating_hours']=[]
        profile['end_datetime']='2026-09-21T00:05:00.5+09:00';self.command('service_configure',profile)
        self.config.update(feed_start_date='2026-09-19',feed_end_date='2026-09-20')
        files=self.feed()['files'];times=rows(files,'stop_times')
        self.assertTrue(any(r['end_pickup_drop_off_window']=='24:05:00' for r in times))
        self.assert_window_parity()
    def test_stop_period_clips_pickup_and_dropoff_without_inventing_times(self):
        stop=copy.deepcopy(json.loads((ROOT/'fixtures/synthetic-catalog.json').read_text())['stops'][0])
        stop['start_datetime']='2026-09-19T10:00:00+09:00';stop['end_datetime']='2026-09-19T12:00:00+09:00'
        self.command('stop_configure',stop)
        self.config.update(feed_start_date='2026-09-19',feed_end_date='2026-09-19')
        self.assert_window_parity()
        self.assertTrue(all(r['start_pickup_drop_off_window']>='09:50:00' and r['end_pickup_drop_off_window']<='12:09:59' for r in rows(self.feed()['files'],'stop_times')))
    def test_passenger_ride_payment_token_and_observation_tables_cannot_change_feed(self):
        before=self.feed()['archive']
        self.command('profile_create',{'first_name':'秘密名','last_name':'試験姓','email':'private-canary@example.invalid','home_address':{'street':'非公開住所カナリア'}},'rider-a1')
        term=self.core.catalog.snapshot('rider-a1')['terms'][0]['id']
        self.command('agreements_register',{'agreements':[{'terms_id':term,'agreed_at':iso(self.core.clock())}]},'rider-a1')
        ride=self.driver('accept',self.create());grant=self.grant(actor='admin-a1')
        self.command('payment_update',{'ride_id':ride['id'],'payment_status':'received','amount':820})
        observation=json.loads((ROOT/'fixtures/synthetic-observations.json').read_text())
        observation['source']['label']='非公開観測元カナリア'
        self.command('observation_configure',observation['source'])
        run=self.sql('SELECT run_id FROM rides WHERE id=?',(ride['id'],))[0][0]
        self.command('observation_publish',{'vehicle_id':ride['vehicle_id'],'run_id':run,'source_id':observation['source']['source_id'],'observed_at':iso(self.core.clock()),'location':observation['location'],'delays':[]})
        after=self.feed();self.assertEqual(before,after['archive'])
        content=b'\n'.join(after['files'].values()).decode()
        for value in [ride['id'],'rider-a1',ride['vehicle_id'],run,grant['access_token'],'private-canary@example.invalid','非公開住所カナリア','非公開観測元カナリア','139.70012','秘密名','service-a','stop-a','driver-a1']:
            self.assertNotIn(value,content)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'),[(1,)])
    def test_export_queries_never_read_personal_or_operational_tables(self):
        from contextlib import contextmanager
        queries=[];original=self.core.db
        @contextmanager
        def traced(write=False):
            with original(write) as db:
                db.set_trace_callback(queries.append);yield db
        self.core.db=traced;self.feed()
        import re
        self.assertFalse(any(re.search(r'\b(?:rides|passengers|payments|sessions|run_offers|ride_bookings|vehicle_observations|observation_snapshots)\b',q,re.I) for q in queries))
        self.assertFalse(any(re.search(r'\b(?:UPDATE|INSERT|DELETE)\b',q,re.I) for q in queries))
    def test_role_and_tenant_denials(self):
        for actor in ('rider-a1','driver-a1','rider-b1'):self.denied('FORBIDDEN',self.core.gtfs.export,actor,self.config)
        self.sql("UPDATE users SET role='admin' WHERE id='rider-b1'")
        self.denied('NOT_FOUND',self.core.gtfs.export,'rider-b1',self.config)
    def test_inactive_admin_and_revoked_read_grant_denied(self):
        grant=self.grant(actor='admin-a1');context=self.authz(grant)
        self.core.gtfs.export('admin-a1',self.config,context)
        self.grants.revoke('admin-a1',grant['grant_id']);self.denied('INVALID_GRANT',self.core.gtfs.export,'admin-a1',self.config,context)
        self.sql("UPDATE users SET active=0 WHERE id='admin-a1'");self.denied('UNAUTHENTICATED',self.feed)
    def test_production_mode_or_implicit_opt_in_denied(self):
        for key,value in [('basis','production'),('profile','other'),('feed_version','0.7.0'),('booking_url','https://real-service.example/')]:
            original=self.config[key];self.config[key]=value;self.denied('GTFS_SYNTHETIC_ONLY',self.feed);self.config[key]=original
        self.sql("UPDATE meta SET value='production' WHERE key='data_mode'");self.denied('GTFS_SYNTHETIC_ONLY',self.feed)
    def test_unset_coordinates_and_service_profile_block_export(self):
        self.sql("DELETE FROM stop_profiles WHERE stop_id='stop-a'");self.denied('STOP_COORDINATES_NOT_CONFIGURED',self.feed)
        self.sql('DELETE FROM service_profiles');self.denied('SERVICE_MASTER_INCOMPLETE',self.feed)
    def test_unknown_or_invalid_fare_is_not_zero(self):
        for fare in [{},{'amount':None,'currency':'JPY'},{'amount':True,'currency':'JPY'},{'amount':10,'currency':'USD'}]:
            self.sql('UPDATE services SET fare_json=?',(packed(fare),));self.denied('FARE_NOT_CONFIGURED',self.feed)
    def test_missing_routes_stopped_service_or_stop_are_distinct(self):
        self.sql('UPDATE services SET active=0');self.denied('SERVICE_UNAVAILABLE',self.feed);self.sql('UPDATE services SET active=1')
        self.sql("UPDATE stops SET active=0 WHERE id='stop-a'");self.denied('STOP_SUSPENDED',self.feed);self.sql('UPDATE stops SET active=1')
        self.sql('DELETE FROM route_policies');self.denied('ROUTE_TIMING_NOT_CONFIGURED',self.feed)
    def test_closed_calendar_has_no_fabricated_trip(self):
        profile=self.profile();profile['operating_hours']={k:[] for k in profile['operating_hours']};profile['special_operating_hours']=[]
        self.command('service_configure',profile);self.denied('GTFS_NO_SERVICE_DATES',self.feed)
    def test_private_residency_or_non_japan_settings_not_broadened(self):
        for scope in ('resident_only','private','other'):
            profile=self.profile();profile['access_scope']=scope;self.command('service_configure',profile);self.denied('GTFS_ACCESS_UNSUPPORTED',self.feed)
        self.sql("UPDATE services SET timezone='UTC'");self.denied('TIMEZONE_UNSUPPORTED',self.feed)
    def test_date_bounds_oversize_and_input_injection(self):
        for end in ('2026-09-18','2028-09-19'):
            self.config['feed_end_date']=end;self.denied('GTFS_INVALID_PERIOD',self.feed)
        self.config=copy.deepcopy(CONFIG);self.config['reservation_id']='private';self.denied('INVALID_INPUT',self.feed)
    def test_public_ids_readings_mappings_and_changed_names(self):
        self.config['stops']['stop-b']['id']='synthetic-A';self.denied('GTFS_DUPLICATE_ID',self.feed)
        self.config=copy.deepcopy(CONFIG);self.config['stops']['stop-b']['kana']='';self.denied('INVALID_TEXT',self.feed)
        self.config=copy.deepcopy(CONFIG);del self.config['stops']['stop-b'];self.denied('GTFS_STOP_MAPPING_REQUIRED',self.feed)
        self.config=copy.deepcopy(CONFIG);self.sql("UPDATE stops SET name='改名' WHERE id='stop-a'");self.denied('GTFS_NAME_CHANGED',self.feed)
    def test_export_does_not_initialize_or_overwrite_files(self):
        target=Path(self.temp.name)/'feed';target.mkdir();(target/'keep').write_text('keep')
        with self.assertRaises(FileExistsError):export(self.path,self.config,target)
        self.assertEqual((target/'keep').read_text(),'keep')
        missing=Path(self.temp.name)/'missing.sqlite3'
        with self.assertRaises(ValueError):export(missing,self.config,Path(self.temp.name)/'unused')
        self.assertFalse(missing.exists())
    def test_export_failure_leaves_no_partial_feed(self):
        self.sql('UPDATE services SET fare_json=?',('{}',));target=Path(self.temp.name)/'failure'
        with self.assertRaises(DomainError):export(self.path,self.config,target)
        self.assertFalse(target.exists())
    def test_domestic_required_tables_and_fields_are_checked(self):
        files=self.feed()['files']
        for filename in ('fare_attributes.txt','translations.txt','feed_info.txt'):
            bad=copy.copy(files);del bad[filename];self.assertTrue(validate(zip_bytes(bad))['errors'])
        for name,field,value,rule in [('feed_info','feed_version','','JP_FEED_REQUIRED_FIELDS'),('agency','agency_lang','en','JP_AGENCY_ID_TIMEZONE_LANGUAGE'),('fare_attributes','price','820.5','JP_FARE_INTEGER_JPY'),('stops','stop_lat','35.5','JP_STOP_POINT_FIELDS')]:
            entries=rows(files,name);entries[0][field]=value
            self.assertIn(rule,validate(zip_bytes(replace_rows(files,name,entries)))['errors'])
    def test_domestic_checks_reject_missing_reading_wrong_coordinate_or_currency(self):
        files=self.feed()['files']
        for name,field,value,rule in [('translations','translation','','JP_KANA_COVERAGE'),('stops','stop_lat','139.500000','STOP_COORDINATE_RANGE'),('fare_attributes','currency_type','USD','JP_FARE_INTEGER_JPY')]:
            entries=rows(files,name);entries[0][field]=value;self.assertIn(rule,validate(zip_bytes(replace_rows(files,name,entries)))['errors'])
    def test_public_feed_allowlist_rejects_extra_private_files_and_columns(self):
        files=self.feed()['files'];bad={**files,'reservations.json':b'{"private":"canary"}'}
        self.assertIn('PROFILE_FILE_ALLOWLIST',validate(zip_bytes(bad))['errors'])
        bad=copy.copy(files);bad['stops.txt']=bad['stops.txt'].replace(b'location_type\r\n',b'location_type,rider_id\r\n')
        self.assertTrue(validate(zip_bytes(bad))['errors'])
    def test_domestic_checks_reject_area_expansion_bad_refs_and_booking_types(self):
        files=self.feed()['files']
        for name,field,value,rule in [('routes','continuous_pickup','0','PROFILE_DESIGNATED_STOPS_ONLY'),('booking_rules','booking_type','2','PROFILE_IMMEDIATE_BOOKING'),('stop_times','stop_id','private-stop','FLEX_STOP_REFERENCES'),('stop_times','pickup_type','0','PROFILE_DIRECTION_AND_BOOKING')]:
            entries=rows(files,name);entries[0][field]=value;self.assertIn(rule,validate(zip_bytes(replace_rows(files,name,entries)))['errors'])
    def test_domestic_checks_reject_bad_zip_and_reversed_windows(self):
        self.assertTrue(validate(b'not a zip')['errors'])
        files=self.feed()['files'];times=rows(files,'stop_times');times[0]['end_pickup_drop_off_window']='00:00:00'
        self.assertIn('FLEX_VALID_WINDOWS',validate(zip_bytes(replace_rows(files,'stop_times',times)))['errors'])
    def test_validator_success_exit_cannot_hide_error_or_skipped_system(self):
        report={'summary':{'validatorVersion':'8.0.1'},'notices':[{'severity':'ERROR','code':'invalid_url'}]}
        self.assertEqual(summarize(report,{'notices':[]},0)['status'],'FAIL')
        report['notices']=[]
        self.assertEqual(summarize(report,{'notices':[{'code':'failure'}]},0)['status'],'FAIL')
        self.assertEqual(summarize(report,{},0)['status'],'FAIL')
        self.assertEqual(summarize(report,{'notices':[]},0)['status'],'PASS')
        report['notices']=[{'severity':'WARNING','code':'kept'}]
        self.assertEqual(summarize(report,{'notices':[]},0)['warnings'],report['notices'])
    def test_validator_hash_mismatch_prevents_execution(self):
        jar=Path(self.temp.name)/'unknown.jar';jar.write_bytes(b'bad')
        with self.assertRaises(ValueError):verify_jar(jar)

if __name__=='__main__':unittest.main()
