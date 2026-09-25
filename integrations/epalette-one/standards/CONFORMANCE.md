# 標準適合・受入状況

2026-09-25。対象はe-Palette ONE v1.1の合成データ検証版です。

**本番MVPは未完了です。20項目を対応づけたローカル自動試験20件の通過と、20項目の外部受入完了を分けます。** 既存業務22件・D1更新SQLのSQLite試験4件も実行済み。対象AI、他交通事業者、QR認証ハブ、実車との接続は0件です。

## 規格別

| 対象 | 実装 | ローカル検証 | 外部テスト接続 | 本番接続 |
|---|---|---|---|---|
| 通常API | 共通業務12操作、確認画面、監査、D1保存 | 業務・本人確認・更新競合、ブラウザで検索→確定 | 未実施 | 未実施 |
| MCP 2026-07-28 | stateless POST、discover/list/call、ヘッダー・入力検証 | Request/Responseハンドラーと原本JSON Schema | 対象AI未接続 | 未接続 |
| A2A v1.0 JSONRPC | AgentCard、SendMessage/GetTask/CancelTask、構造化依頼 | 保存タスクの再送・再開・結果・所有者分離 | 外部エージェント未接続 | 未接続 |
| COMmmmONS デマンド1.0.0 | 19操作中4操作の限定プロファイル | 原本から生成した入出力検査、取消・検索意味 | 交通事業者未接続 | 未接続 |
| GTFS-JP v4 Schedule | 同じ予定から10ファイルのZIP、限定した参照・日時・運賃検査 | 合成ZIPと24時以降、壊れた参照 | 配布先・経路検索側の取込未検証 | 未接続 |
| GTFS Flex | 明示された乗降点・時間帯の変換関数 | 合成窓・booking_rulesの検査のみ | 未実施 | 未接続 |
| GTFS Realtime | 未実装。HTTPは503 | 未接続時の失敗を明示 | 未実施 | 未接続 |
| COMmmmONS QR 1.0.0 | 単回entry通知の内部変換、外部受付は無効 | 合成権利・相手先・再送・二重使用 | 認証ハブ未接続 | 未接続 |

MCPはRequestを直接渡すローカル試験であり、ChatGPT等の実クライアント試験ではありません。A2Aも実相手との相互接続、公式SDK経由の互換試験は未実施です。GTFS検査は本版の限定プロファイルで、GTFS-JP v4全仕様への適合を保証しません。QRの試験用権利台帳は永続化前で、外部口を有効にしてはいけません。

## 追加要件20項目

| ID | ローカル試験で確認したこと | 残る受入条件 |
|---|---|---|
| INT-01 | 共通ticket、空席、通常画面での取消が同一状態になる | 実接続先を含む全経路比較 |
| INT-02 | MCP発見・一覧・呼出・変更案、ヘッダー不一致、原本Schema | 対象生成AI、認証、承認後の実クライアント呼出 |
| INT-03 | A2Aタスク受付・照会・完了・再開・別人拒否 | 実エージェントとのAgentCard取得と通信 |
| INT-04 | 確定再送で二重ticketなし、messageId別内容拒否。SQLite同時再送 | 実ネットワーク切断・タイムアウトからの回復、決済接続 |
| INT-05 | 最終空席、未設定車いす設備、車両・担当者の競合拒否 | 実内装ごとの定員・車いす併用条件 |
| INT-06 | passenger/driver/manager、scope、本人、SQLの別workspace分離 | 実組織の割当、添付・写真・CSV含む認証横断試験 |
| INT-07 | 承認なし、期限切れ、変更後、CSRF不一致、別人・AI承認拒否 | 実AIと本人認証の一連の操作 |
| INT-08 | 承認・ticket・本人IDの記録と状態整合。SQL監査1回 | 実外部ID相関、保存期間・訂正運用 |
| INT-09 | 採用した4操作の原本入出力検査 | 未実装15操作、相手先が要求するプロファイル |
| INT-10 | AND検索、本人予約、取消、未配車をwaitingで保持 | COMmmmONS仮予約・期限・更新の未実装部分 |
| INT-11 | Schedule参照・時刻・日付・運賃、Flex明示窓 | JP v4全検査、区域、予約条件、Realtime・鮮度 |
| INT-12 | ZIP出力と限定検査、外部取込未検証を区別 | 更新配信・外部検索サービスの取込確認 |
| INT-13 | 合成権利の相手先拘束・単回使用・同一/改変再送 | 永続権利台帳、共通QR発券・認証・払戻、認証ハブ |
| INT-14 | 古い/欠測の残量を正常にせず、検索候補・充電を制限 | 正式車両データ・通信断・遅着・矛盾の実接続試験 |
| INT-15 | 普通/急速計算と出発期限、待ち・利用条件不明の明示 | 実車別の検証済み電池・充電モデル |
| INT-16 | 追加role/approved/自由文指示からの昇格・任意命令拒否 | 実AI・外部データを使った攻撃シナリオ |
| INT-17 | 処理失敗はMCP isError、予約成立結果なし | 外部障害・部分成功・照会による回復 |
| INT-18 | demo/source/qualityとSYNTHETICフィード識別 | 本番環境・本番秘密情報の分離を実構成で確認 |
| INT-19 | 12操作の許可リスト、VCI/駆動/扉/鍵/充電開始なし | 正式車両接続後も制御経路がないことを確認 |
| INT-20 | 接続件数0を明示し規格・対象機能を記録 | 対象AI・事業者ごとの試験証跡、版、制約、担当 |

