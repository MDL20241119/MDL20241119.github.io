/* The map uses the same filters and evidence records as the case list. */
'use strict';
window.createAtlasMap = ({ data, stages, onFilter, onClear }) => {
  const $ = s => document.querySelector(s);
  const map = $('#world-map'), layer = $('#map-markers'), panel = $('#map-panel');
  const dialog = $('#map-detail-dialog'), countrySelect = $('#map-country');
  const regionNames = {world:'世界', 'north-america':'北米', europe:'ヨーロッパ', asia:'アジア'};
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const shortCity = d => ({'project-plateau':'東京','manufacturing-usa':'ゲイザースバーグ','hvm-catapult':'シェフィールド','bmw-startup-garage':'ミュンヘン近郊','punggol-digital-district':'シンガポール'}[d.id] || d.city.split(/[（／・]/)[0]);
  const xy = d => [(d.lng + 180) * 1200 / 360, (90 - d.lat) * 600 / 180];
  const mobile = () => matchMedia('(max-width:760px)').matches;
  let items = [], available = [], region = '', country = '', selected = null, groupIds = [];
  let visible = false, touchEnabled = false, box = [0,0,1200,600], pending = false, signature = '', lastAspect = 0;
  const aspect = () => (map.clientWidth || 900) / (map.clientHeight || 520);
  const schedule = () => { if (!pending) { pending = true; requestAnimationFrame(() => { pending = false; draw(); }); } };
  function setBox(next) {
    const a = aspect(), w = Math.max(24, Math.min(1500, next[2])), h = w / a;
    const cx = Math.max(0, Math.min(1200, next[0] + next[2]/2));
    const cy = Math.max(0, Math.min(600, next[1] + next[3]/2));
    box = [cx-w/2, cy-h/2, w, h];
    map.setAttribute('viewBox', box.join(' '));
    $('#zoom-in').disabled = w <= 24.01; $('#zoom-out').disabled = w >= 1499;
    schedule();
  }
  function fit(list = items) {
    if (!list.length) { setBox([0,0,1200,600]); return; }
    const pts = list.map(xy), xs = pts.map(p=>p[0]), ys = pts.map(p=>p[1]);
    const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
    const a = aspect(), width = map.clientWidth || 900, height = map.clientHeight || 520;
    const w = Math.max(45, (maxX-minX)/Math.max(.35,1-130/width), (maxY-minY)*a/Math.max(.35,1-150/height));
    setBox([(minX+maxX-w)/2, (minY+maxY-w/a)/2, w, w/a]);
  }
  function zoom(factor) { const w = box[2]*factor; setBox([box[0]+(box[2]-w)/2,box[1]+(box[3]-w/aspect())/2,w,w/aspect()]); }
  function groups(unit) {
    const result = [];
    for (const d of items) {
      const [x,y] = xy(d);
      const near = result.filter(g => g.items.some(z => { const p=xy(z); return Math.hypot(p[0]-x,p[1]-y)<54*unit; }));
      const all = [d, ...near.flatMap(g=>g.items)];
      for (const g of near) result.splice(result.indexOf(g),1);
      result.push({items:all, x:all.reduce((n,z)=>n+xy(z)[0],0)/all.length, y:all.reduce((n,z)=>n+xy(z)[1],0)/all.length});
    }
    return result;
  }
  function clusterName(g) {
    const cities = [...new Set(g.items.map(shortCity))], countries = [...new Set(g.items.map(d=>d.country))];
    return cities.length === 1 ? cities[0] : countries.length === 1 ? countries[0] : regionNames[g.items[0].region];
  }
  function draw() {
    if (!visible || !map.clientWidth) return;
    const unit = box[2]/map.clientWidth, all = groups(unit);
    const focus = document.activeElement?.closest?.('[data-map-key]')?.dataset.mapKey;
    const onScreen = all.filter(g => g.x>=box[0]-25*unit && g.x<=box[0]+box[2]+25*unit && g.y>=box[1]-25*unit && g.y<=box[1]+box[3]+25*unit);
    const occupied = onScreen.map(g => [g.x/unit-31,g.y/unit-23,62,46]);
    const intersects = (a,b) => a[0]<b[0]+b[2] && a[0]+a[2]>b[0] && a[1]<b[1]+b[3] && a[1]+a[3]>b[1];
    const sorted = [...onScreen].sort((a,b)=>Number(b.items.some(d=>d.id===selected))-Number(a.items.some(d=>d.id===selected)));
    layer.innerHTML = sorted.map((g,i) => {
      const many=g.items.length>1, active=g.items.some(d=>d.id===selected), grouped=!selected&&groupIds.length&&g.items.some(d=>groupIds.includes(d.id));
      const title=many?clusterName(g):shortCity(g.items[0]);
      const a11y=many?`${title}周辺の${g.items.length}拠点を選ぶ`:`${g.items[0].name}／${g.items[0].city}の概要を表示`;
      const key=g.items.map(d=>d.id).sort().join('|');
      const px=g.x/unit, py=g.y/unit, tw=Math.min(168,[...title].reduce((n,c)=>n+(c.charCodeAt(0)>255?12:7),0)+10);
      let label='';
      for (const offset of [-34,37]) {
        const rect=[px-tw/2,py+offset-9,tw,18];
        if (rect[0]<box[0]/unit+4 || rect[0]+tw>(box[0]+box[2])/unit-4 || occupied.some(r=>intersects(rect,r))) continue;
        occupied.push(rect); label=`<text class="marker-place" y="${offset*unit}" font-size="${12*unit}">${esc(title)}</text>`;break;
      }
      const shape=many?`<rect class="marker-cluster" x="${-29*unit}" y="${-19*unit}" width="${58*unit}" height="${38*unit}" rx="${4*unit}"/><text class="marker-count" font-size="${13*unit}">${g.items.length}拠点</text>`:`<circle class="marker-single" r="${10*unit}"/><circle class="marker-core" r="${3*unit}"/>`;
      return `<g class="map-marker ${many?'is-cluster':'is-single'} ${active||grouped?'selected':''}" tabindex="0" role="button" aria-pressed="${!!(active||grouped)}" aria-label="${esc(a11y)}" data-map-key="${esc(key)}" data-map-group="${i}" transform="translate(${g.x} ${g.y})"><title>${esc(a11y)}</title><rect class="marker-hit" x="${-28*unit}" y="${-25*unit}" width="${56*unit}" height="${50*unit}"/>${shape}${label}</g>`;
    }).join('');
    layer.querySelectorAll('[data-map-group]').forEach(el => {
      const g=sorted[Number(el.dataset.mapGroup)];
      const act=()=> { if(g.items.length===1) choose(g.items[0],true); else { selected=null;groupIds=g.items.map(d=>d.id);fit(g.items);renderPanel();openSheet(); } };
      el.addEventListener('click',act);el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();act();}});
    });
    if (focus) [...layer.children].find(el=>el.dataset.mapKey===focus)?.focus({preventScroll:true});
    const countryPaths=[...map.querySelectorAll('.map-countries path')], present=new Set(items.map(d=>d.country));
    countryPaths.forEach(p=>{p.classList.toggle('has-cases',present.has(p.dataset.country));p.classList.toggle('country-selected',p.dataset.country===country&&!!country);});
    const geographic=[];
    if(box[2]<430) for(const p of countryPaths) {
      const name=p.dataset.country;if(!name||!present.has(name))continue;
      const x=Number(p.dataset.labelX),y=Number(p.dataset.labelY),w=name.length*11+8,r=[x/unit-w/2,y/unit-8,w,16];
      if(x<box[0]+15*unit||x>box[0]+box[2]-15*unit||y<box[1]+20*unit||y>box[1]+box[3]-20*unit||occupied.some(z=>intersects(r,z)))continue;
      occupied.push(r);geographic.push(`<text x="${x}" y="${y}" font-size="${11*unit}">${esc(name)}</text>`);
    }
    $('#map-geography').innerHTML=geographic.join('');
  }
  function listMarkup(list) {
    return list.map(d=>`<button type="button" class="map-place-row ${d.id===selected?'active':''}" data-map-case="${esc(d.id)}"><span class="map-place-number">${esc(d.number)}</span><span><small>${esc(d.country)} / ${esc(shortCity(d))}</small><strong>${esc(d.shortName||d.name)}</strong><span class="map-row-stage">${esc(stages[d.stage])}</span></span><span aria-hidden="true">→</span></button>`).join('');
  }
  function renderPanel() {
    const d=items.find(x=>x.id===selected), group=groupIds.length?items.filter(x=>groupIds.includes(x.id)):items;
    let html;
    if(d) {
      html=`<div class="map-preview"><button type="button" class="map-back" data-map-back>← ${groupIds.length?'この周辺の拠点':'拠点一覧'}に戻る</button><div class="map-preview-heading"><p class="eyebrow">CASE ${esc(d.number)} / ${esc(d.country)}</p><p class="map-city">${esc(d.city)}</p><h3>${esc(d.shortName||d.name)}</h3><span class="map-stage-tag">${esc(stages[d.stage])}</span></div>${d.image?`<figure class="map-preview-photo"><img src="${esc(d.image)}" alt="${esc(d.imageAlt||d.name)}" class="${d.imageNoCrop?'uncropped':''}" loading="lazy"><figcaption>${d.imageCaption?`${esc(d.imageCaption)}<br>`:""}${d.imageDate?`${esc(d.imageDate)} · `:""}PHOTO: ${esc(d.imageCredit)} · <a href="${esc(d.imageSource)}" target="_blank" rel="noopener noreferrer">掲載元</a> · <a href="${esc(d.imageRights)}" target="_blank" rel="noopener noreferrer">${esc(d.imageLicense)}</a>${d.imageChanges?`<br>${esc(d.imageChanges)}`:""}</figcaption></figure>`:''}<div class="map-preview-copy"><p class="eyebrow">この事例から学べること</p><p class="map-preview-learning">${esc(d.tagline)}</p><p class="map-location-note">${esc(d.locationNote||'代表所在地です。正確な訪問先は公式サイトで確認してください。')}</p><a class="btn black" href="cases/${esc(d.id)}/">仕組み・成果を詳しく読む →</a><a class="map-official" href="${esc(d.sources[0].url)}" target="_blank" rel="noopener noreferrer">公式サイトを見る ↗</a></div></div>`;
    } else {
      html=`<div class="map-browser-heading"><p class="eyebrow">${groupIds.length?'SELECTED AREA / 選んだエリア':'PLACES / 拠点名からも選べます'}</p><h3>${groupIds.length?'この周辺の拠点':(country||regionNames[region||'world'])+'の拠点'}<span>${group.length}</span></h3><p>${group.length?'気になる拠点を選ぶと、概要を表示します。':'条件を減らして探し直してください。'}</p>${groupIds.length?'<button type="button" class="map-back" data-map-all>← 条件に合う全拠点に戻る</button>':''}</div><div class="map-place-list">${listMarkup(group)}</div>${group.length?'':'<button type="button" class="map-clear" data-map-clear>絞り込みを解除</button>'}`;
    }
    panel.innerHTML=html;panel.scrollTop=0;
    dialog.querySelector('.map-detail-body').innerHTML=html;
    $('#map-status').textContent=d?`選択中：${d.shortName||d.name}`:groupIds.length?`この周辺に${group.length}拠点`:`${items.length}拠点を表示`;
  }
  function openSheet() { if(mobile()&&!dialog.open)dialog.showModal(); }
  function choose(d,fromMarker=false) {
    selected=d.id;
    if(!fromMarker){const p=xy(d),a=aspect(),w=Math.min(box[2],115);setBox([p[0]-w/2,p[1]-w/a/2,w,w/a]);}
    renderPanel();schedule();openSheet();
  }
  const panelAction = e => {
    const b=e.target.closest('button');if(!b)return;
    if(b.dataset.mapCase){const d=items.find(x=>x.id===b.dataset.mapCase);if(d)choose(d);}
    else if(b.hasAttribute('data-map-back')){selected=null;renderPanel();schedule();}
    else if(b.hasAttribute('data-map-all')){selected=null;groupIds=[];fit();renderPanel();}
    else if(b.hasAttribute('data-map-clear')){if(dialog.open)dialog.close();onClear();}
  };
  panel.addEventListener('click',panelAction);dialog.addEventListener('click',panelAction);
  dialog.querySelector('[data-map-dialog-close]').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close();});
  $('#map-empty [data-map-clear]').addEventListener('click',onClear);
  document.querySelectorAll('[data-map-region]').forEach(b=>b.addEventListener('click',()=>onFilter(b.dataset.mapRegion==='world'?'':b.dataset.mapRegion,'')));
  countrySelect.addEventListener('change',()=>onFilter(region,countrySelect.value));
  $('#zoom-in').addEventListener('click',()=>zoom(.68));$('#zoom-out').addEventListener('click',()=>zoom(1/.68));
  $('#map-reset').addEventListener('click',()=>{selected=null;groupIds=[];fit();renderPanel();});
  $('#map-touch').addEventListener('click',()=>{touchEnabled=!touchEnabled;map.classList.toggle('is-interactive',touchEnabled);$('#map-touch').setAttribute('aria-pressed',String(touchEnabled));$('#map-touch').textContent=touchEnabled?'移動を終了する':'地図を動かす';});
  map.addEventListener('keydown',e=>{if(e.target!==map)return;const w=box[2],h=box[3],next=[...box];if(e.key==='ArrowLeft')next[0]-=w*.15;else if(e.key==='ArrowRight')next[0]+=w*.15;else if(e.key==='ArrowUp')next[1]-=h*.15;else if(e.key==='ArrowDown')next[1]+=h*.15;else if(e.key==='+'||e.key==='='){e.preventDefault();zoom(.68);return;}else if(e.key==='-'){e.preventDefault();zoom(1/.68);return;}else if(e.key==='Home'){e.preventDefault();fit();return;}else return;e.preventDefault();setBox(next);});
  const pointers=new Map();let gesture=null;
  function beginGesture(){const pts=[...pointers.values()];gesture=pts.length>1?{box:[...box],mid:[(pts[0][0]+pts[1][0])/2,(pts[0][1]+pts[1][1])/2],distance:Math.hypot(pts[0][0]-pts[1][0],pts[0][1]-pts[1][1])}:{box:[...box],start:pts[0]};}
  map.addEventListener('pointerdown',e=>{if(e.target.closest('.map-marker')||(e.pointerType==='touch'&&!touchEnabled))return;pointers.set(e.pointerId,[e.clientX,e.clientY]);map.setPointerCapture(e.pointerId);beginGesture();map.classList.add('dragging');});
  map.addEventListener('pointermove',e=>{if(!pointers.has(e.pointerId)||!gesture)return;pointers.set(e.pointerId,[e.clientX,e.clientY]);const pts=[...pointers.values()],ratio=gesture.box[2]/map.clientWidth;if(pts.length>1&&gesture.distance){const dist=Math.max(1,Math.hypot(pts[0][0]-pts[1][0],pts[0][1]-pts[1][1])),w=gesture.box[2]*gesture.distance/dist,mid=[(pts[0][0]+pts[1][0])/2,(pts[0][1]+pts[1][1])/2];setBox([gesture.box[0]+(gesture.box[2]-w)/2-(mid[0]-gesture.mid[0])*ratio,gesture.box[1]+(gesture.box[3]-w/aspect())/2-(mid[1]-gesture.mid[1])*ratio,w,w/aspect()]);}else if(gesture.start)setBox([gesture.box[0]-(e.clientX-gesture.start[0])*ratio,gesture.box[1]-(e.clientY-gesture.start[1])*ratio,gesture.box[2],gesture.box[3]]);});
  const end=e=>{pointers.delete(e.pointerId);if(pointers.size)beginGesture();else{gesture=null;map.classList.remove('dragging');}};
  map.addEventListener('pointerup',end);map.addEventListener('pointercancel',end);
  function resize(){if(!visible||!map.clientWidth)return;const a=aspect();if(Math.abs(a-lastAspect)>.02){lastAspect=a;fit();}else schedule();if(!mobile()&&dialog.open)dialog.close();}
  new ResizeObserver(resize).observe(map);
  return {
    update(next, filters) {
      items=next;available=filters.available;region=filters.region;country=filters.country;
      const key=items.map(d=>d.id).join('|')+';'+region+';'+country;
      if(key!==signature){signature=key;selected=null;groupIds=[];fit();}
      document.querySelectorAll('[data-map-region]').forEach(b=>{const r=b.dataset.mapRegion;b.setAttribute('aria-pressed',String(r===(region||'world')));b.querySelector('[data-region-count]').textContent=available.filter(d=>r==='world'||d.region===r).length;});
      const countries=[...new Set(available.filter(d=>!region||d.region===region).map(d=>d.country))].sort((a,b)=>a.localeCompare(b,'ja'));
      if(country&&!countries.includes(country))countries.push(country);
      countrySelect.innerHTML='<option value="">すべての国</option>'+countries.map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('');countrySelect.value=country;
      $('#map-scope').textContent=(country||regionNames[region||'world'])+'の拠点';$('#map-empty').hidden=items.length>0;
      renderPanel();schedule();
    },
    setVisible(value) { visible=value;if(!visible&&dialog.open)dialog.close();if(visible)requestAnimationFrame(resize); }
  };
};
