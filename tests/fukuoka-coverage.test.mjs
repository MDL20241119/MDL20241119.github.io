import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {partitionAnalysisFeeds,unselectedTransportReferences} from '../fukuoka-mobility/assets/transport-coverage.mjs';
import {prepareAccess,evaluateActivity} from '../fukuoka-mobility/access/engine.mjs';
import {defaultProfile,validateProfile,feedCoverage,prepareGapNetwork,measureSupply,activityCriterion,departurePattern} from '../fukuoka-mobility/gaps/engine.mjs';
import {distance,importGTFS,buildNetwork} from '../fukuoka-mobility/lab/gtfs.mjs';
import {scopeFeed} from '../fukuoka-mobility/lab/feed-scope.mjs';

const date='2026-09-14',home={lat:33.6,lon:130.4},destination={id:'D',name:'目的地',lat:33.6,lon:130.42};
const options={departure:9*3600,deadline:12*3600,activityFrom:9.5*3600,activityTo:10*3600,dwell:30,legMinutes:90,maxWalk:0,totalWalk:0,walkSpeed:4,walkFactor:1,maxTransfers:1,budget:null,wheelchair:false,reservation:'no'};
const confirmed={open:'09:00',close:'12:00',acceptance:'yes',walking:'yes',entry:'yes',comfort:'yes',roundCost:200};
function fixture(id='F'){
  return {id,name:id,hash:id+'-hash',source:'https://example.com/'+id,tables:{
    stops:[{stop_id:'A',stop_name:'自宅',stop_lat:String(home.lat),stop_lon:String(home.lon)},{stop_id:'B',stop_name:'目的地',stop_lat:String(destination.lat),stop_lon:String(destination.lon)}],
    routes:[{route_id:'R',route_type:'3'}],trips:[{trip_id:'O',service_id:'S',route_id:'R'},{trip_id:'I',service_id:'S',route_id:'R'}],
    calendar:[{service_id:'S',start_date:'20260901',end_date:'20260930',monday:'1',tuesday:'1',wednesday:'1',thursday:'1',friday:'1',saturday:'1',sunday:'1'}],calendar_dates:[],
    feed_info:[{feed_start_date:'20260901',feed_end_date:'20260930'}],
    stop_times:[['O','A','09:00:00',1],['O','B','09:20:00',2],['I','B','11:00:00',1],['I','A','11:20:00',2]].map(([trip_id,stop_id,t,sequence])=>({trip_id,stop_id,arrival_time:t,departure_time:t,stop_sequence:String(sequence),pickup_type:'0',drop_off_type:'0'}))
  }};
}

test('a calendar extending beyond feed_info cannot establish access from an expired timetable',()=>{
  const expired=fixture('expired');expired.tables.feed_info[0].feed_end_date='20260913';
  assert(evaluateActivity(prepareAccess([expired],date),home,destination,options,confirmed).outbound,'Fixture demonstrates the false positive if feed_info is ignored');
  const partition=partitionAnalysisFeeds([expired],date),result=evaluateActivity(prepareAccess(partition.usable,date),home,destination,options,confirmed);
  assert.equal(partition.usable.length,0);assert.equal(partition.health[0].coverage,'outside');assert.equal(partition.health[0].usedInCalculation,false);
  assert.equal(result.outbound,undefined);assert.equal(result.status,'unknown');
});

test('current routes survive exclusion and every selected source keeps coverage evidence',()=>{
  const current=fixture('current'),future=fixture('future'),undated=fixture('undated');future.tables.feed_info[0].feed_start_date='20260915';delete undated.tables.feed_info;undated.tables.calendar=[];
  const partition=partitionAnalysisFeeds([current,future,undated],date);
  assert.deepEqual(partition.usable,[current]);assert.deepEqual(partition.health.map(f=>[f.coverage,f.usedInCalculation]),[['known',true],['outside',false],['unknown',false]]);
  assert.equal(evaluateActivity(prepareAccess(partition.usable,date),home,destination,options,confirmed).status,'feasible');
});

