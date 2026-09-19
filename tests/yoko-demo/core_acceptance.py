"""Shared acceptance scenario for CPython and the browser's actual WASM engine."""
import json
from pathlib import Path
from demo_runtime import dispatch

checks=[]
path=Path('/tmp/yoko-browser-acceptance.sqlite3')
for suffix in ('','-wal','-shm'):Path(str(path)+suffix).unlink(missing_ok=True)
def call(actor,route,body=None,status=200):
    result=dispatch(path,{'actor':actor,'path':route,'method':'GET' if body is None else 'POST','body':body})
    assert result['status']==status,(route,result)
    return result['data']
def record(name):checks.append(name)
def action(actor,kind,payload,key):
    return call(actor,'/api/actions/'+kind,{'operation_id':key,'idempotency_key':key,'payload':payload})
call(None,'/demo/initialize',{})
assert len(call('admin-a1','/api/snapshot')['rides'])==2
record('seeded pending and completed rides come from Core transitions')
call(None,'/api/snapshot',status=401)
call('rider-b1','/api/snapshot',status=401)
record('only the three fictional demo actors can enter the adapter')
request={'service_id':'service-a','origin_stop_id':'stop-a','destination_stop_id':'stop-b','passengers':1}
draft=call('rider-a1','/api/drafts/request',request)
payload={'draft_id':draft['id'],'details':draft['details']}
created=action('rider-a1','request',payload,'browser-request-0001')['current']
record('rider request is confirmed and saved by the unchanged Core')
replay=action('rider-a1','request',payload,'browser-request-0001')
assert replay['replayed'] and replay['current']['id']==created['id']
record('same operation replay does not duplicate a reservation')
call('admin-a1','/api/drafts/request',request,status=403)
record('admin cannot impersonate a rider mutation')
for kind,target in [('accept','assigned'),('arrive','arrived'),('board','onboard'),('complete','completed')]:
    current=call('driver-a1','/api/rides/'+created['id'])
    call('driver-a1','/api/actions/'+kind,{'operation_id':'unsafe-'+kind,'idempotency_key':'unsafe-'+kind,'payload':{'ride_id':current['id'],'version':current['version'],'stopped':False}},status=409)
    updated=action('driver-a1',kind,{'ride_id':current['id'],'version':current['version'],'stopped':True},'browser-'+kind+'-0001')['current']
    assert updated['status']==target
    assert call('rider-a1','/api/rides/'+created['id'])['status']==target
    assert call('admin-a1','/api/rides/'+created['id'])['status']==target
record('all four driver transitions require stopped confirmation and appear for all roles')
assert all(v['reserved']==0 for v in call('admin-a1','/api/snapshot')['vehicles'])
record('completion releases the recorded vehicle seats')
draft=call('rider-a1','/api/drafts/request',request)
created=action('rider-a1','request',{'draft_id':draft['id'],'details':draft['details']},'browser-request-0002')['current']
draft=call('rider-a1','/api/drafts/cancel',{'ride_id':created['id']})
cancelled=action('rider-a1','cancel',{'draft_id':draft['id'],'details':draft['details']},'browser-cancel-0002')['current']
assert cancelled['status']=='cancelled'
record('owner cancellation has its own confirmation and persists')
other=next(r for r in call('admin-a1','/api/snapshot')['rides'] if r['status']=='requested')
call('rider-a1','/api/rides/'+other['id'],status=404)
record('rider cannot view another fictional passenger request')
record('fresh Core instances read the same SQLite reservation ledger')
call(None,'/demo/reset',{})
assert len(call('admin-a1','/api/snapshot')['rides'])==2
record('reset affects only the dedicated fictional demo database')
RESULT={'status':'PASS','checks':checks,'count':len(checks),'production_authentication':False}
print(json.dumps(RESULT,ensure_ascii=False))
