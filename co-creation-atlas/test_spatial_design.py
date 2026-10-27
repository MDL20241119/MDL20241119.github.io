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
        super().__init__(); self.images=[]; self.ids=[]; self.links=[];self.projects=[];self.photo_links=[];self.photo_sets=[];self.photo_json=None;self.feed(text)
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if attrs.get('id'):self.ids.append(attrs['id'])
        if tag=='img':self.images.append(attrs)
        if tag=='a':self.links.append(attrs.get('href',''))
        if tag=='a' and 'data-sd-photo' in attrs:self.photo_links.append(attrs)
        if tag=='article' and attrs.get('data-project-id'):self.projects.append(attrs['data-project-id'])
        if tag=='script' and 'data-sd-photo-set' in attrs:self.photo_json=''
    def handle_data(self, data):
        if self.photo_json is not None:self.photo_json+=data
    def handle_endtag(self, tag):
        if tag=='script' and self.photo_json is not None:
            self.photo_sets.append(json.loads(self.photo_json));self.photo_json=None


def main():
    data=spatial_design.read(ROOT)
    assert Counter(p['companyId'] for p in data['projects'])=={'studio-oa':6,'gensler':6,'clive-wilkinson':6,'penson':5}
    assert len([p for p in data['projects'] if p['id']=='mcdonalds-hq'])==1
    assert next(p for p in data['projects'] if p['id']=='mcdonalds-hq')['companyIds']==['studio-oa','gensler']
    pending=[m for m in data['media'] if m['publicationMode']=='link-only']
    cleared=[m for m in data['media'] if m['publicationMode']=='image']
    assert len(pending)==69 and len(cleared)>=147
    assert len({m['projectId'] for m in cleared})>=13
    assert sum(m.get('kind')=='video-still' for m in cleared)==24
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
    assert all(marker in rendered for marker in ['data-sd-prev', 'data-sd-next', 'data-sd-count'])
    by_project={p['id']:{m['id']:m for m in cleared if m['projectId']==p['id']} for p in data['projects']}
    found=[]
    for path,page in pages.items():
        assert len(page.ids)==len(set(page.ids)),path
        for img in page.images:
            if img.get('src'):assert img.get('alt') and img.get('width') and img.get('height')
        # Compact company cards can navigate every photo of their own space,
        # while neither full nor compact galleries mix separate facilities.
        for gallery in page.photo_sets:
            expected_photos=by_project[gallery['projectId']]
            assert {p['id'] for p in gallery['photos']}==set(expected_photos),path
            assert len(gallery['photos'])==len(expected_photos),path
            for photo in gallery['photos']:
                original=expected_photos[photo['id']]
                assert photo['src']=='/co-creation-atlas/'+original['local']
                assert photo['credit']==original['credit'] and photo['licenseUrl']==original['licenseUrl']
        for anchor in page.photo_links:
            assert anchor['data-sd-photo-id'] in by_project[anchor['data-sd-project']],path
        found+=page.projects
    assert Counter(found)==Counter(p['id'] for p in data['projects'])
    for p in data['projects']:
        page=(ROOT/'spatial-design'/p['companyId']/'index.html').read_text()
        assert p['name'] in unescape(page) and p['id'] in page
        count=len(by_project[p['id']])
        stills=any(m.get('kind')=='video-still' for m in cleared if m['projectId']==p['id'])
        if count:
            label=f'写真・映像静止画 <b>{count}</b>点' if stills else f'空間写真 <b>{count}</b>枚'
            assert label in page
        assert '掲載 '+spatial_design.media_count_label(spatial_design.project_photos(p,data)) in page
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
    print(f'PASS: 5 feature pages, 23 unique spaces, 69 link-only candidates, {len(cleared)} attributed media; no unconfirmed image sources; 115/37 existing counts retained.')


if __name__=='__main__':main()
