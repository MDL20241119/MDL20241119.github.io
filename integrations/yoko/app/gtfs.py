"""Admin-only synthetic Schedule/Flex export through the Mobility Core.

No ride, passenger, payment, offer, observation or credential table is read.
This local profile has no public HTTP route and cannot export production data.
"""
import csv
import hashlib
import io
import json
import math
import re
import zipfile
from datetime import datetime, timedelta
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
from .core import exact, fail, packed
from .catalog import day, text, timestamp, https_url
from .service_calendar import operating_windows
from .transport_data import geojson_point_to_gtfs

PROFILE='mdl-synthetic-fixed-stop-flex-v1'
HEADERS={
    'agency.txt':['agency_id','agency_name','agency_url','agency_timezone','agency_lang'],
    'stops.txt':['stop_id','stop_name','stop_lat','stop_lon','location_type'],
    'routes.txt':['route_id','agency_id','route_long_name','route_type','continuous_pickup','continuous_drop_off'],
    'trips.txt':['route_id','service_id','trip_id','trip_headsign'],
    'stop_times.txt':['trip_id','stop_id','stop_sequence','start_pickup_drop_off_window','end_pickup_drop_off_window','pickup_type','drop_off_type','pickup_booking_rule_id','drop_off_booking_rule_id'],
    'calendar_dates.txt':['service_id','date','exception_type'],
    'booking_rules.txt':['booking_rule_id','booking_type','message','booking_url'],
    'feed_info.txt':['feed_publisher_name','feed_publisher_url','feed_lang','feed_start_date','feed_end_date','feed_version'],
    'fare_attributes.txt':['fare_id','price','currency_type','payment_method','transfers','agency_id'],
    'fare_rules.txt':['fare_id','route_id'],
    'translations.txt':['table_name','field_name','language','translation','record_id','field_value'],
}

def public_id(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}',value):fail('GTFS_INVALID_ID','公開用IDは1〜40文字の英数字・ハイフン・アンダースコアで指定してください')
    return value

def kana(value):
    text(value,300)
    if not re.fullmatch(r'[ぁ-ゖァ-ヺー・ 　]+',value):fail('GTFS_READING_REQUIRED','読み仮名をひらがな・カタカナで設定してください')
    return value

def synthetic_url(value):
    https_url(value)
    if value!='https://example.com/':fail('GTFS_SYNTHETIC_ONLY','架空試験用URLは予約済みの例示用URL https://example.com/ に限定します')

def hhmmss(seconds):
    return f'{seconds//3600:02d}:{seconds//60%60:02d}:{seconds%60:02d}'

def encode_tables(tables):
    result={}
    for name,headers in HEADERS.items():
        stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=headers,lineterminator='\r\n')
        writer.writeheader();writer.writerows(tables[name]);result[name]=stream.getvalue().encode('utf-8')
    return result

def zip_bytes(files):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16;archive.writestr(info,files[name])
    return stream.getvalue()

def pickup_windows(profile, origin, destination, travel, first, last, timezone):
    """Integer-second pickup intervals admitted by Booking.interval.

    Long continuous service is split by service day; short overnight windows
    retain 24h+ values. Dropoffs may extend beyond the final pickup date.
    """
    zone=ZoneInfo(timezone)
    midnight=lambda d:datetime.combine(d,datetime.min.time(),zone).timestamp()
    lower=max(midnight(first),timestamp(profile['start_datetime']),timestamp(origin['start_datetime']),timestamp(destination['start_datetime'])-travel)
    upper=midnight(last+timedelta(days=1))
    for obj,offset in [(profile,travel),(origin,0),(destination,travel)]:
        if obj.get('end_datetime'):upper=min(upper,timestamp(obj['end_datetime'])-offset)
    result=[]
    for begin,end in operating_windows(profile,first-timedelta(days=1),last+timedelta(days=1),timezone):
        a=math.ceil(max(lower,begin));b=math.ceil(min(upper,end-travel))-1
        while a<b:
            date=datetime.fromtimestamp(a,zone).date();base=int(midnight(date))
            # A <=24h overnight interval stays on its originating service day.
            finish=min(b,base+86400-1) if b-a>=86400 else b
            result.append((date,a-base,finish-base))
            a=finish+1
    return result

