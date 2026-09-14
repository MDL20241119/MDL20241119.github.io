#!/usr/bin/env python3
"""Publish all named OSM service points, deduplicating only exact nearby matches."""
from pathlib import Path
import gzip,json,re,math,collections
ROOT=Path(__file__).resolve().parents[1]/'fukuoka-mobility'
def read(n):return json.loads(gzip.decompress((ROOT/n).read_bytes()) if n.endswith('.gz') else (ROOT/n).read_bytes())
def name(s):return re.sub(r'\s+|[・･　]', '',s)
def dist(a,b):return math.hypot((a['lat']-b['lat'])*111195,(a['lon']-b['lon'])*92500)
base=read('access/destinations.json')+read('access/shopping.json');original=read('data/osm/facilities.json.gz');lookup=collections.defaultdict(list)
for p in base:lookup[name(p['name'])].append(p)
rows=[];duplicates=[]
for p in original['facilities']:
    candidates=[x for x in lookup[name(p['name'])] if x['municipalityCode']==p['municipalityCode'] and dist(x,p)<100]
    if candidates:duplicates.append({'osmId':p['id'],'matches':[x['id'] for x in candidates]});continue
    row={k:v for k,v in p.items() if k!='tags'};rows.append(row);lookup[name(p['name'])].append(row)
(ROOT/'access/osm-destinations.json.gz').write_bytes(gzip.compress((json.dumps(rows,ensure_ascii=False,separators=(',',':'))+'\n').encode(),mtime=0))
(ROOT/'data/osm/facility-audit.json').write_text(json.dumps({'meta':original['meta'],'sourceRecords':len(original['facilities']),'addedRecords':len(rows),'duplicates':duplicates,'categories':dict(collections.Counter(p['category'] for p in rows))},ensure_ascii=False,separators=(',',':'))+'\n')
print(len(rows),'additional OSM destinations',len(duplicates),'matched duplicates')
