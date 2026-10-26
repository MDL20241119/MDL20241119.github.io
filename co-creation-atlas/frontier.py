"""Source-backed editorial discovery page. Does not mutate the existing case corpus."""
import html
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
VERSION = '20261026.1'
AXES = [('hard', 'HARD', 'ハード', '場所・設備のつくり方'),
        ('soft', 'SOFT', 'ソフト', '試し方・続け方'),
        ('partners', 'PARTNERS', 'パートナー', '役割・つながり方')]
FOCUSES = [('all', 'すべてのテーマ'), ('shared-labs', '共用研究工場・試作拠点'),
           ('physical-ai', 'フィジカルAIのラボ')]

def e(value):
    return html.escape(str(value), quote=True)

def focus_tags(c):
    return [tag for tag, key in [('shared-labs', 'sharedLab'), ('physical-ai', 'physicalAI')] if c.get(key)]

def focus_controls(rows):
    out = ['<div class="frontier-focus-controls"><div class="frontier-focus-filters" role="group" aria-label="テーマで絞り込む">']
    for key, label in FOCUSES:
        count = len(rows) if key == 'all' else sum(key in focus_tags(c) for c in rows)
        out.append(f'<button type="button" data-focus-filter="{key}" aria-pressed="{"true" if key == "all" else "false"}" aria-controls="frontier-results"><span>{label}</span> <b data-focus-count="{key}">{count}</b></button>')
    return ''.join(out)+'</div><p>テーマを選び、3つの切り口・8ステップと組み合わせて探せます。</p></div>'

def editorial_media(root, base_media=None):
    """Frontier-only photos never change corpus photo counts or the published catalog."""
    if base_media is None:
        base_media = json.loads((root/'data/media.json').read_text())
    extra_path = root/'data/frontier-media.json'
    extra_media = json.loads(extra_path.read_text()) if extra_path.exists() else []
    combined = list(base_media) + extra_media
    assert len(combined) == len({m['assetId'] for m in combined}), 'duplicate editorial media assetId'
    return combined

def read(root=ROOT):
    rows = json.loads((root/'data/frontier.json').read_text())
    stages = {s['step']:s['title'] for s in json.loads((root/'data/step-guide.json').read_text())}
    known = {c['id'] for c in json.loads((root/'data/cases.json').read_text())}
    media = {m['assetId']:m for m in editorial_media(root)}
    assert len(rows) == len({c['id'] for c in rows})
    assert set(c['lens'] for c in rows) == {a[0] for a in AXES}
    for c in rows:
        if c['id'] not in known:
            # Independent editorial entries do not add rows to the 115-case corpus.
            assert c.get('externalCase') is True and (c.get('photoId') or c.get('photoLink') or c.get('visualEmbed')), c['id']
            official = urlsplit(c.get('caseUrl', ''))
            assert official.scheme == 'https' and official.hostname and not official.username, c['id']
        else:
            assert not c.get('externalCase'), c['id']
        for key in ['headline', 'mechanism', 'interesting', 'checked', 'transfer', 'caution']:
            assert c[key]
        assert c['primaryStep']['number'] != c['secondaryStep']['number']
        for key in ['primaryStep', 'secondaryStep']:
            s = c[key]
            assert stages[s['number']] == s['title'] and s['why']
        assert c['sources']
        if c.get('photoLink'):
            assert c['photoLink']['url'].startswith('https://') and c['photoLink'].get('note'), c['id']
        if c.get('visualEmbed'):
            embed = c['visualEmbed']
            parsed_embed = urlsplit(embed['url'])
            assert parsed_embed.scheme == 'https' and parsed_embed.hostname in {'www.youtube.com', 'www.youtube-nocookie.com', 'player.vimeo.com', 'my.matterport.com'}, c['id']
            assert embed.get('title') and embed.get('note') and embed.get('sourceUrl', '').startswith('https://'), c['id']
        for source in c['sources']:
            assert source['url'].startswith('https://') and source['title'] and source['claim']
        assert not ({'rank', 'rankReason', 'scores', 'scoreNotes'} & set(c))
        for photo_id in ([c['photoId']] if c.get('photoId') else []) + c.get('extraPhotoIds', []):
            assert photo_id in media, c['id']
            selected = media[photo_id]
            assert selected['caseId'] == c['id'] and selected.get('kind') != 'diagram', c['id']
        for detail_key in ['sharedLab', 'facilityStudy']:
            lab = c.get(detail_key)
            if not lab: continue
            required = ['type', 'facilities', 'access', 'collaboration', 'photoReading']
            if detail_key == 'sharedLab': required.append('comparison')
            for key in required:
                assert isinstance(lab.get(key), str) and lab[key].strip(), (c['id'], key)
            assert lab.get('questions') and all(isinstance(q, str) and q.strip() for q in lab['questions'])
            assert lab.get('visualSources')
            for visual in lab['visualSources']:
                assert visual.get('title') and visual.get('note') and visual.get('url', '').startswith('https://')
    return rows, stages

