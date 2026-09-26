# 大分未来モビリティ・コンソーシアム

設立に向けた協議案 Ver.0.3 の説明サイト。

- `index.html`: ホームページ
- `guide/index.html`: 12ページの構想説明書（HTML）
- `guide/oita-consortium-concept-v03.pdf`: 同じ内容の配布用PDF
- `site.css`: オレンジを基調とするレスポンシブ・印刷共通スタイル
- `site.js`: モバイルメニューの閉じる操作
- `../scripts/build-oita-consortium.py`: 同一内容からHTMLを生成

編集の原則：任意団体／TCO＋MDL共同事務局／運営分の契約・口座・会計はMDL／個別事業は各実施主体。参画候補と参画確定、構想と実績を混同しない。2026年9月26日受領のVer.0.3を主資料とし、LVOSは成果の考え方だけを参照する。会費、規約の議決方法、参加団体の確定を独自に補わない。

印刷版は `site.css` の印刷スタイルを用い、720 × 960 pt。日本語フォントをローカルに配置し外部サービスへ依存しない。公開サイトに計測タグ・申込フォームは置いていない。

PDF再生成: `python3 scripts/build-oita-consortium-pdf.py --content oita-consortium/content.json --guide oita-consortium/guide/index.html --font-dir /path/to/fonts --output oita-consortium/guide/oita-consortium-concept-v03.pdf`。フルセットのNotoSansJP-Regular.ttf、NotoSansJP-Black.ttfが必要です。

写真とフォントの出典・ライセンスは `assets/photo-sources.json` と `assets/OFL-NotoSansJP.txt` に記載。
