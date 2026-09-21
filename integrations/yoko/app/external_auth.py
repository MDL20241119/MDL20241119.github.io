"""LINE Login and OAuth resource authentication for opt-in HTTPS integration tests.

Provider endpoints and credentials come only from operator configuration. No URL
from an incoming token, message or claim is fetched. Provider replies are never
logged or forwarded to an agent. Business authorization remains in Core.
"""
import base64
import hashlib
import hmac
import json
import math
import re
import secrets
import ssl
from urllib.parse import urlencode, urlsplit

import httpx

from .core import exact, fail, packed, uid
from .delegation import Grants


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def https_url(value):
    if not isinstance(value, str) or len(value) > 2048 or any(c.isspace() for c in value):
        raise ValueError('A configured HTTPS URL is required')
    u = urlsplit(value)
    if u.scheme != 'https' or not u.hostname or u.username or u.password or u.query or u.fragment or '%' in u.netloc or '\\' in value:
        raise ValueError('HTTPS URLs must have no credentials, query or fragment')
    _ = u.port
    return value


def text_value(value, maximum=512):
    return isinstance(value, str) and 0 < len(value) <= maximum and not any(ord(c) < 32 for c in value)


def epoch(value):
    return type(value) in (int, float) and math.isfinite(value)


class ProviderHTTP:
    """TLS verification, fixed endpoints, bounded body, no redirects or retries."""
    def __init__(self, ca_file=None):
        self.context = ssl.create_default_context(cafile=ca_file)

    def post(self, endpoint, data, basic=None):
        https_url(endpoint)
        try:
            with httpx.Client(verify=self.context, trust_env=False, timeout=5, follow_redirects=False) as client:
                with client.stream('POST', endpoint, data=data, auth=basic, headers={'Accept': 'application/json'}) as response:
                    if response.status_code != 200:
                        fail('PROVIDER_REJECTED', '認証先で確認できませんでした。再度ログインしてください', 401 if response.status_code in (400, 401, 403) else 503)
                    if response.headers.get('content-type', '').split(';')[0] != 'application/json':
                        fail('PROVIDER_UNAVAILABLE', '認証先の応答を確認できません', 503)
                    raw = b''
                    for chunk in response.iter_bytes(chunk_size=8192):
                        raw += chunk
                        if len(raw) > 32768:
                            fail('PROVIDER_UNAVAILABLE', '認証先の応答を確認できません', 503)
                    def unique(pairs):
                        obj = {}
                        for key, value in pairs:
                            if key in obj: raise ValueError('Duplicate key')
                            obj[key] = value
                        return obj
                    value = json.loads(raw, object_pairs_hook=unique, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
                    if not isinstance(value, dict): raise ValueError('Object required')
                    return value
        except (httpx.HTTPError, ValueError, UnicodeDecodeError):
            fail('PROVIDER_UNAVAILABLE', '認証先に接続できません。時間をおいて確認してください', 503)


class Identities:
    def __init__(self, core): self.core = core

    def bind(self, issuer, audience, subject, actor):
        """Operator-only enrollment. Never exposed as a self-registration API."""
        https_url(issuer)
        if not text_value(audience, 2048) or not text_value(subject): raise ValueError('Invalid identity')
        with self.core.db(True) as db:
            self.core.actor(db, actor)
            existing = db.execute('SELECT * FROM external_identities WHERE issuer=? AND audience=? AND subject=?', (issuer, audience, subject)).fetchone()
            if existing:
                if existing['actor_id'] == actor and existing['active']: return existing['id']
                fail('IDENTITY_CONFLICT', '既存の本人対応付けは上書きできません', 409)
            identity = uid('identity')
            db.execute('INSERT INTO external_identities VALUES (?,?,?,?,?,1)', (identity, issuer, audience, subject, actor))
            return identity

    def revoke(self, identity):
        with self.core.db(True) as db:
            if not db.execute('SELECT 1 FROM external_identities WHERE id=?', (identity,)).fetchone():
                fail('NOT_FOUND', '対応付けが見つかりません', 404)
            db.execute('UPDATE external_identities SET active=0 WHERE id=?', (identity,))
            db.execute('UPDATE client_grants SET revoked=1 WHERE id IN (SELECT grant_id FROM oauth_approvals WHERE identity_id=?)', (identity,))
            db.execute('DELETE FROM sessions WHERE token_hash IN (SELECT token_hash FROM external_sessions WHERE identity_id=?)', (identity,))
        return {'revoked': True}


def identity_row(db, issuer, audience, subject):
    row = db.execute('SELECT i.*,u.active AS user_active FROM external_identities i JOIN users u ON u.id=i.actor_id WHERE i.issuer=? AND i.audience=? AND i.subject=?', (issuer, audience, subject)).fetchone()
    if not row or not row['active'] or not row['user_active']:
        fail('IDENTITY_NOT_ENROLLED', '利用登録を確認できません。運営担当者に確認してください', 403)
    return row


class LineLogin:
    ISSUER = 'https://access.line.me'
    AUTHORIZE = 'https://access.line.me/oauth2/v2.1/authorize'
    TOKEN = 'https://api.line.me/oauth2/v2.1/token'
    VERIFY = 'https://api.line.me/oauth2/v2.1/verify'

    def __init__(self, core, auth, channel_id, secret, redirect_uri, http=None):
        if not text_value(channel_id, 100) or not text_value(secret, 512): raise ValueError('LINE channel credentials are required')
        self.core, self.auth, self.channel_id, self.secret = core, auth, channel_id, secret
        self.redirect_uri = https_url(redirect_uri)
        self.http = http or ProviderHTTP()

    def begin(self):
        browser, nonce, verifier = [secrets.token_urlsafe(32) for _ in range(3)]
        # LINE state is alphanumeric; nonce/verifier may use base64url characters.
        state = secrets.token_hex(32)
        with self.core.db(True) as db:
            db.execute('DELETE FROM login_flows WHERE expires_at<=?', (self.core.clock(),))
            if db.execute('SELECT COUNT(*) FROM login_flows').fetchone()[0] >= 100:
                fail('LOGIN_BUSY', 'ログインが集中しています。しばらくお待ちください', 429)
            db.execute('INSERT INTO login_flows VALUES (?,?,?,?,?)', (digest(state), digest(browser), nonce, verifier, self.core.clock()+300))
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
        params = {'response_type': 'code', 'client_id': self.channel_id, 'redirect_uri': self.redirect_uri,
            'state': state, 'nonce': nonce, 'scope': 'openid', 'code_challenge': challenge, 'code_challenge_method': 'S256'}
        return self.AUTHORIZE+'?'+urlencode(params), browser

    def complete(self, state, browser, code=None, error=None):
        if not text_value(state, 100) or not text_value(browser, 100):
            fail('LOGIN_STATE_REJECTED', '同じブラウザーでログインをやり直してください', 401)
        with self.core.db(True) as db:
            flow = db.execute('SELECT * FROM login_flows WHERE state_hash=?', (digest(state),)).fetchone()
            if not flow or flow['expires_at'] <= self.core.clock() or not hmac.compare_digest(flow['browser_hash'], digest(browser)):
                fail('LOGIN_STATE_REJECTED', 'ログイン情報の有効期限を確認できません', 401)
            # Consume before network I/O. A failed exchange must start a new flow.
            db.execute('DELETE FROM login_flows WHERE state_hash=?', (digest(state),))
        if error or not text_value(code, 2048):
            fail('LOGIN_CANCELLED', 'ログインが完了していません。もう一度操作してください', 401)
        response = self.http.post(self.TOKEN, {'grant_type': 'authorization_code', 'code': code,
            'redirect_uri': self.redirect_uri, 'client_id': self.channel_id, 'client_secret': self.secret, 'code_verifier': flow['verifier']})
        if not text_value(response.get('id_token'), 16384):
            fail('INVALID_ID_TOKEN', '本人確認の応答を確認できません', 401)
        claims = self.http.post(self.VERIFY, {'id_token': response['id_token'], 'client_id': self.channel_id, 'nonce': flow['nonce']})
        now = self.core.clock()
        if (claims.get('iss') != self.ISSUER or claims.get('aud') != self.channel_id or claims.get('nonce') != flow['nonce']
                or not text_value(claims.get('sub')) or not epoch(claims.get('exp')) or claims['exp'] <= now
                or not epoch(claims.get('iat')) or claims['iat'] > now+30 or claims['iat'] > claims['exp']):
            fail('INVALID_ID_TOKEN', '本人確認の応答を確認できません', 401)
        with self.core.db() as db:
            row = identity_row(db, self.ISSUER, self.channel_id, claims['sub'])
        # Only the enrolled actor is used. Email, display name and role claims are ignored.
        return self.auth.issue(row['actor_id'], row['id'])


class OAuthGrants:
    def __init__(self, core, issuer, resource, introspection, client_id, secret, trusted_clients, http=None):
        self.core, self.issuer, self.resource = core, https_url(issuer), https_url(resource)
        self.endpoint, self.basic = https_url(introspection), (client_id, secret)
        if not text_value(client_id) or not text_value(secret): raise ValueError('Introspection credentials are required')
        self.clients = frozenset(trusted_clients)
        if not self.clients or any(not re.fullmatch(r'[a-zA-Z0-9_-]{3,80}', c) for c in self.clients): raise ValueError('Preregistered client IDs are required')
        self.http = http or ProviderHTTP()
        u = urlsplit(self.resource)
        self.metadata_url = f'{u.scheme}://{u.netloc}/.well-known/oauth-protected-resource{u.path}'

    def metadata(self):
        return {'resource': self.resource, 'authorization_servers': [self.issuer],
            'scopes_supported': ['mobility:read', 'mobility:execute'], 'bearer_methods_supported': ['header']}

    def challenge(self):
        return f'Bearer resource_metadata="{self.metadata_url}", scope="mobility:read"'

    def issue(self, actor, data, authorization=None):
        exact(data, ['identity_id', 'client_id', 'operation', 'expires_in'])
        if data['client_id'] not in self.clients: fail('UNTRUSTED_CLIENT', '事前登録された接続先を選んでください', 403)
        with self.core.db() as db:
            self.core.check_authorization(db, actor, authorization)
            row = db.execute('SELECT * FROM external_identities WHERE id=?', (data['identity_id'],)).fetchone()
            if not row or row['actor_id'] != actor or not row['active'] or row['issuer'] != self.issuer or row['audience'] != self.resource:
                fail('IDENTITY_NOT_ENROLLED', '本人の接続先登録を確認できません', 403)
        # Reuse the existing owner/draft/role/expiry validation. The generated
        # local bearer is discarded and never exposed through this interface.
        grant = Grants(self.core).issue(actor, {'client_id': data['client_id'], 'operation': data['operation'],
            'expires_in': data['expires_in'], 'scopes': ['mobility:read', 'mobility:execute']}, authorization)
        with self.core.db(True) as db:
            row = identity_row(db, self.issuer, self.resource, row['subject'])
            db.execute('INSERT INTO oauth_approvals VALUES (?,?,?)', (grant['grant_id'], row['id'], self.resource))
        from .agent_tasks import operation_reference
        return {'approval_id': grant['grant_id'], 'resource': self.resource, 'client_id': data['client_id'],
            'expires_at': grant['expires_at'], 'a2a_data': operation_reference(data['operation'])}

    def resolve(self, header, client_id=None, approval_id=None):
        if not isinstance(header, str) or not re.fullmatch(r'Bearer [A-Za-z0-9._~+/=-]{20,4096}', header):
            fail('UNAUTHENTICATED', 'OAuthアクセストークンが必要です', 401)
        claims = self.http.post(self.endpoint, {'token': header[7:], 'token_type_hint': 'access_token'}, basic=self.basic)
        now = self.core.clock()
        audience = claims.get('aud')
        if (claims.get('active') is not True or claims.get('iss') != self.issuer
                or not (audience == self.resource or isinstance(audience, list) and self.resource in audience and all(isinstance(a, str) for a in audience))
                or not text_value(claims.get('sub')) or not epoch(claims.get('exp')) or claims['exp'] <= now
                or not epoch(claims.get('iat')) or claims['iat'] > now+30
                or ('nbf' in claims and (not epoch(claims['nbf']) or claims['nbf'] > now))
                or not isinstance(claims.get('token_type'), str) or claims['token_type'].lower() != 'bearer' or not text_value(claims.get('scope'), 2048)):
            fail('INVALID_TOKEN', '接続先・期限・発行元を確認できないトークンです', 401)
        verified_client = claims.get('client_id')
        if not isinstance(verified_client, str) or verified_client not in self.clients or client_id is not None and client_id != verified_client:
            fail('UNTRUSTED_CLIENT', '認証された接続元と一致しません', 403)
        scopes = claims['scope'].split()
        if 'mobility:read' not in scopes: fail('INSUFFICIENT_SCOPE', '読取権限が必要です', 403)
        with self.core.db() as db:
            row = identity_row(db, self.issuer, self.resource, claims['sub'])
            authorization = {'client_id': verified_client, 'external': {'identity_id': row['id'], 'issuer': self.issuer,
                'subject': claims['sub'], 'resource': self.resource, 'exp': min(claims['exp'], now+15),
                'scopes': scopes, 'approval_id': approval_id}}
            grant = verify_external(db, row['actor_id'], authorization, now)
            return row['actor_id'], authorization, json.loads(grant['operation_json']) if grant['operation_json'] else None


def verify_external(db, actor_id, authorization, now, operation=None):
    """Recheck mapping, token lease and exact revocable approval inside Core tx.

This object is created only from a successful authenticated introspection. It is
never decoded from HTTP JSON and is retained for at most 15 seconds, including
queued A2A work. Every new HTTP request introspects again; no token is cached.
"""
    value = authorization['external']
    identity = identity_row(db, value['issuer'], value['resource'], value['subject'])
    if identity['id'] != value['identity_id'] or identity['actor_id'] != actor_id or value['exp'] <= now:
        fail('INVALID_TOKEN', '本人の接続権限が失効しています', 401)
    scope = 'mobility:execute' if operation is not None else 'mobility:read'
    if scope not in value['scopes']: fail('INSUFFICIENT_SCOPE', 'この操作を委任されていません', 403)
    approval = None
    if value['approval_id']:
        approval = db.execute('SELECT g.*,a.identity_id,a.resource FROM client_grants g JOIN oauth_approvals a ON a.grant_id=g.id WHERE g.id=?', (value['approval_id'],)).fetchone()
        if (not approval or approval['revoked'] or approval['expires_at'] <= now or approval['actor_id'] != actor_id
                or approval['identity_id'] != identity['id'] or approval['resource'] != value['resource'] or approval['client_id'] != authorization['client_id']):
            fail('INVALID_APPROVAL', '本人の個別承認が失効しているか、接続先が異なります', 403)
    elif operation is not None:
        # Standard SDK/AI-host transports need only OAuth. Resolve an exact,
        # existing owner approval from the operation; never infer approval from
        # the token's execute scope or from the model's statement of consent.
        approval = db.execute('SELECT g.* FROM client_grants g JOIN oauth_approvals a ON a.grant_id=g.id WHERE g.actor_id=? AND g.client_id=? AND a.identity_id=? AND a.resource=? AND g.operation_json=? AND g.revoked=0 AND g.expires_at>? ORDER BY g.expires_at DESC LIMIT 1',
            (actor_id, authorization['client_id'], identity['id'], value['resource'], packed(operation), now)).fetchone()
    if operation is not None and (not approval or approval['operation_json'] != packed(operation)):
        fail('APPROVAL_MISMATCH', '本人が承認した操作ID・内容と一致しません', 403)
    scopes = ['mobility:read'] + (['mobility:execute'] if approval and 'mobility:execute' in value['scopes'] else [])
    return {'client_id': authorization['client_id'], 'scopes_json': packed(scopes),
        'operation_json': approval['operation_json'] if approval else None}


def bind_task_approval(db, actor_id, authorization, reference, now):
    """Core-only resolution of A2A's exact operation reference, under its tx."""
    from .agent_tasks import operation_reference
    verify_external(db, actor_id, authorization, now)
    value = authorization['external']
    if value['approval_id'] or 'mobility:execute' not in value['scopes']: return authorization
    rows = db.execute("SELECT g.id,g.operation_json FROM client_grants g JOIN oauth_approvals a ON a.grant_id=g.id WHERE g.actor_id=? AND g.client_id=? AND a.identity_id=? AND a.resource=? AND g.revoked=0 AND g.expires_at>? AND json_extract(g.operation_json,'$.operation_id')=? ORDER BY g.expires_at DESC",
        (actor_id, authorization['client_id'], value['identity_id'], value['resource'], now, reference['operation_id']))
    for row in rows:
        if operation_reference(json.loads(row['operation_json'])) == reference:
            return {**authorization, 'external': {**value, 'approval_id': row['id']}}
    return authorization
