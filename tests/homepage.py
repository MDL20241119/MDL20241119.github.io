"""Static regression checks for the corporate homepage (standard library only)."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import subprocess

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.tags = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


page = Page((ROOT / 'index.html').read_text())
baseline = Page(subprocess.check_output(['git', 'show', '496c341:index.html'], cwd=ROOT, text=True))
ids = [attrs['id'] for _, attrs in page.tags if 'id' in attrs]
assert len(ids) == len(set(ids)), 'Duplicate IDs'
assert sum(tag == 'h1' for tag, _ in page.tags) == 1, 'Expected one H1'
assert sum(tag == 'main' for tag, _ in page.tags) == 1, 'Expected one main landmark'
for key in ['services', 'projects', 'tools', 'news', 'vision', 'contact', 'creative-case',
            'produce-case', 'mobility-case', 'tourism-case', 'yoko-elevator',
            'elevator-pricing', 'elevator-catalogs', 'elevator-consult']:
    assert key in ids, f'Missing stable anchor: {key}'
assert [ids.index(key) for key in ['services', 'projects', 'tools', 'news', 'vision', 'contact']] == sorted(
    ids.index(key) for key in ['services', 'projects', 'tools', 'news', 'vision', 'contact'])

tracked = set(subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', 'HEAD'], cwd=ROOT, text=True).splitlines())
for tag, attrs in page.tags:
    if tag == 'img':
        assert 'alt' in attrs, 'Image needs alternative text'
    if tag == 'a' and attrs.get('target') == '_blank':
        assert 'noopener' in attrs.get('rel', ''), 'External tab needs noopener'
    for key in ('href', 'src'):
        value = attrs.get(key, '')
        url = urlsplit(value)
        if not value or value == '#' or url.scheme or url.netloc:
            continue
        if not url.path:
            assert url.fragment in ids, f'Broken fragment: {value}'
            continue
        path = url.path + ('index.html' if url.path.endswith('/') else '')
        assert path in tracked or (ROOT / path).is_file(), f'Missing local target: {value}'

def content_links(p):
    return {a['href'] for t, a in p.tags if t == 'a' and a.get('href') and not a['href'].startswith(('#', 'mailto:'))}

assert content_links(baseline) <= content_links(page), 'An existing destination link was removed'
assert sum(t == 'li' and a.get('class') == 'news-item' for t, a in page.tags) == 13, 'Preserve news archive'
content = (ROOT / 'index.html').read_text()
for text in ['標準アプリ利用料', '維持・運用費', '運賃無料を意味しません',
             '個別の連携・実施内容には検討中', '公式計画ではなく', '収録データと設定条件']:
    assert text in content, f'Missing qualification: {text}'
for target in ['fukuoka-mobility/', 'oita-mobility/', 'oita-tourism/', 'e-palette/',
               'danchi-elevator/', 'danchi-elevator/detail/', 'shimonoseki-destination/']:
    assert target in content_links(page), f'Missing key destination: {target}'
print('PASS: hierarchy, legacy anchors, all previous destinations, 13 news items, image alt text, safety qualifications, local file paths')
