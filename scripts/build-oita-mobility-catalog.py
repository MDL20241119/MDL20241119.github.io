"""Build an 18-page PDF and matching responsive guide from verified live screens."""
from pathlib import Path
from html import escape
import argparse, json
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor
from reportlab.graphics.barcode import qr
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'oita-mobility/guide'
APP = 'https://mobilitydlab.com/oita-mobility/'
navigation = json.loads((ROOT / 'scripts/catalog/oita-mobility-navigation.json').read_text())
DATE = navigation['edition']
W, H = 720, 960
PAPER, INK, MUTED = '#F8F7F3', '#111111', '#535353'
COLORS = {'START':'#FF4FC3','PEOPLE':'#FF4FC3','ATLAS':'#72D7FF','LAB':'#E7FF38','DETAIL':'#E7FF38','DATA':'#72D7FF','ACTION':'#FF4FC3'}
pages = json.loads((ROOT / 'scripts/catalog/oita-mobility-content.json').read_text())
assert len(pages) == 16 and len({p['id'] for p in pages}) == 16
page_numbers = {p['id']: n for n,p in enumerate(pages,2)}
page_by_id = {p['id']: p for p in pages}
for route in navigation['routes']:
    assert route['start'] in page_numbers
    assert all(target in page_numbers for _,target in route['steps'])
args = argparse.ArgumentParser()
args.add_argument('--font-dir', type=Path, required=True)
fontdir = args.parse_args().font_dir
for name, filename in [('JP','NotoSansJP-Regular.ttf'),('JPB','NotoSansJP-Black.ttf')]:
    pdfmetrics.registerFont(TTFont(name, str(fontdir / filename)))

