#!/usr/bin/env python3
"""Create the two-page programme explanation. Never writes participation-flyer.pdf.

python3 build-program-guide.py --font-variable NotoSansJP.ttf --photo assets/hidaka-yosuke.jpg --output-dir .
Dependencies: reportlab, fonttools, Pillow. Font: Noto Sans JP (OFL).
The companion HTML preserves editable text, links and embedded fonts.
"""
from pathlib import Path
import argparse, base64, html, io, json, re, tempfile
from fontTools.ttLib import TTFont as FTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools import subset
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.graphics import renderPDF, renderSVG
from reportlab.lib.utils import ImageReader

WEB='https://mobilitydlab.com/oita-mirai-mobility-consortium/training/'
LECTURE=WEB+'lecture-20261111.html'
FORM='https://docs.google.com/forms/d/e/1FAIpQLSfuYI4BEl_HRrIx0bEcORS43flu51UYpkyn_p_A4yXNzsQkew/viewform'
W,H=595.2756,841.8898
M=34; CW=W-2*M
NAVY='#142D4E'; ORANGE='#D96732'; INK='#1D2D3E'; MUTED='#596779'; LINE='#D9E0E7'; PALE='#F3F6F9'

class PDF:
 def __init__(self, path, photo):
  self.path=path; self.photo_path=photo; self.page=1; self.records=[]
  self.c=canvas.Canvas(str(path),pagesize=(W,H),pageCompression=1,invariant=0)
  self.c.setTitle('大分未来モビリティ人材育成プログラム｜説明資料')
  self.c.setAuthor('トヨタカローラ大分株式会社／株式会社モビリティデザインラボ')
  self.c.setSubject('設立構想・国土交通省採択事業・活動・参加メリット・11月11日特別講演・参加方法')
 def record(self,kind,**kw): self.records.append(dict(page=self.page,kind=kind,**kw))
 def rect(self,x,y,w,h,color):
  self.c.setFillColor(HexColor(color));self.c.rect(x,H-y-h,w,h,stroke=0,fill=1)
  self.record('rect',x=x,y=y,w=w,h=h,color=color)
 def rule(self,x,y,w,color=LINE):self.rect(x,y,w,.55,color)
 def text(self,s,x,y,w,h,size=10.5,leading=None,bold=False,color=INK,link=None):
  leading=leading or size*1.48
  st=ParagraphStyle('t',fontName='JPB' if bold else 'JP',fontSize=size,leading=leading,textColor=HexColor(color),wordWrap='CJK',splitLongWords=True,allowWidows=0,allowOrphans=0)
  p=Paragraph(s,st);_,ph=p.wrap(w,h)
  if ph>h+.01:raise ValueError(f'Page {self.page} overflow: {s[:50]} {ph}>{h}')
  if x<0 or y<0 or x+w>W+.1 or y+ph>H:raise ValueError('Page bounds')
  p.drawOn(self.c,x,H-y-ph)
  if link:self.c.linkURL(link,(x,H-y-ph,x+w,H-y),relative=0,thickness=0)
  self.record('text',text=s,x=x,y=y,w=w,h=ph,size=size,leading=leading,bold=bold,color=color,link=link)
 def qr(self,url,x,y,size,label):
  q=QrCodeWidget(url,barLevel='M');a,b,c,d=q.getBounds()
  dr=Drawing(size,size,transform=[size/(c-a),0,0,size/(d-b),0,0]);dr.add(q)
  renderPDF.draw(dr,self.c,x,H-y-size)
  self.c.linkURL(url,(x,H-y-size,x+size,H-y),relative=0,thickness=0)
  self.record('qr',url=url,x=x,y=y,w=size,h=size,label=label,svg=renderSVG.drawToString(dr))
 def photo(self,x,y,w,h):
  im=Image.open(self.photo_path).convert('RGB');iw,ih=im.size
  # Fit width and crop vertically around the upper part of the portrait.
  target=w/h;ratio=iw/ih
  if ratio>target:
   nw=ih*target;left=(iw-nw)/2;im=im.crop((left,0,left+nw,ih))
  else:
   nh=iw/target;top=max(0,(ih-nh)*.18);im=im.crop((0,top,iw,top+nh))
  im.thumbnail((700,850));buf=io.BytesIO();im.save(buf,'JPEG',quality=91);data=buf.getvalue()
  self.c.drawImage(ImageReader(io.BytesIO(data)),x,H-y-h,w,h)
  self.record('photo',x=x,y=y,w=w,h=h,data=base64.b64encode(data).decode())
 def section(self,num,title,y):
  self.text(num,M,y,30,25,19,25,True,ORANGE)
  self.text(title,M+39,y+1,CW-39,25,16,24,True,NAVY)
 def header(self,n):
  self.rect(M,24,26,3,ORANGE)
  self.text('OITA MIRAI MOBILITY',M+36,20,255,16,8.5,13,True,NAVY)
  self.text('PROGRAM GUIDE  /  2026.10.27',367,20,195,16,8,13,False,MUTED)
  self.rule(M,45,CW)
 def footer(self,n):
  self.rule(M,811,CW)
  self.text('大分未来モビリティ人材育成プログラム',M,818,420,13,7.8,11,False,MUTED)
  self.text(f'{n:02d} / 02',518,818,46,13,8,11,True,NAVY)
 def next(self):self.c.showPage();self.page+=1
 def save(self):self.c.save()

