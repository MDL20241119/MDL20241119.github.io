(() => {
  'use strict';
  const D = window.MOBILITY_DATA;
  const cases = new Map(D.cases.map(c => [c.id, c]));
  const programs = new Map(D.programs.map(p => [p.id, p]));
  const sources = new Map(D.sources.map(s => [s.source_id, s]));
  const detailed = new Set(D.detailed_case_ids);
  const events = [...D.cases.flatMap(c => c.events), ...D.policy_events];
  const e = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const norm = v => String(v ?? '').normalize('NFKC').toLowerCase().replace(/[\s・･\-‐–—_ー]/g, '');
  const plain = v => v == null ? '' : typeof v === 'object' ? (Array.isArray(v) ? v.map(plain).join(' / ') : Object.entries(v).map(([k,x]) => `${k}: ${plain(x)}`).join(' / ')) : String(v);
  const origin = {mlit:'国土交通省',meti:'経済産業省',environment:'環境省',digital:'デジタル・内閣府等',other:'その他府省・横断',claims_verification:'地域独自・横断検証'};
  const precision = {day:'日まで確認',month:'年月',year:'年',fiscal_year:'年度',date_range:'期間',fiscal_year_overlap:'年度をまたぐ記録',reference_month:'資料参照月',fiscal_year_end:'年度末',retrieval_day:'資料確認日',year_approximate:'年の概数',year_document_contains:'資料の記載年',publication_year:'資料公表年',evaluation_fiscal_year:'評価年度',publication_month:'資料公表月',unknown:'事象日未確認'};
  const keyLabel = {FY2024:'2024年度',FY2023:'2023年度',FY2022:'2022年度',cash_revenue:'資金収入（円）',cash_expense:'資金支出（円）',municipal_subsidy:'市補助（円）',municipal_commission:'市受託（円）',other_commission:'その他受託（円）',personnel_expense:'人件費（円）',outsourcing_expense:'業務委託費（円）',rent_expense:'賃借料（円）',accrual_service_expense:'サービス活動費用（円）',accrual_service_balance:'サービス活動増減差額（円）',type:'区分',note:'注記',amount_jpy:'金額（円）',amount:'金額',value:'値',unit:'単位',period:'対象期間',fy:'年度',year:'年',FY2025_jpy:'2025年度事業規模（円）',definition:'定義',source:'根拠',sources:'根拠',source_url:'根拠URL',budget:'予算',actual:'実績',unknown:'未確認',amount_yen:'金額（円）',jpy:'円',status:'状態',source_id:'出典ID',source_ids:'出典ID',locator:'根拠箇所',date:'日付',revenue:'収入',cost:'費用',subsidy:'補助',fare:'運賃',fiscal_year:'年度',scope:'対象範囲',name:'名称',details:'詳細',description:'説明',classification:'区分',basis:'算定根拠',metric:'指標',target:'目標',actual_jpy:'決算・実績（円）',budget_jpy:'予算（円）',subsidy_jpy:'補助（円）',total_jpy:'合計（円）',revenue_jpy:'収入（円）',cost_jpy:'費用（円）',public_cost_jpy:'公費（円）',context:'補足',finance:'費用・財源',financials:'財務記録',financial:'財務',url:'URL',text:'記載',operating_cost:'運営費',limitation:'制約',source_date:'資料日付',verdict:'検証結果'};
  const typeLabel = {unknown:'未確認',budget:'予算',actual:'実績',fare:'運賃',subsidy:'補助',grant:'交付額',operating_cost:'運営費',estimate:'推計'};
  const path = (view, params = {}, id = '') => '#' + view + (id ? '/' + encodeURIComponent(id) : '') + (Object.values(params).some(v => v !== '' && v != null) ? '?' + new URLSearchParams(Object.entries(params).filter(([,v]) => v !== '' && v != null)).toString() : '');
  const currentHash = () => location.hash.slice(1) || 'home';
  function readRoute(hash = currentHash()) {
    const [a,b=''] = hash.split('?');
    const [view='home',id=''] = a.split('/');
    let decoded = id;
    try { decoded=decodeURIComponent(id); } catch {}
    return {view,id:decoded,p:Object.fromEntries(new URLSearchParams(b))};
  }
  let route = readRoute();
  let lastRenderedHash='';
  const from = () => ({from:currentHash()});
  const caseHref = (id, extra={}) => path('case',{...from(),...extra},id);
  const programHref = (id,extra={}) => path('program',{...from(),...extra},id);
  const sourceHref = id => path('source',from(),id);
  const refs = (ids=[]) => `<span class="refs">${[...new Set(ids)].map(id=>{const s=sources.get(id);return s?`<a class="ref" href="${e(sourceHref(id))}" title="${e(s.title)}" aria-label="出典 ${e(s.display_id)} ${e(s.title)}">${e(s.display_id)}</a>`:'';}).join('')}</span>`;
  const tags = values => `<span class="tags">${(values||[]).map(v=>`<span class="tag">${e(v)}</span>`).join('')}</span>`;
  function value(v) {
    if (v == null || v === '' || (Array.isArray(v) && !v.length)) return '<span class="small">確認資料に記載なし</span>';
    if (Array.isArray(v)) return `<ul class="nested">${v.map(x=>`<li>${value(x)}</li>`).join('')}</ul>`;
    if (typeof v === 'object') return `<dl class="object">${Object.entries(v).map(([k,x])=>`<dt>${e(keyLabel[k]||k)}</dt><dd>${k==='type'?e(typeLabel[x]||x):value(x)}</dd>`).join('')}</dl>`;
    if (typeof v === 'number') return e(v.toLocaleString('ja-JP'));
    return e(v).replace(/\n/g,'<br>');
  }
  const fact = (label,v) => `<dl class="facts"><dt>${e(label)}</dt><dd>${value(v)}</dd></dl>`;
  const badge = (s,cls='') => `<span class="badge ${cls}">${e(s)}</span>`;
  function statusClass(s) {return /終了|辞退|休止|中断|停止/.test(s)?'stop':/変更|移行|見直|修正|代替/.test(s)?'change':'';}
  function eventYear(ev) {
    if (ev.date_precision==='unknown') return 'undated';
    return String(ev.event_date||'').match(/(?:19|20)\d{2}/)?.[0]||'undated';
  }
  function groupYear(ev) {const y=eventYear(ev);return y==='undated'?'日付未確定':+y<2016?'2015以前':+y>2026?'2027以降':y;}
  function sortEvents(es) {
    return [...es].sort((a,b)=>(a.date_sort_bounds?.start||'9999').localeCompare(b.date_sort_bounds?.start||'9999') || a.event_id.localeCompare(b.event_id));
  }
  function eventAgencies(ev) {
    const owner=ev.case_id?cases.get(ev.case_id):programs.get(ev.program_id);
    let a=owner?.agencies||[origin[ev.origin_record_id]||'関係府省・地域独自'];
    // A later ministry's creation is never projected onto its predecessors.
    if (eventYear(ev)!=='undated' && +eventYear(ev)<2021) a=a.filter(x=>x!=='デジタル庁');
    return a.length?a:['内閣府・内閣官房等'];
  }
  function findCases(p={}) {
    const q=norm(p.q);
    return D.cases.filter(c =>
      (!q || norm([c.name,c.region,c.actors,c.intervention,c.aliases,c.events.map(x=>x.event),c.status].map(plain).join(' ')).includes(q)) &&
      (!p.year || c.events.some(ev=>eventMatchesYear(ev,p.year))) &&
      (!p.agency || c.agencies.includes(p.agency)) &&
      (!p.pref || c.prefectures.includes(p.pref)) &&
      (!p.theme || c.themes.includes(p.theme)) &&
      (!p.state || c.states.includes(p.state)) &&
      (!p.status || window.MOBILITY_CASE_STATUS.by_case[c.id]?.category===p.status) &&
      (!p.deep || detailed.has(c.id))
    );
  }
  function eventMatchesYear(ev,y) {const yr=eventYear(ev);return y==='pre'?yr!=='undated'&&+yr<2016:y==='future'?yr!=='undated'&&+yr>2026:y==='undated'?yr==='undated':yr===y;}
  function findPrograms(p={}) {
    const q=norm(p.q);
    return D.programs.filter(x => (!q || norm(plain(x)).includes(q)) && (!p.agency || x.agencies.includes(p.agency)) && (!p.theme || x.themes.includes(p.theme)) && (!p.year || D.policy_events.some(ev=>ev.program_id===x.id&&eventMatchesYear(ev,p.year)) || String(plain(x.years)).includes(p.year)));
  }
  function findEvents(p={}) {
    const q=norm(p.q);
    const matchedCaseIds=new Set(findCases({...p,q:'',year:''}).map(c=>c.id));
    return sortEvents(events.filter(ev=>{
      const c=cases.get(ev.case_id),pr=programs.get(ev.program_id);
      if(p.kind==='policy'&&ev.case_id)return false;
      if(p.kind==='case'&&!ev.case_id)return false;
      if(p.year&&!eventMatchesYear(ev,p.year))return false;
      if(p.agency&&!eventAgencies(ev).includes(p.agency))return false;
      if(c && !matchedCaseIds.has(c.id))return false;
      if(!c && (p.pref||p.state||p.deep||p.status))return false;
      if(!c && p.theme && !(pr?.themes||[]).includes(p.theme))return false;
      if(q && !norm([ev.event,ev.event_id,ev.event_date_display,c?.name,c?.aliases,c?.region,pr?.name,pr?.aliases].map(plain).join(' ')).includes(q))return false;
      return true;
    }));
  }
  function optionList(values,current,all='すべて') {return `<option value="">${e(all)}</option>${values.map(x=>{const [v,l]=Array.isArray(x)?x:[x,x];return `<option value="${e(v)}"${String(v)===current?' selected':''}>${e(l)}</option>`;}).join('')}`;}
  const prefectures=[...new Set(D.cases.flatMap(c=>c.prefectures))].sort((a,b)=>a.localeCompare(b,'ja'));
  const years=[['pre','2015年以前（前史）'],...Array.from({length:11},(_,i)=>[String(2016+i),String(2016+i)+(i===10?'年・年度（途中）':'年・年度')]),['future','2027年以降（当時の予定）'],['undated','日付未確定']];
  function filterForm(view,p,mode='cases') {
    const fields=[['year','記載年・年度',years],['agency','関係府省',D.agencies]];
    if(mode!=='programs')fields.push(['pref','都道府県・地域',prefectures]);
    fields.push(['theme','テーマ',D.themes]);
    if(mode!=='programs')fields.push(['state','確認状態の記述',D.states]);
    return `<div class="filter-area"><form id="filters" data-view="${view}"><div class="search-line"><input class="search-input" type="search" name="q" value="${e(p.q||'')}" placeholder="名称、地域、旧名称、キーワードで探す" aria-label="名称、地域、旧名称、キーワード"><button class="button" type="submit">絞り込む <b aria-hidden="true">↗</b></button></div><div class="filters">${fields.map(([key,label,vals])=>`<label>${label}<select name="${key}">${optionList(vals,p[key])}</select></label>`).join('')}</div><div class="filter-tools"><label class="check">${mode==='programs'?'制度名の変更・後継は、制度詳細と年表で確認できます。':`<input type="checkbox" name="deep" value="1"${p.deep?' checked':''}>主要${D.counts.detailed_cases}事例だけを表示`}</label><button class="reset" type="button" data-reset="${view}" data-kind="${e(p.kind||'')}">条件を解除</button></div>${p.kind?`<input type="hidden" name="kind" value="${e(p.kind)}">`:''}${p.status?`<input type="hidden" name="status" value="${e(p.status)}">`:''}</form></div>`;
  }
  function resultHeading(n,unit,description='') {return `<div class="result-heading"><div aria-live="polite"><strong>${n}</strong>${e(unit)}</div><p>${e(description)}</p></div>`;}
  function empty(view) {return `<div class="empty"><p>条件に合う記録は見つかりませんでした。</p><a class="inline-link" href="${path(view)}">条件を解除して全件を見る ↗</a></div>`;}
  function card(c) {
    return `<article class="case-card" data-tone="${statusClass(c.status)}" data-case-id="${e(c.id)}" data-life="${V.statusOf(c).category}">${V.statusBadge(c)}<div class="meta"><span>${e(c.region)}</span>${detailed.has(c.id)?badge('詳査','detailed'):''}</div><h3><a href="${e(caseHref(c.id))}">${e(c.name)}</a></h3><p class="intervention">${e(c.intervention||plain(c.public_value_observation)||plain(c.outcomes)||'実施記録と確認できた範囲を収録。')}</p><div class="status"><span class="badge ${statusClass(c.status)}">原資料の記述</span><p>${e(c.status)}</p><p class="small">根拠時点 ${e(c.status_as_of||'未確認')}</p></div>${tags(c.themes.slice(0,3))}<span class="card-arrow" aria-hidden="true">↗</span></article>`;
  }
  const V = window.MOBILITY_GRAPHICS.create({e,path,findCases,findEvents,eventYear,eventHtml,card,caseHref,sortEvents});
  function yearChart() { return V.milestones()+V.decade({},true); }
  function resultsTeaser() {
    const c=window.MOBILITY_RESULTS_SUMMARY?.counts;if(!c)return '';
    return `<section class="m-root m-policy-teaser"><p class="m-kicker">RESULTS & CHANGE</p><h2>どんな結果が出て、<br>その後どう変わったか。</h2><div class="m-data-strip"><div><b class="m-num">${c.canonical}</b><span>収録事例</span></div><div><b class="m-num">${c.canonical_municipalities}</b><span>収録事例の自治体</span></div><div><b class="m-num">${c.canonical_events}</b><span>事例の出来事</span></div><div><b class="m-num">${c.selection.toLocaleString('ja-JP')}</b><span>採択・支援の資料</span></div></div><p>利用実績、費用、課題と変遷を主役に。事例の結果と、政策・制度の年月を原典からたどれます。</p><div class="m-grid" data-featured-results><p class="m-small">結果の事例を読み込んでいます。</p></div><div class="m-actions"><a class="m-btn m-primary" href="#results">結果を読む ↗</a><a class="m-btn" href="../municipal-mobility-history/">自治体から読む ↗</a><a class="m-btn" href="#records">採択・支援の全件検索 ↗</a></div><p class="m-small" style="margin-top:16px">原票・案件・自治体は異なる単位です。全国調査完了数・総実証件数には合算しません。</p></section>`;
  }
  function programResults(id) {
    if(!window.MOBILITY_RESULTS_SUMMARY)return '';
    const c=window.MOBILITY_RESULTS_SUMMARY.program_counts?.[id];
    return `<section class="m-root m-policy-extension"><p class="m-kicker">ADOPTION → RESULTS</p><h3>採択された内容と、結果。</h3><div class="m-actions"><a class="m-btn" href="../municipal-mobility-history/#catalog?program=${encodeURIComponent(id)}">この制度の公表資料 ↗</a><a class="m-btn" href="../municipal-mobility-history/#catalog?kind=policy_year&amp;program=${encodeURIComponent(id)}">年度・公募を確認 ↗</a></div>${c?`<div class="m-data-strip"><div><b class="m-num">${c.selection||0}</b><span>対応する採択・支援原票</span></div><div><b class="m-num">${c.outcome_result||0}</b><span>実績結果を確認した原票</span></div></div>`:'<p>関連する採択・結果資料は一覧から確認できます。</p>'}<p class="m-small">既存の制度ID対応を使用。採択と実施、成果、現在の継続は別の事実です。</p><div class="m-actions"><a class="m-btn m-primary" href="${path('records',{program:id})}">対応原票を読む ↗</a><a class="m-btn" href="${path('records',{program:id,layer:'review',evidence:'outcome_result'})}">実績結果を読む ↗</a></div></section>`;
  }
  function home() {
    return `<div class="archive-home"><section class="hero poster-hero"><div class="wrap poster-inner"><div class="topline"><p class="eyebrow"><span class="live-square" aria-hidden="true"></span> JAPAN MOBILITY ARCHIVE</p><p class="small">RESEARCH EDITION / 2026.10.31</p></div><div class="hero-grid"><div class="poster-copy"><p class="poster-kicker">2016.10.31 — 2026.10.31</p><h1><span>日本のモビリティ</span><span>実証と政策の</span><span class="title-ten"><em>10</em>年<span class="title-dot">。</span></span></h1><p class="hero-desc"><strong>何が続き、何が変わり、何が止まったか。</strong><br>国の政策と地域の履歴を、同じ時間軸でたどる。</p><div class="buttons"><a class="button lime" href="#timeline?year=2026">時系列で追う <b>↗</b></a><a class="button secondary" href="#map">地図で探す <b>↗</b></a></div></div><div class="hero-graphic poster-art" aria-label="2016年から2026年、実証のその後を追う10年間のアーカイブ"><div class="art-label"><span>THE MOBILITY DECADE</span><span>2016—2026</span></div><div class="art-geometry" aria-hidden="true"><i></i><i></i><i></i></div><div class="ten num">10<span class="art-years">YEARS</span></div><div class="art-bottom"><p class="graphic-caption">実証の、<br>その先へ。</p><span class="art-arrow" aria-hidden="true">↗</span></div><div class="period"><span>2016</span><i aria-hidden="true"></i><span>2026</span></div></div></div><div class="hero-bottomline"><p>開始・採択 <span>／</span> 実証 <span>／</span> 実装 <span>／</span> 継続・変更・終了</p><a href="#home?section=overview">全体像を知る <span aria-hidden="true">↓</span></a></div></div></section><div class="wrap home-content">${resultsTeaser()}<dl class="metric-strip"><div class="metric"><dt>地域の取組 <span>CASES</span></dt><dd><strong>${window.MOBILITY_RESULTS_SUMMARY?.counts?.canonical??D.counts.cases}</strong><small>結果と年月変遷をまとめて読む</small></dd></div><div class="metric"><dt>政策・制度 <span>PROGRAMS</span></dt><dd><strong>${D.counts.programs}</strong><small>府省をまたぐ制度と系譜</small></dd></div><div class="metric"><dt>地域の経過 <span>REGIONAL EVENTS</span></dt><dd><strong>${window.MOBILITY_RESULTS_SUMMARY?.counts?.canonical_events??D.counts.case_events}</strong><small>各取組の年月変遷</small></dd></div><div class="metric"><dt>政策の経過 <span>POLICY EVENTS</span></dt><dd><strong>${D.policy_events.length}</strong><small>国の制度と方針の変遷</small></dd></div></dl><p class="coverage-note">主期間 2016.10.31–2026.10.31。前史を含み、2026年度は途中。本特集の収録件数であり、全国の採択総数・成功件数ではありません。</p>
    <nav class="explore-jump" aria-label="図から探す"><a href="#home?section=geography"><b>01</b><span>日本地図</span><span aria-hidden="true">↓</span></a><a href="#home?section=shared-time"><b>02</b><span>10年の変化</span><span aria-hidden="true">↓</span></a><a href="#cases"><b>03</b><span>事例の結果と変遷</span><span aria-hidden="true">↗</span></a></nav>
    ${V.homeMap()}
    <section class="section topic-index"><div class="section-tag"><p class="eyebrow">FIND YOUR THEME</p><span class="num">${window.MOBILITY_RESULTS_SUMMARY?.classification?.categories?.length||D.themes.filter(t=>t!=='その他').length} THEMES</span></div><div class="section-heading"><h2>取り組みから、<br>探す。</h2><p>テーマを選ぶと、地域の取組・地図・年表を同じ条件で見られます。</p></div><nav class="topic-grid" aria-label="テーマから事例を探す">${(window.MOBILITY_RESULTS_SUMMARY?.classification?.categories||D.themes.filter(t=>t!=='その他').map(t=>({label:t,legacy:t}))).map((t,i)=>`<a class="topic" href="${e(t.code?'../municipal-mobility-history/#projects?topics='+encodeURIComponent(t.code):path('cases',{theme:t.legacy}))}" data-topic="${e(t.code||t.label)}"><span class="topic-index-label">${String(i+1).padStart(2,'0')} / THEME</span><strong>${e(t.label)}</strong><span class="topic-bottom"><span>取組を見る</span><i aria-hidden="true">↗</i></span></a>`).join('')}</nav></section>
    <section class="section" id="overview"><div class="section-tag"><p class="eyebrow">READ THE CHANGE</p><span class="num">2016 — 2026</span></div><div class="section-heading"><h2>「その後」を知ると、<br>見え方が変わる。</h2><p>車両、サービス、運営、制度。<br>何が続いたのかを分けて読む。</p></div><div class="story-grid"><article class="story"><span class="story-index">01</span><h3>車両を変えて、<br>移動を残す。</h3><p>境町では自動運転車両がメンテナンスで休止する間、普通車で代替運行。技術の休止と移動サービスの終了は同じではない。</p><div class="story-case"><a class="inline-link" href="${e(caseHref('V-C02'))}">境町の履歴を読む ↗</a>${refs(cases.get('V-C02').source_ids)}</div></article><article class="story"><span class="story-index">02</span><h3>名称が変わっても、<br>履歴はつながる。</h3><p>前橋市のMaeMaaSを継承・高度化し、2023年にGunMaaSへ。地域と年度をまたぐ経過を、一つの取り組みとして追う。</p><div class="story-case"><a class="inline-link" href="${e(caseHref('mlit_gunma'))}">群馬・前橋の履歴を読む ↗</a>${refs(['SRC-2f41ffbca3',...cases.get('mlit_gunma').source_ids.filter(s=>sources.get(s).url.includes('616080'))])}</div></article><article class="story"><span class="story-index">03</span><h3>技術から、<br>運営の設計へ。</h3><p><span class="story-interpretation">制度目的を比べた本調査の解釈</span>政策の対象は車両技術から、サービスの統合、共同化、データ、担い手へ広がる。新制度の開始だけで成果を判断しない。</p><div class="story-case"><a class="inline-link" href="${e(programHref('commmmons'))}">COMmmmONSと政策の系譜 ↗</a>${refs(D.claims.find(x=>x.id==='mlit_claim_1')?.source_ids||[])}</div></article></div></section>
    <section class="section"><div class="route-panel"><div><p class="eyebrow">THREE WAYS TO EXPLORE</p><h2 style="margin-top:20px">政策から。<br>時間から。<br>地域から。</h2><p>一つの取り組みを年度ごとに分断せず、開始から最後に確認できた状態までをつなぐ。</p></div><div class="route-list"><a href="#programs"><span>国の政策・制度を知る</span><strong>${D.counts.programs} ↗</strong></a><a href="../municipal-mobility-history/#timeline"><span>地域の経過を追う</span><strong>${window.MOBILITY_RESULTS_SUMMARY?.counts?.canonical_events??D.counts.case_events} ↗</strong></a><a href="#cases"><span>地域・事例から探す</span><strong>${window.MOBILITY_RESULTS_SUMMARY?.counts?.canonical??D.counts.cases} ↗</strong></a></div></div></section>
    <section class="section" id="shared-time"><div class="section-tag"><p class="eyebrow">02 / A SHARED TIMELINE</p><span class="num">11 CALENDAR YEARS</span></div><div class="section-heading"><h2>同じ年に、<br>国と地域で何が起きたか。</h2><p>上のキーワードから政策の記録へ。<br>下のグラフで、気になる年を選べます。</p></div>${yearChart()}<div class="buttons"><a class="button secondary" href="#timeline?kind=policy">政策の経過 ${D.policy_events.length} 記録 <b>↗</b></a><a class="button secondary" href="../municipal-mobility-history/#timeline">地域の経過 ${window.MOBILITY_RESULTS_SUMMARY?.counts?.canonical_events??D.counts.case_events} 記録 <b>↗</b></a></div></section>
    <section class="section"><div class="section-tag"><p class="eyebrow">03 / FOLLOW THE TRAJECTORY</p><span class="num">CASE STORIES</span></div><div class="section-heading"><h2>変化の分岐点を読む。</h2><p>継続も、方式変更も、終了も。<br>成果と不足を、根拠とともに。</p></div><div class="spotlight">${['meti_eiheiji','meti_kosai','mlit_miyama'].map(id=>card(cases.get(id))).join('')}</div><div class="buttons"><a class="button" href="#cases">取組と結果を探す <b>↗</b></a></div></section></div></div>`;
  }
  function casesPage(p) {
    const found=findCases(p);
    return `<div class="wrap"><section class="page-head"><p class="eyebrow">REGIONAL STORIES / ALL CASES</p><div class="count"><h1>地域・事例</h1><span class="head-num num">${D.counts.cases}</span></div><p>一つの取り組みを、一つの履歴で。最後に確認できた状態を示し、情報が不足する事例も収録しています。</p></section>${filterForm('cases',p)}${resultHeading(found.length,'件','状態欄は根拠時点の記述。調査日までの運行継続を意味しません。')}<div class="case-grid">${found.length?found.map(card).join(''):empty('cases')}</div></div>`;
  }
  function publicationMeta(ev) {
    return `<dl><dt>資料公表日</dt><dd>${e(ev.source_publication_date||'未確認')}</dd><dt>資料日付の原記載</dt><dd>${e(ev.source_date_raw||'記載なし')}</dd><dt>確認日</dt><dd>${e(ev.accessed_at||'未確認')}</dd><dt>日付精度</dt><dd>${e(precision[ev.date_precision]||ev.date_precision)}</dd><dt>イベントID</dt><dd class="event-id">${e(ev.event_id)}</dd><dt>元案件・記録ID</dt><dd class="event-id">${e(plain(ev.origin_record_ids||ev.origin_record_id))}</dd>${ev.notes?`<dt>注記</dt><dd>${e(ev.notes)}</dd>`:''}${ev.relative_order_note?`<dt>前後関係</dt><dd>${e(ev.relative_order_note)}</dd>`:''}</dl>`;
  }
  function eventHtml(ev,withOwner=true,selectedYear='') {
    const c=cases.get(ev.case_id),p=programs.get(ev.program_id);
    const owner=c||p;
    const ownerLink=owner?`<a href="${e(c?caseHref(c.id,{event:ev.event_id}):programHref(p.id,{event:ev.event_id}))}">${e(owner.name)}</a>`:'府省横断の政策記録';
    const boundary=+eventYear(ev)<2016?'前史':eventYear(ev)==='2016'&&ev.date_precision==='day'&&ev.event_date<'2016-10-31'?'主期間前の経緯':+eventYear(ev)>2026?'当時の将来予定':'';
    return `<li class="event ${!c?'policy-event':''}" id="event-${e(ev.event_id)}" data-event-id="${e(ev.event_id)}"><div class="event-date"><time>${e(ev.event_date_display||ev.event_date||'日付未確認')}</time>${badge(ev.status_display||ev.status||(!c?'政策の出来事':'記録'),statusClass(ev.status_display||ev.status||''))}${ev.date_precision!=='day'?`<span class="small">${e(precision[ev.date_precision]||ev.date_precision)}</span>`:''}${boundary?`<span class="boundary">${e(boundary)}</span>`:''}</div>${withOwner?`<p class="event-owner"><span class="policy-lane">${c?'地域':'政策'}</span>${ownerLink}<span>${e(c?.region||eventAgencies(ev).join('・'))}</span></p>`:''}<h3>${e(ev.event)}</h3>${refs(ev.source_ids)}<details class="event-info"><summary>資料日付・確認日・原記録</summary>${publicationMeta(ev)}${ev.source_observations?.length?`<p>${e(ev.merge_note||'同一事象の元記録を保持')}（${ev.source_observations.length}記録）</p>${ev.source_observations.map(o=>`<div class="raw-observation"><b>${e(o.event_date_display||o.event_date||'日付未確認')} ／ ${e(precision[o.date_precision]||o.date_precision)}</b><p>${e(o.event)}</p><p>資料公表日 ${e(o.source_publication_date||'未確認')} ／ 原記載 ${e(o.source_date_raw||'記載なし')}</p><p>元ID ${e(o.origin_record_id)} ／ ${e(o.event_id)}</p>${refs(o.source_ids)}</div>`).join('')}`:''}</details></li>`;
  }
  function timelinePage(p) {
    const found=findEvents(p),groups=new Map();
    found.forEach(ev=>{const k=groupYear(ev);if(!groups.has(k))groups.set(k,[]);groups.get(k).push(ev);});
    const tabs=[['','国と地域'],['policy','国の政策'],['case','地域の出来事']];
    return `<div class="wrap"><section class="page-head time-heading"><p class="eyebrow">CHANGES THROUGH TIME</p><h1>10年を、<span class="text-cyan">ひと目で。</span></h1><p>採択、実証、成果、実装、その後の変更。上のグラフで年を選び、下の2つのレーンで出来事を比較。最新確認時点の状況は、各事例の詳細で確認できます。</p><div class="tab-bar">${tabs.map(([k,l])=>`<a class="${(p.kind||'')===k?'selected':''}" href="${e(path('timeline',{...p,kind:k}))}">${l}</a>`).join('')}</div></section>${V.timelineIntro(p)}${filterForm('timeline',p)}<div class="year-rail" aria-label="年を選ぶ">${[['','全期間'],...Array.from({length:11},(_,i)=>[String(2016+i),String(2016+i)]),['pre','前史'],['undated','日付未確定']].map(([v,l])=>`<a class="${(p.year||'')===v?'selected':''}" href="${e(path('timeline',{...p,year:v}))}">${l}</a>`).join('')}</div>${resultHeading(found.length,'件の出来事',p.year==='2026'?'2026年度は調査基準日時点で途中。':'日付は原資料の精度を保持。年度内の順序が不明な記録も含みます。')}<div class="timeline-shell">${found.length?[...groups].map(([y,es])=>V.yearLanes(y,es,p)).join(''):empty('timeline')}</div></div>`;
  }
  function linkBadge(s,detail=false) {
    const ck=s.link_check;
    if(!ck||ck.status===200)return '';
    const code=ck.status||'応答未取得';
    return detail?`<p class="record-note">接続点検 ${e(ck.checked_at)}：原URLは ${e(code)}。資料の消滅や記載内容の誤りを断定するものではありません。元URLと出典IDを保持し、公開前の再確認対象にしています。</p>`:`<p><span class="badge warn">接続再確認 ${e(code)}</span></p>`;
  }
  function sourceCard(s) {
    return `<li class="source-card" data-source-id="${e(s.source_id)}"><div class="source-title"><a class="ref" href="${e(sourceHref(s.source_id))}">${e(s.display_id)}</a><h3>${e(s.title)}</h3></div>${linkBadge(s)}<p>資料日付 ${e(plain(s.dates)||'未確認')} ／ 確認日 ${e(s.accessed_at||'未確認')}</p><p>${e(plain(s.locators))}</p><a class="external" href="${e(s.url)}" target="_blank" rel="noopener noreferrer">原資料を開く <span aria-hidden="true">↗</span></a>${s.access_notes?.length||s.grades?.length||s.date_notes?.length?`<details><summary>資料の補足</summary><p>${e(plain(s.access_notes))}</p><p>${e(plain(s.grades))}</p><p>${e(plain(s.date_notes))}</p></details>`:''}</li>`;
  }
  function programsPage(p) {
    const found=findPrograms(p);
    return `<div class="wrap"><section class="page-head"><p class="eyebrow">POLICY & PROGRAMS</p><div class="count"><h1>国の制度を探す</h1><span class="head-num">${D.counts.programs}</span></div><p>省庁・年度・テーマから、補助事業や実証制度を探せます。</p></section>${filterForm('programs',p,'programs')}${resultHeading(found.length,'項目','')}<div class="program-list">${found.length?found.map(x=>`<article class="program-row" data-program-id="${e(x.id)}"><div class="agency">${e(x.agencies.join('・'))}<p class="id-label">${e(x.id)}</p></div><div><h3><a href="${e(programHref(x.id))}">${e(x.name)}</a></h3><p>${e(plain(x.purpose||x.intervention||x.description||x.trajectory))}</p><p class="small">期間 ${e(plain(x.years)||'未確認')}</p>${tags(x.themes.slice(0,3))}</div>${refs(x.source_ids.slice(0,4))}</article>`).join(''):empty('programs')}</div></div>`;
  }
  function bread(p,defaultView,label) {const ret=p.from?'#'+p.from:path(defaultView);return `<div class="breadcrumb"><a href="#home">特集トップ</a><span>/</span><a href="${e(ret)}">${e(p.from?'前の表示に戻る':label)}</a><button class="reset" type="button" data-share>URLをコピー</button></div>`;}
  function caseDetail(id,p) {
    id=D.id_mapping.cases[id]||id;
    const c=cases.get(id);
    if(!c)return missing('事例','cases');
    const peers=D.id_mapping.related_not_merged.filter(x=>x.ids.includes(c.id));
    const related=peers.flatMap(x=>x.ids.filter(z=>z!==c.id).map(z=>({case:cases.get(D.id_mapping.cases[z]||z),reason:x.reason}))).filter(x=>x.case);
    const pages=D.detail_pages[id];
    const fields=[['何を試したか',c.intervention],['実施・運営主体',c.actors||'この台帳では実施・運営主体の詳細が未収録です。'],['対象期間の原記載',c.years],['実施内容・アウトプット',c.outputs],['利用・社会成果の記載',c.outcomes],['費用・財源の原記載',c.costs||c.finance],['財務の詳細・会計区分',c.financials],['公共価値・利用機会',c.public_value_and_equity||c.public_value_observation],['環境効果の算定範囲',c.co2_boundary],['最新運行等の補足',c.latest_operating_context]];
    const primary=fields.filter(([,v])=>v!=null&&v!==''&&!(Array.isArray(v)&&!v.length));
    return `<div class="wrap detail-head">${bread(p,'cases','事例一覧へ')}<section class="detail-top"><div><p class="eyebrow">${detailed.has(id)?'IN DEPTH / 主要'+D.counts.detailed_cases+'事例':'CASE HISTORY / 追跡台帳'} <span class="id-label">${e(c.id)}</span></p><h1>${e(c.name)}</h1><p class="detail-region">${e(c.region)}</p><div class="pill-line">${c.themes.map(t=>`<a href="${path('cases',{theme:t})}">${e(t)}</a>`).join('')}</div></div><div class="detail-status">${V.statusAssessment(c)}<b>原資料の記述</b>${e(c.status)}<p class="small">状態の根拠時点<br>${e(c.status_as_of||'未確認')}<br>資料確認日 ${D.as_of}</p>${refs(c.source_ids)}</div></section><div class="detail-layout"><article class="detail-article">${window.MOBILITY_RESULTS_SUMMARY?.legacy_updates?.[c.id]?`<section class="detail-section"><h2>結果と根拠を読む。</h2><p>同一事業の結果、原典間の相違、訂正履歴を一つの事例にまとめています。根拠の原記録は保持しています。</p><a class="button" href="../municipal-mobility-history/#case/${encodeURIComponent(c.id)}">事例の結果と原典比較を読む ↗</a></section>`:''}<section class="detail-section"><h2>何に取り組んだか。</h2>${primary.map(([l,v])=>fact(l,v)).join('')}${!c.intervention?fact('実施内容の不足','実施内容の詳しい記載は台帳に未収録です。下記の履歴と出典が読めた範囲です。'):''}</section><section class="detail-section"><h2>開始から、その後まで。</h2>${V.caseTrace(c,p)}<p class="small">${c.events.length}の出来事。同じ期間内の厳密な順序が確認できない記録もあります。</p><ol class="event-list">${sortEvents(c.events).map(ev=>eventHtml(ev,false)).join('')}</ol></section><section class="detail-section"><h2>残る確認。</h2>${value(c.limitations||c.limits||'確認資料だけでは、継続運行・収支・利用者への効果の全てを確定できません。')}${!detailed.has(id)?'<p class="small" style="margin-top:15px">この事例は追跡台帳の収録範囲です。主要25事例と同じ深度の調査ではありません。</p>':''}</section><section class="detail-section"><h2>制度との関係。</h2>${c.program_ids.length?`<p class="small">${e(c.program_attribution||'原資料で関連付けられた制度。個別の採択・補助の確定は根拠資料で確認。')}</p><div class="compact-links" style="margin-top:15px">${c.program_ids.map(z=>`<a href="${e(programHref(z))}">${e(programs.get(z).name)} ↗</a>`).join('')}</div>`:'<p>直接の制度帰属は、この台帳では確定していません。</p>'}${c.program_attribution_text.length?fact('関連・帰属の原記載',c.program_attribution_text):''}${related.length?`<div class="source-bar"><h3>関係する別の取り組み</h3>${related.map(x=>`<p style="margin-top:12px"><a class="inline-link" href="${e(caseHref(x.case.id))}">${e(x.case.name)} ↗</a><br><span class="small">${e(x.reason)}</span></p>`).join('')}</div>`:''}</section><section class="detail-section"><h2>根拠をたどる。</h2><ul class="detail-source-list">${c.source_ids.map(z=>sourceCard(sources.get(z))).join('')}</ul></section><section class="detail-section"><details><summary>旧名称・旧IDと、過去の状態記録</summary>${fact('旧名称・別表記',c.aliases)}${fact('元ID',c.original_ids)}${(c.status_observations||[]).map(o=>`<div class="raw-observation"><b>${e(o.original_id)} ／ ${e(o.status_as_of||'時点未確認')}</b><p>${e(o.status||'状態の記載なし')}</p>${refs(o.source_ids)}</div>`).join('')}<p class="small">元記録の全フィールドは構造化データに保持しています。</p></details></section></article><aside class="side-rail"><div class="rail-box"><h2>この履歴を探す</h2><p>${e(origin[c.origin])}<br>${c.events.length}の出来事<br>${c.source_ids.length}の出典</p><a class="button secondary" href="${path('timeline',{q:c.id})}">年表で見る <b>↗</b></a>${pages?`<a class="button secondary" href="${downloadUrl('pdf')}#page=${pages[0]}" target="_blank" rel="noopener">報告書 ${pages[0]}${pages.length>1?'–'+pages.at(-1):''}ページ <b>↗</b></a>`:''}</div><div class="rail-box"><h2>読み方</h2><p>「選んだ年の出来事」と「最後に確認できた状況」は別です。記録がない期間は、継続を推定しません。</p><a class="inline-link" href="#sources?section=guide">日付・状態・数値の定義 ↗</a></div></aside></div></div>`;
  }
  function programDetail(id,p) {
    id=D.id_mapping.programs[id]||id;
    const x=programs.get(id);if(!x)return missing('制度','programs');
    const es=D.policy_events.filter(ev=>ev.program_id===id);
    const linked=D.cases.filter(c=>c.program_ids.includes(id));
    const mentioned=D.cases.filter(c=>!c.program_ids.includes(id)&&c.program_attribution_text.some(t=>t.includes(id)));
    const fields=[['目的・実施内容',x.purpose||x.intervention||x.description],['関係府省',x.lead||x.agency||x.agencies],['対象期間の原記載',x.years],['変遷・後継等の記載',x.trajectory||x.shared_program],['確認できた根拠・成果',x.evidence||x.outputs],['成果の解釈',x.outcomes],['予算・支援額の原記載',x.budget||x.budgets],['制約・不足',x.limitations]];
    return `<div class="wrap detail-head">${bread(p,'programs','制度一覧へ')}<section class="detail-top"><div><p class="eyebrow">POLICY RECORD <span class="id-label">${e(x.id)}</span></p><h1>${e(x.name)}</h1><p class="detail-region">${e(x.agencies.join('・'))}</p></div><div class="detail-status"><b>確認できた状態・経緯</b>${e(x.status||plain(x.trajectory)||'制度の目的・期間・根拠資料を収録')}<p class="small">根拠時点 ${e(x.status_as_of||'資料ごとに異なるため各出典を参照')}<br>資料確認日 ${D.as_of}</p></div></section><div class="detail-layout"><article class="detail-article"><section class="detail-section"><h2>制度を知る。</h2>${fields.filter(([,v])=>v!=null&&v!=='').map(([l,v])=>fact(l,v)).join('')}${programResults(id)}</section><section class="detail-section"><h2>始まりと、変化。</h2>${es.length?`<ol class="event-list">${sortEvents(es).map(ev=>eventHtml(ev,false)).join('')}</ol>`:'<p>この制度にIDが直接対応する年表イベントは未収録です。対象期間と各出典の記載を確認してください。</p>'}<a class="inline-link" href="${path('timeline',{kind:'policy',q:x.name})}">国の政策年表から探す ↗</a></section><section class="detail-section"><h2>地域の取り組み。</h2><p class="small">正本の制度IDに関連付けられた事例です。採択・補助の確定と関連テーマの記述を同一視しません。</p><div class="compact-links" style="margin-top:17px">${linked.length?linked.map(c=>`<a href="${e(caseHref(c.id))}">${e(c.name)} ↗</a>`).join(''):'この台帳ではID対応の事例なし'}</div>${mentioned.length?`<h3 style="margin-top:25px">関連記述のみ</h3><p class="small">直接の制度帰属を確定していない記述です。</p><div class="compact-links" style="margin-top:12px">${mentioned.map(c=>`<a href="${e(caseHref(c.id))}">${e(c.name)} ↗</a>`).join('')}</div>`:''}</section><section class="detail-section"><h2>公式資料・出典。</h2><ul class="detail-source-list">${x.source_ids.map(z=>sourceCard(sources.get(z))).join('')}</ul></section><section class="detail-section"><details><summary>旧名称・旧IDを確認</summary>${fact('名称・別表記',x.aliases)}${fact('元ID',x.original_ids)}</details></section></article><aside class="side-rail"><div class="rail-box"><h2>制度の記録</h2><p>${es.length}のID対応イベント<br>${linked.length}のID対応事例<br>${x.source_ids.length}の出典</p><a class="button secondary" href="#programs">${D.counts.programs}制度に戻る <b>↗</b></a></div><div class="rail-box"><h2>期間の読み方</h2><p>制度の終了、研究テーマの終了、地域サービスの終了を分けて確認します。</p></div></aside></div></div>`;
  }
  function downloadUrl(kind) {
    return {pdf:'downloads/mobility-history-report.pdf',xlsx:'downloads/mobility-history-ledger.xlsx',json:'data/mobility_history_data.json'}[kind];
  }
  function readingGuide() {
    return `<section class="section" id="guide"><div class="section-tag"><p class="eyebrow">HOW TO READ THIS ARCHIVE</p><span class="num">2016.10.31 — 2026.10.31</span></div><div class="section-heading"><h2>読み方を、<br>そろえる。</h2><p>比較する前に、対象・時点・単位を確認する。</p></div><div class="reading-grid"><div class="reading-item"><h3>採択 ≠ 実装 ≠ 継続</h3><p>選定・実証・運行・継続・成果は別の記録です。技術や車両の停止と住民サービスの終了、研究や補助制度の終了も区別します。「終了情報なし」を継続に変えません。</p></div><div class="reading-item"><h3>３つの日付を分ける。</h3><p>出来事の日、資料の公表日、資料を確認した日は別です。年・年月・年度・期間・日付不明は元の精度を保持。年表は記載年・年度で絞り込み、並べ替え範囲の月日を実日付として表示しません。</p></div><div class="reading-item"><h3>同じ単位で比べる。</h3><p>実人数・延べ乗車・登録・Web閲覧は別です。予算と決算、補助込みの収支と運賃収支、CO₂実績と推計も分けます。収支・利用・安全・環境の全項目が揃う事例ばかりではありません。</p></div><div class="reading-item"><h3>関連と因果を分ける。</h3><p>府省欄は制度台帳の関係府省・資料の整理系列です。直接の採択・補助、事業の系譜、関連テーマは、事例の原記載と出典で確認します。同じ市の別路線・別サービスを一件にまとめません。</p></div><div class="reading-item"><h3>件数は、収録範囲。</h3><p>${D.counts.cases}事例、${D.counts.programs}制度、${D.counts.events}イベントは本調査の整理件数です。全国の全採択・全実証・成功件数ではありません。主期間前の経緯・当時の予定・日付未確定記録も含み、2026年度は途中です。</p></div><div class="reading-item"><h3>不明点を、残す。</h3><p>個別の未確認事項は各詳細に表示。テーマと状態フィルターは記載から探すための分類で、成果の評価ではありません。「最新」は調査基準日時点の正本で確認できた根拠時点を指します。</p></div></div><details class="guide-notes"><summary>名寄せ・情報の不足・更新方法</summary><p>地域イベントの元記録 ${D.source_case_event_records} 件を、同一事象の出典と日付精度を残して ${D.counts.case_events} 件へ整理しています。旧IDの対応と統合前の記録はJSONに保存。過去の状態は消さず、新しいイベントと根拠を追記します。外部APIとの連携・自動更新は行いません。</p><p>政策や制度の開始日・終了日が全項目で確定しているわけではありません。IDが直接対応しない府省別の概況イベントも年表に含みます。後継関係は本文の確認範囲を示し、根拠のない因果線を追加しません。</p><p>本特集は公開情報に基づく調査です。将来の提案や調査上の解釈は、自治体・MDLの正式決定、実証成功、安全性の保証を示すものではありません。写真による実績表現は使用していません。</p>${D.gaps.map(g=>`<p><b>${e(g.gap||g.issue||g.id)}</b><br>${e(g.resolution||g.action||'')}</p>`).join('')}</details></section>`;
  }
  function sourcesPage(p) {
    const q=norm(p.q);
    const found=D.sources.filter(s=>!q||norm([s.display_id,s.source_id,s.title,s.url,s.locators].map(plain).join(' ')).includes(q));
    return `<div class="wrap"><section class="page-head"><p class="eyebrow">SOURCES & METHOD</p><h1>根拠から、<br>確かめる。</h1><p>全 ${D.counts.sources} 出典を収録。資料の公表日・対象年と、出来事の日・確認日を分けて記載しています。</p><div class="buttons"><a class="button secondary" href="#sources?section=guide">読み方を見る <b>↓</b></a><a class="button secondary" href="#sources?section=downloads">原資料を見る <b>↓</b></a></div></section><section class="section" id="downloads"><div class="section-tag"><p class="eyebrow">ORIGINAL RESEARCH FILES</p><span class="num">94 PAGES + DATA</span></div><div class="downloads"><article class="download"><div><h3>REPORT</h3><p>調査報告PDF ／ 94ページ<br>主要25事例・比較・出典</p></div><a class="inline-link" href="${downloadUrl('pdf')}" target="_blank" rel="noopener">報告書を開く ↗</a></article><article class="download"><div><h3>LEDGER</h3><p>Excel年表・事例・制度・出典<br>IDと元の日付表記を照合</p></div><a class="inline-link" href="${downloadUrl('xlsx')}" target="_blank" rel="noopener">Excelを開く ↗</a></article><article class="download"><div><h3>OPEN DATA</h3><p>mobility_history_data.json<br>履歴・旧ID・出典を保持した正本</p></div><a class="inline-link" href="${downloadUrl('json')}" target="_blank" rel="noopener">JSONを開く ↗</a></article></div><p class="small" style="margin-top:17px">調査基準日 ${D.as_of} ／ データ版 ${e(D.evidence_freeze.version)}${window.MOBILITY_STANDALONE?'。このプレビューでは原資料のDriveリンクを開きます。閲覧権限は元資料に従います。':''}</p></section>${readingGuide()}<section class="list-body" id="source-list"><div class="section-heading"><h2>出典一覧。</h2><p>名称・出典番号・URLで探せます。</p></div><div class="filter-area"><form id="source-search"><div class="search-line"><input class="search-input" type="search" name="q" value="${e(p.q||'')}" placeholder="資料名、S001、出典ID、URL" aria-label="出典を検索"><button class="button" type="submit">検索 <b>↗</b></button></div></form></div>${resultHeading(found.length,'出典')}<ul class="detail-source-list">${found.length?found.map(sourceCard).join(''):empty('sources')}</ul></section></div>`;
  }
  function sourceDetail(id,p) {
    const s=sources.get(id);if(!s)return missing('出典','sources');
    const cs=D.cases.filter(c=>c.source_ids.includes(id)),ps=D.programs.filter(p=>p.source_ids.includes(id));
    const es=events.filter(ev=>ev.source_ids.includes(id));
    return `<div class="wrap source-detail">${bread(p,'sources','出典一覧へ')}<section class="page-head"><p class="eyebrow">SOURCE ${e(s.display_id)}</p><h1>${e(s.title)}</h1><p class="id-label">${e(id)}</p>${linkBadge(s,true)}<div class="buttons"><a class="button" href="${e(s.url)}" target="_blank" rel="noopener noreferrer">原資料を開く <b>↗</b></a></div></section>${fact('資料日付の原記載',s.dates)}${fact('資料を確認した日',s.accessed_at)}${fact('根拠箇所',s.locators)}${s.access_notes?.length?fact('資料の補足',s.access_notes):''}${s.date_notes?.length?fact('日付の注記',s.date_notes):''}<div class="source-related"><h2>この資料を使う事例・制度。</h2><div class="compact-links" style="margin-top:22px">${cs.map(c=>`<a href="${e(caseHref(c.id))}">${e(c.name)} ↗</a>`).join('')}${ps.map(p=>`<a href="${e(programHref(p.id))}">${e(p.name)} ↗</a>`).join('')}${!cs.length&&!ps.length?'年表の概況等で使用している出典です。':''}</div></div><div class="detail-section"><h2>根拠が対応する出来事。</h2>${es.length?`<ol class="event-list">${sortEvents(es).map(ev=>eventHtml(ev)).join('')}</ol>`:'<p>直接対応するイベントはありません。事例・制度の本文で使用しています。</p>'}</div></div>`;
  }
  function missing(label,view) {return `<div class="wrap"><section class="page-head"><h1>${e(label)}が見つかりません。</h1><p>URLのIDを確認してください。旧IDは正本の対応表にある範囲で引き継ぎます。</p><a class="inline-link" href="${path(view)}">一覧に戻る ↗</a></section></div>`;}
  function pageHtml(r) {
    switch(r.view) {case 'results':case 'records':return window.MOBILITY_RESULTS.shell(r);case 'home':return home();case 'map':return V.mapPage(r.p)+`<section class="wrap section"><h2>施策の分類から探す。</h2><p>上の地図は政策・制度との関係を表示しています。事例の8分類・地域・年代は、統合アーカイブの地図で一緒に選べます。</p><a class="button secondary" href="../municipal-mobility-history/#prefectures">8分類で事例の地図を開く ↗</a></section>`;case 'cases':return casesPage(r.p);case 'timeline':return timelinePage(r.p);case 'programs':return programsPage(r.p);case 'sources':return sourcesPage(r.p);case 'case':return caseDetail(r.id,r.p);case 'program':return programDetail(r.id,r.p);case 'source':return sourceDetail(r.id,r.p);default:return missing('ページ','home');}
  }
  function saveScroll() {try{history.replaceState({...history.state,scrollY:window.scrollY},'');}catch{}}
  function navigate(hash,keep=false) {
    const y=window.scrollY;
    saveScroll();
    if(hash===location.hash){render(keep?y:0);return;}
    try{history.pushState(keep?{scrollY:y}:{},'',hash);render(keep?y:undefined);}catch{location.hash=hash;}
  }
  function render(forcedScroll) {
    route=readRoute();lastRenderedHash=currentHash();
    if(route.view==='cases'&&typeof location.replace==='function'){const p=new URLSearchParams(Object.entries(route.p).filter(([k])=>['q','pref','year','theme','topics','purpose'].includes(k)));location.replace('../municipal-mobility-history/#projects'+(p.size?'?'+p:''));return;}
    if(route.view==='case'&&typeof location.replace==='function'){const id=D.id_mapping.cases[route.id]||route.id;const q=new URLSearchParams({layer:'legacy',...(route.p.event?{section:'event-'+route.p.event}:{})});location.replace('../municipal-mobility-history/#record/'+encodeURIComponent(id)+'?'+q);return;}
    const main=document.querySelector('main');main.innerHTML=pageHtml(route);window.MOBILITY_RESULTS?.mount();window.MOBILITY_RESULTS?.mountTeasers();
    document.querySelectorAll('[data-count]').forEach(el=>{el.textContent=el.dataset.count==='cases'?(window.MOBILITY_RESULTS_SUMMARY?.counts?.canonical??D.counts.cases):D.counts[el.dataset.count];});
    const navGroup={case:'cases',program:'programs',source:'sources'}[route.view]||route.view;
    document.querySelectorAll('[data-nav]').forEach(el=>{el.classList.toggle('active',el.dataset.nav===navGroup);if(el.dataset.nav===navGroup)el.setAttribute('aria-current','page');else el.removeAttribute('aria-current');});
    const title=route.view==='case'?cases.get(D.id_mapping.cases[route.id]||route.id)?.name:route.view==='program'?programs.get(D.id_mapping.programs[route.id]||route.id)?.name:route.view==='source'?sources.get(route.id)?.title:({home:'日本のモビリティ実証と政策の10年',map:'日本地図でたどるモビリティ',timeline:'国と地域の年表',cases:'111事例の履歴',programs:'66政策・制度',sources:'資料と読み方'}[route.view]);
    document.title=(title||'日本のモビリティ実証と政策の10年')+'｜MDL';
    requestAnimationFrame(()=>{
      if(forcedScroll!==undefined)window.scrollTo(0,forcedScroll);
      else if(history.state?.scrollY!==undefined)window.scrollTo(0,history.state.scrollY);
      else if(route.p.event){const el=document.getElementById('event-'+route.p.event);if(el){let parent=el.parentElement;while(parent&&parent!==main){if(parent.tagName==='DETAILS')parent.open=true;parent=parent.parentElement;}el.scrollIntoView();el.querySelector('details')?.setAttribute('open','');}else window.scrollTo(0,0);}
      else if(route.p.section){document.getElementById(route.p.section)?.scrollIntoView();}
      else window.scrollTo(0,0);
      if(route.view!=='home')main.focus({preventScroll:true});
    });
  }
  // Expose pure selectors and renderers for the local acceptance checks.
  window.MOBILITY_UI={readRoute,findCases,findPrograms,findEvents,eventYear,sortEvents,caseDetail,programDetail,eventHtml,sourceDetail,pageHtml,path,graphics:V};
  if(typeof document==='undefined')return;
  if('scrollRestoration' in history)history.scrollRestoration='manual';
  document.addEventListener('click',async ev=>{
    const share=ev.target.closest('[data-share]');
    if(share){try{await navigator.clipboard.writeText(location.href);const t=document.querySelector('.toast');t.textContent='この表示のURLをコピーしました';t.hidden=false;setTimeout(()=>{t.hidden=true;},2200);}catch{share.textContent='アドレスバーのURLをコピーしてください';}return;}
    const reset=ev.target.closest('[data-reset]');
    if(reset){ev.preventDefault();navigate(path(reset.dataset.reset,reset.dataset.kind?{kind:reset.dataset.kind}:{}));return;}
    const a=ev.target.closest('a[href^="#"]');
    if(a&&!ev.metaKey&&!ev.ctrlKey&&!ev.shiftKey&&!ev.altKey){if(a.classList.contains('skip')){ev.preventDefault();document.querySelector('main').focus();return;}ev.preventDefault();const h=a.getAttribute('href'),next=readRoute(h.slice(1));navigate(h,route.view==='map'&&next.view==='map'&&!next.p.section);}
  });
  document.addEventListener('change',ev=>{
    if(!ev.target.matches('[data-viz-filter]'))return;
    const form=ev.target.closest('form');
    const params=Object.fromEntries([...new FormData(form)].filter(([,v])=>v!==''));
    const y=window.scrollY;
    saveScroll();
    const h=path('map',params);
    try{history.pushState({scrollY:y},'',h);render(y);}catch{navigate(h);}
  });
  document.addEventListener('submit',ev=>{
    if(ev.target.id==='atlas-filters'){ev.preventDefault();return;}
    if(!['filters','source-search'].includes(ev.target.id))return;
    ev.preventDefault();
    const p=Object.fromEntries([...new FormData(ev.target)].filter(([,v])=>v!==''));
    const view=ev.target.id==='source-search'?'sources':ev.target.dataset.view;
    if(view==='sources')p.section='source-list';
    const y=window.scrollY;
    saveScroll();
    const h=path(view,p);
    try{history.pushState({scrollY:y},'',h);render(y);}catch{navigate(h);}
  });
  window.addEventListener('hashchange',()=>{if(currentHash()!==lastRenderedHash)render();});
  window.addEventListener('popstate',()=>render());
  let scrollTimer;
  window.addEventListener('scroll',()=>{clearTimeout(scrollTimer);scrollTimer=setTimeout(saveScroll,160);},{passive:true});
  window.addEventListener('pagehide',saveScroll);
  render();
})();
