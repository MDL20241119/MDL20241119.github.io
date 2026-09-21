import assert from 'node:assert/strict';
import fs from 'node:fs';
import {labels,filterProjects,metricValue,escapeHTML} from '../mobility-training/model.js';
const data=JSON.parse(fs.readFileSync(new URL('../mobility-training/data/r7-projects.json',import.meta.url),'utf8'));
assert.equal(data.projects.length,61);
assert.equal(new Set(data.projects.map(p=>p.id)).size,61);
assert.deepEqual(data.projects.map(p=>p.official_order),Array.from({length:61},(_,i)=>i+1));
const states=new Set(['confirmed','planned','unverified','not_implemented','not_applicable']);
for(const p of data.projects){
 assert(p.project_name&&p.operator&&p.prefectures.length&&p.region,`${p.id}: identity`);
 assert.equal(p.official_source.url,data.population.official_list_url);
 assert(p.checked_at&&p.research_log?.length,`${p.id}: individual research trace`);
 const ids=new Set(p.individual_sources.map(s=>s.id));
 for(const [key,m] of Object.entries(p.metrics)){
  assert(key in labels,`${p.id}: unknown metric ${key}`);assert(states.has(m.status),`${p.id}: ${key} invalid status`);
  assert(m.note,`${p.id}: ${key} missing definition/caveat`);
  for(const id of m.source_ids||[])assert(ids.has(id),`${p.id}: missing source ${id}`);
  if(m.status==='unverified')assert.equal(m.value,null,`${p.id}: unknown must not become false or zero`);
  if(m.status==='confirmed'||m.status==='planned')assert(m.source_ids?.length,`${p.id}: no evidence for ${key}`);
 }
 assert.equal(Object.keys(p.metrics).length,Object.keys(labels).length);
}
const toy=[
 {id:'a',project_name:'ＰＢＬ 大分',operator:'大学',region:'別府',prefectures:['大分県'],metrics:{pbl:{status:'confirmed'},fieldwork:{status:'unverified'}},confirmed_activities:[]},
 {id:'b',project_name:'PBL 福岡',operator:'大学',region:'福岡',prefectures:['福岡県'],metrics:{pbl:{status:'planned'},fieldwork:{status:'confirmed'}},confirmed_activities:[]},
 {id:'c',project_name:'北海道',operator:'行政',region:'札幌',prefectures:['北海道'],metrics:{pbl:{status:'unverified'},fieldwork:{status:'unverified'}},confirmed_activities:[]}
];
assert.deepEqual(filterProjects(toy,{keys:['pbl']}).map(p=>p.id),['a']);
assert.deepEqual(filterProjects(toy,{keys:['pbl'],mode:'documented'}).map(p=>p.id),['a','b']);
assert.deepEqual(filterProjects(toy,{keys:['pbl'],mode:'unverified'}).map(p=>p.id),['c']);
assert.deepEqual(filterProjects(toy,{keys:['pbl','fieldwork'],mode:'documented'}).map(p=>p.id),['b']);
assert.deepEqual(filterProjects(toy,{query:'pbl 大分'}).map(p=>p.id),['a']);
assert.deepEqual(filterProjects(toy,{prefecture:'福岡県',keys:['pbl']}).map(p=>p.id),[]);
assert.equal(metricValue({value:null}),'');assert.equal(metricValue({value:0,unit:'人'}),'0 人');
assert.equal(escapeHTML('<img src=x onerror="evil">'), '&lt;img src=x onerror=&quot;evil&quot;&gt;');
console.log('PASS: 61 unique official records; all 16 fields; evidence references; unknown semantics; planned/confirmed filters; AND search; safe text');
