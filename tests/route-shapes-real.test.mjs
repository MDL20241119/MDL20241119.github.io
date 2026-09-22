import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {importGTFS,distance} from '../oita-mobility/lab/gtfs.mjs';
import {prepareAccess,evaluateActivity} from '../oita-mobility/access/engine.mjs';
import {indexShapes,geometryForLeg,attachRouteGeometry} from '../oita-mobility/v2/route-geometry.mjs';
import {buildShops} from '../scripts/build-shopping-destinations.mjs';

const root=new URL('../oita-mobility/',import.meta.url);
const read=async p=>JSON.parse(await fs.readFile(new URL(p,root),'utf8'));
const catalog=await read('data/gtfs/catalog.json');

test('All bundled feeds render selected trip shapes in boarding-to-alighting order',async()=>{
 let checked=0,matched=0,curved=0;
 const reports=[];
 for(const row of catalog){
  const bytes=await fs.readFile(new URL('data/gtfs/'+row.file,root));
  const feed=await importGTFS(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),row.name,row.file);
  const network=prepareAccess([feed],'2026-09-22'),shapes=indexShapes([feed]);
  const unique=[...new Map(network.trips.filter(t=>t.calls.length>3).map(t=>[t.shape,t])).values()];
  const samples=unique.filter((_,i)=>i%Math.max(1,Math.floor(unique.length/12))===0).slice(0,12);
  let count=0;
  for(const trip of samples){
   const first=trip.calls[1],last=trip.calls.at(-2);
   if(first.stop_sequence===last.stop_sequence)continue;
   const leg={mode:'bus',tripKey:trip.key,boardSequence:first.stop_sequence,alightSequence:last.stop_sequence,from:network.stops[first.stopKey],to:network.stops[last.stopKey]};
   const geometry=geometryForLeg(leg,network,shapes);checked++;
   if(geometry.kind==='gtfs-shape'){
    matched++;count++;
    assert(geometry.points.every(p=>p.length===2&&p.every(Number.isFinite)));
    assert(distance(leg.from,{lat:geometry.points[0][0],lon:geometry.points[0][1]})<=200);
    assert(distance(leg.to,{lat:geometry.points.at(-1)[0],lon:geometry.points.at(-1)[1]})<=200);
    if(geometry.points.length>2)curved++;
   }
  }
  reports.push({feed:row.name,samples:samples.length,matched:count});
 }
 assert(checked>=100,'Test must cover real routes across feeds');
 assert(matched/checked>.9,JSON.stringify(reports));
 assert(curved/checked>.85,'Bus paths must contain intermediate road geometry');
 console.log(JSON.stringify({checked,matched,curved,reports}));
});

test('Expanded shops retain original identifiers, unique source links and municipality-correct positions',async()=>{
 const places=await read('access/destinations.json'),snapshot=await read('access/shopping-sources.json');
 const features=(await read('gaps/data/municipalities.geojson')).features;
 const shops=buildShops(snapshot,features);
 assert.deepEqual(places.filter(p=>p.category==='shopping'),shops);
 assert.equal(places.length,333);assert.equal(shops.length,157);
 assert.equal(new Set(places.map(p=>p.id)).size,places.length);
 assert.equal(new Set(shops.map(p=>p.city)).size,17);
 for(const p of shops){assert(p.address);assert(p.sourceUrl.startsWith('https://'));assert(!p.sourceUrl.includes('shinsenichiba.'));}
 assert(shops.some(p=>p.name.includes('富士見が丘')));
});

test('A real Kusu round trip carries road geometry for both bus directions',async()=>{
 const row=catalog.find(f=>f.name==='玖珠観光バス');
 const bytes=await fs.readFile(new URL('data/gtfs/'+row.file,root));
 const feed=await importGTFS(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),row.name,row.file);
 const network=prepareAccess([feed],'2026-09-22'),shapes=indexShapes([feed]);
 const stops=Object.values(network.stops);
 const origin=stops.find(s=>s.name==='豊後森');
 const target=stops.find(s=>s.name==='塚脇');
 assert(origin&&target,stops.map(s=>s.name).join(','));
 const options={departure:28800,activityFrom:36000,activityTo:43200,dwell:30,deadline:64800,legMinutes:120,maxTransfers:0,maxWalk:200,totalWalk:1000,walkSpeed:4,walkFactor:1.3,wheelchair:false,reservation:'no',budget:null};
 const result=attachRouteGeometry(evaluateActivity(network,origin,{...target,id:'test-only',name:'塚脇'},options),network,shapes);
 assert(result.outbound&&result.inbound,JSON.stringify(result.reasons));
 for(const direction of ['outbound','inbound']){
  const buses=result[direction].path.filter(l=>l.mode==='bus');
  assert(buses.length);
  assert(buses.every(l=>l.geometry.kind==='gtfs-shape'&&l.geometry.points.length>2));
 }
});
