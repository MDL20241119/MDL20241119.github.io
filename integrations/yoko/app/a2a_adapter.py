"""Optional A2A 1.0 JSON-RPC adapter with the official protobuf/HTTP SDK.

This is a loopback synthetic profile. A local bearer grant and allowlisted
client are required; an Agent Card is descriptive, never an authorization.
"""
import json
import os
import re
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from functools import partial
from threading import BoundedSemaphore

import anyio
from google.protobuf.json_format import MessageToDict, ParseDict
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from a2a.server.context import ServerCallContext
from a2a.server.request_handlers.request_handler import RequestHandler
from a2a.server.request_handlers.response_helpers import build_error_response
from a2a.server.routes.common import ServerCallContextBuilder
from a2a.server.routes.jsonrpc_routes import create_jsonrpc_routes
from a2a.types import a2a_pb2 as p
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
from a2a.utils.errors import (TaskNotFoundError, TaskNotCancelableError, InvalidParamsError,
    InternalError, UnsupportedOperationError, PushNotificationNotSupportedError,
    ContentTypeNotSupportedError, VersionNotSupportedError, ExtensionSupportRequiredError)
from a2a.utils.proto_utils import validate_proto_required_fields

from .core import DomainError, iso
from .delegation import Grants

PROTOCOL = '1.0'
SDK_VERSION = '1.1.4'
APP_VERSION = '0.12.0'
MAX_BODY = 16384
TRUSTED_CLIENTS = frozenset({'synthetic-a2a-client'})


def card(port):
    value = {'name': '横のエレベーター・ローカル代理窓口',
        'description': '架空データ専用。本人の予約照会と個別承認済み操作。Task完了は乗車完了を意味しません。',
        'supportedInterfaces': [{'url': f'http://127.0.0.1:{port}/a2a', 'protocolBinding': 'JSONRPC', 'protocolVersion': PROTOCOL}],
        'version': APP_VERSION, 'capabilities': {}, 'defaultInputModes': ['application/json'], 'defaultOutputModes': ['application/json'],
        'skills': [{'id': 'own-reservation', 'name': '本人の予約', 'description': '照会、確認待ち、個別承認済みの依頼・予約・変更・取消。任意テキストの自動解釈は行いません。', 'tags': ['synthetic', 'owner-approved']}],
        'securitySchemes': {'ownerGrant': {'httpAuthSecurityScheme': {'scheme': 'Bearer', 'description': '本人がローカル画面で発行する最大300秒の個別委任'}},
            'clientId': {'apiKeySecurityScheme': {'location': 'header', 'name': 'X-Client-ID', 'description': '事前登録されたローカル検証クライアント'}}},
        'securityRequirements': [{'schemes': {'ownerGrant': {'list': []}, 'clientId': {'list': []}}}]}
    result = ParseDict(value, p.AgentCard())
    validate_proto_required_fields(result)
    return result


def task(value):
    def message(event):
        return {'messageId': event['id'], 'role': 'ROLE_AGENT', 'taskId': value['id'], 'contextId': value['context_id'],
            'parts': [{'data': {'code': event['code'], 'synthetic': True}, 'mediaType': 'application/json'}]}
    body = {'id': value['id'], 'contextId': value['context_id'],
        'status': {'state': 'TASK_STATE_'+value['state'].upper(), 'timestamp': iso(value['updated_at']),
            'message': message({'id': value['status_message_id'], 'code': value['code']})},
        'history': [message(event) for event in value['history']], 'metadata': {'synthetic': True, 'rideCompletionIndependent': True}}
    if value['result'] is not None:
        body['artifacts'] = [{'artifactId': value['id']+'-result', 'name': '実行・照会時点の予約',
            'parts': [{'data': value['result'], 'mediaType': 'application/json'}]}]
    result = ParseDict(body, p.Task())
    validate_proto_required_fields(result)
    return result


class ContextBuilder(ServerCallContextBuilder):
    def build(self, request):
        return ServerCallContext(state={'principal': request.scope.get('yoko_principal'),
            'headers': {'a2a-version': request.headers.get('a2a-version', '')}})


