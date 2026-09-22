import {cityAt,validPoint} from './model.mjs';
import {$,esc,guard} from './shared.mjs';

export function setupArea(boundaries,onChoose){
  let request=0;
  const select=$('#area-city'),button=$('#area-current'),status=$('#area-status');
  select.innerHTML='<option value="" disabled selected>市町村を選んでください</option>'+boundaries.features.map(f=>`<option value="${esc(f.properties.code)}">${esc(f.properties.name)}</option>`).join('');
  select.disabled=false;button.disabled=false;status.textContent='';
  const choose=(area,point)=>{select.value=area.properties.code;$('#area-title').textContent=area.properties.name+'から、調べる。';status.textContent=point?'現在地を出発地に設定しました。次に行きたい場所を選んでください。':'次に、出発地点と行きたい場所を選んでください。';onChoose(area,point);};
  select.onchange=guard(()=>{request++;button.disabled=false;const area=boundaries.features.find(f=>f.properties.code===select.value);if(area)choose(area,null);});
  button.onclick=()=>{
    const id=++request;
    if(!navigator.geolocation){status.textContent='現在地を取得できないブラウザーです。市町村から選んでください。';return;}
    button.disabled=true;status.textContent='現在地を確認しています…';
    navigator.geolocation.getCurrentPosition(guard(position=>{
      if(id!==request)return;button.disabled=false;
      const point={name:'現在地',lat:position.coords.latitude,lon:position.coords.longitude};
      const city=validPoint(point)?cityAt(point,boundaries.features):null;
      const area=boundaries.features.find(f=>f.properties.code===city?.code);
      if(!area){status.textContent='現在地を大分県内の市町村に合わせられませんでした。調べたい市町村を選んでください。';return;}
      choose(area,point);
    }),()=>{if(id!==request)return;button.disabled=false;status.textContent='現在地を取得できませんでした。市町村から選んでください。';},{timeout:10000,maximumAge:60000});
  };
}
