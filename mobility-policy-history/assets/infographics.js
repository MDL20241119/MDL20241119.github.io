/* MDL Research Archive — maps and shared-time infographics. No external runtime. */
(() => {
  'use strict';
  const D = window.MOBILITY_DATA;
  const geography = window.MOBILITY_JAPAN_MAP || [];
  const regions = [
    {name:'北海道・東北',prefs:['北海道','青森県','岩手県','宮城県','秋田県','山形県','福島県'],x:434,y:210},
    {name:'関東',prefs:['茨城県','栃木県','群馬県','埼玉県','千葉県','東京都','神奈川県'],x:465,y:370},
    {name:'北陸・甲信越',prefs:['新潟県','富山県','石川県','福井県','山梨県','長野県'],x:225,y:245},
    {name:'東海',prefs:['岐阜県','静岡県','愛知県','三重県'],x:350,y:470},
    {name:'近畿',prefs:['滋賀県','京都府','大阪府','兵庫県','奈良県','和歌山県'],x:268,y:540},
    {name:'中国',prefs:['鳥取県','島根県','岡山県','広島県','山口県'],x:105,y:335},
    {name:'四国',prefs:['徳島県','香川県','愛媛県','高知県'],x:178,y:583},
    {name:'九州・沖縄',prefs:['福岡県','佐賀県','長崎県','熊本県','大分県','宮崎県','鹿児島県','沖縄県'],x:18,y:600}
  ];
  const ys = Array.from({length:11},(_,i)=>String(2016+i));
  const marks = [
    {year:'2017',word:'自動運転',label:'道の駅等13か所で短期実験',id:'EV-e83e49a4c6fa'},
    {year:'2019',word:'MaaS',label:'日本版MaaS先行19地域',id:'EV-e2a8a40fd353'},
    {year:'2022',word:'共創',label:'共創モデル実証、初回15件',id:'EV-831c5c54abbf'},
    {year:'2025',word:'共通化',label:'COMmmmONSが始動',id:'EV-10b110e49831'}
  ];
  function create(H) {
    const {e,path,findCases,findEvents,eventYear,eventHtml,card,caseHref} = H;
    const short = s => s.replace(/県$|府$|都$/,'');
    const regionCases = (cs,r) => cs.filter(c=>c.prefectures.some(p=>r.prefs.includes(p)));
    const mapCases = p => findCases(p);
    const counts = cs => Object.fromEntries(geography.map(g=>[g.name,cs.filter(c=>c.prefectures.includes(g.name)).length]));
    const yearLabel = y => ({pre:'2015年以前（前史）',future:'2027年以降の予定',undated:'日付未確定'}[y] || (y ? `${y}年・年度` : '全期間'));
    const href = (p,extra={}) => path('map',{...p,page:'',section:'',...extra});
    const band = n => n===0?'0':n===1?'1':n<5?'2':'3';
    const arrow = '<span aria-hidden="true">↗</span>';
    function mapSvg(cs,p={},compact=false) {
      const ct=counts(cs),selected=p.pref;
      return `<svg class="japan-map" viewBox="0 0 640 660" role="group" aria-label="都道府県から事例を探す日本地図"><defs><pattern id="map-grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#34373c" stroke-width=".5"/></pattern></defs><rect width="640" height="660" fill="url(#map-grid)" aria-hidden="true"/><g class="map-inset" aria-hidden="true"><rect x="24" y="32" width="224" height="159" rx="2"/><text x="38" y="55">南西諸島</text><path d="M255 50l-6 7m6 3l-6 7"/></g><g class="map-land">${geography.map(g=>`<a href="${e(href(p,{pref:g.name}))}" aria-label="${e(g.name)} ${ct[g.name]}事例"${selected===g.name?' aria-current="true"':''} class="prefecture${selected===g.name?' is-selected':''}${selected&&selected!==g.name?' is-muted':''}" data-prefecture="${e(g.name)}" data-map-count="${ct[g.name]}" data-band="${band(ct[g.name])}"><path d="${g.d}"></path><title>${e(g.name)}：${ct[g.name]}事例</title></a>`).join('')}</g><g class="map-labels" aria-hidden="true">${regions.map(r=>`<text x="${r.x}" y="${r.y}"><tspan class="map-region-name" x="${r.x}">${r.name}</tspan><tspan class="map-region-count" x="${r.x}" dy="33">${regionCases(cs,r).length}<tspan class="map-region-unit"> 事例</tspan></tspan></text>`).join('')}</g><g class="map-north" aria-hidden="true"><path d="M603 600v-36m-7 10l7-10 7 10"/><text x="599" y="617">N</text></g></svg>`;
    }
    function legend() {
      return '<div class="map-legend" aria-label="地図の色：収録事例数"><span>収録事例数</span><span><i data-band="0"></i>0</span><span><i data-band="1"></i>1</span><span><i data-band="2"></i>2–4</span><span><i data-band="3"></i>5以上</span></div>';
    }
    function credit() {
      return '<p class="map-credit">都道府県単位で表示。南西諸島は別枠、一部島しょは省略。<a href="https://www.naturalearthdata.com/" target="_blank" rel="noopener noreferrer">地図：Natural Earth</a></p>';
    }
    function homeMap() {
      const cs=D.cases,ct=counts(cs),covered=geography.filter(g=>ct[g.name]>0).length;
      const ranked=Object.entries(ct).filter(([,n])=>n).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0],'ja')).slice(0,5);
      return `<section class="section geo-home" id="geography"><div class="section-tag"><p class="eyebrow">01 / GEOGRAPHY OF CHANGE</p><span class="num">JAPAN / ${covered} PREFECTURES</span></div><div class="section-heading"><h2>変化の舞台を、<br><span class="text-cyan">地図でつかむ。</span></h2><p>日本のどこで、何が試されたのか。<br>都道府県を押すと、その地域の履歴へ。</p></div><div class="geo-home-grid"><div class="map-board">${mapSvg(cs)}${legend()}${credit()}</div><div class="map-home-aside"><p class="viz-kicker">PLACES / ${D.as_of}</p><div class="geo-hero-number"><strong>${covered}</strong><span>都道府県の<br>取り組みを収録</span></div><p class="viz-caption">色の濃さは、この特集の収録件数。<br>複数地域の事例は、それぞれに表示。</p><div class="ranked-prefs">${ranked.map(([pref,n],i)=>`<a href="${e(href({},{pref}))}"><span class="rank">0${i+1}</span><strong>${pref}</strong><b>${n}</b>${arrow}</a>`).join('')}</div><a class="button lime" href="#map">地図から探す ${arrow}</a><a class="inline-link" href="#map?pref=${encodeURIComponent('広域・全国等')}">広域・全国の取り組みを見る ${arrow}</a></div></div></section>`;
    }
    function mapPage(p) {
      const base=mapCases({...p,pref:''}),found=mapCases(p),ct=counts(base);
      const selected=p.pref||'全国',selectedCount=found.length;
      const pageSize=12,totalPages=Math.max(1,Math.ceil(found.length/pageSize));
      const page=Math.max(1,Math.min(totalPages,Number(p.page)||1));
      const visible=found.slice((page-1)*pageSize,page*pageSize);
      const wide=base.filter(c=>c.prefectures.includes('広域・全国等')).length;
      const options=(items,val,first)=>`<option value="">${first}</option>${items.map(x=>{const [v,l]=Array.isArray(x)?x:[x,x];return `<option value="${e(v)}"${val===v?' selected':''}>${e(l)}</option>`;}).join('')}`;
      return `<div class="wrap atlas-page"><section class="page-head atlas-heading"><div><p class="eyebrow">MOBILITY ATLAS / 2016 — 2026</p><h1>どこで、<br><span class="text-cyan">何が変わった？</span></h1><p>地図から地域を選び、年とテーマで履歴をたどる。</p></div><div class="atlas-total"><strong>${D.counts.cases}</strong><span>収録事例</span></div></section><form class="atlas-filters" id="atlas-filters" data-view="map"><label>01 年・年度<select name="year" data-viz-filter>${options([...ys,['pre','2015年以前（前史）'],['future','2027年以降の予定'],['undated','日付未確定']],p.year,'全期間')}</select></label><label>02 テーマ<select name="theme" data-viz-filter>${options(D.themes,p.theme,'すべてのテーマ')}</select></label><label>03 都道府県<select name="pref" data-viz-filter>${options([...geography.map(g=>g.name),'広域・全国等'],p.pref,'全国')}</select></label><a class="atlas-reset" href="#map">すべて解除 ↺</a></form><div class="atlas-context"><p><span class="live-square" aria-hidden="true"></span> ${e(yearLabel(p.year))}${p.theme?' / '+e(p.theme):''}</p><p>地図の色＝収録数 / 選択すると下に事例を表示</p></div><div class="atlas-grid"><section class="map-board" aria-label="日本地図から選ぶ">${mapSvg(base,p)}${legend()}${credit()}</section><aside class="atlas-side"><div class="selection-card" aria-live="polite"><p class="viz-kicker">SELECTED AREA</p><h2>${e(selected)}</h2><p class="selected-count"><strong>${selectedCount}</strong> 事例</p><a href="${e(href(p,{section:'map-results'}))}" class="button lime">事例を見る ↓</a><a href="${e(path('timeline',{pref:p.pref,theme:p.theme,year:p.year}))}" class="inline-link">この条件の年表を開く ${arrow}</a></div><div class="pref-directory"><h2>地域から選ぶ</h2>${regions.map(r=>`<details${p.pref&&r.prefs.includes(p.pref)?' open':''}><summary><span>${r.name}</span><b>${regionCases(base,r).length}</b></summary><div class="pref-links">${r.prefs.map(pref=>`<a class="${p.pref===pref?'selected':''}" href="${e(href(p,{pref}))}"${p.pref===pref?' aria-current="true"':''}><span>${pref}</span><b>${ct[pref]}</b></a>`).join('')}</div></details>`).join('')}<a class="wide-region${p.pref==='広域・全国等'?' selected':''}" href="${e(href(p,{pref:'広域・全国等'}))}"><span>広域・全国等</span><b>${wide}</b></a></div></aside></div><section class="map-results" id="map-results"><div class="section-heading"><h2>${e(selected)}の<br><span class="text-cyan">取り組み。</span></h2><p>${e(yearLabel(p.year))}${p.theme?' / '+e(p.theme):''}<br><strong>${selectedCount}</strong>件${found.length?` / ${(page-1)*pageSize+1}–${Math.min(page*pageSize,found.length)}件を表示`:''}</p></div>${p.pref?`<div class="active-filters"><a href="${e(href(p,{pref:''}))}">${e(p.pref)} <span aria-label="地域の絞り込みを解除">×</span></a></div>`:''}<div class="case-grid">${visible.length?visible.map(card).join(''):`<div class="empty"><p>この条件の事例は収録されていません。</p><a href="${e(href(p,{year:'',theme:''}))}" class="inline-link">年・テーマを解除する ↗</a><br><a href="#map" class="inline-link">全国の全事例に戻る ↗</a></div>`}</div>${totalPages>1?`<nav class="atlas-pagination" aria-label="事例一覧のページ">${page>1?`<a class="button secondary" href="${e(href(p,{page:page-1,section:'map-results'}))}">← 前の12件</a>`:'<span></span>'}<span>${page} / ${totalPages}</span>${page<totalPages?`<a class="button secondary" href="${e(href(p,{page:page+1,section:'map-results'}))}">次の12件 →</a>`:'<span></span>'}</nav>`:''}</section></div>`;
    }
    function decade(p={},home=false) {
      const pool=findEvents({...p,year:'',event:''});
      const data=ys.map(y=>({y,c:pool.filter(x=>x.case_id&&eventYear(x)===y).length,p:pool.filter(x=>!x.case_id&&eventYear(x)===y).length}));
      const max=Math.max(1,...data.map(x=>x.c+x.p));
      return `<div class="decade-chart${home?' is-home':''}" aria-label="2016年から2026年の収録記録数"><div class="chart-guide"><p>収録した出来事 <span>件</span></p><span>${e(p.theme||p.pref||'2016 — 2026')}</span></div><div class="decade-columns">${data.map(x=>`<a class="decade-column${p.year===x.y?' selected':''}" href="${e(path('timeline',{...p,year:x.y,event:'',section:home?'':'timeline-visual'}))}" aria-label="${x.y}年・年度：地域${x.c}件、政策${x.p}件"${p.year===x.y?' aria-current="true"':''}><span class="decade-total">${x.c+x.p}</span><span class="decade-bars" aria-hidden="true"><i class="bar-policy" style="height:${x.p/max*100}%"></i><i class="bar-region" style="height:${x.c/max*100}%"></i></span><strong>${x.y}</strong><span class="decade-numbers"><b>${x.c}</b><b>${x.p}</b></span></a>`).join('')}</div><div class="decade-legend"><span><i class="legend-region"></i>地域</span><span><i class="legend-policy"></i>政策</span><p>年・年度の原記載で集計。2026年度は途中。</p></div></div>`;
    }
    function milestones() {
      return `<nav class="policy-milestones" aria-label="政策の主な動き">${marks.map((m,i)=>`<a href="${e(path('timeline',{year:m.year,kind:'policy',event:m.id}))}"><span class="milestone-year">${m.year}</span><span class="milestone-dot" aria-hidden="true"></span><strong>${m.word}</strong><span class="milestone-caption">${m.label}</span><span class="milestone-arrow" aria-hidden="true">↗</span></a>`).join('')}</nav>`;
    }
    function timelineIntro(p) {
      const es=findEvents(p),national=es.filter(x=>!x.case_id).length,local=es.length-national;
      return `<section class="timeline-visual" id="timeline-visual"><div class="timeline-dashboard"><div class="time-readout${p.year&&/^20\d\d$/.test(p.year)?'':' text-period'}"><p class="viz-kicker">SELECTED PERIOD</p><strong>${e(p.year&&/^20\d\d$/.test(p.year)?p.year:yearLabel(p.year))}</strong><span>${p.year&&/^20\d\d$/.test(p.year)?'年・年度の記録':'記録の対象期間'}</span></div><div class="lane-key region-key"><span>地域の出来事</span><strong>${local}</strong><small>実証・実装・継続・変更等</small></div><div class="lane-key policy-key"><span>国の政策</span><strong>${national}</strong><small>制度・採択・改訂等</small></div></div>${decade(p)}<div class="visual-actions"><a class="inline-link" href="${e(path('map',{year:p.year,pref:p.pref,theme:p.theme}))}">この年を地図で見る ${arrow}</a><a class="inline-link" href="${e(path('timeline',{...p,year:'',event:'',section:'timeline-visual'}))}">全期間に戻す ↺</a></div></section>`;
    }
    function lane(es,isPolicy,p) {
      const n=3,head=es.slice(0,n),rest=es.slice(n),label=isPolicy?'国の政策':'地域の出来事';
      return `<section class="time-lane ${isPolicy?'national-lane':'regional-lane'}"><div class="time-lane-heading"><h3><i aria-hidden="true"></i>${label}</h3><span><b>${es.length}</b>件</span></div>${es.length?`<ol class="event-list">${head.map(ev=>eventHtml(ev,true,p.year)).join('')}</ol>${rest.length?`<details class="more-events"><summary>残り <b>${rest.length}</b> 件の${label}を表示 <span aria-hidden="true">＋</span></summary><ol class="event-list">${rest.map(ev=>eventHtml(ev,true,p.year)).join('')}</ol></details>`:''}`:'<p class="lane-empty">この条件の記録はありません。</p>'}</section>`;
    }
    function yearLanes(y,es,p) {
      const national=es.filter(x=>!x.case_id),local=es.filter(x=>x.case_id);
      return `<section class="timeline-year visual-year"><div class="year-label"><strong>${e(y)}</strong><span>${es.length} 記録${/^20\d\d$/.test(y)?' ／ 年・年度':''}</span></div><div class="time-lanes${p.kind?' single-lane':''}">${p.kind!=='case'?lane(national,true,p):''}${p.kind!=='policy'?lane(local,false,p):''}</div></section>`;
    }
    function caseTrace(c,p={}) {
      const raw=H.sortEvents(c.events),bins=ys.map(y=>({y,es:raw.filter(ev=>eventYear(ev)===y)}));
      return `<div class="case-trace"><p class="viz-kicker">記録のある年から、出来事へ</p><div class="trace-years">${bins.map(({y,es})=>`<div class="trace-year${es.length?' has-record':''}"><span>${y}</span>${es.length?`<a href="${e(path('case',{...p,event:es[0].event_id},c.id))}" aria-label="${y}年 ${es.length}件の記録"><b>${es.length}</b><span>件</span></a>`:'<i aria-hidden="true"></i>'}</div>`).join('')}</div></div>`;
    }
    return {homeMap,mapPage,mapSvg,counts,mapCases,decade,milestones,timelineIntro,yearLanes,caseTrace,regions};
  }
  window.MOBILITY_GRAPHICS={create,regions};
})();