class Handler(RequestHandler):
    def __init__(self, core):
        self.core = core
        self.pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='yoko-a2a')
        self.slots = BoundedSemaphore(8)

    def schedule(self, job):
        if not self.slots.acquire(blocking=False): return False
        try:
            future = self.pool.submit(job)
        except RuntimeError:
            self.slots.release()
            return False
        future.add_done_callback(lambda _: self.slots.release())
        return True

    def close(self): self.pool.shutdown(wait=True, cancel_futures=True)

    async def invoke(self, params, context, function, **kwargs):
        validate_proto_required_fields(params)
        if params.tenant: raise InvalidParamsError(message='No routed tenant is advertised')
        principal = context.state.get('principal')
        if not principal: raise InvalidParamsError(message='Authenticated local HTTP is required')
        try:
            return await anyio.to_thread.run_sync(partial(function, *principal, **kwargs))
        except DomainError as error:
            kind = TaskNotFoundError if error.code == 'TASK_NOT_FOUND' else TaskNotCancelableError if error.code == 'TASK_NOT_CANCELABLE' else UnsupportedOperationError if error.code == 'TASK_TERMINAL' else InvalidParamsError
            raise kind(message=error.code) from None
        except Exception:
            raise InternalError(message='Internal error; retrieve the same Task before retrying') from None

    async def on_message_send(self, params, context):
        msg, cfg = params.message, params.configuration
        if msg.role != p.ROLE_USER or len(msg.parts) != 1 or msg.parts[0].WhichOneof('content') != 'data':
            raise ContentTypeNotSupportedError(message='One structured application/json data part is required')
        if msg.parts[0].media_type not in ('', 'application/json'):
            raise ContentTypeNotSupportedError()
        if cfg.HasField('task_push_notification_config'): raise PushNotificationNotSupportedError()
        if cfg.accepted_output_modes and 'application/json' not in cfg.accepted_output_modes:
            raise ContentTypeNotSupportedError()
        length = cfg.history_length if cfg.HasField('history_length') else 20
        value = MessageToDict(msg.parts[0].data)
        return task(await self.invoke(params, context, self.core.tasks.send, message_id=msg.message_id, value=value,
            task_id=msg.task_id, context_id=msg.context_id, history_length=length,
            return_immediately=cfg.return_immediately, schedule=self.schedule if cfg.return_immediately else None))

    async def on_get_task(self, params, context):
        return task(await self.invoke(params, context, self.core.tasks.get, task_id=params.id,
            history_length=params.history_length if params.HasField('history_length') else 20))

    async def on_cancel_task(self, params, context):
        return task(await self.invoke(params, context, self.core.tasks.cancel, task_id=params.id))

    async def on_list_tasks(self, params, context):
        try: state = p.TaskState.Name(params.status).removeprefix('TASK_STATE_').lower() if params.status else ''
        except ValueError: raise InvalidParamsError() from None
        value = await self.invoke(params, context, self.core.tasks.list, context_id=params.context_id, state=state,
            page_size=params.page_size if params.HasField('page_size') else 20, page_token=params.page_token,
            history_length=params.history_length if params.HasField('history_length') else 0,
            after=params.status_timestamp_after.seconds+params.status_timestamp_after.nanos/1e9 if params.HasField('status_timestamp_after') else None,
            include_artifacts=params.include_artifacts)
        return p.ListTasksResponse(tasks=[task(t) for t in value['tasks']], next_page_token=value['next_page_token'],
            page_size=value['page_size'], total_size=value['total_size'])

    async def on_message_send_stream(self, params, context):
        raise UnsupportedOperationError()
        yield

    async def on_subscribe_to_task(self, params, context):
        raise UnsupportedOperationError()
        yield

    async def on_create_task_push_notification_config(self, params, context): raise PushNotificationNotSupportedError()
    async def on_get_task_push_notification_config(self, params, context): raise PushNotificationNotSupportedError()
    async def on_list_task_push_notification_configs(self, params, context): raise PushNotificationNotSupportedError()
    async def on_delete_task_push_notification_config(self, params, context): raise PushNotificationNotSupportedError()
    async def on_get_extended_agent_card(self, params, context): raise UnsupportedOperationError()


