#!/usr/bin/env python3
"""Rebuild the public catalog from bundled evidence. No network or inferred dates.

Run from any directory: python scripts/build-fukuoka-catalog.py [--check]
The generated JSON contains metadata and counts, never a second copy of GIS data.
Unknown source fields stay null. checkedAt is NOT retrievedAt or dataAsOf.
"""
import collections
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / 'fukuoka-mobility'
HASHES = {}


def read(name):
    raw = (ROOT / name).read_bytes()
    HASHES[name] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)


def unique(values):
    return sorted({str(v) for v in values if v is not None and v != ''})


def one(values):
    v = unique(values)
    return v[0] if len(v) == 1 else None


def sources(rows):
    by_url = {}
    for r in rows:
        url = r.get('sourceUrl') or r.get('source_url')
        if url:
            by_url[url] = {'name': r.get('sourceName') or r.get('source') or r.get('provider') or r.get('name') or '原典資料', 'url': url}
    return list(by_url.values())


def record_dates(rows, key):
    return [{'value': v, 'count': sum(str(r.get(key)) == v for r in rows)} for v in unique(r.get(key) for r in rows)]


CATEGORIES = [
    ('population', 'POPULATION', '人口・世帯'),
    ('transport', 'PUBLIC TRANSPORT', 'バス・鉄道・地域交通'),
    ('terrain', 'ROAD / TERRAIN', '道路・歩行・地形'),
    ('healthcare', 'HEALTHCARE', '病院・診療所・薬局'),
    ('welfare', 'WELFARE', '介護・福祉・通いの場'),
    ('shopping', 'SHOPPING', '買物・移動販売'),
    ('education', 'EDUCATION', '学校・保育・学び'),
    ('tourism', 'TOURISM', '観光施設・観光需要'),
    ('safety', 'SAFETY / DISASTER', '交通事故・洪水・災害'),
    ('resources', 'MOBILITY RESOURCES', '送迎・車両・拠点'),
]
datasets = []


def dataset(id, name, category, **kw):
    d = dict(id=id, name=name, category=category, categories=[category], provider=None,
             sourceUrl=None, sourceUrls=[], dataAsOf=None, retrievedAt=None, checkedAt=None,
             sourceUpdatedAt=None, updateFrequency=None, coverage=None, format=None,
             license=None, licenseUrl=None, dataClass=None, status='UNKNOWN', analysisReady='UNKNOWN',
             processing=None, limitations=[], usedFor=[], localFiles=[], records=None,
             recordUnit='件', valueType=None, layerIds=[], scope='未確認')
    d.update(kw)
    d['quality'] = {
        'freshness': {'state': 'UNKNOWN', 'label': '現況との一致は未確認', 'evidence': '基準日・取得日は下記に分離。取得した日が新しくても、現況を保証しません。'},
        'coverage': {'state': 'PARTIAL' if d['records'] is not None else 'UNKNOWN', 'label': '収録範囲に限定' if d['records'] is not None else '未確認', 'evidence': d['coverage'] or '網羅性の検証記録なし'},
        'position': {'state': 'UNKNOWN', 'label': '精度の数値検証なし', 'evidence': d.get('positionNote', '位置精度の検証記録なし。座標があることと、入口に到達できることは別です。')},
        'license': {'state': 'DOCUMENTED' if d['license'] and d['licenseUrl'] else 'UNKNOWN', 'label': '利用条件の記載あり' if d['license'] and d['licenseUrl'] else '要確認', 'evidence': d.get('legalNote') or '個別の原典条件・第三者権利を確認してください。'},
        'analysis': {'state': d['analysisReady'], 'label': {'READY': '指定用途で利用中', 'PARTIAL': '用途・条件に制約', 'NOT_READY': '未実装', 'UNKNOWN': '未確認'}[d['analysisReady']], 'evidence': ' / '.join(x['label'] for x in d['usedFor']) or '分析への接続を確認していません。'}
    }
    datasets.append(d)
    return d


def usage(label, url):
    return {'label': label, 'url': url}


