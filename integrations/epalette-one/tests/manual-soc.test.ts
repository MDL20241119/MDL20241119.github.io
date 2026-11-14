import test from 'node:test';
import assert from 'node:assert/strict';
import {applyCommand,seedState,manualSocStatus,socFresh,shift,readiness,estimate,CHECKS,RETURN_CHECKS,MANUAL_SOC_MAX_AGE_MINUTES,manualSocMaxAgeMinutes,type AppState,type Command,type ManualSocStage} from '../lib/model';

const seed=()=>seedState('2026-09-24T05:00:00Z');
const actor='authenticated-account-123';
const cmd=(s:AppState,c:Command)=>applyCommand(s,c,actor);
const record=(s:AppState,patch:Partial<Command>={})=>cmd(s,{type:'record_soc',vehicleId:'EP-01',stage:'start',soc:80,observedAt:s.clock,recorder:'現場担当 A',safeStationaryConfirmed:true,confirmed:true,...patch});
const declare=(s:AppState,status:string)=>cmd(s,{type:'declare_vehicle_state',vehicleId:'EP-01',status,...(status==='stationary'?{safeStationaryConfirmed:true}:{})});
const current=(s:AppState)=>manualSocStatus(s,s.vehicles[0]);

for(const stage of ['start','return','after_charge'] satisfies ManualSocStage[])test(`manual SOC: ${stage} has immutable evidence and trusted actor`,()=>{
 const s=seed(),before=structuredClone(s),next=record(s,{stage});
 assert.deepEqual(s,before);assert.equal(next.version,s.version+1);assert.equal(next.manualSocObservations?.length,1);
 const observation=next.manualSocObservations![0];
 assert.equal(observation.stage,stage);assert.equal(observation.soc,80);assert.equal(observation.observedAt,s.clock);assert.equal(observation.recordedAt,s.clock);
 assert.equal(observation.recorder,'現場担当 A');assert.equal(observation.actor,actor);assert.equal(observation.source,'manual');assert.equal(observation.safeStationaryConfirmed,true);assert.equal(observation.confirmed,true);
 assert.equal(next.vehicles[0].soc.quality,'manual');assert.equal(next.vehicles[0].soc.source,'manual');assert.equal(next.vehicles[0].manualState?.status,'stationary');
 assert.equal(current(next).valid,true);assert.equal(current(next).observation?.id,observation.id);assert.equal(next.events[0].actor,actor);
 assert.deepEqual(next.vehicles[0].charging,s.vehicles[0].charging);assert.deepEqual(next.vehicles[0].power,s.vehicles[0].power);
 assert.deepEqual(next.vehicles[0].location,s.vehicles[0].location);assert.deepEqual(next.bookings,s.bookings);assert.deepEqual(next.tasks,s.tasks);
});

test('manual SOC: 0 and 100 are valid; noninteger, out-of-range and coerced inputs are refused atomically',()=>{
 for(const soc of [0,100])assert.equal(record(seed(),{soc}).vehicles[0].soc.value,soc);
 for(const soc of [-1,101,99.5,NaN,Infinity,-Infinity,'80',null,true]){
  const s=seed(),before=structuredClone(s);assert.throws(()=>record(s,{soc}));assert.deepEqual(s,before);
 }
});

test('manual SOC: recorder, actor, stages and both explicit confirmations are mandatory',()=>{
 for(const patch of [{recorder:''},{recorder:'   '},{recorder:'a'.repeat(121)},{stage:'during_trip'},{stage:null},{safeStationaryConfirmed:false},{safeStationaryConfirmed:'true'},{safeStationaryConfirmed:undefined},{confirmed:false},{confirmed:1},{confirmed:undefined}])assert.throws(()=>record(seed(),patch));
 assert.throws(()=>applyCommand(seed(),{type:'record_soc',vehicleId:'EP-01',stage:'start',soc:80,observedAt:seed().clock,recorder:'A',safeStationaryConfirmed:true,confirmed:true},''));
 assert.equal(record(seed(),{recorder:'  記録者  '}).manualSocObservations?.[0].recorder,'記録者');
});

test('manual SOC: unknown fields cannot spoof the audit identity or source',()=>{
 for(const patch of [{actor:'another-user'},{source:'vehicle_api'},{activityVersion:999},{id:'chosen-id'},{recordedAt:'2000-01-01T00:00:00Z'},{vehicleId:'missing'}])assert.throws(()=>record(seed(),patch));
});

