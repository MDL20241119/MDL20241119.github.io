"""Reproduce Web/direct API/MCP parity in a temporary synthetic database.

Uses the official SDK client over real loopback HTTP. Never prints a token,
accepts an external URL, starts a paid service or exposes a public listener.
"""
import asyncio
import json
import secrets
import sys
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from app.core import Core
from app.db import initialize
from app.server import LocalServer
from scripts.mcp_test_support import running_mcp, http, rpc


def run():
    checks, evidence = [], {}
    fixture = json.loads((ROOT/'fixtures/synthetic-catalog.json').read_text())
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder)/'mcp-demo.sqlite3'
        initialize(path)
        web = LocalServer(('127.0.0.1', 0), path)
        thread = threading.Thread(target=lambda: web.serve_forever(poll_interval=.01), daemon=True)
        thread.start()
        port = web.server_address[1]

        def web_call(url, body=None, session=None, grant=None, status=200):
            headers = {'X-Requested-With': 'YokoLocal'}
            if session:
                headers.update({'Cookie': session['cookie'], 'X-CSRF-Token': session['csrf']})
            if grant:
                headers.update({'Authorization': 'Bearer '+grant['access_token'], 'X-Client-ID': grant['client_id']})
            code, value, response_headers = http(port, url, 'POST' if body is not None else 'GET', body, headers)
            assert code == status, (url, code)
            if url == '/api/session':
                cookie = next(v for k, v in response_headers.items() if k.lower() == 'set-cookie')
                return {'cookie': cookie.split(';')[0], 'csrf': value['csrf']}
            return value

        def login(actor):
            return web_call('/api/session', {'username': actor, 'password': 'local-test-only'})

        def action(session, kind, data, draft=True):
            if draft:
                prepared = web_call('/api/drafts/'+kind, data, session)
                data = {'draft_id': prepared['id'], 'details': prepared['details']}
            key = secrets.token_hex(16)
            return web_call('/api/actions/'+kind, {'operation_id': key, 'idempotency_key': key, 'payload': data}, session)['current']

        def grant(session, operation=None):
            return web_call('/api/client-grants', {'client_id': 'synthetic-mcp-client',
                'scopes': ['mobility:read']+(['mobility:execute'] if operation else []),
                'expires_in': 300, 'operation': operation}, session)

        def approved(kind, data):
            prepared = web_call('/api/drafts/'+kind, data, rider); key = secrets.token_hex(16)
            operation = {'operation_id': key, 'idempotency_key': key, 'kind': kind,
                'payload': {'draft_id': prepared['id'], 'details': prepared['details']}}
            return operation, grant(rider, operation)

        async def execute_mcp(mcp_port, operation, authorization):
            async with httpx2.AsyncClient(headers={'Authorization': 'Bearer '+authorization['access_token'],
                'X-Client-ID': authorization['client_id']}, trust_env=False) as hc:
                async with Client(streamable_http_client(f'http://127.0.0.1:{mcp_port}/mcp', http_client=hc), cache=None) as client:
                    result = await client.call_tool('yoko_execute_approved_operation', {'operation': operation})
                    return result.structured_content

        def passed(label):
            checks.append(label)
            print('PASS '+label, flush=True)

        try:
            rider, driver, admin, other = [login(actor) for actor in ['rider-a1', 'driver-a1', 'admin-a1', 'rider-a2']]
            action(admin, 'service_configure', fixture['service'])
            for stop in fixture['stops']:
                action(admin, 'stop_configure', stop)
            action(rider, 'profile_create', fixture['profile'])
            request = {'service_id': 'service-a', 'origin_stop_id': 'stop-a', 'destination_stop_id': 'stop-b', 'passengers': 2}
            ride = action(rider, 'request', request)
            read, foreign = grant(rider), grant(other)
            passed('本人の画面APIで確認・保存し、Cookie/CSRF認証から最長300秒の読取委任を発行')

            async def sdk_read(mcp_port):
                async with httpx2.AsyncClient(headers={'Authorization': 'Bearer '+read['access_token'],
                    'X-Client-ID': read['client_id']}, trust_env=False) as http_client:
                    async with Client(streamable_http_client(f'http://127.0.0.1:{mcp_port}/mcp', http_client=http_client), cache=None) as client:
                        tools = await client.list_tools()
                        evidence['sdk'] = {'name': 'mcp', 'version': '2.2.0', 'protocol': client.protocol_version,
                            'tools': [tool.name for tool in tools.tools]}
                        assert len(tools.tools) == 6
                        for tool in ['yoko_list_services', 'yoko_list_stops', 'yoko_list_my_reservations']:
                            value = await client.call_tool(tool, {})
                            assert not value.is_error and value.structured_content['ok']
                        value = await client.call_tool('yoko_get_my_reservation', {'reservation_id': ride['id']})
                        assert not value.is_error
                        result = value.structured_content['data']
                        direct = web_call('/direct/v1/rides/'+ride['id'], grant=read)
                        visible = web_call('/api/rides/'+ride['id'], session=rider)
                        assert all(result[k] == direct[k] == visible[k] for k in result)
                        return result

            with running_mcp(Core(path)) as (mcp_port, _):
                evidence['requested'] = asyncio.run(sdk_read(mcp_port))
                passed('公式SDK 2.2.0で発見・6ツール列挙・基本4読取を実HTTP実行し、画面API・直接APIと同じ予約を照合')
                for state in ['accept', 'arrive', 'board', 'complete']:
                    ride = action(driver, state, {'ride_id': ride['id'], 'version': ride['version'], 'stopped': True}, False)
                result = asyncio.run(sdk_read(mcp_port))
                assert result['status'] == 'completed'
                assert web_call('/api/rides/'+ride['id'], session=admin)['status'] == 'completed'
                evidence['completed'] = result
                passed('ドライバーの引受・到着・乗車・降車後、管理者と再接続したMCPクライアントで同じ完了状態を確認')
                code, denied, _ = rpc(mcp_port, foreign, 'tools/call', {'name': 'yoko_get_my_reservation', 'arguments': {'reservation_id': ride['id']}})
                assert code == 200 and denied['result']['isError'] and denied['result']['structuredContent']['error']['code'] == 'NOT_FOUND'
                code, denied, _ = rpc(mcp_port, read, 'tools/call', {'name': 'yoko_cancel_reservation', 'arguments': {'reservation_id': ride['id']}})
                assert code == 400 and denied['error']['code'] == -32602
                passed('別利用者の予約照会と未実装の更新ツールを拒否し、予約・課金を変えない')
                web_call('/api/client-grants/revoke', {'grant_id': read['grant_id']}, rider)
                assert rpc(mcp_port, read, 'tools/list')[0] == 401
                passed('本人が委任を取り消した直後、以前の接続情報での照会を拒否')

            assert web_call('/api/rides/'+ride['id'], session=rider)['status'] == 'completed'
            passed('MCPプロセスを停止しても通常APIから保存済みの予約を確認できる')
            fresh = grant(rider)
            with running_mcp(Core(path)) as (new_port, _):
                code, value, _ = rpc(new_port, fresh, 'tools/call', {'name': 'yoko_get_my_reservation', 'arguments': {'reservation_id': ride['id']}})
                assert code == 200 and value['result']['structuredContent']['data'] == evidence['completed']
            passed('MCPサーバー再起動後も同じDBと新しい本人委任で状態を再照会')

            with running_mcp(Core(path)) as (mcp_port, _):
                operation, authorization = approved('request', request)
                denied = asyncio.run(execute_mcp(mcp_port, operation, fresh))
                assert denied['error']['code'] == 'INSUFFICIENT_SCOPE'
                created = asyncio.run(execute_mcp(mcp_port, operation, authorization))
                replay = asyncio.run(execute_mcp(mcp_port, operation, authorization))
                assert created['ok'] and replay['data']['replayed']
                current = created['data']['current']
                passed('読取委任だけの更新を拒否し、本人の個別確認後にSDKから依頼を一度だけ保存')
                direct = web_call('/direct/v1/actions/request', {k: v for k, v in operation.items() if k != 'kind'}, grant=authorization)
                assert direct['replayed'] and direct['current']['id'] == current['id']
                passed('同じ操作をMCPから直接APIへ再送しても依頼・通知台帳が重複しない')
                change, authorization = approved('change', {'ride_id': current['id'], **request, 'passengers': 1})
                changed = asyncio.run(execute_mcp(mcp_port, change, authorization))
                assert changed['ok'] and changed['data']['current']['passengers'] == 1
                cancel, authorization = approved('cancel', {'ride_id': current['id']})
                cancelled = asyncio.run(execute_mcp(mcp_port, cancel, authorization))
                assert cancelled['ok'] and cancelled['data']['current']['status'] == 'cancelled'
                assert web_call('/api/rides/'+current['id'], session=rider)['status'] == 'cancelled'
                passed('変更と取消はそれぞれ別の本人確認・委任で実行し、画面APIにも同じ状態を反映')
                web_call('/api/client-grants/revoke', {'grant_id': authorization['grant_id']}, rider)
                code, receipt, _ = rpc(mcp_port, grant(rider), 'tools/call', {'name': 'yoko_get_my_operation',
                    'arguments': {'operation_id': cancel['operation_id']}})
                assert code == 200 and receipt['result']['structuredContent']['data']['current']['status'] == 'cancelled'
                evidence['mcp_cancelled'] = cancelled['data']['current']
                passed('実行委任を取り消した後でも、新しい本人読取委任で同じ操作IDの結果を照合')
        finally:
            web.shutdown(); web.server_close(); thread.join(2)

    return {'status': 'PASS', 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'scope': 'SYNTHETIC_LOOPBACK_REAL_HTTP_OFFICIAL_SDK_READ_AND_EXACT_APPROVED_ACTIONS', 'checks': checks, 'evidence': evidence,
        'oauth_conformance': False, 'https_remote_tested': False, 'external_ai_host_tested': False,
        'mcp_mutations_implemented': True, 'a2a_tested': False, 'production_conformance': False}


if __name__ == '__main__':
    report = run()
    (ROOT/'artifacts/test-results/mcp-client-demo.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(f'{len(report["checks"])}項目合格。架空データ・一時環境・本人の個別委任。')
