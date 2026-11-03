"""Server-rendered lodging and itinerary section of the Yufuin feature."""
from html import escape


def source_link(url, label):
    return f'<a href="{escape(url, quote=True)}">{escape(label)} ↗</a>'


def render(dataset):
    occupancy = dataset["occupancy"]
    months = occupancy["months"]
    peak = max(months, key=lambda row: row["occupancy_percent"])
    trough = min(months, key=lambda row: row["occupancy_percent"])
    bars, rows = [], []
    for row in months:
        month = row["month"]
        rate = row["occupancy_percent"]
        accent = " stay-peak" if row == peak else " stay-trough" if row == trough else ""
        bars.append(f'''<div class="stay-month{accent}">
          <div class="stay-axis"><div class="stay-bar" style="height:{rate}%"><b>{rate:.1f}</b></div></div>
          <span>{month}月</span></div>''')
        rows.append(f'''<tr><th scope="row">{source_link(row["source_url"], str(month) + "月")}</th>
          <td>{rate:.1f}%</td><td>{row["responding_facilities"]}</td><td>{row["occupied_room_nights"]:,}</td></tr>''')

    tour_rows = []
    for tour in dataset["tours"]:
        tour_rows.append(f'''<div class="stay-tour"><dt>{escape(tour["label"])}<strong><small>約</small>{tour["minutes"]}<small>分</small></strong></dt>
          <dd>{escape(tour["schedule"])}<p class="market-sources">{source_link(tour["url"], tour["source"])}</p></dd></div>''')

    next_visit = dataset["next_visit"]
    n = next_visit["n_next_place"]
    destinations = "".join(
        f'<tr><th scope="row">{escape(p["place"])}</th><td>{p["people"]}人</td><td>{p["people"]/n:.1%}</td></tr>'
        for p in next_visit["top_places"]
    )
    source = dataset["survey"]
    return f'''<section class="market-section" id="stay-patterns" aria-labelledby="stay-patterns-title">
      <header class="market-head"><p class="market-kicker">ROOMS &amp; ITINERARIES</p>
        <h2 id="stay-patterns-title">客室の稼働率は、<br><em>月でどう変わる？</em></h2>
        <p class="market-lead">由布市内の従業者10人以上の回答施設では、2025年の客室稼働率は{peak["month"]}月が<strong>{peak["occupancy_percent"]:.1f}%</strong>、{trough["month"]}月が<strong>{trough["occupancy_percent"]:.1f}%</strong>。月平均に{peak["occupancy_percent"]-trough["occupancy_percent"]:.1f}ポイントの開きがありました。</p>
      </header>
      <figure class="stay-figure"><figcaption>月別の客室稼働率 <span>由布市 · 2025年 · ％</span></figcaption>
        <div class="stay-chart" aria-hidden="true"><div class="stay-semester">{"".join(bars[:6])}</div><div class="stay-semester">{"".join(bars[6:])}</div></div>
        <p class="market-note">調査対象は毎月{occupancy["target_facilities"]}施設、回答は15～20施設。予約時に希望の価格や食事条件で空室があったかは、宿泊日と予約日ごとの販売在庫で確かめます。</p>
      </figure>
      <details class="market-season"><summary>12か月の数値と原表を見る</summary>
        <table class="market-table stay-grid"><caption>月を選ぶと観光庁の各月の原表（Excel）が開きます。</caption>
        <thead><tr><th scope="col">月</th><th scope="col">稼働率</th><th scope="col">回答施設数</th><th scope="col">利用客室数<br>（延べ室）</th></tr></thead><tbody>{"".join(rows)}</tbody></table>
      </details>
      <p class="market-sources">{source_link(occupancy["source_url"],"観光庁・宿泊旅行統計　参考第5・11・12表")}</p>
      <div class="market-pair">
        <article class="market-panel"><p class="market-overline">団体旅行の滞在時間</p><h3>行程表にある<strong>散策の時間</strong></h3>
          <p>博多発の日帰り商品でも、湯布院に着く時刻と滞在枠は旅程によって変わります。</p>
          <dl class="stay-tours">{"".join(tour_rows)}</dl>
          <p class="market-note">2商品の予定行程。実際の滞在時間は、当日の到着から出発までを測ります。</p>
        </article>
        <article class="market-panel"><p class="market-overline">宿泊後の広域移動</p><h3>翌日の最初の<strong>立ち寄り先</strong></h3>
          <p>由布市に宿泊したと判定された韓国人アプリ利用者{next_visit["n_lodgers"]}人のうち、翌日の最初の滞在先が分かった{n}人の上位3地域です。</p>
          <table class="market-table"><caption class="market-sr">2018年度の位置情報による翌日最初の滞在先。333人のうち上位3地域</caption><thead><tr><th scope="col">立ち寄り先</th><th scope="col">人数</th><th scope="col">割合</th></tr></thead><tbody>{destinations}</tbody></table>
          <p class="market-note">{next_visit["period"]}の位置情報。1km四方の区画に30分以上いた場所を滞在先としています。</p>
          <p class="market-sources">{source_link(next_visit["url"],next_visit["source"])}</p>
          <p class="market-note">原表の配布先は閲覧に認証を求める場合があります。<a href="downloads/Yufuin-Mobility-Research.pdf#page=9">調査ノート9頁で確認</a></p>
        </article>
      </div>
      <p class="stay-spend-note"><strong>時間が増えると、買物も増える？</strong> 市の周遊バスツアー助成では行程表と参加者の買物額帯を集めています。あと30分でどの店に立ち寄り、いくら使うかを知るには、同じ旅行組の実滞在時間と地区別の支出を照合し、条件の近い通常の行程と比べる必要があります。</p>
      <p class="market-sources">{source_link(source["url"],source["source"])}</p>
    </section>'''
