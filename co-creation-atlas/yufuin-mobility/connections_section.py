"""Render the connections chapter of the Yufuin Atlas from its local dataset."""
from html import escape


def _link(label, url):
    return f'<a href="{escape(url, quote=True)}">{escape(label)} ↗</a>'


def _minutes(time):
    hours, minutes = map(int, time.split(':'))
    return hours * 60 + minutes


def _route(route, cutoff):
    columns = ''.join(f'<th scope="col">{escape(name)}</th>' for name in route['columns'])
    rows = []
    for trip in route['trips']:
        minutes = _minutes(cutoff) - _minutes(trip[-1])
        if minutes == 0:
            margin = '締切と同時'
        elif minutes < 0:
            margin = '受付終了後'
        else:
            hours, remainder = divmod(minutes, 60)
            remaining = (f'{hours}時間' if hours else '') + (f'{remainder}分' if remainder else '')
            margin = f'あと{remaining}'
        departure = ''.join(f'<td>{escape(time)}</td>' for time in trip[:-1])
        highlight = ' class="cn-tight"' if minutes <= 1 else ''
        rows.append(f'<tr>{departure}<th scope="row">{escape(trip[-1])}</th><td{highlight}>{margin}</td></tr>')
    name = escape(route['name'])
    return f'''<details class="cn-fold">
  <summary>{name}<span>{len(rows)}便の時刻</span></summary>
  <div class="cn-content"><p class="cn-context">{escape(route['date_note'])}</p>
    <table class="cn-times"><caption class="market-sr">{name}由布院駅前に着く予定時刻と、荷物配送受付終了までの時間</caption>
      <thead><tr>{columns}<th scope="col">配送の締切まで</th></tr></thead><tbody>{''.join(rows)}</tbody>
    </table>
    <p class="market-sources">{_link(route['source_label'], route['source'])}</p>
  </div></details>'''


def render(dataset):
    baggage = dataset['baggage']
    delivery = baggage['station_to_inn']
    collection = baggage['inn_to_station']
    storage = baggage['temporary_storage']
    schedules = ''.join(_route(route, delivery[1]) for route in dataset['routes'])
    hotels = []
    for shuttle in dataset['shuttles']:
        hotel = escape(shuttle['property'])
        links = '　'.join(_link(label, url) for label, url in shuttle['sources'])
        hotels.append(f'''<tr><th scope="row">{hotel}</th><td>{escape(shuttle["station_pickup"])}</td>
        <td>{escape(shuttle["booking"])}<small>{links}</small></td></tr>''')
    listing = baggage['list_as_of'].split('-')
    list_date = f'{listing[0]}年{int(listing[1])}月{int(listing[2])}日'
    return f'''<section id="connections" class="market-section cn-section" aria-labelledby="cn-title">
  <header class="market-head">
    <p class="market-kicker">YUFUIN STATION <span>/</span> 2026.11</p>
    <h2 id="cn-title">駅に着いたら、<br><em>荷物はどうする？</em></h2>
    <p class="market-lead">駅の隣にある「ゆふいんチッキ」は、荷物を宿に届けるサービスと、駅で預かるサービスで受付時間が違います。</p>
  </header>
  <div class="cn-clocks">
    <div><h3>駅から宿へ配送</h3><p><b>{escape(delivery[1])}</b>まで</p><small>{escape(delivery[0])}受付開始。配送先は提携宿。</small></div>
    <div><h3>駅で一時預かり</h3><p><b>{escape(storage[1])}</b>まで</p><small>{escape(storage[0])}から。預けた荷物は営業時間内に受け取ります。</small></div>
  </div>
  <p class="cn-context">公式の対象宿一覧には{list_date}時点で{baggage['eligible_properties']}施設を掲載。宿から駅へ送る場合の回収受付は{escape(collection[0])}〜{escape(collection[1])}です。</p>
  <p class="market-sources">{_link('ゆふいんチッキ・料金と利用条件', baggage['source'])}{_link('配送・回収対象宿一覧（PDF）', baggage['list_source'])}</p>
  <h3 class="cn-heading">到着便と、荷物を送れる時間</h3>
  <p class="cn-copy">大分空港からの<strong>15:00着</strong>は宿への配送締切と同時。<strong>17:00着</strong>は駅での一時預かりも終了する時刻です。表の時間差は予定時刻で計算しており、降車して窓口に移動する時間が別に必要です。</p>
  <div class="cn-schedules">{schedules}</div>
  <div class="cn-example">
    <p class="market-overline">大分空港 17:35発の例</p>
    <h3><b>18:30</b>着。宿の迎えに間に合う？</h3>
    <p>里山茶風の最終迎車は17:00。星の里では前日までに19:30の迎えを予約すれば、到着予定から<strong>60分</strong>あります。</p>
  </div>
  <details class="cn-fold cn-hotels"><summary>由布院駅から宿への送迎<span>5軒の予約条件</span></summary>
    <div class="cn-content"><table><caption class="market-sr">宿泊者向けの駅からの迎車時刻、宿ごとの予約締切と出典</caption>
      <thead><tr><th scope="col">宿泊施設</th><th scope="col">駅での迎え</th><th scope="col">予約方法・公式案内</th></tr></thead>
      <tbody>{''.join(hotels)}</tbody></table>
      <p class="cn-context">各宿が公表した2026年11月4日時点の案内。空席と当日の運行状況は各宿でご確認ください。</p>
    </div>
  </details>
</section>'''
