"""Source-linked urban thinkers and the specific cases they participated in."""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = 'https://mobilitydlab.com/co-creation-atlas/'


def e(value):
    return html.escape(str(value), quote=True)


def read():
    return json.loads((ROOT/'data/urban-thinkers.json').read_text())


def styles(head, prefix=''):
    return head.replace('</head>', f'<link rel="stylesheet" href="{prefix}experts.css?v=20261006.1"></head>')


def teaser():
    return '<aside class="expert-teaser"><div><p class="eyebrow">NEW / 9 THINKERS · 18 CASES</p><h2>都市の思想を、実際の仕事から学ぶ。</h2><p>市民運動、設計、助言、研究評価。9人が何を担い、どこまで変化を確かめたかを、原典とともに読みます。</p><p class="meta">件数は記事・調査の単位です。同じ都市や関連施策を含み、独立した事業数ではありません。</p></div><a class="btn yellow" href="learn/urban-thinkers/">9人と18事例を見る →</a></aside>'


def case_context(case):
    item = case.get('expertContext')
    if not item:
        return ''
    return ('<aside class="expert-context" aria-label="有識者の関与と原典">'
            f'<p class="eyebrow">THINKER & PRACTICE / 本人の関与</p><h2>{e(item["name"])}</h2>'
            f'<p><strong>{e(item["role"])}</strong></p><p>{e(item["scope"])}</p>'
            f'<a href="../../learn/urban-thinkers/#{e(item["personId"])}">考え方・本人の原文への入口を読む →</a></aside>')


