"""Loopback-only HTTP adapter. This development server cannot serve production."""
import hashlib
import hmac
import json
import mimetypes
import secrets
import sqlite3
import threading
import time
from collections import defaultdict, deque
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs
from .core import Core, DomainError, exact, fail
from .db import ROOT, connect, password_hash
from .delegation import Grants
from .catalog import CATALOG_COMMANDS

MAX_BODY = 16384
STATIC = {"/":"index.html", "/app.js":"app.js", "/style.css":"style.css"}

class Auth:
    def __init__(self,path,clock=time.time):
        self.path,self.clock = path,clock

    def login(self,username,password):
        if not isinstance(username,str) or not isinstance(password,str) or len(username)>100 or len(password)>200:
            fail("INVALID_LOGIN","IDとパスワードを確認してください",401)
        db = connect(self.path)
        try:
            user = db.execute("SELECT * FROM users WHERE id=?",(username,)).fetchone()
            salt = user["salt"] if user else "00"*16
            actual = password_hash(password,salt)
            if not user or not user["active"] or not hmac.compare_digest(actual,user["password_hash"]):
                fail("INVALID_LOGIN","IDとパスワードを確認してください",401)
            return self.issue(username)
        finally:
            db.close()

    def issue(self,username,identity_id=None):
        db=connect(self.path)
        try:
            db.execute('BEGIN IMMEDIATE')
            user=db.execute('SELECT * FROM users WHERE id=? AND active=1',(username,)).fetchone()
            if not user: fail('UNAUTHENTICATED','利用登録を確認できません',401)
            if identity_id and not db.execute('SELECT 1 FROM external_identities WHERE id=? AND actor_id=? AND active=1',(identity_id,username)).fetchone():
                fail('UNAUTHENTICATED','利用登録を確認できません',401)
            token,csrf = secrets.token_urlsafe(32),secrets.token_urlsafe(32)
            db.execute("DELETE FROM sessions WHERE expires_at<=?",(self.clock(),))
            db.execute("INSERT INTO sessions VALUES (?,?,?,?)",(hashlib.sha256(token.encode()).hexdigest(),username,csrf,self.clock()+3600))
            if identity_id:
                db.execute('INSERT INTO external_sessions VALUES (?,?)',(hashlib.sha256(token.encode()).hexdigest(),identity_id))
            db.commit()
            return token,{"user":{"id":username,"role":user["role"],"tenant_id":user["tenant_id"]},"csrf":csrf,"mode":"local_synthetic"}
        finally:
            db.close()

    def session(self,token):
        if not token or len(token)>200:
            fail("UNAUTHENTICATED","ログインしてください",401)
        db=connect(self.path)
        try:
            row=db.execute("SELECT s.*,u.role,u.tenant_id,u.active FROM sessions s JOIN users u ON s.actor_id=u.id WHERE token_hash=? AND expires_at>?",(hashlib.sha256(token.encode()).hexdigest(),self.clock())).fetchone()
            if not row or not row["active"]:
                fail("UNAUTHENTICATED","ログインの有効期限が切れました",401)
            linked=db.execute('SELECT i.active,i.actor_id FROM external_sessions s JOIN external_identities i ON i.id=s.identity_id WHERE s.token_hash=?',(row['token_hash'],)).fetchone()
            if linked and (not linked['active'] or linked['actor_id']!=row['actor_id']):
                fail('UNAUTHENTICATED','利用登録を確認できません',401)
            return dict(row)
        finally:
            db.close()

    def logout(self,token):
        db=connect(self.path)
        try:
            db.execute("DELETE FROM sessions WHERE token_hash=?",(hashlib.sha256(token.encode()).hexdigest(),))
        finally:
            db.close()

class LocalServer(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,address,path,mode="local",enable_mlit=False):
        if mode!="local" or address[0]!="127.0.0.1":
            raise ValueError("Only local synthetic mode on 127.0.0.1 is supported; public hosting is disabled")
        self.core,self.auth=Core(path),Auth(path)
        self.grants=Grants(self.core)
        self.mlit=None
        if enable_mlit:
            from .mlit import MLIT
            self.mlit=MLIT(self.core)
        self.rate=defaultdict(deque)
        self.rate_lock=threading.Lock()
        super().__init__(address,Handler)