def build(p):
 p.header(1)
 p.text('大分未来モビリティ人材育成プログラム',M,64,CW,34,22.3,32,True,NAVY)
 p.text('地域の課題を、来年度の実施・実証計画へ。',M,105,CW,20,12,18,False,MUTED)

 p.text('どなたでも参加無料',M,142,280,35,25,34,True,NAVY)
 p.text('自治体・企業・地域事業者・住民・学生など',M,180,290,18,9.8,15)
 p.text('2026.11 - 2027.2',341,144,222,30,21,29,True,NAVY)
 p.text('2026年11月〜2027年2月',341,180,222,18,10,15,False,MUTED)
 p.rule(M,207,CW)

 p.section('01','コンソーシアムを立ち上げる',222)
 p.text('JMSで発表した構想。自治体・企業・大学・地域の皆さまが課題・技術・人材を持ち寄り、具体的なサービスや実証を進める枠組みです。',M,255,CW,34,10.5,16)
 p.text('e-Palette活用や自動運転実証を起点に、将来は陸・海・空のモビリティに関わる取組みとの連携を目指します。',M,292,CW,31,9.7,14.5,False,MUTED)

 p.section('02','国土交通省の採択事業として人材育成',334)
 p.text('令和8年度「『交通空白』解消等リ・デザイン全面展開プロジェクト」<br/>（モビリティ人材・組織育成タイプ）',M,366,CW,32,9.5,14.5)
 p.text('トヨタカローラ大分株式会社が採択され、株式会社モビリティデザインラボ<br/>（MobilityDesignLab）と連携して企画・運営します。',M,402,CW,32,10.2,15.5)

 p.section('03','課題から、地域別の実施・実証計画へ',450)
 steps=['課題を共有','現地調査','サービス企画','アプリ開発','データ分析']
 stepw=CW/5
 for i,t in enumerate(steps):
  x=M+i*stepw
  p.text(f'{i+1:02d}',x,486,stepw-13,22,17,22,True,ORANGE)
  p.text(t,x,513,stepw-13,18,10.3,16,True,NAVY)
  if i<4:p.text('→',x+stepw-21,500,16,18,11,16,False,MUTED)
 p.rect(M,541,CW,35,PALE)
 p.text('2027年2月末を目標に',M+12,549,141,19,10,16,True,NAVY)
 p.text('来年度以降の実施・実証計画',M+160,547,CW-172,23,14,21,True,NAVY)
 p.text('本プログラム内のサービス開発・アプリ開発・データ分析も無料。<br/>車両管理・整備保守や、継続的な運営も見据えて計画します。',M,584,CW,31,9.8,14.5)
 p.rule(M,626,CW)
 p.text('e-Paletteを活用したサービス企画',M,638,255,22,12,18,True,NAVY)
 p.text('移動・観光・物流・停車中の活用など、<br/>地域に合うサービスを具体化します。',M,664,248,31,9.7,14.5)
 p.rect(299,639,.6,55,LINE)
 p.text('自動運転実証の計画',316,638,246,22,12,18,True,NAVY)
 p.text('ルート・安全性・運営条件を整理し、<br/>来年度以降の実証計画を検討します。',316,664,246,31,9.7,14.5)

 p.section('04','参加で得られること',711)
 # Five concise benefits retain all the invitation's value propositions.
 benefits=[
  '専門家・企業と、地域だけでは進めにくい課題を具体化',
  'サービス企画・アプリ開発・データ分析に取り組む',
  '一緒に実践する仲間・連携先を見つける',
  '来年度の検討・庁内説明に使える計画をつくる',
  '構想段階から、課題・希望をサービス・実証候補地の検討に反映',
 ]
 for i,t in enumerate(benefits):
  p.text('・'+t,M+(0 if i<3 else 272),746+(i if i<3 else i-3)*18,260 if i<3 else 255,36,9.4,14,False,INK)
 p.footer(1);p.next();p.header(2)

 p.text('人材育成プログラム 特別講演',M,66,CW,21,11,17,True,ORANGE)
 p.text('日高洋祐氏 特別講演',M,94,CW,35,25,34,True,NAVY)
 p.text('2026年11月11日（水）',M,143,386,26,18,25,True,NAVY)
 p.text('14:00-16:00',M,174,385,57,40,54,True,NAVY)
 p.text('会場 Garraway0　　参加費 無料',M,236,385,24,14,21,True,NAVY)
 p.text('大分市府内町1丁目1-12',M,266,385,18,10,15,False,MUTED)
 p.photo(451,142,110,130)
 p.text('写真：MaaS Tech Japan公式',443,279,119,13,6.8,10,False,MUTED)
 p.rule(M,296,CW)
 p.text('講師：MTJ社長 日高洋祐氏',M,309,CW,24,15,22,True,NAVY)
 p.text('株式会社MaaS Tech Japan 代表取締役CEO',M,335,CW,18,10.5,16,False,MUTED)
 p.text('国土交通省が目指す方向性と、地域交通・自動運転実証・データ分析／連携について、具体例を交えてお話しいただきます。<br/>当日は、コンソーシアムと人材育成プログラムの趣旨も説明します。',M,361,CW,51,10.5,16.5)
 p.text('後半：トークセッション・質疑応答',M,416,CW,20,11.5,18,True,NAVY)
 p.text('進行：MobilityDesignLabの植野氏',M,440,CW,21,12,18,True,NAVY)
 p.rule(M,474,CW)
 p.text('困りごと・やってみたいことから参加',M,491,CW,28,19,27,True,NAVY)
 p.text('フォームで関心や希望をお知らせください。',M,525,CW,18,10.5,16)
 p.text('企画書・事前資料は不要',M,550,270,23,12.5,19,True,NAVY)
 p.text('初回は30分〜1時間で相談',315,550,248,23,12.5,19,True,NAVY)
 p.rule(M,584,CW)
 p.text('01',M,595,30,21,15,21,True,ORANGE)
 p.text('人材育成プログラムHP',M+39,595,428,21,12,18,True,NAVY,WEB)
 p.text('全体像・活動テーマ・最新情報を確認',M+39,619,428,16,9.3,14,False,MUTED,WEB)
 p.rule(M,640,CW)
 p.text('02',M,651,30,21,15,21,True,ORANGE)
 p.text('11/11 特別講演の詳細',M+39,651,387,21,12,18,True,NAVY,LECTURE)
 p.text('日時・会場・当日の内容を確認',M+39,675,387,16,9.3,14,False,MUTED,LECTURE)
 p.qr(LECTURE,503,645,58,'講演の詳細')
 p.rule(M,705,CW)
 p.text('03',M,716,30,21,15,21,True,ORANGE)
 p.text('プログラム参加・相談フォーム',M+39,716,387,21,12,18,True,NAVY,FORM)
 p.text('地域の困りごと・やってみたいことを伝える',M+39,740,387,16,9.3,14,False,MUTED,FORM)
 p.qr(FORM,503,710,58,'プログラム参加・相談')
 p.text('講演専用の申込フォームではありません。',M+39,760,398,15,8.4,12,False,MUTED)
 p.text('参加無料と企業向けコンソーシアム年会費は別制度です。実際の運行・車両・保険等の費用・条件は別途協議。車両貸与・実証実施・採択・事業化を保証するものではありません。',M,781,CW,26,8.3,11.5,False,MUTED)
 p.footer(2)
 return benefits

