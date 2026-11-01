# 自治体のモビリティ　結果と変遷

2026年11月1日の公開対象版。調査基準日は2026年10月31日。特大の見出し・実績数字・単位付きの主要実績表示を追加。利用者から公開承認を受領。

## 変更範囲

- 新規 `/municipal-mobility-history/`：結果を確認した72案件を初期表示。都道府県→自治体コード→案件→結果・年表・原典の探索、検索・絞込・ページ分割・直接URL・戻る操作。
- 既存 `/mobility-policy-history/`：元の黒背景・ビビッドカラー、1枚の選択式地図（初期状態「全体」）、年表、旧ID・原JSON・PDF・Excelを維持。結果の紹介、自治体ページ、政策IDに対応する採択・結果資料の導線を追加。
- 既存ファイルの修正は `mobility-policy-history/index.html` と `assets/history.js` のみ。他ページ、認証、API、DNS、依存関係は変更しない。

## 記録の単位

| 層 | 収録 | 画面 |
|---|---:|---|
| 旧政策・代表事例 | 66政策・111事例・467出来事 | 既存ページを維持 |
| 追加の結果詳査 | 83案件・75自治体・364出来事 | `#projects` / `#case/原ID` |
| 年度別の採択・支援 | 2,120原票（人材支援339を含む） | `#records?layer=selection` |
| 運行等参照 | 497原票 | `#records?layer=reference` |
| 公式掲載資料の点検 | 343記録 | `#records?layer=review` |
| 自治体公式履歴 | 100原票 | `#records?layer=local` |
| 年度履歴索引 | 3,041行 | `#records?layer=history` |
| 自治体マスタ | 1,741自治体 | 都道府県内の名簿・自治体名検索 |

異なる単位を合算して総実証件数とはしない。旧111事例と詳査83案件の同一性を自動で判定・統合していない。同じ原典を共有する2組も、照合候補として表示する。

343点検記録は実績153、結果未取得186、調査成果1、中間結果1、部分実施1、終了のみ1。旧項目 `outcome_report_url` の名称で実績報告と認定せず、343の分類訂正を原票へ適用。申請計画と結果の根拠を別に表示。

自治体の元の調査状態を保持し、詳査75自治体を追加した状態も保存。統合後の「未調査」ラベルは998自治体。これは収録データの調査状態であり、自治体の取組の不存在を表さない。

## 入力の保持と再生成

制作入力は公開ディレクトリーの外に置く。旧原JSON約2.6MB、統合拡張JSON約24MB、追加JSON約6MBを別に読み、ZIP内JSONのバイト一致、10入力のサイズ・SHA-256を確認する。Drive IDや私用Driveリンクを公開データへ転記しない。

```sh
python3 municipal-mobility-history/maintenance/build.py --inputs /absolute/private-input-directory
python3 municipal-mobility-history/maintenance/verify-inputs.py --inputs /absolute/private-input-directory
node municipal-mobility-history/verification/acceptance.cjs
```

2番目の検査だけ制作時の `pypdf` と `openpyxl` を使用。サイトの実行時はHTML・CSS・JSのみ。

`data/provenance.json` は原ID・元ファイル・原票位置・表示ファイルの対応表。各詳細の「原ID・入力資料」でも追跡できる。原記録は25件単位の詳細ファイルへ分割し、公開側の重複投影と原データ削除を区別する。

旧原JSONと統合版baselineは同一ファイルではない。493フィールド差（sources 177、evidence_records 177、timeline 128、aliases 11）を記録し、両方の内容を保持。旧原JSONのバイトは変更していない。補助索引・旧正本・制度対応・分類訂正・検証記録は遅延読込の別ファイルとして保持する。

## 読込と表示

初期データはbootstrapと83案件インデックスの51,962 bytes。地図・JS・CSS・フォントのバイト数は別。約24MBの原JSONを初期ロードしない。2,120件の採択索引は全件検索へ進んだときだけ読み、詳細は25原票ごとに取得する。表示は12件ごとのページ分割で全IDへ到達可能。

数値は入力の単位・対象期間・母数と留保を保持。新たな達成率や採算率は算出しない。費用では初期・運行、予算・報告会計値・監査済み決算を区別。最終の年月記録、資料の公表日、資料確認日を分ける。年のない記録へ日付を補わない。

状態タグは最後に確認できた記録の検索分類。現在のリアルタイム運行を示すものではない。サービス終了3案件と休止・停止2案件は明示IDで分類。実証終了や導入見送りを永久廃止にしない。

## 検証

