import {cityAt,normalizeCategory,pointInGeometry,validPoint} from './model.mjs';
import {distance} from '../lab/gtfs.mjs';

export const DEFAULT_CITY='44201';
export const ROLES={
 city:{kicker:'自治体の方へ',title:'移動に困る地区を探す',intro:'気になる場所を地図で押すと、駅やバス停への距離がわかります。',pin:'主な駅',scope:'距離は直線の目安です。鉄道は位置のみで、時刻・乗継は未判定です。'},
 operator:{kicker:'交通事業者の方へ',title:'便を見直す場所を見つける',intro:'路線や駅の周辺を見て、気になる停留所を選び、実際の乗降とダイヤを確認します。',pin:'主な駅',scope:'地図だけでは需要や利用者数はわかりません。実績は集計CSVで確認し、未収録をゼロと扱いません。'},
 resident:{kicker:'地元住民の方へ',title:'用事を済ませて、帰れる？',intro:'病院や買物先を地図で選び、行きと帰りの候補を確認します。',pin:'生活施設の一部',scope:'往復検索は収録したバスの時刻表が対象です。JRの時刻・乗継、運休や施設の受付は未統合です。'},
 tourist:{kicker:'観光客の方へ',title:'クルマなしで、どう巡る？',intro:'行きたい観光地の近くにある交通の地点を選び、周遊マップで帰りも確認します。',pin:'観光地近くの停留所',scope:'地図の点はアクセスを調べる基準点です。運行・予約・営業日は公式情報で確認してください。'}
};

