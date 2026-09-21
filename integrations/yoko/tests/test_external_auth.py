import json
import asyncio
import secrets
import shutil
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from app.core import Core, DomainError
from app.db import initialize, connect
from app.external_auth import Identities, LineLogin, ProviderHTTP
from scripts.backup_local import backup
from scripts.https_test_support import integration, enroll, login
from tests.test_core import REQUEST


class ExternalAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = tempfile.TemporaryDirectory(); cls.template = Path(cls.base.name)/'template.db'; initialize(cls.template)
    @classmethod
    def tearDownClass(cls): cls.base.cleanup()
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(); self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/'db.sqlite'; shutil.copyfile(self.template, self.path)
        self.core = Core(self.path)
        self.provider, self.app, self.client, self.origin, self.tls = self.enterContext(integration(self.core, self.directory.name))
        self.ids = enroll(self.core, self.provider, self.origin)
    def sql(self, query, args=()):
        db = connect(self.path)
        try: return [tuple(r) for r in db.execute(query, args)]
        finally: db.close()
    def headers(self, adapter='direct', **changes):
        resource = self.app.grants[adapter].resource
        return {'Authorization': 'Bearer '+self.provider.token(resource, **changes)}
    def operation(self):
        response = self.client.post('/api/drafts/request', json=REQUEST)
        self.assertEqual(response.status_code, 200, response.text)
        draft = response.json(); op = secrets.token_hex(16)
        return {'operation_id': op, 'idempotency_key': op, 'kind': 'request', 'payload': {'draft_id': draft['id'], 'details': draft['details']}}
    def approve(self, operation, adapter='direct'):
        response = self.client.post('/api/oauth-approvals', json={'adapter': adapter, 'identity_id': self.ids[adapter],
            'client_id': 'connected-test', 'operation': operation, 'expires_in': 120})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn('access_token', response.json())
        return response.json()['approval_id']
    def direct(self, operation, headers):
        return self.client.post('/direct/v1/actions/'+operation['kind'], json={k:v for k,v in operation.items() if k!='kind'}, headers=headers)

    def test_tls_chain_verified_and_plain_password_disabled(self):
        with httpx.Client(trust_env=False, timeout=3) as client:
            with self.assertRaises(httpx.ConnectError): client.get(self.origin+'/')
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertNotIn('local-test-only', self.client.get('/').text)
        self.assertEqual(self.client.post('/api/session', json={'username':'rider-a1','password':'local-test-only'}).status_code, 403)

    def test_line_pkce_login_secure_session_and_three_roles_flow(self):
        me = login(self.client, self.provider)
        self.assertEqual(me['user']['role'], 'rider')
        operation = self.operation()
        response = self.client.post('/api/actions/request', json={k:v for k,v in operation.items() if k!='kind'})
        self.assertEqual(response.status_code, 200, response.text); ride = response.json()['current']
        for actor, subject in [('driver-a1','synthetic-driver'),('admin-a1','synthetic-admin')]:
            enroll(self.core, self.provider, self.origin, actor, subject)
            with httpx.Client(base_url=self.origin, verify=self.tls, trust_env=False) as other:
                login(other, self.provider, subject)
                if actor.startswith('driver'):
                    for kind in ('accept','arrive','board','complete'):
                        op=secrets.token_hex(16)
                        r=other.post('/api/actions/'+kind,json={'operation_id':op,'idempotency_key':op,'payload':{'ride_id':ride['id'],'version':ride['version'],'stopped':True}})
                        self.assertEqual(r.status_code,200,r.text);ride=r.json()['current']
                self.assertEqual(other.get('/api/rides/'+ride['id']).json()['status'],'completed')
        self.assertEqual(self.client.get('/api/rides/'+ride['id']).json()['status'],'completed')
        self.assertEqual(self.sql('SELECT COUNT(*) FROM login_flows'),[(0,)])

    def test_callback_browser_binding_state_replay_and_expiry(self):
        start = self.client.get('/auth/line/start'); code,state=self.provider.authorize(start.headers['location'])
        with httpx.Client(base_url=self.origin,verify=self.tls,trust_env=False) as stranger:
            self.assertEqual(stranger.get('/auth/line/callback',params={'code':code,'state':state}).status_code,401)
        response=self.client.get('/auth/line/callback',params={'code':code,'state':state})
        self.assertEqual(response.status_code,303,response.text)
        self.assertIn('Secure',response.headers['set-cookie']);self.assertIn('HttpOnly',response.headers['set-cookie'])
        self.assertEqual(self.client.get('/auth/line/callback',params={'code':code,'state':state}).status_code,401)
        start=self.client.get('/auth/line/start');code,state=self.provider.authorize(start.headers['location'])
        self.sql('UPDATE login_flows SET expires_at=0')
        self.assertEqual(self.client.get('/auth/line/callback',params={'code':code,'state':state}).status_code,401)

    def test_id_token_wrong_issuer_audience_expiry_and_missing_nonce(self):
        for bad in ({'iss':'https://evil.invalid'}, {'aud':'other'}, {'exp':0}, {'iat':time.time()+1000}, {'nonce':'wrong'}):
            with self.subTest(bad=bad):
                self.provider.override=bad
                start=self.client.get('/auth/line/start');code,state=self.provider.authorize(start.headers['location'])
                self.assertEqual(self.client.get('/auth/line/callback',params={'code':code,'state':state}).status_code,401)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM sessions'),[(0,)])

    def test_unenrolled_identity_and_forged_role_are_not_admin(self):
        self.provider.override={'role':'admin','email':'admin@example.invalid'}
        self.assertEqual(login(self.client,self.provider)['user']['role'],'rider')
        self.client.cookies.clear()
        start=self.client.get('/auth/line/start');code,state=self.provider.authorize(start.headers['location'],'not-enrolled')
        self.assertEqual(self.client.get('/auth/line/callback',params={'code':code,'state':state}).status_code,403)

    def test_csrf_logout_and_link_revocation(self):
        login(self.client,self.provider)
        self.assertEqual(self.client.post('/api/drafts/request',json=REQUEST,headers={'X-CSRF-Token':'bad'}).status_code,403)
        Identities(self.core).revoke(self.ids['line'])
        self.assertEqual(self.client.get('/api/snapshot').status_code,401)
        with self.assertRaises(DomainError): Identities(self.core).bind(LineLogin.ISSUER,self.provider.channel,'synthetic-person-a1','admin-a1')

    def test_resource_metadata_and_authentication_challenge(self):
        from jsonschema import Draft202012Validator
        spec_response=self.client.get('/api/openapi.json')
        self.assertEqual(spec_response.status_code,200,spec_response.text)
        spec=spec_response.json()
        self.assertEqual(spec['servers'][0]['url'],self.origin)
        for adapter in ('mcp','a2a','direct'):
            grant=self.app.grants[adapter]
            response=self.client.get(grant.metadata_url)
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()['resource'],grant.resource)
            schema=spec['paths'][urlsplit(grant.metadata_url).path]['get']['responses']['200']['content']['application/json']['schema']
            Draft202012Validator(schema).validate(response.json())
        response=self.client.get('/direct/v1/rides')
        self.assertEqual(response.status_code,401)
        self.assertIn('resource_metadata=',response.headers['www-authenticate'])
        me=login(self.client,self.provider)
        Draft202012Validator({'$ref':'#/components/schemas/Session','components':spec['components']}).validate(me)

    def test_oauth_issuer_audience_active_expiry_scope_client_and_role(self):
        cases=[({'active':False},401),({'iss':'https://evil.invalid'},401),({'aud':self.origin+'/mcp'},401),({'exp':0},401),
            ({'iat':time.time()+1000},401),({'nbf':time.time()+1000},401),({'scope':'mobility:execute'},403),({'client':'not-allowed'},403),({'subject':'unregistered'},403)]
        for changes,status in cases:
            with self.subTest(changes=changes):
                self.assertEqual(self.client.get('/direct/v1/rides',headers=self.headers(**changes)).status_code,status)
        headers=self.headers();headers['X-Client-ID']='second-client'
        self.assertEqual(self.client.get('/direct/v1/rides',headers=headers).status_code,403)
        self.assertEqual(self.client.get('/direct/v1/rides',headers=self.headers()).status_code,200)

    def test_exact_approval_replay_cross_client_and_revocation(self):
        login(self.client,self.provider);op=self.operation();headers=self.headers()
        self.assertEqual(self.direct(op,headers).status_code,403)
        approval=self.approve(op);headers['X-Yoko-Approval']=approval
        tampered={**op,'operation_id':secrets.token_hex(16)}
        self.assertEqual(self.direct(tampered,headers).status_code,403)
        self.assertEqual(self.direct(tampered,self.headers()).status_code,403)
        self.assertEqual(self.direct(op,self.headers(scope='mobility:read')).status_code,403)
        wrong=self.headers(client='second-client');wrong['X-Yoko-Approval']=approval
        self.assertEqual(self.direct(op,wrong).status_code,403)
        first=self.direct(op,headers);self.assertEqual(first.status_code,200,first.text)
        self.assertTrue(self.direct(op,headers).json()['replayed'])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'),[(1,)])
        self.client.post('/api/oauth-approvals/revoke',json={'grant_id':approval})
        self.assertEqual(self.direct(op,headers).status_code,403)

    def test_introspection_revocation_and_core_transaction_recheck(self):
        login(self.client,self.provider);op=self.operation();approval=self.approve(op);headers=self.headers()
        grant=self.app.grants['direct'];actor,authorization,_=grant.resolve(headers['Authorization'],None,approval)
        Identities(self.core).revoke(self.ids['direct'])
        with self.assertRaises(DomainError): self.core.mutate(actor,op['operation_id'],op['idempotency_key'],op['kind'],op['payload'],authorization)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM rides'),[(0,)])
        token=self.provider.token(self.app.grants['mcp'].resource)
        self.provider.tokens[token]['active']=False
        self.assertEqual(self.client.post('/mcp',json={},headers={'Authorization':'Bearer '+token}).status_code,401)

    def test_foreign_owner_and_cross_tenant_access(self):
        login(self.client,self.provider);op=self.operation();approval=self.approve(op);headers=self.headers();headers['X-Yoko-Approval']=approval
        ride=self.direct(op,headers).json()['current']['id']
        for actor,subject in [('rider-a2','another'),('rider-b1','tenant-b')]:
            enroll(self.core,self.provider,self.origin,actor,subject)
            self.assertEqual(self.client.get('/direct/v1/rides/'+ride,headers=self.headers(subject=subject)).status_code,404)

    def test_provider_outage_fail_closed_no_saved_tokens(self):
        self.provider.fail_status=503
        self.assertEqual(self.client.get('/direct/v1/rides',headers=self.headers()).status_code,503)
        self.provider.fail_status=None;login(self.client,self.provider)
        dump='\n'.join(row[0] for row in self.sql('SELECT sql FROM sqlite_master WHERE type="table"'))
        self.assertNotIn('refresh_token',dump)
        self.assertNotIn('synthetic-not-stored',self.path.read_bytes().decode(errors='ignore'))

    def test_backup_clears_flows_external_sessions_approvals_and_enrollment(self):
        login(self.client,self.provider);self.approve(self.operation());self.client.get('/auth/line/start')
        target=Path(self.directory.name)/'backup.sqlite';backup(self.path,target)
        db=connect(target)
        try:
            for table in ('sessions','client_grants','login_flows','external_sessions','oauth_approvals','external_identities'):
                self.assertEqual(db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0],0,table)
        finally:db.close()

    def test_proxy_origin_duplicate_headers_and_body_limit(self):
        for headers in ({'Origin':'https://evil.invalid'},{'X-Forwarded-Proto':'https'},{'Host':'evil.invalid'}):
            self.assertEqual(self.client.get('/',headers=headers).status_code,403)
        self.assertEqual(self.client.post('/api/session',content=b'x'*16385).status_code,413)
        self.assertEqual(self.client.get('/',headers=[('X-Client-ID','one'),('X-Client-ID','two')]).status_code,400)
        navigation={'Sec-Fetch-Site':'cross-site','Sec-Fetch-Mode':'navigate','Sec-Fetch-Dest':'document'}
        self.assertEqual(self.client.get('/',headers=navigation).status_code,200)
        self.assertEqual(self.client.get('/api/snapshot',headers=navigation).status_code,403)

    def test_mcp_and_a2a_https_protocol_calls_share_owner_checks(self):
        from app.mcp_adapter import PROTOCOL
        headers=self.headers('mcp');headers.update({'MCP-Protocol-Version':PROTOCOL,'Mcp-Method':'tools/list','Accept':'application/json, text/event-stream'})
        meta={'io.modelcontextprotocol/protocolVersion':PROTOCOL,'io.modelcontextprotocol/clientInfo':{'name':'https-test','version':'1'},'io.modelcontextprotocol/clientCapabilities':{}}
        response=self.client.post('/mcp',json={'jsonrpc':'2.0','id':'1','method':'tools/list','params':{'_meta':meta}},headers=headers)
        self.assertEqual(response.status_code,200,response.text);self.assertEqual(len(response.json()['result']['tools']),6)
        card=self.client.get('/.well-known/agent-card.json')
        self.assertEqual(card.status_code,200,card.text)
        self.assertEqual(card.json()['supportedInterfaces'][0]['url'],self.origin+'/a2a')
        response=self.client.post('/a2a',json={'jsonrpc':'2.0','id':'1','method':'ListTasks','params':{}},headers={**self.headers('a2a'),'A2A-Version':'1.0'})
        self.assertEqual(response.status_code,200,response.text);self.assertEqual(response.json()['result']['tasks'],[])

    def test_official_sdks_over_tls_cross_adapter_exactly_once(self):
        import httpx2
        from mcp import Client
        from mcp.client.streamable_http import streamable_http_client
        from a2a.client.client import ClientConfig
        from a2a.client.client_factory import create_client
        from a2a.types import a2a_pb2 as p
        from google.protobuf.json_format import ParseDict, MessageToDict
        from app.agent_tasks import operation_reference
        from scripts.a2a_test_support import send_params
        login(self.client,self.provider);op=self.operation()
        headers={adapter:{**self.headers(adapter),'X-Yoko-Approval':self.approve(op,adapter)} for adapter in ('mcp','a2a','direct')}
        # Generic SDK transports need no private HTTP-header extension.
        del headers['mcp']['X-Yoko-Approval']; del headers['a2a']['X-Yoko-Approval']
        async def check():
            async with httpx2.AsyncClient(verify=self.tls,trust_env=False,headers=headers['mcp']) as hc:
                async with Client(streamable_http_client(self.origin+'/mcp',http_client=hc),cache=None) as client:
                    result=await client.call_tool('yoko_execute_approved_operation',{'operation':op})
                    self.assertTrue(result.structured_content['ok'],result.structured_content)
                    ride=result.structured_content['data']['current']['id']
            async with httpx.AsyncClient(verify=self.tls,trust_env=False,headers=headers['a2a']) as hc:
                client=await create_client(self.origin,ClientConfig(streaming=False,httpx_client=hc))
                events=[event async for event in client.send_message(ParseDict(send_params(operation_reference(op),'https-message-1'),p.SendMessageRequest()))]
                self.assertEqual(events[0].task.status.state,p.TASK_STATE_COMPLETED)
                result=MessageToDict(events[0].task.artifacts[0].parts[0].data)
                self.assertTrue(result['replayed']);self.assertEqual(result['current']['id'],ride)
                listed=await client.list_tasks(p.ListTasksRequest(page_size=5));self.assertEqual(listed.total_size,1)
            return ride
        ride=asyncio.run(check())
        replay=self.direct(op,headers['direct']);self.assertEqual(replay.status_code,200,replay.text)
        self.assertTrue(replay.json()['replayed'])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events WHERE ride_id=?',(ride,)),[(1,)])
        self.assertEqual(self.sql('SELECT COUNT(*) FROM outbox'),[(1,)])

    def test_concurrent_oauth_retries_and_expired_transaction_lease(self):
        login(self.client,self.provider);op=self.operation();headers=self.headers();headers['X-Yoko-Approval']=self.approve(op)
        def send(_):
            with httpx.Client(base_url=self.origin,verify=self.tls,trust_env=False) as client:
                return client.post('/direct/v1/actions/request',json={k:v for k,v in op.items() if k!='kind'},headers=headers)
        with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(send,range(2)))
        self.assertEqual([r.status_code for r in results],[200,200])
        self.assertEqual(sorted(r.json()['replayed'] for r in results),[False,True])
        actor,auth,_=self.app.grants['direct'].resolve(headers['Authorization'],None,headers['X-Yoko-Approval'])
        self.core.clock=lambda: time.time()+16
        with self.assertRaises(DomainError): self.core.mutate(actor,op['operation_id'],op['idempotency_key'],op['kind'],op['payload'],auth)
        self.assertEqual(self.sql('SELECT COUNT(*) FROM events'),[(1,)])

    def test_signed_card_pinned_key_endpoint_provider_and_expiry(self):
        from app.agent_trust import verify_card
        card=self.client.get('/.well-known/agent-card.json').content
        trust={'endpoint':self.origin+'/a2a','authorization_metadata':self.provider.origin+'/.well-known/openid-configuration',
            'key_id':'synthetic-card-key','public_key_file':str(Path(self.directory.name)/'test-card-public.pem'),'expires_at':time.time()+60}
        self.assertEqual(verify_card(card,trust,time.time()).supported_interfaces[0].url,trust['endpoint'])
        for changed in ({'endpoint':'https://evil.invalid/a2a'},{'authorization_metadata':'https://evil.invalid/metadata'}, {'key_id':'untrusted'}, {'expires_at':0}):
            with self.subTest(changed=changed),self.assertRaises(ValueError): verify_card(card,{**trust,**changed},time.time())
        value=json.loads(card);value['name']='tampered'
        with self.assertRaises(ValueError):verify_card(json.dumps(value).encode(),trust,time.time())
        del value['signatures']
        with self.assertRaises(ValueError):verify_card(json.dumps(value).encode(),trust,time.time())

    def test_signed_card_remote_key_reference_is_never_followed(self):
        from app.agent_trust import verify_card
        from jwt.utils import base64url_encode
        value=self.client.get('/.well-known/agent-card.json').json()
        value['signatures'][0]['protected']=base64url_encode(json.dumps({'alg':'RS256','kid':'synthetic-card-key','typ':'JOSE','jku':'https://127.0.0.1/private'}).encode()).decode()
        trust={'endpoint':self.origin+'/a2a','authorization_metadata':self.provider.origin+'/.well-known/openid-configuration',
            'key_id':'synthetic-card-key','public_key_file':str(Path(self.directory.name)/'test-card-public.pem'),'expires_at':time.time()+60}
        calls=len(self.provider.calls)
        with self.assertRaises(ValueError):verify_card(json.dumps(value).encode(),trust,time.time())
        self.assertEqual(len(self.provider.calls),calls)

    def test_schema_seven_migrates_without_touching_foreign_database(self):
        self.sql("UPDATE meta SET value='7' WHERE key='schema_version'")
        initialize(self.path)
        self.assertEqual(self.sql("SELECT value FROM meta WHERE key='schema_version'"),[('8',)])
        other=Path(self.directory.name)/'foreign.db';db=connect(other)
        db.execute('CREATE TABLE unrelated (value TEXT)');db.execute("INSERT INTO unrelated VALUES ('preserve')");db.close()
        with self.assertRaises(RuntimeError): initialize(other)
        db=connect(other)
        try:
            self.assertEqual([r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")],['unrelated'])
            self.assertEqual(db.execute('SELECT value FROM unrelated').fetchone()[0],'preserve')
        finally:db.close()
