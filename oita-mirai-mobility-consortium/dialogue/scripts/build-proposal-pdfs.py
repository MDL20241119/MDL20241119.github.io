#!/usr/bin/env python3
"""Build the eight complete regional-proposal PDFs from the adjacent HTML files.

Dependencies: Python 3.10+, beautifulsoup4, reportlab, Pillow, fonttools.
Install: python3 -m pip install beautifulsoup4 reportlab Pillow fonttools

Run from any directory:
  python3 build-proposal-pdfs.py --font-variable /path/to/NotoSansJP-variable.ttf

Use the full official Noto Sans JP variable TTF (SIL Open Font License 1.1):
https://github.com/google/fonts/tree/main/ofl/notosansjp
The font is a build dependency; no 9 MB font is copied into the website.
Alternatively pass static TrueType files with --font-regular and --font-bold.
The site WOFFs are partial CFF/TTF subsets, so they are not sufficient alone.

All paths for HTML, photos and output PDFs are relative to this script. The
extractor preserves substantive text, expanded details, photo captions/credits,
policy notes and source links. UI navigation/download/print controls are omitted.
It never fetches external URLs. Links in the PDF point to the original sources.
A temporary JSON coverage manifest is optional via --qa-json PATH.
"""
from __future__ import annotations
import argparse, hashlib, html, io, json, re, tempfile
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote
from bs4 import BeautifulSoup, NavigableString, Tag
from PIL import Image as PILImage
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont as RLTTFont
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Flowable, KeepTogether

REGIONS=['beppu','yufuin','hiji','usa','kunisaki','usuki','oita','taiyonoie']
DIALOGUE=Path(__file__).resolve().parent.parent
ROOT=DIALOGUE.parent.parent
ORIGIN='https://mobilitydlab.com/oita-mirai-mobility-consortium/dialogue/'
A4=(595.2756,841.8898)
MARGIN=39
WIDTH=A4[0]-2*MARGIN
ORANGE=HexColor('#e68149'); DARKORANGE=HexColor('#a54b20'); INK=HexColor('#111111'); GRAY=HexColor('#555555'); LINE=HexColor('#cccccc'); PALE=HexColor('#fff2e8')


def normalize(text):return re.sub(r'\s+','',text)
def clean(text):return re.sub(r'\s+',' ',text).strip()


def initialize_fonts(args,tmp):
    if args.font_variable:
        from fontTools.ttLib import TTFont
        from fontTools.varLib.instancer import instantiateVariableFont
        paths=[]
        for weight in (500,900):
            f=TTFont(args.font_variable)
            instantiateVariableFont(f,{'wght':weight},inplace=True)
            p=tmp/f'NotoSansJP-{weight}.ttf';f.save(str(p));paths.append(p)
    elif args.font_regular and args.font_bold:
        paths=[Path(args.font_regular),Path(args.font_bold)]
    else:
        raise SystemExit('Provide --font-variable FULL_NotoSansJP.ttf or both --font-regular and --font-bold.')
    for name,path in zip(('JP','JPB'),paths):pdfmetrics.registerFont(RLTTFont(name,str(path)))
    pdfmetrics.registerFontFamily('JP',normal='JP',bold='JPB',italic='JP',boldItalic='JPB')
    # Fail on unsupported characters instead of silently writing missing-glyph boxes.
    from fontTools.ttLib import TTFont
    cmap=set(TTFont(str(paths[0])).getBestCmap())
    return cmap


def styles():
    b=dict(fontName='JP',fontSize=10.5,leading=16,wordWrap='CJK',splitLongWords=1,allowWidows=0,allowOrphans=0,textColor=INK)
    result={'body':ParagraphStyle('Body',**b,spaceAfter=4),
    'lead':ParagraphStyle('Lead',**{**b,'fontName':'JPB','fontSize':12,'leading':19},spaceAfter=10),
    'small':ParagraphStyle('Small',**{**b,'fontSize':9,'leading':13.5,'textColor':GRAY},spaceAfter=4),
    'caption':ParagraphStyle('Caption',**{**b,'fontSize':9,'leading':13,'textColor':GRAY},spaceAfter=0),
    'h1':ParagraphStyle('H1',**{**b,'fontName':'JPB','fontSize':26,'leading':35},spaceAfter=16,keepWithNext=True),
    'h2':ParagraphStyle('H2',**{**b,'fontName':'JPB','fontSize':18,'leading':26},spaceBefore=12,spaceAfter=8,keepWithNext=True),
    'h3':ParagraphStyle('H3',**{**b,'fontName':'JPB','fontSize':13.5,'leading':21},spaceBefore=8,spaceAfter=5,keepWithNext=True),
    'h4':ParagraphStyle('H4',**{**b,'fontName':'JPB','fontSize':11.5,'leading':18},spaceBefore=6,spaceAfter=4,keepWithNext=True),
    'label':ParagraphStyle('Label',**{**b,'fontName':'JPB','fontSize':10,'leading':15,'textColor':DARKORANGE},spaceBefore=2,spaceAfter=7,keepWithNext=True)}
    return result


