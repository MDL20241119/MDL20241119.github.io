#!/usr/bin/env python3
"""Read-only schema + source + preservation checks for the accepted continuation."""
import argparse,hashlib,json,re
from pathlib import Path
import jsonschema

def load(p):return json.loads(Path(p).read_text())
def verify(site,input_file):
 root=Path(site);data=root/'data';schema=load(root/'maintenance/continuation.schema.json');incoming=load(input_file);ap=incoming['continuous_update_appendix_v1'];manifest=load(data/'continuation-manifest.json');report=load(root/'verification/continuation-reconciliation.json')
 assert manifest['ledger_sha256']==ap['ledger_sha256'];rows=load(data/'index-deep.json');assert len({r['id'] for r in rows})==len(rows)
 new_ids=set(manifest['case_ids']);new_details={}
 for file in manifest['detail_files']:
  chunk=load(data/file)
  for cid,detail in chunk.items():jsonschema.validate(detail,schema);assert cid==detail['case_id'];new_details[cid]=detail
 assert set(new_details)==new_ids
 metrics=[m for d in new_details.values() for m in d['metrics']];events=[e for d in new_details.values() for e in d['events']];observations=[i for d in new_details.values() for i in d['observation_ids']]
 assert set(observations)=={o['observation_id'] for o in ap['observations']};assert len(observations)==len(ap['observations'])
 accepted_metrics={m['metric_id']:m for o in ap['observations'] for m in o.get('metrics',[])}
 assert {m['metric_id'] for m in metrics}==set(accepted_metrics)
 for m in metrics:
  orig=accepted_metrics[m['metric_id']]
  for key in ['value','unit','period','definition','phase','verification','source']:assert m[key]==orig[key],(m['metric_id'],key)
 old_events={e['event_id']:e for e in incoming['events']};calendar=load(data/'timeline-index.json');calendar_by_id={e['event_id']:e for e in calendar};assert len(calendar)==len(calendar_by_id)
 for eid,e in old_events.items():
  for field in ['event_id','case_id','date_label','date_precision','event_text','status_as_recorded','sort_key']:
   if field in e:assert calendar_by_id[eid].get(field)==e[field],(eid,field)
 # Every old case, claim, source and event in the branch's first three immutable shards remains untouched.
 old_details={}
 for file in (data/'details/deep').glob('*.json'):
  for cid,d in load(file).items():
   if cid not in new_ids:old_details[cid]=d
 assert set(old_details)=={c['case_id'] for c in incoming['cases']}
 assert {c['claim_id'] for d in old_details.values() for c in d['claims']}=={c['claim_id'] for c in incoming['claims']}
 assert {e['event_id'] for d in old_details.values() for e in d['events']}==set(old_events)
 for name,h in report['protected_file_hashes'].items():assert hashlib.sha256((data/name).read_bytes()).hexdigest()==h,name
 for d in new_details.values():
  sids={s['source_id'] for s in d['sources']}
  assert all(ref['source_id'] in sids for rec in d['claims']+d['events']+d['metrics'] for ref in rec['source_refs'])
  assert all(code in {m['municipality_code'] for m in load(data/'municipalities.json')} for code in d['municipality_codes'])
 result={'result':'pass','schema_validation':'passed','old_case_ids_retained':len(old_details),'old_claim_ids_retained':len(incoming['claims']),'old_event_ids_and_calendar_fields_retained':len(old_events),'cumulative_continuation_case_views':len(new_details),'current_batch':load(data/'summary.json').get('current_batch'),'new_events':len(events),'new_metrics':len(metrics),'new_observations':len(observations),'new_distinct_municipalities':len({code for d in new_details.values() for code in d['municipality_codes']}),'all_metric_values_units_periods_phases_and_sources_match_ledger':True,'unchanged_protected_files':len(report['protected_file_hashes'])}
 print(json.dumps(result,ensure_ascii=False,indent=2));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--site',required=True);p.add_argument('--input',required=True);p.add_argument('--report');a=p.parse_args();result=verify(a.site,a.input)
 if a.report:Path(a.report).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
