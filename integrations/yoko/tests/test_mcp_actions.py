"""Exact owner-approved MCP commands, shared operation receipts and failures."""
import asyncio
import copy
from http.client import HTTPConnection
import json
import secrets
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

import httpx2
from jsonschema import Draft202012Validator
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from app.core import Core
from app.mcp_adapter import PROTOCOL
from app.server import LocalServer
from scripts.export_mcp_tools import build
from scripts.mcp_test_support import running_mcp, rpc, http
from tests.test_p3 import Fixture
from tests.test_core import REQUEST
from tests.test_booking import BookingFixture


class ActionHTTP:
    def start_mcp(self):
        running = running_mcp(self.core)
        self.port, _ = running.__enter__()
        self.addCleanup(running.__exit__, None, None, None)

    def call(self, op, grant=None):
        code, body, _ = rpc(self.port, grant or self.grant(op), 'tools/call',
            {'name': 'yoko_execute_approved_operation', 'arguments': {'operation': op}})
        self.assertEqual(code, 200, body)
        result = body['result']
        schema = next(t['outputSchema'] for t in build()['tools'] if t['name'] == 'yoko_execute_approved_operation')
        Draft202012Validator(schema).validate(result['structuredContent'])
        self.assertEqual(result['isError'], not result['structuredContent']['ok'])
        return result['structuredContent']

    def lookup(self, op, actor='rider-a1', grant=None):
        code, body, _ = rpc(self.port, grant or self.grant(actor=actor), 'tools/call',
            {'name': 'yoko_get_my_operation', 'arguments': {'operation_id': op['operation_id']}})
        self.assertEqual(code, 200)
        return body['result']['structuredContent']


