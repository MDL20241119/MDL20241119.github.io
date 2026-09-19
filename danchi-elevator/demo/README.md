# 横のエレベーター：GitHub Pages体験デモ

## 0.14.0：地図とチャットの入力

ユーザー画面は、手順表示→地図とチャット→内容確認→車両確定の流れ。地図のピン、チャット候補、文章入力、人数ボタンは同じ入力内容へ反映する。例：`中央広場から駅前ロータリーへ2人`、`目的地はふれあいセンター`、`2人`。一つ戻る・選び直す・依頼内容の変更にも対応する。

チャットは登録地点を照合するローカルの入力補助で、外部AI・ジオコーディングへの送信はない。不明な場所・同じ乗降場所・範囲外の人数・曖昧な入力は確定せず案内する。入力しただけでは保存しない。元のフォームからCoreの確認ドラフトを取得し、利用者が確認ボタンを押したときだけ依頼を保存する。

地図は既存の `oita-mobility/assets/leaflet.js` / CSS（Leaflet 1.9.4、同ディレクトリにライセンス）を利用する。[国土地理院の淡色地図](https://maps.gsi.go.jp/development/ichiran.html)を表示するが、3つの乗降場所の名称・座標は架空のデモ設定。実在施設の住所・乗車位置を示さない。破線は地点の組合せのみで、経路計算ではない。位置情報は要求しない。背景タイルの取得時は地図の表示範囲と通常のアクセス情報が国土地理院へ伝わる。

引受後の車両確定・到着・乗車は保存済みのCore状態に連動する。車両写真や到着予測を捏造しない。添付マニュアルの写真は再配布していない。

入力解析と画面→Coreの17項目を `tests/yoko-demo/journey.test.cjs` で確認する。`NODE_PATH` にjsdomとPyodide 314.0.7を配置して実行する。実際の地図表示、ピンのタップ、小画面の配置は公開後にブラウザーで別途確認する。

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

デモ本体と専用の生成・試験ファイルだけを追加し、既存HP・カタログ・他の交通アプリのファイルは変更しない。公開リポジトリへの配置を包括的なオープンソースライセンス付与と扱わない。

## 公開・再開記録（2026-09-19）

GitHub Pagesの公開先は `https://mobilitydlab.com/danchi-elevator/demo/`。`?role=user`、`?role=driver`、`?role=admin` で各画面へ直接入る。ページ上部からも役割を切り替えられる。

実際の公開画面で依頼→引受→到着→乗車→降車、別タブの管理者への反映、再読み込み後の保存、取消を確認済み。試験の範囲と限界は `tests/yoko-demo/browser-result.json`、11件のWASM受入結果は `tests/yoko-demo/wasm-result.json` を参照する。

初回公開で判明した起動エラーは、Pyodideが要求するmodule型Workerと `pyodide.mjs` に変更して解消した。Coreのルール変更はない。

次工程は、元のWebアプリを認証付きのサーバー環境へ接続し、別端末間での保存・共有と運用設定を受け入れること。国交省仕様の原本照合、直接API、MCP、A2Aは必須要件として継続する。LINEはWeb版の後工程とする。この静的デモだけを本番運行に転用しない。
