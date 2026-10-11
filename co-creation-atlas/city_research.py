"""Editorial feature within the place entrance; does not alter the case database."""
from pathlib import Path
URL='/research/fukuoka-startup-policy/'

def integrate(page):
    if 'id="city-growth-feature"' in page:return page
    page=page.replace('</head>','<link rel="stylesheet" href="city-research.css?v=20261011"></head>',1)
    marker='まちづくりの事例を見る <span aria-hidden="true">→</span></a>'
    page=page.replace(marker,marker+f'<a class="city-growth-door-link" href="{URL}">特集：都市の成長と暮らしを読む ↗</a>',1)
    teaser=f'''<aside class="city-growth-feature" id="city-growth-feature" aria-labelledby="city-growth-title"><figure><a href="{URL}" aria-label="都市の成長と暮らしの特集を読む"><img src="{URL}assets/fukuoka-night-unsplash.webp" width="1200" height="800" loading="lazy" alt="福岡タワーと水辺の夜景。2022年公開、撮影日不明"></a><figcaption>Photo: Nichika Sakurai / Unsplash · <a href="{URL}#credits">出典・利用条件</a></figcaption></figure><div><p class="eyebrow">FEATURE / まちづくり・地域運営</p><h2 id="city-growth-title">街は伸びた。<br>暮らしはどう変わった？</h2><p>福岡市と世界10都市の成長を、仕事・所得・住まいから読む。<br>50年先も、100年先も。若者が未来をつくれる街へ。</p><a class="btn black" href="{URL}">都市の成長と暮らしを読む →</a><p class="meta">37枚のビジュアルリサーチ / 2026.10.11<br>MDLの独自調査・提案。行政の公式見解ではありません。</p></div></aside>'''
    page=page.replace('<aside class="expert-teaser">',teaser+'<aside class="expert-teaser">',1)
    return page

def update(path):
    path=Path(path);path.write_text(integrate(path.read_text()))
