# 大分未来モビリティ・コンソーシアム

設立に向けた協議案 Ver.0.3 の説明サイト。

- `index.html`: ホームページ
- `guide/index.html`: 12ページの構想説明書（HTML）
- `guide/oita-consortium-concept-v03.pdf`: 同じ内容の配布用PDF
- `site.css`: オレンジを基調とするレスポンシブ・印刷共通スタイル
- `site.js`: モバイルメニューの閉じる操作
- `../scripts/build-oita-consortium.py`: 同一内容からHTMLを生成

編集の原則：任意団体／トヨタカローラ大分＋モビリティデザインラボ共同事務局／運営分の契約・口座・会計はモビリティデザインラボ／個別事業は各実施主体。参画候補と参画確定、構想と実績を混同しない。2026年9月26日受領のVer.0.3を主資料とし、LVOSは成果の考え方だけを参照する。会費、規約の議決方法、参加団体の確定を独自に補わない。

印刷版は `site.css` の印刷スタイルを用い、720 × 960 pt。日本語フォントをローカルに配置し外部サービスへ依存しない。公開サイトに計測タグ・申込フォームは置いていない。

PDF再生成: `python3 scripts/build-oita-consortium-pdf.py --content oita-mirai-mobility-consortium/content.json --guide oita-mirai-mobility-consortium/guide/index.html --font-dir /path/to/fonts --output oita-mirai-mobility-consortium/guide/oita-consortium-concept-v03.pdf`。フルセットのNotoSansJP-Regular.ttf、NotoSansJP-Black.ttfが必要です。

写真とフォントの出典・ライセンスは `assets/photo-sources.json` と `assets/OFL-NotoSansJP.txt` に記載。

## 公開URLと共通コンテンツ
正規URL: https://mobilitydlab.com/oita-mirai-mobility-consortium/
旧 `/oita-consortium/` と旧説明書HTMLは正規URLへ転送。旧PDFリンクも維持。

`explore/` は `oita-events/`、`oita-mobility/`、`oita-mobility/analysis.html`、`mobility-training/` の元ページをiframeで表示します。データ・検索機能・本文の複製はありません。各タブは `?view=events|mobility|analysis|learning` で共有可能。元ページを直接開くリンクを常設します。

トップ: Bauhaus Cartoon（`bauhaus.css`）。Garraway0の実写写真はトップにも掲載。活動の詳細写真: `activity/`。キャラクター画像は内蔵画像生成、Garraway0写真は公式サイト・公式note掲載素材をユーザーの指定で使用。写真出典は `assets/garraway0-sources.json`。コンソーシアム本文・説明書ではモビリティデザインラボを省略しません。

トップの掲載順は、構想の目的 → コンソーシアムの役割 → 運営の基本 → 活動・拠点の写真 → 参加方法 → 構想説明書 → コンソーシアムから生まれたコンテンツ。4つの既存コンテンツは、大きな見出しとカラーパネルで重要な取組みとして紹介。読む順番は、まず構想理解と参加方法を優先します。

メインのキャラクターは `assets/oita-mobility-duo.png`。e-Paletteを思わせる箱型シャトルと空飛ぶモビリティに、温泉の湯けむりと別府湾の波を取り入れたオリジナルイラスト。
