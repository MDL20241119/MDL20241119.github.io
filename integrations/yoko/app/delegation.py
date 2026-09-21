"""Local-only, short-lived client grants issued by the authenticated owner.

External clients cannot prepare drafts, issue grants or change the authorized
operation. Mutations recheck the grant within the Core transaction.
"""
import hashlib
import json
import re
import secrets
from .core import exact, fail, identifier, iso, packed, uid
from .catalog import CATALOG_COMMANDS, ADMIN_COMMANDS, DRIVER_COMMANDS

AUDIENCE = "yoko-local-mobility"
SCOPES = {"mobility:read", "mobility:execute"}

def verify_grant(db, actor_id, authorization, now, operation=None):
    if 'web_session' in authorization:
        row = db.execute('SELECT s.actor_id,s.expires_at,i.active FROM sessions s JOIN external_sessions x ON x.token_hash=s.token_hash JOIN external_identities i ON i.id=x.identity_id WHERE s.token_hash=?', (authorization['web_session'],)).fetchone()
        if not row or row['actor_id'] != actor_id or not row['active'] or row['expires_at'] <= now:
            fail('UNAUTHENTICATED', '本人のログインが失効しています', 401)
        return row
    if 'external' in authorization:
        from .external_auth import verify_external
        row = verify_external(db, actor_id, authorization, now, operation)
        verify_task_fence(db, actor_id, authorization, row, now)
        return row
    row = db.execute("SELECT g.*,u.active FROM client_grants g JOIN users u ON u.id=g.actor_id WHERE g.token_hash=?",
                     (authorization["token_hash"],)).fetchone()
    if not row or row["actor_id"]!=actor_id or not row["active"] or row["revoked"] or row["expires_at"]<=now:
        fail("INVALID_GRANT","代理権限が失効しています。本人の画面で結果を照合してください",401)
    if row["client_id"]!=authorization["client_id"] or row["audience"]!=AUDIENCE:
        fail("GRANT_TARGET_MISMATCH","このクライアント・接続先では使用できません",403)
    scope="mobility:execute" if operation is not None else "mobility:read"
    if scope not in json.loads(row["scopes_json"]):
        fail("INSUFFICIENT_SCOPE","この操作を委任されていません",403)
    if operation is not None and row["operation_json"]!=packed(operation):
        fail("APPROVAL_MISMATCH","承認された操作ID・内容と一致しません",403)
    # Internal A2A execution fence, constructed only by Core.tasks. It is checked
    # inside the same write transaction as the booking mutation. A stale worker
    # cannot act after its task was recovered, canceled or reclaimed.
    verify_task_fence(db, actor_id, authorization, row, now)
    return row

def verify_task_fence(db, actor_id, authorization, row, now):
    guard = authorization.get('task_execution')
    if guard:
        task = db.execute('SELECT * FROM agent_tasks WHERE id=? AND actor_id=? AND client_id=?',
            (guard['id'], actor_id, row['client_id'])).fetchone()
        if not task or task['state'] != 'working' or task['lease_owner'] != guard['lease_owner'] or task['lease_until'] <= now:
            fail('TASK_LEASE_LOST', '処理権限が更新されました。同じTaskの結果を照会してください', 409)

class Grants:
    def __init__(self,core):
        self.core=core

    def issue(self,actor_id,data,authorization=None):
        exact(data,["client_id","scopes","expires_in","operation"])
        if not isinstance(data["client_id"],str) or not re.fullmatch(r"[a-zA-Z0-9_-]{3,80}",data["client_id"]):
            fail("INVALID_CLIENT","クライアントIDの形式が不正です")
        scopes=data["scopes"]
        if not isinstance(scopes,list) or not scopes or not all(isinstance(s,str) for s in scopes) or len(scopes)!=len(set(scopes)) or not set(scopes)<=SCOPES:
            fail("INVALID_SCOPE","委任する権限の指定が不正です")
        if "mobility:read" not in scopes or type(data["expires_in"]) is not int or not 1<=data["expires_in"]<=300:
            fail("INVALID_GRANT","読取権限と1〜300秒の有効期間が必要です")
        operation=data["operation"]
        with self.core.db(True) as db:
            self.core.actor(db,actor_id)
            self.core.check_authorization(db,actor_id,authorization)
            expiry=self.core.clock()+data["expires_in"]
            if "mobility:execute" in scopes:
                exact(operation,["operation_id","idempotency_key","kind","payload"])
                identifier(operation["operation_id"]); identifier(operation["idempotency_key"])
                if not isinstance(operation['kind'],str) or operation["kind"] not in {"request","change","cancel","book"}|CATALOG_COMMANDS:
                    fail("INVALID_APPROVAL","対応する操作の個別承認が必要です")
                role='admin' if operation['kind'] in ADMIN_COMMANDS else ('driver' if operation['kind'] in DRIVER_COMMANDS else 'rider')
                self.core.actor(db,actor_id,role)
                self.core.check_draft(db,{"id":actor_id},operation["kind"],operation["payload"])
                draft=db.execute("SELECT expires_at FROM drafts WHERE id=?",(operation["payload"]["draft_id"],)).fetchone()
                expiry=min(expiry,draft[0])
            elif operation is not None:
                fail("INVALID_APPROVAL","読取専用の権限には実行操作を含められません")
            grant_id,token=uid("grant"),secrets.token_urlsafe(32)
            db.execute("INSERT INTO client_grants VALUES (?,?,?,?,?,?,?,?,0,?)",
                (grant_id,hashlib.sha256(token.encode()).hexdigest(),actor_id,data["client_id"],AUDIENCE,packed(sorted(scopes)),packed(operation) if operation is not None else None,expiry,iso(self.core.clock())))
            return {"grant_id":grant_id,"access_token":token,"token_type":"Bearer","client_id":data["client_id"],
                    "audience":AUDIENCE,"scopes":sorted(scopes),"expires_at":iso(expiry),"mode":"local_synthetic"}

    def resolve(self,header,client_id):
        if not header or not header.startswith("Bearer ") or not 20<=len(header[7:])<=200 or not client_id:
            fail("UNAUTHENTICATED","クライアント専用のBearer認証が必要です",401)
        authorization={"token_hash":hashlib.sha256(header[7:].encode()).hexdigest(),"client_id":client_id}
        with self.core.db() as db:
            row=db.execute("SELECT actor_id FROM client_grants WHERE token_hash=?",(authorization["token_hash"],)).fetchone()
            if not row:
                fail("INVALID_GRANT","代理権限を確認できません",401)
            grant=verify_grant(db,row[0],authorization,self.core.clock())
            return row[0],authorization,json.loads(grant["operation_json"]) if grant["operation_json"] else None

    def revoke(self,actor_id,grant_id,authorization=None):
        with self.core.db(True) as db:
            self.core.actor(db,actor_id)
            self.core.check_authorization(db,actor_id,authorization)
            row=db.execute("SELECT id FROM client_grants WHERE id=? AND actor_id=?",(grant_id,actor_id)).fetchone()
            if not row:
                fail("NOT_FOUND","委任情報が見つかりません",404)
            db.execute("UPDATE client_grants SET revoked=1 WHERE id=?",(grant_id,))
            return {"revoked":True}