test('deselected feeds remain unknown positions instead of disappearing from gap assessment',()=>{
  const transport={feeds:[{id:'chosen',name:'選択した路線',sha256:'a'},{id:'omitted',name:'選択外の路線',sha256:'b',downloadUrl:'https://example.com/b.zip'}],stops:[{id:'1',feedIndex:0,name:'遠方',lat:34,lon:131},{id:'2',feedIndex:1,name:'近隣',...home}]};
  const refs=unselectedTransportReferences(transport,[{sha256:'a'}]);
  assert.equal(refs.stops.length,1);assert.equal(refs.stops[0].sourceHash,'b');assert.equal(refs.stops[0].coverage,'unselected');assert.equal(refs.feeds[0].usedInCalculation,false);
  const ctx={network:{excluded:0},stops:[],unknownStops:refs.stops,byStop:new Map(),known:true};
  const result=measureSupply(ctx,home,defaultProfile('40130',['chosen.zip']));
  assert.equal(result.status,'unknown');assert(result.criteria.every(c=>c.state==='unknown'));
  assert.equal(unselectedTransportReferences(transport,[{sha256:'a'},{sha256:'b'}]).stops.length,0);
});

test('an unmatched snapshot version remains uncertain and a broken feed reference fails closed',()=>{
  const transport={feeds:[{id:'F',name:'F',sha256:'old'}],stops:[{id:'A',feedIndex:0,name:'A',...home}]};
  assert.equal(unselectedTransportReferences(transport,[{id:'F',sha256:'new'}]).stops.length,1);
  assert.throws(()=>unselectedTransportReferences({feeds:[],stops:transport.stops},[]),/出典/);
});

test('the real Hanebus stop omitted from the old position inventory is retained when deselected',async()=>{
  const root=new URL('../fukuoka-mobility/',import.meta.url),read=async path=>JSON.parse(await readFile(new URL(path,root),'utf8'));
  const [transport,reference]=await Promise.all([read('data/map-data.json'),read('gaps/data/reference-stops.json')]);
  const stop=transport.stops.find(s=>s.name==='ゆめモール'&&s.departures?.[0]>=6);assert(stop);
  assert(Math.min(...reference.stops.map(s=>distance(stop,s)))>500,'The old inventory alone cannot guard this real current service');
  const selected=transport.feeds.filter((_,index)=>index!==stop.feedIndex).map(f=>({sha256:f.sha256}));
  const omitted=unselectedTransportReferences(transport,selected);assert(omitted.stops.some(s=>s.name===stop.name&&s.lat===stop.lat&&s.lon===stop.lon));
  const result=measureSupply({network:{excluded:0},stops:[],unknownStops:[...reference.stops,...omitted.stops],byStop:new Map(),known:true},stop,defaultProfile('40211',['selected.zip']));
  assert.equal(result.criteria.find(c=>c.id==='frequency').state,'unknown');
});

test('legacy profiles receive interval defaults and interval-only profiles retain strict validation',()=>{
  const legacy=defaultProfile('40130',['source.zip']);delete legacy.intervalOn;delete legacy.maximumInterval;delete legacy.wheelchair;delete legacy.reservation;
  validateProfile(legacy);assert.equal(legacy.intervalOn,false);assert.equal(legacy.maximumInterval,120);assert.equal(legacy.wheelchair,false);assert.equal(legacy.reservation,'no');
  const interval={...legacy,distanceOn:false,frequencyOn:false,activityOn:false,intervalOn:true};assert.equal(validateProfile(interval),interval);
  for(const invalid of [{intervalOn:'true'},{maximumInterval:0},{maximumInterval:1441},{maximumInterval:'120'},{wheelchair:1},{reservation:'yes'}])assert.throws(()=>validateProfile({...interval,...invalid}));
});

test('incomplete network coverage permits observed supply but never turns missing data into a deficit',()=>{
  const p={...defaultProfile('40130',['F']),date,minimumTrips:1,distanceM:0,frequencyRadius:0};
  const ctx=prepareGapNetwork([fixture()],date);assert.equal(ctx.networkCoverageComplete,false);
  const sufficient=measureSupply(ctx,home,p);assert.equal(sufficient.status,'pass');assert.equal(sufficient.departures,1);
  const insufficient=measureSupply(ctx,{lat:34,lon:131},p);assert.equal(insufficient.status,'unknown');assert.equal(insufficient.departures,null);
});

test('a missing intermediate operator keeps a failed round trip unknown away from known reference stops',()=>{
  const feed=fixture();feed.tables.stop_times=feed.tables.stop_times.filter(c=>c.trip_id==='O');feed.tables.trips=feed.tables.trips.filter(t=>t.trip_id==='O');
  const p={...defaultProfile('40130',['F']),date,activityOn:true,destinations:['D'],maxWalk:0,totalWalk:0,walkFactor:1};
  const ctx=prepareGapNetwork([feed],date,[]);assert.equal(activityCriterion(ctx,home,[destination],p).state,'unknown');
  ctx.networkCoverageComplete=true;assert.equal(activityCriterion(ctx,home,[destination],p).state,'fail');
});

