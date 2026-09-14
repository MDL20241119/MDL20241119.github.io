#!/usr/bin/env python3
"""Import every Fukuoka row in MHLW's eight 2026-06-01 public CSVs.

Retain unlocated facilities in the audit and source extract, never fabricate points.
Default rebuild uses the bundled Fukuoka source extract; --raw-dir refreshes it.
"""
import argparse, csv, gzip, hashlib, io, json, re, zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'fukuoka-mobility'
SOURCE='https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iryou/newpage_43373.html'
TERMS='https://www.digital.go.jp/resources/open_data/public_data_license_v1.0'
FILES=[('hospital','01-1_hospital_facility_info'),('clinic','02-1_clinic_facility_info'),('dental','03-1_dental_facility_info'),('maternity','04_maternity_home'),('pharmacy','05_pharmacy')]
HOURS=[('hospital','01-2_hospital_speciality_hours'),('clinic','02-2_clinic_speciality_hours'),('dental','03-2_dental_speciality_hours')]
NAMES={'hospital':'病院','clinic':'診療所','dental':'歯科診療所','maternity':'助産所','pharmacy':'薬局'}
def write(p,obj):
    raw=(json.dumps(obj,ensure_ascii=False,separators=(',',':'),allow_nan=False)+'\n').encode()
    (ROOT/p).write_bytes(gzip.compress(raw,mtime=0) if p.endswith('.gz') else raw)
ap=argparse.ArgumentParser();ap.add_argument('--raw-dir',type=Path);args=ap.parse_args()
source_path=ROOT/'data/sources/medical-fukuoka-20260601.json.gz'
if args.raw_dir:
    sources=[];tables={}
    for kind,stem in FILES+HOURS:
        name=stem+'_20260601.csv.zip';raw=(args.raw_dir/name).read_bytes();z=zipfile.ZipFile(io.BytesIO(raw))
        rows=csv.DictReader(io.StringIO(z.read(z.namelist()[0]).decode('utf-8-sig')))
        # Published IDs start with their prefecture code; hours rows have no prefecture column.
        selected=[{'sourceRow':i,'values':r} for i,r in enumerate(rows,2) if r.get('都道府県コード',r['ID'][:2])=='40']
        tables[stem]=selected
        sources.append(dict(file=name,kind=kind,url='https://www.mhlw.go.jp/content/11121000/'+name,sha256=hashlib.sha256(raw).hexdigest(),fukuokaRows=len(selected)))
    write('data/sources/medical-fukuoka-20260601.json.gz',dict(asOf='2026-06-01',retrievedAt='2026-09-14',sources=sources,tables=tables))
data=json.loads(gzip.decompress(source_path.read_bytes()));tables=data['tables'];sources={s['file'].replace('_20260601.csv.zip',''):s for s in data['sources']}
boundaries=json.loads((ROOT/'gaps/data/municipalities.geojson').read_text())['features'];cities={f['properties']['code']:f['properties']['name'] for f in boundaries}
def city(c):return '40100' if c.startswith('4010') else '40130' if c.startswith('4013') else c
def number(v):
    try:return float(v)
    except (ValueError,TypeError):return None
def weekly(rows,kind):
    out=[]
    for entry in rows:
        r=entry['values'];days={}
        for day in '月火水木金土日祝':
            slots=[]
            if kind in ('hospital','clinic','dental'):
                a,b=r.get(day+'_診療開始時間',''),r.get(day+'_診療終了時間','')
                c,d=r.get(day+'_外来受付開始時間',''),r.get(day+'_外来受付終了時間','')
                if a or b or c or d:slots.append({'care':[a or None,b or None],'reception':[c or None,d or None]})
            else:
                for i in range(1,5):
                    key='開店時間帯' if kind=='pharmacy' else '診療時間帯'
                    a,b=r.get(f'{day}_{key}{i}_開始時間',''),r.get(f'{day}_{key}{i}_終了時間','')
                    c,d=r.get(f'{day}_外来受付時間帯{i}_開始時間',''),r.get(f'{day}_外来受付時間帯{i}_終了時間','')
                    if a or b or c or d:slots.append({'care':[a or None,b or None],'reception':[c or None,d or None]})
            if slots:days[day]=slots
        if days:out.append({'department':r.get('診療科目名') or NAMES[kind],'slot':r.get('診療時間帯'),'days':days,'sourceRow':entry['sourceRow']})
    return out
