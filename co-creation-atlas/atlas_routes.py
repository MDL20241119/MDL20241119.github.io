"""Two reader entrances, one case database and evidence-preserving comparisons."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LENSES = {'co':'共創拠点・リビングラボ', 'place':'まちづくり・地域運営'}
INTENTS = {'participation':'住民と一緒につくりたい', 'implementation':'実証で終わらせたくない', 'finance':'運営と財源を知りたい', 'evaluation':'成果の測り方を知りたい'}
FIELDS = {
    'co':[('conditions','参加条件'),('support','支援機能'),('operation','運営体制'),('adoption','実装への接続')],
    'place':[('area','対象地域'),('actors','当事者'),('change','変更内容'),('maintenance','維持管理'),('effect','確認された変化')],
    'cross':[('issue','誰の課題か'),('decision','誰が決めるか'),('payer','誰が払うか'),('operator','誰が続けるか'),('evidence','何が確認できたか')],
}

def e(v):
    return html.escape(str(v if v is not None else ''), quote=True)

def read(data):
    entries = json.loads((ROOT/'data/entries.json').read_text())
    entries = {**original_entries(data), **entries}
    assert set(entries) == {c['id'] for c in data}, 'Entrance metadata must cover every case'
    for c in data:
        a = entries[c['id']]
        assert a['lenses'] and set(a['lenses']) <= set(LENSES), c['id']
        assert set(a['intents']) <= set(INTENTS), c['id']
        assert set(a['status'].get('refs',[])) <= {s['id'] for s in c['sources']}, c['id']
        for lens in a['lenses']:
            assert a['rationale'].get(lens) and a['learning'].get(lens), c['id']
        for lens in [*a['lenses'],'cross']:
            assert all(a['comparison'].get(lens,{}).get(key) for key,_ in FIELDS[lens]), (c['id'],lens)
        c['entry'] = a
    return entries

def original_entries(data):
    """Summarise sourced legacy articles without inferring current operation."""
    fits = {x['caseId']:x for x in json.loads((ROOT/'data/learning-case-fit.json').read_text())}
    chains = {x['id']:x for x in json.loads((ROOT/'data/value-chains.json').read_text())}
    place_learning = {
        'openlab-stockholm':'公共施設の再整備へ、利用者調査と行政の課題をつなぐ。',
        'forum-virium-helsinki':'住民の生活課題を、小規模実証と市のサービスへつなぐ。',
        'punggol-digital-district':'地区のエネルギー・データ基盤を、長期の運用契約と一緒に設計する。',
        'project-plateau':'都市データを、自治体の現場業務や地域の意思決定に組み込む。',
        'newlab-brooklyn':'技術支援拠点を、街の充電・移動の検証へ接続する。',
        'michigan-central-newlab-detroit':'地区と共創施設の役割を分け、公共道路で技術を検証する。',
        'marineterrein-amsterdam':'実際に使われる地区で、公開空間と技術の運用条件を確かめる。',
        'test-in-tallinn':'都市側の窓口を用意し、現場・許認可・実証をつなぐ。',
        'doll-living-lab':'公共インフラを比較・検証し、自治体の導入判断に返す。',
    }
    units={'place':'施設・場所','organization':'運営組織','district':'地区・地域','program':'制度・プログラム','network':'ネットワーク'}
    original_ids={'mit-d-lab','openlab-stockholm','forum-virium-helsinki','ars-electronica-futurelab','cern-ideasquare','geidai-future-art','aalto-design-factory','microsoft-garage','station-f','digital-catapult','punggol-digital-district','project-plateau','arena2036','science-tokyo-robotics-innovation-center','newlab-brooklyn','massrobotics','robohouse','arm-robotics-manufacturing-hub','michigan-central-newlab-detroit','marineterrein-amsterdam','test-in-tallinn','doll-living-lab','bmw-startup-garage','volvo-campx','firstbuild','hvm-catapult','fraunhofer-ahead','manufacturing-usa'}
    def brief(s,n=230):
        return s if len(s)<=n else s[:n]+'…（詳細は本文）'
    result={}
    for c in data:
        if c['id'] not in original_ids:
            continue
        f=fits[c['id']];v=chains[c['id']]
        lenses=['co']+(['place'] if c['id'] in place_learning else [])
        cmp={'co':{'conditions':'設計上の条件：'+'／'.join(f['needs'][:2]),'support':'／'.join(x['title'] for x in v['functions']),'operation':c['operator'],'adoption':f['exitNote']},'cross':{'issue':f['challenge'],'decision':'主な運営主体：'+c['operator']+'。採択・本導入の決裁権限は、本文で確認できる個別案件の範囲に限る。','payer':brief(c['payer']),'operator':f['exitNote']+' 拠点の運営と導入先の維持責任は区別する。','evidence':brief(v['project']['outcome']['text'])}}
        if 'place' in lenses:
            cmp['place']={'area':c['country']+'・'+c['city']+'。'+f['unitNote'],'actors':f['participation'],'change':brief(v['project']['output']['text']),'maintenance':brief(v['inputs']['financial']['text'],180)+' 個別サービスの維持管理条件は本文と未確認点を参照。','effect':brief(v['project']['outcome']['text'])}
        result[c['id']]={'lenses':lenses,'rationale':{'co':f['unitNote']+' 支援機能と実装への接続に注目する。',**({'place':'地区・地域サービスに関わる実践を扱う。'+f['exitNote']} if 'place' in lenses else {})},'unit':units[f['unit']],'unitNote':f['unitNote'],'status':{'label':v['project']['stage']+'を確認','scope':'個別案件：'+v['project']['name'],'asOf':v['updated'],'refs':v['project']['overview']['refs']},'learning':{'co':c['tagline'],**({'place':place_learning[c['id']]} if 'place' in lenses else {})},'intents':['implementation','finance','evaluation']+(['participation'] if c['id'] in place_learning or c['id'] in ['mit-d-lab','geidai-future-art','firstbuild'] else []),'comparison':cmp,'related':[]}
    return result

def badges(c, prefix=''):
    return '<div class="atlas-badges">'+''.join(f'<a class="atlas-badge {lens}" href="{prefix}?lens={lens}#explore">{LENSES[lens]}</a>' for lens in c['entry']['lenses'])+'</div>'

def metadata(c):
    a=c['entry'];s=a['status']
    return f'<dl class="atlas-card-meta"><div><dt>対象単位</dt><dd>{e(a["unit"])}</dd></div><div><dt>状況</dt><dd>{e(s["label"])}<small>{e(s["scope"])} · {e(s["asOf"])}</small></dd></div></dl>'

def hero(data, media, photo):
    counts={k:sum(k in c['entry']['lenses'] for c in data) for k in LENSES}
    countries=len({c['country'] for c in data})
    out=[f'<section class="atlas-hero"><div><p class="eyebrow">MDL / WORLD CO-CREATION ATLAS</p><h1>世界の実践から、<br>共創とまちづくりを学ぶ。</h1><p>場を動かす仕組みから、暮らしを変える実践まで。<br>あなたの課題に合う事例を見つける。</p></div><div class="atlas-hero-index"><span class="display">ONE ATLAS.<br>TWO WAYS IN.</span><p>{len(data)}事例 · {countries}か国<br>共通の4つの切り口と、価値創造の8ステップ</p></div></section><section class="atlas-doors" id="entrances" aria-label="二つの入口">']
    specs=[('co','A','人が集まり、挑戦が進む場をつくる。','共創空間の運営、生活者との共創、試作・実証、企業や大学の事業化支援を学ぶ。','共創の事例を見る','aalto-class-2','人が試作し、学び合う場 / Aalto Design Factory'),('place','B','暮らしを変え、地域で続く仕組みをつくる。','公共空間、交通・生活拠点、地区再生、住民参加、地域の日常運営を学ぶ。','まちづくりの事例を見る','punggol-digital-district','人の暮らしと場所をつなぐ地区 / Punggol Digital District')]
    for key,num,title,desc,cta,asset,caption in specs:
        m=next(m for m in media if m['assetId']==asset)
        out.append(f'<article class="atlas-door {key}"><div class="atlas-door-photo">'+photo(m,cls='atlas-door-figure',loading='eager')+f'<span class="atlas-photo-label">{e(caption)}</span></div><div class="atlas-door-body"><p class="eyebrow">入口 {num} / {counts[key]}事例</p><h2>{LENSES[key]}</h2><h3>{title}</h3><p>{desc}</p><a class="btn black" href="?lens={key}#explore" data-lens-link="{key}">{cta} <span aria-hidden="true">→</span></a></div></article>')
    out.append('</section><section class="atlas-cross-search" aria-labelledby="cross-search-heading"><div><h2 id="cross-search-heading">課題・仕組みから横断して探す</h2><p>入口に迷ったら、知りたい問いから。両方の事例を一緒に探せます。</p></div><div class="atlas-intent-links">')
    out.extend(f'<a href="?intent={k}#explore" data-intent-link="{k}">{v} →</a>' for k,v in INTENTS.items())
    out.append('</div><p class="atlas-overlap-note">二つの入口は、排他的な分類ではありません。都市型リビングラボなどは、同じ記事に両方からたどり着けます。掲載件数には重なりがあります。</p></section>')
    return ''.join(out)

def explorer_controls():
    return '<div class="atlas-explorer-lenses" role="group" aria-label="読む入口"><button type="button" data-lens="co">共創拠点・リビングラボ</button><button type="button" data-lens="place">まちづくり・地域運営</button><button type="button" data-lens="">すべてを横断</button></div><div class="atlas-lens-intro"><div><h3 id="atlas-lens-title">二つの入口を横断して読む</h3><p id="atlas-lens-description">人・場・地域をつなぐ仕組みを、共通の検索で探します。</p></div><a id="atlas-compare-link" class="btn" href="learn/choose/?lens=cross">この切り口で比較する →</a></div><div class="atlas-intent-control"><label for="intent">課題・仕組み</label><select id="intent"><option value="">すべての問い</option>'+''.join(f'<option value="{k}">{v}</option>' for k,v in INTENTS.items())+'</select><p>分類・学びの焦点は、公開情報をもとにしたMDLの編集です。</p></div>'

def comparison_teaser():
    return '<div id="comparison" class="atlas-comparison-teaser"><p class="eyebrow">COMPARE / 同じ問いで比べる</p><h2>入口に合わせて、比べる中身を変える。</h2><div><a href="learn/choose/?lens=co"><strong>共創拠点・リビングラボ →</strong><span>参加条件・支援機能・運営体制・実装への接続</span></a><a href="learn/choose/?lens=place"><strong>まちづくり・地域運営 →</strong><span>対象地域・当事者・変更・維持管理・変化</span></a><a href="learn/choose/?lens=cross"><strong>領域を横断して比較 →</strong><span>誰の課題か・誰が決めるか・払うか・続けるか・何を確認したか</span></a></div></div>'

def reading_context(c):
    a=c['entry']
    out=[f'<section class="atlas-reading" id="reading-context" data-case-lenses="{e(" ".join(a["lenses"]))}">{badges(c,"../../")}{metadata(c)}<p class="atlas-unit-note">{e(a["unitNote"])}</p><div class="atlas-reading-modes" role="group" aria-label="この記事の読み方">']
    for lens in a['lenses']:
        out.append(f'<button type="button" data-reading-lens="{lens}">{LENSES[lens]}として読む</button>')
    out.append('</div>')
    for lens in a['lenses']:
        links=[('vc-inputs','人材・資産と参加者'),('vc-functions','共創・検証の運営'),('vc-backcast','実装を支える工夫')] if lens=='co' else [('vc-inputs','地域の課題・当事者'),('vc-project','空間・サービスへの反映'),('vc-outcomes','確認できた変化'),('vc-backcast','続ける主体・財源')]
        out.append(f'<div class="atlas-reading-panel" data-reading-panel="{lens}"><p class="eyebrow">最初に読むポイント</p><h2>{e(a["learning"][lens])}</h2><p>{e(a["rationale"][lens])}</p><nav aria-label="{LENSES[lens]}の読む順番">'+''.join(f'<a href="#{anchor}">{label} ↓</a>' for anchor,label in links)+'</nav></div>')
    out.append('<p class="atlas-reading-note">どちらの入口でも、本文と根拠は同じです。最初に読むポイントだけを切り替えます。</p></section>')
    return ''.join(out)

def related(c,data,chains):
    known={x['id']:x for x in data}
    out=['<section class="related atlas-related"><a class="back-to-cases" data-return-cases href="../../#explore">← 事例の一覧へ戻る</a><h2>地域の変化と、共創の仕組みをつなぐ。</h2>']
    if 'place' in c['entry']['lenses']:
        out.append('<div class="atlas-relationship actual"><span class="label">この記事で確認した活動</span><h3>この実践を支えた共創の仕組みを読む</h3><p>本記事の当事者・運営・価値創造機能へ戻り、誰が何を担ったかを確認します。</p><a href="#vc-functions">共創・運営の仕組みへ ↑</a></div>')
    out.append(f'<div class="atlas-relationship actual"><span class="label">出典付きの個別案件</span><h3>この拠点・仕組みから、実装された／検証中の事例を読む</h3><p>{e(chains[c["id"]]["project"]["name"])}</p><a href="#vc-project">実施内容と、確認できた段階へ ↑</a><small>実証段階の案件を、継続導入済みとは扱いません。</small></div>')
    links=c['entry'].get('related',[])
    links=[r for r in links if r['id'] in known and r['id']!=c['id']]
    if not links:
        others=[d for d in data if d['id']!=c['id']]
        others.sort(key=lambda d:(-len(set(d['entry']['intents'])&set(c['entry']['intents'])),-int(set(d['entry']['lenses'])!=set(c['entry']['lenses']))))
        links=[{'id':d['id'],'reason':'共通する課題・仕組みの扱い方を比較する。'} for d in others[:3]]
    out.append('<div class="atlas-editorial-relations"><p class="eyebrow">編集上の比較 / 実際の関与を示すものではありません</p><h3>別の事例と比べて、条件の違いを読む</h3><div>')
    for r in links[:3]:
        z=known[r['id']]
        out.append(f'<a href="../{z["id"]}/"><strong>{e(z["name"])}</strong><span>{e(r["reason"])}</span><small>{e(z["entry"]["unit"])} · {e(z["country"])}</small></a>')
    out.append('</div></div></section>')
    return ''.join(out)

def build_compare(data,head,header,footer):
    title='入口に合わせて、事例を比較する。'
    out=[head(title,'共創の支援機能、地域の日常運営、領域横断の責任と財源を、それぞれの問いで比較します。','https://mobilitydlab.com/co-creation-atlas/learn/choose/','../../'),header('../../'),'<main id="main" class="atlas-compare" data-atlas-compare><div class="detail-crumb"><a href="../../">ATLAS</a> / 比較する</div><section class="atlas-compare-head"><p class="eyebrow">COMPARE / 一つの事例基盤、三つの見方</p><h1>'+title+'</h1><p>事例の規模を順位づけせず、必要な機能と継続の条件を選びます。<br>共創もまちづくりも、インプット・価値創造機能・アウトプット・アウトカムを持ちます。</p></section><div class="atlas-explorer-lenses" role="group" aria-label="比較の切り口">']
    for lens,label in [*LENSES.items(),('cross','領域を横断して比較')]:
        out.append(f'<button type="button" data-compare-lens="{lens}">{label}</button>')
    out.append('</div><div class="atlas-compare-tools"><label>キーワード<input type="search" id="compare-search" placeholder="住民、運営、調達、事例名…"></label><label>対象単位<select id="compare-unit"><option value="">すべての単位</option>'+''.join(f'<option>{e(x)}</option>' for x in sorted({c['entry']['unit'] for c in data}))+'</select></label><label class="atlas-selected-toggle"><input type="checkbox" id="compare-selected-only">選んだ事例だけ表示</label><button id="compare-reset" type="button">選択・条件を解除</button></div><div class="atlas-compare-status"><p id="compare-count" role="status"></p><a href="../../#explore" data-compare-return>この入口の一覧へ戻る →</a></div><p class="atlas-compare-note">表示は公開資料の要約とMDLの比較整理です。未確認は「存在しない」ではありません。各記事で、原典・対象期間・実証と継続運用の違いを確認してください。</p><div class="atlas-compare-grid">')
    for c in data:
        a=c['entry']
        out.append(f'<article class="atlas-compare-card" data-compare-id="{e(c["id"])}" data-lenses="{e(" ".join(a["lenses"]))}" data-unit="{e(a["unit"])}" data-search="{e(json.dumps([c["name"],c["country"],c["city"],a],ensure_ascii=False))}"><div class="atlas-compare-card-title"><p class="eyebrow">{e(c["country"])} / {e(c["city"])}</p><h2><a href="../../cases/{c["id"]}/" data-compare-case>{e(c["name"])}</a></h2><label><input type="checkbox" data-compare-select>比較に選ぶ</label></div>{metadata(c)}')
        for lens in [*a['lenses'],'cross']:
            out.append(f'<dl class="atlas-compare-fields" data-compare-fields="{lens}">')
            for key,label in FIELDS[lens]:
                out.append(f'<div><dt>{label}</dt><dd>{e(a["comparison"][lens][key])}</dd></div>')
            out.append('</dl>')
        out.append(f'<a class="atlas-compare-detail" href="../../cases/{c["id"]}/#vc-inputs" data-compare-case>4つの切り口・原典で詳しく読む →</a></article>')
    out.append('</div><p id="compare-empty" class="empty" hidden>条件に合う事例がありません。条件を減らすか、選択を解除してください。</p></main>'+footer()+'</body></html>')
    dest=ROOT/'learn/choose/index.html';dest.write_text(''.join(out))

def shared_reading():
    return '''<details class="atlas-framework-guide"><summary>二つの入口で、4つの切り口をどう読むか ＋</summary><div class="table-wrap"><table><caption>見出しは共通、厚く読む内容は目的に合わせる。</caption><thead><tr><th>共通の切り口</th><th>共創拠点・リビングラボ</th><th>まちづくり・地域運営</th></tr></thead><tbody><tr><th>インプット</th><td>人材、専門性、設備、企業資産、参加者との関係、資金、課題</td><td>住民・事業者、土地・建物・道路、地域の関係、資金、生活課題</td></tr><tr><th>価値創造機能</th><td>課題探索、チーム形成、試作、実証、伴走、導入先への接続</td><td>現場把握、住民との構想、小規模実験、空間・サービスの改善、運営体制づくり</td></tr><tr><th>アウトプット</th><td>チーム、試作品、検証結果、契約、導入仕様</td><td>改修した空間、開始したサービス、運営組織、協定、運用ルール</td></tr><tr><th>アウトカム</th><td>継続導入、利用者の改善、人材の成長、次の共創、新しい事業</td><td>移動・利用・交流の変化、生活の改善、地域経済への影響、継続可能性</td></tr></tbody></table></div><p>共創を「プロセス」、まちづくりを「成果」と分けるものではありません。場・仕組み・領域は別の軸です。同じ事例を、読者の問いから読み解きます。</p></details>'''