class MCPActionTests(ActionHTTP, Fixture):
    def setUp(self):
        super().setUp(); self.start_mcp()

    def test_request_change_cancel_share_one_business_history(self):
        request = self.prepare('request', REQUEST)
        ride = self.call(request)['data']['current']
        change = self.prepare('change', {'ride_id': ride['id'], **REQUEST, 'passengers': 2})
        ride = self.call(change)['data']['current']
        self.assertEqual(ride['passengers'], 2)
        cancel = self.prepare('cancel', {'ride_id': ride['id']})
        ride = self.call(cancel)['data']['current']
        self.assertEqual(ride['status'], 'cancelled')
        self.assertEqual(self.lookup(request)['data']['current']['status'], 'cancelled')
        self.assertEqual(self.sql('SELECT kind FROM events ORDER BY version'), [('request',), ('change',), ('cancel',)])

    def test_sdk_executes_with_exact_grant_and_reports_replay(self):
        op = self.prepare('request', REQUEST); grant = self.grant(op)
        async def run():
            async with httpx2.AsyncClient(headers={'Authorization': 'Bearer '+grant['access_token'], 'X-Client-ID': grant['client_id']}, trust_env=False) as hc:
                async with Client(streamable_http_client(f'http://127.0.0.1:{self.port}/mcp', http_client=hc), cache=None) as client:
                    one = await client.call_tool('yoko_execute_approved_operation', {'operation': op})
                    two = await client.call_tool('yoko_execute_approved_operation', {'operation': op})
                    self.assertFalse(one.is_error); self.assertFalse(two.is_error)
                    self.assertFalse(one.structured_content['data']['replayed'])
                    self.assertTrue(two.structured_content['data']['replayed'])
        asyncio.run(run())
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'), [(1,)])

    def test_read_scope_and_confirmed_flag_do_not_authorize_writes(self):
        op = self.prepare('request', REQUEST); read = self.grant()
        self.assertEqual(self.call(op, read)['error']['code'], 'INSUFFICIENT_SCOPE')
        code, body, _ = rpc(self.port, read, 'tools/call', {'name': 'yoko_execute_approved_operation',
            'arguments': {'operation': op, 'confirmed': True}})
        self.assertEqual(code, 200); self.assertEqual(body['result']['structuredContent']['error']['code'], 'INVALID_INPUT')
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'), [(0,)])

    def test_modified_ids_kind_and_payload_do_not_reuse_approval(self):
        op = self.prepare('request', REQUEST); grant = self.grant(op)
        changed = []
        for key, value in [('operation_id', 'changed-operation'), ('idempotency_key', 'changed-idempotency'), ('kind', 'cancel')]:
            changed.append({**op, key: value})
        payload = copy.deepcopy(op); payload['payload']['details']['passengers'] = 3; changed.append(payload)
        for request in changed:
            with self.subTest(request=request['kind']):
                self.assertEqual(self.call(request, grant)['error']['code'], 'APPROVAL_MISMATCH')
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'), [(0,)])

    def test_other_owner_and_client_cannot_use_the_operation(self):
        op = self.prepare('request', REQUEST); foreign = self.grant(actor='rider-a2')
        self.assertEqual(self.call(op, foreign)['error']['code'], 'INSUFFICIENT_SCOPE')
        grant = self.grant(op)
        self.assertEqual(rpc(self.port, grant, 'tools/call', {'name': 'yoko_execute_approved_operation', 'arguments': {'operation': op}}, {'X-Client-ID': 'another-client'})[0], 403)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'), [(0,)])

    def test_expired_or_revoked_grant_cannot_mutate(self):
        op = self.prepare('request', REQUEST); grant = self.grant(op)
        self.sql('UPDATE client_grants SET expires_at=0')
        self.assertEqual(rpc(self.port, grant, 'tools/call', {'name': 'yoko_execute_approved_operation', 'arguments': {'operation': op}})[0], 401)
        second = self.grant(op); self.grants.revoke('rider-a1', second['grant_id'])
        self.assertEqual(rpc(self.port, second, 'tools/call', {'name': 'yoko_execute_approved_operation', 'arguments': {'operation': op}})[0], 401)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'), [(0,)])

    def test_revocation_between_boundary_and_core_rolls_back(self):
        op = self.prepare('request', REQUEST); grant = self.grant(op); original = self.core.mutate
        def revoke(*args, **kwargs):
            self.grants.revoke('rider-a1', grant['grant_id'])
            return original(*args, **kwargs)
        with patch.object(self.core, 'mutate', side_effect=revoke):
            self.assertEqual(self.call(op, grant)['error']['code'], 'INVALID_GRANT')
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'), [(0,)])

    def test_business_changes_after_approval_are_rechecked(self):
        op = self.prepare('request', REQUEST); grant = self.grant(op)
        self.sql("UPDATE users SET eligible=0 WHERE id='rider-a1'")
        self.assertEqual(self.call(op, grant)['error']['code'], 'INELIGIBLE')
        self.sql("UPDATE users SET eligible=1 WHERE id='rider-a1'")
        self.sql('UPDATE services SET revision=revision+1')
        self.assertEqual(self.call(op, grant)['error']['code'], 'TERMS_CHANGED')
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'), [(0,)])

    def test_draft_expiry_is_checked_even_with_unexpired_grant(self):
        op = self.prepare('request', REQUEST); grant = self.grant(op)
        self.sql('UPDATE drafts SET expires_at=0')
        self.assertEqual(self.call(op, grant)['error']['code'], 'CONFIRMATION_EXPIRED')
        self.assertEqual(self.sql('SELECT COUNT(*) FROM operations'), [(0,)])

    def test_direct_api_and_mcp_same_operation_do_not_duplicate(self):
        op = self.prepare('request', REQUEST); grant = self.grant(op)
        web = LocalServer(('127.0.0.1', 0), self.path)
        thread = threading.Thread(target=lambda: web.serve_forever(poll_interval=.01), daemon=True); thread.start()
        try:
            first = self.call(op, grant)['data']
            code, replay, _ = http(web.server_address[1], '/direct/v1/actions/request', 'POST',
                {k: v for k, v in op.items() if k != 'kind'}, {'Authorization': 'Bearer '+grant['access_token'], 'X-Client-ID': grant['client_id']})
            self.assertEqual(code, 200); self.assertTrue(replay['replayed'])
            self.assertEqual(replay['current']['id'], first['current']['id'])
            self.assertEqual(self.sql('SELECT COUNT(*) FROM outbox'), [(1,)])
        finally:
            web.shutdown(); web.server_close(); thread.join(2)

    def test_simultaneous_mcp_retries_commit_once(self):
        op = self.prepare('request', REQUEST); grant = self.grant(op)
        with ThreadPoolExecutor(2) as pool:
            jobs = [pool.submit(self.call, op, grant) for _ in range(2)]
            results = [j.result() for j in jobs]
        self.assertEqual(sorted(r['data']['replayed'] for r in results), [False, True])
        for table in ['rides', 'operations', 'events', 'outbox']:
            self.assertEqual(self.sql('SELECT COUNT(*) FROM '+table), [(1,)], table)

    def test_storage_failure_leaves_no_partial_booking_or_receipt(self):
        op = self.prepare('request', REQUEST); grant = self.grant(op)
        self.sql("CREATE TRIGGER fail_mcp BEFORE INSERT ON outbox BEGIN SELECT RAISE(ABORT,'forced'); END")
        code, body, _ = rpc(self.port, grant, 'tools/call', {'name': 'yoko_execute_approved_operation', 'arguments': {'operation': op}})
        self.assertEqual(code, 200); self.assertEqual(body['error']['code'], -32603)
        for table in ['rides', 'operations', 'events', 'outbox']:
            self.assertEqual(self.sql('SELECT COUNT(*) FROM '+table), [(0,)], table)
        self.assertEqual(self.sql('SELECT consumed FROM drafts'), [(0,)])

    def test_dropped_response_can_be_looked_up_after_restart_without_repeat(self):
        op = self.prepare('request', REQUEST); grant = self.grant(op)
        committed, release = threading.Event(), threading.Event(); original = self.core.mutate
        def hold_response(*args, **kwargs):
            result = original(*args, **kwargs); committed.set(); release.wait(3); return result
        wire = {'jsonrpc': '2.0', 'id': 'drop-response', 'method': 'tools/call', 'params': {
            'name': 'yoko_execute_approved_operation', 'arguments': {'operation': op}, '_meta': {
                'io.modelcontextprotocol/protocolVersion': PROTOCOL,
                'io.modelcontextprotocol/clientInfo': {'name': 'drop-test', 'version': '1'},
                'io.modelcontextprotocol/clientCapabilities': {}}}}
        headers = {'Authorization': 'Bearer '+grant['access_token'], 'X-Client-ID': grant['client_id'],
            'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
            'MCP-Protocol-Version': PROTOCOL, 'Mcp-Method': 'tools/call', 'Mcp-Name': 'yoko_execute_approved_operation'}
        connection = HTTPConnection('127.0.0.1', self.port, timeout=5)
        with patch.object(self.core, 'mutate', side_effect=hold_response):
            try:
                connection.request('POST', '/mcp', json.dumps(wire), headers)
                self.assertTrue(committed.wait(3))
            finally:
                connection.close(); release.set()
        self.assertTrue(self.lookup(op)['ok'])
        with running_mcp(Core(self.path)) as (port, _):
            code, body, _ = rpc(port, grant, 'tools/call', {'name': 'yoko_execute_approved_operation', 'arguments': {'operation': op}})
            self.assertEqual(code, 200); self.assertTrue(body['result']['structuredContent']['data']['replayed'])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'), [(1,)])

    def test_fresh_read_grant_can_reconcile_after_execution_grant_expired(self):
        op = self.prepare('request', REQUEST); grant = self.grant(op)
        self.call(op, grant); self.sql('UPDATE client_grants SET expires_at=0')
        self.assertTrue(self.lookup(op)['ok'])
        self.assertEqual(self.lookup(op, 'rider-a2')['error']['code'], 'OPERATION_NOT_FOUND')

    def test_cancellation_releases_seats_once_and_receipt_keeps_latest_state(self):
        ride = self.driver('accept', self.create(count=2))
        op = self.prepare('cancel', {'ride_id': ride['id']}); grant = self.grant(op)
        self.assertEqual(self.call(op, grant)['data']['current']['status'], 'cancelled')
        self.assertTrue(self.call(op, grant)['data']['replayed'])
        self.assertEqual(self.sql('SELECT reserved,active FROM runs'), [(0, 0)])
        self.assertEqual(self.lookup(op)['data']['current']['status'], 'cancelled')


