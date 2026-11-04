#!/usr/bin/env python3
"""Build six source-linked regional analyses. No network access; inputs committed beside pages."""
from pathlib import Path
import json,csv,io,re,html,sys
from regions import REGIONS
from deepening import DETAILS
from coverage import get_coverage, ROADS, ROAD_PAGES
ROOT=Path(__file__).resolve().parents[2]
DATA=Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'co-creation-atlas'
E=html.escape
ASSET='/co-creation-atlas/regional-mobility-assets/'
GATE='''<link rel="stylesheet" href="/oita-mirai-mobility-consortium/entry.css?v=20261009-password1"><script defer src="/oita-mirai-mobility-consortium/entry-crypto.js?v=20261009-password1"></script><script defer src="/oita-mirai-mobility-consortium/entry.js?v=20261101-session1"></script>'''
PLANS=[('国の観光','観光立国推進基本計画','2026年3月27日閣議決定・2026–2030年度','観光と交通・まちづくりの連携、誘客と住民生活の両立を掲げます。全国目標を各地域の需要予測へ移植しません。','https://www.mlit.go.jp/kankocho/seisaku_seido/kihonkeikaku.html'),('国の交通','第3次交通政策基本計画','2026年1月16日閣議決定・2025–2030年度','交通ネットワークと地域の移動を持続させる枠組み。地域の車種・路線・運行開始を決めた資料ではありません。','https://www.mlit.go.jp/sogoseisaku/transport/sosei_transport_tk_000257.html'),('県の観光','おおいたツーリズム戦略 第5期','2025–2027年度','来訪者だけでなく住民・事業者を含めた持続性、交通接続を扱います。県統計と市町の集計の対象差を保持します。','https://www.pref.oita.jp/soshiki/14180/tu-rizumusenryaku2025.html'),('県の交通','おおいた地域交通ビジョン2026','2026年10月–2031年9月','2026年9月までの旧圏域計画から更新。方面別路線バス指標は複数自治体をまたぐため、市町別の人数へ按分しません。','https://www.pref.oita.jp/soshiki/10540/chiikikotsuvision.html')]
COMMON_SOURCES=[('大分県2025年観光統計・確報','https://www.pref.oita.jp/uploaded/attachment/2273969.pdf','2026年8月公表。従業員10人以上192施設の調査。対象地域は「その他市町村」合計に含まれ、各市町に按分不可。'),('県交通ビジョン2026 資料編','https://www.pref.oita.jp/uploaded/attachment/2276664.pdf','2024年度事業者報告の方面別分析。輸送量・平均乗車密度を年間延べ人数に変換しない。')]
def a(url,label,cls=''):return f'<a class="{cls}" href="{E(url,quote=True)}">{E(label)} ↗</a>'
def panel(title,text,status=''):return f'<article class="panel">'+(f'<span class="status">{E(status)}</span>' if status else '')+f'<h3>{E(title)}</h3><p class="micro">{E(text)}</p></article>'
def chapter(n,id,title,kicker,content):return f'<section class="chapter" id="{id}" aria-labelledby="{id}-title"><div class="section-head"><span class="section-no" aria-hidden="true">{n:02}</span><div><p class="kicker">{kicker}</p><h2 id="{id}-title">{title}</h2></div></div>{content}</section>'
def chart(c):
 rows=''.join(f'<div><div class="bar-top"><span>{E(label)}</span><b>{E(value)}</b></div><div class="bar-track" aria-hidden="true"><div class="bar-fill" style="--value:{val/c["maximum"]*100:.3f}%"></div></div></div>' for label,val,value in c['rows'])
 return f'<article class="panel"><h3>{E(c["title"])}</h3><p class="micro">{E(c["subtitle"])}</p><p class="micro">目盛：0–{c["maximum"]:,}{E(c["unit"])}</p><div class="bars">{rows}</div><p class="chart-note">{E(c["note"])}</p>{a(c["source"],c["page"],"source-link")}</article>'
