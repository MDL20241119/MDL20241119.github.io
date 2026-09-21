"""Immediate fixed-stop candidates from explicitly configured, driver-offered runs.

Times are plans, never GPS observations. Search does not reserve seats. Core
calls booking under the same transaction as authorization, seats and Outbox.
"""
import json
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from .core import exact,fail,iso,packed,uid,DomainError
from .catalog import text,timestamp
from .service_calendar import operating_windows

CATALOG_KINDS={'route_configure','offer_open','offer_close'}
PASSENGER_TYPE='mdl-synthetic-general'

class Booking:
    def __init__(self,core):self.core=core
    def route(self,db,actor,data):
        for key in ('service_id','origin_stop_id','destination_stop_id'):text(data[key],100)
        service=self.core.catalog.own_service(db,actor,data['service_id'])
        row=db.execute('SELECT * FROM route_policies WHERE service_id=? AND origin_stop_id=? AND destination_stop_id=?',
            (service['id'],data['origin_stop_id'],data['destination_stop_id'])).fetchone()
        if not row:fail('ROUTE_TIMING_NOT_CONFIGURED','この乗降場所間の所要時間・受付条件が未設定です',503)
        return service,row,json.loads(row['data_json'])
    def context(self,db,actor,data):
        service,route,policy=self.route(db,actor,data)
        if not service['active']:fail('SERVICE_UNAVAILABLE','このサービスは停止中です',409)
        self.core.catalog.service_view(db,actor,service)
        points={}
        for key in ('origin_stop_id','destination_stop_id'):
            stop=db.execute('SELECT * FROM stops WHERE id=? AND service_id=?',(data[key],service['id'])).fetchone()
            if not stop:fail('INVALID_STOP','同じサービスの指定乗降場所が必要です')
            if not stop['active']:fail('STOP_SUSPENDED','この乗降場所は休止中です',409)
            points[key]=self.core.catalog.stop_view(db,stop)
        return {'service_revision':service['revision'],'route_id':route['id'],'route_version':route['version'],
            'origin':points['origin_stop_id'],'destination':points['destination_stop_id'],'policy':policy},service
    def interval(self,db,service,context,pickup,dropoff):
        row=db.execute('SELECT data_json FROM service_profiles WHERE service_id=?',(service['id'],)).fetchone()
        if not row:fail('SERVICE_MASTER_INCOMPLETE','営業日・期間が未設定です',503)
        data=json.loads(row[0]);zone=ZoneInfo(service['timezone'])
        def within(value,at):
            return timestamp(value['start_datetime'])<=at and (not value.get('end_datetime') or at<timestamp(value['end_datetime']))
        if not within(data,pickup) or not within(data,dropoff):fail('SERVICE_CLOSED','計画時刻がサービス有効期間外です',409)
        if not within(context['origin'],pickup) or not within(context['destination'],dropoff):fail('STOP_SUSPENDED','計画時刻に利用できない乗降場所です',409)
        # One operating window must contain the whole planned ride, including 24h+.
        local=datetime.fromtimestamp(pickup,zone)
        merged=operating_windows(data,local.date()-timedelta(days=1),local.date()+timedelta(days=1),service['timezone'])
        if any(start<=pickup and dropoff<end for start,end in merged):return
        fail('SERVICE_CLOSED','計画した乗車から降車までを営業時間内に収めてください',409)
    def own_offer(self,db,actor,run_id,driver=False):
        text(run_id,100)
        row=db.execute('SELECT o.*,r.vehicle_id,r.origin_stop_id,r.destination_stop_id,r.reserved,r.accepting,r.active FROM run_offers o JOIN runs r ON r.id=o.run_id JOIN services s ON s.id=o.service_id WHERE o.run_id=? AND s.tenant_id=?',(run_id,actor['tenant_id'])).fetchone()
        if not row or (driver and row['driver_id']!=actor['id']):fail('NOT_FOUND','担当の提示便が見つかりません',404)
        return row
    def offer_view(self,row):
        plan=json.loads(row['plan_json'])
        return {'id':row['run_id'],'service_id':row['service_id'],'vehicle_id':row['vehicle_id'],'vehicle_name':plan['vehicle_name'],
            'origin_stop_id':row['origin_stop_id'],'destination_stop_id':row['destination_stop_id'],
            'origin_name':plan['context']['origin']['name'],'destination_name':plan['context']['destination']['name'],
            'pickup_at':plan['pickup_at'],'dropoff_at':plan['dropoff_at'],'reserved':row['reserved'],
            'accepting':bool(row['accepting'] and row['active'] and timestamp(plan['pickup_at'])>self.core.clock()),
            'active':bool(row['active']),'can_close':bool(row['active'] and row['accepting']),'version':row['version'],'basis':'synthetic_plan_not_observation'}
    def catalog_prepare(self,db,actor,kind,data):
        if kind=='route_configure':
            exact(data,['service_id','origin_stop_id','destination_stop_id','travel_seconds','max_wait_seconds','basis'])
            service=self.core.catalog.own_service(db,actor,data['service_id'])
            for key in ('origin_stop_id','destination_stop_id'):
                text(data[key],100)
                if not db.execute('SELECT 1 FROM stops WHERE id=? AND service_id=?',(data[key],service['id'])).fetchone():fail('INVALID_STOP','同じサービスの指定乗降場所が必要です')
            if data['origin_stop_id']==data['destination_stop_id']:fail('SAME_STOP','乗降場所を分けてください')
            if any(type(data[k]) is not int or not 60<=data[k]<=7200 for k in ('travel_seconds','max_wait_seconds')) or data['basis']!='synthetic_test_only':
                fail('INVALID_ROUTE_POLICY','架空試験用の所要時間・最大待ち時間は60〜7200秒で設定してください')
            row=db.execute('SELECT version FROM route_policies WHERE service_id=? AND origin_stop_id=? AND destination_stop_id=?',(service['id'],data['origin_stop_id'],data['destination_stop_id'])).fetchone()
            return {'input':data,'version':row[0] if row else 0,'dependencies':[service['revision']]}
        if kind=='offer_open':
            exact(data,['service_id','origin_stop_id','destination_stop_id','pickup_at','vehicle_name','stopped'])
            if data['stopped'] is not True:fail('STOP_REQUIRED','安全な場所に停車してから提示してください',409)
            text(data['vehicle_name'],100)
            context,service=self.context(db,actor,data)
            pickup=timestamp(data['pickup_at']);dropoff=pickup+context['policy']['travel_seconds']
            if not self.core.clock()<pickup<=self.core.clock()+context['policy']['max_wait_seconds']:
                fail('INVALID_PICKUP_TIME','計画乗車時刻を現在より後・最大待ち時間以内にしてください',409)
            self.interval(db,service,context,pickup,dropoff)
            vehicle=db.execute('SELECT * FROM vehicles WHERE driver_id=? AND tenant_id=? AND service_id=? AND active=1',(actor['id'],actor['tenant_id'],service['id'])).fetchone()
            if not vehicle:fail('NO_VEHICLE','担当車両がありません',409)
            if db.execute('SELECT 1 FROM runs WHERE vehicle_id=? AND active=1',(vehicle['id'],)).fetchone():fail('VEHICLE_BUSY','進行中または提示中の便があります',409)
            plan={'context':context,'pickup_at':iso(pickup),'dropoff_at':iso(dropoff),'vehicle_name':data['vehicle_name'],
                'vehicle_id':vehicle['id'],'capacity':vehicle['capacity'],'driver_id':actor['id']}
            return {'input':data,'version':0,'dependencies':[plan]}
        exact(data,['offer_id','stopped'])
        if data['stopped'] is not True:fail('STOP_REQUIRED','停車してから受付を終了してください',409)
        offer=self.own_offer(db,actor,data['offer_id'],True)
        if not offer['active'] or not offer['accepting']:fail('OFFER_CLOSED','この便は受付終了済みです',409)
        return {'input':data,'version':offer['version'],'dependencies':[offer['reserved']]}
    def catalog_apply(self,db,actor,kind,details):
        data=details['input'];now=iso(self.core.clock())
        if kind=='route_configure':
            row=db.execute('SELECT id FROM route_policies WHERE service_id=? AND origin_stop_id=? AND destination_stop_id=?',(data['service_id'],data['origin_stop_id'],data['destination_stop_id'])).fetchone()
            target=row[0] if row else uid('route')
            db.execute('INSERT INTO route_policies VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET data_json=excluded.data_json,version=excluded.version,updated_at=excluded.updated_at',
                (target,data['service_id'],data['origin_stop_id'],data['destination_stop_id'],packed(data),details['version']+1,now))
            db.execute('UPDATE services SET revision=revision+1 WHERE id=?',(data['service_id'],))
            return {'resource_type':'route','id':target,'value':data,'deleted':False}
        if kind=='offer_open':
            target=uid('run');plan=details['dependencies'][0]
            db.execute('INSERT INTO runs(id,vehicle_id,origin_stop_id,destination_stop_id) VALUES (?,?,?,?)',(target,plan['vehicle_id'],data['origin_stop_id'],data['destination_stop_id']))
            db.execute('INSERT INTO run_offers VALUES (?,?,?,?,1,?)',(target,actor['id'],data['service_id'],packed(plan),now))
        else:
            target=data['offer_id']
            db.execute('UPDATE runs SET accepting=0,active=CASE WHEN reserved=0 THEN 0 ELSE active END WHERE id=?',(target,))
            db.execute('UPDATE run_offers SET version=version+1 WHERE run_id=?',(target,))
        return {'resource_type':'dispatch_offer','id':target,'value':self.offer_view(self.own_offer(db,actor,target)),'deleted':False}
    def search(self,actor_id,data,authorization=None):
        exact(data,['service_id','origin_stop_id','destination_stop_id','passengers','preferred_pickup_at','vehicle_id'])
        for key in ('service_id','origin_stop_id','destination_stop_id'):text(data[key],100)
        preferred=timestamp(data['preferred_pickup_at']);now=self.core.clock()
        if not now-60<=preferred<=now+60:fail('FUTURE_SEARCH_UNSUPPORTED','この試験サービスは現在時点の呼出のみ対応しています')
        if data['vehicle_id'] is not None:text(data['vehicle_id'],100)
        with self.core.db(True) as db:
            actor=self.core.actor(db,actor_id,'rider');self.core.check_authorization(db,actor_id,authorization)
            self.core.catalog.own_passenger(db,actor,actor_id)
            if data['vehicle_id'] is not None and not db.execute('SELECT 1 FROM vehicles WHERE id=? AND tenant_id=? AND service_id=?',(data['vehicle_id'],actor['tenant_id'],data['service_id'])).fetchone():
                fail('NOT_FOUND','このサービスの車両が見つかりません',404)
            request={k:data[k] for k in ['service_id','origin_stop_id','destination_stop_id','passengers']}
            empty=lambda reason,detail:{'candidates':[],'no_candidate_reason':reason,'availability_reason':detail}
            try:
                context,service=self.context(db,actor,request)
                details=self.core.request_details(db,actor,request)
            except DomainError as error:
                if error.code=='STOP_SUSPENDED':return empty('stops_is_suspended','stops_suspended')
                if error.code=='SERVICE_CLOSED':return empty('no_operation_plans','service_closed')
                raise
            fare=details['fare']
            if type(fare.get('amount')) is not int or not 0<=fare['amount']<=2147483647 or fare.get('currency')!='JPY':fail('FARE_NOT_CONFIGURED','確定可能な日本円の運賃が未設定です',503)
            offers=list(db.execute('SELECT o.run_id FROM run_offers o JOIN runs r ON r.id=o.run_id WHERE o.service_id=? AND r.origin_stop_id=? AND r.destination_stop_id=? AND r.active=1 AND r.accepting=1 ORDER BY o.run_id',(service['id'],data['origin_stop_id'],data['destination_stop_id'])))
            candidates=[];available=0
            for item in offers:
                offer=self.own_offer(db,actor,item['run_id']);plan=json.loads(offer['plan_json']);pickup=timestamp(plan['pickup_at'])
                if data['vehicle_id'] is not None and offer['vehicle_id']!=data['vehicle_id']:continue
                if not now<pickup<=now+context['policy']['max_wait_seconds']:continue
                vehicle=db.execute("SELECT v.* FROM vehicles v JOIN users u ON u.id=v.driver_id WHERE v.id=? AND v.active=1 AND u.active=1 AND u.role='driver' AND v.tenant_id=? AND u.tenant_id=? AND v.service_id=?",(offer['vehicle_id'],actor['tenant_id'],actor['tenant_id'],service['id'])).fetchone()
                if not vehicle:continue
                if plan['context']!=context or vehicle['capacity']!=plan['capacity'] or vehicle['driver_id']!=plan['driver_id']:
                    fail('OFFER_SETTINGS_CHANGED','提示後に運行条件が変わりました。ドライバーの再提示が必要です',409)
                self.interval(db,service,context,pickup,timestamp(plan['dropoff_at']));available+=1
                if offer['reserved']+data['passengers']>vehicle['capacity']:continue
                target=uid('candidate');expiry=min(now+120,pickup)
                value={'id':target,'offer_id':offer['run_id'],**details,'pickup_at':plan['pickup_at'],'dropoff_at':plan['dropoff_at'],
                    'pickup_location':context['origin']['location'],'dropoff_location':context['destination']['location'],
                    'vehicle_id':vehicle['id'],'vehicle_name':plan['vehicle_name'],'vehicle_capacity':vehicle['capacity'],
                    'offer_version':offer['version'],'profile_version':self.core.catalog.version(db,actor_id),
                    'expires_at':iso(expiry),'basis':'synthetic_plan_not_observation'}
                db.execute('INSERT INTO candidates VALUES (?,?,?,?,?,?,NULL,?)',(target,actor_id,actor['tenant_id'],offer['run_id'],packed(value),expiry,iso(now)))
                candidates.append(value)
            return {'candidates':candidates,'no_candidate_reason':None if candidates else ('no_candidate' if available else 'no_operation_plans'),
                'availability_reason':None if candidates else ('capacity_full' if available else 'no_active_offers')}
    def candidate(self,db,actor,candidate_id):
        text(candidate_id,100)
        row=db.execute('SELECT * FROM candidates WHERE id=? AND passenger_id=? AND tenant_id=?',(candidate_id,actor['id'],actor['tenant_id'])).fetchone()
        if not row:fail('CANDIDATE_NOT_FOUND','本人の候補が見つかりません',404)
        return row,json.loads(row['data_json'])
    def prepare(self,db,actor,data):
        exact(data,['candidate_id']);row,value=self.candidate(db,actor,data['candidate_id'])
        if row['used_ride_id']:fail('CANDIDATE_USED','この候補は予約済みです。元の操作IDで確認してください',409)
        if row['expires_at']<=self.core.clock():fail('CANDIDATE_EXPIRED','候補の期限が切れました。検索し直してください',409)
        if value['profile_version']!=self.core.catalog.version(db,actor['id']):fail('CANDIDATE_CHANGED','利用者情報が変わりました。検索し直してください',409)
        fresh=self.core.request_details(db,actor,{k:value[k] for k in ['service_id','origin_stop_id','destination_stop_id','passengers']})
        if any(fresh[k]!=value[k] for k in fresh):fail('CANDIDATE_CHANGED','運賃・規約・運行条件が変わりました。検索し直してください',409)
        offer=self.own_offer(db,actor,value['offer_id']);plan=json.loads(offer['plan_json'])
        if offer['version']!=value['offer_version'] or not offer['active'] or not offer['accepting']:fail('OFFER_CLOSED','この便は受付を終了しました',409)
        context,service=self.context(db,actor,value)
        if context!=plan['context']:fail('CANDIDATE_CHANGED','乗降場所や所要時間が変わりました',409)
        vehicle=db.execute('SELECT * FROM vehicles WHERE id=? AND active=1',(value['vehicle_id'],)).fetchone()
        if not vehicle or vehicle['driver_id']!=plan['driver_id'] or vehicle['capacity']!=value['vehicle_capacity'] or vehicle['tenant_id']!=actor['tenant_id'] or vehicle['service_id']!=value['service_id']:fail('CANDIDATE_CHANGED','担当車両が変わりました',409)
        driver=self.core.actor(db,vehicle['driver_id'],'driver')
        if driver['tenant_id']!=actor['tenant_id']:fail('CANDIDATE_CHANGED','担当事業者が変わりました',409)
        self.interval(db,service,context,timestamp(value['pickup_at']),timestamp(value['dropoff_at']))
        if offer['reserved']+value['passengers']>vehicle['capacity']:fail('CAPACITY_FULL','候補表示後に空席がなくなりました。検索し直してください',409)
        return value
    def book(self,db,actor,details):
        if self.prepare(db,actor,{'candidate_id':details['id']})!=details:fail('CANDIDATE_CHANGED','候補が変わりました',409)
        offer=self.own_offer(db,actor,details['offer_id']);ride_id=uid('ride');now=iso(self.core.clock())
        self.core.reserve_seats(db,offer['run_id'],details['passengers'])
        db.execute('INSERT INTO rides(id,tenant_id,rider_id,service_id,origin_stop_id,destination_stop_id,passengers,fare_json,status,vehicle_id,driver_id,run_id,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (ride_id,actor['tenant_id'],actor['id'],details['service_id'],details['origin_stop_id'],details['destination_stop_id'],details['passengers'],packed(details['fare']),'assigned',details['vehicle_id'],offer['driver_id'],offer['run_id'],now,now))
        db.execute('INSERT INTO ride_bookings VALUES (?,?,?)',(ride_id,details['id'],packed(details)))
        db.execute('UPDATE candidates SET used_ride_id=? WHERE id=?',(ride_id,details['id']))
        return ride_id
    def change_check(self,db,actor,ride):
        row=db.execute('SELECT data_json FROM ride_bookings WHERE ride_id=?',(ride['id'],)).fetchone()
        if not row:return
        value=json.loads(row[0])
        if timestamp(value['pickup_at'])<=self.core.clock():fail('OFFER_CLOSED','計画乗車時刻を過ぎたため変更できません',409)
        context,_=self.context(db,actor,value);offer=self.own_offer(db,actor,value['offer_id'])
        if context!=json.loads(offer['plan_json'])['context']:fail('CANDIDATE_CHANGED','予約後に運行条件が変わりました。運営担当者へ確認してください',409)
    def offers(self,db,actor):
        if actor['role'] not in ('driver','admin'):return []
        rows=db.execute('SELECT o.run_id FROM run_offers o JOIN runs r ON r.id=o.run_id JOIN services s ON s.id=o.service_id WHERE s.tenant_id=? AND r.active=1'+(' AND o.driver_id=?' if actor['role']=='driver' else ''),(actor['tenant_id'],*([actor['id']] if actor['role']=='driver' else [])))
        return [self.offer_view(self.own_offer(db,actor,r[0])) for r in rows]
