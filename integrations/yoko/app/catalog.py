"""Shared passenger, consent and transport-master business services.

No HTTP, MLIT validator or external network dependencies. Called through Core's
transactions, authorizations, confirmations and operation ledger.
"""
import json
import math
import re
from datetime import date, datetime, timedelta
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
from .core import exact, fail, iso, packed, uid
from .transport_data import geojson_point_to_gtfs
from .service_calendar import DAYS, daily_slots

RIDER_COMMANDS={'profile_create','profile_update','profile_delete','agreements_register'}
ADMIN_COMMANDS={'terms_publish','service_configure','stop_configure','route_configure','payment_update','observation_configure','observation_publish'}
DRIVER_COMMANDS={'offer_open','offer_close'}
CATALOG_COMMANDS=RIDER_COMMANDS|ADMIN_COMMANDS|DRIVER_COMMANDS
PROFILE_FIELDS={'first_name','last_name','first_name_kana','last_name_kana','gender','birthdate','phone_number','email','home_address'}

def text(value,maximum=200,empty=False):
    if not isinstance(value,str) or len(value)>maximum or (not empty and not value.strip()) or any(ord(c)<32 for c in value):
        fail('INVALID_TEXT','文字列の形式・長さを確認してください')
    return value

def timestamp(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})',value):
        fail('INVALID_DATETIME','タイムゾーン付きのRFC3339日時が必要です')
    try:return datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()
    except ValueError:fail('INVALID_DATETIME','日時が不正です')

def day(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):fail('INVALID_DATE','日付はYYYY-MM-DDで指定してください')
    try:return date.fromisoformat(value)
    except ValueError:fail('INVALID_DATE','日付が不正です')

def https_url(value):
    text(value,2000)
    try:u=urlsplit(value)
    except ValueError:fail('INVALID_URL','HTTPSのURLが不正です')
    if u.scheme!='https' or not u.hostname or u.username or u.password or u.fragment:
        fail('INVALID_URL','認証情報を含まないHTTPSのURLを指定してください')
    return value

def dates(data):
    start=timestamp(data['start_datetime'])
    if data['end_datetime'] is not None and timestamp(data['end_datetime'])<=start:
        fail('INVALID_PERIOD','終了は開始より後に指定してください')

def slots(items):
    if not isinstance(items,list) or len(items)>24:fail('INVALID_HOURS','営業時間帯が不正です')
    previous=-1
    for item in items:
        exact(item,['start_time_offset_sec','end_time_offset_sec'])
        a,b=item['start_time_offset_sec'],item['end_time_offset_sec']
        if type(a) is not int or type(b) is not int or not 0<=a<b<=172800 or a<previous:
            fail('INVALID_HOURS','営業時間帯は昇順・重複なし、0〜172800秒で指定してください')
        previous=b

def profile(data,now):
    if not isinstance(data,dict) or set(data)-PROFILE_FIELDS:fail('INVALID_PROFILE','未対応の利用者情報です')
    for k,v in data.items():
        if k!='home_address':text(v,254 if k=='email' else 100)
    if not (data.get('first_name') and data.get('last_name')) and not (data.get('first_name_kana') and data.get('last_name_kana')):
        fail('NAME_REQUIRED','氏名の姓・名、またはフリガナの姓・名が必要です')
    if 'gender' in data and data['gender'] not in ('male','female','other','unspecified'):fail('INVALID_PROFILE','性別の指定が不正です')
    if 'birthdate' in data and day(data['birthdate'])>datetime.fromtimestamp(now,ZoneInfo('Asia/Tokyo')).date():fail('INVALID_PROFILE','生年月日が未来になっています')
    if 'phone_number' in data and not re.fullmatch(r'\+[1-9][0-9]{1,14}',data['phone_number']):fail('INVALID_PROFILE','電話番号は国番号付きで指定してください')
    if 'email' in data and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',data['email']):fail('INVALID_PROFILE','メールアドレスの形式が不正です')
    if 'home_address' in data:
        address=data['home_address']
        if not isinstance(address,dict) or set(address)-{'postal_code','state','city','street','location'}:fail('INVALID_PROFILE','住所項目が不正です')
        for k,v in address.items():
            if k=='location':
                exact(v,['type','coordinates']);geojson_point_to_gtfs(v)
            else:text(v,300)
        if 'postal_code' in address and not re.fullmatch(r'\d{7}',address['postal_code']):fail('INVALID_PROFILE','国内郵便番号は7桁で指定してください')