class LocalBoundary:
    def __init__(self, app, core, port, trusted_clients, connection=None):
        self.app, self.grants = app, Grants(core)
        self.hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
        self.trusted_clients, self.requests = frozenset(trusted_clients), deque()
        self.connection, self.scheme = connection, 'https' if connection else 'http'
        if connection: self.grants, self.hosts = connection['grants'], {connection['host']}

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http': return await self.app(scope, receive, send)
        raw = scope.get('headers', [])
        headers = {k.decode().lower(): v.decode() for k, v in raw}
        async def reply(code, value):
            return await JSONResponse(value, code, headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})(scope, receive, send)
        if len(raw) != len(headers): return await reply(400, {'error': {'code': 'DUPLICATE_HEADERS'}})
        host = headers.get('host')
        if scope.get('scheme') != self.scheme or not scope.get('client') or scope['client'][0] != '127.0.0.1' or host not in self.hosts or any(k in headers for k in ('forwarded', 'x-forwarded-for', 'x-forwarded-host', 'x-forwarded-proto')):
            return await reply(403, {'error': {'code': 'LOCAL_ONLY'}})
        if headers.get('origin') not in (None, f'{self.scheme}://{host}') or headers.get('sec-fetch-site') in ('cross-site', 'same-site'):
            return await reply(403, {'error': {'code': 'ORIGIN_REJECTED'}})
        is_card = scope['path'] == AGENT_CARD_WELL_KNOWN_PATH
        if scope.get('query_string') or scope['path'] not in (AGENT_CARD_WELL_KNOWN_PATH, '/a2a'):
            return await reply(404, {'error': {'code': 'NOT_FOUND'}})
        if scope['method'] != ('GET' if is_card else 'POST'):
            return await reply(405, {'error': {'code': 'METHOD_NOT_ALLOWED'}})
        now = time.monotonic()
        while self.requests and self.requests[0] < now-60: self.requests.popleft()
        if len(self.requests) >= 600: return await reply(429, {'error': {'code': 'RATE_LIMITED'}})
        self.requests.append(now)
        if not is_card:
            try:
                args = [headers.get('authorization'), headers.get('x-client-id')]
                if self.connection: args.append(headers.get('x-yoko-approval'))
                actor, authorization, _ = await anyio.to_thread.run_sync(partial(self.grants.resolve, *args))
            except DomainError as error:
                return await reply(error.status, {'error': {'code': error.code}})
            if authorization['client_id'] not in self.trusted_clients:
                return await reply(403, {'error': {'code': 'UNTRUSTED_CLIENT'}})
            if headers.get('content-type', '').split(';')[0].strip() != 'application/json':
                return await reply(415, {'error': {'code': 'JSON_REQUIRED'}})
            body = b''
            while True:
                chunk = await receive()
                if chunk['type'] == 'http.disconnect': return
                body += chunk.get('body', b'')
                if len(body) > MAX_BODY: return await reply(413, {'error': {'code': 'BODY_TOO_LARGE'}})
                if not chunk.get('more_body'): break
            request_id = None
            try:
                envelope = json.loads(body)
                if isinstance(envelope, dict) and isinstance(envelope.get('id'), (str, int)) and not isinstance(envelope.get('id'), bool): request_id = envelope['id']
            except (ValueError, UnicodeDecodeError): pass
            # SDK 1.1.4 compares major versions only. Enforce the spec's
            # major.minor negotiation here while accepting ignored patch parts.
            if not re.fullmatch(r'1\.0(?:\.[0-9]+)?', headers.get('a2a-version', '')):
                return await reply(400, build_error_response(request_id, VersionNotSupportedError(message='Supported version: 1.0')))
            if headers.get('a2a-extensions'):
                return await reply(400, build_error_response(request_id, ExtensionSupportRequiredError(message='No extensions are advertised')))
            scope['yoko_principal'] = (actor, authorization)
            original_receive = receive
            delivered = False
            async def replay():
                nonlocal delivered
                if delivered: return await original_receive()
                delivered = True
                return {'type': 'http.request', 'body': body, 'more_body': False}
            receive = replay
        async def no_cache(message):
            if message['type'] == 'http.response.start':
                message = {**message, 'headers': [(k, v) for k, v in message.get('headers', []) if k.lower() not in (b'cache-control', b'x-content-type-options')] + [(b'cache-control', b'no-store'), (b'x-content-type-options', b'nosniff')]}
            await send(message)
        return await self.app(scope, receive, no_cache)


def create_app(core, port, trusted_clients=TRUSTED_CLIENTS, connection=None):
    if os.environ.get('YOKO_ENV', 'local') != 'local' or type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('A2A is restricted to the local synthetic profile')
    with core.db() as db:
        if dict(db.execute('SELECT key,value FROM meta')) != {'data_mode': 'synthetic', 'schema_version': '8'}:
            raise ValueError('Start the normal local application first to migrate its synthetic database')
    agent_card = card(port)
    if connection:
        value = MessageToDict(agent_card)
        value['supportedInterfaces'][0]['url'] = connection['grants'].resource
        value['securitySchemes'] = {'oauth': {'openIdConnectSecurityScheme': {'openIdConnectUrl': connection['discovery_url']}}}
        value['securityRequirements'] = [{'schemes': {'oauth': {'list': ['mobility:read']}}}]
        agent_card = ParseDict(value, p.AgentCard())
        validate_proto_required_fields(agent_card)
        if connection.get('card_signer'): agent_card = connection['card_signer'](agent_card)
    handler = Handler(core)
    @asynccontextmanager
    async def lifespan(app):
        try: yield
        finally: await anyio.to_thread.run_sync(handler.close)
    async def get_card(request): return JSONResponse(MessageToDict(agent_card))
    app = Starlette(routes=[Route(AGENT_CARD_WELL_KNOWN_PATH, get_card, methods=['GET'])] +
        create_jsonrpc_routes(handler, '/a2a', ContextBuilder(), enable_v0_3_compat=False), lifespan=lifespan)
    return LocalBoundary(app, core, port, trusted_clients, connection)
