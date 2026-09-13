/* Editorial summaries of linked public sources. Counts are calculated by atlas.js.
   Category tags are non-exclusive. Values labelled as goals or interpretation
   must never be rendered as measured results. Verified highlights: 2026-09-13. */
window.ATLAS = {
  updated: '2026-09-13',
  categories: [
    {id:'people', label:'人を運ぶ', en:'PEOPLE', description:'通勤・拠点アクセス・日常の足', example:'EP-003', metric:{value:'6,566',unit:'人',kind:'累計利用者数',note:'2023年9–12月の出退勤シャトル。延べ利用として掲載。',source:'https://toyotatimes.jp/spotlights/1058.html',publisher:'トヨタイムズ / 2024.08.01'}},
    {id:'tourism', label:'観光・回遊', en:'TOURISM', description:'目的地をつなぎ、街を巡るきっかけに',example:'EP-010',metric:{value:'86',unit:'%',kind:'アンケート / 来訪意向',note:'京都旅行の際に出展店舗を訪れたいと回答。実際の来訪率ではありません。',source:'https://toyotatimes.jp/spotlights/1058_2.html',publisher:'トヨタイムズ / 2024.08.01'}},
    {id:'retail', label:'店舗・販売', en:'RETAIL', description:'お店のほうから、お客様の近くへ',example:'EP-009',metric:{value:'88',unit:'%',kind:'アンケート / 体験評価',note:'レジがないことに「スムーズさ」を感じた割合。',source:'https://toyotatimes.jp/spotlights/1058_2.html',publisher:'トヨタイムズ / 2024.08.01'}},
    {id:'entertainment',label:'エンタメ/IP',en:'ENTERTAINMENT',description:'映像・音響・キャラクターと移動を重ねる',example:'EP-016',metric:{value:'9.08',unit:'/ 10点',kind:'アンケート / 総合満足度',note:'「ぼつにゅ〜！なごやツアー！」の公表結果。抽選98名を対象に実施。',source:'https://www.h-products.co.jp/topics/entry/t/2026/04/20/100000',publisher:'博報堂プロダクツ / 2026.04.20'}},
    {id:'logistics',label:'物流',en:'LOGISTICS',description:'人と荷物で、同じ車両を使う',example:'EP-005',metric:{value:'150 → 308',unit:'個/月',kind:'搬送実績 / 貨客混載',note:'2023年11月から2024年2月。専用配送の廃止には至っていません。',source:'https://toyotatimes.jp/spotlights/1058.html',publisher:'トヨタイムズ / 2024.08.01'}},
    {id:'work',label:'業務サービス',en:'WORK & SERVICES',description:'作業やサービスを、必要な現場へ',example:'EP-007',metric:{value:null,kind:'校正工数・休日出勤の削減量',note:'定量成果は公開値未確認。昼休みに現場で工具を校正する実証。',source:'https://toyotatimes.jp/spotlights/1058_1.html',publisher:'トヨタイムズ / 2024.08.01'}},
    {id:'accessibility',label:'アクセシビリティ',en:'ACCESSIBILITY',description:'乗降から目的地の体験までつなぐ',example:'EP-029',metric:{value:'10',unit:'人',kind:'実施前発表 / 参加者の確定数',note:'2026年7月8日発表。ツアーの完了人数や成果を示す数字ではありません。',source:'https://www.city.toyota.aichi.jp/pressrelease/1077298/1077997.html',publisher:'豊田市 / 2026.07.08'}},
    {id:'autonomy',label:'自動運転',en:'AUTONOMOUS',description:'走行技術と、運行を支える仕組み',example:'EP-030',metric:{value:null,kind:'安全性・運行原価の定量成果',note:'公道実証の開始を公表。Level 4に向けた検証段階です。',source:'https://prtimes.jp/main/html/rd/p/000000008.000183366.html',publisher:'NTTモビリティ / 2026.09.03'}},
    {id:'innovation',label:'OI/実証基盤',en:'OPEN INNOVATION',description:'企業が技術やサービスを試せる共通の場',example:'EP-015',metric:{value:'3',unit:'社',kind:'STATION Ai / 実証参加企業',note:'受賞したスタートアップ・パートナー企業による一連の実証。事業化件数ではありません。',source:'https://www.h-products.co.jp/topics/entry/t/2026/04/20/100000',publisher:'博報堂プロダクツ / 2026.04.20'}}
  ],
  eras: [
    {id:'2021',year:'2021',title:'人を運ぶ',stage:'実運用・実証',description:'東京2020の選手村で巡回輸送。多様な利用者の乗降と、安全な運行を経験。',example:'東京2020 選手村シャトル',caseId:'EP-001',source:'https://global.toyota/en/newsroom/corporate/35956185.html'},
    {id:'2022',year:'2022',title:'移動を体験にする',stage:'実証',description:'XR映像・立体音響・座席振動を車内に。移動する時間そのものを体験に変える。',example:'お台場 / 5G・XR・AI',caseId:'EP-002',source:'https://www.docomo.ne.jp/binary/pdf/corporate/technology/rd/topics/2021/topics_220201_00.pdf'},
    {id:'2023',year:'2023–24',title:'モノ・店舗・仕事を動かす',stage:'実証',description:'宮田工場で貨客混載、移動販売、工具校正へ。同じ車両を時間帯で使い分ける。',example:'宮田工場 / 多用途実証',caseId:'EP-008',source:'https://toyotatimes.jp/spotlights/1058_1.html'},
    {id:'2025',year:'2025',title:'街の共用プラットフォーム',stage:'導入・実証',description:'STATION Aiへの定期運行と企業の実証。Woven Cityではサービスを届ける基盤に。',example:'STATION Ai / Woven City',caseId:'EP-015',source:'https://www.pref.aichi.jp/press-release/e-palette2025.html'},
    {id:'2026',year:'2026',title:'地域回遊・自動運転実装へ',stage:'運行・実証',description:'HAMA LOOPでまちなか回遊。武蔵野市で自動運転の公道実証が始まる。',example:'山都町 / 武蔵野市',caseId:'EP-031',source:'https://www.town.kumamoto-yamato.lg.jp/kiji00310654/index.html',source2:'https://prtimes.jp/main/html/rd/p/000000008.000183366.html'},
    {id:'2027',year:'2027年度',title:'Level 4へ',stage:'導入目標',future:true,description:'トヨタはLevel 4に準拠した自動運転システム搭載車の導入を目指すと公表。',example:'将来目標 / 達成実績ではない',source:'https://toyota.jp/e-palette/'}
  ],
  // what, value and learn are concise editorial summaries; evidence qualifiers are explicit.
  summaries: {
    'EP-001': {tags:['people','accessibility','autonomy'],what:'選手村を巡回するシャトルを運行。',value:'低床・スロープで乗降を支援。事故後に運用を見直し。',valueKind:'運用報告',learn:'車両だけでなく、歩行者・誘導・運用を一緒に設計する。'},
    'EP-002': {with:'トヨタ、NTTドコモ、トヨタ紡織、Mobility Technologiesほか',tags:['entertainment','autonomy'],what:'走る車内でXRライブを体験。',value:'移動時間に映像・音響の体験を加える。',valueKind:'検証目的',learn:'移動の便利さに加え、体験への評価も測る。'},
    'EP-003': {tags:['people'],what:'ロッカーと職場を定時シャトルで接続。',value:'往路の移動を徒歩9分13秒から2分11秒へ短縮。',valueKind:'公表実績',learn:'運行時刻を働く人の生活に合わせる。'},
    'EP-004': {tags:['people'],what:'電話で呼べる構内バスを運行。',value:'必要なときに呼び出し、平均4分で乗車。',valueKind:'公表実績',learn:'便数だけでなく、待ち時間と受付負担を測る。'},
    'EP-005': {tags:['logistics','people'],what:'人と事務用品・備品を同じ車両で運ぶ。',value:'人を運ぶ空き空間で配送も担う。',valueKind:'実証内容',learn:'混載量と、専用配送を減らせたかを分けて評価する。'},
    'EP-006': {tags:['people','tourism','entertainment'],what:'工場見学の送迎中に映像を提供。',value:'見学先への移動もブランド体験にする。',valueKind:'検証目的',learn:'到着前から目的地への期待をつくる。'},
    'EP-007': {tags:['work'],what:'校正設備を車内に載せ、現場で作業。',value:'休日の工具回収・返却や校正業務の負担軽減を狙う。',valueKind:'検証目的',learn:'人が出向く前提を、サービスが出向く形で見直す。'},
    'EP-008': {tags:['retail','people','work'],what:'シャトルを売店や作業空間に換装。',value:'食堂から遠い職場へ弁当や飲料を届ける。',valueKind:'実証内容',learn:'需要の時間差と換装の手間をセットで考える。'},
    'EP-009': {tags:['retail'],what:'アプリ認証・決済によるレジなし販売。',value:'レジで支払う手順をなくす。',valueKind:'実証内容',learn:'体験評価と、売上・省人効果の実績を区別する。'},
    'EP-010': {tags:['retail','tourism'],what:'京都の老舗商品を職場で体験・購入。',value:'地域外での商品体験と、本店への来訪意向をつくる。',valueKind:'公表評価',learn:'その場の売上と、その後の来店を別々に追う。'},
    'EP-011': {tags:['entertainment'],what:'公園内で動画・ゲームを楽しむ移動を実証。',value:'移動中に楽しめるサービスを検証。',valueKind:'検証目的',learn:'体験が乗車の動機になるかを確かめる。'},
    'EP-012': {tags:['people','tourism'],what:'園内のパークトレインを代替して運行。',value:'既存ルートで乗り心地・安全性などを検証。',valueKind:'検証目的',learn:'既存サービスとの条件をそろえて比較する。'},
    'EP-013': {tags:['people','autonomy'],what:'May Mobilityの自動運転技術を工場で検証。',value:'構内の移動で自動運転の適用を探る。',valueKind:'検証目的',learn:'走る場所の条件と、運用上の課題を把握する。'},
    'EP-014': {tags:['autonomy','innovation'],what:'構内で自動運転と遠隔監視を検証。',value:'車両の走行と、通信・監視の運用を組み合わせる。',valueKind:'検証目的',learn:'走行性能に加え、監視側の体制も検証する。'},
    'EP-015': {tags:['people','innovation'],what:'駅とSTATION Aiを結び、企業の実証にも活用。',value:'拠点アクセスと、新サービスを試す場を両立。',valueKind:'事業の狙い',learn:'共通の車両・運行基盤を企業の実証に開く。'},
    'EP-016': {tags:['tourism','entertainment','innovation'],what:'地域アーティストの声と立体音響で観光。',value:'総合満足度と支払い意向を確認。',valueKind:'公表評価',learn:'支払い意向を実際の購入・収支につなげて確かめる。'},
    'EP-017': {tags:['people','innovation'],what:'複数の拠点を需要に応じて結ぶ。',value:'乗降ニーズに応じたルートを検証。',valueKind:'検証目的',learn:'利用者の待ち時間と、運行効率を両方測る。'},
    'EP-018': {tags:['work','innovation'],what:'車内で小型モビリティへワイヤレス給電。',value:'乗り継ぐ先の移動機器の充電操作を減らす。',valueKind:'検証目的',learn:'到着後の移動まで含めてサービスを設計する。'},
    'EP-019': {tags:['retail','entertainment','innovation'],what:'Woven Cityでサービス提供の基盤に活用。',value:'暮らしの中で飲食・エンタメなどを試す。',valueKind:'公開された構想',learn:'利用者からのフィードバックを次の改善につなぐ。'},
    'EP-020': {tags:['people','tourism'],what:'台場・青海・有明の拠点をシャトルで接続。',value:'点在する施設の間を移動しやすくする。',valueKind:'サービスの狙い',learn:'乗車数の先に、訪問先や消費が増えたかを見る。'},
    'EP-021': {tags:['retail'],what:'公園やイベントで飲食・グッズを販売。',value:'お店と新しいお客様の接点をつくる。',valueKind:'サービスの狙い',learn:'移動販売が本店への来訪につながるかを測る。'},
    'EP-022': {tags:['people','tourism','entertainment','accessibility'],what:'山下ふ頭のアート会場へ来場者を送迎。',value:'会場までの移動を来場体験の一部にする。',valueKind:'サービスの狙い',learn:'アクセスの負担と、体験の満足度を一緒に見る。'},
    'EP-023': {tags:['people','retail','work','innovation'],what:'市の公用車として送迎・販売・給電などに活用。',value:'複数の用途で車両を共用。',valueKind:'活用方針',learn:'部局をまたぐ予約・運転・費用の管理を決める。'},
    'EP-024': {tags:['people','tourism'],what:'特別展の開催に合わせて博物館へ送迎。',value:'駅側の拠点と文化施設のアクセスを補う。',valueKind:'運行目的',learn:'需要が集まる日と時間に運行を合わせる。'},
    'EP-025': {tags:['entertainment','work'],what:'ラグビー会場で景品交換所として使用。',value:'停車中もイベントのサービス空間になる。',valueKind:'活用内容',learn:'走らない時間の使い方も考える。'},
    'EP-026': {tags:['people','tourism','retail'],what:'北山の文化施設・店舗をつなぎ、多用途を実証。',value:'施設来訪者が周辺の街を巡るきっかけをつくる。',valueKind:'検証目的',learn:'施設の入場者数と、周辺への回遊効果を区別する。'},
    'EP-027': {tags:['people','tourism'],what:'周遊運行とデジタルスタンプ・クーポンを連動。',value:'もう1か所の訪問や飲食利用を促す。',valueKind:'施策の狙い',learn:'クーポン額ではなく、追加の回遊・消費を測る。'},
    'EP-028': {tags:['people','tourism'],what:'ラリーイベントの会場間をシャトルで接続。',value:'集中する来場者の移動を補う。',valueKind:'運行目的',learn:'イベント需要と、日常需要を分けて考える。'},
    'EP-029': {tags:['people','tourism','accessibility'],what:'障がいのある人を含む観光ツアーを企画。',value:'乗車と目的地内の体験を通して使いやすさを検証。',valueKind:'検証目的',learn:'乗り降りだけでなく、旅の全行程を評価する。'},
    'EP-030': {tags:['autonomy','innovation'],what:'武蔵野市で自動運転の公道実証を開始。',value:'走行技術と運行支援の品質を高める。',valueKind:'検証目的',learn:'走行・監視・通信・安全評価の担当をつなぐ。'},
    'EP-031': {tags:['people','tourism'],what:'通潤橋とまちなかを呼出型サービスで結ぶ。',value:'徒歩で巡りきれない場所への回遊を補う。',valueKind:'実証の狙い',learn:'アプリ以外の呼出方法が使いやすいかを確かめる。'},
    'EP-032': {tags:['people','tourism'],what:'美祢駅などと観光地を結ぶ周遊ツアーを計画。',value:'鉄道代行バスと観光地への移動をつなぐ。',valueKind:'計画の狙い',learn:'旅行商品としての購入実績と継続条件を確かめる。'},
    'EP-033': {with:'豊田市、MONET、NTTモビリティ、May Mobility、交通・保険・研究機関',tags:['people','autonomy'],what:'郊外ルートでe-Paletteの自動運転実証を計画。',value:'地域の需要に合う車種と運用モデルを検証する。',valueKind:'計画の狙い',learn:'予定する試験と、すでに得られた結果を区別する。'}
  },
  metrics: {
    'EP-003': {value:'6,566',unit:'人',kind:'利用実績',note:'2023年9–12月の累計利用者数。2024年8月公表。'},
    'EP-004': {value:'4',unit:'分',kind:'平均待ち時間',note:'2台で運行した実証期間。平均利用者数80人/日。'},
    'EP-005': {value:'150 → 308',unit:'個/月',kind:'搬送実績',note:'2023年11月 → 2024年2月。'},
    'EP-008': {value:'5',unit:'分以内',kind:'換装の見通し',note:'スタッフ2人。恒常運用の実績ではありません。'},
    'EP-009': {value:'88',unit:'%',kind:'アンケート結果',note:'レジなしのスムーズさを評価。回答数は出典本文に記載なし。'},
    'EP-010': {value:'86',unit:'%',kind:'来訪意向',note:'京都旅行時に出展店舗へ訪問したいと回答。来訪実績ではありません。'},
    'EP-016': {value:'9.08',unit:'/ 10点',kind:'総合満足度',note:'抽選98名を対象に実施。支払い意向額2,502円（購入実績ではない）。'},
    'EP-029': {value:'10',unit:'人',kind:'参加者の事前確定数',note:'2026年7月8日の実施前発表。完了人数・成果は公開値未確認。'}
  },
  insights: [
    {title:'待ち時間を、短くできたか。',body:'宮田工場では平均待ち時間を公表。便数だけでなく、利用者が必要な移動を実現できたかを見る。',caseId:'EP-004'},
    {title:'意向の先に、行動があるか。',body:'来訪意向や満足度は手がかり。実際の再訪・購入・収益へのつながりは、続けて検証する。',caseId:'EP-016'},
    {title:'一台を、どう使い分けるか。',body:'シャトル・販売・作業の需要を時間帯で組み合わせ、換装工数と運行負担も把握する。',caseId:'EP-008'},
    {title:'移動の全体を、つなげたか。',body:'乗降のしやすさだけでなく、目的地での活動や次の移動まで含めて確かめる。',caseId:'EP-029'},
    {title:'誰が、運行を支えるか。',body:'自動運転の技術に加え、通信・監視・運行・安全評価を担う主体の連携が必要になる。',caseId:'EP-030'},
    {title:'続けられる条件があるか。',body:'参加人数と事業性は別の指標。運行費、負担者、利用収入、継続判断を確認する。',caseId:'EP-032'}
  ]
};
