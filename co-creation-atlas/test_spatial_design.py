"""Feature integrity, attribution boundaries, stable IDs and regression checks."""
import json
import re
from html import unescape
from pathlib import Path
from html.parser import HTMLParser
from collections import Counter
from urllib.parse import urlparse
import spatial_design

ROOT = Path(__file__).resolve().parent


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.images=[]; self.ids=[]; self.links=[];self.projects=[];self.feed(text)
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if attrs.get('id'):self.ids.append(attrs['id'])
        if tag=='img':self.images.append(attrs)
        if tag=='a':self.links.append(attrs.get('href',''))
        if tag=='article' and attrs.get('data-project-id'):self.projects.append(attrs['data-project-id'])


def main():
    data=spatial_design.read(ROOT)
    assert Counter(p['companyId'] for p in data['projects'])=={'studio-oa':6,'gensler':6,'clive-wilkinson':6,'penson':5}
    assert len([p for p in data['projects'] if p['id']=='mcdonalds-hq'])==1
    assert next(p for p in data['projects'] if p['id']=='mcdonalds-hq')['companyIds']==['studio-oa','gensler']
    pending=[m for m in data['media'] if m['publicationMode']=='link-only']
    cleared=[m for m in data['media'] if m['publicationMode']=='image']
    assert len(pending)==69 and len(cleared)>=14
    assert all(m['rightsStatus']=='permission-pending' for m in pending)
    pages={p:Page(p.read_text()) for p in (ROOT/'spatial-design').rglob('index.html')}
    assert len(pages)==5
    # No remote image sources, placeholders, or unconfirmed image files enter the generated pages.
    expected={'/co-creation-atlas/'+m['local'] for m in cleared}
    images={i['src'] for p in pages.values() for i in p.images if i.get('src')}
    assert images==expected
    assert all(not urlparse(src).scheme for src in images)
    assert all(not any(m.get('originalImageUrl')==src for m in pending) for src in images)
    rendered=''.join(p.read_text() for p in pages)
    assert 'Speedee Labs' in rendered and '自己申告' in rendered
    assert '2025-07-22〜09-12' in rendered and '16,459人' in rendered
    assert 'aria-labelledby="sd-photo-title"' in rendered
    found=[]
    for path,page in pages.items():
        assert len(page.ids)==len(set(page.ids)),path
        for img in page.images:
            if img.get('src'):assert img.get('alt') and img.get('width') and img.get('height')
        found+=page.projects
    assert Counter(found)==Counter(p['id'] for p in data['projects'])
    for p in data['projects']:
        page=(ROOT/'spatial-design'/p['companyId']/'index.html').read_text()
        assert p['name'] in unescape(page) and p['id'] in page
        for m in [m for m in cleared if m['projectId']==p['id']]:
            assert spatial_design.e(m['credit']) in page
            assert spatial_design.e(m['caption']) in page
            assert m['licenseUrl'] in page
    for path in [ROOT/'index.html', ROOT/'frontier/index.html']:
        assert path.read_text().count('class="sd-feature-entry"')==1
    sitemap=(ROOT/'sitemap.xml').read_text()
    urls=['https://mobilitydlab.com/co-creation-atlas/spatial-design/']
    urls += [urls[0]+c['id']+'/' for c in data['companies']]
    assert all(sitemap.count('<loc>'+u+'</loc>')==1 for u in urls)
    assert len(json.loads((ROOT/'data/cases.json').read_text()))==115
    frontier=json.loads((ROOT/'data/frontier.json').read_text())
    assert len(frontier)==37
    print(f'PASS: 5 feature pages, 23 unique spaces, 69 link-only candidates, {len(cleared)} attributed CC photos; no unconfirmed image sources; 115/37 existing counts retained.')


if __name__=='__main__':main()