gtfs = read('data/gtfs/catalog.json')
transport = read('data/map-data.json')
places = read('access/destinations.json') + read('access/shopping.json')
resources = read('gaps/resources.json')
geo = read('gaps/data/sources.json')
boundaries = read('gaps/data/municipalities.geojson')
analysis = read('data/analysis.json')
municipalities = [f['properties'] for f in boundaries['features']]

for f in gtfs:
    usable = f.get('current') and f.get('analysisReady')
    meta = next((m for m in transport['feeds'] if m['sha256'] == f['sha256']), None)
    if not meta:
        raise ValueError('GTFS and map metadata disagree: ' + f['file'])
    i = transport['feeds'].index(meta)
    local = 'data/gtfs/' + f['file']
    if hashlib.sha256((ROOT / local).read_bytes()).hexdigest() != f['sha256']:
        raise ValueError('GTFS hash mismatch: ' + local)
    HASHES[local] = f['sha256']
    d = dataset('gtfs-' + meta['id'], f['name'] + ' GTFS', 'transport',
        provider=f['provider'], sourceUrl=f['catalog'], sourceUrls=[{'name': f['name'], 'url': f['source']}],
        retrievedAt=f.get('retrieved'), license=f.get('license'), licenseUrl=f.get('licenseUrl'),
        licenseCheckedAt=f.get('licenseCheckedAt'), dataClass='OPEN', status='USED' if usable else 'PARTIAL', analysisReady='PARTIAL',
        coverage='この配布GTFSの対象路線。県外区間を含み、県内全交通を網羅しません。',
        format='GTFS ZIP → JSON', processing=f.get('processing'), sha256=f['sha256'],
        validFrom=meta.get('validFrom'), validTo=meta.get('validTo'),
        validityNote='配信データの有効期間。データ作成日・現況確認日ではありません。',
        records=sum(s['feedIndex'] == i for s in transport['stops']), recordUnit='停留所ID',
        shapeCount=sum(s['feedIndex'] == i for s in transport['shapes']),
        valueType='時刻表（予定値）', layerIds=['bus-stops', 'bus-routes'],
        usedFor=[usage('バス停・路線・運行頻度', 'index.html#map'), usage('選択時：目的地への往復', 'accessibility.html'), usage('選択時：交通空白候補', 'transport-gaps.html'), usage('時刻表編集・シナリオ比較', 'lab.html#design')] if usable else [usage('過去の停留所位置のみ（経路・便数計算から除外）', 'index.html#map')],
        limitations=([] if usable else ['このスナップショットは有効期間外または構造エラーのため、経路・便数・交通空白の計算から除外しています。原典と過去の停留所位置のみ保存。'])+['リアルタイム遅延・満員情報は含みません。', '停留所は事業者別のID数。同名・同座標でも別のIDを維持しています。', '未収録交通・鉄道・タクシー・施設送迎はこの時刻表に含みません。', '原GTFSの線形のみ表示。欠けた区間の線形を創作しません。', '分析日と選択した事業者により利用範囲が変わります。'],
        localFiles=[local, 'data/gtfs/catalog.json', 'data/map-data.json'], scope='バス時刻表')

place_groups = collections.defaultdict(list)
for p in places:
    place_groups[p['source']].append(p)
