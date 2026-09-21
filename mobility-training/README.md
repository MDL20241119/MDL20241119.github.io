# Evidence-Based Mobility Atlas

公開先: https://mobilitydlab.com/mobility-training/

交通空白37事例と令和7年度人材育成61事業を、項目ごとの出典から探索する静的サイトです。ビルドや外部サービスへの接続は不要です。

## ファイル

- `index.html` / `style.css` / `app.js`: 画面、SOURCEパネル、事例詳細、資料の逆引き、比較、確認事項CSV。
- `atlas-model.js`: 検索、表示、出典使用箇所の抽出。副作用のない関数。
- `data/atlas.json`: 本画面の正本。98件の事例、フィールド、153資料、GAP・タグ、8段階の関係、確認事項、更新履歴。
- `data/methodology.json`: 分類・確認状態・数字・社会実装の定義。atlas内のmethodologyと同時更新。
- `data/ui-verification.json`: 公開画面の操作結果。確認したコミット・画面幅・対象範囲を記録。
- `data/quality-report.json`: 自動検査の結果と検証範囲。PASSは全事実の独立検証完了を意味しません。
- `data/r7-projects.json` / `model.js`: 従来DBの確認記録。今回の再分類前の記録を保持しています。

## 証拠の管理

各フィールドは `id`, `value`, `source_id`, `source_ids`, `kind`, `evidence_level`, `status`, `verification_status`, `last_verified` を持ちます。数字には `unit` と必要に応じて `period`, `qualifier`, `formula`, `inputs` を付けます。

`kind` はFACT / CALCULATION / ANALYSIS / HYPOTHESIS。A–Dは根拠の種類であり点数ではありません。実施状態と情報種別は別軸です。公開資料で見つからない値はnullとNOT_CONFIRMEDで記録し、0・false・NOT_IMPLEMENTEDには変換しません。

GAP分類はMDL ANALYSIS FRAMEWORKです。`source_fact` に原資料の課題要約、`locator` に参照節、`classification_rationale` に分類理由、`temporal_scope` に当時の課題か将来の条件かを保持します。分類なしは空白なしの証明ではありません。タグはSOURCE_TAGとANALYSIS_TAGを分けます。

Graphの関係はSOURCE_CONFIRMED / MDL_ANALYSIS / HYPOTHESIS。資料が関係を明記していない場合は分析・仮説として扱います。各事例の資料確認は、別の地域や全国の因果関係を証明しません。

## 今回の確認範囲

37交通事例は公式事業ページの本文と数表を2026-09-21に取得し、GAP分類を個別に照合。61人材育成事業の内容は既存の項目別確認記録を継承しており、全原典を今回再検証したものではありません。リンクの到達確認は内容照合と別管理です。

大分はユーザー指定の「35活動・750人以上」を表示。750人以上はMDL申告による延べ参加人数であり、ユニーク人数ではありません。原票・算定対象・実証利用者の扱いの突合は未了としてUSER_REPORTEDと確認事項を保持しています。異なる集計の公開noteを750の直接根拠にはしていません。

社会実装は実証後の正式導入・常設サービスまたは運営体制の確立と定義します。従来の広義判定から未確認へ変更した項目は旧状態と変更理由を保持しています。

## 更新手順

1. 原資料のURL、発行者、公開日、対象期間、参照箇所、最終確認日を登録する。公開日不明は推定しない。
2. 対象フィールドの値・単位・期間・状態・根拠を更新する。現在の条件と過去の実証結果を混ぜない。
3. 未解決事項は`quality_issues`に理由・次の確認・担当を記録する。
4. 分類や関係を変える場合は、GAP・タグ・Graphの参照も更新する。
5. `update_log`に対象ID、変更前後、理由、確認日を追記する。
6. リポジトリのルートで `node tests/atlas-evidence.test.mjs` と `node tests/training-database.test.mjs` を実行する。
7. 検索、項目比較、詳細、SOURCE、USED IN、キーボードでの開閉を公開画面で確認する。

## ローカル確認

リポジトリのルートで `python -m http.server 8765` を起動し、`http://localhost:8765/mobility-training/` を開きます。ソースを直接file://で開くとfetchが動きません。

`?project=r7-058`、`?claim=gap-006:activation`、`?source=traffic-426557` で個別項目へリンクできます。既存の `#r7-058` 形式も復元します。
