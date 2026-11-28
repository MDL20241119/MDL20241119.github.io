import {importGTFS,dateKey,validDate} from '../lab/gtfs.mjs';
import {evaluateActivity} from '../access/engine.mjs';
import {prepareOitaRoundTrips} from '../gaps/rail-roundtrip.mjs';
const registry=new URL('../data/rail/authorized.json',import.meta.url);
const filenames=/^[A-Za-z0-9][A-Za-z0-9._-]{0,100}\.zip$/;
function approved(entry,ymd){
 return entry?.publicRedistribution===true&&entry.operator==='JR九州'
  &&Array.isArray(entry.lines)&&entry.lines.length>0&&entry.lines.every(s=>typeof s==='string'&&s.length<40)
  &&filenames.test(entry.file??'')&&/^[a-f0-9]{64}$/.test(entry.sha256??'')
  &&Number.isInteger(entry.bytes)&&entry.bytes>0&&entry.bytes<=20*1024*1024
  &&/^https:\/\//.test(entry.source??'')&&/^https:\/\//.test(entry.permissionSource??'')
  &&validDate(entry.start)&&validDate(entry.end)&&dateKey(entry.start)<=ymd&&ymd<=dateKey(entry.end);
}
export async function loadAutomaticRail(date, fetcher=fetch){
 if(!validDate(date))return {feeds:[],status:'date_unverified'};
 const response=await fetcher(registry,{cache:'no-store',redirect:'error'});
 if(!response.ok)throw Error('JRデータ一覧を読めません');
 const entries=await response.json();
 if(entries.schema!=='atlas-public-rail/v1'||!Array.isArray(entries.feeds)||entries.feeds.length>6)throw Error('JRデータ一覧の形式を確認してください');
 const active=entries.feeds.filter(e=>approved(e,dateKey(date)));
 if(!active.length)return {feeds:[],status:entries.feeds.length?'date_unverified':'unavailable'};
 const files=new Set(active.map(e=>e.file));
 if(files.size!==active.length||active.reduce((n,e)=>n+e.bytes,0)>40*1024*1024)throw Error('JRファイルに重複または容量超過があります');
 const feeds=await Promise.all(active.map(async (e,i)=>{
   const r=await fetcher(new URL(e.file,registry),{redirect:'error'});
   if(!r.ok)throw Error('JRファイルを取得できません');
   const bytes=await r.arrayBuffer();
   if(bytes.byteLength!==e.bytes)throw Error('JRファイルのサイズが一致しません');
   const p=await importGTFS(bytes,'JR九州','atlas-rail-'+i);
   if(p.hash!==e.sha256)throw Error('JRファイルの照合に失敗しました');
   return {...p,dataUse:'authorized'};
 }));
 return {feeds,status:'loaded'};
}
export async function automaticRailResult({busFeeds,date,home,target,options,conditions},get=fetch){
 try{
   const input=await loadAutomaticRail(date,get);
   if(!input.feeds.length)return {status:input.status};
   const ctx=prepareOitaRoundTrips({busFeeds,railFeeds:input.feeds,date});
   if(!ctx.combined)return {status:'date_unverified'};
   const result=evaluateActivity(ctx.combined,home,target,options,conditions);
   const ids=new Set(input.feeds.map(f=>f.id));
   const usesRail=r=>r?.path?.some(l=>l.mode==='bus'&&ids.has(l.from?.feed))===true;
   const outbound=usesRail(result.outbound),inbound=usesRail(result.inbound);
   if(result.outbound&&result.inbound&&(outbound||inbound))return {status:'rail_candidate',outbound,inbound};
   return {status:'no_rail_witness'};
 }catch{return {status:'unavailable_error'};}
}