test('manual SOC: aliases apply identical safeguards',()=>{
 assert.equal(record(seed(),{type:'record_manual_soc'}).manualSocObservations?.length,1);
 const moving=cmd(seed(),{type:'set_manual_motion',vehicleId:'EP-01',motion:'moving'});
 assert.equal(moving.vehicles[0].manualState?.status,'moving');assert.throws(()=>record(moving),/走行中/);
 assert.throws(()=>cmd(moving,{type:'set_manual_motion',vehicleId:'EP-01',motion:'stationary'}),/停車/);
 const stopped=cmd(moving,{type:'set_manual_motion',vehicleId:'EP-01',motion:'stationary',safeStationaryConfirmed:true});
 assert.equal(current(record(stopped)).valid,true);
 assert.throws(()=>cmd(stopped,{type:'set_manual_motion',vehicleId:'EP-01',motion:'charging'}));
});

test('manual SOC: timestamps require a valid timezone-bearing calendar time and cannot be future',()=>{
 const s=seed();
 for(const observedAt of ['invalid','2026-09-24','2026-09-24T05:00:00','2026-02-30T00:00:00Z','2026-09-24T24:00:00Z',shift(s.clock,1),'2026-09-24T05:00:00.001Z',null])assert.throws(()=>record(s,{observedAt}));
 const noncanonical=seed();noncanonical.clock='2026-09-24T05:00:00Z';
 assert.throws(()=>record(noncanonical,{observedAt:'2026-09-24T05:00:00.001Z'}),/未来/);
 assert.equal(record(s,{observedAt:'2026-09-24T14:00:00+09:00'}).manualSocObservations?.[0].observedAt,s.clock);
});

test('manual SOC: stale observations are retained but cannot enable readiness or charge estimates',()=>{
 const s=record(seed(),{observedAt:shift(seed().clock,-11)});
 assert.equal(s.manualSocObservations?.length,1);assert.equal(current(s).valid,false);assert.match(current(s).reason,/10分/);
 assert.equal(socFresh(s,s.vehicles[0]),false);assert.equal(readiness(s,s.vehicles[0],s.bookings[0]).type,'unknown');assert.equal(estimate(s,s.vehicles[0],s.bookings[0],'dc1').valid,false);
});

test('manual SOC: freshness expires after ten minutes without rewriting history',()=>{
 const s=record(seed()),original=structuredClone(s.manualSocObservations);
 const boundary={...s,clock:shift(s.clock,MANUAL_SOC_MAX_AGE_MINUTES)};
 assert.equal(current(boundary).valid,true);
 const expired=cmd(boundary,{type:'advance_clock',minutes:1});
 assert.equal(current(expired).valid,false);assert.deepEqual(expired.manualSocObservations,original);
 assert.equal(current({...s,clock:shift(s.clock,-1)}).valid,false);
});

for(const status of ['moving','charging','unknown'])test(`manual SOC: ${status} invalidates evidence even when stopped again at same clock time`,()=>{
 const s=record(seed()),original=structuredClone(s.manualSocObservations),changed=declare(s,status);
 assert.equal(current(changed).valid,false);assert.equal(socFresh(changed,changed.vehicles[0]),false);
 if(status!=='unknown')assert.throws(()=>record(changed),status==='moving'?/走行中/:/充電中/);
 const stopped=declare(changed,'stationary');assert.equal(current(stopped).valid,false);assert.equal(stopped.vehicles[0].manualState?.activityVersion,1);
 assert.deepEqual(stopped.manualSocObservations,original);
 const newCheck=record(stopped,{stage:status==='charging'?'after_charge':'return',soc:75});
 assert.equal(current(newCheck).valid,true);assert.equal(newCheck.manualSocObservations?.length,2);assert.deepEqual(newCheck.manualSocObservations?.[0],original?.[0]);
});

test('manual SOC: stationary declarations never refresh SOC freshness',()=>{
 const s=cmd(record(seed()),{type:'advance_clock',minutes:11});
 assert.equal(current(declare(s,'stationary')).valid,false);
 assert.throws(()=>cmd(s,{type:'declare_vehicle_state',vehicleId:'EP-01',status:'stationary'}),/停車/);
 assert.throws(()=>cmd(s,{type:'declare_vehicle_state',vehicleId:'EP-01',status:'stationary',safeStationaryConfirmed:'true'}),/停車/);
 assert.throws(()=>cmd(s,{type:'declare_vehicle_state',vehicleId:'EP-01',status:'stationary',safeStationaryConfirmed:true,actor:'spoof'}));
});