def recordtable(records,caption):
 rows=[]
 for r in records:
  rows.append(f'<tr id="record-{E(r["id"])}"><th scope="row">{E(r["label"])}<br><small>{E(r["id"])}</small></th><td><span class="status">{E(r["type"])}</span><br>{E(r["value"])}<br><span class="micro">{E(r["period"])}</span></td><td>{E(r["definition"])}<p class="micro">注意：{E(r["caution"])}</p></td><td>{a(r["url"],r["source"])}<br><span class="micro">{E(r["page"])}</span></td></tr>')
 return f'<div class="table-scroll" tabindex="0" role="region" aria-label="{E(caption)}"><table class="data-table"><caption>{E(caption)}</caption><thead><tr><th scope="col">指標・事項</th><th scope="col">値・年・区分</th><th scope="col">対象と注意</th><th scope="col">原典</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'
def header(title,description,styles=True):return f'<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow,noarchive"><meta name="referrer" content="no-referrer"><meta name="theme-color" content="#080d10"><title>{E(title)}</title><meta name="description" content="{E(description,quote=True)}">{GATE if not styles else ''}'+(f'<link rel="stylesheet" href="{ASSET}style.css"><link rel="stylesheet" href="{ASSET}regional.css"><script defer src="{ASSET}app.js"></script>' if styles else '')+'</head>'
def build(slug,d):
 hub=d.get('hub',slug); dest=ROOT/'co-creation-atlas'/f'{slug}-mobility'; dest.mkdir(parents=True,exist_ok=True); (dest/'downloads').mkdir(exist_ok=True)
 src=DATA/f'{slug}_evidence.json' if DATA.name!='co-creation-atlas' else dest/'downloads'/'evidence.json'
 inp=json.loads(src.read_text()); records=inp['records'];
 for r in records:
  if r['id']=='SG074':
   r.update(source='MDL 大分市の共創提案（検討用ドラフト）',url='https://mobilitydlab.com/oita-mirai-mobility-consortium/dialogue/oita.html',page='暮らしの往復デスク／交通政策と現行施策',definition='大分市全域の提言。佐賀関の参考風景と、大南・野津原の実証をそれぞれ扱う。')
  if r['id']=='SG075':r['caution']='県計画の期間。大分市計画期間とは別。'
  for key in ['definition','caution','page']:
   for code,title in {'H1':'町交通計画','H2':'町行政評価','H5':'第6次町総合計画','K1':'市交通計画','K2':'市行政評価','T1':'市交通計画','T3':'市総合計画','US-T1':'市交通計画','US-T2':'市交通施策評価','US-K1':'市観光戦略','US-K2':'市観光動態調査','US-K3':'市観光施策評価'}.items():
    r[key]=re.sub(r'(?<![A-Z-])'+re.escape(code)+r'(?![A-Z0-9-])',title,r[key])
   r[key]=r[key].replace('、後記','').replace('・後記','').replace('。親レビューで原本・公式入口確認。','。')
 for r in records:
  for k in ['definition','caution','page']:
   r[k]=(r[k] or '対象・期間は同じ行の定義に従う。').replace('親調査確認済み','原本の方面別集計').replace('既存regional_sourcesのoita.html','大分市の共創提案・暮らしの往復デスク').replace('画像拡大でも5.3を確認済み','原本の掲載値は5.3人／便').replace('（画像確認）','').replace('・画像確認','')
 composite=[r for r in records if r['type'].startswith('複合参照')]; primary=[r for r in records if not r['type'].startswith('複合参照')]
 historical=[]; census=[]; current=[]
 for r in primary:
  if r['id'].startswith(('44341_','44211_','44214_','44206_','44210_')):census.append(r)
  elif slug=='kitsuki' and r['id'].startswith('kitsuki_add_') and int(r['id'].rsplit('_',1)[1])<=520 and not r['period'].startswith('2024'):historical.append(r)
  else:current.append(r)
 primary=current
 cov=get_coverage(slug)
 for key,value in DETAILS.get(slug,{}).get("coverage",{}).items():
  cov["main_topics"][int(key)]["status"]=value
  cov["main_topics"][int(key)]["anchor"]="#journeys"
 for row in cov['field_records']:
  ix=int(row['yufuin_record'])
  if ix in [7,9,10,27,28,30,36,40]:
   topic={7:13,9:0,10:0,27:22,28:24,30:27,36:23,40:22}[ix]
   row['regional_status']=cov['main_topics'][topic]['status']+' 湯布院と同じ対象・測定条件ではありません。'
 (dest/'downloads'/'coverage.json').write_text(json.dumps(cov,ensure_ascii=False,indent=2)+'\n')
 public=dict(region=d['name'],checkedAt='2026-11-04',status='追加調査版・調査継続',note='公表値、計画目標、調査標本、独自計算を区別。複合参照と分離レコードは重複を含むため集計不可。未確認を0としない。',records=records)
 (dest/'downloads'/'evidence.json').write_text(json.dumps(public,ensure_ascii=False,indent=2)+'\n')
 out=io.StringIO(); w=csv.DictWriter(out,fieldnames=['id','label','value','period','type','definition','source','url','page','caution'],extrasaction='ignore');w.writeheader();w.writerows(records);(dest/'downloads'/'evidence.csv').write_text('\ufeff'+out.getvalue())
 long='long' if len(d['roman'])>6 else ''; huburl=f'/oita-mirai-mobility-consortium/dialogue/{hub}/'; proposalurl='/oita-mirai-mobility-consortium/dialogue/'+d['proposal'] if d['proposal'] else None
 nav='<nav class="region-nav" aria-label="ほかの地域の分析">'+''.join(f'<a href="/co-creation-atlas/{s}-mobility/"'+(' aria-current="page"' if s==slug else '')+f'>{E(x["short"])}</a>' for s,x in REGIONS.items())+'<a href="/co-creation-atlas/beppu-mobility/">別府</a><a href="/co-creation-atlas/yufuin-mobility/">由布・湯布院</a></nav>'
 hero=f'<section class="hero"><p class="kicker">{E(d["name"])} / MOBILITY &amp; REGIONAL EVIDENCE</p><h1 class="{long}">{d["roman"]}<span>.</span><span class="sr-only"> {E(d["name"])}のデータ分析</span></h1><div class="hero-sub"><h2>{d["headline"]}</h2><div><span class="edition">追加調査版・調査継続 / 2026.11.04 確認</span><p>{E(d["intro"])}</p></div></div>'
 if d['photo']:hero+=f'<figure class="hero-photo"><img src="/oita-mirai-mobility-consortium/dialogue/assets/{d["photo"]}" alt="{E(d["photoalt"])}" width="1800" height="1200" decoding="async" fetchpriority="high"><figcaption class="photo-caption">{E(d["credit"])} {a(d["crediturl"],"写真出典")}</figcaption></figure>'
 else:hero+=f'<div class="hero-typographic"><p>観測を、判断へ。<br>判断を、現場の検証へ。</p><small>公表値・計画目標・仮説を区別した地域データ分析</small></div>'
 hero+='</section>'
 metrics=''.join(f'<article class="metric"><span class="scope">{E(period)}</span><p class="label">{E(label)}</p><p class="big-number">{E(value)}<small>{E(unit)}</small></p><p class="micro">{E(note)}</p>{a(url,page,"source-link")}</article>' for label,value,unit,period,note,url,page in d['metrics'])
 section1=chapter(1,'snapshot','数字の規模と、<br>数字の意味を知る。','OBSERVATION / 観測',f'<div class="metric-grid">{metrics}</div><p class="intro">{E(d["snapshot"])}</p>{a(*d["snapshot_source"],"source-link")}<p class="note warning"><strong>読み方</strong>　人口、延べ利用、施設入場、宿泊、交通費は別の指標です。対象と時点が揃わない数値を足したり割ったりして、需要や採算を算出しません。</p>')
 section2=chapter(2,'mobility',d['traffic_title'],'MOBILITY / 交通と移動',f'<p class="intro">{E(d["traffic_intro"])}</p><div class="split">'+''.join(chart(c) for c in d['charts'])+'</div><div class="triple" style="margin-top:28px">'+''.join(panel(*p) for p in d['traffic_facts'])+'</div><p class="note">本文の数値の出典・対象・分母は <a href="#evidence">全データ・原典</a>でも確認できます。交通の最新利用条件は各運行主体の案内を優先してください。</p>')
 cards=''.join(f'<article class="plan-card"><p class="level">{E(level)}</p><div><h3>{E(title)}</h3><p class="period">{E(period)}</p><p>{E(text)}</p>{a(url,"公式原典","source-link")}</div></article>' for level,title,period,text,url in PLANS+[('市町の計画',*p) for p in d['localplans']])
 section3=chapter(4,'policy','国・県・地域の計画を、<br>別々の役割で読む。','POLICY / 計画と現在地','<p class="intro">現行計画の期間を確認し、実績と目標を分離。計画への記載は、コンソーシアムや特定車両の採用・予算確保を意味しません。</p><div class="plan-grid">'+cards+'</div>')
 section4=chapter(5,'decisions','言えること、言えないこと。<br>次に確かめること。','INFERENCE &amp; TEST / 推論と検証','<div class="triple">'+''.join(panel(title,text,title) for title,text in d['readings'])+'</div><h3 style="margin:40px 0 20px">次の作業と、判断するための条件</h3><p class="micro primary-note">以下は調査・検証の案です。関係者への依頼、実証、導入、費用負担の合意が完了したものではありません。</p><div class="decision-grid">'+''.join(f'<article><p class="kicker">NEXT {i:02}</p><h3>{E(title)}</h3><p>{E(text)}</p></article>' for i,(title,text) in enumerate(d['nextsteps'],1))+'</div>')
 sources={}
 for r in records:sources.setdefault(r['url'],(r['source'],'本文・表の参照位置は各データ行に併記。'))
 for title,url,note in COMMON_SOURCES:
  if slug=='saganoseki' and 'その他市町村' in note:note='2026年8月公表。従業員10人以上施設の調査。大分市集計から佐賀関単独の値は分離できず、地区へ按分しません。'
  sources[url]=(title,note)
 for _,title,period,text,url in PLANS:sources[url]=(title,period)
 for title,period,text,url in d['localplans']:sources[url]=(title,period)
 sourcehtml='<ol class="source-list">'+''.join(f'<li>{a(url,title)}<small>{E(note)}</small></li>' for url,(title,note) in sources.items())+'</ol>'
 coverage='<div class="coverage-grid">'+''.join(f'<article><p class="pill">確認済み・対象範囲は原典に限定</p><h3>{E(title)}</h3><p class="micro">本文の要点と下の出典付きデータ表に収録しています。</p></article>' for title in d['coverage'])+'<article><p class="pill missing">追加調査が必要</p><h3>便別OD・運行制約・事業条件</h3><p class="micro">追加調査を反映した分析ページです。由布・別府と同じ項目を全て取得した状態ではありません。</p></article></div>'
 downloads='<div class="download-row"><a class="button-link primary" href="downloads/evidence.json" download>出典付きデータ JSON ↧</a><a class="button-link" href="downloads/evidence.csv" download>出典付きデータ CSV ↧</a></div>'
 section5=chapter(6,'evidence','原典に戻れる、<br>データと調査の現在地。','EVIDENCE / 全データ・原典',coverage+'<h3 style="margin-top:40px">未確認・未取得のデータ</h3><ul class="missing-list">'+''.join(f'<li>{E(x)}</li>' for x in d['missing'])+'</ul><p class="note warning">未確認は「存在しない」「利用ゼロ」ではありません。2025年県観光確報は確認済みですが、対象地域を含む「その他市町村」の合計を各市町へ按分していません。新しい資料が見つかれば更新します。</p>'+downloads+f'<p class="micro">台帳は{len(records)}行。数値のほか計画・定義・未確認事項を含み、複合参照と分離行には重複があります。独立した指標の件数や合計として扱わないでください。</p><details open><summary>主な指標と確認事項（{len(primary)}行）</summary>'+recordtable(primary,'出典付きデータ一覧')+'</details>'+(f'<details><summary>複合参照・原表のまとまり（{len(composite)}行）</summary>'+recordtable(composite,'分離レコードと重複する参照行')+'</details>' if composite else '')+'<h3 style="margin:40px 0 25px">調査に使った一次資料</h3>'+sourcehtml)
 covrows=''.join(f'<tr><th scope="row">{E(x["topic"])}</th><td>{E(x["status"])}</td></tr>' for x in cov['main_topics'])
 fieldrows=''.join(f'<tr><th scope="row">{x["yufuin_record"]} / {E(x["topic"])}</th><td>{E(x["indicator"])}</td><td>{E(x["regional_status"])}</td></tr>' for x in cov['field_records'])
 covhtml='<h3 style="margin-top:40px">湯布院の調査項目との対応</h3><p class="micro">情報の量を揃えるために欠測を数値で埋めることはしません。29分野・56項目ごとに確認できた範囲を示します。対応表は調査完了率ではなく、次に集めるべき情報を明らかにするものです。</p><details><summary>29分野の確認状況</summary><div class="table-scroll" tabindex="0" role="region" aria-label="29分野の確認状況"><table><thead><tr><th>分野</th><th>確認した範囲・不足</th></tr></thead><tbody>'+covrows+'</tbody></table></div></details><details><summary>湯布院の56項目との対応</summary><div class="table-scroll" tabindex="0" role="region" aria-label="56項目との対応"><table class="wide-table"><thead><tr><th>項目</th><th>湯布院で調べた内容</th><th>この地域での確認範囲</th></tr></thead><tbody>'+fieldrows+'</tbody></table></div></details><div class="download-row"><a class="button-link" href="downloads/coverage.json" download>29分野・56項目の対応 JSON ↧</a></div>'
 extra_tables=''
 if census:extra_tables+='<details><summary>国勢調査の交通手段・通勤通学OD '+str(len(census))+'行</summary>'+recordtable(census,'2020国勢調査・同一母集団の交通手段とOD')+'</details>'
 if historical:extra_tables+='<details><summary>杵築の2020–2023年・月別地区別原表 '+str(len(historical))+'行</summary>'+recordtable(historical,'杵築2020–2023年の過年度詳細')+'</details>'
 extra_tables+='<p class="micro">本文・折りたたみ表・複合参照を合わせて全'+str(len(records))+'行を掲載。複合参照、小計、計算値を含むため、独立した指標数ではありません。</p>'
 extra_tables+='<div class="download-row"><a class="button-link" href="'+ASSET+'commuting-2020.zip" download>5市町の全通勤OD・交通手段 ZIP ↧</a></div><p class="micro">ZIPは2020国勢調査の全国宛先・男女別原セル、CSV/JSON、定義と出典を収録。交通手段とODのクロス集計ではありません。佐賀関は市町村表から分離できず欠測です。</p>'
 section5=section5.replace('</section>',extra_tables+covhtml+'</section>')
 if slug=='saganoseki':section5=section5.replace('対象地域を含む「その他市町村」の合計を各市町へ按分していません。','大分市集計から佐賀関単独値を分離できないため、地区へ按分していません。')
 roadrows=''.join('<tr><th scope="row">'+E(row[0])+'</th>'+''.join(f'<td class="number">{v}</td>' for v in row[1:])+'</tr>' for row in ROADS[slug])
 roadhtml='<h3 style="margin-top:40px">広域幹線と地域内の路線を分ける</h3><p class="micro">県ビジョン2026・資料編。県内路線バス10社の2024年度報告に基づく方面別集計から主要方面を抜粋。運行回数は1日当たりです。自治体内全交通や2026年の現行時刻表ではありません。</p><div class="table-scroll" tabindex="0" role="region" aria-label="方面別バス指標"><table class="wide-table"><thead><tr><th>方面・区分</th><th>系統数</th><th>運行回数（回／日）</th><th>平均乗車密度</th><th>輸送量</th></tr></thead><tbody>'+roadrows+'</tbody></table></div><p class="micro">'+a('https://www.pref.oita.jp/uploaded/attachment/2276664.pdf',ROAD_PAGES[slug])+'</p><p class="note warning">原本の指標名称を保持しています。「輸送量」は年間延べ利用人数・ユニーク利用者数ではありません。複数自治体をまたぐ方面を足して市町別利用者にしたり、密度だけで廃止・導入を決めたりしません。</p>'
 section2=section2.replace('</section>',roadhtml+'</section>')
 extra=DETAILS.get(slug,{})
 lookup={r['id']:r for r in records}
 detailcards=[]
 for card in extra.get('cards',[]):
  refs=[]
  for rid in card['records']:
   r=lookup[rid]
   refs.append(a('#record-'+rid,r['source']+' / '+r['page'],'source-link'))
  detailcards.append('<article class="panel"><span class="status">'+E(card.get('type','観測と解釈'))+'</span><h3>'+E(card['title'])+'</h3><p class="micro">'+E(card['body'])+'</p><p class="detail-refs">'+'<br>'.join(refs)+'</p></article>')
 detailcontent='<p class="intro">'+E(extra.get('intro','公表資料で確認できた移動の条件を、対象・時点を分けて補います。'))+'</p><div class="split">'+''.join(chart(c) for c in extra.get('charts',[]))+'</div><div class="detail-grid">'+''.join(detailcards)+'</div>'
 detailcontent+='<p class="note warning"><strong>調査と実行の状態</strong>　掲載した公表値は原典と照合していますが、原因の特定・利用意思・事業採算・実施主体の合意は未確定です。以下の検証は設計段階で、現地実験や導入を実施した結果ではありません。分析から直ちに増便・新車両導入・路線廃止を決めません。</p>'
 section_detail=chapter(3,'journeys',extra.get('title','来訪と暮らしの、<br>移動の条件を細かく見る。'),'JOURNEYS / 追加調査',detailcontent)
 closing=f'<section class="closing"><p class="kicker">FROM EVIDENCE TO DIALOGUE</p><h2>データを読み、<br>地域と確かめる。</h2><p>公表データは対話の出発点です。次は現在の運行・暮らし・事業条件と照合し、既存交通でできることを含めて検証します。</p><div class="download-row">{a(huburl,d["short"]+"の分析・提案の目次へ","button-link primary")}'
 closing+=(a(proposalurl,'既存の共創提案を読む','button-link') if proposalurl else '<p class="note">杵築の独立した共創提案は未作成です。確認できたデータから検討を進めます。</p>')+'</div>'+nav+'</section>'
 credits=f'<p class="micro">{E(d["credit"])}。{a(d["crediturl"],"原画像")} ／ <a href="https://creativecommons.org/licenses/by/2.0/">CC BY 2.0</a>。既存の縮小・WebP画像を表示枠に合わせてトリミング。現在の混雑や運行状態ではなく参考風景です。</p>' if d['photo'] else ''
 body=header(d['name']+'のデータ分析｜大分未来モビリティ・コンソーシアム',d['intro'])+f'<body><a class="skip" href="#main">本文へスキップ</a><header class="masthead wrap"><a class="brand" href="/oita-mirai-mobility-consortium/">MOBILITY<br>DESIGN LAB</a><nav aria-label="操作">{a(huburl,"地域の目次")}<button type="button" id="motion-toggle" aria-pressed="false">動きを止める</button><button type="button" id="print-page">印刷 / PDF</button></nav></header><main class="wrap" id="main">'+hero+'<nav class="chapter-nav" aria-label="章の目次">'+''.join(f'<a href="#{id}"><b>{i:02}</b>{name}</a>' for i,(id,name) in enumerate([('snapshot','地域の数字'),('mobility','交通・移動'),('journeys','来訪・暮らし'),('policy','計画'),('decisions','次の検証'),('evidence','全データ')],1))+'</nav>'+section1+section2+section_detail+section3+section4+section5+closing+f'</main><footer><div class="wrap"><p class="footer-word {long}">{d["roman"]}.</p>'+credits+'<p class="micro" style="margin-top:20px">調査確認：2026年11月4日。分析はMDLによる整理で、自治体・事業者の見解や合意を示すものではありません。</p></div></footer></body></html>'
 (dest/'index.html').write_text(body)
 # Reuse established light-tone hub design without replacing any proposal.
 base=(ROOT/'oita-mirai-mobility-consortium/dialogue/yufuin/index.html').read_text(); css=re.search(r'<style>(.*?)</style>',base,re.S).group(1)
 css+=' .hero-word{font-size:clamp(65px,12vw,165px)}.card-image.typographic{padding:28px;background:#dce8f4;display:flex;align-items:center;font-size:28px;font-weight:900;line-height:1.5}.card-proposal .typographic{background:#fee3cd}.card-unready{border:1px dashed #999;display:flex;flex-direction:column;background:#efefea}.card-unready .card-foot{background:#ddd}.card-meta{flex-wrap:wrap}@media(max-width:700px){.hero-word{font-size:clamp(49px,13.8vw,90px)}}'
 card1=f'<a class="card card-analysis" href="/co-creation-atlas/{slug}-mobility/"><div class="card-image typographic">数字の意味を知る。<br>次の検証を考える。</div><div class="card-body"><div class="card-meta"><span class="card-number">01</span><span>ANALYSIS / 追加調査版・調査継続</span></div><h2>データ分析</h2><p class="card-subtitle">{E(d["name"])}の交通・地域データ</p><p class="card-description">{E(d["intro"])}</p></div><div class="card-foot"><span>データ分析を読む</span><span aria-hidden="true">↗</span></div></a>'
 if proposalurl:card2=f'<a class="card card-proposal" href="../{d["proposal"]}"><div class="card-image typographic">地域の可能性から、<br>対話を始める。</div><div class="card-body"><div class="card-meta"><span class="card-number">02</span><span>PROPOSAL / 検討用ドラフト</span></div><h2>共創提案</h2><p class="card-subtitle">既存の地域提案</p><p class="card-description">地域のサービスと交通をつなぐ構想。データ分析とは区別した提案です。参画・役割・費用負担・実施は未合意です。</p></div><div class="card-foot"><span>共創提案を読む</span><span aria-hidden="true">↗</span></div></a>'
 else:card2='<article class="card card-unready"><div class="card-image typographic">まず、地域の<br>条件を確かめる。</div><div class="card-body"><div class="card-meta"><span class="card-number">02</span><span>PROPOSAL / 未作成</span></div><h2>共創提案</h2><p class="card-subtitle">分析をもとに検討する段階</p><p class="card-description">独立した提言ページはまだありません。観光数値の不一致、現在の運行と来訪行程、住民・事業者の条件を確認してから構想を具体化します。</p></div><div class="card-foot"><span>データ分析の「次の検証」を参照</span></div></article>'
 hubhtml=header(d['name']+'｜データ分析と共創提案','地域の分析と既存提案をつなぐ目次。',False).replace('</head>','<style>'+css+'</style></head>')+f'<body><a class="skip" href="#main">本文へスキップ</a><header class="masthead wrap"><a class="brand" href="/oita-mirai-mobility-consortium/">MOBILITY<br>DESIGN LAB</a><a href="../">地域・団体の一覧へ ↗</a></header><main class="wrap" id="main"><section class="hero"><p class="eyebrow">{E(d["name"])} / ANALYSIS &amp; PROPOSAL</p><p class="hero-word" aria-hidden="true">{d["roman"]}<span>.</span></p><div class="hero-bottom"><h1>{E(d["name"])}の現在から、<br>これからへ。</h1><p class="hero-intro">公表データを確かめる分析と、未来を考える提案を分けて読む。地域の数字と検証課題へ、ここから進めます。</p></div></section><div class="contents-heading"><h2 id="contents-title">目次 / CONTENTS</h2><span>2026.11.04 更新</span></div><nav class="contents" aria-labelledby="contents-title">{card1}{card2}</nav><aside class="reading-note"><p><strong>分析の読み方</strong><br>追加調査を反映した独立分析です。国・県・市町の計画、公表実績、未取得のデータを整理しています。時点・分母が違う数値をそのまま比較しません。</p><p><strong>提案の位置づけ</strong><br>TCO・MDLによる検討用ドラフト。参画・役割・費用負担・実施は未合意です。既存提言は分析の追加に伴って変更していません。</p></aside></main><footer class="footer wrap"><p>MOBILITY DESIGN LAB / 大分未来モビリティ・コンソーシアム</p><a href="../">地域・団体の一覧へ戻る ↑</a></footer></body></html>'
 hubpath=ROOT/'oita-mirai-mobility-consortium/dialogue'/hub;hubpath.mkdir(exist_ok=True);(hubpath/'index.html').write_text(hubhtml)
 return [str(p.relative_to(ROOT)) for p in [dest/'index.html',dest/'downloads/evidence.json',dest/'downloads/evidence.csv',dest/'downloads/coverage.json',hubpath/'index.html']]
