#!/usr/bin/env python3
"""Extract ODbL roads and services from the public Geofabrik Kyushu snapshot.

Road topology retains OSM node IDs. Crossing ways are connected only at shared
nodes. Forbidden/conditional access and barriers are not treated as walkable.
All derived OSM data is offered under ODbL 1.0 with source and version evidence.
"""
import argparse,gzip,hashlib,json,math,collections
from pathlib import Path
import osmium
from shapely.geometry import shape,Point,LineString
from shapely.ops import unary_union
from shapely.prepared import prep
ROOT=Path(__file__).resolve().parents[1]/'fukuoka-mobility'
ap=argparse.ArgumentParser();ap.add_argument('source',type=Path);ap.add_argument('--cache-dir',type=Path);args=ap.parse_args()
boundaries=json.loads((ROOT/'gaps/data/municipalities.geojson').read_text())['features']
cities=[(f['properties'],prep(shape(f['geometry']))) for f in boundaries]
whole=unary_union([shape(f['geometry']) for f in boundaries]);region=prep(whole.buffer(.03));pref=prep(whole)
nodes={};ways=[];pois=[];blocked=set();roads_by_type=collections.Counter();rejected=collections.Counter()
categories={'school':'school','university':'school','college':'school','kindergarten':'childcare','childcare':'childcare','social_facility':'welfare','library':'library','community_centre':'civic','townhall':'civic','pharmacy':'pharmacy','hospital':'hospital','clinic':'clinic','doctors':'clinic','dentist':'dental'}
def classify(t):
    if t.get('shop') in ('supermarket','convenience','greengrocer','bakery','butcher','seafood','general'):return 'shopping'
    return categories.get(t.get('amenity'))
def in_box(lon,lat):return 129.8<lon<131.6 and 32.6<lat<34.5
def poi(kind,id,lon,lat,t,position):
    category=classify(t)
    if not category or not t.get('name') or not in_box(lon,lat):return
    pt=Point(lon,lat)
    if not pref.covers(pt):return
    city=next((p for p,g in cities if g.covers(pt)),None)
    if not city:return
    pois.append({'id':f'osm-{kind}-{id}','osmId':str(id),'osmType':kind,'name':t['name'],'category':category,'lat':lat,'lon':lon,'city':city['name'],'municipalityCode':city['code'],'address':t.get('addr:full') or ''.join(t.get(k,'') for k in ['addr:province','addr:city','addr:suburb','addr:quarter','addr:neighbourhood','addr:block_number','addr:housenumber']) or '福岡県'+city['name'],'url':t.get('website') or t.get('contact:website'),'openingHours':t.get('opening_hours'),'wheelchairAccess':t.get('wheelchair'),'source':'OpenStreetMap contributors / Geofabrik','sourceUrl':f'https://www.openstreetmap.org/{kind}/{id}','sourceResourceUrl':'https://download.geofabrik.de/asia/japan/kyushu-260913.osm.pbf','dataAsOf':'2026-09-13','retrievedAt':'2026-09-14','license':'ODbL 1.0','licenseUrl':'https://opendatacommons.org/licenses/odbl/1-0/','needsCoordinateConfirmation':True,'dataNote':'OSMの施設情報。'+position+'。現況・入口・利用条件・施設の網羅は未確認。','tags':t})
class Extract(osmium.SimpleHandler):
    def node(self,n):
        lon,lat=n.location.lon,n.location.lat
        if not in_box(lon,lat):return
        t=dict(n.tags)
        if t.get('barrier') and t.get('foot') not in ('yes','designated','permissive'):blocked.add(n.id)
        if t.get('foot') in ('no','private','use_sidepath') or t.get('access') in ('no','private') or t.get('foot:conditional'):blocked.add(n.id)
        poi('node',n.id,lon,lat,t,'登録された地点')
    def way(self,w):
        t=dict(w.tags)
        try:pts=[(n.ref,n.location.lon,n.location.lat) for n in w.nodes]
        except osmium.InvalidLocationError:rejected['missing_nodes']+=1;return
        if not pts or not any(in_box(lon,lat) for _,lon,lat in pts):return
        if classify(t):
            g=LineString([(lon,lat) for _,lon,lat in pts]) if len(pts)>1 else Point(pts[0][1:]);c=g.centroid;poi('way',w.id,c.x,c.y,t,'登録された建物・区域の形状の中心')
        highway=t.get('highway');foot=t.get('foot');access=t.get('access')
        allowed={'primary','primary_link','secondary','secondary_link','tertiary','tertiary_link','unclassified','residential','living_street','service','pedestrian','footway','path','steps','track','cycleway'}
        if highway not in allowed or t.get('area')=='yes':return
        if highway=='cycleway' and foot not in ('yes','designated','permissive'):rejected['cycle_only']+=1;return
        if foot in ('no','private','use_sidepath') or (access in ('no','private','customers','destination') and foot not in ('yes','designated','permissive')) or any('conditional' in k for k in t):rejected['restricted']+=1;return
        line=LineString([(lon,lat) for _,lon,lat in pts])
        if not region.intersects(line):return
        ids=[]
        for id,lon,lat in pts:
            nodes[id]=[round(lat,7),round(lon,7)];ids.append(id)
        ways.append({'id':w.id,'nodes':ids,'tags':t});roads_by_type[highway]+=1
