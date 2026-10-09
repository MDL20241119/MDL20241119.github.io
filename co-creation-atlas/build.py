"""Build the public, source-backed MDL co-creation atlas. Python standard library only."""
import json, html
import learning
import value_chain
import atlas_routes
import evidence
import catalog
import expert_context
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DATA=json.loads((ROOT/'data/cases.json').read_text())
CHAINS=value_chain.read(DATA)
ENTRIES=atlas_routes.read(DATA)
MEDIA=json.loads((ROOT/'data/media.json').read_text()) if (ROOT/'data/media.json').exists() else []
# Preserve existing attributed photos; new cases may explicitly mark rights as pending.
missing_photos={c['id'] for c in DATA if not c.get('photoPending')}-{m.get('caseId') for m in MEDIA}
if missing_photos:
    raise ValueError('写真がない事例: '+', '.join(sorted(missing_photos)))
for item in MEDIA:
    for key in ('caseId','sourceUrl','credit','alt','license'):
        if not item.get(key): raise ValueError(f'写真の{key}が未記入: {item.get("assetId")}')
    if item.get('remote'):
        if item.get('status')!='provider-embed' or not item['remote'].startswith('https://'):
            raise ValueError('外部写真の埋め込み方法を確認してください')
    elif not (ROOT/item['local']).is_file():
        raise ValueError('写真ファイルがありません: '+item['local'])
    elif (ROOT/item['local']).stat().st_size == 0:
        raise ValueError('写真ファイルが空です: '+item['local'])
COUNTERS=json.loads((ROOT/'data/counterpoints.json').read_text())
THEMES={'city':('まち・暮らしをよくする','市民の課題、地域での共創・実証を知りたい。'),'people':('仲間・チームをつくる','異なる専門性を持つ人の集め方を知りたい。'),'prototype':('試作・実証の場をつくる','設備・専門家・現場をどうつなぐか知りたい。'),'business':('事業化につなげる','実証の先の購入・契約・事業移管を知りたい。'),'digital':('データ・仮想空間で試す','都市モデルやデジタルツインを活かしたい。'),'future':('アートから未来を考える','科学や表現から、新しい問いを見つけたい。')}
DATE='2026.10.07'
BASE='https://mobilitydlab.com/co-creation-atlas/'
STAGES=['','課題を捉える','未来を問う','仲間をつくる','デジタルで試す','現物をつくる','現場で確かめる','事業にする','社会へ広げる']
TYPES={'university':'大学・研究機関','company':'企業・事業化制度','city':'都市・地域の実証','network':'産業・研究ネットワーク','expert-practice':'有識者が関わる調査・実践'}
REGIONS={'north-america':'北米','europe':'ヨーロッパ','asia':'アジア','latin-america':'中南米','africa':'アフリカ','oceania':'オセアニア'}
def e(v): return html.escape(str(v if v is not None else ''),quote=True)
def para(v): return ''.join(f'<p>{e(x)}</p>' for x in str(v).split('\n') if x.strip())
def external(url,text,cl=''): return f'<a href="{e(url)}" target="_blank" rel="noopener noreferrer" class="{cl}">{text} ↗</a>'
def source_link(source, text=None, cl=''):
    if source.get('access') == 'private':
        assert not source.get('url'), 'Private source URLs must not enter public data'
        return f'<span class="{e(cl)}">{e(source["title"])}</span>'
    return external(source['url'], e(source['title']) if text is None else text, cl)
def path(c): return f'cases/{c["id"]}/'
def case_link(code,text=None):
    c=next((c for c in DATA if c['code']==code),None)
    return f'<a href="{path(c)}">{e(text or c["name"])}</a>' if c else e(text or code)
def credit(m):
    if not m:return ''
    if m.get('kind') == 'diagram':
        return f'<figcaption class="credit"><strong>{e(m["caption"])}</strong><br>DIAGRAM: {e(m["credit"])} · {external(m["sourceUrl"],"根拠資料")}<details class="photo-details"><summary>図の説明</summary><p>{e(m["alt"])}<br>{e(m["imageDate"])} · {e(m["license"])}</p></details></figcaption>'
    date=f' · {e(m.get("imageDate",""))}' if m.get('imageDate') else ''
    license_url=(m.get('licenseUrl') if m.get('status')=='cleared-cc' else m.get('rightsUrl')) or m.get('rightsUrl') or m.get('licenseUrl') or m['sourceUrl']
    license_link=external(license_url,e(m.get('license','利用条件')))
    changes=(' · '+e(m['changes'])) if m.get('changes') else ''
    caption=f'<strong>{e(m.get("scopeLabel") or m.get("caption") or m.get("alt", ""))}</strong><br>'
    details=f'<details class="photo-details"><summary>写真の詳細</summary><p>{e(m.get("caption", ""))}<br>{e(m.get("title",m.get("name","")))}{date}{changes}</p></details>'
    return f'<figcaption class="credit">{caption}PHOTO: {e(m["credit"])} · {external(m["sourceUrl"],"掲載元")} · {license_link}{details}</figcaption>'

def media_url(m,prefix=""):
    if m.get("remote"): return m["remote"]
    revision='?v='+m['revision'] if m.get('revision') else ''
    return prefix+m['local']+revision
def no_crop(m):
    return m.get("noCrop",False) or m.get("status")=="cleared-editorial-only"

def photo(m,alt='',cls='',prefix='',loading='lazy'):
    width,height=m.get('dimensions',[1600,1000])
    image_style=f' style="max-width:{width}px;margin-inline:auto"' if width < 600 else ''
    visual=f'<img{image_style} src="{e(media_url(m,prefix))}" alt="{e(alt or m.get("alt",m.get("name","")))}" loading="{loading}" width="{width}" height="{height}">'
    if m.get('status')=='provider-embed':
        visual=f'<a data-flickr-embed="true" class="photo-source-link" href="{e(m["sourceUrl"])}" target="_blank" rel="noopener noreferrer" aria-label="{e(m["name"])}の写真を掲載元で見る">{visual}</a>'
    return f'<figure class="{cls} {"no-crop" if no_crop(m) else ""}">{visual}{credit(m)}</figure>'
def media_for(c):return sorted([m for m in MEDIA if m.get('caseId')==c['id']],key=lambda m:m.get('kind')=='diagram')
for n,c in enumerate(DATA,1):
    c['number']=f'{n:02d}';ms=media_for(c)
    if ms:
        m=ms[0];c['image']=media_url(m);c['imageAlt']=m.get('alt',c['name']);c['imageNoCrop']=no_crop(m);c['imageEmbedSource']=m['sourceUrl'] if m.get('status')=='provider-embed' else '';c['imageCredit']=m['credit'];c['imageSource']=m['sourceUrl'];c['imageRights']=(m.get('licenseUrl') if m.get('status')=='cleared-cc' else m.get('rightsUrl')) or m.get('rightsUrl') or m.get('licenseUrl') or m['sourceUrl'];c['imageLicense']=m['license'];c['imageDate']=m.get('imageDate','');c['imageChanges']=m.get('changes','');c['imageCaption']=m.get('caption','')
        if m.get('kind') == 'diagram':c['imageKind']='diagram'
        else:c.pop('imageKind',None)
        c['photoCount']=sum(x.get('kind')!='diagram' for x in ms)
    else:c.pop('image',None)
    if 'stages' not in c:c['stages']=[c['stage']]

