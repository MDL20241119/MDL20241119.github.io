"""Offline release checks for source separation, local assets and homepage entry."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
from collections import Counter
import json, re, sys
P=Path(__file__).resolve().parent
R=P.parent.parent
class Page(HTMLParser):
 def __init__(self,s):
  super().__init__();self.ids=[];self.links=[];self.photos=[];self.h1=0;self.feed(s)
 def handle_starttag(self,t,a):
  a=dict(a)
  if a.get('id'):self.ids.append(a['id'])
  if t=='h1':self.h1+=1
  for k in ('href','src'):
   if a.get(k):self.links.append(a[k])
  if t=='img' and a.get('src'):self.photos.append(a)
s=(P/'index.html').read_text();page=Page(s)
assert page.h1==1
assert len(page.ids)==len(set(page.ids))
assert len(page.photos)==8
for photo in page.photos:
 assert all(photo.get(k) for k in ('alt','width','height','loading','decoding','srcset'))
for link in page.links:
 u=urlsplit(link)
 if u.scheme or u.netloc:continue
 path=(R/u.path.lstrip('/')) if u.path.startswith('/') else (P/u.path)
 if path.is_dir():path=path/'index.html'
 assert path.is_file(),link
 if u.fragment and (not u.path or path==P/'index.html'):assert u.fragment in page.ids,link
studies=json.loads((P/'data.json').read_text())['studies']
assert len(studies)==3
assert [[v['value'] for v in a['values']] for a in studies]==[[51,21,14],[86.1,8.2,4.3,1.5],[25.5,23.5,20.5,20.5]]
assert studies[2]['multiple']=='複数回答'
for phrase in ['残り14％を','観光バス','調査全体','962回答','海外居住者','200','国籍ではなく','調査実施時期は未確認','この３資料では分かりません','MDLの分析・提案']:
 assert phrase in s,phrase
assert s.count('class="on"')==51
photos=json.loads((P/'photos.json').read_text());assert len(photos)==8
assert len(set(p['source'] for p in photos))==8
for photo in photos:
 assert photo['source'].startswith('https://www.city.yufu.oita.jp/')
 assert all(photo.get(k) for k in ['credit','rights','verified','captured','sourceSha256','changes'])
 for size in ('','-small'):assert (P/'assets'/(photo['id']+size+'.webp')).is_file()
css=(P/'style.css').read_text();js=(P/'app.js').read_text()
for phrase in ['prefers-reduced-motion','focus-visible','@media(max-width:700px)']:
 assert phrase in css,phrase
assert "aria-pressed" in js and "dialog.close()" in js and "opener.focus()" in js
sys.path.insert(0,str(P.parent));import mobility_feature
home=P.parent/'index.html';before=home.read_bytes();mobility_feature.update();assert home.read_bytes()==before,'Homepage insertion must be idempotent'
assert home.read_text().count('id="mobility-analysis"')==1
assert 'yufuin-mobility/' in (P.parent/'navigation.py').read_text()
print('PASS: three independent datasets, 8 licensed image records, assets, anchors, source caveats, reduced motion, modal focus and idempotent homepage entry.')