def write_html(p,fontpaths,out):
 css='''@page{size:A4;margin:0}*{box-sizing:border-box}body{margin:0;background:#e6ebf1;color:#1D2D3E;font-family:JP,sans-serif}.page{position:relative;width:595.2756pt;height:841.8898pt;background:white;margin:15pt auto;overflow:hidden}.text{position:absolute;white-space:normal;overflow:visible}.text a{color:inherit;text-decoration:none}.text:focus{outline:1px solid #D96732}svg,img{display:block;width:100%;height:100%}.toolbar{font:14px sans-serif;background:white;padding:12px;text-align:center;position:sticky;top:0;z-index:3}.toolbar button{margin-left:15px;padding:6px 12px}@media print{body{background:white}.page{margin:0;break-after:page}.page:last-child{break-after:auto}.toolbar{display:none}}'''
 for name,key,weight in [('JP','JP',400),('JPB','JPB',700)]:
  css+=f"@font-face{{font-family:{name};src:url(data:font/ttf;base64,{base64.b64encode(Path(fontpaths[key]).read_bytes()).decode()}) format('truetype');font-weight:{weight}}}"
 parts=['<!doctype html><html lang="ja"><meta charset="utf-8"><title>大分未来モビリティ人材育成プログラム 編集用原稿</title><style>'+css+'</style><div class="toolbar">本文をクリックして編集できます。<button onclick="saveCopy()">編集済みHTMLを保存</button><button onclick="window.print()">印刷・PDF保存</button></div>']
 for page in (1,2):
  parts.append('<section class="page">')
  for r in p.records:
   if r['page']!=page:continue
   sty=f"left:{r['x']}pt;top:{r['y']}pt;width:{r['w']}pt;height:{r['h']}pt;"
   if r['kind']=='text':
    sty+=f"font-family:{'JPB' if r['bold'] else 'JP'};font-size:{r['size']}pt;line-height:{r['leading']}pt;color:{r['color']};font-weight:{700 if r['bold'] else 400};"
    txt=r['text']
    if r['link']:txt='<a href="'+html.escape(r['link'])+'">'+txt+'</a>'
    parts.append(f'<div class="text" contenteditable="true" style="{sty}">{txt}</div>')
   elif r['kind']=='rect':parts.append(f'<div style="position:absolute;{sty}background:{r["color"]}"></div>')
   elif r['kind']=='qr':parts.append(f'<a aria-label="{r["label"]}" href="{html.escape(r["url"])}" style="position:absolute;{sty}">{r["svg"]}</a>')
   elif r['kind']=='photo':parts.append(f'<img alt="日高洋祐氏" style="position:absolute;{sty}" src="data:image/jpeg;base64,{r["data"]}">')
  parts.append('</section>')
 parts.append('''<script>function saveCopy(){const h='<!doctype html>'+document.documentElement.outerHTML;const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([h],{type:'text/html'}));a.download='oita-mirai-mobility-program-guide-edited.html';a.click();URL.revokeObjectURL(a.href)}</script></html>''')
 (out/'oita-mirai-mobility-program-guide-editable.html').write_text(''.join(parts))

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--font-variable',required=True);ap.add_argument('--photo',default=str(Path(__file__).resolve().parent.parent/'assets'/'hidaka-yosuke.jpg'));ap.add_argument('--output-dir',default=str(Path(__file__).resolve().parent.parent));ap.add_argument('--pdf-name',default='program-guide.pdf');ap.add_argument('--qa-json');a=ap.parse_args()
 out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory() as td:
  fps={}
  for name,weight in [('JP',400),('JPB',700)]:
   f=FTFont(a.font_variable);instantiateVariableFont(f,{'wght':weight},inplace=True);f.flavor=None
   for rec in list(f['name'].names):
    if rec.nameID in (1,2,3,4,6):rec.string=f'NotoSansJP-Programme-{weight}'.encode(rec.getEncoding(),errors='replace')
   fp=Path(td)/(name+'.ttf');f.save(fp);fps[name]=fp;pdfmetrics.registerFont(TTFont(name,str(fp)))
  pdfmetrics.registerFontFamily('JP',normal='JP',bold='JPB',italic='JP',boldItalic='JPB')
  p=PDF(out/a.pdf_name,Path(a.photo));build(p);p.save()
  # Subset only the HTML font bytes; editable Japanese can fall back to local fonts.
  chars=''.join(re.sub('<[^>]+>','',r.get('text','')) for r in p.records)+'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
  for fp in fps.values():
   f=FTFont(fp);s=subset.Subsetter();s.populate(text=chars);s.subset(f);f.save(fp)
  write_html(p,fps,out)
  (out/'layout.json').write_text(json.dumps(p.records,ensure_ascii=False,indent=2))
  if a.qa_json:Path(a.qa_json).write_text(json.dumps([r for r in p.records if r['kind']=='text'],ensure_ascii=False,indent=2))
 print(json.dumps({'pages':2,'pdf':str(p.path),'text_boxes':sum(r['kind']=='text' for r in p.records)},ensure_ascii=False))
if __name__=='__main__':main()
