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


### 事業者別データ

`operators.html` で事業者・公表主体を検索し、位置と時刻表等の反映状況を確認できます。県内全事業者の反映は未完了です。再生成順序：`python scripts/build-fukuoka-operators.py` → `python scripts/build-fukuoka-catalog.py`。検証：`python scripts/build-fukuoka-operators.py --check`、`node --test tests/fukuoka-operators.test.mjs`。GTFS追加時は原典・利用条件・有効期間を確認し、交通データを先に再生成してください。


### 事業者の実績・収支を再生成

`operators.html#operator-statistics` で、事業者フィルター、駅別の年度切替・駅名検索・全年度表示・CSV出力、年間輸送量と収支を利用できます。データは `station-ridership.json`、`operator-finance.json`、その原典抽出ファイルです。駅別実績を時刻表や経路計算の代わりに使いません。

再生成はプロジェクトルートから次の順序で実行します。各Pythonコマンドは `--check` で変更せず再現性を確認できます。

```sh
python scripts/build-fukuoka-operator-stats.py
python scripts/build-fukuoka-operator-finance.py
python scripts/build-fukuoka-operators.py
python scripts/build-fukuoka-catalog.py
node --test tests/fukuoka-statistics.test.mjs tests/fukuoka-operators.test.mjs tests/fukuoka-ui.test.mjs
node tests/fukuoka-data.mjs
```

原典を更新する場合、駅別実績は `--source-zip <S12-25_GML.zip>` で県境抽出から再生成（Shapely）、鉄道統計は `--source-dir <取得資料フォルダー>` で読み取ります（openpyxlの読取専用モード）。ファイル名・表セル・年度の対応はスクリプトに固定し、別年度へ無検証で適用しません。出典と取得ファイルのSHA-256を保存しています。西鉄グループと各社単体、2023〜2025年度、乗車・乗降・人キロの単位を混ぜずに表示します。

### 県外GTFS・医療・道路の再生成

原典ファイルのURL、取得日、版、SHA-256は各catalog・audit・source.jsonに記録しています。佐賀県GTFSの元ZIPを`raw/saga-current.zip`、MHLWの8 ZIPを`raw/`、Geofabrikの元PBFを`raw/kyushu-260913.osm.pbf`に用意します。原典はNOTICE.mdからたどれます。キャッシュはリポジトリ外に置いてください。

```sh
python scripts/prepare-fukuoka-crossborder.py /path/to/raw
node scripts/build-fukuoka-transport.mjs /path/to/raw
python scripts/build-fukuoka-medical.py --raw-dir /path/to/raw
python scripts/build-fukuoka-osm.py /path/to/raw/kyushu-260913.osm.pbf --cache-dir /path/to/raw
python scripts/pack-fukuoka-walking.py /path/to/raw/walking-graph.json.gz
python scripts/build-fukuoka-osm-destinations.py
python scripts/build-fukuoka-reference-stops.py
python scripts/build-fukuoka-operators.py
python scripts/build-fukuoka-catalog.py
node --test tests/fukuoka-expansion.test.mjs tests/fukuoka-operators.test.mjs tests/fukuoka-statistics.test.mjs
node tests/fukuoka-data.mjs
```

OSM抽出にはpyosmium（osmium）・shapely、圧縮にはnumpyを使用します。道路の中間JSON・元道路タグはキャッシュに、公開道路グラフと施設抽出はdata/osmに保存します。MHLWは`--raw-dir`を省略すると同梱した県内原典抽出から再現できます。大きい施設原典・診療時刻はgzipで保存し、診療時刻は選択施設の市町村分だけ読み込みます。

この更新で全件取得が完了したわけではありません。主要3者の全便時刻表・PTD-HSの認証・e-Statのダウンロード制限などの条件はNOTICE.mdと画面に明記しています。未取得を0件にしないこと、県外区間を切断しないこと、他社の便数を混ぜないこと、道路接続を創作しないことを検証します。
