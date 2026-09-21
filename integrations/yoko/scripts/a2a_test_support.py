"""Loopback HTTP helpers for the synthetic A2A tests and demo."""
import socket
import threading
import time
from contextlib import contextmanager
import uvicorn
from app.a2a_adapter import create_app
from scripts.mcp_test_support import http


@contextmanager
def running_a2a(core, clients=('client-test', 'synthetic-a2a-client')):
    sock = socket.socket(); sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    app = create_app(core, port, clients)
    server = uvicorn.Server(uvicorn.Config(app, host='127.0.0.1', port=port, proxy_headers=False,
        access_log=False, log_level='critical', timeout_keep_alive=1, timeout_graceful_shutdown=2))
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True); thread.start()
    try:
        deadline = time.monotonic()+5
        while not server.started:
            if not thread.is_alive() or time.monotonic()>deadline: raise RuntimeError('A2A server did not start')
            time.sleep(.01)
        yield port, app
    finally:
        server.should_exit = True; thread.join(5); sock.close()
        if thread.is_alive(): raise RuntimeError('A2A server did not stop')


def rpc(port, grant, method, params=None, headers=None):
    hdrs = {'A2A-Version': '1.0', 'Accept': 'application/json'}
    if grant: hdrs.update({'Authorization': 'Bearer '+grant['access_token'], 'X-Client-ID': grant['client_id']})
    hdrs.update(headers or {})
    return http(port, '/a2a', 'POST', {'jsonrpc': '2.0', 'id': 'test-1', 'method': method, 'params': params or {}},
        {k:v for k,v in hdrs.items() if v is not None})


def send_params(value, message_id='message-1', task_id='', context_id=''):
    return {'message': {'messageId': message_id, 'role': 'ROLE_USER', 'taskId': task_id, 'contextId': context_id,
        'parts': [{'data': value, 'mediaType': 'application/json'}]}}
