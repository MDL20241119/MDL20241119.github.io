# 横のエレベーター：GitHub Pages体験デモ

ユーザー、ドライバー、管理者の3画面を、架空の地域・車両・アカウントで体験する公開デモ。実際の送迎、料金請求、外部通知は発生しない。

- ユーザー入口：`./?role=user`
- ドライバー入口：`./?role=driver`
- 管理者入口：`./?role=admin`

同じブラウザーのIndexedDBに保存する。Web Locksで同一ブラウザー内のタブを直列化し、各処理前後にIDBFSを同期する。別端末・ブラウザー間の共有、本番の本人認証は含まない。入口の選択は認証ではない。

## 共通業務処理

`core-bundle.json` はローカルWebアプリ0.12.0のPython業務モジュールをそのまま含む。各ファイルのハッシュと出典コミットを記録。変更したのは架空fixtureの表示名のみ。予約の確認、権限、席数、状態遷移、取消、操作IDと冪等性はCoreが判断する。JavaScript側に予約ルールを作り直していない。

Pyodide 314.0.7 / Python 3.14.2をWeb Workerで実行する。公式配信先 `https://cdn.jsdelivr.net/pyodide/v314.0.7/full/` に固定し、`tzdata` 2025.3を追加する。公式情報：[Web Worker](https://pyodide.org/en/stable/usage/webworker.html)、[永続化](https://pyodide.org/en/stable/usage/file-system.html)。

PyodideにはOpenSSLのPBKDF2が含まれないため、初期の架空アカウントDBだけは、変更していない元の `app.db.initialize` をネイティブPythonで実行して生成する。パスワードハッシュの計算を弱めたり代用したりしない。DBには本番の秘密・セッション・予約・個人情報を含めない。圧縮した初期DBのSHA-256を確認して展開し、最初の架空の受付と完了履歴は実行時にCoreの通常操作で作る。

`demo_runtime.py` は公開された3つの架空actorに入口を対応付ける薄いアダプター。公開サーバーの認証・認可の代わりとして流用しない。各画面のAPI呼出は `demo-bridge.js` がブラウザー内のCoreへ渡す。GitHub Pagesには予約APIを立てない。

## 再生成と試験

```sh
python3 scripts/yoko-demo/build.py --source /path/to/yoko-elevator
npm install --prefix /tmp/yoko-demo-test pyodide@314.0.7
NODE_PATH=/tmp/yoko-demo-test/node_modules node tests/yoko-demo/run-wasm.cjs
node --check danchi-elevator/demo/demo-worker.js
node --check danchi-elevator/demo/demo-bridge.js
node --check danchi-elevator/demo/app.js
```

WASMの受入試験は実際のPyodide上で、3役・操作確認・停止確認・全乗降・取消・他人の参照拒否・二重送信を検証する。DOMや実ブラウザーでの検証とは別に結果を記録する。

LINEは後工程。国交省・直接API・MCP・A2Aは全体要件として維持するが、公開デモで外部接続・全面適合を表明しない。商用本番のアカウント管理、サーバー共有、正式運行設定・写真・通知・配車相手は元のWebアプリの公開条件に従って別途実装・受入する。

このディレクトリだけを追加し、既存HP・カタログ・他の交通アプリのファイルは変更しない。公開リポジトリへの配置を包括的なオープンソースライセンス付与と扱わない。
