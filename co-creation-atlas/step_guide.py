"""Eight-step reader guide; existing research and worksheets remain intact."""
import html
import json
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parent
AXES = {}
AXIS_LABELS = [('hard','ハード','空間・設備・フィールド'),('soft','ソフト','運営・プログラム'),('partners','パートナー','連携相手・役割')]

def e(v): return html.escape(str(v), quote=True)

def read(data):
    steps=json.loads((ROOT/'data/step-guide.json').read_text())
    known={c['id']:c for c in data}
    assert [s['step'] for s in steps]==list(range(1,9))
    for s in steps:
        assert len(s['cases']) in (2,3)
        for item in s['cases']:
            assert item['id'] in known
            assert set(item['refs']) <= {x['id'] for x in known[item['id']]['sources']}
    return steps,known

def assets(page,prefix):
    return page.replace('</head>',f'<link rel="stylesheet" href="{prefix}step-guide.css?v=20261023.1"></head>',1)

def nav(steps,prefix,current=0):
    return '<nav class="step-switch" aria-label="8ステップ">'+''.join(f'<a href="{prefix}learn/step-{s["step"]:02d}/"'+(' aria-current="page"' if current==s['step'] else '')+f'><b>{s["step"]:02d}</b><span>{e(s["title"])}</span></a>' for s in steps)+'</nav>'

def home(steps,known):
    out=['<section class="step-home" id="entrances"><div class="step-home-heading"><div><p class="eyebrow">WORLD CO-CREATION ATLAS</p><h1>共創の進め方を、<br>世界の事例でつかむ。</h1><p>課題を見つけ、試し、社会へ届ける。<br>8つのステップから、知りたい実践へ。</p></div><div class="step-home-mark" aria-hidden="true"><span>WORLD PRACTICES</span><b>08</b><span>STEPS TO CO-CREATE</span></div></div><div class="step-home-grid" id="start">']
    for s in steps:
        i=s['step']
        out.append(f'<a class="step-home-card" href="learn/step-{i:02d}/"><span class="step-card-num">{i:02d}</span><div><h2>{e(s["title"])}</h2><p>{e(s["purpose"])}</p><span class="step-card-cases">'+ ' / '.join(e(known[c['id']].get('shortName',known[c['id']]['name'])) for c in s['cases'])+'</span><strong class="step-card-link">世界の実践を見る →</strong></div></a>')
    out.append('</div><div class="step-home-links"><a href="#explore">全115事例を探す ↓</a><a href="learn/">教材を読む →</a><a href="learn/choose/">事例を比べる →</a></div></section>')
    return ''.join(out)

def axis_block(cid, detailed=False):
    row=AXES[cid]
    out=['<dl class="facility-axes'+(' detailed' if detailed else '')+'">']
    for key,label,subtitle in AXIS_LABELS:
        out.append(f'<div><dt>{label}<small>{subtitle}</small></dt><dd>{e(row[key]["text"])}</dd></div>')
    return ''.join(out)+'</dl>'

def axis_sources(cid,known):
    sources={s['id']:s for s in known[cid]['sources']}
    return '<details class="axes-sources"><summary>3つの切り口の出典</summary>'+''.join('<p><strong>'+label+'</strong>：'+ ' / '.join(f'<a href="#{e(ref)}">{e(sources[ref]["title"])}</a>' for ref in AXES[cid][key]['refs'])+'</p>' for key,label,_ in AXIS_LABELS)+'</details>'

def case_card(item,known,media):
    c=known[item['id']]
    m=next((m for m in media if m['caseId']==c['id'] and m.get('kind')!='diagram'),None)
    categories={'co':'共創拠点・リビングラボ','place':'まちづくり・地域運営'}
    badges='<div class="step-case-badges">'+''.join('<span>'+categories[k]+'</span>' for k in c.get('entry',{}).get('lenses',[]))+'</div>'
    image=''
    if m:
        src=m.get('remote') or '../../'+m['local']
        rights=(m.get('licenseUrl') if m.get('status')=='cleared-cc' else m.get('rightsUrl')) or m.get('rightsUrl') or m.get('licenseUrl') or m['sourceUrl']
        no_crop=m.get('noCrop') or m.get('status')=='cleared-editorial-only'
        label=m.get('scopeLabel') or m.get('caption','')
        image=f'<figure class="step-case-photo'+(' no-crop' if no_crop else '')+f'"><img src="{e(src)}" alt="{e(m["alt"])}" width="900" height="540" loading="lazy"><figcaption>{e(label)}<br>Photo: {e(m["credit"])} · <a href="{e(m["sourceUrl"])}">掲載元</a> · <a href="{e(rights)}">{e(m["license"])}</a></figcaption></figure>'
    return f'<article class="step-case" data-case-id="{e(c["id"])}"><div class="step-case-title">{badges}<p class="eyebrow">{e(c["country"])} / {e(c["city"])}</p><h3>{e(c["name"])}</h3></div>{image}<div class="step-case-copy"><h4>何をしている？</h4><p>{e(item["action"])}</p>{axis_block(c['id'])}<div class="step-case-learning"><h4>学べること</h4><p>{e(item["learning"])}</p></div><a class="step-case-more" href="../../cases/{e(c["id"])}/">詳しい取組・出典を見る →</a></div></article>'