class ContainedPhoto(Flowable):
    """Show the complete existing image, without additional cropping."""
    def __init__(self,path,width,height):
        Flowable.__init__(self);self.path=Path(path);self.width=width;self.height=height
    def draw(self):
        self.canv.setFillColor(HexColor('#fafafa'));self.canv.rect(0,0,self.width,self.height,fill=1,stroke=0)
        with PILImage.open(self.path) as im:
            w,h=im.size;scale=min(self.width/w,self.height/h)
            # ReportLab cannot decode WebP itself; use an in-memory PNG at print resolution.
            target=(max(1,round(w*scale*2.5)),max(1,round(h*scale*2.5)))
            im=im.convert('RGB');im.thumbnail(target,PILImage.Resampling.LANCZOS)
            buf=io.BytesIO();im.save(buf,format='JPEG',quality=85,optimize=True);buf.seek(0)
            self.canv.drawImage(ImageReader(buf),(self.width-w*scale)/2,(self.height-h*scale)/2,width=w*scale,height=h*scale,mask='auto')


class Rule(Flowable):
    def __init__(self,width=WIDTH,color=LINE,thickness=.7):Flowable.__init__(self);self.width=width;self.height=7;self.color=color;self.thickness=thickness
    def draw(self):self.canv.setStrokeColor(self.color);self.canv.setLineWidth(self.thickness);self.canv.line(0,3,self.width,3)


