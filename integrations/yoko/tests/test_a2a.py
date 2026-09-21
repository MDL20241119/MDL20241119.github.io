"""A2A task/business separation, exact approval, recovery, SDK and real HTTP."""
import asyncio
import copy
import hashlib
import json
import secrets
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import httpx
from google.protobuf.json_format import MessageToDict, ParseDict
from a2a.client.client import ClientConfig
from a2a.client.client_factory import create_client
from a2a.types import a2a_pb2 as p
from a2a.utils.proto_utils import validate_proto_required_fields
from app import agent_actions
from app.a2a_adapter import card, create_app
from app.agent_tasks import operation_reference, LEASE_SECONDS
from app.core import Core, DomainError
from app.db import initialize
from app.delegation import Grants
from scripts.a2a_test_support import running_a2a, rpc, http, send_params
from scripts.backup_local import backup
from tests.test_core import REQUEST
from tests.test_p3 import Fixture
from tests.test_booking import BookingFixture


class TaskTests(Fixture):
    def send(self, value, grant=None, **kwargs):
        grant = grant or self.grant()
        return self.core.tasks.send('rider-a1', self.authz(grant), kwargs.pop('message_id', secrets.token_hex(12)), value, **kwargs)

    def test_wait_for_owner_then_resume_exact_operation(self):
        pending = self.send({'action': 'execute'})
        self.assertEqual(pending['state'], 'input_required'); self.assertEqual(self.sql('SELECT count(*) FROM rides'), [(0,)])
        op = self.prepare('request', REQUEST)
        result = self.send(operation_reference(op), self.grant(op), task_id=pending['id'])
        self.assertEqual((result['state'], result['result']['current']['status']), ('completed','requested'))
        self.assertEqual(result['context_id'], pending['context_id'])

    def test_read_scope_cannot_execute_even_with_correct_references(self):
        op = self.prepare('request', REQUEST)
        pending = self.send(operation_reference(op))
        self.assertEqual(pending['code'], 'OWNER_APPROVAL_REQUIRED')
        self.assertEqual(self.sql('SELECT operation_id FROM agent_tasks'), [(None,)])
        self.assertEqual(self.sql('SELECT count(*) FROM operations'), [(0,)])

    def test_modified_approval_is_rejected_without_new_task(self):
        op = self.prepare('request', REQUEST); grant = self.grant(op)
        for key,value in [('kind','cancel'),('operation_id','different-id'),('operation_digest','0'*64)]:
            ref = {**operation_reference(op), key:value}
            self.denied('APPROVAL_MISMATCH', self.send, ref, grant)
        self.assertEqual(self.sql('SELECT count(*) FROM agent_tasks'), [(0,)])

    def test_message_replay_and_changed_message_rejected(self):
        op = self.prepare('request', REQUEST); grant = self.grant(op); ref = operation_reference(op)
        first = self.send(ref, grant, message_id='fixed-message')
        again = self.send(ref, grant, message_id='fixed-message')
        self.assertEqual(again['id'], first['id'])
        self.assertEqual(self.sql('SELECT count(*) FROM events'), [(1,)])
        self.denied('MESSAGE_REUSE', self.send, {'action':'execute'}, grant, message_id='fixed-message')

    def test_cancel_task_is_not_reservation_cancel(self):
        ride = self.create(); pending = self.send({'action':'execute'})
        self.assertEqual(self.core.tasks.cancel('rider-a1',self.authz(self.grant()),pending['id'])['state'],'canceled')
        self.assertEqual(self.core.get_ride('rider-a1',ride['id'])['status'],'requested')
        self.denied('TASK_TERMINAL',self.send,{'action':'execute'},task_id=pending['id'])

    def test_completed_task_cannot_cancel_business_result(self):
        op = self.prepare('request',REQUEST); result = self.send(operation_reference(op),self.grant(op))
        self.denied('TASK_NOT_CANCELABLE',self.core.tasks.cancel,'rider-a1',self.authz(self.grant()),result['id'])
        self.assertEqual(self.sql('SELECT status FROM rides'),[('requested',)])

    def test_owner_tenant_role_and_client_boundaries(self):
        result = self.send({'action':'execute'})
        for actor in ('rider-a2','rider-b1'):
            auth = self.authz(self.grant(actor=actor))
            self.denied('TASK_NOT_FOUND',self.core.tasks.get,actor,auth,result['id'])
            self.assertEqual(self.core.tasks.list(actor,auth)['tasks'],[])
        grant = self.grants.issue('rider-a1',{'client_id':'other-client','scopes':['mobility:read'],'expires_in':300,'operation':None})
        self.denied('TASK_NOT_FOUND',self.core.tasks.get,'rider-a1',self.authz(grant),result['id'])
        self.denied('FORBIDDEN',self.core.tasks.list,'admin-a1',self.authz(self.grant(actor='admin-a1')))

    def test_read_artifact_minimizes_personal_data(self):
        ride = self.create()
        result = self.send({'action':'read_reservation','reservation_id':ride['id']})
        self.assertEqual(result['result']['current']['id'],ride['id'])
        for key in ('rider_id','driver_id','vehicle_id','events','payment'):
            self.assertNotIn(key,result['result']['current'])
        foreign = self.create(actor='rider-a2')
        result = self.send({'action':'read_reservation','reservation_id':foreign['id']})
        self.assertEqual((result['state'],result['code']),('failed','NOT_FOUND'))

    def test_restart_and_fresh_grant_after_revocation(self):
        grant=self.grant(); result=self.send({'action':'execute'},grant)
        self.grants.revoke('rider-a1',grant['grant_id'])
        auth={'token_hash':hashlib.sha256(grant['access_token'].encode()).hexdigest(),'client_id':grant['client_id']}
        self.denied('INVALID_GRANT',Core(self.path).tasks.get,'rider-a1',auth,result['id'])
        self.assertEqual(Core(self.path).tasks.get('rider-a1',self.authz(self.grant()),result['id'])['state'],'input_required')

    def test_revocation_race_before_business_transaction(self):
        op=self.prepare('request',REQUEST); grant=self.grant(op); original=agent_actions.execute
        def revoke(*args):
            self.grants.revoke('rider-a1',grant['grant_id'])
            return original(*args)
        with patch('app.agent_actions.execute',side_effect=revoke):
            with self.assertRaises(DomainError): self.send(operation_reference(op),grant)
        self.assertEqual(self.sql('SELECT count(*) FROM rides'),[(0,)])
        self.assertEqual(self.sql('SELECT state,code FROM agent_tasks'),[('failed','INVALID_GRANT')])

    def test_concurrent_duplicate_is_single_business_commit(self):
        op=self.prepare('request',REQUEST); grant=self.grant(op); barrier=threading.Barrier(4)
        def invoke():
            barrier.wait(3)
            return self.send(operation_reference(op),grant,message_id='parallel-message')
        with ThreadPoolExecutor(4) as pool: results=list(pool.map(lambda _:invoke(),range(4)))
        self.assertEqual(len({r['id'] for r in results}),1)
        self.assertTrue(all(r['state']=='completed' for r in results))
        self.assertEqual(self.sql('SELECT count(*) FROM outbox'),[(1,)])

    def test_cross_adapter_operation_is_not_repeated(self):
        op=self.prepare('request',REQUEST); grant=self.grant(op); auth=self.authz(grant)
        first=agent_actions.execute(self.core,'rider-a1',op,auth)
        result=self.send(operation_reference(op),grant)
        self.assertEqual(result['result']['current']['id'],first['current']['id'])
        self.assertEqual(self.sql('SELECT count(*) FROM events'),[(1,)])

    def test_crash_after_commit_recovers_from_operation_ledger(self):
        op=self.prepare('request',REQUEST); grant=self.grant(op)
        with patch.object(self.core.tasks,'finish',side_effect=RuntimeError('simulated crash')):
            with self.assertRaises(RuntimeError): self.send(operation_reference(op),grant)
        task_id=self.sql('SELECT id FROM agent_tasks')[0][0]
        result=Core(self.path).tasks.get('rider-a1',self.authz(self.grant()),task_id)
        self.assertEqual((result['state'],result['code']),('completed','OPERATION_RECONCILED'))
        self.assertEqual(self.sql('SELECT count(*) FROM operations'),[(1,)])

    def test_abandoned_lease_recovery_fences_stale_worker(self):
        op=self.prepare('request',REQUEST); grant=self.grant(op)
        with patch.object(self.core.tasks,'run',side_effect=RuntimeError('before commit')):
            with self.assertRaises(RuntimeError): self.send(operation_reference(op),grant)
        task_id,lease=self.sql('SELECT id,lease_owner FROM agent_tasks')[0]
        self.sql('UPDATE agent_tasks SET lease_until=0')
        result=self.core.tasks.get('rider-a1',self.authz(grant),task_id)
        self.assertEqual(result['code'],'RETRY_SAME_APPROVAL')
        self.core.tasks.cancel('rider-a1',self.authz(grant),task_id)
        self.core.tasks.run('rider-a1',self.authz(grant),task_id,lease,operation_reference(op),op)
        self.assertEqual(self.sql('SELECT count(*) FROM rides'),[(0,)])
        self.assertEqual(self.sql('SELECT state FROM agent_tasks'),[('canceled',)])

    def test_uncommitted_task_resumes_with_same_approval_and_new_message(self):
        op=self.prepare('request',REQUEST); grant=self.grant(op)
        with patch.object(self.core.tasks,'run',side_effect=RuntimeError('before commit')):
            with self.assertRaises(RuntimeError):self.send(operation_reference(op),grant)
        task_id=self.sql('SELECT id FROM agent_tasks')[0][0]
        self.sql('UPDATE agent_tasks SET lease_until=0')
        result=self.send(operation_reference(op),grant,task_id=task_id)
        self.assertEqual(result['state'],'completed')
        self.assertEqual(self.sql('SELECT count(*) FROM operations'),[(1,)])

    def test_working_task_cancel_is_refused_before_commit(self):
        op=self.prepare('request',REQUEST);grant=self.grant(op)
        with patch.object(self.core.tasks,'run',side_effect=RuntimeError('interrupted')):
            with self.assertRaises(RuntimeError):self.send(operation_reference(op),grant)
        task_id=self.sql('SELECT id FROM agent_tasks')[0][0]
        self.denied('TASK_NOT_CANCELABLE',self.core.tasks.cancel,'rider-a1',self.authz(grant),task_id)
        self.assertEqual(self.sql('SELECT count(*) FROM rides'),[(0,)])

    def test_recovery_does_not_accept_a_different_prior_operation(self):
        op=self.prepare('request',REQUEST); self.execute(op)
        other=self.prepare('request',{**REQUEST,'passengers':2})
        other.update(operation_id=op['operation_id'],idempotency_key=op['idempotency_key'])
        grant=self.grant(other)
        with patch.object(self.core.tasks,'run',side_effect=RuntimeError('before checking conflict')):
            with self.assertRaises(RuntimeError):self.send(operation_reference(other),grant)
        self.sql('UPDATE agent_tasks SET lease_until=0')
        result=self.core.tasks.get('rider-a1',self.authz(grant),self.sql('SELECT id FROM agent_tasks')[0][0])
        self.assertEqual(result['state'],'input_required')

    def test_business_failure_rolls_back_and_task_records_failure(self):
        op=self.prepare('request',REQUEST); grant=self.grant(op)
        self.sql('UPDATE services SET revision=revision+1')
        result=self.send(operation_reference(op),grant)
        self.assertEqual((result['state'],result['code']),('failed','TERMS_CHANGED'))
        self.assertEqual(self.sql('SELECT count(*) FROM operations'),[(0,)])

    def test_round_and_timeout_limits(self):
        pending=self.send({'action':'execute'})
        for _ in range(8): pending=self.send({'action':'execute'},task_id=pending['id'])
        self.assertEqual((pending['state'],pending['code']),('failed','ROUND_LIMIT'))
        expired=self.send({'action':'execute'}); self.sql('UPDATE agent_tasks SET expires_at=0 WHERE id=?',(expired['id'],))
        result=self.core.tasks.get('rider-a1',self.authz(self.grant()),expired['id'])
        self.assertEqual((result['state'],result['code']),('failed','TASK_EXPIRED'))

    def test_context_cannot_be_invented_or_spoofed(self):
        pending=self.send({'action':'execute'})
        self.denied('TASK_NOT_FOUND',self.send,{'action':'execute'},context_id='unknown-context')
        self.denied('INVALID_INPUT',self.send,{'action':'execute'},task_id=pending['id'],context_id='other-context')
        other=self.send({'action':'execute'},context_id=pending['context_id'])
        self.assertEqual(other['context_id'],pending['context_id'])

    def test_paginated_history_artifacts_and_filter_binding(self):
        grant=self.grant(); auth=self.authz(grant)
        for _ in range(3):self.send({'action':'execute'},grant)
        first=self.core.tasks.list('rider-a1',auth,page_size=2)
        self.assertEqual((len(first['tasks']),first['total_size']),(2,3))
        second=self.core.tasks.list('rider-a1',auth,page_size=2,page_token=first['next_page_token'])
        self.assertEqual(len(second['tasks']),1)
        self.assertFalse({t['id'] for t in first['tasks']} & {t['id'] for t in second['tasks']})
        self.denied('INVALID_INPUT',self.core.tasks.list,'rider-a1',auth,state='completed',page_token=first['next_page_token'])
        self.assertTrue(all(t['history']==[] and t['result'] is None for t in first['tasks']))

    def test_keyset_cursor_does_not_repeat_rows_after_new_task(self):
        grant=self.grant();auth=self.authz(grant)
        original=[self.send({'action':'execute'},grant) for _ in range(3)]
        first=self.core.tasks.list('rider-a1',auth,page_size=2)
        self.send({'action':'execute'},grant)
        second=self.core.tasks.list('rider-a1',auth,page_size=2,page_token=first['next_page_token'])
        self.assertEqual({r['id'] for r in first['tasks']+second['tasks']},{r['id'] for r in original})
        self.assertEqual(len(second['tasks']),1)
        self.assertEqual(second['next_page_token'],'')

    def test_task_storage_has_no_token_or_full_approval(self):
        op=self.prepare('request',REQUEST); grant=self.grant(op);self.send(operation_reference(op),grant)
        stored=json.dumps(self.sql('SELECT * FROM agent_tasks')+self.sql('SELECT * FROM agent_messages')+self.sql('SELECT * FROM agent_task_events'))
        for secret in (grant['access_token'],hashlib.sha256(grant['access_token'].encode()).hexdigest(),op['payload']['draft_id']):
            self.assertNotIn(secret,stored)

    def test_schema_six_migration_and_backup_resume(self):
        self.sql('DROP TABLE agent_task_events');self.sql('DROP TABLE agent_messages');self.sql('DROP TABLE agent_tasks')
        self.sql("UPDATE meta SET value='6' WHERE key='schema_version'")
        ride=self.create();initialize(self.path)
        self.assertEqual(self.sql("SELECT value FROM meta WHERE key='schema_version'"),[('8',)])
        pending=self.send({'action':'execute'});dest=Path(self.temp.name)/'restored.sqlite3';backup(self.path,dest)
        restored=Core(dest); grants=Grants(restored)
        grant=grants.issue('rider-a1',{'client_id':'client-test','scopes':['mobility:read'],'expires_in':300,'operation':None})
        auth=grants.resolve('Bearer '+grant['access_token'],'client-test')[1]
        self.assertEqual(restored.tasks.get('rider-a1',auth,pending['id'])['state'],'input_required')
        self.assertEqual(restored.get_ride('rider-a1',ride['id'])['id'],ride['id'])


