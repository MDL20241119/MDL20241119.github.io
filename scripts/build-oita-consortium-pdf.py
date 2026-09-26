#!/usr/bin/env python3
"""Render the canonical consortium JSON and guide HTML as a 12-page PDF.

Dependencies: reportlab, beautifulsoup4. Example:
python build_pdf.py --content ../oita-consortium/content.json \
  --guide ../oita-consortium/guide/index.html --font-dir ./fonts \
  --output oita-consortium-concept-v03.pdf
"""
import argparse, json, re, html, os
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

W,H=720,960
M=48
CW=W-2*M
INK=HexColor('#272323')
MUTED=HexColor('#685a52')
ORANGE=HexColor('#ef761e')
DARK=HexColor('#a64208')
PALE=HexColor('#fff0e2')
LINE=HexColor('#e6d4c7')
WHITE=HexColor('#ffffff')

def plain(node):
    return node.get_text('',strip=False).strip() if node else ''

def markup(node):
    if isinstance(node,str): return html.escape(node).replace('\n','<br/>')
    if isinstance(node,NavigableString): return html.escape(str(node))
    if not isinstance(node,Tag): return ''
    if node.name=='br': return '<br/>'
    inside=''.join(markup(ch) for ch in node.children)
    if node.name in ('b','strong'): return '<b>'+inside+'</b>'
    return inside

