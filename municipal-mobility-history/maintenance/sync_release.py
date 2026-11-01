#!/usr/bin/env python3
"""Synchronize cache keys from public data content; no clock/credentials involved."""
import hashlib,json,re
from pathlib import Path

def sync_release(site):
 site=Path(site);data=site/'data';digest=hashlib.sha256()
 for p in sorted([*data.rglob('*.json'),*(site/'assets').glob('*.js'),*(site/'assets').glob('*.css')]):
  digest.update(str(p.relative_to(site)).encode()+b'\0'+p.read_bytes()+b'\0')
 release=digest.hexdigest()[:20]
 p=data/'bootstrap.js';obj=json.loads(p.read_text().split('=',1)[1].strip().rstrip(';'));obj['release']=release
 updates={p:'window.MOBILITY_RESULTS_SUMMARY='+json.dumps(obj,ensure_ascii=False,separators=(',',':'))+';\n'}
 for p in [site/'index.html',site.parent/'mobility-policy-history/index.html']:
  text=p.read_text()
  for asset in ['data/bootstrap.js','assets/results.js']:
   pattern=r'(src="[^"]*'+re.escape(asset)+r')(?:\?[^"]*)?(" defer)'
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