def build(data, head, header, footer):
    people = read()
    known = {c['id']: c for c in data}
    out = [styles(head('9人の思想と18の実践', '都市・地域・モビリティの9人を、具体的な関与事例と原典から学ぶ。市民運動・設計・助言・研究評価を区別して読む。', BASE+'learn/urban-thinkers/', '../../'), '../../'), header('../../')]
    # This learning-page-only stylesheet leaves all other Atlas entrances unchanged.
    out[0] = out[0].replace('</head>', '<link rel="stylesheet" href="../../urban-thinkers-hero.css?v=20261010.1"></head>')
    media = json.loads((ROOT/'data/media.json').read_text())
    hero_photos = []
    for cid, city in [('nyc-public-realm-strategy', 'NEW YORK'), ('melbourne-places-for-people', 'MELBOURNE')]:
        image = next(m for m in media if m['caseId'] == cid and m.get('kind') != 'diagram')
        width, height = image['dimensions']
        hero_photos.append(
            f'<figure class="thinker-hero-photo"><a href="../../cases/{e(cid)}/" aria-label="{e(image["title"])}の事例を読む">'
            f'<img src="../../{e(image["local"])}" alt="{e(image["alt"])}" width="{width}" height="{height}" loading="eager">'
            f'<span class="thinker-city">{city}<span aria-hidden="true">↗</span></span></a>'
            f'<figcaption><span class="thinker-photo-credit">PHOTO: {e(image["credit"])}</span>'
            f'<details><summary>写真の出典・撮影時点・利用条件</summary><p>{e(image["caption"])}<br>'
            f'<a href="{e(image["sourceUrl"])}" target="_blank" rel="noopener noreferrer">掲載元 ↗</a> · '
            f'<a href="{e(image["licenseUrl"])}" target="_blank" rel="noopener noreferrer">{e(image["license"])} ↗</a><br>'
            f'{e(image["imageDate"])} · {e(image["changes"])}</p></details></figcaption></figure>')
    out.append('<main id="main" class="expert-main"><div class="detail-crumb"><a href="../../">ATLAS</a> / 9人の思想と実践</div>'
               '<section class="expert-hero thinker-hero" aria-labelledby="thinker-title"><div class="thinker-hero-top">'
               '<div><p class="eyebrow">URBAN THINKERS / FROM IDEAS TO PRACTICE</p><h1 id="thinker-title">いい街は、<br><span>何が違う？</span></h1></div>'
               '<div class="thinker-hero-invite"><p>思想を知る。<br>実践を読み解く。</p><a class="thinker-start" href="#thinker-index">9人の視点を見に行く <span aria-hidden="true">→</span></a>'
               '<p class="thinker-english">READ THE CITY. CHECK THE WORK.</p></div></div>'
               '<p class="thinker-hero-strap">まちづくりの大家 <strong>9人 × 18の実践</strong></p>'
               '<div class="thinker-hero-photos">'+''.join(hero_photos)+'</div></section>'
               '<div class="thinker-intro"><p class="thinker-intro-title">9人の思想と、18の実践。</p><p>まちをどう捉え、誰と何を変え、どこまで確かめたのか。<br>本人の仕事を、4つの切り口と8工程につないで読みます。</p>'
               '<p class="note-inline">2026年10月6日確認。思想の要約はMDLの編集です。件数は記事・調査単位で、独立した事業数ではありません。研究や提言を施設運営の実績とは扱いません。本人の原文、自治体の報告、書誌・紹介を区別しています。</p></div>')
    out.append('<nav id="thinker-index" class="expert-nav" aria-label="9人の索引">'+''.join(f'<a href="#{e(p["id"])}">{e(p["name"])}</a>' for p in people)+'</nav>')
    for num, p in enumerate(people, 1):
        out.append(f'<section class="expert-person" id="{e(p["id"])}"><div class="expert-person-heading"><p class="eyebrow">{num:02d} / {e(p["en"])}</p><h2>{e(p["name"])}</h2><p class="expert-key">{e(p["key"])}</p><p>{e(p["idea"])}</p></div><div class="expert-work-grid">')
        for cid in p['caseIds']:
            case = known[cid]
            visual=''
            if case.get('image') and case.get('imageKind')!='diagram':
                visual=f'<a class="expert-work-photo" href="../../cases/{e(cid)}/"><img src="../../{e(case["image"])}" alt="{e(case["imageAlt"])}" width="800" height="500" loading="lazy"></a><p class="expert-photo-credit">PHOTO: {e(case["imageCredit"])} · 写真 {case.get("photoCount",1)}枚</p>'
            out.append(f'<article>{visual}<p class="eyebrow">{e(case["country"])} / {e(case["entry"]["unit"])}</p><h3><a href="../../cases/{e(cid)}/">{e(case["nameJa"])}</a></h3><p class="expert-role">{e(case["expertContext"]["role"])}</p><p>{e(case["tagline"])}</p><a href="../../cases/{e(cid)}/">仕組み・成果・限界を読む →</a></article>')
        out.append('</div><div class="expert-reading"><h3>本人の考え方・原資料へ</h3><p>リンク先の公開範囲を表示しています。書籍紹介や要旨は、原著全文ではありません。</p><ul>')
        for source in p['reading']:
            out.append(f'<li><a href="{e(source["url"])}" target="_blank" rel="noopener noreferrer">{e(source["title"])} ↗</a><span>{e(source["accessNote"])}</span></li>')
        out.append('</ul></div></section>')
    out.append('<aside class="expert-note"><h2>別の地域で使うときは、条件から。</h2><p>同じ手法を移す前に、対象者・意思決定権・財源・運営責任・負担を確認します。研究対象と比較方法が違う数値を成功順位にせず、試す前に継続・修正・停止の条件を決めます。各記事の検証案は未実施の提案です。</p><a href="../choose/">同じ問いで事例を比較する →</a></aside></main>'+footer()+'</body></html>')
    dest = ROOT/'learn/urban-thinkers'
    dest.mkdir(parents=True, exist_ok=True)
    (dest/'index.html').write_text(''.join(out))
    sitemap = ROOT/'sitemap.xml'
    text = sitemap.read_text()
    url = BASE+'learn/urban-thinkers/'
    if url not in text:
        text = text.replace('</urlset>', f'<url><loc>{url}</loc><lastmod>2026-10-06</lastmod></url></urlset>')
    text = text.replace(f'<loc>{BASE}</loc><lastmod>2026-10-02</lastmod>', f'<loc>{BASE}</loc><lastmod>2026-10-06</lastmod>')
    text = re.sub(r'(<loc>'+re.escape(BASE)+r'learn/[^<]*</loc><lastmod>)2026-10-02', r'\g<1>2026-10-06', text)
    expert_ids={c['id'] for c in data if c.get('expertContext')}
    for case in data:
        if case.get('expertContext') or any(r['id'] in expert_ids for r in case['entry'].get('related',[])):
            text = text.replace(f'<loc>{BASE}cases/{case["id"]}/</loc><lastmod>2026-10-02</lastmod>', f'<loc>{BASE}cases/{case["id"]}/</loc><lastmod>2026-10-06</lastmod>')
    sitemap.write_text(text)
