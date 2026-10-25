"""Offline editorial integrity checks; run after build.py."""
import json
import re
from html.parser import HTMLParser
from pathlib import Path
import frontier

ROOT = Path(__file__).resolve().parent
ORIGINAL_IDS = {'doll-living-lab', 'michigan-central-newlab-detroit', 'punggol-digital-district', 'aalto-design-factory', 'firstbuild', 'marineterrein-amsterdam', 'test-in-tallinn', 'josephs', 'cern-ideasquare', 'bmw-startup-garage', 'massrobotics', 'arena2036', 'hvm-catapult'}
SHARED_IDS = {'arena2036', 'hvm-catapult', 'newlab-brooklyn', 'michigan-central-newlab-detroit', 'arm-robotics-manufacturing-hub', 'robohouse', 'massrobotics'}

class Parser(HTMLParser):
    def __init__(self, page):
        super().__init__(); self.cards=[]; self.photos=[]; self.links=[]; self.steps=[]; self.feed(page)
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=='article' and attrs.get('class')=='frontier-card':self.cards.append(attrs)
        if tag=='img':self.photos.append(attrs)
        if tag=='a':self.links.append(attrs.get('href',''))
        if tag=='div' and 'frontier-step ' in attrs.get('class',''):self.steps.append(attrs)

def main():
    rows, stages=frontier.read(ROOT)
    assert len(rows)==16
    assert {c['id'] for c in rows}==ORIGINAL_IDS|{'newlab-brooklyn','arm-robotics-manufacturing-hub','robohouse'}
    assert {c['lens'] for c in rows}=={'hard','soft','partners'}
    assert {c['id'] for c in rows if c.get('sharedLab')}==SHARED_IDS
    assert {c[k]['number'] for c in rows for k in ['primaryStep','secondaryStep']}==set(range(1,9))
    assert all(c.get('statusLabel') and c.get('statusNote') for c in rows)
    page=(ROOT/'frontier/index.html').read_text();parsed=Parser(page)
    assert len(parsed.cards)==len(rows)
    assert len(parsed.photos)==len(rows)+1+sum(len(c.get('extraPhotoIds',[])) for c in rows)
    assert {c['data-case-id'] for c in parsed.cards if c.get('data-focus')=='shared-labs'}==SHARED_IDS
    assert len(parsed.steps)==2*len(rows)
    assert page.count('class="frontier-evidence"')==len(rows)
    assert not re.search(r'世界一(?:の|位)|世界[１1]位|世界最高|ランキング|順位[：:]|scores|rankReason',page)
    assert all(i.get('alt') and i.get('width') and i.get('height') for i in parsed.photos)
    for c in rows:
        assert '../cases/'+c['id']+'/' in parsed.links
        for k in ['primaryStep','secondaryStep']:
            assert f'../learn/step-{c[k]["number"]:02d}/' in parsed.links
            assert frontier.e(c[k]['why']) in page
        for s in c['sources']:assert s['url'] in parsed.links
        if c.get('sharedLab'):
            lab=c['sharedLab']
            for key in ['type','facilities','access','collaboration','comparison','photoReading']:
                assert frontier.e(lab[key]) in page
            for question in lab['questions']:assert frontier.e(question) in page
            for visual in lab['visualSources']:
                assert visual['url'] in parsed.links and frontier.e(visual['note']) in page
            assert f'?focus=shared-labs#case-{c["id"]}' in parsed.links
            detail=(ROOT/'cases'/c['id']/'index.html').read_text()
            assert detail.count('class="frontier-case-return"')==1
            assert f'../../frontier/?focus=shared-labs#case-{c["id"]}' in detail
        if c.get('photoId'):
            media=json.loads((ROOT/'data/media.json').read_text())
            selected=next(m for m in media if m['assetId']==c['photoId'])
            assert selected['caseId']==c['id']
            selected_src=selected.get('remote') or '../'+selected['local']
            if selected.get('revision') and not selected.get('remote'):selected_src+='?v='+selected['revision']
            assert selected_src in {image.get('src') for image in parsed.photos}
    assert '?focus=shared-labs#frontier-explore' in parsed.links
    assert page.count('id="frontier-shared-filter"')==1
    assert page.count('class="frontier-lab-visuals"')==len(SHARED_IDS)
    assert page.count('class="frontier-lab-detail"')==len(SHARED_IDS)
    home=(ROOT/'index.html').read_text()
    assert home.count('class="frontier-entry"')==1
    assert home.index('class="frontier-entry"')<home.index('class="step-home-grid"')
    assert 'href="frontier/"' in home and home.count('class="step-home-card"')==8
    assert 'href="frontier/?focus=shared-labs#frontier-explore"' in home
    assert (ROOT/'sitemap.xml').read_text().count('https://mobilitydlab.com/co-creation-atlas/frontier/')==1
    assert '共通仕様を公開・国際規格へ' in page and '実証終了（2023）' in page and '展開中' in page
    assert '<noscript>' in page
    assert len(json.loads((ROOT/'data/cases.json').read_text()))==115
    print('PASS: 16 source-backed selections (original 13 retained), 7 shared research factories, 3 axes, all 8 steps, attributed photos, visual/source/detail links, home entry and sitemap; 115 existing cases retained.')

if __name__=='__main__':main()
