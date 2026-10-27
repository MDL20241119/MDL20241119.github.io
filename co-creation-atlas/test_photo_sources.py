"""Focused checks for the 2026-10-27 case photo update (standard library only)."""
import json
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import photo_sources

ROOT = Path(__file__).resolve().parent
EXPECTED = {'aalto-design-factory': 5, 'arena2036': 2,
            'ars-electronica-futurelab': 8, 'newlab-brooklyn': 2, 'quintbridge': 1}

class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.images, self.ids, self.external = [], [], []
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.append(attrs['id'])
        if tag == 'img':
            self.images.append(attrs)
        if tag == 'a' and attrs.get('href', '').startswith('https://'):
            self.external.append(attrs)

def main():
    assert sum(len(cards) for cards in photo_sources.DATA.values()) == 8
    assert 'microsoft-garage' not in photo_sources.DATA
    for slug, expected in EXPECTED.items():
        path = ROOT / 'cases' / slug / 'index.html'
        text = path.read_text()
        page = Page(text)
        assert len(page.images) == expected, (slug, 'photo count')
        assert all(n == 1 for n in Counter(page.ids).values()), (slug, 'duplicate IDs')
        for image in page.images:
            assert image.get('alt') and int(image['width']) > 0 and int(image['height']) > 0
            assert (path.parent / image['src'].split('?')[0]).is_file(), image['src']
        rendered = photo_sources.render(slug)
        if rendered:
            assert text.count(rendered) == 1, (slug, 'source cards differ from generator')
            assert '<img' not in rendered and '<iframe' not in rendered
            assert photo_sources.stylesheet('../../') in text
            for link in Page(rendered).external:
                assert link['target'] == '_blank' and 'noopener' in link['rel']
        else:
            assert 'FIELD PHOTOS / 8 PHOTOS' in text
    media = json.loads((ROOT / 'data/media.json').read_text())
    ids = ['ars-jku-medspace', 'ars-open-research-talk', 'ars-hello-worlds', 'ars-founding-lab-data']
    for asset_id in ids:
        matches = [m for m in media if m['assetId'] == asset_id]
        assert len(matches) == 1
        m = matches[0]
        assert m['status'] == 'cleared-editorial-only' and m['noCrop']
        assert m['credit'] and ' / ' in m['title']
        assert m['rightsUrl'] == 'https://photos.ars.electronica.art/'
        assert '切り抜き・色変更なし' in m['changes']
    case = next(c for c in json.loads((ROOT/'data/cases.json').read_text()) if c['id'] == 'ars-electronica-futurelab')
    assert case['photoCount'] == 8
    assert 'href="cases/ars-electronica-futurelab/#field-photos">写真 8枚' in (ROOT/'index.html').read_text()
    print('PASS: five pages, 18 photos, eight link-only source cards, rights/no-crop metadata and synchronized counts.')

if __name__ == '__main__':
    main()
