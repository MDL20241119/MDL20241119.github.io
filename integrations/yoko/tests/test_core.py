import copy
import json
import multiprocessing
import shutil
import tempfile
import threading
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from app.core import Core, DomainError
from app.db import initialize,connect

REQUEST={"service_id":"service-a","origin_stop_id":"stop-a","destination_stop_id":"stop-b","passengers":1}

def run_accept(path,actor,ride,barrier,queue):
    core=Core(path)
    barrier.wait(timeout=15)
    try:
        op=uuid.uuid4().hex
        core.mutate(actor,op,op,"accept",{"ride_id":ride,"version":1,"stopped":True})
        queue.put("ok")
    except DomainError as exc:
        queue.put(exc.code)

class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=tempfile.TemporaryDirectory()
        cls.template=Path(cls.base.name)/"base.sqlite3"
        initialize(cls.template)

    @classmethod
    def tearDownClass(cls):
        cls.base.cleanup()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/"test.sqlite3"
        shutil.copyfile(self.template,self.path)
        self.core=Core(self.path)

    def sql(self,statement,args=()):
        db=connect(self.path)
        try:
            return [tuple(r) for r in db.execute(statement,args)]
        finally:
            db.close()

    def commit(self,kind,payload,actor="rider-a1",op=None):
        op=op or uuid.uuid4().hex
        return self.core.mutate(actor,op,op,kind,payload)

    def create(self,actor="rider-a1",passengers=1):
        draft=self.core.prepare(actor,"request",{**REQUEST,"passengers":passengers})
        return self.commit("request",{"draft_id":draft["id"],"details":draft["details"]},actor)["current"]

    def driver(self,kind,ride,actor="driver-a1"):
        return self.commit(kind,{"ride_id":ride["id"],"version":ride["version"],"stopped":True},actor)["current"]

    def expect_error(self,code,fn,*args,**kwargs):
        with self.assertRaises(DomainError) as result:
            fn(*args,**kwargs)
        self.assertEqual(result.exception.code,code)

    def test_three_roles_end_to_end_and_separate_states(self):
        ride=self.create()
        self.assertEqual((ride["status"],ride["reservation_status"],ride["assignment_status"]),("requested","pending","unassigned"))
        self.assertEqual(self.core.snapshot("driver-a1")["rides"][0]["id"],ride["id"])
        ride=self.driver("accept",ride)
        self.assertEqual((ride["status"],ride["reservation_status"],ride["assignment_status"]),("assigned","confirmed","assigned"))
        self.assertEqual(self.core.get_ride("admin-a1",ride["id"])["status"],"assigned")
        for action,status in [("arrive","arrived"),("board","onboard"),("complete","completed")]:
            ride=self.driver(action,ride)
            self.assertEqual(self.core.get_ride("rider-a1",ride["id"])["status"],status)
        self.assertEqual(len(ride["events"]),5)
        self.assertEqual(self.sql("SELECT reserved,active FROM runs"),[(0,0)])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM outbox"),[(5,)])

    def test_same_request_retries_are_idempotent(self):
        draft=self.core.prepare("rider-a1","request",REQUEST)
        data={"draft_id":draft["id"],"details":draft["details"]}
        first=self.commit("request",data,op="same-operation")
        again=self.commit("request",data,op="same-operation")
        self.assertTrue(again["replayed"])
        self.assertEqual(first["result"],again["result"])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM rides"),[(1,)])

    def test_same_key_different_payload_rejected(self):
        draft=self.core.prepare("rider-a1","request",REQUEST)
        data={"draft_id":draft["id"],"details":draft["details"]}
        self.commit("request",data,op="same-operation")
        data["details"]["passengers"]=2
        self.expect_error("IDEMPOTENCY_CONFLICT",self.commit,"request",data,op="same-operation")
        self.assertEqual(self.sql("SELECT passengers FROM rides"),[(1,)])

    def test_operation_id_and_key_cannot_be_recombined(self):
        draft=self.core.prepare("rider-a1","request",REQUEST)
        payload={"draft_id":draft["id"],"details":draft["details"]}
        self.core.mutate("rider-a1","operation-original","key-original","request",payload)
        self.expect_error("IDEMPOTENCY_CONFLICT",self.core.mutate,"rider-a1","operation-original","key-newvalue","request",payload)
        self.expect_error("IDEMPOTENCY_CONFLICT",self.core.mutate,"rider-a1","operation-newvalue","key-original","request",payload)

    def test_draft_can_only_be_consumed_once(self):
        draft=self.core.prepare("rider-a1","request",REQUEST)
        payload={"draft_id":draft["id"],"details":draft["details"]}
        self.commit("request",payload)
        self.expect_error("CONFIRMATION_USED",self.commit,"request",payload)

    def test_simultaneous_same_operation_is_once(self):
        draft=self.core.prepare("rider-a1","request",REQUEST)
        payload={"draft_id":draft["id"],"details":draft["details"]}
        barrier=threading.Barrier(2)
        def job():
            barrier.wait()
            return Core(self.path).mutate("rider-a1","same-operation","same-operation","request",payload)
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda _:job(),range(2)))
        self.assertEqual(sorted(x["replayed"] for x in results),[False,True])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM rides"),[(1,)])

    def test_last_seat_multi_process_atomicity(self):
        self.driver("accept",self.create(passengers=2))
        a,b=self.create(),self.create("rider-a2")
        ctx=multiprocessing.get_context("spawn")
        barrier,queue=ctx.Barrier(2),ctx.Queue()
        processes=[ctx.Process(target=run_accept,args=(str(self.path),"driver-a1",r["id"],barrier,queue)) for r in (a,b)]
        for process in processes:process.start()
        for process in processes:
            process.join(20)
            if process.is_alive():process.terminate();self.fail("Contention test timed out")
            self.assertEqual(process.exitcode,0)
        results=[queue.get(timeout=2) for _ in processes]
        self.assertCountEqual(results,["ok","CAPACITY_FULL"])
        self.assertEqual(self.sql("SELECT reserved FROM runs WHERE active=1"),[(3,)])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM rides WHERE status='requested'"),[(1,)])
        queue.close()

    def test_two_drivers_cannot_claim_one_ride(self):
        ride=self.create()
        barrier=threading.Barrier(2)
        def job(actor):
            barrier.wait()
            try:self.driver("accept",ride,actor);return "ok"
            except DomainError as exc:return exc.code
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(job,["driver-a1","driver-a2"]))
        self.assertEqual(results.count("ok"),1)
        self.assertEqual(self.sql("SELECT SUM(reserved) FROM runs"),[(1,)])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM events WHERE kind='accept'"),[(1,)])

    def test_other_rider_and_tenant_cannot_read_or_cancel(self):
        ride=self.create()
        for actor in ["rider-a2","rider-b1"]:
            self.expect_error("NOT_FOUND",self.core.get_ride,actor,ride["id"])
            self.expect_error("NOT_FOUND",self.core.prepare,actor,"cancel",{"ride_id":ride["id"]})
            self.assertEqual(self.core.snapshot(actor)["rides"],[])
        self.assertEqual(self.core.snapshot("rider-b1")["services"],[])

    def test_wrong_driver_cannot_update_after_assignment(self):
        ride=self.driver("accept",self.create())
        self.expect_error("NOT_FOUND",self.driver,"arrive",ride,"driver-a2")
        self.assertEqual(self.core.snapshot("driver-a2")["rides"],[])

    def test_confirmation_wrong_owner_or_kind(self):
        draft=self.core.prepare("rider-a1","request",REQUEST)
        payload={"draft_id":draft["id"],"details":draft["details"]}
        self.expect_error("INVALID_CONFIRMATION",self.commit,"request",payload,"rider-a2")
        self.expect_error("INVALID_CONFIRMATION",self.commit,"cancel",payload)

    def test_confirmation_tampered_passengers_stop_or_fare(self):
        for key,value in [("passengers",2),("destination_stop_id","stop-c"),("fare",{"amount":999})]:
            draft=self.core.prepare("rider-a1","request",REQUEST)
            draft["details"][key]=value
            self.expect_error("CONFIRMATION_CHANGED",self.commit,"request",{"draft_id":draft["id"],"details":draft["details"]})
        self.assertEqual(self.sql("SELECT COUNT(*) FROM rides"),[(0,)])

    def test_expired_confirmation_rejected(self):
        draft=self.core.prepare("rider-a1","request",REQUEST)
        self.core.clock=lambda:4000000000
        self.expect_error("CONFIRMATION_EXPIRED",self.commit,"request",{"draft_id":draft["id"],"details":draft["details"]})

    def test_changed_service_price_requires_new_confirmation(self):
        draft=self.core.prepare("rider-a1","request",REQUEST)
        self.sql("UPDATE services SET fare_json=?",(json.dumps({"amount":100,"currency":"JPY"}),))
        self.expect_error("TERMS_CHANGED",self.commit,"request",{"draft_id":draft["id"],"details":draft["details"]})

    def test_changed_eligibility_checked_at_commit(self):
        draft=self.core.prepare("rider-a1","request",REQUEST)
        self.sql("UPDATE users SET eligible=0 WHERE id='rider-a1'")
        self.expect_error("INELIGIBLE",self.commit,"request",{"draft_id":draft["id"],"details":draft["details"]})

    def test_suspended_service_or_stop_rejected(self):
        self.sql("UPDATE services SET active=0")
        self.expect_error("SERVICE_UNAVAILABLE",self.create)
        self.sql("UPDATE services SET active=1")
        self.sql("UPDATE stops SET active=0 WHERE id='stop-a'")
        self.expect_error("INVALID_STOP",self.create)

    def test_operating_hours_policy_is_checked(self):
        policy={"days":[],"open":"00:00","close":"24:00","max_passengers":3}
        self.sql("UPDATE services SET policy_json=?",(json.dumps(policy),))
        self.expect_error("SERVICE_CLOSED",self.create)

    def test_invalid_counts_and_unauthorized_coordinates_rejected(self):
        for count in [0,-1,4,True,1.5,"1"]:
            self.expect_error("INVALID_PASSENGERS",self.create,passengers=count)
        self.expect_error("INVALID_INPUT",self.core.prepare,"rider-a1","request",{**REQUEST,"lat":33.0})
        self.expect_error("SAME_STOP",self.core.prepare,"rider-a1","request",{**REQUEST,"destination_stop_id":"stop-a"})

    def test_response_loss_and_operation_lookup(self):
        draft=self.core.prepare("rider-a1","request",REQUEST)
        payload={"draft_id":draft["id"],"details":draft["details"]}
        self.commit("request",payload,op="lost-response") # Intentionally discard response.
        result=self.core.operation("rider-a1","lost-response")
        retry=self.commit("request",payload,op="lost-response")
        self.assertEqual(result["current"]["id"],retry["current"]["id"])
        self.expect_error("OPERATION_NOT_FOUND",self.core.operation,"rider-a2","lost-response")

    def test_cancel_accept_race_has_single_winner(self):
        ride=self.create()
        draft=self.core.prepare("rider-a1","cancel",{"ride_id":ride["id"]})
        barrier=threading.Barrier(2)
        def job(kind):
            barrier.wait()
            try:
                if kind=="cancel":self.commit("cancel",{"draft_id":draft["id"],"details":draft["details"]})
                else:self.driver("accept",ride)
                return "ok"
            except DomainError as exc:return exc.code
        with ThreadPoolExecutor(2) as pool:results=list(pool.map(job,["cancel","accept"]))
        self.assertEqual(results.count("ok"),1)
        current=self.core.get_ride("rider-a1",ride["id"])
        self.assertIn(current["status"],["cancelled","assigned"])
        reserved=self.sql("SELECT COALESCE(SUM(reserved),0) FROM runs")[0][0]
        self.assertEqual(reserved,1 if current["status"]=="assigned" else 0)

    def test_cancel_releases_capacity_once(self):
        ride=self.driver("accept",self.create(passengers=3))
        draft=self.core.prepare("rider-a1","cancel",{"ride_id":ride["id"]})
        payload={"draft_id":draft["id"],"details":draft["details"]}
        first=self.commit("cancel",payload,op="cancel-operation")
        self.commit("cancel",payload,op="cancel-operation")
        self.assertEqual(first["current"]["status"],"cancelled")
        self.assertEqual(self.sql("SELECT reserved,active FROM runs"),[(0,0)])

    def test_cancel_after_boarding_is_rejected(self):
        ride=self.driver("board",self.driver("arrive",self.driver("accept",self.create())))
        self.expect_error("INVALID_STATE",self.core.prepare,"rider-a1","cancel",{"ride_id":ride["id"]})

    def test_driver_must_be_stopped_and_follow_order(self):
        ride=self.create()
        self.expect_error("STOP_REQUIRED",self.commit,"accept",{"ride_id":ride["id"],"version":1,"stopped":False},"driver-a1")
        self.expect_error("INVALID_STATE",self.driver,"board",ride)

    def test_driver_gets_minimum_data_and_cannot_create_rider_request(self):
        self.create()
        self.assertNotIn("rider_id",self.core.snapshot("driver-a1")["rides"][0])
        self.expect_error("FORBIDDEN",self.core.prepare,"driver-a1","request",REQUEST)

    def test_unknown_location_eta_and_price_stay_unknown(self):
        self.sql("UPDATE services SET fare_json=?",(json.dumps({"amount":None,"currency":"JPY"}),))
        ride=self.create()
        self.assertIsNone(ride["vehicle_location"])
        self.assertIsNone(ride["eta"])
        self.assertIsNone(ride["fare"]["amount"])

    def test_data_survives_core_restart_and_seed_is_non_destructive(self):
        ride=self.create()
        initialize(self.path)
        other=Core(self.path)
        self.assertEqual(other.get_ride("rider-a1",ride["id"])["id"],ride["id"])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM rides"),[(1,)])

    def test_consistent_backup_restores_rides_without_sessions(self):
        from scripts.backup_local import backup
        from app.server import Auth
        ride=self.create()
        Auth(self.path).login("rider-a1","local-test-only")
        target=Path(self.temp.name)/"restored.sqlite3"
        backup(self.path,target)
        restored=Core(target)
        self.assertEqual(restored.get_ride("rider-a1",ride["id"])["status"],"requested")
        with restored.db() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],0)
        with self.assertRaises(ValueError):backup(self.path,target)

    def test_notification_failure_retry_deduplicates_without_replaying_business(self):
        ride=self.driver("accept",self.create())
        result=self.core.deliver_fake(True)
        self.assertEqual(result["delivered"],0)
        self.assertEqual(self.core.get_ride("rider-a1",ride["id"])["status"],"assigned")
        self.core.deliver_fake();self.core.deliver_fake()
        self.assertEqual(self.sql("SELECT COUNT(*) FROM fake_inbox"),[(2,)])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM events"),[(2,)])

    def test_changed_price_after_request_prevents_acceptance(self):
        ride=self.create()
        self.sql("UPDATE services SET fare_json=?",(json.dumps({"amount":100,"currency":"JPY"}),))
        self.expect_error("TERMS_CHANGED",self.driver,"accept",ride)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM runs"),[(0,)])

    def test_different_route_or_departed_run_cannot_accept(self):
        assigned=self.driver("accept",self.create())
        draft=self.core.prepare("rider-a2","request",{**REQUEST,"destination_stop_id":"stop-c"})
        other=self.commit("request",{"draft_id":draft["id"],"details":draft["details"]},"rider-a2")["current"]
        self.expect_error("RUN_UNAVAILABLE",self.driver,"accept",other)
        self.driver("arrive",assigned)
        self.expect_error("RUN_UNAVAILABLE",self.driver,"accept",self.create("rider-a2"))

    def test_replay_reports_historical_and_current_state_separately(self):
        draft=self.core.prepare("rider-a1","request",REQUEST)
        payload={"draft_id":draft["id"],"details":draft["details"]}
        result=self.commit("request",payload,op="operation-replay")
        self.driver("accept",result["current"])
        replay=self.commit("request",payload,op="operation-replay")
        self.assertEqual(replay["result"]["status"],"requested")
        self.assertEqual(replay["current"]["status"],"assigned")

    def test_transaction_rolls_back_ride_if_outbox_insert_fails(self):
        self.sql("CREATE TRIGGER block_outbox BEFORE INSERT ON outbox BEGIN SELECT RAISE(ABORT,'test'); END")
        with self.assertRaises(Exception):self.create()
        self.assertEqual(self.sql("SELECT COUNT(*) FROM rides"),[(0,)])
        self.assertEqual(self.sql("SELECT SUM(consumed) FROM drafts"),[(0,)])

if __name__=="__main__":unittest.main()
