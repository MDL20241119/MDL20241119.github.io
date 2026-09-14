import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {importGTFS,validateFeeds,buildNetwork} from '../fukuoka-mobility/lab/gtfs.mjs';
import {feedCoverage,departurePattern,defaultProfile,measureSupply,validateProfile} from '../fukuoka-mobility/gaps/engine.mjs';
import {publicGapProfile} from '../fukuoka-mobility/assets/share-state.mjs';
import {hourlyAssessment,hourlySummary,timeViewFromParams,hourLabel} from '../fukuoka-mobility/gaps/time-view.mjs';
const root=new URL('../fukuoka-mobility/',import.meta.url);
const read=async p=>JSON.parse(await readFile(new URL(p,root),'utf8'));

test('official links cover all Nishitetsu stations and required JR bus schedules without claiming routing',async()=>{
  const d=await read('data/official-timetables.json');assert.equal(d.networkCoverageComplete,false);
  assert.equal(new Set(d.entries.map(e=>e.id)).size,d.entries.length);
  const n=d.entries.filter(e=>e.group==='nishitetsu-rail');assert.equal(n.length,73);assert(n.every(e=>!e.analysisReady&&e.url.startsWith('https://jik.nishitetsu.jp/trainroute')));
  for(const name of ['博多','小倉','久留米','直方'])assert(d.entries.some(e=>e.group==='jr-kyushu'&&e.name===name&&e.url.includes('tt_dep.cgi?c=')));
  assert.equal(d.documents.filter(e=>e.group==='jr-kyushu-bus').length,5);
  assert(d.entries.some(e=>e.group==='jr-kyushu-bus'&&e.name==='福間駅さいごう口'));
  assert(d.entries.some(e=>e.group==='jr-kyushu'&&e.city==='佐賀県'));
  assert(d.entries.every(e=>/^https?:\/\//.test(e.url)));
});

test('official subway trips match reviewed counts and unsupported dates are never zero-service claims',async()=>{
  const c=(await read('data/gtfs/catalog.json')).find(f=>f.file.startsWith('fukuoka-subway__'));assert(c);
  const b=await readFile(new URL('data/gtfs/'+c.file,root));const f=await importGTFS(b.buffer.slice(b.byteOffset,b.byteOffset+b.length),c.name,c.id);
  assert.equal(validateFeeds([f]).errors,0);
  for(const [date,count] of [['20260914',980],['20260915',980],['20260919',830],['20260920',822]]){
    assert.equal(feedCoverage(f,date),'known');assert.equal(buildNetwork([f],date,{includeOvernight:false}).trips.length,count);
  }
  for(const date of ['20260913','20260916','20260917','20260918','20260921'])assert.equal(feedCoverage(f,date),'unknown');
  const proof=await read('data/sources/subway-timetable-verification.json');assert.equal(proof.pdfComparisons.length,134);assert(proof.pdfComparisons.every(c=>c.matches));assert.equal(proof.currentStationComparisons.length,12);assert(proof.currentStationComparisons.every(c=>c.matches));
  assert.equal(proof.officialExpiryDate,null);
});

test('daily bus totals do not conceal an afternoon with no departures; repeated stops are deduplicated',()=>{
  const events=[{trip:'a',time:8*3600},{trip:'a',time:8*3600+180},...Array.from({length:5},(_,i)=>({trip:'t'+i,time:8*3600+600+i*600}))];
  const d=departurePattern(events,6*3600,22*3600);assert.equal(d.hourly[8],6);assert.equal(d.windowTrips,6);assert.equal(d.maximumIntervalMinutes,13*60+10);
  const p=defaultProfile('40130',['f']);Object.assign(p,{distanceOn:false,frequencyOn:true,intervalOn:true,maximumInterval:120});
  const s={key:'s',name:'test',lat:33.6,lon:130.4},ctx={network:{excluded:0},stops:[s],unknownStops:[],byStop:new Map([['s',events]]),known:true,networkCoverageComplete:false};
  const r=measureSupply(ctx,s,p);assert.equal(r.criteria.find(c=>c.id==='frequency').state,'pass');assert.equal(r.criteria.find(c=>c.id==='interval').state,'unknown');assert.equal(r.status,'unknown');
  const verified=measureSupply({...ctx,networkCoverageComplete:true},s,p);assert.equal(verified.criteria.find(c=>c.id==='interval').state,'fail');
});

test('new interval and personal controls survive safe sharing and old profiles still load',()=>{
  const p=defaultProfile('40130',['f']);Object.assign(p,{intervalOn:true,maximumInterval:90,wheelchair:true,reservation:'allow',note:'private'});
  const shared=publicGapProfile(p);assert.equal(shared.intervalOn,true);assert.equal(shared.maximumInterval,90);assert.equal(shared.wheelchair,true);assert.equal(shared.reservation,'allow');assert.equal(shared.note,'');
  delete p.intervalOn;delete p.maximumInterval;delete p.wheelchair;delete p.reservation;validateProfile(p);assert.equal(p.maximumInterval,120);assert.equal(p.intervalOn,false);
});

test('the same area changes by hour while missing major timetables prevent a confirmed gap',()=>{
  const r={networkCoverageComplete:false,departurePattern:departurePattern([{trip:'morning',time:8*3600},{trip:'evening',time:17*3600}],0,86400)};
  assert.deepEqual(hourlyAssessment(r,8,1),{state:'pass',count:1});
  assert.deepEqual(hourlyAssessment(r,12,1),{state:'review',count:0});
  assert.deepEqual(hourlyAssessment(r,8,2),{state:'review',count:1});
  assert.deepEqual(hourlyAssessment({...r,networkCoverageComplete:true},12,1),{state:'fail',count:0});
  assert.deepEqual(hourlyAssessment({networkCoverageComplete:false,departurePattern:null},12,1),{state:'unknown',count:null});
  assert.deepEqual(hourlyAssessment(undefined,12,1),{state:'unknown',count:null});
});

test('hourly area bars preserve uncomputed areas and can be reproduced from the selected view',()=>{
  const cells=Array.from({length:3},(_,i)=>({id:String(i),properties:{areaKm2:.25}}));
  const trips=Array.from({length:24},(_,h)=>h===8?2:0);
  const results=new Map([['0',{departurePattern:{hourly:trips},networkCoverageComplete:false}],['1',{departurePattern:{hourly:trips},networkCoverageComplete:true}]]);
  assert.deepEqual(hourlySummary(cells,results,8,2),{pass:{count:2,area:.5},review:{count:0,area:0},fail:{count:0,area:0},unknown:{count:1,area:.25}});
  const midday=hourlySummary(cells,results,12,2);assert.equal(midday.review.count,1);assert.equal(midday.fail.count,1);assert.equal(midday.unknown.count,1);
  assert.equal(hourLabel(23),'23:00〜24:00');
  assert.deepEqual(timeViewFromParams(new URLSearchParams('view=hourly&hour=17&hourlyMinimum=2')),{mode:'hourly',hour:17,minimumTrips:2});
  assert.deepEqual(timeViewFromParams(new URLSearchParams('hour=-1&hourlyMinimum=0')),{mode:'hourly',hour:8,minimumTrips:1});
  assert.throws(()=>hourlyAssessment(null,24,1));assert.throws(()=>hourlyAssessment(null,8,0));
});
