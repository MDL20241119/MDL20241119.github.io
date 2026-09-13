"""Build the public visual guide and its 18-page PDF from verified screen captures."""
from pathlib import Path
from html import escape
import argparse, json, hashlib
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.graphics.barcode import qr
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'oita-tourism/catalog'
APP='https://mobilitydlab.com/oita-tourism/'
PAGE_W,PAGE_H=768,1024
PAPER='#F8F7F3'; INK='#111111'; GRAY='#DADADA'
SIGNALS={'start':'#E7FF38','access':'#72D7FF','compare':'#FF4FC3','use':'#E7FF38'}
pages=json.loads((ROOT/'scripts/catalog/tourism-content.json').read_text())
shots={s['name']:s for s in json.loads((ROOT/'scripts/catalog/screens.json').read_text())}
assert len(pages)==16 and len({p['id'] for p in pages})==16
for p in pages:
    p['url']=shots[p['id']]['url']
    p['signal']={'14-search':'#72D7FF','15-source':'#72D7FF','16-guide':'#FF4FC3'}.get(p['id'],SIGNALS[p['group']])
    p['image']='screens/'+p['id']+'.jpg'
    assert (OUT/p['image']).is_file(),p['image']
    assert Image.open(OUT/p['image']).size==(1348,926)

args=argparse.ArgumentParser()
args.add_argument('--font-dir',type=Path,required=True)
font_dir=args.parse_args().font_dir
for name,filename in [('JP','NotoSansJP-Regular.ttf'),('JPB','NotoSansJP-Bold.ttf')]:
    pdfmetrics.registerFont(TTFont(name,str(font_dir/filename)))

pdf_path=OUT/'oita-tourism-catalog.pdf'
c=canvas.Canvas(str(pdf_path),pagesize=(PAGE_W,PAGE_H),pageCompression=1)
c.setTitle('大分観光・周遊データマップ｜実画面でわかる使い方カタログ')
c.setAuthor('Mobility Design Lab')
c.setSubject('16の実画面・18ページ／2026年9月13日撮影')

def rect(x,y,w,h,fill=PAPER,stroke=None):
    c.setFillColor(HexColor(fill));c.setStrokeColor(HexColor(stroke or fill))
    c.setLineWidth(.8);c.rect(x,PAGE_H-y-h,w,h,fill=1,stroke=bool(stroke))

def line(x1,y1,x2,y2,color=INK,width=.8):
    c.setStrokeColor(HexColor(color));c.setLineWidth(width)
    c.line(x1,PAGE_H-y1,x2,PAGE_H-y2)

def txt(text,x,y,size=16,font='JP',color=INK):
    c.setFont(font,size);c.setFillColor(HexColor(color))
    c.drawString(x,PAGE_H-y-size,text)

def wrap(text,width,size,font='JP'):
    lines=[]
    for para in text.split('\n'):
        cur=''
        for ch in para:
            if cur and pdfmetrics.stringWidth(cur+ch,font,size)>width:
                if ch in '、。，．）」』】!?':
                    lines.append(cur[:-1]);cur=cur[-1:]+ch
                else:lines.append(cur);cur=ch
            else:cur+=ch
        lines.append(cur)
    return lines

def block(text,x,y,width,size=16,leading=None,font='JP',color=INK,max_lines=None):
    leading=leading or size*1.5;lines=wrap(text,width,size,font)
    if max_lines: assert len(lines)<=max_lines,(text,lines)
    for i,t in enumerate(lines):txt(t,x,y+i*leading,size,font,color)
    return y+len(lines)*leading

def screenshot(path,x=32,y=358,w=704):
    h=w*926/1348
    c.drawImage(str(path),x,PAGE_H-y-h,w,h)
    c.setStrokeColor(HexColor(INK));c.setLineWidth(.7)
    c.rect(x,PAGE_H-y-h,w,h,stroke=1,fill=0)
    return h

def footer(n,url):
    line(32,993,736,993)
    txt('OITA TOURISM × MOBILITY',32,1003,10,'Helvetica-Bold')
    txt('この機能を開く >',514,1001,12,'JPB')
    c.linkURL(url,(510,8,649,30),relative=0,thickness=0)
    txt(f'{n:02d} / 18',676,1003,11,'Helvetica-Bold')

def header(category):
    rect(0,0,PAGE_W,PAGE_H)
    txt('MOBILITY DESIGN LAB',32,26,13,'Helvetica-Bold')
    txt(category,458,29,10,'Helvetica-Bold')
    line(32,54,736,54)

