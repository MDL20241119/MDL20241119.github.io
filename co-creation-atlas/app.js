(()=>{'use strict';
const DATA=window.ATLAS_DATA||[];
const root=document.querySelector('[data-explorer]');
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const norm=s=>String(s||'').normalize('NFKC').toLowerCase();
const STAGES=['','課題を捉える','未来を問う','仲間をつくる','デジタルで試す','現物をつくる','現場で確かめる','事業にする','社会へ広げる'];
const THEMES={city:'まち・暮らしをよくする',people:'仲間・チームをつくる',prototype:'試作・実証の場をつくる',business:'事業化につなげる',digital:'データ・仮想空間で試す',future:'アートから未来を考える'};
if(root){
 const search=document.querySelector('#case-search'),region=document.querySelector('#region'),type=document.querySelector('#type'),theme=document.querySelector('#theme'),intent=document.querySelector('#intent');
 const LENSES={co:'共創拠点・リビングラボ',place:'まちづくり・地域運営'};
 const stageButtons=[...document.querySelectorAll('[data-stage-filter]')],cards=[...document.querySelectorAll('.case-card')];
 const query=new URLSearchParams(location.search);
 let lens=Object.hasOwn(LENSES,query.get('lens'))?query.get('lens'):'';
 intent.value=query.get('intent')||'';
 let stage=/^[1-8]$/.test(query.get('stage')||'')?query.get('stage'):'',view=query.get('view')==='map'?'map':'list',limit=9,filtered=DATA,country=query.get('country')||'';
 if(!DATA.some(d=>d.country===country))country='';
 search.value=query.get('q')||'';region.value=query.get('region')||'';type.value=query.get('type')||'';theme.value=query.get('theme')||'';
 if(stage||type.value)document.querySelector('.advanced-filters').open=true;
 const fulltext=new Map(DATA.map(d=>[d.id,norm([d.name,d.nameJa,d.country,d.city,d.tagline,d.lead,d.operator,d.operatingModel,d.payer,d.transfer,d.valueChainSearch,JSON.stringify(d.entry),...(d.themes||[]).map(t=>THEMES[t]),...(d.tags||[]),...(d.stages||[]).map(s=>STAGES[s])].join(' '))]));
 const cardOrder=new Map(cards.map((c,i)=>[c.dataset.id,i]));
 const mapApi=window.createAtlasMap({data:DATA,stages:STAGES,onFilter:(r,c)=>{region.value=r;country=c;apply();},onClear:reset});
 function updateURL(){const p=new URLSearchParams();if(lens)p.set('lens',lens);if(intent.value)p.set('intent',intent.value);if(search.value.trim())p.set('q',search.value.trim());if(theme.value)p.set('theme',theme.value);if(region.value)p.set('region',region.value);if(type.value)p.set('type',type.value);if(stage)p.set('stage',stage);if(country)p.set('country',country);if(view==='map')p.set('view','map');history.replaceState(null,'',`${location.pathname}${p.size?'?'+p:''}${location.hash}`);}
 function setView(next){
  view=next==='map'?'map':'list';document.querySelector('#map-view').hidden=view!=='map';document.querySelector('#list-view').hidden=view!=='list';
  for(const b of document.querySelectorAll('[role="tab"][data-view]')){const active=b.dataset.view===view;b.setAttribute('aria-selected',String(active));b.tabIndex=active?0:-1;}
  updateURL();mapApi.setVisible(view==='map');
 }
 function activeFilters(){
  const terms=[];
  if(lens)terms.push(['lens',LENSES[lens]]);
  if(intent.value)terms.push(['intent',intent.selectedOptions[0].textContent]);
  if(search.value.trim())terms.push(['q','キーワード：'+search.value.trim()]);
  if(theme.value)terms.push(['theme',THEMES[theme.value]]);
  if(region.value)terms.push(['region',region.selectedOptions[0].textContent]);
  if(type.value)terms.push(['type',type.selectedOptions[0].textContent]);
  if(stage)terms.push(['stage',STAGES[Number(stage)]]);if(country)terms.push(['country',country]);
  const bar=document.querySelector('#active-filters');bar.hidden=!terms.length;
  bar.innerHTML='<span>検索条件</span>'+terms.map(([k,v])=>`<button type="button" data-remove-filter="${k}" aria-label="${esc(v)}の絞り込みを解除">${esc(v)} ×</button>`).join('');
  bar.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{const k=b.dataset.removeFilter;if(k==='stage')stage='';else if(k==='country')country='';else if(k==='lens')lens='';else({q:search,theme,region,type,intent})[k].value='';if(k==='region')country='';apply();}));
 }
 function render(){
  const terms=norm(search.value).trim().split(/\s+/).filter(Boolean);
  const available=DATA.filter(d=>(!lens||d.entry.lenses.includes(lens))&&(!intent.value||d.entry.intents.includes(intent.value))&&(!theme.value||(d.themes||[]).includes(theme.value))&&(!type.value||d.type===type.value)&&(!stage||(d.stages||[d.stage]).includes(Number(stage)))&&terms.every(t=>fulltext.get(d.id).includes(t)));
  filtered=available.filter(d=>(!region.value||d.region===region.value)&&(!country||d.country===country));
  filtered.sort((a,b)=>cardOrder.get(a.id)-cardOrder.get(b.id));const ids=new Set(filtered.slice(0,limit).map(d=>d.id));cards.forEach(c=>c.hidden=!ids.has(c.dataset.id));
  document.querySelector('#result-count').textContent=filtered.length;document.querySelector('#shown-count').textContent=`${Math.min(limit,filtered.length)} / ${filtered.length}件を表示`;
  document.querySelector('#empty-result').hidden=filtered.length>0;
  const more=document.querySelector('#show-more');more.parentElement.hidden=limit>=filtered.length;more.textContent=`さらに${Math.max(0,Math.min(9,filtered.length-limit))}件を見る ↓`;
  stageButtons.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.stageFilter===stage)));
  document.querySelectorAll('[data-lens]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.lens===lens)));
  document.querySelector('#atlas-lens-title').textContent=lens?LENSES[lens]+'の事例':'二つの入口を横断して読む';
  document.querySelector('#atlas-lens-description').textContent=lens==='co'?'参加条件・支援機能・運営体制・実装への接続に注目します。':lens==='place'?'対象地域・当事者・変更内容・維持管理・確認された変化に注目します。':'誰の課題か、誰が決め・払い・続けるかを、領域をまたいで探します。';
  document.querySelector('#atlas-compare-link').href='learn/choose/?lens='+(lens||'cross');
  cards.forEach(card=>{const d=DATA.find(x=>x.id===card.dataset.id);card.querySelector('[data-card-learning]').textContent=d.entry.learning[lens]||d.tagline;card.querySelectorAll('a').forEach(a=>{const u=new URL(a.href);if(!u.pathname.endsWith('/cases/'+d.id+'/'))return;if(lens)u.searchParams.set('lens',lens);else u.searchParams.delete('lens');a.href=u.pathname+u.search+u.hash;});});
  activeFilters();updateURL();mapApi.update(filtered,{available,region:region.value,country});
 }
 function apply(){limit=9;render();}
 function reset(){stage='';search.value='';region.value='';type.value='';theme.value='';intent.value='';country='';lens='';apply();}
 function jumpToResults(){const target=view==='map'?document.querySelector('#map-view'):root;history.replaceState(null,'',location.pathname+location.search+(view==='map'?'#map-view':'#explore'));target.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'auto':'smooth',block:'start'});}
 search.addEventListener('input',apply);theme.addEventListener('change',apply);type.addEventListener('change',apply);
 intent.addEventListener('change',apply);
 document.querySelectorAll('[data-lens]').forEach(b=>b.addEventListener('click',()=>{lens=b.dataset.lens;apply();}));
 document.querySelectorAll('[data-lens-link]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();reset();lens=a.dataset.lensLink;apply();setView('list');jumpToResults();}));
 document.querySelectorAll('[data-intent-link]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();reset();intent.value=a.dataset.intentLink;apply();setView('list');jumpToResults();}));
 region.addEventListener('change',()=>{country='';apply();});
 stageButtons.forEach(b=>b.addEventListener('click',()=>{stage=b.dataset.stageFilter;apply();}));
 document.querySelectorAll('[data-go-stage]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();reset();stage=a.dataset.goStage;document.querySelector('.advanced-filters').open=true;apply();setView('list');jumpToResults();}));
 document.querySelectorAll('[data-theme-link]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();reset();theme.value=a.dataset.themeLink;apply();setView('list');jumpToResults();}));
 document.querySelectorAll('[data-view-link]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();setView(a.dataset.viewLink);jumpToResults();}));
 document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));
 document.querySelectorAll('[role="tab"]').forEach(b=>b.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();setView(view==='map'?'list':'map');document.querySelector(`[role="tab"][data-view="${view}"]`).focus();}}));
 document.querySelector('#clear-filters').addEventListener('click',reset);
 document.querySelector('#show-more').addEventListener('click',()=>{limit+=9;render();});
 render();setView(view);if(view==='map'&&location.hash==='#map-view')requestAnimationFrame(()=>document.querySelector('#map-view').scrollIntoView({block:'start'}));
}
document.querySelectorAll('[data-open-comparison]').forEach(a=>a.addEventListener('click',()=>{const target=document.querySelector('#comparison');if(target?.tagName==='DETAILS')target.open=true;}));
const dialog=document.querySelector('#video-dialog');
if(dialog){document.querySelectorAll('[data-video]').forEach(b=>b.addEventListener('click',()=>{const url=b.dataset.video;if(!/^https:\/\/(www\.youtube-nocookie\.com\/embed\/|www\.youtube\.com\/embed\/|player\.vimeo\.com\/video\/)/.test(url))return;dialog.querySelector('.dialog-title').textContent=b.dataset.title||'公式動画';dialog.querySelector('.dialog-body').innerHTML=`<iframe src="${esc(url)}" title="${esc(b.dataset.title)}" allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; fullscreen" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>`;dialog.showModal();}));dialog.querySelector('[data-close]').addEventListener('click',()=>dialog.close());dialog.addEventListener('close',()=>dialog.querySelector('.dialog-body').replaceChildren());dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close();});}
document.querySelectorAll('.menu a').forEach(a=>a.addEventListener('click',()=>a.closest('details').open=false));
})();
