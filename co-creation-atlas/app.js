(()=>{'use strict';
const DATA=window.ATLAS_DATA||[];
const root=document.querySelector('[data-explorer]');
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const norm=s=>String(s||'').normalize('NFKC').toLowerCase();
const STAGES=['','課題を捉える','未来を問う','仲間をつくる','デジタルで試す','現物をつくる','現場で確かめる','事業にする','社会へ広げる'];
const THEMES={city:'まち・暮らしをよくする',people:'仲間・チームをつくる',prototype:'試作・実証の場をつくる',business:'事業化につなげる',digital:'データ・仮想空間で試す',future:'アートから未来を考える'};
if(root){
 const search=document.querySelector('#case-search'),region=document.querySelector('#region'),type=document.querySelector('#type'),theme=document.querySelector('#theme');
 const stageButtons=[...document.querySelectorAll('[data-stage-filter]')],cards=[...document.querySelectorAll('.case-card')];
 const query=new URLSearchParams(location.search);
 let stage=/^[1-8]$/.test(query.get('stage')||'')?query.get('stage'):'',view=query.get('view')==='map'?'map':'list',limit=9,filtered=DATA,selected=null;
 search.value=query.get('q')||'';region.value=query.get('region')||'';type.value=query.get('type')||'';theme.value=query.get('theme')||'';
 if(stage||type.value)document.querySelector('.advanced-filters').open=true;
 const fulltext=new Map(DATA.map(d=>[d.id,norm([d.name,d.nameJa,d.country,d.city,d.tagline,d.lead,d.operator,d.operatingModel,d.payer,d.transfer,...(d.themes||[]).map(t=>THEMES[t]),...(d.tags||[]),...(d.stages||[]).map(s=>STAGES[s])].join(' '))]));
 const cardOrder=new Map(cards.map((c,i)=>[c.dataset.id,i]));
 const map=document.querySelector('#world-map'),layer=document.querySelector('#map-markers'),panel=document.querySelector('#map-panel');
 const presets={world:[80,20,1030,515],europe:[565,46,175,87.5],'north-america':[135,98,325,162.5],asia:[900,100,220,110]};
 let box=[...presets.world];
 function setBox(v){box=v;map.setAttribute('viewBox',v.join(' '));document.querySelectorAll('[data-map-region]').forEach(b=>b.classList.toggle('active',presets[b.dataset.mapRegion].every((n,i)=>Math.abs(n-v[i])<.001)));drawMarkers();}
 function zoom(f){const w=Math.max(3,Math.min(1200,box[2]*f));setBox([box[0]+(box[2]-w)/2,box[1]+(box[3]-w/2)/2,w,w/2]);}
 function xy(d){return[(d.lng+180)*1200/360,(90-d.lat)*600/180];}
 function drawMarkers(){
  if(view!=='map'||!map.clientWidth)return;
  const unit=box[2]/map.clientWidth,groups=[];
  for(const d of filtered){const[x,y]=xy(d);const g=groups.find(g=>Math.hypot(x-g.x,y-g.y)<30*unit);if(g){g.items.push(d);g.x=g.items.reduce((n,z)=>n+xy(z)[0],0)/g.items.length;g.y=g.items.reduce((n,z)=>n+xy(z)[1],0)/g.items.length;}else groups.push({x,y,items:[d]});}
  layer.innerHTML=groups.map((g,i)=>{const many=g.items.length>1,label=many?`${g.items.length}件：${g.items.map(d=>d.name).join('、')}`:g.items[0].name;return `<g class="map-marker ${g.items.some(d=>d.id===selected)?'selected':''}" tabindex="0" role="button" aria-label="${esc(label)}" data-group="${i}" transform="translate(${g.x} ${g.y})"><circle r="${(many?18:14)*unit}"/><text font-size="${(many?15:11)*unit}">${many?g.items.length:g.items[0].number}</text></g>`}).join('');
  for(const el of layer.children){const g=groups[Number(el.dataset.group)];const act=()=>{if(g.items.length===1){select(g.items[0]);return;}const pts=g.items.map(xy),xs=pts.map(p=>p[0]),ys=pts.map(p=>p[1]),w=Math.max(8,(Math.max(...xs)-Math.min(...xs))*2.3,(Math.max(...ys)-Math.min(...ys))*4.6);setBox([(Math.min(...xs)+Math.max(...xs))/2-w/2,(Math.min(...ys)+Math.max(...ys))/2-w/4,w,w/2]);select(g.items[0]);};el.addEventListener('click',act);el.addEventListener('keydown',e=>{if(['Enter',' '].includes(e.key)){e.preventDefault();act();}});}
 }
 function select(d){
  selected=d.id;
  panel.innerHTML=`<div class="panel-main"><span class="label">CASE ${esc(d.number)} · ${esc(d.country)}</span><p class="eyebrow" style="margin:16px 0 10px">${esc(d.city)}</p><h3>${esc(d.name)}</h3></div>${d.image?`<img class="panel-photo ${d.imageNoCrop?'no-crop':''}" src="${esc(d.image)}" alt="${esc(d.imageAlt||d.name)}" loading="lazy"><div class="panel-credit">PHOTO: ${esc(d.imageCredit)} · <a href="${esc(d.imageSource)}" target="_blank" rel="noopener noreferrer">掲載元</a> · <a href="${esc(d.imageRights)}" target="_blank" rel="noopener noreferrer">${esc(d.imageLicense)}</a></div>`:''}<p><strong>学べること</strong><br>${esc(d.tagline)}</p><p class="meta">${esc(d.locationNote||'代表所在地です。正確な訪問先は公式案内で確認。')}</p><a class="btn" href="cases/${esc(d.id)}/">この事例を読む <span aria-hidden="true">→</span></a><a href="${esc(d.sources[0].url)}" target="_blank" rel="noopener noreferrer" class="map-original">公式サイトを見る ↗</a>`;
  drawMarkers();
 }
 function emptyPanel(){selected=null;panel.innerHTML=`<div class="panel-main"><span class="label">WORLD EXPLORER</span><div class="display" style="margin:20px 0">LOCAL<br>IDEAS.<br>GLOBAL<br>LESSONS.</div></div><p>${filtered.length?'地図の番号を選ぶと、この場所で何を学べるかがわかります。':'条件に合う事例がありません。絞り込みを解除して探し直せます。'}</p><p class="meta">大学・施設・都市地区・広域ネットワークを掲載。ネットワークは代表所在地です。</p>`;}
 function updateURL(){const p=new URLSearchParams();if(search.value.trim())p.set('q',search.value.trim());if(theme.value)p.set('theme',theme.value);if(region.value)p.set('region',region.value);if(type.value)p.set('type',type.value);if(stage)p.set('stage',stage);if(view==='map')p.set('view','map');history.replaceState(null,'',`${location.pathname}${p.size?'?'+p:''}${location.hash}`);}
 function setView(next){
  view=next==='map'?'map':'list';document.querySelector('#map-view').hidden=view!=='map';document.querySelector('#list-view').hidden=view!=='list';
  for(const b of document.querySelectorAll('[role="tab"][data-view]')){const active=b.dataset.view===view;b.setAttribute('aria-selected',String(active));b.tabIndex=active?0:-1;}
  updateURL();if(view==='map')requestAnimationFrame(drawMarkers);
 }
 function activeFilters(){
  const terms=[];
  if(search.value.trim())terms.push(['q','キーワード：'+search.value.trim()]);
  if(theme.value)terms.push(['theme',THEMES[theme.value]]);
  if(region.value)terms.push(['region',region.selectedOptions[0].textContent]);
  if(type.value)terms.push(['type',type.selectedOptions[0].textContent]);
  if(stage)terms.push(['stage',STAGES[Number(stage)]]);
  const bar=document.querySelector('#active-filters');bar.hidden=!terms.length;
  bar.innerHTML='<span>検索条件</span>'+terms.map(([k,v])=>`<button type="button" data-remove-filter="${k}" aria-label="${esc(v)}の絞り込みを解除">${esc(v)} ×</button>`).join('');
  bar.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{const k=b.dataset.removeFilter;if(k==='stage')stage='';else({q:search,theme,region,type})[k].value='';apply();if(k==='region')setBox(presets.world);}));
 }
 function render(){
  const terms=norm(search.value).trim().split(/\s+/).filter(Boolean);
  filtered=DATA.filter(d=>(!theme.value||(d.themes||[]).includes(theme.value))&&(!region.value||d.region===region.value)&&(!type.value||d.type===type.value)&&(!stage||(d.stages||[d.stage]).includes(Number(stage)))&&terms.every(t=>fulltext.get(d.id).includes(t)));
  filtered.sort((a,b)=>cardOrder.get(a.id)-cardOrder.get(b.id));const ids=new Set(filtered.slice(0,limit).map(d=>d.id));cards.forEach(c=>c.hidden=!ids.has(c.dataset.id));
  document.querySelector('#result-count').textContent=filtered.length;document.querySelector('#shown-count').textContent=`${Math.min(limit,filtered.length)} / ${filtered.length}件を表示`;
  document.querySelector('#empty-result').hidden=filtered.length>0;
  const more=document.querySelector('#show-more');more.parentElement.hidden=limit>=filtered.length;more.textContent=`さらに${Math.max(0,Math.min(9,filtered.length-limit))}件を見る ↓`;
  stageButtons.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.stageFilter===stage)));
  activeFilters();updateURL();if(!selected||!filtered.some(d=>d.id===selected))emptyPanel();drawMarkers();
 }
 function apply(){limit=9;render();}
 function reset(){stage='';search.value='';region.value='';type.value='';theme.value='';selected=null;apply();setBox(presets.world);}
 function jumpToResults(){history.replaceState(null,'',location.pathname+location.search+'#explore');root.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'auto':'smooth',block:'start'});}
 search.addEventListener('input',apply);theme.addEventListener('change',apply);type.addEventListener('change',apply);
 region.addEventListener('change',()=>{apply();setBox(presets[region.value]||presets.world);});
 stageButtons.forEach(b=>b.addEventListener('click',()=>{stage=b.dataset.stageFilter;apply();}));
 document.querySelectorAll('[data-go-stage]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();reset();stage=a.dataset.goStage;document.querySelector('.advanced-filters').open=true;apply();setView('list');jumpToResults();}));
 document.querySelectorAll('[data-theme-link]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();reset();theme.value=a.dataset.themeLink;apply();setView('list');jumpToResults();}));
 document.querySelectorAll('[data-view-link]').forEach(a=>a.addEventListener('click',e=>{e.preventDefault();setView(a.dataset.viewLink);jumpToResults();}));
 document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));
 document.querySelectorAll('[role="tab"]').forEach(b=>b.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight'].includes(e.key)){e.preventDefault();setView(view==='map'?'list':'map');document.querySelector(`[role="tab"][data-view="${view}"]`).focus();}}));
 document.querySelector('#clear-filters').addEventListener('click',reset);
 document.querySelector('#show-more').addEventListener('click',()=>{limit+=9;render();});
 document.querySelectorAll('[data-map-region]').forEach(b=>b.addEventListener('click',()=>setBox(presets[b.dataset.mapRegion])));
 document.querySelector('#zoom-in').addEventListener('click',()=>zoom(.55));document.querySelector('#zoom-out').addEventListener('click',()=>zoom(1.8));document.querySelector('#map-reset').addEventListener('click',()=>setBox(presets.world));
 let drag=null;
 map.addEventListener('pointerdown',e=>{if(e.target.closest('.map-marker')||e.pointerType==='touch')return;drag={x:e.clientX,y:e.clientY,box:[...box]};map.setPointerCapture(e.pointerId);map.classList.add('dragging');});
 map.addEventListener('pointermove',e=>{if(!drag)return;const ratio=drag.box[2]/map.clientWidth;setBox([drag.box[0]-(e.clientX-drag.x)*ratio,drag.box[1]-(e.clientY-drag.y)*ratio,drag.box[2],drag.box[3]]);});
 const end=()=>{drag=null;map.classList.remove('dragging');};map.addEventListener('pointerup',end);map.addEventListener('pointercancel',end);
 window.addEventListener('resize',drawMarkers);render();setView(view);setBox(presets[region.value]||presets.world);
}
document.querySelectorAll('[data-open-comparison]').forEach(a=>a.addEventListener('click',()=>{document.querySelector('#comparison').open=true;}));
const dialog=document.querySelector('#video-dialog');
if(dialog){document.querySelectorAll('[data-video]').forEach(b=>b.addEventListener('click',()=>{const url=b.dataset.video;if(!/^https:\/\/(www\.youtube-nocookie\.com\/embed\/|www\.youtube\.com\/embed\/|player\.vimeo\.com\/video\/)/.test(url))return;dialog.querySelector('.dialog-title').textContent=b.dataset.title||'公式動画';dialog.querySelector('.dialog-body').innerHTML=`<iframe src="${esc(url)}" title="${esc(b.dataset.title)}" allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; fullscreen" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>`;dialog.showModal();}));dialog.querySelector('[data-close]').addEventListener('click',()=>dialog.close());dialog.addEventListener('close',()=>dialog.querySelector('.dialog-body').replaceChildren());dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close();});}
document.querySelectorAll('.menu a').forEach(a=>a.addEventListener('click',()=>a.closest('details').open=false));
})();
