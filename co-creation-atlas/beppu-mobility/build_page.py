"""Build the source-visible Beppu feature from attributed, versioned observations."""
from pathlib import Path
import json,html,csv
P=Path(__file__).resolve().parent
D=json.loads((P/'downloads/Beppu-Tourism-Data.json').read_text())
e=html.escape
fmt=lambda n:f'{n:,}'
C=['#ff83b2','#6cd6ff','#d3fa73','#ffa86d','#a995ff']
pdf=D['primary_source']['pdf']; xlsx=D['primary_source']['xlsx']
def link(url,label):return f'<a class="source-link" href="{e(url)}">{label} ↗</a>'
def table(caption,headers,rows,wide=False):
 return '<div class="table-scroll" tabindex="0" role="region" aria-label="'+e(caption)+'"><table'+(' class="wide-table"' if wide else '')+'><caption>'+caption+'</caption><thead><tr>'+''.join('<th scope="col">'+h+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(('<th scope="row">'+str(v)+'</th>') if i==0 else '<td>'+str(v)+'</td>' for i,v in enumerate(row))+'</tr>' for row in rows)+'</tbody></table></div>'
def detail(label,content):return '<details><summary>'+label+'</summary>'+content+'</details>'
def ring(items,total,center,label,unit="人"):
 offset=0;circles=[];legend=[]
 for i,(name,val) in enumerate(items):
  pct=val/total*100
  circles.append(f'<circle class="ring-segment" cx="60" cy="60" r="45" pathLength="100" stroke="{C[i]}" stroke-dasharray="{pct:.5f} {100-pct:.5f}" stroke-dashoffset="{-offset:.5f}"/>');offset+=pct
  legend.append(f'<li><i class="dot" style="--swatch:{C[i]}"></i><span>{name}<br><span class="micro">{fmt(val)}{unit}</span></span><strong>{pct:.1f}<small>%</small></strong></li>')
 return '<div class="donut-layout"><div class="donut"><svg viewBox="0 0 120 120" aria-hidden="true">'+''.join(circles)+'</svg><div class="donut-center"><span>'+label+'</span><strong>'+center+'<small>%</small></strong></div></div><ul class="legend">'+''.join(legend)+'</ul></div>'
def bars(items,maxval=100,unit='%',accent=C[1]):
 return '<div class="bars">'+''.join(f'<div style="--accent:{accent}"><div class="bar-top"><span>{name}</span><b>{value:g}<small>{unit}</small></b></div><div class="bar-track"><div class="bar-fill" style="--value:{value/maxval*100:.3f}%"></div></div></div>' for name,value in items)+'</div>'
def chart(rows,keys,labels,maxval,unit,stacked=False):
 w=850;h=300;left=50;right=18;top=30;bottom=45;cw=w-left-right;ch=h-top-bottom;parts=[]
 for v in [0,maxval/2,maxval]:
  y=top+ch-v/maxval*ch;parts.append(f'<line class="grid" x1="{left}" y1="{y}" x2="{w-right}" y2="{y}"/><text x="{left-8}" y="{y+4}" text-anchor="end">{v:g}</text>')
 n=len(rows);step=cw/n;bw=min(44,step*.64)
 for i,row in enumerate(rows):
  x=left+step*(i+.5);base=top+ch
  for j,key in enumerate(keys):
   val=row[key]/10000;rh=val/maxval*ch;rx=x-bw/2 if stacked else x-bw/2+j*bw/len(keys);rw=bw if stacked else bw/len(keys)
   ry=base-rh;parts.append(f'<rect x="{rx:.2f}" y="{ry:.2f}" width="{rw:.2f}" height="{rh:.2f}" fill="{C[j]}"/>')
   if stacked:base=ry
  parts.append(f'<text x="{x:.2f}" y="{h-18}" text-anchor="middle">{labels[i]}</text>')
 return f'<div class="chart-scroll" tabindex="0" role="region" aria-label="{unit}。正確な値は下の表。"><svg class="chart chart-long" viewBox="0 0 {w} {h}" role="img" aria-label="{unit}の推移。数値表を併記。"><text x="0" y="15">{unit}</text>'+''.join(parts)+'</svg></div>'