## Web画面の確認

管理画面「その他」→連携画面→EP-01充電計算、便検索→内容確認→確定をローカルpreviewで実操作しました。予約の確定結果、普通/急速の時間、日付を含む期限表示を確認。確定は1回のボタン操作です。65歳以上を含む被験者試験、WCAG 2.2 AA全項目の適合評価、実端末での95% 2秒以内は未実施です。

## 原本と証跡

`registry.json` に固定版、取得元、取得日時、ライセンス、SHA-256を保存。`connections.json` は外部接続を別管理します。ローカル結果は `tests/results/`、再実行方法はREADME。公開した検証版とローカル試験は合成データですが、実行環境・保存データは別です。

## COMmmmONS操作別

以下の「実装」は上の限定条件の実装を表します。仮予約や区域・補助設備を含む全意味条件の適合を表しません。

| 操作ID | HTTP | 実装範囲 |
|---|---|---|
| `getTerms` | `GET /terms` | 未実装：501 |
| `getServices` | `GET /services` | 未実装：501 |
| `getServicesId` | `GET /services/{id}` | 未実装：501 |
| `postPassengers` | `POST /passengers` | 未実装：501 |
| `getPassengersId` | `GET /passengers/{id}` | 未実装：501 |
| `putPassengersId` | `PUT /passengers/{id}` | 未実装：501 |
| `deletePassengersId` | `DELETE /passengers/{id}` | 未実装：501 |
| `getPassengersIdServices` | `GET /passengers/{id}/services` | 未実装：501 |
| `postPassengersIdAgreements` | `POST /passengers/{id}/agreements` | 未実装：501 |
| `getPassengersIdAgreements` | `GET /passengers/{id}/agreements` | 未実装：501 |
| `getPassengersIdReservations` | `GET /passengers/{id}/reservations` | 本人・日付/状態/IDのAND検索・ページング |
| `getStops` | `GET /stops` | 未実装：501 |
| `postReservationsCandidates` | `POST /reservations/candidates` | 指定2点・乗車時刻・一般区分・配車済み便の候補 |
| `postReservations` | `POST /reservations` | 本人確認済みproposalに一致する予約のみ |
| `putReservationsId` | `PUT /reservations/{id}` | 本人予約の取消のみ。その他の変更は未実装 |
| `getReservationsIdPayment` | `GET /reservations/{id}/payment` | 未実装：501 |
| `putReservationsIdPayment` | `PUT /reservations/{id}/payment` | 未実装：501 |
| `getVehicleLocations` | `GET /vehicle-locations` | 未実装：501 |
| `getOperationDelays` | `GET /operation-delays` | 未実装：501 |