def head(title,description,url,prefix=''):
    return f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)} | MDL WORLD CO-CREATION ATLAS</title><meta name="description" content="{e(description)}"><meta name="theme-color" content="#f23bc8"><link rel="canonical" href="{e(url)}"><meta property="og:type" content="article"><meta property="og:image" content="https://mobilitydlab.com/co-creation-atlas/assets/aalto-class-2.jpg"><meta property="og:image:alt" content="Aalto Design Factoryの試作授業。Photo: Aalto Design Factory"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}"><meta property="og:url" content="{e(url)}"><link rel="stylesheet" href="{prefix}style.css?v=20260928.12"><link rel="stylesheet" href="{prefix}map.css?v=20260928.12"><link rel="stylesheet" href="{prefix}learning.css?v=20260928.12"><link rel="stylesheet" href="{prefix}value-chain.css?v=20260928.12"><link rel="stylesheet" href="{prefix}atlas-routes.css?v=20260928.12"><script defer src="{prefix}atlas-routes.js?v=20260928.12"></script><script defer src="{prefix}learning.js?v=20260928.12"></script><link rel="stylesheet" href="{prefix}photo-rich.css?v=20261007.2"><link rel="preload" href="{prefix}assets/display.woff2" as="font" type="font/woff2" crossorigin><link rel="preload" href="{prefix}assets/jp-black.woff" as="font" type="font/woff" crossorigin><script defer src="{prefix}map.js?v=20260928.12"></script><script defer src="{prefix}app.js?v=20260928.12"></script></head><body><a class="skip" href="#main">本文へスキップ</a>'''
def header(prefix=''):
    nav=f'<a href="{prefix}?lens=co#explore">共創を探す</a><a href="{prefix}?lens=place#explore">まちづくりを探す</a><a href="{prefix}learn/first-co-creation/">基礎を学ぶ</a><a href="{prefix}#start">8工程で学ぶ</a><a href="{prefix}#explore">事例を探す</a><a href="{prefix}learn/choose/">比較する</a><a href="{prefix}learn/workbook/">実践シート</a><a href="{prefix}learn/library/">原典</a>'
    return f'<header class="topbar"><a class="brand" href="/" aria-label="モビリティデザインラボのトップ"><span class="brand-mark">MDL.</span><span>MOBILITY<br>DESIGN LAB</span><span class="edition">RESEARCH / 01<br>WORLD CO-CREATION ATLAS</span></a><nav class="topnav" aria-label="メインメニュー">{nav}</nav><details class="menu"><summary>目次 ＋</summary><nav aria-label="モバイル目次">{nav}</nav></details></header>'
def footer():return f'<footer class="footer"><div><div class="display">MAKE IDEAS<br>WORK IN THE WORLD.</div><p style="margin-top:18px">モビリティデザインラボ｜WORLD CO-CREATION ATLAS<br>学習版 3.3 · 更新日 {DATE}</p></div><div><p>編集・分析：モビリティデザインラボ<br>写真・動画の権利は各権利者に帰属します。<br>本レポートは各施設との提携・推薦を示すものではありません。</p><p><a href="/">MDL公式サイト</a> ／ <a href="/co-creation-atlas/#sources">出典・編集方針</a></p></div></footer>'+'<script async src="https://embedr.flickr.com/assets/client-code.js" charset="utf-8"></script>'
def video_dialog():return '<dialog class="video-dialog" id="video-dialog"><div class="dialog-top"><strong class="dialog-title">公式動画</strong><button type="button" data-close>閉じる ×</button></div><div class="dialog-body"></div><p>動画が再生できない場合は、各項目の「公式サイトで見る」をご利用ください。</p></dialog>'
def cards():
    out=[]
    featured=['aalto-design-factory','quintbridge','punggol-digital-district','kamakura-living-lab','barcelona-superblocks','ogal-shiwa','michigan-central-newlab-detroit','marineterrein-amsterdam','ars-electronica-futurelab']
    ordered=sorted(DATA,key=lambda c:featured.index(c['id']) if c['id'] in featured else 100+DATA.index(c))
    for c in ordered:
        ms=media_for(c);m=ms[0] if ms else None
        visual=f'<div class="card-photo {"no-crop" if no_crop(m) else ""}"><img src="{e(media_url(m))}" alt="{e(m.get("alt",c["name"]))}" loading="lazy" width="800" height="500"><span class="card-no">{c["number"]}</span><span class="card-type">{e(TYPES[c["type"]])}</span></div>' if m else f'<div class="card-typographic color-{c["stage"]}"><span class="card-no">{c["number"]}</span><div class="display">{e(c.get("shortName",c["name"]))}</div></div>'
        if not m:
            visual=f'<div class="atlas-photo-missing"><p class="eyebrow">CASE {c["number"]} / {e(c["entry"]["unit"])}</p><strong class="display">{e(c.get("shortName",c["name"]))}</strong><p>写真の転載条件は確認中です。現場の写真は公式サイトでご覧ください。</p></div>'
        image_href=m['sourceUrl'] if m and m.get('status')=='provider-embed' else path(c)
        image_label=(c['name']+'の写真を掲載元で見る') if m and m.get('status')=='provider-embed' else c['name']+'の詳細を読む'
        embed_attributes=' data-flickr-embed="true" class="card-photo no-crop"' if m and m.get('status')=='provider-embed' else ''
        if embed_attributes:
            visual=f'<img src="{e(media_url(m))}" alt="{e(m.get("alt",c["name"]))}" loading="lazy" width="{m.get("dimensions",[1024,683])[0]}" height="{m.get("dimensions",[1024,683])[1]}">'
        real_photos=[x for x in ms if x.get('kind')!='diagram']
        thumbs=''.join(f'<a class="{"no-crop" if no_crop(x) else ""}" href="{path(c)}#field-photos" aria-label="{e(c["name"])}の写真を見る"><img src="{e(media_url(x))}" alt="{e(x["alt"])}" loading="lazy" width="400" height="250"></a>' for x in real_photos[1:3])
        thumb_strip=f'<div class="card-photo-strip">{thumbs}</div>' if thumbs else ''
        photo_count=f'<a class="card-photo-count" href="{path(c)}#field-photos">写真 {len(real_photos)}枚 ↗</a>' if real_photos else ''
        photo_note=(f'<span class="card-photo-context">{("模式図" if m.get("kind")=="diagram" else "写真")}：{e(m.get("scopeLabel",m.get("scope","写真")))}</span>' if m.get('scope') else '') if m else ''
        out.append(f'<article class="case-card" data-id="{e(c["id"])}"><a{embed_attributes} href="{e(image_href)}" aria-label="{e(image_label)}">{visual}</a>{thumb_strip}{photo_count}{photo_note}<div class="card-body">{atlas_routes.badges(c)}<div class="card-place">{e(c["country"])} / {e(c["city"])}</div><h3><a href="{path(c)}">{e(c["name"])}</a></h3><p class="card-learning-label">この事例から学べること</p><div class="tagline" data-card-learning>{e(c["tagline"])}</div>{atlas_routes.metadata(c)}<p class="card-summary">{e(c["lead"])}</p><div class="card-stage">{c["stage"]:02d} {STAGES[c["stage"]]} <span>／ {e(TYPES[c["type"]])}</span></div><div class="card-foot"><span>{external(c["sources"][0]["url"],"主な情報源")}</span><a href="{path(c)}"><strong>事例を読む →</strong></a></div></div>{f"<div class=\"card-credit\">{("DIAGRAM" if m.get("kind")=="diagram" else "PHOTO")}: {e(m['credit'])} · 利用条件は詳細ページに記載</div>" if m else ""}</article>')
    return ''.join(out)
