# e-Palette ONE

次の利用に必要な準備をつなぐ、e-Palette共同利用・運行管理Webアプリ。

この版は管理者用の機能検証版です。実車未接続、架空の検証データを使用します。実車連携は本番MVPの必須条件であり、完成済みとは扱いません。

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
