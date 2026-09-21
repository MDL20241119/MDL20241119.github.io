"""Partial MLIT adapter: conversion only; every business operation uses Core.

All 19 source operations remain indexed. Unimplemented operations explicitly
fail, never return fake empty lists or invented coordinates and timings.
"""
from .core import fail, packed, exact
from .mlit_contract import Contract
from datetime import datetime
from zoneinfo import ZoneInfo

STATE={"requested":"tentative","assigned":"confirmed","arrived":"confirmed","onboard":"in_transit","completed":"completed","cancelled":"cancelled"}
PASSENGER_TYPE="mdl-synthetic-general"
READS={'getTerms':'terms','getServices':'services','getServicesId':'service','getPassengersId':'passenger',
       'getPassengersIdServices':'eligible_services','getPassengersIdAgreements':'agreements','getStops':'stops'}
WRITES={'postPassengers':('profile_create',201),'putPassengersId':('profile_update',200),
        'deletePassengersId':('profile_delete',204),'postPassengersIdAgreements':('agreements_register',200)}
SUPPORTED={"getPassengersIdReservations","putReservationsId","postReservationsCandidates","postReservations","getReservationsIdPayment","putReservationsIdPayment","getVehicleLocations","getOperationDelays"}|set(READS)|set(WRITES)
BLOCKERS={}

def payment(view):
    # The standard description says no independent subresource ID, while its
    # response requires id. Bind it deterministically to the reservation ID.
    return {k:view['record'][k] for k in ('id','amount','payment_status','created_at','updated_at')}

def reservation(view):
    fare=view["fare"]
    if type(fare.get("amount")) is not int or fare["amount"]<0 or fare.get("currency")!="JPY":
        fail("FARE_NOT_CONFIGURED","標準形式に変換できる確定運賃がありません",503)
    result={"id":view["id"],"passenger_id":view["rider_id"],"status":STATE[view["status"]],"service_id":view["service_id"],
        "pickup":{"type":"fixed_stop","stop_id":view["origin_stop_id"],"display_name":view["origin_name"]},
        "dropoff":{"type":"fixed_stop","stop_id":view["destination_stop_id"],"display_name":view["destination_name"]},
        "passenger_count":[{"passenger_type_id":PASSENGER_TYPE,"count":view["passengers"]}],"accessibility_feature_count":[],
        "fare":{"per_passenger_type":[{"passenger_type_id":PASSENGER_TYPE,"subtotal":fare["amount"]}],"total":fare["amount"]},
        "created_at":view["created_at"],"updated_at":view["updated_at"]}
    if view.get('booking'):
        booking=view['booking']
        for key,side in [('pickup','pickup'),('dropoff','dropoff')]:
            result[key].update({'location':booking[side+'_location'],'datetime':booking[side+'_at']})
        result['vehicle']={'id':view['vehicle_id'],'name':booking['vehicle_name'],'capacity':{'seats':booking['vehicle_capacity'],'accessibility_features':[]}}
    # The official prose requires id AND name when vehicle is present. The
    # immediate-call ledger has no confirmed vehicle name; omit that optional
    # object rather than returning an incomplete or fabricated vehicle.
    # Only explicit booking plans add coordinates/times. No live observation or ETA is inferred.
    return result

def reservation_request(candidate,passenger_id=None):
    result={'candidate_id':candidate['id'],'service_id':candidate['service_id'],
        'pickup':{'type':'fixed_stop','stop_id':candidate['origin_stop_id'],'location':candidate['pickup_location'],'datetime':candidate['pickup_at']},
        'dropoff':{'type':'fixed_stop','stop_id':candidate['destination_stop_id'],'location':candidate['dropoff_location'],'datetime':candidate['dropoff_at']},
        'passenger_count':[{'passenger_type_id':PASSENGER_TYPE,'count':candidate['passengers']}],
        'accessibility_feature_count':[],'vehicle_id':candidate['vehicle_id']}
    if passenger_id is not None:result['passenger_id']=passenger_id
    return result

def candidate_response(result):
    items=[]
    for c in result['candidates']:
        items.append({'reservation_request':reservation_request(c),'display':{
            'pickup':{'display_name':c['origin_name']},'dropoff':{'display_name':c['destination_name']},
            'fare':{'per_passenger_type':[{'passenger_type_id':PASSENGER_TYPE,'subtotal':c['fare']['amount']}],'total':c['fare']['amount']},
            'vehicle':{'id':c['vehicle_id'],'name':c['vehicle_name'],'capacity':{'seats':c['vehicle_capacity'],'accessibility_features':[]}}}})
    return {'candidates':items,**({'no_candidate_reason':result['no_candidate_reason']} if not items else {})}