for source, rows in place_groups.items():
    shopping = rows[0]['category'] == 'shopping'
    hospital = rows[0]['category'] == 'hospital'
    id = 'dest-shopping' if shopping else 'dest-hospitals' if source.startswith('厚生労働省') else 'dest-public-' + hashlib.sha256(source.encode()).hexdigest()[:8]
    cats = ['shopping'] if shopping else ['healthcare'] if hospital else ['resources']
    if not shopping and not hospital:
        if any(r['category'] == 'school' for r in rows): cats.append('education')
        if any(r['category'] == 'clinic' for r in rows): cats.append('healthcare')
    d = dataset(id, '買物の目的地（公式案内から収録）' if shopping else source, cats[0], categories=cats,
        provider=source, sourceUrl=one(r.get('sourceUrl') for r in rows), sourceUrls=sources(rows),
        dataAsOf=one(r.get('dataAsOf') for r in rows), retrievedAt=one(r.get('retrievedAt') for r in rows),
        checkedAt=one(r.get('checkedAt') for r in rows), sourceUpdatedAt=one(r.get('sourceUpdatedAt') for r in rows),
        license=one(r.get('license') for r in rows), licenseUrl=one(r.get('licenseUrl') for r in rows),
        dataClass=None if shopping else 'OPEN', status='PARTIAL', analysisReady='PARTIAL',
        coverage=' / '.join(unique(r['city'] for r in rows)) + '。所在地の収録。全施設・当日の利用可否は未検証。',
        format='公開案内 → JSON' if shopping else '公開CSV → JSON',
        processing='公開資料から福岡県内の対象施設と所在地を抜粋。目的別に分類しJSONに整形。',
        limitations=unique([r.get('dataNote') for r in rows] + ['受付時間・当日の利用資格・入口までの歩行経路は未確認。', '収録なしは施設なしを意味しません。'] + (['公式案内の事実情報。包括的なオープンライセンスは未確認。', '公式地図の中心などによる概略位置を含みます。'] if shopping else [])),
        records=len(rows), recordUnit='施設', valueType='公表施設情報（現況は未確認）',
        recordIds=[r['id'] for r in rows],
        usedFor=[usage('目的地の表示・選択した施設への往復', 'accessibility.html'), usage('選択時：交通空白の往復条件', 'transport-gaps.html')],
        localFiles=['access/shopping.json'] if shopping else ['access/destinations.json'], layerIds=unique({'hospital':'hospitals','clinic':'clinics','school':'schools','shopping':'shops','civic':'civic','library':'civic'}[r['category']] for r in rows),
        scope='目的地', positionNote='報告された施設所在地、または公式地図の概略位置。入口・現地精度は未確認。')

b = geo['boundary']
dataset('geo-boundaries', b['title'], 'terrain', provider=b['provider'], sourceUrl=b['url'], dataAsOf=b.get('asOf'), retrievedAt=b.get('retrievedAt'),
    license=b['license'], licenseUrl=b['licenseUrl'], dataClass='OPEN', status='USED', analysisReady='PARTIAL',
    format='GeoJSON', coverage='福岡県の行政区域。居住地の範囲ではありません。', processing=b['processing'],
    records=len(municipalities), recordUnit='市町村', valueType='行政区域', limitations=[b['note'], b['legalNote']], legalNote=b['legalNote'],
    positionNote='表示用に20m許容幅で簡略化。境界確定・測量用途には使えません。', localFiles=['gaps/data/sources.json','gaps/data/municipalities.geojson'],
    usedFor=[usage('区域の切り出し・地図表示', 'transport-gaps.html')], layerIds=['boundaries'], scope='行政区域')

mesh_counts = {}
for m in municipalities:
    meshes = read('gaps/data/' + m['code'] + '-500.geojson')['features']
    # Both resolutions are actual analysis inputs; hash both, without summing them together.
    read('gaps/data/' + m['code'] + '-1000.geojson')
    props = [f['properties'] for f in meshes]
    mesh_counts[m['code']] = {'total': len(props), 'knownPopulation': sum(isinstance(p.get('population2020'), (int,float)) for p in props), 'populated':sum(p.get('populated2020') is True for p in props)}
p = geo['population']
dataset('population-2020', p['title'], 'population', provider=p['provider'], sourceUrl=p['url'],
    dataAsOf=str(p['baselineYear']), retrievedAt=p.get('retrievedAt'), creationFiscalYear=p['creationFiscalYear'],
    license=p['license'], licenseUrl=p['licenseUrl'], dataClass='OPEN', status='PARTIAL', analysisReady='PARTIAL',
    format='GeoJSON', coverage='各自治体の約500m四方の区域。境界またぎ・収録外等は人口未集計のまま保持。',
    processing=p['attribution'] + '。行政界で切り抜いた区域に対応。約1km版は集計値。',
    limitations=p['limitations'], records=sum(x['knownPopulation'] for x in mesh_counts.values()), recordUnit='人口値あり区域（500m版）',
    valueType=p['valueLabel'] + '・調整値（現在人口・将来推計値ではない）',
    localFiles=['gaps/data/sources.json'] + ['gaps/data/' + m['code'] + '-500.geojson' for m in municipalities],
    usedFor=[usage('人口のある区域への絞り込み・人口参考表示', 'transport-gaps.html')], layerIds=['population'], scope='人口',
    positionNote='地域を約500m四方に区切った統計。住民一人ひとりの住所や位置は表しません。')

