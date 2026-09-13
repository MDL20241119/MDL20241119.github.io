# 観光・周遊データマップ：ビジュアルカタログ

2026年9月13日の公開アプリを操作して撮影した16画面。PDFは表紙・16機能・最終案内の18ページ。Web版とPDF版は同じ原稿から生成する。

- `/oita-tourism/catalog/`：拡大表示できるWeb版
- `oita-tourism-catalog.pdf`：3:4縦型・18ページ・機能へのリンク付き
- `screens/`：PCブラウザーの実画面。画面要素の合成やデータの差し替えは行っていない。
- `scripts/catalog/`：原稿、撮影URL、画像ハッシュを保持。

前の交通データカタログ（[ビジュアルカタログ](https://drive.google.com/file/d/1bTt_c9r_rdCrFj-znXEtuUIngGnVp8Ix/view)）の「実画面＋対象ユーザー＋３つの手順＋読み方の注意」を引き継ぎ、観光アプリのNeo Swiss配色で制作。

PDFの日本語は[Google FontsのNoto Sans JP](https://github.com/google/fonts/tree/main/ofl/notosansjp)を埋め込み。フォントはSIL Open Font License 1.1。通常400・見出し800の静的TTFを用意して再生成する。

```bash
python scripts/build-tourism-catalog.py --font-dir /absolute/path/to/fonts
```

画面を撮り直す場合は、同じファイル名で画像と `scripts/catalog/screens.json` を更新し、原稿の実装との一致、対象日、PDF全ページ、写真の拡大・閉じる・機能へのリンク、スマートフォン表示を確認する。

地図写真の出典表示は画面内に保持：地理院タイル、交通データは大分県・CC BY 4.0。観光統計の原典・定義はアプリの「使い方・出典」と各指標の詳細を参照。