# Cover.
header('VISUAL CATALOG / 2026.09')
txt('OITA TOURISM × MOBILITY',32,79,13,'Helvetica-Bold')
block('観光の数字を、\n次の移動へ。',32,119,552,58,73,'JPB',max_lines=2)
txt('16',592,93,118,'Helvetica-Bold')
txt('REAL SCREENS',599,224,12,'Helvetica-Bold')
txt('大分観光・周遊データマップ',32,286,26,'JPB')
txt('実際の画面でわかる、できること・使い方。',32,325,17)
screenshot(OUT/'screens/01-start.jpg',y=374)
rect(32,876,704,58,SIGNALS['start'])
txt('行き方。現地の移動。地域のデータ。',50,890,25,'JPB')
txt('写真を見て、３つの手順で試せる操作カタログ。',32,954,17)
footer(1,APP);c.showPage()

for n,p in enumerate(pages,2):
    signal=p['signal']
    header(p['id'][:2]+' / '+p['category'])
    txt(p['id'][:2],29,83,81,'Helvetica-Bold')
    block(p['title'],157,88,579,40,50,'JPB',max_lines=2)
    block(p['lead'],157,209,579,17,26,max_lines=2)
    rect(32,279,704,33,signal)
    txt('FOR',44,288,11,'Helvetica-Bold');txt(p['audience'],88,286,14)
    rect(32,330,7,7,INK)
    block(p['focus'],49,323,687,14,18,max_lines=1)
    screenshot(OUT/p['image'])
    txt('PC実画面 / 2026.09.13撮影 / Web版では写真をタップして拡大',32,851,10,color='#555555')
    txt('HOW TO',32,876,11,'Helvetica-Bold')
    for i,step in enumerate(p['steps']):
        x=32+i*239
        rect(x,899,25,25,signal)
        txt(str(i+1),x+8,902,14,'Helvetica-Bold')
        block(step,x+34,900,193,15,20,'JPB',max_lines=2)
    block(p['tip'],32,951,704,12,17,color='#444444',max_lines=2)
    footer(n,p['url']);c.showPage()

# Closing page.
header('ACTION / START WITH ONE PLACE')
block('まずは、\nひとつの場所から。',32,103,704,52,69,'JPB',max_lines=2)
block('地域を知る。移動を確かめる。次に測ることを決める。\nアプリは、その会話を始めるための道具です。',32,276,704,19,31,max_lines=2)
actions=[('01','自治体・観光協会','地域の特徴と住民への影響を見て、調査・施策の優先順位を考える。'),('02','宿泊・観光施設','駅・宿泊・飲食・体験をつなぐ、周遊の条件を確かめる。'),('03','交通事業者・観光案内','乗り場と時刻表を確認し、実際の需要や乗り継ぎを調べる。')]
for i,(num,title,body) in enumerate(actions):
    y=373+i*102;line(32,y,736,y)
    txt(num,32,y+17,44,'Helvetica-Bold')
    txt(title,122,y+18,22,'JPB')
    block(body,122,y+55,614,15,21,max_lines=2)
rect(32,711,704,228,SIGNALS['start'])
txt('まず、暘谷駅から',53,739,28,'JPB')
txt('ハーモニーランドへ。',53,781,28,'JPB')
txt('「例から始める」を押して、往復を試す。',53,837,16)
txt('mobilitydlab.com/oita-tourism/',53,884,17,'Helvetica-Bold')
q=qr.QrCodeWidget(APP);b=q.getBounds();d=Drawing(143,143,transform=[143/(b[2]-b[0]),0,0,143/(b[3]-b[1]),0,0]);d.add(q)
renderPDF.draw(d,c,567,PAGE_H-751-143)
c.linkURL(APP,(32,PAGE_H-939,736,PAGE_H-711),relative=0,thickness=0)
block('交通は2026年9月の指定３日分の収録時刻表です。実際の運行・営業・歩行条件は別途確認。\n制作・運営：Mobility Design Lab。県の公式アプリではありません。',32,953,704,11,16,max_lines=2)
footer(18,APP);c.save()

# Responsive web gallery, authored from exactly the same content.
cards=[]
for p in pages:
    index=p['id'][:2];title=escape(p['title']).replace('\n','<br>')
    steps=''.join('<li>'+escape(s)+'</li>' for s in p['steps'])
    cards.append(f'''<article id="{p['id']}" class="screen-card {p['group']}" style="--signal:{p['signal']}">
      <div class="screen-heading"><span class="screen-number">{index}</span><div><p class="eyebrow">{escape(p['category'])}</p><h2>{title}</h2><p class="lead">{escape(p['lead']).replace(chr(10),'<br>')}</p></div></div>
      <p class="audience"><b>FOR</b> {escape(p['audience'])}</p>
      <p class="focus">{escape(p['focus'])}</p>
      <button class="screen-photo" data-photo="{p['image']}" data-caption="{escape(p['title'].replace(chr(10),''))}" data-url="{escape(p['url'])}" aria-label="{index} {escape(p['title'].replace(chr(10),''))}の画面写真を拡大"><img src="{p['image']}" alt="{escape(p['title'].replace(chr(10),''))}を操作するアプリの実画面" width="1348" height="926" loading="lazy" decoding="async"><span>画面写真を拡大 ＋</span></button>
      <div class="howto"><p class="eyebrow">HOW TO</p><ol>{steps}</ol></div>
      <p class="note">{escape(p['tip'])}</p><a class="open-feature" href="{escape(p['url'])}">この機能を開く <span aria-hidden="true">↗</span></a>
    </article>''')
