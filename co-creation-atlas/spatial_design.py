"""Four design philosophies: isolated report data and reproducible static pages.

No external requests. Pending photographs are always links, never image sources.
"""
from pathlib import Path
from html import escape
from urllib.parse import urlparse
import json
import re

ROOT = Path(__file__).resolve().parent
BASE = '/co-creation-atlas/'
FEATURE = BASE + 'spatial-design/'
VERSION = '20261027.3'


def e(value):
    return escape(str(value), quote=True)


def read(root=ROOT):
    data = {name: json.loads((root/'data'/f'spatial-design-{name}.json').read_text())
            for name in ['companies', 'projects', 'sources', 'media', 'editorial']}
    for name in ['companies', 'projects', 'sources', 'media']:
        ids = [x['id'] for x in data[name]]
        assert len(ids) == len(set(ids)), f'Duplicate {name} ID'
    assert len(data['companies']) == 4 and len(data['projects']) == 23
    company_ids = {c['id'] for c in data['companies']}
    source_ids = {s['id'] for s in data['sources']}
    project_ids = {p['id'] for p in data['projects']}
    existing_ids = {c['id'] for c in json.loads((root/'data/cases.json').read_text())}
    for item in data['sources']:
        assert urlparse(item['url']).scheme == 'https', item['id']
    for project in data['projects']:
        assert project['companyId'] in company_ids
        assert set(project['companyIds']) <= company_ids
        assert set(project['sourceIds']) <= source_ids
        assert not project['existingCaseId'] or project['existingCaseId'] in existing_ids
        assert project['steps'] and len(project['steps']) < 8
        assert all(1 <= s['number'] <= 8 and s['why'] for s in project['steps'])
    for media in data['media']:
        assert media['projectId'] in project_ids and media['sourceId'] in source_ids
        if media['publicationMode'] == 'image':
            assert media['rightsStatus'] in {'cleared-cc', 'cleared-public-domain', 'cleared-permission'}
            assert all(media.get(k) for k in ['local', 'credit', 'license', 'licenseUrl', 'alt', 'caption', 'dimensions', 'permission'])
            assert (root/media['local']).is_file()
            assert media.get('kind', 'photograph') in {'photograph', 'video-still'}
            assert media.get('noCrop', True)
            if media.get('kind') == 'video-still':
                assert media.get('videoTimeDisplay') and media.get('originalImageUrl')
            if 'by-nc' in media['licenseUrl'] or media['rightsStatus'] == 'cleared-permission':
                assert media['permission'].get('useContext') == 'free-editorial-learning'
                assert media['permission'].get('commercialPromotion') is False
            for credit_link in media.get('creditLinks', []):
                assert urlparse(credit_link['url']).scheme == 'https'
        else:
            assert media['publicationMode'] == 'link-only'
    return data


def project_url(p):
    return FEATURE + p['companyId'] + '/#' + p['id']


def link(url, title, cls=''):
    return f'<a class="{e(cls)}" href="{e(url)}" target="_blank" rel="noopener noreferrer">{e(title)} <span aria-hidden="true">↗</span></a>'


def source_map(data):
    return {s['id']: s for s in data['sources']}


def inline(block, sources):
    parts = []
    for span in block['spans']:
        if span.get('sourceId'):
            s = sources[span['sourceId']]
            parts.append(link(s['url'], span['text'], 'sd-inline-source'))
        else:
            parts.append(e(span['text']))
    return ''.join(parts)


def render_blocks(blocks, sources, heading_level=3):
    out = []
    list_open = False
    for block in blocks:
        is_bullet = block['type'] == 'p' and block['style'] in {'ListBullet', 'ListText'}
        if list_open and not is_bullet:
            out.append('</ul>'); list_open = False
        if block['type'] == 'table':
            out.append('<div class="sd-table-wrap" role="region" aria-label="詳細比較表" tabindex="0"><table class="sd-table"><tbody>')
            headers = [' '.join(p['text'] for p in cell) for cell in block['rows'][0]]
            for i, row in enumerate(block['rows']):
                out.append('<tr>')
                for j, cell in enumerate(row):
                    tag = 'th' if i == 0 or j == 0 else 'td'
                    scope = ' scope="col"' if i == 0 else ' scope="row"' if j == 0 else ''
                    out.append(f'<{tag}{scope} data-label="{e(headers[j])}">'+ '<br>'.join(inline(p,sources) for p in cell) + f'</{tag}>')
                out.append('</tr>')
            out.append('</tbody></table></div>')
        elif block['text'].strip():
            content = inline(block, sources)
            if is_bullet:
                if not list_open:out.append('<ul>'); list_open = True
                out.append('<li>' + content + '</li>')
            elif block['style'].startswith('Heading'):
                level = min(5, heading_level + (1 if block['style']=='Heading3' else 0))
                out.append(f'<h{level}>{content}</h{level}>')
            elif len(block['text']) < 42 and (block['text'].startswith(('基本情報','確認事実','解釈','空間と運営','成果','適用条件'))):
                out.append(f'<h4>{content}</h4>')
            else:
                out.append('<p>' + content + '</p>')
    if list_open:out.append('</ul>')
    return ''.join(out)


