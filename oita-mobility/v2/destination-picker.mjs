import {distance} from '../lab/gtfs.mjs';
import {PURPOSES,normalizeCategory} from './model.mjs';
import {SHOP_TYPES,shopType,matchingDestinations} from './destinations.mjs';
import {$,esc,fmt,link} from './shared.mjs';

// A visible, paginated picker also works on mobile browsers without datalist UI.
export function createDestinationPicker({getPlaces,getHome,onFilter,onClear}){
 let category='all',query='',limit=6;
 const input=$('#destination'),type=$('#shop-kind');
 function rows(){return matchingDestinations(getPlaces(),{category,type:category==='shopping'?type.value:'all',query,home:getHome()});}
 function render(){
  const pool=getPlaces(),matches=rows(),visible=matches.slice(0,limit),home=getHome();
  $('#shop-filter').hidden=category!=='shopping';
  for(const b of document.querySelectorAll('#purpose-chips [data-purpose]'))b.setAttribute('aria-pressed',String(b.dataset.purpose===category));
  $('#destination-count').textContent=`${category==='all'?'目的地':PURPOSES[category]} ${fmt(matches.length)}件${matches.length?` / ${fmt(visible.length)}件を表示`:''}${home?' · 出発地から近い順':''}`;
  $('#destination-list').innerHTML=matches.map(p=>`<option value="${esc(p.name)}（${esc(p.city)}）"></option>`).join('');
  $('#destination-options').innerHTML=visible.map(p=>`<button type="button" class="destination-card" data-target="${esc(p.id)}"><small>${esc(p.city)} · ${esc(normalizeCategory(p.category)==='shopping'?SHOP_TYPES[shopType(p)]:PURPOSES[normalizeCategory(p.category)])}${home?' · 直線 約'+fmt(distance(home,p))+'m':''}</small><strong>${esc(p.name)}</strong><span>${esc(p.address||'住所の詳細は出典で確認')}</span></button>`).join('')||`<p class="note">この条件に一致する収録施設はありません。${pool.length?'店名を短くする・絞り込みを解除する・「ほかの市町村」も対象にする方法を試してください。':'未収録は、お店や施設が存在しないという意味ではありません。'}地図から任意の場所も指定できます。</p>`;
  $('#destination-more').hidden=limit>=matches.length;
  $('#destination-more').textContent=`次の${Math.min(12,Math.max(0,matches.length-limit))}件を表示`;
  $('#destination-reset').hidden=category==='all'&&!query;
  onFilter(matches);
 }
 function resetSelection(){input.value='';query='';limit=6;$('#destination-selected').hidden=true;onClear();}
 input.addEventListener('input',()=>{query=input.value;limit=6;$('#destination-selected').hidden=true;render();});
 $('#purpose-chips').addEventListener('click',e=>{const b=e.target.closest('[data-purpose]');if(!b)return;resetSelection();category=b.dataset.purpose;type.value='all';render();});
 type.addEventListener('change',()=>{resetSelection();category='shopping';render();});
 $('#destination-more').onclick=()=>{limit+=12;render();};
 $('#destination-reset').onclick=()=>{resetSelection();category='all';type.value='all';render();};
 return {
  refresh({reset=false}={}){if(reset){category='all';type.value='all';query='';limit=6;$('#destination-selected').hidden=true;}const previous=type.value;const counts=Object.fromEntries(Object.keys(SHOP_TYPES).map(k=>[k,getPlaces().filter(p=>normalizeCategory(p.category)==='shopping'&&shopType(p)===k).length]));type.innerHTML='<option value="all">買物のお店すべて</option>'+Object.entries(SHOP_TYPES).filter(([k])=>counts[k]).map(([k,n])=>`<option value="${k}">${n}（${counts[k]}件）</option>`).join('');type.value=Object.hasOwn(counts,previous)&&counts[previous]?previous:'all';render();},
  select(p){query='';const h=typeof p.openingHours==='string'?p.openingHours:'未確認';$('#destination-selected').hidden=false;$('#destination-selected').innerHTML=`<strong>選択中：${esc(p.name)}</strong><p>${esc(p.address||p.city)}</p><p>営業・受付：${esc(h)}<br><small>出典の記載。臨時休業・当日の利用可否は未確認です。</small></p><p class="note">${esc(p.positionNote??p.dataNote??(p.needsCoordinateConfirmation?'公式地図の概略位置。入口は確認が必要です。':'施設の所在地。入口・歩行経路は未確認です。'))}</p><p>${p.sourceUrl||p.url?link(p.sourceUrl??p.url,'店舗・施設の公式案内'):'地図で指定した地点・施設情報は未照合'} · 確認 ${esc(p.checkedAt??p.retrievedAt??p.dataAsOf??'未確認')}</p>`;render();}
 };
}