STAGE_DESC=[
('誰の、どんな困りごとか。','当事者と現場を観察し、解く課題を選ぶ。技術や設備の導入を課題そのものにしない。','課題・当事者・現状値・課題オーナー'),
('どんな未来を、なぜ目指すか。','アートや未来シナリオで前提を問い直す。問いが要求仕様や評価軸をどう変えたかを残す。','未来の問い・仮説・価値観の対立'),
('誰と、どの責任で進めるか。','多様な人を集めるだけでなく、担当時間、役割、知財、意思決定を合意する。','混成チーム・活動時間・合意書'),
('現物をつくる前に、何を試すか。','データや仮想環境で仮説を検証する。モデルの更新主体と現実との差分まで設計する。','モデル・データ条件・検証結果'),
('触って確かめられる形にする。','専門家と設備を組み合わせ、安全に試作する。試作品と量産・保守可能な製品を区別する。','試作品・技術仕様・安全条件'),
('暮らしや現場で、どう変わるか。','利用者、天候、業務、混雑など実条件で反復。利用者が改善判断に関わる仕組みを持つ。','運用ログ・利用者評価・改善判断'),
('誰が買い、誰が運営するか。','有償購入、契約、導入部門、運用予算をつなぐ。試す予算と継続する予算を分ける。','発注・契約・運用体制・採算仮説'),
('別の現場でも、続けられるか。','標準、専門人材、保守、資金を移す。二拠点目での再現性と地域条件の違いを確かめる。','再現手順・移管・保守・学習記録')]

def map_ui():
    countries=json.loads((ROOT/'assets/map-countries.json').read_text())
    grid=''.join(f'<path d="M{x} 0V600"/>' for x in range(0,1201,100))+''.join(f'<path d="M0 {y}H1200"/>' for y in range(0,601,100))
    paths=''.join(f'<path d="{c["path"]}" data-country="{e(c["name"])}" data-label-x="{c["label"][0]}" data-label-y="{c["label"][1]}"/>' for c in countries)
    return (ROOT/'map-ui.html').read_text().replace('__GRID__',grid).replace('__COUNTRIES__',paths).replace('拠点','事例').replace('>28<','>'+str(len(DATA))+'<')

