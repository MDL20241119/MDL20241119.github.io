"""Synthetic payment-information ledger; never executes charges or refunds.

One row per ride, with shared Core authorization, confirmation, idempotency,
transaction and catalog audit/Outbox. Standard fields are mapped separately.
"""
import json
from .core import exact,fail,iso

STATUSES={'uncollected','received','excluded','cancelled'}
MAX_AMOUNT=2147483647

class Payments:
    def __init__(self,core):self.core=core

    def visible(self,db,actor,ride_id):
        if actor['role'] not in ('rider','admin'):
            fail('FORBIDDEN','決済情報は本人または担当事業者の管理者だけが確認できます',403)
        return self.core.visible(db,actor,ride_id)

    def expected(self,ride):
        fare=self.core.cancellation_fee(ride) if ride['status']=='cancelled' else json.loads(ride['fare_json'])
        value=fare.get('amount')
        return value if type(value) is int and 0<=value<=MAX_AMOUNT and fare.get('currency')=='JPY' else None

    def record(self,row):
        return {'id':row['ride_id'],**{k:row[k] for k in ('amount','payment_status','version','created_at','updated_at')}}

    def view(self,db,ride):
        row=db.execute('SELECT * FROM payments WHERE ride_id=?',(ride['id'],)).fetchone()
        expected=self.expected(ride);reason=None
        if row:
            if ride['status']=='cancelled':
                if row['payment_status']=='received' and row['amount']>0:reason='refund_review_required'
                elif row['payment_status']!='cancelled':reason='cancellation_update_required'
            elif expected is None:reason='fare_unknown'
            elif row['amount']!=expected:reason='fare_update_required'
        return {'reservation_id':ride['id'],'record':self.record(row) if row else None,'expected_amount':expected,
            'currency':'JPY','review_required':reason is not None,'review_reason':reason,'basis':'synthetic_ledger_only'}

    def read(self,actor_id,ride_id,authorization=None):
        with self.core.db() as db:
            actor=self.core.actor(db,actor_id);self.core.check_authorization(db,actor_id,authorization)
            result=self.view(db,self.visible(db,actor,ride_id))
            if result['record'] is None:fail('PAYMENT_NOT_RECORDED','決済情報は未登録です。未収や0円とは区別してください',404)
            return result

    def prepare(self,db,actor,data):
        if actor['role']!='admin':fail('FORBIDDEN','決済台帳を更新できるのは管理者だけです',403)
        exact(data,['ride_id','amount','payment_status'])
        if type(data['amount']) is not int or not 0<=data['amount']<=MAX_AMOUNT:
            fail('INVALID_PAYMENT_AMOUNT','金額は0〜2147483647円の整数で指定してください')
        if not isinstance(data['payment_status'],str) or data['payment_status'] not in STATUSES:
            fail('INVALID_PAYMENT_STATUS','決済状態の指定が不正です')
        ride=self.visible(db,actor,data['ride_id'])
        row=db.execute('SELECT * FROM payments WHERE ride_id=?',(ride['id'],)).fetchone()
        if ride['status']=='requested':fail('PAYMENT_RESERVATION_NOT_CONFIRMED','引受前の依頼には決済情報を登録できません',409)
        expected=self.expected(ride)
        # Keep received money visible after cancellation. No refund is inferred.
        if row and row['payment_status']=='received' and row['amount']>0:
            if data['payment_status']!='received' or data['amount']!=row['amount']:
                fail('PAYMENT_SETTLEMENT_REVIEW_REQUIRED','受領済みの金額は保持します。訂正・返金の処理は未実装です',409)
        else:
            if expected is None:fail('FARE_NOT_CONFIGURED','確定済みの日本円運賃がありません',503)
            if ride['status']=='cancelled':
                if data['payment_status']!='cancelled':fail('PAYMENT_STATUS_MISMATCH','取消済みの予約は決済キャンセルを確認してください',409)
            elif data['payment_status']=='cancelled':fail('PAYMENT_STATUS_MISMATCH','予約を取り消す操作とは別です。予約は取消済みではありません',409)
            if data['payment_status']=='excluded' and expected!=0:
                fail('PAYMENT_EXCLUSION_UNSUPPORTED','この試験範囲の対象外登録は確定運賃0円の場合だけです',409)
            if data['amount']!=expected:fail('PAYMENT_AMOUNT_MISMATCH','予約で確定した金額と一致しません。内容を確認してください',409)
        return {'input':data,'version':row['version'] if row else 0,'dependencies':[{
            'ride_version':ride['version'],'ride_status':ride['status'],'fare':json.loads(ride['fare_json']),
            'cancellation_fee':self.core.cancellation_fee(ride) if ride['status']=='cancelled' else None,
            'previous':self.record(row) if row else None}]}

    def resource(self,db,actor,ride_id):
        ride=self.visible(db,actor,ride_id)
        return {'resource_type':'payment','id':ride_id,'value':self.view(db,ride),'deleted':False}

    def apply(self,db,actor,details):
        data=details['input'];now=iso(self.core.clock())
        db.execute('INSERT INTO payments VALUES (?,?,?,?,?,?) ON CONFLICT(ride_id) DO UPDATE SET amount=excluded.amount,payment_status=excluded.payment_status,version=excluded.version,updated_at=excluded.updated_at',
            (data['ride_id'],data['amount'],data['payment_status'],details['version']+1,now,now))
        return self.resource(db,actor,data['ride_id'])

    def check_change(self,db,ride,fare):
        row=db.execute('SELECT * FROM payments WHERE ride_id=?',(ride['id'],)).fetchone()
        if row and row['payment_status'] in ('received','excluded') and (fare.get('currency')!='JPY' or fare.get('amount')!=row['amount']):
            fail('PAYMENT_SETTLEMENT_REVIEW_REQUIRED','受領済み・対象外の記録と金額が変わる変更は、精算対応が必要です',409)
