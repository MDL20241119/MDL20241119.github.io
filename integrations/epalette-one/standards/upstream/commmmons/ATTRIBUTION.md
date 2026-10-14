# 出典・加工・利用条件

出典：国土交通省 COMmmmONS

- [デマンドバスシステム連携API標準仕様書](https://www.mlit.go.jp/commmmons/document/003/)
- [QRチケット相互運用API標準仕様書](https://www.mlit.go.jp/commmmons/document/004/)
- [GTFS-JP v4](https://www.mlit.go.jp/commmmons/document/007/)

原本YAMLは公式ZIPから無変更で抽出し、衝突しないファイル名に保存しました。取得日時、ZIP内パス、バイト数、SHA-256は `../../registry.json` に記録しています。ZIP本体・GTFS-JP PDFは参照用の取得ハッシュを記録し、ここには同梱していません。

国土交通省の[利用条件](https://www.mlit.go.jp/link.html)は特記がない情報に[公共データ利用規約第1.0版](https://www.digital.go.jp/resources/open_data/public_data_license_v1.0)を適用しています。[別条件の一覧](https://www.mlit.go.jp/page/kanbo01_hy_003657.html)と同梱YAMLを確認し、今回のAPI YAMLに別の指定は確認しませんでした。取得日に閲覧した内容に基づきます。ロゴ・第三者コンテンツにこの判断を拡張しません。

`lib/integration/contracts/*.json` は、原本YAMLからdescription/example/examples/summary/titleを除きJSON化した加工物です。型・必須条件・enum・参照等は変更せず、`validators.mjs` はそれをAjvで生成した検証コードです。実装、加工物、試験結果、対応表は本プロジェクトが作成したもので、国土交通省の作成物・認定・適合保証ではありません。