resource_names={'medical':'病院送迎','school':'学校・大学・教習所の送迎','welfare':'福祉・介護の移動支援','commercial':'買物・企業の送迎','tourism':'観光施設・ホテルの送迎','community':'地域交通の資源'}
resource_cats={'medical':'healthcare','school':'education','welfare':'welfare','commercial':'shopping','tourism':'tourism','community':'transport'}
for kind, name in resource_names.items():
    rows=[r for r in resources if r['category']==kind]
    if not rows: continue
    dataset('resource-'+kind, name+'（公開事例）', 'resources', categories=['resources',resource_cats[kind]],
        provider=' / '.join(unique(r.get('provider') for r in rows)), sourceUrl=one(r.get('sourceUrl') for r in rows), sourceUrls=sources(rows),
        dataAsOf=one(r.get('dataAsOf') for r in rows) if all(r.get('dataAsOf') for r in rows) else None,
        dataDates=record_dates(rows,'dataAsOf'), checkedAt=one(r.get('checkedAt') for r in rows),
        status='PARTIAL', analysisReady='PARTIAL', format='公式案内 → JSON',
        coverage=' / '.join(unique(r['city'] for r in rows))+'の公開事例。車両数・送迎区域の網羅ではありません。',
        processing='運営者の公開案内から利用資格・予約条件等を整理。位置が確認できた拠点のみ地図表示。',
        limitations=['公開ページの内容整理であり、MDLによる現地・事業者への運行確認ではありません。', '一般開放・車両共用・空き時間・空き運転手は未確認。', '位置は施設・乗降拠点等であり、送迎車両の現在位置・運行区域ではありません。', '包括的なオープンライセンスは未確認。', '休止事例を含む場合は個別に表示します。'],
        records=len(rows), recordUnit='事例', locatedRecords=sum(isinstance(r.get('lat'),(int,float)) and isinstance(r.get('lon'),(int,float)) for r in rows),
        recordIds=[r['id'] for r in rows], valueType='公開案内（現況・共用可否は未確認）',
        usedFor=[usage('地域の輸送資源の表示（経路判定には未使用）','transport-gaps.html#resources')],
        localFiles=['gaps/resources.json'], layerIds=['shuttles'], scope='移動資源')

observed = {
 'route_actuals':('福岡市地下鉄・路線別乗車実績','index.html#ridership','年度平均乗車人員','福岡市交通局'),
 'stop_actuals':('福岡市地下鉄・駅別乗車実績','index.html#ridership','年度平均乗車人員','福岡市交通局'),
 'subway_history':('福岡市地下鉄・年度別利用実績','index.html#forecast','年度平均乗車人員','福岡市交通局'),
 'finance':('福岡市地下鉄・公表収入費用','index.html#cost','公表損益計算書','福岡市交通局'),
 'commute_od':('福岡市・国勢調査 通勤通学OD','index.html#od','公表調査値／人','総務省統計局・福岡市'),
 'pt_modes':('北部九州圏PT・代表交通手段','index.html#od','公表図の構成比・丸め値','福岡県'),
 'municipal_population':('福岡県60市町村・国勢調査人口','data-catalog.html','公表調査値／人','福岡県・総務省統計局'),
}
for key,(name,url,kind,provider) in observed.items():
    rows=analysis.get(key,[])
    if not rows:continue
    dates=unique(r.get('year') or r.get('source_date') or r.get('observation_date') or r.get('period') or r.get('subsidy_fiscal_year_jp') or r.get('bus_year') for r in rows)
    period=None
    period=' / '.join(dates) or None
    dataset('analysis-'+key, name, 'transport', provider=provider, sourceUrl=one(r.get('source_url') for r in rows), sourceUrls=sources(rows),
        dataAsOf=period, status='PARTIAL', analysisReady='PARTIAL', format='公表PDF・表計算 → JSON',
        coverage='原典の対象路線・調査区域・期間に限定。地域全体の最新実績ではありません。',
        processing='公表表の数値を抜粋・整理。日別・年度別・補助年度等の元の集計単位を維持。',
        limitations=['原典ごとに集計範囲・時点・単位が異なります。合計値を現行GTFSの各便へ自動配分しません。', '非公表・欠測はゼロではありません。', '個票・匿名ICカード履歴や事業者の非公開費用は収録していません。', '抜粋数値の紹介。元報告書全体の再利用許諾ではありません。'],
        records=len(rows), recordUnit='公表表の行', valueType=kind,
        usedFor=[usage('公表実績・試算の紹介',url)], localFiles=['data/analysis.json'],
        jsonPointer='/'+key, scope='公表実績・過去の試算')

