import {newId} from './id.js';
import {applyOperations,OperationData,readyToRelease,overlap} from './operations.js';
export type Purpose = 'shuttle' | 'ondemand' | 'shop' | 'charge';
export type Quality = 'demo' | 'measured' | 'manual' | 'estimated' | 'unavailable';
export type Reading<T> = { value: T | null; observedAt: string; receivedAt: string; source: string; quality: Quality; unit?: string };
// Manual observations are human declarations, never telemetry or control commands.
export type ManualSocStage = 'start' | 'return' | 'after_charge';
export type ManualVehicleStatus = 'stationary' | 'moving' | 'charging' | 'unknown';
export type ManualVehicleState = {status:ManualVehicleStatus; updatedAt:string; actor:string; source:'manual'; activityVersion:number; lastActivityAt?:string; invalidationReason?:string};
export type ManualSocObservation = Readonly<{id:string; vehicleId:string; stage:ManualSocStage; soc:number; observedAt:string; recordedAt:string; recorder:string; actor:string; source:'manual'; safeStationaryConfirmed:true; confirmed:true; activityVersion:number}>;
// Trial-only UI default, not an approved operational or safety threshold.
export const MANUAL_SOC_MAX_AGE_MINUTES = 10;
export const MANUAL_SOC_STAGES:Record<ManualSocStage,string> = {start:'利用開始時',return:'返却時',after_charge:'充電後'};
export type Vehicle = { id: string; name: string; location: Reading<string>; soc: Reading<number>; odometer: Reading<number>; charging: Reading<string>; power: Reading<number>; fault: Reading<string>; hold: boolean; holdReason: string; seats: number; usableKwh: number; acKw: number; dcKw: number; profileVerified: boolean; profileVersion: string; consumption?:number; efficiency?:number; dcCurve?:number[]; profileCheckedBy?:string; profileCheckedAt?:string; fieldObservationId?:string; manualState?:ManualVehicleState; manualSocObservationId?:string };
export type Booking = { id:string; title:string; purpose:Purpose; vehicleId:string; driverId:string; start:string; end:string; buffer:number; status:'draft'|'requested'|'rejected'|'confirmed'|'active'|'return_requested'|'received'|'completed'|'cancelled'; route:string; distance:number; reserveKwh:number; auxiliaryKwh:number; targetSoc:number; seats:number; checks:string[]; returnChecks:string[]; sessionId:string|null; organization:string; requestedBy?:string; requestedAt?:string; approvedBy?:string; approvedAt?:string; returnReceiverId?:string; resourceIds?:string[]; equipment?:string; changeReason?:string; pickupCapacity?:number; returnedBy?:string; receivedBy?:string; receivedAt?:string; };
export type Session = {id:string; bookingId:string; startedAt:string; endedAt:string|null; startSoc:Reading<number>; endSoc:Reading<number>|null; startOdometer:Reading<number>; endOdometer:Reading<number>|null; checkVersion:string; checkedBy:string};
export type Task = { id:string; title:string; vehicleId:string; bookingId:string|null; owner:string; deadline:string; status:'requested'|'acknowledged'|'working'|'completed'; kind:'charge'|'clean'|'review'|'setup'|'maintenance'|'transfer'; requestedBy?:string; acknowledgedBy?:string; completedBy?:string; completedAt?:string; chargeStart?:string; chargeEnd?:string; mode?:'ac'|'dc'; targetSoc?:number; stationId?:string; note:string };
export type Ticket = {id:string; bookingId:string; label:string; count:number; from:number; to:number; status:'reserved'|'boarded'|'alighted'|'cancelled'};
export type Ride = {id:string; from:string; to:string; count:number; requestedAt:string; start:string; end:string; status:'waiting'|'assigned'|'cancelled'; vehicleId:string|null; bookingId:string|null};
export type Order = {id:string; bookingId:string; productId:string; quantity:number; number:string; status:'received'|'preparing'|'ready'|'handed'|'cancelled'; payment:'unpaid'|'paid'|'refund_pending'|'refunded'; pickup:string;paymentEvidence?:{reference:string;actor:string;at:string;kind:'payment'|'refund'}[]};
export type AppState = { version:number; mode:'demo'|'operational'; clock:string; vehicles:Vehicle[]; bookings:Booking[]; sessions:Session[]; tasks:Task[]; tickets:Ticket[]; rides:Ride[]; orders:Order[]; products:{id:string;name:string;price:number;stock:number;accepting:boolean}[]; staff:{id:string;name:string;validUntil:string;active:boolean;qualificationBasis?:string}[]; stations:{id:string;name:string;type:'ac'|'dc';kw:number;travelMin:number;waitMin:number|null;shared:number;compatible:boolean;accessConfirmed:boolean;connectMin?:number;releaseMin?:number;inspectionMin?:number;basis?:string}[]; events:{id:string;time:string;label:string;actor:string}[]; receivedEvents:string[]; manualSocObservations?:readonly ManualSocObservation[]; manualSocMaxAgeMinutes?:number; } & OperationData;
export const PURPOSES: Record<Purpose,string> = {shuttle:'定時送迎',ondemand:'オンデマンド',shop:'物販',charge:'充電'};
export const CHECKS = ['日常点検を実施','体調・資格を確認','酒気帯び確認を記録','積載物・備品を固定','乗降設備・周囲を確認'];
export const RETURN_CHECKS = ['全員の降車・忘れ物を確認','清掃・備品・鍵を確認','異常の有無を確認'];
export function minutes(a:string,b:string){ return (Date.parse(a)-Date.parse(b))/60000; }
export function shift(iso:string,min:number){return new Date(Date.parse(iso)+min*60000).toISOString();}
export function clockText(iso:string){return new Date(iso).toLocaleTimeString('ja-JP',{timeZone:'Asia/Tokyo',hour:'2-digit',minute:'2-digit'});}
export function dateText(iso:string){return new Date(iso).toLocaleDateString('ja-JP',{timeZone:'Asia/Tokyo',month:'long',day:'numeric',weekday:'short'});}
export function inputDate(iso:string){return new Date(Date.parse(iso)+9*3600000).toISOString().slice(0,16);}
export function fromInput(s:string){return new Date(s+(s.length===16?':00':'')+'+09:00').toISOString();}
export function observationInput(iso:string){return new Date(Date.parse(iso)+9*3600000).toISOString().slice(0,19);}
export function fresh(r:Reading<unknown>,now:string,max=10){return r.value!==null&&r.quality!=='unavailable'&&minutes(now,r.observedAt)<=max&&minutes(now,r.observedAt)>=-1;}
export function manualSocMaxAgeMinutes(s:AppState){const value=s.mode==='operational'?s.policy?.maxAgeMinutes:s.manualSocMaxAgeMinutes;return typeof value==='number'&&Number.isInteger(value)&&value>=1&&value<=120?value:MANUAL_SOC_MAX_AGE_MINUTES;}
export type ManualSocStatus = {valid:boolean; reason:string; observation?:ManualSocObservation; expiresAt?:string};
export function manualSocStatus(s:AppState,v:Vehicle):ManualSocStatus {
 const maxAge=manualSocMaxAgeMinutes(s);
 if(s.mode==='operational'&&!s.policy)return {valid:false,reason:'管理者が現場の確認期限と根拠を設定してください。'};
 const observation=s.manualSocObservations?.find(x=>x.id===v.manualSocObservationId&&x.vehicleId===v.id);
 const result={observation,...(observation?{expiresAt:shift(observation.observedAt,maxAge)}:{})};
 if(!observation)return {...result,valid:false,reason:'手入力の残量確認がまだありません。'};
 if(v.manualState?.status==='moving')return {...result,valid:false,reason:'走行中の申告があります。安全な停車後に再確認してください。'};
 if(v.manualState?.status==='charging')return {...result,valid:false,reason:'充電中の申告があります。充電後に再確認してください。'};
 if(v.manualState?.status!=='stationary'||observation.activityVersion!==v.manualState.activityVersion)return {...result,valid:false,reason:'確認後の利用・充電または状態変更があるため、残量を再確認してください。'};
 if(v.soc.quality!=='manual'||v.soc.source!=='manual'||v.soc.value!==observation.soc||v.soc.observedAt!==observation.observedAt)return {...result,valid:false,reason:'残量情報が変更されています。手入力で再確認してください。'};
 const age=minutes(s.clock,observation.observedAt);
 if(!Number.isFinite(age)||age<0)return {...result,valid:false,reason:'確認日時を確認してください。'};
 if(age>maxAge)return {...result,valid:false,reason:`確認から${s.mode==='demo'?'試験設定の':''}${maxAge}分を超えています。残量を再確認してください。`};
 return {...result,valid:true,reason:'安全な停車中に人が確認した記録です。確認期限は試験用の仮設定で、安全を保証するものではありません。'};
}
export function socFresh(s:AppState,v:Vehicle){return s.mode==='operational'||v.manualState||v.manualSocObservationId||v.soc.quality==='manual'?manualSocStatus(s,v).valid:fresh(v.soc,s.clock);}
function invalidateManualSoc(v:Vehicle,now:string,actor:string,reason:string,status:ManualVehicleStatus='unknown') {
 if(!v.manualState&&!v.manualSocObservationId)return;
 v.manualState={status,updatedAt:now,actor,source:'manual',activityVersion:(v.manualState?.activityVersion??0)+1,lastActivityAt:now,invalidationReason:reason};
}
export function reading<T>(value:T,now:string,unit?:string):Reading<T>{return {value,observedAt:now,receivedAt:now,source:'vehicle_simulator',quality:'demo',unit};}
export function seedState(base=new Date().toISOString()):AppState{
 const day=inputDate(base).slice(0,10); const at=(t:string)=>fromInput(day+'T'+t); const now=at('14:00');
 const vehicles:Vehicle[]=[['EP-01','大分駅前ハブ',30,1284],['EP-02','Garraway 0',76,896],['EP-03','わさだ拠点',62,2310]].map(([id,loc,soc,odo])=>({id:String(id),name:'e-Palette',location:reading(String(loc),now),soc:reading(Number(soc),now,'%'),odometer:reading(Number(odo),now,'km'),charging:reading('not_connected',now),power:reading(0,now,'kW'),fault:reading('none',now),hold:false,holdReason:'',seats:8,usableKwh:60,acKw:6,dcKw:90,profileVerified:false,profileVersion:'simulation-v1'}));
 const make=(id:string,title:string,purpose:Purpose,vehicleId:string,start:string,end:string,status:Booking['status'],driverId:string,distance:number,targetSoc:number):Booking=>({id,title,purpose,vehicleId,start:at(start),end:at(end),status,driverId,distance,targetSoc,buffer:15,reserveKwh:8,auxiliaryKwh:purpose==='shop'?4:1,seats:8,route:purpose==='shop'?'Garraway 0': '大分駅前 → 地域拠点',checks:[],returnChecks:[],sessionId:null,organization:'MDL 実証チーム'});
 return {version:1,mode:'demo',clock:now,vehicles,bookings:[make('b1','夕方の地域送迎','shuttle','EP-01','16:00','17:00','confirmed','d1',45,70),make('b2','まちのモバイルストア','shop','EP-02','13:00','15:00','active','d2',0,35),make('b3','拠点間オンデマンド','ondemand','EP-03','17:00','18:00','confirmed','d3',12,40),make('b0','朝の駅前送迎','shuttle','EP-01','09:00','10:00','completed','d1',20,40)],sessions:[],tasks:[{id:'t1',title:'営業終了後の清掃を引き継ぐ',vehicleId:'EP-02',bookingId:'b2',owner:'d2',deadline:at('15:20'),status:'requested',kind:'clean',note:'16:00からの次の利用に備えます。'}],tickets:[{id:'tk1',bookingId:'b1',label:'乗車予約 001',count:2,from:0,to:1,status:'reserved'},{id:'tk2',bookingId:'b1',label:'乗車予約 002',count:3,from:0,to:1,status:'reserved'}],rides:[{id:'r1',from:'大分駅前',to:'地域拠点',count:2,requestedAt:now,start:at('14:30'),end:at('15:00'),status:'waiting',vehicleId:null,bookingId:null}],orders:[{id:'o1',bookingId:'b2',productId:'p1',quantity:2,number:'101',status:'received',payment:'unpaid',pickup:at('14:15')},{id:'o2',bookingId:'b2',productId:'p2',quantity:1,number:'102',status:'ready',payment:'paid',pickup:at('14:20')}],products:[{id:'p1',name:'季節のお弁当',price:800,stock:12,accepting:true},{id:'p2',name:'ドリップコーヒー',price:350,stock:20,accepting:true}],staff:[{id:'d1',name:'送迎担当 A',validUntil:'2028-12-31',active:true},{id:'d2',name:'販売・清掃担当 B',validUntil:'2028-12-31',active:true},{id:'d3',name:'運行・充電担当 C',validUntil:'2028-12-31',active:true}],stations:[{id:'dc1',name:'拠点の急速充電器',type:'dc',kw:90,travelMin:10,waitMin:0,shared:1,compatible:true,accessConfirmed:true},{id:'ac1',name:'車庫の普通充電器',type:'ac',kw:6,travelMin:10,waitMin:0,shared:1,compatible:true,accessConfirmed:true},{id:'dc2',name:'共同利用の急速充電器',type:'dc',kw:50,travelMin:15,waitMin:null,shared:2,compatible:true,accessConfirmed:false}],events:[],receivedEvents:[]};
}
export function neededSoc(v:Vehicle,b:Booking){return Math.max(b.targetSoc,Math.ceil(((b.distance+10)*(v.consumption??0.42)+b.auxiliaryKwh+b.reserveKwh)/v.usableKwh*100));}
export function nextBooking(s:AppState,vehicleId:string){return s.bookings.filter(b=>b.vehicleId===vehicleId&&b.status==='confirmed'&&b.end>s.clock).sort((a,b)=>a.start.localeCompare(b.start))[0];}
export function reverseChargeDeadline(start:string,chargeMin:number,travelMin=10,waitMin=0){const finishAt=shift(start,-35);const startAt=shift(finishAt,-chargeMin);return {finishAt,startAt,leaveAt:shift(startAt,-travelMin-5-waitMin)};}
export type ChargeEstimate={valid:boolean;reason:string;min:number;max:number;energy:number;target:number;leaveAt:string;startAt:string;finishAt:string;possible:boolean;uncertain:boolean;stationId:string};
export function estimate(s:AppState,v:Vehicle,b:Booking,stationId:string,target?:number):ChargeEstimate{
 const st=s.stations.find(x=>x.id===stationId); if(!st)throw new DomainError(422,'充電器が見つかりません。'); const goal=target??neededSoc(v,b); const finishAt=shift(b.start,-((st.releaseMin??20)+(st.inspectionMin??15)));
 const base={valid:false,reason:'',min:0,max:0,energy:0,target:goal,leaveAt:finishAt,startAt:finishAt,finishAt,possible:false,uncertain:st.waitMin===null||!st.accessConfirmed,stationId};
 if(!Number.isFinite(goal)||goal<0||goal>100)return {...base,reason:'必要残量が車両の容量を超えています。予定を変更してください。'};
 if(s.mode==='operational'&&(!v.profileVerified||!st.basis))return {...base,reason:'車両・充電器の実条件と根拠を管理者が登録してください。'};
 if(!socFresh(s,v))return {...base,reason:'現在の残量を確認できません。車両情報の更新が必要です。'};
 if(!st.compatible)return {...base,reason:'この車両に対応する充電器ではありません。'};
 if(v.charging.value==='interrupted')return {...base,reason:'充電が中断しています。再開を確認してください。'};const soc=v.soc.value!; let raw=0; const energy=Math.max(0,(goal-soc)/100*v.usableKwh);
 if(st.type==='ac')raw=energy/(Math.min(st.kw/st.shared,v.acKw)*(v.efficiency??0.9))*60;
 else for(let a=soc;a<goal;a+=0.25){const piece=Math.min(.25,goal-a)/100*v.usableKwh; const curve=v.dcCurve?.[a<50?0:a<80?1:2]??(a<50?60:a<80?45:18);const livePower=v.charging.value==='charging'&&fresh(v.power,s.clock)&&v.power.value!==null?v.power.value:Infinity;const power=Math.min(st.kw/st.shared,v.dcKw,curve,livePower);if(power<=0)return {...base,reason:'接続していますが充電電力が確認できません。'};raw+=piece/power*60;}
 const min=energy===0?0:Math.ceil(raw/5)*5; const max=energy===0?0:Math.ceil((raw*(st.type==='ac'?1.05:1.25)+(st.type==='dc'?4:0))/5)*5;
 const startAt=shift(finishAt,-max),leaveAt=shift(startAt,-st.travelMin-(st.connectMin??5)-(st.waitMin??0));
 return {...base,valid:true,min,max,energy,target:goal,startAt,leaveAt,possible:leaveAt>=s.clock,reason:base.uncertain?'待ち時間・利用権限を確認してください。':s.mode==='demo'?'検証用モデルによる見込みです。':'登録した実条件を使った見込みです。実施・確認済みではありません。'};
}
export function readiness(s:AppState,v:Vehicle,b?:Booking){
 if(v.hold)return {type:'blocked',label:'利用できません',reason:v.holdReason||'使用保留中'};
 if(s.mode==='operational'&&(!v.profileVerified||!s.policy))return {type:'unknown',label:'確認できません',reason:'車両条件と確認期限の設定が必要です'};
 const fieldAge=s.mode==='operational'?manualSocMaxAgeMinutes(s):10;
 if(!socFresh(s,v)||!fresh(v.fault,s.clock,fieldAge)||!fresh(v.charging,s.clock,fieldAge)||!fresh(v.location,s.clock,fieldAge))return {type:'unknown',label:'確認できません',reason:'車両情報が古いか、取得できていません'};
 if(s.mode==='operational'&&!s.fieldObservations?.some(x=>x.id===v.fieldObservationId&&x.activityVersion===v.manualState?.activityVersion))return {type:'unknown',label:'確認できません',reason:'利用・充電後の場所・異常・プラグを再確認してください'};
 if(s.mode==='operational'&&[v.fault,v.charging,v.location].some(x=>x.quality!=='manual'))return {type:'unknown',label:'確認できません',reason:'残量・場所・異常・プラグを現場で確認してください'};
 if(v.charging.value!=='not_connected')return {type:'blocked',label:'利用できません',reason:'プラグの解除・充電終了を現場で確認してください'};
 if(v.fault.value!=='none')return {type:'blocked',label:'利用できません',reason:'車両の異常確認が必要です'};
 const current=s.bookings.find(x=>x.vehicleId===v.id&&['active','return_requested','received'].includes(x.status));
 if(current&&current.id!==b?.id)return {type:'action',label:'対応してください',reason:current.status==='active'?'現在の利用・返却が完了していません':'返却の受領・次回準備を確認してください'};
 if(b){const driver=s.staff.find(x=>x.id===b.driverId);if(!driver?.active||driver.validUntil<inputDate(b.start).slice(0,10))return {type:'blocked',label:'利用できません',reason:'運行日時点の担当者・資格を確認してください'};
 const target=neededSoc(v,b);if(target>100)return {type:'blocked',label:'利用できません',reason:'必要電力量が電池容量を超えます'};
 if(v.soc.value!<target)return {type:'action',label:'対応してください',reason:`次の利用までに残量${target}％が必要です`};
 }
 if(s.mode==='operational'&&s.tasks.some(t=>t.vehicleId===v.id&&t.status!=='completed'))return {type:'action',label:'対応してください',reason:'未完了の準備・引継ぎが残っています'};
 return {type:'ready',label:'準備できる見込み',reason:'開始前の現場確認は別途必要です'};
}
export function conflict(s:AppState,b:Booking,skip=''){
 return s.bookings.find(x=>x.id!==skip&&x.id!==b.id&&!['draft','requested','rejected','completed','cancelled'].includes(x.status)&&(x.vehicleId===b.vehicleId||x.driverId===b.driverId||(x.resourceIds??[]).some(id=>b.resourceIds?.includes(id)))&&Date.parse(shift(x.start,-x.buffer))<Date.parse(shift(b.end,b.buffer))&&Date.parse(shift(x.end,x.buffer))>Date.parse(shift(b.start,-b.buffer)));
}
export class DomainError extends Error{constructor(public status:number,message:string){super(message);}}
const requireThat=(ok:unknown,message:string)=>{if(!ok)throw new DomainError(422,message);};
function number(n:unknown,min:number,max:number){requireThat(typeof n==='number'&&Number.isFinite(n)&&n>=min&&n<=max,'入力した数値を確認してください。');return n as number;}
function text(v:unknown,max=200){requireThat(typeof v==='string'&&v.trim().length>0&&v.length<=max,'必要な項目を入力してください。');return (v as string).trim();}
function validISO(v:unknown){requireThat(typeof v==='string'&&Number.isFinite(Date.parse(v)),'日時を確認してください。');return new Date(v as string).toISOString();}
function manualISO(value:unknown) {
 requireThat(typeof value==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|[+-]\d{2}:\d{2})$/.test(value),'確認日時はタイムゾーン付きの日時で入力してください。');
 const raw=value as string,iso=validISO(raw),day=raw.slice(0,10);
 requireThat(new Date(day+'T00:00:00.000Z').toISOString().slice(0,10)===day&&Number(raw.slice(11,13))<24,'確認日時を確認してください。');
 return iso;
}
function commandKeys(c:Command,allowed:string[]){requireThat(Object.keys(c).every(key=>allowed.includes(key)),'未対応の入力項目があります。');}
export type Command={type:string;[key:string]:unknown};
export type RecordSocCommand = {type:'record_soc'|'record_manual_soc'; vehicleId:string; stage:ManualSocStage; soc:number; observedAt:string; recorder:string; safeStationaryConfirmed:true; confirmed:true};
export type DeclareVehicleStateCommand = {type:'declare_vehicle_state'; vehicleId:string; status:ManualVehicleStatus; safeStationaryConfirmed?:boolean};
export type SetManualPolicyCommand = {type:'set_manual_policy'; maxAgeMinutes:number};
export type SetManualMotionCommand = {type:'set_manual_motion'; vehicleId:string; motion:'stationary'|'moving'; safeStationaryConfirmed?:boolean};
export function applyCommand(input:AppState,c:Command,actor='管理者'):AppState{
 const s=structuredClone(input); const id=()=>newId(); const vehicle=(v:unknown)=>{const x=s.vehicles.find(x=>x.id===v);if(!x)throw new DomainError(404,'車両が見つかりません。');return x;}; const booking=(v:unknown)=>{const b=s.bookings.find(x=>x.id===v);if(!b)throw new DomainError(404,'予定が見つかりません。');return b;};
 let label='';
 const extra=applyOperations(s,c,actor);
 if(extra!==null){s.version+=1;s.events.unshift({id:id(),time:s.clock,label:extra,actor});s.events=s.events.slice(0,500);return s;}
 switch(c.type){
 case 'set_manual_policy':{
 commandKeys(c,['type','maxAgeMinutes']);requireThat(s.mode==='demo','試験用の仮設定は模擬環境専用です。');
 const maxAgeMinutes=number(c.maxAgeMinutes,1,120);requireThat(Number.isInteger(maxAgeMinutes),'確認期限は1〜120分の整数で入力してください。');
 s.manualSocMaxAgeMinutes=maxAgeMinutes;label=`手入力残量の確認期限を試験用の仮設定${maxAgeMinutes}分に変更（安全保証ではありません）`;break;
 }
 case 'record_soc':
 case 'record_manual_soc':{
 commandKeys(c,['type','vehicleId','stage','soc','observedAt','recorder','safeStationaryConfirmed','confirmed']);
 const v=vehicle(c.vehicleId),soc=number(c.soc,0,100),stage=c.stage as ManualSocStage;
 requireThat(Number.isInteger(soc),'残量は0〜100の整数で入力してください。');
 requireThat(['start','return','after_charge'].includes(stage),'確認する場面を選んでください。');
 requireThat(c.safeStationaryConfirmed===true,'安全な場所への停車を確認してください。');
 requireThat(c.confirmed===true,'記録する内容を確認してから確定してください。');
 requireThat(v.manualState?.status!=='moving','走行中は記録できません。安全に停車してから停車の申告をしてください。');
 requireThat(v.manualState?.status!=='charging','充電中は記録できません。充電を終えてから停車の申告をしてください。');
 const observedAt=manualISO(c.observedAt),recorder=text(c.recorder,120),recordActor=text(actor,200);
 requireThat(Date.parse(observedAt)<=Date.parse(s.clock),'未来の確認日時は記録できません。');
 requireThat(!v.manualState?.lastActivityAt||Date.parse(observedAt)>=Date.parse(v.manualState.lastActivityAt),'最後の利用・充電または状態変更より後に残量を再確認してください。');
 const activityVersion=v.manualState?.activityVersion??0;
 const observation:ManualSocObservation={id:id(),vehicleId:v.id,stage,soc,observedAt,recordedAt:s.clock,recorder,actor:recordActor,source:'manual',safeStationaryConfirmed:true,confirmed:true,activityVersion};
 s.manualSocObservations=[...(s.manualSocObservations??[]),observation];
 const current=s.manualSocObservations.find(x=>x.id===v.manualSocObservationId);
 // Late offline entries remain evidence but never replace a newer observation.
 if(!current||Date.parse(observedAt)>=Date.parse(current.observedAt)){
 v.soc={value:soc,observedAt,receivedAt:s.clock,source:'manual',quality:'manual',unit:'%'};
 v.manualSocObservationId=observation.id;
 v.manualState={...v.manualState,status:'stationary',updatedAt:s.clock,actor:recordActor,source:'manual',activityVersion};
 }
 label=`${v.id}の残量${soc}％を手入力で確認（${MANUAL_SOC_STAGES[stage]}・記録者：${recorder}）`;break;
 }
 case 'set_manual_motion':
 case 'declare_vehicle_state':{
 commandKeys(c,c.type==='set_manual_motion'?['type','vehicleId','motion','safeStationaryConfirmed']:['type','vehicleId','status','safeStationaryConfirmed']);
 const v=vehicle(c.vehicleId),status=(c.type==='set_manual_motion'?c.motion:c.status) as ManualVehicleStatus;
 requireThat((c.type==='set_manual_motion'?['stationary','moving']:['stationary','moving','charging','unknown']).includes(status),'車両の申告状態を選んでください。');
 requireThat(status!=='stationary'||c.safeStationaryConfirmed===true,'安全な場所への停車を確認してください。');
 const recordActor=text(actor,200),activityVersion=v.manualState?.activityVersion??0;
 v.manualState={...v.manualState,status,updatedAt:s.clock,actor:recordActor,source:'manual',activityVersion:activityVersion+(status==='stationary'?0:1),...(status!=='stationary'?{lastActivityAt:s.clock,invalidationReason:'車両状態の申告変更'}:v.manualState&&v.manualState.status!=='stationary'?{lastActivityAt:s.clock}:{})};
 const labels:Record<ManualVehicleStatus,string>={stationary:'安全に停車',moving:'走行中',charging:'充電中',unknown:'未確認'};
 label=`${v.id}の現場状態を「${labels[status]}」と申告（実車操作なし）`;break;
 }

 case 'create_booking':{
 const v=vehicle(c.vehicleId); const purpose=c.purpose as Purpose;requireThat(['shuttle','ondemand','shop','charge'].includes(purpose),'用途を選んでください。'); const start=validISO(c.start),end=validISO(c.end);requireThat(end>start&&minutes(end,start)<=10080&&start>=s.clock,'開始・終了日時を確認してください。');
 const staff=s.staff.find(x=>x.id===c.driverId);requireThat(staff?.active&&staff.validUntil>=inputDate(start).slice(0,10),'担当者の資格期限・勤務状態を確認してください。'); requireThat(!v.hold,'使用保留中の車両です。');requireThat(s.mode==='demo'||v.profileVerified,'車両の電池・充電条件を設定してください。');
 const b:Booking={id:id(),title:text(c.title,80),purpose,vehicleId:v.id,driverId:staff!.id,start,end,buffer:15,status:'confirmed',route:text(c.route,120),distance:number(c.distance,0,500),reserveKwh:8,auxiliaryKwh:purpose==='shop'?4:1,targetSoc:number(c.targetSoc,0,100),seats:v.seats,checks:[],returnChecks:[],sessionId:null,returnReceiverId:s.mode==='operational'?actor:undefined,organization:s.organizationName??'MDL 実証チーム'};
 requireThat(!conflict(s,b),'前後15分の準備時間を含め、車両または担当者の予定が重なっています。');requireThat(neededSoc(v,b)<=100,'必要電力が電池容量を超えます。距離・用途を見直してください。');s.bookings.push(b);label=`${b.title}の予定を確定`;break;
 }
 case 'cancel_booking':{const b=booking(c.id);requireThat(['draft','requested','rejected','confirmed'].includes(b.status),'利用開始後は予定取消できません。');requireThat(!s.tickets.some(t=>t.bookingId===b.id&&!['cancelled','alighted'].includes(t.status)),'乗客の予約を先に取り消してください。');requireThat(!s.orders.some(o=>o.bookingId===b.id&&!['cancelled','handed'].includes(o.status)),'未受取注文への対応を先に行ってください。');b.status='cancelled';label=`${b.title}を取消`;break;}
 case 'check_in':{const b=booking(c.id),v=vehicle(b.vehicleId);requireThat(b.status==='confirmed','開始済み、または開始できない予定です。');const ready=readiness(s,v,b);requireThat(ready.type==='ready',ready.reason);if(s.mode==='operational'||v.manualState)requireThat(manualSocStatus(s,v).observation?.stage==='start','利用開始時の残量を手入力で確認してください。');requireThat(minutes(b.start,s.clock)<=30&&s.clock<b.end,'開始30分前から予定終了までに確認してください。');requireThat(Array.isArray(c.checks)&&CHECKS.every(x=>(c.checks as string[]).includes(x)),'必要な現場確認をすべて実施してください。');requireThat(v.charging.value==='not_connected','充電の終了・プラグ解除を確認してください。');b.checks=[...CHECKS];b.status='active';b.sessionId=id();s.sessions.push({id:b.sessionId,bookingId:b.id,startedAt:s.clock,endedAt:null,startSoc:structuredClone(v.soc),endSoc:null,startOdometer:structuredClone(v.odometer),endOdometer:null,checkVersion:'demo-checks-v1',checkedBy:actor});invalidateManualSoc(v,s.clock,actor,'利用開始');label=`${b.title}の利用開始を記録`;break;}
 case 'check_out':{const b=booking(c.id),v=vehicle(b.vehicleId);requireThat(b.status==='active','利用中の予定から返却してください。');if(s.mode==='operational'||v.manualState||v.manualSocObservationId){const status=manualSocStatus(s,v);requireThat(status.valid&&status.observation?.stage==='return','安全に停車し、返却時の最新残量を手入力で確認してください。');}requireThat(Array.isArray(c.checks)&&RETURN_CHECKS.every(x=>(c.checks as string[]).includes(x)),'必要な返却確認を実施してください。');const unresolved=s.orders.some(o=>o.bookingId===b.id&&!['handed','cancelled'].includes(o.status))||s.tickets.some(t=>t.bookingId===b.id&&t.status==='boarded');b.returnChecks=[...RETURN_CHECKS];b.status='return_requested';b.returnedBy=actor;const se=s.sessions.find(x=>x.id===b.sessionId);if(se){se.endedAt=s.clock;se.endSoc=structuredClone(v.soc);se.endOdometer=structuredClone(v.odometer);}if(unresolved)s.tasks.push({id:id(),title:'未降車・未受取を確認する',vehicleId:v.id,bookingId:b.id,owner:b.returnReceiverId??'',deadline:s.clock,status:'requested',kind:'review',note:'受領する前に乗客・注文の対応を完了してください。'});label=`${b.title}の返却を申請`;break;}
 case 'receive_return':{const b=booking(c.id);requireThat(b.status==='return_requested','返却申請が必要です。');requireThat(s.mode==='demo'||(!!b.returnReceiverId&&s.staff.some(x=>x.id===b.returnReceiverId&&x.active)&&(actor===b.returnReceiverId||typeof c.delegateReason==='string'&&c.delegateReason.trim().length>=5)),'返却の受領担当者本人、または理由を記録した管理者が受領してください。');requireThat(!s.orders.some(o=>o.bookingId===b.id&&!['handed','cancelled'].includes(o.status))&&!s.tickets.some(t=>t.bookingId===b.id&&t.status==='boarded'),'未降車者・未受取注文への対応が残っています。');b.status='received';b.receivedBy=actor;b.receivedAt=s.clock;label=`${b.title}の返却を受領`;break;}
 case 'release_vehicle':{const b=booking(c.id),v=vehicle(b.vehicleId);requireThat(b.status==='received','管理側の受領が必要です。');requireThat(!v.hold&&socFresh(s,v),'車両の保留・最新残量を確認してください。');requireThat(!s.tasks.some(t=>t.vehicleId===v.id&&t.status!=='completed'),'未完了の引継ぎがあります。');const nb=nextBooking(s,v.id);requireThat(!nb||v.soc.value!>=neededSoc(v,nb),'次の利用に必要な充電が残っています。');const result=readyToRelease(s,b);requireThat(result.type==='ready',result.reason);b.status='completed';label=`${v.id}を次に貸出可能として記録`;break;}
 case 'assign_charge':{const v=vehicle(c.vehicleId),b=booking(c.bookingId);requireThat(b.vehicleId===v.id&&b.status==='confirmed','充電の対象予定を確認してください。');const e=estimate(s,v,b,text(c.stationId),c.targetSoc===undefined?undefined:number(c.targetSoc,0,100));requireThat(e.valid&&e.possible&&!e.uncertain,e.reason||'開始期限を過ぎています。予定を見直してください。');const staff=s.staff.find(x=>x.id===c.owner&&x.active);requireThat(staff,'担当者を選んでください。');requireThat(!s.tasks.some(t=>t.vehicleId===v.id&&t.kind==='charge'&&t.status!=='completed'),'この車両には未完了の充電依頼があります。');const st=s.stations.find(x=>x.id===c.stationId)!;requireThat(st,'充電器を選んでください。');requireThat(!s.tasks.some(t=>t.kind==='charge'&&t.stationId===st.id&&t.status!=='completed'&&t.chargeStart&&t.chargeEnd&&overlap(e.startAt,e.finishAt,t.chargeStart,t.chargeEnd)),'この充電枠には別の車両の依頼があります。');s.tasks.push({id:id(),chargeStart:e.startAt,chargeEnd:e.finishAt,requestedBy:actor,title:`${v.id}を${e.target}％まで充電`,vehicleId:v.id,bookingId:b.id,owner:staff!.id,deadline:e.leaveAt,status:'requested',kind:'charge',mode:st.type,targetSoc:e.target,stationId:st.id,note:'依頼送信は充電器の外部予約・遠隔開始ではありません。'});label=`${v.id}の充電を${staff!.name}へ依頼`;break;}
 case 'task_action':{const t=s.tasks.find(x=>x.id===c.id);requireThat(t,'引継ぎが見つかりません。');if(c.action==='reassign'){t!.owner=text(c.owner);requireThat(s.staff.some(x=>x.id===t!.owner&&x.active),'担当者が不在です。');t!.status='requested';label='引継ぎの担当者を変更';}else if(c.action==='acknowledge'){requireThat(t!.status==='requested'&&s.staff.some(x=>x.id===t!.owner&&x.active),'受領できる担当者がいません。再割当てが必要です。');requireThat(s.mode==='demo'||actor===t!.owner||typeof c.delegateReason==='string'&&c.delegateReason.trim().length>=5,'受領は担当者本人が行ってください。管理者の代理は理由の記録が必要です。');t!.status='acknowledged';t!.acknowledgedBy=actor;label='担当者の受領を記録';}else if(c.action==='complete'){requireThat(['acknowledged','working'].includes(t!.status),'先に担当者の受領が必要です。');requireThat(s.mode==='demo'||actor===t!.owner||typeof c.delegateReason==='string'&&c.delegateReason.trim().length>=5,'完了は担当者本人が確認してください。');const v=vehicle(t!.vehicleId);if(t!.kind==='charge'){requireThat(socFresh(s,v)&&v.soc.value!>=t!.targetSoc!&&v.charging.value==='not_connected','必要残量への到達とプラグ解除・移動を確認してください。');if(v.manualState)requireThat(manualSocStatus(s,v).observation?.stage==='after_charge','充電後の残量を手入力で確認してください。');}if(t!.kind==='review')requireThat(!s.orders.some(o=>o.bookingId===t!.bookingId&&!['handed','cancelled'].includes(o.status))&&!s.tickets.some(x=>x.bookingId===t!.bookingId&&x.status==='boarded'),'未受取・未降車への対応が残っています。');t!.status='completed';t!.completedBy=actor;t!.completedAt=s.clock;label='引継ぎ作業の完了を記録';}else throw new DomainError(422,'無効な操作です。');break;}
 case 'report_incident':{const v=vehicle(c.vehicleId);v.hold=true;v.holdReason=text(c.reason);s.tasks.push({id:id(),title:`${v.id}の異常を確認`,vehicleId:v.id,bookingId:null,owner:'',deadline:s.clock,status:'requested',kind:'review',note:v.holdReason});s.incidents=[...(s.incidents??[]),{id:id(),vehicleId:v.id,reason:v.holdReason,reportedAt:s.clock,reportedBy:actor,affected:s.bookings.filter(b=>b.vehicleId===v.id&&!['completed','cancelled'].includes(b.status)).map(b=>b.id)}];label=`${v.id}を使用保留`;break;}
 case 'resolve_incident':{const v=vehicle(c.vehicleId);requireThat(v.hold,'使用保留中ではありません。');text(c.reason);requireThat(fresh(v.fault,s.clock)&&v.fault.value==='none','最新の車両異常情報を確認し、異常解消後に復旧してください。');v.hold=false;v.holdReason='';v.fault={...v.fault,receivedAt:s.clock};for(const issue of s.incidents??[])if(issue.vehicleId===v.id&&!issue.resolvedAt){issue.resolvedAt=s.clock;issue.resolvedBy=actor;issue.resolution=String(c.reason);}label=`${v.id}の復旧を確認：${c.reason}`;break;}
 case 'ticket_action':{const t=s.tickets.find(x=>x.id===c.id);requireThat(t,'乗車予約が見つかりません。');const b=booking(t!.bookingId);if(c.action==='board'){requireThat(t!.status==='reserved'&&b.status==='active','利用開始後、予約済みのチケットで乗車を記録してください。');t!.status='boarded';}else if(c.action==='alight'){requireThat(t!.status==='boarded','乗車済みのチケットを選んでください。');t!.status='alighted';}else if(c.action==='cancel'){requireThat(t!.status==='reserved','乗車後の取消はできません。');t!.status='cancelled';}else throw new DomainError(422,'無効な操作です。');label=`${t!.label}の${c.action==='board'?'乗車':c.action==='alight'?'降車':'取消'}を記録`;break;}
 case 'create_ticket':{const b=booking(c.bookingId);requireThat(b.status==='confirmed'||b.status==='active','受付可能な便を選んでください。');requireThat(b.purpose!=='shop'&&b.purpose!=='charge','乗車できる便を選んでください。');const count=number(c.count,1,b.seats),from=number(c.from,0,9),to=number(c.to,1,10);requireThat(Number.isInteger(count)&&Number.isInteger(from)&&Number.isInteger(to)&&to>from,'人数・区間を確認してください。');for(let leg=from;leg<to;leg++){const sum=s.tickets.filter(t=>t.bookingId===b.id&&t.status!=='cancelled'&&t.from<=leg&&t.to>leg).reduce((n,t)=>n+t.count,0);requireThat(sum+count<=b.seats,'この区間の定員を超えます。');}s.tickets.push({id:id(),bookingId:b.id,label:`乗車予約 ${s.tickets.length+1}`,count,from,to,status:'reserved'});label='乗車予約を登録';break;}
 case 'create_ride':{const start=validISO(c.start),end=shift(start,30);requireThat(start>=s.clock,'現在以降の時刻を選んでください。');s.rides.push({id:id(),from:text(c.from),to:text(c.to),count:(()=>{const n=number(c.count,1,30);requireThat(Number.isInteger(n),'人数は整数で入力してください。');return n})(),requestedAt:s.clock,start,end,status:'waiting',vehicleId:null,bookingId:null});label='オンデマンド依頼を受付';break;}
 case 'assign_ride':{const r=s.rides.find(x=>x.id===c.id);requireThat(r?.status==='waiting','未割当の依頼を選んでください。');const v=vehicle(c.vehicleId);const driver=s.staff.find(x=>x.id===c.driverId);requireThat(driver?.active&&driver.validUntil>=inputDate(r!.start).slice(0,10),'担当者の勤務・資格を確認してください。');const b:Booking={id:id(),title:`${r!.from} → ${r!.to}`,purpose:'ondemand',vehicleId:v.id,driverId:driver!.id,start:r!.start,end:r!.end,buffer:15,status:'confirmed',route:`${r!.from} → ${r!.to}`,distance:s.mode==='demo'?12:number(c.distance,0,1000),reserveKwh:8,auxiliaryKwh:1,targetSoc:40,seats:v.seats,checks:[],returnChecks:[],sessionId:null,returnReceiverId:s.mode==='operational'?actor:undefined,organization:s.organizationName??'MDL 実証チーム'};requireThat(r!.count<=v.seats&&!conflict(s,b)&&readiness(s,v,b).type==='ready'&&s.clock<=r!.start,'定員・残量・担当者・前後の予定に適合しません。別の車両・時刻を選んでください。');s.bookings.push(b);s.tickets.push({id:id(),bookingId:b.id,label:'オンデマンド乗車',count:r!.count,from:0,to:1,status:'reserved'});r!.status='assigned';r!.vehicleId=v.id;r!.bookingId=b.id;label=`${v.id}への配車を確定`;break;}
 case 'create_order':{const b=booking(c.bookingId);requireThat(b.purpose==='shop'&&['confirmed','active'].includes(b.status),'営業中・営業予定の物販を選んでください。');const p=s.products.find(x=>x.id===c.productId);const q=number(c.quantity,1,100);requireThat(Number.isInteger(q)&&p?.accepting&&p.stock>=q,'受付停止・売切れ、または数量不足です。');const pickup=validISO(c.pickup);requireThat(pickup>=b.start&&pickup<=b.end&&pickup>=s.clock,'営業時間内の受取日時を指定してください。');const capacity=b.pickupCapacity??(s.mode==='demo'?10:0);requireThat(capacity>0,'物販の15分あたり受取枠を管理者が設定してください。');const slot=Math.floor(minutes(pickup,b.start)/15);requireThat(s.orders.filter(o=>o.bookingId===b.id&&o.status!=='cancelled'&&Math.floor(minutes(o.pickup,b.start)/15)===slot).length<capacity,'この受取枠は満杯です。別の時刻を選んでください。');p!.stock-=q;s.orders.push({id:id(),bookingId:b.id,productId:p!.id,quantity:q,number:String(101+s.orders.length),status:'received',payment:'unpaid',pickup});label='注文を受付・数量を確保';break;}
 case 'order_action':{const o=s.orders.find(x=>x.id===c.id);requireThat(o,'注文が見つかりません。');if(c.action==='paid'){requireThat(o!.payment==='unpaid'&&o!.status!=='cancelled','支払状態を確認してください。');if(s.mode==='operational'){const reference=text(c.reference,200);o!.paymentEvidence=[...(o!.paymentEvidence??[]),{reference,actor,at:s.clock,kind:'payment'}];}o!.payment='paid';label='現地での支払確認を記録';}else if(c.action==='refund'){requireThat(o!.payment==='refund_pending','返金確認が必要な注文を選んでください。');if(s.mode==='operational'){const reference=text(c.reference,200);o!.paymentEvidence=[...(o!.paymentEvidence??[]),{reference,actor,at:s.clock,kind:'refund'}];}o!.payment='refunded';label='実際の返金完了を記録';}else if(c.action==='cancel'){requireThat(!['handed','cancelled'].includes(o!.status),'この注文は取消できません。');o!.status='cancelled';if(o!.payment==='paid')o!.payment='refund_pending';s.products.find(x=>x.id===o!.productId)!.stock+=o!.quantity;label='注文取消・必要な返金対応を記録';}else{const next:Record<string,string>={received:'preparing',preparing:'ready',ready:'handed'};requireThat(next[o!.status]===c.action,'この状態へ変更できません。');if(c.action==='handed')requireThat(o!.payment==='paid','支払確認を先に記録してください。');o!.status=c.action as Order['status'];label=`注文 ${o!.number} を更新`;}break;}
 case 'toggle_product':{const p=s.products.find(x=>x.id===c.id);requireThat(p,'商品が見つかりません。');p!.accepting=!p!.accepting;label=`${p!.name}の受付${p!.accepting?'再開':'停止'}`;break;}
 case 'simulate':{const v=vehicle(c.vehicleId);requireThat(s.mode==='demo','模擬環境専用です。');if(c.soc!==undefined||c.charging!==undefined)invalidateManualSoc(v,s.clock,actor,'模擬車両情報の変更',c.charging==='charging'?'charging':'unknown');if(c.scenario==='stale'){v.soc.observedAt=shift(s.clock,-1440);label=`${v.id}の更新遅延を再現`;}else if(c.scenario==='fault'){v.fault=reading('warning',s.clock);v.hold=true;v.holdReason='模擬の車両異常';label='車両異常を再現';}else{if(c.scenario==='recovered')v.fault=reading('none',s.clock);if(c.soc!==undefined)v.soc=reading(number(c.soc,0,100),s.clock,'%');if(c.charging!==undefined){requireThat(['not_connected','connected','charging','interrupted','target_reached','finished'].includes(String(c.charging)),'充電状態を確認してください。');v.charging=reading(String(c.charging),s.clock);v.power=reading(c.charging==='charging'?number(c.power??45,0,90):0,s.clock,'kW');}v.location={...v.location,observedAt:s.clock,receivedAt:s.clock};v.fault={...v.fault,observedAt:s.clock,receivedAt:s.clock};v.odometer={...v.odometer,observedAt:s.clock,receivedAt:s.clock};if(c.charging===undefined)v.charging={...v.charging,observedAt:s.clock,receivedAt:s.clock};label=`${v.id}の模擬車両情報を更新`;}break;}
 case 'advance_clock':{requireThat(s.mode==='demo','検証時刻は体験環境専用です。');const n=number(c.minutes,1,1440);s.clock=shift(s.clock,n);label=`検証時刻を${n}分進める`;break;}
 case 'reset_demo':{requireThat(s.mode==='demo','実業務データは初期化できません。');const n=seedState(s.clock);n.version=s.version;if(s.manualSocMaxAgeMinutes!==undefined)n.manualSocMaxAgeMinutes=manualSocMaxAgeMinutes(s);if(s.manualSocObservations?.length){n.manualSocObservations=s.manualSocObservations;for(const v of n.vehicles){const previous=s.vehicles.find(x=>x.id===v.id);if(previous?.manualState){v.manualState=structuredClone(previous.manualState);invalidateManualSoc(v,n.clock,actor,'検証データの初期化');}}}return {...n,events:[{id:id(),time:n.clock,label:'検証データを初期化',actor}],version:s.version+1};}
 default:throw new DomainError(422,'未対応の操作です。');
 }
 s.version+=1;s.events.unshift({id:id(),time:s.clock,label,actor});s.events=s.events.slice(0,500);return s;
}
