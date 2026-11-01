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
def main(input_path,root):
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
 assert not (set(groups)&(set(existing_by_id)-owned)),'Existing deep case identity conflict; never infer merge'
 rows=[];details={};timeline=[];new_provenance=[];all_sources={};all_metric_ids=set();old_detail_count=len(list((data/'details/deep').glob('*.json')))-(len(prior.get('detail_files',[])) if prior else 0)
 labels={'summary':'結果概要','limitations':'課題・評価の限界','cost_and_financing':'費用と財源','analyst_lesson':'教訓（分析）'}
 for idx,(cid,observations) in enumerate(sorted(groups.items())):
  raw=observations[0]['raw']['research_case'];first=observations[0];codes=sorted({code for o in observations for code in o.get('municipality_codes',[o['municipality_code']])});assert all(c in master for c in codes)
  names={code:master[code]['municipality_name'] for code in codes};prefs=list(dict.fromkeys(master[code]['prefecture_name'] for code in codes));claims=[];events=[];metrics=[];sources={};obs_ids=[]
  for o in observations:
   obs_ids.append(o['observation_id'])
   for s in o['raw']['research_case'].get('sources',[]):
    clean={k:s.get(k) for k in ['source_id','url','title','publisher','document_date','document_type','locator','accessed_at','read_status','date_note','document_date_basis'] if k in s}
    if s['source_id'] in sources:assert sources[s['source_id']]['url']==clean['url'],'Conflicting source ID'
    else:sources[s['source_id']]=clean
   for field,value in o['fields'].items():
    if field in ('event','date_label','date_precision'):continue
    section='lesson' if field=='analyst_lesson' else 'result';claim_id=o['observation_id']+':'+field
    claims.append({'claim_id':claim_id,'case_id':cid,'section':section,'label':labels.get(field,field),'statement':value,'claim_type':'analysis' if section=='lesson' else 'fact','analysis_flag':section=='lesson','source_refs':[ref(s) for s in o['provenance'].get(field,[])],'verification_status':'accepted_continuation_ledger','observation_id':o['observation_id']})
   for m in o.get('metrics',[]):
    mid=m.get('metric_id') or o['observation_id']+':metric:'+str(len(metrics));assert mid not in all_metric_ids,'Duplicate metric ID';all_metric_ids.add(mid)
    metrics.append({**m,'metric_id':mid,'source_refs':[ref(m['source'])],'observation_id':o['observation_id']})
   f=o['fields']
   if 'event' in f:
    source_event=o['raw'].get('observed_record',{});eid=source_event.get('event_id') or o.get('observation_key') or o['observation_id']
    ev={'event_id':eid,'case_id':cid,'date_label':f['date_label'],'date_precision':f['date_precision'],'date_role':'event_date_as_recorded','event_text':f['event'],'status_as_recorded':PHASE.get(o['phase'],o['phase']),'phase':o['phase'],'source_refs':[ref(s) for s in o['sources']],'sort_key':f['date_label'],'sort_key_note':'原記載による並べ替え専用。日付を補完しない。','observation_id':o['observation_id']};events.append(ev)
    timeline.append({k:ev[k] for k in ['event_id','case_id','date_label','date_precision','event_text','status_as_recorded','sort_key','phase','observation_id']}|{'year':(re.search(r'(?:19|20)\d{2}',ev['date_label']) or ['undated'])[0]})
  # Brief call/selection fields never imply a sourced adoption if status is missing.
  for section,label in [('call','公募と目的'),('selection','採択と実施内容')]:
   part=raw.get(section,{}) or {};claims.append({'claim_id':cid+':'+section,'case_id':cid,'section':section,'label':label,'statement':part.get('text','未取得。結果・年月変遷を優先した調査。'),'claim_type':'fact','analysis_flag':False,'source_refs':[],'verification_status':part.get('status','not_obtained')})
  if not any(c['section']=='lesson' for c in claims):claims.append({'claim_id':cid+':lesson','case_id':cid,'section':'lesson','label':'教訓（分析）','statement':raw.get('lesson','未整理'),'claim_type':'analysis','analysis_flag':True,'source_refs':[]})
  assert all(r['source_id'] in sources for c in claims for r in c['source_refs']);assert all(r['source_id'] in sources for ev in events for r in ev['source_refs']);assert all(m['source']['document_id'] in sources for m in metrics)
  for sid,s in sources.items():
   if sid in all_sources:assert all_sources[sid]['url']==s['url']
   all_sources[sid]=s
  actual=[e for e in events if e['phase'] in ('actual','interim','trial_ended','service_ended','suspended')];last=max(actual,key=lambda e:e['date_label']) if actual else None
  file='data/details/deep/'+f'{old_detail_count+idx//25:03d}.json';source_pointer='/continuous_update_appendix_v1/observations';title=raw.get('title',first['project_name']);municipality='・'.join(names.values());primary=raw['municipality_code']
  row={'id':cid,'title':title,'prefectures':prefs,'municipality':municipality,'codes':codes,'years':base.years(base.text(events)+' '+base.text([m['period'] for m in metrics])),'themes':base.themes(title),'state':'result','state_label':'結果・変遷の追加詳査','evidence':'deep_result','evidence_label':'結果・変遷を詳査','excerpt':raw.get('results',{}).get('summary','')[:260],'last_event_date':last['date_label'] if last else '日付未取得','program_ids':[],'layer':'deep','detail':file}
  provenance={'source_file':Path(input_path).name,'source_pointer':source_pointer,'original_id':cid,'ledger_sha256':ledger,'observation_ids':obs_ids}
  public_raw={k:raw.get(k) for k in ['project_id','municipality_code','prefecture','municipality','title','operator','fiscal_year','results','call','selection','lesson','lesson_type','limitations','current_status_as_recorded'] if k in raw}
  detail={'case_id':cid,'municipality_code':primary,'municipality_codes':codes,'municipality_names':names,'prefecture':raw['prefecture'],'municipality':municipality,'title':title,'claims':claims,'events':events,'metrics':metrics,'sources':list(sources.values()),'source_ids':list(sources),'result_claim_ids':[c['claim_id'] for c in claims if c['section']=='result'],'call_claim_id':cid+':call','selection_claim_id':cid+':selection','lesson_claim_id':next(c['claim_id'] for c in claims if c['section']=='lesson'),'event_ids':[e['event_id'] for e in events],'raw':public_raw,'current_observation':raw.get('current_status_as_recorded') or '記録後の状態は未確認。予定を実施と解釈しない。','last_documented_event':last,'state':'result','state_label':'結果・変遷の追加詳査','current_status_checked_at':None,'related_baseline':[],'corrections':[],'provenance':provenance,'observation_ids':obs_ids,'interpretation_note':'広域案件の指標を自治体ごとに重複計上しない。新たな採択件数ではなく詳査結果の追加。'}
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
 summary=load(data/'summary.json');review_dates=[s.get('accessed_at','') for s in all_sources.values() if re.fullmatch(r'\d{4}-\d{2}-\d{2}',s.get('accessed_at',''))];summary['as_of']=ap.get('as_of') or max(review_dates,default=summary['as_of']);summary['built_for']='public_archive';summary['counts'].update(deep=len(baseline_index)+len(rows),deep_municipalities=len({c for r in baseline_index+rows for c in r['codes']}),deep_events=len(old_timeline)+len(timeline),claims=724+sum(len(v['claims']) for v in details.values()),continuation_cases=len(rows),continuation_events=len(timeline),continuation_metrics=sum(len(d['metrics']) for d in details.values()),continuation_sources=len(all_sources));summary['layers']['deep']['count']=summary['counts']['deep'];summary['municipality_research_depths']=dict(collections.Counter(m['research_depth'] for m in munis));summary['notes']=[x for x in summary['notes'] if '追加72案件' not in x and not x.startswith('旧111代表事例と結果詳査')]+[f"旧111代表事例と結果詳査{len(baseline_index)+len(rows)}案件は別層。旧72詳査に{len(rows)}案件を追加。事業同一性を自動判定しない。"];summary['continuation']={'ledger_sha256':ledger,'input_sha256':sha(Path(input_path).read_bytes()),'cases':len(rows),'events':len(timeline),'metrics':sum(len(d['metrics']) for d in details.values()),'privacy':'allowlist projection; raw input remains private'};write(data/'summary.json',summary)
 bootstrap=(data/'bootstrap.js').read_text();bootstrap_obj=json.loads(bootstrap.split('=',1)[1].strip().rstrip(';'));bootstrap_obj['counts']=summary['counts'];bootstrap_obj['as_of']=summary['as_of'];new_bootstrap='window.MOBILITY_RESULTS_SUMMARY='+json.dumps(bootstrap_obj,ensure_ascii=False,separators=(',',':'))+';\n'
 if (data/'bootstrap.js').read_text()!=new_bootstrap:(data/'bootstrap.js').write_text(new_bootstrap)
 write(data/'sources-continuation.json',list(all_sources.values()))
 manifest={'schema_version':'mobility_continuation_overlay_v1','ledger_sha256':ledger,'source_sha256':sha(Path(input_path).read_bytes()),'case_ids':list(details),'observation_ids':[o['observation_id'] for o in ap['observations']],'detail_files':[f.removeprefix('data/') for f in output_files],'metrics':len(all_metric_ids),'events':len(timeline),'original_layers_retained':True,'retained_baseline_file_hashes':retained_hashes};write(manifest_path,manifest)
 after={str(p.relative_to(data)):sha(p.read_bytes()) for p in data.rglob('*') if p.is_file()};changed_protected=[name for name,h in protected.items() if after.get(name)!=h];assert not changed_protected,changed_protected
 assert len({o for d in details.values() for o in d['observation_ids']})==len(ap['observations'])
 assert len({e['event_id'] for e in timeline})==len(timeline),'Duplicate new event identity'
 for name in ['index-deep.json','timeline-index.json','municipalities.json','summary.json','bootstrap.js','provenance.json','sources-continuation.json','continuation-manifest.json',*[f.removeprefix('data/') for f in output_files]]:
  raw=(data/name).read_text();assert not PRIVATE.search(raw) and not SECRET.search(raw) and not CONTACT.search(raw),name
 report={'result':'pass','ledger_sha256':ledger,'counts':summary['counts'],'retained_deep_ids':len(baseline_index),'retained_deep_events':len(old_timeline),'retained_deep_claims':724,'unchanged_protected_files':len(protected),'changed_protected_files':changed_protected,'new_case_ids':list(details),'new_observation_ids':len(ap['observations']),'source_reference_integrity':'passed','public_privacy_scan':'passed','protected_file_hashes':protected,'privacy_projection_exceptions':{name:{'original_sha256':retained_hashes.get(name),'current_sha256':after.get(name),'reason':'Public QA scope projection only; research data unchanged. Original bytes retained by publishing coordinator.'} for name in sorted(PRIVACY_PROJECTIONS)},'detail_files':manifest['detail_files'],'note':'All pre-existing layers and baseline field-difference support retained. Only explicit new cases appended; no locality-based identity merge.'}
 write(root/'verification/continuation-reconciliation.json',report);__import__('sync_release').sync_release(root);print(json.dumps({k:v for k,v in report.items() if k!='protected_file_hashes'},ensure_ascii=False,indent=2));return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--site',default=str(Path(__file__).resolve().parents[1]));a=p.parse_args();main(a.input,a.site)
