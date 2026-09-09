# 大分 交通データ：出典と権利表記

確認日：2026年9月9日。対象は `/oita-mobility/` の公開デモです。

## データの利用条件

| 対象 | 提供元・出典 | 条件・加工 |
| --- | --- | --- |
| GTFS 16ファイル | 大分県。各交通事業者のデータ名・URLは [catalog.json](data/gtfs/catalog.json) に記載 | CC BY 4.0。ZIPは取得時のもの。サイトで停留所・路線を抽出・集計。ユーザーの変更案は加工物。 |
| 病院147施設 | [厚生労働省 医療情報ネット](https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/kenkou_iryou/iryou/newpage_43373.html)、2026年6月1日 | PDL1.0。大分県の病院を抽出し必要な項目を整形。 |
| 公共施設等29施設 | 別府市・日田市・日出町・玖珠町。個別URLは [destinations.json](access/destinations.json) | CC BY 4.0。施設を抜粋・加工。 |
| 行政区域・人口 | 国土交通省。詳細は [sources.json](gaps/data/sources.json) | CC BY 4.0。行政界の統合・簡略化、メッシュ作成、2020年基準人口列の抽出。行政区域N03の測量法上の二次利用手続は別途確認が必要。 |
| 背景地図 | [国土地理院 地理院タイル](https://maps.gsi.go.jp/development/ichiran.html) | 地理院タイルをリアルタイムで読み込み、MDLの図形を重ねる。出典リンク・個別条件を維持。 |
| 店舗・送迎等 | 各公式サイト。個別出典は施設データと [resources.json](gaps/resources.json) | 所在地・運行条件等の事実情報を整理。一括のオープンライセンスは未確認。埋込地図由来の概略位置を含め、再配布条件は個別確認事項。 |
| 公表乗降・OD・費用 | 各国・自治体資料。個別出典は [analysis.json](data/analysis.json) | 数値を抜粋・整理。元の報告書、図版、写真、説明文全体に再利用許諾を付与するものではない。 |

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.ja) / [PDL1.0](https://www.digital.go.jp/resources/open_data/public_data_license_v1.0)

再利用時は元データの出典、適用ライセンス、加工した旨を維持してください。個別の条件や第三者の権利は各提供元で確認してください。出典の表示は、提供元によるMDLの分析の認定・推奨・監修を意味しません。

## ソフトウェア

Leaflet 1.9.4（`assets/leaflet.js`、`assets/leaflet.css`、関連アイコン）は BSD 2-Clause License です。

- Copyright (c) 2010–2023, Volodymyr Agafonkin
- Copyright (c) 2010–2011, CloudMade
- [ライセンス全文](assets/leaflet-LICENSE.txt)を同梱しています。再配布時も著作権表示・条件・免責文を保持してください。

MDL独自部分には現時点でMIT等の再利用ライセンスを設定していません。無料でデモを使えること、GitHubでコードを閲覧・forkできることと、包括的な改変・再配布許諾は同一ではありません。独自コードと解説の公開ライセンスは、権利帰属と適用範囲を確認して設定する事項です。

## 名称・画像・既存サイト

元の紹介パンフレットの写真・図版はこのデモの配布物に含めていません。機能比較の参考リンクは、参照した製品・企業との提携や監修を示しません。

MDLや第三者の名称・商標・ロゴ、既存の企業サイト（リポジトリルート）の写真・文章は、上記データやライブラリーのライセンスの対象ではありません。この文書は新たな第三者権利を許諾するものではありません。

訂正・権利に関する連絡先：info@mobilitydlab.com
