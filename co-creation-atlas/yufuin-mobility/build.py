from pathlib import Path
import json,html
P=Path(__file__).resolve().parent
photos=json.loads((P/'photos.json').read_text())
e=html.escape
S=[{'id':'summer','title':'由布院・夏の現地調査','period':'2022年8月11日〜9月17日','area':'由布院地域','sample':'調査全体：1,023組・2,565人。交通手段の有効回答数は掲載段落に記載なし。','question':'由布院を訪れる際の利用交通機関','multiple':'選択方式は当該段落では未確認','values':[{'label':'自家用車','value':51},{'label':'JR','value':21},{'label':'レンタカー','value':14}],'source':'https://reposit.sun.ac.jp/dspace/bitstream/10561/2044/1/v57n4p89_takeda.pdf','page':'本文96頁（調査概要）、99頁（交通手段）／PDF 8、11頁','limit':'上位3項目の抜粋。残り14％を観光バスとみなさない。現在の全来訪者の構成比ではない。'}, {'id':'plan','title':'由布市の観光基本計画','period':'2022年2月公表の計画に掲載。交通手段の調査実施時期は未確認。','area':'由布院への来訪','sample':'交通手段の図：962回答','question':'由布院までの移動手段','multiple':'設問の選択方式は原票未確認','values':[{'label':'自家用車','value':86.1},{'label':'電車','value':8.2},{'label':'高速バス','value':4.3},{'label':'その他','value':1.5}],'source':'https://www.city.yufu.oita.jp/uploads/files/2022/07/r4kankoukihonkeikaku.pdf','page':'本文20頁（PDF 21頁）','limit':'レンタカー・貸切観光バスの独立項目なし。丸めにより合計100.1％。2022年夏調査との増減比較には使わない。'}, {'id':'foreign','title':'大分県・海外居住者の調査','period':'2025年度（2025年5月〜2026年2月の指定日）。2026年3月公表','area':'大分県全域','sample':'海外居住者200人（国籍ではなく居住地による区分）','question':'大分県内で利用した交通手段','multiple':'複数回答','values':[{'label':'レンタカー','value':25.5},{'label':'JR在来線','value':23.5},{'label':'貸切・観光バス','value':20.5},{'label':'高速バス','value':20.5}],'source':'https://www.pref.oita.jp/uploaded/attachment/2268519.pdf','page':'本文23〜24頁（PDF 24〜25頁）。調査概要：本文1〜2頁','limit':'湯布院への来訪手段ではない。同じ人が複数の交通機関を利用。上位項目の抜粋で、合計100％にはならない。'}]
B=[{'id': 'council-2017', 'label': '地域内に駐車する観光バス', 'range': [60, 100], 'unit': '台／日', 'period': '2017年6月16日の議会発言', 'area': '湯布院地域。発言の文脈は温湯・金鱗湖付近', 'evidenceType': '議員による当時の現場状況の報告', 'speaker': '野上安一議員', 'source': 'https://www.city.yufu.oita.jp/wp-content/uploads/2017/09/6.16.pdf#page=17', 'page': '印刷119頁／PDF17頁', 'limits': '調査日・数え方・平休日の区別は未記載。市全域の観測統計、外国人専用台数、現在値ではない。'}, {'id': 'plan-2018', 'label': '由布院中心部へ流入する観光バス', 'value': 100, 'approximate': True, 'unit': '台／日', 'period': '2017年の提案を2018年3月の計画に掲載', 'area': '由布院中心部', 'evidenceType': '計画のマスタープラン図に掲載された歴史的数値', 'source': 'https://www.city.yufu.oita.jp/wp-content/uploads/2018/07/sinyufuinonsenkankokihonkeikaku.pdf#page=39', 'page': '39頁', 'limits': '2017年経済産業省事業による提案図。調査日・方法は未記載。2018年の新規実測値や現在値とは断定できない。議会発言の60〜100台と合算・増減比較しない。'}, {'id': 'yufuin-go-2017', 'label': '高速路線バス「ゆふいん号」の利用者数', 'value': 480000, 'approximate': True, 'unit': '人／年度', 'period': '2017年度。2018年5月31日事業者発表', 'area': '福岡〜湯布院の路線全体', 'evidenceType': '事業者発表の年間路線利用者数', 'source': 'https://hitabus.com/wp-content/uploads/2018/05/8b7623dad400e1de970498d591cd4e20.pdf#page=1', 'page': '1頁', 'limits': '貸切観光バスとは別。湯布院への到着人数、固有の来訪者数、外国人客数には置き換えない。'}]
(P/'data.json').write_text(json.dumps({'updated':'2026-11-03','studies':S,'historicalBusRecords':B,'chartMethod':'選択方式未確認の割合は100％目盛の独立した円で表示し、構成比として合算しない。複数回答の県調査は比較バーで表示。'},ensure_ascii=False,indent=2))
def photo(id,cls='',eager=False):
 p=next(x for x in photos if x['id']==id)
 date=p['captured'][:4]+'年（元画像の日時情報）' if p['captured'][0].isdigit() else '撮影時点未確認'
 return f'<figure class="photo {cls}"><button class="photo-open" data-photo="{id}" aria-label="{p["title"]}の写真を拡大"><img src="assets/{id}.webp" srcset="assets/{id}-small.webp 700w, assets/{id}.webp 1600w" sizes="(max-width:700px) 100vw, 60vw" width="{p["width"]}" height="{p["height"]}" alt="{p["title"]}。由布市提供の地域風景写真。" loading="{'eager' if eager else 'lazy'}" decoding="async" {('fetchpriority="high"' if eager else '')}><span class="zoom" aria-hidden="true">↗</span></button><figcaption>{p["title"]} <span>{date} · <a href="#photo-credits">写真：由布市</a></span></figcaption></figure>'
