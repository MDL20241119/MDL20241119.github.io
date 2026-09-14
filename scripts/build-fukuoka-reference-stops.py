#!/usr/bin/env python3
"""Expose source positions with unknown schedules to prevent false gap negatives."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]/'fukuoka-mobility'
read=lambda p:json.loads((ROOT/p).read_text())
bus=read('data/bus-stop-inventory.geojson');rail=read('data/rail.json');stops=[]
for i,f in enumerate(bus['features']):
    lon,lat=f['geometry']['coordinates'];p=f['properties']
    stops.append({'id':'inventory-bus-'+str(i),'name':p['P11_001'],'lat':lat,'lon':lon,'operator':p['P11_002'],'mode':'bus','positionDate':'2022年度'})
seen=set()
for f in rail['stations']['features']:
    p=f['properties'];key=p['N02_005g']
    if key in seen:continue
    seen.add(key);g=f['geometry'];coords=g['coordinates'];points=[p for line in coords for p in line] if g['type']=='MultiLineString' else coords
    lon,lat=points[len(points)//2]
    stops.append({'id':'inventory-rail-'+key,'name':p['N02_005'],'lat':lat,'lon':lon,'operator':p['N02_004'],'mode':'rail','positionDate':'2025-12-31'})
result={'meta':{'sourceHashes':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['data/bus-stop-inventory.geojson','data/rail.json']},'note':'時刻表の網羅未確認を補足する位置資料。過去の位置から現在運行を推定せず、近隣の便数不足・到達不能の断定を保留する。'},'stops':stops}
(ROOT/'gaps/data/reference-stops.json').write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n')
print(len(stops))
