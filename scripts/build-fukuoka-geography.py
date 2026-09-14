#!/usr/bin/env python3
"""Build municipal boundaries and 500/1000 m cells from MLIT public archives.
Requires shapely and pyproj. Raw archives stay in the supplied scratch cache.
No population is copied into two municipalities; boundary-crossing totals stay null.
"""
from pathlib import Path
import collections, hashlib, json, math, re, sys, zipfile
from shapely.geometry import shape, mapping, box, Point, MultiPolygon
from shapely.ops import unary_union, transform
from shapely import make_valid, coverage_simplify, set_precision
from pyproj import Transformer

CACHE=Path(sys.argv[1]); ROOT=Path(__file__).resolve().parents[1]/'fukuoka-mobility'; OUT=ROOT/'gaps/data'
OUT.mkdir(parents=True,exist_ok=True)
def write(name,data): (OUT/name).write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'),allow_nan=False))
def readzip(name):
 z=zipfile.ZipFile(CACHE/name);return json.loads(z.read(next(n for n in z.namelist() if n.endswith('.geojson'))))
def city(code):
 return '40100' if code.startswith('4010') else '40130' if code.startswith('4013') else code
def polygon(g):
 g=make_valid(g)
 if g.geom_type in ('Polygon','MultiPolygon'):return g
 return unary_union([x for x in g.geoms if x.geom_type in ('Polygon','MultiPolygon')])
def meshcode(lat,lon,half=True):
 a=math.floor(lat*1.5+1e-8);b=math.floor(lon)-100
 c=math.floor((lat*1.5-a)*8+1e-7);d=math.floor((lon-math.floor(lon))*8+1e-7)
 e=math.floor(((lat*1.5-a)*8-c)*10+1e-6);f=math.floor(((lon-math.floor(lon))*8-d)*10+1e-6)
 base=f'{a:02}{b:02}{c}{d}{e}{f}'
 if not half:return base
 south=a/1.5+c/12+e/120;west=100+b+d/8+f/80
 return base+str(1+(lat-south>=1/240-1e-8)*2+(lon-west>=1/160-1e-8))

forward=Transformer.from_crs(6668,6670,always_xy=True).transform
inverse=Transformer.from_crs(6670,6668,always_xy=True).transform
groups=collections.defaultdict(list);props={}
for f in readzip('fukuoka-boundary.zip')['features']:
 p=f['properties'];code=city(p['N03_007'])
 if code=='40000':continue # Unassigned reclaimed land is not a municipality.
 groups[code].append(shape(f['geometry']));props[code]={'code':code,'name':p['N03_004'],'prefecture':'福岡県','district':p['N03_003'],'boundaryDate':'2026-01-01'}
geoms={c:polygon(unary_union(g)) for c,g in sorted(groups.items())}
assert len(geoms)==60
projected=[set_precision(transform(forward,g),.001) for g in geoms.values()]
simple=coverage_simplify(projected,20)
source={'boundary':{'title':'国土数値情報 行政区域データ（N03、2026年版）','provider':'国土交通省','url':'https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N03-2026.html','downloadUrl':'https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2026/N03-20260101_40_GML.zip','asOf':'2026-01-01','retrievedAt':'2026-09-14','license':'CC BY 4.0','licenseUrl':'https://nlftp.mlit.go.jp/ksj/other/agreement_01.html','processing':'福岡県を抽出。政令市の区を市単位に統合。JGD2011平面直角座標IIで境界共有を保ち20m簡略化。所属未定地は市町村へ配分しない。','attribution':'国土数値情報（行政区域データ・2026年）（国土交通省）を加工','note':'居住域ではなく行政区域。島・山林・水面を含む。境界確定・測量には使えません。','legalNote':'原典の利用条件と測量成果の二次利用案内を参照。','originalCRS':'JGD2011（EPSG:6668）','archiveSha256':hashlib.sha256((CACHE/'fukuoka-boundary.zip').read_bytes()).hexdigest()},
 'population':{'title':'国土数値情報 500mメッシュ別将来推計人口（R6国政局推計）・福岡県2020年基準人口','provider':'国土交通省 国土政策局','url':'https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-mesh500r6.html','downloadUrl':'https://nlftp.mlit.go.jp/ksj/gml/data/m500r6/m500r6-24/500m_mesh_2024_40_GEOJSON.zip','baselineYear':2020,'creationFiscalYear':2024,'retrievedAt':'2026-09-14','valueField':'PTN_2020','valueLabel':'2020年基準人口（国交省調整値）','license':'CC BY 4.0','licenseUrl':'https://nlftp.mlit.go.jp/ksj/other/agreement_01.html','attribution':'国土数値情報（500mメッシュ別将来推計人口・R6国政局推計）（国土交通省）を加工','limitations':['現在人口ではなく、2020年国勢調査を基準とした国交省調整値です。','市町村境界をまたぐメッシュの人口は二重加算せず未集計とします。政令市内の区境は統合します。','原典にないメッシュの人口はnull。人口ゼロと推測しません。','1000mの人口は構成する収録500mメッシュ人口の和。区域内の完全な人口を意味しません。','2020年の高齢者数は本ファイルに含みません。将来年の年齢別値を実績に転用しません。'],'archiveSha256':hashlib.sha256((CACHE/'fukuoka-population.zip').read_bytes()).hexdigest()}}
