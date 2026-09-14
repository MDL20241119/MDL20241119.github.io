import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {observation,stationRows,coverage,operatingMargin} from '../fukuoka-mobility/operators/statistics-model.mjs';
import {csvText} from '../fukuoka-mobility/operators/model.mjs';
const root=new URL('../fukuoka-mobility/',import.meta.url);
const read=async p=>JSON.parse(await readFile(new URL(p,root),'utf8'));
const [stats,finance,operators,raw]=await Promise.all(['data/station-ridership.json','data/operator-finance.json','data/operators.json','data/sources/station-ridership-2024.geojson'].map(read));

test('every Fukuoka source record and year is retained with source provenance',async()=>{
  assert.equal(stats.stations.length,390);assert.equal(stats.stations.length,raw.features.length);
  assert.equal(new Set(stats.stations.map(s=>s.operatorId)).size,9);
  assert.equal(createHash('sha256').update(await readFile(new URL(stats.source.localFile,root))).digest('hex'),stats.source.sha256);
  for(const s of stats.stations){
    assert(operators.operators.some(o=>o.id===s.operatorId));assert.equal(s.observations.length,14);
    const p=raw.features[s.sourceIndex].properties;
    assert.equal(s.name,p.S12_001);
    assert.equal(observation(s,2011).sourceValue,p.S12_009);assert.equal(observation(s,2024).sourceValue,p.S12_061);
    for(const o of s.observations){
      if(o.status==='available'){assert.equal(o.duplicateCode,1);assert.equal(o.presenceCode,1);assert(Number.isFinite(o.value));assert(o.value>=0);}
      else assert.equal(o.value,null,'Missing or already-counted data cannot become zero');
    }
  }
});

test('filters and coverage keep uncounted records visible without adding them to the measured total',()=>{
  const ids=operators.operators.map(o=>o.id),rows=stationRows(stats,ids,2024);
  assert.deepEqual(coverage(rows),{records:390,available:322,missing:38,other:30});
  const jr=operators.priorityGroups.find(g=>g.id==='jr-kyushu');
  const hakata=stationRows(stats,jr.operatorIds,2024,'博多');
  assert(hakata.some(s=>s.current.value===250924));assert(hakata.every(s=>s.operator==='九州旅客鉄道'));
  assert.equal(stationRows(stats,[],2024).length,0);
  assert.equal(observation(stats.stations[0],2030).value,null);
});

test('group reports are not reassigned as individual-company or Fukuoka-only actuals',()=>{
  assert.equal(finance.accounts.length,15);
  assert.equal(finance.accounts.filter(a=>a.year===2023).length,9);
  const bus=finance.accounts.find(a=>a.id==='nishitetsu-bus-2025');
  const required=operators.priorityGroups.find(g=>g.id==='nishitetsu-bus');
  assert.deepEqual(bus.operatorIds.toSorted(),required.operatorIds.toSorted());
  assert.equal(bus.revenueMillionYen,56317);assert.equal(bus.profitMillionYen,2207);assert.equal(bus.expensesMillionYen,54110);
  assert.equal(bus.passengersValue,207);assert.equal(bus.passengersUnit,'百万人／年');assert(bus.scope.includes('個別の運行会社'));
  assert(bus.expensesMethod.includes('算出値'));
  for(const a of finance.accounts){
    assert(a.sourceUrl.startsWith('https://'));assert(a.sourcePage);assert(a.scope.includes('県外')||a.scope.includes('福岡県内'));
    assert(Math.abs(a.revenueMillionYen-a.expensesMillionYen-a.profitMillionYen)<0.00001);
    assert(a.operatorIds.every(id=>operators.operators.some(o=>o.id===id)));
  }
  const jr=finance.accounts.find(a=>a.id==='jr-kyushu-2025');assert.equal(jr.revenueMillionYen,188800);assert.equal(jr.passengersUnit,'百万人キロ／年');
  const chikuho=finance.accounts.find(a=>a.name==='平成筑豊鉄道');assert(chikuho.profitMillionYen<0);assert(operatingMargin(chikuho)<0);
  assert.equal(operatingMargin({revenueMillionYen:0,profitMillionYen:1}),null);
  assert.equal(operatingMargin({revenueMillionYen:null,profitMillionYen:1}),null);
  assert(csvText([[-518.932,'=1+1']]).includes('"-518.932"'), 'A real financial loss exports as a numeric negative');
  assert(csvText([[-518.932,'=1+1']]).includes("' =1+1"));
});
