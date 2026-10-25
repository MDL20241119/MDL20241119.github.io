"""Source-backed editorial discovery page. Does not mutate the existing case corpus."""
import html
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSION = '20261025.2'
AXES = [('hard', 'HARD', 'ハード', '場所・設備のつくり方'),
        ('soft', 'SOFT', 'ソフト', '試し方・続け方'),
        ('partners', 'PARTNERS', 'パートナー', '役割・つながり方')]

def e(value):
    return html.escape(str(value), quote=True)

def read(root=ROOT):
    rows = json.loads((root/'data/frontier.json').read_text())
    stages = {s['step']:s['title'] for s in json.loads((root/'data/step-guide.json').read_text())}
    known = {c['id'] for c in json.loads((root/'data/cases.json').read_text())}
    media = {m['assetId']:m for m in json.loads((root/'data/media.json').read_text())}
    assert len(rows) == len({c['id'] for c in rows})
    assert set(c['lens'] for c in rows) == {a[0] for a in AXES}
    for c in rows:
        assert c['id'] in known
        for key in ['headline', 'mechanism', 'interesting', 'checked', 'transfer', 'caution']:
            assert c[key]
        assert c['primaryStep']['number'] != c['secondaryStep']['number']
        for key in ['primaryStep', 'secondaryStep']:
            s = c[key]
            assert stages[s['number']] == s['title'] and s['why']
        assert c['sources']
        for source in c['sources']:
            assert source['url'].startswith('https://') and source['title'] and source['claim']
        assert not ({'rank', 'rankReason', 'scores', 'scoreNotes'} & set(c))
        for photo_id in ([c['photoId']] if c.get('photoId') else []) + c.get('extraPhotoIds', []):
            assert photo_id in media, c['id']
            selected = media[photo_id]
            assert selected['caseId'] == c['id'] and selected.get('kind') != 'diagram', c['id']
        if c.get('sharedLab'):
            lab = c['sharedLab']
            for key in ['type', 'facilities', 'access', 'collaboration', 'comparison', 'photoReading']:
                assert isinstance(lab.get(key), str) and lab[key].strip(), (c['id'], key)
            assert lab.get('questions') and all(isinstance(q, str) and q.strip() for q in lab['questions'])
            assert lab.get('visualSources')
            for visual in lab['visualSources']:
                assert visual.get('title') and visual.get('note') and visual.get('url', '').startswith('https://')
    return rows, stages

def source(url, title):
    return f'<a href="{e(url)}" target="_blank" rel="noopener noreferrer">{e(title)} ↗</a>'

def photo(c, media, eager=False):
    m = next(m for m in media if m['caseId']==c['id'] and m.get('kind')!='diagram' and (not c.get('photoId') or m['assetId']==c['photoId']))
    src = m.get('remote') or '../'+m['local']
    if m.get('revision') and not m.get('remote'): src += '?v='+m['revision']
    no_crop = m.get('noCrop') or m.get('status')=='cleared-editorial-only'
    width, height = m.get('dimensions', [1600,1000])
    image = f'<img src="{e(src)}" alt="{e(m["alt"])}" width="{width}" height="{height}" loading="{"eager" if eager else "lazy"}" decoding="async">'
    if m.get('status')=='provider-embed':
        image = f'<a data-flickr-embed="true" href="{e(m["sourceUrl"])}" target="_blank" rel="noopener noreferrer" aria-label="{e(c["name"])}の写真を掲載元で見る">{image}</a>'
    rights = (m.get('licenseUrl') if m.get('status')=='cleared-cc' else m.get('rightsUrl')) or m.get('rightsUrl') or m.get('licenseUrl') or m['sourceUrl']
    caption = m.get('scopeLabel') or m.get('caption') or m['alt']
    credit = f'<figcaption><span>{e(caption)}</span><details><summary>写真の出典・利用条件</summary><p>PHOTO: {e(m["credit"])} · {source(m["sourceUrl"],"掲載元")} · {source(rights,m["license"])}</p><p>{e(m.get("imageDate", ""))} {e(m.get("changes", ""))}</p><p>{e(m.get("caption", ""))}</p></details></figcaption>'
    return f'<figure class="frontier-photo{" no-crop" if no_crop else ""}"><div class="frontier-image">{image}</div>{credit}</figure>'

def step(s, primary):
    return f'<div class="frontier-step {"primary" if primary else "secondary"}" data-step="{s["number"]}"><span class="frontier-step-role">{"特に活かせる" if primary else "あわせて活かせる"}</span><a href="../learn/step-{s["number"]:02d}/"><b>{s["number"]:02d}</b><strong>{e(s["title"])}</strong><span aria-hidden="true">↗</span></a><p>{e(s["why"])}</p></div>'

