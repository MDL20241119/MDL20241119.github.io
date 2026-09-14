import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {importGTFS,buildNetwork,supply} from '../fukuoka-mobility/lab/gtfs.mjs';
import {defaultProfile,validateProfile,prepareGapNetwork,measureSupply} from '../fukuoka-mobility/gaps/engine.mjs';
import {exampleComparison} from '../fukuoka-mobility/lab/example.mjs';
import {calculateBC,forecastSeries} from '../fukuoka-mobility/calculations.js';
import {isFukuokaAreaPoint} from '../fukuoka-mobility/assets/geography.mjs';
const root=new URL('../fukuoka-mobility/',import.meta.url),read=async p=>JSON.parse(await fs.readFile(new URL(p,root),'utf8'));
const [catalog,geo,boundary,analysis,facilities,shops,metadata]=await Promise.all(['data/gtfs/catalog.json','data/map-data.json','gaps/data/municipalities.geojson','data/analysis.json','access/destinations.json','access/shopping.json','data/catalog.json'].map(read));
assert.equal(boundary.features.length,60);assert.equal(analysis.municipal_population.length,60);assert.equal(analysis.municipal_population.reduce((v,p)=>v+p.population,0),5135214);
assert.equal(analysis.commute_od.filter(x=>x.level==='ward').length,49);assert.equal(analysis.stop_actuals.length,40);assert.equal(analysis.expenses.reduce((v,e)=>v+e.yen,0),analysis.finance[0].cost);
assert.equal(metadata.overview.destinations,facilities.length+shops.length);assert(shops.length>100);assert.equal(new Set(metadata.datasets.map(d=>d.id)).size,metadata.datasets.length);
for(const f of [...facilities,...shops]){assert(f.municipalityCode.startsWith('40'));assert(f.lat>32.7&&f.lat<34.4&&f.lon>129.9&&f.lon<131.5);assert(f.sourceUrl.startsWith('https://'));}
const selected=catalog.filter(f=>f.current&&f.analysisReady);validateProfile(defaultProfile('40206',selected.map(f=>f.file)));
assert.equal(catalog.length,geo.feeds.length);assert.equal(geo.meta.currentFeeds,selected.length);
for(const f of catalog){const b=await fs.readFile(new URL('data/gtfs/'+f.file,root));assert.equal(createHash('sha256').update(b).digest('hex'),f.sha256);}
for(const [i,f]of geo.feeds.entries())if(f.dataStatus!=='current')for(const s of geo.stops.filter(s=>s.feedIndex===i))assert.equal(s.departures[0],null);
const chosen=selected.find(x=>x.file.includes('TagawaCityCommunityBus'));const b=await fs.readFile(new URL('data/gtfs/'+chosen.file,root));const feed=await importGTFS(b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength),chosen.name,chosen.id);
const n=buildNetwork([feed],'2026-09-14'),sp=supply(n);assert(sp.trips>0);assert.equal(sp.trips,geo.feeds.find(f=>f.sha256===chosen.sha256).scheduledTrips[0]);
const ctx=prepareGapNetwork([feed],'2026-09-14'),p=defaultProfile('40206',[chosen.file]),s=ctx.stops[0];assert(s);const measured=measureSupply(ctx,s,p);assert(measured.nearest.meters<1);
const ex0=exampleComparison(feed,false),ex1=exampleComparison(feed,true);assert(ex0&&ex1);
const bc=calculateBC({share:.5,minutes:5,annualCost:300000,rate:.04,users:10000,timeValue:30});assert.equal(bc.annualBenefit,750000);assert.equal(bc.bc,2.5);assert.equal(calculateBC({share:.5,minutes:5,annualCost:0,rate:0,users:0,timeValue:30}).bc,null);
assert.deepEqual(forecastSeries([303889,335607,399157,482037,524221]).flat,[524221,524221]);
function checkCoordinates(coordinates){
  if(typeof coordinates[0]==='number')assert(isFukuokaAreaPoint({lat:coordinates[1],lon:coordinates[0]}),'All municipal areas, including islands, must allow resource registration');
  else coordinates.forEach(checkCoordinates);
}
for(const m of boundary.features){checkCoordinates(m.geometry.coordinates);for(const res of [500,1000]){const mesh=await read('gaps/data/'+m.properties.code+'-'+res+'.geojson');assert(mesh.features.length>0);assert.equal(new Set(mesh.features.map(f=>f.id)).size,mesh.features.length);}}
for(const point of [null,{lat:NaN,lon:130.5},{lat:34,lon:Infinity},{lat:0,lon:0},{lat:33.6,lon:132}])assert.equal(isFukuokaAreaPoint(point),false);
console.log(`PASS: 60 municipalities, ${catalog.length} GTFS / ${selected.length} current, ${facilities.length+shops.length} destinations; census, source hashes, OD, financial reconciliation, scenarios and Fukuoka profile validation.`);