def build_index():
    countries=len({country for c in DATA for country in c.get('countries',[c['country']])});source_count=len(set(s['url'] for c in DATA for s in c['sources'] if s.get('url')))
    hero=next((m for m in MEDIA if m.get('hero')),MEDIA[0] if MEDIA else None)
    out=[head('世界の共創から、地域と事業のつくり方を学ぶ。',f'世界{countries}か国・{len(DATA)}件の共創・まちづくり・都市研究を、インプット・価値創造機能・アウトプット・アウトカムで解説。社会実装から逆算した工夫を一次情報で読み解く。',BASE),header(),'<main id="main">']
    out[0] = expert_context.styles(catalog.styles(out[0])).replace("app.js?v=20260928.12", "app.js?v=20261006.1").replace("map.js?v=20260928.12", "map.js?v=20261007.1")
    out.append(catalog.entry())
    out.append(atlas_routes.hero(DATA,MEDIA,photo))
    out.append(expert_context.teaser())
    out.append('<div class="section-index"><p class="eyebrow">CONTENTS / 読みたいところから</p><div class="links"><a href="learn/"><b>01</b>教材の全体像</a><a href="#explore"><b>02</b>世界の事例</a><a href="#insights"><b>03</b>横断分析</a><a href="learn/workbook/"><b>04</b>自分の計画へ</a></div></div>')
    learning_start = len(out)
    out.append(learning.entry())
    out.append(value_chain.framework().replace("28事例",str(len(DATA))+"事例"))
    out.append(atlas_routes.shared_reading())
    out.append('<section id="start" class="start-guide"><div class="intro-strip"><h2>このサイトで、<br>わかること。</h2><div class="intro-topics"><div><b>01</b><strong>共創の仕組み</strong><p>どんな場で、誰が何をするのか。</p></div><div><b>02</b><strong>運営・資金・成果</strong><p>誰が負担し、何が確認できたのか。</p></div><div><b>03</b><strong>日本で活かす条件</strong><p>取り入れるヒントと、注意すべき点。</p></div></div></div><div class="purpose-heading"><div><p class="eyebrow">VALUE CREATION / 価値創造機能の8ステップ</p><h2>価値を生み出す、8つの工程。</h2></div><p>4つの切り口のうち「価値創造機能」を具体化する工程です。進め方・記入例・実践シートを使い、必要な工程から始めて行き来します。</p></div><div class="purpose-grid">')
    for i,(question,desc,result) in enumerate(STAGE_DESC,1):
        n=sum(i in c['stages'] for c in DATA)
        out.append(f'<a class="purpose-card" href="learn/step-{i:02d}/"><span class="display">{i:02d}</span><div><h3>{STAGES[i]}</h3>{'<small>公共サービス・地域活動として続けることも含む</small>' if i==7 else ''}<p>{e(question)}</p></div><span class="purpose-count">実践教材・{n}事例 →</span></a>')
    out.append('</div><div class="start-shortcuts"><span>全体像を先に知りたい方へ</span><a href="#insights">6つの横断分析を読む ↓</a><a href="#comparison" data-open-comparison>28事例を一覧で比較 ↓</a><a href="learn/#town">まちづくりの基礎を学ぶ →</a><a href="learn/when-work-stalls/">つまずきから探す →</a></div></section>')
    out.append(f'''<section class="explorer" id="explore" data-explorer><div class="section-head"><div><p class="eyebrow">01 / WORLD EXPLORER</p><div class="display">FIND YOUR NEXT IDEA.</div><h2>知りたいことから、事例を探す。</h2></div><p>目的・キーワード・地域で絞り込み。<br>事例一覧と世界地図を切り替えて探せます。</p></div>{atlas_routes.explorer_controls()}<div class="filters"><label>キーワード<input type="search" id="case-search" placeholder="施設名、都市名、調達、市民参加、ロボット…" autocomplete="off"></label><label>知りたいこと<select id="theme"><option value="">すべての目的</option>{"".join(f'<option value="{k}">{v[0]}</option>' for k,v in THEMES.items())}</select></label><label>地域<select id="region"><option value="">すべての地域</option><option value="north-america">北米</option><option value="europe">ヨーロッパ</option><option value="asia">アジア</option><option value="latin-america">中南米</option><option value="africa">アフリカ</option><option value="oceania">オセアニア</option></select></label></div><details class="advanced-filters"><summary>さらに絞り込む：運営主体・8つの工程</summary><div class="advanced-inner"><label>運営・仕組みの種類<select id="type"><option value="">すべての種類</option>{''.join(f'<option value="{k}">{v}</option>' for k,v in TYPES.items())}</select></label></div><div class="stage-filters" role="group" aria-label="工程で絞り込む"><button data-stage-filter="" aria-pressed="true">すべての工程</button>{''.join(f'<button data-stage-filter="{i}" aria-pressed="false">{i:02d} {STAGES[i]}</button>' for i in range(1,9))}</div></details><div id="active-filters" class="active-filters" aria-label="現在の検索条件" hidden></div><div class="resultline"><p aria-live="polite"><strong id="result-count">{len(DATA)}</strong>件の事例</p><button id="clear-filters" class="text-button">絞り込みを解除</button></div><div class="view-tabs" role="tablist" aria-label="事例の探し方"><button id="list-tab" role="tab" aria-selected="true" aria-controls="list-view" data-view="list">事例一覧で探す</button><button id="map-tab" role="tab" aria-selected="false" aria-controls="map-view" data-view="map" tabindex="-1">世界地図で探す</button></div>{map_ui()}<div id="list-view" role="tabpanel" aria-labelledby="list-tab"><div class="results-heading" id="results"><h2>気になる事例を、詳しく読む。</h2><p class="meta">カードから運営・資金・成果・応用条件へ。<br><span id="shown-count"></span></p></div><div class="cards">{cards()}</div><div class="empty" id="empty-result" hidden><h3>条件に合う事例がありません。</h3><p>キーワードを短くするか、絞り込みを解除してください。</p></div><div class="more-wrap"><button class="btn black" id="show-more">さらに9件を見る ↓</button></div></div></section>''')
    # Put the explorer before the optional learning material; preserve all anchors.
    explorer_section = out.pop()
    out.insert(learning_start, explorer_section)
    out.append('<section id="chapters"><div class="section-head pink"><div><p class="eyebrow">02 / A PRACTICAL TABLE OF CONTENTS</p><div class="display">8 STEPS. MANY PATHS.</div><h2>いま必要な工程から、深く読む。</h2></div><p>8工程は一本道ではありません。現場での発見を課題や試作へ戻し、必要に応じて繰り返します。</p></div><div class="stage-grid">')
    for i,(question,desc,result) in enumerate(STAGE_DESC,1):
        names=[c for c in DATA if c['stage']==i]
        out.append(f'<article class="stage"><div class="display">{i:02d}</div><p class="eyebrow">{e(question)}</p><h3>{STAGES[i]}</h3><p>{e(desc)}</p><p class="deliverable"><strong>この工程で残すもの</strong><br>{e(result)}</p><p class="note-inline">主な事例：{e(" / ".join(c.get("shortName",c["name"]) for c in names))}</p><a href="learn/step-{i:02d}/">進め方・記入例・シートへ →</a><a href="#explore" data-go-stage="{i}">この工程の事例を探す ↗</a></article>')
    out.append('</div><details><summary class="compare-toggle">施設名から直接読む：全事例の索引 ＋</summary><div class="all-case-index">'+''.join(f'<a href="{path(c)}"><span>{c["number"]}</span>{e(c["name"])} / {e(c["country"])}</a>' for c in DATA)+'</div></details></section>')
    out.append('''<section id="insights"><div class="section-head blue"><div><p class="eyebrow">03 / CROSS-CASE ANALYSIS</p><div class="display">BEYOND THE BUILDING.</div><h2>成果を分けるのは、つながり方。</h2></div><p>ここからは公開資料を横断したMDLの分析です。特定施設の公式見解や、効果の因果証明とは区別して読んでください。</p></div><div class="analysis-lead"><div class="statement"><div class="display">WHO DECIDES?<br>WHO PAYS?<br>WHO CONTINUES?</div><h3>課題の当事者と、<br>続ける責任者をつなぐ。</h3></div><div class="explanation"><span class="label">MDL ANALYSIS / 条件付きの提言</span><p style="margin-top:20px">この調査から優先すべきと考えるのは、<strong>課題、チーム、検証、購入、運営移管を、一つの案件として管理すること</strong>です。施設の広さやイベント数だけでは、社会で続く仕組みができたかは判断できません。</p><p>ただし、全ての活動に事業化を求めるのも誤りです。教育、芸術、公共サービスは異なる価値を持ちます。目的ごとに成果を定義し、そのうえで次の責任者と財源へ接続できているかを確かめます。</p><p class="note-inline">本調査の公開資料では、28対象を同じ分母・期間・対照群で比較できる統一ROIは確認できません。施設の優劣を点数化するランキングは作成していません。</p></div></div><div class="insights">''')
    insights=[
    ('01','市民参加は、人数より影響力。','生活者へのアンケートと、生活者が課題・仕様・継続判断を変えられる共創は別です。参加の結果、何を変更したかを記録し、参加しにくい人や負担を負う人の声も拾う必要があります。','S01-F01','S01-F03'),
    ('02','チームには、時間と役割を渡す。','多様な人を集めても、担当時間や意思決定権がなければ案件は進みません。企業の担当者、学生・研究者、現場の専門家が継続して関わる条件を、募集時点で示す仕組みが参考になります。','S03-F01','S03-F02'),
    ('03','実証の先に、買い手を置く。','有償パイロットは、技術評価と事業部の関与をつなぐ手段です。ただし有償化だけで量産や長期契約は保証されません。試験購入から本導入へ進む条件、決裁者、運用費を分けて設計します。','S07-F01','S07-F02'),
    ('04','データ基盤には、更新の仕事がある。','デジタルツインや3D都市モデルは、作成した時点で完成するものではありません。更新主体、現実との差分、データ利用条件、日常業務への定着を含めて費用と便益を評価する必要があります。','S04-F02','S04-F03'),
    ('05','支援実績と、導入効果を分ける。','参加社数、試作品、パイロット数は活動量です。継続契約、現場導入、採算、働く人や住民への変化までを同じ数字で代用できません。累計・年度・報告年の違いも比較前に揃える必要があります。','S05-F05','S08-F03'),
    ('06','横展開は、設備より運用の移植。','専門家、設計仕様、契約、人材育成、保守を次の現場へ渡す仕組みが不可欠です。ネットワーク化も調整費を伴います。共有設備の便益が接続コストを上回る条件を案件ごとに検証します。','S08-F01','S08-F02')]
    for n,title,txt,c1,c2 in insights:out.append(f'<article class="insight"><div class="insight-top"><span class="display">{n}</span><h3>{title}</h3></div><p>{txt}</p><div class="ref">関連事例：{case_link(c1)} ／ {case_link(c2)}</div></article>')
    out.append('</div>'+atlas_routes.comparison_teaser())


    band=[m for m in MEDIA if m.get('feature')][:2]
    if len(band)<2:band=MEDIA[1:3]
    if band:out.append('<div class="photo-band">'+''.join(photo(m) for m in band)+'</div>')
    out.append('<div class="section-head yellow"><div><p class="eyebrow">A NECESSARY COUNTERPOINT</p><div class="display">QUESTION THE SUCCESS.</div><h2>魅力的な事例こそ、限界まで読む。</h2></div></div><div class="counterpoints">')
    for i,z in enumerate(COUNTERS,1):
        value=z['metric']['value'] if z.get('metric') else '2020'
        out.append(f'<article class="counterpoint"><p class="eyebrow">COUNTERPOINT {i:02d} / {e(z["date"])}</p><div class="display">{e(value)}</div><h3>{e(z["title"])}</h3><p>{e(z["summary"])}</p><p class="counter-limit"><strong>読み違えないために</strong><br>{e(z["doNotConclude"])}</p><p>{e(z["implication"])}</p><div class="counter-sources">'+''.join(f'<p>{external(t["url"],e(t["title"]))}</p>' for t in z['sources'])+'</div></article>')
    out.append('</div></section>')
    out.append('''<section id="playbook"><div class="section-head"><div><p class="eyebrow">04 / IMPLEMENTATION PLAYBOOK</p><div class="display">MAKE IT WORK.</div><h2>日本で始めるなら、何を設計するか。</h2></div><p>以下は本レポートの提案です。実施済みの成果ではありません。予算・権限・当事者の合意を確認してから実行します。</p></div><div class="guide-lead"><div><div class="display">CONNECT THE WHOLE JOURNEY.</div><h3>施設計画より先に、<br>一つの案件が続く道筋を描く。</h3></div><p>まず、受益者、課題オーナー、実証の運営者、買い手または継続財源の決裁者を揃える。共創拠点は、その間にある知識・技術・調整の不足を埋める。足りない機能を外部とつなぐか、自前で持つかを、実案件の必要量から判断します。</p></div><div class="table-wrap"><table><caption>3つの異なる始め方＋現状維持｜どれが優れるかは、課題の状態で変わる。</caption><thead><tr><th>選択肢</th><th>向いている状況</th><th>価値を生む仕組み／負担者</th><th>弱点・方針を変える条件</th></tr></thead><tbody><tr><td><strong>A / 課題形成・人材型</strong></td><td>課題が曖昧、仲間が未形成</td><td>当事者調査、対話、混成教育。行政・企業・教育機関が探索費を負担。</td><td>交流だけで終わりやすい。90日で課題オーナーが決まらなければ募集方法を変える。</td></tr><tr><td><strong>B / 現場実証・公共価値型</strong></td><td>地域課題は明確だが現場での成立条件が未知</td><td>既存のまち・施設をつないで検証。課題を持つ行政・企業が評価費を負担。</td><td>住民・現場の負担を見落としやすい。改善が費用・負担を上回らなければ範囲を縮小。</td></tr><tr><td><strong>C / 購入・事業化型</strong></td><td>買い手の課題と導入部門が明確</td><td>有償試験購入から導入契約へ。利用部門・顧客が費用を負担。</td><td>短期課題に偏りやすい。継続購入の責任者や財源が決まらなければ拡大しない。</td></tr><tr><td><strong>現状維持</strong></td><td>課題や改善便益の根拠が薄い</td><td>既存業務・既存支援策を続ける。追加投資は発生しない。</td><td>取り逃す学習・機会もある。観測費を限定して課題の発生頻度・損失を記録する。</td></tr></tbody></table></div><div class="guide-steps"><article class="guide-step"><div class="display">30 DAYS</div><h3>課題と責任を決める</h3><p>現場観察、当事者対話、現状値を取得。誰が困り、何が変わればよいかを1枚にする。予算上限と中止権限を先に置く。</p><p class="owner"><strong>提案する担当</strong><br>課題オーナー＋プロデューサー</p></article><article class="guide-step"><div class="display">90 DAYS</div><h3>小さく試し、比較する</h3><p>1〜3件を対象に、仮説・比較対象・評価期間を定める。参加者の同意、データ管理、知財、費用分担を合意して試作する。</p><p class="owner"><strong>提案する担当</strong><br>混成チーム＋現場運営者＋評価担当</p></article><article class="guide-step"><div class="display">180 DAYS</div><h3>継続の条件を揃える</h3><p>利用者の変化、実運用費、現場負担を検証。有償導入または恒常財源、運用責任者、保守を確定する。</p><p class="owner"><strong>提案する担当</strong><br>導入部門＋予算決裁者＋運用責任者</p></article><article class="guide-step"><div class="display">365 DAYS</div><h3>別の現場で再現する</h3><p>二拠点目で同じ指標を測る。再設計量、追加費用、便益の偏りを確認し、手順・契約・失敗知を更新する。</p><p class="owner"><strong>提案する担当</strong><br>移管先＋保守担当＋ポートフォリオ責任者</p></article></div><div class="table-wrap"><table><caption>測るべきもの｜分母・期間・測定者を案件開始時に固定する。</caption><thead><tr><th>階層</th><th>指標の例</th><th>測り方／注意</th><th>測定責任の提案</th></tr></thead><tbody><tr><td><strong>活動 / Output</strong></td><td>採択件数、参加者、試作、検証日数</td><td>重複参加と実人数を分ける。多いこと自体を成功にしない。</td><td>運営事務局</td></tr><tr><td><strong>変化 / Outcome</strong></td><td>継続導入率、課題改善、後続契約</td><td>同じ採択期の案件で、12か月後の稼働案件数 ÷ 追跡対象件数。未追跡を別表示。</td><td>導入部門＋評価担当</td></tr><tr><td><strong>社会への影響 / Impact</strong></td><td>生活・業務の改善、地域への便益と負担</td><td>比較対象、費用、事故・格差・参加負担を含める。推計と実測を分ける。</td><td>外部評価者＋当事者代表</td></tr><tr><td><strong>再現・学習</strong></td><td>二拠点目の導入費、再作業、失敗の再発</td><td>条件差と変更点を記録。同じ仕様を押し付けることを横展開と呼ばない。</td><td>運用責任者＋知識管理担当</td></tr></tbody></table></div><div class="gates"><article class="gate"><div class="display">CONTINUE / SCALE</div><p>事前の目標を満たし、継続財源と運用責任者が決まったら継続。二拠点目でも便益と負担が許容範囲に収まったら拡大する。</p></article><article class="gate"><div class="display">PIVOT</div><p>ニーズは確認できたが使い方・費用・体制が合わない場合は変更する。期間と追加費用の上限を決め、次の仮説を検証する。</p></article><article class="gate"><div class="display">STOP</div><p>当事者の重要な不利益、安全条件の未達、予算上限超過、継続主体の不在が解消できない場合は停止する。結果と理由を残す。</p></article></div><div class="update-note"><strong>実行・学習の状態：</strong>このガイドは設計提案です。MDLによる本ガイドの比較実験・因果評価は未実施。実行後の観測に基づき、仮説と判断を更新します。</div></section>''')
    out.append(f'''<section id="sources"><div class="section-head pink"><div><p class="eyebrow">05 / EVIDENCE & EDITORIAL POLICY</p><div class="display">BACK TO THE SOURCE.</div><h2>原典から読み、確かめる。</h2></div><p>{source_count}件の重複を除く事例出典を掲載。<br>各詳細ページから、主張を支える原典へ移動できます。</p></div><div class="method"><div><h3>事実、自己報告、分析を分ける。</h3><dl class="legend"><dt>確認した事実</dt><dd>公式の制度、募集条件、組織、公開した活動。</dd><dt>運営者の報告</dt><dd>運営主体が公表した実績。独立した効果測定とは限りません。</dd><dt>MDLの分析</dt><dd>複数事例から整理した意味・応用条件。公式見解ではありません。</dd><dt>提案・未実施</dt><dd>検証方法、実行手順、継続・変更・停止条件の提案。</dd></dl><p>情報が見つからなかった項目は「未確認」としています。「存在しない」とは断定しません。費用対効果・導入率の分母が違う場合は、順位や統合スコアを算出していません。</p></div><div><h3>調査範囲と更新方針</h3><p>これまでの共創・リビングラボ・アート共創調査を起点に、公開版は{len(DATA)}事例を、運営者・行政の一次資料と原著を中心に整理しています。目的・工程の分類は、公開情報に基づく編集上の整理です。既存の調査資料を手掛かりに、公開主張の根拠は各事例の原典で示しています。</p><p>北米・欧州・アジア・中南米等の{countries}か国を対象とする選定事例集です。世界全域の網羅調査や代表サンプルではありません。未掲載の地域・条件への一般化には追加調査が必要です。</p><p>掲載日は{DATE}。数値は各項目の対象年・公表時点を併記。募集終了、運営者変更、集計定義の変更は、元の記述をそのまま継承せず見直しています。</p></div></div><details><summary class="compare-toggle">基礎を押さえる：用語集 ＋</summary><div class="table-wrap"><table><thead><tr><th>用語</th><th>このレポートでの読み方</th><th>混同しないこと</th></tr></thead><tbody><tr><td>オープンイノベーション</td><td>組織の内外の知識・技術・資源を組み合わせて価値をつくる考え方。</td><td>交流イベントを開催しただけでは、価値の実現は確認できない。</td></tr><tr><td>リビングラボ</td><td>生活者が共同設計に関わり、実生活の環境で研究・開発・評価を反復する仕組み。</td><td>利用者を試験参加者として招くテストベッドと、意思決定に参加する共創は異なる。</td></tr><tr><td>PoC / PoV</td><td>概念や技術が成立するかを試す段階／利用者や買い手にとっての価値を確かめる段階。</td><td>成立した試験と、続く運用・事業を区別する。</td></tr><tr><td>Venture Client</td><td>企業がスタートアップの顧客となり、購入を通じて技術を検証・採用する方式。</td><td>株式投資をするCVCや、無償の協業相談とは異なる。</td></tr><tr><td>社会実装</td><td>本レポートでは、実際の現場で、責任者・財源・運用体制を持って価値提供が続く状態。</td><td>実証の実施数や公開デモの数で代用しない。</td></tr></tbody></table></div></details>''')
    out.append('<details><summary class="compare-toggle">原典の一覧：28事例・基礎資料 ＋</summary><div class="source-list"><div class="source-item"><span class="label">FOUNDATION 01</span><p>'+external('https://enoll.org/living-labs/','ENoLL｜What are Living Labs')+'</p><p>利用者中心、実生活環境、共創の定義。確認日 2026-09-27。</p></div><div class="source-item"><span class="label">FOUNDATION 02</span><p>'+external('https://timreview.ca/article/1088','Steen & van Bueren (2017)｜The Defining Characteristics of Urban Living Labs')+'</p><p>90案件の定義適合性を検討した原著。全世界の成功率ではない。</p></div>')
    for c in DATA:
        out.append(f'<div class="source-item"><span class="label">CASE {c["number"]}</span><p><a href="{path(c)}#evidence-sources">{e(c["name"])}｜出典と確認した内容</a></p><p>{len(c["sources"])}件の参照資料を掲載。</p>'+''.join(f'<p>{source_link(s)}</p><div class="meta">{e(s.get("publisher",""))} · {e(s.get("published","日付記載なし"))}</div>' for s in c['sources'])+'</div>')
    out.append('</div></details><details><summary class="compare-toggle">写真・動画のクレジットと利用条件 ＋</summary><div class="source-list">')
    out.append(f'<div class="source-item"><h3>写真の対象と確認範囲</h3><p>{len(DATA)}事例に関連する{len(MEDIA)}点を掲載しています。施設・活動そのものの写真に加え、入居建物、旧拠点、対象地区の写真を含みます。何を写した写真か、撮影時点と合わせて確認してください。</p><a href="learn/updates/">今回の修正と確認範囲を見る →</a></div>')
    out.append('<div class="source-item"><h3>動画・360°体験</h3><p>各事例の公式公開コンテンツへリンクしています。埋め込みは再生を選んだ後に読み込み、配信者の設定に従います。動画本体の再配布は行っていません。</p></div>')
    for m in MEDIA:out.append(f'<div class="source-item"><p>{external(m["sourceUrl"],e(m.get("name",m.get("alt","写真"))))}</p><p>{e(m["credit"])}</p><p>{e(m["license"])}</p><div class="meta">{e(m.get("changes","表示枠に合わせたトリミング・縮小"))}</div></div>')
    out.append('<div class="source-item"><p>'+external('https://www.naturalearthdata.com/about/terms-of-use/','Natural Earth｜地図データ')+'</p><p>Public domain。110m landデータを緯度・経度から描画。地図の位置は施設または運営本部の代表地点であり、ネットワーク全域を示すものではありません。</p></div></div></details></section></main>'+footer()+f'<script>window.ATLAS_DATA={json.dumps(DATA,ensure_ascii=False).replace("</","<\\/")};</script></body></html>')
    (ROOT/'index.html').write_text(''.join(out).replace('28事例',str(len(DATA))+'事例').replace('世界の共創から、地域と事業のつくり方を学ぶ。','世界の実践から、共創とまちづくりを学ぶ。').replace('13か国',str(countries)+'か国').replace('28対象',str(len(DATA))+'対象'))