def update(root,data,stages,media):
    global AXES
    AXES=json.loads((ROOT/'data/facility-axes.json').read_text())
    steps,known=read(data)
    assert set(AXES)==set(known)
    for cid,row in AXES.items():
        for key,_,_ in AXIS_LABELS:
            assert row[key]['text'] and row[key]['refs']
            assert set(row[key]['refs']) <= {x['id'] for x in known[cid]['sources']}
    p=root/'index.html';page=p.read_text()
    # Keep existing sections, IDs and query-driven explorer, but not as competing entrances.
    start=page.index('<main id="main">')+len('<main id="main">')
    explorer=page.index('<section class="explorer"')
    supplements=''.join(re.findall(r'<aside class="(?:city-growth-feature|expert-teaser)".*?</aside>',page[start:explorer],re.S))
    page=page[:start]+home(steps,known)+page[explorer:]
    # Old learning summaries repeat the same eight steps; retain them in a folded reference area.
    marker='<section class="learn-entry"'
    pos=page.find(marker)
    if pos<0:
        # The first section after the complete explorer is the learning entry.
        pos=page.find('<section class="learning-entry"')
    # Remove the duplicate start ID, while keeping legacy chapters and analysis addressable.
    page=page.replace('<section id="start" class="start-guide">','<section id="legacy-start" class="start-guide">')
    # The top-level learning block starts directly after the explorer.
    match=re.search(r'<(?:section|div)[^>]+(?:class="learn-entry|id="learning")',page)
    if match: pos=match.start()
    if pos>=0:
        page=page[:pos]+'<details class="step-reference"><summary>学習ガイド・横断分析・原典</summary>'+supplements+page[pos:]
        page=page.replace('</main>','</details></main>',1)
    def catalog_axes(match):
        block=match.group(0);cid=match.group(1)
        block=re.sub(r'<dl class="atlas-card-meta">.*?</dl>', '',block,flags=re.S)
        return re.sub(r'<p class="card-summary">.*?</p>',axis_block(cid),block,flags=re.S)
    page=re.sub(r'<article class="case-card" data-id="([^"]+)".*?</article>',catalog_axes,page,flags=re.S)
    page=assets(page,'')
    page=page.replace('<title>世界の実践から、共創とまちづくりを学ぶ。','<title>共創の8ステップを、世界の事例で学ぶ。')
    p.write_text(page)
    for s in steps:
        i=s['step'];p=root/f'learn/step-{i:02d}/index.html';page=p.read_text()
        # Replace only the lesson opening; keep all original lesson anchors, fields and scripts.
        start=page.index('<main id="main"');end=page.index('<div class="learn-fit-note"',start)
        opening=f'<main id="main" class="step-page"><div class="step-breadcrumb"><a href="../../#start">8ステップの全体像</a><span> / STEP {i:02d}</span></div>'+nav(steps,'../../',i)+f'<section class="step-hero"><span class="step-hero-number">{i:02d}</span><div><p class="eyebrow">STEP {i:02d}</p><h1>{e(s["title"])}</h1><p>{e(s["purpose"])}</p></div></section><section class="step-world"><div class="step-world-heading"><h2>世界では、こう進める。</h2><a href="../../?stage={i}#explore">この工程の全事例 →</a></div><div class="step-case-grid">'+''.join(case_card(c,known,media) for c in s['cases'])+'</div></section><nav class="step-next" aria-label="前後のステップ">'
        if i>1: opening+=f'<a href="../step-{i-1:02d}/">← {i-1:02d} {e(steps[i-2]["title"])}</a>'
        else: opening+='<a href="../../#start">← 8ステップの全体像</a>'
        if i<8: opening+=f'<a href="../step-{i+1:02d}/">{i+1:02d} {e(steps[i]["title"])} →</a>'
        else: opening+='<a href="../../#start">8ステップの全体像 →</a>'
        featured={x['id'] for x in s['cases']}
        more=[c for c in data if i in c.get('stages',[c['stage']]) and c['id'] not in featured]
        more.sort(key=lambda c: 'co' not in c.get('entry',{}).get('lenses',[]))
        if more:
            extra='<details class="step-more"><summary><span class="step-more-plus" aria-hidden="true">＋</span> ほかの事例を見る <span class="step-more-count">'+str(len(more))+'事例</span></summary><div class="step-case-grid">'+''.join(case_card({'id':c['id'],'action':c['lead'],'learning':c['tagline']},known,media) for c in more)+'</div></details>'
            opening=opening.replace('</div></section><nav class="step-next"', '</div>'+extra+'</section><nav class="step-next"',1)
        opening+='</nav><details class="step-reference"><summary>実践教材・記入シートを開く</summary><div class="learn-page">'
        page=page[:start]+opening+page[end:]
        page=page.replace('</main>','</div></details></main>',1)
        page=assets(page,'../../')
        p.write_text(page)

    for cid in known:
        p=root/'cases'/cid/'index.html';page=p.read_text()
        hero=page.index('<section class="detail-hero"')
        end=page.index('</section>',hero)+len('</section>')
        block='<section class="facility-overview" id="facility-overview"><div class="facility-overview-heading"><h2>ハード・ソフト・パートナー</h2></div>'+axis_block(cid,True)+axis_sources(cid,known)+'</section>'
        page=page[:end]+block+page[end:]
        p.write_text(assets(page,'../../'))