def source(url, title):
    return f'<a href="{e(url)}" target="_blank" rel="noopener noreferrer">{e(title)} ↗</a>'

def case_photos(c, media):
    """Every selection needs a real photograph, including without JavaScript."""
    photos = [m for m in media if m['caseId'] == c['id'] and m.get('kind') != 'diagram' and m['assetId'] not in c.get('excludedPhotoIds', [])]
    preferred = ([c['photoId']] if c.get('photoId') else []) + c.get('extraPhotoIds', [])
    return sorted(photos, key=lambda m: preferred.index(m['assetId']) if m['assetId'] in preferred else len(preferred))

def photo(c, media, eager=False):
    if c.get('visualEmbed') and not c.get('photoId'):
        v = c['visualEmbed']
        return f'<figure class="frontier-photo frontier-video"><div class="frontier-image"><iframe src="{e(v["url"])}" title="{e(v["title"])}" loading="lazy" allow="fullscreen; picture-in-picture" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div><figcaption><span>{e(v["note"])}</span><p>{source(v["sourceUrl"], "公式の施設映像を開く")}</p></figcaption></figure>'
    if c.get('photoLink') and not c.get('photoId'):
        v = c['photoLink']
        return f'<figure class="frontier-photo frontier-photo-link"><div class="frontier-image"><a href="{e(v["url"])}" target="_blank" rel="noopener noreferrer"><span class="frontier-space-label">SPACE VIEW</span><strong>{e(c["name"])}</strong><span>公式の施設写真を見る <b aria-hidden="true">↗</b></span></a></div><figcaption><span>{e(v["note"])}</span></figcaption></figure>'
    m = next(m for m in media if m['caseId']==c['id'] and m.get('kind')!='diagram' and (not c.get('photoId') or m['assetId']==c['photoId']))
    src = m.get('remote') or '../'+m['local']
    if m.get('revision') and not m.get('remote'): src += '?v='+m['revision']
    no_crop = m.get('noCrop') or m.get('status') in {'cleared-editorial-only', 'editorial-quotation'}
    width, height = m.get('dimensions', [1600,1000])
    image = f'<img src="{e(src)}" alt="{e(m["alt"])}" width="{width}" height="{height}" loading="{"eager" if eager else "lazy"}" decoding="async">'
    if m.get('status')=='provider-embed':
        image = f'<a data-flickr-embed="true" href="{e(m["sourceUrl"])}" target="_blank" rel="noopener noreferrer" aria-label="{e(c["name"])}の写真を掲載元で見る">{image}</a>'
    else:
        image = f'<a class="frontier-photo-open" href="{e(src)}" target="_blank" rel="noopener noreferrer" aria-label="{e(c["name"])}：{e(m["alt"])}（写真を拡大）">{image}</a>'
    rights = (m.get('licenseUrl') if m.get('status')=='cleared-cc' else m.get('rightsUrl')) or m.get('rightsUrl') or m.get('licenseUrl') or m['sourceUrl']
    caption = m.get('scopeLabel') or m.get('caption') or m['alt']
    credit = f'<figcaption><span>{e(caption)}</span><details><summary>写真の出典・利用条件</summary><p>PHOTO: {e(m["credit"])} · {source(m["sourceUrl"],"掲載元")} · {source(rights,m["license"])}</p><p>{e(m.get("imageDate", ""))} {e(m.get("changes", ""))}</p><p>{e(m.get("caption", ""))}</p><p>{e(m.get("rightsNote", ""))}</p></details></figcaption>'
    return f'<figure class="frontier-photo{" no-crop" if no_crop else ""}"><div class="frontier-image">{image}</div>{credit}</figure>'

