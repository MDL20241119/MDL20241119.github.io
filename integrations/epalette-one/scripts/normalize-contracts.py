"""Requires PyYAML; regenerate the checked-in JSON contracts from pinned original YAML."""
from pathlib import Path
import json, yaml
REMOVE={'description','example','examples','summary','title'}
def strip(x):
 if isinstance(x,dict):return {k:strip(v) for k,v in x.items() if k not in REMOVE}
 if isinstance(x,list):return [strip(v) for v in x]
 return x
for name in ['demand','qr-hub','qr-maas','qr-auth']:
 p=Path('standards/upstream/commmmons')/(name+'.yaml')
 out=Path('lib/integration/contracts')/(name+'.json')
 out.write_text(json.dumps(strip(yaml.safe_load(p.read_text())),ensure_ascii=False,separators=(',',':'))+'\n')