dataset('analysis-derived','需要シナリオ・条件付きB/Cの派生計算','transport',provider='モビリティデザインラボ',
    status='USED',analysisReady='PARTIAL',format='JSON・ブラウザー計算',dataAsOf=None,
    calculatedAt=analysis.get('forecast',{}).get('calculated_on'),valueType='条件付き推計・シナリオ（実測・検証済み予測ではない）',
    coverage='ユーザーが設定する対象・仮定に限る。',processing='公表実績の時系列と入力仮定から計算。B/Cと運行収支は別指標。',
    limitations=['供給変更による需要増の因果関係は未検証。', '便益・費用の対象範囲が限定された部分B/C。公式事業評価の代用ではありません。'],
    localFiles=['data/analysis.json','calculations.js','lab/models.mjs'],
    usedFor=[usage('需要シナリオ','index.html#forecast'),usage('条件付きB/C','index.html#bc'),usage('Scenario Lab','lab.html#economics')],scope='派生計算')

rail=read('data/rail.json')
dataset('rail-geography','福岡県内の鉄道駅・線路位置','transport',provider='国土交通省',sourceUrl=rail['meta']['sourceUrl'],dataAsOf=rail['meta']['dataAsOf'],retrievedAt=rail['meta']['retrievedAt'],license='CC BY 4.0',licenseUrl=rail['meta']['licenseUrl'],dataClass='OPEN',status='PARTIAL',analysisReady='PARTIAL',format='GeoJSON',records=len(rail['stations']['features']),recordUnit='駅施設線分',coverage='福岡県行政界で切り抜いた鉄道施設',limitations=[rail['meta']['note']],localFiles=['data/rail.json'],layerIds=['rail'],scope='鉄道位置')
bus_inventory=read('data/bus-stop-inventory.geojson')
dataset('bus-inventory','福岡県バス停留所・2022年位置資料','transport',provider='国土交通省',sourceUrl='https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-P11-2022.html',dataAsOf='2022年度',retrievedAt='2026-09-14',license='CC BY 4.0',licenseUrl='https://nlftp.mlit.go.jp/ksj/other/agreement_01.html',dataClass='OPEN',status='PARTIAL',analysisReady='PARTIAL',format='GeoJSON',records=len(bus_inventory['features']),recordUnit='停留所位置',coverage='福岡県の収録分',limitations=['過去の位置資料。現在の運行有無・本数は判断しない。時刻表計算とは別。'],localFiles=['data/bus-stop-inventory.geojson'],layerIds=['bus-inventory'],scope='バス停位置資料')

operators=read('data/operators.json')
dataset('operator-coverage','県内交通事業者・公表主体の反映状況','transport',provider='各原典をモビリティデザインラボが集約',
    sourceUrl=rail['meta']['sourceUrl'],sourceUrls=[{'name':'国土数値情報 バス停留所','url':operators['sources']['bus']['url']},{'name':'国土数値情報 鉄道','url':operators['sources']['rail']['url']}],
    checkedAt=operators['checkedAt'],dataAsOf=None,dataClass='VERIFIED',status='PARTIAL',analysisReady='PARTIAL',format='JSON・画面からCSV保存',
    records=len(operators['operators']),recordUnit='事業者・公表主体（県内総数ではない）',coverage=operators['scope'],
    processing='原典の事業者名とGTFS agencyを集約。位置を索引で参照し、時刻表・実績・費用・リアルタイムの反映状況を明示。',
    limitations=[operators['agencyNote'],'県内全事業者の網羅は未完了。西鉄バス・西鉄電車・JR九州の公表実績・収支は反映。時刻表・往復計算・リアルタイムは未反映。'],
    usedFor=[usage('事業者別の位置と反映・未反映','operators.html')],localFiles=['data/operators.json'],scope='県内全事業者のデータ反映は未完了')

