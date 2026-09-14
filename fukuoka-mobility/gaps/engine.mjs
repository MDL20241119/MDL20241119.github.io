import {distance,dateKey,validDate,buildNetwork} from '../lab/gtfs.mjs';
import {prepareAccess,evaluateActivity,validateOptions} from '../access/engine.mjs';

export const GAP_VERSION='fukuoka-gaps-1.2';
export const STATES={fail:'交通空白候補',pass:'空白条件に非該当',unknown:'データ不足・未計算'};
export const timeSeconds=v=>{if(!/^\d{2}:\d{2}$/.test(v??''))throw Error('時刻を確認してください');const [h,m]=v.split(':').map(Number);if(h>23||m>59)throw Error('時刻を確認してください');return h*3600+m*60;};
export function combineDeficits(states,mode='any'){
  if(!states.length)throw Error('判定条件を1つ以上選んでください');
  if(states.some(s=>!['fail','pass','unknown'].includes(s)))throw Error('判定値が不正です');
  if(mode==='any')return states.includes('fail')?'fail':states.every(s=>s==='pass')?'pass':'unknown';
  if(mode==='all')return states.includes('pass')?'pass':states.every(s=>s==='fail')?'fail':'unknown';
  throw Error('条件の組み合わせを確認してください');
}
export function defaultProfile(cityCode,files=[]){return {schema:1,cityCode,name:'検討用の初期条件',note:'',date:'2026-09-14',resolution:500,populatedOnly:true,combine:'any',distanceOn:true,distanceM:300,frequencyOn:true,frequencyRadius:500,minimumTrips:6,serviceStart:'06:00',serviceEnd:'22:00',intervalOn:false,maximumInterval:120,wheelchair:false,reservation:'no',activityOn:false,destinations:[],destinationRule:'any',departure:'09:00',deadline:'16:00',activityFrom:'10:00',activityTo:'11:00',dwell:50,legMinutes:90,maxWalk:500,totalWalk:2000,walkSpeed:4,walkFactor:1.3,transfers:1,activityScope:'view',files};}
export function activityOptions(p){return {departure:timeSeconds(p.departure),deadline:timeSeconds(p.deadline),activityFrom:timeSeconds(p.activityFrom),activityTo:timeSeconds(p.activityTo),dwell:p.dwell,legMinutes:p.legMinutes,maxWalk:p.maxWalk,totalWalk:p.totalWalk,walkSpeed:p.walkSpeed,walkFactor:p.walkFactor,maxTransfers:p.transfers,budget:null,wheelchair:!!p.wheelchair,reservation:p.reservation??'no'};}
export function validateProfile(p){
  if(!p||p.schema!==1||!/^40\d{3}$/.test(p.cityCode)||!validDate(p.date))throw Error('自治体・日付を確認してください');
  p.intervalOn??=false;p.maximumInterval??=120;p.wheelchair??=false;p.reservation??='no';
  if(typeof p.intervalOn!=='boolean'||typeof p.wheelchair!=='boolean'||!['no','allow'].includes(p.reservation)||!Number.isFinite(p.maximumInterval)||p.maximumInterval<1||p.maximumInterval>1440)throw Error('運行間隔・利用条件を確認してください');
  if(typeof p.name!=='string'||p.name.length>80||typeof p.note!=='string'||p.note.length>1200)throw Error('条件の名前・根拠が長すぎます');
  for(const k of ['distanceOn','frequencyOn','activityOn','populatedOnly'])if(typeof p[k]!=='boolean')throw Error('選択条件が不正です');
  combineDeficits([p.distanceOn,p.frequencyOn,p.intervalOn,p.activityOn].filter(Boolean).map(()=>'unknown'),p.combine);
  for(const [k,min,max,int]of [['distanceM',0,5000,false],['frequencyRadius',0,5000,false],['minimumTrips',1,1000,true]])if(!Number.isFinite(p[k])||p[k]<min||p[k]>max||int&&!Number.isInteger(p[k]))throw Error('距離・便数の範囲を確認してください');
  if(![500,1000].includes(p.resolution))throw Error('区域の細かさを確認してください');
  if(timeSeconds(p.serviceStart)>=timeSeconds(p.serviceEnd))throw Error('運行便数の開始時刻は終了時刻より前にしてください');
  if(!Array.isArray(p.files)||p.files.length<1||p.files.length>100||new Set(p.files).size!==p.files.length)throw Error('交通データを1つ以上選んでください');
  if(!Array.isArray(p.destinations)||p.destinations.length>5||new Set(p.destinations).size!==p.destinations.length||!p.destinations.every(x=>typeof x==='string'))throw Error('目的地は重複なく5施設まで選べます');
  if(!['any','all'].includes(p.destinationRule)||!['view','city'].includes(p.activityScope))throw Error('往復の対象条件が不正です');
  validateOptions(activityOptions(p));
  if(p.activityOn&&!p.destinations.length)throw Error('往復を比べる目的地を選んでください');
  return p;
}

