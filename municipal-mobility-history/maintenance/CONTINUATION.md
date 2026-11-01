# 同一台帳から公開データへ追記する

このページは中断Work branchの既存schema・表示・全データ層を土台とする。別schemaへの置換や、自治体名だけでの案件統合は行わない。

## 入力と順序

1. 既存`build.py --inputs /secure/original-inputs`は従来の凍結版を再生成する。旧原JSONと拡張版baselineの493 field差は別保持し、どちらかへ寄せて上書きしない。
2. 継続研究を重複照合し、accepted ledgerからPDF/XLSX/JSONを同時生成・QA。既存Driveの同一file ID更新とreadback SHA照合を完了する。秘密情報・認証設定をこのrepoに置かない。
3. 私用の確定JSONにある`continuous_update_appendix_v1`を以下で追記する。

```bash
python maintenance/append-continuation.py --input /secure/accepted-outcomes.json --site .
python maintenance/verify-continuation.py --input /secure/accepted-outcomes.json --site . --report verification/continuation-schema-check.json
```

Python標準ライブラリと検証用`jsonschema`を使用。ブラウザー実行時の依存は増やさない。入力ファイルは公開checkoutへコピーしない。

## 保持と追加

- 元72詳査のdetail shards、724記述、313出来事、出典、日付精度を不変保持する。
- 採択2120・参照497・資料点検343・自治体公式履歴100・旧代表事例111・年度索引3041・旧政策66・旧出来事467の各層を削除しない。
- 追加案件は`raw.research_case.case_id`という明示IDごとにまとめ、OBS ID・元event ID・metric IDを残す。別案件の類推結合はしない。
- 追加detailだけを新shardへ出力し、index-deep/timeline/municipality links/summary/bootstrap/provenanceを追記する。
- 元templateの再生成後に全accepted ledgerを再適用する。同じ入力の2回目は変更0。更新済みの案件と同一IDで矛盾する新事実は研究側でholdし、承認なく上書きしない。
- 旧非表示の内部診断2ファイルのみ、公開用の検証範囲/件数/注記へ縮約する別privacy処理を許す。元bytesは公開外で保持し、`verification/continuation-reconciliation.json`の例外欄で元SHAと現SHAを区別する。他supportはbyte保持。

## 公開値

新案件のpublic rawは人が読む属性・結果・留保等だけのallowlist。指標・出来事・出典はrootのtyped arraysで保持するためraw内へ二重複製しない。個人連絡先、私用Drive/Library URL、local path、secretは公開しない。

指標の値・単位・対象期間・定義・phase・原典頁を元ledgerと照合する。計画/実績、実証終了/サービス終了を分ける。広域は1案件と関係自治体コードを保持し、自治体ごとに指標を複製しない。教訓は分析と明記する。

summaryの`deep`等は詳査層だけの件数。旧111や採択2120と合算して全国事業数としない。`as_of`は追加層の原典取得日から更新基準日を示すが、出来事の日付や現在稼働の確認日を代用しない。

## 今回の検証

旧72→83詳査、62→75自治体、313→364出来事。新規11案件/13自治体/51出来事/84指標/33出典/62 OBS。旧724＋新62＝786記述。`verification/continuation-schema-check.json`と`continuation-idempotence.json`が検査結果。公開前には既存全UI検査・モバイル表示・戻る/直リンク・全層到達・privacy scanを別途実施する。

## 配信キャッシュの版同期
`sync_release.py` は公開JSONとUI assetsのpath/bytesから決定的releaseを生成し、bootstrapと政策/自治体両HTMLの読込queryを同期する。`build.py`・`append-continuation.py`末尾から自動実行。同一入力・UIならreleaseもbyteも不変。手動UI修正後も実行する。

```sh
python3 municipal-mobility-history/maintenance/sync_release.py
```

UIのJSON読込・scope検証読込は同releaseを使用する。bootstrapと詳査index/summaryの件数が違う場合は内容表示を停止して再読込を案内する。GitHub Pagesのqueryはimmutable snapshotではなく、古いページは配信キャッシュ期限まで残り得る。版queryは新HTMLの依存cache混在を防ぐもので、過去URLの永久再現を保証しない。公開後は通常URLと再読込/戻る、両ページの件数/版を確認する。公開原典URLにはqueryを付加しない。

## 累積バッチ・既存案件の増補（第2バッチ以降）

- `current_batch_id` と `observation_batches` をaccepted ledgerから受け取り、`summary.current_batch.case_ids`で今回の表示対象を決める。IDの接頭辞で選別しない。`#projects?batch=latest`が正式導線、旧`batch=continuation`は同じ集合への互換alias。
- 初回の詳査化は新規事業ではない。今回の「新規詳査」と「既存案件の増補」を別数で表示。`update_existing_case`は既存legacy ID、`baseline_layer=legacy`、同一性根拠と更新理由を要求する。元72詳査への変更は現adapterではholdし、明示の別契約なしに上書きしない。
- adapterを動かす**前**に、accepted累積入力と前公開版から独立期待値を固定する。前公開版の83詳細・111legacyのbyte hashを残す。現在の生成後dataから期待値を作り直してはならない。

