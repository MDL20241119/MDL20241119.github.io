#!/usr/bin/env python3
"""Download Fukuoka public sources listed in the bundled manifest.
Cached files are reused. Revised upstream files get fresh hashes; review changes before publishing.
Usage: python3 scripts/fetch-fukuoka.py /path/to/raw
"""
import concurrent.futures,hashlib,json,sys,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'fukuoka-mobility';CACHE=Path(sys.argv[1]);CACHE.mkdir(parents=True,exist_ok=True)
manifest=json.loads((ROOT/'data/gtfs/catalog.json').read_text());public=json.loads((ROOT/'data/public-facility-sources.json').read_text())
urls={**{'gtfs/'+m['file']:m['source'] for m in manifest},**{m['file']:m['url'] for m in public},
'fukuoka-boundary.zip':'https://nlftp.mlit.go.jp/ksj/gml/data/N03/N03-2026/N03-20260101_40_GML.zip',
'fukuoka-population.zip':'https://nlftp.mlit.go.jp/ksj/gml/data/m500r6/m500r6-24/500m_mesh_2024_40_GEOJSON.zip',
'hospital.zip':'https://www.mhlw.go.jp/content/11121000/01-1_hospital_facility_info_20260601.csv.zip',
'rail.zip':'https://nlftp.mlit.go.jp/ksj/gml/data/N02/N02-25/N02-25_GML.zip',
'busstops.zip':'https://nlftp.mlit.go.jp/ksj/gml/data/P11/P11-22/P11-22_40_SHP.zip',
'facilities/400009_kokuseichousa_r02.xlsx':'https://data.bodik.jp/dataset/f1e8c484-d6a3-4527-a4de-37402671a744/resource/a96a9b85-7c73-4c9f-b3b2-3ec3a658c0ad/download/r2kokuchou_kakuhou_huhyou2.xlsx',
'facilities/401307_tikatetuekibetujoushajinin.xlsx':'https://data.bodik.jp/dataset/aa87a835-44b2-4730-a194-6e0676d45182/resource/1d91f387-243c-435a-a874-86178eb8f4dd/download/upload.xlsx',
'commute-out.xlsx':'https://www.city.fukuoka.lg.jp/soki/tokeichosa/shisei/toukei/kokusei/R2kokuchou_kouhyou/documents/R2kokuchou_3_6_1.xlsx',
'aeon-shops.json':'https://g9ey9rioe.api.hp.can-ly.com/v2/companies/680/shops/search?sort=area:asc&limit=1000',
'subway-decision.pdf':'https://www.city.fukuoka.lg.jp/gikaizimukyoku/giji/shisei/documents/20250926-koutsu-siryo.pdf',
'pt.pdf':'https://www.pref.fukuoka.lg.jp/uploaded/life/796583_62719454_misc.pdf'}
def get(item):
 name,url=item;p=CACHE/name;p.parent.mkdir(parents=True,exist_ok=True)
 if not p.exists():p.write_bytes(urllib.request.urlopen(url,timeout=100).read())
 return name,len(p.read_bytes())
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 for name,size in pool.map(get,urls.items()):print(name,size,flush=True)
for m in manifest:
 p=CACHE/'gtfs'/m['file'];m.update(downloaded=True,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
(CACHE/'gtfs-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
(CACHE/'public-manifest.json').write_text(json.dumps(public,ensure_ascii=False,indent=2))
print('Downloaded public sources. Review revisions, dates and official tables before rebuilding.')
