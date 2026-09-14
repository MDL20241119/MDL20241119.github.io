#!/usr/bin/env python3
"""Normalize factual extracts, retaining period, reporting scope and source cells.

--source-dir reads the downloaded MLIT workbooks, without editing them.
Normal builds only require the bundled source-facts JSON.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'fukuoka-mobility'
parser = argparse.ArgumentParser()
parser.add_argument('--source-dir', type=Path)
parser.add_argument('--check', action='store_true')
args = parser.parse_args()
facts_path = ROOT / 'data/sources/operator-finance-facts.json'
def oid(name, mode='rail'): return 'op-' + hashlib.sha256((mode + ':' + name).encode()).hexdigest()[:12]
if args.source_dir:
    import openpyxl
    finance_file = args.source_dir / 'rail-finance-2023.xlsx'
    passengers_file = args.source_dir / 'rail-passengers-2023.xlsx'
    finance = openpyxl.load_workbook(finance_file, read_only=True, data_only=True).active
    passengers = openpyxl.load_workbook(passengers_file, read_only=True, data_only=True).active
    names = [('西日本鉄道',377,346),('北九州高速鉄道',380,350),('筑豊電気鉄道',382,353),
        ('甘木鉄道',385,352),('皿倉登山鉄道',387,362),('平成筑豊鉄道',391,358),
        ('福岡市',400,366),('西日本旅客鉄道',434,385),('九州旅客鉄道',436,387)]
    extracts=[]
    for name, frow, prow in names:
        assert passengers[f'A{prow}'].value == name
        values={k:finance[f'{col}{frow}'].value for k,col in [('revenue','N'),('expenses','CE'),('profit','CF')]}
        assert all(isinstance(v,(int,float)) for v in values.values())
        assert abs(values['revenue']-values['expenses']-values['profit']) < 0.001
        extracts.append(dict(operator=name,year=2023,valuesThousandYen=values,
            annualPassengersThousand=passengers[f'I{prow}'].value,
            financeCells={k:f'{col}{frow}' for k,col in [('revenue','N'),('expenses','CE'),('profit','CF')]},
            passengersCell=f'I{prow}',financeSheet=finance.title,passengersSheet=passengers.title))
    nishitetsu_url='https://www.nishitetsu.co.jp/ja/ir/library/earnings/main/00/teaserItems2/0110/linkList/04/link/hosokusetumei.pdf'
    jr_url='https://www.jrkyushu.co.jp/company/ir/library/earnings/__icsFiles/afieldfile/2026/05/12/9142.FY2026.4q.material.ja_1.pdf'
    facts=dict(checkedAt='2026-09-14',mlit=extracts,
        mlitSource=dict(title='鉄道統計年報 令和5年度（2023年度）',url='https://www.mlit.go.jp/tetudo/tetudo_tk1_000074.html',
            financeUrl='https://www.mlit.go.jp/tetudo/content/001977420.xlsx',
            passengersUrl='https://www.mlit.go.jp/tetudo/content/001977752.xlsx',
            errataUrl='https://www.mlit.go.jp/tetudo/content/001984232.xlsx',
            financeSha256=hashlib.sha256(finance_file.read_bytes()).hexdigest(),
            passengersSha256=hashlib.sha256(passengers_file.read_bytes()).hexdigest(),
            note='2026年7月9日更新の正誤表を確認。配布中ファイルから抽出。合計行を二重加算せず、事業者の年間輸送人員を採用。'),
        recent=[dict(id=f'nishitetsu-{mode}-{year}',kind='nishitetsu-'+mode,year=year,
            revenueMillionYen=revenue,profitMillionYen=profit,passengersValue=pax,passengersUnit='百万人／年',
            sourceUrl=nishitetsu_url,sourceTitle='西日本鉄道 2025年度決算補足説明資料',sourcePage='印刷3ページ（PDF5ページ）',
            sourceMoneyUnit='百万円',sourcePrecisionMillionYen=1)
            for mode,year,revenue,profit,pax in [('rail',2025,23866,1828,112),('rail',2024,22595,2223,107),
                ('bus',2025,56317,2207,207),('bus',2024,55846,2675,207)]]+
        [dict(id=f'jr-kyushu-{year}',kind='jr-kyushu',year=year,revenueMillionYen=revenue*100,
            profitMillionYen=profit*100,passengersValue=pkm,passengersUnit='百万人キロ／年',
            sourceUrl=jr_url,sourceTitle='JR九州 2026年3月期決算説明会資料',sourcePage='13・23ページ',
            sourceMoneyUnit='億円',sourcePrecisionMillionYen=100)
            for year,revenue,profit,pkm in [(2025,1888,242,8493),(2024,1670,134,8595)]])
    facts_path.write_text(json.dumps(facts,ensure_ascii=False,indent=2)+'\n')

raw=facts_path.read_bytes()
facts=json.loads(raw)
accounts=[]
aliases={'福岡市':'福岡市地下鉄','西日本鉄道':'西鉄電車（西日本鉄道）','九州旅客鉄道':'JR九州','西日本旅客鉄道':'JR西日本','北九州高速鉄道':'北九州モノレール'}
for x in facts['mlit']:
    name=x['operator'];v=x['valuesThousandYen']
    accounts.append(dict(id='mlit-'+oid(name)+'-2023',name=aliases.get(name,name),operatorIds=[oid(name)],year=2023,
        scope='事業者全体の鉄・軌道業。県外区間を含み、福岡県内の金額・人数に分割していません。',
        revenueMillionYen=v['revenue']/1000,expensesMillionYen=v['expenses']/1000,profitMillionYen=v['profit']/1000,
        expensesMethod='公表値（差引営業費合計）',sourceMoneyUnit='千円',sourcePrecisionMillionYen=0.001,
        passengersValue=x['annualPassengersThousand'],passengersUnit='千人／年',
        sourceUrl=facts['mlitSource']['url'],sourceTitle=facts['mlitSource']['title'],
        sourcePage='営業損益 '+','.join(x['financeCells'].values())+'／輸送人員 '+x['passengersCell']))

# Group results must be one record, even when several listed affiliates are selected.
# The highway GTFS also uses the group label 西鉄バス. Relate that label to
# the single group report without allocating the report to an individual company.
bus_keys=['西日本鉄道','西鉄バス','西鉄バス北九州','西鉄バス久留米','西鉄バス大牟田','西鉄バス筑豊','西鉄バス二日市','西鉄バス宗像','西鉄バス佐賀']
for x in facts['recent']:
    bus=x['kind']=='nishitetsu-bus';nishi=x['kind'].startswith('nishitetsu')
    name='西鉄グループ '+('バス事業' if bus else '鉄道事業') if nishi else 'JR九州 単体・鉄道事業'
    ids=[oid(k,'bus') for k in bus_keys] if bus else [oid('西日本鉄道')] if nishi else [oid('九州旅客鉄道')]
    scope=('グループ事業の集計。個別の運行会社や福岡県内だけの実績ではありません。事業内部取引を含む公表値。' if nishi
        else 'JR九州単体の鉄道事業全体。県外区間を含み、福岡県内だけの収支ではありません。')
    accounts.append(dict(x,name=name,operatorIds=ids,scope=scope,
        expensesMillionYen=x['revenueMillionYen']-x['profitMillionYen'],
        expensesMethod='算出値（公表された丸め済み営業収益−営業利益）'))
result=dict(schemaVersion=1,checkedAt=facts['checkedAt'],accounts=accounts,
    sourceFacts='data/sources/operator-finance-facts.json',sourceSha256=hashlib.sha256(raw).hexdigest(),
    notes=['年度は4月〜翌年3月。2026年3月期は2025年度です。',
        '決算の範囲・年度・単位を揃えて読みます。グループ値と各社単体値を合算しません。',
        '営業利益率は営業利益÷営業収益。算出費用は元資料の丸めの影響を受けます。路線別原価・自治体内原価には配賦していません。',
        '年間輸送人員、1日乗降客数、輸送人キロは別の指標です。駅の乗降客数を年間旅客数に変換しません。'])
encoded=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
target=ROOT/'data/operator-finance.json'
if args.check: assert target.read_text()==encoded,'Rebuild operator-finance.json'
else: target.write_text(encoded)
print('Annual operator/segment records:',len(accounts))
