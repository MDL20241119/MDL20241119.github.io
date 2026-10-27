#!/usr/bin/env python3
"""Create the two-page programme explanation. Never writes participation-flyer.pdf.

python3 build-program-guide.py --font-variable NotoSansJP.ttf --photo assets/hidaka-yosuke.jpg --output-dir .
Dependencies: reportlab, fonttools, Pillow. Font: Noto Sans JP (OFL).
The companion HTML preserves editable text, links and embedded fonts.
"""
from pathlib import Path
import argparse, base64, hashlib, html, io, json, math, re, tempfile
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
M=28; CW=W-2*M
NAVY='#102E53'; ORANGE='#D96732'; INK='#17212D'; MUTED='#536276'; LINE='#C7D3E1'; PALE='#EAF1FB'; PAPER='#F3F5F7'; WHITE='#FFFFFF'

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
 def text(self,s,x,y,w,h,size=10.5,leading=None,bold=False,color=INK,link=None,align=0):
  leading=leading or size*1.48
  st=ParagraphStyle('t',fontName='JPB' if bold else 'JP',fontSize=size,leading=leading,textColor=HexColor(color),wordWrap='CJK',splitLongWords=True,allowWidows=0,allowOrphans=0,alignment=align)
  p=Paragraph(s,st);_,ph=p.wrap(w,h)
  if ph>h+.01:raise ValueError(f'Page {self.page} overflow: {s[:50]} {ph}>{h}')
  if x<0 or y<0 or x+w>W+.1 or y+ph>H:raise ValueError('Page bounds')
  p.drawOn(self.c,x,H-y-ph)
  if link:self.c.linkURL(link,(x,H-y-ph,x+w,H-y),relative=0,thickness=0)
  self.record('text',text=s,x=x,y=y,w=w,h=ph,size=size,leading=leading,bold=bold,color=color,link=link,align=align)
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
 def panel(self,x,y,w,h,fill=WHITE,stroke=NAVY,r=3):
  self.c.setFillColor(HexColor(fill));self.c.setStrokeColor(HexColor(stroke));self.c.setLineWidth(.7)
  self.c.roundRect(x,H-y-h,w,h,r,stroke=1,fill=1)
  self.record('panel',x=x,y=y,w=w,h=h,color=fill,stroke=stroke,r=r)
 def band(self,x,y,w,label,size=12,h=24):
  self.rect(x,y,w,h,NAVY)
  self.text(label,x+10,y+(h-size*1.35)/2,w-20,h,size,size*1.35,True,WHITE)
 def circle(self,x,y,r,fill=NAVY,label=None,size=10):
  self.c.setFillColor(HexColor(fill));self.c.circle(x,H-y,r,stroke=0,fill=1)
  self.record('circle',x=x-r,y=y-r,w=2*r,h=2*r,color=fill)
  if label is not None:self.text(str(label),x-r,y-r+.4,2*r,2*r,size,size*1.5,True,WHITE,align=1)
 def arrow(self,x1,y1,x2,y2,color=NAVY):
  self.c.setStrokeColor(HexColor(color));self.c.setFillColor(HexColor(color));self.c.setLineWidth(1)
  self.c.line(x1,H-y1,x2,H-y2)
  ang=math.atan2(y2-y1,x2-x1);a=4.3
  pts=[(x2,y2),(x2-a*math.cos(ang)+2.4*math.sin(ang),y2-a*math.sin(ang)-2.4*math.cos(ang)),(x2-a*math.cos(ang)-2.4*math.sin(ang),y2-a*math.sin(ang)+2.4*math.cos(ang))]
  path=self.c.beginPath();path.moveTo(pts[0][0],H-pts[0][1])
  for xx,yy in pts[1:]:path.lineTo(xx,H-yy)
  path.close();self.c.drawPath(path,stroke=0,fill=1)
  x=min(x1,x2)-5;y=min(y1,y2)-5;w=abs(x2-x1)+10;h=abs(y2-y1)+10
  coords=' '.join(f'{xx-x},{yy-y}' for xx,yy in pts)
  svg=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}"><line x1="{x1-x}" y1="{y1-y}" x2="{x2-x}" y2="{y2-y}" stroke="{color}" stroke-width="1"/><polygon points="{coords}" fill="{color}"/></svg>'
  self.record('arrow',x=x,y=y,w=w,h=h,svg=svg)
 def header(self,n):
  self.rect(0,0,W,H,PAPER)
  self.text('大分未来モビリティ人材育成プログラム',M,20,350,18,10.1,15,True,MUTED)
  self.text('2026年度 国土交通省採択事業',386,22,182,15,8.5,12,True,NAVY,align=2)
 def footer(self,n):
  self.rule(M,814,CW,LINE)
  self.text('トヨタカローラ大分 × MobilityDesignLab',M,821,383,12,7.5,10.5,False,MUTED)
  self.text(f'2026.10.27   {n:02d} / 02',447,821,121,12,7.7,10.5,False,MUTED,align=2)
 def next(self):self.c.showPage();self.page+=1
 def save(self):self.c.save()

