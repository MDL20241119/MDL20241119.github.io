#!/usr/bin/env python3
"""Index official timetable links. These records are not routing schedules.

python scripts/build-fukuoka-timetable-directory.py /path/to/source-cache [--fetch]
The cache is outside the published tree. Publish names, URLs and source hashes,
not copies of operators' timetable documents or executable source pages.
"""
import argparse, hashlib, json, re
from pathlib import Path
from urllib.parse import urljoin, urlencode, urlparse, parse_qs
from lxml import html

ROOT = Path(__file__).resolve().parents[1] / 'fukuoka-mobility'
SOURCES = {
    'nishi-rail': 'https://www.nishitetsu.jp/train/rosen/',
    'nishi-jik': 'https://jik.nishitetsu.jp/',
    'nishi-print': 'https://www.nishitetsu.jp/train/rosen/print/',
    'nishi-text': 'https://jik.nishitetsu.jp/am/',
    'jr-fukuoka': 'https://www.jrkyushu-timetable.jp/jr-k_time/ken_hukuoka.html',
    'jr-saga': 'https://www.jrkyushu-timetable.jp/jr-k_time/ken_saga.html',
    'jr-oita': 'https://www.jrkyushu-timetable.jp/jr-k_time/ken_oita.html',
    'jr-bus': 'https://www.jrkbus.co.jp/rosen/nogata',
    'jr-ieon': 'https://www.jrkbus.co.jp/rosen/nogata-ieon',
}

