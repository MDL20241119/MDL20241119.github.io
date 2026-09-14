import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createContext,runInContext} from 'node:vm';
import {calculateBC,forecastSeries,TIME_VALUE} from '../fukuoka-mobility/calculations.js';

// Exercise the actual renderers with small DOM stand-ins; network startup is excluded.
const source=(await readFile(new URL('../fukuoka-mobility/app.js',import.meta.url),'utf8'))
  .replace(/^import .*;\n/gm,'').replace(/\nstart\(\);\s*$/,'');
const geo=JSON.parse(await readFile(new URL('../fukuoka-mobility/data/map-data.json',import.meta.url),'utf8'));
function page(){
  const nodes=new Map();
  const node=id=>{if(!nodes.has(id))nodes.set(id,{value:'',innerHTML:'',textContent:'',setAttribute(){},classList:{remove(){}}});return nodes.get(id);};
  for(const [id,value]of Object.entries({'bc-share':'50','bc-minutes':'5','bc-cost':'30','bc-rate':'0.04','bc-users':'10000','bc-time-value':'30','map-date':'0'}))node('#'+id).value=value;
  const context=createContext({document:{querySelector:node},calculateBC,forecastSeries,TIME_VALUE});
  runInContext(source,context);
  return {node,context,run:code=>runInContext(code,context)};
}

test('blank cost, trip count and time value do not become a zero-benefit result',()=>{
  for(const id of ['bc-cost','bc-users','bc-time-value']){
    const p=page();p.run('updateBC()');assert.match(p.node('#bc-results').innerHTML,/75\.00/);
    p.node('#'+id).value='';p.run('updateBC()');
    assert.match(p.node('#bc-results').innerHTML,/数値を入力してください/);
    assert.doesNotMatch(p.node('#bc-results').innerHTML,/bc-hero/);
    p.node('#'+id).value='0';p.run('updateBC()');assert.match(p.node('#bc-results').innerHTML,/bc-hero/,'An explicitly entered zero remains valid');
    p.node('#'+id).value='-1';p.run('updateBC()');assert.match(p.node('#bc-results').innerHTML,/数値を入力してください/);
  }
});

test('stop details use the dates paired with the loaded timetable counts',()=>{
  const p=page();p.context.loadedGeo=geo;p.run('geo=loadedGeo');
  p.context.stop=geo.stops.find(s=>s.name==='海老津駅入口');
  p.run('renderStopDetail(stop)');
  const html=p.node('#map-detail').innerHTML;
  for(const date of ['9/14 月','9/19 土','9/20 日'])assert(html.includes(date),date);
  assert(!html.includes('9/8 月'));
  // Updating the timetable dates updates the renderer without another source edit.
  p.context.loadedGeo=structuredClone(geo);p.context.loadedGeo.meta.dateLabels=['2026年9月21日（月）','2026年9月26日（土）','2026年9月27日（日）'];
  p.run('geo=loadedGeo;renderStopDetail(stop)');assert.match(p.node('#map-detail').innerHTML,/9\/21 月/);
});

test('expired timetable details show that service frequency is unconfirmed',()=>{
  const p=page();p.context.loadedGeo=geo;p.run('geo=loadedGeo');
  p.context.stop=geo.stops.find(s=>s.departures[0]===null);assert(p.context.stop);
  p.run('renderStopDetail(stop)');assert.match(p.node('#map-detail').innerHTML,/運行本数は未確認/);
});