class Gtfs:
    def __init__(self,core):self.core=core

    def export(self,actor_id,config,authorization=None):
        with self.core.db() as db:
            actor=self.core.actor(db,actor_id,'admin');self.core.check_authorization(db,actor_id,authorization)
            exact(config,['profile','basis','service_id','feed_start_date','feed_end_date','feed_version','agency','publisher','booking_url','route_type','payment_method','transfers','stops'])
            mode=db.execute("SELECT value FROM meta WHERE key='data_mode'").fetchone()
            if not mode or mode[0]!='synthetic' or config['profile']!=PROFILE or config['basis']!='synthetic_test_only':fail('GTFS_SYNTHETIC_ONLY','現在の出力器は明示された架空試験専用です')
            first,last=day(config['feed_start_date']),day(config['feed_end_date'])
            if not 1900<=first.year<=last.year<=9998 or not 0<=(last-first).days<=365:fail('GTFS_INVALID_PERIOD','出力期間は1900〜9998年の1〜366日で指定してください')
            text(config['feed_version'],100)
            if 'synthetic' not in config['feed_version']:fail('GTFS_SYNTHETIC_ONLY','試験版を識別するfeed_versionが必要です')
            agency=config['agency'];publisher=config['publisher']
            exact(agency,['id','name','kana','url']);public_id(agency['id']);text(agency['name']);kana(agency['kana']);synthetic_url(agency['url'])
            exact(publisher,['name','kana','url']);text(publisher['name']);kana(publisher['kana']);synthetic_url(publisher['url']);synthetic_url(config['booking_url'])
            if not all('架空' in x['name'] for x in (agency,publisher)):fail('GTFS_SYNTHETIC_ONLY','事業者・提供元の名称に架空試験を明記してください')
            if type(config['route_type']) is not int or config['route_type']!=3:fail('GTFS_MODE_UNSUPPORTED','この試験プロファイルはバス相当のroute_type=3だけを扱います')
            if type(config['payment_method']) is not int or config['payment_method'] not in (0,1) or type(config['transfers']) is not int or config['transfers']!=0:fail('GTFS_FARE_UNSUPPORTED','支払時期を明示し、乗継なしを指定してください')
            service=self.core.catalog.own_service(db,actor,config['service_id'])
            if not service['active']:fail('SERVICE_UNAVAILABLE','停止中サービスは出力できません',409)
            if service['timezone']!='Asia/Tokyo':fail('TIMEZONE_UNSUPPORTED','国内試験プロファイルはAsia/Tokyoのみです')
            self.core.catalog.service_view(db,actor,service)
            profile=json.loads(db.execute('SELECT data_json FROM service_profiles WHERE service_id=?',(service['id'],)).fetchone()[0])
            if profile['access_scope'] not in ('public','registered_user_only'):fail('GTFS_ACCESS_UNSUPPORTED','居住資格・非公開等の条件は公開プロファイルで表現できません')
            if json.loads(service['policy_json']).get('call_mode')!='immediate':fail('GTFS_MODE_UNSUPPORTED','即時呼出だけを扱います')
            fare=json.loads(service['fare_json'])
            if type(fare.get('amount')) is not int or not 0<=fare['amount']<=2147483647 or fare.get('currency')!='JPY':fail('FARE_NOT_CONFIGURED','確定した日本円の均一運賃が必要です',503)
            routes=list(db.execute('SELECT * FROM route_policies WHERE service_id=? ORDER BY origin_stop_id,destination_stop_id',(service['id'],)))
            if not routes:fail('ROUTE_TIMING_NOT_CONFIGURED','指定乗降場所間の経路設定が必要です',503)
            if len(routes)>100:fail('GTFS_LIMIT','試験出力は100経路までです')
            used={r[k] for r in routes for k in ('origin_stop_id','destination_stop_id')}
            labels=config['stops']
            if not isinstance(labels,dict) or set(labels)!=used:fail('GTFS_STOP_MAPPING_REQUIRED','利用する全指定乗降場所の公開ID・名称・読み仮名を過不足なく指定してください')
            points={};public_ids=set()
            for stop_id,label in sorted(labels.items()):
                exact(label,['id','name','kana']);public_id(label['id']);text(label['name']);kana(label['kana'])
                if label['id'] in public_ids:fail('GTFS_DUPLICATE_ID','乗降場所の公開IDが重複しています')
                public_ids.add(label['id'])
                stop=db.execute('SELECT * FROM stops WHERE id=? AND service_id=?',(stop_id,service['id'])).fetchone()
                if not stop:fail('INVALID_STOP','同じサービスの指定乗降場所が必要です')
                if not stop['active']:fail('STOP_SUSPENDED','休止中の乗降場所を含むため出力できません',409)
                if stop['name']!=label['name']:fail('GTFS_NAME_CHANGED','乗降場所の名称が変わっています。公開名・読み仮名を再確認してください',409)
                points[stop_id]=self.core.catalog.stop_view(db,stop)
            tables={name:[] for name in HEADERS};mappings=[]
            add=lambda name,**row:tables[name+'.txt'].append(row)
            def translation(table,field,value,reading,record=''):
                add('translations',table_name=table,field_name=field,language='ja-Hrkt',translation=reading,record_id=record,field_value='' if record else value)
            add('agency',agency_id=agency['id'],agency_name=agency['name'],agency_url=agency['url'],agency_timezone=service['timezone'],agency_lang='ja')
            translation('agency','agency_name',agency['name'],agency['kana'],agency['id'])
            for key,p in sorted(points.items()):
                label=labels[key];coords=geojson_point_to_gtfs(p['location'])
                add('stops',stop_id=label['id'],stop_name=p['name'],stop_lat=f"{coords['stop_lat']:.6f}",stop_lon=f"{coords['stop_lon']:.6f}",location_type=0)
                translation('stops','stop_name',p['name'],label['kana'],label['id'])
            add('feed_info',feed_publisher_name=publisher['name'],feed_publisher_url=publisher['url'],feed_lang='ja',feed_start_date=first.strftime('%Y%m%d'),feed_end_date=last.strftime('%Y%m%d'),feed_version=config['feed_version'])
            translation('feed_info','feed_publisher_name',publisher['name'],publisher['kana'])
            message='架空試験データ。実際には利用できません。即時呼出のみ。車両・空席の確約ではありません。'
            if profile['access_scope']=='registered_user_only':message+='利用者登録が必要です。'
            add('booking_rules',booking_rule_id='immediate',booking_type=0,message=message,booking_url=config['booking_url'])
            add('fare_attributes',fare_id='uniform',price=fare['amount'],currency_type='JPY',payment_method=config['payment_method'],transfers=0,agency_id=agency['id'])
            calendars={}
            for row in routes:
                policy=json.loads(row['data_json'])
                if policy.get('basis')!='synthetic_test_only' or type(policy.get('travel_seconds')) is not int or not 60<=policy['travel_seconds']<=7200:fail('GTFS_TIMING_UNSUPPORTED','架空の所要時間設定が必要です')
                origin,destination=row['origin_stop_id'],row['destination_stop_id'];a,b=labels[origin],labels[destination]
                rid='r_'+hashlib.sha256(packed([agency['id'],a['id'],b['id']]).encode()).hexdigest()[:24]
                windows=pickup_windows(profile,points[origin],points[destination],policy['travel_seconds'],first,last,service['timezone'])
                if not windows:fail('GTFS_NO_SERVICE_DATES','期間内に乗降できる時間帯がない経路があります',409)
                add('routes',route_id=rid,agency_id=agency['id'],route_long_name=a['name']+' → '+b['name'],route_type=3,continuous_pickup=1,continuous_drop_off=1)
                translation('routes','route_long_name','',a['kana']+' から '+b['kana'],rid)
                add('fare_rules',fare_id='uniform',route_id=rid)
                patterns={}
                for date,start,end in windows:patterns.setdefault((start,end),set()).add(date)
                for (start,end),dates in sorted(patterns.items()):
                    dates=tuple(sorted(dates));cid='c_'+hashlib.sha256(packed([d.isoformat() for d in dates]).encode()).hexdigest()[:24]
                    calendars[cid]=dates;tid=f'{rid}_{start}_{end}'
                    add('trips',route_id=rid,service_id=cid,trip_id=tid,trip_headsign=b['name'])
                    translation('trips','trip_headsign','',b['kana'],tid)
                    for seq,label,offset,pickup,dropoff in [(1,a,0,2,1),(2,b,policy['travel_seconds'],1,2)]:
                        add('stop_times',trip_id=tid,stop_id=label['id'],stop_sequence=seq,start_pickup_drop_off_window=hhmmss(start+offset),end_pickup_drop_off_window=hhmmss(end+offset),pickup_type=pickup,drop_off_type=dropoff,pickup_booking_rule_id='immediate' if pickup==2 else '',drop_off_booking_rule_id='immediate' if dropoff==2 else '')
                mappings.append({'route_policy_id':row['id'],'route_id':rid,'route_version':row['version']})
            for cid,dates in sorted(calendars.items()):
                for date in dates:add('calendar_dates',service_id=cid,date=date.strftime('%Y%m%d'),exception_type=1)
            files=encode_tables(tables);archive=zip_bytes(files)
            return {'archive':archive,'files':files,'report':{'profile':PROFILE,'synthetic':True,'public_feed_created':False,'production_conformance':'NOT_ESTABLISHED','service_revision':service['revision'],'config_sha256':hashlib.sha256(packed(config).encode()).hexdigest(),'feed_sha256':hashlib.sha256(archive).hexdigest(),'stop_mapping':{k:v['id'] for k,v in labels.items()},'route_mapping':mappings,'rows':{k:len(v) for k,v in tables.items()},'excluded_data':['passengers','rides','ride_bookings','payments','vehicles','observations','credentials']}}
