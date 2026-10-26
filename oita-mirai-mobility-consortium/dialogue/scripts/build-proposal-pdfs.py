#!/usr/bin/env python3
"""Build eight editorial proposal briefs, exactly two A4 landscape pages each.

Python dependencies: reportlab, Pillow, fonttools (pypdf for optional QA).
Run: python3 scripts/build-proposal-pdfs.py --font-variable /path/to/NotoSansJP-variable.ttf
Alternative: --font-regular regular.ttf --font-bold bold.ttf
Official full font: https://github.com/google/fonts/tree/main/ofl/notosansjp (OFL-1.1).

Editorial source: ../data/proposal-briefs.json, summarized from the adjacent HTML.
The detailed proposal, policy evidence and full credits remain on the source page.
No external requests, browser print engine or runtime JavaScript are required.
Every text block has a fixed reading size and checked bounds; overflow fails the build.
Use --regions beppu yufuin to render selected briefs; --qa-json PATH records layout QA.
"""
from __future__ import annotations
import argparse, hashlib, html, io, json, re, tempfile
from pathlib import Path
from urllib.parse import urljoin
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor, Color, white
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

DIALOGUE=Path(__file__).resolve().parent.parent
ROOT=DIALOGUE.parent.parent
ORIGIN='https://mobilitydlab.com/oita-mirai-mobility-consortium/dialogue/'
W,H=841.8898,595.2756
INK='#142232'; ORANGE='#F18B4B'; DARKORANGE='#A64D1E'; MUTED='#536272'; LINE='#D9DFE5'; PALE='#F2F5F7'; WARM='#FFF3E9'
M=34
REGIONS=['beppu','yufuin','hiji','usa','kunisaki','usuki','oita','taiyonoie']

def esc(s):return html.escape(str(s))
def normalize(s):return re.sub(r'\s+','',s)

def fonts(args,tmp):
    if args.font_variable:
        from fontTools.ttLib import TTFont as FTFont
        from fontTools.varLib.instancer import instantiateVariableFont
        paths=[]
        for weight in (500,900):
            f=FTFont(args.font_variable);instantiateVariableFont(f,{'wght':weight},inplace=True)
            p=tmp/f'jp-{weight}.ttf';f.save(str(p));paths.append(p)
    elif args.font_regular and args.font_bold:paths=[Path(args.font_regular),Path(args.font_bold)]
    else:raise SystemExit('A full Japanese TrueType font is required. See this script docstring.')
    for n,p in zip(('JP','JPB'),paths):pdfmetrics.registerFont(TTFont(n,str(p)))
    pdfmetrics.registerFontFamily('JP',normal='JP',bold='JPB',italic='JP',boldItalic='JPB')

