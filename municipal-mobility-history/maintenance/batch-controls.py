#!/usr/bin/env python3
"""Freeze independent accepted-ledger controls BEFORE generating a public overlay.
Never derive expected outcomes from newly generated public files.
"""
import argparse,collections,hashlib,json
from pathlib import Path

def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def build(input_path,previous_site,output):
 incoming=read(input_path);ap=incoming['continuous_update_appendix_v1'];root=Path(previous_site);groups=collections.defaultdict(list)
 for o in ap['observations']:
  raw=o['raw']['research_case'];groups[raw.get('case_id',raw.get('project_id'))].append(o)
 current=ap['current_batch_id'];case_ids=[];updates=[];claims=724;events=313
 for cid,observations in groups.items():
  members=[o for o in observations if current in ap['observation_batches'].get(o['observation_id'],[])]
  if members:
   case_ids.append(cid)
   if members[0]['raw']['research_case'].get('change_type')=='update_existing_case':updates.append(cid)
  claims+=sum(len([k for k in o['fields'] if k not in ('event','date_label','date_precision')]) for o in observations)+2
  if not any('analyst_lesson' in o['fields'] for o in observations):claims+=1
  events+=sum('event' in o['fields'] for o in observations)
 fixture={'basis':'accepted ledger plus prior published byte snapshots, not generated overlay','input_sha256':sha(input_path),'ledger_sha256':ap['ledger_sha256'],'current_batch_id':current,'case_ids':sorted(groups),'current_case_ids':sorted(case_ids),'updated_case_ids':sorted(updates),'new_case_ids':sorted(set(case_ids)-set(updates)),'expected':{'deep':72+len(groups),'claims':claims,'events':events},'previous_file_hashes':{str(p.relative_to(root)):sha(p) for folder in ['data/details/deep','data/details/legacy'] for p in sorted((root/folder).glob('*.json'))},'metrics':[{k:m[k] for k in ['metric_id','value','unit','period','definition','phase','verification']} for o in ap['observations'] for m in o.get('metrics',[])],'events':[{'event_id':o['raw'].get('observed_record',{}).get('event_id') or o.get('observation_key') or o['observation_id'],'date_label':o['fields']['date_label'],'phase':o['phase'],'evidence_conflict':bool(o['raw'].get('observed_record',{}).get('evidence_conflict')),'original_phase':o['raw'].get('observed_record',{}).get('original_phase')} for o in ap['observations'] if 'event' in o['fields']]}
 Path(output).write_text(json.dumps(fixture,ensure_ascii=False,indent=2)+'\n');return fixture
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',required=True);p.add_argument('--previous-site',required=True);p.add_argument('--output',required=True);a=p.parse_args();f=build(a.input,a.previous_site,a.output);print(json.dumps({'expected':f['expected'],'current_cases':len(f['current_case_ids']),'new':len(f['new_case_ids']),'updated':len(f['updated_case_ids'])}))