def norm(s):
    import unicodedata
    return re.sub(r'[\s（）()・]', '', unicodedata.normalize('NFKC', s)).replace('ケ','ヶ')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('cache',type=Path);ap.add_argument('--fetch',action='store_true');args=ap.parse_args()
    args.cache.mkdir(parents=True,exist_ok=True)
    if args.fetch:
        import requests
        for key,url in SOURCES.items():
            r=requests.get(url,timeout=40);r.raise_for_status();r.encoding=r.apparent_encoding
            (args.cache/(key+'.html')).write_text(r.text)
    docs={key:html.fromstring((args.cache/(key+'.html')).read_text()) for key in SOURCES}
    operators=json.loads((ROOT/'data/operators.json').read_text())
    rail=json.loads((ROOT/'data/rail.json').read_text())
    bus=json.loads((ROOT/'data/bus-stop-inventory.geojson').read_text())
    feeds=json.loads((ROOT/'data/gtfs/catalog.json').read_text())
    rows=[]
    def add(id,group,name,mode,url,source,**other):
        rows.append(dict(id=id,group=group,name=name,mode=mode,url=url,sourceUrl=SOURCES.get(source,source),
                         checkedAt='2026-09-15',analysisReady=False,**other))
    stationdata=json.loads(docs['nishi-jik'].xpath('//input[@id="stationdata"]/@value')[0])
    station_by_id={x['id']:x for x in stationdata}
    pdfs={Path(a.get('href')).stem.split('-')[0]:a.get('href') for a in docs['nishi-print'].xpath('//a[contains(@href,".pdf")]')}
    for li in docs['nishi-rail'].xpath('//li[contains(concat(" ",normalize-space(@class)," ")," station ")]'):
        links=li.xpath('.//a[contains(@href,"traintimetable")]/@href')
        if not links:continue
        u=links[0].replace('http:','https:',1);sid=parse_qs(urlparse(u).query)['list'][0]
        name=''.join(li.xpath('./h3//text()')).strip();s=station_by_id.get(sid,{})
        code=''.join(li.xpath('./div[@class="label"]//text()'));code=re.sub(r'\s+','',code)
        line=next((v for k,v in [('NK','貝塚線'),('T','天神大牟田線'),('D','太宰府線'),('A','甘木線')] if code.startswith(k)),'西鉄電車')
        xy=[float(x) for x in s['zahyo'].split(',')] if s.get('zahyo') else [None,None]
        add('nishi-rail-'+sid,'nishitetsu-rail',name,'rail',u,'nishi-rail',line=line,city=s.get('city','福岡県'),
            lat=xy[0],lon=xy[1],pdfUrl=pdfs.get(code),kind='駅別時刻表',positionDate='公式検索地点・2026-09-15確認')
    for s in stationdata:
        if not s['id'].startswith('0004,'):continue
        xy=[float(x) for x in s['zahyo'].split(',')]
        add('chikuho-'+s['id'],'chikuho-rail',s['name'],'rail','https://jik.nishitetsu.jp/trainroute?'+urlencode({'f':'traintimetable','list':s['id']}),
            'nishi-jik',line='筑豊電気鉄道線',city=s.get('city',''),lat=xy[0],lon=xy[1],kind='駅別時刻表',positionDate='公式検索地点・2026-09-15確認')
    rail_by_name={}
    for f in rail['stations']['features']:
        p=f['properties']
        if p['N02_004']!='九州旅客鉄道':continue
        coords=f['geometry']['coordinates'];pts=[p for ln in coords for p in ln] if f['geometry']['type']=='MultiLineString' else coords
        lon,lat=pts[len(pts)//2];rail_by_name.setdefault(norm(p['N02_005']),dict(lat=lat,lon=lon,lines=set()))['lines'].add(p['N02_003'])
    for key,pref in [('jr-fukuoka','福岡県'),('jr-saga','佐賀県'),('jr-oita','大分県')]:
        for a in docs[key].xpath('//a[contains(@href,"tt_dep.cgi?c=")]'):
            raw=a.text_content().strip();name=re.split('[（(]',raw)[0].strip();u=urljoin(SOURCES[key],a.get('href'));sid=parse_qs(urlparse(u).query)['c'][0]
            p=rail_by_name.get(norm(name),{}) if pref=='福岡県' else {}
            add('jr-'+sid,'jr-kyushu',name,'rail',u,key,line='・'.join(sorted(p.get('lines',[]))) or 'JR九州（BRT停留所を含む）',
                city=pref,lat=p.get('lat'),lon=p.get('lon'),kind='駅・停留所別時刻表',reading=raw,positionDate='国土数値情報・2025年末' if p else None)
    jr_bus_positions={}
    for f in bus['features']:
        if 'JR九州' not in f['properties']['P11_002']:continue
        jr_bus_positions.setdefault(norm(f['properties']['P11_001']),f)
    for key,line in [('jr-bus','直方線：博多駅〜久山〜脇田温泉〜直方駅'),('jr-ieon','福間駅〜イオンモール福津循環線')]:
        for a in docs[key].xpath('//a[contains(@href,"qbus.jp")]'):
            name=a.text_content().strip();u=a.get('href').replace('http:','https:',1);sid=parse_qs(urlparse(u).query)['from'][0]
            pos=jr_bus_positions.get(norm(name));lon,lat=pos['geometry']['coordinates'] if pos else (None,None)
            add('jrbus-'+sid,'jr-kyushu-bus',name,'bus',u,key,line=line,city='福岡県',lat=lat,lon=lon,kind='停留所別時刻表',positionDate='国土数値情報・2022年度' if pos else None)
    # An old position is never silently treated as an active stop. A name search
    # lets the operator confirm changes and resolve stops with identical names.
    seen=set()
    for f in bus['features']:
        p=f['properties'];op=p['P11_002']
        if not (op=='西日本鉄道' or op.startswith('西鉄バス')):continue
        name=p['P11_001'];lon,lat=f['geometry']['coordinates'];key=(name,round(lat,4),round(lon,4),op)
        if key in seen:continue
        seen.add(key)
        url='https://jik.nishitetsu.jp/am/menu?'+urlencode({'ftKbn':'f','fkeyword':name,'tkeyword':'','btnSearchFT':'検索'})
        add('nishibus-'+hashlib.sha256(str(key).encode()).hexdigest()[:12],'nishitetsu-bus',name,'bus',url,'nishi-text',
            line='・'.join(str(v) for k,v in p.items() if k.startswith('P11_003_')),city=op,lat=lat,lon=lon,
            kind='停留所名を公式検索',positionDate='国土数値情報・2022年度（現況未確認）')
    # Also expose all acquired open feed providers, retaining attribution.
    groups=[
        dict(id='nishitetsu-bus',name='西鉄バス',mode='bus',description='福岡・北九州・筑豊・筑後など。停留所名で公式検索へ。',timetableUrl='https://jik.nishitetsu.jp/',mapUrl='https://www.nishitetsu.jp/bus/rosen/rosenmap/',statusUrl='https://www.nishitetsu.jp/bus/',analysis='一部共同運行・自治体公表分のみ。西鉄全便の計算は未接続。'),
        dict(id='nishitetsu-rail',name='西鉄電車',mode='rail',description='天神大牟田線・太宰府線・甘木線・貝塚線。各駅の検索と印刷用PDF。',timetableUrl=SOURCES['nishi-print'],mapUrl=SOURCES['nishi-rail'],analysis='公式時刻表を参照可能。全便の経路計算は未接続。'),
        dict(id='jr-kyushu',name='JR九州',mode='rail',description='福岡県の公式掲載駅に加え、佐賀・大分の接続先も検索。',timetableUrl=SOURCES['jr-fukuoka'],mapUrl='https://www.jrkyushu.co.jp/railway/',analysis='公式時刻表を参照可能。全便の経路計算は未接続。'),
        dict(id='jr-kyushu-bus',name='JR九州バス',mode='bus',description='直方線・福間イオン循環線。上下方向と平日・土日祝のPDFを掲載。',timetableUrl=SOURCES['jr-bus'],mapUrl='https://www.jrkbus.co.jp/rosen/index',analysis='公式時刻表を参照可能。福岡県内の全便計算は未接続。'),
        dict(id='chikuho-rail',name='筑豊電気鉄道',mode='rail',description='にしてつ時刻表の駅別検索。',timetableUrl='https://jik.nishitetsu.jp/',analysis='公式時刻表を参照可能。全便の経路計算は未接続。')]
    for f in feeds:
        gid='feed-'+f['id'];groups.append(dict(id=gid,name=f['name'],mode='open',description='取得した公開時刻表。県外接続路線のデータも掲載しています。',timetableUrl=f.get('catalog') or f['source'],analysis='計算に収録（有効日・収録路線のみ）' if f['current'] else '期限外・検証未完了。計算には使いません。'))
        add(gid,gid,f['name'],'open',f.get('catalog') or f['source'],f.get('catalog') or f['source'],line='公開GTFS',city='',lat=None,lon=None,kind='公開時刻表データ',downloadUrl='data/gtfs/'+f['file'],validFrom=f['validFrom'],validTo=f['validTo'])
        rows[-1]['analysisReady']=bool(f['current'])
    documents=[]
    for key in ['jr-bus','jr-ieon']:
        matches=[a for a in docs[key].xpath('//a[contains(@href,".pdf")]') if any(w in a.text_content() for w in ['ダイヤ','時刻表'])]
        labels=['博多 → 山の神・直方｜平日','博多 → 山の神・直方｜土日祝','直方・山の神 → 博多｜平日','直方・山の神 → 博多｜土日祝'] if key=='jr-bus' else ['福間駅〜イオンモール福津｜全日']
        assert len(matches)==len(labels),(key,len(matches))
        for a,label in zip(matches,labels):documents.append(dict(group='jr-kyushu-bus',label=label,url=urljoin(SOURCES[key],a.get('href')),sourceUrl=SOURCES[key],revision='2026-04-01' if key=='jr-bus' else None,checkedAt='2026-09-15'))
    # Repeated source links refer to the same station, keep one record.
    unique={r['id']:r for r in rows}
    result=dict(schemaVersion=1,checkedAt='2026-09-15',networkCoverageComplete=False,groups=groups,entries=list(unique.values()),documents=documents,
        sources=[dict(url=u,sha256=hashlib.sha256((args.cache/(k+'.html')).read_bytes()).hexdigest()) for k,u in SOURCES.items()],
        note='公式時刻表への案内と、計算用の停車時刻データは別項目。西鉄・JRの全便が計算に入ったという意味ではありません。')
    out=ROOT/'data/official-timetables.json';out.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n')
    print(json.dumps({'entries':len(unique),'byGroup':{g['name']:sum(e['group']==g['id'] for e in unique.values()) for g in groups[:5]},'documents':len(documents)},ensure_ascii=False))

if __name__=='__main__':main()
