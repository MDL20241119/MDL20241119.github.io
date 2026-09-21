"""Synthetic observation ledger shared by Web, direct and standard adapters.

Admin approval authorizes each import; this is not a GPS collector. A complete
delay snapshot is distinct from missing data. Expiry never resolves an incident.
"""
import json
from urllib.parse import parse_qs
from .core import ACTIVE, exact, fail, iso, packed
from .catalog import text, timestamp
from .transport_data import geojson_point_to_gtfs

COMMANDS={'observation_configure','observation_publish'}
REASONS=('traffic','operational','accident','weather','vehicle_issue','passenger_issue','other')
CLOSED=('vehicle_moved','resolved','schedule_changed','cancelled')
QUALITY=('fresh','not_configured','not_acquired','stale','expired','stopped','source_changed','not_operating')

def query_params(query,kind):
    allowed={'vehicle_ids','service_ids','offset','limit'}
    if kind=='delays':allowed|={'status','started_at_from','started_at_to'}
    try:
        raw=parse_qs(query,keep_blank_values=True,strict_parsing=True,max_num_fields=7)
        if set(raw)-allowed or any(len(v)!=1 or not v[0] for v in raw.values()):raise ValueError()
        result={k:(int(v[0]) if k in ('offset','limit') else v[0].split(',') if k in ('vehicle_ids','service_ids','status') else v[0]) for k,v in raw.items()}
    except ValueError:fail('INVALID_QUERY','検索条件を確認してください')
    return result

