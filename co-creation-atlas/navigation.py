"""Purpose-led navigation, shared by every Atlas page. No research data edits."""
from html import escape
from pathlib import Path
import re
import json

BASE = '/co-creation-atlas/'
VERSION = '20261011.1'
GROUPS = [
    ('共創の場をつくる', [
        ('共創施設の事例を探す', BASE+'?lens=co#explore', '共創拠点・リビングラボ'),
        ('共創の事例を比較する', BASE+'learn/choose/?lens=co', '支援機能・運営・実装への接続'),
        ('共創の基礎を学ぶ', BASE+'learn/first-co-creation/', '共創を始めるための考え方'),
    ]),
    ('まちを育てる', [
        ('行きたくなる場所を探す', BASE+'destination-experiences/', '食と体験・150の事例'),
        ('まちづくりの事例を探す', BASE+'?lens=place#explore', 'まちづくり・地域運営'),
        ('まちづくりの事例を比較する', BASE+'learn/choose/?lens=place', '対象地域・担い手・維持管理・変化'),
        ('まちづくりの基礎を学ぶ', BASE+'learn/#town', '暮らしと地域から考える'),
    ]),
    ('都市の成長を読む', [
        ('福岡市と世界10都市を読む', '/research/fukuoka-startup-policy/', '仕事・所得・住まいの変化'),
        ('問いから選ぶ', '/research/fukuoka-startup-policy/#chapters', '5つの章から読む'),
        ('都市から選ぶ', '/research/fukuoka-startup-policy/#cities', '世界10都市の索引'),
        ('資料をダウンロード', '/research/fukuoka-startup-policy/#downloads', 'スマホ版・PC版の37枚'),
    ]),
    ('考え方と進め方を学ぶ', [
        ('空間をつくる4社の思想を読む', BASE+'spatial-design/', 'O+A・Gensler・CWA・PENSON／23の実空間'),
        ('都市の思想家から学ぶ', BASE+'learn/urban-thinkers/', '9人の思想と18の実践'),
        ('8つの工程で学ぶ', BASE+'#start', '課題を捉えるところから社会実装まで'),
        ('横断分析を読む', BASE+'#insights', '複数の実践から考える'),
        ('自分の計画をつくる', BASE+'learn/workbook/', '記入・保存できる実践シート'),
        ('教材の全体像', BASE+'learn/', '基礎・工程・実践の学習案内'),
    ]),
]

UTILITY=[('すべての事例',BASE+'#explore'),('横断比較',BASE+'learn/choose/'),('使い方',BASE+'catalog/'),('原典',BASE+'learn/library/')]

def utilities():
    return '<div class="atlas-nav-utilities">'+''.join(f'<a href="{url}">{title}</a>' for title,url in UTILITY)+'</div>'

def assets():
    return f'<link rel="stylesheet" href="{BASE}navigation.css?v={VERSION}"><script defer src="{BASE}navigation.js?v={VERSION}"></script>'

def groups(mode):
    out=[]
    for i,(label,links) in enumerate(GROUPS):
        opened=''
        entries=''.join(f'<a href="{escape(url,quote=True)}"><strong>{escape(title)}</strong><span>{escape(desc)}</span></a>' for title,url,desc in links)
        if i==len(GROUPS)-1:
            entries+=utilities()
        out.append(f'<details class="atlas-nav-group" name="atlas-{mode}-group"{opened}><summary>{escape(label)}<span aria-hidden="true" class="atlas-nav-plus">＋</span></summary><div class="atlas-nav-links">{entries}</div></details>')
    return ''.join(out)

def header():
    return ('<header class="topbar atlas-topbar">'
        '<a class="brand" href="/" aria-label="モビリティデザインラボのトップ"><span class="brand-mark">MDL.</span><span>MOBILITY<br>DESIGN LAB</span></a>'
        f'<a class="atlas-home-link" href="{BASE}" aria-label="ATLASのトップ">ATLAS<span>共創とまちづくり</span></a>'
        f'<nav class="atlas-desktop-nav" aria-label="ATLASメニュー">{groups("desktop")}</nav>'
        '<details class="atlas-mobile-menu"><summary class="atlas-mobile-toggle">メニュー<span aria-hidden="true" class="atlas-menu-icon">＋</span></summary>'
        '<nav class="atlas-mobile-panel" aria-label="ATLASモバイルメニュー">'
        f'<a class="atlas-panel-home" href="{BASE}">ATLASトップ <span aria-hidden="true">↗</span></a>{groups("mobile")}'
        '<p class="atlas-menu-hint">知りたいテーマから読む。事例を比べ、自分の計画へ。</p></nav></details></header>')

