"""Single business core. Adapters must provide a verified actor, never a client role."""
import hashlib
import json
import re
import secrets
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from .db import connect

ACTIVE = ("assigned", "arrived", "onboard")
STATES = {"requested":"引受待ち", "assigned":"迎車中", "arrived":"到着", "onboard":"乗車中", "completed":"降車完了", "cancelled":"取消済み"}
NEXT = {"requested":"ドライバーの引受をお待ちください", "assigned":"指定した乗降場所でお待ちください", "arrived":"車両を確認してご乗車ください", "onboard":"降車までお待ちください", "completed":"ご利用ありがとうございました", "cancelled":"依頼は取り消されました"}

class DomainError(Exception):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status

def fail(code, message, status=400):
    raise DomainError(code, message, status)

def packed(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)

def uid(prefix):
    return prefix + "_" + secrets.token_hex(12)

def iso(epoch=None):
    return datetime.fromtimestamp(time.time() if epoch is None else epoch, timezone.utc).isoformat()

def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,100}",value):
        fail("INVALID_OPERATION_ID", "操作IDと再送キーは8〜100文字の英数字・ハイフン・アンダースコアで指定してください")
    return value

def exact(data, required):
    if not isinstance(data,dict) or set(data) != set(required):
        fail("INVALID_INPUT", "入力項目が不足しているか、対応していない項目が含まれています")