def gallery(c, media, eager=False):
    photos = case_photos(c, media)
    assert photos, '先進事例の写真がありません: '+c['id']
    lead = photo(dict(c, photoId=photos[0]['assetId']), media, eager)
    rail = ''
    if len(photos) > 1:
        rail = '<div class="frontier-gallery-thumbs" aria-label="別の角度から見る写真">'+''.join(photo(dict(c, photoId=m['assetId']), media) for m in photos[1:])+'</div>'
    return f'<div class="frontier-gallery" data-photo-count="{len(photos)}">{lead}{rail}</div>'

def photo_dialog():
    return '<dialog class="frontier-lightbox" aria-labelledby="frontier-photo-title"><div class="frontier-lightbox-header"><h2 id="frontier-photo-title">写真を拡大して見る</h2><button type="button" data-photo-close autofocus>閉じる ×</button></div><div data-photo-viewer-image></div><div class="frontier-lightbox-caption"></div></dialog>'

def step(s, primary):
    return f'<div class="frontier-step {"primary" if primary else "secondary"}" data-step="{s["number"]}"><span class="frontier-step-role">{"特に活かせる" if primary else "あわせて活かせる"}</span><a href="../learn/step-{s["number"]:02d}/"><b>{s["number"]:02d}</b><strong>{e(s["title"])}</strong><span aria-hidden="true">↗</span></a><p>{e(s["why"])}</p></div>'

def lab_visuals(c):
    lab = c.get('sharedLab') or c.get('facilityStudy')
    if not lab: return ''
    title = '写真から見る、共用する場' if c.get('sharedLab') else '写真から見る、施設・空間'
    out = [f'<aside class="frontier-lab-visuals"><h3>{title}</h3>', f'<p>{e(lab["photoReading"])}</p>', '<ul>']
    for visual in lab['visualSources']:
        out.append(f'<li>{source(visual["url"],visual["title"])}<p>{e(visual["note"])}</p></li>')
    return ''.join(out)+'</ul></aside>'

def lab_detail(c):
    lab = c.get('sharedLab') or c.get('facilityStudy')
    if not lab: return ''
    title = '共用研究工場の仕組みを詳しく' if c.get('sharedLab') else '施設・空間の仕組みを詳しく'
    comparison_label = 'ARENA2036との共通点・違い（ATLASの分析）' if c.get('sharedLab') else '施設を読む視点（ATLASの分析）'
    out = [f'<section class="frontier-lab-detail"><h3>{title}</h3><dl>']
    for key, label in [('type','どんな場か'), ('facilities','使える設備・環境'), ('access','利用条件と支援'), ('collaboration','場を動かす運営・連携'), ('comparison', comparison_label)]:
        if lab.get(key): out.append(f'<dt>{label}</dt><dd>{e(lab[key])}</dd>')
    out.append('</dl><h3>取り入れる前に確かめたいこと</h3><ul>')
    out.extend(f'<li>{e(q)}</li>' for q in lab['questions'])
    return ''.join(out)+'</ul></section>'

