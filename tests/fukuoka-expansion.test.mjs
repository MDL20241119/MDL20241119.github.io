import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {gunzipSync} from 'node:zlib';
import {importGTFS,validateFeeds,buildNetwork} from '../fukuoka-mobility/lab/gtfs.mjs';
import {scopeFeed} from '../fukuoka-mobility/lab/feed-scope.mjs';
import {createWalkingGraph} from '../fukuoka-mobility/access/walking.mjs';
import {prepareGapNetwork,measureSupply,defaultProfile} from '../fukuoka-mobility/gaps/engine.mjs';
const root=new URL('../fukuoka-mobility/',import.meta.url),read=async p=>{const b=await fs.readFile(new URL(p,root));return JSON.parse(p.endsWith('.gz')?gunzipSync(b):b)};

test('Saga routes keep complete cross-border journeys without assigning all agencies to each operator',async()=>{
  const catalog=await read('data/gtfs/catalog.json'),source=catalog.find(f=>f.file.startsWith('saga-fukuoka'));
  const buffer=await fs.readFile(new URL('data/gtfs/'+source.file,root)),full=await importGTFS(buffer.buffer.slice(buffer.byteOffset,buffer.byteOffset+buffer.length),source.name,source.id),scoped=scopeFeed(full,source);
  assert.equal(scoped.tables.routes.length,22);assert.equal(source.fukuokaStopIds.length,740);assert.equal(validateFeeds([scoped]).errors,0);
  assert.deepEqual(scoped.tables.agency.map(a=>a.agency_name).sort(),['昭和自動車株式会社','祐徳自動車株式会社'].sort());
  const trips=new Set(scoped.tables.trips.map(t=>t.trip_id));assert.deepEqual(scoped.tables.stop_times,full.tables.stop_times.filter(c=>trips.has(c.trip_id)),'Do not clip calls at the county boundary');
  assert(scoped.tables.stops.some(s=>!source.fukuokaStopIds.includes(s.stop_id)));
  const data=await read('data/operators.json'),n=buildNetwork([scoped],'20260914',{includeOvernight:false});
  for(const agency of scoped.tables.agency){const ownRoutes=new Set(scoped.tables.routes.filter(r=>r.agency_id===agency.agency_id).map(r=>r.route_id)),operator=data.operators.find(r=>r.sourceNames.includes(agency.agency_name));assert(operator);assert.equal(operator.timetable.scheduledTrips[0],n.trips.filter(t=>ownRoutes.has(t.routeId)).length);}
  assert.equal(full.tables.agency.length,5,'Original input remains intact');
  const geo=await read('data/map-data.json');for(const stop of geo.stops)for(let d=0;d<3;d++)if(stop.departures[d]!==null)assert.equal(Object.values(stop.routeDepartures).reduce((n,v)=>n+v[d],0),stop.departures[d],stop.name+' per-route totals must equal all-agency source departures');
});

test('medical source rows are all accounted for, and unlocated records stay explicit',async()=>{
  const audit=await read('data/medical-audit.json'),places=(await read('access/destinations.json')).filter(p=>p.source==='厚生労働省 医療情報ネット');
  assert.equal(places.length,10205);assert.equal(audit.unlocated.length,321);assert.equal(Object.values(audit.counts).reduce((n,c)=>n+c.sourceRows,0),10526);
  for(const [k,c] of Object.entries(audit.counts))assert.equal(c.sourceRows,c.located+c.unlocated);
  const ids=new Set(places.map(p=>p.id));for(const p of audit.unlocated)assert(!ids.has(p.id));
  const example=places.find(p=>p.category==='pharmacy'&&p.openingHours),detail=await read(example.medicalHoursFile);assert(detail.facilities[example.id].schedules.length);assert(detail.facilities[example.id].schedules[0].days);
});

test('walk graph follows connected roads, one-way edges and stairs, and never bridges disconnected lines',()=>{
  const graph=createWalkingGraph({meta:{},nodes:[[33,130],[33,130.001],[33.001,130.001],[33.001,130],[33.0001,130]],edges:[[0,1,95,0],[1,2,111,1],[2,3,95,0],[3,2,95,0],[2,1,111,1],[1,0,95,0]]});
  const a={lat:33,lon:130},b={lat:33.001,lon:130};assert.equal(graph.route(a,b,500,false).meters,301);assert.equal(graph.route(a,b,500,true).meters,Infinity);assert.equal(graph.route(a,b,200,false).meters,Infinity);
  const isolated=createWalkingGraph({meta:{},nodes:[[33,130],[33,130.001],[33.0001,130],[33.0001,130.001]],edges:[[0,1,95,0],[2,3,95,0]]});assert.equal(isolated.route(a,{lat:33.0001,lon:130},500,false).meters,Infinity);
  assert.equal(graph.route({lat:34,lon:131},b,500,false).meters,Infinity);
});

test('an unverified nearby railway or bus stop prevents a false transport-gap label',()=>{
  const point={lat:33.6,lon:130.4},profile=defaultProfile('40130',['source']);
  const ctx={network:{excluded:0},stops:[],unknownStops:[{...point,name:'時刻表未取得の駅'}],byStop:new Map(),known:true};
  assert.equal(measureSupply(ctx,point,profile).status,'unknown');
});
