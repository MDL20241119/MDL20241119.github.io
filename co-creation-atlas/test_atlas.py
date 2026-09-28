"""Static release checks. Run after build.py; no network or external writes."""
import json
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, unquote

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent

class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids = []
        self.links = []
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'): self.ids.append(attrs['id'])
        if tag in {'a', 'link'} and attrs.get('href'): self.links.append(attrs['href'])
        if tag in {'script', 'img'} and attrs.get('src'): self.links.append(attrs['src'])

def main():
    cases = json.loads((ROOT/'data/cases.json').read_text())
    chains = json.loads((ROOT/'data/value-chains.json').read_text())
    fits = json.loads((ROOT/'data/learning-case-fit.json').read_text())
    ids = [c['id'] for c in cases]
    assert len(ids) == len(set(ids)), 'Duplicate case IDs'
    assert len({c['name'] for c in cases}) == len(cases), 'Duplicate case names'
    assert not any('woven' in json.dumps(c, ensure_ascii=False).lower() or 'ウーブン' in json.dumps(c, ensure_ascii=False) for c in cases), 'Excluded case must not appear in public case data'
    assert set(ids) == {c['id'] for c in chains} == {c['caseId'] for c in fits}
    pages = {p: Page(p.read_text()) for p in ROOT.rglob('*.html') if p.name == 'index.html'}
    errors = []
    for path, page in pages.items():
        for anchor, count in Counter(page.ids).items():
            if count > 1: errors.append(f'{path.relative_to(ROOT)}: duplicate id {anchor}')
        for href in page.links:
            url = urlparse(href)
            if url.scheme or url.netloc: continue
            target = (REPO/unquote(url.path).lstrip('/')) if url.path.startswith('/') else (path.parent/unquote(url.path))
            target = target.resolve()
            if target.is_dir(): target /= 'index.html'
            if not target.exists():
                errors.append(f'{path.relative_to(ROOT)}: missing {href}')
            elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                errors.append(f'{path.relative_to(ROOT)}: missing anchor {href}')
    for cid in ids:
        page = pages[ROOT/'cases'/cid/'index.html']
        for anchor in ['vc-inputs', 'vc-functions', 'vc-outputs', 'vc-outcomes', 'vc-project']:
            if anchor not in page.ids: errors.append(f'{cid}: missing four-cut section {anchor}')
    assert not errors, '\n'.join(errors)
    print(f'PASS: {len(cases)} unique cases; {len(pages)} pages; local links, anchors, IDs and four-cut sections valid.')

if __name__ == '__main__': main()