class Extractor:
    SKIP_CLASSES={'flow-arrow','idea-number','flow-number','proposal-download-actions'}
    SMALL_CLASSES={'flow-small','policy-small','policy-period','policy-date','policy-eyebrow','idea-eyebrow','flow-kicker','photo-note','credits','credit-row','proposal-status','separation','conditions'}
    def __init__(self,soup,slug,style):
        self.soup=soup;self.slug=slug;self.style=style;self.url=ORIGIN+slug+'.html';self.covered=set();self.link_urls=set();self.units=[]
    def skipped(self,node):
        if not isinstance(node,Tag):return False
        return node.name in {'script','style','nav','button'} or node.get('aria-hidden')=='true' or bool(self.SKIP_CLASSES.intersection(node.get('class',[])))
    def mark(self,node):
        for x in node.descendants if isinstance(node,Tag) else [node]:
            if isinstance(x,NavigableString) and clean(str(x)):
                # A leaf in skipped decorative/UI content is intentionally excluded.
                if any(self.skipped(p) for p in x.parents if p is not node):continue
                self.covered.add(id(x))
    def inline(self,node):
        if isinstance(node,NavigableString):self.covered.add(id(node));return html.escape(str(node))
        if not isinstance(node,Tag) or self.skipped(node):return ''
        if node.name=='br':return '<br/>'
        if node.name in {'wbr','img'}:return ''
        value=''.join(self.inline(x) for x in node.children)
        if node.name in {'b','strong'}:return '<b>'+value+'</b>'
        if node.name=='a' and node.get('href'):
            href=urljoin(self.url,node['href']);self.link_urls.add(href)
            return '<link href="'+html.escape(href,quote=True)+'" color="#a54b20">'+value+'</link>'
        return value
    def paragraph(self,node,sty='body',prefix=''):
        value=self.inline(node).strip()
        if not clean(BeautifulSoup(value,'html.parser').get_text()):return []
        self.units.append({'text':node.get_text(' ',strip=True),'kind':sty})
        return [Paragraph(prefix+value,self.style[sty])]
    def flow(self,node,small=False):
        if isinstance(node,NavigableString):
            if clean(str(node)):
                self.covered.add(id(node));self.units.append({'text':clean(str(node)),'kind':'body'})
                return [Paragraph(html.escape(clean(str(node))),self.style['small' if small else 'body'])]
            return []
        if not isinstance(node,Tag) or self.skipped(node):return []
        classes=set(node.get('class',[]));small=small or bool(classes.intersection(self.SMALL_CLASSES))
        if node.name in {'img','figure'}:return [] # All photos and captions are on the cover/gallery.
        if node.name in {'h1','h2','h3','h4'}:return self.paragraph(node,node.name)
        if node.name=='summary':return self.paragraph(node,'h4')
        if node.name in {'p','small','figcaption'}:return self.paragraph(node,'small' if small or node.name=='small' else 'body')
        if node.name=='a':return self.paragraph(node,'small' if small else 'body')
        if node.name in {'ul','ol'}:
            out=[]
            for i,li in enumerate(node.find_all('li',recursive=False),1):
                if self.skipped(li):continue
                prefix=(str(i)+'. ' if node.name=='ol' else '・')
                if not li.find(['p','div','h1','h2','h3','h4','ul','ol','figure','details'],recursive=False):out+=self.paragraph(li,'small' if small else 'body',prefix)
                else:out+=self.flow(li,small)
            return out
        if node.name in {'strong','span','b','time'}:return self.paragraph(node,'small' if small else 'body')
        if 'flow-place' in classes:
            return self.paragraph(node,'body')
        if 'flow-step-top' in classes:
            number=node.parent.select_one('.flow-number')
            return self.paragraph(node,'label',(html.escape(number.get_text(strip=True))+' / ') if number else '')
        if 'flow-step' in classes:
            return [Rule(color=ORANGE,thickness=2)]+sum((self.flow(ch,small) for ch in node.children),[])+[Spacer(1,7)]
        if 'chapter' in classes:
            return self.paragraph(node,'label')
        if 'credit-row' in classes:
            # Keep each author/license/source row together where possible.
            content=sum((self.flow(ch,True) for ch in node.children),[])
            return [KeepTogether(content)]
        return sum((self.flow(ch,small) for ch in node.children),[])
    def photo_gallery(self):
        figures=self.soup.select('main figure')
        figures=[fig for fig in figures if fig.find('img')]
        columns=3 if len(figures)>=5 else 2
        gap=10;iw=(WIDTH-gap*(columns-1))/columns
        out=[];cells=[];n=0
        def add_row(row):
            while len(row)<columns:row.append([])
            t=Table([row],colWidths=[iw+gap]*columns)
            t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),gap),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),10)]))
            out.append(t)
        for fig in figures:
            img=fig.find('img');src=img.get('src','')
            path=(ROOT/unquote(src).lstrip('/')) if src.startswith('/') else (DIALOGUE/unquote(src))
            if not path.is_file():raise FileNotFoundError(path)
            caption=fig.find('figcaption');cap=caption.get_text(' ',strip=True) if caption else img.get('alt','')
            if caption:self.mark(caption)
            cells.append([ContainedPhoto(path,iw,115 if columns==3 else 125),Spacer(1,5),Paragraph(html.escape(cap),self.style['caption'])]);n+=1
            if len(cells)==columns:add_row(cells);cells=[]
        if cells:add_row(cells)
        return out,n
    def coverage(self):
        missed=[]
        for leaf in self.soup.select_one('main').descendants:
            if not isinstance(leaf,NavigableString) or not clean(str(leaf)):continue
            if any(self.skipped(p) for p in leaf.parents):continue
            if id(leaf) not in self.covered:missed.append(clean(str(leaf)))
        return missed