def assets():
    return f'<link rel="stylesheet" href="{BASE}spatial-design.css?v={VERSION}"><script defer src="{BASE}spatial-design.js?v={VERSION}"></script>'


def breadcrumb(company=None):
    tail = f'<a href="{FEATURE}">4つの設計思想</a><span aria-hidden="true">／</span><span>{e(company["shortName"])}</span>' if company else '<span>4つの設計思想</span>'
    return f'<nav class="sd-breadcrumb" aria-label="現在位置"><a href="{BASE}">ATLAS</a><span aria-hidden="true">／</span>{tail}</nav>'


def company_nav(data, active=None):
    links = ''.join(f'<a href="{FEATURE}{c["id"]}/"'+(' aria-current="page"' if active == c['id'] else '')+f'><span>{e(c["number"])}</span> {e(c["shortName"])}</a>' for c in data['companies'])
    return f'<nav class="sd-company-nav" aria-label="設計会社から読む"><a href="{FEATURE}">特集トップ</a>{links}</nav>'


def project_photos(project, data):
    photos = [m for m in data['media'] if m['projectId'] == project['id'] and m['publicationMode']=='image']
    return sorted(photos, key=lambda m: not m.get('featured', False))


def photo_count(project, data):
    return len(project_photos(project, data))


def media_count_label(photos):
    stills = sum(p.get('kind') == 'video-still' for p in photos)
    return f'{len(photos)}点（写真{len(photos)-stills}枚・映像静止画{stills}点）' if stills else f'写真{len(photos)}枚'


def media_kind_label(photo):
    if photo.get('kind') == 'video-still':
        return '公式映像の静止画 ' + photo['videoTimeDisplay']
    return {'interior': '内観', 'exterior': '外観', 'exterior-context': '外観・周辺',
            'activity': '活動の記録', 'opening-event-context': '開業時の記録'}.get(photo.get('imageScope'), '写真')


def usage_label(photo):
    if 'by-nc' in photo['licenseUrl']:
        return '非営利の学習・分析記事で使用。広告・営業資料への写真転用はしません。'
    if photo['rightsStatus'] == 'cleared-permission':
        return '提供元が認める報道・編集用途で掲載。一般的な再利用許諾ではありません。'
    return ''