station_stats=read('data/station-ridership.json')
read(station_stats['source']['localFile'])
ss=station_stats['source']
dataset('station-ridership','福岡県内9事業者・駅別乗降客数（2011〜2024年度）','transport',provider='国土交通省 国土数値情報',
    sourceUrl=ss['url'],retrievedAt='2026-09-14',checkedAt=station_stats['checkedAt'],dataAsOf='2011〜2024年度',
    dataClass='OPEN',status='USED',analysisReady='PARTIAL',format='GeoJSON → JSON・画面からCSV保存',
    license=ss['license'],licenseUrl=ss['licenseUrl'],records=len(station_stats['stations']),recordUnit='駅・路線レコード',
    coverage=station_stats['scope'],processing='福岡県の市町村境界と交差する地点を抽出。年度別のデータ有無・他線計上コードを維持。',
    limitations=station_stats['notes'],valueType=ss['unit'],
    usedFor=[usage('駅別実績・年度切替・前年比参考・全年度CSV','operators.html#operator-statistics')],
    localFiles=['data/station-ridership.json',ss['localFile']],scope='県内地点・駅別公表実績')

finance_stats=read('data/operator-finance.json')
finance_facts=read(finance_stats['sourceFacts'])
dataset('operator-finance','9鉄道事業者と西鉄グループ・年間輸送量と収支','transport',provider='国土交通省・西日本鉄道・JR九州',
    sourceUrl=finance_facts['mlitSource']['url'],sourceUrls=sources(finance_stats['accounts']),
    retrievedAt='2026-09-14',checkedAt=finance_stats['checkedAt'],dataAsOf='2023〜2025年度（資料ごと）',
    dataClass='VERIFIED',status='USED',analysisReady='PARTIAL',format='公式資料の数値 → JSON・画面からCSV保存',
    records=len(finance_stats['accounts']),recordUnit='年度・事業区分',
    coverage='2023年度は県内9鉄道事業者の事業全体。2024・2025年度は西鉄の鉄道・バス事業、JR九州単体鉄道事業。県外を含む。',
    processing='原表セル・単位・年度・集計範囲を保存。営業収益・利益から算出した費用は公表費用と区別。',
    limitations=finance_stats['notes'],valueType='年度実績・公表値、一部費用は算出値',
    usedFor=[usage('年間輸送量・収支・営業利益率・CSV','operators.html#operator-statistics')],
    localFiles=['data/operator-finance.json',finance_stats['sourceFacts']],scope='県外を含む事業全体の実績')

missing = [
    ('elderly','高齢者人口','population','2020年の高齢者人口は既存抽出データに含まれません。将来推計で補いません。'),
    ('rail-timetable','鉄道時刻表','transport','鉄道を含む往復判定は未実装。'),
    ('taxi','タクシーの供給・予約可能台数','transport','予約可能台数・現時点の供給状況は未収録。'),
    ('roads','歩行道路・歩道段差','terrain','現在の徒歩計算は直線距離に補正係数を掛けた概算です。'),
    ('elevation','標高・傾斜','terrain','実際の坂道・勾配を計算には反映していません。'),
    ('pharmacies','薬局の所在地・営業時間','healthcare','薬局の一覧は未収録。'),
    ('welfare','福祉施設・通いの場の一覧','welfare','移動支援事例の収録と、福祉施設・通いの場の網羅は別です。'),
    ('mobile-shopping','移動販売の運行日・区域','shopping','店舗の所在地や買物送迎と、移動販売の運行情報は別です。'),
    ('childcare','保育施設・学校の網羅的な一覧','education','学校は自治体公表データの一部のみ。'),
    ('tourism','観光施設の網羅的な一覧・時間帯別の観光需要','tourism','施設の網羅的な一覧、実測OD・時間帯別需要は未収録。'),
    ('flood','洪水想定区域・交通事故','safety','洪水時や災害時に通行できるかの判定は未実装。'),
    ('vehicles','送迎の共用可否・車両・運転手','resources','公開事例から車両の空き時間や一般住民への開放を推定しません。'),
]
for id,name,category,note in missing:
    dataset('planned-'+id,name,category,status='PLANNED',analysisReady='NOT_READY',limitations=[note],scope='今後の収録候補',coverage='未収録。提供元・利用条件・収録範囲の確認が必要。')

