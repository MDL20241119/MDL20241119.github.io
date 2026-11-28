// Internal analysis only. Never load public timetable HTML or ship timetable rows with the UI.
import {dateKey,seconds,validDate,validateFeeds} from '../lab/gtfs.mjs';
import {prepareAccess,evaluateActivity} from '../access/engine.mjs';
import {activityOptions,feedCoverage} from './engine.mjs';

export const OITA_RAIL_LINES=Object.freeze(['日豊本線','久大本線','豊肥本線']);
const standardRailTypes=new Set(['2',...Array.from({length:18},(_,i)=>String(100+i))]);

function normalizeRail(feed){
  const byTrip=new Map();
  for(const row of feed.tables.stop_times??[]){
    const rows=byTrip.get(row.trip_id)??[];
    rows.push({...row});
    byTrip.set(row.trip_id,rows);
  }
  for(const rows of byTrip.values()){
    if(rows.length<2)continue;
    rows.sort((a,b)=>Number(a.stop_sequence)-Number(b.stop_sequence));
    const first=rows[0],last=rows.at(-1);
    if(!first.arrival_time&&seconds(first.departure_time)!==null)first.arrival_time=first.departure_time;
    if(!last.departure_time&&seconds(last.arrival_time)!==null)last.departure_time=last.arrival_time;
    first.drop_off_type='1';
    last.pickup_type='1';
  }
  return {...feed,tables:{...feed.tables,stop_times:[...byTrip.values()].flat()}};
}

export function prepareOitaRoundTrips({busFeeds,railFeeds=[],date,railScope=null,busCoverageComplete=false}){
  if(!validDate(date))throw Error('分析日が不正です');
  date=dateKey(date);
  const all=[...busFeeds,...railFeeds], ids=new Set(all.map(x=>x.id));
  if(ids.size!==all.length||all.some(f=>!f.id||f.id.includes('::')))throw Error('交通データのIDが不正です');
  const validBus=busFeeds.filter(f=>feedCoverage(f,date)==='known');
  const accepted=[], railHealth=[];
  for(const input of railFeeds){
    // License is verified by the operator outside this function; this gate is not a license verifier.
    if(!['synthetic','authorized'].includes(input.dataUse))throw Error('JRデータの利用条件を確認してください');
    const f=normalizeRail(input);
    const coverage=feedCoverage(f,date);
    const checks=validateFeeds([f]);
    const railOnly=(f.tables.routes??[]).every(r=>standardRailTypes.has(r.route_type));
    const tripsWithCalls=new Set(f.tables.stop_times.map(r=>r.trip_id));
    const everyTripHasCalls=(f.tables.trips??[]).every(r=>tripsWithCalls.has(r.trip_id));
    const usable=coverage==='known'&&!checks.errors&&railOnly&&everyTripHasCalls;
    if(usable)accepted.push(f);
    railHealth.push({id:f.id,coverage,usable,partial:checks.warnings>0});
  }
  const scopedIds=railScope?.feedIds;
  const coveredLines=new Set(railScope?.lines??[]);
  const fullRail=accepted.length>0&&railHealth.every(f=>f.usable&&!f.partial)
    &&railScope?.cityCode==='44201'&&dateKey(railScope.date)===date
    &&railScope.crossBoundary===true&&OITA_RAIL_LINES.every(l=>coveredLines.has(l))
    &&Array.isArray(scopedIds)&&scopedIds.length===accepted.length&&new Set(scopedIds).size===accepted.length
    &&accepted.every(f=>scopedIds.includes(f.id));
  const bus=prepareAccess(validBus,date);
  const combined=accepted.length?prepareAccess([...validBus,...accepted],date):null;
  return {date,bus,combined,railHealth,fullRail,synthetic:accepted.some(f=>f.dataUse==='synthetic'),
    fullBus:busCoverageComplete===true&&validBus.length>0&&validBus.length===busFeeds.length};
}

export function judgeOitaRoundTrip(ctx,origin,destination,profile,selectedOptions=null){
  if(profile.cityCode!=='44201'||dateKey(profile.date)!==ctx.date)throw Error('大分市と分析日を確認してください');
  for(const p of [origin,destination])if(!Number.isFinite(p?.lat)||!Number.isFinite(p?.lon)||Math.abs(p.lat)>90||Math.abs(p.lon)>180)throw Error('地点の座標が不正です');
  const options=selectedOptions??activityOptions(profile);
  const run=(network,complete)=>{
    if(!network)return 'unknown';
    const result=evaluateActivity(network,origin,destination,options);
    if(result.outbound)return 'pass';
    return complete&&!result.searchIncomplete&&!network.excluded?'fail':'unknown';
  };
  const bus=run(ctx.bus,ctx.fullBus);
  const combined=bus==='pass'?'pass':run(ctx.combined,ctx.fullRail&&ctx.fullBus);
  const status=bus==='pass'?'bus_baseline':combined==='pass'?(bus==='fail'?'rail_adds_option':'combined_option_baseline_unknown'):
    combined==='fail'?'no_scheduled_roundtrip':'unknown';
  return {status,bus,combined,railInput:ctx.combined?(ctx.synthetic?'synthetic':'authorized'):'not_loaded'};
}

export function judgeOitaBatch(ctx,origins,destinations,profile){
  return origins.flatMap(origin=>destinations.map(destination=>({
    originId:origin.id,destinationId:destination.id,...judgeOitaRoundTrip(ctx,origin,destination,profile)
  })));
}