test('manual SOC: observations from before use or charging cannot be replayed as fresh',()=>{
 const s=record(seed()),later=cmd(s,{type:'advance_clock',minutes:2}),moved=declare(later,'moving'),stopped=declare(moved,'stationary');
 const before=structuredClone(stopped);assert.throws(()=>record(stopped,{observedAt:s.clock}),/再確認/);assert.deepEqual(stopped,before);
 assert.equal(current(record(stopped)).valid,true);
});

test('manual SOC: a reading observed before the declared stop cannot bypass a known moving interval',()=>{
 const first=record(seed()),moving=declare(first,'moving'),later=cmd(moving,{type:'advance_clock',minutes:5}),stopped=declare(later,'stationary');
 assert.throws(()=>record(stopped,{observedAt:shift(first.clock,2)}),/再確認/);
 assert.equal(current(record(stopped)).valid,true);
});

test('manual SOC: late offline entries append to history without rolling back a newer reading',()=>{
 const first=record(seed(),{soc:75}),later=cmd(first,{type:'advance_clock',minutes:2}),latest=record(later,{soc:70,stage:'return'});
 const old=record(latest,{observedAt:shift(later.clock,-1),soc:73});
 assert.equal(old.manualSocObservations?.length,3);assert.equal(old.vehicles[0].soc.value,70);assert.equal(current(old).observation?.stage,'return');
 assert.equal(current(old).observation?.id,current(latest).observation?.id);assert.deepEqual(old.manualSocObservations?.slice(0,2),latest.manualSocObservations);
});

test('manual SOC: use starts with fresh start evidence, snapshots it, and invalidates it immediately',()=>{
 let s=seed();s.clock=shift(s.bookings[0].start,-20);s=cmd(s,{type:'simulate',vehicleId:'EP-01',soc:80});s=record(s);
 const checkedIn=cmd(s,{type:'check_in',id:'b1',checks:CHECKS});
 assert.equal(checkedIn.bookings[0].status,'active');assert.equal(checkedIn.sessions[0].startSoc.value,80);assert.equal(checkedIn.sessions[0].startSoc.source,'manual');assert.equal(current(checkedIn).valid,false);
 assert.deepEqual(checkedIn.manualSocObservations,s.manualSocObservations);
 assert.throws(()=>cmd(checkedIn,{type:'check_out',id:'b1',checks:RETURN_CHECKS}),/返却時/);
 const wrongStage=record(checkedIn,{stage:'after_charge',soc:65});assert.throws(()=>cmd(wrongStage,{type:'check_out',id:'b1',checks:RETURN_CHECKS}),/返却時/);
 const returned=cmd(record(checkedIn,{stage:'return',soc:60}),{type:'check_out',id:'b1',checks:RETURN_CHECKS});
 assert.equal(returned.sessions[0].endSoc?.value,60);assert.equal(returned.sessions[0].startSoc.value,80);assert.equal(returned.bookings[0].status,'return_requested');
 const changed=cmd(returned,{type:'simulate',vehicleId:'EP-01',scenario:'stale'});
 assert.equal(changed.sessions[0].endSoc?.observedAt,returned.sessions[0].endSoc?.observedAt);assert.deepEqual(changed.manualSocObservations,returned.manualSocObservations);
});

test('manual SOC: a charging/return check cannot substitute for the start-stage record',()=>{
 let s=seed();s.clock=shift(s.bookings[0].start,-20);s=cmd(s,{type:'simulate',vehicleId:'EP-01',soc:80});
 assert.throws(()=>cmd(record(s,{stage:'after_charge'}),{type:'check_in',id:'b1',checks:CHECKS}),/利用開始時/);
});

test('manual SOC: simulator charge and SOC changes invalidate manual authority without discarding history',()=>{
 const s=record(seed());
 for(const patch of [{charging:'charging',power:20},{soc:90},{charging:'not_connected'}]){
  const changed=cmd(s,{type:'simulate',vehicleId:'EP-01',...patch});assert.equal(current(changed).valid,false);assert.equal(socFresh(changed,changed.vehicles[0]),false);
  assert.equal(readiness(changed,changed.vehicles[0],changed.bookings[0]).type,'unknown');assert.deepEqual(changed.manualSocObservations,s.manualSocObservations);
 }
});

