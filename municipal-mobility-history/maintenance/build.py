#!/usr/bin/env python3
"""Reproducible additive projection. Inputs stay outside the public checkout."""
import argparse, collections, hashlib, json, pathlib, re, zipfile
from public_verification import public_audit, public_evidence

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / 'municipal-mobility-history'
DATA = OUT / 'data'

def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n')

def text(value):
    if value is None: return ''
    if isinstance(value, str): return value
    if isinstance(value, list): return ' / '.join(text(v) for v in value)
    if isinstance(value, dict): return ' / '.join(text(v) for k,v in value.items() if k not in ['sources','source_ids','source_refs','raw'])
    return str(value)

PRIVATE_KEYS = {'authorized_by', 'worker', 'worker_id', 'queue_index', 'local_path', 'workspace_path', 'download_url'}
def public(v):
    if isinstance(v, dict): return {k:public(x) for k,x in v.items() if k not in PRIVATE_KEYS}
    if isinstance(v, list): return [public(x) for x in v]
    if isinstance(v, str):
        v = re.sub(r'https?://(?:drive|docs)\.google\.com/[^\s"<>]+', '[制作入力への非公開参照]', v)
        v = re.sub(r'(?:/workspace/|/root/)[^\s"<>]+', '[制作時の保存先]', v)
    return v

THEMES = [('自動運転',r'自動運転|レベル[234４]|L[234]'), ('オンデマンド',r'デマンド|のるーと|チョイソコ|乗合タクシー|いねタク'), ('MaaS',r'MaaS|マース'), ('グリスロ・EV',r'グリスロ|グリーンスロー|低速|電動|\bEV\b'), ('物流・配送',r'物流|配送|ドローン|貨客'), ('医療・福祉',r'医療|病院|通院|福祉|患者|介助'), ('観光',r'観光|ツーリズム|試乗|空港'), ('共同運行・担い手',r'共同|共創|運転士|人材|担い手|助け合い'), ('データ・通信',r'通信|データ|API|5G|配車')]
def themes(s): return [k for k,p in THEMES if re.search(p,s,re.I)] or ['地域交通']
def years(s): return sorted(set(re.findall(r'(?<!\d)(?:19|20)\d{2}(?!\d)',s)))
def actual_event(ev):
    s = ' '.join(str(ev.get(k) or '') for k in ['date_label','event_text','status_as_recorded'])
    return not re.search(r'予定|目標|計画|調整中|検討中|future|planned',s,re.I)
