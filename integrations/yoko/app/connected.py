"""Opt-in HTTPS integration stack. Loopback only; synthetic business data only.

Runs real LINE/OAuth client code with registered providers. Default/password
login is disabled here. This is not a public production hosting profile.
"""
import hmac
import html
import json
import os
import sqlite3
import time
from collections import deque
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path
from urllib.parse import urlsplit

import anyio
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from .catalog import CATALOG_COMMANDS
from .core import Core, DomainError, exact, fail
from .db import ROOT
from .delegation import Grants
from .direct_api import dispatch as direct
from .external_auth import LineLogin, OAuthGrants, ProviderHTTP, digest, https_url
from .server import Auth, MAX_BODY, STATIC

COOKIE = '__Host-yoko_session'
FLOW_COOKIE = '__Secure-yoko_login'


def configuration(path):
    value = json.loads(Path(path).read_text())
    exact(value, ['origin', 'line_channel_id', 'line_secret_env', 'oauth_issuer', 'oauth_discovery_url',
        'oauth_introspection_url', 'oauth_client_id', 'oauth_secret_env', 'trusted_clients', 'ca_file'])
    for name in ('line_secret_env', 'oauth_secret_env'):
        env = value.pop(name)
        if not isinstance(env, str) or not env.startswith('YOKO_'):
            raise ValueError('Use a YOKO_ environment variable for credentials')
        value[name.removesuffix('_env')] = os.environ.get(env, '')
    return value


