#!/usr/bin/env python3
"""Build four linked founding PDFs from canonical reader HTML; no private inputs.

Run: python3 oita-mirai-mobility-consortium/read/founding/build_documents.py
Requires lxml, fontTools[woff], reportlab.
"""
import json,hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from html import escape
from lxml import html
from fontTools.ttLib import TTFont as Font
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate,PageTemplate,Frame,Paragraph,Spacer,Table,TableStyle,PageBreak,Image,CondPageBreak,KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader

BASE=Path(__file__).resolve().parents[2]
FONTDIR=BASE/'read/main/assets'
OUTPUT=BASE/'documents'
W,H,PAD=595.276,841.89,28
WIDTH=W-2*PAD
PINK,INK,ACCENT,SOFT=map(HexColor,['#f2f5f7','#102e53','#244d78','#ffffff'])
ORIGIN='https://mobilitydlab.com'
ST={}
CHAPTER_PAGES={}

class LinkedImage(Image):
    def draw(self):
        super().draw()
        self.canv.linkURL(self.link,(0,0,self.drawWidth,self.drawHeight),relative=1,thickness=0)

def href(s):return ORIGIN+s if s.startswith('/') else s
def inline(el):
    out=escape(el.text or '')
    for child in el:
        c=inline(child)
        if child.tag=='br':c='<br/>'
        elif child.tag in ('b','strong'):c=f'<b>{c}</b>'
        elif child.tag=='a':c=f'<a href="{escape(href(child.get("href","")),quote=True)}" color="#244d78"><u>{c}</u></a>'
        out+=c+escape(child.tail or '')
    return out.strip()

def prepare_fonts(tmp):
    for label,weight in [('JP','regular'),('JP-Bold','black')]:
        f=Font(FONTDIR/f'proposal-jp-{weight}.woff');f.flavor=None
        for record in f['name'].names:
            if record.nameID in [1,4,6]:record.string=f'NotoSansJPProposal-{weight}'.encode(record.getEncoding(),errors='replace')
        p=Path(tmp)/f'{weight}.ttf';f.save(p);pdfmetrics.registerFont(TTFont(label,str(p)))
    pdfmetrics.registerFontFamily('JP',normal='JP',bold='JP-Bold',italic='JP',boldItalic='JP-Bold')
    def make(name,size,leading,bold=False,**kw):return ParagraphStyle(name,fontName='JP-Bold' if bold else 'JP',fontSize=size,leading=leading,textColor=INK,wordWrap='CJK',spaceAfter=6,**kw)
    ST.update(body=make('body',10.5,16.5),note=make('note',9,14),h3=make('h3',16,23,True,spaceBefore=10,keepWithNext=True),label=make('label',10,15,True,keepWithNext=True),large=make('large',19,27,True),title=make('title',27,37,True,keepWithNext=True),section=make('section',22,31,True,keepWithNext=True),number=make('number',28,34,True),lead=make('lead',13,21,True,keepWithNext=True))

def para(el,key='body'):
    c=inline(el)
    if el.tag in ('b','strong'):c=f'<b>{c}</b>'
    if el.tag=='a':c=f'<a href="{escape(href(el.get("href","")),quote=True)}" color="#244d78"><u>{c}</u></a>'
    return Paragraph(c,ST[key])

def boxed(cols,width,gap=12):
    cw=(width-gap*(len(cols)-1))/len(cols);cells=[];widths=[]
    for i,col in enumerate(cols):
        if i:cells.append('');widths.append(gap)
        cells.append(col or [Spacer(1,1)]);widths.append(cw)
    t=Table([cells],colWidths=widths);cmd=[('VALIGN',(0,0),(-1,-1),'TOP')]
    for i in range(0,len(cells),2):cmd += [('BOX',(i,0),(i,0),.6,INK),('BACKGROUND',(i,0),(i,0),SOFT),('LEFTPADDING',(i,0),(i,0),12),('RIGHTPADDING',(i,0),(i,0),12),('TOPPADDING',(i,0),(i,0),12),('BOTTOMPADDING',(i,0),(i,0),5)]
    t.setStyle(TableStyle(cmd));return [t,Spacer(1,12)]