# Point-in-polygon uses original coordinate order (GeoJSON lon,lat), including holes.
def in_ring(x,y,ring):
    inside=False
    for a,b in zip(ring,ring[1:]+ring[:1]):
        if (a[1]>y)!=(b[1]>y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:inside=not inside
    return inside


def shape_data(f):
    g=f['geometry'];polys=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
    return [(min(a[0] for a in p[0]),min(a[1] for a in p[0]),max(a[0] for a in p[0]),max(a[1] for a in p[0]),p) for p in polys]


shapes={f['properties']['code']:shape_data(f) for f in boundaries['features']}
def inside_city(x,y,code):
    return any(a<=x<=c and b<=y<=d and in_ring(x,y,p[0]) and not any(in_ring(x,y,h) for h in p[1:]) for a,b,c,d,p in shapes[code])


gap_columns=[(i,j) for i,_,j in CATEGORIES]
service_columns=[('bus','バス'),('rail','鉄道'),('taxi','タクシー供給'),('medical','病院送迎'),('commercial','買物・企業送迎'),('school','学校等送迎'),('welfare-shuttle','福祉送迎')]
gap_rows=[]
for m in municipalities:
    code=m['code'];city_places=[p for p in places if p.get('municipalityCode')==code or p['city']==m['name']]
    city_res=[r for r in resources if r['city']==m['name']]
    stop_count=sum(inside_city(s['lon'],s['lat'],code) for s in transport['stops'])
    counts={
        'population':(mesh_counts[code]['knownPopulation'],'人口値を持つ500m区域','population-2020'),
        'transport':(stop_count,'行政界内の収録バス停ID',None),
        'healthcare':(sum(p['category'] in ['hospital','clinic'] for p in city_places),'病院・診療所の施設',None),
        'shopping':(sum(p['category']=='shopping' for p in city_places),'買物の施設','dest-shopping'),
        'education':(sum(p['category']=='school' for p in city_places),'学校の施設',None),
        'resources':(len(city_res),'送迎・移動支援事例',None),
        'tourism':(0,'観光の指標',None),
        'bus':(stop_count,'行政界内の収録バス停ID',None),
    }
    for k in ['medical','commercial','school']:
        counts[k]=(sum(r['category']==k for r in city_res),'送迎・移動支援事例','resource-'+k)
    counts['welfare-shuttle']=(sum(r['category']=='welfare' for r in city_res),'福祉送迎事例','resource-welfare')
    cells={}
    for k,label in gap_columns+service_columns:
        n,unit,ds=counts.get(k,(0,'収録件数',None))
        # Available proves complete coverage only when explicitly verified; there is no such evidence today.
        # Zero bundled records is NOT proof of no service, nor of no external open dataset.
        state='PARTIAL' if n else 'NOT_AVAILABLE'
        evidence=(f'{n} {unit}を既存ファイル内で確認。カテゴリ全体の網羅性は未確認。' if n else '対応するレイヤー／この自治体のレコードを既存ファイルに収録していません。外部データや実際のサービスの有無は未確認。')
        if k=='terrain':evidence='行政界のみ収録。歩行道路・標高・傾斜は未収録。'
        if k=='tourism':evidence=f'{n}指標を観光専用ページに収録。対象年・系列を保持。観光施設の網羅的な一覧・時間帯別需要は未収録。' if n else 'この市町の観光指標は未収録。観光施設や需要がないことを意味しません。'
        if k=='welfare':evidence='福祉施設・通いの場の一覧は未収録。移動支援事例とは区別しています。'
        cells[k]={'status':state,'count':n,'unit':unit,'evidence':evidence,'datasetId':ds}
    gap_rows.append({'code':code,'name':m['name'],'cells':cells,'mesh':mesh_counts[code]})

layer_specs=[
    ('population','人口メッシュ','population',None),('elderly','高齢者人口','population',None),
    ('bus-stops','バス停','transport',len(transport['stops'])),('bus-routes','バス路線','transport',len(transport['shapes'])),
    ('rail','鉄道駅','transport',len(rail['stations']['features'])),('bus-inventory','バス停位置資料・2022年','transport',len(bus_inventory['features'])),('hospitals','病院','healthcare',sum(p['category']=='hospital' for p in places)),
    ('clinics','診療所','healthcare',sum(p['category']=='clinic' for p in places)),('pharmacies','薬局','healthcare',None),
    ('shops','スーパー・買物','shopping',sum(p['category']=='shopping' for p in places)),('welfare','福祉施設','welfare',None),
    ('schools','学校','education',sum(p['category']=='school' for p in places)),('gatherings','通いの場','welfare',None),
    ('civic','公共施設・図書館','resources',sum(p['category'] in ['civic','library'] for p in places)),
    ('shuttles','送迎・移動支援','resources',sum(isinstance(r.get('lat'),(int,float)) and isinstance(r.get('lon'),(int,float)) for r in resources)),
    ('elevation','標高','terrain',None),('flood','洪水想定区域','safety',None),('boundaries','行政区域','terrain',len(municipalities))
]
layers=[{'id':id,'name':name,'category':cat,'available':n is not None or id=='population','count':n,
         'datasetIds':[d['id'] for d in datasets if id in d['layerIds']]} for id,name,cat,n in layer_specs]
history=[]
for date in unique((d.get('retrievedAt') or '')[:10] for d in datasets):
    ids=[d['id'] for d in datasets if (d.get('retrievedAt') or '')[:10]==date]
    history.append({'date':date,'kind':'取得記録','label':'元データに記録された取得日','datasetIds':ids})
# No claim of a past file diff when the previous data snapshot is not available.
history.append({'date':'2026-09-14','kind':'機能追加','label':'DATA CATALOG・収録状況・分析出典の表示を追加','datasetIds':[]})
out={'schemaVersion':1,'title':'福岡県交通空白を見つけて解消を考えるアクセシビリティマップ',
     'generator':'scripts/build-fukuoka-catalog.py','sourceHashes':HASHES,
     'categories':[{'id':i,'number':f'{n+1:02}','name':en,'label':ja} for n,(i,en,ja) in enumerate(CATEGORIES)],
     'datasets':datasets,'municipalities':[{'code':m['code'],'name':m['name']} for m in municipalities],
     'overview':{'destinations':len(places),'resources':len(resources),'locatedResources':sum(l['count'] or 0 for l in layers if l['id']=='shuttles'),
                 'lastRetrieved':max((d.get('retrievedAt') or '')[:10] for d in datasets)},
     'gap':{'columns':[{'id':i,'label':j} for i,j in gap_columns],'serviceColumns':[{'id':i,'label':j} for i,j in service_columns],'rows':gap_rows,
            'method':'既存JSONの施設・事例を自治体コード／明記された市町村名で集計。バス停は表示用N03行政界内の点を集計（境界付近に誤差あり）。0件はこのサイトでの未収録を示し、サービス不存在や外部データ不存在を意味しません。公表事例の所在自治体と送迎区域は別です。'},
     'layers':layers,'history':sorted(history,key=lambda h:h['date'],reverse=True)}
encoded=json.dumps(out,ensure_ascii=False,indent=2)+'\n'
target=ROOT/'data/catalog.json'
if '--check' in sys.argv:
    if not target.exists() or target.read_text()!=encoded:
        sys.exit('Catalog is stale: run python scripts/build-fukuoka-catalog.py')
    print('PASS: catalog reproducible; all source hashes and counts agree.')
else:
    target.write_text(encoded)
    print(f'Generated {len(datasets)} dataset entries, {len(gap_rows)} municipalities, {len(layers)} layer definitions.')
