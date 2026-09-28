"""Merge independently researched, validated case bundles without duplication.

Usage: python3 integrate_additions.py /absolute/path/to/additions-group.json [...]
Only public case/chain/fit/entry fields are persisted; private review notes are not.
"""
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def main(paths):
    cases=json.loads((ROOT/'data/cases.json').read_text())
    chains=json.loads((ROOT/'data/value-chains.json').read_text())
    fits=json.loads((ROOT/'data/learning-case-fit.json').read_text())
    entries=json.loads((ROOT/'data/entries.json').read_text())
    groups=[(cases,'id'),(chains,'id'),(fits,'caseId')]
    records=[]
    for path in paths:
        records.extend(json.loads(Path(path).read_text()))
    ids=[r['case']['id'] for r in records]
    assert len(ids)==len(set(ids)), 'Duplicate addition id in source bundles'
    for r in records:
        c=r['case'];cid=c['id']
        assert cid==r['chain']['id']==r['fit']['caseId']
        assert cid!='woven-city', 'Excluded case'
        assert r['fit']['unit'] in {'place','organization','district','program','network'}, cid
        assert set(r['fit']['exits']) <= {'purchase','public-service','local-operation','education','research','licensing'}, cid
        assert not any(d['name']==c['name'] and d['id']!=cid for d in cases), 'Duplicate case name: '+c['name']
        c['photoPending']=True
        for (target,key),value in zip(groups,[c,r['chain'],r['fit']]):
            index=next((i for i,d in enumerate(target) if d[key]==cid),None)
            if index is None:target.append(value)
            else:target[index]=value
        entries[cid]=r['entry']
    for filename,value in [('cases',cases),('value-chains',chains),('learning-case-fit',fits),('entries',entries)]:
        (ROOT/f'data/{filename}.json').write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    print(f'Merged {len(records)} researched records; {len(cases)} unique articles.')

if __name__=='__main__':
    main(sys.argv[1:])
