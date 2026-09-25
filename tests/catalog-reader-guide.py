"""Validate the reader-first catalog's facts, links, page numbers and PDF navigation."""
import json
from pathlib import Path
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from pypdf import PdfReader

root = Path(__file__).resolve().parents[1]
guide = root / 'oita-mobility/guide'
pages = json.loads((root / 'scripts/catalog/oita-mobility-content.json').read_text())
nav = json.loads((root / 'scripts/catalog/oita-mobility-navigation.json').read_text())
numbers = {p['id']: i for i,p in enumerate(pages,2)}
soup = BeautifulSoup((guide / 'index.html').read_text(), 'html.parser')
ids = [node['id'] for node in soup.select('[id]')]
assert len(ids) == len(set(ids)), 'Duplicate HTML ids'
assert len(soup.select('.reader-card')) == 5
assert len(soup.select('.key-panel')) == 13
assert len(soup.select('.chapter-nav')) == 16
assert not soup.select('script'), 'Guide should work without scripts'
for a in soup.select('a[href]'):
    href = a['href']
    if href.startswith('#'):
        assert href[1:] in ids, href
    elif not urlsplit(href).scheme:
        assert (guide / urlsplit(href).path).exists(), href
for img in soup.select('img'):
    assert img.get('alt') and (guide / img['src']).exists(), img
for r in nav['routes']:
    assert r['start'] in numbers
    for label,target in r['steps']:
        assert target in numbers
for p in pages:
    node = soup.find(id=p['id'])
    assert node.select_one('.page-number').get_text(strip=True) == f'P{numbers[p["id"]]:02d}'
    assert p['note'] in node.get_text(), 'Must preserve caveat: '+p['id']
    url = urlsplit(p['url'])
    appfile = root / 'oita-mobility' / url.path
    assert appfile.exists(), str(appfile)
    if url.fragment:
        target = BeautifulSoup(appfile.read_text(), 'html.parser')
        # Existing SPA routers map hashes to their corresponding page/panel IDs.
        prefix = {'lab.html': 'page-', 'data-catalog.html': 'panel-'}.get(url.path, '')
        assert target.find(id=url.fragment) or (prefix and target.find(id=prefix+url.fragment)), p['url']

pdf = PdfReader(guide / 'oita-mobility-catalog.pdf')
assert len(pdf.pages) == 18
assert len(pdf.outline) == 16
for i,page in enumerate(pdf.pages,1):
    text = page.extract_text()
    assert f'{i:02d}' in text and 'P02 読者別ガイドへ' in text
    annotations = [a.get_object() for a in page.get('/Annots', [])]
    assert any('/Dest' in a for a in annotations), f'P{i} missing index link'
    assert any(a.get('/A', {}).get('/S') == '/URI' for a in annotations), f'P{i} missing app link'
destinations = [a.get_object()['/Dest'] for a in pdf.pages[1]['/Annots'] if '/Dest' in a.get_object()]
assert len(destinations) == 8, 'P02: 5 reader routes + 2 help routes + return link'
page2text = pdf.pages[1].extract_text()
for r in nav['routes']:
    assert r['pages'] in page2text and r['who'] in page2text
for n,p in enumerate(pages,2):
    if p['id'] in nav['highlights']:
        assert nav['highlights'][p['id']][0] in pdf.pages[n-1].extract_text()
assert '2026.09.24' in pdf.pages[-1].extract_text(), 'Keep actual capture date'
assert nav['edition'] in pdf.pages[-1].extract_text(), 'Separate revision date'
print('PASS: 18 pages, 5 reader routes, 13 key panels, internal/external links, unchanged caveats')