- `verification/data-reconciliation.json`：入力→索引→詳細のID・件数。主要7層の欠落・重複0。724記述・313詳査出来事・216公式結果関連出来事を保持。
- `verification/input-file-verification.json`：PDF94・79・10ページの全ページ抽出、Excel全22シート解析、9組のID照合。PDF全図表の独立目視再監査ではない。
- `verification/acceptance-results.json`：新規12項目。全72詳細・6,101原票等の画面生成、全ページへの到達、数値訂正、出典参照、分類、個人Drive情報除外。
- 既存の `acceptance.cjs` 14項目、`infographics.cjs` 8項目、`status-map.cjs` 9項目も通過。
- `verification/browser-results.json`：PCと320px・390pxフレームの確認。検索・階層探索・地図・年表・原票・戻る・直リンク・再読込。実機iOS/Safariの確認とは別。
- `verification/source-links.json`：公開URL1,022件の構文検査、代表12URLのHEAD接続確認（200）。全URLのHTTP再監査・本文再読解ではない。

## 持ち運べるプレビュー

```sh
python3 municipal-mobility-history/maintenance/build-review.py --output /absolute/output/mobility-history-review.html
```

2ページと分割データを1つのHTMLへ同梱する。上部で自治体別・政策別・照合結果を切り替える。原典へのリンクは公開元を開く。これは確認用ファイルで、本番サイトへのデプロイではない。

## 残る調査

全国の全自治体・全年度を調べ終えたわけではない。結果未取得186原票、自治体データ上の未調査998自治体、確認時点後の継続、恒常的な財源、因果効果、同一事業の年度横断名寄せは引き続き調査対象。

公開時には最新mainと対象2フォルダーを再照合し、他のWorkの変更を上書きしない。2026年11月1日の公開指示を受け、Draft PR #72を更新してmainへの統合と公開反映確認を行う。

## 特大フォントの公開版

`assets/editorial.css` は見出し・件数・事例名・実績数字を拡大する追加スタイル。`results.js` の数値強調は原文の数字と単位を保持し、日付は通常の文字サイズで表示。主要4案件の実績表示は入力の記述からの引用で、達成率などの計算は行わない。

## 配色の更新

2026年11月1日の追加指示を反映。`assets/palette.css` を最後に読み、チャコール・エレクトリックブルー・オレンジへ統一。本文はアイスシルバー、主要ボタンは白文字のブルー。状態別地図の継続・終了などの意味を持つ色分けは維持する。

2026年11月1日の追加調整：スカイブルー `#7cddf7`、ソフトピンク `#ffacd5`、アプリコット `#ffbb94`、レモン `#fff2a8` に更新。主要ボタンは明るいブルーと濃い文字の組合せ。見出し・実績・副指標に淡いアクセントを配置。
本番公開は統合QAと最新ブランチの競合確認後、公開担当が行う。公開前に最新mainと対象2フォルダーを再照合し、他のWorkの変更を上書きしない。

## 継続更新（2026-11-01）

旧72案件の全フィールド・724記述・313出来事、別層6,101原票、旧政策史の66政策・111事例・467出来事を保持。追加11案件・13自治体・84実績指標・51出来事は別IDで追記し、広域案件の値を自治体別に二重計上しない。予定は実績と別表示。旧検証記録の数は旧入力時点の監査であり、最新差分は `verification/continuation-*.json` を参照。

正本台帳からPDF・XLSX・JSONを同時生成し、同一Driveファイルの更新・readback SHA照合を完了したJSONだけを入力する。私用Drive URL・資格情報・ローカルパスを公開入力に含めない。

```sh
python3 municipal-mobility-history/maintenance/append-continuation.py --input /absolute/private/accepted-ledger-artifact.json
python3 municipal-mobility-history/maintenance/verify-continuation.py --site municipal-mobility-history --input /absolute/private/accepted-ledger-artifact.json
node municipal-mobility-history/verification/acceptance.cjs
```

回収済みの公開投影へ追記できるため、旧私用入力が手元にない場合に `build.py` を再実行して旧層を失う必要はない。旧入力から全面再生成する場合は `build.py` の後で差分adapterを実行する。同一入力2回で公開データのbyte差は0。既存ID衝突・参照不整合・秘密情報は停止対象。内部QA原文は公開せず、範囲と検証結果の要約だけを投影する。

公開直前に最新mainと回収元branchのSHAを再取得し、変化があれば差分を再照合する。公開後はCI・HTTP・配信ファイルhashを確認する。未成功なら旧公開版を維持しpendingを報告する。Drive書込成功はHP公開成功とは別に記録し、公開再試行時にDriveを再書込しない。
