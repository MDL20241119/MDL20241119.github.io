#!/usr/bin/env python3
"""Check the municipal guide's lecture links and original six opportunities."""
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]

class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids, self.links, self.images, self.benefits = [], [], [], []
        self.robots = None
        self.image_alts = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'a' and 'href' in attrs:
            self.links.append(attrs['href'])
        if tag == 'img':
            self.images.append(attrs.get('src', ''))
            self.image_alts.append(attrs.get('alt'))
        if tag == 'h3' and 'aria-label' in attrs:
            self.benefits.append(attrs['aria-label'])
        if tag == 'meta' and attrs.get('name') == 'robots':
            self.robots = attrs.get('content')

text = (ROOT / 'guide.html').read_text(encoding='utf-8')
page = Page(text)
assert all(page.image_alts), 'Each visible guide image needs alt text'
assert page.robots == 'noindex,nofollow,noarchive', 'Preserve search exclusion'
assert len(page.ids) == len(set(page.ids)), 'Duplicate HTML id'
assert all(link[1:] in page.ids for link in page.links if link.startswith('#')), 'Broken fragment'
assert page.benefits == [
    'モビリティサービス企画', 'e-Paletteを活用したサービス開発', '自動運転実証',
    'アプリ開発・DX・AI活用', 'データ分析・改善', '車両管理・整備保守',
], 'The original six opportunities must remain'
assert all((ROOT / src).is_file() for src in page.images), 'Missing guide image'
assert '宮代陽之氏は登壇候補' not in text, 'Outdated speaker status'
assert '無料支援と分けて協議' in text, 'Keep implementation costs separate'
assert '車両の提供、実証地域への選定、補助金採択、事業化を保証するものではありません。' in text
assert all(date in text for date in ['2026年11月11日', '2026年12月2日'])
lectures = json.loads((ROOT / 'lectures.json').read_text(encoding='utf-8'))['lectures']
for lecture in lectures:
    assert lecture['page'] in page.links, f"Missing lecture page: {lecture['page']}"
    start = lecture['starts_at'][11:16]
    end = lecture['ends_at'][11:16]
    assert f'{start}–{end}' in text, f"Wrong lecture hours: {lecture['id']}"
    source = (ROOT / lecture['page']).read_text(encoding='utf-8')
    form_links = {link for link in Page(source).links if link.startswith('https://docs.google.com/forms/')}
    assert form_links and form_links.issubset(set(page.links)), f"Wrong registration: {lecture['id']}"
miyadai = next(item for item in lectures if item['id'] == 'lecture-20261202')
assert miyadai['registration']['url'] in page.links
assert miyadai['fee'] == 0 and miyadai['online_delivery'] is False
assert '参加費無料' in text and '配信なし（会場開催のみ）' in text
assert any(urlsplit(link).path == miyadai['resources']['participation_flyer'] for link in page.links)
assert any(urlsplit(link).path == 'participation-flyer.pdf' for link in page.links)
assert 'プログラム説明PDFは10月27日版です。' in text
print('PASS: six opportunities, both lectures/forms, resources, anchors, images and conditions')
