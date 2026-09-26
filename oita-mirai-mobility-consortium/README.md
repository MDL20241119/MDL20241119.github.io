# 大分未来モビリティ・コンソーシアム

正規URL: https://mobilitydlab.com/oita-mirai-mobility-consortium/

設立に向けた構想・協議案を紹介するサイト。トップは設立基本案 Ver.1.0（全13ページ）を基に2026年9月26日更新。運営・参加の構想説明書は従来の基本案 Ver.0.3を維持しています。

## トップページと根拠

指定資料: https://docs.google.com/presentation/d/1f1kkzJ_9ACYEyJ9NvyuGiNwCVM5htd-JRww_XPNVzMA/edit

資料中の文章は画像として配置されているため、13ページすべてを画像で確認しました。VMVという名称・区分は原資料にはなく、原意をWeb用に整理したものです。正式に承認されたVMVや参画確定を示しません。ページ内にも「設立基本案 Ver.1.0（協議用）の考え方を、Vision・Mission・Valueとして整理」と明記しています。

| 表現 | 根拠ページ | 編集上の判断 |
| --- | --- | --- |
| Vision：若者が大分で挑戦したくなる仕事と産業 | 1・5・13 | 人口減少、仕事の魅力、挑戦・成長・所得を含める |
| Mission：つなぎ、試し、育てて、大分に残す | 1〜3・5・8 | 政策と地域の力を具体化し、成果確認後に各実施主体と事業へ育てる |
| Value 01：地域から始める | 3・8 | 地域の思い・課題を起点にする |
| Value 02：違う得意をつなぐ | 1・9・13 | 分野を越え、人材・技術・知識等を持ち寄る |
| Value 03：試して成果を確かめる | 3・8 | 実証だけで終わらず、成果を確かめて継続へ進む |
| Value 04：大分に残し、次へ回す | 1・6 | 人材・知識・事業も含む成長投資。資金拠出の義務を新設しない |
| モビリティの広い定義・5つの成長テーマ | 2・7 | 産業、若者、観光、技術、暮らしの順。交通だけに狭めない |
| 所得・雇用・地域資産 | 1・6 | 行動原則とは分けて、目指す成果として示す |

情報設計は、VMVを冒頭にまとめる案を採用。MissionとValueを分散する案、5テーマを先頭にする案、現状維持を比較し、依頼された理念の発見性を優先しました。初見の読者による理解度テストは未実施です。

トップの順序: **Vision → Mission → Value → 5つの成長テーマ → 事業を生む流れ → Garraway0の写真 → 参加方法 → 構想説明書 → 生まれたコンテンツ → HOW WE WORK**。運営の基本は最下部に、小さめの見出し・薄いグレー・細い罫線で掲載。

最新のデザイン指定は https://ginger.sakatashop.jp/ 。画面いっぱいの写真・大胆な縦書き・大きな明朝体・余白のある構成を参考にし、カローラを意識したオレンジ（#EF741F）と生成り（#FFFAF3）を基調にしました。画像・ロゴ・文章は参考サイトから転用していません。

## ファイルと編集

- `index.html`: トップページ。現在は直接編集する独立したページ。
- `vision.css`: オレンジと風景写真を中心にしたトップのスタイル。見出しはローカルのNoto Serif JP、本文は従来のNoto Sans JP。
- `bauhaus.css`: 既存の写真・参加・コンテンツ・運営欄の共通スタイル。
- `guide/index.html`: 全12ページの運営・参加の構想説明書（HTML、基本案 Ver.0.3）。
- `guide/oita-consortium-concept-v03.pdf`: 同じ内容の配布用PDF。
- `site.css`: 説明書のオレンジを基調としたスタイル・印刷レイアウト・日本語フォント。
- `site.js`: モバイルメニューの閉じる操作。
- `mascots/`: B-SIDE／キャラクター特設サイト。
- `../scripts/build-oita-mascots.py`: B-SIDEだけを再生成。トップは変更しない。
- `../scripts/build-oita-consortium.py`: 従来の説明書・共通コンテンツ表示ページを生成。旧トップの書き出しは無効化済み。