bf=[]
for (code,g),simp,proj in zip(geoms.items(),simple,projected):
 props[code]['areaKm2']=round(proj.area/1e6,4)
 bf.append({'type':'Feature','id':code,'properties':props[code],'bbox':list(g.bounds),'geometry':mapping(transform(inverse,simp))})
write('municipalities.geojson',{'type':'FeatureCollection','source':source['boundary'],'features':bf})
pop={str(f['properties']['MESH_ID']):f['properties'] for f in readzip('fukuoka-population.zip')['features']}
totals={'municipalities':60,'sourcePopulationMeshes':len(pop),'sourcePopulation2020':round(sum(p['PTN_2020'] or 0 for p in pop.values()),4),'cells500':0,'cells1000':0}
for code,g in geoms.items():
 minx,miny,maxx,maxy=g.bounds;cells=[];coarse=collections.defaultdict(list)
 for y in range(math.floor(miny*240),math.ceil(maxy*240)):
  for x in range(math.floor(minx*160),math.ceil(maxx*160)):
   square=box(x/160,y/240,(x+1)/160,(y+1)/240)
   if not g.intersects(square):continue
   piece=polygon(g.intersection(square))
   if piece.is_empty or piece.area<1e-12:continue
   c=meshcode((y+.5)/240,(x+.5)/160);p=pop.get(c)
   codes={city(c) for c in re.findall(r'\d{5}',str(p.get('SHICODE','')))} if p else set()
   known=p is not None and codes=={code} and isinstance(p.get('PTN_2020'),(int,float))
   point=square.centroid if piece.covers(square.centroid) else piece.representative_point()
   pp=transform(forward,piece);area=pp.area/1e6
   pr={'id':code+':'+c,'meshCode':c,'cityCode':code,'city':props[code]['name'],'lat':round(point.y,7),'lon':round(point.x,7),'areaKm2':round(area,7),'populated2020':bool(p and (p.get('PTN_2020') or 0)>0),'population2020':p['PTN_2020'] if known else None,'populationNote':'2020年基準の国交省調整値' if known else '境界またぎ・原典収録外のため自治体内人口は未集計'}
   cells.append({'type':'Feature','id':pr['id'],'properties':pr,'geometry':mapping(transform(inverse,pp.simplify(5,preserve_topology=True)))})
   coarse[c[:8]].append((piece,pr))
 metadata={'cityCode':code,'city':props[code]['name'],'resolution':500,'boundaryDate':'2026-01-01','populationLabel':source['population']['valueLabel'],'method':'標準地域メッシュを行政界で切抜き。中心が区域外のとき区域内代表点を判定点にする。人口不明をゼロにしない。'}
 write(code+'-500.geojson',{'type':'FeatureCollection','metadata':metadata,'features':cells})
 out=[]
 for c,children in coarse.items():
  piece=polygon(unary_union([a for a,_ in children]));pt=piece.centroid if piece.covers(piece.centroid) else piece.representative_point()
  pp=[p for _,p in children];values=[p['population2020'] for p in pp];hasCross=any(p['populated2020'] and p['population2020'] is None for p in pp)
  population=None if hasCross or all(v is None for v in values) else round(sum(v for v in values if v is not None),4)
  pr={'id':code+':'+c,'meshCode':c,'cityCode':code,'city':props[code]['name'],'lat':round(pt.y,7),'lon':round(pt.x,7),'areaKm2':round(sum(p['areaKm2'] for p in pp),7),'populated2020':any(p['populated2020'] for p in pp),'population2020':population,'populationNote':'収録500mメッシュ人口の合算（原典収録外は補完しない）' if population is not None else '境界またぎ・収録外等のため人口未集計'}
  out.append({'type':'Feature','id':pr['id'],'properties':pr,'geometry':mapping(transform(inverse,transform(forward,piece).simplify(5,preserve_topology=True)))})
 write(code+'-1000.geojson',{'type':'FeatureCollection','metadata':{**metadata,'resolution':1000},'features':out})
 totals['cells500']+=len(cells);totals['cells1000']+=len(out)
 print(code,props[code]['name'],len(cells),flush=True)
write('sources.json',source);write('summary.json',totals);print(totals,flush=True)
