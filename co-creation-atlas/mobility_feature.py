"""Keep the mobility feature entrance in the Atlas homepage on regeneration."""
from pathlib import Path
import re
import navigation
START = '<!-- mobility-feature:start -->'
END = '<!-- mobility-feature:end -->'
CARD = '''<section class="mobility-feature" id="mobility-analysis" aria-labelledby="mobility-feature-title"><a class="mobility-feature-photo" href="yufuin-mobility/" aria-label="湯布院のモビリティ分析を読む"><img src="yufuin-mobility/assets/street-small.webp" width="700" height="469" alt="由布市が提供する湯の坪街道の風景" loading="lazy" decoding="async"></a><div class="mobility-feature-copy"><p class="eyebrow">MOBILITY ANALYSIS / モビリティ分析</p><h2 id="mobility-feature-title">湯布院へ、<br><em>どう来る？</em></h2><p>車・鉄道・バス。３つの調査を、対象と時期を分けて読む。写真とインフォグラフィックでたどる交通分析特集。</p><a class="mobility-feature-link" href="yufuin-mobility/">湯布院の交通を読む <span aria-hidden="true">↗</span></a><p class="mobility-feature-credit">写真：由布市フォトアルバム／2012年（元画像の日時情報）。<a href="yufuin-mobility/#photo-credits">出典・利用条件</a></p></div></section>'''
STYLE = '''<style id="mobility-feature-style">.mobility-feature{display:grid;grid-template-columns:1fr 1fr;max-width:1360px;margin:72px auto;background:#111719;border:1px solid #3d4547;overflow:hidden;color:#f6f5ed}.mobility-feature-photo{display:block;min-height:400px;overflow:hidden}.mobility-feature-photo img{display:block;width:100%;height:100%;object-fit:cover}.mobility-feature-copy{padding:44px}.mobility-feature-copy .eyebrow{color:#d5ff67;font-weight:800}.mobility-feature-copy h2{font-size:clamp(36px,4.5vw,70px);font-weight:900;line-height:1.22;margin:18px 0}.mobility-feature-copy h2 em{color:#ff78c5;font-style:normal}.mobility-feature-copy>p{line-height:1.85}.mobility-feature-link{display:flex;justify-content:space-between;align-items:center;min-height:52px;margin-top:22px;padding:12px 18px;color:#090b0c!important;background:#d5ff67;border-radius:6px;font-weight:900}.mobility-feature-link:focus-visible,.mobility-feature-photo:focus-visible{outline:3px solid #ff78c5;outline-offset:-3px}.mobility-feature-copy .mobility-feature-credit{font-size:11px;color:#b3babb;margin-top:20px}.mobility-feature-credit a{color:inherit;text-decoration:underline}@media(max-width:760px){.mobility-feature{grid-template-columns:1fr;margin:40px 18px}.mobility-feature-photo{min-height:0;aspect-ratio:1.8}.mobility-feature-copy{padding:26px}.mobility-feature-copy h2{font-size:44px}}</style>'''

def update(root=None):
    root=Path(root) if root else Path(__file__).resolve().parent
    p=root/'index.html';s=p.read_text()
    s=re.sub(re.escape(START)+r'.*?'+re.escape(END),'',s,flags=re.S)
    s=re.sub(r'<style id="mobility-feature-style">.*?</style>','',s,flags=re.S)
    marker='<section class="explorer" id="explore"'
    if s.count(marker)!=1:raise ValueError('Expected a single Atlas explorer entrance')
    s=s.replace(marker,START+CARD+END+marker)
    s=s.replace('</head>',STYLE+'</head>')
    s,n=re.subn(r'<header class="topbar atlas-topbar">.*?</header>',lambda m:navigation.header(),s,count=1,flags=re.S)
    if n!=1:raise ValueError('Expected current Atlas header')
    p.write_text(s)
    sitemap=root/'sitemap.xml'
    if sitemap.exists():
        xml=sitemap.read_text()
        url='https://mobilitydlab.com/co-creation-atlas/yufuin-mobility/'
        if url not in xml:
            xml=xml.replace('</urlset>','<url><loc>'+url+'</loc><lastmod>2026-11-03</lastmod></url></urlset>')
            sitemap.write_text(xml)

if __name__=='__main__':update()
