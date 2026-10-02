"""Source-backed curriculum and browser-local worksheets. Standard library only."""
import html
import json
import value_guide
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = 'https://mobilitydlab.com/co-creation-atlas/'
CATEGORIES = {'basics':'はじめての共創','town':'まちづくりの基礎','steps':'8工程の実践教材','operations':'運営・人材・お金','cases':'判断を追うケース教材','troubleshooting':'つまずきから学ぶ'}
UNITS = {'place':'施設・場所','organization':'運営組織','district':'地区・地域','program':'制度・プログラム','network':'ネットワーク'}
EXITS = {'purchase':'購入・導入','public-service':'公共サービス','local-operation':'地域での運営','education':'教育','research':'研究成果の利用','licensing':'ライセンス'}
LESSONS = []
SOURCES = {}
FIT = []

def e(value):
    return html.escape(str(value if value is not None else ''), quote=True)

def paras(values):
    if isinstance(values, str): values = [values]
    return ''.join(f'<p>{e(v)}</p>' for v in values)

def bullets(values):
    return '<ul>'+''.join(f'<li>{e(v)}</li>' for v in values)+'</ul>' if values else ''

def href(lesson_id, prefix='../'):
    return f'{prefix}{lesson_id}/'

def configure(data, stages, media, head, header, footer, photo):
    global DATA, STAGES, MEDIA, HEAD, HEADER, FOOTER, PHOTO, LESSONS, SOURCES, FIT
    DATA, STAGES, MEDIA, HEAD, HEADER, FOOTER, PHOTO = data, stages, media, head, header, footer, photo
    for name in ['foundations', 'practice', 'cases']:
        bundle = json.loads((ROOT/f'data/learning-{name}.json').read_text())
        LESSONS.extend(bundle['lessons'])
        for source in bundle['sources']:
            assert source['id'] not in SOURCES, source['id']
            SOURCES[source['id']] = source
    assert len({x['id'] for x in LESSONS}) == len(LESSONS)
    FIT = json.loads((ROOT/'data/learning-case-fit.json').read_text())
    if isinstance(FIT, dict): FIT = FIT.get('cases', FIT.get('items', []))
    known = {c['id'] for c in DATA}
    for lesson in LESSONS:
        assert set(lesson.get('relatedCases', [])) <= known, lesson['id']
        refs = lesson.get('sourceIds', []) + [sid for section in lesson['sections'] for sid in section.get('sourceIds', [])]
        assert set(refs) <= SOURCES.keys(), (lesson['id'], set(refs) - SOURCES.keys())
    assert {f['caseId'] for f in FIT} == known

def page_start(title, summary, slug='', display='', category='LEARNING ATLAS'):
    prefix = '../' if not slug else '../../'
    url = BASE+'learn/'+(slug+'/' if slug else '')
    crumb = '<a href="../">学びの入口</a> / '+e(title) if slug else '学びの入口'
    return [HEAD(title, summary, url, prefix), HEADER(prefix), f'<main id="main" class="learn-page"><div class="learn-crumb"><a href="{prefix}">ATLAS</a> / {crumb}</div><section class="learn-hero"><div><p class="eyebrow">{e(category)}</p><div class="display">{e(display or "LEARN. DESIGN. DO.")}</div><h1>{e(title)}</h1><p class="learn-summary">{e(summary)}</p></div><div class="learn-hero-note"><span class="display">READ.<br>TRY.<br>RETHINK.</span><p>知る。自分の案件で考える。<br>確かめて、また学び直す。</p><a href="{prefix}learn/workbook/">実践シートを開く ↗</a></div></section>']

def save_page(parts, slug=''):
    parts.append('</main>'+FOOTER()+'</body></html>')
    dest = ROOT/'learn'/slug
    dest.mkdir(parents=True, exist_ok=True)
    (dest/'index.html').write_text(''.join(parts))

def lesson_card(lesson, prefix='', compact=False):
    num = f'{lesson["step"]:02d}' if lesson.get('step') else CATEGORIES[lesson['category']]
    return f'<a class="learn-card {"compact" if compact else ""}" href="{href(lesson["id"],prefix)}"><span class="learn-card-kicker">{e(num)}</span><h3>{e(lesson["title"])}</h3><p>{e(lesson["summary"])}</p><span class="learn-card-foot">読む目安 {e(lesson.get("minutes",8))}分 · 演習は別途 <b>→</b></span></a>'

