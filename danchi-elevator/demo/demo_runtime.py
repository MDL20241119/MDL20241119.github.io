"""Browser demo adapter. No network, authentication service or production data.

The unmodified Mobility Core owns all reservation rules and SQLite writes.
The three actor IDs below are deliberately public, fictional demo identities.
"""
import json
import base64
import hashlib
import zlib
from pathlib import Path
from app.core import Core, DomainError, fail, exact
from app.db import connect

ACTORS = {'rider-a1', 'driver-a1', 'admin-a1'}
DRAFTS = {'request', 'change', 'cancel', 'book', 'profile_create', 'profile_update',
          'profile_delete', 'agreements_register', 'payment_update', 'offer_open', 'offer_close'}
ACTIONS = DRAFTS | {'accept', 'arrive', 'board', 'complete'}


def prepare_database(path):
    path = Path(path)
    if path.exists():
        db = connect(path)
        try:
            meta = dict(db.execute('SELECT key,value FROM meta'))
            if meta.get('data_mode') != 'synthetic' or meta.get('schema_version') != '8':
                raise RuntimeError('Unexpected demo database schema')
        finally:
            db.close()
        return
    seed=json.loads((Path(__file__).parent/'fixtures/browser-seed.json').read_text())
    raw=zlib.decompress(base64.b64decode(seed['data']))
    if hashlib.sha256(raw).hexdigest()!=seed['sha256']:raise RuntimeError('Demo seed integrity mismatch')
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    # One pending request and one completed ride make all three entry screens
    # understandable. Seeding follows exactly the ordinary Core transitions.
    core = Core(path)
    def request(actor, origin, destination, passengers, key):
        draft = core.prepare(actor, 'request', {'service_id':'service-a',
            'origin_stop_id':origin, 'destination_stop_id':destination, 'passengers':passengers})
        return core.mutate(actor,key,key,'request',{'draft_id':draft['id'],'details':draft['details']})['current']
    ride=request('rider-a1','stop-c','stop-a',1,'demo-history-request')
    for kind in ('accept','arrive','board','complete'):
        key='demo-history-'+kind
        ride=core.mutate('driver-a2',key,key,kind,{'ride_id':ride['id'],'version':ride['version'],'stopped':True})['current']
    request('rider-a2','stop-a','stop-b',2,'demo-pending-request')


def dispatch(path, command):
    try:
        route=command['path'];body=command.get('body');method=command.get('method','GET');actor=command.get('actor')
        if route=='/demo/initialize' and method=='POST':
            prepare_database(path)
            return {'status':200,'data':{'ready':True}}
        if route=='/demo/reset' and method=='POST':
            for suffix in ('','-wal','-shm'):
                Path(str(path)+suffix).unlink(missing_ok=True)
            prepare_database(path)
            return {'status':200,'data':{'reset':True}}
        if actor not in ACTORS: fail('UNAUTHENTICATED','体験する役割を選んでください',401)
        core=Core(path)
        with core.db() as db:
            person=dict(core.actor(db,actor))
        if route=='/api/me' and method=='GET':
            value={'user':{k:person[k] for k in ('id','role','tenant_id')},'csrf':'browser-demo-only','mode':'browser_demo'}
        elif route=='/api/snapshot' and method=='GET':value=core.snapshot(actor)
        elif route=='/api/catalog' and method=='GET':value=core.catalog.snapshot(actor)
        elif route=='/api/candidates' and method=='POST':value=core.booking.search(actor,body)
        elif route.startswith('/api/rides/') and method=='GET':value=core.get_ride(actor,route.rsplit('/',1)[1])
        elif route.startswith('/api/operations/') and method=='GET':value=core.operation(actor,route.rsplit('/',1)[1])
        elif route.startswith('/api/payments/') and method=='GET':value=core.payments.read(actor,route.rsplit('/',1)[1])
        elif route.startswith('/api/drafts/') and method=='POST' and route.rsplit('/',1)[1] in DRAFTS:
            value=core.prepare(actor,route.rsplit('/',1)[1],body)
        elif route.startswith('/api/actions/') and method=='POST' and route.rsplit('/',1)[1] in ACTIONS:
            exact(body,['operation_id','idempotency_key','payload'])
            value=core.mutate(actor,body['operation_id'],body['idempotency_key'],route.rsplit('/',1)[1],body['payload'])
        else:fail('NOT_FOUND','このデモでは利用できません',404)
        return {'status':200,'data':value}
    except DomainError as error:
        return {'status':error.status,'data':{'error':{'code':error.code,'message':error.message}}}


def dispatch_json(path, raw):
    return json.dumps(dispatch(path,json.loads(raw)),ensure_ascii=False,allow_nan=False)
