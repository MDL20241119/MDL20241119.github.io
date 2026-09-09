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
const bounds=[[32.70,130.75],[33.79,132.05]];
const places={oita:[33.2341,131.6069,13],beppu:[33.2792,131.5012,13],nakatsu:[33.5992,131.1917,12],hita:[33.3185,130.9403,12],saiki:[32.9726,131.9029,12],kunisaki:[33.565,131.729,11]};
function day(){return Number($('#map-date').value)}function feed(){return $('#map-feed').value}
function feedName(i){return geo.feeds[i].name.replace('GTFSデータ','')}
function color(n){return n===0?colors.zero:n<10?colors.low:n<30?colors.medium:colors.high}
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
  document.title='公開デモ｜'+$('#view-'+view+' h1').textContent+'｜大分 交通データ';
  if(view==='map'&&map)setTimeout(()=>map.invalidateSize(),30);
  if(view==='forecast'&&data)$('#forecast-chart').innerHTML=forecastChart($('#forecast-method').value);
  if(scroll){window.scrollTo({top:0,behavior:'auto'});$('#main').focus({preventScroll:true})}
}
function setupMap(){
  if(!window.L)throw new Error('地図の表示に必要なファイルを読み込めませんでした。ページを再読み込みしてください。');
  map=L.map('map',{preferCanvas:true,scrollWheelZoom:false,minZoom:5,maxZoom:18}).fitBounds(bounds,{padding:[8,8]});
  const tiles=L.tileLayer('https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png',{maxNativeZoom:18,maxZoom:18,attribution:'背景：<a href="https://maps.gsi.go.jp/development/ichiran.html" target="_blank" rel="noopener">地理院タイル</a>｜交通：大分県・CC BY 4.0'}).addTo(map);
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
  else $('#map-legend').innerHTML='<b>出発するバスの本数／日</b><span><i style="--dot:#a3adb4"></i>0 <i style="--dot:#d6a23e"></i>1–9 <i style="--dot:#139c91"></i>10–29 <i style="--dot:#1f539b"></i>30以上</span>';
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
  $('#map-detail').innerHTML=mode==='reach'?`<div class="detail-label">直通60分の到達先</div><h3>${esc(geo.origins[Number($('#reach-origin').value)].name)}から</h3><p class="muted">点を選ぶと、その乗り場の情報が分かります。</p><div class="data-scope"><b>到達停留所名の参考集約</b><p>同名の乗り場をまとめた集計です。同名別地点の混同が残ります。</p><p style="margin-top:14px">背景の線は当日の路線形状です。個々の到達経路を示すものではありません。</p></div>`:`<div class="detail-hint"><div class="hint-icon" aria-hidden="true"><svg viewBox="0 0 32 32"><path d="M24 13c0 6-8 15-8 15S8 19 8 13a8 8 0 0 1 16 0Z"/><circle cx="16" cy="13" r="3"/></svg></div><h3>停留所を選んでみましょう</h3><p>地図の丸を押すと、曜日ごとの本数が分かります。停留所名でも検索できます。</p></div><div class="data-scope"><b>対象データ全体の片道便</b>${f==='all'?'公開16データ':esc(feedName(Number(f)))}<div class="weekday-bars">${['火','土','日'].map((label,i)=>`<div class="weekday-row ${i===d?'current':''}"><span>${label}</span><div class="weekday-track"><i style="width:${trips[i]/max*100}%"></i></div><b>${fmt(trips[i])}</b></div>`).join('')}</div><p>県境外も含む運行予定です。地図内の便数・乗客数ではありません。</p></div>`;
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
  $('#map-detail').innerHTML=`<div class="detail-label">選択した乗り場</div><h3>${esc(s.name)}</h3><p class="muted">${esc(feedName(s.feedIndex))}</p><div class="detail-stats">${['火','土','日'].map((d,i)=>`<div class="${i===day()?'current':''}">9/${[8,12,13][i]} ${d}<b>${fmt(s.departures[i])}</b>本／日</div>`).join('')}</div><p class="muted">${s.departures[day()]===0?'当日の通常乗車可能な出発が0。地域の交通手段がないという意味ではありません。':'この乗り場から通常乗車できる出発数です。利用人数ではありません。'}</p><details><summary>登録路線と出典</summary><div class="details-content"><p class="muted">登録路線のうち当日運行あり</p><p>${routes.length?routes.map(r=>esc(r.name)).join('<br>'):'該当する登録路線なし'}</p><p class="muted">路線の登録関係から表示。各便の停車は時刻表を確認してください。</p>${ext(f.sourceUrl,'公開データ・出典')}</div></details><button class="quiet-button detail-clear" data-clear-stop>選択を解除</button>`;
}
function renderStopTable(){
  const q=$('#stop-search').value.trim().toLowerCase(),filtered=visibleStops.filter(s=>q?s.name.toLowerCase().includes(q):map.getBounds().contains([s.lat,s.lon])).sort((a,b)=>b.departures[day()]-a.departures[day()]);const size=12,pages=Math.max(1,Math.ceil(filtered.length/size));stopPage=Math.min(Math.max(0,stopPage),pages-1);
  $('#stop-list-title').textContent=q?'「'+$('#stop-search').value.trim()+'」の検索結果':'地図の範囲にある停留所';
  $('#stop-list-description').textContent=q?'選択した交通データ'+(mode==='reach'?'・直通到達先':'全体')+'から検索。地図の範囲外も含みます。':'地図を動かすと一覧も変わります。本数の多い順に表示。';
  $('#stop-table').innerHTML=filtered.length?`<div class="stop-grid">${filtered.slice(stopPage*size,(stopPage+1)*size).map(s=>`<button class="stop-card" data-stop="${s.index}"><span class="stop-heading"><span>${esc(s.name)}</span><span class="stop-arrow" aria-hidden="true">↗</span></span><span class="stop-operator">${esc(feedName(s.feedIndex))} · 乗り場別</span><span class="day-counts">${['火','土','日'].map((label,i)=>`<span class="${i===day()?'current':''}">${label}<b>${fmt(s.departures[i])}</b>本</span>`).join('')}</span></button>`).join('')}</div>`:'<div class="notice">該当する停留所はありません。地図の範囲を広げるか、停留所名・表示条件を変更してください。</div>';
  $('#stop-page').textContent=`${fmt(filtered.length)}件 · ${stopPage+1} / ${pages}ページ`;$('#stop-prev').disabled=stopPage===0;$('#stop-next').disabled=stopPage===pages-1;
}
function renderRidership(){
  const departures=data.nakatsu_trunk_survey_departures;const total=departures.reduce((s,r)=>s+Number(r.boardings),0);
  $('#ridership-content').innerHTML=`<div class="metric-grid">${metric('停留所の公表乗降値','46観測','大分市40・杵築4・佐伯IC2')}${metric('中津の便別乗車調査',fmt(total)+'乗車','2024年4月22日・対象35便')}${metric('ひたはしり号の利用',fmt(85402),'2024/10〜2025/9・延べ利用人員')}</div><div class="notice">乗降合算は「乗る＋降りる」の数です。乗車だけの人数、同時に車内にいた人数、実人数とは異なります。異なる観測年・調査窓・決済範囲を合算していません。</div><div class="section-block"><h3>路線ごとの利用実績</h3>${table(['路線・事業者','観測期間','延べ利用人員','運送収入','出典'],data.route_actuals.map(r=>[`${esc(r.route)}<span class="cell-meta">${esc(r.operator)}</span>`,`${esc(r.period)}<span class="cell-meta">${esc(r.scope)}</span>`,fmt(r.passengers),r.revenue===null?'未掲載':fmt(r.revenue)+'円',ext(r.source_url)]))}</div><div class="section-block"><div class="subheading"><h3>停留所・停留所群の乗降</h3><div class="field-inline"><label for="stop-city">地域</label><select id="stop-city"><option value="all">すべて</option><option>大分市</option><option>杵築市</option><option>佐伯市</option></select></div></div><div id="observed-table"></div></div><details><summary>中日・中安線の便別乗車を見る（35便）</summary><div class="details-content"><p>1日調査です。2024年は同年度の調査群から解釈。現行GTFSの便とは結合していません。</p>${table(['路線','方向','発時刻','乗車人員'],departures.map(r=>[esc(r.route_name),esc(r.direction),esc(r.departure_time),fmt(r.boardings)]))}<p>${ext(departures[0].source_url,'中津市の調査資料')}</p></div></details>`;
  function observed(){const city=$('#stop-city').value;$('#observed-table').innerHTML=table(['停留所・地域','年度・曜日','公表値','単位・捕捉範囲','出典'],data.stop_actuals.filter(r=>city==='all'||r.municipality===city).map(r=>[`${esc(r.stop)}<span class="cell-meta">${esc(r.municipality)}</span>`,`${r.year}年度${r.day_type?'<span class="cell-meta">'+esc(({weekday:'平日',holiday:'休日'})[r.day_type]??r.day_type)+'</span>':''}`,fmt(r.value,Number.isInteger(r.value)?0:1),esc(r.unit),ext(r.source_url)]));}$('#stop-city').addEventListener('change',observed);observed();
}
function renderOD(){
  const s=data.od_summary,zones=[...new Set(data.nakatsu_taxi_od_2022.map(r=>r.origin))];
  const taxiRows=zones.map(o=>`<tr><th scope="row">${esc(o)}</th>${zones.map(d=>{const raw=data.nakatsu_taxi_od_2022.find(r=>r.origin===o&&r.destination===d).people;return raw===''?'<td class="empty" aria-label="非表示・0ではない">非表示</td>':`<td style="background:rgba(8,126,128,${.05+.48*Math.log1p(Number(raw))/Math.log1p(3219)});color:#183a4c">${fmt(raw)}</td>`}).join('')}</tr>`).join('');
  $('#od-content').innerHTML=`<div class="metric-grid">${metric('2013年・バスの推計移動数',fmt(s.pt_bus_trips),'5市1町居住者・平日・人口拡大集計')}${metric('2013年・バスのOD',fmt(s.pt_bus_od_pairs)+'組','目的別の行を起点・終点で集計')}${metric('2022年・中津タクシー',fmt(s.taxi_published_sum)+'人','5平日・公開14セルの合計')}</div><div class="notice amber">2013年のPT調査と2022年のタクシー調査です。2026年の全県需要ではありません。ゾーン名称辞書を取得できていないPTを、現在の地図や路線へ推測で結び付けていません。</div>${panel('中津市のタクシーOD',`<p class="scroll-hint">横にスクロールして、起点から終点への人数を確認できます →</p><div class="table-wrap"><table class="data-table heatmap"><thead><tr><th>起点 ↓ ／終点 →</th>${zones.map(z=>`<th scope="col">${esc(z)}</th>`).join('')}</tr></thead><tbody>${taxiRows}</tbody></table></div><p class="source-note">2022年7月25〜29日の5平日。公開14セル計3,638人。中津地域内3,219人は公開分の88.5%。「非表示」の22セルは、0ではありません。参加事業者の捕捉率は未確認です。</p>${ext(data.nakatsu_taxi_od_2022[0].source_url,'中津市地域公共交通計画・PDF42頁')}`,'方向ごとに集計。3人未満は図示しない公表資料から抽出。')}
  ${panel('2013年・バスODの内訳',`<div class="subheading"><p class="muted">移動数の多い順・上位30組を表示</p><label class="search"><span class="sr-only">起点または終点のゾーンコード</span><input id="od-search" type="search" placeholder="ゾーンコードを検索"></label></div><div id="pt-od-table"></div><p class="source-note">コード999999の意味は未確定。未掲載の組合せを0で補完していません。全件はExcelに収録。${ext('https://www.pref.oita.jp/uploaded/attachment/1016707.xlsx','県公開PT原本')}</p>`,'大分・別府・臼杵・豊後大野・由布・日出の5市1町に住む5歳以上。')}
  <details><summary>PT調査の全手段集計と母集団</summary><div class="details-content"><p>全手段1,832,489トリップ、11,061組。62,080行から再集計し、公式総計と一致。バスの構成比は約2.89%です。拡大推計であり、事業者が実際に記録した乗車数ではありません。</p>${table(['移動手段','拡大トリップ','全手段内の割合'],data.pt_modes.map(r=>[esc(r.mode),fmt(r.trips),fmt(r.share*100,2)+'%']))}<p>2013年10月1日・17日、11月7日・28日の平日調査。約3.1万世帯・6.4万人回答。観光客・県内全域の移動を代表しません。${ext('https://www.pref.oita.jp/site/oitatoshiken-sogo-koutsu/oitatoshiken-h25ptdata.html','大分県・調査の公開案内')}</p></div></details>`;
  function odTable(){const q=$('#od-search').value.trim();const a=data.bus_od.filter(r=>!q||r.origin_zone.includes(q)||r.destination_zone.includes(q));$('#pt-od-table').innerHTML=table(['起点コード','終点コード','推計トリップ','バス合計内の割合'],a.slice(0,30).map(r=>[esc(r.origin_zone),esc(r.destination_zone),fmt(r.published_trips),fmt(r.published_trips/s.pt_bus_trips*100,2)+'%']))+`<p class="source-note">該当 ${fmt(a.length)}組${a.length>30?'／先頭30組を表示':''}</p>`;}$('#od-search').addEventListener('input',odTable);odTable();
}
function history(){return data.hita_ridership_bus_year_2021_2025.filter(r=>r.route_name==='ひたはしり号計').sort((a,b)=>Number(a.bus_year)-Number(b.bus_year)).map(r=>Number(r.passenger_uses))}
function forecastChart(which){
  const hist=history(),projected=forecastSeries(hist)[which],years=[2021,2022,2023,2024,2025,2026,2027],values=[...hist,...projected];
  const mobile=window.innerWidth<=700,W=mobile?Math.max(260,window.innerWidth-68):800,H=270,left=mobile?32:62,right=mobile?20:48,top=28,bottom=50,min=60000,max=100000;
  const x=i=>left+i*(W-left-right)/6,y=v=>top+(max-v)/(max-min)*(H-top-bottom),line=a=>a.map(([i,v],j)=>`${j?'L':'M'}${x(i)},${y(v)}`).join(' ');
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="ひたはしり号の2021〜2025年実績と、2026〜2027年の${which==='flat'?'横ばい':'3点線形'}参考外挿。正確な人数は下の表で確認できます。"><rect x="${x(4)}" y="10" width="${W-x(4)-5}" height="220" fill="#fff6e7"/>${[60000,70000,80000,90000,100000].map(v=>`<line x1="${left}" y1="${y(v)}" x2="${W-right}" y2="${y(v)}" stroke="#dde7eb"/><text x="${left-8}" y="${y(v)+5}" text-anchor="end" class="chart-label">${v/10000}万</text>`).join('')}<path d="${line(hist.map((v,i)=>[i,v]))}" fill="none" stroke="#087e80" stroke-width="3"/><path d="${line([[4,hist[4]],[5,projected[0]],[6,projected[1]]])}" fill="none" stroke="#b87917" stroke-width="3" stroke-dasharray="7 5"/>${values.map((v,i)=>`<circle cx="${x(i)}" cy="${y(v)}" r="4" fill="${i<5?'#087e80':'#b87917'}"><title>${years[i]}年：${fmt(v)}人${i>4?'（仮定の試算）':'（公表実績）'}</title></circle>${!mobile||i===4||i===6?`<text class="chart-value" x="${x(i)}" y="${y(v)-14}" text-anchor="${mobile&&i===6?'end':'middle'}">${mobile?fmt(v/10000,2)+'万':fmt(v)}</text>`:''}<text class="chart-label" x="${x(i)}" y="${H-18}" text-anchor="middle">${mobile?String(years[i]).slice(2):years[i]}</text>`).join('')}</svg>`;
}
function renderForecast(){
  const names=[...new Set(data.north_east_trunk_actuals.map(r=>r.route_name))],f=forecastSeries(history());
  const rows=names.map(name=>{const a=data.north_east_trunk_actuals.filter(r=>r.route_name===name),q0=Number(a.find(r=>r.subsidy_fiscal_year_jp==='令和6年度').passenger_boardings),q=Number(a.find(r=>r.subsidy_fiscal_year_jp==='令和7年度').passenger_boardings),g=q/q0;return[esc(name),fmt(q0),fmt(q),fmt((g-1)*100,1)+'%',fmt(q),fmt(q*g),fmt(q*g*g)]});
  $('#forecast-content').innerHTML=`<div class="notice amber"><strong>ひたはしり号は2026年10月にAコース減便・Bコース延伸。</strong> 下の外挿は2025年のサービスが続くと仮定した比較基準です。改正後の利用者数を予測したものではありません。五馬線は2026年9月30日廃止予定のため、継続利用を外挿しません。${ext('https://www.city.hita.oita.jp/site/traffic/1962.html','日田市の改正案内')}</div>${panel('ひたはしり号の利用と参考外挿',`<div class="subheading"><div class="legend-row"><span><i></i>公表実績</span><span><i class="dashed"></i>条件付き参考値</span></div><div class="field-inline"><label for="forecast-method">方式</label><select id="forecast-method"><option value="flat">前年実績を据え置く</option><option value="linear">直近3点の直線を延長</option></select></div></div><div id="forecast-chart"></div><p class="chart-source">横軸：2021〜2027年。単位：延べ利用人員／バス年度（前年10月〜当年9月）。2027年は2026/10〜2027/9。${ext('https://www.city.hita.oita.jp/uploaded/attachment/9067.pdf','日田市・年度別利用実績')}</p>${table(['方式','2026年参考','2027年参考'],[['前年実績据置',fmt(f.flat[0]),fmt(f.flat[1])],['直近3点の線形',fmt(f.linear[0]),fmt(f.linear[1])]])}<details><summary>2021〜2025年の実績値を確認する</summary><div class="details-content">${table(['バス年度','公表実績・延べ利用人員'],history().map((v,i)=>[String(2021+i)+'年',fmt(v)+'人']))}</div></details>`)}
  <div class="two-col">${panel('過去2回の予測誤差',table(['方式','平均絶対誤差','平均絶対誤差率'],data.forecast.model_scores.map(r=>[r.model==='previous_observation'?'前年値据置':'直近3点の線形',fmt(r.MAE_passenger_uses,1)+'人',fmt(r.MAPE_pct,2)+'%']))+'<p class="source-note">2024年・2025年を順に隠して予測。この2回では据置の誤差が小さいものの、モデルの一般的優位性は確認できません。</p>')}${panel('この計算で分からないこと','<ul class="bullet-list"><li>減便・増便、運賃、人口変化それぞれの因果効果。</li><li>未利用者の外出断念や、供給変更による誘発需要。</li><li>将来値の統計的な予測区間。</li></ul><p class="source-note">2023年の再編等で条件が変化。R4人数は68,469と71,783の資料間不一致があり、本表は前者の系列を保持しています。</p>')}</div>
  <div class="section-block"><h3>県北東4路線の需要シナリオ</h3>${table(['路線','R6実績','R7実績','増減率','R8・R9据置','R8同率継続','R9同率継続'],rows)}<p class="source-note">単位：延べ利用人員／補助年度。2年度の増減率を繰り返す比較用仮定です。補助年度の厳密な暦日起終日は抽出表で未確認。新規誘発需要や政策効果としては使えません。${ext('https://wwwtb.mlit.go.jp/kyushu/content/000369184.pdf','九州運輸局・R7評価')}</p></div>`;
  $('#forecast-method').addEventListener('change',()=>$('#forecast-chart').innerHTML=forecastChart($('#forecast-method').value));$('#forecast-chart').innerHTML=forecastChart('flat');
}
function renderCost(){
  const us=data.finance.find(r=>r.service==='臼関線'),hi=data.finance.find(r=>r.service==='ひたはしり号全体');
  $('#cost-content').innerHTML=`<div class="metric-grid">${metric('臼関線・R7経常費用',fmt(us.cost/10000,1)+'万円','経常収益 '+fmt(us.revenue/10000,1)+'万円')}${metric('ひたはしり号・R4運行費',fmt(hi.cost)+'円','運賃収入 '+fmt(hi.revenue)+'円')}${metric('臼関線・経常収益÷費用',fmt(us.revenue/us.cost*100,2)+'%','会計上の収支比率。社会的B/Cではありません。')}</div><div class="notice">臼関線の利用5,391人は大分市内分。費用の対象範囲との一致を確認できず「費用÷人数」を計算していません。日田も費用と人数の厳密な期間が一致しないため、人当たり原価は空欄です。</div>
  <div class="two-col">${panel('臼関線：費用と負担の内訳',table(['項目','公表値・算定値'],[['経常費用','1,224.7万円'],['経常収益','191.5万円'],['国補助','233.1万円'],['差引の大分市負担','800.1万円']])+`<p class="source-note">市負担＝費用−収益−国補助。R7実績の同一段落から算定。経常収益は運賃収入だけと確認できていません。${ext(us.source_url,'大分市・協議会資料')}</p>`)}${panel('ひたはしり号：総費用と委託料',table(['項目','公表値・算定値'],[['運行経費',fmt(hi.cost)+'円'],['運賃収入',fmt(hi.revenue)+'円'],['差額の市運行委託料',fmt(hi.cost-hi.revenue)+'円'],['運賃収入÷運行経費',fmt(hi.revenue/hi.cost*100,4)+'%']])+`<p class="source-note">R4公表実績。委託料48,125,423円は運賃を差し引いた市支出で、総運行費と同じではありません。${ext(hi.source_url,'日田市・公表回答')}</p>`)}</div>
  <div class="section-block"><div class="subheading"><h3>地域別の公表財務</h3><div class="field-inline"><label for="cost-area">地域</label><select id="cost-area"><option value="all">すべて</option>${[...new Set(data.finance.map(r=>r.area))].map(a=>`<option>${esc(a)}</option>`).join('')}</select></div></div><div id="finance-table"></div></div><p class="source-note">別府H26は2013/10〜2014/9の同じ表の行内計算。共通費配賦の監査や2026年の原価ではありません。仙人田線は区間注記で費用/人を除外。原表の費用総計に17,711円の不整合があり、合計原価は使っていません。</p>`;
  function finances(){const a=$('#cost-area').value;const rows=data.finance.filter(r=>a==='all'||r.area===a);$('#finance-table').innerHTML=table(['地域・路線','期間／費用項目','収入','費用','収入÷費用','参考費用/人','出典'],rows.map(r=>[`${esc(r.area)}<br>${esc(r.service)}`,`${esc(r.period)}<span class="cell-meta">${esc(r.cost_label)}</span>`,fmt(r.revenue)+'円',fmt(r.cost)+'円',fmt(r.revenue/r.cost*100,1)+'%',r.cost_per_passenger===null?'未算定':fmt(r.cost_per_passenger,2)+'円',ext(r.source_url)]));}$('#cost-area').addEventListener('change',finances);finances();
}
function setupBC(){
  const brt=data.oita_brt_published_bc_2020;
  $('#bc-more').innerHTML=`<details><summary>計算式・評価に含めている範囲</summary><div class="details-content"><p><strong>年時間便益＝5,391移動 × 対象割合 × 短縮分 × ${fmt(TIME_VALUE,3)}円／人・分</strong></p><p>5年間同じ利用・効果・年額費用を仮定し、各年末の便益と費用を割り引きます。初期投資・残存価値なし。追加費用は賃借・運用・労務等を含む追加資源費です。同じ期間・年額なので割引率を変えても比率は変わらず、現在価値・純便益が変わります。</p><p>移動1回に1回だけ配賦し、乗換による重複を除く前提。既存利用者のほかの移動に悪化なし。誘発需要・事故・CO2・混雑・分配への影響は未評価で、影響ゼロと確認したものではありません。時間部分B/Cは社会全体B/Cの下限を保証しません。</p><p>時間価値は大分県2025年の給与304,379円÷（労働137.3時間×60）。所得接近の参考換算で、利用者の選好を実測した値ではありません。${ext('https://www.pref.oita.jp/uploaded/life/2331505_4681636_misc.pdf','県毎月勤労統計')}／${ext('https://www.mlit.go.jp/tec/hyouka/public/250918_shishin/shishin/shishin250918.pdf','国交省の評価指針')}</p><p>運賃・補助金を社会便益に加算しません。正式評価には変更案の実費見積り、時間差の実測、利用者の対象範囲、外部影響が必要です。</p></div></details><details><summary>2020年に大分県が公表したBRT試算（6案）</summary><div class="details-content"><p>当時の公表値を転記。便益・費用の現在価値総額が非掲載のため、独立再算定値ではありません。2026年の需要・価格・実施判断へ転用しません。</p>${table(['方面・経由','現況推定/日','BRT予測/日','公表費用','公表B/C','年収支'],brt.map(r=>[`${esc(r.area)}<span class="cell-meta">${esc(r.via)}</span>`,fmt(r.baseline_riders_estimate_per_day),fmt(r.brt_riders_forecast_per_day),fmt(r.published_cost_100m_yen,1)+'億円',fmt(r.published_bc,2),fmt(r.published_annual_financial_balance_million_yen)+'百万円']))}<p>${ext(brt[0].source_url,'大分県・2020年BRT調査')}</p></div></details>`;
  $('#bc-form').addEventListener('submit',e=>e.preventDefault());['#bc-share','#bc-minutes','#bc-cost','#bc-rate'].forEach(id=>$(id).addEventListener('input',updateBC));$('#bc-reset').addEventListener('click',()=>{$('#bc-share').value='50';$('#bc-minutes').value='5';$('#bc-cost').value='30';$('#bc-rate').value='0.04';updateBC()});updateBC();
}
function updateBC(){
  const share=Number($('#bc-share').value)/100,minutes=Number($('#bc-minutes').value),cost=$('#bc-cost').value.trim()===''?NaN:Number($('#bc-cost').value)*10000,rate=Number($('#bc-rate').value);$('#bc-share-value').textContent=fmt(share*100)+'%';$('#bc-minutes-value').textContent=fmt(minutes,Number.isInteger(minutes)?0:1)+'分';
  $('#bc-share').setAttribute('aria-valuetext',fmt(share*100)+'パーセントの移動');$('#bc-minutes').setAttribute('aria-valuetext',fmt(minutes,1)+'分短縮');
  const r=calculateBC({share,minutes,annualCost:cost,rate});
  if(!r){$('#bc-results').innerHTML='<div class="error">追加費用に0以上の数値を入力してください。</div>';$('#bc-mobile-summary').innerHTML='<span>費用便益の試算</span><b>費用を入力してください</b>';return}
  $('#bc-results').innerHTML=`<div class="bc-hero"><div class="bc-assumption">いまの条件：対象 ${fmt(share*100)}% · ${fmt(minutes,Number.isInteger(minutes)?0:1)}分短縮 · 年${fmt(cost/10000,1)}万円</div><div class="label">時間便益と釣り合う追加費用</div><div class="value">${fmt(r.annualBenefit/10000,2)}<small>万円／年</small></div><span class="bc-badge">時間便益のみのB/C <b>${r.bc===null?'算定不可':fmt(r.bc,2)}</b></span><p style="margin-top:14px">${r.bc===null?'追加費用が0のため比率は算定できません。':'B/C＝時間短縮の価値 ÷ 追加費用。'}<br>この仮定での費用上限です。正式な事業評価・見積額ではありません。</p></div><div class="bc-summary">${metric('5年分の便益現在価値',fmt(r.pvBenefit/10000,2)+'万円')}${metric('5年分の費用現在価値',fmt(r.pvCost/10000,2)+'万円')}${metric('部分純便益の現在価値',fmt(r.npv/10000,2)+'万円')}${metric('B/C＝1に必要な短縮',r.requiredMinutes===null?'算定不可':fmt(r.requiredMinutes,2)+'分')}</div><p class="source-note">現在の短縮時間で必要な対象割合：${r.requiredShare===null?'算定不可':fmt(r.requiredShare*100,1)+'%'}${r.requiredShare>1?'（100%を超えるため、この短縮時間では費用を賄えません）':''}。費用と効果を確認するための条件整理です。</p>`;
  $('#bc-mobile-summary').innerHTML=`<div><span>時間便益のみのB/C</span><strong>${r.bc===null?'—':fmt(r.bc,2)}</strong></div><div><span>釣り合う追加費用</span><br><b>${fmt(r.annualBenefit/10000,2)}万円／年</b></div>`;
}
function renderSources(){
  const titles={
  'https://www.pref.oita.jp/uploaded/attachment/1016707.xlsx':'大分県｜2013年PT調査・公開集計原本',
  'https://www.city-nakatsu.jp/doc/2023033000074/file_contents/2606_keikaku.pdf':'中津市｜地域公共交通計画・タクシーOD',
  'https://www.city.oita.oita.jp/o256/shisejoho/kekakuzaise/documents/2606_oitacityptplan_full.pdf':'大分市｜地域公共交通計画・乗降実績',
  'https://www.city.oita.oita.jp/o256/machizukuri/kotsu/kotukyougikai/documents/06_giji3.pdf':'大分市｜臼関線の利用・財務評価',
  'https://www.city.hita.oita.jp/uploaded/attachment/9067.pdf':'日田市｜年度別の利用実績',
  'https://www.city.hita.oita.jp/uploaded/attachment/9066.pdf':'日田市｜令和7年度の自己評価',
  'https://www.city.hita.oita.jp/uploaded/attachment/2682.pdf':'日田市｜ひたはしり号の運行費用',
  'https://www.city.hita.oita.jp/site/traffic/1962.html':'日田市｜ひたはしり号・2026年10月改正',
  'https://wwwtb.mlit.go.jp/kyushu/content/000369184.pdf':'九州運輸局｜令和7年度・幹線輸送評価',
  'https://wwwtb.mlit.go.jp/kyushu/content/000347224.pdf':'九州運輸局｜令和6年度・幹線輸送評価',
  'https://www.pref.oita.jp/uploaded/attachment/2087473.pdf':'大分県｜2020年BRT導入調査',
  'https://www.city.beppu.oita.jp/doc/seikatu/bouhan_anzen/koukyou_koutuu/koukyou_kassei/h26/01kyougikai/setsumei.pdf':'別府市｜平成26年度・生活バス財務',
  'https://www.city.usa.oita.jp/material/files/group/14/0116.pdf':'宇佐市｜地域公共交通計画・財務',
  'https://www.city.kitsuki.lg.jp/material/files/group/7/koutuukeikaku_dai7syou-urabyoushi.pdf':'杵築市｜公共交通計画・乗降調査',
  'https://www.city.saiki.oita.jp/kiji0038705/3_8705_up_qdq0npjl.pdf':'佐伯市｜公共交通計画・IC乗降指標',
  'https://www.city-nakatsu.jp/doc/2026021200036/file_contents/file_202632185157_2.pdf':'中津市｜公共交通調査資料・便別乗車',
  'https://www.pref.oita.jp/uploaded/life/2331505_4681636_misc.pdf':'大分県｜2025年毎月勤労統計・時間価値の換算元'};
  $('#sources-content').innerHTML=`<div class="notice">公開集計による算定版です。最新の全県OD、変更案の実費見積り、改善効果の実測は未取得。調査・契約・運行変更を実施したものではありません。</div>${panel('今回確認できること',table(['分析','根拠と範囲','未確定の点'],[['交通マップ','2026年9月の公開16 GTFS・予定供給','県内全交通の網羅、実際の運行・遅延'],['乗降・OD','地域・観測年ごとの公表集計','2026年全県OD、乗降合算の分離'],['需要の見通し','年度実績を据置・傾向延長','改正による因果効果、予測区間'],['財務・費用便益','公表財務と条件付き時間便益','最新費目原価、正式な全項目B/C']]))}
  <details open><summary>地図の定義と出典</summary><div class="details-content"><p>背景は${ext('https://maps.gsi.go.jp/development/ichiran.html','国土地理院の地理院タイル')}。交通データは${ext('https://odcs.bodik.jp/440001/2023/03/30/gtfs_bus/','大分県の公開GTFS')}を加工（${ext('https://creativecommons.org/licenses/by/4.0/deed.ja','CC BY 4.0')}）。</p><p>5,944乗り場、原GTFSの826形状を約15m許容幅で簡素化。推測で停留所間を直線接続していません。停留所の同名・同座標も事業者別IDのまま保持。0は有効期間内・収録済み乗り場で当日の通常乗車可能な出発が0。未収録の交通を0と判定しません。</p><p>曜日便数は当日有効な片道trip。カレンダー例外と24時超の時刻を反映。乗り場の出発数は通常乗車可能なstop_time。直通60分は徒歩・乗換・帰りの便・目的地の営業時間を含みません。</p></div></details>
  <details><summary>公開GTFS16件の有効期間と出典</summary><div class="details-content">${table(['公開データ','適用期間','火／土／日','出典'],geo.feeds.map(f=>[esc(f.name.replace('GTFSデータ','')),`${f.validFrom}〜${f.validTo}`,f.scheduledTrips.map(n=>fmt(n)).join(' / '),ext(f.sourceUrl)]))}</div></details>
  <div class="panel"><h3>主な一次資料</h3><ol class="sources-list">${Object.entries(titles).map(([url,title])=>`<li>${ext(url,title)}</li>`).join('')}</ol></div>
  <details><summary>正式な評価に進むための確認項目</summary><div class="details-content"><p>事業者から、同じ期間の便別乗降・公開可能な集計OD・IC以外の総利用・当時のGTFS対応表を受領。現状維持と変更案の営業・回送・待機・労務・車両・管理費を区別します。カードIDなど個人識別子は不要です。</p><p>利用者の時間差と他の利用者の悪化、予約不成立、外出断念、帰宅条件を実測。自治体の評価責任者が対象・比較案・上限費用を決め、事業者が運行可能性と費用を確認し、分析担当と独立確認者が再計算します。役割・費用負担は未合意です。</p><p>必要な移動が改善し、継続可能な運営・負担が成立した範囲で継続を判断。利用回数や部分B/Cだけでは決定しません。</p></div></details>`;
}
async function start(){
  route(location.hash.slice(1));window.addEventListener('hashchange',()=>route(location.hash.slice(1),true));
  try{const results=await Promise.all([fetch('data/analysis.json'),fetch('data/map-data.json')]);if(results.some(r=>!r.ok))throw new Error('分析データの読み込みに失敗しました。');[data,geo]=await Promise.all(results.map(r=>r.json()));
    renderRidership();renderOD();renderForecast();renderCost();setupBC();renderSources();setupMap();$('#loading').hidden=true;route(lastView);
  }catch(e){$('#loading').hidden=true;$('#error').hidden=false;$('#error').innerHTML=esc(e.message)+' <a href="downloads/oita-transport-report.pdf">PDF報告書で確認する</a>。';}
}
start();
