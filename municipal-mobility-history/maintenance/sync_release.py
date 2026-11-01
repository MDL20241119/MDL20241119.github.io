#!/usr/bin/env python3
"""Synchronize cache keys from public data content; no clock/credentials involved."""
import hashlib,json,re
from pathlib import Path

def sync_release(site):
 site=Path(site);data=site/'data';digest=hashlib.sha256()
 for p in sorted([*data.rglob('*.json'),*(site/'assets').glob('*.js'),*(site/'assets').glob('*.css'),site.parent/'mobility-policy-history/assets/history.js']):
  digest.update(str(p.relative_to(site.parent)).encode()+b'\0'+p.read_bytes()+b'\0')
 release=digest.hexdigest()[:20]
 p=data/'bootstrap.js';obj=json.loads(p.read_text().split('=',1)[1].strip().rstrip(';'));obj['release']=release
 updates={p:'window.MOBILITY_RESULTS_SUMMARY='+json.dumps(obj,ensure_ascii=False,separators=(',',':'))+';\n'}
 for p in [site/'index.html',site.parent/'mobility-policy-history/index.html']:
  text=p.read_text()
  text=re.sub(r'\d+案件・\d+自治体の結果と変遷',str(obj['counts']['deep'])+'案件・'+str(obj['counts']['deep_municipalities'])+'自治体の結果と変遷',text)
  text=re.sub(r'(data-deep-count>)\d+案件',lambda m:m[1]+str(obj['counts']['deep'])+'案件',text)
  if p.parent.name=='mobility-policy-history':text=re.sub(r'\d+案件の結果詳査',str(obj['counts']['deep'])+'案件の結果詳査',text)
  for asset,attribute in [('data/bootstrap.js','src'),('assets/results.js','src'),('assets/results.css','href')]+([('assets/history.js','src')] if p.parent.name=='mobility-policy-history' else []):
   pattern=r'('+attribute+r'="[^"]*'+re.escape(asset)+r')(?:\?[^"]*)?(")'
   text,n=re.subn(pattern,lambda m:m[1]+'?v='+release+m[2],text)
   assert n==1,(p,asset,n)
  updates[p]=text
 changed=[]
 for p,text in updates.items():
  if p.read_text()!=text:p.write_text(text);changed.append(str(p.relative_to(site.parent)))
 return {'release':release,'changed':changed,'basis':'sorted public JSON and UI assets paths and bytes; bootstrap excluded; not immutable hosting'}
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--site',default=str(Path(__file__).resolve().parents[1]));a=p.parse_args();print(json.dumps(sync_release(a.site),ensure_ascii=False))