class HttpTests(Fixture):
    def test_official_sdk_card_send_get_list_cancel_and_resume(self):
        async def check(port,grant):
            async with httpx.AsyncClient(headers={'Authorization':'Bearer '+grant['access_token'],'X-Client-ID':grant['client_id']},trust_env=False) as http_client:
                client=await create_client(f'http://127.0.0.1:{port}',ClientConfig(streaming=False,httpx_client=http_client))
                request=ParseDict(send_params({'action':'execute'}),p.SendMessageRequest())
                events=[event async for event in client.send_message(request)]
                pending=events[0].task
                self.assertEqual(pending.status.state,p.TASK_STATE_INPUT_REQUIRED)
                received=await client.get_task(p.GetTaskRequest(id=pending.id,history_length=0))
                self.assertEqual(len(received.history),0)
                listed=await client.list_tasks(p.ListTasksRequest(page_size=5))
                self.assertEqual(listed.total_size,1)
                canceled=await client.cancel_task(p.CancelTaskRequest(id=pending.id))
                self.assertEqual(canceled.status.state,p.TASK_STATE_CANCELED)
                op=self.prepare('request',REQUEST); write=self.grant(op)
                http_client.headers['Authorization']='Bearer '+write['access_token']
                events=[event async for event in client.send_message(ParseDict(send_params(operation_reference(op),'message-2'),p.SendMessageRequest()))]
                self.assertEqual(events[0].task.status.state,p.TASK_STATE_COMPLETED)
                data=MessageToDict(events[0].task.artifacts[0].parts[0].data)
                self.assertEqual(data['current']['status'],'requested')
        with running_a2a(self.core) as (port,_):asyncio.run(check(port,self.grant()))

    def test_card_is_public_local_description_not_authorization(self):
        with running_a2a(self.core) as (port,_):
            code,body,headers=http(port,'/.well-known/agent-card.json')
            self.assertEqual(code,200);validate_proto_required_fields(ParseDict(body,p.AgentCard()))
            self.assertEqual(body['supportedInterfaces'][0]['protocolVersion'],'1.0')
            self.assertEqual(headers.get('cache-control'),'no-store')
            self.assertEqual(rpc(port,None,'ListTasks')[0],401)
            self.assertNotIn('access_token',json.dumps(body))

    def test_missing_wrong_minor_and_legacy_versions_rejected(self):
        with running_a2a(self.core) as (port,_):
            grant=self.grant()
            for version in (None,'','0.3','1.1','1.99','2.0'):
                code,body,_=rpc(port,grant,'ListTasks',headers={'A2A-Version':version})
                self.assertEqual((code,body['error']['code']),(400,-32009))
            self.assertIn('result',rpc(port,grant,'ListTasks',headers={'A2A-Version':'1.0.4'})[1])

    def test_untrusted_client_origin_host_and_proxy(self):
        with running_a2a(self.core,clients=('other-client',)) as (port,_):
            self.assertEqual(rpc(port,self.grant(),'ListTasks')[0],403)
        with running_a2a(self.core) as (port,_):
            for header in ({'Origin':'https://evil.invalid'},{'Host':'evil.invalid'},{'X-Forwarded-For':'127.0.0.1'}):
                self.assertEqual(rpc(port,self.grant(),'ListTasks',headers=header)[0],403)

    def test_invalid_commands_urls_and_metadata_do_not_authorize(self):
        with running_a2a(self.core) as (port,_):
            grant=self.grant()
            for value in ({'action':'execute','confirmed':True},{'action':'run','url':'http://169.254.169.254'},{'action':'execute','role':'admin'}):
                self.assertIn('error',rpc(port,grant,'SendMessage',send_params(value))[1])
            params=send_params({'action':'execute'});params['message']['parts']=[{'url':'http://169.254.169.254/latest','mediaType':'application/json'}]
            self.assertEqual(rpc(port,grant,'SendMessage',params)[1]['error']['code'],-32005)
            params=send_params({'action':'execute'});params['tenant']='tenant-b'
            self.assertIn('error',rpc(port,grant,'SendMessage',params)[1])
            self.assertEqual(self.sql('SELECT count(*) FROM rides'),[(0,)])

    def test_legacy_method_unknown_and_bad_json(self):
        with running_a2a(self.core) as (port,_):
            grant=self.grant()
            for method in ('message/send','not-a-method'):
                self.assertEqual(rpc(port,grant,method)[1]['error']['code'],-32601)
            self.assertIn('error',rpc(port,grant,'SendMessage',{})[1])

    def test_task_owner_and_revoked_grant_over_http(self):
        with running_a2a(self.core) as (port,_):
            grant=self.grant();body=rpc(port,grant,'SendMessage',send_params({'action':'execute'}))[1]
            task_id=body['result']['task']['id']
            self.assertEqual(rpc(port,self.grant(actor='rider-a2'),'GetTask',{'id':task_id})[1]['error']['code'],-32001)
            rpc(port,grant,'CancelTask',{'id':task_id})
            self.assertEqual(rpc(port,grant,'SendMessage',send_params({'action':'execute'},'message-2',task_id))[1]['error']['code'],-32004)
            self.grants.revoke('rider-a1',grant['grant_id'])
            self.assertEqual(rpc(port,grant,'GetTask',{'id':task_id})[0],401)

    def test_no_push_streaming_or_autonomous_loop(self):
        with running_a2a(self.core) as (port,_):
            grant=self.grant()
            self.assertEqual(rpc(port,grant,'GetExtendedAgentCard')[1]['error']['code'],-32004)
            params=send_params({'action':'execute'});params['configuration']={'acceptedOutputModes':['image/png']}
            self.assertEqual(rpc(port,grant,'SendMessage',params)[1]['error']['code'],-32005)

    def test_nonblocking_sdk_returns_working_then_get_completed(self):
        entered,release=threading.Event(),threading.Event()
        original=agent_actions.execute
        def slow(*args):
            entered.set()
            if not release.wait(3):raise RuntimeError('test worker was not released')
            return original(*args)
        async def check(port,grant,operation):
            async with httpx.AsyncClient(headers={'Authorization':'Bearer '+grant['access_token'],'X-Client-ID':grant['client_id']},trust_env=False) as hc:
                client=await create_client(f'http://127.0.0.1:{port}',ClientConfig(streaming=False,polling=True,httpx_client=hc))
                request=ParseDict(send_params(operation_reference(operation)),p.SendMessageRequest())
                try:
                    events=[event async for event in client.send_message(request)]
                    working=events[0].task
                    self.assertTrue(entered.wait(1))
                    self.assertEqual(working.status.state,p.TASK_STATE_WORKING)
                    self.assertEqual((await client.get_task(p.GetTaskRequest(id=working.id))).status.state,p.TASK_STATE_WORKING)
                finally:release.set()
                for _ in range(100):
                    finished=await client.get_task(p.GetTaskRequest(id=working.id))
                    if finished.status.state==p.TASK_STATE_COMPLETED:break
                    await asyncio.sleep(.02)
                self.assertEqual(finished.status.state,p.TASK_STATE_COMPLETED)
                self.assertNotEqual(finished.status.message.message_id,working.status.message.message_id)
        operation=self.prepare('request',REQUEST);grant=self.grant(operation)
        with running_a2a(self.core) as (port,_),patch('app.agent_actions.execute',side_effect=slow):
            asyncio.run(check(port,grant,operation))
        self.assertEqual(self.sql('SELECT count(*) FROM rides'),[(1,)])

    def test_valid_empty_protocol_state_filters(self):
        with running_a2a(self.core) as (port,_):
            for status in ('TASK_STATE_SUBMITTED','TASK_STATE_AUTH_REQUIRED'):
                body=rpc(port,self.grant(),'ListTasks',{'status':status})[1]
                self.assertEqual(body['result']['tasks'],[])
                self.assertEqual(body['result']['nextPageToken'],'')

    def test_status_message_ids_change_even_with_zero_history_and_fixed_clock(self):
        now=self.core.clock();self.core.clock=lambda:now
        with running_a2a(self.core) as (port,_):
            grant=self.grant();params=send_params({'action':'execute'});params['configuration']={'historyLength':0}
            first=rpc(port,grant,'SendMessage',params)[1]['result']['task']
            params=send_params({'action':'execute'},'message-2',first['id']);params['configuration']={'historyLength':0}
            second=rpc(port,grant,'SendMessage',params)[1]['result']['task']
            self.assertNotEqual(first['status']['message']['messageId'],second['status']['message']['messageId'])
            self.assertFalse(second.get('history'))

    def test_body_limit_and_rate_limit(self):
        with running_a2a(self.core) as (port,app):
            grant=self.grant()
            self.assertEqual(rpc(port,grant,'SendMessage',{'padding':'x'*17000})[0],413)
            app.requests.extend([time.monotonic()]*600)
            self.assertEqual(rpc(port,grant,'ListTasks')[0],429)

    def test_server_restart_retains_task_and_grant(self):
        grant=self.grant()
        with running_a2a(self.core) as (port,_):
            result=rpc(port,grant,'SendMessage',send_params({'action':'execute'}))[1]['result']['task']
        with running_a2a(Core(self.path)) as (port,_):
            again=rpc(port,grant,'GetTask',{'id':result['id']})[1]['result']
            self.assertEqual(again['id'],result['id'])

    def test_official_sources_and_sdk_are_pinned(self):
        from importlib.metadata import version
        root=Path(__file__).resolve().parents[1]
        self.assertEqual(version('a2a-sdk'),'1.1.4')
        self.assertEqual(hashlib.sha256((root/'artifacts/standards/a2a/a2a.proto').read_bytes()).hexdigest(),
            '945df6e34001b2bfd0fd62d9484b63094dfad9d78705e41e2873441c419ae2d1')
        self.assertEqual(p.Task.DESCRIPTOR.full_name,'lf.a2a.v1.Task')
        self.assertEqual(p.DESCRIPTOR.services_by_name['A2AService'].methods_by_name['SendMessage'].input_type.name,'SendMessageRequest')

    def test_http_failure_after_commit_is_opaque_and_get_recovers(self):
        op=self.prepare('request',REQUEST);grant=self.grant(op)
        with running_a2a(self.core) as (port,_):
            with patch.object(self.core.tasks,'finish',side_effect=RuntimeError('private SQL / secret token')):
                body=rpc(port,grant,'SendMessage',send_params(operation_reference(op)))[1]
            self.assertEqual(body['error']['code'],-32603)
            self.assertNotIn('private SQL',json.dumps(body))
            task_id=self.sql('SELECT id FROM agent_tasks')[0][0]
            result=rpc(port,self.grant(),'GetTask',{'id':task_id})[1]['result']
            self.assertEqual(result['status']['state'],'TASK_STATE_COMPLETED')
            self.assertEqual(self.sql('SELECT count(*) FROM rides'),[(1,)])

    def test_cli_rejects_public_mode_missing_db_and_invalid_port(self):
        import subprocess,os
        for args,env in [(['--host','0.0.0.0'],{}),(['--db',str(Path(self.temp.name)/'missing.sqlite3')],{}),(['--port','0'],{}),([] ,{'YOKO_ENV':'production'})]:
            result=subprocess.run([sys.executable,'-m','app.a2a_local',*args],env={**os.environ,**env},capture_output=True,text=True)
            self.assertEqual(result.returncode,2)