def bars(vals,cls=''):
 colors=['pink','blue','lime','orange']
 return '<div class="bars '+cls+'">'+''.join(f'<div class="bar-row {colors[i]}"><div class="bar-label"><span>{v["label"]}</span><strong>{v["value"]}<small>%</small></strong></div><div class="bar-track" aria-hidden="true"><span style="--value:{v["value"]}%"></span></div></div>' for i,v in enumerate(vals))+'</div>'

def circles(values,cls=''):
 colors=['pink','blue','lime','orange']
 return '<div class="circle-grid '+cls+'">'+''.join(f'<figure class="circle-card {colors[i]}"><figcaption>{v["label"]}</figcaption><div class="donut"><svg viewBox="0 0 120 120" role="img" aria-label="{v["label"]}、掲載割合{v["value"]}パーセント。各円は100パーセントの目盛です"><circle class="donut-track" cx="60" cy="60" r="51"/><circle class="donut-value" cx="60" cy="60" r="51" pathLength="100" stroke-dasharray="{v["value"]} 100" style="--portion:{v["value"]}"/></svg><div class="donut-number" aria-hidden="true">{v["value"]}<small>%</small></div></div><span class="circle-scale">100％目盛 / 掲載値</span></figure>' for i,v in enumerate(values))+'</div>'