def physical_ai_detail(c):
    lab = c.get('physicalAI')
    if not lab: return ''
    fields = [('robots', 'ロボット・実機'), ('data', 'データを集める'),
              ('simulation', '仮想環境で試す'), ('validation', '実機で確かめる'),
              ('safety', '安全・人との協働'), ('access', '利用・連携の条件'),
              ('status', '現在の運用状況')]
    items = ''.join(f'<dt>{label}</dt><dd>{e(lab[key])}</dd>' for key, label in fields if lab.get(key))
    if not items: return ''
    return '<section class="frontier-lab-detail frontier-physical-ai-detail"><h3>フィジカルAIを動かす実験環境</h3><dl>'+items+'</dl></section>'

def photo_notes(c, media):
    """Keep reading notes separate from the always-visible photographs."""
    content = lab_visuals(c)
    if not content:
        return '<div class="frontier-visuals-row" aria-hidden="true"></div>'
    return '<div class="frontier-visuals-row"><details class="frontier-visual-details"><summary>写真で読み解く、空間の特徴 <span aria-hidden="true">＋</span></summary><div class="frontier-visual-details-inner">'+content+'</div></details></div>'

def shared_lab_feature(rows, media):
    labs = [c for c in rows if c.get('sharedLab')]
    if not labs: return ''
    arena = next(c for c in labs if c['id']=='arena2036')
    out = ['<section class="frontier-shared-feature" aria-labelledby="frontier-shared-title"><div class="frontier-shared-lead"><div class="frontier-shared-copy"><p class="eyebrow">FOCUS / SHARED RESEARCH FACTORIES</p><h2 id="frontier-shared-title">ARENA2036のような、<br>一緒につくり、試す場所へ。</h2><p>工場、試作設備、技術者、企業の課題。何を共用し、誰が実験を支え、共同開発を次へ進めるのか。研究工場やロボティクス拠点を、空間と運営の両方から読み解きます。</p>', f'<a class="frontier-focus-link" href="?focus=shared-labs#frontier-explore">共用研究工場の{len(labs)}事例を探す <span aria-hidden="true">↓</span></a><p class="frontier-shared-note">類似性はATLASの編集上の分析です。施設の規模や成果の順位ではありません。</p></div>', photo(arena, media, True), '</div><details class="frontier-shared-comparison"><summary>7つの場を、役割の違いから見比べる</summary><div class="frontier-comparison-scroll"><table><caption>共用研究工場・試作拠点の比較はATLASの分析です。詳細と根拠は各事例へ。</caption><thead><tr><th scope="col">施設</th><th scope="col">どんな場か</th><th scope="col">ARENA2036との共通点・違い</th></tr></thead><tbody>']
    for c in labs:
        out.append(f'<tr><th scope="row"><a href="?focus=shared-labs#case-{e(c["id"])}">{e(c["name"])}</a></th><td>{e(c["sharedLab"]["type"])}</td><td>{e(c["sharedLab"]["comparison"])}</td></tr>')
    return ''.join(out)+'</tbody></table></div></details></section>'

def physical_ai_feature(rows):
    count = sum(bool(c.get('physicalAI')) for c in rows)
    if not count: return ''
    return f'<section class="frontier-physical-ai-feature" aria-labelledby="frontier-physical-ai-title"><div><p class="eyebrow">FOCUS / PHYSICAL AI</p><h2 id="frontier-physical-ai-title">フィジカルAIのラボを探す</h2><p>ロボットが学び、実空間で動くまで。データ収集、シミュレーション、実機試験を支える設備と、利用・連携の条件を読み解きます。</p></div><a class="frontier-focus-link" href="?focus=physical-ai#frontier-explore">{count}事例の実験環境を見る <span aria-hidden="true">↓</span></a></section>'