def photo(key,alt,caption,hero=False):
 from PIL import Image
 im=Image.open(P/'assets'/f'{key}.webp');w,h=im.size
 return f'<figure class="'+('hero-photo' if hero else '')+f'"><img src="assets/{key}.webp" srcset="assets/{key}-small.webp 720w, assets/{key}.webp {w}w" sizes="'+('(max-width:700px) 90vw, 1320px' if hero else '(max-width:700px) 90vw, 650px')+f'" width="{w}" height="{h}" alt="{alt}" loading="'+('eager' if hero else 'lazy')+f'" decoding="async"><figcaption class="photo-caption">{caption}</figcaption></figure>'
def chapter(i,id,en,title,body):return f'<section class="chapter" id="{id}"><div class="section-head"><span class="section-no" aria-hidden="true">{i:02}</span><div><p class="kicker">{en}</p><h2>{title}</h2></div></div>{body}</section>'
parts=[]
parts.append('''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#080d10"><title>別府の観光と交通を読み解く｜データ分析｜MDL</title><meta name="description" content="別府市の観光客・宿泊・消費・交通・計画を一次資料から読み解く。2025年最新観光統計と2026年交通計画を、調査対象と限界を分けて可視化。"><link rel="canonical" href="https://mobilitydlab.com/co-creation-atlas/beppu-mobility/"><link rel="stylesheet" href="style.css"><script src="app.js" defer></script></head><body><a class="skip" href="#main">本文へスキップ</a><header class="masthead wrap"><a class="brand" href="/">MOBILITY<br>DESIGN LAB</a><nav aria-label="関連ページ"><a href="/oita-mirai-mobility-consortium/dialogue/beppu/">別府の目次へ</a><button id="motion-toggle" type="button" aria-pressed="false">動きを止める</button><button id="print-page" type="button">印刷 / PDF保存</button></nav></header><main id="main" class="wrap"><section class="hero" aria-labelledby="page-title"><p class="kicker">MOBILITY ANALYSIS / 大分県・別府市 / 2026.11.04</p><h1 id="page-title">BEPPU<span>.</span></h1><div class="hero-sub"><h2>温泉都市の、<br>人と移動を読む。</h2><p>誰が来て、どこに泊まり、どう巡るのか。<br>別府のデータと、国・県・市の計画を重ねて考える。<br>事実・推計・未確認を分けた、共創のための分析です。</p></div>''')
parts.append(photo('hills','鳥越大橋から望む別府市街と別府湾','別府市／別府たび。撮影年未記載の参考風景。現在の混雑を示す写真ではありません。',True))
parts.append('''</section><nav class="chapter-nav" aria-label="分析の目次"><a href="#visitors"><b>01</b>来訪と季節</a><a href="#stay"><b>02</b>泊まる・使う</a><a href="#mobility"><b>03</b>移動と交通</a><a href="#plans"><b>04</b>国・県・市の計画</a><a href="#coverage"><b>05</b>全項目と原典</a></nav>''')
a=D['annual_visitors'][-1];prev=D['annual_visitors'][-2];monthly=[r for r in D['monthly'] if r['year']==2025]
body='<p class="intro">2025年の別府市の観光客数は733.0万人。前年より3.6%増え、宿泊客の増加率は7.3%。ただし年間観光客数と、宿泊施設・交通機関の利用回数は別の指標です。</p><span class="scope">別府市全域</span><span class="scope">2025年1〜12月</span><span class="scope">市公表推計</span>'
body+='<div class="metric-grid">'+''.join(f'<div class="metric"><p class="label">{label}</p><p class="big-number">{value}<small>万人</small></p><p class="micro">{note}</p></div>' for label,value,note in [('総観光客数','733.0','7,330,300人 / 前年比 +3.6%'),('宿泊客数','275.2','2,752,193人 / 前年比 +7.3%'),('日帰り客数','457.8','4,578,107人 / 前年比 +1.5%')])+'</div>'
body+='<div class="split"><article class="panel"><h3>日帰りと宿泊の構成</h3>'+ring([('宿泊',a['overnight']),('日帰り',a['day'])],a['total'],f'{a["overnight"]/a["total"]*100:.1f}','宿泊客の構成比')+'<p class="micro">日帰りは総数から宿泊を引いた値。宿泊は入湯税申告に基づき、課税対象外施設を含みません。</p></article><article class="panel"><h3>2019年を100とすると</h3>'+bars([('総観光客数',round(a['total']/D['annual_visitors'][0]['total']*100,1)),('宿泊客数',round(a['overnight']/D['annual_visitors'][0]['overnight']*100,1)),('日帰り客数',round(a['day']/D['annual_visitors'][0]['day']*100,1))],120,'',C[2])+'<p class="note">観光客全体は2019年を下回る一方、宿泊は上回ります。<strong>「人を増やす」だけでなく、泊まる場所と街での行動を分けて見る</strong>必要があります。これは統計からの読み取りで、追加輸送の需要量を示すものではありません。</p></article></div>'
body+='<h3 style="margin-top:40px">7年間の回復を、同じ指標で見る</h3>'+chart(D['annual_visitors'],['overnight','day'],[str(x['year']) for x in D['annual_visitors']],900,'万人',True)+'<div class="chart-legend"><span style="--swatch:'+C[0]+'"><i></i>宿泊</span><span style="--swatch:'+C[1]+'"><i></i>日帰り</span></div>'
body+=detail('2019〜2025年の人数と各年の原典',table('別府市の観光客数（人）',['年','総数','宿泊','日帰り'],[[f'<a href="{r["source_url"]}#page=7">{r["year"]}年 ↗</a>',fmt(r['total']),fmt(r['overnight']),fmt(r['day'])] for r in D['annual_visitors']]))
body+='<div class="split"><article><h3>宿泊は3月、外国人宿泊は10月が最多</h3><p class="intro">年間合計だけでは見えない波があります。市の月別宿泊数は3月27.8万人、6月17.9万人。外国人宿泊は10月10.1万人、9月5.4万人です。</p></article><article class="note warning"><strong>月別グラフは「宿泊客数」です。</strong><br>月別の総観光客数・日帰り客数は公表表で確認できません。市周辺19施設の月別入込は、市外施設や同じ人の重複も含むため、代用しません。</article></div>'
body+=chart(monthly,['overnight_city','foreign_overnight'],[str(r['month'])+'月' for r in monthly],30,'万人（並列表示）')+'<div class="chart-legend"><span style="--swatch:'+C[0]+'"><i></i>宿泊全体（入湯税ベース）</span><span style="--swatch:'+C[1]+'"><i></i>外国人宿泊（拡大推計）</span></div><p class="micro">外国人は宿泊全体の内数として公表されますが、別方式の推計です。2系列を足し合わせません。</p>'
body+=detail('月別宿泊・外国人宿泊・施設入込の全数値',table('2025年月別。施設入込は別府市周辺19施設合計で、観光客総数ではない',['月','宿泊全体','外国人宿泊','19施設入込'],[[str(r['month'])+'月',fmt(r['overnight_city']),fmt(r['foreign_overnight']),fmt(r['attraction_entries'])] for r in monthly])+link(xlsx,'市公式Excel・表3宿泊客数／表4主要観光施設'))
body+=detail('四半期ごとの総観光客・宿泊・日帰り',table('2025年・四半期別（人）',['期間','総観光客','宿泊','日帰り'],[[str((r['quarter']-1)*3+1)+'〜'+str(r['quarter']*3)+'月',fmt(r['total']),fmt(r['overnight']),fmt(r['day'])] for r in D['quarterly_2025']]))+link(pdf+'#page=4','市観光動態要覧・算出方法1〜2頁／結果4〜10頁')
parts.append(chapter(1,'visitors','VISITORS & SEASONS','訪れる人は、<br>いつ、どれくらい？',body))
body='<div class="split"><article class="panel"><span class="scope">2025年・市全域・入湯税ベース</span><h3>宿泊客の半数は、北浜・中央</h3>'+ring([(r['district'],r['2025']) for r in D['districts']],a['overnight'],'50.5','北浜・中央')+'</article><article><h3>増加の大きい地区は、堀田・観海寺</h3><p class="big-number" style="color:var(--orange);margin-top:22px">18.1<small>万人増</small></p><p class="intro">2024年から2025年の市全体の宿泊増は18.8万人。そのうち堀田・観海寺は18.1万人増えています。北浜・中央も増加し、鉄輪・明礬とその他は減少しました。</p><p class="note">地区別の宿泊数は、どこから街へ出る可能性があるかを考える出発点。<strong>宿から外出した割合、時刻、移動先、車の空席は未計測</strong>です。</p></article></div>'
body+=detail('地区別宿泊数の2024年・2025年比較',table('宿泊客数（人）。地区定義は市公表表に従う',['地区','2024年','2025年','前年差'],[[r['district'],fmt(r['2024']),fmt(r['2025']),f'{r["2025"]-r["2024"]:+,}'] for r in D['districts']]))
foreign=D['foreign_annual_revised'][-1]
body+='<div class="split"><article class="panel"><h3>外国人観光客は109.96万人</h3><p class="big-number" style="color:var(--blue)">109.96<small>万人</small></p><p class="micro">2025年 1,099,582人 / 改訂後2024年比 +6.3%</p>'+ring([('宿泊',foreign['overnight']),('日帰り',foreign['day'])],foreign['total'],f'{foreign["overnight"]/foreign["total"]*100:.1f}','外国人の宿泊構成比')+'</article><article><h3>外国人宿泊の上位市場</h3>'+bars([(r['market'],round(r['overnight']/foreign['overnight']*100,1)) for r in sorted(D['foreign_markets_2025'],key=lambda x:x['overnight'],reverse=True)[:5]],50,'%',C[1])+'<p class="micro">2025年外国人宿泊962,230人に占める構成比。上位5区分のみ。全22区分は下の表。</p></article></div>'
body+='<p class="note warning"><strong>外国人の推計は2026年7月10日に見直されています。</strong><br>2024年・2025年は遡及改訂済みです。比較に使う2024年総数は1,034,716人、宿泊918,108人。旧2024年報の451,894人・335,286人から急増したように描きません。2019〜2023年とも単純な長期比較はできません。</p>'
body+=detail('外国人の全22国・地域別、宿泊と日帰り',table('2025年外国人観光客（人）。原表に合わせた国・地域区分',['国・地域','総数','宿泊','日帰り'],[[r['market'].strip(),fmt(r['total']),fmt(r['overnight']),fmt(r['day'])] for r in D['foreign_markets_2025']]))
body+='<div class="photo-pair">'+photo('umijigoku','海地獄の青い湯と湯けむり','海地獄 / TANAKA Juuyoh / 2009年 / CC BY 2.0')+photo('takegawara','別府市竹瓦温泉の木造玄関','竹瓦温泉 / Yusuke Kawasaki / 2009年 / CC BY 2.0')+'</div>'
body+='<h3 style="margin-top:45px">客数の増加と、消費額の増加は同じではない</h3><div class="metric-grid"><div class="metric"><p class="label">2025年・観光消費額の市推計</p><p class="big-number">1,290.8<small>億円</small></p><p class="micro">129,076,220千円。県単価 × 市推計客数。</p></div><div class="metric"><p class="label">改訂後2024年との比較</p><p class="big-number">−7.1<small>%</small></p><p class="micro">2024年は1,389.5億円。客数増でも推計額は減少。</p></div><div class="metric"><p class="label">宿泊客の消費額構成比</p><p class="big-number">71.0<small>%</small></p><p class="micro">宿泊客の推計消費916.4億円 ÷ 全体。</p></div></div>'
body+='<p class="note warning"><strong>市内の実支出を直接集計した金額ではありません。</strong><br>大分県の国内・外国人別／宿泊・日帰り別単価を、市の該当人数に掛けた推計です。日本人用単価は県の「観光目的・県外客」に一致します。消費単価の変化と外国人推計方法の変更を含むため、交通改善の効果とは読めません。</p>'
body+=detail('消費単価・対象人数・推計消費額を確認',table('2025年・県単価を用いた別府市の観光消費推計',['区分','人数（人）','県単価（円/人回）','市推計（千円）'],[[r['segment'],fmt(r['visitors']),fmt(r['unit_spend_yen_per_person_trip']),fmt(r['consumption_thousand_yen'])] for r in D['consumption_segments_2025']],True))+link(pdf+'#page=13','市観光動態要覧・消費額10頁')
body+='<div class="split"><article class="panel"><span class="scope">2024年度・市事業評価の実績</span><h3>平均泊数として公表された値</h3><p class="big-number" style="color:var(--lime)">1.106<small>泊</small></p><p class="micro">目標1.14泊に対する事業評価実績。基礎調査の対象年・標本・算式は評価表に未記載。2025年の平均泊数とは表示しません。</p>'+link(D['kpi_avg_stay']['source_url'],'市2024年度事業評価・事業2 指標①')+'</article><article><h3>「泊数」と「街にいる時間」を分ける</h3><p class="intro">1泊でも、夕食後に出かける人と宿の中で過ごす人では移動が違います。市の泊数KPIは、夜の外出率・店舗滞在時間・交通待ち時間を表しません。</p><p class="note">湯布院で確認した客室稼働率・訪日客費目・滞在時間に対応する別府資料は、末尾の全項目表で確認状況を示します。</p></article></div>'
parts.append(chapter(2,'stay','STAY, MARKETS & SPENDING','泊まる場所と、<br>街に残るお金。',body))
for f in ['stay-detail.html','mobility-section.html','plans-section.html','coverage-section.html']:
 if (P/f).exists(): parts.append((P/f).read_text())
