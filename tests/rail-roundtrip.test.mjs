import test from 'node:test';
import assert from 'node:assert/strict';
import {defaultProfile} from '../oita-mobility/gaps/engine.mjs';
import {OITA_RAIL_LINES,prepareOitaRoundTrips,judgeOitaRoundTrip,judgeOitaBatch} from '../oita-mobility/gaps/rail-roundtrip.mjs';

const p={...defaultProfile('44201'),date:'2026-11-30',departure:'08:50',activityFrom:'10:00',activityTo:'10:00',dwell:30,deadline:'12:00',transfers:1,maxWalk:80,walkFactor:1};
const point=(id,lat,lon)=>({id,lat,lon});
const a=point('origin',33.23,131.60), k=point('interchange',33.23,131.62), d=point('destination',33.23,131.64);
function feed(id,mode,places,schedules,lines=['R']){
  const tables={
    agency:[{agency_id:'x',agency_timezone:'Asia/Tokyo'}],
    routes:lines.map((name,i)=>({route_id:'r'+i,route_type:mode,route_long_name:name})),
    stops:places.map((s,i)=>({stop_id:String(i),stop_name:s.id,stop_lat:String(s.lat),stop_lon:String(s.lon)})),
    trips:schedules.map((_,i)=>({trip_id:String(i),route_id:'r'+(i%lines.length),service_id:'weekday'})),
    calendar:[{service_id:'weekday',start_date:'20261101',end_date:'20261130',monday:'1',tuesday:'1',wednesday:'1',thursday:'1',friday:'1',saturday:'0',sunday:'0'}],
    stop_times:schedules.flatMap((calls,i)=>calls.map(([stop,arrival,departure],j)=>({trip_id:String(i),stop_id:String(stop),arrival_time:arrival,departure_time:departure,stop_sequence:String(j+1)}))),
  };
  return {id,name:id,dataUse:'synthetic',tables};
}
const trip=(from,to,start,end,endpoints=false)=>[[from,endpoints?'':start,start],[to,end,endpoints?'':end]];
const buses=()=>feed('b','3',[k,d],[trip(0,1,'09:30:00','09:50:00'),trip(1,0,'10:35:00','10:50:00')]);
const rail=()=>feed('j','2',[a,k],[trip(0,1,'09:00:00','09:20:00',true),trip(1,0,'11:00:00','11:20:00',true)],OITA_RAIL_LINES);
const scope={cityCode:'44201',date:p.date,crossBoundary:true,feedIds:['j'],lines:OITA_RAIL_LINES};
const prepare=(bus,train,extra={})=>prepareOitaRoundTrips({busFeeds:[bus],railFeeds:train?[train]:[],date:p.date,railScope:scope,busCoverageComplete:true,...extra});
const judge=(ctx,profile=p)=>judgeOitaRoundTrip(ctx,a,d,profile);

test('rail plus bus round trip; terminal blanks normalized without modifying input; no raw times in result',()=>{
  const r=rail();
  assert.deepEqual(judge(prepare(buses(),r)),{status:'rail_adds_option',bus:'fail',combined:'pass',railInput:'synthetic'});
  assert.equal(r.tables.stop_times[0].arrival_time,'');
});
test('valid connection is not counted if return transfer cannot be made',()=>{
  const r=rail();r.tables.stop_times[2].departure_time='10:52:00';
  assert.equal(judge(prepare(buses(),r)).status,'no_scheduled_roundtrip');
});
test('missing, expired, partial, and malformed data cannot produce no-service verdict',()=>{
  assert.equal(judge(prepare(buses(),null)).status,'unknown');
  assert.equal(judge(prepare(buses(),rail(),{railScope:{...scope,lines:['日豊本線']},busCoverageComplete:false}),{...p,deadline:'10:59'}).status,'unknown');
  const r=rail();r.tables.calendar[0].end_date='20261129';
  assert.equal(judge(prepare(buses(),r)).railInput,'not_loaded');
  const f=rail();f.tables.stops[0].stop_lat='';assert.equal(judge(prepare(buses(),f)).combined,'unknown');
});
test('an intermediate blank is not invented; incomplete bus baseline is not counted as a rail gain',()=>{
  const r=rail();r.tables.stop_times.splice(1,0,{...r.tables.stop_times[0],arrival_time:'',departure_time:'09:10:00',stop_sequence:'2'});
  r.tables.stop_times[2].stop_sequence='3';
  assert.equal(judge(prepare(buses(),r)).combined,'unknown');
  assert.equal(judge(prepare(buses(),rail(),{busCoverageComplete:false})).status,'combined_option_baseline_unknown');
});
test('calendar exception with current coverage is zero service, not expired coverage',()=>{
  const r=rail();r.tables.calendar_dates=[{service_id:'weekday',date:'20261130',exception_type:'2'}];
  assert.equal(judge(prepare(buses(),r)).status,'no_scheduled_roundtrip');
});
test('bus is retained as baseline, and batch can compare separate locations',()=>{
  const direct=feed('b','3',[a,d],[trip(0,1,'09:00:00','09:30:00'),trip(1,0,'10:40:00','11:00:00')]);
  const ctx=prepare(direct,null);
  const rs=judgeOitaBatch(ctx,[a,point('other',33.28,131.60)],[d],p);
  assert.deepEqual(rs.map(x=>[x.originId,x.status]),[['origin','bus_baseline'],['other','unknown']]);
});
test('unapproved input and invalid date are rejected',()=>{
  const r=rail();delete r.dataUse;assert.throws(()=>prepare(buses(),r),/利用条件/);
  assert.throws(()=>judge(prepare(buses(),rail()),{...p,date:'2026-12-01'}),/分析日/);
});

import {csvText,sha256,zip} from '../oita-mobility/lab/io.mjs';
import {runRailJourney} from '../oita-mobility/v2/rail-journey-worker.mjs';
import {activityOptions} from '../oita-mobility/gaps/engine.mjs';
const asZip=f=>zip(Object.fromEntries(Object.entries(f.tables).filter(([,rows])=>rows.length).map(([n,rows])=>[n+'.txt',csvText(rows)])));
test('browser worker reads locally supplied rail ZIP, requests only public bus data, returns no raw rows',async()=>{
 const bus=asZip(buses()),tr=asZip(rail()),requested=[],progress=[];
 const input={date:p.date,home:a,facilities:[d],options:activityOptions(p),railFile:tr,files:[{file:'bus.zip',name:'bus',sha256:await sha256(await bus.arrayBuffer())}]};
 const fetchPublic=async u=>{requested.push(String(u));return new Response(bus);};
 const r=await runRailJourney(input,m=>progress.push(m),fetchPublic);
 assert.deepEqual(r,{status:'combined_option_baseline_unknown',bus:'unknown',combined:'pass',railInput:'authorized'});
 assert.equal(requested.length,1);
 assert.ok(requested[0].endsWith('/data/gtfs/bus.zip'));
 assert.equal(progress.length,1);
 assert.equal((await runRailJourney({...input,date:'2026-12-01'},()=>{},fetchPublic)).reason,'date');
 await assert.rejects(runRailJourney({...input,railFile:new Blob()},()=>{},fetchPublic),/GTFS ZIP/);
});
