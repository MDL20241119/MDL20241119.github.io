"""Offline editorial integrity checks; run after build.py."""
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
import frontier

ROOT = Path(__file__).resolve().parent

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
    assert len(rows)==13
    assert Counter(c['lens'] for c in rows)=={'hard':4,'soft':5,'partners':4}
    assert {c[k]['number'] for c in rows for k in ['primaryStep','secondaryStep']}==set(range(1,9))
    assert all(c.get('statusLabel') and c.get('statusNote') for c in rows)
    page=(ROOT/'frontier/index.html').read_text();parsed=Parser(page)
    assert len(parsed.cards)==len(rows)==len(parsed.photos)
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
    home=(ROOT/'index.html').read_text()
    assert home.count('class="frontier-entry"')==1
    assert home.index('class="frontier-entry"')<home.index('class="step-home-grid"')
    assert 'href="frontier/"' in home and home.count('class="step-home-card"')==8
    assert (ROOT/'sitemap.xml').read_text().count('https://mobilitydlab.com/co-creation-atlas/frontier/')==1
    assert '共通仕様を公開・国際規格へ' in page and '実証終了（2023）' in page and '展開中' in page
    assert '<noscript>' in page
    assert len(json.loads((ROOT/'data/cases.json').read_text()))==115
    print('PASS: 13 source-backed selections, 3 axes, all 8 steps, statuses, photos, source/detail links, home entry and sitemap.')

if __name__=='__main__':main()
