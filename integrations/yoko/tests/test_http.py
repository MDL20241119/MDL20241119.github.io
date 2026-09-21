import http.client
import json
import secrets
import shutil
import socket
import tempfile
import threading
import time
import unittest
from pathlib import Path
from app.db import initialize,connect
from app.server import LocalServer,Auth
from tests.test_core import REQUEST

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.template=Path(cls.temp.name)/"template.sqlite3"
        initialize(cls.template)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def setUp(self):
        self.case=tempfile.TemporaryDirectory()
        self.path=Path(self.case.name)/"http.sqlite3"
        shutil.copyfile(self.template,self.path)
        self.start()
        self.addCleanup(self.case.cleanup)
        self.addCleanup(self.stop)

    def start(self):
        self.server=LocalServer(("127.0.0.1",0),self.path)
        self.port=self.server.server_address[1]
        self.thread=threading.Thread(target=lambda:self.server.serve_forever(poll_interval=.01),daemon=True)
        self.thread.start()

    def stop(self):
        self.server.shutdown();self.server.server_close();self.thread.join(2)

    def request(self,path,body=None,session=None,headers=None):
        conn=http.client.HTTPConnection("127.0.0.1",self.port,timeout=5)
        h={"Origin":f"http://127.0.0.1:{self.port}"}
        if session:h.update({"Cookie":session[0],"X-CSRF-Token":session[1]})
        raw=None
        if body is not None:
            h.update({"Content-Type":"application/json","X-Requested-With":"YokoLocal"})
            raw=json.dumps(body)
        h.update(headers or {})
        conn.request("POST" if body is not None else "GET",path,body=raw,headers=h)
        resp=conn.getresponse();raw=resp.read();status=resp.status;head=dict(resp.getheaders());conn.close()
        data=json.loads(raw) if head.get("Content-Type","").startswith("application/json") else raw.decode()
        return status,data,head

    def login(self,user):
        status,data,headers=self.request("/api/session",{"username":user,"password":"local-test-only"})
        self.assertEqual(status,200)
        self.assertIn("HttpOnly",headers["Set-Cookie"])
        return headers["Set-Cookie"].split(";")[0],data["csrf"]

    def create(self,session):
        status,draft,_=self.request("/api/drafts/request",REQUEST,session)
        self.assertEqual(status,200)
        op=secrets.token_hex(16)
        body={"operation_id":op,"idempotency_key":op,"payload":{"draft_id":draft["id"],"details":draft["details"]}}
        status,data,_=self.request("/api/actions/request",body,session)
        self.assertEqual(status,200)
        return data,body

    def test_http_three_clients_flow_and_restart(self):
        rider,driver,admin=[self.login(user) for user in ["rider-a1","driver-a1","admin-a1"]]
        ride,_=self.create(rider);ride=ride["current"]
        for action,target in [("accept","assigned"),("arrive","arrived"),("board","onboard"),("complete","completed")]:
            op=secrets.token_hex(16)
            code,data,_=self.request("/api/actions/"+action,{"operation_id":op,"idempotency_key":op,"payload":{"ride_id":ride["id"],"version":ride["version"],"stopped":True}},driver)
            self.assertEqual(code,200,data);ride=data["current"]
            for session in [rider,admin]:
                code,view,_=self.request("/api/rides/"+ride["id"],session=session)
                self.assertEqual(view["status"],target)
        self.stop();self.start()
        code,view,_=self.request("/api/rides/"+ride["id"],session=rider)
        self.assertEqual((code,view["status"]),(200,"completed"))

    def test_authentication_required_and_spoofed_role_rejected(self):
        self.assertEqual(self.request("/api/snapshot")[0],401)
        self.assertEqual(self.request("/api/session",{"username":"rider-a1","password":"wrong"})[0],401)
        self.assertEqual(self.request("/api/session",{"username":"admin-a1","password":"local-test-only","role":"admin"})[0],400)
        rider=self.login("rider-a1")
        self.assertEqual(self.request("/api/actions/accept",{"operation_id":"operation-test","idempotency_key":"operation-test","payload":{"ride_id":"unknown","version":1,"stopped":True}},rider)[0],403)

    def test_csrf_and_cross_origin_and_host_guards(self):
        session=self.login("rider-a1")
        for headers,code in [({"X-CSRF-Token":"wrong"},403),({"Origin":"https://evil.example"},403),({"Host":"evil.example"},403),({"X-Forwarded-For":"127.0.0.1"},403),({"X-Requested-With":""},403),({"Sec-Fetch-Site":"cross-site"},403)]:
            self.assertEqual(self.request("/api/drafts/request",REQUEST,session,headers)[0],code)

    def test_expired_or_logged_out_session_is_rejected(self):
        session=self.login("rider-a1")
        db=connect(self.path);db.execute("UPDATE sessions SET expires_at=0");db.close()
        self.assertEqual(self.request("/api/snapshot",session=session)[0],401)
        session=self.login("rider-a1")
        self.assertEqual(self.request("/api/logout",{},session)[0],200)
        self.assertEqual(self.request("/api/snapshot",session=session)[0],401)

    def test_cross_user_http_object_authorization(self):
        rider=self.login("rider-a1");other=self.login("rider-a2");tenant=self.login("rider-b1")
        data,body=self.create(rider)
        for session in [other,tenant]:
            self.assertEqual(self.request("/api/rides/"+data["current"]["id"],session=session)[0],404)
            self.assertEqual(self.request("/api/operations/"+body["operation_id"],session=session)[0],404)
            self.assertEqual(self.request("/api/drafts/cancel",{"ride_id":data["current"]["id"]},session)[0],404)

    def test_network_response_loss_can_be_reconciled(self):
        session=self.login("rider-a1")
        _,draft,_=self.request("/api/drafts/request",REQUEST,session)
        op=secrets.token_hex(16)
        body={"operation_id":op,"idempotency_key":op,"payload":{"draft_id":draft["id"],"details":draft["details"]}}
        raw=json.dumps(body).encode()
        wire=(f"POST /api/actions/request HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\nContent-Type: application/json\r\nX-Requested-With: YokoLocal\r\nCookie: {session[0]}\r\nX-CSRF-Token: {session[1]}\r\nContent-Length: {len(raw)}\r\nConnection: close\r\n\r\n").encode()+raw
        sock=socket.create_connection(("127.0.0.1",self.port));sock.sendall(wire);sock.shutdown(socket.SHUT_WR);sock.close()
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            status,result,_=self.request("/api/operations/"+op,session=session)
            if status==200:break
            time.sleep(.01)
        self.assertEqual(status,200,result)
        status,replayed,_=self.request("/api/actions/request",body,session)
        self.assertEqual(status,200)
        self.assertTrue(replayed["replayed"])
        self.assertEqual(result["current"]["id"],replayed["current"]["id"])

    def test_oversized_body_and_content_type_rejected(self):
        session=self.login("rider-a1")
        self.assertEqual(self.request("/api/drafts/request",{"data":"a"*17000},session)[0],413)
        self.assertEqual(self.request("/api/drafts/request",REQUEST,session,{"Content-Type":"text/plain"})[0],415)

    def test_malformed_inputs_fail_explicitly(self):
        session=self.login("rider-a1")
        self.assertEqual(self.request("/api/drafts/cancel",{"ride_id":[]},session)[0],400)
        self.assertEqual(self.request("/api/actions/request",{"operation_id":"valid-op-id","idempotency_key":"valid-op-id","payload":{"draft_id":[],"details":{}}},session)[0],400)

    def test_public_bind_and_production_are_disabled(self):
        for address,mode in [(('0.0.0.0',0),'local'),(('127.0.0.1',0),'production')]:
            with self.assertRaises(ValueError):LocalServer(address,self.path,mode)

    def test_external_protocols_are_not_exposed(self):
        session=self.login("rider-a1")
        for path in ["/mcp","/.well-known/agent-card.json","/reservations","/services","/gtfs.zip"]:
            self.assertEqual(self.request(path,session=session)[0],404)

    def test_static_assets_have_security_headers_and_no_directory_listing(self):
        for path in ["/","/app.js","/style.css"]:
            status,body,headers=self.request(path)
            self.assertEqual(status,200)
            self.assertEqual(headers["X-Frame-Options"],"DENY")
            self.assertIn("script-src 'self'",headers["Content-Security-Policy"])
        self.assertEqual(self.request("/var/http.sqlite3")[0],401)
        self.assertEqual(self.request("/../app/db.py")[0],401)

    def test_local_openapi_matches_generated_contract(self):
        from scripts.export_local_openapi import build
        status,contract,_=self.request("/api/openapi.json")
        self.assertEqual(status,200)
        self.assertEqual(contract,build())
        self.assertEqual(contract["openapi"],"3.1.1")

    def test_rate_limit_returns_retryable_error(self):
        with self.server.rate_lock:
            self.server.rate[("127.0.0.1","login")].extend([time.monotonic()]*30)
        status,result,_=self.request("/api/session",{"username":"rider-a1","password":"local-test-only"})
        self.assertEqual(status,429)
        self.assertTrue(result["error"]["retryable"])

if __name__=="__main__":unittest.main()