export function feedCoverage(feed,date){
  const d=dateKey(date),info=feed.tables.feed_info?.[0];
  if(info?.feed_version?.startsWith('analysis-snapshot-'))return (feed.tables.calendar_dates??[]).some(r=>r.date===d&&r.exception_type==='1')?'known':'unknown';
  if(info?.feed_start_date&&info?.feed_end_date)return d<info.feed_start_date||d>info.feed_end_date?'outside':'known';
  const starts=(feed.tables.calendar??[]).map(r=>r.start_date),ends=(feed.tables.calendar??[]).map(r=>r.end_date),exceptions=(feed.tables.calendar_dates??[]).map(r=>r.date);
  const low=[...starts,...exceptions].filter(Boolean).sort()[0],high=[...ends,...exceptions].filter(Boolean).sort().at(-1);
  return low&&high&&low<=d&&d<=high?'known':'unknown';
}
function validStop(s){return Number.isFinite(s.lat)&&Number.isFinite(s.lon)&&s.lat>=24&&s.lat<=46&&s.lon>=122&&s.lon<=146;}
export function prepareGapNetwork(feeds,date,referenceStops=[]){
  const valid=[],invalid=[],health=[];
  for(const f of feeds){const coverage=feedCoverage(f,date);health.push({name:f.name,id:f.id,hash:f.hash,source:f.source,coverage,analysisSnapshot:f.tables.feed_info?.[0]?.feed_version?.startsWith('analysis-snapshot-')??false});(coverage==='known'?valid:invalid).push(f);}
  const network=prepareAccess(valid,date),uncertain=buildNetwork(invalid,date);
  // Include only registered stop IDs used for ordinary boarding; station centroids and alighting-only points are excluded.
  const boardingKeys=new Set(),uncertainKeys=new Set();
  for(const [list,set]of [[valid,boardingKeys],[invalid,uncertainKeys]])for(const f of list){const last=new Map();for(const c of f.tables.stop_times??[])last.set(c.trip_id,Math.max(last.get(c.trip_id)??-Infinity,Number(c.stop_sequence)));for(const c of f.tables.stop_times??[])if(Number(c.stop_sequence)<last.get(c.trip_id)&&(!c.pickup_type||c.pickup_type==='0'))set.add(f.id+'::'+c.stop_id);}
  const stops=Object.values(network.stops).filter(s=>validStop(s)&&boardingKeys.has(s.key)),unknownStops=Object.values(uncertain.stops).filter(s=>validStop(s)&&uncertainKeys.has(s.key));
  const byStop=new Map();
  for(const t of network.trips)for(let i=0;i<t.calls.length-1;i++){const c=t.calls[i];if(!c.pickup||c.departure<0||c.departure>=86400||!validStop(network.stops[c.stopKey]??{}))continue;const entries=byStop.get(c.stopKey)??[];entries.push({trip:t.key,time:c.departure});byStop.set(c.stopKey,entries);}
  unknownStops.push(...referenceStops.filter(validStop));
  // A valid feed is evidence of some service, never of complete area coverage.
  return {network,stops,unknownStops,byStop,health,referenceStops,networkCoverageComplete:false,known:valid.length>0,invalid:invalid.length>0};
}
export function departurePattern(events,start,end){
  const all=events.filter(c=>c.time>=0&&c.time<86400).sort((a,b)=>a.time-b.time),within=all.filter(c=>c.time>=start&&c.time<end);
  const byHour=Array.from({length:24},()=>new Set());for(const c of all)byHour[Math.floor(c.time/3600)].add(c.trip);const hours=byHour.map(s=>s.size);
  const boundaries=[start,...within.map(c=>c.time),end];let max=0,gapFrom=start,gapTo=end;
  for(let i=1;i<boundaries.length;i++)if(boundaries[i]-boundaries[i-1]>max){max=boundaries[i]-boundaries[i-1];gapFrom=boundaries[i-1];gapTo=boundaries[i];}
  return {hourly:hours,first:all[0]?.time??null,last:all.at(-1)?.time??null,windowTrips:new Set(within.map(c=>c.trip)).size,maximumIntervalMinutes:max/60,gapFrom,gapTo};
}
export function measureSupply(ctx,point,p){
  let closest=null,min=Infinity,unknownMin=Infinity,roadUnknown=false;const tripIds=new Set(),nearby=[],events=[],nearbyUnverified=[];const start=timeSeconds(p.serviceStart),end=timeSeconds(p.serviceEnd);
  for(const s of ctx.stops){const straight=distance(point,s),d=ctx.network.walkingGraph?ctx.network.walkingGraph.route(point,s,Math.max(p.distanceM,p.frequencyRadius),false).meters:straight;if(!Number.isFinite(d)&&straight<=Math.max(p.distanceM,p.frequencyRadius))roadUnknown=true;if(d<min){min=d;closest=s;}if(d<=p.frequencyRadius+1e-6){events.push(...ctx.byStop.get(s.key)??[]);let n=0;for(const c of ctx.byStop.get(s.key)??[])if(c.time>=start&&c.time<end){tripIds.add(c.trip);n++;}if(n)nearby.push({name:s.name,meters:d,departures:n});}}
  for(const s of ctx.unknownStops){const d=distance(point,s);unknownMin=Math.min(unknownMin,d);if(d<=Math.max(p.distanceM,p.frequencyRadius,p.maxWalk??0)+1e-6)nearbyUnverified.push({name:s.name,operator:s.operator??s.feedName??'選択外・期間外の時刻表',mode:s.mode??'',meters:d,positionDate:s.positionDate??'GTFSの収録位置'});}
  const pattern=departurePattern(events,start,end),complete=ctx.networkCoverageComplete===true;
  const distanceState=min<=p.distanceM+1e-6?'pass':!complete||!ctx.known||roadUnknown||unknownMin<=p.distanceM+1e-6?'unknown':'fail';
  const frequencyState=tripIds.size>=p.minimumTrips?'pass':!complete||!ctx.known||roadUnknown||unknownMin<=p.frequencyRadius+1e-6||ctx.network.excluded>0?'unknown':'fail';
  const criteria=[];
  if(p.distanceOn)criteria.push({id:'distance',state:distanceState,observedState:min<=p.distanceM?'pass':'fail',label:'停留所までの距離',value:Number.isFinite(min)?min:null,threshold:p.distanceM,reason:distanceState==='pass'?'収録した乗車地点で距離条件を満たす':distanceState==='unknown'?'現行交通網・乗車地点を網羅できていないため、距離不足の確定を保留':'確認済みの乗車用停留所が距離の上限を超える'});
  if(p.frequencyOn)criteria.push({id:'frequency',state:frequencyState,observedState:tripIds.size>=p.minimumTrips?'pass':'fail',label:'時間帯内の乗車便数',value:tripIds.size||complete?tripIds.size:null,threshold:p.minimumTrips,reason:frequencyState==='pass'?'収録便だけで必要な便数以上':frequencyState==='unknown'?'未接続・選択外・期間外の交通を含む全便数は未確認。収録便だけでは設定本数に届かない':'確認済みの便数が設定した本数に届かない'});
  if(p.intervalOn){const state=ctx.known&&pattern.windowTrips>0&&pattern.maximumIntervalMinutes<=p.maximumInterval?'pass':complete&&ctx.known&&!roadUnknown&&unknownMin>p.frequencyRadius&&!ctx.network.excluded?'fail':'unknown';criteria.push({id:'interval',state,observedState:pattern.windowTrips>0&&pattern.maximumIntervalMinutes<=p.maximumInterval?'pass':'fail',label:'乗車便がない最大時間',value:events.length||complete?pattern.maximumIntervalMinutes:null,threshold:p.maximumInterval,reason:state==='pass'?'収録便だけで空き時間の上限を満たす':state==='unknown'?'収録便では長い空き時間があるか、時刻表を確認できない。全交通の不足は未確定':'設定時間帯に便がない、または乗車便がない時間が上限を超える'});}
  if(p.activityOn)criteria.push({id:'activity',state:'unknown',label:'選択した目的地への往復',value:null,reason:'往復は未計算'});
  return {criteria,status:combineDeficits(criteria.map(x=>x.state),p.combine),networkCoverageComplete:complete,departurePattern:events.length||complete?pattern:null,nearbyUnverified:nearbyUnverified.sort((a,b)=>a.meters-b.meters).slice(0,12),nearest:closest?{name:closest.name,lat:closest.lat,lon:closest.lon,meters:min,feed:closest.feed}:null,departures:tripIds.size||complete?tripIds.size:null,nearby:nearby.sort((a,b)=>a.meters-b.meters).slice(0,5),roadSearchMeters:ctx.network.walkingGraph?Math.max(p.distanceM,p.frequencyRadius):null,walkingModel:ctx.network.walkingGraph?'OSM道路距離・75m以内の地点接続':'直線距離',scope:'収録交通の供給下限。網羅未確認の不足は判定保留'};
}
export function activityCriterion(ctx,point,facilities,p){
  const details=[],o=activityOptions(p);
  for(const f of facilities){const r=evaluateActivity(ctx.network,point,f,o,{});const unverified=ctx.networkCoverageComplete!==true||(ctx.unknownStops??[]).some(s=>distance(point,s)<=p.maxWalk||distance(f,s)<=p.maxWalk);const personalUnknown=!!r.outbound&&(r.outbound.unknowns.length>0||r.inbound.unknowns.length>0||o.wheelchair);const state=r.outbound&&!personalUnknown?'pass':personalUnknown||r.searchIncomplete||ctx.network.excluded||!ctx.known||ctx.invalid||unverified?'unknown':'fail';details.push({id:f.id,name:f.name,state,homeAt:r.homeAt??null,begin:r.begin??null,walk:r.walk??null,unknowns:r.unknowns,reasons:r.reasons,searchIncomplete:!!r.searchIncomplete});}
  // 'any destination reachable' means failure only when all selected destinations have no candidate.
  const state=combineDeficits(details.map(x=>x.state),p.destinationRule==='any'?'all':'any');
  return {id:'activity',state,label:'選択した目的地への往復',value:details.filter(x=>x.state==='pass').length,threshold:details.length,reason:state==='pass'?'時刻表上の往復候補あり（施設の利用条件は別途確認）':state==='fail'?'指定施設への往復候補が設定した条件で見つからない':'未収録・探索の制約があり判定できない',details};
}
export function finalizeCell(supply,activity,p){const criteria=supply.criteria.map(c=>c.id==='activity'?activity:c);return {...supply,criteria,status:combineDeficits(criteria.map(c=>c.state),p.combine)};}