def image_gallery(project, data, compact=False):
    sources = source_map(data)
    photos = project_photos(project, data)
    if not photos:
        return ''
    payload = {'projectId': project['id'], 'photos': []}
    for photo in photos:
        payload['photos'].append({
            'id': photo['id'], 'src': BASE + photo['local'], 'title': project['name'],
            'alt': photo['alt'], 'caption': photo['caption'], 'credit': photo['credit'],
            'source': sources[photo['sourceId']]['url'], 'license': photo['license'],
            'licenseUrl': photo['licenseUrl'], 'photoTitle': photo.get('photoTitle', ''),
            'creditLinks': photo.get('creditLinks', []),
            'meta': photo['imageDate'] + ' · ' + photo.get('changes', '改変なし'),
            'kindLabel': media_kind_label(photo), 'usage': usage_label(photo)})
    serialized = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    serialized = serialized.replace('<', chr(92)+'u003c').replace('&', chr(92)+'u0026')
    stills = sum(photo.get('kind') == 'video-still' for photo in photos)
    out = [f'<div class="sd-photo-gallery" data-sd-gallery="{e(project["id"])}">']
    if not compact:
        heading = f'写真・映像静止画 <b>{len(photos)}</b>点' if stills else f'空間写真 <b>{len(photos)}</b>枚'
        note = e(project.get('galleryNote', '写真を選ぶと拡大できます。前後の写真も続けて読めます。'))
        out.append(f'<header class="sd-gallery-heading"><h4>{heading}</h4><p>{note}</p></header>')
    out.append('<script type="application/json" data-sd-photo-set>'+serialized+'</script>')
    for photo in (photos[:1] if compact else photos):
        src = BASE + photo['local']
        source = sources[photo['sourceId']]
        width, height = photo['dimensions']
        unit = '点' if stills else '枚'
        enlarge = f'{len(photos)}{unit}を見る' if compact else '拡大'
        credit_links = ' · '.join(link(c['url'], c['label']) for c in photo.get('creditLinks', []))
        original_title = f'<span>原題：{e(photo["photoTitle"])}</span>' if photo.get('photoTitle') else ''
        usage = f'<span class="sd-usage">{e(usage_label(photo))}</span>' if usage_label(photo) else ''
        out.append(
            f'<figure class="sd-photo" data-rights="{e(photo["rightsStatus"])}">'
            f'<a href="{e(src)}" data-sd-photo data-sd-project="{e(project["id"])}" data-sd-photo-id="{e(photo["id"])}">'
            f'<img src="{e(src)}" alt="{e(photo["alt"])}" width="{width}" height="{height}" loading="lazy">'
            f'<span class="sd-enlarge">{enlarge} <span aria-hidden="true">↗</span></span></a>'
            f'<figcaption><span class="sd-media-kind">{e(media_kind_label(photo))}</span>'
            f'<strong>{e(photo["caption"])}</strong><span>{e(photo["credit"])} · '
            + link(source['url'], '掲載元') + ' · ' + link(photo['licenseUrl'], photo['license']) + '</span>'
            + original_title + (f'<span>{credit_links}</span>' if credit_links else '')
            + f'<span>{e(photo["imageDate"])} · {e(photo.get("changes", "改変なし"))}</span>'
            + usage + '</figcaption></figure>')
    return ''.join(out) + '</div>'


def photo_reading(project, data):
    sources = source_map(data)
    media = [m for m in data['media'] if m['projectId']==project['id'] and m['publicationMode']=='link-only']
    out = ['<details class="sd-photo-readings"><summary>公式写真の、3つの見るポイント <span aria-hidden="true">＋</span></summary><p>写真は掲載元でご覧ください。見える形と、行動の仮説・実測結果を分けて読みます。</p><div class="sd-view-grid">']
    for m in media:
        s = sources[m['sourceId']]
        out.append(f'<article><span class="sd-view-number">{e(m["label"])}</span><p>{e(m["reading"])}</p>{link(s["url"],"公式の空間写真を見る")}</article>')
    out.append('</div><details class="sd-rights-note"><summary>撮影・掲載時点と権利の確認状況</summary>')
    for note in dict.fromkeys(m['rightsNote'] for m in media):out.append('<p>'+e(note)+'</p>')
    out.append('<p>提供レポートの69候補は当初、転載許諾未取得でした。追加掲載した写真は、撮影者や配布元の利用条件を別途確認しています。未確認画像は複製・埋め込みをせず、参照先を案内しています。</p></details></details>')
    return ''.join(out)


def project_sources(project, data):
    sources = source_map(data)
    return '<details class="sd-project-sources"><summary>この空間の原典を読む <span>'+str(len(project['sourceIds']))+'資料 ＋</span></summary><ul>'+''.join('<li>'+link(sources[sid]['url'], sources[sid]['title'])+'</li>' for sid in project['sourceIds'])+'</ul></details>'


