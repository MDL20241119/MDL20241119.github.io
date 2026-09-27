# 販売店が、地域の未来をつくるハブになる

町いちばん活動メニューと価値・資金循環カタログ。販売店の経営会議向け。

- [動くHTMLスライド](https://mobilitydlab.com/dealer-mobility-catalog/)：4ページ。活動・記録の深掘り、収入試算、着手条件の確認。Neo Swissの意匠。
- [ページ一覧・数字台帳・操作方法](interactive-notes.md)
- [106枚のカタログ](https://mobilitydlab.com/dealer-mobility-catalog/catalog.html)：従来版。全88掲載記録を収録。
- [A 設計図](https://mobilitydlab.com/dealer-mobility-catalog/blueprint.html)：ガバニングメッセージ、論点、ヘッド台帳、証拠対応表。
- [編集用データ](content.json)：各ページの文言と出所。

## 使い方

カード・棒を押すと右から出所付きの根拠パネルが開きます。会費は有料契約者数を動かして試算し、着手条件はスイッチで仮に確認できます。→／Space、←、1〜4、O（一覧）、D（自動デモ）、Escに対応。#staticと動きを減らす設定では完成状態を表示します。

冒頭と最終ページの共通論点は、①活動、②役割、③還元と負担、④検証です。各個票には、事実、支払者、運営への還流、住民・地元企業・販売店・地域への還元、追加確認を配置しています。

## 出典と確認範囲

添付の調査編PDFと88事例台帳を基に、大分の交通構造資料、LVOS大分構想を照合しました。事例ごとに原表の位置と一次資料URLを記載しています。

88は掲載記録数であり、独立した成功事業数ではありません。総事業費は56記録に記載があり、32記録が空欄です。費用の範囲と期間が異なるため、単純な乗客単価や採算の順位を作っていません。金額不明はxx、地元での展開と還元は提案・仮説として示しています。

**未達**：全88記録の現在の運行・契約・決算、販売店の増分利益、地域の追加所得を確認し切れていません。実施、予算承認、責任者の確定は未実行です。最終ページの30・90・365日は確認工程を設計するための計画上の仮定です。

## 再生成

動く版は`interactive-template.html`と共通データ`content.json`から再生成します。`python build_interactive.py`で単一の`index.html`ができます。従来の106枚版は`content.json`と`blueprint.md`から`render.py`で再生成します。元資料を複製せず、要約・分析と参照先を格納しています。

```bash
python -m pip install Pillow fonttools markdown budoux
python render.py --font /path/to/NotoSansJP.ttf --qa /tmp/dealer-catalog-qa
```

動く版の外部読み込みはGoogle FontsのNoto Sans JPのみ。従来版にはフォントのサブセットを埋め込んでいます。フォントの著作権表示とSIL Open Font License 1.1は[FONT-LICENSE.txt](FONT-LICENSE.txt)に記載しています。

作成日：2026年9月27日。
