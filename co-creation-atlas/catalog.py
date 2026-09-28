"""Publish the approved user catalog and an accessible web reading companion."""
from pathlib import Path
import html

PDF = 'atlas-user-catalog.pdf'
PAGES = [
    ('overview', 'まずは、できることから。', '世界の事例を探す。仕組みを比べる。基礎を学ぶ。自分の計画を書く。共創とまちづくりを、実践につなげるためのATLASです。',
     [], [('../', 'ATLASを使ってみる')]),
    ('find', '気になる事例が、見つかる。', '知りたい課題からも、気になる国や地域からも探せます。',
     ['「共創」「まちづくり」「すべてを横断」から入口を選ぶ。', '課題・キーワード・目的・地域で絞り込む。', '「世界地図で探す」に切り替えると、場所から事例を選べます。'],
     [('../#explore', '事例を探す'), ('../?view=map#explore', '世界地図を開く')]),
    ('compare', '同じ問いで、違いが見える。', '運営・費用・必要な支援を見比べ、自分の計画に取り入れたい点を見つけます。',
     ['「共創」「まちづくり」「領域を横断」から見方を選ぶ。', '気になるカードの「比較に選ぶ」にチェック。', '「選んだ事例だけ表示」で、同じ項目を読み比べる。'],
     [('../learn/choose/', '事例を比較する')]),
    ('read', '何をしたか、何が変わったか。', '全87事例を、インプット・価値創造機能・アウトプット・アウトカムの4つの切り口で読めます。',
     ['人・場所・関係・お金など、持ち込んだ資源を知る。', '対話・試作・検証と、そこから生まれたものを読む。', '継続利用や暮らしの変化を、出典・確認時点とあわせて確かめる。'],
     [('../learn/value-creation/', '4つの切り口を学ぶ'), ('../cases/garraway-f/', 'Garraway Fの事例を読む')]),
    ('learn', '必要なところから、学べる。', '21の教材で、基礎・進め方・記入例を確認。必要な工程を行き来しながら学べます。',
     ['初めてなら、リビングラボ・まちづくり・オープンイノベーションの基礎から。', '課題を捉える、仲間をつくる、試す、事業にする。いまの仕事に合う工程へ。', '体制・費用・日常の運営や、仕事が止まったときの教材も。'],
     [('../learn/', '教材の入口へ')]),
    ('plan', '読んだことを、自分の計画へ。', '「実践シート」で、自分の案件を6つの欄に整理します。分かるところから書き始められます。',
     ['課題・指標・仲間・費用・試す方法・継続条件を書き出す。', '入力は同じブラウザに自動保存。文章での保存や印刷もできます。', '別の端末へは「全シートをバックアップ」と「バックアップを読み込む」を使います。'],
     [('../learn/workbook/', '実践シートを開く')]),
]

def e(value):
    return html.escape(str(value), quote=True)

def styles(head, prefix=''):
    return head.replace('</head>', f'<link rel="stylesheet" href="{prefix}catalog.css?v=20260928.1"></head>')

def entry():
    return '<aside class="catalog-entry" aria-label="はじめての方へ"><span>はじめての方へ</span><a href="catalog/">できることカタログを読む <span aria-hidden="true">→</span></a><a class="catalog-entry-pdf" href="catalog/atlas-user-catalog.pdf" download>PDFを保存 ↓</a></aside>'

def build(root, head, header, footer, base):
    dest = root / 'catalog'
    assert (dest/PDF).read_bytes().startswith(b'%PDF-'), 'Approved catalog PDF is required'
    for number in range(1,7):
        assert (dest/f'page-{number}.webp').stat().st_size > 0
    page_head = styles(head('できることカタログ', '事例を探す・比べる・学ぶ・計画する。実際の画面と操作手順で紹介する6ページの利用者向けカタログ。PDFをダウンロードできます。', base+'catalog/', '../'), '../')
    page_head = page_head.replace(base+'assets/aalto-class-2.jpg', base+'catalog/page-1.webp').replace('Aalto Design Factoryの試作授業。Photo: Aalto Design Factory', 'ATLAS できることカタログの表紙')
    out = [page_head, header('../'), '<main id="main" class="catalog-main">']
    out.append('<section class="catalog-hero"><a class="catalog-back" href="../">← ATLASに戻る</a><p class="eyebrow">USER GUIDE / できることカタログ</p><h1>このATLASで、<br>できること。</h1><p class="catalog-lead">探す・比べる・学ぶ・計画する。<br>実際の画面で、使い方をご紹介します。</p><div class="catalog-actions"><a class="btn" href="atlas-user-catalog.pdf">PDFを開く ↗</a><a class="btn catalog-secondary" href="atlas-user-catalog.pdf" download>PDFをダウンロード ↓</a><span>6ページ · 1.3 MB · 2026.09.28版</span></div></section>')
    labels=['概要','探す','比べる','読み解く','学ぶ','計画する']
    out.append('<nav class="catalog-nav" aria-label="カタログの目次">'+''.join(f'<a href="#{p[0]}"><span>{i:02d}</span>{labels[i-1]}</a>' for i,p in enumerate(PAGES,1))+'</nav>')
    for number,(slug,title,description,steps,links) in enumerate(PAGES,1):
        out.append(f'<section class="catalog-page" id="{slug}" aria-labelledby="catalog-title-{slug}"><div class="catalog-copy"><p class="eyebrow">{number:02d} / {labels[number-1]}</p><h2 id="catalog-title-{slug}">{e(title)}</h2><p>{e(description)}</p>')
        if steps: out.append('<ol>'+''.join(f'<li>{e(step)}</li>' for step in steps)+'</ol>')
        out.append('<div class="catalog-page-links">'+''.join(f'<a href="{e(url)}">{e(label)} <span aria-hidden="true">→</span></a>' for url,label in links)+'</div></div>')
        out.append(f'<figure class="catalog-preview"><a href="page-{number}.webp" aria-label="カタログ{number}ページ目を大きく表示：{e(title)}"><img src="page-{number}.webp" width="1516" height="1072" alt="カタログ{number}ページ目：{e(title)}" loading="{"eager" if number==1 else "lazy"}"></a><figcaption>{number} / 6 · 画像を押すと大きく表示できます。</figcaption></figure></section>')
    out.append('<section class="catalog-bottom"><div><p class="eyebrow">YOUR NEXT STEP</p><h2>気になる事例を、ひとつ開いてみる。</h2></div><a class="btn" href="../#explore">事例を探す →</a></section></main>'+footer()+'</body></html>')
    (dest/'index.html').write_text(''.join(out),encoding='utf-8')
    sitemap = root/'sitemap.xml'
    entry = f'<url><loc>{e(base+"catalog/")}</loc><lastmod>2026-09-28</lastmod></url>'
    text = sitemap.read_text()
    if base+'catalog/' not in text: sitemap.write_text(text.replace('</urlset>',entry+'</urlset>'))
