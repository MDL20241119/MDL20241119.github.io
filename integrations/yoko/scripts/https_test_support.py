"""Synthetic HTTPS issuer and TLS harness. Never used by the application CLI."""
import base64
import hashlib
import ipaddress
import secrets
import socket
import ssl
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
import uvicorn
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.connected import create_app
from app.agent_trust import signer
from app.external_auth import Identities, LineLogin


def certificates(directory):
    directory = Path(directory)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Yoko ephemeral test CA')])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1))
        .not_valid_after(now+timedelta(hours=2)).add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'), x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False)
        .sign(key, hashes.SHA256()))
    cert_path, key_path = directory/'test-ca.pem', directory/'test-key.pem'
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    key_path.chmod(0o600)
    return cert_path, key_path


@contextmanager
def serving(factory, cert, key):
    sock = socket.socket(); sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    app = factory(port)
    config = uvicorn.Config(app, host='127.0.0.1', port=port, proxy_headers=False, access_log=False,
        ssl_certfile=str(cert), ssl_keyfile=str(key), log_level='critical', timeout_keep_alive=1, timeout_graceful_shutdown=3)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True); thread.start()
    try:
        deadline = time.monotonic()+5
        while not server.started:
            if not thread.is_alive() or time.monotonic()>deadline: raise RuntimeError('HTTPS test server failed to start')
            time.sleep(.01)
        yield port, app
    finally:
        server.should_exit = True; thread.join(5); sock.close()
        if thread.is_alive(): raise RuntimeError('HTTPS test server did not stop')


class SyntheticProvider:
    def __init__(self):
        self.tokens, self.codes, self.ids, self.calls = {}, {}, {}, []
        self.override = {}
        self.fail_status = None
        self.channel, self.secret = 'synthetic-line-channel', 'synthetic-line-secret'

    def app(self, port):
        self.origin = f'https://127.0.0.1:{port}'
        return Starlette(routes=[Route('/{path:path}', self.endpoint, methods=['GET', 'POST'])])

    def authorize(self, location, subject='synthetic-person-a1'):
        params = {k: v[0] for k, v in parse_qs(urlsplit(location).query).items()}
        assert params['client_id'] == self.channel and params['code_challenge_method'] == 'S256'
        code = secrets.token_urlsafe(32)
        self.codes[code] = {**params, 'subject': subject}
        return code, params['state']

    def token(self, resource, subject='synthetic-person-a1', client='connected-test', **changes):
        token = secrets.token_urlsafe(32)
        self.tokens[token] = {'active': True, 'iss': self.origin, 'aud': resource, 'sub': subject,
            'client_id': client, 'scope': 'mobility:read mobility:execute', 'token_type': 'Bearer', 'iat': time.time(), 'exp': time.time()+300, **changes}
        return token

    async def endpoint(self, request):
        path = request.url.path
        if self.fail_status: return JSONResponse({'error': 'synthetic_failure'}, self.fail_status)
        params = {k: v[0] for k, v in parse_qs((await request.body()).decode()).items()}
        # Record only parameter names, never codes, tokens or secrets.
        self.calls.append((path, sorted(params)))
        if path == '/token':
            values = self.codes.pop(params.get('code'), None)
            if not values or params.get('client_secret') != self.secret: return JSONResponse({}, 400)
            challenge = base64.urlsafe_b64encode(hashlib.sha256(params.get('code_verifier', '').encode()).digest()).rstrip(b'=').decode()
            if challenge != values['code_challenge'] or params.get('redirect_uri') != values['redirect_uri'] or params.get('client_id') != self.channel:
                return JSONResponse({}, 400)
            token = secrets.token_urlsafe(32)
            self.ids[token] = {'iss': LineLogin.ISSUER, 'aud': self.channel, 'sub': values['subject'],
                'nonce': values['nonce'], 'iat': time.time(), 'exp': time.time()+300, **self.override}
            return JSONResponse({'id_token': token, 'access_token': 'synthetic-not-stored', 'refresh_token': 'synthetic-not-stored'})
        if path == '/verify':
            values = self.ids.get(params.get('id_token'))
            if not values or values.get('nonce') != params.get('nonce') or params.get('client_id') != self.channel: return JSONResponse({}, 400)
            return JSONResponse(values)
        if path == '/introspect':
            expected = 'Basic '+base64.b64encode(b'yoko-resource:synthetic-introspection-secret').decode()
            if request.headers.get('authorization') != expected: return JSONResponse({}, 401)
            return JSONResponse(self.tokens.get(params.get('token'), {'active': False}))
        if path == '/.well-known/openid-configuration':
            return JSONResponse({'issuer': self.origin, 'authorization_endpoint': self.origin+'/authorize', 'token_endpoint': self.origin+'/token',
                'introspection_endpoint': self.origin+'/introspect', 'response_types_supported': ['code'], 'code_challenge_methods_supported': ['S256']})
        return JSONResponse({}, 404)


@contextmanager
def integration(core, directory):
    cert, key = certificates(directory)
    public = x509.load_pem_x509_certificate(cert.read_bytes()).public_key()
    (Path(directory)/'test-card-public.pem').write_bytes(public.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
    provider = SyntheticProvider()
    with serving(provider.app, cert, key):
        class TestLine(LineLogin):
            # Test dependency injection; not configurable by runtime users.
            AUTHORIZE, TOKEN, VERIFY = [provider.origin+p for p in ('/authorize', '/token', '/verify')]
        def factory(port):
            origin = f'https://127.0.0.1:{port}'
            config = {'origin': origin, 'line_channel_id': provider.channel, 'line_secret': provider.secret,
                'oauth_issuer': provider.origin, 'oauth_discovery_url': provider.origin+'/.well-known/openid-configuration',
                'oauth_introspection_url': provider.origin+'/introspect', 'oauth_client_id': 'yoko-resource',
                'oauth_secret': 'synthetic-introspection-secret', 'trusted_clients': ['connected-test', 'second-client'], 'ca_file': str(cert)}
            return create_app(core, config, TestLine, signer(key, 'synthetic-card-key'))
        with serving(factory, cert, key) as (port, app):
            origin = f'https://127.0.0.1:{port}'
            context = ssl.create_default_context(cafile=cert)
            with httpx.Client(base_url=origin, verify=context, trust_env=False, timeout=5, follow_redirects=False) as client:
                yield provider, app, client, origin, context


def enroll(core, provider, origin, actor='rider-a1', subject='synthetic-person-a1'):
    identities = Identities(core)
    result = {'line': identities.bind(LineLogin.ISSUER, provider.channel, subject, actor)}
    for name, path in [('mcp', '/mcp'), ('a2a', '/a2a'), ('direct', '/direct/v1')]:
        result[name] = identities.bind(provider.origin, origin+path, subject, actor)
    return result


def login(client, provider, subject='synthetic-person-a1'):
    start = client.get('/auth/line/start')
    assert start.status_code == 303, start.text
    code, state = provider.authorize(start.headers['location'], subject)
    response = client.get('/auth/line/callback', params={'code': code, 'state': state}, headers={'Sec-Fetch-Site': 'cross-site'})
    assert response.status_code == 303, response.text
    me = client.get('/api/me')
    assert me.status_code == 200, me.text
    client.headers.update({'X-CSRF-Token': me.json()['csrf'], 'X-Requested-With': 'YokoLocal'})
    return me.json()