credits=''.join(f'<li><a href="{p["source"]}">{p["title"]}</a>：{p["captured"][:4]+"年（元画像の日時情報）" if p["captured"][0].isdigit() else "撮影時点未確認"}。</li>' for p in photos)
sourcecards=''.join(f'<article id="source-{s["id"]}"><p class="eyebrow">SOURCE 0{i+1}</p><h3>{s["title"]}</h3><dl><dt>時期</dt><dd>{s["period"]}</dd><dt>対象</dt><dd>{s["area"]}／{s["sample"]}</dd><dt>掲載指標</dt><dd>{s["question"]}。{s["multiple"]}。</dd><dt>掲載箇所</dt><dd>{s["page"]}</dd></dl><p>{s["limit"]}</p><a class="source-link" href="{s["source"]}" target="_blank" rel="noopener">原典のPDFを読む ↗</a></article>' for i,s in enumerate(S))
page='''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#090b0c"><title>湯布院の観光と交通｜MOBILITY DESIGN LAB</title><meta name="description" content="湯布院へどう来て、何にいくら使い、何泊して、どこで過ごすのか。由布市の観光統計と現地調査を、図と実測データで読み解きます。"><link rel="canonical" href="https://mobilitydlab.com/co-creation-atlas/yufuin-mobility/"><meta property="og:type" content="article"><meta property="og:title" content="湯布院の観光と交通"><meta property="og:description" content="湯布院へどう来て、何にいくら使い、何泊して、どこで過ごすのか。由布市の観光統計と現地調査を、図と実測データで読み解きます。"><meta property="og:image" content="https://mobilitydlab.com/co-creation-atlas/yufuin-mobility/assets/street.webp"><meta property="og:url" content="https://mobilitydlab.com/co-creation-atlas/yufuin-mobility/"><link rel="preload" href="../assets/display.woff2" as="font" type="font/woff2" crossorigin><link rel="stylesheet" href="style.css?v=20261103-2"><link rel="stylesheet" href="research.css?v=20261103-3"><script defer src="app.js?v=20261103-3"></script></head><body><a class="skip" href="#main">本文へスキップ</a><div class="reading-progress" aria-hidden="true"></div><header class="masthead"><a class="wordmark" href="/#data-design">MDL.<span>MOBILITY DESIGN LAB</span></a><span class="issue">MOBILITY ANALYSIS / 01</span><button id="motion-toggle" type="button" aria-pressed="false">動きを止める</button></header><main id="main"><section class="hero" id="top"><div class="hero-kicker"><span>大分・湯布院</span><span>DATA STORY / 2026.11.03</span></div><h1><span class="hero-en">YUFUIN.</span><span class="hero-ja">湯布院の<br><em>観光と交通。</em></span></h1><div class="hero-photo">__HERO__<div class="photo-tag">BEYOND THE NUMBERS.</div></div><div class="hero-bottom"><p class="lead">どこから来て、<br><strong>町でどう過ごす？</strong></p><p>由布市の観光統計から宿泊と消費を、由布院の現地調査から交通手段と町歩きの時間を読み解きます。</p><a class="round-link" href="#visitors" aria-label="観光客の内訳を見る">↓</a></div></section>
<nav class="chapter-nav" aria-label="特集の目次"><a href="#visitors">観光客</a><a href="#spending">消費額</a><a href="#nights">宿泊日数</a><a href="#access">交通手段</a><a href="#bus-history">観光バス</a><a href="#journey">町歩き</a><a href="#traffic-now">混雑</a><a href="#sources">資料</a></nav>
<section class="market-section" id="visitors" aria-labelledby="market-visitors-title">
  <header class="market-head">
    <p class="market-kicker">VISITORS <span>/</span> 2025</p>
    <h2 id="market-visitors-title">由布市を訪れるのは、<br><em>どんな人？</em></h2>
    <p class="market-lead">由布市を訪れた観光客は419.6万人。もっとも大きい層は、国内からの日帰り客です。</p>
  </header>
  <div class="market-dashboard">
    <div class="market-visual">
      <div class="market-wheel market-wheel-visitors" aria-hidden="true"><div><strong>419.6</strong><small>万人</small></div></div>
      <p class="market-caption">由布市全域の観光入込客数</p>
    </div>
    <div>
      <h3 class="market-subtitle">観光入込客 <b>4,196,408</b> 人の内訳</h3>
      <table class="market-table market-share"><caption class="market-sr">2025年の由布市全体。国内・外国、日帰り・宿泊の4区分</caption><thead><tr><th scope="col">旅行者</th><th scope="col">人数</th><th scope="col">構成比</th></tr></thead><tbody>
        <tr><th scope="row"><i class="market-key market-c1"></i>国内・日帰り</th><td>1,787,297人</td><td>42.6%</td></tr>
        <tr><th scope="row"><i class="market-key market-c2"></i>国内・宿泊</th><td>1,105,743人</td><td>26.3%</td></tr>
        <tr><th scope="row"><i class="market-key market-c3"></i>外国人・日帰り</th><td>1,015,786人</td><td>24.2%</td></tr>
        <tr><th scope="row"><i class="market-key market-c4"></i>外国人・宿泊</th><td>287,582人</td><td>6.9%</td></tr>
      </tbody></table>
      <p class="market-annotation">国内客の<strong>61.8%</strong>、外国人客の<strong>77.9%</strong>が市内では日帰り。市によると、外国人客の約9割は由布院エリアだけを訪れます。</p>
    </div>
  </div>
  <div class="market-pair">
    <div class="market-panel">
      <p class="market-overline">国内客の発地</p><h3>福岡県と大分県で<strong>49.7%</strong></h3>
      <p>国内からの旅行者289.3万人のうち、福岡県から80.8万人、大分県内から63.1万人が訪れました。</p>
      <table class="market-table"><caption class="market-sr">主な国内発地別の来訪者数</caption><thead><tr><th scope="col">発地</th><th scope="col">来訪者数</th></tr></thead><tbody>
        <tr><th scope="row">福岡県</th><td>808,389人</td></tr><tr><th scope="row">大分県</th><td>630,721人</td></tr><tr><th scope="row">その他九州</th><td>513,787人</td></tr><tr><th scope="row">関東</th><td>283,044人</td></tr>
      </tbody></table>
    </div>
    <div class="market-panel">
      <p class="market-overline">訪日客が湯布院を選んだ理由</p><h3>泊まる人は<strong>温泉</strong>を挙げる</h3>
      <p>由布院駅周辺の外国人400人に聞くと、温泉を挙げた割合は宿泊客の44%、日帰り客の8%でした。</p>
      <table class="market-table"><caption class="market-sr">宿泊客204人・日帰り客196人別の訪問理由</caption><thead><tr><th scope="col">訪問理由</th><th scope="col">宿泊客</th><th scope="col">日帰り客</th></tr></thead><tbody>
        <tr><th scope="row">温泉</th><td>44%</td><td>8%</td></tr><tr><th scope="row">SNS</th><td>4%</td><td>24%</td></tr>
      </tbody></table>
      <p class="market-note">2023年12月〜2024年1月の7日間。複数回答を含み、団体旅行者は回答に応じにくい調査でした。</p>
    </div>
  </div>
  <details class="market-season"><summary>2025年の月別推移を見る <span>総数は11月、外国人は1月が最多</span></summary>
    <div class="market-season-body"><div><p class="market-overline">月別入込客数（万人）</p><svg class="market-trend" viewBox="0 0 420 168" role="img" aria-label="市全体は11月39.8万人、外国人は1月14.5万人が最も多く、7月はともに最少。全月の人数は表に掲載。"><g class="market-grid-lines"><path d="M43 143.00H400"/><text x="35" y="146.00">0</text><path d="M43 114.80H400"/><text x="35" y="117.80">10</text><path d="M43 86.60H400"/><text x="35" y="89.60">20</text><path d="M43 58.40H400"/><text x="35" y="61.40">30</text><path d="M43 30.20H400"/><text x="35" y="33.20">40</text></g><polyline class="market-line-all" points="43.00,39.05 75.40,49.13 107.80,36.63 140.20,37.87 172.60,35.05 205.00,57.81 237.40,64.30 269.80,51.10 302.20,56.55 334.60,37.44 367.00,30.89 399.40,36.81"/><polyline class="market-line-foreign" points="43.00,102.05 75.40,105.67 107.80,109.29 140.20,107.89 172.60,111.85 205.00,119.19 237.40,124.83 269.80,123.22 302.20,122.12 334.60,109.50 367.00,109.12 399.40,103.73"/><g class="market-month-labels"><text x="43.00" y="161">1月</text><text x="107.80" y="161">3月</text><text x="172.60" y="161">5月</text><text x="237.40" y="161">7月</text><text x="302.20" y="161">9月</text><text x="399.40" y="161">12月</text></g></svg><p class="market-line-legend"><span>全体</span><span>うち外国人</span></p></div>
    <div class="market-season-tables"><table class="market-table"><caption class="market-sr">2025年1〜6月の由布市観光客数、単位は人</caption><thead><tr><th scope="col">月</th><th scope="col">総数</th><th scope="col">うち外国人</th></tr></thead><tbody><tr><th scope="row">1月</th><td>368,621</td><td>145,219</td></tr><tr><th scope="row">2月</th><td>332,887</td><td>132,361</td></tr><tr><th scope="row">3月</th><td>377,207</td><td>119,532</td></tr><tr><th scope="row">4月</th><td>372,796</td><td>124,513</td></tr><tr><th scope="row">5月</th><td>382,810</td><td>110,468</td></tr><tr><th scope="row">6月</th><td>302,090</td><td>84,445</td></tr></tbody></table><table class="market-table"><caption class="market-sr">2025年7〜12月の由布市観光客数、単位は人</caption><thead><tr><th scope="col">月</th><th scope="col">総数</th><th scope="col">うち外国人</th></tr></thead><tbody><tr><th scope="row">7月</th><td>279,091</td><td>64,422</td></tr><tr><th scope="row">8月</th><td>325,894</td><td>70,157</td></tr><tr><th scope="row">9月</th><td>306,561</td><td>74,049</td></tr><tr><th scope="row">10月</th><td>374,334</td><td>118,800</td></tr><tr><th scope="row">11月</th><td>397,558</td><td>120,136</td></tr><tr><th scope="row">12月</th><td>376,559</td><td>139,266</td></tr></tbody></table></div></div></details>
  <p class="market-sources"><a href="https://www.city.yufu.oita.jp/uploads/files/2026/06/R7-kankoudautaityousakekka.pdf">由布市・2025年観光動態調査 ↗</a><a href="https://wwwtb.mlit.go.jp/kyushu/content/000321821.pdf#page=27">九州運輸局・外国人観光客調査 27頁 ↗</a></p>
</section>
<section class="market-section" id="spending" aria-labelledby="market-spending-title">
  <header class="market-head"><p class="market-kicker">SPENDING <span>/</span> 2025</p><h2 id="market-spending-title">人は減っても、<br><em>消費額は増えた。</em></h2>
    <p class="market-lead">2025年の由布市の観光客数は前年比2.4%減。市が推計する観光消費額は前年の272.0億円から279.5億円へ増えました。</p>
  </header>
  <dl class="market-kpis"><div><dt>由布市の観光消費額</dt><dd>279.5<small>億円</small></dd></div><div><dt>前年差（前年比＋2.8%）</dt><dd>＋7.5<small>億円</small></dd></div><div><dt>入込客数で割った名目平均</dt><dd>6,661<small>円</small></dd></div></dl>
  <div class="market-dashboard">
    <div class="market-visual"><div class="market-wheel market-wheel-spending" aria-hidden="true"><div><strong>14,448</strong><small>円／人</small></div></div><p class="market-caption">訪日客の由布市内での平均支出</p></div>
    <div><h3 class="market-subtitle">訪日客の市内支出は、<b>宿泊費</b>が約6割</h3>
      <table class="market-table market-share"><caption class="market-sr">2025年、由布市を訪れた外国人の支出設問回答1,303件。日帰り客を含む</caption><thead><tr><th scope="col">費目</th><th scope="col">1人当たり</th><th scope="col">構成比</th></tr></thead><tbody>
        <tr><th scope="row"><i class="market-key market-c1"></i>宿泊費</th><td>8,651円</td><td>59.9%</td></tr>
        <tr><th scope="row"><i class="market-key market-c2"></i>飲食費</th><td>3,834円</td><td>26.5%</td></tr>
        <tr><th scope="row"><i class="market-key market-c3"></i>買物代</th><td>1,437円</td><td>9.9%</td></tr>
        <tr><th scope="row"><i class="market-key market-c4"></i>娯楽等サービス費</th><td>263円</td><td>1.8%</td></tr>
        <tr><th scope="row"><i class="market-key market-c5"></i>都道府県内交通費</th><td>151円</td><td>1.0%</td></tr>
        <tr><th scope="row"><i class="market-key market-c6"></i>その他</th><td>111円</td><td>0.8%</td></tr>
      </tbody></table>
      <p class="market-note">観光庁の訪日客調査をアンド・ディが独自集計。支出回答1,303件に日帰り客も含みます。訪問地間の交通費・団体やパックの参加費は対象外。費目は丸めにより計14,447円です。</p>
    </div>
  </div>
  <p class="market-sources"><a href="https://www.city.yufu.oita.jp/uploads/files/2026/06/R7-kankoudautaityousakekka.pdf#page=2">由布市・発地別観光客数と消費額 ↗</a><a href="https://inbound-data.and-d.co.jp/p/2025/muni/4410013/">アンド・ディ・2025年の由布市集計 ↗</a></p>
</section>
<section class="market-section" id="nights" aria-labelledby="market-nights-title">
  <header class="market-head"><p class="market-kicker">STAY <span>/</span> 2025</p><h2 id="market-nights-title">由布市に、<br><em>何泊する？</em></h2></header>
  <div class="market-pair"><div class="market-panel">
    <p class="market-overline">宿泊施設での1回の滞在</p><h3 class="market-metric">1.085<small>泊</small></h3>
    <p>由布市内で従業者10人以上の回答施設について、年間の延べ218,653人泊を、各施設で宿泊手続をした計201,597人で割った値です。</p>
    <p class="market-note">毎月の対象46施設、回収15〜20施設。市内で宿を替えれば施設ごとに数えます。観光庁の月次第2次速報12か月の合計。</p>
  </div><div class="market-panel">
    <p class="market-overline">訪日客が由布市内に泊まった日数</p><h3 class="market-metric">82.4<small>%が1泊</small></h3>
    <p>訪日客の市内宿泊者に絞ると、約82.4%が1泊、約17.6%が2泊以上でした。</p>
    <p class="market-note">2025年の訪日客の支出回答1,303件。全回答者に占める市内1泊の割合31.8%を、市内宿泊率38.6%で割った概算。知人宅・民泊を含みます。</p>
  </div></div>
  <p class="market-sources"><a href="https://www.mlit.go.jp/kankocho/page02_00022.html">観光庁・2025年月次宿泊統計 参考第5〜9表 ↗</a><a href="https://inbound-data.and-d.co.jp/p/2025/muni/4410013/">アンド・ディ・市内での泊数 ↗</a></p>
</section>

<section class="wrap route-guide" id="access" aria-labelledby="route-heading"><p class="eyebrow blue-text">ACCESS / 2026年11月3日時点</p>
<h2 id="route-heading">由布院へ、<br><em class="blue-text">どう来る？</em></h2>
<p class="route-lead">福岡方面からは列車と高速バス、大分空港からは駅前までの直行バスがあります。</p>
<div class="route-grid">
<article><h3>博多駅から</h3><b>2時間14分</b><p>特急ゆふいんの森1号の例。9:17発、11:31着。全車指定席。</p><a href="https://www.jrkyushu.co.jp/trains/yufuinnomori/">JR九州の運転日・時刻 ↗</a></article>
<article><h3>福岡・天神から</h3><b>約2時間20分</b><p>高速バス「ゆふいん号」。平常時は1日14往復、事前予約制です。</p><a href="https://kamenoibus.com/highway/">亀の井バスの路線案内 ↗</a></article>
<article><h3>大分空港から</h3><b>55分</b><p>由布院駅前行きは1日5便。11月30日までのダイヤです。</p><a href="https://www.oitakotsu.co.jp/bus/airport/disp.php?period=20261025_20261130&amp;rosen=03&amp;shubetu=2">大分交通の時刻表 ↗</a></article>
<article><h3>別府駅から</h3><b>36番</b><p>西口から湯布院線へ。観光快速「ゆふりん」は10月17日から当面全便運休です。</p><a href="https://kamenoibus.com/archive/3724.html">亀の井バスの運行案内 ↗</a></article>
</div><p class="route-stat">JR由布院駅の乗車人員は<strong>1日平均1,363人</strong>（2025年度）。通勤・通学などの利用も含む、乗車のみの実績です。 <a href="https://www.jrkyushu.co.jp/company/info/data/pdf/2025ekibetsu.pdf">JR九州・駅別乗車人員 ↗</a></p>
<a class="source-chip" href="#arrival">来訪者が実際に使った交通手段を見る ↓</a></section>
<section class="study wrap" id="arrival"><div class="section-top"><span class="section-no pink-text">01</span><div><p class="eyebrow">YUFUIN / SUMMER 2022</p><h2>旅の入口は、<br><em class="pink-text">自家用車が51％。</em></h2></div><a class="source-chip" href="#source-summer">調査の条件・出典 ↗</a></div><p class="context">2022年8月11日〜9月17日／由布院地域の現地調査</p>__SUMMERCIRCLES__<p class="circle-note"><b>それぞれの円が100％の目盛です。</b>色は各項目の掲載割合。灰色は100％までの目盛で、残りの交通手段の内訳や人数を示していません。選択方式が確認できないため、３項目を一つの円にまとめていません。</p><div class="sample circle-sample"><p>調査全体</p><div><b>1,023</b>組 <span>/</span> <b>2,565</b>人</div><p>交通手段の有効回答数は、掲載段落に記載がありません。</p></div><p class="important"><span>CHECK</span>上位３項目の抜粋です。<strong>残り14％を「観光バス」とは扱えません。</strong>2026年現在の全来訪者の構成比を示す数字でもありません。</p><div class="photo-pair">__TRAIN____LIFE__</div><div class="editor-note"><span>MDLの視点</span><p><strong>駐車場から歩く人と、駅から歩く人。</strong><br>到着手段の違いを、到着後の動線・荷物・案内の設計へつなぐことが次の問いです。</p></div></section>
<section class="comparison wrap" id="comparison"><div class="section-top"><span class="section-no lime-text">02</span><div><p class="eyebrow">SAME PLACE, DIFFERENT SURVEY</p><h2>51と86.1。<br><em class="lime-text">違いにも、理由がある。</em></h2></div></div><div class="compare-statement"><p>由布市の観光基本計画には、<br>自家用車<strong class="lime-text">86.1<small>%</small></strong></p><div><p class="eyebrow">由布院までの移動手段 / 962回答</p><p>2022年2月公表の計画に掲載された、別の調査です。前の51％との差を、そのまま「車利用が減った」と読むことはできません。</p><p class="micro">交通手段の調査実施時期・詳細な抽出条件は未確認。計画の公表年と、現地調査の実施年は別です。</p><a class="source-link" href="#source-plan">条件と原典を見る ↗</a></div></div>__PLANCIRCLES__<p class="circle-note"><b>４つの独立した円で、掲載割合を表示。</b>各円は100％の目盛です。原票の選択方式が未確認のため、一つの構成比円グラフにはまとめていません。掲載値の合計は丸めにより100.1％。レンタカー・貸切観光バスの独立項目はありません。</p><div class="compare-rule"><p class="eyebrow">DON'T MIX THE DENOMINATORS</p><h3>場所。時期。対象。設問。</h3><p>この４つがそろわなければ、<strong>数字の差を「変化」にしない。</strong></p></div></section>
<section class="photo-interlude">__MIST__<div><p class="eyebrow">LOOK BEYOND THE DESTINATION</p><h2>湯布院へ来る。<br>大分を巡る。<br><em>それは、別の問い。</em></h2></div></section>
<section class="study wrap" id="foreign"><div class="section-top"><span class="section-no blue-text">03</span><div><p class="eyebrow">OITA PREFECTURE / FY2025</p><h2>海外居住者は、<br><em class="blue-text">複数の足で。</em></h2></div><a class="source-chip" href="#source-foreign">調査の条件・出典 ↗</a></div><div class="scope-banner"><strong>大分県全域</strong><span>海外居住者 <b>200</b>人</span><span>複数回答</span></div><p class="body-lead">2025年度の県調査で聞いたのは、<strong>「大分県内で使った交通手段」</strong>。湯布院に来た人だけの調査ではありません。「海外居住者」は国籍ではなく、住んでいる場所による区分です。</p><div class="foreign-grid">__FOREIGN__</div><p class="important"><span>CHECK</span>一人が鉄道とバスの両方を使うこともあります。<strong>合計を100％にする円グラフにはできません。</strong>掲載は一部項目の抜粋です。</p><div class="photo-pair">__CARRIAGE____LAKE__</div></section>
<section class="bus-history wrap" id="bus-history"><div class="section-top"><span class="section-no orange-text">04</span><div><p class="eyebrow">TOUR BUS / HISTORICAL EVIDENCE</p><h2>観光バスの、<br><em class="orange-text">具体的な数字。</em></h2></div></div><p class="body-lead">過去資料には、台数の記録があります。<strong>いつ・どこを・どう捉えた数字か</strong>を付けて読みます。現在の実測台数ではありません。</p><div class="bus-stat-grid"><article class="bus-stat"><p class="historical-badge">2017年6月 / 議会での報告</p><h3>地域内に駐車する観光バス</h3><div class="bus-number orange-text">60<span>〜</span>100<small>台／日</small></div><p>野上安一議員が、地域に１日60〜100台の観光バスが駐車していると報告。発言の文脈は、湯布院の温湯・金鱗湖付近です。</p><p class="micro">議員による当時の現場状況の報告。調査日・数え方・平休日の区別は記載されておらず、市全域の観測統計ではありません。</p><a class="source-link" href="https://www.city.yufu.oita.jp/wp-content/uploads/2017/09/6.16.pdf#page=17" target="_blank" rel="noopener">2017年6月16日 市議会会議録 ↗<small>印刷119頁 / PDF17頁</small></a></article><article class="bus-stat"><p class="historical-badge">2017年の提案 / 2018年計画掲載</p><h3>由布院中心部への流入</h3><div class="bus-number lime-text"><span class="approx">約</span>100<small>台／日</small></div><p>『新・由布院温泉観光基本計画』のマスタープラン図に、中心部へ流入する観光バスの台数として掲載されています。</p><p class="micro">2017年の経済産業省事業による提案図を、2018年3月の計画に掲載。調査日・集計方法は未記載で、2018年の新規実測値とは断定できません。</p><a class="source-link" href="https://www.city.yufu.oita.jp/wp-content/uploads/2018/07/sinyufuinonsenkankokihonkeikaku.pdf#page=39" target="_blank" rel="noopener">新・由布院温泉観光基本計画 ↗<small>由布院温泉観光協会・由布院温泉旅館組合 / 39頁</small></a></article></div><p class="important"><span>CHECK</span>「地域内の駐車」と「中心部への流入」は同じ定義ではありません。<strong>60〜100台と約100台を足したり、増減として比べたりしません。</strong>いずれも外国人専用バスの台数ではありません。</p><article class="highway-stat"><div><p class="historical-badge">別の種類 / 高速路線バス</p><h3>ゆふいん号</h3><p>福岡〜湯布院<br>2017年度・路線全体の利用者数</p></div><div class="highway-number blue-text"><span>約</span>48<small>万人</small></div><div><p>2018年5月31日の事業者発表で確認できる年間利用者数です。貸切観光バスの人数とは分けて扱います。</p><p class="micro">湯布院への到着人数、固有の来訪者数、外国人客数には置き換えません。</p><a class="source-link" href="https://hitabus.com/wp-content/uploads/2018/05/8b7623dad400e1de970498d591cd4e20.pdf#page=1" target="_blank" rel="noopener">事業者発表を読む ↗</a></div></article><div class="current-limit"><b>いまの台数・人数は、別に確かめる。</b><p>歴史資料は当時の規模を知る手がかりです。現在の湯布院だけの観光バス台数・人数を示す継続的な実測値は、この特集では確認できていません。県全体の20.5％を来訪者数に掛けたり、座席数で割って台数を埋めたりはしません。</p></div></section><section class="wrap journey-section" id="journey" aria-labelledby="journey-title">
  <p class="eyebrow blue-text">WALK / 由布院駅から金鱗湖へ</p>
  <h2 id="journey-title">湖まで歩くと、<br><em class="blue-text">あと何分過ごせる？</em></h2>
  <p class="journey-intro">由布院駅で降り、湯の坪街道を通って金鱗湖へ。帰りも同じ駅から出発するなら、徒歩だけで往復約50〜60分かかります。</p>
  <div class="journey-calculator">
    <div class="journey-controls">
      <fieldset id="journey-presets">
        <legend>駅に着いてから、駅に戻るまで</legend>
        <div class="journey-options">
          <label><input type="radio" name="journey-duration" value="90"><span>90分</span></label>
          <label><input type="radio" name="journey-duration" value="120" checked><span>120分</span></label>
          <label><input type="radio" name="journey-duration" value="180"><span>180分</span></label>
        </div>
      </fieldset>
      <p>片道は徒歩約25〜30分。帰りの乗車準備や、混雑・信号待ちにかかる余裕は別に見てください。</p>
    </div>
    <div class="journey-result">
      <span class="journey-label">食事・買い物・湖畔で過ごせる時間</span>
      <output id="journey-remaining" aria-live="polite">60〜70<span>分</span></output>
      <p id="journey-equation">120分 − 往復徒歩50〜60分</p>
    </div>
  </div>
  <noscript><p>往復徒歩を引いた残りは、持ち時間90分なら30〜40分、120分なら60〜70分、180分なら120〜130分です。</p></noscript>
  <p class="journey-sources">徒歩の目安　<a href="https://www.michinoekiyufuin.com/gallery/1464/">道の駅ゆふいん</a> ／ <a href="https://yufuin.gr.jp/feature/feature-1981/">由布市公式旅ガイド</a></p>
  <div class="journey-practice">
    <h3>荷物を持ったまま歩く？</h3>
    <p>駅に隣接する「ゆふいんチッキ」で、手荷物を9〜17時に預けられます。対象の宿に泊まる方は、駅から宿への配送も9〜15時に受け付けています。 <a href="https://yufuin.gr.jp/spot/spot-2295/">料金・対象の宿 ↗</a></p>
  </div>
  <div class="journey-evidence">
    <div class="journey-evidence-title">
      <p class="eyebrow">TIME ON SITE</p>
      <h3>実際に、どこで<br>どれくらい過ごしたか。</h3>
      <p>じゃらんの投稿者では、金鱗湖は1時間未満、湯の坪街道は1〜2時間が最多でした。</p>
    </div>
    <div class="journey-evidence-data">
      <table class="journey-distribution">
        <caption>投稿者が答えたスポット別の滞在時間</caption>
        <thead><tr><th scope="col">滞在時間</th><th scope="col">金鱗湖</th><th scope="col">湯の坪街道</th></tr></thead>
        <tbody>
          <tr><th scope="row">1時間未満</th><td><strong>57%</strong></td><td>20%</td></tr>
          <tr><th scope="row">1〜2時間</th><td>31%</td><td><strong>45%</strong></td></tr>
          <tr><th scope="row">2〜3時間</th><td>7%</td><td>21%</td></tr>
          <tr><th scope="row">3時間以上</th><td>4%</td><td>14%</td></tr>
        </tbody>
      </table>
      <p class="journey-note">各スポットへの投稿者の自己申告。集計期間・有効回答数は非公表。金鱗湖の合計は丸めにより99％です。</p>
      <p class="journey-sources">じゃらんnet　<a href="https://www.jalan.net/kankou/spt_44364ab2030004879/">金鱗湖</a> ／ <a href="https://www.jalan.net/kankou/spt_guide000000185268/">湯の坪街道</a></p>
    </div>
  </div>
  <aside class="journey-parking">
    <div><span class="journey-label">2002年11月｜中心部5カ所の予約駐車場</span><h3>車を停めた時間は、平均<span>約2時間半</span>。</h3></div>
    <div><p>11月23日は<strong>約2時間19分</strong>（387台）、24日は<strong>2時間30分</strong>（448台）。両日とも最も多かったのは1時間30分でした。測ったのは入庫から出庫までです。</p>
    <a href="https://www.jstage.jst.go.jp/article/journalip1984/21/0/21_0_885/_pdf/-char/ja#page=5">交通社会実験の原表・表3 ↗</a></div>
  </aside>
</section>
<section class="wrap journey-section journey-traffic" id="traffic-now" aria-labelledby="journey-traffic-title">
  <p class="eyebrow orange-text">TRAFFIC / 到着・出発の時間帯</p>
  <h2 id="journey-traffic-title">駅前と大型バス駐車場。<br><em class="orange-text">混む時間が違う。</em></h2>
  <p class="journey-intro">九州運輸局が2023年度に調べたところ、日帰り客と宿泊客は時間帯によって逆向きに動き、同じ場所に集まっていました。</p>
  <dl class="journey-times">
    <div><dt><b>9〜10</b><span>時台</span></dt><dd><strong>由布院駅・駅前バスセンター</strong>博多・大分方面からの列車と福岡方面からの高速バスが到着。帰路に就く宿泊客と重なります。</dd></div>
    <div><dt><span>午前〜</span><b>15</b><span>時台ごろ</span></dt><dd><strong>旧民芸村の大型バス駐車場周辺</strong>金鱗湖に近い乗降拠点。団体客が出入りし、大型バスと歩行者が狭い道を共有します。</dd></div>
    <div><dt><b>15〜17</b><span>時台</span></dt><dd><strong>由布院駅・駅前バスセンター</strong>福岡方面へ帰る日帰り客と、これから泊まる人の到着が重なります。</dd></div>
  </dl>
  <p class="journey-sources"><a href="https://wwwtb.mlit.go.jp/kyushu/content/000325204.pdf#page=29">九州運輸局の実態調査・本文28頁 ↗</a></p>
  <div class="journey-road">
    <div><span class="journey-label">2026年GW｜県道216号上り</span><p class="journey-speed"><b>20</b><span>km/h 未満</span></p></div>
    <div><h3>昼も混む、金鱗湖方面への右折手前。</h3><p>2026年4月26日〜5月6日のETC2.0データでは、湯布院ICから交番までの混雑は2024年GWより改善。一方、金鱗湖・湯の坪街道方面へ右折する交差点の手前には、12時台に速度が時速20kmを下回る区間が連続しました。</p>
    <p class="journey-sources"><a href="https://www.qsr.mlit.go.jp/oita/site_files/file/road_info/jutai_kyogikai/r08/R8_1_kaigisiryou.pdf#page=39">大分県交通渋滞対策協議会・本文38頁 ↗</a> ／ <a href="https://yufu-uramichi.com/">当日の混雑を見る ↗</a></p></div>
  </div>
</section>

<section class="wrap next" id="next"><div class="section-top"><span class="section-no pink-text">05</span><div><p class="eyebrow">FROM DATA TO A BETTER JOURNEY</p><h2>「来る」を、<br><em class="pink-text">「過ごす」へ。</em></h2></div></div><p class="body-lead">ここからはMDLの分析・提案です。交通量の観測や施策の効果を確認した結果ではありません。</p><ol class="journey"><li><span>01</span><h3>来る</h3><p>出発地・交通手段・<br>到着時刻を記録</p></li><li><span>02</span><h3>降りる</h3><p>駅・駐車場・乗降場の<br>集中と待ち時間を確認</p></li><li><span>03</span><h3>巡る</h3><p>歩行・立寄り・荷物の<br>困りごとを把握</p></li><li><span>04</span><h3>戻る</h3><p>帰路・乗継ぎ・再乗車の<br>安心を確かめる</p></li></ol><div class="research-list"><article><b>01 / COUNT</b><h3>同じ日に、数える。</h3><p>平日・休日、季節、時間帯をそろえ、駐車場の入出庫、バス台数、乗降人数を把握する。</p></article><article><b>02 / CONNECT</b><h3>移動の前後をつなぐ。</h3><p>出発地・次の目的地、宿泊／日帰り、滞在時間を同じ調査票で聞く。個人を特定しない集計にする。</p></article><article><b>03 / TEST</b><h3>小さく試し、比べる。</h3><p>駐車・乗換え案内や荷物対応を試し、歩きやすさ・待ち時間・店舗への回遊を実測する。</p></article></div><div class="closing-photos">__SPRING____PATH__</div></section>
<section class="sources wrap" id="sources"><p class="eyebrow">EVIDENCE / OPEN THE ORIGINAL</p><h2>調査資料と出典</h2><div class="report-downloads"><a href="downloads/Yufuin-Research.pdf">図表で読む調査レポート <b>PDF · 6ページ ↗</b></a><a href="downloads/Yufuin-Atlas-Data.xlsx" download>出典と計算式を見る <b>Excel · 11シート ↓</b></a><a href="downloads/Yufuin-Atlas-Research.json" download>全調査データを使う <b>JSON ↓</b></a></div><p>確認・更新日：2026年11月3日。調査の対象年はそれぞれ異なります。観光バスの歴史資料は各数値の直下に掲載しています。公式・原著の記述と、MDLの分析・提案を分けています。</p><div class="source-grid">__SOURCES__</div><details id="photo-credits"><summary>写真８点の出典・撮影時点・利用条件</summary><p>全８点は由布市フォトアルバムの実景写真です。地域の風景を伝えるもので、交通調査日の記録や現在の混雑・運行状況を示すものではありません。</p><p><a href="https://www.city.yufu.oita.jp/kankou/photomovie" target="_blank" rel="noopener">由布市の写真配布ページ・利用条件 ↗</a>：営利・非営利を問わず無償利用可能、データ自体の販売は禁止。写真提供：由布市フォトアルバム。撮影者の個人名は配布ページに記載なし。</p><ul>__CREDITS__</ul><p>縮小・WebP変換、表示枠に応じたトリミングを実施。拡大時は写真全体を表示します。日時は元画像に記録された情報であり、独立した撮影日の確認ではありません。生成画像は使用していません。</p><a href="photos.json">画像ごとの出典台帳（JSON）</a></details><div class="data-links"><a href="data.json" download>来訪手段3調査・観光バスの歴史資料（JSON） ↓</a><a href="/#data-design">データ分析のトップへ戻る ↗</a></div></section></main><footer><div class="footer-word">YUFUIN.<em>MOVE BETTER.</em></div><p>MOBILITY DESIGN LAB · MOBILITY ANALYSIS<br>モビリティ分析 / 2026.11.03</p><a href="#top">ページの先頭へ ↑</a></footer><dialog id="photo-dialog" aria-label="地域写真の拡大"><button class="dialog-close" type="button" aria-label="写真を閉じる">閉じる ×</button><img alt=""><p></p><a href="#photo-credits">出典・利用条件</a></dialog></body></html>'''
replacements={'HERO':photo('street',eager=True),'DOTS':''.join('<i class="'+('on' if i<51 else '')+'"></i>' for i in range(100)),'TRAIN':photo('train'),'LIFE':photo('street-life'),'SUMMERCIRCLES':circles(S[0]['values']),'PLANCIRCLES':circles(S[1]['values'],'circle-grid--four'),'MIST':photo('mist'),'CARRIAGE':photo('carriage'),'LAKE':photo('lake'),'SPRING':photo('spring'),'PATH':photo('path'),'SOURCES':sourcecards,'CREDITS':credits,'FOREIGN':''.join(f'<article class="foreign-card {c}"><span class="transport-no">0{i+1}</span><h3>{v["label"]}</h3><div class="foreign-value">{v["value"]}<small>%</small></div><div class="bar-track" aria-hidden="true"><span style="--value:{v["value"]}%"></span></div></article>' for i,(v,c) in enumerate(zip(S[2]['values'],['pink','blue','lime','orange'])))}
for k,v in replacements.items(): page=page.replace('__'+k+'__',v)
(P/'index.html').write_text(page)
