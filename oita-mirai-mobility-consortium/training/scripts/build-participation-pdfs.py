#!/usr/bin/env python3
"""Rebuild the existing municipal guide (2 A4 pages).

The user-selected distribution flyer is an approved PDF original and is not regenerated.

Usage: python3 scripts/build-participation-pdfs.py --font-variable /path/NotoSansJP.ttf
Dependencies: reportlab, fonttools, Pillow. Font: Google Fonts Noto Sans JP (OFL).
The full font is supplied locally; the generator makes no network requests.
All text boxes have explicit overflow checks. Existing source photos are retained.
"""
from __future__ import annotations
import argparse, html, io, json, tempfile
from pathlib import Path
from PIL import Image
from fontTools.ttLib import TTFont as FTFont
from fontTools.varLib.instancer import instantiateVariableFont
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF

HERE=Path(__file__).resolve().parent.parent
ASSETS=HERE.parent/'assets'
WEB='https://mobilitydlab.com/oita-mirai-mobility-consortium/training/'
FORM='https://docs.google.com/forms/d/e/1FAIpQLSfuYI4BEl_HRrIx0bEcORS43flu51UYpkyn_p_A4yXNzsQkew/viewform'
MLIT='https://www.mlit.go.jp/report/press/content/002012284.pdf#page=6'
INK='#141414'; ORANGE='#E68149'; DEEP='#A34A1E'; PALE='#FFF2E9'; GRAY='#555555'; LINE='#D8D4D0'
OPPORTUNITIES=[
 ('モビリティサービス企画','課題の整理から、対象者・使い方・運営方法を具体化します。'),
 ('e-Paletteを活用したサービス開発','地域での使い方を考え、実証内容と実施候補地の検討を進めます。'),
 ('自動運転実証','ルート・安全性・担い手を調べ、来年度の実証に向けた条件を整理します。'),
 ('アプリ開発・DX・AI活用','必要な機能を整理し、既存の仕組みや試作を活用して形にします。'),
 ('データ分析・改善','現地調査と試作品のデータを分析し、サービス案を改善します。'),
 ('車両管理・整備保守','継続して運営するための車両管理・整備保守の体制も相談できます。')
]

class PDF:
 def __init__(self,path,size,title):
  self.w,self.h=size;self.path=path;self.records=[];self.page=1
  self.c=canvas.Canvas(str(path),pagesize=size,pageCompression=1,invariant=1)
  self.c.setTitle(title);self.c.setAuthor('トヨタカローラ大分株式会社／株式会社モビリティデザインラボ')
  self.c.setSubject('自治体の参加価値・無料支援・地域別実施計画と11月11日講演の案内')
 def rect(self,x,y,w,h,col):
  self.c.setFillColor(HexColor(col));self.c.rect(x,self.h-y-h,w,h,fill=1,stroke=0)
 def rule(self,x,y,w,col=LINE):
  self.c.setStrokeColor(HexColor(col));self.c.setLineWidth(.6);self.c.line(x,self.h-y,x+w,self.h-y)
 def text(self,s,x,y,w,h,size=10,leading=None,font='JP',color=INK,label=''):
  p=Paragraph(s,ParagraphStyle('x',fontName=font,fontSize=size,leading=leading or size*1.5,textColor=HexColor(color),wordWrap='CJK',allowWidows=0,allowOrphans=0))
  aw,ah=p.wrap(w,h)
  if ah>h+.1:raise ValueError(f'{self.path.name} p{self.page} {label or s[:25]}: {ah} > {h}')
  if min(x,y)<0 or x+w>self.w+.1 or y+ah>self.h+.1:raise ValueError('Outside page: '+label)
  p.drawOn(self.c,x,self.h-y-ah)
  self.records.append({'page':self.page,'text':s,'size':size,'bounds':[x,y,w,ah]})
  return ah
 def link(self,s,url,x,y,w,h,size=9,font='JPB',color=DEEP):
  return self.text('<link href="'+html.escape(url,quote=True)+'" color="'+color+'">'+s+'</link>',x,y,w,h,size,font=font,color=color)
 def photo(self,name,x,y,w,h,contain=False):
  p=HERE/'assets'/name if name=='hidaka-yosuke.jpg' else ASSETS/name
  with Image.open(p) as im:
   im=im.convert('RGB');iw,ih=im.size;factor=min(w/iw,h/ih) if contain else max(w/iw,h/ih);dw,dh=iw*factor,ih*factor
   self.rect(x,y,w,h,'#F1F1F1');self.c.saveState();clip=self.c.beginPath();clip.rect(x,self.h-y-h,w,h);self.c.clipPath(clip,stroke=0,fill=0)
   im.thumbnail((int(dw*2.5),int(dh*2.5)),Image.Resampling.LANCZOS);buf=io.BytesIO();im.save(buf,'JPEG',quality=90);buf.seek(0)
   self.c.drawImage(ImageReader(buf),x+(w-dw)/2,self.h-y-h+(h-dh)/2,dw,dh);self.c.restoreState()
 def qr(self,url,x,y,size):
  q=QrCodeWidget(url);a,b,c,d=q.getBounds();drawing=Drawing(size,size,transform=[size/(c-a),0,0,size/(d-b),0,0]);drawing.add(q);renderPDF.draw(drawing,self.c,x,self.h-y-size)
  self.c.linkURL(url,(x,self.h-y-size,x+size,self.h-y),relative=0,thickness=0)
 def next(self):self.c.showPage();self.page+=1
 def save(self):self.c.save();return {'file':str(self.path),'pages':self.page,'boxes':self.records}