class Book:
    def __init__(self,args):
        self.args=args
        self.data=json.loads(Path(args.content).read_text())
        self.guide=BeautifulSoup(Path(args.guide).read_text(),'html.parser')
        pdfmetrics.registerFont(TTFont('JP',str(Path(args.font_dir)/'NotoSansJP-Regular.ttf')))
        pdfmetrics.registerFont(TTFont('JPB',str(Path(args.font_dir)/'NotoSansJP-Black.ttf')))
        pdfmetrics.registerFontFamily('JP',normal='JP',bold='JPB',italic='JP',boldItalic='JPB')
        Path(args.output).parent.mkdir(parents=True,exist_ok=True)
        self.c=canvas.Canvas(args.output,pagesize=(W,H),pageCompression=1)
        self.c.setTitle('大分未来モビリティ・コンソーシアム 構想説明書｜基本案 Ver.0.3')
        self.c.setAuthor('モビリティデザインラボ')
        self.c.setSubject('規約・参加方法・運営方法 基本案 Ver.0.3｜協議用')
        self.c.setCreator('ReportLab / canonical content.json')
        self.extents=[]
        self.page=0

    def box(self,x,y,w,h,fill=WHITE,stroke=LINE,r=0):
        self.c.setFillColor(fill)
        self.c.setStrokeColor(stroke or fill)
        self.c.setLineWidth(.8)
        if r: self.c.roundRect(x,H-y-h,w,h,r,fill=1,stroke=bool(stroke))
        else: self.c.rect(x,H-y-h,w,h,fill=1,stroke=bool(stroke))

    def rule(self,x,y,w,color=LINE):
        self.c.setStrokeColor(color);self.c.setLineWidth(.8)
        self.c.line(x,H-y,x+w,H-y)

    def p(self,txt,x,y,w,size=16.5,leading=None,bold=False,color=INK,align=0,record=True):
        if not isinstance(txt,str): txt=markup(txt)
        style=ParagraphStyle('p',fontName='JPB' if bold else 'JP',fontSize=size,
             leading=leading or size*1.44,textColor=color,wordWrap='CJK',alignment=align,
             splitLongWords=True,spaceBefore=0,spaceAfter=0,allowWidows=0,allowOrphans=0)
        p=Paragraph(txt,style);ww,hh=p.wrap(w,H)
        p.drawOn(self.c,x,H-y-hh)
        if record:self.extents.append((self.page,x,y,w,hh,re.sub('<[^>]+>','',txt)[:55]))
        return y+hh

    def label(self,txt,x,y,w=CW,size=13,color=DARK):
        return self.p(txt,x,y,w,size=size,leading=size*1.3,bold=True,color=color)

    def note(self,node,y):
        self.rule(M,y,CW)
        return self.p(node,M,y+12,CW,size=13.2,leading=19,color=MUTED)

    def footer(self,num):
        self.rule(M,906,CW)
        self.p('大分未来モビリティ・コンソーシアム',M,917,370,size=12,leading=17,color=MUTED,record=False)
        self.p('基本案 Ver.0.3｜協議用',M,934,330,size=11,leading=14,color=MUTED,record=False)
        self.p(f'{num:02d} / 12',590,919,82,size=16,leading=22,bold=True,color=DARK,align=2,record=False)
        if num>1:
            self.p('目次へ',482,924,81,size=12,color=DARK,align=2,record=False)
            ax=574
            self.c.setStrokeColor(DARK);self.c.setLineWidth(.9)
            self.c.line(ax,H-939,ax,H-924)
            path=self.c.beginPath()
            path.moveTo(ax-3,H-928);path.lineTo(ax,H-924);path.lineTo(ax+3,H-928)
            self.c.drawPath(path,stroke=1,fill=0)
            self.c.linkRect('', 'cover',(482,H-946,572,H-916),relative=0,thickness=0)

    def start(self,key,title,num):
        self.page=num
        self.box(0,0,W,H,WHITE,None)
        self.box(0,0,12,H,PALE,None)
        self.c.bookmarkPage(key)
        self.c.addOutlineEntry(title,key,0,False)

    def finish(self):
        self.footer(self.page);self.c.showPage()

    def header(self,p,num):
        self.start(p['id'],p['title'],num)
        self.p(f'{num:02d}',M,35,66,size=34,leading=42,bold=True,color=ORANGE)
        self.label(p['category'],123,53,450,size=13.5)
        self.rule(M,88,CW)
        h2=self.guide.select_one('#'+p['id']+' h2')
        title=markup(h2) if h2 else markup(p['title'])
        end=self.p(title,M,106,CW,size=32,leading=41,bold=True)
        end=self.p(p['lead'],M,end+14,CW,size=16.5,leading=24,color=MUTED)
        self.p('基本案の対応項目：'+p['source_sections'],M,end+10,CW,size=13,leading=18,color=DARK)
        return end+42

    def cover(self):
        s=self.guide.select_one('#cover');self.start('cover','構想説明書 / 目次',1)
        self.label(plain(s.select_one('.kicker')),M,40,size=13)
        self.box(M,69,224,28,PALE,None)
        self.label(plain(s.select_one('.status')),M+12,74,204,size=13)
        self.p(s.select_one('h1 small'),M,116,CW,size=28,leading=38,bold=True)
        self.p('構想説明書',M,202,CW,size=47,leading=61,bold=True)
        self.p(s.select_one('.statement'),M,285,CW,size=22,leading=32,bold=True,color=DARK)
        self.p(s.select_one('.hero-summary'),M,396,CW,size=16.5,leading=25,color=MUTED)
        self.box(M,478,CW,212,PALE,None)
        self.p('4',M+20,487,68,size=60,leading=75,bold=True,color=ORANGE)
        self.p(s.select_one('.cover-card h2'),M+104,501,480,size=21,leading=28,bold=True)
        for i,li in enumerate(s.select('.cover-card li')):
            spans=li.find_all('span');y=548+i*31
            self.label(plain(spans[0]),M+25,y,40,size=16)
            self.p(spans[1],M+68,y,528,size=17,leading=24,bold=True)
        self.label('読むページを選ぶ',M,716,size=15)
        short=['全体像','3つの参加方法','参加・会費','運営の4機能','役割・意思決定','プロジェクトの進め方','契約・お金の流れ','名称・情報のルール','大分に残す成果','将来の法人化','設立準備の進め方']
        for i,p in enumerate(self.data['pages']):
            col=0 if i<6 else 1;row=i if i<6 else i-6;x=M+col*320;y=750+row*23
            self.p(f'{i+2:02d}',x,y,34,size=13,bold=True,color=DARK)
            self.p(short[i],x+37,y,267,size=13.5,color=INK)
            self.c.linkRect('',p['id'],(x,H-y-21,x+302,H-y+2),thickness=0)
        self.finish()

    def structure(self,s,y):
        self.p(s.select_one('.architecture > p'),M,y,CW,size=16,leading=23,align=1,color=MUTED)
        y+=60
        nodes=s.select('.arch-node');arrows=s.select('.arch-arrow')
        heights=[154,136,127]
        for i,node in enumerate(nodes):
            h=heights[i]
            self.box(M,y,CW,h,PALE if i==0 else WHITE,LINE)
            self.label(node.select_one('.micro'),M+20,y+13,CW-40,size=13)
            title=node.find('b',recursive=False)
            t=markup(title).replace('<br/>','') if i==0 else markup(title)
            te=self.p(t,M+20,y+39,CW-40,size=25 if i==0 else 26,leading=34,bold=True)
            self.p(node.find('small',recursive=False),M+20,te+8,CW-40,size=16.5,leading=25)
            y+=h
            if i<2:
                # Draw the downward connector as vector geometry so it does not
                # depend on the Japanese font containing the arrow glyph.
                ax=M+28
                self.c.setStrokeColor(ORANGE);self.c.setFillColor(ORANGE)
                self.c.setLineWidth(1.5)
                self.c.line(ax,H-y-7,ax,H-y-27)
                path=self.c.beginPath()
                path.moveTo(ax-5,H-y-22);path.lineTo(ax,H-y-28);path.lineTo(ax+5,H-y-22)
                self.c.drawPath(path,stroke=1,fill=0)
                self.p(markup(arrows[i]).replace('↓','').strip(),M,y+8,CW,size=14.5,leading=21,bold=True,color=DARK,align=1)
                y+=39
        self.note(s.select_one('.note'),y+15)

    def participation(self,s,y):
        for i,node in enumerate(s.select('.role-card')):
            # Density follows content, without making the first card's caveat tiny.
            h=[207,185,171][i]
            self.box(M,y,CW,h,PALE if i==0 else WHITE,LINE)
            self.p(node.select_one('.role-no'),M+18,y+13,68,size=37,leading=45,bold=True,color=ORANGE)
            x=M+100;w=CW-120
            end=self.p(node.select_one('h3'),x,y+18,w,size=24,leading=32,bold=True)
            end=self.p(node.select_one('.promise'),x,end+5,w,size=16.5,leading=24,bold=True,color=DARK)
            for pp in node.select('p:not(.promise)'):
                end=self.p(pp,x,end+7,w,size=14 if 'examples' in pp.get('class',[]) else 16,leading=21 if 'examples' in pp.get('class',[]) else 23,color=MUTED if 'examples' in pp.get('class',[]) else INK)
            y+=h+14

    def entry(self,s,y):
        gap=12;bw=(CW-3*gap)/4
        for i,li in enumerate(s.select('.inline-flow li')):
            x=M+i*(bw+gap);self.box(x,y,bw,89,PALE,None)
            self.p(li.b,x+15,y+8,bw-30,size=30,leading=39,bold=True,color=ORANGE)
            txt=''.join(str(n) for n in li.contents if n is not li.b)
            self.p(txt,x+15,y+51,bw-30,size=16,leading=23,bold=True)
        y+=112;bw=(CW-20)/2
        for i,node in enumerate(s.select('.mini')):
            x=M+i*(bw+20)
            self.p(node.h3,x,y,bw,size=20,leading=29,bold=True)
            self.p(node.p,x,y+40,bw,size=16.5,leading=24)
        y+=180
        node=s.select_one('.decision-box');self.box(M,y,CW,178,PALE,None)
        self.p(node.h3,M+22,y+18,CW-44,size=21,leading=30,bold=True)
        self.p(node.p,M+22,y+60,CW-44,size=16.5,leading=25)
        for i,chip in enumerate(node.select('.chip')):
            x=M+22+i*146;self.box(x,y+129,135,30,WHITE,LINE)
            self.p(chip,x,y+133,135,size=14,leading=21,bold=True,color=DARK,align=1)
        self.note(s.select_one('.note'),y+198)

    def operations(self,s,y):
        bw=(CW-18)/2;bh=258
        for i,node in enumerate(s.select('.operating-card')):
            x=M+(i%2)*(bw+18);top=y+(i//2)*(bh+16)
            self.box(x,top,bw,bh,PALE if i>1 else WHITE,LINE)
            self.p(node.select_one('.big-num'),x+17,top+13,48,size=28,leading=36,bold=True,color=ORANGE)
            self.p(node.h3,x+74,top+17,bw-90,size=23,leading=32,bold=True)
            oe=self.p(node.select_one('.owner'),x+18,top+63,bw-36,size=17.5,leading=24,bold=True,color=DARK)
            self.p(node.p,x+18,oe+10,bw-36,size=16,leading=23)
            if node.select_one('.emphasis'):
                self.p(node.select_one('.emphasis'),x+18,top+212,bw-36,size=25,leading=35,bold=True,color=DARK)
        self.note(s.select_one('.note'),y+2*bh+30)

    def roles(self,s,y):
        for node in s.select('.split-row'):
            self.rule(M,y,CW)
            self.p(node.h3,M,y+12,195,size=17,leading=25,bold=True,color=DARK)
            right=node.find('div',recursive=False)
            end=self.p(right.strong,M+212,y+12,CW-212,size=17,leading=24,bold=True)
            end=self.p(right.p,M+212,end+5,CW-212,size=16,leading=22)
            y=max(y+89,end+12)
        y+=10;box=s.select_one('.decision-box')
        self.box(M,y,CW,135,PALE,None)
        self.p(box.h3,M+18,y+14,CW-36,size=19,leading=26,bold=True)
        yy=y+53
        for row in box.select('.decision-row'):
            self.p(row.b,M+18,yy,126,size=16,leading=22,bold=True,color=DARK)
            end=self.p(row.span,M+156,yy,CW-174,size=16,leading=22)
            yy=end+9
        self.note(s.select_one('.note'),y+145)

    def projects(self,s,y):
        x=M+61
        self.c.setStrokeColor(LINE);self.c.setLineWidth(2)
        self.c.line(M+20,H-y-12,M+20,H-y-429)
        for i,node in enumerate(s.select('.journey li')):
            top=y+i*65
            self.box(M,top,42,40,PALE,None)
            self.p(node.b,M,top+4,42,size=21,leading=31,bold=True,color=DARK,align=1)
            self.p(node.h3,x,top-1,CW-61,size=20,leading=29,bold=True)
            self.p(node.p,x,top+32,CW-61,size=16,leading=23)
        y+=473
        node=s.select_one('.checklist');self.box(M,y,CW,120,PALE,None)
        self.p(node.h3,M+20,y+13,CW-40,size=19,leading=27,bold=True)
        for i,li in enumerate(node.select('li')):
            col=i%3;row=i//3
            self.p('・'+markup(li),M+20+col*195,y+51+row*29,196,size=15.5,leading=23)

    def money(self,s,y):
        for i,node in enumerate(s.select('.fund-card')):
            h=249
            self.box(M,y,CW,h,PALE if i==0 else WHITE,LINE)
            self.p(node.select_one('.fund-letter'),M+18,y+12,58,size=47,leading=59,bold=True,color=ORANGE)
            title=markup(node.h3).replace('<br/>','')
            self.p(title,M+92,y+24,330,size=22,leading=30,bold=True)
            manager=node.select_one('.manager')
            self.p(manager.span,M+434,y+19,170,size=13,leading=18,bold=True,color=DARK)
            name=''.join(str(n) for n in manager.contents if n is not manager.span)
            self.p(name,M+434,y+47,172,size=26,leading=34,bold=True,color=DARK)
            yy=y+99
            for pp in node.find_all('p',recursive=False):
                yy=self.p(pp,M+20,yy,CW-40,size=16.5,leading=24)+9
            self.rule(M+20,y+209,CW-40)
            self.p(node.select_one('.fund-route'),M+20,y+219,CW-40,size=15.5,leading=23,bold=True,color=DARK,align=1)
            y+=h+16
        self.note(s.select_one('.note'),y+2)

    def rules(self,s,y):
        cards=s.select('.rules-card');n=cards[0]
        self.box(M,y,CW,267,PALE,None)
        self.p(n.h3,M+22,y+18,CW-44,size=23,leading=32,bold=True)
        pp=n.find_all('p',recursive=False)
        self.p(pp[0],M+22,y+67,CW-44,size=16.5,leading=24)
        self.box(M+22,y+125,CW-44,66,WHITE,LINE)
        brand=n.select_one('.brand-example')
        self.p(brand,M+37,y+136,CW-74,size=17,leading=24,bold=True,color=DARK)
        self.p(pp[1],M+22,y+210,CW-44,size=16.5,leading=24)
        y+=295;n=cards[1]
        self.p(n.h3,M,y,CW,size=23,leading=32,bold=True)
        for i,p in enumerate(n.select('.mini-grid p')):
            x=M+i*324
            self.p(p,x,y+52,300,size=17,leading=26)
        y+=204
        self.box(M,y,CW,62,PALE,None)
        self.p(s.select_one('.keyline'),M+18,y+15,CW-36,size=18,leading=27,bold=True,color=DARK)
        self.note(s.select_one('.note'),y+82)

    def outcomes(self,s,y):
        bw=(CW-24)/3
        for i,n in enumerate(s.select('.value-card')):
            x=M+i*(bw+12);self.box(x,y,bw,176,PALE,None)
            self.label(n.span,x+16,y+14,bw-32,size=13)
            self.p(n.b,x+16,y+44,bw-32,size=31,leading=41,bold=True,color=DARK)
            self.p(n.p,x+16,y+97,bw-32,size=16,leading=23)
        y+=188
        for i,n in enumerate(s.select('.value-flow > div')):
            x=M+i*160
            self.box(x,y,144,78,WHITE,LINE)
            t=''.join(str(ch) for ch in n.contents if ch is not n.small)
            self.p(t,x,y+12,144,size=16.5,leading=24,bold=True,align=1)
            self.p(n.small,x,y+43,144,size=13,leading=18,color=MUTED,align=1)
            if i<3:self.p('→',x+145,y+24,16,size=15,color=DARK,align=1)
        y+=101;table=s.select_one('table')
        self.p(table.caption,M,y,CW,size=20,leading=28,bold=True)
        y+=43
        self.box(M,y,CW,30,PALE,None)
        self.label('見るもの',M+14,y+6,140,size=13)
        self.label('確認すること',M+159,y+6,440,size=13)
        y+=30
        for tr in table.select('tbody tr'):
            self.p(tr.th,M+14,y+13,140,size=17,leading=25,bold=True)
            end=self.p(tr.td,M+159,y+13,CW-175,size=16.5,leading=24)
            y=max(y+49,end+12);self.rule(M,y,CW)
        self.note(s.select_one('.note'),y+17)

    def future(self,s,y):
        self.p(s.select_one('.guide-section-title'),M,y,CW,size=21,leading=30,bold=True)
        y+=48
        for li in s.select('.triggers li'):
            self.label(li.b,M,y,46,size=20)
            self.p(li.span,M+58,y,CW-58,size=18,leading=27,bold=True)
            self.rule(M,y+39,CW);y+=53
        y+=17;bw=(CW-18)/2
        for i,n in enumerate(s.select('.future-options > div')):
            x=M+(i%2)*(bw+18);top=y+(i//2)*108
            self.box(x,top,bw,94,PALE,None)
            self.p(n.b,x+17,top+12,bw-34,size=19,leading=27,bold=True,color=DARK)
            self.p(n.p,x+17,top+49,bw-34,size=15.5,leading=23)
        self.note(s.select_one('.note'),y+220)

    def next(self,s,y):
        for node in s.select('.next-list li'):
            self.p(node.b,M,y,58,size=32,leading=41,bold=True,color=ORANGE)
            self.p(node.h3,M+74,y+2,CW-74,size=22,leading=31,bold=True)
            end=self.p(node.p,M+74,y+36,CW-74,size=16.5,leading=24)
            y=max(y+95,end+11)
        y+=8
        self.box(M,y,CW,106,PALE,None)
        self.p(s.select_one('.closing-line'),M+20,y+11,CW-40,size=21,leading=28,bold=True,color=DARK)
        y+=119
        self.p(s.select_one('.subnote'),M,y,CW,size=13,leading=18,color=MUTED)
        a=s.select_one('.actions a')
        if a:
            self.c.linkURL(a['href'],(M,H-901,M+CW,H-877),relative=0,thickness=0)
            self.p('構想のホームページへ → mobilitydlab.com/oita-consortium/',M,880,CW,size=13,leading=19,bold=True,color=DARK)

    def build(self):
        self.cover()
        for i,p in enumerate(self.data['pages'],2):
            y=self.header(p,i)
            # Fine-grained layouts adapt to the canonical text, not screenshots.
            s=BeautifulSoup(p['html'],'html.parser')
            getattr(self,p['id'])(s,y)
            self.finish()
        self.c.save()
        manifest=Path(self.args.output).with_suffix('.layout.json')
        manifest.write_text(json.dumps(self.extents,ensure_ascii=False,indent=2))
        problems=[v for v in self.extents if v[2]+v[4]>899 or v[1]+v[3]>W-M+.01]
        print(json.dumps({'pdf':self.args.output,'pages':12,'layout_warnings':problems},ensure_ascii=False,indent=2))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--content',required=True)
    p.add_argument('--guide',required=True)
    p.add_argument('--font-dir',required=True)
    p.add_argument('--output',required=True)
    Book(p.parse_args()).build()

if __name__=='__main__':main()
