"""由布市の訪日客支出・宿泊。四半期は公表された期間別の集計値を使う。"""

from datetime import date
from html import escape


def render(data):
    area = escape(data["area"])
    period = escape(data["period"])
    checked = date.fromisoformat(data["checked"])
    quarter_rows = "".join(
        f'<tr><th scope="row"><a href="{escape(q["url"])}">{escape(q["period"])}</a>'
        f'<br><small>{q["n"]:,}件</small></th><td>{q["spend_yen"]:,}円</td>'
        f'<td>{q["mean_nights"]:.1f}泊</td><td>{q["overnight_pct"]:.1f}%</td></tr>'
        for q in data["quarters"]
    )
    spend_rows = "".join(
        f'<tr><th scope="row">{escape(label)}</th><td>{amount:,}円</td><td>{pct:.1f}%</td></tr>'
        for label, amount, pct in data["spending"]
    )
    return f'''<article class="market-panel" id="inbound-spending-update" aria-labelledby="inbound-spending-title">
  <p class="market-overline">{period}　｜　{area}を訪れた外国人旅行者</p>
  <h3 id="inbound-spending-title">訪日客は、市内でいくら使い、何泊したか</h3>
  <dl class="market-kpis">
    <div><dt>市内での1人当たり支出</dt><dd>{data["spend_yen"]:,}<small>円</small></dd></div>
    <div><dt>平均泊数（日帰りを含む）</dt><dd>{data["mean_nights"]:.1f}<small>泊</small></dd></div>
    <div><dt>市内宿泊率</dt><dd>{data["overnight_pct"]:.1f}<small>%</small></dd></div>
  </dl>
  <p class="market-note">支出の設問に答えた{data["respondents"]:,}件が対象。民泊・友人宅での宿泊を含みます。上の2025年通年値とは7〜12月の6か月が重なるため、期間差を前年比としては使えません。</p>
  <details class="market-season"><summary>四半期別の支出・宿泊を見る</summary>
    <table class="market-table"><caption class="market-sr">四半期別の回答件数・1人当たり市内支出・日帰り込みの平均泊数・市内宿泊率</caption><thead><tr><th scope="col">調査期・回答</th><th scope="col">支出</th><th scope="col">平均泊数</th><th scope="col">宿泊率</th></tr></thead><tbody>{quarter_rows}</tbody></table>
  </details>
  <details class="market-season"><summary>1人当たりの支出内訳を見る</summary>
    <table class="market-table"><caption class="market-sr">{period}の市内支出の内訳</caption><thead><tr><th scope="col">費目</th><th scope="col">1人当たり</th><th scope="col">構成比</th></tr></thead><tbody>{spend_rows}</tbody></table>
    <p class="market-note">訪問地間の交通費と団体・パック参加費は集計対象外。宿泊費には日帰りなどの0円を含みます。公表値の丸めにより、費目の合計と総額に1円の差があります。</p>
  </details>
  <p class="market-note">観光庁「インバウンド消費動向調査」B1地域調査の個票を、アンド・ディが大分県のウェイトを用いて独自集計。公表元の「最新1年」は更新されます。ここでは{checked.year}年{checked.month}月{checked.day}日確認時の4四半期を表示しています。</p>
  <p class="market-sources"><a href="{escape(data["source_url"])}">由布市の公表表を見る ↗</a><a href="{escape(data["method_url"])}">対象と集計方法 ↗</a></p>
</article>'''
