import {distance} from '../lab/gtfs.mjs';
import {normalizeCategory,validPoint} from './model.mjs';

export const SHOP_TYPES={supermarket:'スーパー・食品店',drugstore:'ドラッグストア',convenience:'コンビニ',department:'百貨店・商業施設',homecenter:'ホームセンター・日用品',food:'パン・生鮮・直売所',other:'その他のお店'};
export function shopType(p){return Object.hasOwn(SHOP_TYPES,p.shopType)?p.shopType:normalizeCategory(p.category)==='shopping'?'supermarket':null;}
export function searchText(value){return String(value??'').normalize('NFKC').toLocaleLowerCase('ja').replace(/[ァ-ヶ]/g,c=>String.fromCharCode(c.charCodeAt(0)-0x60)).replace(/[\s・･ー‐‑–—−-]/g,'');}
export function matchingDestinations(places,{category='all',type='all',query='',home=null}={}){
 const words=String(query).normalize('NFKC').trim().split(/[\s　]+/).filter(Boolean).map(searchText);
 return places.filter(p=>validPoint(p)&&(category==='all'||normalizeCategory(p.category)===category)&&(type==='all'||normalizeCategory(p.category)==='shopping'&&shopType(p)===type)&&words.every(w=>searchText([p.name,p.city,p.address,p.brand,...(p.aliases??[]),SHOP_TYPES[shopType(p)]].filter(Boolean).join(' ')).includes(w)))
 .sort((a,b)=>validPoint(home)?distance(home,a)-distance(home,b)||a.name.localeCompare(b.name,'ja'):a.name.localeCompare(b.name,'ja')||String(a.address??'').localeCompare(String(b.address??''),'ja'));
}
export function resolveDestination(value,places,label=p=>p.city?`${p.name}（${p.city}）`:p.name){
 const exact=places.filter(p=>label(p)===value);if(exact.length===1)return exact[0];
 const named=places.filter(p=>p.name===value);return named.length===1?named[0]:null;
}