def build(p):
 p.header(1)
 # Read from national project, to shared vision, this year's activity and benefits.
 p.text('01  国土交通省の人材・組織育成事業の一環として',M,49,CW,24,14.4,22,True,NAVY)
 p.text('令和8年度「『交通空白』解消等リ・デザイン全面展開プロジェクト」<br/>（モビリティ人材・組織育成タイプ）',M,79,CW,27,9.2,13)
 p.text('トヨタカローラ大分株式会社が採択。株式会社モビリティデザインラボと連携して企画・運営。',M,111,CW,16,9.3,14,False,MUTED)
 p.text('大分未来モビリティ<br/>コンソーシアムを立ち上げる',M,140,CW,63,24.5,30.5,True,INK)
 p.text('JMSで発表した構想。設立に向けた準備を進めます。',M,207,CW,17,9.7,14,False,MUTED)

 p.panel(M,233,CW,100);p.band(M,233,CW,'02  VISION / コンソーシアムが目指す大分',12.5,h=23)
 p.text('大分をモビリティで、もっと元気に。',M+13,264,CW-26,33,23,31,True,NAVY)
 p.text('人口減少の抑制に貢献し、暮らし・仕事・交流が続く大分を目指す。<br/>e-Palette活用や自動運転実証を起点に、将来は陸・海・空の取組みとの連携へ。',M+13,301,CW-26,29,9.8,13.5)

 p.text('いろいろな分野・業界の皆さまと、共創する。',M,345,CW,23,14.4,21,True,NAVY)
 p.text('自治体・交通・観光・商業・福祉・企業・大学・住民・学生など',M,374,CW,18,10.8,16)
 p.text('課題・技術・人材を持ち寄り、具体的なサービスや事業を一緒につくります。',M,397,CW,15,9.8,14,False,MUTED)

 p.text('03  今年度の人材育成プログラムで、来年度の事業案をつくる',M,418,CW,23,14.0,21,True,NAVY)
 leftw=347;gap=18;right=M+leftw+gap;rightw=CW-leftw-gap
 p.panel(M,450,leftw,91);p.band(M,450,leftw,'今年度  2026年11月〜2027年2月',12.5,h=24)
 p.text('地域の課題・やってみたいことを、みんなで持ち寄る。',M+12,484,leftw-24,17,10.1,15,True,NAVY)
 p.text('課題共有→現地調査→企画→アプリ開発→データ分析',M+12,504,leftw-24,15,9.2,13.5)
 p.text('2027年2月末を目標に、地域別の実施・実証計画へ',M+12,524,leftw-24,14,9.1,13,False,MUTED)
 p.panel(right,450,rightw,91);p.band(right,450,rightw,'来年度  2027年度〜',11.5,h=24)
 p.text('実施・実証を検討',right+10,485,rightw-20,24,14.0,21,True,NAVY,align=1)
 p.text('費用・体制・実施条件を協議し、<br/>事業化や実証につなげる。',right+10,513,rightw-20,27,9.1,12.5,False,INK,align=1)
 p.arrow(M+leftw+2,500,right-2,500)

 p.text('04  参加する6つのメリット',M,553,323,25,15.3,23,True,NAVY)
 p.text('どなたでも参加無料',357,552,W-M-357,26,18,24,True,NAVY,align=2)
 p.text('トヨタのe-Paletteのサービス開発と、自動運転実証の検討を、一緒に。',M,583,CW,16,10.1,14.5,True,NAVY)
 benefits=[
  ('モビリティサービス企画','課題を、利用者・使い方・運営の具体案へ'),
  ('e-Paletteを活用したサービス開発','トヨタのe-Paletteを使うサービスを一緒に開発'),
  ('自動運転実証','ルート・安全性を整理し、実証を一緒に検討'),
  ('アプリ開発・DX・AI活用','必要な機能を、アプリや試作を通じて形に'),
  ('データ分析・改善','現地や試作のデータを、サービス改善に活用'),
  ('車両管理・整備保守','管理・整備保守を含め、続ける体制を考える'),
 ]
 half=(CW-12)/2
 for i,(title,body) in enumerate(benefits):
  col=i%2;row=i//2;x=M+col*(half+12);y=605+row*59
  core=i in (1,2)
  p.panel(x,y,half,51,PALE if core else WHITE,ORANGE if core else NAVY)
  p.circle(x+16,y+15,9,ORANGE if core else NAVY,i+1,9.8)
  p.text(title,x+33,y+7,half-44,18,11.0,16,True,NAVY)
  p.text(body,x+10,y+33,half-20,15,9.2,13)
 p.text('本プログラム内のサービス開発・アプリ開発・データ分析も無料。<br/>実運行・車両・保険・継続運用・管理保守等は別途協議。地域の希望を構想段階から検討に反映。',M,781,CW,27,9.0,12.5,False,MUTED)
 p.footer(1);p.next();p.header(2)

 p.text('05  人材育成プログラムの一環として',M,49,CW,22,12.5,19,True,NAVY)
 p.text('11月11日 特別講演を開催',M,79,CW,38,24.5,34,True,INK)
 p.panel(M,127,CW,327);p.band(M,127,CW,'日高洋祐氏 特別講演',16,h=28)
 p.photo(M+13,166,84,99)
 p.text('写真：MaaS Tech Japan公式',M+9,270,100,12,6.3,9,False,MUTED)
 p.text('2026年11月11日（水）',M+116,166,CW-132,28,19,26,True,NAVY)
 p.text('14:00-16:00',M+116,201,CW-132,43,30,40,True,NAVY)
 p.text('会場 Garraway0　参加費 無料',M+116,246,CW-132,23,12.5,19,True,NAVY)
 p.text('大分市府内町1丁目1-12',M+116,272,CW-132,17,9.5,14,False,MUTED)
 p.rule(M+12,299,CW-24,LINE)
 p.text('講師：MTJ社長 日高洋祐氏',M+13,311,CW-26,25,14,21,True,NAVY)
 p.text('株式会社MaaS Tech Japan 代表取締役CEO',M+13,338,CW-26,18,10,15,False,MUTED)
 p.text('国土交通省が目指す方向性と、地域交通・自動運転実証・データ分析／連携について、具体例を交えてお話しいただきます。<br/>当日は、コンソーシアムと人材育成プログラムの趣旨も説明します。',M+13,365,CW-26,48,10.1,15)
 p.rect(M+10,414,CW-20,35,PALE)
 p.text('後半：トークセッション・質疑応答',M+18,416,300,18,10.5,15,True,NAVY)
 p.text('進行：MobilityDesignLabの植野氏',M+18,432,CW-36,16,10.5,15,True,NAVY)

 p.text('企画書・事前資料は不要。まずは無料相談。',M,470,CW,27,18,26,True,NAVY)
 tw=(CW-26)/3
 for i,(title,body) in enumerate([
  ('1  困りごとを伝える','課題や、やってみたいことを<br/>フォームから伝える'),
  ('2  初回の打合せ','<b>30分〜1時間</b>で相談。<br/>地域の課題と希望を一緒に整理'),
  ('3  地域で具体化','仲間と現地調査・企画へ。<br/>来年度以降の実施・実証計画に')]):
  x=M+i*(tw+13);p.panel(x,506,tw,78)
  p.rect(x+.7,506.7,tw-1.4,24,PALE)
  p.text(title,x+8,511,tw-16,18,10.5,16,True,NAVY)
  p.text(body,x+9,541,tw-18,33,9.4,14,False,INK)
  if i<2:p.arrow(x+tw+2,548,x+tw+11,548)

 p.text('目的に合わせて選べる、3つの入口',M,600,CW,21,13.5,20,True,NAVY)
 links=[('人材育成<br/>プログラムHP','全体像・活動・最新情報',WEB,'プログラム全体の案内'),('11/11 特別講演<br/>詳細ページ','日時・会場・講演内容',LECTURE,'講演の詳細を確認'),('プログラム<br/>参加・相談フォーム','困りごと・希望を伝える',FORM,'講演専用ではありません')]
 lw=(CW-16)/3
 for i,(title,body,url,caption) in enumerate(links):
  x=M+i*(lw+8);p.panel(x,631,lw,138)
  p.rect(x+.7,631.7,lw-1.4,37,NAVY)
  p.text(title,x+7,635,lw-14,31,10.7,14.5,True,WHITE,link=url,align=1)
  p.text(body,x+7,675,lw-14,16,9.1,13,False,INK,link=url,align=1)
  p.qr(url,x+(lw-56)/2,694,56,caption)
  p.text(caption,x+5,752,lw-10,14,8.3,12,False,NAVY,link=url,align=1)
 p.text('参加無料と企業向けコンソーシアム年会費は別制度です。実際の運行・車両・保険等の費用・条件は別途協議。車両貸与・実証実施・採択・事業化を保証するものではありません。',M,784,CW,26,8.3,11.5,False,MUTED)
 p.footer(2)
 return benefits

