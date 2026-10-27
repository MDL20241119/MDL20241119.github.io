"""Feature integrity, attribution boundaries, stable IDs and regression checks."""
import json
import re
from copy import deepcopy
from html import unescape
from pathlib import Path
from html.parser import HTMLParser
from collections import Counter
from urllib.parse import urlparse
import spatial_design

ROOT = Path(__file__).resolve().parent


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.images=[]; self.iframes=[]; self.ids=[]; self.links=[];self.projects=[];self.photo_links=[];self.photo_sets=[];self.photo_json=None;self.company_images=[];self.in_company=False;self.feed(text)
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if attrs.get('id'):self.ids.append(attrs['id'])
        if tag=='article' and 'sd-company-card' in attrs.get('class','').split():self.in_company=True
        if tag=='img':
            self.images.append(attrs)
            if self.in_company:self.company_images.append(attrs)
        if tag=='iframe':self.iframes.append(attrs)
        if tag=='a':self.links.append(attrs.get('href',''))
        if tag=='a' and 'data-sd-photo' in attrs:self.photo_links.append(attrs)
        if tag=='article' and attrs.get('data-project-id'):self.projects.append(attrs['data-project-id'])
        if tag=='script' and 'data-sd-photo-set' in attrs:self.photo_json=''
    def handle_data(self, data):
        if self.photo_json is not None:self.photo_json+=data
    def handle_endtag(self, tag):
        if tag=='article':self.in_company=False
        if tag=='script' and self.photo_json is not None:
            self.photo_sets.append(json.loads(self.photo_json));self.photo_json=None


def test_embed_contract(embeds):
    for media in embeds:
        spatial_design.validate_official_embed(media)
    example = deepcopy(embeds[0])
    for url in [
        'http://www.behance.net/embed/project/4859177?ilo0=1',
        'https://behance.net/embed/project/4859177?ilo0=1',
        'https://www.behance.net.evil.example/embed/project/4859177?ilo0=1',
        'https://www.behance.net/embed/project/4859177?ilo0=1&extra=1',
        'https://www.behance.net/embed/project/4859177?ilo0=1#fragment',
        'https://www.behance.net/embed/project/abc?ilo0=1',
        'https://www.behance.net/gallery/4859177/project',
    ]:
        invalid=deepcopy(example);invalid['embedUrl']=url
        try:spatial_design.validate_official_embed(invalid)
        except AssertionError:pass
        else:raise AssertionError('Unapproved iframe URL accepted: '+url)
    for changes in [{'rightsStatus':'cleared-permission'}, {'local':'assets/copied-embed.jpg'}, {'permission':{'basis':'official-embed','termsUrl':'http://example.com/terms'}}, {'permission':{'basis':'unconfirmed','termsUrl':'https://example.com/terms'}}]:
        invalid=deepcopy(example);invalid.update(changes)
        try:spatial_design.validate_official_embed(invalid)
        except AssertionError:pass
        else:raise AssertionError('Invalid official embed record accepted')