// Access points retained from the existing tourism atlas as an offline fallback.
// Source: ../oita-tourism/data/tourism.json (BODIK public GTFS).
const touristFallback=[
 {id:'oita-station',areaCode:'44201',name:'大分駅前',lat:33.2338196,lon:131.6072061},
 {id:'oita-takasaki',areaCode:'44201',name:'高崎山・うみたまご（高崎山バス停）',lat:33.2591732,lon:131.5331382},
 {id:'beppu-jigoku',areaCode:'44202',name:'別府地獄めぐり（海地獄前）',lat:33.314967,lon:131.4707421},
 {id:'yufu-station',areaCode:'44213',name:'由布院駅前',lat:33.2628842,lon:131.3555834},
 {id:'hiji-harmony',areaCode:'44341',name:'ハーモニーランド（バス停）',lat:33.3993532,lon:131.5464794}
];
const nearbyCodes=new Set(['44201','44202','44206','44208','44212','44213','44341']);
export function roleLinks(role,city=DEFAULT_CITY,cross=false,pick=null){
  const area=/^44\d{3}$/.test(city)?city:DEFAULT_CITY;
  const near='?city='+area;
  const journey=new URLSearchParams({city:area,cross:cross?'1':'0'});
  if(role==='resident'&&pick?.id)journey.set('destination',pick.id);
  const path='journey.html?'+journey+'#'+(pick?.id?'people-map':'area-entry');
  const tourism=new URLSearchParams({from:'oita-station'});
  if(role==='tourist'&&pick?.id)tourism.set('place',pick.id);
  else if(area===DEFAULT_CITY)tourism.set('place','oita-takasaki');
  return ({
    city:[['時間帯別の交通空白を見る','atlas.html'+near+'#atlas-time-gaps'],['目的地まで行ける地区を比べる','atlas.html?view=detail&city='+area+'#city-form']],
    operator:[['乗降・ODの実績を確かめる','ridership.html#ridership-input'],['増便・ダイヤ調整を比べる','lab.html#design']],
    resident:[[pick?'行き帰りの条件を入れる':'出発地を選んで往復を調べる',path],['施設の受付・利用条件も確認','accessibility.html']],
    tourist:[['観光地の行き方・帰り方を調べる','../oita-tourism/?'+tourism+'#access'],['出発地からバスの往復を調べる','journey.html?city='+area+'&cross=1#area-entry']]
  })[role]??[];
}
const $=s=>document.querySelector(s);
async function fetchHere(path){
  const r=await fetch(new URL('../'+path,import.meta.url));
  if(!r.ok)throw Error(path);
  return r.json();
}
function nearest(point,rows){
  let found=null;
  for(const entry of rows){const meters=distance(point,entry);if(Number.isFinite(meters)&&(!found||meters<found.meters))found={...entry,meters};}
  return found;
}
function link(el,text,href,arrow){el.href=href;const mark=document.createElement('span');mark.textContent=arrow;mark.setAttribute('aria-hidden','true');el.replaceChildren(document.createTextNode(text+' '),mark);}
function routeLabel(p){return p.mode==='rail'?'鉄道駅':p.mode==='tourist'?'観光アクセス地点':'施設';}
async function start(){
  if(!globalThis.L&&document.readyState!=='complete')await new Promise(resolve=>window.addEventListener('load',resolve,{once:true}));
  if(!globalThis.L)throw Error('map');
  const q=new URLSearchParams(location.search);
  let city=DEFAULT_CITY, role=Object.hasOwn(ROLES,q.get('role'))?q.get('role'):'city', filter='all', selected=null, features=[], stations=[], railLines=[], busLines=[], stops=[], facilities=[], tourist=touristFallback, degraded=false, live=false;
  $('#cross').checked=q.get('cross')==='1';
  const map=L.map('audience-map',{preferCanvas:true,scrollWheelZoom:false,zoomSnap:.5}).setView([33.223,131.623],11);
  L.tileLayer('https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png',{maxZoom:18,attribution:'<a href="https://maps.gsi.go.jp/development/ichiran.html">地理院タイル</a>'}).addTo(map);
  const boundaries=L.layerGroup().addTo(map), lines=L.layerGroup().addTo(map), markers=L.layerGroup().addTo(map), focus=L.layerGroup().addTo(map);
  const cityBounds=new Map();
  const areaCode=p=>String(p.municipalityCode??p.areaCode??cityAt(p,features.filter(f=>cityBounds.get(f.properties.code)?.contains([p.lat,p.lon])))?.code??'');
  const cross=()=>$('#cross').checked;
  const cityName=()=>features.find(f=>f.properties.code===city)?.properties.name??'大分市';
  const allowed=p=>{
    if(cross())return true;
    if(p.municipalityCode!=null||p.areaCode!=null)return areaCode(p)===city;
    const area=features.find(f=>f.properties.code===city);
    return !!area&&cityBounds.get(city)?.contains([p.lat,p.lon])&&pointInGeometry(p,area.geometry);
  };
  const toView=p=>L.latLng(p.lat,p.lon);
  function paintBounds(){
    boundaries.clearLayers();
    const f=features.find(x=>x.properties.code===city);
    if(!f)return;
    L.geoJSON(f,{interactive:false,style:{color:'#30675c',dashArray:'5 4',weight:1.5,opacity:.75,fillOpacity:.025}}).addTo(boundaries);
  }
  function fit(){
    const f=features.find(x=>x.properties.code===city);
    if(!f)return;
    const bounds=L.latLngBounds(cityBounds.get(city).getSouthWest(),cityBounds.get(city).getNorthEast());
    if(cross()){
      if(city===DEFAULT_CITY){for(const c of features.filter(g=>nearbyCodes.has(g.properties.code)))bounds.extend(cityBounds.get(c.properties.code));}
    }
    map.fitBounds(cross()&&city!==DEFAULT_CITY?bounds.pad(.25):bounds,{padding:[10,10],animate:false,maxZoom:13});
  }
  function renderCopy(){
    const copy=ROLES[role];
    for(const [id,key] of [['#role-kicker','kicker'],['#action-title','title'],['#role-intro','intro'],['#key-pin','pin'],['#role-scope','scope']])$(id).textContent=copy[key];
    for(const b of document.querySelectorAll('[data-role]'))b.setAttribute('aria-pressed',String(b.dataset.role===role));
    const [primary,secondary]=roleLinks(role,city,cross(),['facility','tourist'].includes(selected?.mode)?selected:null);
    link($('#primary-link'),...primary,'→');link($('#secondary-link'),...secondary,'↗');
    $('#audience-map').setAttribute('aria-label',cityName()+(cross()?'と周辺':'')+'の交通地図');
  }
  function status(){
    $('#map-status').textContent=(live?cityName()+(cross()?'と周辺':'')+'を表示中。地図を押すと近くの駅・バス停がわかります。':'地図データを読み込んでいます。')+(degraded?' 一部データを表示できません。':'');
  }
  function describe(){
    const box=$('#selection');box.hidden=!selected;box.replaceChildren();
    if(!selected)return;
    const title=document.createElement('strong');title.textContent=selected.name;box.append(title);
    const p=document.createElement('p');
    const rail=nearest(selected,stations),bus=nearest(selected,stops);
    const section=s=>s?s.name+' 約'+(Math.round(s.meters/10)*10).toLocaleString('ja-JP')+'m':live?'収録なし':'読み込み中';
    p.textContent=(selected.mode?routeLabel(selected)+' ｜ ':'')+'バス停 '+section(bus)+' ／ 鉄道駅 '+section(rail)+'（直線）';box.append(p);
    if(role==='operator'&&bus?.operator){const ag=document.createElement('p');ag.textContent='最寄り停留所の収録事業者：'+bus.operator;box.append(ag);}
  }
  function choose(p,{recenter=false,popup=false}={}){
    selected=p;
    focus.clearLayers();
    if(!p){$('#point-picker').value='';describe();renderCopy();return;}
    $('#point-picker').value=p.key??'';
    if(recenter)map.setView(toView(p),Math.max(map.getZoom(),13),{animate:false});
    describe();renderCopy();
    if(popup){
      const tip=document.createElement('div');tip.className='map-pop';
      for(const child of $('#selection').children)tip.append(child.cloneNode(true));
      if(p.mode==='facility'||p.mode==='tourist'){
        const action=document.createElement('a');action.className='map-pop-link';
        link(action,...roleLinks(role,city,cross(),p)[0],'→');tip.append(action);
      }
      L.circleMarker(toView(p),{radius:9,color:'#135243',weight:3,fill:false,interactive:false}).addTo(focus).bindPopup(tip,{maxWidth:230}).openPopup();
    }
  }
  function points(){
    if(role==='resident')return facilities.filter(allowed).filter(p=>filter==='all'||normalizeCategory(p.category)===filter).map(p=>({...p,mode:'facility',key:'facility:'+p.id}));
    if(role==='tourist')return tourist.filter(p=>allowed(p)).map(p=>({...p,mode:'tourist',key:'tourist:'+p.id}));
    if(role==='operator'){
      const inView=stops.filter(allowed).filter(p=>p.name.includes(filter==='all'?'':filter));
      const core=[...new Map(inView.map(p=>[p.name,p])).values()];
      const hubs=core.filter(p=>/(駅前|大分駅|鶴崎駅|大在駅|坂ノ市駅|賀来駅|中判田駅|西大分|中央通り|バスセンター|ターミナル)/.test(p.name));
      const top=(hubs.length?hubs:core).slice(0,24);
      return top.map(p=>({...p,mode:null,key:'bus:'+p.id+':'+p.operator}));
    }
    return stations.filter(allowed).map(p=>({...p,mode:'rail',key:'station:'+p.id}));
  }
  function paintPoints(){
    markers.clearLayers();
    const s=$('#point-picker'), rows=points(), mapRows=role==='resident'&&cross()?rows.slice(0,180):rows, head=new Option(rows.length?'一覧から選ぶ':'この範囲に収録地点なし','');
    head.disabled=true;s.replaceChildren(head);
    const byKey=new Map(rows.map(x=>[x.key,x]));
    for(const p of rows)s.add(new Option(p.name,p.key));
    s.disabled=!rows.length;
    s.onchange=()=>{const p=byKey.get(s.value);if(p)choose(p,{recenter:true,popup:true});};
    if(selected?.key&&byKey.has(selected.key))s.value=selected.key;
    else if(selected?.key)choose(null);
    for(const p of mapRows){
      const marker=L.marker(toView(p),{icon:L.divIcon({className:'marker-dot',iconSize:[10,10]}),keyboard:true,title:p.name,alt:p.name,riseOnHover:true});
      marker.on('click',()=>choose(p,{popup:true})).addTo(markers);
      marker.getElement()?.setAttribute('aria-label',p.name);
    }
    $('#picks').hidden=false;
    $('#pick-legend').textContent=role==='resident'?'用事の種類で絞る':role==='tourist'?'観光のアクセス地点':role==='operator'?'主な乗降拠点':'主な鉄道駅';
    $('#key-pin').textContent=role==='operator'?'主な乗降拠点':ROLES[role].pin;
  }
  function paintFilters(){
    const wrap=$('#filters');wrap.replaceChildren();
    if(role!=='resident')return;
    for(const [key,label] of [['all','すべて'],['hospital','通院'],['shopping','買物'],['civic','公共施設']]){
      const b=document.createElement('button');b.type='button';b.textContent=label;b.dataset.category=key;b.setAttribute('aria-pressed',String(filter===key));
      b.onclick=()=>{filter=key;paintFilters();paintPoints();$('#filters').querySelector('[data-category="'+key+'"]').focus();};
      wrap.append(b);
    }
  }
  function paintLines(){
    lines.clearLayers();
    const maxBounds=map.getBounds().pad(.25);
    for(const [data,color,weight] of [[busLines,'#0a776a',1.6],[railLines,'#654299',2.3]]){
      const inView=data.filter(r=>r.bounds.intersects(maxBounds));
      if(inView.length)L.polyline(inView.map(r=>r.points),{color,weight,opacity:.76,interactive:false}).addTo(lines);
    }
  }
  document.querySelectorAll('[data-role]').forEach(b=>b.onclick=()=>{
    if(role===b.dataset.role)return;
    role=b.dataset.role;filter='all';choose(null);paintFilters();paintPoints();status();
  });
  $('#area').onchange=()=>{city=$('#area').value;choose(null);paintBounds();fit();paintPoints();status();};
  $('#cross').onchange=()=>{if(!cross()&&selected&&!allowed(selected))choose(null);renderCopy();fit();paintPoints();status();};
  $('#fit').onclick=fit;
  map.on('moveend',paintLines);
  map.on('click',e=>choose({lat:e.latlng.lat,lon:e.latlng.lng,name:'地図で選んだ地点'},{popup:true}));
  renderCopy();
  const request=await Promise.allSettled([
    fetchHere('gaps/data/municipalities.geojson'),fetchHere('gaps/data/rail-stations-2024.json'),
    fetchHere('gaps/data/rail-lines-2024.json'),fetchHere('gaps/data/bus-lines-oitabus-20261001.json'),
    fetchHere('data/map-data.json'),fetchHere('access/destinations.json'),fetchHere('../oita-tourism/data/tourism.json')
  ]);
  degraded=request.slice(0,6).some(x=>x.status==='rejected');
  const v=(i)=>request[i].value;
  features=v(0)?.features??[];
  for(const f of features)cityBounds.set(f.properties.code,L.geoJSON(f).getBounds());
  city=features.some(f=>f.properties.code===q.get('city'))?q.get('city'):DEFAULT_CITY;
  if(features.length)$('#area').replaceChildren(...features.map(f=>new Option(f.properties.name,f.properties.code)));
  $('#area').value=city;
  stations=(v(1)?.stations??[]).filter(validPoint).map(p=>({...p,municipalityCode:areaCode(p)}));
  const withBounds=(rows=[])=>rows.filter(r=>r.points?.length>1).map(r=>({...r,bounds:L.latLngBounds(r.points)}));
  railLines=withBounds(v(2)?.lines);busLines=withBounds(v(3)?.lines);
  const localBus=v(4);
  stops=(localBus?.stops??[]).filter(validPoint).map(p=>({...p,operator:localBus.feeds[p.feedIndex]?.name??''}));
  facilities=(v(5)??[]).filter(validPoint);
  if(v(6)?.anchors?.length)tourist=v(6).anchors.filter(validPoint).map(p=>({...p,name:p.gwFacility?p.gwFacility+'（'+p.name+'）':p.name}));
  live=true;paintBounds();fit();paintLines();renderCopy();paintFilters();paintPoints();status();
  document.documentElement.dataset.audiencesReady='true';
}
if(typeof document!=='undefined')start().catch(()=>{
  $('#map-status').textContent='地図を読み込めません。下のリンクから各機能を利用できます。';
});
