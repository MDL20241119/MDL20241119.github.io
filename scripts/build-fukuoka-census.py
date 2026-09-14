#!/usr/bin/env python3
"""Join 2020 census mesh observations without allocating suppressed/border counts.
Usage: python scripts/build-fukuoka-census.py RAW_DIR
The four e-Stat T001141 ZIPs are acquired from the URLs in the output audit.
"""
import csv, gzip, hashlib, io, json, sys, zipfile
from pathlib import Path
from shapely.geometry import shape, box

ROOT = Path(__file__).resolve().parents[1] / 'fukuoka-mobility'
FIELDS = {'censusPopulation2020':'001', 'censusAge65':'019', 'censusAge75':'022',
          'censusAge85':'025', 'censusHouseholds':'034', 'censusSingleElderly':'049', 'censusElderlyCouples':'050'}

def mesh_box(code):
    y=int(code[:2])/1.5+int(code[4])/12+int(code[6])/120
    x=100+int(code[2:4])+int(code[5])/8+int(code[7])/80
    q=int(code[8])-1
    return box(x+(q%2)/160,y+(q//2)/240,x+(q%2+1)/160,y+(q//2+1)/240)

def build(raw):
    rows={};archives=[];labels={}
    for code in ['4930','5030','5031','5130']:
        p=raw/f'census2020-{code}.zip';data=p.read_bytes()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            table=list(csv.reader(io.StringIO(z.read(f'tblT001141H{code}.txt').decode('cp932'))))
        labels.update(zip(table[0],table[1]))
        for values in table[2:]:
            r=dict(zip(table[0],values));assert r['KEY_CODE'] not in rows;rows[r['KEY_CODE']]=r
        archives.append({'mesh':code,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),
          'url':f'https://www.e-stat.go.jp/gis/statmap-search/data?statsId=T001141&code={code}&downloadType=2'})
    bounds=json.loads((ROOT/'gaps/data/municipalities.geojson').read_text())
    grids={};selected=set();counts={'numeric500':0,'boundary500':0,'suppressed500':0,'missing500':0}
    for f in bounds['features']:
        city=f['properties']['code'];boundary=shape(f['geometry']);fine={}
        for cell in json.loads((ROOT/f'gaps/data/{city}-500.geojson').read_text())['features']:
            code=cell['properties']['meshCode'];r=rows.get(code)
            if r:selected.add(code)
            # 30m geographic guard around the mesh also covers the 20m simplified boundary error.
            state='missing' if r is None else 'suppressed' if r['HTKSYORI']!='0' else 'boundary' if not boundary.covers(mesh_box(code).buffer(.0003)) else 'numeric'
            counts[state+'500']+=1
            values={k:int(r['T001141'+v]) if state=='numeric' and r['T001141'+v].isdigit() else None for k,v in FIELDS.items()}
            fine[code]={**values,'censusState':state,'censusYear':2020}
        grids[city+'-500']=fine
        coarse={}
        for cell in json.loads((ROOT/f'gaps/data/{city}-1000.geojson').read_text())['features']:
            code=cell['properties']['meshCode'];children=[fine.get(code+str(i)) for i in range(1,5)]
            complete=all(v and v['censusState']=='numeric' for v in children)
            values={k:sum(v[k] for v in children) if complete and all(v[k] is not None for v in children) else None for k in FIELDS}
            coarse[code]={**values,'censusState':'numeric' if complete else 'incomplete','censusYear':2020}
        grids[city+'-1000']=coarse
    source={'title':'2020年国勢調査 500mメッシュ 人口及び世帯（JGD2011・T001141）',
      'provider':'総務省統計局・e-Stat','url':'https://www.e-stat.go.jp/gis/statmap-search?type=1&statsId=T001141',
      'dataAsOf':'2020-10-01','sourceUpdatedAt':'2024-03-14','retrievedAt':'2026-09-14',
      'license':'政府標準利用規約に基づく加工','licenseUrl':'https://www.e-stat.go.jp/terms-of-use',
      'archives':archives,'fields':{k:{'code':'T001141'+v,'label':labels['T001141'+v].strip()} for k,v in FIELDS.items()},
      'sourceRows':len(rows),'selectedSourceRows':len(selected),'counts':counts,
      'notes':['2020年実績。現在人口や交通空白人口ではありません。国交省調整人口とは別の統計です。',
      '秘匿・合算対象は集計から除外。欠測・区域境界付近を0や面積按分で補完しません。',
      '500mメッシュ全体と約30mの余裕が自治体境界内に収まる場合のみ区域人数を計上。',
      '1000mは4子メッシュすべてに集計可能な数値がある場合だけ合算します。',
      '高齢単身世帯・高齢夫婦世帯は世帯数。人数へ変換しません。']}
    def write(name,obj):
        b=json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode()
        p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(gzip.compress(b,mtime=0) if name.endswith('.gz') else b+b'\n')
    write('data/census-audit.json',source)
    write('data/sources/census2020.json.gz',{'source':source,'rows':[rows[k] for k in sorted(selected)]})
    write('gaps/data/census2020.json.gz',{'source':source,'grids':grids})
    print(json.dumps({'sourceRows':len(rows),'selected':len(selected),**counts},ensure_ascii=False))

if __name__=='__main__':build(Path(sys.argv[1]))