def render(el,width):
    cls=set(el.get('class','').split())
    if el.tag in ('nav','script','style','details','summary'):return []
    if 'rules-article' in cls:
        flows=[]
        for child in el:flows+=render(child,width)
        return [KeepTogether(flows)] if len(el.findall('p'))<=3 and el.find('ol') is None else flows
    if 'pvmv-block' in cls:
        flows=[]
        for child in el:flows+=render(child,width)
        return [KeepTogether(flows)]
    if 'permission-line' in cls:return [para(el,'h3')]
    if el.tag in ('p','h3','h4','strong','a','span','dt','dd'):
        if 'flow-arrow' in cls:return []
        key='h3' if el.tag in ('h3','h4') else 'body'
        if cls & {'note','source-link'}:key='note'
        if 'eyebrow' in cls or el.tag=='dt':key='label'
        if el.tag=='p' and 'fee' in cls:return [Paragraph(f'<font size="54"><b>{escape(el.find("b").text_content())}</b></font> <b>{escape(el.find("strong").text_content())}</b>',ParagraphStyle('fee',parent=ST['body'],leading=63,spaceBefore=8))]
        return [para(el,key)] if el.text_content().strip() else []
    if el.tag=='figure' and el.xpath('.//img'):
        img=el.xpath('.//img')[0];p=BASE.parent/img.get('src').lstrip('/');iw,ih=ImageReader(str(p)).getSize();im=LinkedImage(str(p),width=width,height=width*ih/iw);im.link=href(img.get('src'));out=[im,Spacer(1,9)]
        if el.find('figcaption') is not None:out.append(para(el.find('figcaption'),'note'))
        return out
    if el.tag=='table':
        trs=el.xpath('.//tr');n=len(trs[0]);fractions={2:[.32,.68],3:[.22,.39,.39],4:[.12,.24,.24,.40]}.get(n,[1/n]*n)
        if 'founder-roles' in cls:fractions=[.08,.36,.56]
        t=Table([[para(c) for c in tr] for tr in trs],colWidths=[width*x for x in fractions],repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,HexColor('#afc2d8')),('BACKGROUND',(0,0),(-1,0),HexColor('#e8f0fc')),('BACKGROUND',(0,1),(-1,-1),SOFT),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),3)]));return [t,Spacer(1,12)]
    if el.tag in ('ol','ul'):
        if 'training-flow' in cls:
            items=[Paragraph(f'<b>{i:02}</b><br/>{inline(c)}',ST['body']) for i,c in enumerate(el,1)];rows=[items[i:i+3] for i in range(0,len(items),3)];t=Table(rows,colWidths=[width/3]*3)
            t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,INK),('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,-1),SOFT),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),9)]));return [t,Spacer(1,12)]
        out=[]
        for n,li in enumerate(el,1):
            if li.tag!='li':continue
            if cls & {'decision-flow','consultation-list'}:
                flows=[]
                for c in li.find('div'):flows+=render(c,width-56)
                row=[Paragraph(li.find('b').text_content(),ST['number']),flows];nw=56
            else:nw=34;row=[Paragraph(f'{n:02}' if el.tag=='ol' else '-',ST['label']),para(li)]
            t=Table([row],colWidths=[nw,width-nw]);t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LINEABOVE',(0,0),(-1,-1),.4,INK),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),3)]));out.append(t)
        return out+[Spacer(1,6)]
    if cls & {'split-row','fee-options','milestones','meeting-topics','accounts','purpose-flow'}:
        children=[c for c in el if 'flow-arrow' not in c.get('class','')]
        if 'accounts' in cls and len(children)>2 and 'accounts-three' not in cls:
            out=[]
            for c in children:out+=boxed([render(c,width-24)],width)
            return out
        cw=(width-12*(len(children)-1))/len(children)-24;return boxed([render(c,cw) for c in children],width)
    if cls & {'joint-leaders','secretariat-lead','working-team'}:
        out=[]
        for c in el:
            if c.tag=='div':out += [para(x,'large') for x in c]
            else:out += render(c,width-24)
        return boxed([out],width)
    out=[]
    if el.text and el.text.strip():out.append(Paragraph(escape(el.text),ST['body']))
    for c in el:out+=render(c,width)
    return out

class Document(BaseDocTemplate):
    def __init__(self,path,title,print_mode=False,total=0):
        super().__init__(str(path),pagesize=(W,H),leftMargin=PAD,rightMargin=PAD,topMargin=55,bottomMargin=62,title=title,author='トヨタカローラ大分・モビリティデザインラボ')
        self.label=title;self.print_mode=print_mode;self.total=total
        self.addPageTemplates(PageTemplate('reader',[Frame(PAD,62,WIDTH,H-117,id='body',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=self.paint_page))
    def paint_page(self,c,d):
        date=json.loads((OUTPUT/'founding.json').read_text())['updated'].replace('-', '.')
        c.saveState();c.setFillColor(HexColor('#ffffff') if self.print_mode else PINK);c.rect(0,0,W,H,fill=1,stroke=0)
        c.setFillColor(INK);c.setFont('JP-Bold',8);c.drawString(PAD,H-26,'大分未来モビリティコンソーシアム');c.drawRightString(W-PAD,H-26,'（設立準備案）')
        c.bookmarkPage(f'page-{d.page}')
        c.setFont('JP',8)
        if d.page>1:
            c.drawString(PAD,47,'目次へ戻る');c.linkRect('', 'contents',(PAD,44,PAD+60,56),relative=0,thickness=0)
            c.drawString(PAD+85,47,'前のページ');c.linkRect('',f'page-{d.page-1}',(PAD+85,44,PAD+140,56),relative=0,thickness=0)
        if self.total and d.page<self.total:
            c.drawRightString(W-PAD,47,'次のページ');c.linkRect('',f'page-{d.page+1}',(W-PAD-60,44,W-PAD,56),relative=0,thickness=0)
        c.setStrokeColor(HexColor('#afc2d8'));c.line(PAD,37,W-PAD,37);c.setFont('JP',7.5);c.drawString(PAD,21,self.label+' / '+date);c.drawRightString(W-PAD,21,str(d.page));c.restoreState()
    def afterFlowable(self,f):
        if isinstance(f,Paragraph) and hasattr(f,'bookmark'):
            self.canv.bookmarkPage(f.bookmark);self.canv.addOutlineEntry(f.getPlainText(),f.bookmark,level=0,closed=False);CHAPTER_PAGES[f.bookmark]=self.page

def make_story(root,slug,title,known):
    sections=root.xpath('//section[contains(@class,"reader-section")]');story=[]
    date=json.loads((OUTPUT/'founding.json').read_text())['updated'];year,month,day=map(int,date.split('-'))
    heading=Paragraph(escape(title),ST['title']);heading.bookmark='contents';story.append(heading)
    reference=next((r for r in json.loads((OUTPUT/'founding.json').read_text()).get('reference_documents',[]) if r['key']==slug),None)
    if reference:
        story.append(Paragraph(f'参考資料 / {year}年{month}月{day}日整理',ST['note']))
    else:
        story.append(Paragraph(f'コンソーシアム構想 {year}年{month}月{day}日' if slug=='main' else f'設立準備案 {year}年{month}月{day}日',ST['note']))
        story.append(Paragraph('参画・就任・費用負担は、関係者の了承と設立時の決定を経て確定します。',ST['note']))
    story.extend([Spacer(1,12),Paragraph('目次',ST['h3'])])
    for n,sec in enumerate(sections,1):
        dest=sec.get('id');label=sec.xpath('./header/h2')[0].text_content();num=known.get(dest,'-')
        story.append(Paragraph(f'<a href="#{dest}" color="#102e53"><b>{n:02} {escape(label)}</b> / p. {num}</a>',ST['body']))
    story.append(PageBreak())
    for n,sec in enumerate(sections,1):
        if n>1:story.append(PageBreak() if slug=='main' or sec.get('data-pdf-start')=='page' else CondPageBreak(125))
        label=sec.xpath('./header/h2')[0];heading=Paragraph(inline(label),ST['section']);heading.bookmark=sec.get('id');story.append(heading)
        lead=sec.xpath('./header/p')
        if lead:story.append(para(lead[0],'lead'))
        body=sec.xpath('./div[contains(@class,"chapter-body")]')[0]
        for child in body:story.extend(render(child,WIDTH))
        if slug=='main':
            while story and isinstance(story[-1],Spacer):story.pop()
        if slug!='main':story.append(Spacer(1,16))
    return story

def build(slug,path,title,print_mode=False):
    root=html.fromstring(path.read_text());known={};total=0;out=OUTPUT/(slug+('-print' if print_mode else '')+'.pdf')
    for attempt in range(4):
        CHAPTER_PAGES.clear();Document(out,title,print_mode,total).build(make_story(root,slug,title,known));actual={k:v for k,v in CHAPTER_PAGES.items() if k!='contents'}
        import fitz
        with fitz.open(out) as rendered:new_total=len(rendered)
        if actual==known and new_total==total:break
        known=actual;total=new_total
    else:raise RuntimeError('Chapter pagination did not converge: '+slug)
    print(out);return actual

def build_reference_documents(sources):
    import fitz
    records=[]
    for source in sources:
        slug=source['key'];path=BASE/source['path']/'index.html'
        chapters=build(slug,path,source['title']);assert build(slug,path,source['title'],True)==chapters
        record=dict(source);record.update(pages=len(fitz.open(OUTPUT/f'{slug}.pdf')),chapter_pages=chapters,sha256=hashlib.sha256((OUTPUT/f'{slug}.pdf').read_bytes()).hexdigest(),print_pdf=f'documents/{slug}-print.pdf',print_pages=len(fitz.open(OUTPUT/f'{slug}-print.pdf')),print_sha256=hashlib.sha256((OUTPUT/f'{slug}-print.pdf').read_bytes()).hexdigest())
        records.append(record)
    return records

def sync_page_counts(records):
    counts={r['key']:r['pages'] for r in records}
    for path in BASE.rglob('*.html'):
        source=path.read_text()
        if 'data-pdf-key' not in source:continue
        root=html.fromstring(source);changed=False
        for el in root.xpath('//*[@data-pdf-key]'):
            key=el.get('data-pdf-key')
            if key in counts:
                import re
                current=el.text or ''
                new=re.sub(r'\d+\s*(ページ|p)',lambda m:str(counts[key])+m.group(1),current)
                if new!=current:el.text=new;changed=True
        if changed:path.write_text('<!DOCTYPE html>\n'+html.tostring(root,encoding='unicode',method='html')+'\n')

def main():
    OUTPUT.mkdir(exist_ok=True)
    with TemporaryDirectory() as tmp:
        prepare_fonts(tmp)
        manifest=json.loads((OUTPUT/'founding.json').read_text());records=[]
        previous=json.loads((OUTPUT/'document-manifest.json').read_text()) if (OUTPUT/'document-manifest.json').exists() else {}
        for slug,title in [('main','構想説明書・設立趣意書'),('members','発起人・会員・役員名簿'),('rules','規約'),('secretariat','事務局の役割分担・会計')]:
            path=BASE/'read/main/index.html' if slug=='main' else BASE/f'{slug}/index.html'
            chapter_pages=build(slug,path,title);print_chapters=build(slug,path,title,True);assert print_chapters==chapter_pages
            import fitz
            with fitz.open(OUTPUT/f'{slug}.pdf') as pdf:pages=len(pdf)
            record=next(dict(x) for x in manifest['documents'] if x['key']==slug);record.update(pages=pages,chapter_pages=chapter_pages,sha256=hashlib.sha256((OUTPUT/f'{slug}.pdf').read_bytes()).hexdigest(),print_pdf=f'documents/{slug}-print.pdf',print_pages=pages,print_sha256=hashlib.sha256((OUTPUT/f'{slug}-print.pdf').read_bytes()).hexdigest());records.append(record)
        references=build_reference_documents(manifest.get('reference_documents',[]))
        previous.update(version=manifest['version'],target_date=manifest['target_date'],target_status=manifest['target_status'],documents=records,reference_documents=references)
        (OUTPUT/'document-manifest.json').write_text(json.dumps(previous,ensure_ascii=False,indent=2)+'\n')
        sync_page_counts(records+references)

if __name__=='__main__':main()