def project_article(p, data, stages):
    fields=[('場所・年',p['location']+'｜'+p['year']),('クライアント',p['client']),('設計の範囲・協働',p['designScope']),('運営',p['operator'])]
    meta='<dl class="sd-project-meta">'+''.join(f'<div><dt>{e(k)}</dt><dd>{e(v)}</dd></div>' for k,v in fields)+'</dl>'
    glance=''.join(f'<section class="sd-case-point"><p class="sd-kicker">{en} / {ja}</p><h4>{title}</h4><p>{e(p[key])}</p></section>' for key,en,ja,title in [
        ('space','SPACE','確認できる仕掛け','何を、どこに置いたか。'),
        ('behaviorHypothesis','HYPOTHESIS','編集上の解釈','どんな行動へつながるか。'),
        ('operation','OPERATION','運営と成立条件','誰が、日々動かすか。'),
        ('evidence','EVIDENCE','成果の根拠と留保','何が、確かめられたか。')])
    steps=''.join(f'<li><a href="{BASE}learn/step-{s["number"]:02d}/"><b>{s["number"]:02d}</b> {e(stages[s["number"]])} →</a><p>{e(s["why"])}</p></li>' for s in p['steps'])
    existing=f'<a href="{BASE}cases/{p["existingCaseId"]}/">既存Atlasの記事を読む →</a>' if p['existingCaseId'] else ''
    return (f'<article class="sd-project" id="{p["id"]}" data-project-id="{p["id"]}"><header class="sd-project-heading"><p class="sd-kicker">CASE STUDY <span>{e(p["status"])}</span></p><h3>{e(p["name"])}</h3><p class="sd-project-tagline">{e(p["tagline"])}</p></header>'+meta+image_gallery(p,data)+'<div class="sd-case-points">'+glance+'</div>'+f'<div class="sd-case-limit"><strong>真似する前の条件・限界</strong><p>{e(p["limits"])}</p></div>'+photo_reading(p,data)+f'<details class="sd-deep-reading"><summary>仕掛け・運営・成果を、詳しく読む <span aria-hidden="true">＋</span></summary><div class="sd-prose">{render_blocks(p["body"],source_map(data),4)}</div></details><section class="sd-case-steps"><h4>Atlasの工程で読む</h4><p class="sd-note">実空間単位の編集上の解釈です。各社がAtlasの工程を採用したという意味ではありません。</p><ul>{steps}</ul>{existing}</section>'+project_sources(p,data)+'</article>')


def source_library(ids, data):
    sources = source_map(data)
    return '<details class="sd-source-library"><summary>出典一覧を開く <span>'+str(len(ids))+'資料 ＋</span></summary><ol>'+''.join(f'<li id="{e(sid)}">'+link(sources[sid]['url'],sources[sid]['title'])+f'<span>{e(sources[sid]["publisher"])} · 参照情報整理日 2026.10.27</span></li>' for sid in dict.fromkeys(ids))+'</ol></details>'


def dialog():
    return '<dialog class="sd-lightbox" aria-labelledby="sd-photo-title"><div class="sd-lightbox-bar"><h2 id="sd-photo-title">空間の写真</h2><button type="button" data-sd-close autofocus>閉じる ×</button><nav class="sd-lightbox-controls" aria-label="この空間の写真を切り替える"><button type="button" data-sd-prev aria-label="前の写真">← 前</button><p data-sd-count role="status" aria-live="polite" aria-atomic="true"></p><button type="button" data-sd-next aria-label="次の写真">次 →</button></nav></div><img alt=""><div class="sd-lightbox-caption"><p data-kind-label></p><p data-caption></p><p data-credit></p><p data-credit-links></p><p data-original-title></p><p data-photo-meta></p><p data-usage></p><a data-source target="_blank" rel="noopener noreferrer">原掲載元 ↗</a> · <a data-license target="_blank" rel="noopener noreferrer">利用条件 ↗</a></div></dialog>'


def shell(title, description, url, body, head, header, footer):
    h = head(title, description, url, '')
    # Use existing fonts and the current navigation without loading the map/app runtime.
    h = re.sub(r'<(?:link|script)\b[^>]*(?:href|src)="(?:app|map|learning|value-chain|atlas-routes|photo-rich)\.[^"]*"[^>]*>(?:</script>)?', '',h)
    h = h.replace('href="style.css', f'href="{BASE}style.css').replace('href="assets/', f'href="{BASE}assets/')
    h = re.sub(r'<meta property="og:image[^>]*>', '', h)
    end = re.sub(r'<script[^>]+src="https://embedr\.flickr\.com/[^>]*></script>', '', footer())
    end = re.sub(r'学習版 3\.3 · 更新日 [\d.]+', '空間デザイン特集 · 更新日 2026.10.27', end)
    return h.replace('</head>',assets()+'</head>') + header() + '<main id="main" class="sd-page">'+body+'</main>'+end+dialog()+'</body></html>'


