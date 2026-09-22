import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {zip,csvText,sha256} from '../oita-mobility/lab/io.mjs';
import {classify,populationSummary,comparePopulation,policyCost,opportunitySummary,demandRecord,aggregateDemand} from '../oita-mobility/v2/model.mjs';

const fields={
  agency:[{agency_id:'s',agency_name:'Synthetic test only',agency_url:'https://example.org',agency_timezone:'Asia/Tokyo'}],
  routes:[{route_id:'r',agency_id:'s',route_long_name:'Test',route_type:'3'}],
  stops:[{stop_id:'A',stop_name:'A',stop_lat:'33',stop_lon:'131'},{stop_id:'B',stop_name:'B',stop_lat:'33',stop_lon:'131.02'}],
  trips:[{trip_id:'out',route_id:'r',service_id:'s'},{trip_id:'back',route_id:'r',service_id:'s'}],
  calendar:[{service_id:'s',start_date:'20260901',end_date:'20260930',monday:'1',tuesday:'1',wednesday:'1',thursday:'1',friday:'1',saturday:'1',sunday:'1'}],
  calendar_dates:[{service_id:'s',date:'20261001',exception_type:'1'}],
  feed_info:[{feed_publisher_name:'Test only',feed_publisher_url:'https://example.org',feed_lang:'ja',feed_start_date:'20260901',feed_end_date:'20260930'}],
  stop_times:[['out','A','09:00:00','1'],['out','B','09:30:00','2'],['back','B','10:00:00','1'],['back','A','10:30:00','2']].map(([trip_id,stop_id,at,stop_sequence])=>({trip_id,stop_id,arrival_time:at,departure_time:at,stop_sequence,pickup_type:'0',drop_off_type:'0'}))
};
const bytes=zip(Object.fromEntries(Object.entries(fields).map(([k,v])=>[k+'.txt',csvText(v)])));
const buffer=await bytes.arrayBuffer();
const fixture={name:'Synthetic test only',file:'__atlas_v2_test.zip',sha256:await sha256(buffer)};
const catalog=JSON.parse(await fs.readFile(new URL('../oita-mobility/data/gtfs/catalog.json',import.meta.url)));
let messages=[];
globalThis.self={postMessage:r=>messages.push(r)};
globalThis.fetch=async url=>{const file=decodeURIComponent(String(url).split('/').at(-1));const b=file===fixture.file?buffer:await fs.readFile(new URL('../oita-mobility/data/gtfs/'+file,import.meta.url));return new Response(b)};
await import('../oita-mobility/v2/worker.mjs');
const options={departure:32400,activityFrom:34200,activityTo:34200,dwell:30,deadline:43200,legMinutes:90,maxTransfers:0,maxWalk:0,totalWalk:0,walkSpeed:4,walkFactor:1,wheelchair:false,reservation:'no',budget:null};
const request={mode:'journey',files:[fixture],home:{lat:33,lon:131},facilities:[{id:'b',name:'Test B',lat:33,lon:131.02}],options};
async function run(data){messages=[];await self.onmessage({data:{id:1,...data}});const final=messages.at(-1);assert(!final.error,final.error);assert.equal(final.done,true);return final;}

test('Worker returns a valid round trip with no fabricated fare',async()=>{const d=await run({...request,date:'2026-09-22'});const r=d.results[0].result;assert.equal(r.state,'candidate');assert.equal(r.homeAt,37800);assert.equal(r.cost,null);});
test('Expired feed with an added service exception cannot produce a round-trip candidate',async()=>{const d=await run({...request,date:'2026-10-01'});const r=d.results[0].result;assert.equal(r.state,'unknown');assert.equal(r.outbound,undefined);assert.equal(d.evidence.feeds[0].coverage,'outside');});
test('Valid walking-only candidate is preserved when transport data has expired',async()=>{const d=await run({...request,date:'2026-10-01',facilities:[{id:'near',name:'Near',lat:33,lon:131.001}],options:{...options,maxWalk:500,totalWalk:1000}});assert.equal(d.results[0].result.state,'candidate');});
test('Real Kamenoi expired date exposes no selectable trips',async()=>{const d=await run({mode:'trips',date:'2027-03-21',files:catalog.filter(f=>f.name==='亀の井バス')});assert.equal(d.evidence.feeds[0].coverage,'outside');assert.equal(d.trips.length,0);});
test('Missing population and unknown access cannot become improvement gains',()=>{const cells=[{id:'a',population2020:100},{id:'b',population2020:50},{id:'c',population2020:null}],before={a:{state:'not_found'},b:{state:'unknown'}},after={a:{state:'candidate'},b:{state:'candidate'}};const s=populationSummary(cells,before);assert.equal(s.knownPopulation,150);assert.equal(s.unknownPopulation,50);assert.equal(s.missingPopulationCells,1);assert.deepEqual(comparePopulation(cells,before,after),{gained:100,lost:0,uncertain:50,net:100});assert.equal(policyCost({cost:10000,gained:0}),null);assert.equal(policyCost({cost:null,gained:100}),null);});
test('Opportunity counts distinguish unknown from observed no candidate',()=>{assert.equal(opportunitySummary([{minutes:null,unknown:true}],30).label,'判定保留');assert.equal(opportunitySummary([{minutes:null,unknown:false}],30).label,'0');assert.deepEqual(opportunitySummary([{minutes:20,unknown:true},{minutes:null,unknown:true}],30),{candidates:1,unknown:1,label:'1'});});
test('Search, self-reported outcome, and privacy-safe aggregation stay separate',()=>{const r=demandRecord({cityCode:'44201',category:'hospital',hour:36000,state:'unknown',month:'2026-09',home:{lat:33,lon:131},name:'never save'});assert.equal(r.home,undefined);assert.equal(r.name,undefined);const five=Array.from({length:5},()=>r);assert.equal(aggregateDemand(five,{threshold:5})[0].count,5);assert.equal(aggregateDemand(five.slice(0,4),{threshold:5}).length,0);assert.equal(aggregateDemand([...five,{...r,kind:'reported_unmet'}]).length,2);assert.equal(classify({searchIncomplete:true}), 'unknown');});
