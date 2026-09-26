"""Build the standalone B-SIDE mascot catalogue. The homepage is maintained separately."""
import json
from html import escape
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/'oita-mirai-mobility-consortium'
CAT=json.loads((SITE/'mascots/catalog.json').read_text())
SIM=json.loads((SITE/'mascots/simulation.json').read_text())
BY_ID={x['id']:x for x in CAT}
RANK={x['id']:x for x in SIM['ranking']}
SELECTED=SIM['topFive']+([] if SIM['alwaysFeature'] in SIM['topFive'] else [SIM['alwaysFeature']])
def art(c,pre='',eager=False):
 x,y,w,h=c['crop'];iw,ih=c['imageSize']
 style=f'--crop-ratio:{w/h:.6f};--image-width:{iw/w*100:.6f}%;--image-left:{-x/w*100:.6f}%;--image-top:{-y/h*100:.6f}%'
 return f'<div class="mascot-crop" style="{style}"><img src="{pre+c["image"]}" alt="{escape(c["name"]+"："+c["motif"]+"と"+c["mobility"])}" width="{iw}" height="{ih}" {"fetchpriority=\"high\"" if eager else "loading=\"lazy\""}></div>'
def card(cid,pre='',catalog=False):
 c=BY_ID[cid];r=RANK[cid];special=cid==SIM['alwaysFeature'] and cid not in SIM['topFive']
 label='図鑑 No.'+cid if catalog else ('いつも一緒 / SPECIAL' if special else 'SIMULATION / 選定順位')
 num=f'{r["rank"]:02d}' if not special else '＋1'
 if catalog:num=cid
 copy=f'<p class="mascot-votes">仮想得票 {r["votes"]}票 · シミュレーション {r["rank"]}位</p>' if catalog else ''
 if special and not catalog:copy='<p class="mascot-special-note">順位にかかわらず掲載する仲間</p>'
 return f'<article class="mascot-card{" special" if special else ""}" id="character-{cid}" data-search="{escape(c["name"]+c["motif"]+c["mobility"]+c["region"])}"><header class="mascot-card-head"><span>{label}</span><b class="mascot-rank">{num}</b></header><div class="mascot-art">{art(c,pre)}</div><div class="mascot-copy"><h3>{escape(c["name"])}</h3><p class="mascot-combination">{escape(c["motif"])}<br>× {escape(c["mobility"])}</p><p class="mascot-character-line">{escape(c["feature"])}</p>{copy}</div></article>'