parts.append('''<section class="closing" aria-labelledby="closing-title"><p class="kicker">FROM EVIDENCE TO DIALOGUE</p><h2 id="closing-title">データを読み、<br>地域と確かめる。</h2><p>宿泊の増加、交通の供給、夜の外出は、それぞれ別の問いです。データだけで新しい運行を決めず、宿・店・交通事業者・住民と、実際に困る場面を照合する。共創提案は、分析と区別した別ページでご覧ください。</p><div class="download-row"><a class="button-link primary" href="/oita-mirai-mobility-consortium/dialogue/beppu/">別府の分析・提案の目次へ ↗</a><a class="button-link" href="/oita-mirai-mobility-consortium/dialogue/beppu.html">既存の共創提案を読む ↗</a><a class="button-link" href="../yufuin-mobility/">湯布院のデータ分析 ↗</a></div></section></main><footer><div class="wrap"><p class="footer-word">BEPPU.</p><p class="micro">調査確認：2026年11月4日（日本時間）。公表値の意味・対象・時点を保持し、計画目標と実績、県全体と別府市を分けています。</p><details id="photo-credits"><summary>写真の出典・利用条件</summary><div class="credits"><p>湯けむり展望台：別府市／別府たび（撮影年未記載）。<a href="https://beppu-tourism.com/photo/616/">原画像ページ</a>。別府市の同利用規約に基づき、作品を構成する素材として使用。画像素材としての二次配布不可。</p><p>写真は地域の参考風景です。現在の混雑・サービス・整備状況を示すものではありません。縮小・WebP変換、表示枠によるトリミングを行っています。</p><p>鳥越大橋からの景色：別府市／別府たび。撮影年未記載。<a href="https://beppu-tourism.com/photo/4411/">原画像ページ</a> ／ <a href="https://beppu-tourism.com/terms/">利用規約</a>。作品を構成する素材として使用。画像素材としての二次配布は不可。</p><p>別府湾と別府市（2021年）：Project Kei。<a href="https://commons.wikimedia.org/wiki/File:Beppu_City_and_Beppu_Bay.jpg">原画像</a> ／ <a href="https://creativecommons.org/licenses/by-sa/4.0/">CC BY-SA 4.0</a>。加工画像も同ライセンス。</p><p>海地獄（2009年）：TANAKA Juuyoh (田中十洋)。<a href="https://www.flickr.com/photos/tanaka_juuyoh/3536167065">原画像</a> ／ <a href="https://creativecommons.org/licenses/by/2.0/">CC BY 2.0</a>。</p><p>竹瓦温泉（2009年）：Yusuke Kawasaki。<a href="https://www.flickr.com/photos/u-suke/3354137062/">原画像</a> ／ <a href="https://creativecommons.org/licenses/by/2.0/">CC BY 2.0</a>。</p></div></details><p class="micro" style="margin-top:25px">MOBILITY DESIGN LAB / <a href="/">ホームへ</a></p></div></footer></body></html>''')
(P/'index.html').write_text('\n'.join(parts))
with (P/'downloads/Beppu-Monthly-Lodging-2025.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['月','市宿泊客数_人_入湯税ベース','外国人宿泊客数_人_拡大推計','北浜中央_人','鉄輪明礬_人','堀田観海寺_人','その他_人','原典'])
 for r in monthly:w.writerow([r['month'],r['overnight_city'],r['foreign_overnight'],r['kitahama_chuo'],r['kannawa_myouban'],r['horita_kankaiji'],r['other'],xlsx])
print('Built',len(''.join(parts)),'characters')