def comparison(data):
    by_id = {p['id']:p for p in data['projects']}
    # Each cell points to the particular space that supports the comparison.
    rows=[
        ('文化・物語', [('kokuyo-hq','展示を、社員が説明・参加する機会へ。'),('etsy-brooklyn','地域のつくり手と、価値観を家具・材料へ。'),('barbarian-group','一続きの机を共同体の象徴へ。'),('frasers-london','商品・食・発表を日常へ重ねる。')]),
        ('動線と接点',[('mcdonalds-innovation-center','議論の場所を試験厨房へ近接。'),('nvidia-campus','共用動線の途中に、小さな滞在点。'),('tbwa-chiat-day','街路・広場・近隣単位を組み合わせる。'),('jojoe-gentilly','街路から飲食・庭へ。利用領域も分ける。')]),
        ('集中と交流',[('slack-hq','ラウンジと個人ブースを対照させる。'),('gensler-san-francisco','活動・気分別ゾーンと静かなVault。'),('intuit-bayshore','共用核とquiet libraries等の退避先。'),('google-super-hq','居間・集会・少人数等の参加強度を選ぶ。')]),
        ('可変性',[('microsoft-envisioning-center','デジタル機能と物理レイアウトを同時に試す。'),('adobe-founders-tower','可動ホワイトボード・AV・床配線。'),('intuit-bayshore','設備再構成の床と多様な家具。'),('frasers-london','可動壁・家具・照明で発表へ転換。')]),
        ('試作・表現の資源',[('mcdonalds-innovation-center','実物の厨房で試す。展示と実験を分ける。'),('adobe-founders-tower','craft・VR・podcast等を近づける。'),('googleplex-2005','小室の存在だけでは制作設備まで確認できない。'),('thg-media-city','移動できるremote programming labs。')]),
        ('運営者とルール',[('kokuyo-hq','コクヨとCHEERSによる部署別参加支援。'),('ibm-one-madison','IBMの専門家が課題・検証・導入計画をつなぐ。'),('macquarie-one-shelley','IT・行動・チーム拠点と変革支援。'),('jojoe-gentilly','飲食・イベント・ホストによる反復活動。')]),
        ('検証の方法',[('kokuyo-hq','イベント出力・満足度。空間単独の効果は不明。'),('gensler-san-francisco','occupancyの報告。出社方針との同時変化に留保。'),('macquarie-one-shelley','移転後の受容・有効性。自己申告と比較条件に留保。'),('gsk-global-hq','音響モデル→現物対策→コミッショニング。')]),
    ]
    out=['<div class="sd-table-wrap"><table class="sd-table sd-comparison"><caption>7つの観点で、実空間と適用条件を比較する</caption><thead><tr><th scope="col">見る観点</th>'+''.join('<th scope="col">'+e(c['shortName'])+'</th>' for c in data['companies'])+'</tr></thead><tbody>']
    for axis,values in rows:
        out.append('<tr><th scope="row">'+axis+'</th>')
        for c,(pid,text) in zip(data['companies'],values):
            out.append(f'<td data-label="{e(c["shortName"])}"><p>{e(text)}</p><a href="{project_url(by_id[pid])}">{e(by_id[pid]["name"])} →</a></td>')
        out.append('</tr>')
    return ''.join(out)+'</tbody></table></div>'