def lab_visuals(c):
    lab = c.get('sharedLab')
    if not lab: return ''
    out = ['<aside class="frontier-lab-visuals"><h3>写真から見る、共用する場</h3>', f'<p>{e(lab["photoReading"])}</p>', '<ul>']
    for visual in lab['visualSources']:
        out.append(f'<li>{source(visual["url"],visual["title"])}<p>{e(visual["note"])}</p></li>')
    return ''.join(out)+'</ul></aside>'

def lab_detail(c):
    lab = c.get('sharedLab')
    if not lab: return ''
    out = ['<section class="frontier-lab-detail"><h3>共用研究工場の仕組みを詳しく</h3><dl>']
    for key, label in [('type','どんな場か'), ('facilities','共用する設備・環境'), ('access','利用条件と支援'), ('collaboration','共同開発の進め方'), ('comparison','ARENA2036との共通点・違い（ATLASの分析）')]:
        out.append(f'<dt>{label}</dt><dd>{e(lab[key])}</dd>')
    out.append('</dl><h3>取り入れる前に確かめたいこと</h3><ul>')
    out.extend(f'<li>{e(q)}</li>' for q in lab['questions'])
    return ''.join(out)+'</ul></section>'

def shared_lab_feature(rows, media):
    labs = [c for c in rows if c.get('sharedLab')]
    if not labs: return ''
    arena = next(c for c in labs if c['id']=='arena2036')
    out = ['<section class="frontier-shared-feature" aria-labelledby="frontier-shared-title"><div class="frontier-shared-lead"><div class="frontier-shared-copy"><p class="eyebrow">FOCUS / SHARED RESEARCH FACTORIES</p><h2 id="frontier-shared-title">ARENA2036のような、<br>一緒につくり、試す場所へ。</h2><p>工場、試作設備、技術者、企業の課題。何を共用し、誰が実験を支え、共同開発を次へ進めるのか。研究工場やロボティクス拠点を、空間と運営の両方から読み解きます。</p>', f'<a class="frontier-focus-link" href="?focus=shared-labs#frontier-explore">共用研究工場の{len(labs)}事例を探す <span aria-hidden="true">↓</span></a><p class="frontier-shared-note">類似性はATLASの編集上の分析です。施設の規模や成果の順位ではありません。</p></div>', photo(arena, media, True), '</div><details class="frontier-shared-comparison"><summary>7つの場を、役割の違いから見比べる</summary><div class="frontier-comparison-scroll"><table><caption>共用研究工場・試作拠点の比較はATLASの分析です。詳細と根拠は各事例へ。</caption><thead><tr><th scope="col">施設</th><th scope="col">どんな場か</th><th scope="col">ARENA2036との共通点・違い</th></tr></thead><tbody>']
    for c in labs:
        out.append(f'<tr><th scope="row"><a href="?focus=shared-labs#case-{e(c["id"])}">{e(c["name"])}</a></th><td>{e(c["sharedLab"]["type"])}</td><td>{e(c["sharedLab"]["comparison"])}</td></tr>')
    return ''.join(out)+'</tbody></table></div></details></section>'

def card(c, media, eager=False):
    axis = next(a for a in AXES if a[0]==c['lens'])
    status = ''
    if c.get('statusLabel'):
        status = f'<div class="frontier-status"><strong>{e(c["statusLabel"])}</strong><span>{e(c.get("statusNote", ""))}</span></div>'
    out = [f'<article class="frontier-card" id="case-{e(c["id"])}" data-case-id="{e(c["id"])}" data-axis="{c["lens"]}" data-focus="{"shared-labs" if c.get("sharedLab") else ""}" data-steps="{c["primaryStep"]["number"]} {c["secondaryStep"]["number"]}">',
           f'<div class="frontier-card-heading"><div class="frontier-card-meta"><span class="frontier-axis-label">{axis[1]} / {axis[2]}</span><span>{e(c["country"])}</span></div><h2>{e(c["headline"])}</h2><p class="frontier-facility">{e(c["name"])} <span>／ {e(c["city"])}</span></p></div>',
           photo(c, media, eager),
           ('<details class="frontier-photo-more"><summary>別の角度から空間を見る</summary>'+''.join(photo(dict(c, photoId=pid), media) for pid in c.get('extraPhotoIds', []))+'</details>') if c.get('extraPhotoIds') else '',
           '<div class="frontier-card-body">'+status,
           lab_visuals(c),
           f'<p class="frontier-mechanism">{e(c["mechanism"])}</p>',
           f'<div class="frontier-insight"><span>ここが面白い</span><p>{e(c["interesting"])}</p></div>',
           '<div class="frontier-steps"><h3>活かせるステップ</h3>'+step(c['primaryStep'],True)+step(c['secondaryStep'],False)+'</div>',
           f'<details class="frontier-evidence"><summary>{"設備・利用条件・実績・一次資料" if c.get("sharedLab") else "実績・取り入れるヒント・一次資料"} <span aria-hidden="true">＋</span></summary><div class="frontier-evidence-inner">'+lab_detail(c)+f'<h3>確認できた実績と限界</h3><p>{e(c["outcome"]["text"])}</p><p class="frontier-date">対象・公表時点：{e(c["outcome"]["date"])}</p><p>{e(c["outcome"]["caveat"])}</p><h3>取り入れるなら</h3><p>{e(c["transfer"])}</p><p class="frontier-caution">{e(c["caution"])}</p><h3>誰が、何を担う？</h3><dl class="frontier-partner-roles">']
    for p in c['partners']:
        out.append(f'<dt>{e(p["name"])}</dt><dd>{e(p["contribution"])}</dd>')
    out.append(f'</dl><h3>一次資料</h3><p class="frontier-date">確認日：{e(c["checked"])}（日本時間）</p><ul class="frontier-source-list">')
    for s in c['sources']:
        note = ''.join(f'<p>{label}：{e(s[key])}</p>' for key, label in [('locator', '確認箇所'), ('accessNote', '閲覧・確認の範囲')] if s.get(key))
        out.append(f'<li>{source(s["url"],s["title"])}<p>公表：{e(s.get("publishedDate", "日付記載なし"))}</p><p>{e(s["claim"])}</p>{note}</li>')
    out.append(f'</ul></div></details><a class="frontier-case-link" href="../cases/{e(c["id"])}/">ATLASの詳しい事例を読む <span aria-hidden="true">→</span></a></div></article>')
    return ''.join(out)