def head(p,page):
 p.rect(0,0,p.w,6,INK)
 p.text('OITA MIRAI MOBILITY / PROGRAM 2026',30,20,360,16,8.3,11,'Helvetica-Bold')
 p.text('自治体向け参加案内',410,20,155,16,8.5,11,'JPB',DEEP)
 p.rule(30,44,p.w-60)
def foot(p,n):
 p.rule(30,799,p.w-60)
 p.link('最新情報・申込み：自治体向け案内ページ',WEB+'guide.html',30,809,360,16,8)
 p.text(f'2026.10.27　{n} / 2',440,809,125,16,8,11,'JP',GRAY)

def guide():
 p=PDF(HERE/'program-guide.pdf',(595.2756,841.8898),'大分未来モビリティ人材育成プログラム｜自治体向け参加案内')
 head(p,1)
 p.text('地域の困りごとを、<br/>来年度の具体的な計画へ。',30,65,535,88,27,38,'JPB')
 p.text('大分未来モビリティ人材育成プログラム',30,154,535,23,13,20,'JPB')
 p.text('買物・通院・観光の移動、担い手不足、地域のにぎわい。<br/>地域の仲間と専門家と、考え、つくり、実施計画にまとめます。',30,187,535,44,10.6,16)
 for i,(top,big,small) in enumerate([
  ('自治体参加','無料','2026年11月〜2027年2月'),
  ('プログラム内で一緒に','企画・開発・分析','必要な専門性を無料で支援'),
  ('手元に残すもの','実施・実証計画','2027年2月末を目標に具体化')]):
  x=30+i*182;p.rect(x,247,171,82,PALE);p.rect(x,247,171,3,ORANGE)
  p.text(top,x+12,258,147,17,8.8,13,'JPB',DEEP);p.text(big,x+12,278,147,27,18 if i==0 else 13,22,'JPB');p.text(small,x+12,309,147,16,7.6,11,'JP',GRAY)
 p.text('6つのオポチュニティ',30,350,535,31,20,28,'JPB')
 y=395
 for i,(title,body) in enumerate(OPPORTUNITIES):
  p.rule(30,y-8,535);p.text(f'{i+1:02d}',30,y,42,32,26,30,'Helvetica-Bold',DEEP)
  p.text(title,87,y,478,25,14,21,'JPB')
  p.text(body,87,y+27,478,36,9.2,14)
  y+=63
 p.text('無料の範囲は本プログラム内のサービス開発・アプリ開発・データ分析。個別の実証・運行、継続的な車両管理・整備保守は別途協議します。',30,768,535,26,8,12)
 foot(p,1);p.next();head(p,2)
 p.text('参加後に目指す、5つの成果。',30,63,535,32,21,29,'JPB')
 outcomes=['地域の課題と現地調査の整理','具体的なサービス企画','テーマに応じたアプリの試作・データ分析','協力する相手と役割の整理','来年度以降の実施・実証計画']
 for i,s in enumerate(outcomes):p.text(f'<font color="{DEEP}">{i+1:02d}</font>　{s}',30,108+i*23,340,22,10.3,16,'JPB')
 p.photo('garraway0-cocreation.webp',389,106,176,111)
 p.text('地域の仲間と考える場／Garraway0',389,220,176,13,7,10,'JP',GRAY)
 p.text('地域の課題に応じて内容を組み立てます。同じアプリや実証を全自治体へ一律に提供するものではありません。',30,241,535,31,9,14)
 p.rule(30,282,535)
 p.text('A　e-Paletteをどう使うか',30,296,258,23,12.8,19,'JPB')
 p.text('観光、生活の移動、移動店舗、物流、停車中の活用。地域に合ったサービスを企画します。',30,324,258,46,9.3,14)
 p.text('B　自動運転実証をどう進めるか',309,296,256,23,12.8,19,'JPB')
 p.text('地域の課題、運行方法、担い手、継続性から、走らせる目的と実証計画を考えます。',309,324,256,46,9.3,14)
 p.text('構想段階から参加することで、地域の課題や希望を企画に反映しやすくなります。',30,373,535,18,9.3,14,'JPB',DEEP)
 p.rect(30,406,535,71,PALE)
 p.text('困りごと・希望 → 初回相談〈30分〜1時間〉 → 現地調査・企画',43,418,509,21,10,15,'JPB')
 p.text('地域の仲間と進める → 必要な開発・分析 → 実施・実証計画',43,445,509,21,10,15,'JPB')
 p.text('自治体にお願いすること',30,493,535,20,11.3,17,'JPB')
 p.text('窓口担当の設定／課題の共有／地域関係者との調整／可能な範囲のデータ・現地調査への協力。参加回数・時間は相談します。',30,519,535,34,9.2,14)
 p.photo('hidaka-yosuke.jpg',30,571,60,70)
 p.text('写真：MaaS Tech Japan公式',30,643,180,11,6,9,'JP',GRAY)
 p.text('まずは11/11の講演で、趣旨を知り、相談を。',103,568,383,23,12.8,19,'JPB')
 p.text('日高 洋祐 氏｜MaaS Tech Japan 代表取締役CEO<br/><b>2026年11月11日（水）14:00〜16:00　会場 Garraway0</b>',103,598,383,36,9.2,14)
 p.qr(WEB+'guide.html',494,568,71)
 p.link('11/11の講演を見る',WEB+'lecture-20261111.html',30,653,190,19,9.5)
 p.link('プログラムに申し込む・相談する',FORM,231,653,334,19,9.5)
 p.text('共通フォームでプログラムに登録し、任意設問「11月11日 特別講演・トークセッションへの参加予定」に回答します。講演欠席でも登録できます。',30,677,535,27,8.1,12)
 p.text('<b>費用・条件：</b>自治体参加とプログラム内の企画・開発・分析は無料。実運行・車両・保険・継続運用・管理保守等は別途協議。企業向けコンソーシアム年会費とは別です。参画はプログラム参加の前提ではありませんが、同コンソーシアムでの実証には参画が必要です。',30,710,535,44,7.6,11)
 p.text('車両提供、実証地域への選定、補助金採択、事業化は保証しません。<br/>事業主体：トヨタカローラ大分株式会社／企画・運営・伴走支援：株式会社モビリティデザインラボ<br/>国土交通省 令和8年度「『交通空白』解消等リ・デザイン全面展開プロジェクト」モビリティ人材・組織育成タイプ<br/>採択事業名：大分未来モビリティ・コンソーシアムによる交通空白解消人材育成・地域交通実装組織構築事業',30,751,535,44,6.6,9.8)
 foot(p,2)
 return p.save()

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--font-variable',required=True);parser.add_argument('--qa-json');args=parser.parse_args()
 with tempfile.TemporaryDirectory() as td:
  for name,weight in [('JP',400),('JPB',900)]:
   f=FTFont(args.font_variable);instantiateVariableFont(f,{'wght':weight},inplace=True);f.flavor=None
   # ReportLab keys embedded font faces by PostScript name. Variable-font
   # instances must have distinct names or the black face silently reuses 400.
   for record in list(f['name'].names):
    if record.nameID in (1,2,3,4,6):
     value={1:'NotoSansJP-Training',2:('Regular' if weight==400 else 'Black'),3:f'Training-{weight}',4:f'NotoSansJP-Training-{weight}',6:f'NotoSansJP-Training-{weight}'}[record.nameID]
     record.string=value.encode(record.getEncoding(),errors='replace')
   path=Path(td)/(name+'.ttf');f.save(path);pdfmetrics.registerFont(TTFont(name,str(path)))
  pdfmetrics.registerFontFamily('JP',normal='JP',bold='JPB',italic='JP',boldItalic='JPB')
  results=[guide()]
 if args.qa_json:Path(args.qa_json).write_text(json.dumps(results,ensure_ascii=False,indent=2))
 print(json.dumps([{'file':r['file'],'pages':r['pages'],'text_boxes':len(r['boxes'])} for r in results],ensure_ascii=False))
if __name__=='__main__':main()