def entry():
    return '<div class="learn-entry"><div><p class="eyebrow">FIRST THINGS FIRST / はじめての共創</p><h2>3つの分野を、ひとつの見取り図に。</h2><p>リビングラボ、まちづくり、オープンイノベーション。違いと関係を知り、自分の課題に合う進め方を選ぶ。</p></div><a class="btn black" href="learn/first-co-creation/">基礎から学ぶ →</a><a class="learn-entry-more" href="learn/">教材の全体を見る ↗</a></div>'

def case_bridge(case):
    step = case['stage']
    traced = [l for l in LESSONS if l['category']=='cases' and case['id'] in l.get('relatedCases', [])]
    extra = ''.join(f'<a href="../../learn/{l["id"]}/">判断の変化を追う：{e(l["title"])} →</a>' for l in traced)
    return f'<section class="learn-bridge"><p class="eyebrow">FROM THIS CASE TO YOUR PROJECT</p><h2>読んだ事例を、自分の計画へ。</h2><div class="learn-bridge-links"><a href="../../learn/step-{step:02d}/"><b>01</b><span>この方法を学ぶ<small>{STAGES[step]}</small></span>→</a><a href="../../learn/step-{step:02d}/#worked-example"><b>02</b><span>記入例を見る<small>考え方を、具体的な形に</small></span>→</a><a href="../../learn/step-{step:02d}/#worksheet"><b>03</b><span>自分の案件で考える<small>シートに書き、判断を残す</small></span>→</a></div>{f"<div class=\"learn-traced-link\">{extra}</div>" if extra else ""}</section>'

def build_hub():
    out = page_start('世界の共創から、実践の方法を学ぶ。','基礎を理解する。事例を読み解く。自分の計画をつくる。8つの工程を行き来しながら、地域と事業のつくり方を考える学習アトラス。')
    out.append('<div class="learn-route"><a href="first-co-creation/"><span>初めて学ぶ</span><b>3分野の違いから →</b></a><a href="#eight-steps"><span>実務で使う</span><b>必要な工程と記入例へ ↓</b></a><a href="roles-and-work/"><span>責任者として考える</span><b>体制・仕事・財源へ →</b></a></div>')
    out.append('<div class="learn-fit-note"><p><strong>事例を読むための共通の軸：</strong>インプット → 価値創造機能 → アウトプット → アウトカム。<a href="value-creation/">4つの切り口と社会実装からの逆算を学ぶ →</a></p></div>')
    out.append('<section class="learn-overview"><p class="eyebrow">THREE LENSES / 3分野の関係</p><h2>同じ「共創」でも、見る問いが違う。</h2><div class="learn-three"><article><span>01 / LIVING LAB</span><h3>リビングラボ</h3><p>生活者と、暮らしの中で<br>何をつくり、どう確かめるか。</p></article><article><span>02 / PLACE & COMMUNITY</span><h3>まちづくり</h3><p>誰にとって、どんな地域にし、<br>誰が支え続けるか。</p></article><article><span>03 / OPEN INNOVATION</span><h3>オープンイノベーション</h3><p>何を自分で持ち、何を外部と<br>組み合わせ、価値につなげるか。</p></article></div><p class="learn-caption">MDLによる学習用の整理。互いに重なりますが、同義でも上下関係でもありません。<a href="first-co-creation/">定義・向き不向き・原典を読む →</a></p></section>')
    out.append('<section id="eight-steps"><div class="learn-section-head"><p class="eyebrow">START HERE / 8つの工程から選ぶ</p><h2>いま必要な工程から、手を動かす。</h2><p>順番どおりに進む必要はありません。デジタルを使わない、前の工程へ戻る、その地域で続ける選択もあります。</p></div><div class="learn-stage-grid">')
    for lesson in sorted([l for l in LESSONS if l['category']=='steps'], key=lambda l:l['step']): out.append(lesson_card(lesson))
    out.append('</div></section><div class="learn-workbook-banner"><div><p class="eyebrow">YOUR FIRST PROJECT PLAN</p><h2>まず、自分の案件を一枚に。</h2><p>課題・当事者・責任者・費用・検証・継続条件を、6つの欄に整理します。</p></div><a class="btn black" href="workbook/">計画シートを開く →</a></div>')
    summaries = {'basics':'用語の違い、適した課題、開くものと守るもの。','town':'土地・住民・日常の運営・地域経済・行政をつなぐ5つの教材。','operations':'誰が日々何を担い、その仕事をどの財源で支えるか。','cases':'途中で何を見て、どの判断を変えたか。公開資料から3案件を追います。','troubleshooting':'起きていることから、確認する情報と対処の選択肢を探します。'}
    for category in ['basics','town','operations','cases','troubleshooting']:
        out.append(f'<section id="{category}"><div class="learn-section-head"><p class="eyebrow">LEARNING COLLECTION</p><h2>{CATEGORIES[category]}</h2><p>{summaries[category]}</p></div><div class="learn-collection">')
        out.extend(lesson_card(l,compact=True) for l in LESSONS if l['category']==category)
        out.append('</div></section>')
    out.append('<div class="learn-route bottom"><a href="choose/"><span>条件から選ぶ</span><b>自分に近い事例を探す →</b></a><a href="library/"><span>原典から確かめる</span><b>読む順番のあるライブラリ →</b></a><a href="updates/"><span>更新・編集方針</span><b>確認できた範囲を読む →</b></a></div>')
    save_page(out)

