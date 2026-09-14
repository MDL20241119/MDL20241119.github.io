import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {selectOperators,summarize,csvText} from '../fukuoka-mobility/operators/model.mjs';

const root=new URL('../fukuoka-mobility/',import.meta.url);
const read=async name=>JSON.parse(await readFile(new URL(name,root),'utf8'));
const [data,bus,rail,geo,catalog]=await Promise.all(['data/operators.json','data/bus-stop-inventory.geojson','data/rail.json','data/map-data.json','data/gtfs/catalog.json'].map(read));

test('every source position and feed is accounted for, with current source hashes',async()=>{
  for(const [path,expected]of Object.entries(data.sourceHashes))assert.equal(createHash('sha256').update(await readFile(new URL(path,root))).digest('hex'),expected,path);
  for(const [field,source]of [['busIndices',bus.features],['stationIndices',rail.stations.features],['lineIndices',rail.lines.features]]){
    const indices=data.operators.flatMap(r=>r[field]);assert.equal(indices.length,source.length);
    assert.deepEqual(indices.toSorted((a,b)=>a-b),source.map((_,i)=>i),'No source omitted or assigned twice: '+field);
  }
  for(const r of data.operators){
    for(const i of r.busIndices)assert(r.sourceNames.includes(bus.features[i].properties.P11_002));
    for(const i of r.stationIndices)assert(r.sourceNames.includes(rail.stations.features[i].properties.N02_004));
  }
  assert.deepEqual([...new Set(data.operators.flatMap(r=>r.feedIds))].sort(),catalog.map(f=>f.id).sort());
  assert.equal(new Set(data.operators.map(r=>r.id)).size,data.operators.length);
});

test('required operators distinguish complete positions from partial or missing schedules',()=>{
  const busRows=selectOperators(data,{operator:'nishitetsu-bus'});
  assert.equal(summarize(busRows).bus,4065);
  const highway=busRows.find(r=>r.name==='西鉄バス');assert(highway?.timetable);
  assert.deepEqual(highway.timetable.scheduledTrips,[60,64,64]);assert.match(highway.timetable.note,/網羅は未確認/);
  const expected=[['nishitetsu-rail',0,73,1],['jr-kyushu',0,165,1],['jr-kyushu-bus',76,0,1]];
  for(const [id,busCount,stations,providers]of expected){
    const rows=selectOperators(data,{operator:id});assert.deepEqual(summarize(rows),{providers,bus:busCount,stations,stops:0,timetable:0});
    for(const r of rows){assert.equal(r.timetable,null);assert(r.officialTimetableUrl);assert.equal(r.realtime,null);assert.equal(r.status,'location');assert(r.missingReason.includes('未取得'));}
  }
  assert.equal(data.coverageComplete,false);assert(data.missingCategories.some(r=>r.name.includes('全交通事業者名簿')));
});

test('invalid or expired data is not represented as zero service or ready for routing',()=>{
  const invalid=data.operators.find(r=>r.name==='北九州市営渡船');assert(invalid);assert.equal(invalid.status,'unusable');assert.equal(invalid.timetable,null);
  assert(data.feeds.filter(f=>invalid.feedIds.includes(f.id)).every(f=>f.scheduledTrips.every(n=>n===null)));
  const missing=selectOperators(data,{status:'missing'});assert(missing.includes(invalid));assert(missing.every(r=>r.timetable===null));
  const ready=selectOperators(data,{status:'timetable'});for(const r of ready){assert(r.feedIds.some(id=>geo.feeds.find(f=>f.id===id)?.dataStatus==='current'));assert(r.timetable.note.includes('網羅は未確認'));}
});

test('filters distinguish JR rail from JR bus and CSV remains safe',()=>{
  assert(selectOperators(data,{mode:'rail',query:'ＪＲ九州'}).some(r=>r.name==='JR九州'));
  assert(selectOperators(data,{mode:'rail',query:'JR九州'}).every(r=>!r.name.includes('バス')));
  assert.equal(selectOperators(data,{query:'__no_operator__'}).length,0);
  const csv=csvText([['=formula','a,"b"','未反映']]);assert(csv.includes("' =formula"));assert(csv.includes('"a,""b"""'));
});

test('all main pages expose missing major operators without opening a disclosure',async()=>{
  for(const name of ['index.html','accessibility.html','transport-gaps.html','lab.html','data-catalog.html','usage.html','operators.html']){
    const html=await readFile(new URL(name,root),'utf8');assert.match(html,/<aside class="operator-notice"/);assert.match(html,/西鉄バス・西鉄電車・JR九州/);assert.match(html,/href="operators.html"/);
  }
});