def build(slug,args,cmap):
    source=DIALOGUE/f'{slug}.html';raw=source.read_text(encoding='utf-8');soup=BeautifulSoup(raw,'html.parser');s=styles();ex=Extractor(soup,slug,s)
    main=soup.select_one('main');title=soup.select_one('main h1').get_text(' ',strip=True)
    all_visible=''.join(str(n) for n in main.descendants if isinstance(n,NavigableString) and not any(ex.skipped(p) for p in n.parents))
    missing=sorted({c for c in all_visible if not c.isspace() and ord(c) not in cmap})
    if missing:raise ValueError(f'{slug}: font missing {missing}')
    region=soup.select_one('main .region strong').get_text(' ',strip=True)
    def page(canvas,doc):
        w,h=A4;canvas.saveState();canvas.setFillColor(INK);canvas.setFont('JPB',10);canvas.drawString(MARGIN,h-26,'MOBILITY DESIGN LAB');canvas.setFont('JP',8);canvas.drawRightString(w-MARGIN,h-26,region+' ／ 企画例・検討用ドラフト')
        canvas.setStrokeColor(LINE);canvas.setLineWidth(.7);canvas.line(MARGIN,h-34,w-MARGIN,h-34);canvas.line(MARGIN,31,w-MARGIN,31)
        canvas.setFont('JP',7.6);canvas.setFillColor(GRAY);canvas.drawString(MARGIN,18,'地域の皆さんと具体化する共創提案');canvas.drawRightString(w-MARGIN,18,f'{doc.page}')
        canvas.linkURL(ex.url,(MARGIN,10,w-MARGIN-20,28),relative=0);canvas.restoreState()
    dest=DIALOGUE/'pdf'/f'{slug}-proposal.pdf';dest.parent.mkdir(exist_ok=True)
    doc=BaseDocTemplate(str(dest),pagesize=A4,leftMargin=MARGIN,rightMargin=MARGIN,topMargin=48,bottomMargin=44,title=soup.title.get_text(),author='モビリティデザインラボ')
    doc.addPageTemplates([PageTemplate(id='default',frames=[Frame(MARGIN,44,WIDTH,A4[1]-92,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0,id='normal')],onPage=page)])
    story=[]
    # 1. Original proposal opening + complete existing photo gallery.
    story+=ex.flow(main.find('header',recursive=False));story.append(Spacer(1,6));photos,count=ex.photo_gallery();story+=photos
    story.append(Paragraph('<link href="'+ex.url+'" color="#a54b20">Web版・最新の提案内容を開く ↗</link>',s['small']))
    story.append(Paragraph('写真の出典・利用条件は、本資料末尾に掲載しています。画像は全体を保持して縮小表示しています。',s['small']))
    story.append(PageBreak())
    # 2. Full four-stage relationship, including all details and related links.
    story+=ex.flow(main.select_one('.value-flow'));story.append(Spacer(1,8))
    # 3. All local proposals and additional hub concept.
    story.append(Paragraph('この地域で具体的に取り組むこと',s['h2']))
    if main.select_one('.hub-concept'):story+=ex.flow(main.select_one('.hub-concept'))
    story+=ex.flow(main.select_one('.three-fields'))
    sep=main.find('p',class_='separation',recursive=False)
    if sep:story+=ex.flow(sep)
    story.append(Spacer(1,8))
    # 4. Optional commons and all future-idea content.
    if main.select_one('.commons-overview'):story+=ex.flow(main.select_one('.commons-overview'))
    story+=ex.flow(main.select_one('.idea-section'));story.extend([Spacer(1,10),Rule(color=ORANGE,thickness=2)])
    # 5+. Complete policy, reference notes, source links, constraints and photo credits.
    story+=ex.flow(main.select_one('.policy-context'))
    footer=[Spacer(1,10),Rule(color=ORANGE,thickness=2),Paragraph('提案の条件・写真出典',s['h2'])]+ex.flow(main.find('footer',recursive=False))
    # Taiyo has additional official-organization links; keep its complete credits together.
    story+=([KeepTogether(footer)] if slug=='taiyonoie' else footer)
    missed=ex.coverage()
    if missed:raise ValueError(f'{slug}: unhandled source text {missed}')
    doc.build(story)
    return {'slug':slug,'source_sha256':hashlib.sha256(raw.encode()).hexdigest(),'pdf':str(dest.relative_to(DIALOGUE)),'source_text_leaf_coverage':'100%','semantic_units':len(ex.units),'photos':count,'source_link_count':len(ex.link_urls),'links':sorted(ex.link_urls),'unhandled_text':missed,'pdf_sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}


def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--font-variable');p.add_argument('--font-regular');p.add_argument('--font-bold');p.add_argument('--regions',nargs='+',choices=REGIONS,default=REGIONS);p.add_argument('--qa-json',type=Path)
    args=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='proposal-pdf-font-') as temp:
        cmap=initialize_fonts(args,Path(temp));results=[build(slug,args,cmap) for slug in args.regions]
    if args.qa_json:args.qa_json.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    for result in results:print(json.dumps({k:v for k,v in result.items() if k!='links'},ensure_ascii=False))
if __name__=='__main__':main()
