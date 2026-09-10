import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {outcome,usedDatasets,matchDatasets,overview,dateText,httpURL} from '../oita-mobility/catalog/model.mjs';
import {feedCoverage} from '../oita-mobility/gaps/engine.mjs';
const base=new URL('../oita-mobility/',import.meta.url);
const read=async name=>JSON.parse(await readFile(new URL(name,base),'utf8'));
const [c,g,p,r,b]=await Promise.all(['data/catalog.json','data/gtfs/catalog.json','access/destinations.json','gaps/resources.json','gaps/data/municipalities.geojson'].map(read));
assert.equal(c.schemaVersion,1);
for(const [name,hash]of Object.entries(c.sourceHashes))assert.equal(createHash('sha256').update(await readFile(new URL(name,base))).digest('hex'),hash,name+' must be regenerated when changed');
assert.equal(new Set(c.datasets.map(d=>d.id)).size,c.datasets.length);
assert.equal(overview(c).destinations,p.length);assert.equal(overview(c).municipalities,b.features.length);
assert.equal(c.overview.resources,r.length);
assert.equal(c.datasets.filter(d=>d.scope==='バス時刻表').length,g.length);
for(const d of c.datasets){
 for(const file of d.localFiles)await readFile(new URL(file,base));
 if(d.dataClass==='OPEN')assert(d.license&&httpURL(d.licenseUrl));
 assert(!['VERIFIED','PARTNER'].includes(d.dataClass),'No such verification/provision records currently exist');
 if(d.scope==='バス時刻表')assert.equal(d.dataAsOf,null,'GTFS validity is not an acquisition or baseline date');
 if(d.scope==='移動資源'){assert.equal(d.retrievedAt,null);assert.equal(d.dataClass,null);assert(d.checkedAt);}
 if(d.id==='dest-shopping'){assert.equal(d.retrievedAt,null);assert.equal(d.dataAsOf,null);assert.equal(d.license,null);}
 if(d.id.startsWith('dest-public-')){assert.equal(d.dataAsOf,null);assert(d.sourceUpdatedAt);}
 if(d.status==='PLANNED'){assert.equal(d.records,null);assert.equal(d.localFiles.length,0);}
}
assert.equal(dateText(null),'未確認');
assert.equal(httpURL('javascript:alert(1)'),null);
for(const row of c.gap.rows){
 assert(b.features.some(f=>f.properties.code===row.code));
 for(const cell of Object.values(row.cells)){assert(cell.evidence);assert.equal(cell.status,cell.count?'PARTIAL':'NOT_AVAILABLE');}
 // A city with no bundled bus point must be marked uncollected, never as a confirmed transport desert.
 if(!row.cells.bus.count)assert(row.cells.bus.evidence.includes('実際のサービスの有無は未確認'));
}
const selected=usedDatasets(c,{sources:[{hash:g[0].sha256}],facilityIds:[p[0].id]});
assert.equal(selected.filter(d=>d.scope==='バス時刻表').length,1);
assert.equal(selected.filter(d=>d.scope==='目的地').length,1);
assert(!selected.some(d=>d.id==='population-2020'));
assert.equal(usedDatasets(c,{sources:[{name:'Unknown custom feed'}]}).length,0,'Missing hashes must not match unrelated datasets');
assert.equal(usedDatasets(c,{includeBoundary:true,includePopulation:true}).length,2);
assert(matchDatasets(c,{category:'healthcare',query:'医療情報ネット'}).some(d=>d.id==='dest-hospitals'));
assert.equal(matchDatasets(c,{dataClass:'VERIFIED'}).length,0);
const evidence={feeds:[{coverage:'known'}],excluded:0};
assert.equal(outcome({status:'unknown',dataEvidence:evidence}),'NOT_FOUND');
assert.equal(outcome({status:'unknown',dataEvidence:{...evidence,excluded:1}}),'INSUFFICIENT_DATA');
assert.equal(outcome({status:'unknown',dataEvidence:{feeds:[{coverage:'outside'}],excluded:0}}),'INSUFFICIENT_DATA');
assert.equal(outcome({status:'unknown',searchIncomplete:true,dataEvidence:evidence}),'INSUFFICIENT_DATA');
assert.equal(outcome({status:'unknown'}),'INSUFFICIENT_DATA','Legacy results without provenance cannot claim an exhaustive search');
assert.equal(outcome({status:'feasible',outbound:{},inbound:{},dataEvidence:evidence}),'AVAILABLE');
assert.equal(outcome({status:'conditional',outbound:{},inbound:{},dataEvidence:evidence}),'CONDITIONAL');
assert.equal(outcome({status:'not_met',reasons:['受付条件を満たさない']}),'NOT_FOUND');
for(const layer of c.layers){if(!layer.available){assert.equal(layer.count,null);assert.equal(layer.datasetIds.length,0);}}

// Exercise the actual worker boundary: hash verification and evidence accompany results.
const file=g.find(f=>f.name==='玖珠観光バス');assert(file);
const originalFetch=globalThis.fetch,messages=[];
globalThis.self={postMessage:m=>messages.push(m)};
globalThis.fetch=async url=>new Response(await readFile(new URL(url,new URL('access/',base))));
await import('../oita-mobility/access/worker.mjs');
await self.onmessage({data:{id:42,files:[file],date:'2026-09-09',home:{lat:33.28,lon:131.15},facilities:[{id:'TEST',name:'検証用（非公開）',lat:33.28,lon:131.15}],conditions:{TEST:{acceptance:'no'}},options:{departure:32400,deadline:57600,activityFrom:36000,activityTo:39600,dwell:30,legMinutes:60,maxWalk:500,totalWalk:1000,walkSpeed:4,walkFactor:1.3,maxTransfers:1}}});
const final=messages.find(m=>m.results);assert(final,JSON.stringify(messages));
assert.equal(final.sources.length,1);assert.equal(final.sources[0].hash,file.sha256);
assert.equal(final.results[0].dataEvidence.feeds[0].hash,file.sha256);
assert.equal(final.results[0].status,'not_met');
globalThis.fetch=originalFetch;delete globalThis.self;
console.log('PASS: source integrity, exact selected provenance, date separation, no invented availability, four result states, real GTFS worker.');
