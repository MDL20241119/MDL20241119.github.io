import {$,esc,time,fmt} from './shared.mjs';

export function createMapRoute({map,layer,getHome,getTarget,onPick,onSearch,onClear,onSwap}){
  let result=null,direction='both',bounds=null;
  const setStatus=(message,isError=false)=>{const el=$('#map-route-status');el.textContent=message;el.classList.toggle('route-error',isError);};
  function sync(){
    $('#map-origin-label').textContent=getHome()?.name??'出発地を選ぶ';
    $('#map-destination-label').textContent=getTarget()?.name??'目的地を選ぶ';
    $('#map-swap').disabled=!getHome()||!getTarget();
    $('#map-conditions-summary').textContent=`${$('#date').value} ／ ${$('#departure').value}出発 → ${$('#activity-time').value}から${$('#dwell').value}分滞在 → ${$('#deadline').value}までに帰宅`;
  }
  function picking(which){
    for(const id of ['origin','destination'])$('#map-pick-'+id).setAttribute('aria-pressed',String(which===id));
    $('#map-pick-cancel').hidden=!which;
    if(which)setStatus((which==='origin'?'出発地':'目的地')+'にする地点を地図で押してください。施設の丸からも選べます。');
  }
  function busy(value){$('#map-search').disabled=value;$('#map-cancel').hidden=!value;$('#map-search').textContent=value?'ルートを検索中…':'往復ルートを検索 →';}
  function reset(){result=null;bounds=null;layer.clearLayers();$('#map-route-result').hidden=true;$('#map-route-directions').hidden=true;busy(false);sync();setStatus('出発地と目的地を選び、日時・徒歩条件を確認して検索してください。');}
  function draw(fit=false){
    layer.clearLayers();bounds=L.latLngBounds([]);
    for(const d of ['outbound','inbound']){
      if(direction!=='both'&&direction!==d)continue;
      const color=d==='outbound'?'#bd2476':'#00709c',name=d==='outbound'?'行き':'帰り';
      for(const [i,l]of (result?.[d]?.path??[]).entries()){
        if(l.mode==='walk'&&l.meters<1)continue;
        const geometry=l.geometry??{kind:l.mode==='walk'?'walk-estimate':'approximate',points:[[l.from.lat,l.from.lon],[l.to.lat,l.to.lon]]};
        const exact=geometry.kind==='gtfs-shape';
        const caption=l.mode==='walk'?'徒歩の概略線・道路経路ではありません':exact?'この便の公開走行経路（時刻表データ）':'この区間の走行経路は未確認・乗降地点のみ表示';
        const popup=`<b>${name} ${time(l.departure)} → ${time(l.arrival)}</b><p>${esc(l.mode==='bus'?l.routeName:'徒歩 約'+fmt(l.meters)+'m')}</p><p>${esc(l.from.name??'地点')} → ${esc(l.to.name??'地点')}</p><small>${caption}</small>`;
        if(exact||l.mode==='walk'){
          const line=L.polyline(geometry.points,{bubblingMouseEvents:false,color:l.mode==='walk'?'#65656e':color,weight:l.mode==='walk'?3:5,dashArray:exact?null:'3 7',opacity:.9}).addTo(layer).bindPopup(popup);
          line.routeLeg=d+'-'+i;bounds.extend(line.getBounds());
        }
        bounds.extend([l.from.lat,l.from.lon]);bounds.extend([l.to.lat,l.to.lon]);
        if(l.mode==='bus')for(const [p,t,action]of [[l.from,l.departure,'乗車'],[l.to,l.arrival,'降車']])L.circleMarker([p.lat,p.lon],{bubblingMouseEvents:false,radius:5,color,weight:2,fillColor:'#fff',fillOpacity:1}).addTo(layer).bindPopup(`<b>${name} ${time(t)} ${action}</b><p>${esc(p.name)}</p><small>${esc(l.routeName)}</small>`);
      }
    }
    if(fit&&bounds.isValid())map.fitBounds(bounds,{padding:[30,30],maxZoom:16});
    document.querySelectorAll('[data-route-direction]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.routeDirection===direction)));
  }
  function show(r,request,focusMap){
    result=r;direction='both';sync();
    const found=!!(r.outbound&&r.inbound),el=$('#map-route-result');el.hidden=false;
    const buses=['outbound','inbound'].flatMap(d=>r[d]?.path??[]).filter(l=>l.mode==='bus'),missing=buses.filter(l=>l.geometry?.kind!=='gtfs-shape').length;
    const geometryNote=missing?`バス${buses.length}区間のうち${missing}区間は形状を照合できず、乗降地点のみ表示しています。`:buses.length?'バスはこの便の公開走行経路を表示。徒歩は概略の点線です。':'徒歩のみの候補です。点線は距離の概算で、歩道の案内ではありません。';
    $('#map-route-directions').hidden=!found;
    el.innerHTML=found?`<div class="map-route-summary"><b>往復候補が見つかりました</b><span>行き ${time(r.outbound.path[0]?.departure)} → ${time(r.outbound.arrival)} ／ 帰り ${time(r.end)} → ${time(r.homeAt)}</span><small>往復の徒歩 約${fmt(r.walk)}m・運賃／利用条件は未確認</small></div><div class="map-leg-list">${['outbound','inbound'].map(d=>`<div><h3>${d==='outbound'?'行き':'帰り'}</h3>${r[d].path.filter(l=>l.mode==='bus'||l.meters>5).map(l=>`<p><b>${time(l.departure)} → ${time(l.arrival)} ${esc(l.mode==='bus'?l.routeName:'徒歩 約'+fmt(l.meters)+'m')}</b><span>${esc(l.from.name??'地点')} → ${esc(l.to.name??'地点')}</span></p>`).join('')}</div>`).join('')}</div><a href="#result">用事の時間・利用条件・根拠を見る ↓</a>`:`<b>この条件で往復候補は見つかりませんでした</b><p>${esc(r.reasons?.join(' / '))}</p><small>未収録の交通・別の日時は未評価です。公共交通で行けないと断定するものではありません。</small>`;
    draw(found);setStatus(found?geometryNote+' 行き・帰りを切り替えられます。':'出発時刻・滞在時間・徒歩上限・使う時刻表を確認してください。');
    if(focusMap)$('#people-map').scrollIntoView({behavior:'smooth',block:'start'});
  }
  for(const which of ['origin','destination'])$('#map-pick-'+which).onclick=()=>onPick(which);
  $('#map-pick-cancel').onclick=()=>onPick(null);
  $('#map-search').onclick=()=>onSearch();
  $('#map-cancel').onclick=()=>$('#cancel').click();
  $('#map-clear').onclick=()=>onClear();
  $('#map-swap').onclick=()=>onSwap();
  $('#map-route-fit').onclick=()=>draw(true);
  $('#map-edit-conditions').onclick=()=>{$('#journey-when').scrollIntoView({behavior:'smooth',block:'start'});$('#date').focus({preventScroll:true});};
  document.querySelectorAll('[data-route-direction]').forEach(b=>b.onclick=()=>{direction=b.dataset.routeDirection;draw(true);});
  return {sync,picking,busy,reset,show,setStatus};
}
