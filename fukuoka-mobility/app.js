import {calculateBC,forecastSeries,TIME_VALUE} from './calculations.js';
const $=s=>document.querySelector(s),all=s=>[...document.querySelectorAll(s)];
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(v,d=0)=>v===null||v===undefined||!Number.isFinite(Number(v))?'—':Number(v).toLocaleString('ja-JP',{maximumFractionDigits:d,minimumFractionDigits:d});
const ext=(url,label='一次資料')=>/^https:\/\//.test(url??'')?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`:'—';
const tag=(text,cls='')=>`<span class="tag ${cls}">${esc(text)}</span>`;
const metric=(label,value,sub='')=>`<div class="metric"><span class="label">${label}</span><strong>${value}</strong><span class="sub">${sub}</span></div>`;
const table=(headers,rows,cls='')=>`<div class="table-wrap"><table class="data-table ${cls}"><thead><tr>${headers.map(h=>`<th scope="col">${h}</th>`).join('')}</tr></thead><tbody>${rows.length?rows.map(r=>`<tr>${r.map((c,i)=>`<td data-label="${esc(headers[i].replace(/<[^>]*>/g,''))}"><div class="cell-value">${c??'—'}</div></td>`).join('')}</tr>`).join(''):`<tr><td colspan="${headers.length}">該当するデータはありません。</td></tr>`}</tbody></table></div>`;
const panel=(title,body,meta='')=>`<div class="panel"><div class="panel-title"><div><h3>${title}</h3>${meta?`<p>${meta}</p>`:''}</div></div>${body}</div>`;
let data,geo,map,stopLayer,shapeLayer,originLayer,visibleStops=[],stopPage=0,selectedStop=null,mode='frequency',lastView='start';
const colors={zero:'#a3adb4',low:'#d6a23e',medium:'#139c91',high:'#1f539b'};
const bounds=[[32.98,130.01],[34.03,131.20]];
const places={fukuoka:[33.59,130.42,13],kitakyushu:[33.885,130.882,13],kurume:[33.32,130.502,12],tagawa:[33.63,130.815,12],omuta:[33.029,130.444,12],itoshima:[33.558,130.2,12]};
function day(){return Number($('#map-date').value)}function feed(){return $('#map-feed').value}
function feedName(i){return geo.feeds[i].name.replace('GTFSデータ','')}
function color(n){return n===null?'#d4c5d0':n===0?colors.zero:n<10?colors.low:n<30?colors.medium:colors.high}
function route(view,scroll=false){
  if(view==='main'){$('#main').focus();return}
  if(!['start','map','ridership','od','forecast','cost','bc','sources'].includes(view))view='start';lastView=view;
  const group=({ridership:'use',od:'use',forecast:'use',bc:'cost'})[view]??view;
  const tabs=({use:[['ridership','乗降人数'],['od','起点・終点'],['forecast','需要の見通し']],cost:[['cost','運行費用'],['bc','費用便益を試す']]})[group]??[];
  all('.view').forEach(x=>x.hidden=x.id!=='view-'+view);
  all('#nav a').forEach(x=>{const active=x.dataset.group===group;x.classList.toggle('active',active);active?x.setAttribute('aria-current','page'):x.removeAttribute('aria-current')});
  $('#subnav').hidden=!tabs.length;$('#subnav').classList.toggle('two-items',tabs.length===2);
  $('#subnav').innerHTML=tabs.map(([key,label])=>`<a href="#${key}" class="${view===key?'active':''}" ${view===key?'aria-current="page"':''}>${label}</a>`).join('');
  $('#bc-mobile-summary').hidden=view!=='bc';
  document.title='公開デモ｜'+$('#view-'+view+' h1').textContent+'｜福岡 交通データ';
  if(view==='map'&&map)setTimeout(()=>map.invalidateSize(),30);
  if(view==='forecast'&&data)$('#forecast-chart').innerHTML=forecastChart($('#forecast-method').value);
  if(scroll){window.scrollTo({top:0,behavior:'auto'});$('#main').focus({preventScroll:true})}
}
function setupMap(){
  if(!window.L)throw new Error('地図の表示に必要なファイルを読み込めませんでした。ページを再読み込みしてください。');
  map=L.map('map',{preferCanvas:true,scrollWheelZoom:false,minZoom:5,maxZoom:18}).fitBounds(bounds,{padding:[8,8]});
  const tiles=L.tileLayer('https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png',{maxNativeZoom:18,maxZoom:18,attribution:'背景：<a href="https://maps.gsi.go.jp/development/ichiran.html" target="_blank" rel="noopener">地理院タイル</a>｜交通：各自治体・運行事業者（個別の利用条件）'}).addTo(map);
  let failures=0;tiles.on('tileerror',()=>{failures++;if(failures>3)$('#tile-warning').hidden=false});tiles.on('tileload',()=>{$('#tile-warning').hidden=true;failures=0});
  shapeLayer=L.layerGroup().addTo(map);stopLayer=L.layerGroup().addTo(map);originLayer=L.layerGroup().addTo(map);
  geo.stops.forEach((s,i)=>s.index=i);
  $('#map-feed').innerHTML='<option value="all">すべての公開データ</option>'+geo.feeds.map((f,i)=>`<option value="${i}">${esc(feedName(i))}</option>`).join('');
  $('#reach-origin').innerHTML=geo.origins.map((o,i)=>`<option value="${i}">${esc(o.name)}</option>`).join('');
  ['#map-date','#map-feed'].forEach(id=>$(id).addEventListener('change',()=>{selectedStop=null;stopPage=0;map.closePopup();closeSuggestions();drawMap()}));
  all('[data-day]').forEach(button=>button.addEventListener('click',()=>{$('#map-date').value=button.dataset.day;$('#map-date').dispatchEvent(new Event('change'))}));
  $('#map-place').addEventListener('change',()=>{const p=places[$('#map-place').value];$('#stop-search').value='';closeSuggestions();selectedStop=null;map.closePopup();renderMapSummary();p?map.setView(p.slice(0,2),p[2]):map.fitBounds(bounds);updateMapSummary();renderStopTable()});
  $('#show-shapes').addEventListener('change',drawMap);
  $('#reach-origin').addEventListener('change',()=>{selectedStop=null;stopPage=0;map.closePopup();closeSuggestions();drawMap();map.setView(geo.origins[Number($('#reach-origin').value)].center,11)});
  ['frequency','reach'].forEach(m=>$('#mode-'+m).addEventListener('click',()=>{mode=m;selectedStop=null;stopPage=0;map.closePopup();closeSuggestions();all('.map-modes .segmented button').forEach(x=>{const active=x.id==='mode-'+m;x.classList.toggle('selected',active);x.setAttribute('aria-pressed',String(active))});$('#reach-control').hidden=m!=='reach';$('#reach-note').hidden=m!=='reach';drawMap();if(m==='reach')map.setView(geo.origins[Number($('#reach-origin').value)].center,11)}));
  $('#reset-map').addEventListener('click',()=>{$('#map-date').value='0';$('#map-feed').value='all';$('#map-place').value='all';$('#stop-search').value='';$('#show-shapes').checked=true;selectedStop=null;stopPage=0;$('#mode-frequency').click();map.fitBounds(bounds);$('.map-settings').open=false});
  $('#stop-search').addEventListener('input',()=>{stopPage=0;renderStopTable();renderSuggestions()});
  $('#stop-search').addEventListener('focus',renderSuggestions);
  $('#stop-search').addEventListener('keydown',e=>{if(e.key==='Escape')closeSuggestions();if(e.key==='Enter'&&!$('#stop-suggestions').hidden){e.preventDefault();$('#stop-suggestions button')?.click()}if(e.key==='ArrowDown'&&!$('#stop-suggestions').hidden){e.preventDefault();$('#stop-suggestions button')?.focus()}});
  $('#stop-suggestions').addEventListener('keydown',e=>{if(e.key==='Escape'){closeSuggestions();$('#stop-search').focus();closeSuggestions()}if(['ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();const buttons=all('#stop-suggestions button'),i=buttons.indexOf(document.activeElement);buttons[(i+(e.key==='ArrowDown'?1:-1)+buttons.length)%buttons.length]?.focus()}});
  document.addEventListener('click',e=>{if(!e.target.closest('.map-search'))closeSuggestions();if(!e.target.closest('.map-settings'))$('.map-settings').open=false});
  ['#stop-table','#stop-suggestions'].forEach(id=>$(id).addEventListener('click',e=>{const b=e.target.closest('[data-stop]');if(b)selectStop(Number(b.dataset.stop),true)}));
  $('#map-detail').addEventListener('click',e=>{if(e.target.closest('[data-clear-stop]')){selectedStop=null;map.closePopup();renderMapSummary();$('#stop-search').focus();closeSuggestions()}});
  $('#stop-prev').addEventListener('click',()=>{stopPage--;renderStopTable();$('#stop-list-title').scrollIntoView({block:'start',behavior:'smooth'})});$('#stop-next').addEventListener('click',()=>{stopPage++;renderStopTable();$('#stop-list-title').scrollIntoView({block:'start',behavior:'smooth'})});
  map.on('moveend',()=>{stopPage=0;updateMapSummary();renderStopTable()});
  drawMap();
}
function closeSuggestions(){$('#stop-suggestions').hidden=true;$('#stop-search').setAttribute('aria-expanded','false')}
function renderSuggestions(){
  const q=$('#stop-search').value.trim().toLowerCase();if(!q){closeSuggestions();return}
  const matches=visibleStops.filter(s=>s.name.toLowerCase().includes(q)).sort((a,b)=>b.departures[day()]-a.departures[day()]);
  $('#stop-suggestions').innerHTML=matches.length?matches.slice(0,6).map(s=>`<button type="button" data-stop="${s.index}"><span>${esc(s.name)}</span><small>${esc(feedName(s.feedIndex))} · ${fmt(s.departures[day()])}本／日</small></button>`).join('')+`<p>全${fmt(matches.length)}件は地図の下に表示</p>`:'<p>該当なし。停留所名の一部でも検索できます。</p>';
  $('#stop-suggestions').hidden=false;$('#stop-search').setAttribute('aria-expanded','true');
}
function drawMap(){
  const d=day(),f=feed(),origin=Number($('#reach-origin').value);const belongs=s=>f==='all'||s.feedIndex===Number(f);
  visibleStops=geo.stops.filter(s=>belongs(s)&&(mode==='frequency'||(s.reach[d]&(1<<origin))));
  shapeLayer.clearLayers();stopLayer.clearLayers();originLayer.clearLayers();
  if($('#show-shapes').checked)geo.shapes.filter(s=>belongs(s)&&s.trips[d]>0).forEach(s=>L.polyline(s.coordinates,{color:'#2d8896',weight:1.5,opacity:mode==='reach'?.19:.35,interactive:false,smoothFactor:1}).addTo(shapeLayer));
  visibleStops.forEach(s=>{const n=s.departures[d];const active=mode==='reach';L.circleMarker([s.lat,s.lon],{radius:active?4:(n>=30?4:3),color:active?'#fff':color(n),weight:active?.8:.6,fillColor:active?'#086f78':color(n),fillOpacity:n===0?.38:.82,opacity:.8}).addTo(stopLayer).on('click',()=>selectStop(s.index,false)).bindTooltip(esc(s.name),{direction:'top',opacity:.95});});
  if(mode==='reach'){const o=geo.origins[origin];L.circleMarker(o.center,{radius:9,color:'#fff',weight:3,fillColor:'#cb6b22',fillOpacity:1}).addTo(originLayer).bindTooltip(esc(o.name)+'（起点集合の中心）');$('#map-legend').innerHTML='<b>9時から60分以内・直通到達</b><span><i style="--dot:#cb6b22"></i>起点 <i style="--dot:#086f78"></i>到達する乗り場</span>';}
  else $('#map-legend').innerHTML='<b>出発する便数／日</b><span><i style="--dot:#a3adb4"></i>0 <i style="--dot:#d6a23e"></i>1–9 <i style="--dot:#139c91"></i>10–29 <i style="--dot:#1f539b"></i>30以上</span>';
  all('[data-day]').forEach(b=>{const active=Number(b.dataset.day)===d;b.classList.toggle('selected',active);b.setAttribute('aria-pressed',String(active))});
  if(selectedStop!==null&&visibleStops.some(s=>s.index===selectedStop))renderStopDetail(geo.stops[selectedStop]);else{selectedStop=null;renderMapSummary()}
  updateMapSummary();renderStopTable();
}
function updateMapSummary(){
  if(!map)return;const d=day(),f=feed(),inView=visibleStops.filter(s=>map.getBounds().contains([s.lat,s.lon]));
  const trips=f==='all'?geo.meta.scheduledTripTotals[d]:geo.feeds[Number(f)].scheduledTrips[d];
  $('#map-summary').innerHTML=`<div>地図内の乗り場 <b>${fmt(inView.length)}</b></div><div>当日出発あり <b>${fmt(inView.filter(s=>s.departures[d]>0).length)}</b></div><div class="scope-summary">${mode==='reach'?`直通到達・参考集約 <b>${fmt(new Set(visibleStops.map(s=>s.name)).size)}</b>停留所名`:`対象データ全体 <b>${fmt(trips)}</b>片道便`}</div>`;
}
function renderMapSummary(){
  const d=day(),f=feed(),trips=f==='all'?geo.meta.scheduledTripTotals:geo.feeds[Number(f)].scheduledTrips,max=Math.max(1,...trips);
  $('#map-detail').classList.add('default-detail');
  $('#map-detail').innerHTML=mode==='reach'?`<div class="detail-label">直通60分の到達先</div><h3>${esc(geo.origins[Number($('#reach-origin').value)].name)}から</h3><p class="muted">点を選ぶと、その乗り場の情報が分かります。</p><div class="data-scope"><b>到達停留所名の参考集約</b><p>同名の乗り場をまとめた集計です。同名別地点の混同が残ります。</p><p style="margin-top:14px">背景の線は当日の路線形状です。個々の到達経路を示すものではありません。</p></div>`:`<div class="detail-hint"><div class="hint-icon" aria-hidden="true"><svg viewBox="0 0 32 32"><path d="M24 13c0 6-8 15-8 15S8 19 8 13a8 8 0 0 1 16 0Z"/><circle cx="16" cy="13" r="3"/></svg></div><h3>停留所を選んでみましょう</h3><p>地図の丸を押すと、曜日ごとの本数が分かります。停留所名でも検索できます。</p></div><div class="data-scope"><b>対象データ全体の片道便</b>${f==='all'?'公開'+geo.feeds.length+'データ':esc(feedName(Number(f)))}<div class="weekday-bars">${['月','土','日'].map((label,i)=>`<div class="weekday-row ${i===d?'current':''}"><span>${label}</span><div class="weekday-track"><i style="width:${trips[i]/max*100}%"></i></div><b>${fmt(trips[i])}</b></div>`).join('')}</div><p>県境外も含む運行予定です。地図内の便数・乗客数ではありません。</p></div>`;
}
function selectStop(i,fly){
  const s=geo.stops[i];selectedStop=i;closeSuggestions();renderStopDetail(s);
  if(fly)map.setView([s.lat,s.lon],Math.max(map.getZoom(),14));
  L.popup({maxWidth:270}).setLatLng([s.lat,s.lon]).setContent(`<h3>${esc(s.name)}</h3>${esc(feedName(s.feedIndex))}<br>${esc(geo.meta.dateLabels[day()])}：出発 ${fmt(s.departures[day()])} 本`).openOn(map);
  if(fly&&window.innerWidth<701)$('#map').scrollIntoView({block:'start',behavior:'smooth'});
}
function renderStopDetail(s){
  const f=geo.feeds[s.feedIndex],routes=s.routes.map(i=>geo.routes[i]).filter(r=>r.trips[day()]>0);
  $('#map-detail').classList.remove('default-detail');
  $('#map-detail').innerHTML=`<div class="detail-label">選択した乗り場</div><h3>${esc(s.name)}</h3><p class="muted">${esc(feedName(s.feedIndex))}</p><div class="detail-stats">${['月','土','日'].map((d,i)=>`<div class="${i===day()?'current':''}">9/${[8,12,13][i]} ${d}<b>${fmt(s.departures[i])}</b>本／日</div>`).join('')}</div><p class="muted">${s.departures[day()]===0?'当日の通常乗車可能な出発が0。地域の交通手段がないという意味ではありません。':'この乗り場から通常乗車できる出発数です。利用人数ではありません。'}</p><details><summary>登録路線と出典</summary><div class="details-content"><p class="muted">登録路線のうち当日運行あり</p><p>${routes.length?routes.map(r=>esc(r.name)).join('<br>'):'該当する登録路線なし'}</p><p class="muted">路線の登録関係から表示。各便の停車は時刻表を確認してください。</p>${ext(f.sourceUrl,'公開データ・出典')}</div></details><button class="quiet-button detail-clear" data-clear-stop>選択を解除</button>`;
}
function renderStopTable(){
  const q=$('#stop-search').value.trim().toLowerCase(),filtered=visibleStops.filter(s=>q?s.name.toLowerCase().includes(q):map.getBounds().contains([s.lat,s.lon])).sort((a,b)=>b.departures[day()]-a.departures[day()]);const size=12,pages=Math.max(1,Math.ceil(filtered.length/size));stopPage=Math.min(Math.max(0,stopPage),pages-1);
  $('#stop-list-title').textContent=q?'「'+$('#stop-search').value.trim()+'」の検索結果':'地図の範囲にある停留所';
  $('#stop-list-description').textContent=q?'選択した交通データ'+(mode==='reach'?'・直通到達先':'全体')+'から検索。地図の範囲外も含みます。':'地図を動かすと一覧も変わります。本数の多い順に表示。';
  $('#stop-table').innerHTML=filtered.length?`<div class="stop-grid">${filtered.slice(stopPage*size,(stopPage+1)*size).map(s=>`<button class="stop-card" data-stop="${s.index}"><span class="stop-heading"><span>${esc(s.name)}</span><span class="stop-arrow" aria-hidden="true">↗</span></span><span class="stop-operator">${esc(feedName(s.feedIndex))} · 乗り場別</span><span class="day-counts">${['月','土','日'].map((label,i)=>`<span class="${i===day()?'current':''}">${label}<b>${fmt(s.departures[i])}</b>本</span>`).join('')}</span></button>`).join('')}</div>`:'<div class="notice">該当する停留所はありません。地図の範囲を広げるか、停留所名・表示条件を変更してください。</div>';
  $('#stop-page').textContent=`${fmt(filtered.length)}件 · ${stopPage+1} / ${pages}ページ`;$('#stop-prev').disabled=stopPage===0;$('#stop-next').disabled=stopPage===pages-1;
}
function renderRidership(){
 const total=data.route_actuals.find(r=>r.route==='全線');
 $('#ridership-content').innerHTML=`<div class="metric-grid">${metric('地下鉄・1日平均乗車人員',fmt(total.passengers)+'人','2024年度・福岡市交通局')}${metric('駅・接続線の公表値',fmt(data.stop_actuals.length)+'行','同名駅は路線別。接続線の流入を含む。')}${metric('全線の時系列','1981〜2024年度','各年の公表値。開業・延伸の影響を含む。')}</div><div class="notice">年度平均の乗車人員です。実人数・乗降合算・当日の乗客数とは異なります。路線別と全線合計を重複して合算しません。</div><div class="section-block"><h3>路線ごとの利用実績</h3>${table(['路線・事業者','観測期間','乗車人員／日','出典'],data.route_actuals.map(r=>[esc(r.route)+'<span class="cell-meta">'+esc(r.operator)+'</span>',esc(r.period),fmt(r.passengers),ext(r.source_url)]))}</div><div class="section-block"><div class="subheading"><h3>駅・接続線ごとの乗車人員</h3><div class="field-inline"><label for="stop-city">路線</label><select id="stop-city"><option value="all">すべて</option>${['空港線','箱崎線','七隈線'].map(n=>`<option>${n}</option>`).join('')}</select></div></div><div id="observed-table"></div></div><details><summary>数値の読み方・原表を確認</summary><div class="details-content"><p>中洲川端・博多などは路線別に掲載。JR筑肥線・西鉄貝塚線は接続線として原表の区分を維持。丸めのため駅別の和と路線合計に差がある場合があります。2022年度の七隈線延伸区間は開業後5日分を年度日数で平均した値です。</p>${ext(total.source_url,'福岡市・地下鉄駅別乗車人員')}</div></details>`;
 function observed(){const a=$('#stop-city').value;$('#observed-table').innerHTML=table(['駅・接続線','路線','年度','乗車人員／日','原表セル'],data.stop_actuals.filter(r=>a==='all'||r.route===a).map(r=>[esc(r.stop),esc(r.route),r.year,fmt(r.value),esc(r.source_cell)]));}$('#stop-city').addEventListener('change',observed);observed();
}
function renderOD(){
 const wards=[...new Set(data.commute_od.filter(r=>r.level==='ward').map(r=>r.origin))],rows=data.commute_od.filter(r=>r.level==='municipality'),source=rows[0]?.source_url;
 const grid=wards.map(o=>`<tr><th scope="row">${esc(o.replace('福岡市',''))}</th>${wards.map(d=>{const r=data.commute_od.find(r=>r.level==='ward'&&r.origin===o&&r.destination===d);return `<td style="background:rgba(8,126,128,${r?.people==null?0:.05+.45*Math.log1p(r.people)/Math.log1p(120000)})">${fmt(r?.people)}</td>`}).join('')}</tr>`).join('');
 $('#od-content').innerHTML=`<div class="metric-grid">${metric('通勤・通学の調査年','2020年','国勢調査・常住地から従業地／通学地')}${metric('福岡市7区の組合せ',fmt(wards.length**2)+'組','通勤者・通学者数／人')}${metric('主な交通手段','2017年PT','北部九州圏。県単独集計ではない。')}</div><div class="notice amber">国勢調査の通勤・通学者数は、1日の移動回数やバス利用者数ではありません。2017年PTは佐賀県の鳥栖市・基山町を含む北部九州圏の調査です。</div>${panel('福岡市内の通勤・通学OD',`<p class="scroll-hint">横にスクロールして確認できます →</p><div class="table-wrap"><table class="data-table heatmap"><thead><tr><th>常住地 ↓ ／従業・通学地 →</th>${wards.map(w=>`<th scope="col">${esc(w.replace('福岡市',''))}</th>`).join('')}</tr></thead><tbody>${grid}</tbody></table></div><p class="source-note">2020年・男女総数。原表の「－」などの非数値を0に置換していません。${ext(source,'福岡市・国勢調査 第6-1表')}</p>`,'区内と区間の人数を方向別に表示。全交通手段。')}${panel('福岡市から県内各市町村への通勤・通学',`<div class="subheading"><p class="muted">人数の多い順。福岡市合計と区別内訳は別集計。</p><label class="search"><input id="od-search" type="search" placeholder="市町村名を検索" aria-label="従業地・通学地を検索"></label></div><div id="pt-od-table"></div>`)}<details><summary>北部九州圏の主な交通手段の変化</summary><div class="details-content">${table(['交通手段','1993年','2005年','2017年'],['徒歩','二輪車','自動車','バス','鉄道'].map(mode=>[mode,...[1993,2005,2017].map(y=>data.pt_modes.find(r=>r.mode===mode&&r.year===y).share_pct+'%')]))}<p>公表図の丸め値。代表交通手段は鉄道・バス等の優先順位で1つに分類。複数回答の利用経験率ではありません。${ext(data.pt_modes[0].source_url,'福岡県・調査結果概要 印刷8頁')}</p></div></details>`;
 function odTable(){const q=$('#od-search').value.trim();$('#pt-od-table').innerHTML=table(['常住地','従業・通学地','通勤・通学者数','単位・時点'],rows.filter(r=>r.destination.includes(q)).sort((a,b)=>(b.people??-1)-(a.people??-1)).map(r=>[esc(r.origin),esc(r.destination),fmt(r.people),'人・2020年']));}$('#od-search').addEventListener('input',odTable);odTable();
}
function history(){return data.subway_history.filter(r=>r.route==='全線'&&r.year>=2020).map(r=>r.value)}
function forecastChart(which){
 const h=history(),f=forecastSeries(h)[which],values=[...h,...f],years=[2020,2021,2022,2023,2024,2025,2026],W=800,H=270,left=65,right=45,top=30,bottom=48,max=Math.ceil(Math.max(...values)/100000)*100000,min=200000;
 const x=i=>left+i*(W-left-right)/6,y=v=>top+(max-v)/(max-min)*(H-top-bottom),line=a=>a.map(([i,v],j)=>`${j?'L':'M'}${x(i)},${y(v)}`).join(' ');
 return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="福岡市地下鉄の2020〜2024年度実績と2025〜2026年度の条件付き参考値"><rect x="${x(4)}" y="10" width="${W-x(4)-5}" height="220" fill="#fff6e7"/>${Array.from({length:(max-min)/100000+1},(_,i)=>min+i*100000).map(v=>`<line x1="${left}" y1="${y(v)}" x2="${W-right}" y2="${y(v)}" stroke="#dde7eb"/><text x="${left-8}" y="${y(v)+5}" text-anchor="end" class="chart-label">${v/10000}万</text>`).join('')}<path d="${line(h.map((v,i)=>[i,v]))}" fill="none" stroke="#087e80" stroke-width="3"/><path d="${line([[4,h[4]],[5,f[0]],[6,f[1]]])}" fill="none" stroke="#b87917" stroke-width="3" stroke-dasharray="7 5"/>${values.map((v,i)=>`<circle cx="${x(i)}" cy="${y(v)}" r="4" fill="${i<5?'#087e80':'#b87917'}"><title>${years[i]}年度 ${fmt(v)}人／日</title></circle><text class="chart-label" x="${x(i)}" y="${H-18}" text-anchor="middle">${years[i]}</text>`).join('')}</svg>`;
}
function renderForecast(){
 const f=forecastSeries(history()),src=data.route_actuals[0].source_url;
 $('#forecast-content').innerHTML=`<div class="notice amber">感染症による利用減と2023年3月の七隈線延伸を含む時系列です。サービス条件が一定だったとは言えません。2025・2026年度の値は2024年度までの実績からの参考外挿です。</div>${panel('福岡市地下鉄の利用と参考外挿',`<div class="subheading"><div class="legend-row"><span><i></i>公表実績</span><span><i class="dashed"></i>条件付き参考値</span></div><div class="field-inline"><label for="forecast-method">方式</label><select id="forecast-method"><option value="flat">前年実績を据え置く</option><option value="linear">直近3点の直線を延長</option></select></div></div><div id="forecast-chart"></div><p class="chart-source">単位：年度平均乗車人員・人／日。${ext(src,'福岡市の公表実績')}</p>${table(['方式','2025年度参考','2026年度参考'],[['前年実績据置',fmt(f.flat[0]),fmt(f.flat[1])],['直近3点の線形',fmt(f.linear[0]),fmt(f.linear[1])]])}<details><summary>2020〜2024年度の実績値</summary><div class="details-content">${table(['年度','1日平均乗車人員'],history().map((v,i)=>[2020+i,fmt(v)+'人']))}</div></details>`)}<div class="two-col">${panel('仮定を変えて比較する','<p>過去の系列、予測期間、本数を変えた場合の条件は、分析画面で入力して比較できます。</p><a class="button" href="lab.html#demand">需要の計算を試す →</a>')}${panel('この計算で分からないこと','<ul class="bullet-list"><li>増減便・運賃・人口変化の因果効果。</li><li>将来値の統計的な予測区間。</li><li>未利用者の外出断念・誘発需要。</li></ul>')}</div>`;
 $('#forecast-method').addEventListener('change',()=>$('#forecast-chart').innerHTML=forecastChart($('#forecast-method').value));$('#forecast-chart').innerHTML=forecastChart('flat');
}
function renderCost(){const r=data.finance[0];
 $('#cost-content').innerHTML=`<div class="metric-grid">${metric('地下鉄・営業費用',fmt(r.cost/1e8,2)+'億円','2024年度・減価償却費を含む')}${metric('地下鉄・営業収益',fmt(r.revenue/1e8,2)+'億円','運輸収益と運輸雑収益の合計')}${metric('営業収益÷営業費用',fmt(r.revenue/r.cost*100,1)+'%','会計上の指標。社会的B/Cではありません。')}</div><div class="notice">福岡市高速鉄道事業の2024年度損益計算書です。県内バス全体の原価ではありません。営業費用・補助金・減価償却・利益を区別します。</div><div class="two-col">${panel('営業費用の内訳',table(['項目','円'],data.expenses.map(x=>[esc(x.item),fmt(x.yen)])))}${panel('収益・補助金・利益',table(['項目','円'],[['運輸収益',fmt(r.transport_revenue)],['運輸雑収益',fmt(r.revenue-r.transport_revenue)],['営業利益',fmt(r.operating_profit)],['一般会計補助金（営業外収益）',fmt(r.subsidy)],['経常利益',fmt(r.ordinary_profit)],['当年度純利益',fmt(r.net_profit)]]))}</div><div class="section-block"><div class="subheading"><h3>公表財務の集計範囲</h3></div>${table(['地域・事業','期間','営業収益','営業費用','出典'],[[r.area+'・'+r.service,esc(r.period),fmt(r.revenue)+'円',fmt(r.cost)+'円',ext(r.source_url,'決算資料 印刷39頁')]])}<p class="source-note">${esc(r.unit)}。営業外・特別損益を含む純利益と営業利益は異なります。新たな運行案の見積額は別途入力してください。</p></div>`;
}
function setupBC(){
 $('#bc-more').innerHTML=`<details><summary>計算式・評価に含めている範囲</summary><div class="details-content"><p>年間時間便益＝年間対象移動回数 × 改善する割合 × 短縮分 × 時間価値。</p><p>初期値は10,000移動／年、30円／人・分の計算例です。福岡県の実測値や公的な評価原単位ではありません。対象回数・時間価値は上の固定条件欄で変更できます。</p><p>5年間、同じ利用・効果・年額費用を仮定し、各年末の値を割り引きます。初期投資・残存価値なし。運賃・補助金は社会便益に加算しません。事故・環境・分配への影響を含む正式評価は未実施です。</p></div></details>`;
 $('#bc-form').addEventListener('submit',e=>e.preventDefault());['#bc-share','#bc-minutes','#bc-cost','#bc-rate','#bc-users','#bc-time-value'].forEach(id=>$(id).addEventListener('input',updateBC));$('#bc-reset').addEventListener('click',()=>{$('#bc-share').value='50';$('#bc-minutes').value='5';$('#bc-cost').value='30';$('#bc-rate').value='0.04';$('#bc-users').value='10000';$('#bc-time-value').value='30';updateBC()});updateBC();
}
function updateBC(){
  const share=Number($('#bc-share').value)/100,minutes=Number($('#bc-minutes').value),cost=$('#bc-cost').value.trim()===''?NaN:Number($('#bc-cost').value)*10000,rate=Number($('#bc-rate').value);$('#bc-share-value').textContent=fmt(share*100)+'%';$('#bc-minutes-value').textContent=fmt(minutes,Number.isInteger(minutes)?0:1)+'分';
  $('#bc-share').setAttribute('aria-valuetext',fmt(share*100)+'パーセントの移動');$('#bc-minutes').setAttribute('aria-valuetext',fmt(minutes,1)+'分短縮');
  const users=Number($('#bc-users').value),timeValue=Number($('#bc-time-value').value);const r=calculateBC({share,minutes,annualCost:cost,rate,users,timeValue});
  if(!r){$('#bc-results').innerHTML='<div class="error">追加費用に0以上の数値を入力してください。</div>';$('#bc-mobile-summary').innerHTML='<span>費用便益の試算</span><b>費用を入力してください</b>';return}
  $('#bc-results').innerHTML=`<div class="bc-hero"><div class="bc-assumption">いまの条件：対象 ${fmt(share*100)}% · ${fmt(minutes,Number.isInteger(minutes)?0:1)}分短縮 · 年${fmt(cost/10000,1)}万円</div><div class="label">時間便益と釣り合う追加費用</div><div class="value">${fmt(r.annualBenefit/10000,2)}<small>万円／年</small></div><span class="bc-badge">時間便益のみのB/C <b>${r.bc===null?'算定不可':fmt(r.bc,2)}</b></span><p style="margin-top:14px">${r.bc===null?'追加費用が0のため比率は算定できません。':'B/C＝時間短縮の価値 ÷ 追加費用。'}<br>この仮定での費用上限です。正式な事業評価・見積額ではありません。</p></div><div class="bc-summary">${metric('5年分の便益現在価値',fmt(r.pvBenefit/10000,2)+'万円')}${metric('5年分の費用現在価値',fmt(r.pvCost/10000,2)+'万円')}${metric('部分純便益の現在価値',fmt(r.npv/10000,2)+'万円')}${metric('B/C＝1に必要な短縮',r.requiredMinutes===null?'算定不可':fmt(r.requiredMinutes,2)+'分')}</div><p class="source-note">現在の短縮時間で必要な対象割合：${r.requiredShare===null?'算定不可':fmt(r.requiredShare*100,1)+'%'}${r.requiredShare>1?'（100%を超えるため、この短縮時間では費用を賄えません）':''}。費用と効果を確認するための条件整理です。</p>`;
  $('#bc-mobile-summary').innerHTML=`<div><span>時間便益のみのB/C</span><strong>${r.bc===null?'—':fmt(r.bc,2)}</strong></div><div><span>釣り合う追加費用</span><br><b>${fmt(r.annualBenefit/10000,2)}万円／年</b></div>`;
}
function renderSources(){
 $('#sources-content').innerHTML=`<div class="notice">原典の時点・地域・定義を保持しています。全県の交通・施設を網羅するものではありません。未収録・非公表・有効期間外を0と扱いません。</div>${panel('主な一次資料','<ol class="sources-list">'+data.sources.map(s=>'<li>'+ext(s.url,s.title)+'</li>').join('')+'</ol>')}<details open><summary>公開GTFSの有効期間と出典</summary><div class="details-content">${table(['公開データ','有効期間','月／土／日・片道便','出典'],geo.feeds.map(f=>[esc(f.name),esc(f.validFrom)+'〜'+esc(f.validTo),f.scheduledTrips.map(n=>fmt(n)).join(' / '),ext(f.sourceUrl)]))}<p>有効期間外・構造エラーのデータの本数は「—」。乗客数ではなく運行予定です。西鉄バス・JRなどの全時刻表は未収録。</p></div></details>${panel('全データの出典・再利用条件','<p>病院・公共施設・スーパー・鉄道・行政界・人口メッシュの基準日、利用条件、加工方法を確認できます。</p><a class="button" href="data-catalog.html">DATA CATALOG →</a> <a class="button" href="usage.html#sources">出典・利用条件 →</a>')}`;
}
function applyTourismLink(){
  const q=new URLSearchParams(location.search),f=geo.feeds.findIndex(f=>f.id===q.get('feedId'));
  const stop=f<0?-1:geo.stops.findIndex(s=>s.feedIndex===f&&s.id===q.get('stopId'));
  if(stop<0)return;
  if(['0','1','2'].includes(q.get('day')))$('#map-date').value=q.get('day');
  $('#map-feed').value=String(f);drawMap();route('map');selectStop(stop,true);
}
async function start(){
  route(location.hash.slice(1));window.addEventListener('hashchange',()=>route(location.hash.slice(1),true));
  try{const results=await Promise.all([fetch('data/analysis.json'),fetch('data/map-data.json')]);if(results.some(r=>!r.ok))throw new Error('分析データの読み込みに失敗しました。');[data,geo]=await Promise.all(results.map(r=>r.json()));
    for(const [id,value] of [['home-feeds',geo.feeds.length]])if($('#'+id))$('#'+id).textContent=fmt(value);fetch('data/catalog.json').then(r=>r.json()).then(c=>{for(const [id,value] of [['home-destinations',c.overview.destinations],['home-resources',c.overview.resources]])if($('#'+id))$('#'+id).textContent=fmt(value)});renderRidership();renderOD();renderForecast();renderCost();setupBC();renderSources();setupMap();$('#loading').hidden=true;route(lastView);applyTourismLink();
  }catch(e){$('#loading').hidden=true;$('#error').hidden=false;$('#error').innerHTML=esc(e.message)+' <a href="downloads/fukuoka-data-report.html">データ報告書で確認する</a>。';}
}
start();
