#!/usr/bin/env python3
"""Prepare a cached GTFS manifest with all routes touching the Fukuoka boundary.

The input is the already downloaded Saga 2026-09-07 snapshot, not a live URL.
All stops/calls outside Fukuoka remain in a selected route. Originals stay intact.
"""
import argparse,csv,hashlib,io,json,shutil,zipfile
from pathlib import Path
from shapely.geometry import shape,Point
from shapely.ops import unary_union
from shapely.prepared import prep
ROOT=Path(__file__).resolve().parents[1]/'fukuoka-mobility'
ap=argparse.ArgumentParser();ap.add_argument('cache',type=Path);args=ap.parse_args()
raw=(args.cache/'saga-current.zip').read_bytes();sha=hashlib.sha256(raw).hexdigest()
if sha!='dd522638eb9686e99d6b3350424bdbb6adb2d8efd32397af1c4bd93049072ef2':
    raise ValueError('The source changed: verify its license, agency and validity before accepting a new snapshot.')
z=zipfile.ZipFile(io.BytesIO(raw))
def table(name):return list(csv.DictReader(io.StringIO(z.read(name+'.txt').decode('utf-8-sig'))))
border=prep(unary_union([shape(f['geometry']) for f in json.loads((ROOT/'gaps/data/municipalities.geojson').read_text())['features']]))
inside=set()
for s in table('stops'):
    try:point=Point(float(s['stop_lon']),float(s['stop_lat']))
    except (ValueError,KeyError):continue
    if border.covers(point):inside.add(s['stop_id'])
trips={t['trip_id']:t['route_id'] for t in table('trips')}
routes=sorted({trips[c['trip_id']] for c in table('stop_times') if c['stop_id'] in inside})
item={'name':'佐賀県GTFS・福岡乗入路線（昭和バス・祐徳自動車）','file':'saga-fukuoka__'+sha[:8]+'.zip',
      'source':'http://opendata.sagabus.info/saga-current.zip','catalog':'http://opendata.sagabus.info/',
      'provider':'佐賀県・昭和自動車・祐徳自動車','license':'CC BY 4.0','licenseUrl':'https://creativecommons.org/licenses/by/4.0/deed.ja',
      'sourceUpdatedAt':'2026-09-07','downloaded':True,'bytes':len(raw),'sha256':sha,
      'analysisRouteIds':routes,'fukuokaStopIds':sorted(inside),
      'analysisScope':'福岡県の行政界内に停留所を持つ22路線を抽出。対象路線の県外停留所・全停車時刻・線形を維持。配布ZIPは原典の全路線を保存。'}
manifest=[f for f in json.loads((ROOT/'data/gtfs/catalog.json').read_text()) if not f['file'].startswith('saga-fukuoka')]
folder=args.cache/'gtfs';folder.mkdir(exist_ok=True,parents=True)
for f in manifest:shutil.copyfile(ROOT/'data/gtfs'/f['file'],folder/f['file'])
(folder/item['file']).write_bytes(raw)
(args.cache/'gtfs-manifest.json').write_text(json.dumps(manifest+[item],ensure_ascii=False,indent=2)+'\n')
print(len(routes),'selected routes,',len(inside),'stops in Fukuoka')