def latest(events):
    es = [x for x in events if actual_event(x) and re.match(r'(?:19|20)\d{2}',x.get('date_label',''))]
    return max(es, key=lambda x:x.get('sort_key',x['date_label'])) if es else None

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--inputs',type=pathlib.Path,required=True);args=ap.parse_args()
    inp=args.inputs.resolve();oldpath=inp/'mobility_history_data.json';expath=next(inp.glob('*統合拡張*.json'));npath=next(inp.glob('*追加データ*.json'))
    old=json.loads(oldpath.read_text());ext=json.loads(expath.read_text());new=json.loads(npath.read_text())
    manifest=json.loads((inp/'manifest.json').read_text())
    for f in manifest:
        b=(inp/f['name']).read_bytes();assert len(b)==f['expected_bytes'];assert hashlib.sha256(b).hexdigest()==f['sha256']
    with zipfile.ZipFile(next(inp.glob('*統合拡張*.zip'))) as z:
        member=next(x for x in z.namelist() if x.endswith('.json'));assert z.read(member)==expath.read_bytes()
    assert len(old['programs'])==66 and len(old['cases'])==111
    assert sum(len(c['events']) for c in old['cases'])+len(old['policy_events'])==467
    assert len(ext['expansion']['records'])==2120 and len(ext['expansion']['reference_records'])==497
    assert len(new['cases'])==72 and len(new['events'])==313 and len(new['official_document_reviews'])==343
    masters={x['municipality_code']:x for x in ext['municipality_index']['official_master']}
    claims={x['claim_id']:x for x in new['claims']};sources={x['source_id']:x for x in new['sources']}
    newevents={x['event_id']:x for x in new['events']}
    reviews_by_selection={rid:rv for rv in new['official_document_reviews'] for rid in rv['selection_record_ids']}
    overlays={x['target_selection_record_id']:x for x in new['legacy_classification_overlay']}
    review_events=collections.defaultdict(list)
    for ev in new['official_result_events']: review_events[ev['review_id']].append(ev)
    baseline_by_id={x['id']:x for x in old['cases']}
    verified_links=collections.defaultdict(list)
    for x in ext['municipality_index']['baseline_links']:
        if x.get('case_locality_evidence_status')=='primary_project_locality_confirmed':verified_links[x['case_id']].append(x['municipality_code'])

    index=[];ids_by_layer={};detail_locs={};provenance=[]
    def add(layer, detail, row):
        rid=row['id'];row.update(layer=layer,detail=f'data/details/{layer}/{len(ids_by_layer.get(layer,[]))//25:03d}.json')
        ids_by_layer.setdefault(layer,[]).append(rid);index.append(row);detail_locs[rid]=row['detail']
        detail['provenance']={'source_file':detail.pop('_file'), 'source_pointer':detail.pop('_pointer'), 'original_id':rid}
        provenance.append({'layer':layer,'id':rid,**detail['provenance'],'display_file':row['detail']})
        return detail
    layers=collections.defaultdict(list)
    for c in new['cases']:
        cid=c['case_id'];cs=[x for x in new['claims'] if x['case_id']==cid];evs=[newevents[i] for i in c['event_ids']]
        assert {x['claim_id'] for x in cs} == {c['call_claim_id'],c['selection_claim_id'],c['lesson_claim_id'],*c['result_claim_ids']}
        raw=c['raw'];rs=raw['results'];summary=raw.get('summary',{});le=latest(evs)
        current=rs.get('current_status') or rs.get('latest_verified_state') or summary.get('current_status') or (le or {}).get('event_text','後続未確認')
        if not isinstance(current,str):current=text(current)
        # A tag describes the last documented fact, never real-time operation.
        state='unknown';sl='後続未確認'
        if cid in ['west-40229-06','west-43100-10','west-44211-15']:state='service_end';sl='サービス終了を確認'
        elif cid in ['central_tottori_torimobi','west-47375-20']:state='pause';sl='休止・停止を確認'
        elif cid in ['central_toyono_ai','central_hikari_ai','central_wakayama_auto']:state='review';sl='導入見送り・再検討'
        elif cid in ['NORTH-R-03','NORTH-R-11','NORTH-R-14','EAST-R-03','EAST-R-07','EAST-R-17','EAST-R-18','central_ine_ev','central_izumo_sada','central_sanda_gsm','central_fukuyama_tomo','west-37207-02','west-42214-08','west-43100-11','west-43348-12','west-44201-13','west-44211-14']:state='operation';sl='運行・提供の記録あり'
        elif cid in ['NORTH-R-02','NORTH-R-05','NORTH-R-06','NORTH-R-10','EAST-R-01','EAST-R-02','EAST-R-05','EAST-R-08','EAST-R-12','EAST-R-13','EAST-R-14','EAST-R-15','central_kobe_nada','central_niimi_koigakubo','west-36201-01']:state='trial_end';sl='実証・対象期間終了'
        else:state='result';sl='結果・検証の記録あり'
        cids=[x['source_id'] for x in cs for x in x['source_refs']]
        sid=list(dict.fromkeys(c['source_ids']+cids));assert all(s in sources for s in sid)
        matched=masters.get(c['municipality_code']);assert matched and matched['prefecture_name']==c['prefecture']
        assert matched['municipality_name'] in c['municipality']
        headline=next((x['statement'] for x in cs if x['label'] in ['利用実績','結果観測']),next((x['statement'] for x in cs if x['section']=='result'),''))
        row={'id':cid,'title':c['title'],'prefectures':[c['prefecture']],'municipality':c['municipality'],'codes':[c['municipality_code']],'years':years(text(evs)+text(rs.get('period',rs.get('implementation_period','')))), 'themes':themes(c['title']+' '+str(raw.get('mobility_type',''))),'state':state,'state_label':sl,'evidence':'deep_result','evidence_label':'結果・変遷を詳査','excerpt':headline[:260], 'last_event_date':(le or {}).get('date_label','日付未取得'),'program_ids':[]}
        detail={**c,'claims':cs,'events':evs,'sources':[sources[s] for s in sid], 'current_observation':current,'last_documented_event':le,'state':state,'state_label':sl,'current_status_checked_at':rs.get('status_checked_at',None),'related_baseline':[x for x in new['baseline_reference_links'] if x['case_id']==cid], 'corrections':[{k:v for k,v in x.items() if k!='authorized_by'} for x in new['evidence_corrections'] if x['case_id']==cid], '_file':npath.name,'_pointer':'/cases/'+str(new['cases'].index(c))}
        layers['deep'].append(add('deep',detail,row))

    progmap={x['program_id']:x for x in ext['expansion']['programs']}
    def region_parts(region):
        # Only explicit prefectures are searchable; no inferred map placement.
        prefs=list(dict.fromkeys(re.findall(r'北海道|東京都|大阪府|京都府|.{2,3}県',region)))
        prefs=[p for p in prefs if p in {m['prefecture_name'] for m in masters.values()}]
        return prefs
    for layer,key in [('selection','records'),('reference','reference_records')]:
        for i,r in enumerate(ext['expansion'][key]):
            rv=reviews_by_selection.get(r['record_id']);overlay=overlays.get(r['record_id']);evkind=rv['result_evidence_kind'] if rv else 'not_reviewed'
            labels={'outcome_result':'実績結果','study_result':'調査成果','interim_result':'中間結果','partial_implementation_result':'部分実施のみ','termination_only':'終了のみ','outcome_not_obtained':'結果未取得','not_reviewed':'資料未点検'}
            bp=r.get('baseline_program_ids',[]) or progmap.get(r['program_id'],{}).get('baseline_program_ids',[])
            raw=r.get('raw',{});training=r['program_id']=='mlit_mobility_talent'
            resolved_ids=([rv.get('source_id'),rv.get('summary_evidence_source_id')]+[ev.get('source_id') for ev in review_events.get(rv['review_id'],[])]) if rv else []
            detail={**r,'review':rv,'classification_correction':overlay,'review_events':review_events.get(rv['review_id'],[]) if rv else [],'resolved_sources':[sources[s] for s in dict.fromkeys(resolved_ids) if s in sources], '_file':expath.name,'_pointer':f'/expansion/{key}/{i}'}
            row={'id':r['record_id'],'title':r['project_name'],'region':r.get('region',''),'prefectures':region_parts(r.get('region','')),'codes':[],'municipality':'','years':[str(r['fiscal_year'])] if r.get('fiscal_year') else years(str(r.get('announcement_date',''))),'themes':themes(r['program_name']+' '+r['project_name']),'state':('training' if training else 'selection') if layer=='selection' else (r.get('status_raw') or r['status']),'state_label':'人材支援の原票' if training else ('採択・支援の原票' if layer=='selection' else r['status']),'evidence':evkind,'evidence_label':labels[evkind],'excerpt':rv['summary'][:260] if rv and rv.get('summary') else (r.get('operator') or r.get('notes',''))[:260],'program_ids':list(dict.fromkeys([r['program_id'],*bp])),'training':training}
            layers[layer].append(add(layer,detail,row))

    for i,rv in enumerate(new['official_document_reviews']):
        resolved_ids=[rv.get('source_id'),rv.get('summary_evidence_source_id')]+[ev.get('source_id') for ev in review_events[rv['review_id']]]
        detail={**rv,'events':review_events[rv['review_id']],'resolved_sources':[sources[s] for s in dict.fromkeys(resolved_ids) if s in sources],'classification_correction':overlays.get(rv['selection_record_ids'][0]),'_file':npath.name,'_pointer':f'/official_document_reviews/{i}'}
        target=next(x for x in index if x['id']==rv['selection_record_ids'][0] and x['layer']=='selection')
        row={k:v for k,v in target.items() if k not in ['id','layer','detail']};row.update(id=rv['review_id'],title=rv['project_name'])
        layers['review'].append(add('review',detail,row))

    for i,r in enumerate(ext['municipality_index']['municipality_records']):
        codes=[m['municipality_code'] for m in masters.values() if m['prefecture_name']==r['prefecture'] and m['municipality_name']==r['municipality']]
        row={'id':r['record_id'],'title':r['project_name'],'prefectures':[r['prefecture']],'codes':codes,'municipality':r['municipality'],'years':years(r.get('event_date','')),'themes':themes(r['project_name']),'state':r['status'],'state_label':r['status'],'evidence':'local_history','evidence_label':'自治体公式履歴','excerpt':r['description'],'program_ids':[]}
        layers['local'].append(add('local',{**r,'_file':expath.name,'_pointer':f'/municipality_index/municipality_records/{i}'},row))

    for i,c in enumerate(old['cases']):
        codes=verified_links[c['id']];prefs=list(dict.fromkeys(masters[z]['prefecture_name'] for z in codes))
        row={'id':c['id'],'title':c['name'],'region':c.get('region',''),'prefectures':prefs,'codes':codes,'municipality':'・'.join(masters[z]['municipality_name'] for z in codes),'years':years(text(c['events'])),'themes':themes(c['name']+' '+c.get('intervention','')),'state':c.get('status') or 'unknown','state_label':c.get('status',''),'evidence':'baseline','evidence_label':'旧調査の代表事例','excerpt':text(c.get('outcomes',''))[:260],'program_ids':c.get('program_ids',c.get('program',[]))}
        layers['legacy'].append(add('legacy',{**c,'_file':oldpath.name,'_pointer':f'/cases/{i}'},row))

    for i,r in enumerate(ext['municipality_index']['history']):
        rid=r.get('history_id') or r.get('event_id') or r.get('record_id') or f'HISTORY-{i:04d}'
        row={'id':rid,'title':r.get('project_name') or r.get('event') or r.get('name') or '年度別参照索引','prefectures':region_parts(str(r.get('region',''))),'codes':[],'municipality':'','years':years(text(r.get('fiscal_year',r.get('event_date','')))),'themes':[],'state':'reference','state_label':'年度履歴の索引行','evidence':'index','evidence_label':'索引（事業件数に加算しない）','excerpt':text(r)[:240],'program_ids':[r['program_id']] if r.get('program_id') else []}
        layers['history'].append(add('history',{**r,'_file':expath.name,'_pointer':f'/municipality_index/history/{i}'},row))

    # Write small indexes separately. Deep 72 loads initially; 2,120 records load on demand.
    for layer,details in layers.items():
        for start in range(0,len(details),25):dump(DATA/'details'/layer/f'{start//25:03d}.json',public({x['provenance']['original_id']:x for x in details[start:start+25]}))
        dump(DATA/f'index-{layer}.json',public([x for x in index if x['layer']==layer]))
    munis=[]
    for m in ext['municipality_index']['research_queue']:
        record={k:m[k] for k in ['municipality_code','prefecture_code','prefecture_name','municipality_name','research_depth']}
        case_ids=[c['case_id'] for c in new['cases'] if c['municipality_code']==m['municipality_code']]
        record['original_research_depth']=record['research_depth'];record['deep_case_ids']=case_ids
        if case_ids:record['research_depth']='結果詳査あり（全年度調査未完）'
        munis.append(record)
    dump(DATA/'municipalities.json',munis)
    dump(DATA/'programs.json',public(ext['expansion']['programs']))
    dump(DATA/'coverage.json',public(ext['expansion']['coverage']))
    # Full supporting objects are retained in lazy, separately named projections.
    for k in ['regions','baseline_links','candidate_links','official_master','research_queue']:
        dump(DATA/f'support-{k}.json',public(ext['municipality_index'][k]))
    dump(DATA/'crosswalk.json',public(ext['expansion']['crosswalk']))
    dump(DATA/'sources.json',public({'baseline':old['sources'],'expansion':ext['expansion']['sources'],'addendum':new['sources']}))
    dump(DATA/'classification-corrections.json',public(new['legacy_classification_overlay']))
    dump(DATA/'corrections.json',public(new['evidence_corrections']))
    dump(DATA/'research-gaps.json',public({'old':old['gaps'],'expansion':ext['expansion']['gaps'],'addendum':new['gaps']}))
    dump(DATA/'timeline-index.json',public([{k:v for k,v in ev.items() if k in ['event_id','case_id','date_label','date_precision','event_text','status_as_recorded','sort_key']}|{'year':(re.search(r'(?:19|20)\d{2}',ev['date_label']) or ['undated'])[0]} for ev in sorted(new['events'],key=lambda x:x.get('sort_key') or '9999')]))
    dump(DATA/'support-audit.json',public_audit(ext['audit']))
    dump(DATA/'support-baseline.json',public(ext['baseline']))
    dump(DATA/'verification-evidence.json',public_evidence({'independent':new['independent_verification'],'sets':new['additional_verification_sets']}))
    # Do not publish snapshots containing local research paths or private Drive ids.
    dump(DATA/'provenance.json',provenance)
    summary={'as_of':new['as_of'],'built_for':'public_archive','counts':{'baseline_programs':66,'baseline_cases':111,'baseline_events':467,'selection':2120,'training':sum(x.get('training',False) for x in index if x['layer']=='selection'),'reference':497,'municipality_universe':len(munis),'deep':72,'deep_municipalities':len({x['municipality_code'] for x in new['cases']}),'deep_events':313,'claims':len(new['claims']),'review':343,'outcome_result':153,'study_result':1,'interim_result':1,'partial_implementation_result':1,'termination_only':1,'local':100,'history':len(layers['history'])},'evidence_counts':dict(collections.Counter(x['result_evidence_kind'] for x in new['official_document_reviews'])),'input_files':[{'filename':f['name'],'bytes':f['actual_bytes'],'sha256':f['sha256']} for f in manifest],'layers':{k:{'count':len(v),'index':f'data/index-{k}.json'} for k,v in layers.items()},'notes':['件数は資料ごとに単位が異なる。合計して総実証件数にしない。','1,741は調査母集団。全国自治体の10年史を調査し終えた数ではない。','旧111事例と追加72案件は別層。事業同一性を自動判定しない。']}
    assert summary['counts']['training']==339 and len(munis)==1741
    summary['municipality_research_depths']=dict(collections.Counter(m['research_depth'] for m in munis))
    dump(DATA/'summary.json',summary)
    # Stable small bootstrap supports policy detail additions without loading full indexes.
    pcounts=collections.defaultdict(lambda:collections.Counter())
    for x in index:
        if x['layer'] not in ['selection','reference']:continue
        for pid in x['program_ids']:
            pcounts[pid][x['layer']]+=1
            if x['evidence']=='outcome_result':pcounts[pid]['outcome_result']+=1
    (DATA/'bootstrap.js').write_text('window.MOBILITY_RESULTS_SUMMARY='+json.dumps({'counts':summary['counts'],'program_counts':pcounts},ensure_ascii=False,separators=(',',':'))+';\n')

    expected={
      'deep':{x['case_id'] for x in new['cases']},'selection':{x['record_id'] for x in ext['expansion']['records']},'reference':{x['record_id'] for x in ext['expansion']['reference_records']},'review':{x['review_id'] for x in new['official_document_reviews']},'local':{x['record_id'] for x in ext['municipality_index']['municipality_records']},'legacy':{x['id'] for x in old['cases']},'history':{x['record_id'] for x in ext['municipality_index']['history']}}
    checks=[]
    for k,es in expected.items():
        actual=set(ids_by_layer[k]);checks.append({'layer':k,'input_count':len(es),'index_count':len(ids_by_layer[k]),'detail_count':len(layers[k]),'missing_ids':sorted(es-actual),'extra_ids':sorted(actual-es),'duplicate_ids':len(ids_by_layer[k])-len(actual)})
        assert not es-actual and not actual-es and len(actual)==len(ids_by_layer[k])
    preserved_claims={x['claim_id'] for c in layers['deep'] for x in c['claims']};preserved_events={x['event_id'] for c in layers['deep'] for x in c['events']}
    assert preserved_claims==set(claims) and preserved_events==set(newevents)
    assert {i for r in layers['review'] for i in r['event_ids']}=={x['event_id'] for x in new['official_result_events']}
    assert len({x['target_selection_record_id'] for x in new['legacy_classification_overlay']})==343
    all_source_refs={ref['source_id'] for cl in new['claims'] for ref in cl['source_refs']}
    assert all_source_refs<=set(sources)
    oldmap={x['id']:x for x in ext['baseline']['cases']};program_oldmap={x['id']:x for x in ext['baseline']['programs']}
    fielddiff=[]
    for kind,items,other in [('case',old['cases'],oldmap),('program',old['programs'],program_oldmap)]:
        for c in items:
            for key in c:
                if c[key]!=other[c['id']].get(key):fielddiff.append({'kind':kind,'id':c['id'],'field':key,'resolution':'旧原JSONと拡張版baselineを別保持。旧原JSONを上書きしない。'})
    checks_path=OUT/'verification'/'data-reconciliation.json'
    report={'result':'pass','as_of':new['as_of'],'input_files_verified':len(manifest),'zip_json_byte_identical':True,'layers':checks,'claims':{'input':724,'projected':len(preserved_claims),'missing_source_ids':sorted(all_source_refs-set(sources))},'events':{'baseline':467,'deep_input':313,'deep_projected':len(preserved_events),'official_result_input':216,'official_result_projected':sum(len(v) for v in review_events.values())},'classification_overlay':{'input':343,'applied':len(overlays),'evidence_counts':summary['evidence_counts']},'municipalities':{'primary_universe':1741,'official_master_including_wards_and_references':len(masters),'deep_distinct_codes':62,'automatic_succession_merges':0},'baseline_field_differences':fielddiff,'private_input_ids_in_public':False,'scope_note':'機械的な入力・表示対応の検査。原典全件再読解や全国調査完了を意味しない。'}
    dump(checks_path,report)
    print(json.dumps({'counts':summary['counts'],'indexes_bytes':{p.name:p.stat().st_size for p in DATA.glob('index*.json')},'baseline_field_differences':len(fielddiff),'audit':str(checks_path)},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
    __import__('sync_release').sync_release(OUT)