日本語フォントはローカル配置。公開サイトに計測タグや申込フォームはありません。

PDF再生成: `python3 scripts/build-oita-consortium-pdf.py --content oita-mirai-mobility-consortium/content.json --guide oita-mirai-mobility-consortium/guide/index.html --font-dir /path/to/fonts --output oita-mirai-mobility-consortium/guide/oita-consortium-concept-v03.pdf`。フルセットのNotoSansJP-Regular.ttf、NotoSansJP-Black.ttfが必要です。印刷版は720 × 960 ptです。

## 維持する運営前提

法人を新設せず任意団体として開始。共同事務局はトヨタカローラ大分＋モビリティデザインラボ。運営分の契約・口座・会計はモビリティデザインラボ。個別事業は各実施主体。

これはユーザーの明示指定を優先したものです。新資料の概要4ページ目・発起人案内13ページ目と、詳細9ページ目にはおおいたプラットの運営上の位置づけに差がありますが、今回の更新で運営前提を変更していません。資料に出る組織名は候補・協議案であり、確定先として掲載しません。会費・基金・議決方法・収益分配・発足日の確約は独自に補いません。本文ではモビリティデザインラボを省略しません。

## 共通コンテンツと写真

`explore/` は `oita-events/`、`oita-mobility/`、`oita-mobility/analysis.html`、`mobility-training/` の元ページをiframeで表示。データや本文を複製せず、各タブは `?view=events|mobility|analysis|learning` で共有できます。元ページを直接開くリンクも常設します。トップではコンソーシアムから生まれた重要なコンテンツとして紹介します。

Garraway0の実写写真はトップと `activity/` に掲載。公式サイト・公式note掲載素材をユーザー指定で使用し、既存拠点・公開イベントの写真であると記載。出典は `assets/garraway0-sources.json`、その他の写真とフォントの情報は `assets/photo-sources.json` と `assets/OFL-NotoSansJP.txt`。

旧 `/oita-consortium/` と旧説明書HTMLは正規URLへ転送。旧PDFリンクも維持。

## B-SIDEとキャラクター

特設サイト: https://mobilitydlab.com/oita-mirai-mobility-consortium/mascots/

基本56案と追加6案、計62案を掲載。名前・モチーフ・説明・表示範囲は `mascots/catalog.json` に集約。生成画像そのものは変更せず、CSSの枠で表示します。

上位5体は、かぼすエア、ゆけむりパレット、うさぐうパレット、たかモンライド、うさパレット。やせうまスクーターはユーザー指定の常設枠。トップには大きな紹介欄も順位表示も置かず、6体を43〜88px程度の小さなアクセントとして分散し、各画像から特設サイトの紹介へ移動できます。主メニューからキャラクターを外し、特設サイトのテキストリンクはフッターに配置。

人気投票はユーザー指定によりシミュレーション。実際の投票・アンケートや需要予測ではありません。主観評価5項目、仮想の好み4類型、仮想1,000票、固定乱数で比較。仮定と全得票は `mascots/simulation.json`。`python3 scripts/simulate-oita-mascots.py` で再現できます。B-SIDEは6体紹介→選定方法→全62案図鑑の順で、検索を維持しています。

## 風景写真（2026年9月26日追加）

由布市フォトアルバムの由布岳（春）、由布岳と列車、金鱗湖（紅葉）、別府市フォトギャラリーの鳥越大橋からの景色を採用。各公式ページで営利利用を含む無償利用条件を確認し、ページのフッターに出典を掲載しています。色や被写体は変更せず、Web向けの縮小と圧縮、CSSの表示枠によるトリミングのみ。元画像素材を配布する目的ではありません。出典URL・画像URL・利用条件は `assets/scenery-sources.json`。スマートフォンには軽量版を配信します。
