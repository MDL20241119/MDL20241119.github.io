"""Real loopback HTTP harness; used only by tests and the synthetic demo."""
from http.client import HTTPConnection
import json
import socket
import threading
import time
from contextlib import contextmanager

import uvicorn

from app.mcp_adapter import PROTOCOL, create_app


@contextmanager
def running_mcp(core):
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    app = create_app(core, port)
    config = uvicorn.Config(app, host='127.0.0.1', port=port, proxy_headers=False, access_log=False,
        log_level='critical', timeout_keep_alive=1, timeout_graceful_shutdown=2)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=lambda: server.run(sockets=[sock]), daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 5
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError('Local MCP test server did not start')
            time.sleep(.01)
        yield port, app
    finally:
        server.should_exit = True
        thread.join(5)
        sock.close()
        if thread.is_alive():
            raise RuntimeError('Local MCP test server did not stop')


def http(port, path, method='GET', data=None, headers=None, raw=None):
    headers = dict(headers or {})
    if data is not None:
        headers.setdefault('Content-Type', 'application/json')
    body = raw if raw is not None else json.dumps(data, ensure_ascii=False).encode() if data is not None else None
    connection = HTTPConnection('127.0.0.1', port, timeout=5)
    try:
        connection.request(method, path, body, headers)
        response = connection.getresponse()
        body = response.read()
        content_type = response.getheader('Content-Type', '')
        value = json.loads(body) if body and 'application/json' in content_type else body.decode()
        return response.status, value, dict(response.getheaders())
    finally:
        connection.close()


def rpc(port, grant, method, params=None, headers=None, request_id='read-1'):
    params = {'_meta': {'io.modelcontextprotocol/protocolVersion': PROTOCOL,
        'io.modelcontextprotocol/clientInfo': {'name': 'yoko-http-test', 'version': '0.8.0'},
        'io.modelcontextprotocol/clientCapabilities': {}}, **(params or {})}
    wire = {'jsonrpc': '2.0', 'id': request_id, 'method': method, 'params': params}
    hdrs = {'Accept': 'application/json, text/event-stream', 'MCP-Protocol-Version': PROTOCOL, 'Mcp-Method': method}
    if method == 'tools/call' and 'name' in params:
        hdrs['Mcp-Name'] = params['name']
    if grant:
        hdrs.update({'Authorization': 'Bearer '+grant['access_token'], 'X-Client-ID': grant['client_id']})
    hdrs.update(headers or {})
    hdrs = {k: v for k, v in hdrs.items() if v is not None}
    return http(port, '/mcp', 'POST', wire, hdrs)
