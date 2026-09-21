# 横のエレベーター — 連携コードと検証環境

MDL の元アプリ `yoko-elevator_web_v0.12.0` を再利用した、**合成データ専用のローカル検証環境**です。公開ブラウザーデモとは別の実行環境です。GitHub Pages では Python サーバーは起動しません。国交省・交通事業者・認証事業者の本番環境には接続していません。

公開デモの Python Core 12 モジュールと元アプリの同モジュールが一致することを確認しました。通常 API・COMmmmONS アダプタ・MCP・A2A は同じ Core と DB を使い、予約や定員の処理を別々に実装しません。出所と取り込み前の SHA-256 は [source-import.json](source-import.json) に記録しています。

## 起動と再現

Python 3.12 以降を使用します。依存パッケージの取得時にネット接続が必要です。

```sh
cd integrations/yoko
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-agents.lock
.venv/bin/python scripts/record_tests.py --scope application
.venv/bin/python scripts/start_local_stack.py --agents --enable-mlit-local
```

Windows は `.venv/bin/python` を `.venv\Scripts\python.exe` に読み替えます。

Web 画面は `http://127.0.0.1:8765`、MCP は `http://127.0.0.1:8766/mcp`、A2A は `http://127.0.0.1:8767/a2a` です。Ctrl+C で停止します。画面だけなら `python3 start_web.py` でも起動できます。ローカル DB は `var/` に作られます。実在する利用者の情報を入力しないでください。

利用者・ドライバー・管理者は画面のテスト用ボタンで選択します。アカウントとパスワードは架空試験用で、公開サービスの認証情報ではありません。

## 今回の監査で変更した点

- COMmmmONS の予約更新で、人数変更に紛れた乗降場所・サービスの変更を拒否。
- 任意の車両情報は ID と名称を揃え、未取得の名称を作らない。変更しない任意の定員情報は省略可能。
- 取得済みの乗車予定日時を JST の日付で絞り込み、絞り込み後にページ分割。予定時刻が不明な対象を黙って除外しない。
- 乗降場所検索で、半径だけを明示する不正な組合せを拒否。
- これらの HTTP 回帰テスト 12 件を追加。候補 API の全必須項目欠落と、実 HTTP のタイムアウト後の再送も検証。テスト用 Python の決め打ちを実行中の Python に統一。

変更対象は標準アダプタであり、公開デモの Core と UI はこの取り込みでは変更していません。

## 根拠と限界

[公開適合表](../../danchi-elevator/standards/)に、公開デモ・ローカルソース・外部本番接続の区分を掲載しています。[試験結果](artifacts/test-results/application.json)には実際の試験名と結果があります。全 19 操作には限定条件下の成功系がありますが、19 操作の全要件への適合を意味しません。詳細な採用範囲は [LOCAL_PROFILE.md](LOCAL_PROFILE.md) を参照してください。

通常の予約 API と、AI エージェントの通信方式である MCP/A2A は別の連携層です。MCP/A2A のテスト通過は COMmmmONS 適合の証明ではありません。

原本の COMmmmONS OpenAPI と MCP/A2A の検証用スキーマは、出典・ハッシュ・ライセンスを保って同梱しています。内部検討資料、個人情報、本番 DB、秘密鍵、実サービスの認証情報は含めていません。
