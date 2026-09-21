"""Validate redesigned public pages and their local targets before release."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
from collections import Counter
import json,subprocess
ROOT=Path(__file__).resolve().parents[1]
PAGES=['index.html','mobility-training/index.html','evidence/index.html','danchi-elevator/index.html','danchi-elevator/standards/index.html']
class Page(HTMLParser):
 def __init__(self,s):
  super().__init__();self.tags=[];self.feed(s)
 def handle_starttag(self,t,a):self.tags.append((t,dict(a)))
parsed={f:Page((ROOT/f).read_text()) for f in PAGES}
errors=[]
for name,p in parsed.items():
 ids=[a['id'] for t,a in p.tags if 'id' in a]
 if len(ids)!=len(set(ids)):errors.append(f'{name}: duplicate IDs')
 for tag in ['h1','main']:
  if sum(t==tag for t,a in p.tags)!=1:errors.append(f'{name}: expected one {tag}')
 for tag,a in p.tags:
  if tag=='img' and 'alt' not in a:errors.append(f'{name}: image without alt')
  if a.get('target')=='_blank' and 'noopener' not in a.get('rel',''):errors.append(f'{name}: missing noopener')
  for key in ('href','src'):
   v=a.get(key,'');u=urlsplit(v)
   if not v or v=='#' or u.scheme or u.netloc:continue
   target=ROOT/unquote(u.path.lstrip('/')) if u.path.startswith('/') else (ROOT/name).parent/unquote(u.path)
   if not u.path:target=ROOT/name
   elif u.path.endswith('/'):target=target/'index.html'
   if not target.is_file():errors.append(f'{name}: missing {v}');continue
   if u.fragment and target.suffix=='.html':
    ids2=[a['id'] for t,a in Page(target.read_text()).tags if 'id' in a]
    dynamic = (target == ROOT/'oita-tourism/index.html' and u.fragment in {'access','mobility','compare','data'}) or (target == ROOT/'evidence/index.html' and u.fragment.startswith('source-') and u.fragment[7:] in [s['id'] for s in json.loads((ROOT/'evidence/data.json').read_text()).get('sources',[])])
    if u.fragment not in ids2 and not dynamic:errors.append(f'{name}: missing fragment {v}')
source=(ROOT/'index.html').read_text()
for must in ['社会実装から','750+','35','PARTICIPATIONS','標準アプリ利用料','mobility-training/','danchi-elevator/standards/']:
 if must not in source:errors.append(f'homepage missing {must}')
for path in ROOT.glob('integrations/**/*.pyc'):
 if subprocess.run(['git','check-ignore','-q',str(path)],cwd=ROOT).returncode != 0:errors.append(f'compiled file not excluded from publication: {path.relative_to(ROOT)}')
print(json.dumps({'pages':len(PAGES),'errors':errors},ensure_ascii=False,indent=2))
raise SystemExit(bool(errors))
