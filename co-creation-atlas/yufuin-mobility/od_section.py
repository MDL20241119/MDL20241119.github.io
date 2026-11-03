"""Render the Yufuin nolc rider comparison from the published trip matrix."""
import html
import json


def render(od, performance):
    stops = od['stops']
    matrix = od['matrix']
    start = stops.index('由布院駅')
    all_pairs = [i for i in range(len(stops)) if i != start]
    all_pairs.sort(key=lambda i: -(matrix[start][i] + matrix[i][start]))
    max_flow = max(max(row) for row in matrix)
    payload = json.dumps({'stops': stops, 'matrix': matrix}, ensure_ascii=False,
                         separators=(',', ':')).replace('<', r'\u003c')
    options = ''.join(
        f'<option value="{i}"{" selected" if i == start else ""}>{html.escape(stop)}</option>'
        for i, stop in enumerate(stops)
    )

    performance_rows = ''.join(
        f'<tr><th scope="row">{row["fiscal_year"]}</th><td>{row["target"]:.1f}</td>'
        f'<td>{row["actual"]:.1f}</td><td>{row["attainment_percent"]:.1f}％</td></tr>'
        for row in performance['years']
    )
    latest = performance['years'][-1]

    def pair_table(indices, caption):
        rows = []
        for dest in indices:
            cells = []
            for value in (matrix[start][dest], matrix[dest][start]):
                cells.append(f'<td><b>{value}</b><small>人</small>'
                             f'<progress aria-hidden="true" max="{max_flow}" value="{value}"></progress></td>')
            rows.append(f'<tr><th scope="row">{html.escape(stops[dest])}</th>{"".join(cells)}</tr>')
        return (f'<table class="od-table"><caption class="market-sr">{caption}</caption>'
                '<colgroup><col class="od-name-col"><col><col></colgroup>'
                '<thead><tr><th scope="col">相手の地点</th><th scope="col">この地点から</th>'
                '<th scope="col">この地点へ</th></tr></thead><tbody>'
                + ''.join(rows) + '</tbody></table>')

    return f'''
<section class="market-section od-section" id="nolc-data" aria-labelledby="od-title">
  <header class="market-head">
    <p class="market-kicker">NOLC <span>/</span> 由布院の乗降記録</p>
    <h2 id="od-title">ノルクで、<br><em>どこからどこへ？</em></h2>
    <p class="market-lead">2020年2月、予約に応じて17地点を結んだ無料実証では、{od['operating_days']}日間に延べ{od['total']}人が乗りました。由布院駅から宇奈岐日女神社へは17人、神社から駅へは6人でした。</p>
  </header>
  <div class="od-explorer">
    <div class="od-context">
      <p class="market-overline">2020年2月5日〜29日 · 無料実証</p>
      <h3>地点別に見る<br>行きと帰り</h3>
      <div class="od-picker" hidden><label for="od-stop">発着を比べる地点</label>
        <select id="od-stop">{options}</select>
      </div>
      <div aria-live="polite" aria-atomic="true" class="od-totals">
        <p><strong data-od-active>{html.escape(stops[start])}</strong>の乗降</p>
        <dl><div><dt>ここから乗車</dt><dd><b data-od-out>{od['origin_totals'][start]}</b><small>人</small></dd></div>
        <div><dt>ここで降車</dt><dd><b data-od-in>{od['destination_totals'][start]}</b><small>人</small></dd></div></dl>
      </div>
    </div>
    <div class="od-routes">
      <p class="od-explainer">選んだ地点と相手の地点を結ぶ、方向別の延べ人数。両方向の合計が多い区間から表示します。</p>
      {pair_table(all_pairs[:3], '選択地点と上位3地点を結ぶ方向別の延べ人数')}
      <details class="od-more">
        <summary>残り{len(all_pairs)-3}地点との乗降を見る</summary>
        {pair_table(all_pairs[3:], '選択地点と残りの地点を結ぶ方向別の延べ人数')}
      </details>
      <p class="market-note">往路・復路は区間の向きを表します。0人はこの実証期間の利用が0件だった区間です。金鱗湖に専用の乗降地点は設けられていませんでした。</p>
      <p class="market-sources"><a href="{html.escape(od['source'], quote=True)}">環境省掲載・由布地区実証報告書の乗降表（PDF 166頁）↗</a></p>
    </div>
    <script type="application/json" id="od-matrix">{payload}</script>
  </div>
  <div class="market-pair od-follow">
    <article class="market-panel">
      <p class="market-overline">2025年度の実績 · 観光特化型</p>
      <h3>観光便の1便当たり利用者数</h3>
      <p class="market-metric">{latest['actual']:.1f}<small>人／便</small></p>
      <p>目標{latest['target']:.1f}人に対し達成率{latest['attainment_percent']:.1f}％。市の次世代交通実験事業費{performance['fy2025_city_subsidy_yen']/10000:.1f}万円は共同企業体への補助金です。車両全体の運行原価は、この評価表からは分かりません。</p>
      <details class="od-more"><summary>2021〜2025年度の目標・実績を見る</summary>
        <table class="market-table"><caption>観光便の1便当たり平均利用者数（人／便）</caption>
          <thead><tr><th scope="col">年度</th><th scope="col">目標</th><th scope="col">実績</th><th scope="col">達成率</th></tr></thead>
          <tbody>{performance_rows}</tbody></table>
      </details>
      <p class="market-sources"><a href="{html.escape(performance['source'], quote=True)}">由布市・事務事業事後評価 本文13頁 ↗</a></p>
    </article>
    <article class="market-panel">
      <p class="market-overline">2026年の運行案内 · 観光周遊</p>
      <h3>駅から寺社を巡る約50分</h3>
      <p>由布院駅を出て興禅院・宇奈岐日女神社に立ち寄り、駅へ戻るコース。4〜11月の金・土・日・月と祝日に10:30、11:30、13:30発。大人1,800円、小人1,300円です。</p>
      <p class="market-sources"><a href="https://yufuin.gr.jp/news/news-5769/">観光局・2026年の運行日とコース ↗</a>
      <a href="https://yufuin.gr.jp/spot/spot-1282/">料金・当日の予約方法 ↗</a></p>
    </article>
  </div>
  <details class="market-season od-civic"><summary>住民の足を支える事業の実績 <span>由布市全域・2025年度</span></summary>
    <p>地域公共交通事業の年間利用者は20,496人（目標45,000人）、事業費は6,347.9万円。市の二次評価は「見直して事業実施」です。ノルクの観光便は、次世代交通実験事業の項目で評価されています。</p>
    <p class="market-sources"><a href="https://www.city.yufu.oita.jp/uploads/files/2026/09/r7zimuzigyouhyoukasyo.pdf#page=14">由布市・事務事業事後評価 本文11〜12頁 ↗</a></p>
  </details>
</section>
'''
