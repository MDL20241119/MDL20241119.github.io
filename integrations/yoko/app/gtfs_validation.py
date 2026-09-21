"""Independent domestic checks for the narrow synthetic Flex export profile.

Not a general GTFS validator or a conformance certificate. The canonical
MobilityData validator must also be run; manual data/consumer review remains.
"""
import csv
import io
import math
import re
import zipfile
from datetime import datetime
from .gtfs import HEADERS,PROFILE

def validate(archive):
    errors=[];passed=[];tables={}
    def check(rule,condition):
        (passed if condition else errors).append(rule)
    try:
        if len(archive)>10*1024*1024:raise ValueError('archive size')
        with zipfile.ZipFile(io.BytesIO(archive)) as z:
            names=z.namelist()
            check('PROFILE_FILE_ALLOWLIST',len(names)==len(set(names)) and set(names)==set(HEADERS))
            if errors:return {'profile':PROFILE,'errors':errors,'passed':passed,'conformance':False}
            if sum(i.file_size for i in z.infolist())>20*1024*1024:raise ValueError('expanded size')
            for name,headers in HEADERS.items():
                content=z.read(name).decode('utf-8-sig')
                reader=csv.DictReader(io.StringIO(content,newline=''))
                check('PROFILE_COLUMNS_'+name,reader.fieldnames==headers)
                rows=list(reader)
                if any(None in r or any(v is None for v in r.values()) for r in rows):raise ValueError('invalid CSV row')
                if any(any(ord(c)<32 for c in v) for r in rows for v in r.values()):raise ValueError('CSV control character')
                tables[name]=rows
        if errors:return {'profile':PROFILE,'errors':errors,'passed':passed,'conformance':False}
        feeds=tables['feed_info.txt'];agencies=tables['agency.txt'];stops=tables['stops.txt'];fares=tables['fare_attributes.txt'];routes=tables['routes.txt'];trips=tables['trips.txt']
        check('JP_REQUIRED_TABLES_NONEMPTY',all(tables.values()))
        check('JP_FEED_REQUIRED_FIELDS',len(feeds)==1 and all(feeds[0].get(k) for k in ('feed_publisher_name','feed_publisher_url','feed_lang','feed_start_date','feed_end_date','feed_version')))
        check('JP_FEED_JAPANESE',bool(feeds) and all(f['feed_lang']=='ja' for f in feeds))
        valid_dates=all(re.fullmatch(r'\d{8}',f[k]) for f in feeds for k in ('feed_start_date','feed_end_date'))
        if valid_dates:
            valid_dates=all(datetime.strptime(f['feed_start_date'],'%Y%m%d')<=datetime.strptime(f['feed_end_date'],'%Y%m%d') for f in feeds)
        check('JP_FEED_PERIOD',valid_dates)
        check('JP_AGENCY_ID_TIMEZONE_LANGUAGE',len(agencies)==1 and all(a['agency_id'] and a['agency_timezone']=='Asia/Tokyo' and a['agency_lang']=='ja' for a in agencies))
        check('JP_STOP_POINT_FIELDS',bool(stops) and all(s['stop_name'] and s['location_type']=='0' and all(re.fullmatch(r'-?\d+\.\d{5,}',s[k]) for k in ('stop_lat','stop_lon')) for s in stops))
        check('STOP_COORDINATE_RANGE',all(math.isfinite(float(s['stop_lat'])) and -90<=float(s['stop_lat'])<=90 and math.isfinite(float(s['stop_lon'])) and -180<=float(s['stop_lon'])<=180 for s in stops))
        check('JP_FARE_INTEGER_JPY',len(fares)==1 and all(re.fullmatch(r'\d+',f['price']) and f['currency_type']=='JPY' and f['payment_method'] in ('0','1') and f['transfers']=='0' for f in fares))
        check('JP_ROUTE_AGENCY',all(r['agency_id'] in {a['agency_id'] for a in agencies} for r in routes))
        readings={(r['table_name'],r['field_name'],r['record_id'],r['field_value']):r['translation'] for r in tables['translations.txt'] if r['language']=='ja-Hrkt'}
        targets=[]
        for table,rows,idfield,field in [('agency',agencies,'agency_id','agency_name'),('stops',stops,'stop_id','stop_name'),('routes',routes,'route_id','route_long_name'),('trips',trips,'trip_id','trip_headsign')]:
            targets.extend((table,field,r[idfield],'') for r in rows)
        targets.extend(('feed_info','feed_publisher_name','',f['feed_publisher_name']) for f in feeds)
        check('JP_KANA_COVERAGE',all(re.fullmatch(r'[ぁ-ゖァ-ヺー・ 　]+',readings.get(key,'')) for key in targets))
        check('PROFILE_DESIGNATED_STOPS_ONLY',all(r['continuous_pickup']=='1' and r['continuous_drop_off']=='1' and r['route_type']=='3' for r in routes))
        bookings=tables['booking_rules.txt'];booking_ids={b['booking_rule_id'] for b in bookings}
        check('PROFILE_IMMEDIATE_BOOKING',bool(bookings) and all(b['booking_type']=='0' and b['booking_url'] for b in bookings))
        check('PROFILE_SYNTHETIC_NOTICE',all('架空' in a['agency_name'] for a in agencies) and all('架空' in f['feed_publisher_name'] and 'synthetic' in f['feed_version'] for f in feeds) and all('架空' in b['message'] for b in bookings))
        urls=[a['agency_url'] for a in agencies]+[f['feed_publisher_url'] for f in feeds]+[b['booking_url'] for b in bookings]
        check('PROFILE_SYNTHETIC_URLS',all(u=='https://example.com/' for u in urls))
        stop_ids={s['stop_id'] for s in stops};trip_ids={t['trip_id'] for t in trips};route_ids={r['route_id'] for r in routes}
        check('PROFILE_UNIQUE_IDS',len(stop_ids)==len(stops) and len(trip_ids)==len(trips) and len(route_ids)==len(routes))
        check('TRIP_ROUTE_REFERENCES',all(t['route_id'] in route_ids for t in trips))
        check('FARE_ROUTE_REFERENCES',set(r['route_id'] for r in tables['fare_rules.txt'])==route_ids and all(r['fare_id'] in {f['fare_id'] for f in fares} for r in tables['fare_rules.txt']))
        calendars=tables['calendar_dates.txt'];cal_ids={c['service_id'] for c in calendars}
        check('CALENDAR_REFERENCES',cal_ids=={t['service_id'] for t in trips} and len({(c['service_id'],c['date']) for c in calendars})==len(calendars) and all(c['exception_type']=='1' and feeds[0]['feed_start_date']<=c['date']<=feeds[0]['feed_end_date'] and datetime.strptime(c['date'],'%Y%m%d') for c in calendars))
        times=tables['stop_times.txt'];grouped={}
        for row in times:grouped.setdefault(row['trip_id'],[]).append(row)
        check('FLEX_STOP_REFERENCES',set(grouped)==trip_ids and all(r['stop_id'] in stop_ids for r in times))
        def seconds(value):
            if not re.fullmatch(r'\d{2,3}:[0-5]\d:[0-5]\d',value):raise ValueError('time format')
            h,m,s=map(int,value.split(':'));return h*3600+m*60+s
        check('FLEX_VALID_WINDOWS',all(seconds(r['start_pickup_drop_off_window'])<seconds(r['end_pickup_drop_off_window']) for r in times))
        def od(rows):
            if len(rows)!=2:return False
            a,b=sorted(rows,key=lambda r:int(r['stop_sequence']))
            return (a['stop_sequence'],b['stop_sequence'],a['pickup_type'],a['drop_off_type'],b['pickup_type'],b['drop_off_type'])==('1','2','2','1','1','2') and a['stop_id']!=b['stop_id'] and a['pickup_booking_rule_id'] in booking_ids and b['drop_off_booking_rule_id'] in booking_ids and not a['drop_off_booking_rule_id'] and not b['pickup_booking_rule_id'] and seconds(b['start_pickup_drop_off_window'])>seconds(a['start_pickup_drop_off_window']) and seconds(b['end_pickup_drop_off_window'])>seconds(a['end_pickup_drop_off_window'])
        check('PROFILE_DIRECTION_AND_BOOKING',all(od(rows) for rows in grouped.values()))
    except (ValueError,KeyError,IndexError,TypeError,UnicodeError,zipfile.BadZipFile,RuntimeError,OverflowError) as e:
        errors.append('MALFORMED_FEED:'+type(e).__name__)
    return {'profile':PROFILE,'errors':errors,'passed':passed,'conformance':False,'scope':'GTFS-JP v4 mandatory fields and fixed-stop synthetic subset; not all domestic rules or consumer validation','remaining':['verified source data','live booking/contact URLs','consumer interoperability','fare and operating approval','full applicable domestic review']}
