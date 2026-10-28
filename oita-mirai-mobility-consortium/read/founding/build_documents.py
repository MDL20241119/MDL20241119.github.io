#!/usr/bin/env python3
"""Build four linked founding PDFs from canonical reader HTML; no private inputs.

Run: python3 oita-mirai-mobility-consortium/read/founding/build_documents.py
Requires lxml, fontTools[woff], reportlab.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from html import escape
from lxml import html
from fontTools.ttLib import TTFont as Font
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate,PageTemplate,Frame,Paragraph,Spacer,Table,TableStyle,PageBreak,Image,CondPageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader

BASE=Path(__file__).resolve().parents[2]
FONTDIR=BASE/'read/main/assets'
OUTPUT=BASE/'documents'
W,H,PAD=720,960,44
WIDTH=W-2*PAD
PINK,INK,ACCENT,SOFT=map(HexColor,['#f7ecee','#111111','#bd3c39','#fff8fa'])
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
        elif child.tag=='a':c=f'<a href="{escape(href(child.get("href","")),quote=True)}" color="#bd3c39"><u>{c}</u></a>'
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
    ST.update(body=make('body',12.5,19),note=make('note',11,18),h3=make('h3',19,28,True,spaceBefore=10,keepWithNext=True),label=make('label',11,17,True,keepWithNext=True),large=make('large',22,31,True),title=make('title',35,47,True,keepWithNext=True),section=make('section',26,37,True,keepWithNext=True),number=make('number',35,40,True),lead=make('lead',15,25,True))

def para(el,key='body'):
    c=inline(el)
    if el.tag in ('b','strong'):c=f'<b>{c}</b>'
    if el.tag=='a':c=f'<a href="{escape(href(el.get("href","")),quote=True)}" color="#bd3c39"><u>{c}</u></a>'
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
    if 'permission-line' in cls:return [para(el,'h3')]
    if el.tag in ('p','h3','h4','strong','a','span','dt','dd'):
        if 'flow-arrow' in cls:return []
        key='h3' if el.tag in ('h3','h4') else 'body'
        if cls & {'note','source-link'}:key='note'
        if 'eyebrow' in cls or el.tag=='dt':key='label'
        if el.tag=='p' and 'fee' in cls:return [Paragraph(f'<font size="54"><b>{escape(el.find("b").text_content())}</b></font> <b>{escape(el.find("strong").text_content())}</b>',ParagraphStyle('fee',parent=ST['body'],leading=63,spaceBefore=8))]
        return [para(el,key)] if el.text_content().strip() else []
    if el.tag=='figure':
        img=el.xpath('.//img')[0];p=BASE.parent/img.get('src').lstrip('/');iw,ih=ImageReader(str(p)).getSize();im=LinkedImage(str(p),width=width,height=width*ih/iw);im.link=href(img.get('src'));out=[im,Spacer(1,9)]
        if el.find('figcaption') is not None:out.append(para(el.find('figcaption'),'note'))
        return out
    if el.tag=='table':
        trs=el.xpath('.//tr');n=len(trs[0]);fractions={2:[.32,.68],3:[.22,.39,.39],4:[.12,.24,.24,.40]}.get(n,[1/n]*n)
        t=Table([[para(c) for c in tr] for tr in trs],colWidths=[width*x for x in fractions],repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,HexColor('#a7989c')),('BACKGROUND',(0,0),(-1,0),HexColor('#eddee2')),('BACKGROUND',(0,1),(-1,-1),SOFT),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),3)]));return [t,Spacer(1,12)]
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
    def __init__(self,path,title):
        super().__init__(str(path),pagesize=(W,H),leftMargin=PAD,rightMargin=PAD,topMargin=72,bottomMargin=57,title=title,author='トヨタカローラ大分・モビリティデザインラボ');self.label=title
        self.addPageTemplates(PageTemplate('reader',[Frame(PAD,57,WIDTH,H-130,id='body',leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=self.page))
    def page(self,c,d):
        c.saveState();c.setFillColor(PINK);c.rect(0,0,W,H,fill=1,stroke=0);c.setFillColor(INK);c.setFont('JP-Bold',11);c.drawString(PAD,H-32,self.label);c.setFont('JP',10);c.drawRightString(W-PAD,H-32,'設立協議用・正式承認前 / 2026.10.28');c.setStrokeColor(INK);c.line(PAD,H-48,W-PAD,H-48);c.line(PAD,43,W-PAD,43);c.setFont('JP',9);c.drawString(PAD,27,'大分未来モビリティコンソーシアム / TCO・MDL');c.setFont('JP-Bold',11);c.drawRightString(W-PAD,26,str(d.page));c.restoreState()
    def afterFlowable(self,f):
        if isinstance(f,Paragraph) and hasattr(f,'bookmark'):self.canv.bookmarkPage(f.bookmark);self.canv.addOutlineEntry(f.getPlainText(),f.bookmark,level=0,closed=False);CHAPTER_PAGES[f.bookmark]=self.page

def build(slug,path,title):
    root=html.fromstring(path.read_text());sections=root.xpath('//section[contains(@class,"reader-section")]');story=[]
    for n,sec in enumerate(sections,1):
        if slug=='main' and n>1:story.append(PageBreak())
        elif n>1:story.append(CondPageBreak(100))
        label=sec.xpath('./header/h2')[0];prefix=f'{n:02} / ' if slug=='main' else '';heading=Paragraph(prefix+inline(label),ST['title'] if slug=='main' else ST['section']);heading.bookmark=sec.get('id');story.append(heading)
        lead=sec.xpath('./header/p')
        if lead:story.append(para(lead[0],'lead'))
        if n==1:
            story.append(Paragraph('<b>設立目標：2027年1月26日。</b>正式な設立は関係者の合意を経て決めます。',ST['note']))
            story.append(Paragraph('<b>未決・提案｜設立時の承認前。</b>候補は了承待ち。正式参画・就任・負担の承認を示すものではありません。',ST['note']))
            links=' / '.join(f'<a href="{ORIGIN}/oita-mirai-mobility-consortium/{u}/" color="#bd3c39"><u>{t}</u></a>' for u,t in [('read/main','構想・趣意書'),('members','名簿'),('rules','規約'),('secretariat','事務局・会計')]);story.append(Paragraph(links,ST['note']));story.append(Spacer(1,12))
        body=sec.xpath('./div[contains(@class,"chapter-body")]')[0]
        for c in body:
            if slug=='main' and 'pvmv-block' in c.get('class',''):
                story.append(PageBreak());story.append(Paragraph('PVMV / みんなの力で、<br/>大分の未来を動かす。',ST['title']))
                for x in c:
                    if x.tag=='figure':story+=render(x,WIDTH)
                for dt,dd in zip(c.xpath('.//dt'),c.xpath('.//dd')):story.append(Paragraph(f'<b>{escape(dt.text_content())}</b>　{escape(dd.text_content())}',ST['body']))
            else:story+=render(c,WIDTH)
        if slug!='main':story.append(Spacer(1,14))
    story.append(Paragraph(f'<a href="{ORIGIN}/oita-mirai-mobility-consortium/read/main/#founding-docs" color="#bd3c39"><u>設立に必要な4文書・最新版へ戻る</u></a>',ST['note']));out=OUTPUT/f'{slug}.pdf';Document(out,title).build(story);print(out);return dict(CHAPTER_PAGES)

def main():
    OUTPUT.mkdir(exist_ok=True)
    with TemporaryDirectory() as tmp:
        prepare_fonts(tmp)
        manifest=json.loads((OUTPUT/'founding.json').read_text());records=[]
        for slug,title in [('main','構想説明書・設立趣意書'),('members','発起人・会員・役員名簿'),('rules','規約案'),('secretariat','事務局の役割分担・会計')]:
            path=BASE/'read/main/index.html' if slug=='main' else BASE/f'{slug}/index.html';CHAPTER_PAGES.clear();chapter_pages=build(slug,path,title)
            import fitz
            pages=len(fitz.open(OUTPUT/f'{slug}.pdf'));record=next(dict(x) for x in manifest['documents'] if x['key']==slug);record.update(pages=pages,chapter_pages=chapter_pages);records.append(record)
        (OUTPUT/'document-manifest.json').write_text(json.dumps({'version':manifest['version'],'target_date':manifest['target_date'],'target_status':manifest['target_status'],'documents':records},ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':main()
