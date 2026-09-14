# 福岡県交通データマップ

モビリティデザインラボ。元の大分県版と共通のフォント・レイアウト・計算機能を使用し、福岡県の資料に置換。背景色は薄いピンク（#FFF1F5）。

- データの出典・個別利用条件・基準日：`data/catalog.json`、`data/gtfs/catalog.json`、`access/destinations.json`、`access/shopping.json`、`gaps/data/sources.json`。
- 著作権者による本サイトの推奨を意味しません。GTFSの原典ライセンス・帰属を保持。数値・所在地などの事実情報と説明文・写真・商標等の権利を区別。
- Leaflet 1.9.4 は BSD 2-Clause。`assets/leaflet-LICENSE.txt` を同梱。
- MDL独自コードの包括的な再利用ライセンスは未設定。
- 未収録の交通・施設、非公表値、期限外時刻表をゼロとして推測しません。実際の運行・受付・現地の歩行経路は原典や運営者に確認してください。

再構築：`scripts/build-fukuoka-geography.py`、`scripts/build-fukuoka-transport.mjs`、`scripts/build-fukuoka-data.py`、`scripts/build-fukuoka-catalog.py`。公開データの取得日：2026-09-14。