class Core:
    def __init__(self, path, clock=time.time):
        self.path, self.clock = path, clock
        from .catalog import Catalog
        self.catalog=Catalog(self)
        from .booking import Booking
        self.booking=Booking(self)
        from .payments import Payments
        self.payments=Payments(self)
        from .observations import Observations
        self.observations=Observations(self)
        from .gtfs import Gtfs
        self.gtfs=Gtfs(self)
        from .agent_tasks import AgentTasks
        self.tasks=AgentTasks(self)

    @contextmanager
    def db(self, write=False):
        db = connect(self.path)
        try:
            db.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def actor(self, db, actor_id, role=None):
        actor = db.execute("SELECT id,tenant_id,role,eligible,active FROM users WHERE id=?", (actor_id,)).fetchone()
        if not actor or not actor["active"]:
            fail("UNAUTHENTICATED", "ログインし直してください", 401)
        if role and actor["role"] != role:
            fail("FORBIDDEN", "この操作を行う権限がありません", 403)
        return actor

    def visible(self, db, actor, ride_id):
        if not isinstance(ride_id,str) or len(ride_id)>100:
            fail("INVALID_INPUT", "依頼IDの形式が不正です")
        row = db.execute("SELECT * FROM rides WHERE id=? AND tenant_id=?", (ride_id,actor["tenant_id"])).fetchone()
        allowed = row and (actor["role"] == "admin" or
            (actor["role"] == "rider" and row["rider_id"] == actor["id"]) or
            (actor["role"] == "driver" and (row["driver_id"] == actor["id"] or
                (row["status"] == "requested" and db.execute("SELECT 1 FROM vehicles WHERE driver_id=? AND service_id=? AND active=1",(actor["id"],row["service_id"])).fetchone()))))
        if not allowed:
            fail("NOT_FOUND", "依頼が見つからないか、閲覧権限がありません", 404)
        return row

    def ride_view(self, db, row, actor):
        result = {k:row[k] for k in ["id","service_id","origin_stop_id","destination_stop_id","passengers","status","version","vehicle_id","created_at","updated_at"]}
        for key, stop in [("origin_name","origin_stop_id"),("destination_name","destination_stop_id")]:
            result[key] = db.execute("SELECT name FROM stops WHERE id=?", (row[stop],)).fetchone()[0]
        result.update({"fare":json.loads(row["fare_json"]), "status_label":STATES[row["status"]], "next_action":NEXT[row["status"]],
            "reservation_status":"pending" if row["status"] == "requested" else ("cancelled" if row["status"]=="cancelled" else "confirmed"),
            "assignment_status":"released" if row["status"] in ("cancelled","completed") and row["vehicle_id"] else ("assigned" if row["vehicle_id"] else "unassigned"),
            "vehicle_location":None, "eta":None, "location_status":"not_acquired", "eta_status":"not_acquired", "synthetic":True})
        if actor["role"] == "admin" or row["rider_id"] == actor["id"]:
            result["rider_id"] = row["rider_id"]
            result['payment']=self.payments.view(db,row)
        result["events"] = [dict(e) for e in db.execute("SELECT kind,status,version,created_at FROM events WHERE ride_id=? ORDER BY version",(row["id"],))]
        booking=db.execute('SELECT data_json FROM ride_bookings WHERE ride_id=?',(row['id'],)).fetchone()
        if booking:
            value=json.loads(booking[0])
            result['booking']={k:value[k] for k in ('pickup_at','dropoff_at','pickup_location','dropoff_location','vehicle_name','vehicle_capacity','basis')}
        observation=self.observations.for_ride(db,actor,row)
        result['observation']=observation
        if observation:
            result['vehicle_location']=observation['location']
            result['location_status']=observation['location_status']
        return result

    def check_authorization(self, db, actor_id, authorization, operation=None):
        if authorization is not None:
            from .delegation import verify_grant
            verify_grant(db, actor_id, authorization, self.clock(), operation)

    def get_ride(self, actor_id, ride_id, authorization=None):
        with self.db() as db:
            actor = self.actor(db,actor_id)
            self.check_authorization(db,actor_id,authorization)
            return self.ride_view(db,self.visible(db,actor,ride_id),actor)

    def list_rides(self, actor_id, offset=0, limit=20, reservation_ids=None, statuses=None, authorization=None, owner_only=False):
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
            fail("INVALID_PAGINATION","offset は0以上、limit は1〜100で指定してください")
        with self.db() as db:
            actor = self.actor(db,actor_id,"rider" if owner_only else None)
            self.check_authorization(db,actor_id,authorization)
            where, args = ["r.tenant_id=?"], [actor["tenant_id"]]
            if actor["role"] == "rider":
                where.append("r.rider_id=?"); args.append(actor_id)
            elif actor["role"] == "driver":
                where.append("(r.driver_id=? OR (r.status='requested' AND EXISTS (SELECT 1 FROM vehicles v WHERE v.driver_id=? AND v.service_id=r.service_id AND v.active=1)))")
                args.extend([actor_id,actor_id])
            for field,values in [("id",reservation_ids),("status",statuses)]:
                if values is not None:
                    if not isinstance(values,list) or not values or len(values)>100 or not all(isinstance(v,str) and len(v)<=100 for v in values):
                        fail("INVALID_FILTER","絞り込み条件の形式が不正です")
                    if field == "status" and not set(values)<=set(STATES):
                        fail("INVALID_FILTER","予約状態の指定が不正です")
                    where.append("r."+field+" IN ("+",".join("?" for _ in values)+")"); args.extend(values)
            condition=" AND ".join(where)
            total=db.execute("SELECT COUNT(*) FROM rides r WHERE "+condition,args).fetchone()[0]
            rows=db.execute("SELECT r.* FROM rides r WHERE "+condition+" ORDER BY r.created_at,r.id LIMIT ? OFFSET ?",[*args,limit,offset])
            return {"rides":[self.ride_view(db,r,actor) for r in rows],"total":total,"offset":offset,"limit":limit}

    def snapshot(self, actor_id, authorization=None):
        with self.db() as db:
            actor = self.actor(db,actor_id)
            self.check_authorization(db,actor_id,authorization)
            services = []
            for s in db.execute("SELECT * FROM services WHERE tenant_id=?",(actor["tenant_id"],)):
                services.append({"id":s["id"],"name":s["name"],"active":bool(s["active"]),"fare":json.loads(s["fare_json"]),
                    "routes":[{'id':r['id'],**json.loads(r['data_json'])} for r in db.execute('SELECT * FROM route_policies WHERE service_id=? ORDER BY id',(s['id'],))],
                    "policy":json.loads(s["policy_json"]),"stops":[dict(x) for x in db.execute("SELECT id,name,photo_url,active FROM stops WHERE service_id=?",(s["id"],))]})
            rides = []
            for row in db.execute("SELECT * FROM rides WHERE tenant_id=? ORDER BY created_at DESC,id DESC LIMIT 200",(actor["tenant_id"],)):
                try:
                    self.visible(db,actor,row["id"])
                except DomainError:
                    continue
                rides.append(self.ride_view(db,row,actor))
            vehicles = []
            if actor["role"] in ("driver","admin"):
                for v in db.execute("SELECT v.*,s.active AS service_active FROM vehicles v JOIN services s ON s.id=v.service_id WHERE v.tenant_id=?",(actor["tenant_id"],)):
                    if actor["role"] == "driver" and v["driver_id"] != actor_id:
                        continue
                    run = db.execute("SELECT * FROM runs WHERE vehicle_id=? AND active=1",(v["id"],)).fetchone()
                    observation=self.observations.view(db,v)
                    vehicles.append({"id":v["id"],"capacity":v["capacity"],"reserved":run["reserved"] if run else 0,
                        "accepting":bool(run["accepting"]) if run else True,"location_status":observation['location_status'],"observation":observation})
            counts = {s:sum(1 for r in rides if r["status"]==s) for s in STATES}
            pending = db.execute("SELECT COUNT(*) FROM outbox WHERE tenant_id=? AND delivered=0",(actor["tenant_id"],)).fetchone()[0] if actor["role"]=="admin" else None
            if pending is not None:
                pending += db.execute("SELECT COUNT(*) FROM catalog_outbox o JOIN catalog_events e ON e.id=o.event_id WHERE e.tenant_id=? AND o.delivered=0",(actor["tenant_id"],)).fetchone()[0]
            return {"user":dict(actor),"services":services,"rides":rides,"vehicles":vehicles,"counts":counts,
                    "outbox_pending":pending,"as_of":iso(self.clock()),"limit":200,"mode":"local_synthetic","offers":self.booking.offers(db,actor),
                    "capabilities":{"mlit":False,"mcp":False,"a2a":False,"line":False,"live_notifications":False}}

    def request_details(self, db, actor, data):
        exact(data,["service_id","origin_stop_id","destination_stop_id","passengers"])
        if not all(isinstance(data[k],str) for k in ("service_id","origin_stop_id","destination_stop_id")):
            fail("INVALID_INPUT","乗降場所とサービスを選んでください")
        if not actor["eligible"]:
            fail("INELIGIBLE","このサービスの利用資格がありません",403)
        service = db.execute("SELECT * FROM services WHERE id=? AND tenant_id=?",(data["service_id"],actor["tenant_id"])).fetchone()
        if not service or not service["active"]:
            fail("SERVICE_UNAVAILABLE","このサービスは利用できません",409)
        policy = json.loads(service["policy_json"])
        now = datetime.fromtimestamp(self.clock(),ZoneInfo(service["timezone"]))
        configured=self.catalog.check_request(db,actor,service)
        if not configured and (now.weekday() not in policy["days"] or not policy["open"] <= now.strftime("%H:%M") < policy["close"]):
            fail("SERVICE_CLOSED","運行時間外です",409)
        if type(data["passengers"]) is not int or not 1 <= data["passengers"] <= policy["max_passengers"]:
            fail("INVALID_PASSENGERS",f"人数は1〜{policy['max_passengers']}名で指定してください")
        stops = {}
        for key in ("origin_stop_id","destination_stop_id"):
            stop = db.execute("SELECT * FROM stops WHERE id=? AND service_id=? AND active=1",(data[key],service["id"])).fetchone()
            if not stop:
                fail("INVALID_STOP","利用できる指定乗降場所を選んでください")
            self.catalog.check_stop(db,stop)
            stops[key] = stop["name"]
        if data["origin_stop_id"] == data["destination_stop_id"]:
            fail("SAME_STOP","乗る場所と降りる場所を分けてください")
        return {**data,"origin_name":stops["origin_stop_id"],"destination_name":stops["destination_stop_id"],
                "fare":json.loads(service["fare_json"]),"service_revision":service["revision"]}

    def prepare(self, actor_id, kind, data, authorization=None):
        from .catalog import CATALOG_COMMANDS
        with self.db(True) as db:
            actor = self.actor(db,actor_id,None if kind in CATALOG_COMMANDS else "rider")
            self.check_authorization(db,actor_id,authorization)
            if kind in CATALOG_COMMANDS:
                details=self.catalog.prepare(db,actor,kind,data)
            elif kind=='book':
                details=self.booking.prepare(db,actor,data)
            elif kind == "request":
                details = self.request_details(db,actor,data)
            elif kind == "change":
                exact(data,["ride_id","service_id","origin_stop_id","destination_stop_id","passengers"])
                ride=self.visible(db,actor,data["ride_id"])
                details=self.change_details(db,actor,ride,{k:v for k,v in data.items() if k!="ride_id"})
            elif kind == "cancel":
                exact(data,["ride_id"])
                row = self.visible(db,actor,data["ride_id"])
                if row["status"] not in ("requested","assigned","arrived"):
                    fail("INVALID_STATE","現在の状態では取り消せません。運営担当者にご相談ください",409)
                details = {"ride_id":row["id"],"version":row["version"],"origin_stop_id":row["origin_stop_id"],
                           "destination_stop_id":row["destination_stop_id"],"passengers":row["passengers"],
                           "cancellation_fee":self.cancellation_fee(row)}
            else:
                fail("INVALID_ACTION","対応していない確認操作です")
            draft_id, expiry = uid("draft"), self.clock()+300
            if kind=='book':
                from .catalog import timestamp
                expiry=min(expiry,timestamp(details['expires_at']))
            db.execute("INSERT INTO drafts VALUES (?,?,?,?,?,0)",(draft_id,actor_id,kind,packed(details),expiry))
            return {"id":draft_id,"kind":kind,"details":details,"expires_at":iso(expiry)}

    def cancellation_fee(self,ride):
        # Existing explicit synthetic policy, shared by cancellation and ledger.
        return {"amount":0,"currency":"JPY","basis":"synthetic_test_only"}

    def change_details(self, db, actor, ride, data):
        if ride["status"] not in ("requested","assigned"):
            fail("INVALID_STATE","到着以降は変更できません。運営担当者にご相談ください",409)
        details=self.request_details(db,actor,data)
        self.payments.check_change(db,ride,details['fare'])
        self.booking.change_check(db,actor,ride)
        if details["service_id"] != ride["service_id"]:
            fail("SERVICE_CHANGE_UNSUPPORTED","サービスをまたぐ変更には対応していません",409)
        if ride["status"] == "assigned":
            if any(details[k]!=ride[k] for k in ("origin_stop_id","destination_stop_id")):
                fail("ROUTE_CHANGE_UNSUPPORTED","引受後は乗降場所を変更できません",409)
            run=db.execute("SELECT * FROM runs WHERE id=? AND active=1",(ride["run_id"],)).fetchone()
            vehicle=db.execute("SELECT * FROM vehicles WHERE id=? AND active=1",(ride["vehicle_id"],)).fetchone()
            if not run or not run["accepting"] or not vehicle:
                fail("RUN_UNAVAILABLE","この便は変更受付を終了しました",409)
            if run["reserved"]-ride["passengers"]+details["passengers"] > vehicle["capacity"]:
                fail("CAPACITY_FULL","変更後の人数に必要な空席がありません",409)
        return {**details,"ride_id":ride["id"],"version":ride["version"],"status":ride["status"]}

    def check_draft(self, db, actor, kind, payload):
        exact(payload,["draft_id","details"])
        if not isinstance(payload["draft_id"],str) or not isinstance(payload["details"],dict):
            fail("INVALID_INPUT", "確認情報の形式が不正です")
        row = db.execute("SELECT * FROM drafts WHERE id=? AND actor_id=?",(payload["draft_id"],actor["id"])).fetchone()
        if not row or row["kind"] != kind:
            fail("INVALID_CONFIRMATION","この確認情報は使用できません",403)
        if row["consumed"]:
            fail("CONFIRMATION_USED","確認済み操作です。元の操作IDで結果を確認してください",409)
        if row["expires_at"] <= self.clock():
            fail("CONFIRMATION_EXPIRED","確認の有効期限が切れました。内容を確認し直してください",409)
        if row["details_json"] != packed(payload["details"]):
            fail("CONFIRMATION_CHANGED","確認内容が変わっています。確認し直してください",409)
        return json.loads(row["details_json"])

    def event(self, db, ride_id, actor_id, operation_id, kind):
        ride = db.execute("SELECT * FROM rides WHERE id=?",(ride_id,)).fetchone()
        event_id = uid("event")
        db.execute("INSERT INTO events VALUES (?,?,?,?,?,?,?,?)",(event_id,ride_id,actor_id,operation_id,kind,ride["status"],ride["version"],iso(self.clock())))
        db.execute("INSERT INTO outbox(event_id,tenant_id) VALUES (?,?)",(event_id,ride["tenant_id"]))

    def mutate(self, actor_id, operation_id, key, kind, payload, authorization=None):
        identifier(operation_id); identifier(key)
        digest = hashlib.sha256(packed({"kind":kind,"payload":payload}).encode()).hexdigest()
        with self.db(True) as db:
            actor = self.actor(db,actor_id)
            self.check_authorization(db,actor_id,authorization,{"operation_id":operation_id,"idempotency_key":key,"kind":kind,"payload":payload})
            previous = db.execute("SELECT * FROM operations WHERE actor_id=? AND (operation_id=? OR idempotency_key=?)",(actor_id,operation_id,key)).fetchone()
            if previous:
                if previous["operation_id"]!=operation_id or previous["idempotency_key"]!=key or previous["digest"]!=digest:
                    fail("IDEMPOTENCY_CONFLICT","同じ操作ID・再送キーで別の内容は実行できません",409)
                current = self.ride_view(db,self.visible(db,actor,previous["ride_id"]),actor)
                return {"operation_id":operation_id,"replayed":True,"result":json.loads(previous["result_json"]),"current":current}
            from .catalog import CATALOG_COMMANDS
            previous=db.execute("SELECT * FROM catalog_operations WHERE actor_id=? AND (operation_id=? OR idempotency_key=?)",(actor_id,operation_id,key)).fetchone()
            if previous:
                if previous['operation_id']!=operation_id or previous['idempotency_key']!=key or previous['digest']!=digest:
                    fail('IDEMPOTENCY_CONFLICT','同じ操作ID・再送キーで別の内容は実行できません',409)
                if previous['redacted']:fail('RESULT_ERASED','この操作の個人情報は削除済みです',410)
                return {'operation_id':operation_id,'replayed':True,'result':json.loads(previous['result_json']),'current':self.catalog.current(db,actor,previous)}
            if kind in CATALOG_COMMANDS:
                details=self.check_draft(db,actor,kind,payload)
                if self.catalog.prepare(db,actor,kind,details['input'])!=details:
                    if kind=='payment_update':fail('STALE_PAYMENT','予約または決済情報が変わりました。内容を確認し直してください',409)
                    fail('STALE_CATALOG','情報や規約が変わりました。内容を確認し直してください',409)
                result=self.catalog.apply(db,actor,kind,details)
                db.execute('UPDATE drafts SET consumed=1 WHERE id=?',(payload['draft_id'],))
                db.execute('INSERT INTO catalog_operations VALUES (?,?,?,?,?,?,?,?,0,?)',(actor_id,operation_id,key,kind,digest,result['resource_type'],result['id'],packed(result),iso(self.clock())))
                event_id=uid('catalog_event')
                db.execute('INSERT INTO catalog_events VALUES (?,?,?,?,?,?,?,?)',(event_id,actor_id,actor['tenant_id'],operation_id,kind,result['resource_type'],result['id'],iso(self.clock())))
                db.execute('INSERT INTO catalog_outbox(event_id) VALUES (?)',(event_id,))
                return {'operation_id':operation_id,'replayed':False,'result':result,'current':result}
            if kind=='book':
                self.actor(db,actor_id,'rider')
                details=self.check_draft(db,actor,kind,payload)
                ride_id=self.booking.book(db,actor,details)
                db.execute('UPDATE drafts SET consumed=1 WHERE id=?',(payload['draft_id'],))
            elif kind in ("request","cancel","change"):
                self.actor(db,actor_id,"rider")
                details = self.check_draft(db,actor,kind,payload)
                if kind == "request":
                    data = {k:details[k] for k in ["service_id","origin_stop_id","destination_stop_id","passengers"]}
                    if self.request_details(db,actor,data) != details:
                        fail("TERMS_CHANGED","運賃・乗降場所・利用条件が変わりました。確認し直してください",409)
                    ride_id, now = uid("ride"), iso(self.clock())
                    db.execute("INSERT INTO rides(id,tenant_id,rider_id,service_id,origin_stop_id,destination_stop_id,passengers,fare_json,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (ride_id,actor["tenant_id"],actor_id,details["service_id"],details["origin_stop_id"],details["destination_stop_id"],details["passengers"],packed(details["fare"]),"requested",now,now))
                elif kind == "change":
                    ride_id=details["ride_id"]
                    ride=self.visible(db,actor,ride_id)
                    if ride["version"] != details["version"]:
                        fail("STALE_VERSION","状態が変わりました。変更内容を確認し直してください",409)
                    data={k:details[k] for k in ["service_id","origin_stop_id","destination_stop_id","passengers"]}
                    if self.change_details(db,actor,ride,data) != details:
                        fail("TERMS_CHANGED","運賃・利用条件が変わりました。変更内容を確認し直してください",409)
                    if ride["status"] == "assigned":
                        self.reserve_seats(db,ride['run_id'],details['passengers']-ride['passengers'])
                    db.execute("UPDATE rides SET origin_stop_id=?,destination_stop_id=?,passengers=?,fare_json=?,version=version+1,updated_at=? WHERE id=?",
                               (details["origin_stop_id"],details["destination_stop_id"],details["passengers"],packed(details["fare"]),iso(self.clock()),ride_id))
                else:
                    ride_id = details["ride_id"]
                    ride = self.visible(db,actor,ride_id)
                    if ride["version"]!=details["version"] or ride["status"] not in ("requested","assigned","arrived"):
                        fail("STALE_VERSION","状態が変わりました。最新状況を確認して、取消内容を確認し直してください",409)
                    if self.cancellation_fee(ride)!=details['cancellation_fee']:
                        fail('TERMS_CHANGED','取消料が変わりました。内容を確認し直してください',409)
                    self.release(db,ride)
                    db.execute("UPDATE rides SET status='cancelled',version=version+1,updated_at=? WHERE id=?",(iso(self.clock()),ride_id))
                db.execute("UPDATE drafts SET consumed=1 WHERE id=?",(payload["draft_id"],))
            elif kind in ("accept","arrive","board","complete"):
                self.actor(db,actor_id,"driver")
                exact(payload,["ride_id","version","stopped"])
                if payload["stopped"] is not True:
                    fail("STOP_REQUIRED","安全な場所に停車してから操作してください",409)
                if type(payload["version"]) is not int:
                    fail("INVALID_INPUT","対象の版が必要です")
                ride_id = payload["ride_id"]
                ride = self.visible(db,actor,ride_id)
                if ride["version"] != payload["version"]:
                    fail("STALE_VERSION","他の操作で状態が変わりました。最新状況を確認してください",409)
                if kind == "accept":
                    self.accept(db,actor,ride)
                else:
                    before, after = {"arrive":("assigned","arrived"),"board":("arrived","onboard"),"complete":("onboard","completed")}[kind]
                    if ride["driver_id"] != actor_id or ride["status"] != before:
                        fail("INVALID_STATE","担当または操作順序が正しくありません",409)
                    db.execute("UPDATE runs SET accepting=0 WHERE id=?",(ride["run_id"],))
                    if kind == "complete":
                        self.release(db,ride)
                    db.execute("UPDATE rides SET status=?,version=version+1,updated_at=? WHERE id=?",(after,iso(self.clock()),ride_id))
            else:
                fail("INVALID_ACTION","対応していない操作です")
            self.event(db,ride_id,actor_id,operation_id,kind)
            view = self.ride_view(db,self.visible(db,actor,ride_id),actor)
            db.execute("INSERT INTO operations VALUES (?,?,?,?,?,?,?,?)",(actor_id,operation_id,key,kind,digest,ride_id,packed(view),iso(self.clock())))
            return {"operation_id":operation_id,"replayed":False,"result":view,"current":view}

    def accept(self, db, actor, ride):
        if ride["status"] != "requested":
            fail("ALREADY_ASSIGNED","この依頼はすでに処理されています",409)
        rider = self.actor(db,ride["rider_id"],"rider")
        current = self.request_details(db,rider,{k:ride[k] for k in ["service_id","origin_stop_id","destination_stop_id","passengers"]})
        if current["fare"] != json.loads(ride["fare_json"]):
            fail("TERMS_CHANGED","受付後に運賃が変わりました。運営担当者へ確認してください",409)
        vehicle = db.execute("SELECT * FROM vehicles WHERE driver_id=? AND tenant_id=? AND service_id=? AND active=1",(actor["id"],actor["tenant_id"],ride["service_id"])).fetchone()
        if not vehicle:
            fail("NO_VEHICLE","担当する車両がありません",409)
        run = db.execute("SELECT * FROM runs WHERE vehicle_id=? AND active=1",(vehicle["id"],)).fetchone()
        if run:
            if db.execute('SELECT 1 FROM run_offers WHERE run_id=?',(run['id'],)).fetchone():
                fail('RUN_UNAVAILABLE','提示便の座席は候補からの予約で確保します。通常の引受には別の便が必要です',409)
            if not run["accepting"] or run["origin_stop_id"]!=ride["origin_stop_id"] or run["destination_stop_id"]!=ride["destination_stop_id"]:
                fail("RUN_UNAVAILABLE","現在の便では、この乗降場所の依頼を引き受けられません",409)
            run_id, reserved = run["id"], run["reserved"]
        else:
            run_id, reserved = uid("run"),0
            db.execute("INSERT INTO runs(id,vehicle_id,origin_stop_id,destination_stop_id) VALUES (?,?,?,?)",(run_id,vehicle["id"],ride["origin_stop_id"],ride["destination_stop_id"]))
        self.reserve_seats(db,run_id,ride['passengers'])
        db.execute("UPDATE rides SET status='assigned',driver_id=?,vehicle_id=?,run_id=?,version=version+1,updated_at=? WHERE id=?",(actor["id"],vehicle["id"],run_id,iso(self.clock()),ride["id"]))

    def reserve_seats(self,db,run_id,delta):
        row=db.execute('SELECT r.*,v.capacity,v.active AS vehicle_active,u.active AS driver_active FROM runs r JOIN vehicles v ON v.id=r.vehicle_id JOIN users u ON u.id=v.driver_id WHERE r.id=?',(run_id,)).fetchone()
        if not row or not row['active'] or not row['accepting'] or not row['vehicle_active'] or not row['driver_active']:
            fail('RUN_UNAVAILABLE','この便は受付を終了しました',409)
        if type(delta) is not int or not 0<=row['reserved']+delta<=row['capacity']:
            fail('CAPACITY_FULL','必要な空席がありません',409)
        db.execute('UPDATE runs SET reserved=reserved+? WHERE id=?',(delta,run_id))

    def release(self, db, ride):
        if ride["run_id"] and ride["status"] in ACTIVE:
            db.execute("UPDATE runs SET reserved=reserved-? WHERE id=?",(ride["passengers"],ride["run_id"]))
            db.execute("UPDATE runs SET active=0,accepting=0 WHERE id=? AND reserved=0",(ride["run_id"],))

    def operation(self, actor_id, operation_id, authorization=None):
        identifier(operation_id)
        with self.db() as db:
            actor = self.actor(db,actor_id)
            self.check_authorization(db,actor_id,authorization)
            row = db.execute("SELECT * FROM operations WHERE actor_id=? AND operation_id=?",(actor_id,operation_id)).fetchone()
            if not row:
                row=db.execute('SELECT * FROM catalog_operations WHERE actor_id=? AND operation_id=?',(actor_id,operation_id)).fetchone()
                if row:
                    return {'operation_id':operation_id,'result':json.loads(row['result_json']),'current':self.catalog.current(db,actor,row)}
                fail("OPERATION_NOT_FOUND","この操作の確定結果はまだ記録されていません。同じ操作ID・同じ内容で照合または再送してください",404)
            return {"operation_id":operation_id,"result":json.loads(row["result_json"]),"current":self.ride_view(db,self.visible(db,actor,row["ride_id"]),actor)}

    def deliver_fake(self, simulate_failure=False):
        """Synthetic receiver only. No network. Unique event IDs deduplicate retries."""
        with self.db(True) as db:
            rows = list(db.execute("SELECT * FROM outbox WHERE delivered=0 ORDER BY event_id"))
            for row in rows:
                db.execute("UPDATE outbox SET attempts=attempts+1 WHERE event_id=?",(row["event_id"],))
                if simulate_failure:
                    db.execute("UPDATE outbox SET last_error='synthetic_failure' WHERE event_id=?",(row["event_id"],))
                    continue
                db.execute("INSERT OR IGNORE INTO fake_inbox VALUES (?,?)",(row["event_id"],iso(self.clock())))
                db.execute("UPDATE outbox SET delivered=1,last_error=NULL WHERE event_id=?",(row["event_id"],))
            catalog=list(db.execute('SELECT * FROM catalog_outbox WHERE delivered=0'))
            for row in catalog:
                db.execute('UPDATE catalog_outbox SET attempts=attempts+1 WHERE event_id=?',(row['event_id'],))
                if simulate_failure:
                    db.execute("UPDATE catalog_outbox SET last_error='synthetic_failure' WHERE event_id=?",(row['event_id'],));continue
                db.execute('INSERT OR IGNORE INTO catalog_fake_inbox VALUES (?)',(row['event_id'],))
                db.execute('UPDATE catalog_outbox SET delivered=1,last_error=NULL WHERE event_id=?',(row['event_id'],))
            count=len(rows)+len(catalog)
            return {"processed":count,"delivered":0 if simulate_failure else count,"mode":"fake_only"}
