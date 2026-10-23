"""Release regression checks for the eight-step reading guide."""
import json
import re
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path(__file__).resolve().parent

def main():
    cases=json.loads((ROOT/'data/cases.json').read_text())
    axes=json.loads((ROOT/'data/facility-axes.json').read_text())
    steps=json.loads((ROOT/'data/step-guide.json').read_text())
    assert len(cases)==115 and set(axes)=={c['id'] for c in cases}
    home=(ROOT/'index.html').read_text()
    assert home.count('class="step-home-card"')==8
    assert home.index('class="step-home"') < home.index('data-explorer')
    assert home.count('class="case-card"')==115
    assert home.count('class="facility-axes"')==115
    for c in cases:
        sources={s['id'] for s in c['sources']}
        for key in ['hard','soft','partners']:
            assert axes[c['id']][key]['text']
            assert set(axes[c['id']][key]['refs'])<=sources
        detail=(ROOT/'cases'/c['id']/'index.html').read_text()
        assert detail.count('id="facility-overview"')==1
        assert 'class="facility-axes detailed"' in detail
        for anchor in ['vc-inputs','vc-functions','vc-outputs','vc-outcomes','vc-project','evidence-sources']:
            assert f'id="{anchor}"' in detail
    for s in steps:
        i=s['step'];page=(ROOT/f'learn/step-{i:02d}/index.html').read_text()
        assert page.count('<h1')==1
        assert page.count('aria-current="page"')==1
        assert page.count('class="step-more"')==1
        before=page.split('<details class="step-more">')[0]
        assert before.count('class="step-case"')==2
        actual=set(re.findall(r'class="step-case" data-case-id="([^"]+)"',page))
        expected={c['id'] for c in cases if i in c.get('stages',[c['stage']])}|{c['id'] for c in s['cases']}
        assert actual==expected,(i,expected-actual)
        assert f'data-workbook="step-{i:02d}"' in page
        assert 'data-export="json"' in page and 'data-import' in page
        assert '<details class="step-more" open' not in page
        assert 'window.ATLAS_WORKBOOKS=' in page
        print(f'STEP {i:02d}: 2 featured + {len(actual)-2} expandable cases; worksheet retained')
    print('PASS: eight-step guide, all 115 three-axis summaries, source references and worksheets')
if __name__=='__main__':main()
