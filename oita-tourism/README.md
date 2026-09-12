# 大分観光・周遊データマップ

観光ページの入口は `index.html`。交通データは隣の `oita-mobility` と共用します。

## 利用の流れ

1. 「観光地へ行く」で出発地と行き先を選ぶ。旅行当日は公共交通・車の経路確認を開く。
2. 出発・帰着・滞在・乗車時間を選び、収録日の直通往復候補を確認する。
3. 「現地を回る」で近くの乗り場と次の立ち寄り先を確認する。
4. 「交通分担・比較」で国内客・海外客の利用割合や同系列の統計を確認する。
5. 「データを探す」で対象・出典を開き、絞り込んだCSVを保存する。

自治体・観光協会、宿泊・観光施設、交通事業者には地域別の検証項目を用意。旅行者・案内者にはアクセスの入口を用意しています。

## データ更新

```sh
python scripts/import-tourism.py /path/to/oita_tourism_data.xlsx
node scripts/build-tourism-access.mjs
python scripts/build-data-catalog.py
node --test tests/tourism.test.mjs
node tests/data-catalog.mjs
node tests/publication.mjs
```

コマンドはリポジトリ直下で実行。観光JSONは観測値・原表行・出典を保持する正規化データで、自動更新される外部データベースではありません。新資料は定義・利用条件を照合して更新してください。市町コード、GTFS feed ID / stop ID、原典URLで接続します。

`data/access.json` は共通GTFSから再生成する軽量な索引形式。`access-model.mjs` の `unpackAccess` で出典付きの明細に戻ります。同じtripが複数地点間・日付に現れるため、明細数を固有便数として使いません。

直通の停留所間候補のみ。徒歩経路、施設入口・営業時間、乗り換え、空席、運賃、バリアフリー、リアルタイムの混雑は別途確認が必要です。複数回答の交通利用割合を、100%分担率や地点別需要へ変換しません。

## 表示確認

`tests/responsive.html` から観光・周遊を選び、320 / 390 / 768 / 1440pxで確認できます。背景地図は地理院タイル、経路確認はGoogle マップです。