html='''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#F8F7F3"><title>観光・周遊データマップ｜実画面でわかる使い方カタログ｜MDL</title><meta name="description" content="16の実画面でわかる、大分観光・周遊データマップの使い方。観光地へのアクセス、現地の移動、交通利用割合、観光統計と出典確認を３ステップで紹介。"><link rel="stylesheet" href="catalog.css"><script src="catalog.js" defer></script></head><body>
<a class="skip-link" href="#contents">カタログの内容へ</a><header class="site-header"><a class="brand" href="../../">MOBILITY<br>DESIGN LAB</a><nav aria-label="関連ページ"><a href="../">アプリを開く ↗</a><a href="oita-tourism-catalog.pdf">PDFを開く ↗</a></nav></header>
<main><section class="cover"><div><p class="eyebrow">OITA TOURISM × MOBILITY / VISUAL CATALOG</p><h1>観光の数字を、<br>次の移動へ。</h1><p class="app-name">大分観光・周遊データマップ</p><p class="lead">実際の画面でわかる、できること・使い方。</p></div><div class="cover-count"><b>16</b><span>REAL SCREENS</span></div><a class="cover-image" href="#contents"><img src="screens/01-start.jpg" width="1348" height="926" alt="大分観光・周遊データマップの最初の画面"></a><p class="cover-tagline">行き方。現地の移動。地域のデータ。</p><div class="cover-meta"><p>2026.09.13撮影 / 18ページのPDF版付き</p><a href="oita-tourism-catalog.pdf">配布用PDFを開く ↗</a></div></section>
<section class="contents" id="contents" aria-labelledby="contents-heading"><p class="eyebrow">HOW TO USE THIS CATALOG</p><h2 id="contents-heading">目的から選んで、写真でわかる。</h2><p>写真をタップすると拡大できます。「この機能を開く」から実際に試してください。</p><nav class="chapter-nav" aria-label="カタログの目次"><a href="#01-start"><span>01–03</span>地域を知る</a><a href="#04-access"><span>04–08</span>アクセスを調べる</a><a href="#09-modes"><span>09–12</span>数字を比べる</a><a href="#13-issues"><span>13–16</span>地域で使う</a></nav></section>
'''+''.join(cards)+'''
<section class="closing"><p class="eyebrow">ACTION / START WITH ONE PLACE</p><h2>まずは、<br>ひとつの場所から。</h2><p>地域を知る。移動を確かめる。次に測ることを決める。<br>アプリは、その会話を始めるための道具です。</p><div class="closing-actions"><a href="../">アプリを開く ↗</a><a href="oita-tourism-catalog.pdf">18ページのPDFを開く ↗</a></div><p class="note">掲載写真は2026年9月13日のPC実画面です。交通は2026年9月8・12・13日の収録時刻表に基づきます。実際の運行・営業・歩行条件は別途確認してください。</p></section></main>
<footer><p>© Mobility Design Lab / 県の公式アプリではありません。</p><a href="../#guide">アプリの使い方・出典</a><a href="../../#tourism-case">MDLの紹介ページ</a></footer>
<dialog id="screen-dialog" aria-labelledby="screen-caption"><div class="dialog-bar"><p id="screen-caption"></p><button id="close-dialog" type="button">閉じる ×</button></div><p class="dialog-hint">小さい画面では、写真を左右にスクロールして確認できます。</p><div class="image-scroll" tabindex="0" role="region" aria-label="拡大した画面写真"><img id="dialog-image" alt=""></div><a id="dialog-feature" class="open-feature" href="../">この機能を開く ↗</a></dialog></body></html>'''
(OUT/'index.html').write_text(html)
manifest={'captured':'2026-09-13','screenCount':16,'pdfPages':18,'images':[{'id':p['id'],'url':p['url'],'sha256':hashlib.sha256((OUT/p['image']).read_bytes()).hexdigest()} for p in pages]}
(ROOT/'scripts/catalog/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(f'Created {pdf_path} ({pdf_path.stat().st_size:,} bytes), 18 pages and web gallery.')
