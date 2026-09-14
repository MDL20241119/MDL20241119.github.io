#!/usr/bin/env python3
"""Index every named provider in the bundled Fukuoka sources; do not infer contracts.

Positions remain references to the original files. Missing schedules and statistics
are null, never zero. Run with --check to verify reproducibility.
"""
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1] / 'fukuoka-mobility'
hashes = {}


def read(path):
    data = (ROOT / path).read_bytes()
    hashes[path] = hashlib.sha256(data).hexdigest()
    return json.loads(data)


def clean(name):
    return re.sub(r'株式会社|（株）|\(株\)|\s+', '', name)


# Exact source-label aliases only. A commissioning municipality is not reassigned
# to a commercial contractor without source evidence.
ALIASES = {
    'うきは市(うきはバス)': 'うきは市', '芦屋タウンバス': '芦屋町',
    '古賀市公共施設等連絡バスコガバス': '古賀市', '苅田町コミュニティバス': '苅田町',
    '直方市コミュニティバス': '直方市', '遠賀町コミュニティバス': '遠賀町',
    '新宮町コミュニティバスマリンクス': '新宮町', '福岡県添田町（添田町バス）': '添田町',
    '田川市コミュニティバス': '田川市', '宮若市・飯塚市共同運行コミュニティバス': '飯塚市・宮若市',
    '福岡市営渡船': '福岡市', '北九州市営渡船': '北九州市',
}
RAIL_NAMES = {'西日本鉄道': '西鉄電車（西日本鉄道）', '九州旅客鉄道': 'JR九州',
              '西日本旅客鉄道': 'JR西日本', '福岡市': '福岡市地下鉄',
              '北九州高速鉄道': '北九州モノレール'}
bus = read('data/bus-stop-inventory.geojson')
rail = read('data/rail.json')
transport = read('data/map-data.json')
feeds = read('data/gtfs/catalog.json')
analysis = read('data/analysis.json')
station_stats = read('data/station-ridership.json')
finance_stats = read('data/operator-finance.json')
rows = {}


def get(name, mode):
    key = ALIASES.get(clean(name), clean(name))
    if (mode, key) not in rows:
        display = RAIL_NAMES.get(key, key) if mode == 'rail' else key
        if mode == 'bus' and key == '西日本鉄道': display = '西鉄バス（西日本鉄道）'
        if mode == 'bus' and key == '北九州市': display = '北九州市営バス'
        if mode == 'bus' and key == '昭和自動車': display = '昭和バス（昭和自動車）'
        if mode == 'ferry': display += '営渡船' if key.endswith('市') else '営渡船'
        rows[mode, key] = dict(id='op-' + hashlib.sha256((mode + ':' + key).encode()).hexdigest()[:12],
            name=display, sourceNames=[], mode=mode, busIndices=[], stationIndices=[], lineIndices=[],
            feedIds=[], routes=[], timetable=None, realtime=None, ridership=None, costs=None,
            officialUrl=None, officialTimetableUrl=None, missingReason=None)
    row = rows[mode, key]
    if name not in row['sourceNames']: row['sourceNames'].append(name)
    return row


for i, f in enumerate(bus['features']):
    p = f['properties']; row = get(p['P11_002'], 'bus'); row['busIndices'].append(i)
    row['routes'].extend(v for k, v in p.items() if k.startswith('P11_003_'))
for kind, field in [('stations', 'stationIndices'), ('lines', 'lineIndices')]:
    for i, f in enumerate(rail[kind]['features']):
        p = f['properties']; row = get(p['N02_004'], 'rail'); row[field].append(i)
        row['routes'].append(p['N02_003'])

feed_details = []
for f in feeds:
    with zipfile.ZipFile(ROOT / 'data/gtfs' / f['file']) as z:
        paths = {p.rsplit('/', 1)[-1]: p for p in z.namelist()}
        def table(name):
            return list(csv.DictReader(io.StringIO(z.read(paths[name]).decode('utf-8-sig')))) if name in paths else []
        agencies, routes = table('agency.txt'), table('routes.txt')
        for a in agencies:
            own = [r for r in routes if r.get('agency_id') == a.get('agency_id') or (len(agencies) == 1 and not r.get('agency_id'))]
            for mode in sorted({'ferry' if r['route_type'] == '4' else 'rail' if r['route_type'] in ('0','1','2','5','6','7') else 'bus' for r in own}):
                row = get(a['agency_name'], mode)
                if f['id'] not in row['feedIds']: row['feedIds'].append(f['id'])
                row['routes'].extend(r.get('route_long_name') or r.get('route_short_name') or r['route_id'] for r in own)
    source = next(x for x in transport['feeds'] if x['id'] == f['id'])
    feed_details.append({k: source[k] for k in ['id','name','validFrom','validTo','dataStatus','scheduledTrips','sourceUrl','downloadUrl','license','licenseUrl','sha256']})