def create_app(core, config, line_factory=LineLogin, card_signer=None):
    from .mcp_adapter import create_app as mcp_app
    from .a2a_adapter import create_app as a2a_app
    if os.environ.get('YOKO_ENV', 'local') != 'local': raise ValueError('Public hosting is disabled')
    origin = https_url(config['origin'])
    url = urlsplit(origin)
    if url.path or url.hostname not in ('127.0.0.1', 'localhost') or not url.port:
        raise ValueError('The integration profile needs an explicit loopback HTTPS origin and port')
    with core.db() as db:
        if dict(db.execute('SELECT key,value FROM meta')) != {'data_mode': 'synthetic', 'schema_version': '8'}:
            raise ValueError('Migrate the synthetic database before starting the HTTPS stack')
    discovery = https_url(config['oauth_discovery_url'])
    http = ProviderHTTP(config.get('ca_file'))
    auth = Auth(core.path, core.clock)
    line = line_factory(core, auth, config['line_channel_id'], config['line_secret'], origin+'/auth/line/callback', http)
    grants = {name: OAuthGrants(core, config['oauth_issuer'], origin+path, config['oauth_introspection_url'],
        config['oauth_client_id'], config['oauth_secret'], config['trusted_clients'], http)
        for name, path in [('mcp', '/mcp'), ('a2a', '/a2a'), ('direct', '/direct/v1')]}
    connection = lambda name: {'host': url.netloc, 'grants': grants[name], 'discovery_url': discovery, 'card_signer': card_signer}
    mcp = mcp_app(core, url.port, connection('mcp'))
    a2a = a2a_app(core, url.port, config['trusted_clients'], connection('a2a'))

    async def work(function, *args):
        return await anyio.to_thread.run_sync(partial(function, *args))

    def session(request, write=False):
        token = request.cookies.get(COOKIE)
        result = auth.session(token)
        with core.db() as db:
            if not db.execute('SELECT 1 FROM external_sessions WHERE token_hash=?', (result['token_hash'],)).fetchone():
                fail('UNAUTHENTICATED', 'LINEログインが必要です', 401)
        if write and (request.headers.get('x-requested-with') != 'YokoLocal'
                or not hmac.compare_digest(result['csrf'], request.headers.get('x-csrf-token', ''))):
            fail('CSRF_REJECTED', '同じ画面でログインし直してください', 403)
        return result, token, {'web_session': result['token_hash']}

    async def body(request):
        if request.headers.get('content-type', '').split(';')[0] != 'application/json':
            fail('INVALID_CONTENT_TYPE', 'JSON形式で送信してください', 415)
        raw = await request.body()
        def unique(pairs):
            obj = {}
            for key, value in pairs:
                if key in obj: raise ValueError('Duplicate key')
                obj[key] = value
            return obj
        value = json.loads(raw, object_pairs_hook=unique, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if not isinstance(value, dict): fail('INVALID_INPUT', 'JSONオブジェクトが必要です')
        return value

    async def endpoint(request):
        path, method = request.url.path, request.method
        for grant in grants.values():
            if path == urlsplit(grant.metadata_url).path and method == 'GET': return JSONResponse(grant.metadata())
        if method == 'GET' and path in STATIC:
            name = STATIC[path]
            content = (ROOT/'app/static'/name).read_bytes()
            if path == '/':
                content = content.replace(b'<script src="/app.js" defer></script>', b'<script src="/app.js" defer></script><script src="/connected.js" defer></script>')
                # Retain controls for existing event handlers, but never expose demo credentials.
                content = content.replace(b'<form id="login-form">', b'<form id="login-form" hidden>').replace(b'value="local-test-only"', b'value=""')
                content = content.replace(b'<div id="web-entry">', b'<div id="web-entry" hidden>')
                content = content.replace('共通：local-test-only（このローカル試験専用）'.encode(), b'')
            mime = {'index.html': 'text/html', 'app.js': 'text/javascript', 'style.css': 'text/css'}[name]
            return Response(content, media_type=mime)
        if method == 'GET' and path == '/connected.js': return Response((ROOT/'app/static/connected.js').read_bytes(), media_type='text/javascript')
        if method == 'GET' and path == '/api/openapi.json':
            value=json.loads((ROOT/'api/https-integration.openapi.json').read_text())
            value['servers']=[{'url':origin}]
            value['components']['securitySchemes']['OAuth']['openIdConnectUrl']=discovery
            return JSONResponse(value)
        if method == 'GET' and path == '/auth/line/start':
            location, browser = await work(line.begin)
            response = RedirectResponse(location, status_code=303)
            response.set_cookie(FLOW_COOKIE, browser, max_age=300, path='/auth/line', secure=True, httponly=True, samesite='lax')
            return response
        if method == 'GET' and path == '/auth/line/callback':
            params = dict(request.query_params)
            if len(request.query_params.multi_items()) != len(params) or set(params)-{'state', 'code', 'error', 'error_description', 'friendship_status_changed'}:
                fail('INVALID_CALLBACK', 'ログインの応答を確認できません', 400)
            token, _ = await work(line.complete, params.get('state'), request.cookies.get(FLOW_COOKIE), params.get('code'), params.get('error'))
            response = RedirectResponse('/', status_code=303)
            response.delete_cookie(FLOW_COOKIE, path='/auth/line', secure=True, httponly=True, samesite='lax')
            response.set_cookie(COOKIE, token, max_age=3600, path='/', secure=True, httponly=True, samesite='lax')
            return response
        if path.startswith('/direct/v1/'):
            grant = grants['direct']
            actor, authorization, _ = await work(grant.resolve, request.headers.get('authorization'), request.headers.get('x-client-id'), request.headers.get('x-yoko-approval'))
            data = await body(request) if method in ('POST', 'PUT') else None
            return JSONResponse(await work(direct, core, method, path, request.url.query, data, actor, authorization))
        if request.url.query: fail('INVALID_URL', 'この操作はクエリを受け付けません')
        if path == '/api/session': fail('PASSWORD_LOGIN_DISABLED', 'LINEログインを使ってください', 403)
        current, token, authorization = await work(session, request, method != 'GET')
        actor = current['actor_id']
        data = await body(request) if method == 'POST' else None
        if method == 'GET' and path == '/api/me':
            result = {'user': {'id': actor, 'role': current['role'], 'tenant_id': current['tenant_id']}, 'csrf': current['csrf'], 'mode': 'https_integration_synthetic'}
        elif method == 'GET' and path == '/api/snapshot': result = await work(core.snapshot, actor, authorization)
        elif method == 'GET' and path == '/api/catalog': result = await work(core.catalog.snapshot, actor, authorization)
        elif method == 'GET' and path.startswith('/api/rides/'): result = await work(core.get_ride, actor, path.removeprefix('/api/rides/'), authorization)
        elif method == 'GET' and path.startswith('/api/payments/'): result = await work(core.payments.read, actor, path.removeprefix('/api/payments/'), authorization)
        elif method == 'GET' and path.startswith('/api/operations/'): result = await work(core.operation, actor, path.removeprefix('/api/operations/'), authorization)
        elif method == 'POST' and path == '/api/candidates': result = await work(core.booking.search, actor, data, authorization)
        elif method == 'POST' and path == '/api/logout':
            exact(data, [])
            await work(auth.logout, token)
            response = JSONResponse({'logged_out': True}); response.delete_cookie(COOKIE, path='/', secure=True, httponly=True, samesite='lax')
            return response
        elif method == 'GET' and path == '/api/oauth-options':
            def options():
                with core.db() as db:
                    core.check_authorization(db, actor, authorization)
                    return [{'adapter': name, 'resource': grant.resource, 'identity_id': row['id'], 'clients': sorted(grant.clients)}
                        for name, grant in grants.items() for row in db.execute('SELECT id FROM external_identities WHERE actor_id=? AND issuer=? AND audience=? AND active=1', (actor, grant.issuer, grant.resource))]
            result = await work(options)
        elif method == 'POST' and path == '/api/oauth-approvals':
            exact(data, ['adapter', 'identity_id', 'client_id', 'operation', 'expires_in'])
            adapter = data.pop('adapter')
            if not isinstance(adapter, str) or adapter not in grants: fail('INVALID_ADAPTER', '接続先を選んでください')
            result = await work(grants[adapter].issue, actor, data, authorization)
        elif method == 'GET' and path == '/api/oauth-approvals':
            def approvals():
                with core.db() as db:
                    core.check_authorization(db, actor, authorization)
                    return [dict(row) for row in db.execute('SELECT g.id,g.client_id,g.expires_at,g.revoked,a.resource,g.operation_json FROM client_grants g JOIN oauth_approvals a ON a.grant_id=g.id WHERE g.actor_id=? AND g.expires_at>? ORDER BY g.created_at DESC LIMIT 20', (actor, core.clock()))]
            result = await work(approvals)
        elif method == 'POST' and path == '/api/oauth-approvals/revoke':
            exact(data, ['grant_id']); result = await work(Grants(core).revoke, actor, data['grant_id'], authorization)
        elif method == 'POST' and path in {'/api/drafts/'+k for k in {'request', 'book', 'change', 'cancel'} | CATALOG_COMMANDS}:
            result = await work(core.prepare, actor, path.rsplit('/', 1)[1], data, authorization)
        elif method == 'POST' and path in {'/api/actions/'+k for k in {'request', 'book', 'change', 'cancel', 'accept', 'arrive', 'board', 'complete'} | CATALOG_COMMANDS}:
            exact(data, ['operation_id', 'idempotency_key', 'payload'])
            result = await work(core.mutate, actor, data['operation_id'], data['idempotency_key'], path.rsplit('/', 1)[1], data['payload'], authorization)
        else: fail('NOT_FOUND', 'この入口では提供していません', 404)
        return JSONResponse(result)

    @asynccontextmanager
    async def lifespan(app):
        async with a2a.app.router.lifespan_context(a2a.app):
            async with mcp.app.router.lifespan_context(mcp.app): yield
    async def domain_error(request, error):
        if request.url.path == '/auth/line/callback':
            return Response('<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>ログインの確認</title><h1>ログインを確認できませんでした</h1><p>'+html.escape(error.message)+'</p><a href="/">入口に戻ってやり直す</a></html>', error.status, media_type='text/html')
        response_headers = {'WWW-Authenticate': grants['direct'].challenge()} if error.status == 401 and request.url.path.startswith('/direct/') else {}
        return JSONResponse({'error': {'code': error.code, 'message': error.message}}, error.status, headers=response_headers)
    async def input_error(request, error): return await domain_error(request, DomainError('INVALID_INPUT', '入力を確認してください', 400))
    async def storage_error(request, error): return await domain_error(request, DomainError('STORAGE_BUSY', '同じ操作IDで結果を照会してください', 503))
    app = Starlette(routes=[Route('/{path:path}', endpoint, methods=['GET', 'POST', 'PUT', 'DELETE'])], lifespan=lifespan,
        exception_handlers={DomainError: domain_error, ValueError: input_error, TypeError: input_error, KeyError: input_error, sqlite3.OperationalError: storage_error})
    return Boundary(app, mcp, a2a, origin, grants)


class Boundary:
    def __init__(self, app, mcp, a2a, origin, grants):
        self.app, self.mcp, self.a2a, self.origin, self.grants = app, mcp, a2a, origin, grants
        self.requests, self.logins = deque(), deque()

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http': return await self.app(scope, receive, send)
        async def guarded_send(message):
            if message['type'] == 'http.response.start':
                security = {'cache-control': 'no-store', 'x-content-type-options': 'nosniff', 'referrer-policy': 'no-referrer',
                    'x-frame-options': 'DENY', 'content-security-policy': "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"}
                message = {**message, 'headers': [(k, v) for k, v in message.get('headers', []) if k.decode().lower() not in security] + [(k.encode(), v.encode()) for k, v in security.items()]}
            await send(message)
        try:
            pairs = scope['headers']; headers = {k.decode('latin1').lower(): v.decode('latin1') for k, v in pairs}
            if len(pairs) != len(headers): fail('DUPLICATE_HEADERS', '重複ヘッダーは受け付けません')
            if (scope.get('scheme') != 'https' or scope.get('client', ('',))[0] != '127.0.0.1' or 'https://'+headers.get('host', '') != self.origin
                    or any(k in headers for k in ('forwarded', 'x-forwarded-for', 'x-forwarded-host', 'x-forwarded-proto'))):
                fail('TLS_LOCAL_ONLY', 'HTTPSの接続試験環境専用です', 403)
            callback = scope['path'] == '/auth/line/callback' and scope['method'] == 'GET'
            navigation = scope['method'] == 'GET' and scope['path'] in ('/', '/auth/line/start') and headers.get('sec-fetch-mode') == 'navigate' and headers.get('sec-fetch-dest') == 'document'
            if headers.get('origin') not in (None, self.origin) or not (callback or navigation) and headers.get('sec-fetch-site') in ('same-site', 'cross-site'):
                fail('ORIGIN_REJECTED', '同じ画面から操作してください', 403)
            for queue, limit in [(self.requests, 600)] + ([(self.logins, 30)] if scope['path'].startswith('/auth/') else []):
                now = time.monotonic()
                while queue and queue[0] < now-60: queue.popleft()
                if len(queue) >= limit: fail('RATE_LIMITED', '操作が集中しています', 429)
                queue.append(now)
            if len(scope.get('query_string', b'')) > 4096 or 'transfer-encoding' in headers:
                fail('INVALID_REQUEST', 'リクエストを確認できません', 400)
            raw = b''
            with anyio.fail_after(10):
                while True:
                    item = await receive()
                    if item['type'] == 'http.disconnect': return
                    raw += item.get('body', b'')
                    if len(raw) > MAX_BODY: fail('BODY_TOO_LARGE', '入力が大きすぎます', 413)
                    if not item.get('more_body'): break
            original_receive = receive; delivered = False
            async def replay():
                nonlocal delivered
                if delivered: return await original_receive()
                delivered = True
                return {'type': 'http.request', 'body': raw, 'more_body': False}
            target = self.mcp if scope['path'] == '/mcp' else self.a2a if scope['path'] in ('/a2a', '/.well-known/agent-card.json') else self.app
            await target(scope, replay, guarded_send)
            return
        except DomainError as exc: error = exc
        except (ValueError, TypeError, KeyError): error = DomainError('INVALID_INPUT', '入力を確認してください', 400)
        except sqlite3.OperationalError: error = DomainError('STORAGE_BUSY', '同じ操作IDで結果を照会してください', 503)
        except TimeoutError: error = DomainError('REQUEST_TIMEOUT', '入力の受信期限が切れました', 408)
        await JSONResponse({'error': {'code': error.code, 'message': error.message}}, error.status,
            headers={'WWW-Authenticate': self.grants['direct'].challenge()} if error.status == 401 and scope['path'].startswith('/direct/') else {})(scope, receive, guarded_send)
