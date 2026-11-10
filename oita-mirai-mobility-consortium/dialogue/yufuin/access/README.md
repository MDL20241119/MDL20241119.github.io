# 湯布院の暗号化配信

対象は `dialogue/yufuin.html` と同じ企画の関連入口、本文に含む画像・図面、提案PDFのみ。他地域の認証設定、DNS、契約、料金、閲覧権限は変更しない。

## 構成

- 本文HTMLは写真・図面・必要なフォントをdata URIで同梱する。
- HTML/PDFをそれぞれgzip圧縮し、PBKDF2-SHA256 600,000回とランダム16byte saltから得た鍵でAES-256-GCM暗号化する。
- 資料ごとにランダム12byte IV、異なるAdditional Authenticated Dataを使用する。
- 公開treeは入口HTML、ゲートJS/CSS、公開manifest、暗号化されたbinだけを含む。平文本文、写真、原図、新PDF、パスワード、復号鍵を公開リポジトリに保存しない。
- ブラウザーはパスワードから鍵を導出し、復号後だけ本文iframeを生成する。画面を覆うだけのパスワードUIではない。
- 関連入口は同じmanifest/key_idを使用。sessionStorageに復号鍵を保持し、同タブのセッションで再入力を避ける。パスワード文字列は保存しない。開いている認証済みタブから同じorigin・同じ資料版の別タブへ、BroadcastChannelの要求/応答で鍵を一時的に渡す。要求nonceと宛先tab IDを照合し、受信鍵でAES-GCM復号できたときだけ受け入れる。localStorageや永続cookieには鍵を保存しない。
- 明示ロックは全関連タブにbroadcastして鍵とiframeを破棄する。閲覧中タブがなく、sessionStorageもない新しいタブでは再入力が必要。通常の全タブ終了でセッションは終了するが、ブラウザーのセッション復元機能がsessionStorageを復元する場合まで失効を保証する方式ではない。更新版のkey_id変更でも再入力となる。別ブラウザー・別端末へは引き継がない。
- PDFは復号したBlobからダウンロードする。旧平文PDFの公開パスは削除し、Yufuin提案を指すリンクのみPDF入口へ変更する。
- 本文は `allow-scripts allow-downloads allow-modals allow-popups allow-popups-to-escape-sandbox` のsandbox iframe。`allow-same-origin`は付けず、親と本文の連携は固定メッセージ型と発信元ウィンドウで限定する。

## 保護の限界

サーバー側の認証・認可ではない。誰でも暗号文を取得できる。短い共有パスワードはオフライン推測に弱く、PBKDF2で完全には防げない。ブラウザーの復号鍵や平文を閲覧者がコピーすることを防げず、コピー済み資料の回収、閲覧者別失効、監査ログ、アクセス元制限もできない。機密性や個別失効が必要な運用には、別途サーバー側の認証と配信制御を選ぶ。

別タブ引継ぎとsessionStorageの信頼境界は同一origin（このサイト全体）。同一originで動く他のスクリプトを信頼する前提であり、パス単位のセキュリティ分離ではない。XSSや別の同一originページに悪意あるコードが入れば、鍵へのアクセスやBroadcastChannel要求を防げない。第三者コンテンツはallow-same-originなしのsandboxに入れる。

旧版HTML・画像・PDFは既に平文公開されていた。現在の公開treeから除外しても、Git履歴、fork、キャッシュ、他者が保存したコピーを回収したことにはならない。旧原図や個人名をこの仕組みに新たに平文投入しない。

## 更新

2026年11月10日版は、現地写真4枚と原図の撮影位置・方向を対応させた3案・10枚構成。西側ピンク地を全案で活用し、交差点で右折して西側へ入る主入口候補を共通条件とする。北側3664-2、公道、水路、既存建物・住宅の条件を保持し、用途・通行・権利を確定扱いしない。PDFと本文は同じ版を同時に梱包する。

パスワードは公開コードや引数に書かず、stdinから渡す。

```text
python3 access/package.py --repo /absolute/repo --html /absolute/build/content.html --pdf /absolute/build/yufuin-hub-proposal.pdf
```

公開前に正しいパスワードでHTML/PDFが開く、誤パスワードと改竄暗号で復号失敗、manifest/key_idが全入口で一致、セッション再利用、明示ロック、未ログイン直URLは暗号のみ、旧平文PDFは404となることを確認する。写真や原図の平文が別URLに混入していないか、変更ファイル一覧とリンクを点検する。
