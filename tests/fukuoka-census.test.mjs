import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {gunzipSync} from 'node:zlib';
const root=new URL('../fukuoka-mobility/',import.meta.url);
const read=p=>JSON.parse(p.endsWith('.gz')?gunzipSync(fs.readFileSync(new URL(p,root))):fs.readFileSync(new URL(p,root)));
const data=read('gaps/data/census2020.json.gz'),source=read('data/sources/census2020.json.gz'),rows=new Map(source.rows.map(r=>[r.KEY_CODE,r]));
test('2020 census joins all 60 cities and preserves source counts, suppression and units',()=>{
 assert.equal(Object.keys(data.grids).length,120);assert.equal(rows.size,11423);
 const used=new Set();let numeric=0;
 for(const [key,grid] of Object.entries(data.grids)){
  const geometry=read('gaps/data/'+key+'.geojson');assert.equal(Object.keys(grid).length,geometry.features.length);
  if(!key.endsWith('-500'))continue;
  for(const [mesh,v] of Object.entries(grid)){
   const r=rows.get(mesh);
   if(v.censusState==='numeric'){
    assert(!used.has(mesh),'No source population assigned to multiple municipalities');used.add(mesh);numeric++;
    assert.equal(r.HTKSYORI,'0');
    for(const [field,meta] of Object.entries(data.source.fields))assert.equal(v[field],/^\d+$/.test(r[meta.code])?Number(r[meta.code]):null);
    assert(v.censusAge75<=v.censusAge65);assert(v.censusAge65<=v.censusPopulation2020);
   }else for(const field of Object.keys(data.source.fields))assert.equal(v[field],null,'Unavailable is never zero');
  }
 }
 assert.equal(numeric,data.source.counts.numeric500);
});
test('1000m values require all four child cells; empty or partial children remain unavailable',()=>{
 for(const [key,grid] of Object.entries(data.grids))if(key.endsWith('-1000'))for(const [mesh,v] of Object.entries(grid)){
  const fine=data.grids[key.replace('-1000','-500')],children=[1,2,3,4].map(q=>fine[mesh+q]);
  if(v.censusState==='numeric'){
   assert(children.every(c=>c?.censusState==='numeric'));
   for(const field of Object.keys(data.source.fields))assert.equal(v[field],children.every(c=>Number.isFinite(c[field]))?children.reduce((n,c)=>n+c[field],0):null);
  }else assert.equal(v.censusAge65,null);
 }
});