class Handler(BaseHTTPRequestHandler):
    server_version="YokoLocal/0.1"
    sys_version=""
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self,format,*args):
        # Do not log request URLs, cookies, tokens or passenger history.
        pass

    def reply(self,status,data,content_type="application/json; charset=utf-8",cookie=None):
        raw=b'' if status==204 else json.dumps(data,ensure_ascii=False,allow_nan=False).encode() if content_type.startswith("application/json") else data
        self.send_response(status)
        self.send_header("Content-Type",content_type)
        self.send_header("Content-Length",str(len(raw)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Referrer-Policy","no-referrer")
        self.send_header("X-Frame-Options","DENY")
        self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        if cookie:
            self.send_header("Set-Cookie",cookie)
        self.end_headers()
        self.wfile.write(raw)

    def guard(self,path):
        port=self.server.server_address[1]
        allowed={f"127.0.0.1:{port}",f"localhost:{port}"}
        if self.client_address[0]!="127.0.0.1" or self.headers.get("Host") not in allowed:
            fail("LOCAL_ONLY","このテスト環境はローカル接続専用です",403)
        if any(self.headers.get(k) for k in ("Forwarded","X-Forwarded-For","X-Forwarded-Host")):
            fail("LOCAL_ONLY","プロキシ経由の公開には対応していません",403)
        origin=self.headers.get("Origin")
        if origin and origin!=f"http://{self.headers.get('Host')}":
            fail("ORIGIN_REJECTED","別のサイトからの操作はできません",403)
        if self.headers.get("Sec-Fetch-Site") in ("cross-site","same-site"):
            fail("ORIGIN_REJECTED","同一画面から操作してください",403)
        bucket="login" if path=="/api/session" else "requests"
        limit=30 if bucket=="login" else 600
        with self.server.rate_lock:
            q=self.server.rate[(self.client_address[0],bucket)]
            now=time.monotonic()
            while q and q[0]<now-60:
                q.popleft()
            if len(q)>=limit:
                fail("RATE_LIMITED","操作が集中しています。1分後に同じ操作IDで結果を確認してください",429)
            q.append(now)

    def body(self,client=False):
        if self.headers.get("Transfer-Encoding"):
            fail("INVALID_BODY","分割されたリクエストには対応していません",400)
        if self.headers.get("Content-Type","").split(";")[0]!="application/json":
            fail("INVALID_CONTENT_TYPE","JSON形式で送信してください",415)
        if not client and self.headers.get("X-Requested-With")!="YokoLocal":
            fail("ORIGIN_REJECTED","対応する画面から操作してください",403)
        try:
            length=int(self.headers.get("Content-Length","-1"))
        except ValueError:
            length=-1
        if not 0<=length<=MAX_BODY:
            fail("BODY_TOO_LARGE","リクエストの大きさが不正です",413)
        def reject_constant(value):
            raise ValueError(value)
        try:
            data=json.loads(self.rfile.read(length),parse_constant=reject_constant)
        except (ValueError,UnicodeDecodeError):
            fail("INVALID_JSON","JSONを読み取れません")
        if not isinstance(data,dict):
            fail("INVALID_INPUT","JSONオブジェクトが必要です")
        return data

    def authenticate(self,write=False):
        jar=SimpleCookie()
        try:
            jar.load(self.headers.get("Cookie",""))
            token=jar["yoko_session"].value if "yoko_session" in jar else None
        except Exception:
            token=None
        session=self.server.auth.session(token)
        if write and not hmac.compare_digest(session["csrf"],self.headers.get("X-CSRF-Token","")):
            fail("CSRF_REJECTED","確認情報が無効です。画面を再読み込みしてください",403)
        return session,token

    def do_GET(self):
        self.dispatch(False)

    def do_POST(self):
        self.dispatch(True)

    def do_PUT(self):
        self.dispatch(True)

    def do_DELETE(self):
        self.dispatch(True)

    def do_OPTIONS(self):
        self.reply(405,{"error":{"code":"METHOD_NOT_ALLOWED","message":"CORS is disabled"}})

    def dispatch(self,write):
        matched=None
        try:
            url=urlsplit(self.path)
            path=url.path
            if self.server.mlit:
                matched=self.server.mlit.contract.match(self.command,path)
            if url.fragment or (url.query and not matched and not path.startswith("/direct/v1/")):
                fail("INVALID_URL","クエリ付きURLには対応していません")
            self.guard(path)
            if matched or path.startswith("/direct/v1/"):
                actor,authorization,approved=self.server.grants.resolve(self.headers.get("Authorization"),self.headers.get("X-Client-ID"))
                has_body=self.command in ("POST","PUT") or self.headers.get("Content-Length") not in (None,"0")
                data=self.body(client=True) if has_body else None
                if matched:
                    status,result=self.server.mlit.execute(matched,url.query,data,actor,authorization,approved,self.headers)
                    self.server.mlit.contract.response(matched,status,result)
                    self.reply(status,result)
                else:
                    result=self.direct(path,url.query,data,actor,authorization)
                    self.reply(200,result)
                return
            if self.command not in ("GET","POST"):
                fail("NOT_FOUND","この機能は実装・公開されていません",404)
            if not write and path in STATIC:
                name=STATIC[path]
                mime={"index.html":"text/html","app.js":"text/javascript","style.css":"text/css"}[name]
                self.reply(200,(ROOT/"app/static"/name).read_bytes(),mime+"; charset=utf-8")
                return
            if not write and path=="/api/openapi.json":
                self.reply(200,json.loads((ROOT/"api/mdl-local.openapi.json").read_text()))
                return
            data=self.body() if write else None
            if write and path=="/api/session":
                exact(data,["username","password"])
                token,result=self.server.auth.login(data["username"],data["password"])
                self.reply(200,result,cookie=f"yoko_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=3600")
                return
            session,token=self.authenticate(write)
            actor=session["actor_id"]
            if not write and path=="/api/me":
                result={"user":{"id":actor,"role":session["role"],"tenant_id":session["tenant_id"]},"csrf":session["csrf"],"mode":"local_synthetic"}
            elif not write and path=="/api/snapshot":
                result=self.server.core.snapshot(actor)
            elif not write and path=="/api/catalog":
                result=self.server.core.catalog.snapshot(actor)
            elif write and path=='/api/candidates':
                result=self.server.core.booking.search(actor,data)
            elif not write and path.startswith("/api/rides/"):
                result=self.server.core.get_ride(actor,path.removeprefix("/api/rides/"))
            elif not write and path.startswith('/api/payments/'):
                result=self.server.core.payments.read(actor,path.removeprefix('/api/payments/'))
            elif not write and path.startswith("/api/operations/"):
                result=self.server.core.operation(actor,path.removeprefix("/api/operations/"))
            elif write and path=="/api/logout":
                exact(data,[])
                self.server.auth.logout(token)
                self.reply(200,{"logged_out":True},cookie="yoko_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
                return
            elif write and path=="/api/client-grants":
                result=self.server.grants.issue(actor,data)
            elif write and path=="/api/client-grants/revoke":
                exact(data,["grant_id"])
                result=self.server.grants.revoke(actor,data["grant_id"])
            elif write and path in tuple('/api/drafts/'+k for k in ({'request','cancel','change','book'}|CATALOG_COMMANDS)):
                result=self.server.core.prepare(actor,path.rsplit("/",1)[1],data)
            elif write and path in tuple("/api/actions/"+a for a in ({"request","cancel","change","book","accept","arrive","board","complete"}|CATALOG_COMMANDS)):
                exact(data,["operation_id","idempotency_key","payload"])
                result=self.server.core.mutate(actor,data["operation_id"],data["idempotency_key"],path.rsplit("/",1)[1],data["payload"])
            else:
                fail("NOT_FOUND","この機能は実装・公開されていません",404)
            self.reply(200,result)
        except DomainError as e:
            self.error(e,matched)
        except sqlite3.OperationalError:
            self.error(DomainError("STORAGE_BUSY","保存結果を確認できません。同じ操作IDで照合してください",503),matched)
        except (TypeError,ValueError,KeyError):
            self.error(DomainError("INVALID_INPUT","入力の形式を確認してください",400),matched)
        except (BrokenPipeError,ConnectionResetError):
            pass
        except Exception:
            self.error(DomainError("INTERNAL_ERROR","処理結果を確認できません。同じ操作IDで照合してください",500),matched)

    def error(self,error,matched):
        if matched:
            status,result=self.server.mlit.contract.problem(matched,error)
            self.reply(status,result)
        else:
            self.reply(error.status,{"error":{"code":error.code,"message":error.message,"retryable":error.status in (429,503)}})

    def direct(self,path,query,data,actor,authorization):
        from .direct_api import dispatch
        return dispatch(self.server.core,self.command,path,query,data,actor,authorization)