def write_html(p,fontpaths,out):
 css='''@page{size:A4;margin:0}*{box-sizing:border-box}body{margin:0;background:#e6ebf1;color:#1D2D3E;font-family:JP,sans-serif}.page{position:relative;width:595.2756pt;height:841.8898pt;background:white;margin:15pt auto;overflow:hidden}.text{position:absolute;white-space:normal;overflow:visible}.text a{color:inherit;text-decoration:none}.text:focus{outline:1px solid #D96732}svg,img{display:block;width:100%;height:100%}.toolbar{font:14px sans-serif;background:white;padding:12px;text-align:center;position:sticky;top:0;z-index:3}.toolbar button{margin-left:15px;padding:6px 12px}@media print{body{background:white}.page{margin:0;break-after:page}.page:last-child{break-after:auto}.toolbar{display:none}}'''
 for name,key,weight in [('JP','JP',400),('JPB','JPB',800)]:
  css+=f"@font-face{{font-family:{name};src:url(data:font/ttf;base64,{base64.b64encode(Path(fontpaths[key]).read_bytes()).decode()}) format('truetype');font-weight:{weight}}}"
 parts=['<!doctype html><html lang="ja"><meta charset="utf-8"><title>大分未来モビリティ人材育成プログラム 編集用原稿</title><style>'+css+'</style><div class="toolbar">本文をクリックして編集できます。<button onclick="saveCopy()">編集済みHTMLを保存</button><button onclick="window.print()">印刷・PDF保存</button></div>']
 for page in (1,2):
  parts.append('<section class="page">')
  for r in p.records:
   if r['page']!=page:continue
   sty=f"left:{r['x']}pt;top:{r['y']}pt;width:{r['w']}pt;height:{r['h']}pt;"
   if r['kind']=='text':
    sty+=f"font-family:{'JPB' if r['bold'] else 'JP'};font-size:{r['size']}pt;line-height:{r['leading']}pt;color:{r['color']};font-weight:{800 if r['bold'] else 400};text-align:{['left','center','right'][r['align']]};"
    txt=r['text']
    if r['link']:txt='<a href="'+html.escape(r['link'])+'">'+txt+'</a>'
    parts.append(f'<div class="text" contenteditable="true" style="{sty}">{txt}</div>')
   elif r['kind']=='rect':parts.append(f'<div style="position:absolute;{sty}background:{r["color"]}"></div>')
   elif r['kind']=='panel':parts.append(f'<div style="position:absolute;{sty}background:{r["color"]};border:.7pt solid {r["stroke"]};border-radius:{r["r"]}pt"></div>')
   elif r['kind']=='circle':parts.append(f'<div style="position:absolute;{sty}background:{r["color"]};border-radius:50%"></div>')
   elif r['kind']=='arrow':parts.append(f'<div style="position:absolute;{sty}">{r["svg"]}</div>')
   elif r['kind']=='qr':parts.append(f'<a aria-label="{r["label"]}" href="{html.escape(r["url"])}" style="position:absolute;{sty}">{r["svg"]}</a>')
   elif r['kind']=='photo':parts.append(f'<img alt="日高洋祐氏" style="position:absolute;{sty}" src="data:image/jpeg;base64,{r["data"]}">')
  parts.append('</section>')
 parts.append('''<script>function saveCopy(){const h='<!doctype html>'+document.documentElement.outerHTML;const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([h],{type:'text/html'}));a.download='oita-mirai-mobility-program-guide-edited.html';a.click();URL.revokeObjectURL(a.href)}</script></html>''')
 (out/'oita-mirai-mobility-program-guide-editable.html').write_text(''.join(parts))

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--font-variable',required=True);ap.add_argument('--photo',default=str(Path(__file__).resolve().parent.parent/'assets'/'hidaka-yosuke.jpg'));ap.add_argument('--output-dir',default=str(Path(__file__).resolve().parent.parent));ap.add_argument('--pdf-name',default='program-guide.pdf');ap.add_argument('--qa-json');ap.add_argument('--font-cache');a=ap.parse_args()
 out=Path(a.output_dir);out.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory() as td:
  fps={}
  cache=Path(a.font_cache) if a.font_cache else Path(td)
  cache.mkdir(parents=True,exist_ok=True)
  key=hashlib.sha256(Path(a.font_variable).read_bytes()).hexdigest()[:12]
  for name,weight in [('JP',400),('JPB',800)]:
   fp=cache/f'NotoSansJP-{key}-{weight}.ttf'
   if not fp.exists():
    f=FTFont(a.font_variable);instantiateVariableFont(f,{'wght':weight},inplace=True);f.flavor=None
    for rec in list(f['name'].names):
     if rec.nameID in (1,2,3,4,6):rec.string=f'NotoSansJP-Programme-{weight}'.encode(rec.getEncoding(),errors='replace')
    f.save(fp)
   fps[name]=fp;pdfmetrics.registerFont(TTFont(name,str(fp)))
  pdfmetrics.registerFontFamily('JP',normal='JP',bold='JPB',italic='JP',boldItalic='JPB')
  p=PDF(out/a.pdf_name,Path(a.photo));build(p);p.save()
  # Subset only the HTML font bytes; editable Japanese can fall back to local fonts.
  chars=''.join(re.sub('<[^>]+>','',r.get('text','')) for r in p.records)+'0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
  for name,fp in list(fps.items()):
   f=FTFont(fp);s=subset.Subsetter();s.populate(text=chars);s.subset(f)
   subset_path=Path(td)/(name+'-subset.ttf');f.save(subset_path);fps[name]=subset_path
  write_html(p,fps,out)
  (out/'layout.json').write_text(json.dumps(p.records,ensure_ascii=False,indent=2))
  if a.qa_json:Path(a.qa_json).write_text(json.dumps([r for r in p.records if r['kind']=='text'],ensure_ascii=False,indent=2))
 print(json.dumps({'pages':2,'pdf':str(p.path),'text_boxes':sum(r['kind']=='text' for r in p.records)},ensure_ascii=False))
if __name__=='__main__':main()