def build_case(c):
    prefix='../../';ms=media_for(c);m=ms[0] if ms else None
    name=c['name'];title=c.get('nameJa') or name
    case_date=CHAINS[c["id"]]["updated"].replace("-", ".")
    out=[head(f'{name}｜{c["tagline"]}',c['lead'],BASE+path(c),prefix),header(prefix),f'<main id="main"><div class="detail-crumb"><a href="../../">WORLD CO-CREATION ATLAS</a> / <a href="../../?stage={c["stage"]}#explore">{c["stage"]:02d} {STAGES[c["stage"]]}</a> / CASE {c["number"]}</div><section class="detail-hero"><div class="detail-title"><p class="eyebrow">CASE {c["number"]} / {e(c["country"])} / {e(c["city"])}</p><div class="display">{e(name)}</div><h1>{e(title)}</h1><p class="tagline">{e(c["tagline"])}</p><p>{e(c["lead"])}</p><div style="margin-top:24px">{external(c["sources"][0]["url"],"主要な原典を見る" if c.get("expertContext") else "公式サイトを見る","btn yellow")}</div><p class="meta" style="margin-top:22px">{TYPES[c["type"]]} · 調査確認日 {case_date}</p></div>']
    if c.get('expertContext'):
        out[0] = expert_context.styles(out[0],prefix)
    if m:out.append(photo(m,cls='detail-photo',prefix=prefix,loading='eager'))
    else:out.append(f'<div class="atlas-photo-missing"><p class="eyebrow">{e(c["entry"]["unit"])}</p><h2>{e(c["tagline"])}</h2><p>写真の転載条件は確認中です。現場の写真は公式サイトでご覧ください。</p>{external(c["sources"][0]["url"],"公式サイトで見る")}</div>')
    real_photos=[x for x in ms if x.get('kind')!='diagram']
    gallery=''
    if len(real_photos)>1:
        gallery='<section class="field-photos" id="field-photos"><div class="field-photo-heading"><p class="eyebrow">FIELD PHOTOS / '+str(len(real_photos))+' PHOTOS</p><h2>写真で、場所と活動を読む。</h2></div><div class="field-photo-grid">'+''.join(photo(x,prefix=prefix) for x in real_photos[1:])+'</div></section>'
    elif real_photos:
        out[2]=out[2].replace('<section class="detail-hero">','<section class="detail-hero" id="field-photos">')
    out.append(f'</section>{gallery}<dl class="detail-meta"><div><dt>LOCATION / 所在地</dt><dd>{e(c["country"])}・{e(c["city"])}<br><small>{e(c.get("locationNote","代表所在地"))}</small></dd></div><div><dt>ESTABLISHED / 設立・開始</dt><dd>{e(c["established"])}</dd></div><div><dt>OPERATOR / 運営</dt><dd>{e(c["operator"])}</dd></div><div><dt>ROLE / 主な工程</dt><dd>{" / ".join(STAGES[s] for s in c["stages"])}</dd></div></dl><section class="case-glance" id="at-a-glance"><div class="glance-heading"><p class="eyebrow">AT A GLANCE</p><h2>この事例の要点。</h2><p>概要をつかんでから、知りたい項目へ。</p></div><div><h3>何をする場・制度？</h3><p>{e(c["lead"].split("。")[0])}。</p><a href="#mechanism">運営の仕組みを読む ↓</a></div><div><h3>何を学べる？</h3><p>{e(c["tagline"])}</p><a href="#transfer">日本で活かす条件を読む ↓</a></div><div><h3>どこまでわかっている？</h3><p>公表された成果と、まだ確認できない点を分けて整理しています。</p><a href="#evidence">成果と根拠を確かめる ↓</a></div></section><div class="detail-layout"><aside class="detail-toc"><nav aria-label="この事例の目次"><div class="display">IN THIS CASE.</div><p class="toc-guide">知りたい項目から読む</p><a href="#mechanism">01 どんな仕組みで動く？</a><a href="#funding">02 誰が費用と責任を担う？</a><a href="#evidence">03 どこまで成果が出た？</a><a href="#transfer">04 日本で活かす条件は？</a><a href="#limits">05 真似する際の注意点は？</a><a href="#next-test">06 次に何を検証する？</a><a href="#media">07 写真・動画で見る</a><a href="#evidence-sources">08 元サイト・出典へ</a></nav></aside><article>')
    if c['id'] in CHAINS:
        out[-1] = out[-1].replace('<section class="case-glance"', evidence.notice(c)+expert_context.case_context(c)+'<section class="case-glance"')
        row = CHAINS[c['id']]
        out[-1] = out[-1].replace('<div class="detail-layout">', atlas_routes.reading_context(c)+value_chain.glance(row)+'<div class="detail-layout">')
        out[-1] = out[-1].replace('<p class="toc-guide">知りたい項目から読む</p>', value_chain.toc()+'<details class="vc-extra-toc"><summary>運営・根拠・応用も読む ＋</summary>')
        out[-1] = out[-1].replace('08 元サイト・出典へ</a></nav>', '08 元サイト・出典へ</a></details></nav>')
        sections=value_chain.case_sections(row)
        if c.get('expertContext'):
            sections=sections.replace('各施設の公式な工程名','各取り組みの公式な工程名').replace('施設の活動に帰属できる効果','当該活動に帰属できる効果')
        if 'place' in c['entry']['lenses']:
            sections=sections.replace('07 事業にする</a>','07 事業にする（公共サービス・地域活動として続ける）</a>')
        out.append(sections)
    out.append(f'<section class="detail-section" id="mechanism"><h2><span class="display">01</span>どう動かしているのか。</h2>{para(c["operatingModel"])}<ol class="process">'+''.join(f'<li>{e(p)}</li>' for p in c['process'])+'</ol></section>')
    out.append(f'<section class="detail-section" id="funding"><h2><span class="display">02</span>誰が負担し、誰が担うか。</h2>{para(c["payer"])}<p class="note-inline">制度やプログラムの財源と、各参加企業・地域に発生する費用は同じではありません。公開範囲を超える案件別予算・契約条件は未確認です。</p></section>')
    out.append('<section class="detail-section" id="evidence"><h2><span class="display">03</span>確認できたこと。</h2>')
    source_by_id={t["id"]:t for t in c["sources"]}
    metric=c.get('metric')
    if metric:out.append(f'<div class="metric-block"><div class="display">{e(metric["value"])}</div><div><p><strong>{e(metric["label"])}</strong></p><p>{e(metric["asOf"])}</p>{source_link(source_by_id[metric["sourceId"]],"この数字の原典を読む","ref")}</div></div>')
    for z in c['evidence']:
        kind=('研究者・関係者の報告' if c.get('expertContext') else '運営者の報告') if z['kind']=='self-report' else '確認した事実'
        out.append(f'<div class="evidence-item"><span class="fact {e(z["kind"])}">{kind}</span><span class="meta"> {e(z.get("asOf",""))}</span><h3>{e(z["claim"])}</h3><p><strong>読み取れる範囲：</strong>{e(z.get("limit",""))}</p>{source_link(source_by_id[z["sourceId"]],"原典で確かめる","ref")} <a class="source-note-link" href="#{e(z["sourceId"])}">出典の説明 ↓</a></div>')
    out.append(f'</section><section class="detail-section analysis" id="transfer"><span class="label">MDL ANALYSIS</span><h2 style="margin-top:16px"><span class="display">04</span>日本で活かすなら。</h2>{para(c["transfer"])}</section><section class="detail-section limit" id="limits"><h2><span class="display">05</span>そのまま真似できないこと。</h2>{para(c["limits"])}</section><section class="detail-section test" id="next-test"><span class="label">PROPOSAL / 未実施の検証案</span><h2 style="margin-top:16px"><span class="display">06</span>次に、何を確かめるか。</h2>{para(c["nextTest"])}</section>')
    media_title = "写真・図と原資料で確かめる。" if c.get("expertContext") else "写真・動画と原資料へ。"
    out.append(f'<section class="detail-section" id="media"><h2><span class="display">07</span>{media_title}</h2>')
    if real_photos:out.append('<a class="btn yellow" href="#field-photos">現場の写真を見る ↑</a>')
    for x in ms:
        if x.get('kind')=='diagram':out.append(photo(x,prefix=prefix))
    if m:out.append(f'<p class="note-inline">{("冒頭模式図" if m.get("kind")=="diagram" else "冒頭写真")}：{e(m.get("alt",m.get("name",c["name"])))}</p>')
    vs=c.get('videos',[])
    if vs:
        out.append('<div class="video-grid" style="margin-top:24px">')
        for v in vs:
            embed=v.get('embedUrl');embed=embed if embed and any(embed.startswith(u) for u in ['https://www.youtube-nocookie.com/embed/','https://www.youtube.com/embed/','https://player.vimeo.com/video/']) else None;button=f'<button type="button" data-video="{e(embed)}" data-title="{e(v["title"])}">動画を再生 ▷</button>' if embed else ''
            out.append(f'<article class="video-card"><div class="play">PLAY / WATCH</div><h3>{e(v["title"])}</h3><p>{e(v.get("publisher","公式コンテンツ"))}</p>{button}{external(v["url"],"公式サイトで見る")}</article>')
        out.append('</div>')
    if not ms or not vs:out.append(f'<a class="media-link" href="{e(c["sources"][0]["url"])}" target="_blank" rel="noopener noreferrer">{("原資料で、当時の調査・実践を読む" if c.get("expertContext") else "公式サイトで、写真・最新の活動を見る")} ↗</a>')
    if not ms:out.append('<p class="note-inline">掲載許諾を確認できない写真は転載せず、公式ページでご覧いただけるようにしています。</p>')
    out.append('</section><section class="detail-section" id="evidence-sources"><h2><span class="display">08</span>原典を読む。</h2><p class="meta">制度の説明と運営者による実績報告を区別しています。日付記載のない資料は、公表時点を確定できません。確認日は資料を確認した日であり、活動や成果が発生した日ではありません。</p>')
    for s in c['sources']:
        access_note = f'<p class="expert-source-access">{e(s["accessNote"])}</p>' if s.get('accessNote') else ''
        out.append(f'<div class="source-item" id="{e(s["id"])}"><span class="label">{e(s["id"])}</span><p>{source_link(s)}</p><p>{e(s.get("claim",""))}</p>{access_note}<div class="meta">{e(s.get("publisher",""))} · 公表：{e(s.get("published","日付記載なし"))}<br>確認箇所：{e(s.get("locator","本文"))} · 確認日：{e(s.get("verified","2026-09-27"))}</div></div>')
    out.append('</section></article></div>')
    out.append(learning.case_bridge(c))

    # Retain the published edition on untouched research articles; adding cases
    # does not reissue or re-verify their existing content.
    article_footer=footer()
    if CHAINS[c['id']]['updated'] < '2026-10-02':
        article_footer=article_footer.replace('学習版 3.3 · 更新日 '+DATE,'学習版 3.1 · 調査確認日 2026.09.28')
    elif CHAINS[c['id']]['updated'] < '2026-10-06':
        article_footer=article_footer.replace('学習版 3.3 · 更新日 '+DATE,'学習版 3.2 · 更新日 2026.10.02')
    out.append(atlas_routes.related(c,DATA,CHAINS)+'</main>'+article_footer+video_dialog()+'</body></html>')
    rendered=''.join(out)
    if c.get('expertContext'):
        rendered=rendered.replace('具体的な実装事例','具体的な調査・実践').replace('この拠点・仕組みから、実装された／検証中の事例を読む','この研究・実践の対象と、確認できた段階を読む').replace('07 写真・動画で見る','07 写真・図と原資料で見る')
    dest=ROOT/'cases'/c['id'];dest.mkdir(parents=True,exist_ok=True);(dest/'index.html').write_text(rendered)

learning.configure(DATA,STAGES,MEDIA,head,header,footer,photo)
build_index()
for c in DATA:build_case(c)
learning.build_all()
atlas_routes.build_compare(DATA,head,header,footer)
catalog.build(ROOT,head,header,footer,BASE)
expert_context.build(DATA,head,header,footer)
(ROOT/'data/cases.json').write_text(json.dumps(DATA,ensure_ascii=False,indent=2))
print(f'Built {len(DATA)} cases and index. {len([m for m in MEDIA if m.get('kind') != 'diagram'])} photographs; {len([m for m in MEDIA if m.get('kind') == 'diagram'])} diagrams. '+str(len(set(s['url'] for c in DATA for s in c['sources'] if s.get('url'))))+' unique case sources.')