def source_block(source):
    stages = ' / '.join(f'{i:02d} {STAGES[i]}' for i in source.get('steps', []))
    return f'<article class="learn-source" id="source-{e(source["id"])}"><p class="eyebrow">{e(source["publisher"])} · {e(source.get("year","日付記載なし"))}</p><h3><a href="{e(source["url"])}" target="_blank" rel="noopener noreferrer">{e(source["title"])} ↗</a></h3><p><strong>何が分かるか：</strong>{e(source["what"])}</p><p><strong>読み取れる範囲・限界：</strong>{e(source["limits"])}</p><p class="meta">確認箇所：{e(source.get("locator","本文"))}<br>関連工程：{e(stages)} · 確認日：2026-09-27</p></article>'

def cite(ids):
    return '<p class="learn-citations">根拠：'+ ' / '.join(f'<a href="#source-{e(sid)}">{e(SOURCES[sid]["publisher"])}・{e(SOURCES[sid].get("year","原典"))}</a>' for sid in ids)+'</p>' if ids else ''

def worked_example(lesson):
    exercise = lesson['exercise']
    rows = ''.join(f'<div><dt>{e(f["label"])}</dt><dd>{e(f["example"])}</dd></div>' for f in exercise['fields'])
    return f'<section class="learn-content-section learn-example" id="worked-example"><p class="eyebrow">WORKED EXAMPLE / 編集部による記入例</p><h2>どこまで書けばよいか、例でつかむ。</h2><p>以下は考え方を示す学習用の記入例です。実案件の実績・予算・合意を示すものではありません。</p><dl class="learn-example-fields">{rows}</dl></section>'

def worksheet(lesson):
    ex = lesson['exercise']
    fields = []
    for i, f in enumerate(ex['fields'], 1):
        fid = lesson['id']+'-'+f['key']
        fields.append(f'<div class="workbook-field"><label for="{e(fid)}"><b>{i:02d}</b> {e(f["label"])}</label><p id="hint-{e(fid)}">{e(f["hint"])}</p><textarea id="{e(fid)}" data-field="{e(f["key"])}" aria-describedby="hint-{e(fid)}" rows="5" maxlength="4000" placeholder="まだ分からないことは「未確認」と書き、誰に確かめるかを残してください。"></textarea><div class="workbook-print-value" aria-hidden="true"></div><details class="field-example"><summary>記入例を参考にする</summary><p>{e(f["example"])}</p></details></div>')
    checks = ''.join(f'<label><input type="checkbox" data-review="{i}"><span>{e(v)}</span></label>' for i,v in enumerate(ex.get('review',[])))
    return f'<section class="learn-content-section workbook" id="worksheet" data-workbook="{e(lesson["id"])}"><p class="eyebrow">YOUR WORKSHEET / 自分の案件で考える</p><h2>{e(ex["title"])}</h2><p>{e(ex["intro"])}</p><p class="workbook-storage">入力はこのブラウザに自動保存されます。ほかの端末への引き継ぎには「バックアップ」と「読み込み」を使ってください。共有する前に、個人情報や非公開情報が含まれていないか確認してください。</p><noscript><p>自動保存と書き出しにはJavaScriptが必要です。欄はそのまま記入・印刷できます。</p></noscript><label class="workbook-title-label">案件名<input type="text" data-project-title maxlength="150" placeholder="自分の案件に名前を付ける"></label><div class="workbook-status-line"><span data-save-state role="status">入力を待っています</span><span data-field-count>0 / {len(fields)}項目を記入</span></div><div class="workbook-fields">{"".join(fields)}</div><fieldset class="workbook-review"><legend>次の人に説明できるか、確かめる</legend>{checks}</fieldset><p class="meta">記入済みの数は進捗の目安です。内容の妥当性や、実行の準備が整ったことを判定するものではありません。</p><div class="workbook-actions"><button type="button" data-export="markdown">このシートを保存（文章） ↓</button><button type="button" data-print>このシートを印刷</button><button type="button" data-export="json">全シートをバックアップ ↓</button><label class="workbook-import">バックアップを読み込む<input type="file" accept="application/json,.json" data-import></label></div><p class="workbook-feedback" data-feedback role="status"></p></section>'

