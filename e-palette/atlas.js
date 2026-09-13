(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const esc = text => String(text ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const safeURL = url => {try {const u = new URL(url); return u.protocol === 'https:' && !u.username && !u.password ? u.href : '#';} catch {return '#';}};
  if (!window.CASES || !window.ATLAS) { $('cases').innerHTML = '<p class="empty-state">事例を読み込めませんでした。ページを再読み込みしてください。</p>'; return; }
  const { categories, summaries, metrics, eras, insights } = window.ATLAS;
  const cases = window.CASES.map(c => ({...c, ...summaries[c.ID], metric: metrics[c.ID]}));
  const byId = new Map(cases.map(c => [c.ID,c]));
  const sourceLink = (url,label,cls='') => `<a class="${cls}" href="${esc(safeURL(url))}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`;
  const publisher = url => {try {const h=new URL(url).hostname; return ({'toyotatimes.jp':'トヨタイムズ','www.city.toyota.aichi.jp':'豊田市','www.pref.aichi.jp':'愛知県','global.toyota':'トヨタ ニュースルーム','www.docomo.ne.jp':'NTTドコモ','group.ntt':'NTT','www.h-products.co.jp':'博報堂プロダクツ','www.westjr.co.jp':'JR西日本','www.town.kumamoto-yamato.lg.jp':'山都町','prtimes.jp':'発表主体のプレスリリース / PR TIMES','www.pref.kyoto.jp':'京都府','toyota.jp':'トヨタ e-Palette','maymobility.com':'May Mobility','www.woven-city.global':'Woven City','woven-city.global':'Woven City','kitayama.or.jp':'北山街協同組合','www.monet-technologies.com':'MONET','www.toyota-kyushu.com':'トヨタ自動車九州'})[h] || h;} catch{return '公開出典';}};
  const stage = c => ['EP-032','EP-033'].includes(c.ID) ? '予定' : c['段階'].includes('③') ? '実装' : '実証';
  const stageLabel = c => stage(c)==='予定' ? '実施予定' : stage(c)==='実装' ? '実装 / 公開時点' : '実証';
  const yearOf = c => c.ID==='EP-033' ? '2027' : (c['年'].match(/20\d\d/) || ['時期未確認'])[0];
  const regionOf = c => c['地域'].match(/^.{2,3}?[都道府県]/)?.[0] || c['地域'].split('・')[0];
  const state = {q:'',cat:'',year:'',stage:'',region:'',sort:'oldest'};
  let singleId = '';
  const opened = new Set();
  const yearOptions = [...new Set(cases.map(yearOf))].sort();
  $('cat').insertAdjacentHTML('beforeend',categories.map(c=>`<option value="${c.id}">${esc(c.label)}</option>`).join(''));
  $('year').insertAdjacentHTML('beforeend',yearOptions.map(y=>`<option value="${esc(y)}">${esc(y)}${/^20/.test(y)?'年':''}</option>`).join(''));
  $('region').insertAdjacentHTML('beforeend',[...new Set(cases.map(regionOf))].sort((a,b)=>a.localeCompare(b,'ja')).map(r=>`<option>${esc(r)}</option>`).join(''));
  $('timeline-cards').innerHTML = eras.map(e=>`<article class="era" id="era-${e.id}"><div class="era-head"><span class="era-year">${esc(e.year)}</span><span class="state-label ${e.future?'plan':''}">${esc(e.stage)}</span></div><h3>${esc(e.title)}</h3><p>${esc(e.description)}</p><p class="era-example">${esc(e.example)}</p>${e.caseId?`<button class="era-link" data-case="${e.caseId}">代表事例を見る →</button>`:sourceLink(e.source,'公式の導入目標を読む','era-link')}${e.caseId?sourceLink(e.source,'出典','era-source'):''}${e.source2?sourceLink(e.source2,'公道実証の出典','era-source'):''}</article>`).join('');
  $('use-index').innerHTML = categories.map(c=>`<a href="#use-${c.id}"><span>${esc(c.label)}</span><b>${cases.filter(x=>x.tags.includes(c.id)).length}<small>件</small></b></a>`).join('');
  $('usegrid').innerHTML = categories.map((c,i)=> {
    const n=cases.filter(x=>x.tags.includes(c.id)).length, m=c.metric;
    return `<article class="use-card" id="use-${c.id}"><div class="use-top"><span>${String(i+1).padStart(2,'0')} / ${esc(c.en)}</span><span class="case-count"><b>${n}</b> 件</span></div><h3>${esc(c.label)}</h3><p class="use-desc">${esc(c.description)}</p><p class="use-example"><span>代表事例</span>${esc(byId.get(c.example)['案件名'])}</p><div class="use-metric"><span class="metric-type">${esc(m.kind)}</span><div class="metric-number ${m.value===null?'no-value':''}">${esc(m.value??'公開値未確認')}${m.unit?`<small>${esc(m.unit)}</small>`:''}</div><p class="metric-note">${esc(m.note)}</p></div>${sourceLink(m.source,m.publisher,'metric-source')}<div class="use-actions"><button data-category="${c.id}">${n}件の事例を見る →</button><button data-case="${c.example}">代表事例を開く ↗</button></div></article>`;
  }).join('');
  $('insights').innerHTML=insights.map((a,i)=>`<article class="insight"><span>${String(i+1).padStart(2,'0')} / MDLの考察</span><h3>${esc(a.title)}</h3><p>${esc(a.body)}</p><a href="#case-${a.caseId}" data-case="${a.caseId}">関連する事例 →</a></article>`).join('');

  function numberHTML(c){
    const m=c.metric;
    if(!m) return `<span class="field-tag">${stage(c)==='予定'?'実施前':'定量成果'}</span>公開値未確認`;
    return `<span class="field-tag">${esc(m.kind)}</span><div class="card-number">${esc(m.value)}<small>${esc(m.unit)}</small></div><span class="result-explainer">${esc(m.note)}</span>${sourceLink(m.source||c.Source,'数字の出典','result-source')}`;
  }
  function field(name,label,content,extra=''){return `<div class="field-row ${extra}"><dt>${name}<span>${label}</span></dt><dd>${content}</dd></div>`;}
  function card(c){
    const details=[['実施時期・期間',c['期間']],['運行・活用方法',c['サービス内容']],['対象者',c['ターゲット']],['車両・台数（計画・公表仕様を含む）',c['台数']],['料金・利用条件（公開当時）',c['料金']],['自動運転の位置づけ',c['自動運転']],['共創先（公開情報）',c['共創先']],[c.valueKind+'（出典に沿った整理）',c.value],['成果を読むときの留意点',c['弱点/課題']]];
    return `<article class="case-card" id="case-${c.ID}" aria-labelledby="title-${c.ID}"><div class="case-heading"><div class="case-top"><span class="case-ref">${c.ID} / ${esc(yearOf(c))}</span><span class="badge ${stage(c)==='予定'?'planned':stage(c)==='実証'?'trial':''}">${stageLabel(c)}</span></div><h3 id="title-${c.ID}">${esc(c['案件名'])}</h3><p class="case-location">${esc(c['地域'])}</p></div><dl class="six-fields">${field('WHAT','何をした？',esc(c.what))}${field('WHO','誰向け？',esc(c['ターゲット']))}${field('VALUE','何が良くなった？',`<span class="field-tag">${esc(c.valueKind)}</span>${esc(c.value)}`)}${field('RESULT','数字は？',numberHTML(c),'result-row')}${field('WITH','誰と共創？',esc(c.with||c['共創先']))}${field('LEARN','何を学べる？',`<span class="field-tag">MDLの考察</span>${esc(c.learn)}`)}</dl><details class="case-details" data-id="${c.ID}" ${opened.has(c.ID)?'open':''}><summary>期間・運行条件・公開出典を見る</summary><div class="detail-body"><dl>${details.map(([key,val])=>`<div><dt>${esc(key)}</dt><dd>${esc(val||'公開値未確認')}</dd></div>`).join('')}<div><dt>用途・テーマ（複数分類）</dt><dd>${c.tags.map(id=>esc(categories.find(x=>x.id===id).label)).join(' / ')}</dd></div></dl><ul class="source-list">${[c.Source,c.Source2].filter(Boolean).map((u,i)=>`<li>${sourceLink(u,`${i+1}. ${publisher(u)}`)}</li>`).join('')}</ul><p class="editorial-note">実証の目的・期待と、測定済みの成果は異なります。VALUEには情報の性質を表示し、LEARNは公開情報に基づくMDLの考察として掲載しています。</p></div></details></article>`;
  }
  function render(){
    const q=state.q.normalize('NFKC').toLocaleLowerCase('ja').trim();
    const filtered=cases.filter(c=>(!singleId||c.ID===singleId)&&(!state.cat||c.tags.includes(state.cat))&&(!state.year||yearOf(c)===state.year)&&(!state.stage||stage(c)===state.stage)&&(!state.region||regionOf(c)===state.region)&&(!q||Object.values(c).filter(v=>typeof v==='string').join(' ').concat(' ',c.tags.map(id=>categories.find(x=>x.id===id).label).join(' ')).normalize('NFKC').toLocaleLowerCase('ja').includes(q))).sort((a,b)=>{let ya=Number(yearOf(a))||9999,yb=Number(yearOf(b))||9999;if(ya===9999||yb===9999)return ya-yb;return(state.sort==='newest'?-1:1)*(ya-yb||a.ID.localeCompare(b.ID));});
    $('count').textContent=filtered.length;
    $('filter-description').textContent = [singleId?'代表事例':null,categories.find(c=>c.id===state.cat)?.label,state.year?`${state.year}${/^20/.test(state.year)?'年':''}`:null,state.stage==='予定'?'実施予定':state.stage,state.region,state.q?`「${state.q}」`:null].filter(Boolean).join(' / ');
    $('cases').innerHTML=filtered.length?filtered.map(card).join(''):'<div class="empty-state"><h3>該当する事例はありません。</h3><p>キーワードを変えるか、絞り込みを解除してください。</p><button data-reset>すべての事例を見る</button></div>';
  }
  function reset(){singleId='';for(const k of ['q','cat','year','stage','region']){state[k]='';$(k).value='';}render();}
  function focusCases(){ $('db-title').focus({preventScroll:true}); $('db').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'}); }
  function showCase(id){if(!byId.has(id))return;reset();singleId=id;opened.add(id);render();history.replaceState(null,'',`#case-${id}`);focusCases();}
  function applyCategory(id){if(!categories.some(c=>c.id===id))return;reset();state.cat=id;$('cat').value=id;render();history.replaceState(null,'','#db');focusCases();}
  for(const k of ['q','cat','year','stage','region','sort'])$(k).addEventListener(k==='q'?'input':'change',e=>{singleId='';state[k]=e.target.value;render();});
  $('filters').addEventListener('submit',e=>e.preventDefault());
  $('reset').addEventListener('click',()=>{reset();history.replaceState(null,'','#db');});
  document.addEventListener('click',e=>{const trigger=e.target.closest('[data-case],[data-category],[data-reset]');if(!trigger)return;e.preventDefault();if(trigger.dataset.case)showCase(trigger.dataset.case);else if(trigger.dataset.category)applyCategory(trigger.dataset.category);else reset();});
  $('cases').addEventListener('toggle',e=>{const d=e.target;if(d.matches('details[data-id]')){if(d.open)opened.add(d.dataset.id);else opened.delete(d.dataset.id);}},true);
  function followHash(){const match=location.hash.match(/^#(?:case-)?(EP-\d{3})$/);if(match&&byId.has(match[1]))showCase(match[1]);}
  render();followHash();window.addEventListener('hashchange',followHash);
})();