class A2ABookingTests(BookingFixture):
    def run_booking(self,op,actor='rider-a1',grant=None):
        grant=grant or self.grant(op,actor)
        return self.core.tasks.send(actor,self.authz(grant),secrets.token_hex(16),operation_reference(op))

    def test_candidate_booking_assigns_and_cancellation_releases_once(self):
        self.ready();op=self.booking(self.candidate(passengers=2))
        result=self.run_booking(op);ride=result['result']['current']
        self.assertEqual((result['state'],ride['status']),('completed','assigned'))
        cancel=self.prepare('cancel',{'ride_id':ride['id']})
        grant=self.grant(cancel)
        self.run_booking(cancel,grant=grant);self.run_booking(cancel,grant=grant)
        self.assertEqual(self.sql('SELECT reserved FROM runs'),[(0,)])
        self.assertEqual(self.sql('SELECT count(*) FROM events'),[(2,)])

    def test_two_agents_compete_for_last_seat(self):
        self.ready();self.execute(self.booking(self.candidate(passengers=2)))
        first=self.booking();second=self.booking(actor='rider-a2')
        with ThreadPoolExecutor(2) as pool:
            jobs=[pool.submit(self.run_booking,first),pool.submit(self.run_booking,second,'rider-a2')]
            results=[job.result() for job in jobs]
        self.assertCountEqual([r['state'] for r in results],['completed','failed'])
        self.assertEqual([r['code'] for r in results if r['state']=='failed'],['CAPACITY_FULL'])
        self.assertEqual(self.sql('SELECT reserved FROM runs'),[(3,)])
