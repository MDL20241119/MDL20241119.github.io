#!/usr/bin/env python3
"""Append accepted continuation observations to the retained preview-branch schema.
Run after build.py with the original frozen inputs. Never replaces prior data layers.
"""
import argparse,collections,copy,hashlib,importlib.util,json,re,sys
sys.dont_write_bytecode=True
from pathlib import Path
PRIVACY_PROJECTIONS={'support-audit.json','verification-evidence.json'}
PRIVATE=re.compile(r'https?://(?:drive|docs)\.google\.com/[^\s"<>]+|https?://chatgpt\.com/api/[^\s"<>]+|libfile_[A-Za-z0-9_-]+|(?:/workspace/|/root/|/tmp/)[^\s"<>]*',re.I)
SECRET=re.compile(r'gh[pousr]_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16}|-----BEGIN .*PRIVATE KEY-----|Bearer\s+[A-Za-z0-9._-]+',re.I)
CONTACT=re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}|(?<!\d)0\d{1,3}-\d{2,4}-\d{4}(?!\d)')
PHASE={'actual':'実績として確認','interim':'中間結果として確認','planned':'予定・計画（実施未確認）','trial_ended':'実証終了（サービス終了とは別）','service_ended':'サービス終了','suspended':'休止・中断','unknown':'未確認'}
def encode(v):return (json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n').encode()
def sha(v):return hashlib.sha256(v).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def safe(v):
 if isinstance(v,dict):return {k:safe(x) for k,x in v.items()}
 if isinstance(v,list):return [safe(x) for x in v]
 if isinstance(v,str):
  if SECRET.search(v):raise ValueError('Secret marker in public field')
  return CONTACT.sub('［連絡先非掲載］',PRIVATE.sub('［非公開参照を省略］',v))
 return v
def ref(s):return {'source_id':s['document_id'],'url':s['url'],'locator':s['locator'],'support_scope':'specified_source_location'}
def write(p,v):
 b=encode(safe(v));p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 if not p.exists() or p.read_bytes()!=b:p.write_bytes(b)
 return sha(b)
def main(input_path,root,defer_classification=False):
 root=Path(root);data=root/'data';incoming=load(input_path);ap=incoming['continuous_update_appendix_v1'];ledger=ap['ledger_sha256'];manifest_path=data/'continuation-manifest.json';prior=load(manifest_path) if manifest_path.exists() else None
 spec=importlib.util.spec_from_file_location('retained_builder',root/'maintenance/build.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
 before={str(p.relative_to(data)):sha(p.read_bytes()) for p in data.rglob('*') if p.is_file()};old_index=load(data/'index-deep.json');existing_by_id={x['id']:x for x in old_index};owned=set(prior['case_ids']) if prior else set();baseline_index=[x for x in old_index if x['id'] not in owned]
 assert len(baseline_index)==72,'Retained baseline must remain 72 deep cases'
 retained_hashes=prior.get('retained_baseline_file_hashes',before) if prior else before
 protected={name:h for name,h in retained_hashes.items() if name not in PRIVACY_PROJECTIONS and name not in {'index-deep.json','timeline-index.json','municipalities.json','summary.json','bootstrap.js','provenance.json','continuation-manifest.json','sources-continuation.json'} and not (prior and name in prior.get('detail_files',[]))}
 master={x['municipality_code']:x for x in load(data/'municipalities.json')};groups=collections.defaultdict(list)
 for o in ap['observations']:
  raw=o.get('raw',{}).get('research_case',{});cid=raw.get('case_id',raw.get('project_id'));assert cid,'explicit case identity required'
  groups[cid].append(o)
 assert owned <= set(groups),'Cumulative ledger omitted previously published continuation cases'
 legacy_by_id={x['id']:x for x in load(data/'index-legacy.json')}
 prior_details={cid:load(root/row['detail'])[cid] for cid,row in existing_by_id.items() if cid in owned}
 next_shard=1+max(int(p.stem) for p in (data/'details/deep').glob('*.json'))
 new_ids=sorted(set(groups)-set(existing_by_id));new_files={cid:'data/details/deep/'+f'{next_shard+i//25:03d}.json' for i,cid in enumerate(new_ids)}
 assert not (set(groups)&(set(existing_by_id)-owned)),'Existing deep case identity conflict; never infer merge'
 rows=[];details={};timeline=[];new_provenance=[];all_sources={};all_metric_ids=set();old_detail_count=len(list((data/'details/deep').glob('*.json')))-(len(prior.get('detail_files',[])) if prior else 0)
 labels={'summary':'結果概要','limitations':'課題・評価の限界','cost_and_financing':'費用と財源','analyst_lesson':'教訓（分析）','correction_note':'旧記録の再検証・原典間の相違','coverage_scope':'調査対象期間の区分（原記載）','evidence_conflict_note':'原典間の相違に関する注記'}
 for idx,(cid,observations) in enumerate(sorted(groups.items())):
  current_members=[o for o in observations if ap.get('current_batch_id') in ap.get('observation_batches',{}).get(o['observation_id'],[]) and ap.get('current_batch_id')]
  preferred=next((o for o in current_members if 'summary' in o['fields']),None) or next((o for o in observations if 'summary' in o['fields']),observations[0])
  raw=preferred['raw']['research_case'];first=preferred;
  if raw.get('change_type')=='update_existing_case':
   assert raw.get('baseline_case_id')==cid and raw.get('baseline_layer')=='legacy' and cid in legacy_by_id,'Update identity must explicitly match an existing legacy case'
   assert raw.get('identity_evidence') and raw.get('update_reason'),'Update identity evidence and reason required'
  codes=sorted({code for o in observations for code in o.get('municipality_codes',[o['municipality_code']])});assert all(c in master for c in codes)
  names={code:master[code]['municipality_name'] for code in codes};prefs=list(dict.fromkeys(master[code]['prefecture_name'] for code in codes));claims=[];events=[];metrics=[];sources={};obs_ids=[]
  for o in observations:
   obs_ids.append(o['observation_id'])
   for s in o['raw']['research_case'].get('sources',[]):
    clean={k:s.get(k) for k in ['source_id','url','title','publisher','document_date','document_type','locator','accessed_at','read_status','date_note','document_date_basis'] if k in s}
    if s['source_id'] in sources:assert sources[s['source_id']]['url']==clean['url'],'Conflicting source ID'
    else:sources[s['source_id']]=clean
   for field,value in o['fields'].items():
    if field in ('event','date_label','date_precision'):continue
    section='lesson' if field=='analyst_lesson' else 'metadata' if field=='coverage_scope' else 'result';claim_id=o['observation_id']+':'+field
    claims.append({'claim_id':claim_id,'case_id':cid,'section':section,'label':labels.get(field,field),'statement':value,'claim_type':'analysis' if section=='lesson' else 'fact','analysis_flag':section=='lesson','source_refs':[ref(s) for s in o['provenance'].get(field,[])],'verification_status':'accepted_continuation_ledger','observation_id':o['observation_id']})
   for m in o.get('metrics',[]):
    mid=m.get('metric_id') or o['observation_id']+':metric:'+str(len(metrics));assert mid not in all_metric_ids,'Duplicate metric ID';all_metric_ids.add(mid)
    metrics.append({**m,'metric_id':mid,'source_refs':[ref(m['source'])],'observation_id':o['observation_id']})
   f=o['fields']
   if 'event' in f:
    source_event=o['raw'].get('observed_record',{});eid=source_event.get('event_id') or o.get('observation_key') or o['observation_id']
    ev={'event_id':eid,'case_id':cid,'date_label':f['date_label'],'date_precision':f['date_precision'],'date_role':'event_date_as_recorded','event_text':f['event'],'status_as_recorded':'原典間相違（確定実績への採用を保留）' if source_event.get('evidence_conflict') else PHASE.get(o['phase'],o['phase']),'phase':o['phase'],'source_refs':[ref(s) for s in o['sources']],'sort_key':f['date_label'],'sort_key_note':'原記載による並べ替え専用。日付を補完しない。','observation_id':o['observation_id'],'evidence_conflict':bool(source_event.get('evidence_conflict')),'original_phase':source_event.get('original_phase'),'raw_event_record':source_event};events.append(ev)
    timeline.append({k:ev[k] for k in ['event_id','case_id','date_label','date_precision','event_text','status_as_recorded','sort_key','phase','observation_id','evidence_conflict','original_phase']}|{'year':(re.search(r'(?:19|20)\d{2}',ev['date_label']) or ['undated'])[0]})
  # Brief call/selection fields never imply a sourced adoption if status is missing.
  for section,label in [('call','公募と目的'),('selection','採択と実施内容')]:
   part=raw.get(section,{}) or {};claims.append({'claim_id':cid+':'+section,'case_id':cid,'section':section,'label':label,'statement':part.get('text','未取得。結果・年月変遷を優先した調査。'),'claim_type':'fact','analysis_flag':False,'source_refs':[],'verification_status':part.get('status','not_obtained')})
  if not any(c['section']=='lesson' for c in claims):claims.append({'claim_id':cid+':lesson','case_id':cid,'section':'lesson','label':'教訓（分析）','statement':raw.get('lesson','未整理'),'claim_type':'analysis','analysis_flag':True,'source_refs':[]})
  assert all(r['source_id'] in sources for c in claims for r in c['source_refs']);assert all(r['source_id'] in sources for ev in events for r in ev['source_refs']);assert all(m['source']['document_id'] in sources for m in metrics)
  for sid,s in sources.items():
   if sid in all_sources:assert all_sources[sid]['url']==s['url']
   all_sources[sid]=s
  actual=[e for e in events if not e.get('evidence_conflict') and e['phase'] in ('actual','interim','trial_ended','service_ended','suspended')];last=max(actual,key=lambda e:e['date_label']) if actual else None
  file=existing_by_id[cid]['detail'] if cid in owned else new_files[cid];source_pointer='/continuous_update_appendix_v1/observations';title=raw.get('title',first['project_name']);municipality='・'.join(names.values());primary=raw['municipality_code']
  row={'id':cid,'title':title,'prefectures':prefs,'municipality':municipality,'codes':codes,'years':base.years(base.text(events)+' '+base.text([m['period'] for m in metrics])),'themes':base.themes(title),'state':'result','state_label':'結果・変遷の追加詳査','evidence':'deep_result','evidence_label':'結果・変遷を詳査','excerpt':raw.get('results',{}).get('summary','')[:260],'last_event_date':last['date_label'] if last else '日付未取得','program_ids':[],'layer':'deep','detail':file}
  provenance={'source_file':Path(input_path).name,'source_pointer':source_pointer,'original_id':cid,'ledger_sha256':ledger,'observation_ids':obs_ids}
  public_raw={k:raw.get(k) for k in ['project_id','municipality_code','prefecture','municipality','title','operator','fiscal_year','results','call','selection','lesson','lesson_type','limitations','current_status_as_recorded'] if k in raw}
  detail={'case_id':cid,'municipality_code':primary,'municipality_codes':codes,'municipality_names':names,'prefecture':raw['prefecture'],'municipality':municipality,'title':title,'claims':claims,'events':events,'metrics':metrics,'sources':list(sources.values()),'source_ids':list(sources),'result_claim_ids':[c['claim_id'] for c in claims if c['section']=='result'],'call_claim_id':cid+':call','selection_claim_id':cid+':selection','lesson_claim_id':next(c['claim_id'] for c in claims if c['section']=='lesson'),'event_ids':[e['event_id'] for e in events],'raw':public_raw,'current_observation':raw.get('current_status_as_recorded') or '記録後の状態は未確認。予定を実施と解釈しない。','last_documented_event':last,'state':'result','state_label':'結果・変遷の追加詳査','current_status_checked_at':raw.get('current_status_checked_at'),'related_baseline':[],'corrections':[],'provenance':provenance,'observation_ids':obs_ids,'interpretation_note':'広域案件の指標を自治体ごとに重複計上しない。新たな採択件数ではなく詳査結果の追加。'}
  # Explicit continuity classifications; a new detailed view is not a new project.
  change_type=raw.get('change_type','new_detailed_case');is_update=change_type=='update_existing_case'
  row.update(change_type=change_type,current_batch=bool(current_members),batch_ids=sorted({b for o in observations for b in ap.get('observation_batches',{}).get(o['observation_id'],[])}))
  detail.update(change_type=change_type,baseline_case_id=raw.get('baseline_case_id'),baseline_layer=raw.get('baseline_layer'),identity_evidence=raw.get('identity_evidence'),update_reason=raw.get('update_reason'),evidence_conflicts=raw.get('evidence_conflicts') or raw.get('contradictory_sources') or [],research_corrections=raw.get('corrections') or [],baseline_event_context=raw.get('baseline_event_context'),baseline_snapshot_sha256=raw.get('baseline_snapshot_sha256'),correction_note=raw.get('correction_note'))
  if cid in owned and not current_members and ap.get('current_batch_id'):
   assert set(obs_ids)==set(prior_details[cid]['observation_ids']),'Prior case observations changed outside current batch'
   detail=copy.deepcopy(prior_details[cid]);row=copy.deepcopy(existing_by_id[cid]);row['current_batch']=False
  details[cid]=detail;rows.append(row);new_provenance.append({'layer':'deep','id':cid,**provenance,'display_file':file})
 output_files=sorted(set(row['detail'] for row in rows))
 for file in output_files:write(root/file,{row['id']:details[row['id']] for row in rows if row['detail']==file})
 write(data/'index-deep.json',baseline_index+rows)
 old_timeline=load(data/'timeline-index.json');old_timeline=[e for e in old_timeline if e['case_id'] not in owned];assert len(old_timeline)==313;assert not set(e['event_id'] for e in old_timeline)&set(e['event_id'] for e in timeline)
 write(data/'timeline-index.json',sorted(old_timeline+timeline,key=lambda e:e.get('sort_key') or '9999'))
 munis=load(data/'municipalities.json')
 for m in munis:
  original=[cid for cid in m['deep_case_ids'] if cid not in owned];extra=[r['id'] for r in rows if m['municipality_code'] in r['codes']];m['deep_case_ids']=original+extra
  if m['deep_case_ids']:m['research_depth']='結果詳査あり（全年度調査未完）'
 write(data/'municipalities.json',munis)
 provenance=load(data/'provenance.json');write(data/'provenance.json',[x for x in provenance if not (x['layer']=='deep' and x['id'] in owned)]+new_provenance)
 summary=load(data/'summary.json');review_dates=[s.get('accessed_at','') for s in all_sources.values() if re.fullmatch(r'\d{4}-\d{2}-\d{2}',s.get('accessed_at',''))];summary['as_of']=ap.get('as_of') or max(review_dates,default=summary['as_of']);summary['built_for']='public_archive';summary['counts'].update(deep=len(baseline_index)+len(rows),deep_municipalities=len({c for r in baseline_index+rows for c in r['codes']}),deep_events=len(old_timeline)+len(timeline),claims=724+sum(len(v['claims']) for v in details.values()),continuation_cases=len(rows),continuation_events=len(timeline),continuation_metrics=sum(len(d['metrics']) for d in details.values()),continuation_sources=len(all_sources));summary['layers']['deep']['count']=summary['counts']['deep'];summary['municipality_research_depths']=dict(collections.Counter(m['research_depth'] for m in munis));summary['notes']=[x for x in summary['notes'] if '追加72案件' not in x and not x.startswith('旧111代表事例と結果詳査')]+[f"旧111代表事例と結果詳査{len(baseline_index)+len(rows)}案件は別層。旧72詳査に{len(rows)}詳査ビューを増補（既存案件の初回詳査を含み、新規事業数ではない）。事業同一性を自動判定しない。"];summary['continuation']={'ledger_sha256':ledger,'input_sha256':sha(Path(input_path).read_bytes()),'cases':len(rows),'events':len(timeline),'metrics':sum(len(d['metrics']) for d in details.values()),'privacy':'allowlist projection; raw input remains private'};write(data/'summary.json',summary)
 current_rows=[r for r in rows if r.get('current_batch')]
 if not ap.get('current_batch_id'):current_rows=rows
 summary['legacy_updates']={r['id']:{'case_id':r['id'],'identity_evidence':details[r['id']].get('identity_evidence'),'has_conflicts':bool(details[r['id']].get('evidence_conflicts'))} for r in rows if r.get('change_type')=='update_existing_case'}
 summary['current_batch']={'id':ap.get('current_batch_id'),'case_ids':[r['id'] for r in current_rows],'new_cases':sum(r['change_type']!='update_existing_case' for r in current_rows),'updated_cases':sum(r['change_type']=='update_existing_case' for r in current_rows),'note':'既存案件の初回詳査を新規事業数に含めない。'}
 summary['counts'].update(current_batch_cases=len(current_rows),current_batch_new_cases=summary['current_batch']['new_cases'],current_batch_updated_cases=summary['current_batch']['updated_cases'])
 write(data/'summary.json',summary)
 bootstrap=(data/'bootstrap.js').read_text();bootstrap_obj=json.loads(bootstrap.split('=',1)[1].strip().rstrip(';'));bootstrap_obj['counts']=summary['counts'];bootstrap_obj['as_of']=summary['as_of'];bootstrap_obj['current_batch']=summary['current_batch'];bootstrap_obj['legacy_updates']=summary['legacy_updates'];new_bootstrap='window.MOBILITY_RESULTS_SUMMARY='+json.dumps(bootstrap_obj,ensure_ascii=False,separators=(',',':'))+';\n'
 if (data/'bootstrap.js').read_text()!=new_bootstrap:(data/'bootstrap.js').write_text(new_bootstrap)
 write(data/'sources-continuation.json',list(all_sources.values()))
 manifest={'schema_version':'mobility_continuation_overlay_v1','ledger_sha256':ledger,'source_sha256':sha(Path(input_path).read_bytes()),'case_ids':list(details),'current_batch':summary['current_batch'],'observation_ids':[o['observation_id'] for o in ap['observations']],'detail_files':[f.removeprefix('data/') for f in output_files],'metrics':len(all_metric_ids),'events':len(timeline),'original_layers_retained':True,'retained_baseline_file_hashes':retained_hashes};write(manifest_path,manifest)
 after={str(p.relative_to(data)):sha(p.read_bytes()) for p in data.rglob('*') if p.is_file()};changed_protected=[name for name,h in protected.items() if after.get(name)!=h];assert not changed_protected,changed_protected
 assert len({o for d in details.values() for o in d['observation_ids']})==len(ap['observations'])
 assert len({e['event_id'] for e in timeline})==len(timeline),'Duplicate new event identity'
 for name in ['index-deep.json','timeline-index.json','municipalities.json','summary.json','bootstrap.js','provenance.json','sources-continuation.json','continuation-manifest.json',*[f.removeprefix('data/') for f in output_files]]:
  raw=(data/name).read_text();assert not PRIVATE.search(raw) and not SECRET.search(raw) and not CONTACT.search(raw),name
 report={'result':'pass','ledger_sha256':ledger,'counts':summary['counts'],'retained_deep_ids':len(baseline_index),'retained_deep_events':len(old_timeline),'retained_deep_claims':724,'unchanged_protected_files':len(protected),'changed_protected_files':changed_protected,'continuation_case_ids':list(details),'cumulative_observation_count':len(ap['observations']),'current_batch':summary['current_batch'],'source_reference_integrity':'passed','public_privacy_scan':'passed','protected_file_hashes':protected,'privacy_projection_exceptions':{name:{'original_sha256':retained_hashes.get(name),'current_sha256':after.get(name),'reason':'Public QA scope projection only; research data unchanged. Original bytes retained by publishing coordinator.'} for name in sorted(PRIVACY_PROJECTIONS)},'detail_files':manifest['detail_files'],'note':'All pre-existing layers and baseline field-difference support retained. Explicit new detailed views and evidence-backed existing legacy case enrichments only; no locality-based identity merge.'}
 write(root/'verification/continuation-reconciliation.json',report)
 if defer_classification:
  staged_summary=load(data/'summary.json');staged_summary['classification_pending']=True;write(data/'summary.json',staged_summary)
  staged_boot=json.loads((data/'bootstrap.js').read_text().split('=',1)[1].strip().rstrip(';'));staged_boot['classification_pending']=True;(data/'bootstrap.js').write_text('window.MOBILITY_RESULTS_SUMMARY='+json.dumps(staged_boot,ensure_ascii=False,separators=(',',':'))+';\n')
  write(root/'verification/classification-pending.json',{'public_build_blocked':True,'reason':'Temporary index for classification refresh; do not publish.'})
 elif incoming.get('mobility_classification_v1'):
  class_spec=importlib.util.spec_from_file_location('classification_importer',root/'maintenance/import-classification.py');class_module=importlib.util.module_from_spec(class_spec);class_spec.loader.exec_module(class_module);class_module.main(input_path,root)
 __import__('sync_release').sync_release(root);print(json.dumps({k:v for k,v in report.items() if k!='protected_file_hashes'},ensure_ascii=False,indent=2));return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--site',default=str(Path(__file__).resolve().parents[1]));p.add_argument('--defer-classification',action='store_true',help='Temporary private staging only; blocks publication until refreshed metadata is imported');a=p.parse_args();main(a.input,a.site,a.defer_classification)