hour_index={}
for kind,stem in HOURS:
    for entry in tables[stem]:hour_index.setdefault(kind+'-'+entry['values']['ID'],[]).append(entry)
places=[];details={};rejected=[];counts={}
for kind,stem in FILES:
    count=0
    for entry in tables[stem]:
        r=entry['values'];id=kind+'-'+r['ID'];name=r.get('正式名称') or r.get('名称');c=city('40'+r['市区町村コード'].zfill(3));lat=number(r['所在地座標（緯度）']);lon=number(r['所在地座標（経度）'])
        schedules=weekly(hour_index.get(id,[]) if kind in ('hospital','clinic','dental') else [entry],kind)
        details[id]={'municipalityCode':c,'name':name,'category':kind,'schedules':schedules,'asOf':data['asOf'],'sourceUrl':SOURCE,'sourceResourceUrl':sources[stem]['url'],'hoursSourceResourceUrl':sources.get(dict(HOURS).get(kind,''),sources[stem])['url'],
            'exceptionsSource':'data/sources/medical-fukuoka-20260601.json.gz','exceptionCodes':'例外・休診コードは原典のまま保存。通常週の時刻から祝日・個別週の受診可否を推定しません。'}
        if not name or c not in cities or lat is None or lon is None or not(32.7<lat<34.4 and 129.9<lon<131.5):
            rejected.append({'id':id,'name':name,'address':r.get('所在地'),'category':kind,'sourceRow':entry['sourceRow'],'sourceUrl':sources[stem]['url'],'reason':'原典座標・市町村コードが未収録または県周辺の範囲外'});continue
        places.append(dict(id=id,name=name,category=kind,city=cities[c],municipalityCode=c,lat=lat,lon=lon,address=r['所在地'],url=r.get('案内用ホームページアドレス') or r.get('薬局のホームページアドレス') or None,source='厚生労働省 医療情報ネット',sourceUrl=SOURCE,sourceResourceUrl=sources[stem]['url'],sourceRow=entry['sourceRow'],dataAsOf=data['asOf'],retrievedAt=data['retrievedAt'],license='公共データ利用規約 第1.0版（PDL1.0）',licenseUrl=TERMS,openingHours='公表された診療科別・曜日別時刻あり' if schedules else None,medicalHoursId=id,medicalHoursFile='access/medical-hours/'+c+'.json.gz',wheelchairAccess=None,dataNote='医療機関の報告位置・通常週の診療時刻。臨時休診・受入可否・入口は個別確認。'))
        count+=1
    counts[kind]={'sourceRows':len(tables[stem]),'located':count,'unlocated':len(tables[stem])-count}
# Replace the previous MHLW snapshot, retaining other source identities and existing user links.
existing=json.loads((ROOT/'access/destinations.json').read_text());existing=[p for p in existing if p.get('source')!='厚生労働省 医療情報ネット']
write('access/destinations.json',places+existing)
(ROOT/'access/medical-hours').mkdir(exist_ok=True)
for c in sorted({f['municipalityCode'] for f in details.values()}):
    write('access/medical-hours/'+c+'.json.gz',dict(meta=dict(asOf=data['asOf'],retrievedAt=data['retrievedAt'],sourceUrl=SOURCE,license='PDL1.0',licenseUrl=TERMS),facilities={id:f for id,f in details.items() if f['municipalityCode']==c}))
write('data/medical-audit.json',dict(asOf=data['asOf'],retrievedAt=data['retrievedAt'],counts=counts,located=sum(c['located'] for c in counts.values()),unlocated=rejected,sources=data['sources'],sourceExtractSha256=hashlib.sha256(source_path.read_bytes()).hexdigest(),note='福岡県コード40の全原典行を保存。座標未確認は一覧に残し、地図・経路計算から除外。一般に利用できる医療機関であることを保証しません。'))
print(json.dumps(counts,ensure_ascii=False))
