import {STATUS,MODES,esc,fmt,selectOperators,summarize,csvText} from './model.mjs';
import {setupStatistics,renderStatistics} from './statistics.mjs';
const $=s=>document.querySelector(s);
let data,rows=[],page=0,map,layers,mapSources,mapEpoch=0;
const PAGE_SIZE=15;
const link=(url,label)=>/^https?:\/\//.test(url??'')?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`:'';
const badge=r=>`<span class="op-status ${STATUS[r.status].className}">${STATUS[r.status].label}</span>`;
const statLink=(value,label)=>value?`<a href="${esc(value.url)}">${esc(value.period)} ${esc(value.label??label)} ↗</a><small>${esc(value.note)}</small>`:'未反映';
async function json(path){const response=await fetch(path+'?v=20260914-3');if(!response.ok)throw Error(path+' を取得できません（'+response.status+'）');return response.json();}
function filters(){return {operator:$('#operator-select').value,mode:$('#mode-select').value,status:$('#status-select').value,query:$('#operator-query').value.trim()};}
function fail(error){$('#operator-error').hidden=false;$('#operator-error').textContent='読み込み・表示が完了していません。'+error.message+'。未取得の件数は0とは扱いません。';}
function updateURL(){const url=new URL(location.href);url.search='';for(const [key,value] of Object.entries(filters()))if(value&&value!=='all')url.searchParams.set(key,value);if($('#stats-year').value!=='2024')url.searchParams.set('year',$('#stats-year').value);if($('#station-query').value.trim())url.searchParams.set('station',$('#station-query').value.trim());history.replaceState(null,'',url);}
function renderPriority(){
  $('#priority-operators').innerHTML=data.priorityGroups.map(group=>{const rs=selectOperators(data,{operator:group.id}),s=summarize(rs);return `<a class="priority-card" href="?operator=${group.id}#operator-statistics"><span class="op-status missing">時刻表・往復計算は未反映</span><h2>${esc(group.name)}</h2><b>${fmt(s.bus||s.stations)} <small>${s.bus?'停留所位置・2022年度':'駅グループ・2025年末'}</small></b><small>${s.bus?`${s.providers}社の原典表記を集約。現行の全停留所数ではありません。`:'原典の駅グループコードで集計。線路位置も反映。'}</small><small>${group.id==='nishitetsu-bus'?'グループの年間輸送実績・収支を反映':'県内駅別実績（公表分）・事業収支を反映'}</small><small>リアルタイム：未反映</small><strong>実績・収支と位置を見る →</strong></a>`;}).join('');
}
function render(){
  rows=selectOperators(data,filters());page=Math.min(page,Math.max(0,Math.ceil(rows.length/PAGE_SIZE)-1));const s=summarize(rows);
  $('#operator-summary').innerHTML=[['掲載主体',s.providers,'県内総数ではありません'],['時刻表反映',s.timetable,'収録ファイルの範囲のみ'],['バス停位置',s.bus,'2022年度の位置資料'],['鉄道駅グループ',s.stations,'2025年末の原典コード']].map(([title,n,note])=>`<div><dt>${title}</dt><dd>${fmt(n)} <small>${note}</small></dd></div>`).join('');
  $('#operator-count').textContent=`${fmt(rows.length)}主体を表示。自治体・地域交通の公表主体を含みます。`;
  $('#operator-table-body').innerHTML=rows.slice(page*PAGE_SIZE,(page+1)*PAGE_SIZE).map(r=>`<tr><td><button data-operator="${r.id}">${esc(r.name)}</button><small>${MODES[r.mode]}</small></td><td>${badge(r)}<small>${r.timetable?esc(r.timetable.note):esc(r.missingReason)}</small></td><td>${r.busIndices.length?fmt(r.busIndices.length)+'停留所（2022年度）<br>':''}${r.stationCount?fmt(r.stationCount)+'駅グループ（2025年末）<br>':''}${r.gtfsStopCount?fmt(r.gtfsStopCount)+'乗降地点（取得GTFS）':''}</td><td>${statLink(r.ridership,'乗車人員')}</td><td>${statLink(r.costs,'費用')}</td><td>未反映</td></tr>`).join('')||'<tr><td colspan="6">この条件で確認できる主体はありません。県内に事業者が存在しないという意味ではありません。</td></tr>';
  $('#operator-page').textContent=`${rows.length?page+1:0} / ${Math.ceil(rows.length/PAGE_SIZE)}ページ`;$('#operator-prev').disabled=page===0;$('#operator-next').disabled=(page+1)*PAGE_SIZE>=rows.length;
  renderDetail();renderStatistics(rows);updateURL();drawMap().catch(fail);
}
function renderDetail(){
  const target=$('#operator-select').value;if(target==='all'){$('#operator-detail').hidden=true;return;}
  const rs=selectOperators(data,{operator:target}),group=data.priorityGroups.find(g=>g.id===target);
  if(!rs.length){$('#operator-detail').hidden=true;return;}$('#operator-detail').hidden=false;
  const fids=[...new Set(rs.flatMap(r=>r.feedIds))],fs=data.feeds.filter(f=>fids.includes(f.id)),routeNames=[...new Set(rs.flatMap(r=>r.routes))].sort();
  $('#operator-detail').innerHTML=`<h2>${esc(group?.name??rs[0].name)}</h2>${rs.map(r=>`<p><strong>${esc(r.name)}</strong> ${badge(r)}<br>${esc(r.missingReason??r.timetable.note)}<br>${link(r.officialUrl,'公式案内')}${link(r.officialTimetableUrl,'公式の時刻表を確認')}${link(r.acquisitionSource,'取得元候補（未反映）')}</p>`).join('')}<p><strong>公式サイトへのリンクは、当サイトの分析へのデータ反映を意味しません。</strong></p><h3>出典と対象期間</h3>${rs.some(r=>r.busIndices.length)?`<p>${link(data.sources.bus.url,'国土数値情報・バス停留所')} / 2022年度。廃止・移設・会社変更を含む現況の確認は未完了。</p>`:''}${rs.some(r=>r.stationIndices.length)?`<p>${link(data.sources.rail.url,'国土数値情報・鉄道')} / 2025年12月31日。駅・線路位置のみ。時刻・停車便・運賃・遅延は未反映。</p>`:''}${fs.length?`<ul>${fs.map(f=>`<li>${esc(f.name)} — ${esc(f.validFrom)}〜${esc(f.validTo)} / ${f.dataStatus==='current'?'基準日の検証済み・収録分のみ':'期限外または検証エラー・計算に不使用'}<br>${link(f.sourceUrl,'公開元')}${link(f.licenseUrl,f.license)}</li>`).join('')}</ul>`:'<p>有効な時刻表ファイル：未反映。往復判定・便数・交通空白判定の計算対象に含みません。</p>'}<details><summary>原典の路線名 ${fmt(routeNames.length)}件を確認</summary><p>事業者内の表記を重複除去。現在運行中の路線数ではありません。位置資料とGTFSの名称は未統合です。</p><ul class="op-route-list">${routeNames.map(n=>`<li>${esc(n)}</li>`).join('')}</ul></details>`;
}
function pointOf(feature){const cs=feature.geometry.coordinates;if(feature.geometry.type==='Point')return cs;const pts=cs.flat(feature.geometry.type==='MultiLineString'?1:0);return pts[Math.floor(pts.length/2)];}
async function drawMap(){
  const epoch=++mapEpoch;$('#operator-map-status').textContent='収録した位置データを読み込んでいます…';
  if(!mapSources)mapSources=Promise.all(['data/bus-stop-inventory.geojson','data/rail.json','data/map-data.json'].map(json)).catch(e=>{mapSources=null;throw e;});
  const [bus,rail,geo]=await mapSources;if(epoch!==mapEpoch)return;
  if(!window.L)throw Error('地図ライブラリが読み込まれていません');
  if(!map){map=L.map('operator-map',{preferCanvas:true,scrollWheelZoom:false,minZoom:5}).setView([33.6,130.6],9);const tile=L.tileLayer('https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png',{maxNativeZoom:18,maxZoom:18,attribution:'背景：地理院タイル｜国土数値情報・各GTFS公開元'}).addTo(map);tile.on('tileerror',()=>{$('#operator-tile-warning').hidden=false});tile.on('tileload',()=>{$('#operator-tile-warning').hidden=true});layers=L.featureGroup().addTo(map);}
  layers.clearLayers();
  const dot=(coords,label,body,color)=>L.circleMarker([coords[1],coords[0]],{radius:4,color,weight:.6,fillOpacity:.75}).bindTooltip(esc(label)).bindPopup(`<b>${esc(label)}</b><br>${body}`,{maxWidth:300}).addTo(layers);
  const wantedRoutes=new Map();
  for(const r of rows){
    for(const i of r.routeIndices)wantedRoutes.set(i,r);
    for(const i of r.busIndices){const f=bus.features[i],p=f.properties;dot(f.geometry.coordinates,p.P11_001,`${esc(r.name)}<br>停留所位置資料：2022年度<br><strong>この位置資料の運行本数・現況は未確認</strong><br>${esc(p.P11_003_01)}`,'#a46b39');}
    const seen=new Set();for(const i of r.stationIndices){const f=rail.stations.features[i],p=f.properties;if(seen.has(p.N02_005g))continue;seen.add(p.N02_005g);dot(pointOf(f),p.N02_005,`${esc(r.name)} / ${esc(p.N02_003)}<br>駅位置：2025年12月31日<br><strong>時刻表・往復計算は未反映</strong>`,'#2857a0');}
    if(r.lineIndices.length)L.geoJSON({type:'FeatureCollection',features:r.lineIndices.map(i=>rail.lines.features[i])},{style:{color:'#2857a0',weight:2,opacity:.55},interactive:false}).addTo(layers);
  }
  for(const s of geo.stops){const f=geo.feeds[s.feedIndex],owners=[...new Set(s.routes.map(i=>wantedRoutes.get(i)).filter(Boolean))];if(!owners.length)continue;dot([s.lon,s.lat],s.name,`${esc(owners.map(r=>r.name).join('・'))}<br>${esc(f.name)}<br>${s.inFukuoka===false?'県外の接続区間<br>':''}${s.routes.some(i=>wantedRoutes.has(i)&&(s.routeDepartures?.[i]?.[0]??null)===null)?'有効期間外・便数未確認':'基準日の選択事業者の出発：'+fmt(s.routes.filter(i=>wantedRoutes.has(i)).reduce((n,i)=>n+(s.routeDepartures[i][0]??0),0))+'便'}（乗客数ではありません）。`,'#227554');}
  for(const s of geo.shapes)if(s.routeIndices.some(i=>wantedRoutes.has(i)))L.polyline(s.coordinates,{color:'#227554',weight:1.4,opacity:.4,interactive:false}).addTo(layers);
  const b=layers.getBounds();if(b.isValid())map.fitBounds(b,{padding:[20,20],maxZoom:13});else map.setView([33.6,130.6],9);
  const n=summarize(rows);$('#operator-map-status').textContent=`表示：${fmt(rows.length)}主体／バス停位置資料 ${fmt(n.bus)}点／駅グループ ${fmt(n.stations)}件／取得GTFSの乗降地点 ${fmt(n.stops)}点（県外区間・共同地点の各社計上を含む）。位置資料とGTFSには重複があります。`;
}
function exportCSV(){const columns=['事業者・公表主体','交通種別','時刻表反映状況','未反映理由・収録範囲','バス停位置2022年度','駅グループ2025年末','GTFS乗降地点','乗降実績','費用','リアルタイム','確認日','名簿網羅','出典'];const values=rows.map(r=>[r.name,MODES[r.mode],STATUS[r.status].label,r.missingReason??r.timetable.note,r.busIndices.length||'',r.stationCount||'',r.gtfsStopCount||'',r.ridership?.period??'未反映',r.costs?.period??'未反映','未反映',data.checkedAt,'県内全事業者は未網羅',[...(r.busIndices.length?[data.sources.bus.url]:[]),...(r.stationCount?[data.sources.rail.url]:[]),...data.feeds.filter(f=>r.feedIds.includes(f.id)).map(f=>f.sourceUrl)].join(' | ')]);const url=URL.createObjectURL(new Blob([csvText([columns,...values])],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='fukuoka-operator-coverage.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
async function start(){
  data=await json('data/operators.json');if(data.schemaVersion!==1||!Array.isArray(data.operators)||data.coverageComplete!==false)throw Error('事業者データの形式を確認してください');
  $('#operator-select').innerHTML='<option value="all">すべての掲載主体</option><optgroup label="主要3事業者">'+data.priorityGroups.map(g=>`<option value="${g.id}">${esc(g.name)}</option>`).join('')+'</optgroup><optgroup label="事業者・公表主体">'+data.operators.map(r=>`<option value="${r.id}">${esc(r.name)}（${MODES[r.mode]}）</option>`).join('')+'</optgroup>';
  const params=new URLSearchParams(location.search);for(const [key,id] of [['operator','operator-select'],['mode','mode-select'],['status','status-select']])if([...$('#'+id).options].some(o=>o.value===params.get(key)))$('#'+id).value=params.get(key);$('#operator-query').value=params.get('query')??'';
  $('#operator-gaps').innerHTML=data.missingCategories.map(g=>`<article><h3>${esc(g.name)}</h3><strong>${esc(g.status)}</strong><p>${esc(g.reason)}</p></article>`).join('');
  $('#operator-scope').textContent=data.scope+' '+data.agencyNote;
  await setupStatistics({json,onChange:updateURL});renderPriority();render();$('#operator-loading').hidden=true;
  for(const id of ['operator-select','mode-select','status-select'])$('#'+id).addEventListener('change',()=>{page=0;render()});$('#operator-query').addEventListener('input',()=>{page=0;render()});
  $('#operator-reset').addEventListener('click',()=>{for(const id of ['operator-select','mode-select','status-select'])$('#'+id).value='all';$('#operator-query').value='';$('#stats-year').value='2024';$('#station-query').value='';page=0;render()});
  $('#operator-table-body').addEventListener('click',e=>{const button=e.target.closest('[data-operator]');if(!button)return;$('#operator-select').value=button.dataset.operator;$('#operator-query').value='';page=0;render();$('#operator-map-section').scrollIntoView({block:'start'});});
  $('#operator-prev').addEventListener('click',()=>{page--;render()});$('#operator-next').addEventListener('click',()=>{page++;render()});$('#operator-export').addEventListener('click',exportCSV);
  $('#share-catalog').addEventListener('click',async()=>{updateURL();try{await navigator.clipboard.writeText(location.href);$('#share-catalog').textContent='コピーしました';}catch{window.prompt('このURLで表示条件を共有できます。',location.href);}});
}
start().catch(fail);