source_by_id = {f['id']: f for f in feed_details}
for (mode, key), row in rows.items():
    row['routes'] = sorted(set(row['routes']))
    row['gtfsStopCount'] = sum(1 for s in transport['stops'] if transport['feeds'][s['feedIndex']]['id'] in row['feedIds'])
    row['stationCount'] = len({rail['stations']['features'][i]['properties']['N02_005g'] for i in row['stationIndices']})
    current = [source_by_id[i] for i in row['feedIds'] if source_by_id[i]['dataStatus'] == 'current']
    if current:
        row['timetable'] = {'status':'partial', 'feedCount':len(current), 'dates':transport['meta']['dates'],
            'scheduledTrips':[sum(f['scheduledTrips'][d] or 0 for f in current) for d in range(3)],
            'note':'収録した公開ファイルの路線のみ。事業者の全路線・全便の網羅は未確認。'}
        row['status'] = 'timetable'
    elif row['feedIds']:
        row['status'] = 'unusable'
        row['missingReason'] = '取得済みの時刻表は有効期間外または検証エラー。運行本数・経路計算には使いません。'
    else:
        row['status'] = 'location'
        row['missingReason'] = '計算に使える時刻表は未取得。停留所・駅の位置と原典の路線名は反映済み。'
    row['positionDates'] = (['2022年度'] if row['busIndices'] else []) + ([rail['meta']['dataAsOf']] if row['stationIndices'] else [])
    if key.startswith('西鉄バス') or key == '西日本鉄道':
        row['officialUrl'] = 'https://www.nishitetsu.jp/train/rosen/' if mode == 'rail' else 'https://www.nishitetsu.jp/bus/rosen/'
        row['officialTimetableUrl'] = 'https://jik.nishitetsu.jp/'
    if mode == 'rail' and key == '九州旅客鉄道':
        row['officialUrl'] = 'https://www.jrkyushu.co.jp/'
        row['officialTimetableUrl'] = 'https://www.jrkyushu-timetable.jp/'
    if mode == 'rail' and key == '福岡市':
        row['costs'] = {'status':'partial','period':'2024年度','url':'index.html#cost','note':'地下鉄の公表決算。'}
    own_stations = [s for s in station_stats['stations'] if s['operatorId'] == row['id']]
    own_accounts = [a for a in finance_stats['accounts'] if row['id'] in a['operatorIds']]
    row['statisticRecordCount'] = len(own_stations)
    if own_stations:
        row['ridership'] = {'status':'partial','period':'2011〜2024年度','label':'駅別乗降実績',
            'url':'operators.html?operator='+row['id']+'#operator-statistics',
            'available2024':sum(s['observations'][-1]['status']=='available' for s in own_stations),
            'note':'県内の原典収録地点。データなし・他線計上等を区別。日別・個人単位ODは未反映。'}
    if own_accounts:
        years = sorted(set(a['year'] for a in own_accounts))
        period = '・'.join(str(y) for y in years)+'年度'
        scope = '西鉄グループ集計。各社単独の値ではありません。' if mode=='bus' else '事業者・事業区分全体。県外を含み、路線別原価は未反映。'
        row['annualStatistics'] = {'recordIds':[a['id'] for a in own_accounts],'note':scope}
        if not row['costs']:
            row['costs'] = {'status':'partial','period':period,'label':'収支',
                'url':'operators.html?operator='+row['id']+'#operator-statistics','note':scope}
        if not row['ridership']:
            row['ridership'] = {'status':'group','period':period,'label':'グループ輸送実績',
                'url':'operators.html?operator='+row['id']+'#operator-statistics','note':scope}
    if mode == 'bus' and key == '昭和自動車':
        row['officialUrl'] = 'https://www.showa-bus.jp/'
        row['acquisitionSource'] = 'http://opendata.sagabus.info/'
        row['missingReason'] = '福岡路線を含む佐賀側GTFSの追加取得が保留。時刻表は未反映。取得後に福岡県内の対象路線・有効期間・利用条件の検証が必要。'
    if mode == 'bus' and key == '北九州市':
        row['acquisitionSource'] = 'https://www.ptd-hs.jp/'
        row['missingReason'] = 'PTD-HSに2027年2月28日までの時刻表配信を確認。利用登録の審査・APIキー発行が必要。現時点では未取得。'