def candidate_query(body):
    exact(body,['service_ids','preferred_time','pickup','dropoff','passenger_count','accessibility_feature_count']+(['vehicle_id'] if 'vehicle_id' in body else []))
    if len(body['service_ids'])!=1:fail('MULTI_SERVICE_SEARCH_UNSUPPORTED','このローカル範囲では一つのサービスを指定してください')
    exact(body['preferred_time'],['type','datetime'])
    if body['preferred_time']['type']!='pickup':fail('SEARCH_TIME_UNSUPPORTED','このサービスは現在の乗車希望に対応しています')
    for key in ('pickup','dropoff'):
        if body[key].get('type')!='fixed_stop':fail('LOCATION_TYPE_UNSUPPORTED','このサービスは指定乗降場所のみ対応しています')
        exact(body[key],['type','stop_id'])
    if len(body['passenger_count'])!=1 or body['accessibility_feature_count']:
        fail('PASSENGER_TYPE_UNSUPPORTED','このローカル範囲では一般区分・設備指定なしのみ対応しています')
    person=body['passenger_count'][0];exact(person,['passenger_type_id','count'])
    if person['passenger_type_id']!=PASSENGER_TYPE:fail('PASSENGER_TYPE_UNSUPPORTED','未設定の乗客区分です')
    return {'service_id':body['service_ids'][0],'origin_stop_id':body['pickup']['stop_id'],'destination_stop_id':body['dropoff']['stop_id'],
        'passengers':person['count'],'preferred_pickup_at':body['preferred_time']['datetime'],'vehicle_id':body.get('vehicle_id')}

