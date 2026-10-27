# 5事例の写真更新 — 2026-10-27

## 実画像の追加：Ars Electronica Futurelab 4点

公式写真サービス https://photos.ars.electronica.art/ と各個別写真ページは、Ars Electronicaとその活動に関する記事向けに写真を提供し、作品名・アーティスト・撮影者の表示を求めている。その他の用途には事前書面同意を求める。CC BY-NC-ND 4.0の経路と、この関連記事向け編集利用案内を混同しない。

本件は既存の無料・独立したFuturelab解説記事内の写真説明に限る。個別の書面許諾を新たに取得したという意味ではない。広告・営業資料・有料商品・施設との提携表示への転用は含めない。

|assetId|原掲載元|写真が示す対象|
|---|---|---|
|ars-jku-medspace|https://photos.ars.electronica.art/picture.php?/898/category/56|2021年の人体投影と開発チーム。授業風景ではない|
|ars-open-research-talk|https://photos.ars.electronica.art/picture.php?/6255/category/56|2025年POSTCITYの公開トーク|
|ars-hello-worlds|https://photos.ars.electronica.art/picture.php?/14722/category/56|2026年Center公開展示。執務室ではない|
|ars-founding-lab-data|https://photos.ars.electronica.art/picture.php?/8398/category/56|街路での観察・データ収集。屋外活動|

提供画像を無改変保存し、表示時のみ縮小。原比率を保ち、トリミング・色調変更・文字の焼込みを行わない。作品・共同制作者・撮影者をmedia.jsonと各写真の出典欄に保持する。写真から共同開発の効果や導入成果を断定しない。

## 公式写真への案内：4施設・8カード・21場面

Aalto 3カード、ARENA2036 2カード、Newlab Brooklyn 1カード、QUINTBRIDGE 2カード。画像を複製・埋め込みせず、公式掲載ページへ案内する。掲載写真枚数にリンクカードを加算しない。

- Aalto：press albumの用途説明と個別写真のAll Rights Reservedを区別し、追加転載は保留。
- ARENA2036：公式配布・ギャラリーの存在だけで、包括的な転載や加工の許可と扱わない。
- Newlab：公式写真のAll rights reservedを維持。提供元を撮影者と推測しない。
- QUINTBRIDGE：写真配布があっても掲載前の事務局照会条件を省略しない。冒頭の既存写真は同一キャンパスのNTT西日本本社ビル（別棟）で、本施設の館内ではないと案内する。

既存14点の画像と出典・ライセンスは変更しない。Microsoft Garageは別作業が進行中のため変更対象外。既存14点＋追加4点＝この5ページは18点。別作業で更新されたMicrosoft Garageの22点を含めた6ページでは40点。Microsoftの更新コミット9fd61cbcの内容は維持する。

## 再生成・検査

通常の `python3 co-creation-atlas/build.py` にsource-cardレンダラを統合。更新時は既存集約テストに加え `python3 co-creation-atlas/test_photo_sources.py` を実行する。