test('manual SOC: charge assignment/receipt never starts the charger or invalidates by itself; completion requires after-charge evidence',()=>{
 let s=record(seed(),{soc:80});
 s=cmd(s,{type:'assign_charge',vehicleId:'EP-01',bookingId:'b1',stationId:'dc1',targetSoc:80,owner:'d3'});
 const task=s.tasks.at(-1)!;assert.equal(current(s).valid,true);assert.equal(s.vehicles[0].charging.value,'not_connected');
 s=cmd(s,{type:'task_action',id:task.id,action:'acknowledge'});assert.equal(current(s).valid,true);
 assert.throws(()=>cmd(s,{type:'task_action',id:task.id,action:'complete'}),/充電後/);
 const done=cmd(record(s,{stage:'after_charge'}),{type:'task_action',id:task.id,action:'complete'});
 assert.equal(done.tasks.at(-1)?.status,'completed');assert.equal(done.vehicles[0].charging.value,'not_connected');
});

test('manual SOC: reset keeps historical confirmations while requiring new evidence',()=>{
 const s=record(seed()),reset=cmd(s,{type:'reset_demo'});
 assert.deepEqual(reset.manualSocObservations,s.manualSocObservations);assert.equal(current(reset).valid,false);assert.equal(socFresh(reset,reset.vehicles[0]),false);
 const rerecorded=record(reset);assert.equal(rerecorded.manualSocObservations?.length,2);assert.equal(current(rerecorded).valid,true);
});

test('manual SOC: other vehicles and legacy persisted states stay backwards-compatible',()=>{
 const s=seed();assert.equal('manualSocObservations' in s,false);assert.equal(current(s).valid,false);assert.equal(socFresh(s,s.vehicles[0]),true);
 const persisted=JSON.parse(JSON.stringify(s)) as AppState,n=record(persisted);assert.deepEqual(n.vehicles.slice(1),persisted.vehicles.slice(1));assert.equal(socFresh(n,n.vehicles[2]),true);
 assert.equal(readiness(s,s.vehicles[2],s.bookings[2]).type,'ready');
});


test('manual SOC policy: default and configured age are trial placeholders, not safety guarantees',()=>{
 const initial=record(seed());assert.equal(manualSocMaxAgeMinutes(initial),10);assert.match(current(initial).reason,/試験用の仮設定.*保証/);
 const aged=cmd(initial,{type:'advance_clock',minutes:11});assert.equal(current(aged).valid,false);
 const configured=cmd(aged,{type:'set_manual_policy',maxAgeMinutes:20});
 assert.equal(configured.manualSocMaxAgeMinutes,20);assert.equal(manualSocMaxAgeMinutes(configured),20);assert.equal(current(configured).valid,true);
 assert.equal(current(configured).expiresAt,shift(initial.clock,20));assert.match(configured.events[0].label,/試験用の仮設定20分.*安全保証/);
 assert.deepEqual(configured.manualSocObservations,aged.manualSocObservations);assert.deepEqual(configured.vehicles,aged.vehicles);
 const moving=declare(configured,'moving'),stopped=declare(moving,'stationary'),longer=cmd(stopped,{type:'set_manual_policy',maxAgeMinutes:120});
 assert.equal(current(longer).valid,false);assert.equal(socFresh(longer,longer.vehicles[0]),false);
 assert.equal(cmd(longer,{type:'reset_demo'}).manualSocMaxAgeMinutes,120);
});

test('manual SOC policy: integer bounds and command scope are enforced atomically',()=>{
 for(const maxAgeMinutes of [1,120])assert.equal(manualSocMaxAgeMinutes(cmd(seed(),{type:'set_manual_policy',maxAgeMinutes})),maxAgeMinutes);
 for(const maxAgeMinutes of [0,121,-1,1.5,NaN,Infinity,'20',null,undefined]){const s=seed(),before=structuredClone(s);assert.throws(()=>cmd(s,{type:'set_manual_policy',maxAgeMinutes}));assert.deepEqual(s,before);}
 assert.throws(()=>cmd(seed(),{type:'set_manual_policy',maxAgeMinutes:20,source:'approved-safety-policy'}));
 assert.throws(()=>cmd({...seed(),mode:'production'} as unknown as AppState,{type:'set_manual_policy',maxAgeMinutes:20}),/模擬環境専用/);
 assert.equal(manualSocMaxAgeMinutes({...seed(),manualSocMaxAgeMinutes:999}),10);
});
