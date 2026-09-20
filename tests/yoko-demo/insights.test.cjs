const assert=require('node:assert/strict');
const fs=require('node:fs');
const I=require('../../danchi-elevator/demo/insights.js');
const checks=[];function test(name,fn){fn();checks.push(name);}
const iso=time=>'2026-09-20T'+time+':00+09:00';
function ride(id,vehicle,status,created,assigned,board,finish,people=1){return{id,vehicle_id:vehicle,status,created_at:created,passengers:people,origin_stop_id:'stop-a',destination_stop_id:'stop-b',origin_name:'中央広場',destination_name:'駅前',events:[{status:'requested',created_at:created},...(assigned?[{status:'assigned',created_at:assigned}]:[]),...(board?[{status:'onboard',created_at:board}]:[]),...(finish?[{status,created_at:finish}]:[])]};}
const r1=ride('r1','v1','completed',iso('09:00'),iso('09:00'),iso('09:10'),iso('10:00'),2);
const r2=ride('r2','v1','completed',iso('09:30'),iso('09:30'),iso('09:40'),iso('10:30'));
const r3=ride('r3','v2','onboard',iso('11:30'),iso('11:30'),iso('11:40'));
const r4=ride('r4',null,'cancelled','2026-09-19T23:50:00+09:00',null,null,iso('00:10'));
const snap={rides:[r1,r2,r3,r4],vehicles:[{id:'v1',capacity:3,reserved:0},{id:'v2',capacity:3,reserved:1}],as_of:iso('12:00'),limit:200};
const m=I.metrics(snap,1,{start:'09:00',end:'17:00'});
test('Daily periods use Japan midnight and each metric uses its actual event date',()=>{assert.equal(m.requested,3);assert.equal(m.completed,2);assert.equal(m.cancelled,1);assert.equal(m.people,3);});
test('Completed ratio excludes ongoing rides and waiting time uses boarding records',()=>{assert.equal(m.completionRate,200/3);assert.equal(m.waitMinutes,10);assert.equal(m.waitSamples,3);});
test('Time utilization unions overlaps per vehicle and counts only elapsed operating windows',()=>{assert.equal(m.utilization.busyMinutes,120);assert.equal(m.utilization.availableMinutes,360);assert.ok(Math.abs(m.utilization.rate-100/3)<1e-9);});
test('Current assignment and occupancy have different explicit denominators',()=>{assert.equal(m.assignmentRate,50);assert.ok(Math.abs(m.occupancyRate-100/6)<1e-9);assert.equal(m.totalVehicles,2);assert.equal(m.capacity,6);});
test('No schedule means no invented time utilization',()=>assert.equal(I.metrics(snap,1).utilization,null));
test('No vehicles or no finished rides produce unavailable ratios rather than fictitious percentages',()=>{const e=I.metrics({as_of:iso('12:00'),rides:[],vehicles:[]},1,{start:'09:00',end:'17:00'});assert.equal(e.assignmentRate,null);assert.equal(e.occupancyRate,null);assert.equal(e.completionRate,null);assert.equal(e.waitMinutes,null);assert.equal(e.utilization.rate,null);});
test('Unknown or malformed hours never create a denominator',()=>{for(const schedule of [{start:'xx',end:'17:00'},{start:'09:00',end:'09:00'},{start:'24:00',end:'25:00'}])assert.equal(I.metrics(snap,1,schedule).utilization,null);});
test('Future operating windows have no elapsed availability',()=>assert.equal(I.metrics(snap,1,{start:'13:00',end:'17:00'}).utilization.rate,null));
test('Overnight windows clip to the selected local day',()=>{const s={...snap,as_of:iso('02:00'),rides:[ride('night','v1','completed','2026-09-19T22:30:00+09:00','2026-09-19T22:30:00+09:00',null,iso('01:50'))]};const n=I.metrics(s,1,{start:'21:00',end:'03:00'});assert.equal(n.utilization.availableMinutes,240);assert.equal(n.utilization.busyMinutes,110);});
test('Missing terminal timestamps are excluded, never replaced by the snapshot clock',()=>{const s={...snap,rides:[{...r1,events:r1.events.filter(e=>e.status!=='completed')}]};const n=I.metrics(s,1,{start:'09:00',end:'17:00'});assert.equal(n.utilization.busyMinutes,0);assert.equal(n.utilization.missing,1);});
test('Daily totals, route rankings and request hours reconcile with the summary',()=>{assert.equal(m.trend.reduce((n,r)=>n+r.people,0),m.people);assert.equal(m.routes.reduce((n,r)=>n+r.people,0),m.people);assert.equal(m.hours.reduce((n,r)=>n+r.requests,0),m.requested);});
test('Snapshot limits are disclosed when the record cap is reached',()=>assert.equal(I.metrics({...snap,limit:4},1).possiblyTruncated,true));
test('Itinerary excludes pending, completed and other vehicles and drops off onboard passengers first',()=>{const list=I.itinerary([r1,r2,r3,{...r3,id:'other',vehicle_id:'other'},ride('waiting',null,'requested',iso('10:00')),ride('assigned','v2','assigned',iso('11:00'),iso('11:01'))],['v2']);assert.deepEqual(list.map(r=>[r.number,r.rideId,r.kind]),[[1,'r3','dropoff'],[2,'assigned','pickup'],[3,'assigned','dropoff']]);});
test('Navigator destinations are allowlisted demo coordinates, never personal or arbitrary text',()=>{const url=new URL(I.navigation('stop-b'));assert.equal(url.origin,'https://www.google.com');assert.equal(url.searchParams.get('destination'),'33.2024,131.5784');assert.equal(url.searchParams.get('dir_action'),'navigate');assert.equal(url.searchParams.has('origin'),false);assert.equal(I.navigation('some-address'),null);});
test('Disjoint and nested busy intervals never double count',()=>assert.equal(I.union([[1,10],[2,3],[8,12],[20,22]]),13));
const result={status:'PASS',count:checks.length,checks};fs.writeFileSync(__dirname+'/ux-insights-result.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