priority = [
    {'id':'nishitetsu-bus','name':'西鉄バス','operatorIds':[v['id'] for (m,k),v in rows.items() if m=='bus' and (k=='西日本鉄道' or k.startswith('西鉄バス'))]},
    {'id':'nishitetsu-rail','name':'西鉄電車','operatorIds':[rows['rail','西日本鉄道']['id']]},
    {'id':'jr-kyushu','name':'JR九州','operatorIds':[rows['rail','九州旅客鉄道']['id']]},
]
result = {'schemaVersion':1,'checkedAt':'2026-09-14','coverageComplete':False,
    'scope':'国土数値情報の福岡県収録分と、保存した公開GTFSに記載された事業者・公表主体。現行の県内全事業者名簿ではありません。',
    'agencyNote':'自治体・地域交通名は原典の公表主体で表示。委託運行会社を推定して割り当てていません。西鉄の委託路線を含む自治体GTFSがあっても、西鉄全線の時刻表反映には数えません。',
    'missingCategories':[
        {'name':'西鉄バス・西鉄電車・JR九州','status':'公表実績・収支を追加。時刻表・往復計算・遅延情報は未反映','reason':'公開検索画面の閲覧と分析用データの接続は別です。全便の時刻表ファイル、再利用・配信条件、有効期間を確認できていないため、経路・交通空白判定には使いません。停留所別・時間帯別ODと県内路線別原価も未取得。'},
        {'name':'北九州市営バスの時刻表','status':'配信あり・利用登録待ち','reason':'PTD-HSの福岡県一覧で静的データと2027年2月28日の期限を確認。配信元の登録審査、APIキー発行、利用条件の確認が必要。資料・申請先：https://www.ptd-hs.jp/'},
        {'name':'昭和バスの時刻表','status':'追加取得が保留','reason':'福岡・糸島の運行は公式案内で確認。福岡路線を含む佐賀側配布ファイルを取得し、県内路線・有効期間・利用条件を確認する作業が残っています。'},
        {'name':'現行の県内全交通事業者名簿','status':'全件照合は未完了','reason':'2022年度のバス停資料、2025年の鉄道資料、取得GTFSに現れない事業者は個別に列挙できていません。掲載数は県内の事業者総数ではありません。'},
        {'name':'タクシー各社','status':'各社名簿・配車供給は未反映','reason':'公開GTFSに含まれる乗合タクシー路線等のみ。一覧の会社についても通常のタクシー予約可能台数・運行区域は未取得。'},
        {'name':'旅客船・フェリー','status':'公営渡船の一部のみ','reason':'福岡市・宗像市・新宮町の収録GTFSを反映。北九州市営渡船は期限外・検証エラー。その他の会社・航路は網羅していません。'},
        {'name':'高速・貸切・福祉・送迎、航空等','status':'全事業者・全路線は未反映','reason':'県外から乗り入れる事業者を含む現行名簿・時刻表・供給データの照合が未完了。送迎の公表事例は別画面で参考表示。'},
    ],'priorityGroups':priority,'operators':sorted(rows.values(),key=lambda r:(r['mode'],r['name'])),
    'feeds':feed_details,'sourceHashes':hashes,
    'sources':{'bus':{'url':'https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-P11-2022.html','date':'2022年度','license':'CC BY 4.0'},
        'rail':{'url':rail['meta']['sourceUrl'],'date':rail['meta']['dataAsOf'],'license':rail['meta']['license']},
        'licenseUrl':'https://nlftp.mlit.go.jp/ksj/other/agreement_01.html'},
}
encoded = json.dumps(result,ensure_ascii=False,indent=2)+'\n'
target = ROOT / 'data/operators.json'
if '--check' in sys.argv:
    assert target.read_text() == encoded, 'operators.json needs rebuilding'
else:
    target.write_text(encoded)
print(json.dumps({'providers':len(rows),'timetable':sum(r['status']=='timetable' for r in rows.values()),
    'positionOnly':sum(r['status']=='location' for r in rows.values()),'unusable':sum(r['status']=='unusable' for r in rows.values()),
    'busPoints':sum(len(r['busIndices']) for r in rows.values()),'railStations':sum(r['stationCount'] for r in rows.values())},ensure_ascii=False))