handler=Extract();handler.apply_file(str(args.source),locations=True,filters=[osmium.filter.KeyFilter('highway','amenity','shop','barrier','foot','access')])
print('extracted',len(nodes),'nodes',len(ways),'ways',len(pois),'POIs',flush=True)
def distance(a,b):
    rad=math.pi/180;lat=(a[0]+b[0])*.5*rad
    return math.hypot((a[0]-b[0])*111195,(a[1]-b[1])*111195*math.cos(lat))
# Indexed arrays are smaller to download; source IDs and original way memberships are retained.
ids=sorted(nodes);idx={id:i for i,id in enumerate(ids)};edges=[]
for w in ways:
    t=w['tags'];direction=t.get('oneway:foot','no')
    for a,b in zip(w['nodes'],w['nodes'][1:]):
        if a in blocked or b in blocked:continue
        length=round(distance(nodes[a],nodes[b]),2)
        if length<=0:continue
        if direction!='-1':edges.append([idx[a],idx[b],length,1 if t.get('highway')=='steps' else 0])
        if direction not in ('yes','1','true'):edges.append([idx[b],idx[a],length,1 if t.get('highway')=='steps' else 0])
source={'title':'OpenStreetMap 福岡県と県境周辺の歩行道路・生活施設','provider':'OpenStreetMap contributors / Geofabrik','url':'https://download.geofabrik.de/asia/japan/kyushu.html','downloadUrl':'https://download.geofabrik.de/asia/japan/kyushu-260913.osm.pbf','dataAsOf':'2026-09-13T20:21:20Z','retrievedAt':'2026-09-14','sha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),'license':'ODbL 1.0','licenseUrl':'https://opendatacommons.org/licenses/odbl/1-0/','attribution':'© OpenStreetMap contributors','nodeCount':len(nodes),'directedEdges':len(edges),'wayCount':len(ways),'poiCount':len(pois),'roadTypes':dict(roads_by_type),'excluded':dict(rejected),'notes':['福岡県行政界と約3kmの県境周辺を抽出。主要道路は歩道・横断可能性の欠測を含みます。','歩行禁止・私有・条件付き道路、通過可能性が未確認の障害物を除外。階段は保持し車いす条件で除外。','OSMの網羅・現在の通行可否・勾配・路面・幅員・交通信号待ちは未検証。','施設の原典は点・wayのみ。複数ポリゴンのrelation施設はこの抽出には含みません。']}
out=ROOT/'data/osm';out.mkdir(exist_ok=True)
def write(name,obj,compressed=False):
    folder=(args.cache_dir or args.source.parent) if name in ('walking-graph.json.gz','roads-source.json.gz') else out
    folder.mkdir(parents=True,exist_ok=True)
    b=(json.dumps(obj,ensure_ascii=False,separators=(',',':'))+'\n').encode();(folder/name).write_bytes(gzip.compress(b,mtime=0) if compressed else b)
write('source.json',source);write('walking-graph.json.gz',{'meta':source,'nodes':[nodes[id] for id in ids],'edges':edges},True)
write('roads-source.json.gz',{'meta':source,'nodes':nodes,'ways':ways,'blockedNodeIds':sorted(blocked)},True)
write('facilities.json.gz',{'meta':source,'facilities':pois},True)
print(json.dumps(source,ensure_ascii=False),flush=True)
