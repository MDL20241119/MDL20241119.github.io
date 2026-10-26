# 地域・団体別の提案PDF

一覧カードと各詳細ページの上部・末尾から、対応するPDFを直接ダウンロードできます。既存デザイン・カードリンク・閲覧入口は維持しています。

対象は別府市、由布市（湯布院）、日出町、宇佐市（安心院含む）、国東市、臼杵市、大分市、太陽の家の8提案です。

- HTML: `index.html` と8地域・団体の既存ページ
- 追加スタイル: `assets/proposal-downloads.css`
- PDF: `pdf/<ページ名>-proposal.pdf`
- 生成スクリプト: `scripts/build-proposal-pdfs.py`

PDFには既存ページの提案本文、図の説明、写真と出典、交通政策・検討論点・原典を収録します。企画例・検討用ドラフトであることを維持します。

## 内容を更新した場合

ページ本文を変更した場合は、生成スクリプトの冒頭に記載した依存ライブラリと日本語フォントを用意し、PDFを再生成してください。

```bash
python3 scripts/build-proposal-pdfs.py --font-variable /path/to/NotoSansJP-variable.ttf
```

HTML・CSS・PDFを同じGitHub Pagesの公開変更に含めます。PDFはブラウザー印刷や外部サービスに依存しない静的ファイルです。生成処理は外部URLを取得しません。