class Catalog:
    def __init__(self,core):self.core=core
    def own_service(self,db,actor,service_id):
        text(service_id,100)
        row=db.execute('SELECT * FROM services WHERE id=? AND tenant_id=?',(service_id,actor['tenant_id'])).fetchone()
        if not row:fail('NOT_FOUND','サービスが見つかりません',404)
        return row
    def own_passenger(self,db,actor,passenger_id):
        if actor['role']!='rider' or passenger_id!=actor['id']:fail('FORBIDDEN','本人の利用者情報だけを扱えます',403)
        row=db.execute('SELECT * FROM passengers WHERE id=? AND tenant_id=?',(passenger_id,actor['tenant_id'])).fetchone()
        if not row:fail('NOT_FOUND','利用者情報は登録されていないか、削除されています',404)
        return row
    def version(self,db,actor_id):
        row=db.execute('SELECT version FROM passenger_versions WHERE actor_id=?',(actor_id,)).fetchone()
        return row[0] if row else 0
    def terms(self,db,actor,service_id=None,category=None):
        if service_id is not None:self.own_service(db,actor,service_id)
        return list(db.execute('SELECT * FROM terms WHERE tenant_id=? AND service_id IS ? AND active=1'+(' AND category=?' if category else '')+' ORDER BY category',
            (actor['tenant_id'],service_id,*([category] if category else []))))
    def term_view(self,row):
        return {'id':row['id'],'category':row['category'],'name':row['name'],'url':row['url'],'agreement_required':bool(row['agreement_required']),'created_at':row['created_at'],'updated_at':row['created_at']}
    def passenger_view(self,row):return {'id':row['id'],**json.loads(row['profile_json']),'created_at':row['created_at'],'updated_at':row['updated_at']}
    def agreement_view(self,row):
        result={'terms_id':row['terms_id'],'term_category':row['category'],'agreed_at':row['agreed_at']}
        if row['service_id'] is not None:result['service_id']=row['service_id']
        return result
    def agreement_rows(self,db,actor,service_id=None):
        self.own_passenger(db,actor,actor['id'])
        if service_id is not None:self.own_service(db,actor,service_id)
        return list(db.execute('SELECT a.*,t.category,t.service_id FROM agreements a JOIN terms t ON t.id=a.terms_id WHERE a.passenger_id=?'+(' AND t.service_id=?' if service_id is not None else '')+' ORDER BY a.terms_id',(actor['id'],*([service_id] if service_id is not None else []))))
    def prepare(self,db,actor,kind,data):
        required_role='rider' if kind in RIDER_COMMANDS else ('driver' if kind in DRIVER_COMMANDS else 'admin')
        if actor['role']!=required_role:fail('FORBIDDEN','この台帳操作の権限がありません',403)
        if kind=='payment_update':return self.core.payments.prepare(db,actor,data)
        if kind in ('observation_configure','observation_publish'):return self.core.observations.prepare(db,actor,kind,data)
        if kind in {'route_configure','offer_open','offer_close'}:return self.core.booking.catalog_prepare(db,actor,kind,data)
        version=0;dependencies=[]
        if kind in ('profile_create','profile_update'):
            profile(data,self.core.clock());version=self.version(db,actor['id'])
            row=db.execute('SELECT id FROM passengers WHERE id=?',(actor['id'],)).fetchone()
            if kind=='profile_create' and row:fail('PROFILE_EXISTS','登録済みです。取得または更新を使ってください',409)
            if kind=='profile_update':self.own_passenger(db,actor,actor['id'])
        elif kind=='profile_delete':
            exact(data,[]);self.own_passenger(db,actor,actor['id']);version=self.version(db,actor['id'])
            if db.execute("SELECT 1 FROM rides WHERE rider_id=? AND status NOT IN ('completed','cancelled')",(actor['id'],)).fetchone():
                fail('ACTIVE_RESERVATIONS','進行中の依頼があります。先に取消または運行完了を確認してください',409)
        elif kind=='agreements_register':
            self.own_passenger(db,actor,actor['id']);version=self.version(db,actor['id']);exact(data,['agreements'])
            if not isinstance(data['agreements'],list) or not 1<=len(data['agreements'])<=50:fail('INVALID_AGREEMENTS','1〜50件の同意を指定してください')
            seen=set()
            for item in data['agreements']:
                exact(item,['terms_id','agreed_at']);text(item['terms_id'],100)
                if item['terms_id'] in seen:fail('INVALID_AGREEMENTS','同じ規約IDを重複して指定できません')
                seen.add(item['terms_id'])
                if timestamp(item['agreed_at'])>self.core.clock()+60:fail('INVALID_AGREED_AT','同意日時が未来になっています')
                term=db.execute('SELECT * FROM terms WHERE id=? AND tenant_id=?',(item['terms_id'],actor['tenant_id'])).fetchone()
                if not term:fail('NOT_FOUND','規約が見つかりません',404)
                old=db.execute('SELECT 1 FROM agreements WHERE passenger_id=? AND terms_id=?',(actor['id'],item['terms_id'])).fetchone()
                if not term['active'] and not old:fail('TERMS_REPLACED','更新された規約を確認してください',409)
                dependencies.append({'terms_id':term['id'],'active':bool(term['active'])})
        elif kind=='terms_publish':
            exact(data,['service_id','category','name','url','agreement_required']);text(data['name'],200);https_url(data['url'])
            allowed={'privacy','cancellation','user','third_party'}|({'platform','provider'} if data['service_id'] is None else {'service'})
            if not isinstance(data['category'],str) or data['category'] not in allowed or type(data['agreement_required']) is not bool:fail('INVALID_TERMS','規約の分類または同意要否が不正です')
            if data['service_id'] is not None:self.own_service(db,actor,data['service_id'])
            dependencies=[r['id'] for r in self.terms(db,actor,data['service_id'],data['category'])]
        elif kind=='service_configure':
            exact(data,['service_id','access_scope','start_datetime','end_datetime','cities','operating_hours','special_operating_hours','holiday_dates'])
            service=self.own_service(db,actor,data['service_id']);version=service['revision'];dates(data)
            if data['access_scope'] not in ('public','resident_only','registered_user_only','private','other'):fail('INVALID_SERVICE','公開範囲が不正です')
            exact(data['operating_hours'],DAYS)
            for v in data['operating_hours'].values():slots(v)
            if not isinstance(data['special_operating_hours'],list) or len(data['special_operating_hours'])>400:fail('INVALID_HOURS','特別営業日の指定が不正です')
            seen=set()
            for item in data['special_operating_hours']:
                exact(item,['date','time_slots']);day(item['date']);slots(item['time_slots'])
                if item['date'] in seen:fail('INVALID_HOURS','特別営業日が重複しています')
                seen.add(item['date'])
            if not isinstance(data['holiday_dates'],list) or len(data['holiday_dates'])>400:fail('INVALID_HOURS','祝日カレンダーが不正です')
            for value in data['holiday_dates']:day(value)
            if len(set(data['holiday_dates']))!=len(data['holiday_dates']):fail('INVALID_HOURS','祝日が重複しています')
            if not isinstance(data['cities'],list) or len(data['cities'])>47:fail('INVALID_SERVICE','運行地域が不正です')
            for city in data['cities']:
                exact(city,['prefecture_code','prefecture_name','municipalities']);text(city['prefecture_code'],2);text(city['prefecture_name'],40)
                if not re.fullmatch(r'\d{2}',city['prefecture_code']):fail('INVALID_SERVICE','都道府県コードが不正です')
                if not isinstance(city['municipalities'],list) or len(city['municipalities'])>200:fail('INVALID_SERVICE','市区町村が不正です')
                for m in city['municipalities']:
                    exact(m,['code','name']);text(m['code'],6);text(m['name'],80)
                    if not re.fullmatch(r'\d{5,6}',m['code']):fail('INVALID_SERVICE','市区町村コードが不正です')
            dependencies=[r['id'] for r in self.terms(db,actor,data['service_id'])]
        elif kind=='stop_configure':
            exact(data,['stop_id','location','start_datetime','end_datetime','pictures'])
            stop=db.execute('SELECT * FROM stops WHERE id=?',(text(data['stop_id'],100),)).fetchone()
            if not stop:fail('NOT_FOUND','乗降場所が見つかりません',404)
            self.own_service(db,actor,stop['service_id']);dates(data)
            exact(data['location'],['type','coordinates']);geojson_point_to_gtfs(data['location'])
            if not isinstance(data['pictures'],list) or len(data['pictures'])>10:fail('INVALID_PICTURES','写真の指定が不正です')
            for picture in data['pictures']:
                if not isinstance(picture,dict) or 'url' not in picture or set(picture)-{'url','title','description'}:fail('INVALID_PICTURES','写真の項目が不正です')
                https_url(picture['url'])
                for k in ('title','description'):
                    if k in picture:text(picture[k],500)
            old=db.execute('SELECT version FROM stop_profiles WHERE stop_id=?',(data['stop_id'],)).fetchone();version=old[0] if old else 0
        else:fail('INVALID_ACTION','未対応の台帳操作です')
        return {'input':data,'version':version,'dependencies':dependencies}
    def apply(self,db,actor,kind,details):
        if kind=='payment_update':return self.core.payments.apply(db,actor,details)
        if kind in ('observation_configure','observation_publish'):return self.core.observations.apply(db,actor,kind,details)
        if kind in {'route_configure','offer_open','offer_close'}:return self.core.booking.catalog_apply(db,actor,kind,details)
        data=details['input'];now=iso(self.core.clock());resource_id=actor['id'];resource_type='passenger'
        if kind in ('profile_create','profile_update'):
            if kind=='profile_create':db.execute('INSERT INTO passengers VALUES (?,?,?,?,?)',(actor['id'],actor['tenant_id'],packed(data),now,now))
            else:db.execute('UPDATE passengers SET profile_json=?,updated_at=? WHERE id=?',(packed(data),now,actor['id']))
            db.execute('INSERT INTO passenger_versions VALUES (?,?) ON CONFLICT(actor_id) DO UPDATE SET version=excluded.version',(actor['id'],details['version']+1))
            value=self.passenger_view(self.own_passenger(db,actor,actor['id']))
        elif kind=='profile_delete':
            # Physical row deletion cascades to agreements; purge cached personal data.
            db.execute('DELETE FROM passengers WHERE id=?',(actor['id'],))
            db.execute('UPDATE passenger_versions SET version=version+1 WHERE actor_id=?',(actor['id'],))
            db.execute('DELETE FROM drafts WHERE actor_id=?',(actor['id'],))
            db.execute('DELETE FROM client_grants WHERE actor_id=?',(actor['id'],))
            db.execute('DELETE FROM sessions WHERE actor_id=?',(actor['id'],))
            db.execute("UPDATE catalog_operations SET result_json='null',redacted=1 WHERE actor_id=? AND resource_type IN ('passenger','agreements')",(actor['id'],))
            value=None
        elif kind=='agreements_register':
            resource_type='agreements';result=[]
            for item in data['agreements']:
                inserted=db.execute('INSERT OR IGNORE INTO agreements VALUES (?,?,?,?)',(actor['id'],item['terms_id'],item['agreed_at'],now)).rowcount
                row=db.execute('SELECT a.*,t.category,t.service_id FROM agreements a JOIN terms t ON t.id=a.terms_id WHERE a.passenger_id=? AND a.terms_id=?',(actor['id'],item['terms_id'])).fetchone()
                result.append({**self.agreement_view(row),'status':'created' if inserted else 'already_agreed'})
            value={'agreements':result}
        elif kind=='terms_publish':
            resource_type='term';resource_id=uid('terms')
            db.execute('UPDATE terms SET active=0 WHERE tenant_id=? AND service_id IS ? AND category=? AND active=1',(actor['tenant_id'],data['service_id'],data['category']))
            db.execute('INSERT INTO terms VALUES (?,?,?,?,?,?,?,1,?)',(resource_id,actor['tenant_id'],data['service_id'],data['category'],data['name'],data['url'],int(data['agreement_required']),now))
            db.execute('UPDATE services SET revision=revision+1 WHERE tenant_id=?'+(' AND id=?' if data['service_id'] else ''),(actor['tenant_id'],*([data['service_id']] if data['service_id'] else [])))
            value=self.term_view(db.execute('SELECT * FROM terms WHERE id=?',(resource_id,)).fetchone())
        elif kind=='service_configure':
            resource_type='service';resource_id=data['service_id']
            db.execute('INSERT INTO service_profiles VALUES (?,?,?) ON CONFLICT(service_id) DO UPDATE SET data_json=excluded.data_json,updated_at=excluded.updated_at',(resource_id,packed(data),now))
            db.execute('UPDATE services SET revision=revision+1 WHERE id=?',(resource_id,));value=self.service_view(db,actor,self.own_service(db,actor,resource_id),True)
        elif kind=='stop_configure':
            resource_type='stop';resource_id=data['stop_id']
            db.execute('INSERT INTO stop_profiles VALUES (?,?,?,?) ON CONFLICT(stop_id) DO UPDATE SET data_json=excluded.data_json,version=excluded.version,updated_at=excluded.updated_at',(resource_id,packed(data),details['version']+1,now))
            db.execute('UPDATE services SET revision=revision+1 WHERE id=(SELECT service_id FROM stops WHERE id=?)',(resource_id,))
            value=self.stop_view(db,db.execute('SELECT * FROM stops WHERE id=?',(resource_id,)).fetchone())
        return {'resource_type':resource_type,'id':resource_id,'value':value,'deleted':kind=='profile_delete'}
    def current(self,db,actor,row):
        kind,target=row['resource_type'],row['resource_id']
        if kind=='payment':return self.core.payments.resource(db,actor,target)
        if kind in ('observation_source','observation'):return self.core.observations.resource(db,actor,target,kind)
        if row['redacted']:return {'resource_type':kind,'id':target,'value':None,'deleted':True,'redacted':True}
        value=None
        if kind=='passenger':
            r=db.execute('SELECT * FROM passengers WHERE id=? AND tenant_id=?',(target,actor['tenant_id'])).fetchone()
            if r:value=self.passenger_view(r)
        elif kind=='agreements':
            if db.execute('SELECT 1 FROM passengers WHERE id=?',(target,)).fetchone():value={'agreements':[self.agreement_view(r) for r in self.agreement_rows(db,actor)]}
        elif kind=='term':
            r=db.execute('SELECT * FROM terms WHERE id=? AND tenant_id=?',(target,actor['tenant_id'])).fetchone()
            if r:value=self.term_view(r)
        elif kind=='service':value=self.service_view(db,actor,self.own_service(db,actor,target),True)
        elif kind=='stop':value=self.stop_view(db,db.execute('SELECT * FROM stops WHERE id=?',(target,)).fetchone())
        elif kind=='route':
            r=db.execute('SELECT rp.data_json FROM route_policies rp JOIN services s ON s.id=rp.service_id WHERE rp.id=? AND s.tenant_id=?',(target,actor['tenant_id'])).fetchone()
            if r:value=json.loads(r[0])
        elif kind=='dispatch_offer':value=self.core.booking.offer_view(self.core.booking.own_offer(db,actor,target))
        return {'resource_type':kind,'id':target,'value':value,'deleted':value is None}
    def service_view(self,db,actor,service,detail=False):
        row=db.execute('SELECT * FROM service_profiles WHERE service_id=?',(service['id'],)).fetchone()
        if not row:fail('SERVICE_MASTER_INCOMPLETE','サービスの有効期間・営業日等が未設定です',503)
        data=json.loads(row['data_json']);policy=json.loads(service['policy_json'])
        result={'id':service['id'],'name':service['name'],'access_scope':data['access_scope'],'operation_type':'on_demand','allow_ridepooling':True,
            'start_datetime':data['start_datetime'],'cities':data['cities'],'service_terms':[self.term_view(t) for t in self.terms(db,actor,service['id'])],
            'available_passenger_types':[{'passenger_type_id':'mdl-synthetic-general','name':'一般（合成テスト区分）'}],
            'supported_accessibility_features':[],'operating_hours':data['operating_hours'],'special_operating_hours':data['special_operating_hours'],'announcements':[]}
        if data['end_datetime'] is not None:result['end_datetime']=data['end_datetime']
        if detail:result.update({'operation_settings':{'time_specifiable':{'departure':False,'arrival':False},'max_advance_reservable_days':0,'min_advance_reservable_minutes':0,'cancel_deadline_minutes':0,'search_passenger_limit':policy['max_passengers'],'search_accessibility_limit':0,'reservable_location_types':['fixed_stop']},'reservable_areas':[],'area_transitions':{'areas':[],'rules':[]},'updated_at':row['updated_at']})
        return result
    def stop_view(self,db,stop):
        row=db.execute('SELECT * FROM stop_profiles WHERE stop_id=?',(stop['id'],)).fetchone()
        if not row:fail('STOP_COORDINATES_NOT_CONFIGURED','乗降場所の座標・有効期間が未設定です',503)
        data=json.loads(row['data_json'])
        result={'id':stop['id'],'service_ids':[stop['service_id']],'name':stop['name'],'location':data['location'],'start_datetime':data['start_datetime'],
            'is_boarding_available':bool(stop['active']),'is_alighting_available':bool(stop['active']),'suspensions':[],'pictures':data['pictures'],'updated_at':row['updated_at']}
        if data['end_datetime'] is not None:result['end_datetime']=data['end_datetime']
        return result
    def state(self,data):
        if timestamp(data['start_datetime'])>self.core.clock():return 'upcoming'
        if data.get('end_datetime') and timestamp(data['end_datetime'])<=self.core.clock():return 'ended'
        return 'active'
    def read(self,actor_id,kind,target=None,params=None,authorization=None):
        params=params or {}
        with self.core.db() as db:
            actor=self.core.actor(db,actor_id);self.core.check_authorization(db,actor_id,authorization)
            if kind=='passenger':return self.passenger_view(self.own_passenger(db,actor,target))
            if kind=='agreements':
                self.own_passenger(db,actor,target)
                return {'agreements':[self.agreement_view(r) for r in self.agreement_rows(db,actor,params.get('service_id'))]}
            if kind=='terms':return {'terms':[self.term_view(r) for r in self.terms(db,actor,None,params.get('category'))]}
            if kind=='service':return self.service_view(db,actor,self.own_service(db,actor,target),True)
            if kind in ('services','eligible_services','stops'):
                if kind=='eligible_services':self.own_passenger(db,actor,target)
                items=[]
                if kind in ('services','eligible_services'):
                    rows=db.execute('SELECT * FROM services WHERE tenant_id=? AND active=1 ORDER BY id',(actor['tenant_id'],))
                    for s in rows:
                        if kind=='eligible_services' and not actor['eligible']:continue
                        if params.get('service_ids') is not None and s['id'] not in params['service_ids']:continue
                        if params.get('name') is not None and params['name'].casefold() not in s['name'].casefold():continue
                        item=self.service_view(db,actor,s)
                        if self.state(item) not in params.get('status',['upcoming','active']):continue
                        cities=[c for c in item['cities'] if not params.get('prefecture_code') or c['prefecture_code']==params['prefecture_code']]
                        if params.get('prefecture_code') and not cities:continue
                        if params.get('municipality_code') and not any(m['code']==params['municipality_code'] for c in cities for m in c['municipalities']):continue
                        items.append(item)
                    key='services'
                else:
                    rows=db.execute('SELECT st.* FROM stops st JOIN services s ON s.id=st.service_id WHERE s.tenant_id=? ORDER BY st.id',(actor['tenant_id'],))
                    point=None
                    if 'location' in params:
                        try:point=[float(x) for x in params['location'].split(',')]
                        except (ValueError,AttributeError):fail('INVALID_COORDINATES','検索位置が不正です')
                        geojson_point_to_gtfs({'type':'Point','coordinates':point})
                    if 'radius' in params and point is None and params['radius']!=500:fail('INVALID_QUERY','半径検索には位置を指定してください')
                    for s in rows:
                        if 'stop_ids' in params and s['id'] not in params['stop_ids']:continue
                        if 'service_ids' in params and s['service_id'] not in params['service_ids']:continue
                        if 'name' in params and params['name'].casefold() not in s['name'].casefold():continue
                        item=self.stop_view(db,s)
                        if self.state(item) not in params.get('status',['upcoming','active']):continue
                        if point is not None:
                            lon,lat=map(math.radians,point);lon2,lat2=map(math.radians,item['location']['coordinates'])
                            distance=12742000*math.asin(min(1,math.sqrt(math.sin((lat2-lat)/2)**2+math.cos(lat)*math.cos(lat2)*math.sin((lon2-lon)/2)**2)))
                            if distance>params.get('radius',500):continue
                        items.append(item)
                    key='stops'
                offset,limit=params.get('offset',0),params.get('limit',20)
                if type(offset) is not int or offset<0 or type(limit) is not int or not 1<=limit<=100:fail('INVALID_PAGINATION','ページ指定が不正です')
                return {key:items[offset:offset+limit],'total':len(items),'offset':offset,'limit':limit}
            fail('NOT_FOUND','未対応の照会です',404)
    def check_request(self,db,actor,service):
        passenger=db.execute('SELECT 1 FROM passengers WHERE id=?',(actor['id'],)).fetchone()
        required=list(db.execute('SELECT id FROM terms WHERE tenant_id=? AND active=1 AND agreement_required=1 AND (service_id IS NULL OR service_id=?)',(actor['tenant_id'],service['id'])))
        row=db.execute('SELECT data_json FROM service_profiles WHERE service_id=?',(service['id'],)).fetchone()
        if (required or self.version(db,actor['id'])>0 or (row and json.loads(row[0])['access_scope']=='registered_user_only')) and not passenger:
            fail('PROFILE_REQUIRED','利用者情報を登録してください',409)
        agreed={r[0] for r in db.execute('SELECT terms_id FROM agreements WHERE passenger_id=?',(actor['id'],))}
        if any(r['id'] not in agreed for r in required):fail('AGREEMENT_REQUIRED','最新の利用規約を確認し、同意してください',409)
        if row:
            data=json.loads(row[0])
            if self.state(data)!='active':fail('SERVICE_CLOSED','サービスの有効期間外です',409)
            now=datetime.fromtimestamp(self.core.clock(),ZoneInfo(service['timezone']))
            for delta in (0,1):
                day_value=now.date()-timedelta(days=delta)
                daily=daily_slots(data,day_value)
                seconds=now.hour*3600+now.minute*60+now.second+delta*86400
                if any(x['start_time_offset_sec']<=seconds<x['end_time_offset_sec'] for x in daily):return True
            fail('SERVICE_CLOSED','運行時間外です',409)
        return False
    def check_stop(self,db,stop):
        row=db.execute('SELECT data_json FROM stop_profiles WHERE stop_id=?',(stop['id'],)).fetchone()
        if row and self.state(json.loads(row[0]))!='active':fail('INVALID_STOP','この乗降場所は有効期間外です',409)
    def snapshot(self,actor_id,authorization=None):
        with self.core.db() as db:
            actor=self.core.actor(db,actor_id)
            self.core.check_authorization(db,actor_id,authorization)
            p=db.execute('SELECT * FROM passengers WHERE id=?',(actor_id,)).fetchone() if actor['role']=='rider' else None
            terms=list(db.execute('SELECT * FROM terms WHERE tenant_id=? AND active=1 ORDER BY service_id,category',(actor['tenant_id'],)))
            return {'passenger':self.passenger_view(p) if p else None,
                'terms':[{**self.term_view(r),'service_id':r['service_id']} for r in terms],
                'agreements':[self.agreement_view(r) for r in self.agreement_rows(db,actor)] if p else [],
                'mode':'local_synthetic'}