def main():
    data=spatial_design.read(ROOT)
    assert Counter(p['companyId'] for p in data['projects'])=={'studio-oa':6,'gensler':6,'clive-wilkinson':6,'penson':5}
    assert len([p for p in data['projects'] if p['id']=='mcdonalds-hq'])==1
    assert next(p for p in data['projects'] if p['id']=='mcdonalds-hq')['companyIds']==['studio-oa','gensler']
    pending=[m for m in data['media'] if m['publicationMode']=='link-only']
    cleared=[m for m in data['media'] if m['publicationMode']=='image']
    embeds=[m for m in data['media'] if m['publicationMode']=='embed']
    quotations=[m for m in data['media'] if m['publicationMode']=='quotation']
    assert len(pending)==69 and len(cleared)>=147
    assert len({m['projectId'] for m in cleared})>=13
    assert sum(m.get('kind')=='video-still' for m in cleared)==24
    assert all(m['rightsStatus']=='permission-pending' for m in pending)
    assert spatial_design.visual_coverage(data)=={p['id'] for p in data['projects']}, 'Every space needs displayed photos, an official photo embed, or a specifically analysed photo quotation'
    for project in data['projects']:
        photographic_views=[m for m in spatial_design.project_visuals(project,data) if m.get('kind')!='video-still']
        assert len(photographic_views)>=3, project['id']+' needs at least three actual photographic views; video frames do not fill this requirement'
    assert embeds, 'Official photo embeds must remain represented separately'
    test_embed_contract(embeds)
    pages={p:Page(p.read_text()) for p in (ROOT/'spatial-design').rglob('index.html')}
    assert len(pages)==5
    # No remote image sources, placeholders, or unconfirmed image files enter the generated pages.
    expected={'/co-creation-atlas/'+m['local'] for m in cleared+quotations}
    images={i['src'] for p in pages.values() for i in p.images if i.get('src')}
    assert images==expected
    assert all(not urlparse(src).scheme for src in images)
    assert all(not any(m.get('originalImageUrl')==src for m in pending) for src in images)
    iframe_sources={f['src'] for page in pages.values() for f in page.iframes}
    assert iframe_sources=={m['embedUrl'] for m in embeds}
    for page in pages.values():
        for frame in page.iframes:
            assert spatial_design.BEHANCE_EMBED_URL.fullmatch(frame['src'])
            assert frame.get('title') and frame.get('loading')=='lazy'
            assert frame.get('width')=='404' and frame.get('height')=='316'
            assert 'allowfullscreen' in frame
    quoted_sources={'/co-creation-atlas/'+m['local'] for m in quotations}
    assert all(not quoted_sources.intersection(a['href'] for a in page.photo_links) for page in pages.values())
    assert all(not quoted_sources.intersection(page.links) for page in pages.values()), 'Do not link directly to standalone quotation files'
    assert all(not quoted_sources.intersection(i.get('src') for i in page.company_images) for page in pages.values())
    rendered=''.join(p.read_text() for p in pages)
    assert 'Speedee Labs' in rendered and '自己申告' in rendered
    assert '2025-07-22〜09-12' in rendered and '16,459人' in rendered
    assert 'aria-labelledby="sd-photo-title"' in rendered
    assert all(marker in rendered for marker in ['data-sd-prev', 'data-sd-next', 'data-sd-count'])
    assert '掲載写真 0枚' not in rendered
    assert spatial_design.visual_summary(data) in unescape(rendered)
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
        assert 'id="photos-'+p['id']+'"' in page
        assert spatial_design.project_photo_url(p) in (ROOT/'spatial-design/index.html').read_text()
        count=len(by_project[p['id']])
        stills=any(m.get('kind')=='video-still' for m in cleared if m['projectId']==p['id'])
        if count:
            label=f'写真・映像静止画 <b>{count}</b>点' if stills else f'空間写真 <b>{count}</b>枚'
            assert label in page
        assert spatial_design.availability_label(p,data) in unescape(page)
        for m in [m for m in cleared if m['projectId']==p['id']]:
            assert spatial_design.e(m['credit']) in page
            assert spatial_design.e(m['caption']) in page
            assert m['licenseUrl'] in page
        for m in spatial_design.project_embeds(p,data):
            assert m['embedUrl'] in unescape(page)
            assert spatial_design.e(m['credit']) in page and m['permission']['termsUrl'] in page
        for m in spatial_design.project_quotations(p,data):
            fragment=spatial_design.quotation_gallery(p,data)
            assert '<h5>'+spatial_design.e(m.get('quoteTitle') or '写真の配置を読む。')+'</h5>' in fragment
            assert spatial_design.e(m['quotePurpose']) not in fragment, 'Internal quotation review purpose must not become reader copy'
            assert all(spatial_design.e(paragraph) in fragment for paragraph in m['quoteAnalysis'])
            assert m['id'] in fragment and '写真引用' in fragment
            assert 'id="view-'+m['id']+'"' in fragment
            if len(spatial_design.project_quotations(p,data))>1:
                assert 'href="#view-'+m['id']+'"' in fragment
            assert 'data-sd-photo' not in fragment and 'data-sd-photo-set' not in fragment
            assert spatial_design.e(m['credit']) in page and m['permission']['termsUrl'] in page
            assert not any(p['id']==g['projectId'] and m['id'] in {photo['id'] for photo in g['photos']} for parsed in pages.values() for g in parsed.photo_sets)
            index=spatial_design.index_visual(p,data)
            lead=spatial_design.project_quotations(p,data)[0]
            assert 'sd-index-quotation' in index and spatial_design.e(lead['quoteSummary']) in index
            if m['id'] != lead['id']:
                assert m['id'] not in index, 'Keep the index to one analysed lead image; compare further views in the article'
    for path in [ROOT/'index.html', ROOT/'frontier/index.html']:
        assert path.read_text().count('class="sd-feature-entry"')==1
    sitemap=(ROOT/'sitemap.xml').read_text()
    urls=['https://mobilitydlab.com/co-creation-atlas/spatial-design/']
    urls += [urls[0]+c['id']+'/' for c in data['companies']]
    assert all(sitemap.count('<loc>'+u+'</loc>')==1 for u in urls)
    assert len(json.loads((ROOT/'data/cases.json').read_text()))==115
    frontier=json.loads((ROOT/'data/frontier.json').read_text())
    assert len(frontier)==37
    print(f'PASS: 5 feature pages, all 23 spaces have displayed visuals, 69 link-only candidates, {len(cleared)} local media, {len(embeds)} official embeds, {len(quotations)} analytical photo quotations; mode separation and 115/37 existing counts retained.')


if __name__=='__main__':main()
