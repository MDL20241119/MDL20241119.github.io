(() => {
  'use strict';
  const standalone = document.body.dataset.municipal === 'true';
  const base = standalone ? '' : '../municipal-mobility-history/';
  const summary = window.MOBILITY_RESULTS_SUMMARY;
  const countValue = key => summary?.counts?.[key] ?? '—';
  const countText = key => typeof countValue(key)==='number' ? countValue(key).toLocaleString('ja-JP') : countValue(key);
  const latestCaseIds = () => summary?.current_batch?.case_ids || [];
  const latestBatchLabel = () => '今回の調査 '+latestCaseIds().length+'案件';
  const latestBatchNote = () => summary?.current_batch ? '新規詳査 '+summary.current_batch.new_cases+'件 ／ 既存案件の増補 '+summary.current_batch.updated_cases+'件（新規事業数ではありません）' : '今回の調査範囲を確認できます。';
  const asOf = () => summary?.as_of || '2026-10-31';
  const cache = new Map();
  const escape = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  // Enlarge only measured quantities with their units; dates stay ordinary text.
  function numberMarkup(value) {
    return escape(value).replace(/((?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:万|千|億)?)(%|％|円|人(?:\/日|／日)?|件|回|便|台|枚|乗車|施設|エリア)/g,(_,number,unit)=>`<strong class="m-number">${number}<span>${unit}</span></strong>`);
  }
  const norm = v => String(v ?? '').normalize('NFKC').toLowerCase().replace(/[\s・･\-_]/g,'');
  const list = v => v == null ? [] : Array.isArray(v) ? v : [v];
  const plain = v => v == null ? '' : typeof v === 'object' ? (Array.isArray(v) ? v.map(plain).join(' / ') : Object.values(v).map(plain).join(' / ')) : String(v);
  const geography = window.MOBILITY_JAPAN_MAP || [];
  const layerNames = {selection:'採択・支援',reference:'運行等の参照',review:'公式資料点検',local:'自治体公式履歴',legacy:'旧代表事例',history:'年度履歴索引'};
  const evidenceNames = {deep_result:'結果・変遷を詳査',outcome_result:'実績結果',study_result:'調査成果',interim_result:'中間結果',partial_implementation_result:'部分実施のみ',termination_only:'終了のみ',outcome_not_obtained:'結果未取得',not_reviewed:'資料未点検'};
  const precisionNames={day:'日まで確認',month:'年月',year:'年',fiscal_year:'年度',date_range:'期間',unknown:'日付未取得',year_as_recorded:'年の記載',month_as_recorded:'年月の記載'};
  const stateNames = {operation:'運行・提供の記録あり',result:'結果・検証の記録あり',trial_end:'実証・対象期間終了',pause:'休止・停止を確認',service_end:'サービス終了を確認',review:'導入見送り・再検討',unknown:'後続未確認'};
  const objectLabels = {value:'数値',unit:'単位',definition:'何を数えたか',period:'対象期間',denominator:'母数',type:'区分',amount:'金額',amount_yen:'金額（円）',amount_jpy:'金額（円）',budget_yen:'予算（円）',settlement_yen:'決算（円）',budget:'予算',settlement:'決算',kind:'会計の区分',revenue_yen:'実証収入（円）',initial_cost_yen:'初期費用（円）',running_cost_yen:'運行費用（円）',reported_profit_loss_yen:'報告損益（円）',audited_settlement_yen:'監査済み決算（円）',initial_cost:'初期費用',operating_cost:'運行費用',running_cost:'運行費用',note:'補足',status:'確認状況',implementation_period:'実施期間',cost_and_financing:'費用と財源',issues:'課題',summary:'概要',text:'記載',source_locator:'原典の該当箇所'};
  let generation = 0, activeRoute;
  const releaseUrl = path => summary?.release ? path+(path.includes('?')?'&':'?')+'v='+encodeURIComponent(summary.release) : path;
  function validateData(key,value) {
    if((key==='index-deep.json'&&Array.isArray(value)&&value.length!==summary?.counts?.deep)||(key==='summary.json'&&value.counts?.deep!==summary?.counts?.deep))throw Error('更新データの版が一致しません。ページを再読み込みしてください。');
    return value;
  }
  function data(path) {
    const key = path.replace(/^data\//,'');
    if(!cache.has(key)) cache.set(key,fetch(releaseUrl(base+'data/'+key)).then(r=>{if(!r.ok)throw Error('データを取得できませんでした ('+r.status+')');return r.json();}).then(value=>validateData(key,value)).catch(e=>{cache.delete(key);throw e;}));
    return cache.get(key);
  }
  const index = layer => data('index-'+layer+'.json');
  const route = () => {
    const [loc,query='']=(location.hash.slice(1)||'home').split('?');const [view,id='']=loc.split('/');
    let decoded=id;try{decoded=decodeURIComponent(id);}catch{}
    return {view,id:decoded,p:Object.fromEntries(new URLSearchParams(query))};
  };
  function hash(view='home',id='',p={}) {const query=new URLSearchParams(Object.entries(p).filter(([,v])=>v!==''&&v!=null));return '#'+view+(id?'/'+encodeURIComponent(id):'')+(query.size?'?'+query:'');}
  function url(view,id='',p={}) {
    if(!standalone && ['projects','records'].includes(view))return hash(view==='projects'?'results':'records',id,p);
    return (standalone?'':base)+hash(view,id,p);
  }
  function btn(label,href,primary=false) {return `<a class="m-btn${primary?' m-primary':''}" href="${escape(href)}" data-mnav>${escape(label)} <span aria-hidden="true">↗</span></a>`;}
  const badge = (s,cls='') => `<span class="m-badge ${cls}">${escape(s)}</span>`;
  const crumb = items => `<div class="m-crumb">${items.map(([label,href])=>href?`<a href="${escape(href)}" data-mnav>${escape(label)}</a>`:escape(label)).join('<span aria-hidden="true">/</span>')}</div>`;
  const pageHead = (kicker,title,desc='') => `<section class="m-hero"><p class="m-kicker">${escape(kicker)}</p><h1>${title}</h1>${desc?`<p class="m-lead">${desc}</p>`:''}</section>`;
  function card(x) {
    if(!x)return '';
    const href = x.layer==='deep'?url('case',x.id,{from:location.hash.slice(1),from_origin:standalone?'municipal':'policy'}):url('record',x.id,{layer:x.layer,from:location.hash.slice(1),from_origin:standalone?'municipal':'policy'});
    return `<article class="m-card" data-record-id="${escape(x.id)}"><div class="m-badges">${badge(x.evidence_label,x.evidence==='deep_result'||x.evidence==='outcome_result'?'m-result':'')}${badge(x.state_label,['pause','service_end'].includes(x.state)?'m-stop':'')}</div><p class="m-place">${escape(x.prefectures?.join('・')||x.region||'所在地未確定')} ${escape(x.municipality||'')}</p><h3><a class="m-card-link" href="${escape(href)}" data-mnav>${escape(x.title)}</a></h3><p class="m-card-result">${numberMarkup(x.excerpt||'原票の内容と出典を確認できます。')}</p><div class="m-card-bottom"><span>${x.last_event_date?'最後の年月記録 '+escape(x.last_event_date):escape(x.years?.join('・')||'年度未取得')}<br>${escape(x.id)}</span><span class="m-arrow" aria-hidden="true">↗</span></div></article>`;
  }
  function pagination(rows,p,view,id='',size=12) {
    const pages=Math.max(1,Math.ceil(rows.length/size)),page=Math.min(pages,Math.max(1,Number(p.page)||1)),start=(page-1)*size;
    const choices=[...new Set([1,page-1,page,page+1,pages])].filter(n=>n>=1&&n<=pages).sort((a,b)=>a-b);
    const nav=pages>1?`<nav class="m-pagination" aria-label="ページ切替">${page>1?`<a class="m-page" href="${escape(url(view,id,{...p,page:page-1}))}" data-mnav>前へ</a>`:''}${choices.map((n,i)=>`${i&&n-choices[i-1]>1?'<span>…</span>':''}<a class="m-page" href="${escape(url(view,id,{...p,page:n}))}" ${n===page?'aria-current="page"':''} data-mnav>${n}</a>`).join('')}${page<pages?`<a class="m-page" href="${escape(url(view,id,{...p,page:page+1}))}" data-mnav>次へ</a>`:''}<span class="m-small">${page} / ${pages}ページ</span></nav>`:'';
    return {slice:rows.slice(start,start+size),nav,page,pages,start};
  }
  function counts(found,total,unit='案件') {return `<div class="m-results-count"><p><b class="m-num" data-filtered-count>${found.toLocaleString('ja-JP')}</b> ${unit}<span class="m-small"> / 全 ${total.toLocaleString('ja-JP')} ${unit}</span></p><a href="${escape(url('scope'))}" class="m-small" data-mnav>収録範囲</a></div>`;}
  const empty = text => `<div class="m-empty"><p>${escape(text)}</p><p class="m-small">未調査・未取得は、取組がないことを意味しません。</p>${btn('条件をリセット',url('projects'))}</div>`;
  function options(values,selected,first) {return `<option value="">${escape(first)}</option>`+values.map(v=>{const [value,label]=Array.isArray(v)?v:[v,v];return `<option value="${escape(value)}" ${String(value)===String(selected)?'selected':''}>${escape(label)}</option>`;}).join('');}
  function filters(rows,p,view,id='',master=[],programs=[]) {
    const municipalities=new Map();for(const r of rows)for(const code of r.codes||[])if(!p.pref||r.prefectures.includes(p.pref))municipalities.set(code,r.municipality||code);
    if(view==='records'&&p.pref)for(const m of master.filter(m=>m.prefecture_name===p.pref))municipalities.set(m.municipality_code,m.municipality_name);
    const y=[...new Set(rows.flatMap(r=>r.years))].sort().reverse(),themes=[...new Set(rows.flatMap(r=>r.themes))].sort();
    return `<form class="m-filter" data-mfilter data-view="${view}" data-id="${escape(id)}"><div class="m-search-row"><input type="search" name="q" value="${escape(p.q||'')}" placeholder="自治体名・取組・キーワード・原ID" aria-label="自治体名・取組・IDを検索"><button class="m-btn m-primary" type="submit">検索 <span>↗</span></button></div><div class="m-filter-grid"><label>都道府県<select name="pref">${options(geography.map(g=>g.name),p.pref,'全国')}</select></label><label>自治体<select name="municipality">${options([...municipalities.entries()].map(([code,name])=>[code,name+' ('+code+')']),p.municipality,view==='records'&&!p.pref?'都道府県を選択':'すべての自治体')}</select></label><label>${view==='records'?'採択等の年度':'出来事の年・年度'}<select name="year">${options(y,p.year,'すべての年')}</select></label><label>テーマ<select name="theme">${options(themes,p.theme,'すべてのテーマ')}</select></label><label>${view==='records'?'原票の区分':'実施状態（最終確認）'}<select name="state">${options([...new Map(rows.map(r=>[r.state,r.state_label])).entries()],p.state,'すべての状態')}</select></label><label>結果資料の確認<select name="evidence">${options([...new Map(rows.map(r=>[r.evidence,r.evidence_label])).entries()],p.evidence,'すべての確認状況')}</select></label></div>${view==='records'?`<label class="m-program-filter">政策・支援枠<select name="program" aria-label="政策・支援枠">${options([...programs.map(x=>[x.program_id,x.name]),...(p.program&&!programs.some(x=>x.program_id===p.program)?[[p.program,'政策史からの対応ID：'+p.program]]:[])],p.program,'すべての政策・支援枠')}</select></label>`:''}${p.batch?`<input type="hidden" name="batch" value="${escape(p.batch)}">`:''}${p.layer?`<input type="hidden" name="layer" value="${escape(p.layer)}">`:''}${p.program&&view!=='records'?`<input type="hidden" name="program" value="${escape(p.program)}">`:''}${p.municipality&&!municipalities.has(p.municipality)?`<input type="hidden" name="municipality" value="${escape(p.municipality)}">`:''}</form>`;
  }
  function filter(rows,p,master=[]) {
    const q=norm(p.q);const m=master.find(x=>x.municipality_code===p.municipality);
    return rows.filter(x=>(!['continuation','latest'].includes(p.batch)||latestCaseIds().includes(x.id))&&(!q||norm([x.id,x.title,x.region,x.municipality,x.codes,x.excerpt,x.prefectures].join(' ')).includes(q))&&(!p.pref||x.prefectures.includes(p.pref))&&(!p.year||x.years.includes(p.year))&&(!p.theme||x.themes.includes(p.theme))&&(!p.state||x.state===p.state)&&(!p.evidence||x.evidence===p.evidence)&&(!p.program||x.program_ids.includes(p.program))&&(!p.municipality||x.codes.includes(p.municipality)||(m&&x.prefectures.includes(m.prefecture_name)&&norm(x.region).includes(norm(m.municipality_name)))));
  }
  function map(rows) {
    const ct=Object.fromEntries(geography.map(g=>[g.name,rows.filter(x=>x.prefectures.includes(g.name)).length]));
    return `<div class="m-map-layout"><div><svg class="m-japan" viewBox="0 0 640 660" role="group" aria-label="都道府県から結果詳査案件を探す地図"><g>${geography.map(g=>`<a href="${escape(url('prefecture',g.name))}" data-mnav aria-label="${g.name} 結果詳査${ct[g.name]}案件" data-count="${ct[g.name]===0?0:ct[g.name]===1?1:ct[g.name]<4?2:3}"><path d="${g.d}"></path><title>${g.name} 結果詳査${ct[g.name]}案件</title></a>`).join('')}</g><text x="30" y="55" fill="#b7b9c4" font-size="15">南西諸島</text></svg><p class="m-small">都道府県単位の詳査収録数。0は取組なしを意味しません。<br>地図：Natural Earth。南西諸島は別枠、一部島しょを省略。</p></div><div><h3>都道府県から、<br>自治体へ。</h3><div class="m-pref-grid">${geography.map(g=>`<a href="${escape(url('prefecture',g.name))}" class="${ct[g.name]?'':'m-zero'}" data-mnav><span>${g.name}</span><b class="m-num">${ct[g.name]}</b></a>`).join('')}</div></div></div>`;
  }
  async function home() {
    const rows=await index('deep');
    const featured=['NORTH-R-01','central_toyono_ai','central_tottori_torimobi','west-44211-15'].map(id=>rows.find(r=>r.id===id));
    return `<section class="m-hero"><div class="m-hero-grid"><div><p class="m-kicker">Municipal Mobility / Results & Change</p><h1>自治体の<br>モビリティ。<br><em>結果と変遷。</em></h1><p class="m-lead">どんな結果が出て、<br>その後、どう変わったか。</p><div class="m-actions">${btn('結果を読む',url('projects'),true)}${btn('地域から探す',url('prefectures'))}${btn(latestBatchLabel(),url('projects','',{batch:'latest'}))}</div></div><div class="m-stamp"><span class="m-num">${countText('deep')}</span><p>結果と変遷を詳査した案件</p><div class="m-split"><div><b>${countText('deep_municipalities')}</b><p>自治体</p></div><div><b>${countText('deep_events')}</b><p>出来事</p></div></div></div></div><div class="m-data-strip"><div><b class="m-num">${countText('deep')}</b><span>詳査した案件</span></div><div><b class="m-num">${countText('deep_municipalities')}</b><span>詳査の対象自治体</span></div><div><b class="m-num">${countText('deep_events')}</b><span>詳査の出来事</span></div><div><b class="m-num">2,120</b><span>別層の採択・支援原票</span></div></div><p class="m-note">${escape(asOf())}基準の選択的な詳査です。全国1,741自治体の調査完了を示すものではありません。</p>${summary?.current_batch?`<p class="m-note">${escape(latestBatchNote())}</p>`:''}</section><section class="m-section"><div class="m-section-head"><div><p class="m-kicker">Read the turning points</p><h2>数字と、その先。</h2></div><a class="m-inline" href="${escape(url('projects'))}" data-mnav>全${countText('deep')}案件へ ↗</a></div><div class="m-grid">${featured.map(card).join('')}</div></section><section class="m-section">${map(rows)}</section><section class="m-section"><p class="m-kicker">Selection is a separate fact</p><h2>採択の先を、<br>原典から確かめる。</h2><p>年度別の採択・支援2,120原票、運行等の参照497原票も収録。結果資料が未取得の原票は、別の確認状況でたどれます。</p><div class="m-actions">${btn('全件検索へ',url('records'),true)}${btn('公式資料343件の点検',url('records','',{layer:'review'}))}${btn('国の政策・制度へ','../mobility-policy-history/')}</div></section>`;
  }
  async function projects(p) {
    const rows=await index('deep'),found=filter(rows,p);const page=pagination(found,p,'projects');
    return pageHead(countText('deep')+' projects / outcomes first','結果から、<br>読む。','利用実績、費用、評価、課題。その後の変更を案件ごとに確認できます。選択的な詳査であり、全国の案件総数ではありません。')+`<section class="m-section"><div class="m-actions" style="margin:0 0 24px">${btn('公式の実績153原票も読む',url('records','',{layer:'review',evidence:'outcome_result'}))}</div>${['continuation','latest'].includes(p.batch)?`<p class="m-note">${escape(latestBatchLabel())}を表示中。${escape(latestBatchNote())}。${btn('全'+countText('deep')+'案件へ',url('projects'))}</p>`:`<p>${btn(latestBatchLabel(),url('projects','',{batch:'latest'}))}</p>`}${filters(rows,p,'projects')}${counts(found.length,rows.length)}${found.length?`<div class="m-grid">${page.slice.map(card).join('')}</div>`:empty('この条件の結果詳査案件はありません。')}${page.nav}</section>`;
  }
  async function prefectures() {return pageHead('Prefecture → Municipality → Project','地域から、<br>その先へ。','都道府県を選ぶと、結果を確認できる自治体と取組を表示します。')+`<section class="m-section">${map(await index('deep'))}</section>`;}
  async function prefecture(name,p) {
    if(!geography.some(g=>g.name===name))return empty('都道府県が見つかりません。');
    const [deep,master]=await Promise.all([index('deep'),data('municipalities.json')]);const rows=deep.filter(x=>x.prefectures.includes(name));const available=new Set(rows.flatMap(x=>x.codes));
    const showAll=p.all==='1'||Boolean(p.q);const munis=master.filter(m=>m.prefecture_name===name&&(showAll||available.has(m.municipality_code))&&(!p.q||norm(m.municipality_name+m.municipality_code).includes(norm(p.q))));
    return crumb([['地域から',url('prefectures')],[name]])+pageHead('Municipalities / '+name,escape(name)+'。','結果を確認できる自治体から表示しています。')+`<section class="m-section"><p class="m-kicker">${rows.length} projects / ${available.size} municipalities</p><h2>自治体を選ぶ。</h2><form class="m-municipal-search" data-mmunicipal data-pref="${escape(name)}"><input type="search" name="q" aria-label="${name}の自治体を検索" placeholder="自治体名・コードで調査範囲も検索" value="${escape(p.q||'')}"><button class="m-btn" type="submit">検索 ↗</button></form>${munis.length?`<ul class="m-municipality-list">${munis.map(m=>`<li><a href="${escape(url('municipality',m.municipality_code))}" data-mnav><b>${escape(m.municipality_name)}</b><span>${m.municipality_code} ／ ${available.has(m.municipality_code)?rows.filter(x=>x.codes.includes(m.municipality_code)).length+'詳査案件':m.research_depth}</span></a></li>`).join('')}</ul>`:empty('該当する自治体の詳査は未収録です。')}${!showAll?`<div class="m-actions">${btn('未調査を含む自治体名簿から探す',url('prefecture',name,{all:'1'}))}</div>`:''}<p class="m-note">詳査未収録でも、採択原票・旧調査・自治体履歴が見つかる場合があります。</p><div class="m-actions">${btn(name+'の採択・支援原票',url('records','',{pref:name}))}</div></section>`;
  }
  async function municipality(code,p) {
    const [master,deep,local,legacy]=await Promise.all([data('municipalities.json'),index('deep'),index('local'),index('legacy')]);const m=master.find(x=>x.municipality_code===code);
    if(!m)return empty('自治体コードが見つかりません。');const d=deep.filter(x=>x.codes.includes(code)),l=local.filter(x=>x.codes.includes(code)),b=legacy.filter(x=>x.codes.includes(code));
    return crumb([['地域から',url('prefectures')],[m.prefecture_name,url('prefecture',m.prefecture_name)],[m.municipality_name]])+pageHead(m.prefecture_name+' / '+code,escape(m.municipality_name)+'。','同じ自治体の取組も、案件ごとに分けて表示します。')+`<section class="m-section"><h2>結果と変遷。</h2>${d.length?`<div class="m-grid">${d.map(card).join('')}</div>`:empty('この自治体の結果詳査案件は未収録です。')}<div class="m-actions">${btn('採択・支援の地域表記から探す',url('records','',{pref:m.prefecture_name,municipality:code,q:m.municipality_name}))}</div></section>${l.length?`<section class="m-section"><h2>自治体公式履歴。</h2><p class="m-small">原票ごとに記録。別事業間の継承関係は推定しません。</p><div class="m-grid">${l.map(card).join('')}</div></section>`:''}${b.length?`<section class="m-section"><h2>旧調査の代表事例。</h2><div class="m-grid">${b.map(card).join('')}</div></section>`:''}`;
  }
  async function detailRow(layer,id) {const rows=await index(layer);const row=rows.find(x=>x.id===id);if(!row)return {};const shard=await data(row.detail);return {row,detail:shard[id]};}
  function returnUrl(p,fallback='projects') {const from=p.from||fallback;return /^[a-zA-Z]+(?:\/|\?|$)/.test(from)?(p.from_origin==='policy'?'../mobility-policy-history/':(standalone?'':base))+'#'+from:url(fallback);}
  function refLinks(refs,view,id,p) {return list(refs).filter(Boolean).map(r=>`<a class="m-ref" href="${escape(url(view,id,{...p,section:'source-'+(r.source_id||r)}))}" data-mnav title="${escape(r.locator||'原典の該当箇所')}">${escape(r.source_id||r)}</a>`).join('');}
  function sourceList(sources) {
    return `<ul class="m-source-list">${sources.map(s=>{const id=s.source_id||s.id;return `<li id="source-${escape(id)}"><p class="m-src-id">${escape(id||'原典')}</p><h3>${escape(s.title||s.name||'原典資料')}</h3><dl><dt>公表者</dt><dd>${escape(s.publisher||'資料ごとに確認')}</dd><dt>資料の公表日・記載日</dt><dd>${escape(s.document_date||s.date||s.dates?.join(' / ')||'未取得')}<br>${escape(s.reporting_period||'')}</dd><dt>該当箇所</dt><dd>${escape(s.locator||s.locators?.join(' / ')||'原典の該当記述を参照')}</dd><dt>原典の最終確認日</dt><dd>${escape(s.accessed_at||s.accessed||'未取得')}</dd></dl>${/^https:\/\//.test(s.url||'')?`<a href="${escape(s.url)}" target="_blank" rel="noopener noreferrer">公開原典を開く ↗</a>`:'<p class="m-small">公開URLの確定待ち</p>'}</li>`;}).join('')}</ul>`;
  }
  function isPlanned(ev) {return ['planned','actual','interim','trial_ended','service_ended','suspended'].includes(ev.phase)?ev.phase==='planned':/予定|目標|計画|planned|future/i.test([ev.event_text,ev.date_label,ev.status_as_recorded].join(' '));}
  function eventList(events,view,id,p) {
    return `<ol class="m-event-list">${events.map(ev=>{const planned=isPlanned(ev);const evrefs=ev.source_refs||[{source_id:ev.source_id,locator:ev.source_locator}];return `<li class="m-event ${planned?'m-planned':''}" id="event-${escape(ev.event_id)}"><time>${escape(ev.date_label||'日付未取得')}</time>${ev.evidence_conflict?badge('原典間の相違あり・確定実績として扱わない','m-stop'):planned?badge('予定・目標（実績に含めない）','m-stop'):''}<h3>${escape(ev.event_text)}</h3><p class="m-small">${escape(ev.status_as_recorded||'原典の記載')} ／ ${escape(precisionNames[ev.date_precision]||'原文の日付精度')}<br>${ev.date_role&&ev.date_role!=='event_date_as_recorded'?'資料日・報告期間の記載：実際の実施日とは別。<br>':''}${escape(ev.event_id)}</p>${refLinks(evrefs,view,id,p)}</li>`;}).join('')}</ol>`;
  }
  function claimHtml(c,id,p) {return `<div class="m-claim" id="claim-${escape(c.claim_id)}"><h3>${escape(c.label)}${c.analysis_flag||c.claim_type==='analysis'?' ［分析・解釈］':''}</h3><p>${numberMarkup(c.statement)}</p><div class="m-refline">${escape(c.claim_id)} ${refLinks(c.source_refs,'case',id,p)}</div></div>`;}
  function shortClaim(c,id,p) {
    if(!c)return '<p class="m-small">未取得</p>';
    const parts=c.statement.split(/(?<=。)\s*/u).filter(Boolean),first=parts[0]||c.statement;
    return `<p>${escape(first)}</p>${parts.length>1?`<details><summary>確認範囲</summary><p class="m-small">${escape(parts.slice(1).join(' '))}</p></details>`:''}<p class="m-small">${escape(c.claim_id)} ${refLinks(c.source_refs,'case',id,p)}</p>`;
  }
  // These callouts are literal observations, not calculated success measures.
  function resultFigures(c,p) {
    const definitions={
      'NORTH-R-01':[
        ['延べ乗車','2,190','人','2024.10.15–2025.02.11','利用実績'],
        ['予約','1,979','件','2024.10.15–2025.02.11','利用実績'],
        ['乗合が発生した予約','284','件','2024.10.15–2025.02.11','利用実績']],
      'central_toyono_ai':[
        ['R4年度','115','人/日','無料実証・28運行日','結果観測'],
        ['R5年度','26','人/日','有料実証・126運行日','結果観測'],
        ['R6年度','18','人/日','有料実証・31運行日','結果観測']],
      'central_tottori_torimobi':[
        ['アプリ調査','269','人','R7年度の調査対象','結果観測'],
        ['外出が増えた','17.1','%','R7年度アプリ調査・269人','結果観測'],
        ['他の公共交通利用が増えた','2.6','%','R7年度アプリ調査・269人','結果観測']],
      'west-44211-15':[['延べ乗車','99','乗車','FY2022・安心院まちなか循環便','利用実績']]
    };
    const figures=definitions[c.case_id];if(!figures)return '';
    return `<div class="m-figure-strip" data-columns="${figures.length}" aria-label="原典で確認した主な実績">${figures.map(([label,value,unit,context,claimLabel])=>{
      const claim=c.claims.find(x=>x.label===claimLabel&&x.statement.includes(value));
      if(!claim)return '';
      return `<dl class="m-figure"><dt>${escape(label)}</dt><dd><b class="m-figure-value">${escape(value)}</b><span class="m-figure-unit">${escape(unit)}</span><span class="m-figure-context">${escape(context)}</span>${refLinks(claim.source_refs,'case',c.case_id,p)}</dd></dl>`;
    }).join('')}</div>`;
  }
  async function caseDetail(id,p) {
    const {row,detail:c}=await detailRow('deep',id);if(!c)return empty('案件IDが見つかりません。');
    const claims=c.claims,call=claims.find(x=>x.section==='call'),selection=claims.find(x=>x.section==='selection'),lesson=claims.find(x=>x.section==='lesson');
    const results=claims.filter(x=>x.section==='result'),unknown=results.filter(x=>/^(未確認|未取得|この資料では未取得)/.test(x.statement)),known=results.filter(x=>!unknown.includes(x));
    const events=[...c.events].sort((a,b)=>(a.sort_key||'9999').localeCompare(b.sort_key||'9999'));
    const parameter={...p};delete parameter.section;
    const related=c.related_baseline||[];
    const localityCodes=list(c.municipality_codes||row.codes||c.municipality_code);
    const background = `<details class="m-background"><summary>公募・採択の背景（参考）</summary><div class="m-call-grid"><div><h2>公募と目的。</h2>${shortClaim(call,id,parameter)}</div><div><h2>採択と実施内容。</h2>${shortClaim(selection,id,parameter)}</div></div><p class="m-small">公募・採択は結果とは別の事実です。結果と年月変遷を先に掲載しています。</p></details>`;
    const sourceDates=[...new Set(c.sources.map(s=>s.document_date).filter(Boolean))];
    return crumb([['一覧へ',returnUrl(p)],[c.prefecture,url('prefecture',c.prefecture)],[c.municipality,url('municipality',c.municipality_code)]])+`<section class="m-hero m-detail-title"><p class="m-kicker">Result history / ${escape(id)}</p><p class="m-local">${escape(c.prefecture)} ${escape(c.municipality)}</p><h1>${escape(c.title)}</h1><div class="m-badges">${badge('結果・変遷を詳査','m-result')}${badge(c.state_label,['service_end','pause'].includes(c.state)?'m-stop':'')}${badge('自治体コード '+localityCodes.join('・'))}</div><div class="m-observation"><p class="m-small">最後に確認できた状況</p><p>${escape(c.current_observation)}</p><p class="m-small">最後の年月が分かる記録：${escape(row.last_event_date)}${c.current_status_checked_at?' ／ 原典確認日 '+escape(c.current_status_checked_at):''}<br>${escape(asOf())}を調査基準日とし、記録後の状態は推定しません。</p></div></section><div class="m-detail-layout"><article><section class="m-section" id="results"><p class="m-kicker">What actually happened</p><div class="m-step-heading"><span class="m-num">03</span><h2>結果報告。</h2></div>${resultFigures(c,parameter)}${(c.observation_ids?.length?known.filter(x=>x.claim_id.endsWith(':summary')):known).map(x=>claimHtml(x,id,parameter)).join('')}${caseMetrics(c.metrics,id,parameter)}${c.observation_ids?.length?known.filter(x=>!x.claim_id.endsWith(':summary')).map(x=>claimHtml(x,id,parameter)).join(''):''}${unknown.length?`<details><summary>不足している項目 ${unknown.length}</summary>${unknown.map(x=>claimHtml(x,id,parameter)).join('')}<p class="m-small">今回の資料で未取得。未公表・不存在とは断定しません。</p></details>`:''}</section><section class="m-section" id="changes"><div class="m-step-heading"><span class="m-num">04</span><h2>年月順に、たどる。</h2></div><p class="m-small">確認できた転換点だけを表示。記録のない期間は運行線でつなぎません。</p><div class="m-trace" aria-label="出来事の見取り図">${events.map(ev=>`<a href="${escape(url('case',id,{...parameter,section:'event-'+ev.event_id}))}" data-mnav><b>${escape(ev.date_label)}</b><span>${escape(ev.event_text)}</span></a>`).join('')}</div>${eventList(events,'case',id,parameter)}</section><section class="m-section"><p class="m-kicker">One lesson / analysis</p><p class="m-lesson">${escape(lesson?.statement||'教訓は未整理です。')}</p><p class="m-small">教訓は原典の事実から導いた分析です。${escape(lesson?.claim_id||'')}</p></section>${background}${continuityNotes(c)}${related.length?`<section class="m-section"><h2>旧調査との照合。</h2>${related.map(x=>`<p><a href="../mobility-policy-history/#case/${escape(x.baseline_case_id)}">${escape(x.baseline_case_name)} ↗</a></p><p class="m-small">同じ原典を参照しています。事業同一性・継承は未確定です。</p>`).join('')}</section>`:''}<section class="m-section" id="sources"><h2>公開原典を読む。</h2>${sourceList(c.sources)}</section><section class="m-section"><details><summary>原ID・入力資料・訂正履歴</summary><p class="m-provenance">原案件ID：${escape(id)}<br>入力：${escape(c.provenance.source_file)}<br>原票位置：${escape(c.provenance.source_pointer)}<br>${claims.length}記述・${events.length}出来事・${c.sources.length}出典参照を保持。別案件への自動統合は行っていません。</p>${claims.some(x=>x.section==='metadata')?`<details><summary>調査範囲メタデータ（結果の事実とは別）</summary>${claims.filter(x=>x.section==='metadata').map(x=>claimHtml(x,id,parameter)).join('')}</details>`:''}${c.corrections.map(x=>`<p>${escape(x.reason)}</p><p class="m-small">訂正前：${escape(x.old_statement)}<br>訂正後：${escape(x.corrected_statement)}</p>`).join('')}<a class="m-inline" href="${escape(base+row.detail)}" target="_blank" rel="noopener">構造化データを開く ↗</a></details></section></article><aside><p><b>この案件を読む</b></p><a href="${escape(url('case',id,{...parameter,section:'results'}))}" data-mnav>03 結果報告 ↓</a><a href="${escape(url('case',id,{...parameter,section:'changes'}))}" data-mnav>04 年表 ↓</a><a href="${escape(url('case',id,{...parameter,section:'sources'}))}" data-mnav>公開原典 ↓</a><a href="${escape(url('municipality',c.municipality_code))}" data-mnav>${escape(c.municipality)}の別案件 ↗</a><p class="m-small">資料の公表日と出来事の日付は別です。公表日は各出典に記載しています。</p></aside></div>`;
  }
  function continuityNotes(c) {
    if(!c.baseline_case_id&&!list(c.evidence_conflicts).length&&!list(c.research_corrections).length)return '';
    return `<section class="m-section"><h2>旧記録との照合・異説。</h2>${c.baseline_case_id?`<p>既存ID ${escape(c.baseline_case_id)} の増補です。新規事業として数えません。</p><p>${objectValue(c.identity_evidence||'同一性根拠未取得')}</p><a href="../mobility-policy-history/#case/${encodeURIComponent(c.baseline_case_id)}">旧調査の原記録を読む ↗</a>`:''}${c.correction_note?`<p class="m-note">${escape(c.correction_note)}</p>`:''}${list(c.evidence_conflicts).length?`<h3>原典間の相違（確定訂正ではありません）</h3>${objectValue(c.evidence_conflicts)}<p class="m-note">相反する記載は原典別に保持しています。双方を確定実績として合算・採用しません。</p>`:''}${c.baseline_event_context?`<details><summary>旧出来事の原記録と照合</summary>${objectValue(c.baseline_event_context)}</details>`:''}${list(c.research_corrections).length?`<h3>訂正・再検証の履歴</h3>${objectValue(c.research_corrections)}`:''}</section>`;
  }
  function caseMetrics(metrics,id,p) {
    if(!list(metrics).length)return '';
    const metricRefs=m=>m.source_refs||(m.source?[{...m.source,source_id:m.source.source_id||m.source.document_id}]:[]);
    const phaseNames={actual:'実績の観測',interim:'途中経過',planned:'計画・目標',unknown:'区分未確認'};
    const group=(values,planned)=>!values.length?'':`<h3 class="m-metric-heading">${planned?'計画・目標（実績とは別）':'指標の定義・期間・根拠'}</h3><div class="m-table-wrap"><table><thead><tr><th>何を測ったか / 原ID</th><th>値・単位</th><th>対象期間 / 区分</th><th>根拠</th></tr></thead><tbody>${values.map(m=>`<tr><td>${escape(m.definition||'定義未取得')}<br><span class="m-small">${escape(m.metric_id||m.id||'')}</span></td><td>${escape(m.value??'未取得')} ${escape(m.unit||'')}</td><td>${escape(m.period||'期間未取得')}<br>${escape(phaseNames[m.phase]||'原典の区分を参照')}${m.verification&&m.verification!=='verified'?'<br>数値未確認':''}</td><td>${refLinks(metricRefs(m),'case',id,p)}<div class="m-small">${list(metricRefs(m)).map(r=>escape(r.locator||'')).join(' / ')}</div></td></tr>`).join('')}</tbody></table></div>`;
    return group(metrics.filter(m=>m.phase!=='planned'),false)+group(metrics.filter(m=>m.phase==='planned'),true);
  }
  function resultExtras(rv) {
    return [['結果の補足',rv.result_context],['利用者の評価',rv.user_evaluation],['課題',rv.challenges],['目標と実績の比較',rv.target_gap]].filter(([,v])=>v&&plain(v)!==rv.issues&&plain(v)!==rv.summary).map(([label,v])=>`<div class="m-claim"><h3>${escape(label)}</h3><p>${escape(plain(v))}</p></div>`).join('');
  }
  function objectValue(v) {
    if(v==null||v==='')return '未取得';
    if(typeof v==='number')return escape(v.toLocaleString('ja-JP',{maximumFractionDigits:20}));
    if(Array.isArray(v))return `<ul>${v.map(x=>`<li>${objectValue(x)}</li>`).join('')}</ul>`;
    if(typeof v==='object')return `<div class="m-table-wrap"><table><tbody>${Object.entries(v).filter(([k])=>!['sources','source_ids','source_refs','raw'].includes(k)).map(([k,x])=>`<tr><th>${escape(objectLabels[k]||k)}</th><td>${objectValue(x)}</td></tr>`).join('')}</tbody></table></div>`;
    const names={confirmed:'確認済み',not_obtained:'未取得',reported_demonstration_accounts_not_audited_settlement:'実証報告の会計値（監査済み決算とは別）'};
    return escape(names[v]||v).replace(/\n/g,'<br>');
  }
  function metricsTable(metrics,kind) {return !metrics?.length?'':`<h3>${kind==='plan'?'当初計画・目標（実績とは別）':'実績の指標'}</h3><div class="m-table-wrap"><table><thead><tr><th>何を測ったか</th><th>値・単位</th><th>対象期間・母数</th></tr></thead><tbody>${metrics.map(m=>`<tr><td>${escape(m.definition||m.metric||m.name||'原典の記載')}</td><td><b class="m-metric-value">${escape(m.value??m.amount??'未取得')}</b> ${escape(m.unit||'')}</td><td>${escape(m.period||'対象期間未取得')}${m.denominator?' ／ 母数 '+escape(m.denominator):''}</td></tr>`).join('')}</tbody></table></div>`;}
  async function records(p) {
    const layer=layerNames[p.layer]?p.layer:'selection';const [rows,master,progs]=await Promise.all([index(layer),(p.municipality||p.pref)?data('municipalities.json'):Promise.resolve([]),data('programs.json')]);const found=filter(rows,p,master),page=pagination(found,{...p,layer},'records');
    const pr=progs.find(x=>x.program_id===p.program||x.baseline_program_ids.includes(p.program));
    const units={selection:'原票',reference:'参照原票',review:'点検記録',local:'履歴原票',legacy:'事例',history:'索引行'};
    return pageHead('Full record search','原票を、<br>たどる。','資料の種類ごとに検索します。年度別の採択原票を、独立した事業数には合算しません。')+`<section class="m-section"><nav class="m-layers" aria-label="検索する資料の種類">${Object.entries(layerNames).map(([key,label])=>`<a href="${escape(url('records','',{...p,layer:key,page:'',state:'',evidence:''}))}" ${layer===key?'aria-current="page"':''} data-mnav>${label} ${summary.counts[key==='legacy'?'baseline_cases':key]}</a>`).join('')}</nav>${p.program?`<h3>${escape(pr?.name||p.program)}</h3><p class="m-small">政策IDとの既存対応を使用。同一事業・成果達成を保証しません。テーマ類似だけで採択・財源を結び付けません。 <a href="${escape(url('records','',{...p,program:'',page:''}))}" data-mnav>制度条件を解除 ↗</a></p>`:''}${filters(rows,{...p,layer},'records','',master,progs)}${p.municipality?'<p class="m-note">地域表記の一致も含みます。個別案件の事業範囲・主体の一致を確定したものではありません。</p>':''}${counts(found.length,rows.length,units[layer])}${found.length?`<div class="m-grid">${page.slice.map(card).join('')}</div>`:empty('この条件に一致する原票はありません。')}${page.nav}${layer==='review'?'<p class="m-note">343点検記録の結果証拠は、実績153・調査成果1・中間結果1。部分実施1・終了のみ1は別扱いです。申請計画や事業概要も、資料種別を保って収録しています。</p>':''}</section>`;
  }
  async function recordDetail(id,p) {
    const layer=layerNames[p.layer]?p.layer:'selection';const {row,detail:r}=await detailRow(layer,id);if(!r)return empty('原票IDが見つかりません。');
    if(layer==='legacy')return crumb([['一覧へ',returnUrl(p,'records')]])+pageHead('Baseline / original case',escape(row.title),escape(row.region||''))+`<section class="m-section"><p>${escape(row.excerpt)}</p>${summary?.legacy_updates?.[id]?`<p class="m-note">同一IDの追加詳査があります。旧記述を上書きせず、訂正履歴・原典間の相違も比較できます。</p>${btn('最新の結果詳査・旧記録との照合',url('case',id),true)}`:''}${btn('政策史ページの元事例を読む','../mobility-policy-history/#case/'+encodeURIComponent(id),true)}<p class="m-small">旧調査の111事例は元ページ・元ID・467の出来事を保持しています。</p></section>`;
    const rv=layer==='review'?r:r.review;const raw=rv?.raw_record||{};const correction=r.classification_correction;
    let sources=[];
    if(rv) {
      sources=[{source_id:rv.summary_evidence_source_id||rv.source_id,url:rv.summary_evidence_url||rv.source_url,title:'結果・要約の根拠',locator:rv.summary_evidence_locator||rv.source_locator,document_date:rv.document_date,reporting_period:rv.reporting_period,publisher:rv.source_publisher||'公開原典の発行主体'}];
      const extra=list(rv.additional_result_sources);for(const s of extra)if(typeof s==='object')sources.push({source_id:s.source_id||s.id||'additional-'+(sources.length+1),title:s.title||'追加の結果原典',url:s.url||s.source_url,locator:s.locator||s.source_locator,document_date:s.document_date});
    }
    if(r.source_url&&!sources.some(s=>s.url===r.source_url))sources.push({source_id:r.source_ids?.[0]||'original',url:r.source_url,title:'採択・原票の根拠',locator:r.source_locator,document_date:r.announcement_date||r.publication_date});
    for(const src of r.resolved_sources||[]) {const i=sources.findIndex(s=>s.source_id===src.source_id);if(i>=0)sources[i]=src;else sources.push(src);}
    const evs=layer==='review'?r.events:(r.review_events||[]);
    return crumb([['原票一覧へ',returnUrl(p,'records')],[layerNames[layer]]])+`<section class="m-hero m-detail-title"><p class="m-kicker">${escape(layerNames[layer])} / ${escape(id)}</p><h1>${escape(row.title)}</h1><p class="m-local">${escape(r.region||row.prefectures.join('・'))}</p><div class="m-badges">${badge(row.evidence_label,rv?.result_evidence_kind==='outcome_result'?'m-result':'')}${badge(row.state_label)}</div><p class="m-note">${escape(r.counting_unit||'原票・資料ごとの記録')}。採択、実施、成果、現在の継続は別に確認します。</p></section><div class="m-detail-layout"><article><section class="m-section m-call-grid"><div><div class="m-step-heading"><span class="m-num">01</span><h2>公募と目的。</h2></div><p>${escape(raw.call_brief?.text||'公募条件の詳細は、この原票では未取得です。結果資料の整理を優先しています。')}</p></div><div><div class="m-step-heading"><span class="m-num">02</span><h2>採択・主体。</h2></div><p>${escape(raw.selection_brief?.text||r.status||r.support_type||'原票の内容を保持')}</p><p>${escape(r.operator||rv?.operator||'主体名は原典で確認')}</p><p class="m-small">${escape(r.operator_role||'原典の主体欄。実際の運行主体・契約主体との一致は別確認。')}</p></div></section><section class="m-section" id="results"><div class="m-step-heading"><span class="m-num">03</span><h2>結果と確認範囲。</h2></div>${rv?`<div class="m-badges">${badge(rv.result_evidence_label||row.evidence_label,'m-result')}</div><div class="m-claim"><h3>確認できた内容</h3><p>${escape(rv.summary||'要約未収録')}</p></div>${metricsTable(rv.outcome_metrics||rv.result_observations,'actual')}${metricsTable(rv.plan_metrics,'plan')}<div class="m-claim"><h3>対象期間</h3><p>${escape(rv.result_period||rv.reporting_period||'未取得')}</p></div><div class="m-claim"><h3>費用と財源</h3><p>${escape(rv.costs_summary||'費用実績は未取得')}</p>${rv.costs_structured&&rv.costs_structured.status==='confirmed'?objectValue(rv.costs_structured):''}</div><div class="m-claim"><h3>課題・評価の限界</h3><p>${escape(rv.issues||raw.results?.issues||raw.results?.result_evidence_limit||'該当資料の範囲を参照')}</p></div>${resultExtras(rv)}<div class="m-claim"><h3>後続の確認</h3><p>${escape(rv.followup_status==='after_report_not_verified'?'報告後の継続・変更は未確認です。':plain(raw.continuation_status||rv.followup_status||'未確認'))}</p></div>`:`<p>${escape(r.description||r.outcomes||r.status||'この原票では結果資料を未取得です。')}</p>${r.notes?`<p class="m-small">${escape(r.notes)}</p>`:''}<p class="m-note">確認済みなのは上記の原票の事実です。利用実績・決算・継続状況は、別の原典が必要です。</p>`}${correction?`<details><summary>掲載資料の種別を確認する</summary><p>旧項目名は「成果資料URL」でしたが、本文の種別は「${escape(correction.corrected_document_type_label)}」です。</p><p class="m-small">URLのreport表記や旧項目名だけで実績報告とは判定しません。${escape(correction.overlay_id)}</p>${correction.legacy_url?`<a href="${escape(correction.legacy_url)}" target="_blank" rel="noopener">旧掲載資料の本文を確認 ↗</a>`:''}</details>`:''}</section><section class="m-section"><div class="m-step-heading"><span class="m-num">04</span><h2>確認できた経過。</h2></div>${evs.length?eventList(evs,'record',id,{...p,layer}):`<p>${escape(r.event_date||r.announcement_date||'日付未取得')}　${escape(r.description||r.status||'原典の記録')}</p><p class="m-small">${r.event_date?'出来事の日付':r.announcement_date?'資料の発表日（実施日とは別）':'日付の精度は原票のまま保持しています。'}</p>`}</section>${raw.lesson?`<section class="m-section"><p class="m-kicker">One lesson / analysis</p><p class="m-lesson">${escape(raw.lesson)}</p></section>`:''}<section class="m-section" id="sources"><h2>公開原典を読む。</h2>${sourceList(sources)}</section><section class="m-section"><details><summary>原ID・元ファイル・政策との対応</summary><p class="m-provenance">原票ID ${escape(id)}<br>入力 ${escape(r.provenance.source_file)}<br>位置 ${escape(r.provenance.source_pointer)}</p>${row.program_ids.length?`<p>対応する制度ID：${row.program_ids.map(pid=>`<a class="m-ref" href="${escape(url('records','',{program:pid}))}" data-mnav>${escape(pid)}</a>`).join('')}</p>`:''}${r.baseline_program_ids?.length?`<p>${r.baseline_program_ids.map(pid=>`<a href="../mobility-policy-history/#program/${escape(pid)}">元の政策説明へ ↗</a>`).join(' / ')}</p>`:''}${rv?.selection_record_ids?.length?`<p>対応する採択原票：${rv.selection_record_ids.map(z=>`<a href="${escape(url('record',z,{layer:'selection'}))}" data-mnav>${escape(z)}</a>`).join(' / ')}</p>`:''}<a href="${escape(base+row.detail)}" target="_blank" rel="noopener">原票の構造化データ ↗</a></details></section></article><aside><p><b>記録の読み方</b></p><p>計画値と実績値を分けています。年度や対象が異なる数値から達成率を計算しません。</p><a href="${escape(url('records','',{layer}))}" data-mnav>${escape(layerNames[layer])}の全件へ ↗</a><a href="${escape(url('scope'))}" data-mnav>資料種別・収録範囲 ↗</a></aside></div>`;
  }
  async function timeline(p) {
    const [rows,events]=await Promise.all([index('deep'),data('timeline-index.json')]);const caseMap=new Map(rows.map(x=>[x.id,x]));const q=norm(p.q);
    const found=events.filter(ev=>(!p.year||ev.year===p.year)&&(!q||norm(ev.event_text+' '+ev.case_id+' '+caseMap.get(ev.case_id)?.title+' '+caseMap.get(ev.case_id)?.municipality).includes(q)));
    const ct=Object.fromEntries(Array.from({length:11},(_,i)=>[2016+i,events.filter(e=>e.year===String(2016+i)).length]));const max=Math.max(...Object.values(ct));const pg=pagination(found,p,'timeline','',24);
    return pageHead(countText('deep_events')+' documented events','変化の年を、<br>選ぶ。','年・年度・期間の原記載を保持。棒は収録記録数で、運行期間や実証の総数を表しません。')+`<section class="m-section"><div class="m-year-track" aria-label="年別の収録出来事件数">${Object.entries(ct).map(([y,n])=>`<a href="${escape(url('timeline','',{...p,year:y,page:''}))}" ${p.year===y?'aria-current="page"':''} data-mnav><b>${n}</b><i style="--bar:${Math.round(n/max*100)}%"></i><span>${y}</span></a>`).join('')}</div><form class="m-search-row" data-mtimeline><input class="search-input" type="search" name="q" value="${escape(p.q||'')}" aria-label="年表を検索" placeholder="自治体名・出来事で検索">${p.year?`<input type="hidden" name="year" value="${escape(p.year)}">`:''}<button class="m-btn" type="submit">検索 ↗</button></form>${counts(found.length,events.length,'出来事')}${p.year?`<p>${escape(p.year)}年・年度　<a href="${escape(url('timeline'))}" data-mnav>全年へ戻る</a></p>`:''}<ol class="m-event-list">${pg.slice.map(ev=>`<li class="m-event"><time>${escape(ev.date_label)}</time><p class="m-small">${escape(caseMap.get(ev.case_id)?.prefectures.join('・'))} ${escape(caseMap.get(ev.case_id)?.municipality)}</p><h3><a href="${escape(url('case',ev.case_id,{from:location.hash.slice(1),section:'event-'+ev.event_id}))}" data-mnav>${escape(ev.event_text)} ↗</a></h3><p class="m-small">${escape(caseMap.get(ev.case_id)?.title)}<br>${escape(ev.event_id)}${ev.evidence_conflict?' ／ 原典間の相違あり・確定実績として扱わない':isPlanned(ev)?' ／ 予定・目標':''}</p></li>`).join('')}</ol>${pg.nav}</section>`;
  }
  async function scope() {
    const [s,a]=await Promise.all([data('summary.json'),fetch(releaseUrl((standalone?'':base)+'verification/data-reconciliation.json')).then(r=>r.json())]);
    const rows=[['旧調査の政策・事例・出来事','66政策 / 111事例 / 467出来事','政策・事例・出来事は別の単位'],['年度別の採択・支援','2,120原票','人材支援339原票を含む。独立事業数ではない'],['運行等の参照','497原票','採択原票への加算はしない'],['全国自治体マスタ','1,741自治体','調査母集団。調査完了数ではない'],['追加詳査',countText('deep')+'案件 / '+countText('deep_municipalities')+'自治体 / '+countText('deep_events')+'出来事','同一自治体の別案件を統合しない'],['公式掲載資料の点検','343点検記録','実績153、調査成果1、中間結果1'],['部分確認','部分実施1 / 終了のみ1','実績結果153とは別扱い'],['結果未取得','186点検記録','未公表・不存在を意味しない'],['自治体公式履歴','100原票','国費の有無・制度帰属とは別'],['年度履歴索引','3,041行','同じ原票への参照を含む。総実証数に加算しない']];
    return pageHead('Scope / provenance / reconciliation','何が分かり、<br>何が残るか。','実装の完了と、全国調査の完了は別です。')+`<section class="m-section"><h2>収録数の読み方。</h2><div class="m-table-wrap"><table><thead><tr><th>資料の層</th><th>収録数</th><th>数え方</th></tr></thead><tbody>${rows.map(r=>`<tr>${r.map((v,i)=>`<${i?'td':'th'}>${escape(v)}</${i?'td':'th'}>`).join('')}</tr>`).join('')}</tbody></table></div></section><section class="m-section"><h2>原票から画面への照合。</h2><div class="m-table-wrap"><table><thead><tr><th>層</th><th>入力ID数</th><th>検索ID数</th><th>詳細ID数</th><th>欠落ID</th></tr></thead><tbody>${a.layers.map(r=>`<tr><th>${escape(layerNames[r.layer]||'結果詳査')}</th><td>${r.input_count}</td><td>${r.index_count}</td><td>${r.detail_count}</td><td>${r.missing_ids.length}</td></tr>`).join('')}</tbody></table></div><p>${countText('claims')}の記述、${countText('deep_events')}の詳査出来事、216の公式結果関連の出来事を保持。343原票へ資料種別の訂正を適用しています。</p><p class="m-small">旧原JSONと拡張版baselineには${a.baseline_field_differences.length}のフィールド差があり、両入力を別々に保持しています。旧原JSONの原記録を上書きしていません。</p><div class="m-actions">${btn('件数・IDの照合データ',(standalone?'':base)+'verification/data-reconciliation.json')}${btn('原ID・表示先の対応',base+'data/provenance.json')}</div></section><section class="m-section"><h2>現在の確認限界。</h2><div class="m-table-wrap"><table><thead><tr><th>自治体データの調査状態</th><th>自治体数</th></tr></thead><tbody>${Object.entries(s.municipality_research_depths||{}).map(([label,n])=>`<tr><th>${escape(label)}</th><td>${n}</td></tr>`).join('')}</tbody></table></div><p class="m-small">追加${countText('deep')}案件の${countText('deep_municipalities')}自治体を重ねた、収録データ上の分類です。候補一致は一次資料による結果確認とは別です。</p><p>${countText('deep')}案件は、結果原典を追える案件を選んだ詳査です。全国1,741自治体の全年度・全事業を調査したものではありません。</p><p>資料を読めても、報告後の継続、恒常収支、利用者の生活改善まで確認できるとは限りません。各案件に、確認した事実と不足項目を記載しています。</p><p>原典の公表日、出来事の日付、調査基準日は別々に表示しています。予定日を過ぎただけでは、実施済みへ変更しません。</p></section><section class="m-section"><h2>入力資料の照合。</h2><p class="m-small">受領した入力をファイルとして解析し、サイズとSHA-256を確認。統合ZIP内のJSONと単独JSONもバイト単位で一致しています。</p><div class="m-table-wrap"><table><thead><tr><th>入力資料</th><th>バイト数</th><th>照合SHA-256</th></tr></thead><tbody>${s.input_files.map(f=>`<tr><th>${escape(f.filename)}</th><td>${f.bytes.toLocaleString('ja-JP')}</td><td class="m-small">${f.sha256}</td></tr>`).join('')}</tbody></table></div></section>`;
  }
  async function content(r) {
    switch(r.view) {
      case 'home':return home();case 'projects':case 'results':return projects(r.p);case 'prefectures':return prefectures();case 'prefecture':return prefecture(r.id,r.p);case 'municipality':return municipality(r.id,r.p);case 'case':return caseDetail(r.id,r.p);case 'records':return records(r.p);case 'record':return recordDetail(r.id,r.p);case 'timeline':return timeline(r.p);case 'scope':return scope();default:return empty('ページが見つかりません。');
    }
  }
  async function mountTeasers() {
    const host=document.querySelector('[data-featured-results]');if(!host)return;try{const rows=await index('deep');if(host.isConnected)host.innerHTML=['NORTH-R-01','central_tottori_torimobi'].map(id=>card(rows.find(r=>r.id===id))).join('');}catch{if(host.isConnected)host.innerHTML='<p class="m-small">結果一覧から案件を確認できます。</p>';}
  }
  function shell(r) {return `<div class="wrap m-root" data-results-host data-route="${escape(JSON.stringify(r))}"><p class="m-loading" role="status">結果の記録を読み込んでいます。</p></div>`;}
  async function mount() {
    const host=document.querySelector('[data-results-host]');if(!host)return;const g=++generation;const r=JSON.parse(host.dataset.route);activeRoute=r;
    try {const html=await content(r);if(g!==generation||!host.isConnected)return;host.innerHTML=html;host.setAttribute('aria-busy','false');
      if(r.p.section)document.getElementById(r.p.section)?.scrollIntoView();else if(history.state?.scrollY!=null)window.scrollTo(0,history.state.scrollY);
    } catch(err) {if(g===generation&&host.isConnected)host.innerHTML=`<div class="m-error" role="alert"><h2>読み込みを完了できませんでした。</h2><p>${escape(err.message)}</p><button class="m-btn" type="button" data-mretry>再読み込み</button></div>`;}
  }
  function saveScroll() {history.replaceState({...history.state,scrollY:window.scrollY},'');}
  function render() {const r=route();document.querySelector('main').innerHTML=shell(r);document.title=({case:'案件の結果と変遷',record:'原票の結果と出典',records:'全件検索',timeline:'モビリティの年表',scope:'収録範囲とID照合'}[r.view]||'自治体のモビリティ｜結果と変遷')+'｜MDL';window.scrollTo(0,history.state?.scrollY||0);mount();}
  function navigate(h,keep=false) {
    if(!standalone){location.hash=h;return;}const y=window.scrollY;saveScroll();history.pushState(keep?{scrollY:y}:{},'',h);render();
  }
  document.addEventListener('click',ev=>{
    if(ev.target.closest('[data-mretry]')){cache.clear();standalone?render():mount();return;}
    if(!standalone)return;if(ev.target.closest('a.skip')){ev.preventDefault();document.querySelector('main').focus();return;}const a=ev.target.closest('a[data-mnav][href^="#"]');if(!a||ev.metaKey||ev.ctrlKey||ev.shiftKey||ev.altKey)return;ev.preventDefault();navigate(a.getAttribute('href'));
  });
  document.addEventListener('change',ev=>{const f=ev.target.closest('[data-mfilter]');if(f&&ev.target.matches('select')){if(ev.target.name==='pref')f.querySelectorAll('[name="municipality"]').forEach(el=>{el.value='';});f.requestSubmit();}});
  document.addEventListener('submit',ev=>{
    const f=ev.target;if(!f.matches('[data-mfilter],[data-mmunicipal],[data-mtimeline]'))return;ev.preventDefault();
    const p=Object.fromEntries([...new FormData(f)].filter(([,v])=>v!==''));let view=f.dataset.view,id=f.dataset.id||'';
    if(f.matches('[data-mmunicipal]')){view='prefecture';id=f.dataset.pref;p.all='1';}
    if(f.matches('[data-mtimeline]'))view='timeline';
    const h=standalone?hash(view,id,p):hash(view==='projects'?'results':view,id,p);navigate(h,true);
  });
  window.MOBILITY_RESULTS={shell,mount,mountTeasers,numberMarkup,resultFigures,releaseUrl,validateData,filter,hash,content,cache};
  (document.querySelectorAll?.('[data-deep-count]')||[]).forEach(el=>{el.textContent=countText('deep')+'案件';});
  (document.querySelectorAll?.('[data-results-asof]')||[]).forEach(el=>{el.textContent='調査基準日 '+asOf()+' ／ 選択的な詳査';});
  if(standalone){if('scrollRestoration' in history)history.scrollRestoration='manual';window.addEventListener('hashchange',render);window.addEventListener('popstate',render);let timer;window.addEventListener('scroll',()=>{clearTimeout(timer);timer=setTimeout(saveScroll,140);},{passive:true});render();}
})();
