# e-Palette ONE

次の利用に必要な準備をつなぐ、e-Palette共同利用・運行管理Webアプリ。

この版は管理者用の機能検証版です。実車未接続、架空の検証データを使用します。実車連携は本番MVPの必須条件であり、完成済みとは扱いません。

## UI/UX刷新・ログイン不要の体験版（2026-09-26）

URLを開くと、ログインなしで「今日の準備」を使えます。最優先の仕事と期限、時刻順の予定、車両の準備状態を表示。スマートフォンは4つの下部メニュー、大きい文字への切替、64pxの主ボタンを採用しました。予約・取消は内容の明示確認を残します。

- `/`・`/connections`・`/try/approvals/*`：合成データの体験。保存先は各タブのsessionStorageだけで、D1や外部APIには送信しません。タブを閉じると失われることがあります。
- `/workspace`・`/workspace/connections`・`/approvals/*`：認証された利用者専用の保存用管理画面。D1・通常API・MCP・A2Aは従来どおり同じデータを扱います。
- 開発環境でもサーバーAPIの認証は必須です。公開体験の操作は、保存用管理画面や外部AIの予約ではありません。
- [デザイン・操作・検証結果](docs/UI-UX-REDESIGN.md)

追加試験：`node --import tsx --test tests/guest-ui.test.ts`。全68件のローカル自動試験を通過。外部接続・実車試験・高齢者による操作試験・WCAG適合判定は未実施です。

## 開発

Node.js 22.13以降、pnpm。Cloudflare Workers / D1、React 19、Vinext。

```sh
pnpm install --frozen-lockfile
pnpm run db:generate
pnpm run build
node --import ./scripts/sites-env.mjs ./node_modules/wrangler/bin/wrangler.js d1 execute DB --local --config dist/server/wrangler.json --persist-to .wrangler/state --file drizzle/0000_jazzy_ultragirl.sql
pnpm run dev
```

初回だけローカルマイグレーションを適用します。本番のD1と認証ヘッダーはホストが提供します。
GitHub PagesはこのサーバーAPIを実行できません。GitHubでソースを管理し、実行環境はWorkers/D1対応ホストを用います。

```sh
node node_modules/typescript/bin/tsc --noEmit
node node_modules/typescript/bin/tsc lib/model.ts --target es2022 --module es2022 --moduleResolution bundler --skipLibCheck --outDir .test-build
node --test tests/domain.test.mjs
python3 tests/concurrency_test.py
```

- [実装範囲と未接続条件](docs/IMPLEMENTATION.md)
- [要件との受入対応表](docs/ACCEPTANCE.md)

車両接続情報や実際の乗客・注文・運行データは含めません。秘密情報はサーバー側の環境変数で管理します。

## 生成AI・交通標準連携（v1.2）

「その他 → AI・ほかの交通サービスとつなぐ」から検索、充電計算、本人確認を操作できます。同じD1データを使用する通常API、MCP 2026-07-28、A2A 1.0、COMmmmONSの限定アダプターを追加しました。外部AI・交通事業者・実車は未接続です。

- [接続方法・本人承認・未完了条件](docs/AI-INTEGRATION.md)
- [規格別・20項目の適合状況](standards/CONFORMANCE.md)
- [API定義](api/openapi.json)、[MCPツール](api/mcp-tools.json)、[A2Aカード](api/a2a-agent-card.json)
- [原本・版・ハッシュ](standards/registry.json)、[外部接続の記録](standards/connections.json)

```sh
node --import ./scripts/sites-env.mjs ./node_modules/wrangler/bin/wrangler.js d1 execute DB --local --config dist/server/wrangler.json --persist-to .wrangler/state --file drizzle/0001_first_morph.sql
pnpm run test:integration
pnpm run spec:export
```

追加マイグレーションは初回のみ適用します。20件の追加要件試験と10件のサービス照会・取消試験は合成データによるローカル検証であり、20項目すべての外部受入完了を表しません。

乗車予約の一覧から、日時・場所・人数を確認して2操作で取り消せます。`get_service_catalog` を通常API・MCP・A2A共通の13番目の操作として追加。COMmmmONSは19操作中10操作の限定実装です。実車・外部接続、全仕様への適合、高齢者による実操作試験は未完了です。
