import fs from 'node:fs/promises';
import path from 'node:path';
import {importGTFS,buildNetwork,supply,validateFeeds} from '../fukuoka-mobility/lab/gtfs.mjs';
import {scopeFeed} from '../fukuoka-mobility/lab/feed-scope.mjs';

const raw=process.argv[2],root=new URL('../fukuoka-mobility/',import.meta.url);
const manifest=JSON.parse(await fs.readFile(path.join(raw,'gtfs-manifest.json'),'utf8'));
const dates=['20260914','20260919','20260920'];
const catalog=[],feeds=[],routes=[],stops=[],shapes=[],networks=[[],[],[]];
const reviews=[];
// Display geometry only. Route calculations and downloadable GTFS retain original coordinates.
function simplifyLine(points,tolerance=15){
 if(points.length<3)return points.map(p=>p.map(v=>Number(v.toFixed(6))));
 const projected=points.map(([lat,lon])=>[lon*111320*Math.cos(33.6*Math.PI/180),lat*111320]);
 const keep=new Set([0,points.length-1]),stack=[[0,points.length-1]],threshold=tolerance*tolerance;
 while(stack.length){const [first,last]=stack.pop(),a=projected[first],b=projected[last],dx=b[0]-a[0],dy=b[1]-a[1],length=dx*dx+dy*dy;let maximum=threshold,index=-1;
  for(let i=first+1;i<last;i++){const p=projected[i],t=length?Math.max(0,Math.min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/length)):0;const distance=(p[0]-a[0]-t*dx)**2+(p[1]-a[1]-t*dy)**2;if(distance>maximum){maximum=distance;index=i;}}
  if(index!==-1){keep.add(index);stack.push([first,index],[index,last]);}
 }
 return [...keep].sort((a,b)=>a-b).map(i=>points[i].map(v=>Number(v.toFixed(6))));
}
for(const item of manifest.filter(m=>m.downloaded)){
 const buffer=await fs.readFile(path.join(raw,'gtfs',item.file));
 try{
  const id=item.file.split('__').at(-1).slice(0,8),f=scopeFeed(await importGTFS(buffer.buffer.slice(buffer.byteOffset,buffer.byteOffset+buffer.byteLength),item.name,id),item),t=f.tables;
  const q=validateFeeds([f]);
  const starts=[...(t.calendar??[]).map(r=>r.start_date),...(t.calendar_dates??[]).filter(r=>r.exception_type==='1').map(r=>r.date)].filter(Boolean);
  const ends=[...(t.calendar??[]).map(r=>r.end_date),...(t.calendar_dates??[]).filter(r=>r.exception_type==='1').map(r=>r.date)].filter(Boolean);
  const info=t.feed_info?.[0],validFrom=info?.feed_start_date||starts.sort()[0]||null,validTo=info?.feed_end_date||ends.sort().at(-1)||null;
  const analysisReady=q.errors===0;
  const current=analysisReady&&!!validFrom&&validFrom<=dates[0]&&!!validTo&&validTo>=dates[0];
  reviews.push({file:item.file,errors:q.errors,warnings:q.warnings,issues:q.issues,validFrom,validTo,current});
  // Keep expired source snapshots inspectable without reporting them as today's zero service.
  const m={...item,id,validFrom,validTo,current,analysisReady,retrieved:'2026-09-14',licenseCheckedAt:'2026-09-14',attribution:`出典：${item.provider}／${item.name}`,
   processing:(item.derived?'公式公開ExcelをGTFSに加工。分析対象日を限定。公式の有効期限ではない。':'公開GTFS ZIPを保存。')+'原典の運行暦・例外日・乗降制限を適用。'+(item.analysisScope??''),dataStatus:!analysisReady?'invalid':current?'current':'expired'};
  await fs.mkdir(new URL('data/gtfs/',root),{recursive:true});await fs.writeFile(new URL('data/gtfs/'+item.file,root),buffer);
  catalog.push(m);
  const fi=feeds.length,ns=dates.map(d=>buildNetwork([f],d,{includeOvernight:false}));
  const supplies=ns.map(n=>supply(n));const inValidity=dates.map(d=>analysisReady&&!!validFrom&&validFrom<=d&&!!validTo&&d<=validTo);
  const stopIndex=new Map(),routeIndex=new Map(),tripRoutes=new Map(t.trips.map(r=>[r.trip_id,r.route_id])),stopRoutes=new Map();
  for(const r of t.routes??[]){routeIndex.set(r.route_id,routes.length);routes.push({id:r.route_id,feedIndex:fi,agencyId:r.agency_id??t.agency?.[0]?.agency_id??'',name:r.route_long_name||r.route_short_name||r.route_id,routeType:r.route_type,trips:ns.map((n,i)=>inValidity[i]?n.trips.filter(tr=>tr.routeId===r.route_id).length:null)})}
  for(const c of t.stop_times??[]){if(!stopRoutes.has(c.stop_id))stopRoutes.set(c.stop_id,new Set());const ri=routeIndex.get(tripRoutes.get(c.trip_id));if(ri!==undefined)stopRoutes.get(c.stop_id).add(ri);}
  const perRouteStop=ns.map((n,i)=>{const result=new Map();if(inValidity[i])for(const trip of n.trips)if(trip.offset===0)for(const c of trip.calls)if(c.pickup&&c.departure>=0&&c.departure<172800){const k=c.stop_id+'|'+routeIndex.get(trip.routeId);result.set(k,(result.get(k)??0)+1);}return result;});
  const prefStops=item.fukuokaStopIds?new Set(item.fukuokaStopIds):null;
  for(const s of t.stops??[]){if(!s.stop_lat||!s.stop_lon||!Number.isFinite(Number(s.stop_lat))||!Number.isFinite(Number(s.stop_lon)))continue;
   if(!item.analysisRouteIds&&(Number(s.stop_lat)<32.7||Number(s.stop_lat)>34.4||Number(s.stop_lon)<129.9||Number(s.stop_lon)>131.5))continue;
   stopIndex.set(s.stop_id,stops.length);stops.push({id:s.stop_id,feedIndex:fi,name:s.stop_name,lat:Number(s.stop_lat),lon:Number(s.stop_lon),inFukuoka:prefStops?prefStops.has(s.stop_id):true,departures:supplies.map((v,i)=>inValidity[i]?(v.byStop[id+'::'+s.stop_id]?.departures??0):null),routes:[...(stopRoutes.get(s.stop_id)??[])],routeDepartures:Object.fromEntries([...(stopRoutes.get(s.stop_id)??[])].map(ri=>[ri,perRouteStop.map((d,i)=>inValidity[i]?(d.get(s.stop_id+'|'+ri)??0):null)])),reach:[0,0,0]});}
  const shapeGroups=new Map();for(const s of t.shapes??[]){if(!shapeGroups.has(s.shape_id))shapeGroups.set(s.shape_id,[]);shapeGroups.get(s.shape_id).push(s)}
  for(const [sid,points] of shapeGroups){points.sort((a,b)=>Number(a.shape_pt_sequence)-Number(b.shape_pt_sequence));const related=[...new Set((t.trips??[]).filter(tr=>tr.shape_id===sid).map(tr=>routeIndex.get(tr.route_id)))];
   shapes.push({id:sid,feedIndex:fi,routeIndices:related,trips:ns.map((n,i)=>inValidity[i]?n.trips.filter(tr=>tr.shape===sid).length:0),coordinates:simplifyLine(points.map(p=>[Number(p.shape_pt_lat),Number(p.shape_pt_lon)]))});}
  feeds.push({id,name:item.name,sourceUrl:item.catalog,downloadUrl:item.source,license:item.license,licenseUrl:item.licenseUrl,validFrom,validTo,scheduledTrips:supplies.map((v,i)=>inValidity[i]?v.trips:null),sha256:item.sha256,stopCount:stopIndex.size,shapeCount:shapeGroups.size,analysisSampleDates:item.analysisSampleDates??null,validityNote:item.validityNote??null,shapeStatus:shapeGroups.size?'GTFS shapesあり':'線形未収録',dataStatus:!analysisReady?'invalid':current?'current':'expired'});
  ns.forEach((n,i)=>inValidity[i]&&networks[i].push({n,stopIndex}));
  console.log(item.file,stopIndex.size,supplies.map(x=>x.trips).join('/'),current?'有効':'期限外',q.errors+' errors');
 }catch(e){reviews.push({file:item.file,error:String(e)});console.error(item.file,String(e));}
}
// Reference origins come from actual stop names, not synthesized bus coordinates.
const originSpecs=[['田川後藤寺駅',/後藤寺駅/],['西鉄二日市駅',/西鉄二日市/],['海老津駅',/海老津駅/],['苅田駅',/苅田駅/],['博多ふ頭',/博多ふ頭|博多埠頭/]];
const origins=originSpecs.map(([name,re])=>{const indices=stops.map((s,i)=>re.test(s.name)?i:-1).filter(i=>i>=0);return {name,stopIndices:indices,center:indices.length?[indices.reduce((v,i)=>v+stops[i].lat,0)/indices.length,indices.reduce((v,i)=>v+stops[i].lon,0)/indices.length]:null,reachableNames:[0,0,0]}}).filter(o=>o.center);
for(let d=0;d<dates.length;d++)for(let oi=0;oi<origins.length;oi++){
 const origin=origins[oi],allowed=new Set(origin.stopIndices);
 for(const {n,stopIndex} of networks[d])for(const trip of n.trips){let boarded=false;for(const call of trip.calls){const i=stopIndex.get(call.stop_id);if(i===undefined)continue;if(allowed.has(i)&&call.pickup&&call.departure>=32400&&call.departure<=36000)boarded=true;if(boarded&&call.dropoff&&call.arrival<=36000)stops[i].reach[d]|=1<<oi;}}
 origin.reachableNames[d]=new Set(stops.filter(s=>s.reach[d]&(1<<oi)).map(s=>s.name)).size;
}
const result={meta:{version:1,analysisDate:'2026-09-14',retrievedAt:'2026-09-14',dates,dateLabels:['2026年9月14日（月）','2026年9月19日（土）','2026年9月20日（日）'],scope:'福岡県の公開GTFSと、佐賀・大分県配布の福岡接続路線、福岡市地下鉄の限定日データ（県外区間を含む）。県内全交通の網羅ではありません。西鉄バス・西鉄電車・JR九州等の全時刻表は未収録。',realtime:false,scheduleOnly:true,coordinateOrder:'[latitude, longitude]',attribution:'各自治体・運行事業者／BODIK、GTFSデータリポジトリ、佐賀県GTFS',departureDefinition:'当日の運行暦・例外日に従うGTFSの通常乗車可能な出発の数。乗客数ではありません。',zeroDefinition:'有効期間内の収録停留所で出発がない場合だけ0。期限外はnull。未収録の交通を0とはしません。',scheduledTripTotals:dates.map((_,i)=>feeds.reduce((n,f)=>n+(f.scheduledTrips[i]??0),0)),currentFeeds:feeds.filter(f=>f.dataStatus==='current').length},feeds,routes,stops,shapes,origins};
await fs.writeFile(new URL('data/gtfs/catalog.json',root),JSON.stringify(catalog,null,2));await fs.writeFile(new URL('data/map-data.json',root),JSON.stringify(result));await fs.writeFile(new URL('data/gtfs-validation.json',root),JSON.stringify(reviews,null,2));
console.log({feeds:feeds.length,current:result.meta.currentFeeds,stops:stops.length,shapes:shapes.length,totals:result.meta.scheduledTripTotals});
