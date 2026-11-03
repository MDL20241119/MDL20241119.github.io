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
for phrase in ['残り14％を','観光バス','調査全体','962回答','海外居住者','200','国籍ではなく','調査実施時期は未確認','現在の湯布院だけの観光バス台数','MDLの分析・提案']:
 assert phrase in s,phrase
assert s.count('class="donut-value"')==7
assert 'stroke-dasharray="51 100"' in s
assert '60<span>〜</span>100' in s
assert len(json.loads((P/'data.json').read_text())['historicalBusRecords'])==3
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
home=R/'index.html'
assert home.read_text().count('id="yufuin-mobility-feature"')==1
assert home.read_text().index('id="data-design"')<home.read_text().index('id="yufuin-mobility-feature"')<home.read_text().index('id="challenge-support"')
assert 'id="mobility-analysis"' not in (P.parent/'index.html').read_text()
assert 'モビリティ分析｜湯布院' not in (P.parent/'navigation.py').read_text()
assert not (P.parent/'mobility_feature.py').exists()
print('PASS: three independent datasets, 8 licensed image records, assets, anchors, source caveats, reduced motion, modal focus and MDL homepage entry and historical bus evidence.')


# Additional field evidence is available in the HTML as well as in its source files.
field=json.loads((P/'downloads/Yufuin-Field-Evidence.json').read_text())
records=field['records']
assert len(records)==56
assert sorted(i for i in page.ids if i.startswith('fd-record-'))==sorted('fd-record-'+r['id'] for r in records)
for anchor in ('stay-patterns','nolc-data','connections','field-data','originals'):
 assert anchor in page.ids
assert not re.search(r'__[A-Z_]+__',s)
months=field['stay']['occupancy']['months']
assert [m['month'] for m in months]==list(range(1,13))
assert min(m['occupancy_percent'] for m in months)==41.7 and max(m['occupancy_percent'] for m in months)==76.0
assert all(m['source_url'] in page.links for m in months)
connections=field['connections']
assert [len(r['trips']) for r in connections['routes']]==[5,14]
assert len(connections['shuttles'])==5 and connections['baggage']['eligible_properties']==93
od=json.loads((P/'downloads'/field['od_file']).read_text())
matrix=od['matrix']
assert len(od['stops'])==len(matrix)==17 and all(len(row)==17 for row in matrix)
assert [sum(row) for row in matrix]==od['origin_totals']
assert [sum(col) for col in zip(*matrix)]==od['destination_totals']
assert sum(od['origin_totals'])==od['total']==141
assert sum(n>0 for row in matrix for n in row)==35
inline=json.loads(re.search(r'<script type="application/json" id="od-matrix">(.+?)</script>',s)[1])
assert inline=={'stops':od['stops'],'matrix':matrix}
assert not any('kitakyushu.lg.jp/files/000803199.pdf' in url for url in page.links)
assert all(phrase in s for phrase in ('2025年度の実績','3.2<small>人／便','30.4万円','2026年の運行案内','20,496人'))
assert not any(phrase in s for phrase in ('3,266人','371.8万円'))
print('PASS: 56 records, monthly occupancy, 19 arrivals, 5 shuttles, 17-stop matrix, source links and corrected municipal indicators.')
