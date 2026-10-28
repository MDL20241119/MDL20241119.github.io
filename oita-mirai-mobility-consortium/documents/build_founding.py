#!/usr/bin/env python3
"""Validate/synchronize the four canonical HTML documents and shared metadata.

The complete articles are authored in read/main/, members/, rules/, secretariat/.
This command keeps navigation, versioned downloads and page metadata together,
without regenerating a shorter or older set of articles over reviewed content.
Run build_pdf.py --all afterwards to rebuild PDFs and document-manifest.json.
"""
from pathlib import Path
from lxml import html
import argparse,json,re

ROOT=Path(__file__).resolve().parents[1]
DATA=json.loads((ROOT/'documents/founding.json').read_text())

def build():
    expected={'main','members','rules','secretariat'}
    assert {x['key'] for x in DATA['documents']}==expected
    assert DATA['annual_fee_yen']==100000 and DATA['votes_per_organization']==1
    assert DATA['plan_deadline']=='2027-02-26'
    assert len(DATA['founder_groups'])==5
    assert DATA['target_date']=='2027-01-26'
    assert DATA['target_date_label']=='2027年1月26日'
    assert DATA['sanrio_relationship']=='県の後援＝サンリオの利用許諾'
    assert '契約' in DATA['sanrio_scope']
    for doc in DATA['documents']:
        p=ROOT/doc['path']/'index.html';s=p.read_text();r=html.fromstring(s)
        assert r.xpath('//script[contains(@src,"/entry.js")]'),p
        assert r.xpath('//meta[@name="robots"]/@content')==['noindex,nofollow,noarchive'],p
        assert r.xpath('//nav[@class="founding-doc-nav"]'),p
        text=r.xpath('//main')[0].text_content()
        assert '未決' in s,p
        assert DATA['target_date_label'] in r.text_content(),p
        assert '県の後援≠' not in text,p
        assert '1月26日は日程候補' not in text and '1月26日は候補' not in text,p
        if doc['key']=='main':assert DATA['sanrio_relationship'] in text,p
        for a in r.xpath('//a[@href]'):
            href=a.get('href')
            if href.startswith('/oita-mirai-mobility-consortium/documents/') and '.pdf' in href:
                path=href.split('?')[0];a.set('href',path+'?v='+DATA['version'])
        p.write_text('<!DOCTYPE html>\n'+html.tostring(r,encoding='unicode',method='html')+'\n')
    print('Canonical documents validated; shared policy:',DATA['version'])

def build_fonts(variable_path):
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont
    from fontTools import subset
    paths=[ROOT/d['path']/'index.html' for d in DATA['documents']]
    paths += [ROOT/x for x in ['organization/index.html','guide/index.html','index.html','concept/index.html']]
    text=''.join(html.fromstring(p.read_text()).text_content() for p in paths)
    for name,weight in [('regular',400),('black',900)]:
        path=ROOT/f'read/main/assets/proposal-jp-{name}.woff'
        old=TTFont(path);text += ''.join(map(chr,old.getBestCmap()));old.close()
        font=instantiateVariableFont(TTFont(variable_path),{'wght':weight},inplace=True)
        options=subset.Options();options.flavor='woff'
        options.notdef_glyph=options.notdef_outline=options.recommended_glyphs=True
        sub=subset.Subsetter(options=options);sub.populate(text=text);sub.subset(font)
        for record in font['name'].names:
            if record.nameID in [1,4,6]:record.string=f'NotoSansJPProposal-{name}'.encode(record.getEncoding(),errors='replace')
        font.flavor='woff';font.save(path);print('Font:',name,len(font.getBestCmap()),'characters')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--font-variable',type=Path)
    args=parser.parse_args();build()
    if args.font_variable:build_fonts(args.font_variable)
