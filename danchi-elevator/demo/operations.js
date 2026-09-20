/* Shared presentation helpers. No dispatch, location tracking or booking rules. */
(function(){
  'use strict';
  const points={'stop-a':[33.1968,131.5718],'stop-b':[33.2024,131.5784],'stop-c':[33.2028,131.5652]};
  const terminal=r=>['completed','cancelled'].includes(r.status);
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const status={requested:'引受待ち',assigned:'迎車中',arrived:'到着・乗車待ち',onboard:'乗車中',completed:'降車完了',cancelled:'取消済み'};
  const vehicle=id=>({'vehicle-a1':'デモ車両 1','vehicle-a2':'デモ車両 2'}[id]||id||'未割当');
  const time=v=>new Date(v).toLocaleTimeString('ja-JP',{hour:'2-digit',minute:'2-digit',timeZone:'Asia/Tokyo'});
  const route=r=>`<div class="driver-selected-route"><b>${esc(r.origin_name)}</b><span aria-label="から">→</span><b>${esc(r.destination_name)}</b><strong>${r.passengers}名</strong><small>受付番号 ${esc(r.id.slice(-8))}</small></div>`;
  function find(text,stops){
    const q=text.normalize('NFKC').trim().replace(/[。！!？?]/g,'');
    if(/^(全て|すべて|全件|全部)(の依頼)?(を表示|を見せて)?$/.test(q))return {kind:'all'};
    if(/^(処理待ち|引受待ち|未引受|待っている依頼)(を表示|を見せて)?$/.test(q))return {kind:'requested'};
    if(/^(運行中|送迎中|運行確定)(の依頼)?(を表示|を見せて)?$/.test(q))return {kind:'running'};
    if(/^(履歴|完了|完了・取消)(を表示|を見せて)?$/.test(q))return {kind:'history'};
    const receipt=q.match(/^(?:受付番号\s*)?([a-f0-9-]{8,36})(?:の依頼)?$/i);
    if(receipt)return {kind:'receipt',value:receipt[1].toLowerCase()};
    const names=stops.flatMap(s=>[{id:s.id,name:s.name},...({'stop-a':['ちゅうおうひろば'],'stop-b':['駅前','ロータリー'],'stop-c':['ふれあい']}[s.id]||[]).map(name=>({id:s.id,name}))]).sort((a,b)=>b.name.length-a.name.length);
    const found=names.find(s=>q===s.name||q===s.name+'の依頼'||q===s.name+'を表示'||q===s.name+'の依頼を見せて');
    return found?{kind:'stop',value:found.id}:{kind:'unknown'};
  }
  function matches(r,filter){
    if(filter.kind==='stop')return r.origin_stop_id===filter.value||r.destination_stop_id===filter.value;
    if(filter.kind==='receipt')return r.id.toLowerCase().endsWith(filter.value);
    if(filter.kind==='requested')return r.status==='requested';
    if(filter.kind==='running')return ['assigned','arrived','onboard'].includes(r.status);
    if(filter.kind==='history')return terminal(r);
    return filter.kind==='all';
  }
  function say(id,text,kind='guide',choices=[]){
    const log=document.getElementById(id),row=document.createElement('div');row.className='ops-chat-row '+kind;
    const bubble=document.createElement('div');bubble.className='ops-bubble';bubble.textContent=text;row.append(bubble);
    const time=document.createElement('time');time.className='chat-time';time.dateTime=new Date().toISOString();time.textContent=new Date().toLocaleTimeString('ja-JP',{hour:'2-digit',minute:'2-digit'});row.append(time);
    if(choices.length){const group=document.createElement('div');group.className='ops-chat-choices';for(const item of choices){const b=document.createElement('button');b.type='button';b.textContent=item.label;b.dataset.opsRide=item.id;group.append(b);}row.append(group);}
    log.append(row);while(log.children.length>20)log.firstElementChild.remove();log.scrollTop=log.scrollHeight;
  }
  function mapView({id,errorId,onPick}){
    let map=null,line=null,key='',selectionKey='';const markers=new Map();
    const el=()=>document.getElementById(id),error=()=>document.getElementById(errorId);
    function fit(){if(map&&markers.size){map.invalidateSize();map.fitBounds([...markers.values()].map(m=>m.getLatLng()),{padding:[60,50],maxZoom:15,animate:false});}}
    function init(){
      if(map){requestAnimationFrame(()=>map.invalidateSize());return;}
      if(!window.L){error().hidden=false;return;}
      map=L.map(id,{scrollWheelZoom:false,zoomControl:false,minZoom:11,maxZoom:18,zoomAnimation:false,fadeAnimation:false});
      L.control.zoom({position:'bottomright',zoomInTitle:'地図を拡大',zoomOutTitle:'地図を縮小'}).addTo(map);
      const tiles=L.tileLayer('https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png',{maxZoom:18,attribution:'<a href="https://maps.gsi.go.jp/development/ichiran.html" target="_blank" rel="noopener noreferrer">地理院タイル</a>'}).addTo(map);
      tiles.on('tileerror',()=>{error().hidden=false;});
      tiles.on('load',()=>{const images=[...el().querySelectorAll('.leaflet-tile')];if(images.length&&images.every(i=>i.complete&&i.naturalWidth>0))error().hidden=true;});
      map.setView([33.1998,131.5718],14);
      if(window.ResizeObserver){let size='';new ResizeObserver(()=>{const next=el().clientWidth+'x'+el().clientHeight;if(el().clientWidth&&el().clientHeight&&next!==size){size=next;fit();}}).observe(el());}
    }
    function draw(stops,rides,selected){
      init();if(!map)return;
      const next=JSON.stringify(stops.map(s=>[s.id,s.name]));
      if(next!==key){key=next;markers.forEach(m=>m.remove());markers.clear();
        for(const stop of stops){if(!points[stop.id])continue;const b=document.createElement('button');b.type='button';b.setAttribute('aria-label','地図で'+stop.name+'の依頼を見る');const small=document.createElement('small'),label=document.createElement('span');label.textContent=stop.name.replace('ふれあいセンター','ふれあい\nセンター').replace('駅前ロータリー','駅前\nロータリー');b.append(small,label);b.addEventListener('click',()=>onPick(stop.id));
          const m=L.marker(points[stop.id],{icon:L.divIcon({className:'driver-map-pin',html:b,iconSize:[120,76],iconAnchor:[60,38]}),keyboard:false}).addTo(map);markers.set(stop.id,m);
        }fit();
      }
      for(const [stopId,m] of markers){const b=m.getElement().querySelector('button'),end=selected?.origin_stop_id===stopId?'pickup':selected?.destination_stop_id===stopId?'dropoff':'';b.dataset.end=end;
        const waiting=rides.filter(r=>r.status==='requested'&&r.origin_stop_id===stopId).length;
        b.querySelector('small').textContent=end==='pickup'?'乗車場所':end==='dropoff'?'降車場所':waiting?`引受待ち ${waiting}件`:'乗降場所';
      }
      const sk=selected?selected.origin_stop_id+':'+selected.destination_stop_id:'';
      if(sk!==selectionKey){selectionKey=sk;if(line){line.remove();line=null;}if(selected&&points[selected.origin_stop_id]&&points[selected.destination_stop_id])line=L.polyline([points[selected.origin_stop_id],points[selected.destination_stop_id]],{color:'#111111',weight:3,dashArray:'6 8',interactive:false}).addTo(map);}
    }
    return {draw,fit};
  }
  window.YokoOps={esc,status,terminal,vehicle,time,route,find,matches,say,mapView};
})();