def build(root, media, head, header, footer, base):
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
           f'<div class="frontier-intro"><p><strong>{len(rows)}の編集選定事例</strong> <span>／ 順位ではなく、仕組みの違いから学ぶ。</span></p><a href="#frontier-policy">選定・読み方について ↓</a></div>',
           '<section id="frontier-explore" class="frontier-explore" aria-label="切り口とステップで探す"><div id="frontier-controls" class="frontier-controls" hidden>',
           f'<div class="frontier-focus-controls"><label for="frontier-shared-filter"><input type="checkbox" id="frontier-shared-filter" aria-controls="frontier-results"><span>共用研究工場・試作拠点に絞る <b data-focus-count>{sum(bool(c.get("sharedLab")) for c in rows)}</b></span></label><p>ARENA2036から広げて探す。3つの切り口・8ステップと組み合わせられます。</p></div><div class="frontier-axis-filters" role="group" aria-label="切り口で絞り込む">',
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
    out.append('</div></section><section id="frontier-policy" class="frontier-policy"><div><p class="eyebrow">HOW TO READ</p><h2>新しさを、<br>実践に変えるために。</h2></div><div><p><strong>世界の先進事例を、仕組みで選ぶ。</strong><br>既存のATLAS掲載事例から、設備・運営・連携の工夫が一次資料で具体的に読める事例を編集選定しています。世界全域の網羅調査、公式の世界順位、効果の優劣を示すものではありません。掲載順に優劣はありません。</p><p><strong>ステップへの対応は、ATLASの分析。</strong><br>主に役立つステップと、あわせて役立つステップを、その理由とともに示しています。各施設がこの8ステップを採用しているという意味や、工程別の効果の保証ではありません。</p><p><strong>実績、計画、限界を分ける。</strong><br>運営者の報告は独立した効果測定と区別し、計画・実証終了・標準化への移管などの状態も表示。写真の時点・対象範囲・権利は各写真の詳細に、根拠と確認日は各カードの一次資料に記載しています。</p><p class="frontier-date">選定・資料確認：2026年10月25日（日本時間）</p><div class="frontier-policy-links"><a href="../#start">8ステップで学ぶ →</a><a href="../#explore">全115事例を探す →</a></div></div></section></main>')
    out.append(footer().replace('学習版 3.3 · 更新日 2026.10.07', 'フロンティア選定 · 確認日 2026.10.25')+'</body></html>')
    dest = root/'frontier'; dest.mkdir(exist_ok=True)
    (dest/'index.html').write_text(''.join(out))
    # Add one high-visibility entry, after the existing hero and before the eight steps.
    home = root/'index.html'; page = home.read_text()
    marker = '<div class="step-home-grid" id="start">'
    assert page.count(marker)==1
    shared_count = sum(bool(c.get('sharedLab')) for c in rows)
    teaser = f'<aside class="frontier-entry"><div><p class="eyebrow">WORLD FRONTIERS / 世界の先進事例</p><h2>ハード・ソフト・パートナーから、<br>面白い共創の仕組みを発見する。</h2><p>各事例で「活かせるステップ」と、その理由もわかる。</p><a class="frontier-entry-topic" href="frontier/?focus=shared-labs#frontier-explore">ARENA2036のような共用研究・試作拠点 {shared_count}件を読む →</a></div><a href="frontier/">3つの切り口から探す <span aria-hidden="true">↗</span></a></aside>'
    page = page.replace(marker, teaser+marker, 1)
    page = page.replace('</head>', f'<link rel="stylesheet" href="frontier.css?v={VERSION}"></head>', 1)
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