manifest=[]
for slug,d in REGIONS.items():manifest.extend(build(slug,d))
# Start from the reviewed main index, not the previous PR16 branch.
index=ROOT/'oita-mirai-mobility-consortium/dialogue/index.html'
if DATA.name!='co-creation-atlas':s=json.loads((DATA/'existing_regional_sources.json').read_text())['indexHtml']
else:s=index.read_text()
for slug in ['hiji','usa','kunisaki','usuki','oita']:s=s.replace(f'href="{slug}.html"',f'href="{slug}/"')
if 'href="kitsuki/"' not in s:s=s.replace('<a href="taiyonoie.html">','<a href="kitsuki/">杵築市<span aria-hidden="true">↗</span></a><a href="taiyonoie.html">',1)
# Update only card navigation labels; preserve all existing proposal copy and PDFs.
def adjust_card(m):
 text=m.group(0)
 if re.search(r'href="(?:hiji|usa|kunisaki|usuki|oita)/"',text):
  text=re.sub(r'<span class="card-arrow">[^<]*</span>','<span class="card-arrow">分析と提案を見る ↗</span>',text)
 return text
s=re.sub(r'<a class="index-card".*?</a>',adjust_card,s,flags=re.S)
if 'id="regional-analysis-status"' not in s:
 section='<section class="policy-context wrap" id="regional-analysis-status" aria-labelledby="analysis-status-title"><h2 id="analysis-status-title">地域別データ分析</h2><p>別府・由布に加え、日出・宇佐・国東・臼杵・大分市佐賀関・杵築の独立分析を追加。新規6地域は初版で、確認済みデータと未取得項目を各ページに明記しています。既存の共創提案は変更していません。杵築は分析から検討を始める段階で、独立提言は未作成です。</p><p style="display:flex;flex-wrap:wrap;gap:18px;margin-top:20px">'+''.join(a(f'{x.get("hub",k)}/',x['short']) for k,x in REGIONS.items())+'</p></section>'
 s=s.replace('<section aria-labelledby="policy-title"',section+'<section aria-labelledby="policy-title"',1)
s=s.replace('新規6地域は初版で、確認済みデータと未取得項目を各ページに明記しています。','6地域は公表一次資料の追加調査版です。確認済みデータと未取得項目を各ページに明記しています。')
index.write_text(s);manifest.append(str(index.relative_to(ROOT)))
manifest.extend(str(p.relative_to(ROOT)) for p in Path(__file__).parent.glob('*') if p.is_file() and p.name in ['style.css','regional.css','app.js','regions.py','coverage.py','build.py','deepening.py','test_region.py','commuting-2020.zip'])
(ROOT/'regional-analysis-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print(json.dumps(dict(pages=len(REGIONS),files=len(manifest),records=sum(len(json.loads((ROOT/'co-creation-atlas'/f'{s}-mobility/downloads/evidence.json').read_text())['records']) for s in REGIONS)),ensure_ascii=False))
