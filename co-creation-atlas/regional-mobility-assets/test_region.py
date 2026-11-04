import unittest,json,re,sys,hashlib
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent));from regions import REGIONS
class Parse(HTMLParser):
 def __init__(self):super().__init__();self.ids=[];self.hrefs=[];self.imgs=[];self.scripts=[];self.h1=0
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if 'id'in a:self.ids.append(a['id'])
  if tag=='a' and 'href'in a:self.hrefs.append(a['href'])
  if tag=='img':self.imgs.append(a)
  if tag=='script':self.scripts.append(a.get('src',''))
  if tag=='h1':self.h1+=1
class TestRegions(unittest.TestCase):
 def test_pages(self):
  for slug,d in REGIONS.items():
   with self.subTest(slug=slug):
    p=ROOT/'co-creation-atlas'/f'{slug}-mobility'/'index.html';s=p.read_text();h=Parse();h.feed(s)
    self.assertEqual(h.h1,1);self.assertEqual(len(h.ids),len(set(h.ids)))
    self.assertFalse(any('entry.js' in x for x in h.scripts));self.assertIn('noindex,nofollow,noarchive',s)
    self.assertNotRegex(s,r'(?i)(/workspace/|parent agent|親調査|TODO|undefined|nan%)')
    for x in ['snapshot','mobility','policy','decisions','evidence']:self.assertIn(x,h.ids)
    for im in h.imgs:self.assertTrue(im.get('alt'));self.assertTrue((ROOT/im['src'].lstrip('/')).exists())
    for href in h.hrefs:
     u=urlsplit(href)
     if u.scheme or u.netloc:continue
     if not u.path:target=p
     else:target=(ROOT/u.path.lstrip('/')) if u.path.startswith('/') else (p.parent/unquote(u.path)).resolve()
     if target.is_dir():target=target/'index.html'
     # Root consortium landing page is outside sparse preview; verified on main separately.
     if u.path=='/oita-mirai-mobility-consortium/':continue
     self.assertTrue(target.exists(),str(target))
     if u.fragment and target==p:self.assertIn(u.fragment,h.ids)
    j=json.loads((p.parent/'downloads/evidence.json').read_text());self.assertGreater(len(j['records']),35)
    for r in j['records']:
     for k in ['id','label','value','period','type','definition','source','url','page','caution']:self.assertTrue(str(r[k]),k)
     self.assertTrue(r['url'].startswith('https://'))
    c=json.loads((p.parent/'downloads/coverage.json').read_text());self.assertEqual(len(c['main_topics']),29);self.assertEqual(len(c['field_records']),56)
 def test_hubs_and_preservation(self):
  baseline={'hiji.html': 'd477288e3bda534c95bb2d253812a56ca0aba81aa58fb0acf417117913444802', 'usa.html': 'f6dacf8e5bc71d256e13a8ff7bfd55612570263756f96c3af2e1b3c1c4d772c1', 'kunisaki.html': 'a2eb2ec344039d452379a33eccab1c0fadb78c24a9c6f839b04021779f077260', 'usuki.html': 'b696e814ae3d8c2d3c5926c3a38df02ef45b4d6ffd1f4751d20b5a6a30e84fbe', 'oita.html': '42075004f6d3b02e7de0822fd80c4921a55c206b3bc860070d5c284e89278704'}
  for slug,d in REGIONS.items():
   hub=d.get('hub',slug);s=(ROOT/'oita-mirai-mobility-consortium/dialogue'/hub/'index.html').read_text()
   self.assertIn(f'/co-creation-atlas/{slug}-mobility/',s);self.assertIn('entry.js',s)
   if d['proposal']:
    self.assertIn('../'+d['proposal'],s)
    if baseline:self.assertEqual(hashlib.sha256((ROOT/'oita-mirai-mobility-consortium/dialogue'/d['proposal']).read_bytes()).hexdigest(),baseline[d['proposal']])
   else:self.assertIn('未作成',s)
  index=(ROOT/'oita-mirai-mobility-consortium/dialogue/index.html').read_text()
  for d in REGIONS.values():self.assertIn('href="'+d.get('hub',next(k for k,v in REGIONS.items() if v is d))+'/"',index)
 def test_cautions(self):
  strings={'hiji':['11,839','13,600','WEB','無作為'],'usa':['2023年度','2025年4月','新ビジョン'],'kunisaki':['共同通勤','717,163','717,670','507人'],'usuki':['745','76.8','16.4','2.40'],'kitsuki':['785','758,312','404'],'saganoseki':['代替車両','被災前','途中','大分市内分']}
  for slug,words in strings.items():
   s=(ROOT/'co-creation-atlas'/f'{slug}-mobility/index.html').read_text()
   for word in words:self.assertIn(word,s)
if __name__=='__main__':unittest.main()
