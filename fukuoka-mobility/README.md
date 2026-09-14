# 福岡県 交通データマップ

公開先: https://mobilitydlab.com/fukuoka-mobility/

モビリティデザインラボの大分県版のフォント・レイアウト・構成を踏襲し、薄いピンク背景で福岡県の公開資料に置換した静的サイトです。

## 収録と定義

- 福岡県60市町村。政令市は市単位に統合。500m・1000m区域。
- 国土交通省 N03（2026年行政界）、R6国政局推計の2020年基準人口、鉄道2025年、バス停位置2022年。
- 自治体・事業者の公開GTFS。収録分のみ。時刻表の本数は乗客数ではありません。
- 厚生労働省 医療情報ネット、県内自治体の公共施設CSV、イオン九州の店舗公式案内。
- 福岡市地下鉄の駅別・路線別年度平均乗車人員、2024年度損益、2020年通勤通学OD、北部九州圏PT（佐賀県の一部を含む）。

欠測・非公表・期限外を0にしません。GTFSの構造エラーは計算から除外。施設の0,0座標などは除外し data/facility-audit.json に記録。送迎は公表事例であり車両共用・一般開放を推測しません。詳細は usage.html と data/catalog.json。

地図表示用のGTFS路線形状は約15mの許容誤差で簡略化し、座標を小数点以下6桁に丸めています。計算用・ダウンロード用GTFS ZIPは原典のままです。静的バス停GeoJSONはnull属性キーを省略し、座標を小数点以下6桁に丸めています。

## 更新

Python 3（openpyxl, shapely, pyproj, pyshp）およびNode 24以上を使用。原典URLと取得日の記録を維持し、改訂ファイルの内容・有効期間を確認してから再構築します。

```sh
python3 scripts/fetch-fukuoka.py /path/to/raw
python3 scripts/build-fukuoka-geography.py /path/to/raw
node scripts/build-fukuoka-transport.mjs /path/to/raw
python3 scripts/build-fukuoka-data.py /path/to/raw
python3 scripts/build-fukuoka-catalog.py
node tests/fukuoka-data.mjs
```

index.html は既存ホームページへの入口追加のみ。大分県版は変更しません。通常のローカル確認はリポジトリ直下で `python3 -m http.server`。
