import {distance,clock} from '../lab/gtfs.mjs';
import {localDay} from './model.mjs';
export const $=s=>document.querySelector(s);
export const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const fmt=(v,d=0)=>Number.isFinite(v)?v.toLocaleString('ja-JP',{maximumFractionDigits:d}):'—';
export const time=v=>Number.isFinite(v)?clock(v).slice(0,5):'—';
export async function json(url){const r=await fetch(url);if(!r.ok)throw Error('データを読み込めません。通信を確認して再度お試しください。');return r.json();}
export function link(url,label){try{const u=new URL(url);return ['https:','http:'].includes(u.protocol)?`<a href="${esc(u.href)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`:esc(label);}catch{return esc(label);}}
export function mapAt(id){const map=L.map(id,{preferCanvas:true,scrollWheelZoom:false}).setView([33.25,131.40],9);L.tileLayer('https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png',{maxZoom:18,attribution:'<a href="https://maps.gsi.go.jp/development/ichiran.html">地理院タイル</a> | MDL・公開データを加工'}).addTo(map).on('tileerror',()=>{const n=$('#map-note');if(n)n.textContent='背景地図の取得に失敗しました。地点・判定と一覧は利用できます。';});return map;}
export function nearbyFeeds(catalog,transport,points){const feedIds=new Set();for(const p of points)for(const s of transport.stops)if(distance(p,s)<=3000)feedIds.add(s.feedIndex);const hashes=new Set([...feedIds].map(i=>transport.feeds[i]?.sha256));return catalog.filter(f=>hashes.has(f.sha256));}
export function feedChooser(catalog,selected=[]){return catalog.map(f=>`<label class="check"><input type="checkbox" name="feeds" value="${esc(f.file)}" ${selected.some(s=>s.file===f.file)?'checked':''}>${esc(f.name)}</label>`).join('');}
export function chosenFeeds(catalog){return catalog.filter(f=>[...document.querySelectorAll('[name=feeds]:checked')].some(c=>c.value===f.file));}
export function setFeeds(files){document.querySelectorAll('[name=feeds]').forEach(n=>n.checked=files.some(f=>f.file===n.value));}
export function error(e){const n=$('#error');if(n){n.hidden=false;n.textContent=e.message??String(e);}}
export function guard(fn){return(...a)=>{try{Promise.resolve(fn(...a)).catch(error);}catch(e){error(e);}};}
export function dateInputs(){document.querySelectorAll('input[data-today]').forEach(n=>n.value=localDay());}
export function localRead(key,fallback=[]){try{return JSON.parse(localStorage.getItem(key)??'null')??fallback;}catch{return fallback;}}
export function localWrite(key,value){try{localStorage.setItem(key,JSON.stringify(value));return true;}catch{throw Error('このブラウザでは保存できません。ブラウザの保存設定を確認してください。');}}
export const DEMAND_KEY='oita-atlas-v2-demand';
