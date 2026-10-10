"""Regression checks for the source-linked urban-thinker extension."""
import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main():
    data = json.loads((ROOT/'data/cases.json').read_text())
    people = json.loads((ROOT/'data/urban-thinkers.json').read_text())
    media = json.loads((ROOT/'data/media.json').read_text())
    known = {c['id']:c for c in data}
    cases = [c for c in data if c.get('expertContext')]
    assert len(data) == 115 and len(cases) == 18
    assert len(people) == 9
    assert len({p['id'] for p in people}) == 9
    assert all(count == 2 for count in Counter(c['expertContext']['personId'] for c in cases).values())
    assert {cid for p in people for cid in p['caseIds']} == {c['id'] for c in cases}
    hub = (ROOT/'learn/urban-thinkers/index.html').read_text()
    assert 'NEW / 9 THINKERS' in (ROOT/'index.html').read_text()
    # The thumbnail-style entrance remains live HTML with a working index CTA.
    assert '<h1 id="thinker-title">いい街は、<br><span>何が違う？</span></h1>' in hub
    assert hub.count('<h1') == 1
    assert 'href="#thinker-index"' in hub and 'id="thinker-index"' in hub
    assert 'urban-thinkers-hero.css?v=' in hub
    assert len([p for person in people for p in person['reading']]) == 27
    hero = hub.split('<section class="expert-hero thinker-hero"', 1)[1].split('</section>', 1)[0]
    for cid in ['nyc-public-realm-strategy', 'melbourne-places-for-people']:
        image = next(m for m in media if m['caseId'] == cid and m.get('kind') != 'diagram')
        assert image['local'] in hero and image['sourceUrl'] in hero and image['licenseUrl'] in hero
        assert image['credit'] in hero and image['imageDate'] in hero
        assert (ROOT/image['local']).is_file()
    hero_css = (ROOT/'urban-thinkers-hero.css').read_text()
    assert 'object-fit:contain' in hero_css  # Preserve existing no-crop image metadata.
    assert '@media(max-width:600px)' in hero_css and ':focus-visible' in hero_css

    for p in people:
        assert len(p['caseIds']) == 2 and p['reading']
        assert f'id="{p["id"]}"' in hub
        for source in p['reading']:
            assert source['url'].startswith('https://') and source['accessNote']
    for case in cases:
        page = (ROOT/'cases'/case['id']/'index.html').read_text()
        assert 'THINKER &amp; PRACTICE' in page or 'THINKER & PRACTICE' in page
        assert 'expert-context' in page and 'DIAGRAM:' in page
        assert '原資料で、当時の調査・実践を読む' in page
        assert 'PROPOSAL / 未実施の検証案' in page
        assert '写真の転載条件は確認中' not in page
        assert all(s['url'].startswith('https://') and s.get('accessNote') for s in case['sources'])
        assert case['operator'] and case['payer'] and case['limits'] and case['nextTest']
        assert 'World_Class_Streets_Gehl_08.pdf' not in json.dumps(case)
        for related in case['entry']['related']:
            assert related['id'] in known and related['id'] != case['id']
    diagrams = [m for m in media if m.get('kind') == 'diagram']
    assert len(diagrams) == 18
    for item in diagrams:
        assert item['noCrop'] and item['status'] == 'original-diagram'
        tree = ET.parse(ROOT/item['local'])
        assert tree.getroot().tag.endswith('svg')
        assert item['caseId'] in {c['id'] for c in cases}
    # Preserve the existing programme boundaries: comparison links do not
    # silently assign authorship of a different project to the named thinker.
    for cid in ['nyc-plaza-program','paris-school-streets','paris-oasis-courtyards']:
        assert 'expertContext' not in known[cid]
    ET.parse(ROOT/'sitemap.xml')
    print('PASS: 115 cases; 9 thinkers × 2 distinct cases; role, access labels, diagram provenance and programme boundaries checked.')


if __name__ == '__main__':
    main()