page='''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>B-SIDE｜キャラクター特設サイト｜大分未来モビリティ・コンソーシアム</title><meta name="description" content="大分の名物・名所・文化とモビリティを組み合わせた62のキャラクター。選定シミュレーションの結果と方法を公開。"><link rel="canonical" href="https://mobilitydlab.com/oita-mirai-mobility-consortium/mascots/"><link rel="stylesheet" href="../site.css?v=20260926.2"><link rel="stylesheet" href="../bauhaus.css?v=20260926.7"><link rel="stylesheet" href="../mascots.css?v=20260926.10"></head><body class="bauhaus-page mascot-page bside-page"><a class="skip" href="#main">本文へ移動</a><header class="site-head"><a class="brand" href="../"><span class="brand-mark" aria-hidden="true">O.</span><span>大分未来モビリティ・<br>コンソーシアム<small>OITA MIRAI MOBILITY CONSORTIUM</small></span></a><a class="mascot-home-link" href="../">コンソーシアムへ ↗</a></header><main id="main" class="wrap"><section class="mascot-page-head mascot-hero"><div><span class="bside-label">B-SIDE / OUR CHARACTERS</span><h1>大分の、<br>もうひとつの顔。</h1><p>かぼす、温泉、宇佐神宮。<br>大分の名物・名所・文化と、未来のモビリティから生まれた仲間たち。</p><p class="mascot-stats"><b>62</b> DESIGNS　/　大分の未来を、ちょっと遊ぶ。</p><nav class="bside-index" aria-label="特設サイトの目次"><a href="#chosen-title">6つの仲間 ↓</a><a href="#catalog">全62案の図鑑 ↓</a><a href="#method">選定方法 ↓</a></nav></div>'''+art(BY_ID[SIM['topFive'][0]],'../')+'''</section><section class="mascot-method" id="method"><span class="bau-overline">SELECTION SIMULATION</span><h2>選定シミュレーション</h2><p><strong>これは実際の人気投票・アンケートではありません。</strong>62案を制作者の主観で採点し、1,000人が1人1票を投じる仮想モデルで比較しました。仮定を変えると順位も変わります。予測や実証済みの人気を示すものではありません。</p><p>上位5案をコンソーシアムのキャラクターとして選定。やせうまスクーターは、順位にかかわらず掲載する仲間です。</p><details><summary>評価項目・仮定・再現方法</summary><dl><dt>評価項目</dt><dd>親しみやすさ、大分らしさ、モビリティの分かりやすさ、小さな表示での見やすさ、形の独自性。各1〜5点の主観評価です。</dd><dt>仮想の好み</dt><dd>親しみやすさ重視30%、大分らしさ重視30%、モビリティ重視20%、造形・使いやすさ重視20%。実在する人の構成比ではありません。</dd><dt>集計方法</dt><dd>評価項目を好み別に加重平均し、その点数から抽選確率を設定。1,000回の仮想投票を得票順に並べています。同票は候補ID順です。</dd><dt>固定条件</dt><dd>乱数シード 20260926、抽選の温度パラメータ 0.16。候補ごとの点数・重み・全得票は、下のデータで確認できます。</dd><dt>評価データ</dt><dd><a href="simulation.json">点数・重み・仮想得票のJSON</a></dd></dl></details></section><section aria-labelledby="chosen-title"><header class="mascot-all-head"><span class="bau-overline">MEET THE SIX</span><h2 id="chosen-title">コンソーシアムの、6つの仲間。</h2><p>シミュレーションで選んだ上位5体 ＋ やせうまスクーター。<br>実際の人気投票による順位ではありません。<a href="#method">選定方法を見る ↓</a></p></header><div class="mascot-grid">'''+''.join(card(c,'../') for c in SELECTED)+'''</div></section><section id="catalog" aria-labelledby="catalog-title"><header class="mascot-all-head"><span class="bau-overline">CHARACTER ENCYCLOPEDIA</span><h2 id="catalog-title">全62案の図鑑</h2><p>イラストは創作デザイン、名前は仮称です。実在の機体の設計図ではありません。</p><div class="mascot-filter"><label for="character-search">キャラクターを探す</label><input id="character-search" type="search" placeholder="かぼす、宇佐神宮、空飛ぶ…" aria-controls="character-list"><span id="result-count" role="status">62案</span></div></header><div class="mascot-grid mascot-catalog-grid" id="character-list">'''+''.join(card(c['id'],'../',True).replace('id="character-','id="catalog-') for c in CAT)+'''</div><p id="character-empty" class="mascot-empty" hidden>該当するキャラクターがありません。別の言葉で探してみてください。</p></section></main><footer class="site-foot"><strong>大分未来モビリティ・コンソーシアム</strong><p>キャラクター図鑑・選定シミュレーション ／ 2026年9月26日</p><nav><a href="../">ホームへ戻る</a><a href="../guide/">構想説明書</a><a href="https://mobilitydlab.com/">制作：モビリティデザインラボ ↗</a></nav></footer><script src="catalog.js?v=20260926.8" defer></script></body></html>'''
# Lead with the characters; keep the simulation methodology after the six.
start=page.index('<section class="mascot-method"')
end=page.index('<section aria-labelledby="chosen-title">',start)
method=page[start:end]
page=page[:start]+page[end:]
page=page.replace('<section id="catalog"',method+'<section id="catalog"',1)
(SITE/'mascots/index.html').write_text(page)
print(json.dumps({'catalog':len(CAT),'featuredCharacters':SELECTED,'homepageModified':False},ensure_ascii=False))