def workbook_metadata():
    return {l['id']:{'title':l['title'], 'fields':[{'key':f['key'],'label':f['label']} for f in l['exercise']['fields']], 'review':l['exercise'].get('review',[])} for l in LESSONS+[PROJECT]}

def workbook_script():
    return '<script>window.ATLAS_WORKBOOKS='+json.dumps(workbook_metadata(),ensure_ascii=False).replace('<','\\u003c')+';</script>'

def related_cases(ids):
    out = ['<div class="learn-related-cases">']
    for cid in ids:
        c = next(c for c in DATA if c['id']==cid)
        media = next((m for m in MEDIA if m['caseId']==cid), None)
        visual = PHOTO(media, cls='learn-case-photo',prefix='../../') if media else f'<div class="learn-case-type display">CASE {c["number"]}</div>'
        out.append(f'<article>{visual}<div class="learn-case-body"><p class="eyebrow">{e(c["country"])} / {e(c["city"])}</p><h3><a href="../../cases/{cid}/">{e(c["name"])} →</a></h3><p>{e(c["tagline"])}</p></div></article>')
    return ''.join(out)+'</div>'

def build_lesson(lesson):
    cat = CATEGORIES[lesson['category']]
    display = f'STEP {lesson["step"]:02d}.' if lesson.get('step') else {'basics':'THE BASICS.','town':'MAKE PLACES WORK.','operations':'KEEP IT RUNNING.','cases':'FOLLOW THE DECISION.','troubleshooting':'PAUSE. LOOK. ADAPT.'}[lesson['category']]
    out = page_start(lesson['title'],lesson['summary'],lesson['id'],display,cat+' / '+lesson.get('kicker',''))
    if lesson.get('step') or lesson['id'] == 'first-co-creation':
        out.append('<div class="learn-fit-note"><p><strong>8工程は、価値創造機能の中にあります。</strong>資源を持ち込み、働きかけ、直接の成果と利用者・地域の変化を分けて確かめます。<a href="../value-creation/">4つの切り口の読み方 →</a></p></div>')
    if lesson.get('step') == 7:
        out.append('<div class="learn-fit-note"><p><strong>まちづくり・地域運営での読み方：</strong>この工程の「事業にする」には、公共サービス・地域活動として続けることも含みます。商業化だけを出口にせず、利用者、費用負担者、運営者、意思決定者を分けて確認し、維持管理・引継ぎ・見直しの条件を決めます。</p></div>')
    out.append(f'<div class="learn-objectives"><div><p class="eyebrow">AFTER THIS LESSON</p><h2>読んだ後、できること。</h2><p class="meta">読む目安 {e(lesson.get("minutes",8))}分 / 演習の時間は含みません</p></div>{bullets(lesson["goals"])}</div>')
    if lesson.get('forWhom') or lesson.get('prerequisite'):
        out.append(f'<div class="learn-fit-note"><p><strong>こんな人へ：</strong>{e(lesson.get("forWhom","このテーマを自分の案件で考えたい方"))}<br><strong>読む前に：</strong>{e(lesson.get("prerequisite","自分が取り組む課題を一つ思い浮かべてください。"))}</p></div>')
    out.append('<div class="learn-layout"><aside class="learn-toc"><nav aria-label="この教材の目次"><p class="eyebrow">IN THIS LESSON</p>')
    out.extend(f'<a href="#content-{e(s["id"])}">{i:02d} {e(s["title"])}</a>' for i,s in enumerate(lesson['sections'],1))
    out.append('<a href="#worked-example">記入例を見る</a><a href="#worksheet">自分のシートに書く</a><a href="#decision">進む・戻る・止める</a><a href="#lesson-sources">原典を読む</a></nav></aside><article class="learn-article">')
    for i,s in enumerate(lesson['sections'],1):
        out.append(f'<section class="learn-content-section" id="content-{e(s["id"])}"><span class="learn-section-num display">{i:02d}</span><h2>{e(s["title"])}</h2>{paras(s.get("body",[]))}{bullets(s.get("bullets",[]))}')
        if s.get('table'):
            table = s['table']
            out.append('<div class="learn-table-wrap" tabindex="0" role="region" aria-label="'+e(s['title'])+'の表"><table><thead><tr>'+''.join(f'<th scope="col">{e(h)}</th>' for h in table['headers'])+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<{"th scope=\"row\"" if j==0 else "td"}>{e(cell)}</{"th" if j==0 else "td"}>' for j,cell in enumerate(row))+'</tr>' for row in table['rows'])+'</tbody></table></div>')
        out.append(cite(s.get('sourceIds',[]))+'</section>')
    out.append(worked_example(lesson)+worksheet(lesson))
    out.append('<section class="learn-content-section" id="decision"><p class="eyebrow">DECISION / 次に何をするか</p><h2>進む。変える。いったん止める。</h2><p>以下はMDLによる判断の手掛かりです。担当者と当事者で確認し、判断した日と理由をシートに残してください。</p><div class="learn-decisions">')
    for key,label in [('continue','進める条件'),('change','戻って、変える条件'),('stop','保留・停止する条件')]:
        value = lesson['decision'][key]
        out.append(f'<div><h3>{label}</h3>{bullets(value) if isinstance(value,list) else paras(value)}</div>')
    out.append('</div></section><section class="learn-content-section" id="related-learning"><p class="eyebrow">NEXT / 学びをつなぐ</p><h2>事例と、ほかの工程へ。</h2><div class="learn-step-links">')
    out.extend(f'<a href="../step-{s:02d}/">{s:02d} {STAGES[s]} →</a>' for s in lesson.get('relatedSteps',[]) if s!=lesson.get('step'))
    out.append('<a href="../workbook/">6項目の計画にまとめる →</a></div>'+related_cases(lesson.get('relatedCases',[]))+'</section>')
    ids = list(dict.fromkeys(lesson.get('sourceIds',[]) + [sid for s in lesson['sections'] for sid in s.get('sourceIds',[])]))
    out.append('<section class="learn-content-section" id="lesson-sources"><p class="eyebrow">SOURCES / 原典を読む</p><h2>根拠と、読み取れる範囲。</h2><p>定義・資料に書かれたことと、教材としての整理・演習を区別しています。記入例と判断基準はMDLによる学習用の提案です。</p>'+''.join(source_block(SOURCES[s]) for s in ids)+'<a class="btn" href="../library/">読む順番のあるライブラリへ →</a></section></article></div>')
    out.append(workbook_script())
    save_page(out,lesson['id'])

PROJECT = {'id':'project-plan','title':'自分の案件を一枚に整理する','exercise':{'title':'6つの欄から、計画を始める。','intro':'まずは分かるところから。未確認の点も残し、各工程の教材を使って具体化してください。記入例は架空の地域拠点の計画です。','fields':[
    {'key':'problem','label':'課題と当事者','hint':'誰の、どの場面の、何を変えたいか。観察した事実と推測を分ける。','example':'駅前の空き店舗を使いたいという案がある。高齢者の外出先が足りないという声は仮説。平日の過ごし方を本人に聞き、既存の場を調べる。'},
    {'key':'outcome','label':'変えたい状態と指標','hint':'誰にとっての改善か。現在の状態、確かめる期間、比較するものを記す。','example':'必要な人が徒歩圏で安心して相談できる。試行前の利用先・負担時間と、試行4週間の相談内容・再訪理由を比べる。人数だけで改善と判断しない。'},
    {'key':'owner','label':'責任者と仲間','hint':'課題の責任者、日々の担当、判断する人、不参加の当事者を挙げる。','example':'地域団体の担当者が試行の責任を持つ案。店舗所有者に使用範囲を確認し、清掃・鍵・苦情対応の担当時間を合意する。平日参加できない人にも別の聞き方を用意する。'},
    {'key':'money','label':'費用と負担する人','hint':'整備費、組織の経常費、試行費、導入後の運用費を分ける。金額が不明なら確認先を書く。','example':'試行の机・保険・人件費と、常設後の家賃・保守を別にする。費用額は未確認。責任者が見積もりを集め、試行前に負担上限と支払者を決める。'},
    {'key':'test','label':'試す方法と比較','hint':'どの仮説を、誰と、どんな条件で確かめるか。安全・同意・負担・限界も書く。','example':'週1回の相談窓口を4週間試す案。既存サービスを調べ、本人の同意のもと相談の前後を記録。氏名を集めず負担時間を記す。少人数の前後比較だけでは因果を断定できない。'},
    {'key':'decision','label':'継続・変更・停止の条件','hint':'判断する日と責任者、必要な根拠、止める条件、次の引き継ぎ先を決める。','example':'4週後に当事者・運営者・所有者で振り返る。継続の担当・財源・安全が確認できれば次期試行へ。負担過多なら日時を変更し、安全や同意を確保できなければ止める。'}
], 'review':['課題と当事者を、観察した事実から説明できる。','責任者と費用負担者に、合意した範囲を確認できる。','検証する方法と、継続・変更・停止の条件を説明できる。']}}

def build_workbook():
    out = page_start('自分の案件を、一枚に。','課題・当事者・責任者・費用・検証・継続条件を整理する実践シート。書いてみて足りない点が見つかったら、必要な工程に戻れます。','workbook','MAKE YOUR PLAN.')
    out.append(worksheet(PROJECT))
    out.append('<section class="learn-section-head"><p class="eyebrow">GO DEEPER / 計画を具体化する</p><h2>工程ごとのシートを使う。</h2><p>入力は工程ごとに保存されます。全シートのバックアップを一つのファイルにまとめられます。</p></section><div class="learn-stage-grid">')
    out.extend(lesson_card(l,'../') for l in LESSONS if l['category']=='steps')
    out.append('</div>'+workbook_script())
    save_page(out,'workbook')

def fit_fields(f):
    needs = bullets(f['needs'])
    return [('取り組む課題',paras(f['challenge'])),('対象の単位',paras(UNITS[f['unit']]+'：'+f['unitNote'])),('必要な条件',needs),('生活者の関わり方',paras(f['participation'])),('実装の出口',paras(' / '.join(EXITS[x] for x in f['exits']))+paras(f['exitNote'])),('確認できている段階',paras(f['confirmed'])),('未確認の点',bullets(f['unknowns']) if isinstance(f['unknowns'],list) else paras(f['unknowns']))]

def build_choose():
    out = page_start('有名な事例より、自分に近い事例。','場所の形だけで選ばず、課題、必要な条件、生活者の役割、継続の出口を比べる。全28事例を同じ問いで読みます。','choose','FIND YOUR FIT.')
    out.append('<div class="learn-fit-note"><p>必要な条件は、既存の一次資料からMDLが整理した設計上の論点です。予算や人員の未確認は「低コスト」「少人数で可能」と読み替えません。出口のタグには学習上の適用も含むため、各事例の説明で実績の範囲を確認してください。</p></div><div class="learn-fit-filters"><label>キーワード<input type="search" id="fit-search" placeholder="住民、調達、試作、教育…"></label><label>対象の単位<select id="fit-unit"><option value="">すべての単位</option>'+''.join(f'<option value="{k}">{v}</option>' for k,v in UNITS.items())+'</select></label><label>実装の出口<select id="fit-exit"><option value="">すべての出口</option>'+''.join(f'<option value="{k}">{v}</option>' for k,v in EXITS.items())+'</select></label></div><div class="learn-fit-toolbar"><p role="status" id="fit-count">28件の事例</p><label><input id="fit-selected-only" type="checkbox">選んだ事例だけ表示</label><button type="button" id="fit-reset">条件を解除</button></div><p class="learn-fit-empty" id="fit-empty" hidden>該当する事例がありません。条件を減らしてお試しください。</p><div class="learn-fit-grid">')
    for f in FIT:
        c = next(c for c in DATA if c['id']==f['caseId'])
        source_ids = {s['id'] for s in c['sources']}
        assert set(f['sourceIds']) <= source_ids, c['id']
        details = ''.join(f'<div><dt>{e(label)}</dt><dd>{value}</dd></div>' for label,value in fit_fields(f))
        searchable = json.dumps([c['name'],c['country'],c['city'],f],ensure_ascii=False)
        refs = ' / '.join(f'<a href="../../cases/{c["id"]}/#{e(sid)}">{e(sid)}</a>' for sid in f['sourceIds'])
        out.append(f'<article class="learn-fit-card" data-fit-id="{c["id"]}" data-unit="{f["unit"]}" data-exits="{e(" ".join(f["exits"]))}" data-search="{e(searchable)}"><div class="learn-fit-card-head"><p class="eyebrow">{e(c["country"])} / {e(c["city"])}</p><h2><a href="../../cases/{c["id"]}/">{e(c["name"])} →</a></h2><label><input type="checkbox" data-fit-select>比較に選ぶ</label></div><dl>{details}</dl><p class="learn-citations">根拠を確かめる：{refs}</p></article>')
    out.append('</div>')
    save_page(out,'choose')

def build_library():
    out = page_start('原典を、読む順番でつなぐ。','何を知るために読むか。どこまで読み取れるか。基礎、参加、設計、地域運営から入り、各教材の根拠へ進みます。','library','READ WITH A PURPOSE.')
    sequence = [('first-co-creation','01','3分野の違いをつかむ'),('participation','02','参加と判断の関係を考える'),('step-01','03','課題を捉え、試す設計へ'),('everyday-operations','04','地域の日常と運営を考える')]
    existing = {l['id'] for l in LESSONS}
    # Semantic category fallbacks preserve links if editorial lesson IDs change.
    sequence = [(sid if sid in existing else next(l['id'] for l in LESSONS if l['category']=='town'),n,t) for sid,n,t in sequence]
    out.append('<ol class="learn-reading-order">'+''.join(f'<li><span class="display">{n}</span><a href="../{sid}/">{t} →</a><p>教材で問いをつかみ、末尾の原典へ。</p></li>' for sid,n,t in sequence)+'</ol><div class="learn-section-head"><h2>目的から、資料を読む。</h2><p>同じURLの資料は一つにまとめています。制度・手法の原典と、効果や限界を検討する研究は役割を分けて読んでください。</p></div><div class="learn-library-grid">')
    grouped = {}
    for s in SOURCES.values(): grouped.setdefault(s['url'],[]).append(s)
    for sources in grouped.values():
        s = sources[0]
        ids = {x['id'] for x in sources}
        lessons = [l for l in LESSONS if ids.intersection(l.get('sourceIds',[]) + [sid for x in l['sections'] for sid in x.get('sourceIds',[])])]
        links = ''.join(f'<a href="../{l["id"]}/">{e(l["title"])} →</a>' for l in lessons[:5])
        related_lesson = next((l for l in lessons if l.get('forWhom')), {})
        audience = s.get('forWhom',related_lesson.get('forWhom','この資料を使う教材の読者・実務担当者'))
        prereq = s.get('prerequisite',related_lesson.get('prerequisite','「はじめての共創」で、扱う対象と問いを整理してから読む。'))
        out.append('<div class="learn-library-card">'+source_block(s)+f'<p><strong>誰向け：</strong>{e(audience)}</p><p><strong>読む前に：</strong>{e(prereq)}</p><div class="learn-source-lessons">{links}</div></div>')
    out.append('</div>')
    save_page(out,'library')

def build_updates():
    count = len({m['caseId'] for m in MEDIA})
    out = page_start('根拠と、更新を残す。','どこまで確かめたか。何を変えたか。未確認のことと、次に確かめることを明示します。','updates','KEEP LEARNING.')
    out.append('<section class="learn-content-section"><p class="eyebrow">2026.10.02 / TEN ADDITIONAL CASES</p><h2>交通・公共空間・地区運営の10事例を追加。</h2><p>のるーと塩尻、aspern Seestadt、Toronto King Street、柏の葉AEMS、Shenzhen Bus Group、Jakarta MRT/TOD、Atlanta WalkATL Oakland City、Kigali Nyandungu、Milan Piazze Aperte、Sidewalk Torontoを追加しました。</p><p>既存記事と同じ4つの切り口で、運営・資金・意思決定・維持管理と、確認できた成果・未確認点を整理しています。Sidewalk Torontoは撤退した構想として扱い、その後のQuayside事業と区別しています。導入、運用、計画、撤退を成功の単一尺度に並べていません。</p><p>各記事の出典確認日・写真の撮影時点は個別に記載しています。今回の追加は既存87記事の全主張を再検証したものではありません。</p><a class="btn" href="../../#explore">事例を探す →</a></section>')
    out.append('<section class="learn-content-section"><p class="eyebrow">2026.09.28 / EVIDENCE REVIEW</p><h2>主張と出典の対応を、点検しました。</h2><p>全事例の出典情報を点検し、主要な数値・現況を一次資料と照合しました。全文の独立検証は未完了です。</p><ul><li>オガール：別資料を指していたPDFを正しい内閣府・国土交通省資料へ差し替え。公共分の事業費と、2014年度の来訪・雇用の根拠を分けました。</li><li>Seoul Innovation Park：公開資料で確認できない終了後の引き継ぎを示唆する表現を修正しました。</li><li>写真：松本の所在地建物、日立の視察現場などを照合。対象地区や旧拠点の写真には、現在の施設・活動写真と誤認しない説明を付けました。</li></ul><p>各記事の冒頭から、出典の発行者・公表日・確認箇所・確認日へ移動できます。確認日は資料を確認した日であり、成果の発生日ではありません。写真は現況や効果を証明する資料として扱いません。</p><a class="btn" href="../../#sources">情報源と編集方針を見る →</a></section>')
    out.append(f'<section class="learn-content-section"><p class="eyebrow">2026.09.28 / TWO ENTRANCES, ONE ATLAS</p><h2>二つの入口、一つの事例基盤。</h2><p>「共創拠点・リビングラボ」と「まちづくり・地域運営」から、重複を除いた{len(DATA)}記事を探せます。両方の関心に応える記事には、二つの入口から到達できます。入口別の件数は重なりを含みます。</p><p>全記事をインプット・価値創造機能・アウトプット・アウトカムで整理。8ステップは価値創造機能の工程として扱い、公共サービス・地域活動として続ける形も読み取れるようにしました。</p><p>追加事例は公式資料をもとに、対象単位・確認時点・成果の範囲・未確認点を記載しています。施設の成果と地区全体の変化、実装実績と将来計画を区別します。記事間の参考比較は、実際の関与を示す関係と分けています。</p><p>写真には出典・撮影時点・利用条件を記載。施設・活動の写真と、入居建物・対象地区・過去の風景を区別し、写っていない設備や成果を写真から推定しません。</p><a class="btn" href="../../#explore">二つの入口から探す →</a></section>')
    out.append(f'<section class="learn-content-section"><p class="eyebrow">2026.09.28 / PHOTOGRAPHS</p><h2>すべての事例に、対象を知る写真を。</h2><p>施設の外観・館内、活動、対象地区や入居建物を、{count}事例・{len(MEDIA)}点の写真で紹介しています。一覧・地図・詳細ページから見られます。</p><p>撮影年、入居前・旧拠点の区別、写真に写る対象、出典と利用条件を併記。配信元が提供する埋め込み写真は、公式の表示方法と出典リンクで掲載しています。</p><a class="btn" href="../../#explore">写真から事例を探す →</a></section>')
    out.append(f'<section class="learn-content-section"><p class="eyebrow">2026.09.27 / LEARNING EDITION</p><h2>事例を読むサイトから、計画をつくる教材へ。</h2><ul><li>既存の28事例と8工程を維持し、{len(LESSONS)}の教材を追加。</li><li>3分野の基礎、まちづくり5テーマ、8工程の実践、運営・費用、3案件の判断経緯、つまずきの教材を掲載。</li><li>ブラウザに保存できる実践シートと、条件別の事例比較、読む順番のある原典ライブラリを追加。</li><li>施設・活動写真を14事例・30点に拡充。撮影時点・出典・利用条件を各写真に表示。</li></ul><h3>編集の約束</h3><p>定義と確認した事実、運営者の報告、MDLの解釈、架空の記入例、未実施の検証案を分けます。未公表の費用・人員・意思決定は推測で補いません。成果の観察と因果の確認、実証の継続と恒久的な土地利用の決定を区別します。</p><h3>学習への効果は、まだ未検証です。</h3><p>教材を読んだ人が、課題・当事者・責任者・費用負担・検証方法・継続条件を説明できるかを、今後の利用者テストで確かめる必要があります。シートの記入数や閲覧数を、学習効果の証明とは扱いません。</p><p>確認方法の案：教材を読む前と読んだ後に同じ案件の計画を書き、根拠・未確認点・判断条件を第三者が確認する。使えなかった箇所と戻った工程も記録し、教材を改訂する。この評価は未実施です。</p><a class="btn" href="../../#sources">事例の原典・写真の利用条件へ →</a></section>')
    save_page(out,'updates')

def build_all():
    guide = page_start('共創の価値を、4つの切り口で読む。','インプットの分類、8工程の位置づけ、成果と変化の違いを学び、社会実装の条件から計画を逆算します。','value-creation','FROM INPUT TO OUTCOME.')
    guide.append(value_guide.guide_content(len(DATA)))
    save_page(guide, 'value-creation')
    build_hub()
    for lesson in LESSONS: build_lesson(lesson)
    build_workbook()
    build_choose()
    build_library()
    build_updates()
    urls = [BASE] + [BASE+'cases/'+c['id']+'/' for c in DATA] + [BASE+'learn/'] + [BASE+'learn/'+slug+'/' for slug in [l['id'] for l in LESSONS]+['workbook','choose','library','updates','value-creation']]
    (ROOT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{e(url)}</loc><lastmod>2026-10-02</lastmod></url>' for url in urls)+'</urlset>')
    print(f'Built {len(LESSONS)} lessons, workbook, condition finder and source library.')