class Brief:
    def __init__(self,slug,data,index):
        self.slug=slug;self.d=data;self.index=index;self.records=[];self.page=0
        self.url=ORIGIN+slug+'.html';self.path=DIALOGUE/'pdf'/f'{slug}-proposal.pdf'
        self.path.parent.mkdir(exist_ok=True)
        self.c=canvas.Canvas(str(self.path),pagesize=(W,H),pageCompression=1,invariant=1)
        self.c.setTitle(data['region']+'｜共創提案｜2ページ要点版')
        self.c.setAuthor('モビリティデザインラボ');self.c.setSubject('地域の未来と実証に向けた設計をまとめた企画例・検討用ドラフト')
    def rect(self,x,y,w,h,color,stroke=None):
        self.c.setFillColor(HexColor(color))
        if stroke:self.c.setStrokeColor(HexColor(stroke));self.c.setLineWidth(.7)
        self.c.rect(x,H-y-h,w,h,fill=1,stroke=bool(stroke))
    def line(self,x,y,w,color=LINE,thickness=.7):
        self.c.setStrokeColor(HexColor(color));self.c.setLineWidth(thickness);self.c.line(x,H-y,x+w,H-y)
    def text(self,t,x,y,w,h,size=11.4,leading=None,font='JP',color=INK,label='',align=0):
        style=ParagraphStyle('p',fontName=font,fontSize=size,leading=leading or size*1.55,textColor=HexColor(color),wordWrap='CJK',splitLongWords=True,alignment=align,spaceBefore=0,spaceAfter=0,allowWidows=0,allowOrphans=0)
        p=Paragraph(t,style);actual_w,actual_h=p.wrap(w,h)
        if actual_h>h+.1:raise ValueError(f'{self.slug}/p{self.page}/{label}: {actual_h:.1f} > {h:.1f} pt')
        if x<0 or y<0 or x+w>W+.1 or y+actual_h>H+.1:raise ValueError('Text outside page: '+label)
        p.drawOn(self.c,x,H-y-actual_h)
        self.records.append({'page':self.page,'label':label,'font_pt':size,'bounds':[x,y,w,actual_h],'allocated_height':h,'text':re.sub('<[^>]+>','',t)})
        return actual_h
    def label(self,t,x,y,w,color=DARKORANGE):return self.text(esc(t),x,y,w,15,9.1,12,'JPB',color,t)
    def link(self,label,url,x,y,w,h,size=9.2,color=DARKORANGE):
        return self.text('<link href="'+html.escape(url,quote=True)+'" color="'+color+'">'+esc(label)+'</link>',x,y,w,h,size,size*1.5,'JP',color,label)
    def logo(self,dark=False):
        col='#FFFFFF' if dark else INK
        self.text('MOBILITY<br/>DESIGN LAB',M,17,118,31,10.3,12.5,'JPB',col,'brand')
        self.text('OITA MIRAI MOBILITY',169,23,250,16,10,12,'JPB',col,'project')
        region=self.d['region']+' / '+self.d['english']
        self.text(esc(region),445,22,W-M-445,20,11,15,'JPB',col,'region',2)
    def footer(self):
        self.line(M,554,W-2*M)
        self.text('2026年度 人材育成プログラムで磨く企画例 / 2026.10.26',M,565,340,15,7.7,11.5,'JP',MUTED,'program')
        self.link('詳細・最新情報はWebへ ↗',self.url,378,564,240,17,8.2,MUTED)
        self.text(f'{self.page:02d}<font color="#9AA5AF"> / 02</font>',W-M-94,562,94,22,13,17,'Helvetica-Bold',INK,'page-number',2)
    def hero_photo(self):
        p=self.d['photos'][0];path=ROOT/p['src'].lstrip('/')
        x,y,w,h=443,80,W-M-443,272
        self.rect(x,y,w,h,PALE)
        with Image.open(path) as im:
            im=im.convert('RGB');iw,ih=im.size
            contain=self.slug=='taiyonoie'
            factor=min(w/iw,h/ih) if contain else max(w/iw,h/ih)
            dw,dh=iw*factor,ih*factor
            # Clip to the layout frame. The source photograph is not overwritten.
            self.c.saveState();clip=self.c.beginPath();clip.rect(x,H-y-h,w,h);self.c.clipPath(clip,stroke=0,fill=0)
            target=(round(dw*2.5),round(dh*2.5));im.thumbnail(target,Image.Resampling.LANCZOS)
            b=io.BytesIO();im.save(b,format='JPEG',quality=88,optimize=True);b.seek(0)
            self.c.drawImage(ImageReader(b),x+(w-dw)/2,H-y-h+(h-dh)/2,width=dw,height=dh)
            self.c.restoreState()
        # A neutral small caption preserves the distinction between a place and a reference photo.
        cap='参考写真／太陽の家の撮影ではありません' if self.slug=='taiyonoie' else self.d['region']+'の風景・参考写真'
        self.text(esc(cap),x,y+h+7,w,16,8.4,12,'JP',MUTED,'photo-caption')
    def first_page(self):
        self.page=1;self.rect(0,0,W,H,'#FFFFFF');self.logo();self.line(M,56,W-2*M);self.rect(M,55,52,3,ORANGE)
        self.label('REGIONAL PROPOSAL  /  '+f'{self.index:02d}',M,79,380)
        self.hero_photo()
        headline=self.d['headline'];size=min(40,390/max(pdfmetrics.stringWidth(t,'JPB',1) for t in headline))
        if size<32:raise ValueError(self.slug+': headline needs editorial shortening')
        top=105
        for i,t in enumerate(headline):self.text(esc(t),M,top+i*49,390,49,size,48,'JPB',INK,'headline')
        # Stable concept and promise baselines keep all eight briefs comparable.
        self.text(esc(self.d['concept']),M,266,384,25,11,15,'JPB',DARKORANGE,'concept')
        self.text(esc(self.d['promise']),M,299,382,64,12.2,19,'JP',INK,'promise')
        self.line(M,384,W-2*M)
        widths=[237,261,237];xs=[M,293,573]
        labels=[('01 / ISSUE','地域の課題・仮説'),('02 / SERVICE','つくるサービス'),('03 / VALUE','目指す変化')]
        for i,((en,jp),x,w) in enumerate(zip(labels,xs,widths)):
            if i==1:self.rect(x-12,397,w+8,139,WARM)
            self.label(en,x,404,w);self.text(jp,x,425,w,28,17,23,'JPB',INK,'card-heading')
        self.text(esc(self.d['challenge']),xs[0],459,widths[0],78,11.2,17.5,'JP',INK,'challenge')
        self.text(esc(self.d['service']),xs[1],459,widths[1]-7,78,11.2,17.5,'JP',INK,'service')
        for i,t in enumerate(self.d['outcomes']):
            self.rect(xs[2],464+i*24,4,4,ORANGE)
            self.text(esc(t),xs[2]+13,457+i*24,widths[2]-13,27,11.7,17.5,'JPB',INK,'outcome')
        for x in (277,557):
            yy=H-438;self.c.setStrokeColor(HexColor(ORANGE));self.c.setLineWidth(1)
            self.c.line(x,yy,x+10,yy);self.c.line(x+7,yy+3,x+10,yy);self.c.line(x+7,yy-3,x+10,yy)
        p=self.d['photos'][0]
        credit=p['credit']
        credit=re.sub(r'全体を保持して表示。|トリミングなし。','',credit)
        # Full attribution remains human-readable; source and license links are live.
        short=credit.split(' · ')[0]+' / '+credit.split(' · ')[1] if ' · ' in credit else credit
        short=re.sub(r'「[^」]+」','',short)
        short=short.replace('（部分）','').replace('／撮影：',' / ')
        if self.slug=='oita':short='写真：佐賀関「漁港の朝」（部分） / 大分市デジタルアーカイブ / CC BY'
        elif self.slug=='taiyonoie':short='参考写真：Disabled And Here / Chona Kasinger / CC BY 4.0'
        else:short='写真：'+short
        short+=' / '+('全体表示' if self.slug=='taiyonoie' else 'レイアウトに合わせてトリミング')
        self.text(esc(short),M,540,610,12,6.8,9.8,'JP',MUTED,'photo-credit')
        self.link('写真出典',p['source'],662,539,63,14,7.3,MUTED)
        self.link('利用条件',p['license'],733,539,75,14,7.3,MUTED)
        self.footer();self.c.showPage()
    def second_page(self):
        self.page=2;self.rect(0,0,W,H,'#FFFFFF');self.rect(0,0,W,108,INK);self.logo(True)
        self.text('実証に向けた設計図',M,57,565,43,27,35,'JPB','#FFFFFF','page2-title')
        self.text('対話する。試す。続ける仕組みをつくる。',590,72,218,22,9.3,14,'JP','#D9E0E7','page2-subtitle')
        lx=M;lw=516;rx=577;rw=W-M-rx
        self.rect(rx-15,123,rw+15,408,PALE)
        # Two distinct technology stages; autonomy is explicitly a future examination.
        gap=18;cw=(lw-gap)/2
        for key,tag,title,x in [('epalette','SERVICE DESIGN','e-Paletteの使い方',lx),('autonomy','FUTURE OPTION','自動運転は条件から検討',lx+cw+gap)]:
            self.label(tag,x,128,cw)
            self.text(title,x,147,cw,24,13.3,19,'JPB',INK,key+'-heading')
            self.text(esc(self.d[key]),x,175,cw,73,11.0,16.6,'JP',INK,key)
        self.line(lx,250,lw)
        self.label('FIRST TEST',lx,263,lw)
        self.text('最初に確かめること',lx,280,lw,25,17,23,'JPB',INK,'first-test-heading')
        self.text(esc(self.d['first_test']),lx,311,lw,55,11.7,18.3,'JP',INK,'first-test')
        self.label('評価指標（検証案）',lx,369,lw)
        mw=(lw-16)/3
        for i,t in enumerate(self.d['metrics']):
            x=lx+i*(mw+8);self.rect(x,390,mw,35,WARM)
            self.text(esc(t),x+9,399,mw-18,21,10.1,14.5,'JPB',DARKORANGE,'metric')
        for key,title,x in [('partners','想定する共創チーム',lx),('revenue','継続の仕組み・対価',lx+cw+gap)]:
            self.text(title,x,442,cw,23,12.1,18,'JPB',INK,key+'-heading')
            self.text(esc(self.d[key]),x,470,cw,59,10.4,15.5,'JP',INK,key)
        # Evidence and decisions are placed apart from the proposed service.
        self.label('LOCAL CONTEXT',rx,135,rw-8)
        self.text('地域の現在地',rx,153,rw-8,25,15.3,21,'JPB',INK,'policy-heading')
        self.text(esc(self.d['policy_context']),rx,183,rw-8,93,10.1,15.7,'JP',INK,'policy-context')
        self.line(rx,279,rw-8,'#CCD5DD')
        self.text('対話で決める3つの問い',rx,293,rw-8,23,12.2,18,'JPB',INK,'questions-heading')
        for i,t in enumerate(self.d['decision_questions']):
            y=326+i*45
            self.text(str(i+1).zfill(2),rx,y,22,18,11.8,15,'Helvetica-Bold',DARKORANGE,'question-number')
            self.text(esc(t),rx+28,y-1,rw-36,39,10.1,15.1,'JP',INK,'decision-question')
        self.line(rx,459,rw-8,'#CCD5DD')
        self.label('詳細・原典',rx,471,rw-75)
        for i,source in enumerate(self.d['source_links'][:3]):
            self.link(str(i+1)+'. '+source['label'],source['url'],rx,490+i*13.6,rw-74,14,7.5,MUTED)
        q=qr.QrCodeWidget(self.url);b=q.getBounds();size=54
        d=Drawing(size,size,transform=[size/(b[2]-b[0]),0,0,size/(b[3]-b[1]),0,0]);d.add(q)
        renderPDF.draw(d,self.c,W-M-size,H-474-size)
        self.c.linkURL(self.url,(W-M-size,H-474-size,W-M,H-474),relative=0)
        self.text('詳細はWebへ',W-M-65,529,65,12,7.5,10,'JPB',MUTED,'qr-label',2)
        self.text(esc(self.d['scope_note']),M,535,lw,18,7.4,10.7,'JP',MUTED,'scope-note')
        self.footer();self.c.showPage()
    def build(self):
        self.first_page();self.second_page();self.c.save()
        return {'slug':self.slug,'pages':2,'pdf':str(self.path.relative_to(DIALOGUE)),'bytes':self.path.stat().st_size,'sha256':hashlib.sha256(self.path.read_bytes()).hexdigest(),'layout':self.records}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--font-variable');p.add_argument('--font-regular');p.add_argument('--font-bold');p.add_argument('--regions',nargs='+',choices=REGIONS);p.add_argument('--qa-json')
    a=p.parse_args();data=json.loads((DIALOGUE/'data/proposal-briefs.json').read_text())
    results=[]
    with tempfile.TemporaryDirectory(prefix='proposal-ir-') as tmp:
        fonts(a,Path(tmp))
        for slug in a.regions or REGIONS:results.append(Brief(slug,data[slug],REGIONS.index(slug)+1).build())
    if a.qa_json:Path(a.qa_json).write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print(json.dumps([{k:v for k,v in r.items() if k!='layout'} for r in results],ensure_ascii=False))

if __name__=='__main__':main()