def integrate_index(page):
    """Four large photo entrances; leave all research/search sections untouched."""
    root=Path(__file__).resolve().parent
    media=json.loads((root/'data/media.json').read_text())
    cases=json.loads((root/'data/cases.json').read_text())
    entries=json.loads((root/'data/atlas-entries.json').read_text()) if (root/'data/atlas-entries.json').exists() else None
    # Keep the current published counts rather than treating slides as cases.
    co=re.search(r'入口 A / (\d+)事例',page)
    place=re.search(r'入口 B / (\d+)事例',page)
    stats=re.search(r'(\d+事例 · \d+か国 · 実写真\d+枚)',page)
    counts=(co.group(1) if co else '67',place.group(1) if place else '77')
    current_stats=stats.group(1) if stats else '115事例 · 26か国 · 実写真139枚'
    specs=[
        ('co','共創の場を<br>つくる','共創施設・リビングラボ',counts[0]+'事例',BASE+'?lens=co#explore','aalto-class-2'),
        ('place','まちを<br>育てる','まちづくり・地域運営',counts[1]+'事例',BASE+'?lens=place#explore','punggol-digital-district'),
        ('growth','都市の成長を<br>読む','福岡市と世界10都市','37枚','/research/fukuoka-startup-policy/',None),
        ('learn','考え方と<br>進め方を学ぶ','9人の思想・共創プロセス','',BASE+'learn/','aalto-lowfi'),
    ]
    cards=[];credits=[]
    for n,(kind,title,desc,count,url,asset) in enumerate(specs,1):
        if asset:
            m=next(m for m in media if m.get('assetId')==asset)
            src=BASE+m['local'];alt=m['alt'];rights=m.get('licenseUrl') or m.get('rightsUrl') or m['sourceUrl']
            credit=f'{escape(m["credit"])} · <a href="{escape(m["sourceUrl"],quote=True)}" target="_blank" rel="noopener noreferrer">掲載元</a> · <a href="{escape(rights,quote=True)}" target="_blank" rel="noopener noreferrer">{escape(m["license"])}</a><br>{escape(m.get("imageDate",""))} · {escape(m.get("changes",""))}'
        else:
            src='/research/fukuoka-startup-policy/assets/fukuoka-night-unsplash.webp';alt='福岡タワーと水辺の夜景。2022年公開、撮影日不明。'
            credit='Nichika Sakurai / Unsplash · <a href="/research/fukuoka-startup-policy/#credits">原写真・利用条件</a><br>2022年公開、撮影日不明。表示枠に合わせた切り抜き。'
        cards.append(f'<a class="atlas-gateway-card {kind}" href="{url}"><div class="atlas-gateway-photo"><img src="{src}" alt="{escape(alt,quote=True)}" width="900" height="600" loading="eager"><span class="atlas-gateway-number" aria-hidden="true">0{n}</span></div><div class="atlas-gateway-label"><h2>{title}</h2><span class="atlas-gateway-arrow" aria-hidden="true">↗</span><p>{desc}<span>{count}</span></p></div></a>')
        credits.append(f'<div><strong>0{n} {re.sub("<br>","",title)}</strong><p>{credit}</p></div>')
    gateway='<section class="atlas-gateway" id="entrances" aria-labelledby="atlas-gateway-title"><div class="atlas-gateway-intro"><p class="eyebrow">WORLD CO-CREATION ATLAS</p><h1 id="atlas-gateway-title">世界の実践から、<br>共創とまちづくりを学ぶ。</h1><p class="atlas-gateway-instruction">知りたいことから、4つの入口へ。</p></div><div class="atlas-gateway-grid">'+''.join(cards)+'</div><div class="atlas-gateway-meta"><p>'+current_stats+'</p><a href="'+BASE+'catalog/">はじめての方へ：使い方を見る →</a></div><details class="atlas-gateway-credits"><summary>写真の出典・撮影時点</summary><div>'+''.join(credits)+'</div><p>写真は既存掲載素材を使用。04はAalto Design Factoryの試作風景で、思想家本人の写真ではありません。</p></details></section>'
    if 'class="atlas-gateway"' in page:
        return page
    page=re.sub(r'<aside class="catalog-entry".*?</aside>', '',page,count=1,flags=re.S)
    page,n=re.subn(r'<section class="atlas-hero">.*?</section><section class="atlas-doors".*?</section>',gateway,page,count=1,flags=re.S)
    assert n==1,'The original Atlas entrance layout was not found.'
    return page

def refresh_existing(root):
    """Update generated navigation only; keep all article bodies byte-for-byte."""
    updated=0
    for p in Path(root).rglob('index.html'):
        before=p.read_text()
        if '<header class="topbar' not in before:
            continue
        after,n=re.subn(r'<header class="topbar[^\"]*">.*?</header>',header(),before,count=1,flags=re.S)
        assert n==1,p
        after=re.sub(r'<link[^>]+href="[^"]*navigation\.css[^\"]*"[^>]*>', '',after)
        after=re.sub(r'<script[^>]+src="[^"]*navigation\.js[^\"]*"[^>]*></script>', '',after)
        after=after.replace('</head>',assets()+'</head>',1)
        if p==Path(root)/'index.html':
            after=integrate_index(after)
        if after!=before:
            p.write_text(after)
            updated+=1
    return updated

if __name__=='__main__':
    print(f'Updated navigation on {refresh_existing(Path(__file__).resolve().parent)} pages.')
