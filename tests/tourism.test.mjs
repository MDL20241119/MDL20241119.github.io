import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {readState,stateUrl,filterRecords,lodgingComparison,nearbyStops,csvFor,displayValue} from '../oita-tourism/model.mjs';
import {directCalls,accessOptions,directionsUrl,packAccess,unpackAccess} from '../oita-tourism/access-model.mjs';
import {buildNetwork} from '../oita-mobility/lab/gtfs.mjs';
const data=JSON.parse(await fs.readFile(new URL('../oita-tourism/data/tourism.json',import.meta.url)));
const transport=JSON.parse(await fs.readFile(new URL('../oita-mobility/data/map-data.json',import.meta.url)));
const access=unpackAccess(JSON.parse(await fs.readFile(new URL('../oita-tourism/data/access.json',import.meta.url))));
test('Observations retain provenance, missingness and separate lodging series',()=>{
 assert.equal(data.records.length,177);assert.equal(data.sourceWorkbook.sheets.length,10);
 assert.equal(new Set(data.records.map(r=>r.id)).size,data.records.length);
 for(const r of data.records){assert(r.provenance.sheet);assert(r.period);assert(r.method);if(r.sourceId)assert(data.sources.some(s=>s.id===r.sourceId));if(r.value===null)assert.equal(r.status,'未取得');}
 assert.equal(data.records.find(r=>r.sourceId==='P02'&&r.area==='大分県'&&r.metric==='延べ宿泊客数'&&r.period==='2025年').value,5311433);
 assert.equal(data.records.find(r=>r.sourceId==='P05'&&r.metric==='延べ宿泊者数').value,8232000);
 const rows=lodgingComparison(data);assert.equal(rows.filter(r=>r.record).length,3);assert(rows.filter(r=>r.record).every(r=>r.record.unit==='人泊'));assert.equal(rows.reduce((n,r)=>n+(r.record?.value??0),0),4440890);
 assert.equal(displayValue({value:null,unit:'人'}).value,'未取得');
});
test('Yufu monthly totals, Beppu districts and traffic denominators reconcile',()=>{
 const y=data.tables['05_由布2025月次'].filter(r=>r[0]!=='年間計');assert.equal(y.length,12);assert.equal(y.reduce((s,r)=>s+r[1]+r[2],0),4196408);
 const b=data.tables['06_別府詳細'].filter(r=>r[0]==='地区別宿泊');assert.equal(b.reduce((s,r)=>s+r[3],0),2564685);
 const modes=data.records.filter(r=>r.category==='交通手段'&&r.population==='国内居住者');assert(modes.every(r=>r.denominator===4742));for(const r of modes)assert(Math.abs(r.value-r.numerator/r.denominator)<1e-10);
});
test('Shared stop identity, map hash and null versus zero survive proximity filtering',async()=>{
 const raw=await fs.readFile(new URL('../oita-mobility/data/map-data.json',import.meta.url));assert.equal(createHash('sha256').update(raw).digest('hex'),data.transport.sha256);
 for(const a of data.anchors){const f=transport.feeds.findIndex(f=>f.id===a.feedId);const s=transport.stops.find(s=>s.feedIndex===f&&s.id===a.stopId);assert(s);assert.equal(a.lat,s.lat);assert.equal(a.lon,s.lon);}
 const a={lat:33,lon:131},g={stops:[{...a,id:'1',feedIndex:0,departures:[null]},{...a,id:'2',feedIndex:0,departures:[0]},{...a,id:'3',feedIndex:0,departures:[2]}]};assert.equal(nearbyStops(g,a,500,0).length,3);assert.deepEqual(nearbyStops(g,a,500,0,true).map(s=>s.id),['3']);
});
test('Shared access and comparison conditions round-trip; invalid values do not enter state',()=>{
 const bad=readState('https://example.test/?role=constructor&place=bad&day=99&radius=-1&at=34:70#unknown',data);assert.equal(bad.role,'government');assert.equal(bad.view,'overview');assert.equal(bad.day,0);assert.equal(bad.departure,'09:00');
 const desired={...bad,view:'access',area:'日出町',origin:'hiji-yokoku',anchor:'hiji-harmony',departure:'10:30',deadline:'17:00',dwell:180,maxMinutes:60,day:2,radius:500};assert.deepEqual(readState(stateUrl('https://example.test/',desired),data),desired);
 const comp={...bad,view:'compare',comparison:'modes'};assert.equal(readState(stateUrl('https://example.test/',comp),data).comparison,'modes');
});
test('Search and CSV preserve provenance and numeric values, with safe text cells',()=>{
 const rows=filterRecords(data.records,{area:'日出町',query:'ハーモニーランド',year:'2026'});assert.equal(rows.length,1);assert.equal(rows[0].value,33345);
 const csv=csvFor([{...rows[0],metric:' =HYPERLINK(1)',value:-5}],data.sources);assert(csv.includes("' =HYPERLINK(1)"));assert(csv.includes('"-5"'));assert(csv.includes('出典URL'));
});
function fixture(){return {id:'test',tables:{stops:['A','B'].map((id,i)=>({stop_id:id,stop_name:id,stop_lat:'33',stop_lon:String(131+i*.01)})),routes:[{route_id:'R',route_long_name:'合成テスト'}],trips:[{trip_id:'T',route_id:'R',service_id:'S'}],calendar:[{service_id:'S',start_date:'20260901',end_date:'20260930',tuesday:'1'}],calendar_dates:[],stop_times:[{trip_id:'T',stop_id:'A',stop_sequence:'1',arrival_time:'09:00:00',departure_time:'09:00:00'},{trip_id:'T',stop_id:'B',stop_sequence:'2',arrival_time:'09:20:00',departure_time:'09:20:00'}]}};}
const anchors=[{id:'a',lat:33,lon:131},{id:'b',lat:33,lon:131.01}];
test('Direct calls obey direction, calendar exceptions and pickup/dropoff restrictions',()=>{
 const f=fixture();let n=buildNetwork([f],'20260908');const c=directCalls(n,anchors,{id:'test'},0);assert.equal(c.length,1);assert.equal(c[0].departure,32400);assert.equal(c[0].arrival,33600);assert.equal(c[0].from,'a');assert.equal(c[0].to,'b');
 f.tables.stop_times[0].pickup_type='1';assert.equal(directCalls(buildNetwork([f],'20260908'),anchors,{id:'test'},0).length,0);
 f.tables.stop_times[0].pickup_type='0';f.tables.stop_times[1].drop_off_type='2';assert.equal(directCalls(buildNetwork([f],'20260908'),anchors,{id:'test'},0).length,0);
 f.tables.stop_times[1].drop_off_type='0';f.tables.calendar_dates=[{service_id:'S',date:'20260908',exception_type:'2'}];assert.equal(directCalls(buildNetwork([f],'20260908'),anchors,{id:'test'},0).length,0);
});
test('Accessibility requires enough dwell, margin and return before deadline',()=>{
 const base={day:0,from:'a',to:'b',departure:32400,arrival:33600},back={day:0,from:'b',to:'a',departure:41400,arrival:42600};
 const s={day:0,origin:'a',anchor:'b',departure:'09:00',deadline:'12:00',maxMinutes:30,dwell:120};assert.equal(accessOptions([base,back],s).pairs.length,0,'two hours + 20 min cannot fit');
 back.departure=42000;back.arrival=43200;assert.equal(accessOptions([base,back],s).pairs.length,1);
 assert.equal(accessOptions([base,back],{...s,deadline:'11:59'}).pairs.length,0);assert(accessOptions([base],{...s,deadline:'08:00'}).invalid);
});
test('Packed timetable is lossless and real examples have traceable, time-valid calls',()=>{
 assert.deepEqual(unpackAccess(packAccess({...access,encoding:undefined})).calls,access.calls);
 assert.equal(access.calls.length,2301);for(const c of access.calls){assert(data.anchors.some(a=>a.id===c.from));assert(data.anchors.some(a=>a.id===c.to));assert(c.arrival>=c.departure);assert(c.board.distance<=300);assert(c.alight.distance<=300);assert(access.feeds.some(f=>f.id===c.feedId));}
 for(const [origin,anchor]of [['beppu-station','beppu-jigoku'],['hiji-yokoku','hiji-harmony'],['yufu-station','yufu-takemoto']]){const r=accessOptions(access.calls,{origin,anchor,day:0,departure:'09:00',deadline:'18:00',dwell:120,maxMinutes:90});assert(r.pairs.length>0);assert(r.pairs.every(p=>p.back.departure>=p.out.arrival+8400));}
});
test('External directions carry coordinates and selected mode without implying date support',()=>{
 const u=new URL(directionsUrl(anchors[0],anchors[1],'walking'));assert.equal(u.origin,'https://www.google.com');assert.equal(u.searchParams.get('api'),'1');assert.equal(u.searchParams.get('travelmode'),'walking');assert.equal(u.searchParams.get('origin'),'33,131');assert(!u.searchParams.has('departure_time'));
});