def build(root, head, header, footer, stages):
    data = read(root); sources=source_map(data); editorial=data['editorial']
    dest=root/'spatial-design'; dest.mkdir(exist_ok=True)
    cards=[]
    for c in data['companies']:
        photos=[m for m in data['media'] if m['publicationMode']=='image' and next(p for p in data['projects'] if p['id']==m['projectId'])['companyId']==c['id']]
        photos.sort(key=lambda m: (not m.get('companyFeatured', False), not m.get('featured', False)))
        photo=''
        if photos:
            p=next(p for p in data['projects'] if p['id']==photos[0]['projectId'])
            photo=image_gallery(p,data,compact=True)
        keyword=e(c['keyword']).replace('、','、<wbr>')
        cards.append(f'<article class="sd-company-card sd-color-{c["number"]}"><div class="sd-card-title"><p class="sd-kicker"><span>{c["number"]}</span> {e(c["name"])}</p><h3>{keyword}</h3><span class="sd-word" aria-hidden="true">{c["word"]}</span></div>{photo}<p class="sd-card-lead">{e(c["lead"])}</p><a class="sd-card-cta" href="{FEATURE}{c["id"]}/">{c["representativeCount"]}つの実空間から読む <span aria-hidden="true">↗</span></a></article>')
    project_cards=[]
    for i,p in enumerate(data['projects'],1):
        c=next(c for c in data['companies'] if c['id']==p['companyId'])
        count = photo_count(p, data)
        photos = project_photos(p, data)
        availability = '掲載 ' + media_count_label(photos) if count else '掲載写真 0枚 · 公式写真へのリンクあり'
        if photos:
            cover = photos[0]
            w, h = cover['dimensions']
            visual = f'<a class="sd-index-visual" href="{project_url(p)}"><img src="{BASE}{e(cover["local"])}" alt="{e(cover["alt"])}" width="{w}" height="{h}" loading="lazy"><span>{e(media_kind_label(cover))}</span></a>'
        else:
            reference = next(m for m in data['media'] if m['projectId'] == p['id'] and m['publicationMode'] == 'link-only')
            visual = f'<a class="sd-index-visual sd-reference-visual" href="{e(sources[reference["sourceId"]]["url"])}" target="_blank" rel="noopener noreferrer">公式掲載元の空間写真を見る ↗</a>'
        project_cards.append(f'<article class="sd-index-card" data-company="{p["companyId"]}"><p class="sd-kicker">{i:02d} / {e(c["shortName"])}</p>{visual}<h3><a href="{project_url(p)}">{e(p["name"])}</a></h3><p class="sd-index-meta">{e(p["location"])}<br>{e(p["year"])}</p><p>{e(p["tagline"])}</p><p class="sd-index-photo-count">{availability}</p><a class="sd-index-cta" href="{project_url(p)}">仕掛け・運営・成果を読む →</a></article>')
    stage_rows=[]
    for n in range(1,9):
        matches=[(p,s) for p in data['projects'] for s in p['steps'] if s['number']==n]
        refs=''.join(f'<li><a href="{project_url(p)}">{e(p["name"])} →</a><p>{e(s["why"])}</p></li>' for p,s in matches)
        stage_rows.append(f'<details class="sd-stage"><summary><b>{n:02d}</b><span>{e(stages[n])}</span><span aria-hidden="true">＋</span></summary><ul>{refs}</ul><p class="sd-stage-add"><strong>追加で担う仕事</strong>{e(editorial["stageConditions"][n-1])}</p><a class="sd-step-link" href="{BASE}learn/step-{n:02d}/">この工程を既存Atlasで学ぶ →</a></details>')
    filters='<div class="sd-filters" hidden aria-label="特集の実空間を絞る"><button type="button" data-sd-company="all" aria-pressed="true">すべて <span>23</span></button>'+''.join(f'<button type="button" data-sd-company="{c["id"]}" aria-pressed="false">{e(c["shortName"])}</button>' for c in data['companies'])+'<p id="sd-result-count" role="status" aria-live="polite">23の実空間</p></div>'
    checklist=[('変えたい行動','誰の、どの仕事や困りごとを変えるか。非利用者・遠隔参加者にも聞く。'),('運営する人','日常運営・IT/FM・安全・評価・データ・決裁の担当と予算を決める。'),('試すための資源','30〜120分の実験枠、道具、小予算、収納、静かな場所をそろえる。'),('測り方と中止条件','再会から試行への移行、着手時間、復旧時間、集中妨害・公平性・負担を記録する。')]
    body=breadcrumb()+f'<section class="sd-hero"><div><p class="sd-kicker">SPATIAL DESIGN / 独立特集</p><h1>空間は、共創を<br>どう変えるか。</h1><p class="sd-hero-lead">4つの設計思想、23の実空間。<br>仕掛けと日常の使われ方から、<br>人の行動を変える条件を読む。</p><a class="sd-button" href="#companies">4社の違いを見る <span aria-hidden="true">↓</span></a></div><div class="sd-hero-number"><b>04</b><span>DESIGN PHILOSOPHIES</span><p><strong>23</strong> 代表空間 <span>／ 2026.10.27</span></p></div></section>'+company_nav(data)+f'<section class="sd-section" id="companies"><header class="sd-section-heading"><span>01 / PHILOSOPHY</span><h2>何を、設計の単位にするか。</h2><p>優劣ではなく、思想と適用条件の違いを読む。</p></header><div class="sd-company-grid">{"".join(cards)}</div></section>'
    body+='<section class="sd-section sd-dark" id="relationships"><header class="sd-section-heading"><span>SPACE × OPERATION</span><h2>集まる、その先へ。</h2><p>出会いから次の行動へ。以下は検証するための仮説です。</p></header>'+render_blocks(editorial['causalPath'],sources)+'</section>'
    body+=f'<section class="sd-section" id="spaces"><header class="sd-section-heading"><span>02 / CASE STUDIES</span><h2>実空間から、深く読む。</h2><p>会社と実空間を別に管理。共同設計のMcDonald’s HQは一つの実空間として数えています。</p></header>{filters}<div class="sd-project-index">{"".join(project_cards)}</div><noscript><p>JavaScriptが無効な場合も、全23空間から詳細を読めます。</p></noscript></section>'
    body+='<section class="sd-section" id="compare"><header class="sd-section-heading"><span>03 / COMPARE</span><h2>同じ問いで、横断する。</h2><p>表のリンクから、比較の根拠となる実空間へ。</p></header>'+comparison(data)+'<details class="sd-deep-reading"><summary>公開される成果と、反証を読む ＋</summary><div class="sd-prose">'+render_blocks(editorial['results'],sources)+'</div></details></section>'
    body+='<section class="sd-section sd-principles" id="principles"><header class="sd-section-heading"><span>TRANSFER / 編集上の解釈・提案</span><h2>形より、原理を持ち帰る。</h2></header><ol>'+''.join('<li><span class="sd-principle-number">'+f'{i:02d}'+'</span><p>'+e(re.sub(r'^\d+\s+', '', b['text']))+'</p></li>' for i,b in enumerate(editorial['principles'],1) if b['type']=='p' and b['text'].strip())+'</ol></section>'
    body+='<section class="sd-section" id="steps"><header class="sd-section-heading"><span>04 / CONNECT TO 8 STEPS</span><h2>既存の8工程へ、つなぐ。</h2><p>実空間単位の編集上の解釈です。支える工程と、別途必要な仕事を確認できます。</p></header><div class="sd-stages">'+''.join(stage_rows)+'</div></section>'
    body+='<section class="sd-section sd-check" id="before-you-build"><header class="sd-section-heading"><span>05 / BEFORE YOU BUILD</span><h2>取り入れる前に、決める。</h2><p>交流が増えたことだけで、成功にしない。</p></header><div class="sd-checklist">'+''.join(f'<article><b>{i:02d}</b><h3>{title}</h3><p>{desc}</p></article>' for i,(title,desc) in enumerate(checklist,1))+'</div><details class="sd-deep-reading"><summary>導入3案＋現状維持と、30・90・365日の検証案 ＋</summary><div class="sd-prose">'+render_blocks(editorial['options']+editorial['experiment'],sources)+'</div></details><a class="sd-button" href="'+BASE+'learn/workbook/">既存の実践シートで計画する →</a></section>'
    cleared = [m for m in data['media'] if m['publicationMode'] == 'image']
    summary = media_count_label(cleared)
    body = body.replace('<a class="sd-button" href="#companies">', f'<p class="sd-hero-media">{summary}を掲載</p><a class="sd-button" href="#companies">', 1)
    body+=f'<section class="sd-section" id="sources"><header class="sd-section-heading"><span>SOURCES / 原典と確認範囲</span><h2>根拠と限界を、一緒に読む。</h2></header><div class="sd-prose">{render_blocks(editorial["sourceScope"],sources)}<p>利用条件を個別に確認した{summary}を掲載しています。提供レポートの69候補は、未許諾のまま複製せず公式掲載元への参照リンクを保持しています。追加素材の条件は写真ごとに異なり、写真・設計の権利は各権利者に帰属します。</p></div>'+source_library([s['id'] for s in data['sources']],data)+'</section>'
    (dest/'index.html').write_text(shell('空間は、共創をどう変えるか。｜4つの設計思想','O+A・Gensler・Clive Wilkinson Architects・PENSONの4社、23空間の仕掛け・運営・成果の根拠を読む。', 'https://mobilitydlab.com'+FEATURE,body,head,header,footer))
    for c in data['companies']:
        projects=[p for p in data['projects'] if p['companyId']==c['id']]
        jump='<nav class="sd-case-jump" aria-label="この会社の実空間">'+''.join(f'<a href="#{p["id"]}"><span>{e(p["name"])}<small>掲載 {media_count_label(project_photos(p, data))}</small></span><span aria-hidden="true">↓</span></a>' for p in projects)+'</nav>'
        body=breadcrumb(c)+f'<section class="sd-company-hero sd-color-{c["number"]}"><p class="sd-kicker">{c["number"]} / {c["word"]}</p><h1>{e(c["name"])}</h1><h2>{e(c["keyword"])}</h2><p>{e(c["intro"])}</p></section>'+company_nav(data,c['id'])
        body+='<section class="sd-section"><header class="sd-section-heading"><span>PHILOSOPHY & METHOD</span><h2>思想と、設計の方法。</h2><p>'+e(c['lead'])+'</p></header><details class="sd-deep-reading"><summary>思想・方法と成立条件を詳しく読む ＋</summary><div class="sd-prose">'+render_blocks(c['philosophy'],sources)+'</div></details>'+jump+'</section>'
        body+='<section class="sd-section sd-company-cases" aria-label="代表空間のケーススタディ">'+''.join(project_article(p,data,stages) for p in projects)+'</section>'
        if c['id']=='gensler':
            shared=next(p for p in data['projects'] if p['id']=='mcdonalds-hq')
            body+=f'<aside class="sd-section sd-shared"><h2>共同設計の参照：McDonald’s HQ</h2><p>Genslerは基幹建築/AOR、内装はIA＋Studio O+A、職場戦略はIA。既存の一つの実空間へリンクし、重複計数しません。</p><a href="{project_url(shared)}">担当範囲と実空間を読む →</a></aside>'
        body+='<section class="sd-section"><details class="sd-deep-reading"><summary>横断的な学び・補助事例・限界も読む ＋</summary><div class="sd-prose">'+render_blocks(c['furtherReading'],sources)+'</div></details>'+source_library(c['sourceIds'],data)+'</section><div class="sd-bottom-link"><a href="'+FEATURE+'#compare">4社を横断して比べる →</a><a href="'+FEATURE+'#before-you-build">自分の場で試す前に →</a></div>'
        out=dest/c['id'];out.mkdir(exist_ok=True)
        (out/'index.html').write_text(shell(c['name']+'｜'+c['keyword'],c['lead'],'https://mobilitydlab.com'+FEATURE+c['id']+'/',body,head,header,footer))
    integrate(root)
    print(f'Spatial design: 4 companies, 23 spaces, {len(cleared)} cleared media ({summary}); 69 original candidates remain link-only.')


