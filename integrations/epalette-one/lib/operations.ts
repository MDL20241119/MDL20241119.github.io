import {AppState,Booking,Command,DomainError,Vehicle,applyCommand,seedState,inputDate,shift,minutes,readiness,nextBooking,manualSocStatus,neededSoc,conflict} from './model.js';
import {newId} from './id.js';

export type FieldObservation={id:string;vehicleId:string;observedAt:string;recordedAt:string;actor:string;location:string;fault:string;charging:string;odometer:number;note:string;activityVersion:number};
export type OperationData={organizationName?:string;policy?:{maxAgeMinutes:number;basis:string;approvedBy:string;approvedAt:string};resources?:{id:string;name:string}[];fieldObservations?:FieldObservation[];incidents?:{id:string;vehicleId:string;reason:string;reportedAt:string;reportedBy:string;affected:string[];resolvedAt?:string;resolvedBy?:string;resolution?:string}[];contacts?:{id:string;bookingId:string;method:string;note:string;actor:string;at:string}[];actuals?:{bookingId:string;distanceKm:number|null;energyKwh:number|null;costYen:number|null;note:string;actor:string;at:string}[]};
const fail=(ok:unknown,message:string)=>{if(!ok)throw new DomainError(422,message)};
const text=(v:unknown,max=400)=>{fail(typeof v==='string'&&v.trim().length>0&&v.length<=max,'必須項目を入力してください。');return String(v).trim()};
const num=(v:unknown,min:number,max:number)=>{fail(typeof v==='number'&&Number.isFinite(v)&&v>=min&&v<=max,'数値の範囲を確認してください。');return Number(v)};
const iso=(v:unknown)=>{fail(typeof v==='string'&&/^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$/.test(v)&&Number.isFinite(Date.parse(v)),'日時を日本時間で入力してください。');return new Date(String(v)).toISOString()};
const keys=(c:Command,allowed:string[])=>fail(Object.keys(c).every(x=>['type',...allowed].includes(x)),'未対応の入力項目があります。');
export function currentTime(s:AppState,now=new Date().toISOString()):AppState{return s.mode==='operational'?{...s,clock:now}:s;}
export function newOperationalState(name:string,subject:string,displayName:string,count:number,now=new Date().toISOString()):AppState{
 fail(Number.isInteger(count)&&count>=1&&count<=3,'最初の車両数は1〜3台です。');
 const s=seedState(now);s.clock=now;s.mode='operational';s.organizationName=text(name,80);
 s.vehicles=s.vehicles.slice(0,count).map(v=>({...v,name:'車両名を設定',profileVerified:false,profileVersion:'未設定',manualState:{status:'unknown',updatedAt:now,actor:subject,source:'manual',activityVersion:0},...Object.fromEntries(['soc','location','charging','fault','odometer','power'].map(k=>[k,{value:null,observedAt:now,receivedAt:now,quality:'unavailable',source:'not_observed'}]))}));
 s.bookings=[];s.sessions=[];s.tasks=[];s.tickets=[];s.rides=[];s.orders=[];s.products=[];s.stations=[];s.events=[];s.staff=[{id:subject,name:displayName,active:true,validUntil:''}];s.resources=[];s.incidents=[];s.contacts=[];s.actuals=[];s.fieldObservations=[];
 return s;
}
export function readyToRelease(s:AppState,b:Booking){const v=s.vehicles.find(v=>v.id===b.vehicleId)!;const state={...s,bookings:s.bookings.map(x=>x.id===b.id?{...x,status:'completed' as const}:x)};return readiness(state,v,nextBooking(state,v.id));}
export function overlap(a:string,b:string,c:string,d:string){return Date.parse(a)<Date.parse(d)&&Date.parse(b)>Date.parse(c);}
function nested(s:AppState,c:Command,actor:string){const before=s.version,events=s.events;Object.assign(s,applyCommand(s,c,actor));s.version=before;s.events=events;}
export function applyOperations(s:AppState,c:Command,actor:string):string|null{
 const v=()=>{const x=s.vehicles.find(v=>v.id===c.vehicleId);if(!x)throw new DomainError(404,'車両が見つかりません。');return x};
 const booking=()=>{const x=s.bookings.find(b=>b.id===c.id);if(!x)throw new DomainError(404,'予定が見つかりません。');return x};
 switch(c.type){
 case 'request_booking':{nested(s,{...c,type:'save_booking_draft'},actor);const b=c.id?s.bookings.find(b=>b.id===c.id)!:s.bookings.at(-1)!;nested(s,{type:'submit_booking',id:b.id},actor);return `${b.title}を管理者へ申請`;}
 case 'set_return_receiver':{keys(c,['id','owner']);const b=booking();fail(!['completed','cancelled'].includes(b.status),'この予定の担当者は変更できません。');const owner=text(c.owner);fail(s.staff.some(x=>x.id===owner&&x.active),'受領者が不在です。');b.returnReceiverId=owner;return `${b.title}の返却受領者を変更`;}
 case 'set_policy':keys(c,['maxAgeMinutes','basis']);s.policy={maxAgeMinutes:num(c.maxAgeMinutes,1,120),basis:text(c.basis),approvedBy:actor,approvedAt:s.clock};fail(Number.isInteger(s.policy.maxAgeMinutes),'有効時間は整数で入力してください。');return '残量・現場確認の運用基準を記録';
 case 'configure_vehicle':{
  keys(c,['vehicleId','name','seats','usableKwh','acKw','dcKw','consumption','efficiency','dcLow','dcMid','dcHigh','basis']);const vehicle=v();
  Object.assign(vehicle,{name:text(c.name,80),seats:num(c.seats,1,30),usableKwh:num(c.usableKwh,1,500),acKw:num(c.acKw,1,350),dcKw:num(c.dcKw,1,500),consumption:num(c.consumption,.01,5),efficiency:num(c.efficiency,.5,1),dcCurve:[num(c.dcLow,1,500),num(c.dcMid,1,500),num(c.dcHigh,1,500)],profileVersion:text(c.basis),profileVerified:true,profileCheckedBy:actor,profileCheckedAt:s.clock});fail(Number.isInteger(vehicle.seats),'乗車枠は整数で入力してください。');return `${vehicle.id}の車両条件と根拠を記録`;
 }
 case 'configure_station':{
  keys(c,['id','name','chargingType','kw','travelMin','waitMin','shared','connectMin','releaseMin','inspectionMin','basis']);fail(['ac','dc'].includes(String(c.chargingType)),'充電方式を選んでください。');
  // The command discriminator is separate from the charging connector type.
  const id=text(c.id,60);const type=String(c.chargingType);
  const station={id,name:text(c.name,80),type:type as 'ac'|'dc',kw:num(c.kw,1,500),travelMin:num(c.travelMin,0,240),waitMin:num(c.waitMin,0,360),shared:num(c.shared,1,20),connectMin:num(c.connectMin,0,120),releaseMin:num(c.releaseMin,0,240),inspectionMin:num(c.inspectionMin,0,120),basis:text(c.basis),compatible:true,accessConfirmed:true};
  fail(Number.isInteger(station.shared),'同時利用台数は整数です。');const i=s.stations.findIndex(st=>st.id===id);if(i<0)s.stations.push(station);else s.stations[i]=station;return '充電場所・電力・作業時間の根拠を記録';
 }
 case 'set_staff':{keys(c,['id','validUntil','active','basis']);const staff=s.staff.find(x=>x.id===c.id);fail(staff,'担当者が見つかりません。');const date=text(c.validUntil,10);fail(/^\d{4}-\d{2}-\d{2}$/.test(date)&&new Date(date+'T00:00:00Z').toISOString().slice(0,10)===date,'資格の有効期限を確認してください。');staff!.validUntil=date;staff!.active=c.active===true;staff!.qualificationBasis=text(c.basis);return `${staff!.name}の勤務・資格確認を記録`;}
 case 'set_resources':{keys(c,['names']);fail(Array.isArray(c.names)&&c.names.length<=20,'設備を20件以内で入力してください。');const names=(c.names as unknown[]).map(n=>text(n,80));const old=s.resources??[];fail(old.every((r,i)=>names[i]===r.name),'既存設備の削除・並べ替えは、予約との対応が変わるためできません。末尾へ追加してください。');s.resources=names.map((name,i)=>({id:old[i]?.id??newId(),name}));return '共用設備を設定';}
 case 'record_inspection':{
  keys(c,['vehicleId','stage','soc','observedAt','recorder','safeStationaryConfirmed','confirmed','location','fault','charging','odometer','note']);const vehicle=v();
  const observedAt=iso(c.observedAt),location=text(c.location,120),odometer=num(c.odometer,0,9999999);
  fail(['none','warning'].includes(String(c.fault)),'異常の有無を確認してください。');fail(['not_connected','connected','interrupted'].includes(String(c.charging)),'プラグ・充電の状態を確認してください。');
  fail(vehicle.odometer.quality==='demo'||vehicle.odometer.value===null||odometer>=vehicle.odometer.value,'積算走行距離が前の記録より小さくなっています。');
  fail(c.safeStationaryConfirmed===true&&c.confirmed===true,'安全な停車と内容を確認してください。');
  if(vehicle.manualState?.status!=='stationary'){nested(s,{type:'declare_vehicle_state',vehicleId:vehicle.id,status:'stationary',safeStationaryConfirmed:true},actor);const after=s.vehicles.find(x=>x.id===vehicle.id)!;after.manualState!.lastActivityAt=vehicle.manualState?.lastActivityAt;}
  nested(s,{type:'record_soc',vehicleId:vehicle.id,stage:c.stage,soc:c.soc,observedAt,recorder:c.recorder,safeStationaryConfirmed:true,confirmed:true},actor);
  const actual=s.vehicles.find(x=>x.id===vehicle.id)!;const item:FieldObservation={id:newId(),vehicleId:actual.id,observedAt,recordedAt:s.clock,actor,location,fault:String(c.fault),charging:String(c.charging),odometer,note:String(c.note??'').slice(0,400),activityVersion:actual.manualState!.activityVersion};
  s.fieldObservations=[...(s.fieldObservations??[]),item];const prior=vehicle.location;
  if(prior.quality!=='manual'||observedAt>=prior.observedAt){for(const [key,value] of Object.entries({location,fault:c.fault,charging:c.charging,odometer})){(actual as unknown as Record<string,unknown>)[key]={value,observedAt,receivedAt:s.clock,quality:'manual',source:'manual',...(key==='odometer'?{unit:'km'}:{})};}actual.fieldObservationId=item.id;}
  if(c.fault!=='none'){const reason=item.note||'現場確認で異常を報告';if(!actual.hold)nested(s,{type:'report_incident',vehicleId:actual.id,reason},actor);else actual.holdReason=reason;}
  return `${actual.id}の残量・場所・プラグ・異常・距離を現場で確認`;
 }
 case 'save_booking_draft':{
  keys(c,['id','title','purpose','vehicleId','driverId','start','end','route','distance','targetSoc','buffer','resourceIds','returnReceiverId','equipment','people','pickupCapacity']);
  const old=c.id?booking():undefined;fail(!old||['draft','rejected'].includes(old.status),'申請済みの予定は直接編集できません。');
  const start=iso(c.start),end=iso(c.end);fail(end>start&&minutes(end,start)<=10080,'利用期間は7日以内で指定してください。');fail(['shuttle','ondemand','shop','charge'].includes(String(c.purpose)),'用途を選んでください。');
  const b:Booking={id:old?.id??newId(),title:text(c.title,80),purpose:c.purpose as Booking['purpose'],vehicleId:String(c.vehicleId??''),driverId:String(c.driverId??''),start,end,buffer:num(c.buffer??15,0,240),status:'draft',route:text(c.route,120),distance:num(c.distance,0,1000),targetSoc:num(c.targetSoc,0,100),reserveKwh:8,auxiliaryKwh:c.purpose==='shop'?4:1,seats:num(c.people??1,1,30),checks:[],returnChecks:[],sessionId:null,organization:s.organizationName??'体験チーム',requestedBy:old?.requestedBy??actor,returnReceiverId:String(c.returnReceiverId??''),resourceIds:Array.isArray(c.resourceIds)?c.resourceIds.map(String):[],equipment:String(c.equipment??'').slice(0,200),pickupCapacity:c.purpose==='shop'?num(c.pickupCapacity,1,100):undefined};
  fail(b.resourceIds!.every(id=>s.resources?.some(r=>r.id===id)),'設備の設定が変わりました。');if(old)s.bookings[s.bookings.indexOf(old)]=b;else s.bookings.push(b);return `${b.title}を下書き保存`;
 }
 case 'submit_booking':{keys(c,['id']);const b=booking();fail(['draft','rejected'].includes(b.status),'下書きから申請してください。');b.status='requested';b.requestedAt=s.clock;return `${b.title}を管理者へ申請`;}
 case 'approve_booking':{
  keys(c,['id','vehicleId','driverId','returnReceiverId']);const b=booking();fail(b.status==='requested','申請中の予定を選んでください。');const vid=String(c.vehicleId??b.vehicleId),did=String(c.driverId??b.driverId),receiver=String(c.returnReceiverId??b.returnReceiverId);
  fail(s.staff.some(x=>x.id===receiver&&x.active),'返却を受領する担当者を割り当ててください。');const vehicle=s.vehicles.find(v=>v.id===vid);fail(vehicle,'車両を選んでください。');fail(b.seats<=vehicle!.seats,'必要人数が車両の乗車枠を超えています。');
  const candidate={...b,vehicleId:vid,driverId:did,status:'confirmed' as const};fail(!conflict(s,candidate,b.id),'車両・担当者・共用設備の準備時間を含む予定が競合しています。');
  const before=s.bookings.length;nested(s,{type:'create_booking',...Object.fromEntries(['title','purpose','start','end','route','distance','targetSoc'].map(k=>[k,(b as unknown as Record<string,unknown>)[k]])),vehicleId:vid,driverId:did},actor);
  s.bookings.splice(before,1);Object.assign(s.bookings.find(x=>x.id===b.id)!,{...candidate,returnReceiverId:receiver,approvedBy:actor,approvedAt:s.clock,seats:Math.min(b.seats,vehicle!.seats)});return `${b.title}の車両・担当・設備を確定`;
 }
 case 'reject_booking':{keys(c,['id','reason']);const b=booking();fail(b.status==='requested','申請中の予定を選んでください。');b.status='rejected';b.changeReason=text(c.reason);return `${b.title}を理由付きで差し戻し`;}
 case 'reschedule_booking':{keys(c,['id','start','end','reason']);const b=booking();fail(b.status==='confirmed','確定済み・開始前の予定を選んでください。');const start=iso(c.start),end=iso(c.end);fail(start>=s.clock&&end>start&&minutes(end,start)<=10080,'変更日時を確認してください。');fail(!s.tickets.some(t=>t.bookingId===b.id&&t.status!=='cancelled')&&!s.orders.some(o=>o.bookingId===b.id&&!['handed','cancelled'].includes(o.status)),'先に乗車予約・注文の利用者と調整し、対象の予約・注文を取り消してください。');const candidate={...b,start,end};fail(!conflict(s,candidate,b.id),'変更先で予定が競合します。');b.start=start;b.end=end;b.changeReason=text(c.reason);return `${b.title}の予定変更：${b.changeReason}`;}
 case 'create_task':{keys(c,['vehicleId','bookingId','title','owner','deadline','kind','note']);const vehicle=v();const owner=text(c.owner);fail(s.staff.some(x=>x.id===owner&&x.active),'受け手がいません。別の担当者を選んでください。');const deadline=iso(c.deadline);fail(deadline>=s.clock,'期限が過去です。');fail(['clean','review','setup','maintenance','transfer'].includes(String(c.kind)),'作業の種類を選んでください。');s.tasks.push({id:newId(),vehicleId:vehicle.id,bookingId:c.bookingId?String(c.bookingId):null,title:text(c.title,100),owner,deadline,kind:c.kind as 'clean',status:'requested',note:text(c.note),requestedBy:actor});return '担当者・期限・次の行動を付けて作業を依頼';}
 case 'record_contact':{keys(c,['id','method','note']);const b=booking();s.contacts=[...(s.contacts??[]),{id:newId(),bookingId:b.id,method:text(c.method,80),note:text(c.note),actor,at:s.clock}];return `${b.title}の利用者への連絡を記録（受領・業務完了とは別）`;}
 case 'record_actuals':{keys(c,['id','distanceKm','energyKwh','costYen','note']);const b=booking();fail(['return_requested','received','completed'].includes(b.status),'利用終了後に実績を記録してください。');const nullable=(v:unknown,max:number)=>v===null||v===undefined?null:num(v,0,max);const item={bookingId:b.id,distanceKm:nullable(c.distanceKm,100000),energyKwh:nullable(c.energyKwh,100000),costYen:nullable(c.costYen,100000000),note:text(c.note),actor,at:s.clock};s.actuals=[...(s.actuals??[]),item];return `${b.title}の実績・予定との差を追記`;}
 case 'configure_product':{keys(c,['id','name','price','stock']);const id=c.id?text(c.id,80):newId();const stock=num(c.stock,0,100000);fail(Number.isInteger(stock),'在庫数は整数です。');const p={id,name:text(c.name,100),price:num(c.price,0,1000000),stock,accepting:true};const i=s.products.findIndex(p=>p.id===id);if(i<0)s.products.push(p);else s.products[i]=p;return '商品・価格・在庫を登録';}
 default:return null;
 }
}
export function utilizationMinutes(s:AppState){let total=0;for(const v of s.vehicles){const spans=s.sessions.filter(x=>s.bookings.find(b=>b.id===x.bookingId)?.vehicleId===v.id&&x.endedAt).map(x=>[Date.parse(x.startedAt),Date.parse(x.endedAt!)]).sort((a,b)=>a[0]-b[0]);let start=0,end=0;for(const [a,b]of spans){if(a>end){total+=Math.max(0,end-start);start=a;end=b}else end=Math.max(end,b)}total+=Math.max(0,end-start);}return total/60000;}