class MCPBookingTests(ActionHTTP, BookingFixture):
    def setUp(self):
        super().setUp(); self.start_mcp(); self.ready()

    def test_candidate_booking_is_confirmed_once_with_same_core(self):
        op = self.booking(); grant = self.grant(op)
        ride = self.call(op, grant)['data']['current']
        self.assertEqual(ride['status'], 'assigned')
        self.assertEqual(self.core.get_ride('rider-a1', ride['id'])['reservation_status'], 'confirmed')
        self.assertTrue(self.call(op, grant)['data']['replayed'])
        self.assertEqual(self.sql('SELECT reserved FROM runs'), [(1,)])

    def test_two_clients_compete_for_last_capacity_in_core(self):
        a = self.booking(self.candidate(passengers=2)); b = self.booking(self.candidate('rider-a2', passengers=2), 'rider-a2')
        ga, gb = self.grant(a), self.grant(b, 'rider-a2')
        with ThreadPoolExecutor(2) as pool:
            results = [j.result() for j in [pool.submit(self.call, a, ga), pool.submit(self.call, b, gb)]]
        self.assertEqual(sum(r['ok'] for r in results), 1)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'), [(1,)])
        self.assertEqual(self.sql('SELECT reserved FROM runs'), [(2,)])

    def test_expired_candidate_cannot_be_substituted_by_another(self):
        op = self.booking(); grant = self.grant(op); self.now += 121
        self.assertEqual(rpc(self.port, grant, 'tools/call', {'name': 'yoko_execute_approved_operation', 'arguments': {'operation': op}})[0], 401)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'), [(0,)])