def teaser():
    return '<aside class="sd-feature-entry"><div><p class="sd-kicker">SPATIAL DESIGN / 新しい独立特集</p><h2>空間は、共創をどう変えるか。</h2><p>O+A ／ Gensler ／ CWA ／ PENSON<br>4つの設計思想と23の実空間から、仕掛け・運営・成果を読む。</p></div><a href="'+FEATURE+'">4社の思想と実空間へ <span aria-hidden="true">↗</span></a></aside>'


def integrate(root):
    for path in [root/'index.html',root/'frontier/index.html']:
        text=path.read_text()
        text=re.sub(r'<aside class="sd-feature-entry">.*?</aside>','',text,flags=re.S)
        if path==root/'index.html':text=text.replace('<div class="step-home-grid"',teaser()+'<div class="step-home-grid"',1)
        else:text=text.replace('<section id="frontier-explore"',teaser()+'<section id="frontier-explore"',1)
        text=re.sub(r'<link[^>]+href="[^"]*spatial-design.css[^>]*>','',text)
        text=text.replace('</head>',f'<link rel="stylesheet" href="{BASE}spatial-design.css?v={VERSION}"></head>',1)
        path.write_text(text)
    sitemap=root/'sitemap.xml';text=sitemap.read_text()
    for suffix in ['']+[c['id']+'/' for c in read(root)['companies']]:
        url='https://mobilitydlab.com'+FEATURE+suffix
        if '<loc>'+url+'</loc>' not in text:text=text.replace('</urlset>',f'<url><loc>{url}</loc><lastmod>2026-10-27</lastmod></url></urlset>')
    sitemap.write_text(text)