class Observations:
    def __init__(self,core):self.core=core

    def vehicle(self,db,actor,vehicle_id,admin=False):
        text(vehicle_id,100)
        if admin and actor['role']!='admin':fail('FORBIDDEN','管理者の確認が必要です',403)
        row=db.execute('SELECT v.*,s.active AS service_active,s.revision AS service_revision FROM vehicles v JOIN services s ON s.id=v.service_id WHERE v.id=? AND v.tenant_id=?',(vehicle_id,actor['tenant_id'])).fetchone()
        if not row:fail('FORBIDDEN','車両を参照する権限がありません',403)
        if actor['role']=='driver' and row['driver_id']!=actor['id']:fail('FORBIDDEN','担当車両だけを参照できます',403)
        if actor['role']=='rider' and not db.execute("SELECT 1 FROM rides r JOIN runs u ON u.id=r.run_id WHERE r.rider_id=? AND r.vehicle_id=? AND r.status IN ('assigned','arrived','onboard') AND u.active=1",(actor['id'],vehicle_id)).fetchone():
            fail('FORBIDDEN','現在割り当てられた車両だけを参照できます',403)
        return row

    def source(self,db,vehicle_id):
        row=db.execute('SELECT * FROM observation_sources WHERE vehicle_id=?',(vehicle_id,)).fetchone()
        return ({**json.loads(row['data_json']),'version':row['version']} if row else None)

    def prepare(self,db,actor,kind,data):
        if not isinstance(data,dict):fail('INVALID_INPUT','入力オブジェクトが必要です')
        fields=['vehicle_id','source_id','label','location_ttl_seconds','delay_ttl_seconds','enabled','basis'] if kind=='observation_configure' else ['vehicle_id','run_id','source_id','observed_at','location','delays']
        exact(data,fields)
        vehicle=self.vehicle(db,actor,data['vehicle_id'],True)
        text(data['source_id'],100)
        source=self.source(db,vehicle['id'])
        version=source['version'] if source else 0
        dependencies=[{'service_id':vehicle['service_id'],'service_revision':vehicle['service_revision'],'driver_id':vehicle['driver_id'],'active':vehicle['active'],'service_active':vehicle['service_active']}]
        if kind=='observation_configure':
            text(data['label'],100)
            if data['basis']!='synthetic_test_only' or type(data['enabled']) is not bool:fail('SYNTHETIC_ONLY','架空試験用の取得元設定だけを扱います')
            for key,maximum in [('location_ttl_seconds',300),('delay_ttl_seconds',3600)]:
                if type(data[key]) is not int or not 1<=data[key]<=maximum:fail('INVALID_FRESHNESS','試験用の鮮度上限が不正です')
        else:
            if not source:fail('SOURCE_NOT_CONFIGURED','取得元を先に設定してください',409)
            if not source['enabled'] or not vehicle['active'] or not vehicle['service_active']:fail('OBSERVATION_STOPPED','取得元・車両・サービスが停止しています',409)
            if source['source_id']!=data['source_id']:fail('SOURCE_MISMATCH','許可された取得元と一致しません',403)
            text(data['run_id'],100)
            run=db.execute('SELECT * FROM runs WHERE vehicle_id=? AND active=1',(vehicle['id'],)).fetchone()
            if not run or run['id']!=data['run_id']:fail('RUN_MISMATCH','現在の担当便と一致しません',409)
            observed=timestamp(data['observed_at'])
            if observed>timestamp(iso(self.core.clock())):fail('FUTURE_OBSERVATION','未来の日時を観測日時にはできません')
            old=db.execute('SELECT * FROM observation_snapshots WHERE vehicle_id=?',(vehicle['id'],)).fetchone()
            if old and observed<=old['observed_at']:fail('OUT_OF_ORDER_OBSERVATION','新しい観測を古い情報や同時刻の別送信で上書きできません',409)
            dependencies += [{'source_version':version,'run_id':run['id']}]
            version=old['version'] if old else 0
            if data['location'] is not None:
                exact(data['location'],['type','coordinates']);geojson_point_to_gtfs(data['location'])
            if data['delays'] is not None:
                if not isinstance(data['delays'],list) or len(data['delays'])>20:fail('INVALID_DELAYS','遅延情報は20件以内の完全な一覧、または未取得を示すnullで指定してください')
                seen=set()
                for item in data['delays']:
                    exact(item,['id','status','delay_minutes','delay_reason','started_at','closed_at','closed_reason','effective_end'])
                    text(item['id'],100)
                    if item['id'] in seen:fail('INVALID_DELAYS','同じ遅延IDを重複できません')
                    seen.add(item['id'])
                    if item['status'] not in ('active','resolved') or item['delay_reason'] not in REASONS:fail('INVALID_DELAYS','状態・理由の指定が不正です')
                    if item['delay_minutes'] is not None and (type(item['delay_minutes']) is not int or not 0<=item['delay_minutes']<=2147483647):fail('INVALID_DELAY_MINUTES','遅延分数は0以上の整数または不明を示すnullです')
                    start,end=timestamp(item['started_at']),timestamp(item['effective_end'])
                    if start>observed or end<=observed:fail('INVALID_OBSERVATION_PERIOD','開始は観測以前、有効期限は観測より後にしてください')
                    if item['status']=='active':
                        if item['closed_at'] is not None or item['closed_reason'] is not None:fail('INVALID_DELAYS','進行中の遅延に解消情報を設定できません')
                    elif item['closed_reason'] not in CLOSED or not start<=timestamp(item['closed_at'])<=observed:
                        fail('INVALID_DELAYS','解消済みの遅延は確認した解消日時と理由が必要です')
                    previous=db.execute('SELECT * FROM observation_delays WHERE id=?',(item['id'],)).fetchone()
                    if previous:
                        p=json.loads(previous['data_json'])
                        if previous['vehicle_id']!=vehicle['id'] or previous['run_id']!=run['id']:fail('DELAY_ID_CONFLICT','この遅延IDは別の車両・便に使用されています',409)
                        if timestamp(p['started_at'])!=start or (p['status']=='resolved' and item!=p):fail('DELAY_STATE_CONFLICT','開始日時や確定した解消記録は変更できません',409)
                active={r['id'] for r in db.execute("SELECT id FROM observation_delays WHERE vehicle_id=? AND run_id=? AND json_extract(data_json,'$.status')='active'",(vehicle['id'],run['id']))}
                if not active<=seen:fail('UNRESOLVED_DELAY_OMITTED','未解消の遅延を一覧から消せません。解消を確認して記録してください',409)
        return {'input':data,'version':version,'dependencies':dependencies}

    def apply(self,db,actor,kind,details):
        data=details['input'];vehicle_id=data['vehicle_id'];now=iso(self.core.clock())
        if kind=='observation_configure':
            db.execute('INSERT INTO observation_sources VALUES (?,?,?) ON CONFLICT(vehicle_id) DO UPDATE SET data_json=excluded.data_json,version=excluded.version',(vehicle_id,packed(data),details['version']+1))
            resource='observation_source'
        else:
            source=self.source(db,vehicle_id);observed=timestamp(data['observed_at'])
            db.execute('INSERT INTO observation_snapshots VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(vehicle_id) DO UPDATE SET run_id=excluded.run_id,source_version=excluded.source_version,observed_at=excluded.observed_at,data_json=excluded.data_json,version=excluded.version,recorded_at=excluded.recorded_at',
                (vehicle_id,data['run_id'],source['version'],observed,packed(data),details['version']+1,now,actor['tenant_id']))
            for item in data['delays'] or []:
                db.execute('INSERT INTO observation_delays VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET data_json=excluded.data_json,source_version=excluded.source_version,observed_at=excluded.observed_at,updated_at=excluded.updated_at',
                    (item['id'],vehicle_id,data['run_id'],packed(item),source['version'],observed,now,now,actor['tenant_id']))
            resource='observation'
        return self.resource(db,actor,vehicle_id,resource)

    def resource(self,db,actor,vehicle_id,kind):
        vehicle=self.vehicle(db,actor,vehicle_id,True)
        value=self.source(db,vehicle_id) if kind=='observation_source' else self.view(db,vehicle)
        return {'resource_type':kind,'id':vehicle_id,'value':value,'deleted':value is None}

    def view(self,db,vehicle):
        source=self.source(db,vehicle['id']);now=timestamp(iso(self.core.clock()))
        run=db.execute('SELECT id FROM runs WHERE vehicle_id=? AND active=1',(vehicle['id'],)).fetchone()
        row=db.execute('SELECT * FROM observation_snapshots WHERE vehicle_id=?',(vehicle['id'],)).fetchone()
        base='fresh'
        if not source:base='not_configured'
        elif not source['enabled'] or not vehicle['active'] or not vehicle['service_active']:base='stopped'
        elif not run:base='not_operating'
        elif not row or row['run_id']!=run['id']:base='not_acquired'
        elif row['source_version']!=source['version']:base='source_changed'
        elif row['observed_at']>now:base='not_acquired'
        matched=bool(row and run and row['run_id']==run['id'] and source and row['source_version']==source['version'])
        data=json.loads(row['data_json']) if matched else None
        result={'vehicle_id':vehicle['id'],'service_id':vehicle['service_id'],'run_id':run['id'] if run else None,
            'source':source,'observed_at':iso(row['observed_at']) if matched else None,'recorded_at':row['recorded_at'] if matched else None,
            'version':row['version'] if row else 0,'location_status':base,'delay_status':base,'location':None,'delays':[],
            'location_valid_until':None,'delay_valid_until':None,'delay_assessment':'unknown','basis':'synthetic_test_only'}
        if base!='fresh':return result
        for kind,field in [('location','location'),('delay','delays')]:
            end=row['observed_at']+source[kind+'_ttl_seconds'];result[kind+'_valid_until']=iso(end)
            result[kind+'_status']='not_acquired' if data[field] is None else 'stale' if now>=end else 'fresh'
        if result['location_status']=='fresh':result['location']=data['location']
        if result['delay_status']=='fresh':
            reports=list(db.execute('SELECT * FROM observation_delays WHERE vehicle_id=? AND run_id=? ORDER BY id',(vehicle['id'],run['id'])))
            for report in reports:
                item=json.loads(report['data_json'])
                end=min(timestamp(item['effective_end']),report['observed_at']+source['delay_ttl_seconds'])
                if item['status']=='active' and (now>=end or report['source_version']!=source['version']):
                    result['delay_status']='expired';break
                if now<end and report['source_version']==source['version']:
                    value={k:v for k,v in item.items() if v is not None}
                    value.update({'vehicle_id':vehicle['id'],'service_id':vehicle['service_id'],'created_at':report['created_at'],'updated_at':report['updated_at']})
                    result['delays'].append(value)
                    if item['status']=='active':result['delay_valid_until']=iso(min(timestamp(result['delay_valid_until']),end))
            if result['delay_status']!='fresh':result['delays']=[]
            else:result['delay_assessment']='delayed' if any(r['status']=='active' for r in result['delays']) else 'no_active_delay_reported'
        return result

    def for_ride(self,db,actor,ride):
        if ride['status'] not in ACTIVE or not ride['vehicle_id']:return None
        vehicle=self.vehicle(db,actor,ride['vehicle_id'])
        view=self.view(db,vehicle)
        return view if view['run_id']==ride['run_id'] else None

    def read(self,actor_id,kind,params=None,authorization=None,standard=False):
        params=params or {};offset=params.get('offset',0);limit=params.get('limit',20)
        if kind not in ('locations','delays'):fail('INVALID_QUERY','未対応の観測種類です')
        allowed={'vehicle_ids','service_ids','offset','limit'}|({'status','started_at_from','started_at_to'} if kind=='delays' else set())
        if set(params)-allowed or type(offset) is not int or offset<0 or type(limit) is not int or not 1<=limit<=100:fail('INVALID_QUERY','ページ・検索項目を確認してください')
        for key in ('vehicle_ids','service_ids','status'):
            if key in params:
                values=params[key]
                if not isinstance(values,list) or not 1<=len(values)<=100 or any(not isinstance(v,str) or not v or len(v)>100 for v in values):fail('INVALID_QUERY','絞り込み条件が不正です')
        statuses=params.get('status',['active']);start=end=None
        if kind=='delays':
            if not set(statuses)<={'active','resolved'}:fail('INVALID_QUERY','遅延状態が不正です')
            if 'started_at_to' in params and 'started_at_from' not in params:fail('INVALID_QUERY','終了日時には開始日時も必要です')
            start=timestamp(params['started_at_from']) if 'started_at_from' in params else self.core.clock()-86400
            end=timestamp(params['started_at_to']) if 'started_at_to' in params else self.core.clock()
            if start>end:fail('INVALID_QUERY','開始日時が終了日時より後です')
        with self.core.db() as db:
            actor=self.core.actor(db,actor_id);self.core.check_authorization(db,actor_id,authorization)
            # Explicit identifiers must be authorized even when another filter matches nothing.
            for vehicle_id in params.get('vehicle_ids',[]):self.vehicle(db,actor,vehicle_id)
            for service_id in params.get('service_ids',[]):
                if not db.execute('SELECT 1 FROM services WHERE id=? AND tenant_id=?',(service_id,actor['tenant_id'])).fetchone():fail('FORBIDDEN','サービスを参照する権限がありません',403)
            rows=db.execute('SELECT v.*,s.active AS service_active FROM vehicles v JOIN services s ON s.id=v.service_id WHERE v.tenant_id=? ORDER BY v.id',(actor['tenant_id'],))
            views=[]
            for vehicle in rows:
                if actor['role']=='driver' and vehicle['driver_id']!=actor['id']:continue
                if actor['role']=='rider' and not db.execute("SELECT 1 FROM rides r JOIN runs u ON u.id=r.run_id WHERE r.rider_id=? AND r.vehicle_id=? AND r.status IN ('assigned','arrived','onboard') AND u.active=1",(actor_id,vehicle['id'])).fetchone():continue
                if 'vehicle_ids' in params and vehicle['id'] not in params['vehicle_ids']:continue
                if 'service_ids' in params and vehicle['service_id'] not in params['service_ids']:continue
                views.append(self.view(db,vehicle))
            status_key='location_status' if kind=='locations' else 'delay_status'
            prefix='VEHICLE' if kind=='locations' else 'DELAY'
            if standard and (not views or any(v[status_key]!='fresh' for v in views)):
                fail(prefix+'_OBSERVATIONS_NOT_ACQUIRED','対象の全車両について有効な観測を確認できません。MDL APIで取得状態を確認してください',503)
            items=[]
            for view in views:
                if view[status_key]!='fresh':continue
                if kind=='locations':items.append({'vehicle_id':view['vehicle_id'],'service_id':view['service_id'],'location':view['location'],'timestamp':view['observed_at']})
                else:items.extend(d for d in view['delays'] if d['status'] in statuses and start<=timestamp(d['started_at'])<=end)
            items.sort(key=lambda x:(x['vehicle_id'],x.get('id','')))
            key='vehicle_locations' if kind=='locations' else 'operation_delays'
            result={key:items[offset:offset+limit],'total':len(items),'offset':offset,'limit':limit}
            if not standard:result.update({'observations':[{k:v for k,v in view.items() if k not in ('location','delays')} for view in views],'as_of':iso(self.core.clock()),'basis':'synthetic_test_only','availability':'no_authorized_vehicles' if not views else 'complete' if all(v[status_key]=='fresh' for v in views) else 'incomplete'})
            return result