def card(c, media, eager=False):
    axis = next(a for a in AXES if a[0]==c['lens'])
    status = ''
    if c.get('statusLabel'):
        status = f'<div class="frontier-status"><strong>{e(c["statusLabel"])}</strong><span>{e(c.get("statusNote", ""))}</span></div>'
    out = [f'<article class="frontier-card" id="case-{e(c["id"])}" data-case-id="{e(c["id"])}" data-axis="{c["lens"]}" data-focus="{" ".join(focus_tags(c))}" data-steps="{c["primaryStep"]["number"]} {c["secondaryStep"]["number"]}">',
           f'<div class="frontier-card-heading"><div class="frontier-card-meta"><span class="frontier-axis-label">{axis[1]} / {axis[2]}</span><span>{e(c["country"])}</span></div><h2>{e(c["headline"])}</h2><p class="frontier-facility">{e(c["name"])} <span>／ {e(c["city"])}</span></p></div>',
           gallery(c, media, eager),
           '<div class="frontier-card-body">'+status,
           f'<p class="frontier-mechanism">{e(c["mechanism"])}</p>',
           f'<div class="frontier-insight"><span>ここが面白い</span><p>{e(c["interesting"])}</p></div>',
           '<div class="frontier-steps"><h3>活かせるステップ</h3>'+step(c['primaryStep'],True)+step(c['secondaryStep'],False)+'</div>',
           photo_notes(c, media),
           f'<details class="frontier-evidence"><summary>{"設備・利用条件・実績・一次資料" if c.get("sharedLab") or c.get("facilityStudy") else "実績・取り入れるヒント・一次資料"} <span aria-hidden="true">＋</span></summary><div class="frontier-evidence-inner">'+lab_detail(c)+physical_ai_detail(c)+f'<h3>確認できた実績と限界</h3><p>{e(c["outcome"]["text"])}</p><p class="frontier-date">対象・公表時点：{e(c["outcome"]["date"])}</p><p>{e(c["outcome"]["caveat"])}</p><h3>取り入れるなら</h3><p>{e(c["transfer"])}</p><p class="frontier-caution">{e(c["caution"])}</p><h3>誰が、何を担う？</h3><dl class="frontier-partner-roles">']
    for p in c['partners']:
        out.append(f'<dt>{e(p["name"])}</dt><dd>{e(p["contribution"])}</dd>')
    out.append(f'</dl><h3>一次資料</h3><p class="frontier-date">確認日：{e(c["checked"])}（日本時間）</p><ul class="frontier-source-list">')
    for s in c['sources']:
        note = ''.join(f'<p>{label}：{e(s[key])}</p>' for key, label in [('locator', '確認箇所'), ('accessNote', '閲覧・確認の範囲')] if s.get(key))
        out.append(f'<li>{source(s["url"],s["title"])}<p>公表：{e(s.get("publishedDate", "日付記載なし"))}</p><p>{e(s["claim"])}</p>{note}</li>')
    case_url = c['caseUrl'] if c.get('externalCase') else f'../cases/{c["id"]}/'
    case_label = '施設の公式サイトを見る' if c.get('externalCase') else 'ATLASの詳しい事例を読む'
    case_target = ' target="_blank" rel="noopener noreferrer"' if c.get('externalCase') else ''
    out.append(f'</ul></div></details><a class="frontier-case-link" href="{e(case_url)}"{case_target}>{case_label} <span aria-hidden="true">{"↗" if c.get("externalCase") else "→"}</span></a></div></article>')
    return ''.join(out)

