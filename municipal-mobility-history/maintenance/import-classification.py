#!/usr/bin/env python3
"""Project independent classification metadata; never rewrite research indexes/details.
Accepts either classification_v1.json or the Drive JSON's mobility_classification_v1.
"""
import argparse,collections,hashlib,json,re,jsonschema
from pathlib import Path
import sync_release
LAYERS=['deep','legacy','selection','reference','review','local','history']
CODES={'rideshare','ondemand','maas','automated','transit','small_shared','logistics','data_dx'}
PURPOSE={'tourism':'観光・来訪','decarbonization':'脱炭素','welfare':'福祉','medical':'通院・医療','shopping':'買物','school':'通学','commute':'通勤'}
def read(p):return json.loads(Path(p).read_text())
def encode(v):return (json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n').encode()
def write(p,v):
 p=Path(p);b=encode(v);assert not re.search(rb'https?://(?:drive|docs)\.google\.com|(?:/workspace/|/root/|/tmp/)|libfile_|ghp_[A-Za-z0-9]{20}|github_pat_|-----BEGIN .*PRIVATE KEY',b),'Private reference in public classification projection';p.parent.mkdir(parents=True,exist_ok=True)
 if not p.exists() or p.read_bytes()!=b:p.write_bytes(b)
def main(input_path,site):
 root=Path(site);data=root/'data';source=read(input_path);ledger=source.get('mobility_classification_v1',source)
 jsonschema.validate(ledger,read(root/'maintenance/classification.schema.json'))
 assert ledger['schema_version']=='mobility-classification-v1';assert {c['code'] for c in ledger['categories']}==CODES
 rows={layer:read(data/f'index-{layer}.json') for layer in LAYERS};expected={layer+':'+r['id'] for layer,rs in rows.items() for r in rs};assert set(ledger['records'])==expected,'Classification/index layer:id coverage mismatch'
 indexes={layer:hashlib.sha256((data/f'index-{layer}.json').read_bytes()).hexdigest() for layer in LAYERS}
 assert all(ledger['input_manifest'][layer]['sha256']==h for layer,h in indexes.items()),'Classification input index fingerprint is stale'
 protected={str(p.relative_to(data)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (data/'details').rglob('*.json')}
 source_rows={layer+':'+row['id']:row for layer,rs in rows.items() for row in rs};source_shards={}
 projections={layer:{} for layer in LAYERS};counts=collections.Counter();themes=collections.Counter();candidates=collections.Counter()
 for key,r in ledger['records'].items():
  layer,cid=key.split(':',1);assert r['record_id']==cid and r['layer']==layer
  source_row=source_rows[key];detail={}
  if layer in ('deep','legacy'):
   f=source_row['detail']
   if f not in source_shards:source_shards[f]=read(root/f)
   detail=source_shards[f][cid]
  assert r['source_fingerprint']==hashlib.sha256(json.dumps({'index':source_row,'detail':detail},ensure_ascii=False,sort_keys=True).encode()).hexdigest(),'Stale classification record '+key
  assert r['status'] in ['confirmed','candidate','unclassified'];assert set(r['themes']+r['candidates'])<=CODES
  assert len(r['themes'])==len(set(r['themes'])) and len(r['candidates'])==len(set(r['candidates']))
  if r['status']=='confirmed':assert r['primary'] in r['themes'] and r['primary'] in CODES
  else:assert r['primary'] is None and not r['themes'],'Unconfirmed classifications cannot have a primary/assigned theme'
  if r['status']=='unclassified':assert not r['candidates']
  projections[layer][cid]={k:r[k] for k in ['primary','themes','candidates','status','purpose_tags','lifecycle_tags']}
  counts[r['status']]+=1;themes.update(set(r['themes']));candidates.update(set(r['candidates']))
 # Full evidence is downloadable, never part of the initial UI request.
 public=encode(ledger)  # Hash private authoritative content; only allowlisted outputs below are published.
 for layer,records in projections.items():
  write(data/'classification'/f'{layer}.json',records)
  public_evidence={}
  for cid in records:
   rec=ledger['records'][layer+':'+cid];refs=[]
   for evidence in rec.get('evidence',[])+rec.get('facets',{}).get('attribute_evidence',[]):
    for source in evidence.get('source_urls',[]):
     if re.match(r'^https://',source.get('url','')):refs.append({k:source.get(k,'') for k in ['url','title','locator']})
   public_evidence[cid]={'version':rec['version'],'layer':layer,'record_id':cid,'original_themes':rec['original_themes'],'record_path':source_rows[layer+':'+cid]['detail'],'evidence':[{'source_urls':refs}]}
  write(data/'classification-evidence'/f'{layer}.json',public_evidence)
 old_map_file=root.parent/'mobility-policy-history/data/view-data.js';old_map=json.loads(old_map_file.read_text().split('=',1)[1].strip().rstrip(';'));old_map_cases={c['id']:c for c in old_map['cases']};valid_prefectures={m['prefecture_name'] for m in read(data/'municipalities.json')};locations={}
 for row in rows['legacy']:
  old=old_map_cases.get(row['id']);assert old,'Legacy location requires an identical published case ID'
  locations[row['id']]={'prefectures':[p for p in old.get('prefectures',[]) if p in valid_prefectures],'source_file':'../mobility-policy-history/data/view-data.js','source_sha256':hashlib.sha256(old_map_file.read_bytes()).hexdigest(),'source_record_id':row['id'],'source_as_of':old_map['as_of'],'method':'retained_published_prefectures_only_no_new_geocoding'}
 write(data/'classification/legacy-locations.json',locations)
 legacy_events=[]
 for row in rows['legacy']:
  f=row['detail']
  if f not in source_shards:source_shards[f]=read(root/f)
  for e in source_shards[f][row['id']].get('events',[]):
   date=e.get('event_date_display') or e.get('event_date') or '日付未取得';year=re.search(r'(?:19|20)\d{2}',str(e.get('event_date','')))
   legacy_events.append({'event_id':e['event_id'],'case_id':row['id'],'date_label':date,'date_precision':e.get('date_precision','unknown'),'event_text':e.get('event',''),'status_as_recorded':e.get('status','原記載参照'),'year':year[0] if year else 'undated','sort_key':str(e.get('event_date','')),'phase':'as_recorded'})
 assert len({e['event_id'] for e in legacy_events})==len(legacy_events)
 write(data/'classification/legacy-timeline.json',sorted(legacy_events,key=lambda e:e['sort_key']))
 # The full authoritative ledger stays in Drive/the private bundle, not duplicated publicly.
 if (data/'classification_v1.json').exists():(data/'classification_v1.json').unlink()
 meta={'schema_version':ledger['schema_version'],'sha256':hashlib.sha256(public).hexdigest(),'categories':ledger['categories'],'purposes':[{'code':k,'label':v} for k,v in ledger.get('tag_catalog',{}).get('purpose_tags',PURPOSE).items()],'semantics':ledger['semantics'],'counts':dict(counts),'theme_record_counts':dict(themes),'candidate_record_counts':dict(candidates),'counting_unit':'layer-scoped source records, not distinct projects'}
 summary=read(data/'summary.json');summary['classification']=meta;summary.pop('classification_pending',None);write(data/'summary.json',summary)
 p=data/'bootstrap.js';boot=json.loads(p.read_text().split('=',1)[1].strip().rstrip(';'));boot['classification']=meta;boot.pop('classification_pending',None);p.write_text('window.MOBILITY_RESULTS_SUMMARY='+json.dumps(boot,ensure_ascii=False,separators=(',',':'))+';\n')
 if (root/'verification/classification-pending.json').exists():(root/'verification/classification-pending.json').unlink()
 assert all(hashlib.sha256((data/f'index-{layer}.json').read_bytes()).hexdigest()==h for layer,h in indexes.items())
 assert all(hashlib.sha256((data/p).read_bytes()).hexdigest()==h for p,h in protected.items())
 report={'result':'pass','records':len(expected),'counts':dict(counts),'all_layers':{layer:len(v) for layer,v in projections.items()},'all_layer_ids_preserved':True,'legacy_case_events':len(legacy_events),'policy_events_not_reclassified':read(root/'verification/data-reconciliation.json')['events']['baseline']-len(legacy_events),'original_index_hashes':indexes,'detail_files_unchanged':len(protected),'classification_sha256':meta['sha256'],'primary_counts_do_not_double_count_secondary':True,'notes':'Classification confirms description only, never operation, authorization or successful outcomes.'}
 write(root/'verification/classification-reconciliation.json',report);sync_release.sync_release(root);print(json.dumps(report,ensure_ascii=False,indent=2));return report
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--site',default=str(Path(__file__).resolve().parents[1]));a=p.parse_args();main(a.input,a.site)