```sh
python maintenance/batch-controls.py --input /secure/accepted-outcomes.json \
  --previous-site /secure/previous-published/municipal-mobility-history \
  --output verification/current-batch-controls.json
python maintenance/append-continuation.py --input /secure/accepted-outcomes.json --site .
python maintenance/verify-continuation.py --input /secure/accepted-outcomes.json --site . \
  --report verification/continuation-schema-check.json
node verification/acceptance.cjs
```

- 前バッチのcaseが累積ledgerから欠けた場合は停止。前バッチの詳細snapshotは再パック・書換せず、新規詳細は次のshardへ出力。旧legacyもbyteを変えず、同IDの別層詳査と根拠・異説へのリンクを足す。
- `evidence_conflict=true`のeventは元phase・原eventを保持する一方、確定実績として表示しない。最終確認済み出来事の選出から除外し、詳細と年表で異説表示を優先する。`contradictory_sources`、`correction_note`、`baseline_event_context`を比較できるよう保持する。原典間の相違は確定訂正を意味しない。
- `coverage_scope`は原claim IDを保持した調査範囲メタデータであり、結果の事実には分類しない。
- `sync_release.py`は公開JSON・municipal UI資産・旧policyの`history.js`をhash対象にし、両ページのbootstrap/results.jsと旧policy history.jsを同じreleaseに同期する。固定snapshot配信ではなくキャッシュ区別である。

## 8分類metadata：正本・公開投影・次回の更新順序

正本JSONの`mobility_classification_v1`に全分類台帳を保持する。公開repoには全台帳や内部レビュー本文を重複掲載せず、`data/classification/<layer>.json`（主・副・候補・確認度・目的・状態）と`classification-evidence/<layer>.json`（旧テーマ・公開原典URL/title/locator・公開原記録パス）だけをallowlistで導出する。原研究index/detail/ID/旧themesは書き換えない。`layer:id`の完全一致、元indexとrich detailのfingerprint、JSONschemaを検査し、不一致は停止する。

```sh
python maintenance/import-classification.py --input /secure/latest-drive-outcomes.json --site .
node verification/classification.cjs
```

分類確認は施策記述の分類であり、運行・法的許可・成果の確認ではない。`confirmed`以外はprimary/themesを持たせず、候補はcandidatesに分離する。8入口未判定・対象外の記録も全件/目的検索から到達できる。テーマはOR、地域・年・目的・状況はAND。主分類・副分類の重複でlayer:idを二重計上しない。異年度原票を独立事業数として足さない。

### 新規・変更記録がある次回の安全な順序

1. 研究を重複照合してaccepted累積ledgerへmergeする。前公開版と前分類台帳をprivate snapshotとして保持する。
2. **公開先とは別の一時site**で`append-continuation.py --input /secure/new-outcomes.json --site /secure/staging-site --defer-classification`を実行し、更新indexを作る。このモードは`classification_pending=true`と公開禁止markerを置き、UIを停止する。公開不可。
3. private研究ZIPに収録した分類CLIを`--data-root /secure/staging-site/data --previous /secure/previous-classification.json --output /secure/next-classification.json`で実行する。同じsource fingerprintは既判定保持、新規/変更は候補・未分類へ戻す。自動確定しない。
4. 明示レビューと分類QA後、正本JSONの`mobility_classification_v1`を新台帳に置換してPDF/XLSX/JSONを同ledgerで再生成する。全台帳と内部ルール/研究QAはDrive正本とprivate ZIPに保存する。
5. 最終siteで正本JSONを`append-continuation.py`へ渡す（deferなし）。付属分類は自動的にimportされる。独立importも可能。全ID・fingerprint一致とschemaに合格した場合だけ公開禁止markerを解除する。
6. 受入検査・分類検査・旧policy検査・公開漏洩検査・同入力2回目差分0・browser確認を実施する。分類欠損/古いfingerprint/公開禁止markerのまま公開しない。Drive同ID更新・readbackを確認後、最新Git baseを再照合して公開する。

### 表示と性能

- 初期は詳査101案件＋8入口。原票6,313件分の根拠を初期取得しない。薄い分類は層別、根拠は詳細画面時に層別遅延取得する。全台帳9MB級の初期取得を禁止する。
- 詳査と旧代表事例は`layer`をURLに持ち、一覧・地図・年表で同じ絞込集合を使う。旧111事例の年表はcase関連378イベントのみ。政策89は旧政策頁に保全し、自治体出来事へ混入させない。
- 都道府県の原記載がない記録は地図に推定配置せず、未配置件数を明示して一覧に残す。原票各層は記録単位、詳査は案件単位。候補と結果証拠は別の判定。
- `verification/classification-controls.json`はaccepted分類入力から独立に固定したhash/count/安全回帰例。公開projectionから期待値を作り直してはならない。新分類版の承認後にのみ更新する。