pdfmetrics.registerFont(TTFont('EN', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('ENB', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))

pdf = OUT / 'oita-mobility-catalog.pdf'
c = canvas.Canvas(str(pdf), pagesize=(W,H), pageCompression=1)
c.setTitle('大分モビリティ・アトラス 2.0｜ビジュアルカタログ')
c.setAuthor('株式会社モビリティデザインラボ / Mobility Design Lab')
c.setSubject('読む人別の5つの入口・ページ案内・重要な数字｜実画面でわかる18ページ｜'+navigation['edition_ja']+'改訂')
c.setCreator('Mobility Design Lab - verified browser screens and editable catalog source')

def rect(x,y,w,h,fill=PAPER,stroke=None):
    c.setFillColor(HexColor(fill)); c.setStrokeColor(HexColor(stroke or fill)); c.setLineWidth(.7)
    c.rect(x,H-y-h,w,h,fill=1,stroke=bool(stroke))

def line(x1,y1,x2,y2,color=INK,width=.7):
    c.setStrokeColor(HexColor(color));c.setLineWidth(width);c.line(x1,H-y1,x2,H-y2)

def txt(s,x,y,size=16,font='JP',color=INK):
    c.setFillColor(HexColor(color));c.setFont(font,size);c.drawString(x,H-y-size,s)

def wrap(s,width,size,font):
    result=[]
    for para in s.split('\n'):
        cur=''
        for ch in para:
            if cur and pdfmetrics.stringWidth(cur+ch,font,size)>width:
                if ch in '、。，．）」』】!?：・': result.append(cur[:-1]);cur=cur[-1:]+ch
                else: result.append(cur);cur=ch
            else: cur+=ch
        result.append(cur)
    return result

def block(s,x,y,width,size=16,font='JP',leading=None,color=INK,max_lines=None):
    rows=wrap(s,width,size,font); leading=leading or size*1.5
    if max_lines is not None: assert len(rows)<=max_lines,(s,len(rows),max_lines)
    for i,row in enumerate(rows): txt(row,x,y+i*leading,size,font,color)
    return y+len(rows)*leading

def photo(name,x,y,w,h=None):
    path=OUT/'screens'/name
    iw,ih=Image.open(path).size
    if h is None: h=w*ih/iw
    else:
        scale=min(w/iw,h/ih); dw,dh=iw*scale,ih*scale
        x+=(w-dw)/2;y+=(h-dh)/2;w,h=dw,dh
    c.drawImage(str(path),x,H-y-h,w,h)
    c.setStrokeColor(HexColor(INK)); c.setLineWidth(.7); c.rect(x,H-y-h,w,h,fill=0,stroke=1)
    return h

def link(label,url,x,y,w=160,size=12):
    txt(label,x,y,size,'JPB');c.linkURL(url,(x,H-y-25,x+w,H-y+4),relative=0,thickness=0)

def header(group):
    rect(0,0,W,H)
    txt('MOBILITY DESIGN LAB',32,25,12,'ENB')
    category='VISUAL CATALOG / '+group
    txt(category,688-pdfmetrics.stringWidth(category,'ENB',9),27,9,'ENB')
    line(32,54,688,54)

def internal_link(label,target,x,y,w,size=12):
    txt(label,x,y,size,'JPB')
    c.linkRect('',target,(x,H-y-25,x+w,H-y+4),relative=0,thickness=0)

def footer(n,url,label='アプリを開く'):
    line(32,927,688,927)
    internal_link('P02 読者別ガイドへ', 'purpose',32,935,160,11)
    link(label+' →',url,238,935,335,12)
    txt(f'{n:02d}',621,930,22,'ENB')
    txt('/ 18',659,938,11,'ENB')

def bookmark(p):
    c.bookmarkPage(p['id']);c.addOutlineEntry(p['title'].replace('\n',''),p['id'],level=0)

def intro(p,n):
    header(p['group']);bookmark(p)
    rect(32,81,66,66,COLORS[p['group']]);txt(f'{n:02d}',38,86,40,'ENB')
    block(p['title'],116,76,572,34,'JPB',44,max_lines=2)
    block(p['description'],32,185,656,17,leading=26,max_lines=2)
    line(32,248,688,248,'#C9C9C9')
    txt('読む人',32,257,12,'JPB')
    block(p['audience'],84,255,604,12.2,'JPB',max_lines=1)

def key_panel(p):
    value,unit,label,note = navigation['highlights'][p['id']]
    rect(32,292,656,78,COLORS[p['group']])
    is_latin=all(ord(ch)<128 for ch in value)
    font='ENB' if is_latin else 'JPB'
    size=42 if is_latin else 36
    while pdfmetrics.stringWidth(value,font,size)>190: size-=1
    txt(value,46,296,size,font)
    if unit: txt(unit,47,347,11.5,'JPB')
    line(246,306,246,356,INK,.8)
    block(label,261,305,415,18,'JPB',max_lines=1)
    block(note,261,340,415,11.5,max_lines=1)

# 01: cover.
header(DATE+' / READER GUIDE')
c.bookmarkPage('cover')
txt('OITA MOBILITY ATLAS',32,77,15,'ENB')
rect(593,75,95,31,COLORS['START']);txt('2.0',614,77,22,'ENB')
block('その用事、\n行って帰れる？',32,113,656,51,'JPB',66,max_lines=2)
block('大分の暮らしの移動を、公開データで確かめる。\nあなたの立場から、必要なページと機能へ。',32,263,656,18,leading=28,max_lines=2)
photo('people.jpg',32,335,656,414)
rect(32,760,656,58,INK)
txt('まずは、読む人別の入口へ',48,773,22,'JPB','#FFFFFF')
txt('P02',574,769,30,'ENB','#E7FF38')
c.linkRect('','purpose',(32,H-818,688,H-760),relative=0,thickness=0)
rect(32,837,656,53,COLORS['START'])
txt('暮らしの往復 → 地域の課題 → 改善案',49,850,22,'JPB')
txt('全18ページ / '+navigation['edition_ja']+' 読者別ガイド改訂 / 画面撮影 9月24日',32,901,11)
footer(1,APP);c.showPage()

for n,p in enumerate(pages,2):
    intro(p,n)
    if p['kind']=='audience':
        y=284
        for route in navigation['routes']:
            rect(32,y,656,106,'#FFFFFF',INK)
            rect(32,y,7,106,COLORS[route['group']])
            block(route['who'],48,y+9,439,19,'JPB',max_lines=1)
            block(route['goal'],48,y+39,439,14.5,max_lines=1)
            block(route['more'],48,y+66,439,10.8,max_lines=1)
            link(route['app_label']+' →',APP+route['url'],48,y+84,435,10.5)
            rect(503,y,185,106,COLORS[route['group']],INK)
            txt('読むページ / PAGES',516,y+7,10,'JPB')
            txt(route['pages'],516,y+23,39,'ENB')
            txt('ここから読む →',516,y+77,12,'JPB')
            c.linkRect('',route['start'],(503,H-y-106,688,H-y),relative=0,thickness=0)
            y+=114
        block(p['takeaway'],32,868,656,17,'JPB',max_lines=1)
        c.linkRect('','three-views',(32,H-891,390,H-864),relative=0,thickness=0)
        c.linkRect('','first-use',(391,H-891,688,H-864),relative=0,thickness=0)
        block(p['note'],32,901,656,10.5,color=MUTED,max_lines=1)
    elif p['kind']=='flow':
        y=295
        for i,(num,en,question,answer,img,url) in enumerate(p['rows']):
            color=COLORS[en]
            rect(32,y,656,176,'#FFFFFF',INK)
            rect(32,y,8,176,color)
            txt(en+' / P'+['04-06','07-09','10-12'][i],51,y+12,17,'ENB')
            block(question,51,y+43,365,23,'JPB',max_lines=1)
            block(answer,51,y+85,359,15,leading=24,max_lines=2)
            photo(img,441,y+18,228,142)
            internal_link('説明を読む →',['people-conditions','atlas-area','lab-baseline'][i],51,y+143,150,11)
            link('機能を開く →',APP+url,244,y+143,157,11)
            y+=187
        block(p['takeaway'],32,864,656,15,'JPB',max_lines=1)
        block(p['note'],32,894,656,10.5,color=MUTED,max_lines=2)
    elif p['kind']=='action':
        y=303
        for num,title,question,answer in p['rows']:
            rect(32,y,54,46,COLORS['ACTION']);txt(num,43,y+4,29,'ENB')
            txt(title,108,y-1,26,'JPB')
            block(question,108,y+48,569,17,leading=26,max_lines=2)
            block(answer,108,y+109,569,14,'JPB',leading=22,max_lines=2)
            line(108,y+159,688,y+159,'#CACACA');y+=178
        block(p['takeaway'],32,850,656,16,'JPB',max_lines=1)
        block(p['note'],32,884,656,10.5,leading=16,color=MUTED,max_lines=2)
    else:
        key_panel(p)
        photo(p['image'],32,385,656,353)
        block(p['caption'],32,750,656,10.3,leading=16,color=MUTED,max_lines=2)
        if p['kind']=='reading':
            for i,(title,body,color) in enumerate(p['legend']):
                x=32+i*223
                rect(x,797,210,78,color,INK);txt(title,x+10,805,15,'JPB')
                block(body,x+10,832,192,10.5,leading=15,max_lines=2)
        else:
            txt('HOW TO / 使い方',32,794,10,'JPB')
            for i,s in enumerate(p['steps']):
                x=32+i*223
                line(x,815,x+210,815)
                rect(x,828,20,20,COLORS[p['group']]);txt(str(i+1),x+6,831,11,'ENB')
                block(s,x+29,827,179,14,'JPB',leading=21,max_lines=2)
        block(p['note'],32,890,656,10.3,leading=15.5,color=MUTED,max_lines=2)
    footer(n,APP+p['url'],navigation['open_labels'][p['id']]);c.showPage()

# 18: final page / live links and source context.
header('ACTION / START HERE')
c.bookmarkPage('start')
block('行きたいところへ、\n行ける地域を。',32,89,656,43,'JPB',58,max_lines=2)
block('調べる道具から、地域で使える仕組みへ。\nまずは、一つの用事を選んで試してください。',32,232,656,20,leading=31,max_lines=2)
for i,(en,jp,img,url) in enumerate([('PEOPLE','往復を調べる','people.jpg','index.html'),('ATLAS','地域を比べる','atlas.jpg','atlas.html'),('LAB','改善案を試す','lab.jpg','policy.html')]):
    x=32+i*223;photo(img,x,335,210,150);rect(x,497,210,34,COLORS[en]);txt(en,x+12,505,15,'ENB')
    link(jp+' →',APP+url,x+12,545,190,16)
rect(32,600,656,145,COLORS['START'])
txt('アプリを開いて、地域と目的地を選ぶ。',50,618,21,'JPB')
txt('mobilitydlab.com/oita-mobility/',50,665,18,'ENB')
link('Webでカタログを読む →',APP+'guide/',50,706,300,13)
q=qr.QrCodeWidget(APP);b=q.getBounds();d=Drawing(105,105,transform=[105/(b[2]-b[0]),0,0,105/(b[3]-b[1]),0,0]);d.add(q)
rect(561,620,110,110,'#FFFFFF');renderPDF.draw(d,c,563,H-727)
txt('本番開発・データ連携・地域での活用のご相談',32,777,16,'JPB')
link('info@mobilitydlab.com','mailto:info@mobilitydlab.com',32,811,400,18)
block('制作：株式会社モビリティデザインラボ / 読者別案内改訂：'+DATE+' / 画面撮影：2026.09.24\n出典：公開アプリ・各データの原典。地図：地理院タイル。画面内の出典表示を保持。\n写真内の数値は操作例。データの基準日・取得日・有効期間は、アプリの出典で確認できます。',32,858,656,10.2,leading=17,max_lines=3)
footer(18,APP);c.save()

# Web guide: same exact copy, semantic text, responsive layout and original screenshot links.
def e(s): return escape(str(s),quote=True)
def br(s): return e(s).replace('\n','<br>')
def webphoto(img,caption,cls=''):
    iw,ih=Image.open(OUT/'screens'/img).size
    return f'<figure class="{cls}"><a href="screens/{e(img)}" target="_blank" rel="noopener" aria-label="{e(caption)}を拡大"><img src="screens/{e(img)}" width="{iw}" height="{ih}" alt="{e(caption)}" loading="lazy" decoding="async"></a><figcaption>{e(caption)} <span>実画面を拡大 ↗</span></figcaption></figure>'

def reader_card(r):
    steps=''.join(f'<a href="#{target}"><span>P{page_numbers[target]:02d}</span> {e(label)}</a>' for label,target in r['steps'])
    return f'''<article class="reader-card" id="route-{r['id']}" style="--accent:{COLORS[r['group']]}">
    <div class="reader-person"><h3>{e(r['who'])}</h3><p>{e(r['goal'])}</p></div>
    <div class="reader-detail"><p class="reader-learn">{e(r['learn'])}</p><nav class="route-steps" aria-label="{e(r['who'])}の読む順番">{steps}</nav><p class="reader-more">{e(r['more'])}</p></div>
    <div class="reader-actions"><a class="reader-pages" href="#{r['start']}"><small>まず読むページ</small><strong><span>P</span>{r['pages']}</strong><span>読む →</span></a><a class="reader-app" href="{APP+r['url']}">{e(r['app_label'])} ↗</a></div></article>'''

def key_html(p):
    value,unit,label,note=navigation['highlights'][p['id']]
    return f'<aside class="key-panel" aria-label="ここがポイント"><div class="key-value"><strong>{e(value)}</strong><span>{e(unit)}</span></div><div class="key-copy"><strong>{e(label)}</strong><p>{e(note)}</p></div></aside>'

sections=[]
for n,p in enumerate(pages,2):
    head=f'<header class="chapter-title"><p class="chapter-kicker"><span class="page-number"><small>P</small>{n:02d}</span><span>{e(p["group"])}</span></p><h2>{br(p["title"])}</h2><p class="lead">{e(p["description"])}</p><p class="for"><b>このページを読む人</b> {e(p["audience"])}</p></header>'
    if p['kind']=='audience':
        body='<div class="reader-list">'+''.join(reader_card(r) for r in navigation['routes'])+'</div>'
        body+='<p class="reader-help">迷ったら <a href="#three-views">P03 全体像</a> へ。進め方は <a href="#first-use">P17 はじめの一歩</a> へ。</p>'
    elif p['kind']=='flow':
        body='<div class="flow-list">'
        for i,(num,en,q,a,img,url) in enumerate(p['rows']):
            target=['people-conditions','atlas-area','lab-baseline'][i]
            span=['04-06','07-09','10-12'][i]
            body+=f'<article class="flow-card" style="--accent:{COLORS[en]}"><b>{en}</b><h3>{e(q)}</h3><p>{br(a)}</p><img src="screens/{img}" alt="{en}の実画面" loading="lazy"><a class="flow-pages" href="#{target}">P<span>{span}</span> 説明を読む →</a><a href="{APP+url}">{en}を開く ↗</a></article>'
        body+='</div>'
        body+=f'<p class="takeaway">{e(p["takeaway"])}</p>'
    elif p['kind']=='action':
        body='<ol class="action-list">'+''.join(f'<li><span>{num}</span><div><h3>{e(t)}</h3><p>{e(q)}</p><strong>{e(a)}</strong></div></li>' for num,t,q,a in p['rows'])+'</ol>'
        body+=f'<p class="takeaway">{e(p["takeaway"])}</p>'
    else:
        body=key_html(p)+webphoto(p['image'],p['caption'])
        if p['kind']=='reading':
            body+='<div class="legend-cards">'+''.join(f'<div style="background:{col}"><h3>{e(t)}</h3><p>{br(b)}</p></div>' for t,b,col in p['legend'])+'</div>'
        else:
            body+='<ol class="steps">'+''.join(f'<li><span>{i+1}</span>{e(s)}</li>' for i,s in enumerate(p['steps']))+'</ol>'
        if p.get('links'):body+='<nav class="detail-links" aria-label="詳細分析の機能">'+''.join(f'<a href="{APP+u}">{e(t)} ↗</a>' for t,u in p['links'])+'</nav>'
    next_p=pages[n-1] if n<17 else None
    next_link=f'<a href="#{next_p["id"]}">次は P{n+1:02d}｜{e(next_p["title"].replace(chr(10),""))} →</a>' if next_p else '<a href="#start">P18 アプリを使い始める →</a>'
    sections.append(f'<section class="chapter {e(p["kind"])}" id="{p["id"]}" style="--accent:{COLORS[p["group"]]}">{head}<div class="chapter-body">{body}<p class="note">{e(p["note"])}</p><a class="chapter-open" href="{APP+p["url"]}">{e(navigation["open_labels"][p["id"]])} ↗</a></div><nav class="chapter-nav" aria-label="P{n:02d}のページ案内"><a href="#purpose">← 読む人別の入口に戻る</a>{next_link}</nav></section>')

html='''<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#F8F7F3">
<title>実画面でわかるビジュアルカタログ｜大分モビリティ・アトラス 2.0</title>
<meta name="description" content="誰が使うとよいか、何がわかるか。大分の移動を暮らしから調べるPEOPLE・ATLAS・LABを、現在の実画面で紹介。18ページのPDFも保存できます。">
<link rel="canonical" href="https://mobilitydlab.com/oita-mobility/guide/"><link rel="icon" href="../assets/favicon.svg"><link rel="stylesheet" href="guide.css?v=20260924">
<meta property="og:title" content="その用事、行って帰れる？｜大分モビリティ・アトラス 2.0"><meta property="og:description" content="目的・使う人・わかることを、実画面で。更新版ビジュアルカタログ。"><meta property="og:image" content="https://mobilitydlab.com/oita-mobility/guide/screens/people.jpg"><meta property="og:type" content="website"></head>
<body><a class="skip" href="#main">本文へ移動</a><header class="site-head"><a href="../../">MOBILITY DESIGN LAB</a><nav aria-label="カタログのメニュー"><a href="#purpose">読む人別ガイド</a><a href="../">アプリを開く ↗</a><a class="pdf-link" href="oita-mobility-catalog.pdf">PDF・18ページ ↓</a></nav></header>
<main id="main"><section class="cover"><div><p class="eyebrow">OITA MOBILITY ATLAS <span class="version">2.0</span></p><h1>その用事、<br>行って帰れる？</h1><p class="cover-lead">大分の暮らしの移動を、公開データで確かめる。<br><strong>あなたの立場から、必要なページと機能へ。</strong></p><p class="edition">ビジュアルカタログ / 2026年9月24日更新</p><div class="hero-actions"><a class="button" href="#purpose">自分が読むページを選ぶ ↓</a><a href="oita-mobility-catalog.pdf">PDF・18ページを保存 ↗</a></div></div>'''
html+=webphoto('people.jpg','PEOPLE / 大分駅前から買い物先への往復を調べた実画面','hero-photo')
html+='</section><nav class="reader-shortcuts" aria-label="読む人別の入口">'+''.join(f'<a href="#route-{r["id"]}"><span>{e(r["short"])}</span><small>P{r["pages"]} →</small></a>' for r in navigation['routes'])+'</nav>'
html+=''.join(sections)
html+='''<section class="closing" id="start"><p class="eyebrow">P18　 ACTION / START HERE</p><h2>行きたいところへ、<br>行ける地域を。</h2><p>調べる道具から、地域で使える仕組みへ。<br>まずは、一つの用事を選んで試してください。</p><div class="hero-actions"><a class="button" href="../">地域と目的地を選ぶ →</a><a href="oita-mobility-catalog.pdf">PDF・18ページを開く ↗</a><a href="#purpose">読む人別ガイドに戻る ↑</a></div><p class="consult">本番開発・データ連携・地域での活用のご相談<br><a href="mailto:info@mobilitydlab.com">info@mobilitydlab.com ↗</a></p></section></main>
<footer class="site-foot"><p>MOBILITY DESIGN LAB / OITA MOBILITY ATLAS 2.0</p><p>制作：株式会社モビリティデザインラボ。画面撮影・内容確認：2026年9月24日。<br>出典：公開アプリ・各データの原典。地図：地理院タイル。画面内の出典表示を保持しています。<br>写真内の数値は操作例です。データの基準日・取得日・有効期間は、アプリの出典で確認できます。</p><nav><a href="../usage.html">利用条件・データの扱い</a><a href="../data-catalog.html">データ・出典</a><a href="../../">MDLサイト</a></nav></footer></body></html>'''
html=html.replace('2026年9月24日更新',navigation['edition_ja']+' 読者別ガイド改訂').replace('guide.css?v=20260924','guide.css?v=20260926.2')
html=html.replace('画面撮影・内容確認：2026年9月24日。','画面撮影・内容確認：2026年9月24日。読者別案内改訂：'+navigation['edition_ja']+'。')
(OUT/'index.html').write_text(html)
print(json.dumps({'pdf':str(pdf),'pages':18,'web':str(OUT/'index.html'),'screens':len(list((OUT/'screens').glob('*.jpg')))},ensure_ascii=False))