class MLIT:
    def __init__(self,core):
        self.core,self.contract=core,Contract()

    def execute(self,matched,query,body,actor,authorization,approved,headers):
        params=self.contract.request(matched,query,body)
        template,op,ids=matched
        operation=op["operationId"]
        if operation in ('getVehicleLocations','getOperationDelays'):
            return 200,self.core.observations.read(actor,'locations' if operation=='getVehicleLocations' else 'delays',params,authorization,standard=True)
        if operation=='getReservationsIdPayment':
            return 200,payment(self.core.payments.read(actor,ids['id'],authorization))
        if operation=='putReservationsIdPayment':
            exact(body,['amount','payment_status'])
            if not approved or approved['kind']!='payment_update':fail('APPROVAL_REQUIRED','管理者が確認した決済情報の個別委任が必要です',403)
            if headers.get('X-Operation-ID')!=approved['operation_id'] or headers.get('Idempotency-Key')!=approved['idempotency_key']:
                fail('APPROVAL_MISMATCH','承認された操作ID・再送キーが必要です',403)
            if packed(approved['payload']['details']['input'])!=packed({'ride_id':ids['id'],**body}):
                fail('APPROVAL_MISMATCH','対象予約・金額・状態が管理者の承認と一致しません',403)
            result=self.core.mutate(actor,approved['operation_id'],approved['idempotency_key'],'payment_update',approved['payload'],authorization)
            return 200,payment(result['result']['value'])
        if operation=='postReservationsCandidates':
            return 200,candidate_response(self.core.booking.search(actor,candidate_query(body),authorization))
        if operation=='postReservations':
            if body['passenger_id']!=actor:fail('FORBIDDEN','本人の予約だけを作成できます',403)
            if not approved or approved['kind']!='book':fail('APPROVAL_REQUIRED','選んだ候補に対する本人の個別承認が必要です',403)
            if headers.get('X-Operation-ID')!=approved['operation_id'] or headers.get('Idempotency-Key')!=approved['idempotency_key']:
                fail('APPROVAL_MISMATCH','承認された操作ID・再送キーが必要です',403)
            if packed(body)!=packed(reservation_request(approved['payload']['details'],actor)):
                fail('APPROVAL_MISMATCH','候補の時刻・場所・人数・車両が本人の承認と一致しません',403)
            result=self.core.mutate(actor,approved['operation_id'],approved['idempotency_key'],'book',approved['payload'],authorization)
            return 201,reservation(result['result'])
        if operation in BLOCKERS:
            fail(BLOCKERS[operation],"この標準操作は設定・実装が未完了です。必須工程として継続し、成功応答は返しません",503)
        if operation in READS:
            return 200,self.core.catalog.read(actor,READS[operation],ids.get('id'),params,authorization)
        if operation in WRITES:
            kind,status=WRITES[operation]
            if 'id' in ids and ids['id']!=actor:fail('FORBIDDEN','本人の利用者情報だけを扱えます',403)
            if not approved or approved['kind']!=kind:fail('APPROVAL_REQUIRED','本人が内容を確認した個別委任が必要です',403)
            if headers.get('X-Operation-ID')!=approved['operation_id'] or headers.get('Idempotency-Key')!=approved['idempotency_key']:
                fail('APPROVAL_MISMATCH','承認された操作ID・再送キーが必要です',403)
            if packed(approved['payload']['details']['input'])!=packed({} if body is None else body):
                fail('APPROVAL_MISMATCH','本文が本人の承認と一致しません',403)
            result=self.core.mutate(actor,approved['operation_id'],approved['idempotency_key'],kind,approved['payload'],authorization)
            return status,result['result']['value']
        if operation=="getPassengersIdReservations":
            if ids["id"]!=actor:
                fail("FORBIDDEN","本人の予約だけ取得できます",403)
            statuses=None
            if "status" in params:
                statuses=[k for k,v in STATE.items() if v in params["status"]]
                # no_show is a defined standard state but this Core never produces it.
                if not statuses:
                    result=self.core.list_rides(actor,params.get("offset",0),params.get("limit",20),authorization=authorization,owner_only=True)
                    return 200,{"reservations":[],"total":0,"offset":result["offset"],"limit":result["limit"]}
            if "pickup_date_from" in params or "pickup_date_to" in params:
                return 200,self.dated_reservations(actor,authorization,params,statuses)
            result=self.core.list_rides(actor,params.get("offset",0),params.get("limit",20),params.get("reservation_ids"),statuses,authorization,owner_only=True)
            return 200,{"reservations":[reservation(x) for x in result["rides"]],**{k:result[k] for k in ("total","offset","limit")}}
        if operation=="putReservationsId":
            if body["passenger_id"]!=actor:
                fail("FORBIDDEN","本人の予約だけ更新できます",403)
            if not approved or approved["kind"] not in ("cancel","change"):
                fail("APPROVAL_REQUIRED","本人が確認した変更・取消の個別委任が必要です",403)
            if headers.get("X-Operation-ID")!=approved["operation_id"] or headers.get("Idempotency-Key")!=approved["idempotency_key"]:
                fail("APPROVAL_MISMATCH","承認された操作ID・再送キーが必要です",403)
            details=approved["payload"]["details"]
            if details["ride_id"]!=ids["id"]:
                fail("APPROVAL_MISMATCH","承認対象の予約ではありません",403)
            current=self.core.get_ride(actor,ids["id"],authorization)
            if approved['kind']=='change' and any(details[k]!=current[k] for k in ('service_id','origin_stop_id','destination_stop_id')):
                # PUT /reservations/{id} permits counts and cancellation only.
                # Web/MDL route changes remain separate, unchanged Core actions.
                fail('STANDARD_ROUTE_CHANGE_UNSUPPORTED','標準APIでは乗降場所・サービスを変更できません。対応するMDLの変更操作を利用してください',400)
            changed={**current,**details}
            expected=reservation(changed)
            fields=("passenger_id","service_id","pickup","dropoff","passenger_count","accessibility_feature_count")
            if 'vehicle' in body:
                # id/name are required by the official prose. Optional capacity
                # may be omitted; every field that is sent must stay unchanged.
                vehicle=body['vehicle']
                if 'vehicle' not in expected or not {'id','name'}<=set(vehicle) or any(
                    key not in expected['vehicle'] or packed(value)!=packed(expected['vehicle'][key])
                    for key,value in vehicle.items()
                ):
                    fail('APPROVAL_MISMATCH','車両情報は変更できません',403)
                expected['vehicle']=vehicle
                fields+=('vehicle',)
            expected={k:expected[k] for k in fields}
            # Bind the standard status to the state that the owner approved.
            if approved["kind"]=="cancel":
                expected["status"]="cancelled"
            else:
                expected["status"]=STATE[details["status"]]
            if packed(body)!=packed(expected):
                fail("APPROVAL_MISMATCH","変更・取消の内容が本人の承認と一致しません",403)
            result=self.core.mutate(actor,approved["operation_id"],approved["idempotency_key"],approved["kind"],approved["payload"],authorization)
            # Replay returns the committed result; current state is in /direct/v1/operations/{id}.
            return 200,reservation(result["result"])
        fail("NOT_IMPLEMENTED","この標準操作は未実装です",503)

    def dated_reservations(self,actor,authorization,params,statuses):
        """Filter authorized planned rides before pagination, in local JST.

        Unknown planned dates never silently disappear. Date filtering fails
        explicitly if a relevant legacy call lacks a planned pickup timestamp.
        This bounded local adapter does not make a production consistency SLA.
        """
        lower=params.get('pickup_date_from','0001-01-01')
        upper=params.get('pickup_date_to','9999-12-31')
        if lower>upper:fail('INVALID_QUERY','開始日は終了日以前にしてください')
        items=[];position=0
        while True:
            page=self.core.list_rides(actor,position,100,params.get('reservation_ids'),statuses,authorization,owner_only=True)
            for ride in page['rides']:
                booking=ride.get('booking')
                if not booking or not booking.get('pickup_at'):
                    fail('PICKUP_TIME_NOT_ACQUIRED','対象の依頼に乗車予定日時が未取得のものがあるため日付で絞り込めません',503)
                planned=datetime.fromisoformat(booking['pickup_at']).astimezone(ZoneInfo('Asia/Tokyo')).date().isoformat()
                if lower<=planned<=upper:items.append(reservation(ride))
            position+=len(page['rides'])
            if position>=page['total']:break
            if position>=10000:fail('QUERY_LIMIT','ローカル試験の照会上限を超えました。予約IDや状態で絞り込んでください',503)
        offset,limit=params.get('offset',0),params.get('limit',20)
        return {'reservations':items[offset:offset+limit],'total':len(items),'offset':offset,'limit':limit}
