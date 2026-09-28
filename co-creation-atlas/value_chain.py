"""Four-part, evidence-linked explanations of the atlas's existing cases."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HUMAN = [('self','自社・運営組織'),('companies','他社・事業会社'),('government','行政・公共機関'),('startups','スタートアップ'),('academia','アカデミア'),('citizens','市民・利用者・現場')]
CAPITAL = [('tangible','有形資産','場所・設備・実証環境'),('relational','関係資本','信頼・ネットワーク・導入先'),('financial','金融資本','活動資金・投資・費用負担'),('intellectual','知的資本・データ','技術・知財・知識・標準'),('issues','課題・ニーズ','誰の何を変えるのか')]
KINDS = {'fact':'公開資料で確認','self-report':'運営者・関係者の報告','analysis':'MDLの分析','unknown':'公開資料では未確認'}
STAGES = ['','課題を捉える','未来を問う','仲間をつくる','デジタルで試す','現物をつくる','現場で確かめる','事業にする','社会へ広げる']

def e(value):
    return html.escape(str(value if value is not None else ''), quote=True)

def read(data):
    source = ROOT/'data/value-chains.json'
    if not source.exists():
        raise FileNotFoundError('全事例の価値創造データが必要です: '+str(source))
    rows = json.loads(source.read_text())
    chains = {row['id']:row for row in rows}
    assert len(chains) == len(rows), 'Duplicate value-chain case id'
    assert set(chains) == {c['id'] for c in data}, 'Value chains must cover every existing case exactly once'
    for c in data:
        row = chains[c['id']]
        sources = {s['id']:s for s in c['sources']}
        for s in row['sources']:
            assert s['url'].startswith('https://'), s['id']
            sources[s['id']] = s
        c['sources'] = list(sources.values())
        assert set(row['inputs']['human']) == {key for key, _ in HUMAN}, c['id']
        assert {key for key, _, _ in CAPITAL} <= set(row['inputs']), c['id']
        def check(obj):
            if isinstance(obj, dict):
                if 'refs' in obj:
                    assert set(obj['refs']) <= set(sources), (c['id'],obj['refs'])
                    assert obj.get('kind') in KINDS, (c['id'],obj.get('kind'))
                    assert obj.get('text'), c['id']
                    assert obj['refs'] or obj.get('kind') == 'unknown', (c['id'],obj['text'])
                if 'steps' in obj:
                    assert obj['steps'] and set(obj['steps']) <= set(range(1,9)), c['id']
                for k,v in obj.items():
                    if k != 'sources':check(v)
            elif isinstance(obj,list):
                for v in obj:check(v)
        check(row)
        def text_values(obj):
            if isinstance(obj,dict):
                for k,v in obj.items():
                    if k not in ('sources','refs','id','kind','updated'):yield from text_values(v)
            elif isinstance(obj,list):
                for v in obj:yield from text_values(v)
            elif isinstance(obj,str):yield obj
        c['valueChainSearch'] = ' '.join(text_values(row))
    return chains

def block(item, tag='div', cls=''):
    refs = ''.join(f'<a href="#{e(sid)}" aria-label="出典 {e(sid)} の説明へ">出典 {i+1}</a>' for i,sid in enumerate(dict.fromkeys(item.get('refs',[]))))
    kind = item.get('kind','analysis')
    return f'<{tag} class="vc-block {e(cls)}"><p>{e(item["text"])}</p><div class="vc-evidence"><span class="vc-kind {e(kind)}">{KINDS[kind]}</span>{refs}</div></{tag}>'

def framework():
    return '''<section class="vc-framework" id="value-creation"><div class="vc-framework-heading"><p class="eyebrow">INPUT → FUNCTION → OUTPUT → OUTCOME</p><h2>社会実装までを、<br>4つの切り口で読む。</h2><p>誰の課題に、どんな資源を持ち込み、どう価値へ変えるか。<br>全28事例を同じ構造で読み解きます。</p></div><div class="vc-flow"><div><span class="vc-flow-no">I / INPUT</span><h3>インプット</h3><p>人・場所・関係・お金・知識・課題</p><small>何を持ち込むか</small></div><div class="vc-flow-function"><span class="vc-flow-no">II / FUNCTION</span><h3>価値創造機能</h3><p>資源をつなぎ、検証し、実装へ進める</p><small>既存の8ステップは、この中の工程</small></div><div><span class="vc-flow-no">III / OUTPUT</span><h3>アウトプット</h3><p>試作品・検証結果・契約・標準・事業</p><small>直接、何が生まれたか</small></div><div><span class="vc-flow-no">IV / OUTCOME</span><h3>アウトカム</h3><p>継続利用・行動変化・事業や暮らしの改善</p><small>利用した結果、何が変わったか</small></div></div><p class="vc-framework-note"><strong>社会実装から逆算：</strong>導入する人、支払う人、運用する人を確かめ、検証結果を次の課題と資源配分へ戻します。工程は必要に応じて行き来します。</p><div class="vc-framework-actions"><a class="vc-framework-link" href="learn/value-creation/">4つの切り口・インプットの分類を学ぶ →</a><a class="vc-framework-link" href="#explore">28事例の具体的な工夫を読む ↓</a></div></section>'''

def glance(row):
    parts = '<section class="vc-glance"><div><p class="eyebrow">VALUE CREATION / 価値が生まれる仕組み</p><h2>この事例を、4つの切り口で。</h2><p>'+e(row['summary'])+'</p></div><nav class="vc-jump" aria-label="価値創造の4つの切り口">'
    for num,slug,name,sub in [('I','inputs','インプット','人・資産・関係・資金・課題'),('II','functions','価値創造機能','8ステップのうち何を担うか'),('III','outputs','アウトプット','直接生まれたもの'),('IV','outcomes','アウトカム','確認できた変化・未確認の点')]:
        parts += f'<a href="#vc-{slug}"><b>{num}</b><span><strong>{name}</strong><small>{sub}</small></span><span aria-hidden="true">↓</span></a>'
    return parts+'</nav><div class="vc-case-links"><a href="#vc-project">具体的な実装事例を読む ↓</a><a href="#vc-backcast">社会実装から逆算した工夫へ ↓</a></div></section>'

def toc():
    return '<div class="vc-toc"><p class="toc-guide">価値が生まれる仕組み</p><a href="#vc-inputs">I インプット</a><a href="#vc-functions">II 価値創造機能</a><a href="#vc-outputs">III アウトプット</a><a href="#vc-outcomes">IV アウトカム</a><a href="#vc-project">具体的な実装事例</a><a href="#vc-backcast">社会実装から逆算する工夫</a></div>'

def case_sections(row):
    inputs = row['inputs']
    out = ['<section class="detail-section vc-section" id="vc-inputs"><p class="eyebrow">I / INPUT</p><h2>何を持ち込んでいるか。</h2><p class="vc-intro">活動の出発点となる資源と課題を分けて整理します。「自社」は、その場・制度を運営する組織を指します。</p><div class="vc-capital-title"><b>人的資本</b><span>誰が、どんな力と責任を持ち寄るか</span></div><dl class="vc-human">']
    for key,label in HUMAN:
        out.append('<div><dt>'+label+'</dt><dd>'+block(inputs['human'][key])+'</dd></div>')
    out.append('</dl><div class="vc-capitals">')
    for key,label,sub in CAPITAL:
        out.append(f'<section><div class="vc-capital-title"><h3>{label}</h3><span>{sub}</span></div>'+block(inputs[key])+'</section>')
    out.append('</div></section><section class="detail-section vc-section" id="vc-functions"><p class="eyebrow">II / VALUE CREATION FUNCTIONS</p><h2>資源を、どう価値へ変えるか。</h2><p class="vc-intro">以下は既存の8ステップへの編集上の対応づけです。各施設の公式な工程名や、全工程を自前で担うことを意味しません。</p><div class="vc-functions">')
    for n,item in enumerate(row['functions'],1):
        steps = ''.join(f'<a href="../../learn/step-{s:02d}/">{s:02d} {STAGES[s]}</a>' for s in item['steps'])
        out.append(f'<section><div class="vc-step-links">{steps}</div><h3>{e(item["title"])}</h3>'+block(item)+'</section>')
    out.append('</div></section>')
    for slug,num,name,title,desc in [('outputs','III','OUTPUT','直接、何が生まれたか。','試作品、データ、契約、標準、育成した人材など、活動から直接生まれたもの。'),('outcomes','IV','OUTCOME','その結果、何が変わったか。','実際の利用、行動、業務、事業、地域の変化。報告された変化と、施設の活動に帰属できる効果は区別します。')]:
        out.append(f'<section class="detail-section vc-section" id="vc-{slug}"><p class="eyebrow">{num} / {name}</p><h2>{title}</h2><p class="vc-intro">{desc}</p><ol class="vc-results">')
        for item in row[slug]:out.append(block(item,'li'))
        out.append('</ol>')
        if slug == 'outcomes':
            out.append('<aside class="vc-gaps"><h3>まだ確認できないこと</h3><ul>'+''.join(f'<li>{e(v)}</li>' for v in row['outcomeGaps'])+'</ul></aside>')
        out.append('</section>')
    project = row['project']
    out.append(f'<section class="detail-section vc-project" id="vc-project"><p class="eyebrow">PROJECT IN FOCUS / 具体的な事例</p><h2>{e(project["name"])}</h2><p class="vc-project-stage">確認できた段階：{e(project["stage"])} <span>調査確認日 {e(row["updated"])}</span></p>')
    for key,label in [('overview','誰の課題を、どう扱ったか'),('output','生まれたもの'),('outcome','確認できた変化')]:
        out.append(f'<div class="vc-project-part"><h3>{label}</h3>'+block(project[key])+'</div>')
    out.append(f'<p class="vc-project-gap"><strong>評価の限界：</strong>{e(project["gap"])}</p></section>')
    if row.get('relatedProjects'):
        out.append('<section class="detail-section" id="vc-related-projects"><p class="eyebrow">CONNECTED PRACTICE / 実際の関与を確認した取り組み</p><h2>個別案件から、地区・事業間のつながりへ。</h2><p>同じ組織が関与する別の取り組みを、事業期間と成果の単位を分けて読みます。記事数を増やすために重複掲載はしていません。</p>')
        for item in row['relatedProjects']:
            out.append('<h3>'+e(item['title'])+'</h3>'+block(item))
        if row.get('relatedProjectGaps'):
            out.append('<aside class="vc-gaps"><h3>期間・数値の読み方</h3><ul>'+''.join('<li>'+e(v)+'</li>' for v in row['relatedProjectGaps'])+'</ul></aside>')
        out.append('</section>')
    out.append('<section class="detail-section vc-backcast" id="vc-backcast"><p class="eyebrow">DESIGN BACKWARDS FROM IMPLEMENTATION</p><h2>社会実装から逆算して、<br>何を先に整えているか。</h2><p class="vc-intro">実証の先にある導入・運用・継続から、この事例の設計を読み解きます。原典で確認できる仕組みと、MDLの設計解釈・他地域へ応用するための提案を区別して読んでください。「提案」「未実施」と記す内容は、当地で実施済みの工夫ではありません。仕組みの存在と、全案件で成果が出たことも別に扱います。</p><div>')
    for n,item in enumerate(row['backcast'],1):
        out.append(f'<section><span class="vc-backcast-no">{n:02d}</span><div><h3>{e(item["title"])}</h3>'+block(item)+'</div></section>')
    out.append('</div></section><div class="vc-supporting"><p class="eyebrow">MORE DETAIL / 運営・根拠・応用</p><h2>運営の全体像と、学びを深める資料。</h2><p>費用負担、公表値、応用条件、写真・動画、原典を続けて確認できます。</p></div>')
    return ''.join(out)
