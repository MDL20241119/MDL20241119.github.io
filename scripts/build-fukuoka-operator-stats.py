#!/usr/bin/env python3
"""Prepare source-coded station observations. Never replace missing values with 0.

The bundled GeoJSON is the Fukuoka boundary intersection of MLIT S12-25
(2024 observations). --source-zip regenerates that extract from the original.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1] / 'fukuoka-mobility'
parser = argparse.ArgumentParser()
parser.add_argument('--source-zip', type=Path)
parser.add_argument('--check', action='store_true')
args = parser.parse_args()
source_path = ROOT / 'data/sources/station-ridership-2024.geojson'
if args.source_zip:
    from shapely.geometry import shape
    from shapely.ops import unary_union
    boundaries = json.loads((ROOT / 'gaps/data/municipalities.geojson').read_text())
    area = unary_union([shape(f['geometry']) for f in boundaries['features']])
    with zipfile.ZipFile(args.source_zip) as z:
        member = next(n for n in z.namelist() if '/UTF-8/' in n and n.endswith('.geojson'))
        raw = json.loads(z.read(member).decode('utf-8-sig'))
    raw['features'] = [f for f in raw['features'] if area.intersects(shape(f['geometry']))]
    source_path.parent.mkdir(exist_ok=True)
    source_path.write_text(json.dumps(raw, ensure_ascii=False, separators=(',', ':')) + '\n')

raw = source_path.read_bytes()
features = json.loads(raw)['features']
stations = []
for i, f in enumerate(features):
    p = f['properties']
    observations = []
    for year in range(2011, 2025):
        def field(offset): return p[f'S12_{6 + (year - 2011) * 4 + offset:03}']
        duplicate, presence, note, value = [field(n) for n in range(4)]
        assert duplicate in (1, 2, 3) and presence in (1, 2, 3, 4), (i, year)
        # A duplicate's raw value is retained for audit, but not a second count.
        status = ('no-station' if duplicate == 3 or presence == 4 else 'other-line'
                  if duplicate == 2 else {1:'available', 2:'no-data', 3:'nonpublic'}[presence])
        observations.append(dict(year=year, value=value if status == 'available' else None,
            sourceValue=value, status=status, duplicateCode=duplicate, presenceCode=presence, note=note))
    coords = f['geometry']['coordinates']
    point = coords[len(coords) // 2]
    operator_id = 'op-' + hashlib.sha256(('rail:' + p['S12_002']).encode()).hexdigest()[:12]
    stations.append(dict(id=f's12-{i}', sourceIndex=i, name=p['S12_001'], line=p['S12_003'],
        operator=p['S12_002'], operatorId=operator_id, stationCode=p['S12_001c'], groupCode=p['S12_001g'],
        lon=point[0], lat=point[1], observations=observations))

result = dict(schemaVersion=1, checkedAt='2026-09-14', years=list(range(2011, 2025)),
    source=dict(name='国土数値情報 駅別乗降客数（2024年度版）',
        url='https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-S12-2024.html',
        downloadUrl='https://nlftp.mlit.go.jp/ksj/gml/data/S12/S12-25/S12-25_GML.zip',
        license='CC BY 4.0', licenseUrl='https://nlftp.mlit.go.jp/ksj/other/agreement_01.html',
        localFile='data/sources/station-ridership-2024.geojson', sha256=hashlib.sha256(raw).hexdigest(),
        period='2011〜2024年度', unit='人／日（乗降客数）'),
    scope='福岡県の市町村境界と交差する原典の駅・路線レコード。駅名や事業者間で統合せず、原典の計上先コードを維持。',
    notes=['乗車人数と乗降客数は別指標。各社の算定基準は統一されておらず、会社間の単純比較や合算はできません。',
        '他線計上・データなし・非公表・駅なしを区別。原典の0は0として保持し、欠測を0で補完しません。',
        '2024年度の実績は現在の時刻表や運行状況を示しません。年度をまたぐ駅改廃や計上先の変更に注意してください。',
        'JR九州の原典案内には上位300駅以外は非公表との説明があります。この抽出ファイルの欠測は実際のコードに従い表示します。'],
    stations=stations)
encoded = json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n'
target = ROOT / 'data/station-ridership.json'
if args.check:
    assert target.read_text() == encoded, 'Rebuild station-ridership.json'
else:
    target.write_text(encoded)
print(json.dumps(dict(records=len(stations), operators=len(set(s['operatorId'] for s in stations)),
    available2024=sum(s['observations'][-1]['status'] == 'available' for s in stations)), ensure_ascii=False))
