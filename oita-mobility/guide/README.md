# 大分モビリティ・アトラス 2.0：ビジュアルカタログ

2026年9月26日、読者別ガイドと文字の階層を改訂。2026年9月24日版の18ページ構成・実画面・事実関係を保持し、5つの読者別ルート、読むページ、開く機能を明示する。画面の撮影日は9月24日のまま分けて表示する。

- `index.html`：同じ原稿から作るレスポンシブWeb版。実画面はクリックで元の写真を開く。
- `oita-mobility-catalog.pdf`：3:4縦型、18ページ。各ページから対象機能へリンク。
- `screens/`：2026年9月24日に公開サイトを操作して取得した12枚のブラウザー実画面。画面要素やデータの描き替えは行っていない。
- `scripts/catalog/oita-mobility-content.json`：編集用原稿。
- `scripts/catalog/oita-mobility-navigation.json`：5つの読者別ルート、ページ案内、重要語・数字、機能リンク名。
- `scripts/catalog/oita-mobility-screens.json`：撮影URL、日付、画像サイズ、SHA-256。

PEOPLEの操作例は大分駅前からあけのアクロスタウン、ATLASの操作例は大分市からリバーサイド病院。いずれも2026年9月24日を指定。LABの費用比較写真は「操作説明用の仮定」と明記し、改善後23万人・年間追加費用1,200万円を仮入力したもの。実際の施策評価・見積・利用実績ではない。実績記録ボタンは使用していない。

PDFはNoto Sans CJK JP Regular/Black（SIL Open Font License 1.1）をTrueTypeアウトラインへ変換したフォントを埋め込み。英数字はDejaVu Sans Boldを埋め込み。フォントはビルド用で、このリポジトリには同梱しない。静的TTFを次の名称で用意して再生成する。

```bash
python3 scripts/build-oita-mobility-catalog.py --font-dir /absolute/path/to/fonts
# NotoSansJP-Regular.ttf / NotoSansJP-Black.ttf
```

再生成時はPDF全18ページのレンダリング、本文抽出、リンク、Webの小画面レイアウトを確認する。地図内の地理院タイル等の出典表示を保持し、データの取得日と基準日を混同しない。

## 読者別の案内

| 読む人 | まず読むページ | 最初に開く機能 |
| --- | --- | --- |
| 住民・家族・支援者 | P04-06 | PEOPLE |
| 自治体・まちづくり担当 | P07-12（根拠はP14-16） | ATLAS |
| 交通事業者・企画担当 | P10-13（基準はP07） | LAB |
| 病院・店舗・学校 | P09（地域比較はP07-08） | ATLASの送迎資源 |
| 研究・データ担当 | P14-16（詳細分析はP13） | DATA |

PDFの大きなページ番号は実ページと一致させる。P02の色面から該当ページへ移動でき、全ページの下部からP02へ戻れる。Webは役割別の入口、説明への内部リンク、アプリへの外部リンクを分離。重要語・数字のパネルは、指標の単位・解釈上の制約を隣接表示する。例の数値を実績として強調しない。

以前のGoogle Drive PDFを参照して更新。連携アプリに元ファイルの上書き権限がないため、新版PDFをサイト内で直接公開し、サイト内のカタログ導線を新版へ切り替える。従来のDriveリンクは旧版の参照資料として保持する。

- [公開Web版](https://mobilitydlab.com/oita-mobility/guide/)
- [公開PDF](https://mobilitydlab.com/oita-mobility/guide/oita-mobility-catalog.pdf)
- [旧版の参照資料（Google Drive）](https://drive.google.com/file/d/1bTt_c9r_rdCrFj-znXEtuUIngGnVp8Ix/view)
