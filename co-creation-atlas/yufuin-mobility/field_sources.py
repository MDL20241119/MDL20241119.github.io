"""Render the Atlas's browsable evidence ledger."""
from html import escape


GROUPS = (
    ("訪問を見送る理由と、来訪者・住民の声", ("訪問を見送った理由", "現地の声", "団体の調査漏れ")),
    ("日帰り・宿泊と、地域をまたぐ旅程", ("日帰り・宿泊", "旅行の組み合わせ", "地域間回遊", "宿泊と周遊")),
    ("団体ツアーの時間と受け入れ条件", ("誰が時間を決めるか", "貸切行程", "既存の受け皿", "ツアー実績の取り寄せ")),
    ("観光消費と宿泊統計", ("消費の測り方", "訪日客の市内支出", "支出と泊数", "宿泊施設の供給")),
    ("住民の移動・地域交通とタクシー", ("住民への影響", "住民の交通供給", "交通供給", "住民の移動")),
    ("観光周遊便と手荷物", ("既存観光便", "荷物と乗継")),
    ("2020年の無料デマンド交通実験", ("無料デマンド実験",)),
)


def _value(record):
    unit, value = record["unit"], record["value"]
    if value is None:
        return escape(record["period"] if unit == "期間" else unit)
    number = f'{value:,}'
    if unit == "推計人":
        return f'推計{number}人'
    if unit == "予定分":
        return f'{number}分（予定）'
    if unit == "延べ人以上":
        return f'延べ{number}人以上'
    return escape(number + ("％" if unit == "%" else unit))


def _source(record):
    url = record["source_url"]
    if url.endswith("/000803199.pdf"):
        return ('北九州市公表「ビッグデータ等を活用した訪日外国人観光客の動向等の調査・分析業務」図表3-2。'
                '<a href="downloads/Yufuin-Mobility-Research.pdf#page=9">旧URLで閲覧できないため調査ノートに収録（PDF 9頁）</a>')
    if 'marketing.oita.jp' in url:
        return (f'<a href="{escape(url, quote=True)}">{escape(record["source_location"])} ↗</a>（閲覧に認証を求められる場合があります）。'
                '<a href="downloads/Yufuin-Mobility-Research.pdf#page=9">調査ノート9頁で確認</a>')
    return f'<a href="{escape(url, quote=True)}">{escape(record["source_location"])} ↗</a>'


def _entry(record):
    rid = escape(record['id'])
    return f'''<li class="fd-row" id="fd-record-{rid}">
      <div class="fd-row-head"><span class="fd-no">No. {rid}</span>
        <h4>{escape(record["indicator"])}</h4><strong>{_value(record)}</strong></div>
      <dl class="fd-def"><dt>時点</dt><dd>{escape(record["period"])}</dd>
        <dt>対象・範囲</dt><dd>{escape(record["population"])}</dd>
        <dt>読み方</dt><dd>{escape(record["interpretation"])}</dd>
        <dt>出典</dt><dd>{_source(record)}</dd></dl></li>'''


def render(records):
    by_id = {r["id"]: r for r in records}
    groups = []
    for title, topics in GROUPS:
        members = [r for r in records if r["topic"] in topics]
        groups.append(f'''<details class="fd-group">
          <summary><span>{escape(title)}</span><small>{len(members)}件</small></summary>
          <ul class="fd-rows">{''.join(_entry(r) for r in members)}</ul></details>''')
    return f'''<section id="field-data" class="market-section" aria-labelledby="fd-title">
    <header class="market-head"><p class="market-kicker">FIELD DATA <span>/</span> 資料別索引</p>
    <h2 id="fd-title">湯布院の移動を読む<br><em>{len(records)}件の調査データ</em></h2>
    <p class="market-lead">誰に聞いたか、どの地域を数えたかで、同じ「利用者数」の意味も変わります。テーマを開くと、各値の対象、時点、出典を確認できます。</p></header>
    <div class="fd-context">
    <div><small>湯布院地域の輸送実績</small><h3>暮らしの足</h3>
    <p>2021年10月〜2022年9月に、コミュニティバスは<strong>{_value(by_id["40"])}</strong>、スクールバスは<strong>{_value(by_id["41"])}</strong>が利用しました。</p></div>
    <div><small>由布市営業区域の集計</small><h3>タクシーの供給</h3>
    <p>2024年度末の車両は<strong>{_value(by_id["34"])}</strong>。年度の実働率は<strong>{_value(by_id["35"])}</strong>で、営業区域全体の延べ台日から算出しています。</p></div>
    <div class="fd-unknown"><small>今回の公開資料では未観測</small><h3>夕方に駅で待った時間</h3>
    <p>時間帯ごとの空車台数、依頼から乗車までの分数、乗車を諦めた組数、通院や通学が遅れた件数は、駅での観察や住民・運行者の記録が必要です。</p></div></div>
    <div class="fd-groups">{''.join(groups)}</div></section>'''