def build(root, media, head, header, footer, base):
    media = editorial_media(root, media)
    rows, stages = read(root)
    counts = Counter(c['lens'] for c in rows)
    title = '世界の先進事例を、ハード・ソフト・パートナーから探す。'
    description = '世界の面白い共創の仕組みを、場所・設備、運営・プログラム、連携相手から発見。各事例で活かせる8ステップと、その理由を紹介します。'
    page_head = head(title, description, base+'frontier/', '../')
    page_head = page_head.replace('</head>', f'<link rel="stylesheet" href="../frontier.css?v={VERSION}"><script defer src="../frontier.js?v={VERSION}"></script></head>')
    out = [page_head, header('../'), '<main id="main" class="frontier-page">',
           '<nav class="frontier-breadcrumb" aria-label="現在位置"><a href="../">ATLASトップ</a><span aria-hidden="true">／</span><span aria-current="page">世界の先進事例</span></nav>',
           '<section class="frontier-hero"><div><p class="eyebrow">WORLD CO-CREATION ATLAS / EDITORIAL SELECTION</p><div class="frontier-wordmark" aria-hidden="true">WORLD<br><span>FRONTIERS.</span></div></div><div class="frontier-hero-copy"><h1>共創の次の一手を、<br>世界の面白い仕組みから。</h1><p>ハード、ソフト、パートナー。<br>3つの切り口で発見し、<br>「どのステップで、どう役立つか」まで。</p><a href="#frontier-explore">事例を探す <span aria-hidden="true">↓</span></a></div></section>',
           shared_lab_feature(rows, media),
           physical_ai_feature(rows),
           f'<div class="frontier-intro"><p><strong>{len(rows)}の編集選定事例</strong> <span>／ 順位ではなく、仕組みの違いから学ぶ。</span></p><a href="#frontier-policy">選定・読み方について ↓</a></div>',
           '<section id="frontier-explore" class="frontier-explore" aria-label="切り口とステップで探す"><div id="frontier-controls" class="frontier-controls" hidden>',
           focus_controls(rows)+'<div class="frontier-axis-filters" role="group" aria-label="切り口で絞り込む">',
           f'<button type="button" data-axis-filter="all" aria-pressed="true" aria-controls="frontier-results"><span class="frontier-tab-en">ALL</span><span class="frontier-tab-name">すべて <b data-axis-count="all">{len(rows)}</b></span><small>切り口を横断する</small></button>']
    for key, en, ja, desc in AXES:
        out.append(f'<button type="button" data-axis-filter="{key}" aria-pressed="false" aria-controls="frontier-results"><span class="frontier-tab-en">{en}</span><span class="frontier-tab-name">{ja} <b data-axis-count="{key}">{counts[key]}</b></span><small>{desc}</small></button>')
    out.append('</div><div class="frontier-filter-line"><label for="frontier-step-filter">活かせるステップで絞る<select id="frontier-step-filter" aria-controls="frontier-results">')
    out.append(f'<option value="all">すべてのステップ（{len(rows)}）</option>')
    for n, name in stages.items():
        count = sum(n in [c['primaryStep']['number'],c['secondaryStep']['number']] for c in rows)
        out.append(f'<option value="{n}">{n:02d} {e(name)}（{count}）</option>')
    out.append('</select></label><button type="button" id="frontier-reset" disabled>条件をクリア <span aria-hidden="true">×</span></button><p>「特に活かせる」「あわせて活かせる」の両方から探せます。</p></div></div>')
    out.append(f'<noscript><p class="frontier-noscript">全{len(rows)}件を表示しています。絞り込みはJavaScriptを有効にすると使えます。</p></noscript><div class="frontier-result-line"><p id="frontier-result-status" role="status" aria-live="polite" aria-atomic="true"><strong>{len(rows)}</strong> 件 ／ すべての切り口・ステップ</p><a href="../#start">8ステップの全体像を見る ↗</a></div><div id="frontier-empty" class="frontier-empty" hidden><p class="frontier-tab-en">NO MATCH</p><h2>この組み合わせの選定事例は、まだありません。</h2><p>取り組みが存在しない、という意味ではありません。条件を変えて探してみてください。</p><button type="button" data-frontier-reset>すべての事例に戻す →</button></div><div class="frontier-grid" id="frontier-results">')
    for i,c in enumerate(rows): out.append(card(c, media, i<2))
    out.append('</div></section><section id="frontier-policy" class="frontier-policy"><div><p class="eyebrow">HOW TO READ</p><h2>新しさを、<br>実践に変えるために。</h2></div><div><p><strong>世界の先進事例を、仕組みで選ぶ。</strong><br>世界の研究・試作・実証拠点から、設備・運営・連携の工夫が一次資料で具体的に読める事例を編集選定しています。世界全域の網羅調査、公式の世界順位、効果の優劣を示すものではありません。掲載順に優劣はありません。</p><p><strong>ステップへの対応は、ATLASの分析。</strong><br>主に役立つステップと、あわせて役立つステップを、その理由とともに示しています。各施設がこの8ステップを採用しているという意味や、工程別の効果の保証ではありません。</p><p><strong>実績、計画、限界を分ける。</strong><br>運営者の報告は独立した効果測定と区別し、計画・実証終了・標準化への移管などの状態も表示。写真の時点・対象範囲・権利は各写真の詳細に、根拠と確認日は各カードの一次資料に記載しています。</p><p class="frontier-date">選定・資料確認：2026年10月25日（日本時間）</p><div class="frontier-policy-links"><a href="../#start">8ステップで学ぶ →</a><a href="../#explore">全115事例を探す →</a></div></div></section></main>')
    out.append(photo_dialog()+footer().replace('学習版 3.3 · 更新日 2026.10.07', 'フロンティア選定 · 写真・レイアウト更新 2026.10.26')+'</body></html>')
    dest = root/'frontier'; dest.mkdir(exist_ok=True)
    (dest/'index.html').write_text(''.join(out))
    # Add one high-visibility entry, after the existing hero and before the eight steps.
    home = root/'index.html'; page = home.read_text()
    marker = '<div class="step-home-grid" id="start">'
    assert page.count(marker)==1
    shared_count = sum(bool(c.get('sharedLab')) for c in rows)
    physical_ai_count = sum(bool(c.get('physicalAI')) for c in rows)
    physical_ai_entry = f'<a class="frontier-entry-topic" href="frontier/?focus=physical-ai#frontier-explore">フィジカルAIのラボ {physical_ai_count}件を読む →</a>' if physical_ai_count else ''
    teaser = f'<aside class="frontier-entry"><div><p class="eyebrow">WORLD FRONTIERS / 世界の先進事例</p><h2>ハード・ソフト・パートナーから、<br>面白い共創の仕組みを発見する。</h2><p>各事例で「活かせるステップ」と、その理由もわかる。</p><a class="frontier-entry-topic" href="frontier/?focus=shared-labs#frontier-explore">ARENA2036のような共用研究・試作拠点 {shared_count}件を読む →</a>{physical_ai_entry}</div><a href="frontier/">3つの切り口から探す <span aria-hidden="true">↗</span></a></aside>'
    page = page.replace(marker, teaser+marker, 1)
    page = page.replace('</head>', f'<link rel="stylesheet" href="frontier.css?v={VERSION}"><link rel="stylesheet" href="atlas-layout.css?v={VERSION}"></head>', 1)
    home.write_text(page)
    # Add a return route to the freshly generated detail pages of this selection.
    for c in rows:
        if not c.get('sharedLab'): continue
        case_page = root/'cases'/c['id']/'index.html'
        detail = case_page.read_text()
        assert detail.count('</main>') == 1, c['id']
        back = f'<aside class="frontier-case-return"><div><p class="eyebrow">WORLD FRONTIERS / 共用研究・試作拠点</p><h2>この場所を、ARENA2036や他の拠点と見比べる。</h2><p>設備、利用条件、共同開発の進め方を、{shared_count}事例から読み解きます。比較とステップ対応はATLASの分析です。</p></div><a href="../../frontier/?focus=shared-labs#case-{e(c["id"])}">共用研究工場の特集へ →</a></aside>'
        if 'class="frontier-case-return"' not in detail:
            detail = detail.replace('</main>', back+'</main>', 1)
        if '../../frontier.css?' not in detail:
            detail = detail.replace('</head>', f'<link rel="stylesheet" href="../../frontier.css?v={VERSION}"></head>', 1)
        case_page.write_text(detail)
    sitemap = root/'sitemap.xml'; xml = sitemap.read_text()
    entry = f'<url><loc>{base}frontier/</loc><lastmod>2026-10-25</lastmod></url>'
    if base+'frontier/' not in xml: sitemap.write_text(xml.replace('</urlset>',entry+'</urlset>'))