test('hourly counts deduplicate a trip within an hour and keep the documented separate hourly appearances',()=>{
  const pattern=departurePattern([{trip:'a',time:9*3600},{trip:'a',time:9*3600+60},{trip:'a',time:10*3600},{trip:'b',time:11*3600}],9*3600,12*3600);
  assert.equal(pattern.windowTrips,2);assert.equal(pattern.hourly[9],1);assert.equal(pattern.hourly[10],1);assert.equal(pattern.hourly[11],1);
  assert.equal(pattern.first,9*3600);assert.equal(pattern.last,11*3600);assert.equal(pattern.maximumIntervalMinutes,60);
});

test('an interval with no known timetable does not pass just because the selected window is short',()=>{
  const p={...defaultProfile('40130',['missing.zip']),distanceOn:false,frequencyOn:false,activityOn:false,intervalOn:true,serviceStart:'06:00',serviceEnd:'08:00',maximumInterval:120};
  const result=measureSupply({network:{excluded:0},stops:[],unknownStops:[],byStop:new Map(),known:false,networkCoverageComplete:false},home,p);
  assert.equal(result.criteria[0].state,'unknown');assert.equal(result.criteria[0].value,null);assert.equal(result.status,'unknown');
});

test('the actual subway analysis snapshot allows only its four explicitly recorded dates',async()=>{
  const root=new URL('../fukuoka-mobility/',import.meta.url),catalog=JSON.parse(await readFile(new URL('data/gtfs/catalog.json',root),'utf8'));
  const source=catalog.find(f=>f.file.startsWith('fukuoka-subway__'));assert(source);
  const buffer=await readFile(new URL('data/gtfs/'+source.file,root)),feed=await importGTFS(buffer.buffer.slice(buffer.byteOffset,buffer.byteOffset+buffer.byteLength),source.name,source.id);
  assert.match(feed.tables.feed_info[0].feed_version,/^analysis-snapshot-/);
  assert.deepEqual(feed.tables.calendar_dates.map(r=>r.date).sort(),['20260914','20260915','20260919','20260920']);
  for(const d of ['20260914','20260915','20260919','20260920'])assert.equal(feedCoverage(feed,d),'known',d);
  for(const d of ['20260913','20260916','20260917','20260918','20260921']){
    assert.equal(feedCoverage(feed,d),'unknown',d);const partition=partitionAnalysisFeeds([feed],d);assert.equal(partition.usable.length,0);assert.equal(prepareGapNetwork([feed],d).known,false);
  }
});

test('Oita cross-border source trips belong only to their actual agencies and retained routes stay complete',async()=>{
  const root=new URL('../fukuoka-mobility/',import.meta.url),catalog=JSON.parse(await readFile(new URL('data/gtfs/catalog.json',root),'utf8'));
  const sources=catalog.filter(f=>f.file.startsWith('gtfs10_highway')&&f.file.includes('-fukuoka__'));assert.equal(sources.length,3);
  let nishitetsuTrips=0;
  for(const source of sources){
    const buffer=await readFile(new URL('data/gtfs/'+source.file,root)),full=await importGTFS(buffer.buffer.slice(buffer.byteOffset,buffer.byteOffset+buffer.byteLength),source.name,source.id),scoped=scopeFeed(full,source);
    const selectedTrips=new Set(scoped.tables.trips.map(t=>t.trip_id));assert.deepEqual(scoped.tables.stop_times,full.tables.stop_times.filter(c=>selectedTrips.has(c.trip_id)));
    const agency=scoped.tables.agency.find(a=>a.agency_name==='西鉄バス');assert(agency,source.name);
    const routes=new Set(scoped.tables.routes.filter(r=>r.agency_id===agency.agency_id).map(r=>r.route_id));assert(routes.size>0);
    nishitetsuTrips+=buildNetwork([scoped],date,{includeOvernight:false}).trips.filter(t=>routes.has(t.routeId)).length;
  }
  const operators=JSON.parse(await readFile(new URL('data/operators.json',root),'utf8')),nishitetsu=operators.operators.find(o=>o.name==='西鉄バス');assert(nishitetsu);
  assert.equal(nishitetsu.timetable.scheduledTrips[0],nishitetsuTrips);assert.equal(nishitetsu.timetable.status,'partial');assert.equal(operators.coverageComplete,false);
});
