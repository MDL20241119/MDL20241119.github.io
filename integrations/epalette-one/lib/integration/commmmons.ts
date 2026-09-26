import document from './contracts/demand.json';
import * as validators from './contracts/validators.mjs';
import {State,Principal,tripRecords,ownReservations,stops,passengerType,serviceId,getProposal,canonical,fail,permit} from './core';
import {inputDate} from '../model';
import {serviceCatalogue,requireDemo} from './network';
type Json=Record<string,any>;
export const demandDocument=document as Json;
export function validateContract(operation:string,phase:string,value:unknown){const key=`demand_${operation}_${phase}`;const fn=(validators as Record<string,(v:unknown)=>boolean>)[key];if(!fn||!fn(value))fail(phase==='request'||phase==='query'?400:503,phase==='request'||phase==='query'?'標準仕様の入力項目・型・必須条件を確認してください。':'応答が標準仕様を満たさないため、結果を返しません。');}
export function candidate(s:State,tripId:string,count:number){const t=tripRecords(s).find(t=>t.id===tripId);if(!t)fail(404,'便が見つかりません。');const location=(i:number)=>({type:'Point',coordinates:[stops[i].lon,stops[i].lat]});return {reservation_request:{candidate_id:`${t.id}:${count}`,service_id:serviceId,pickup:{type:'fixed_stop',stop_id:stops[0].id,location:location(0),datetime:t.start},dropoff:{type:'fixed_stop',stop_id:stops[1].id,location:location(1),datetime:t.end},passenger_count:[{passenger_type_id:passengerType,count}],accessibility_feature_count:[],vehicle_id:t.vehicleId},display:{pickup:{display_name:stops[0].name},dropoff:{display_name:stops[1].name},fare:{per_passenger_type:[{passenger_type_id:passengerType,subtotal:0}],total:0},vehicle:{id:t.vehicleId,name:'e-Palette',capacity:{seats:s.bookings.find(b=>b.id===t.id)!.seats,accessibility_features:[]}}}};}
export function standardReservation(s:State,p:Principal,id:string){const r=ownReservations(s,p).find(r=>r.ticketId===id);if(!r)fail(404,'予約が見つかりません。');const c=candidate(s,r.tripId,r.count);const status=({reserved:'confirmed',boarded:'in_transit',alighted:'completed',cancelled:'cancelled'} as Record<string,string>)[r.status];if(!status)fail(503,'予約状態を確認できません。');return {id:r.ticketId,passenger_id:p.subject,status,service_id:serviceId,pickup:{...c.reservation_request.pickup,...c.display.pickup},dropoff:{...c.reservation_request.dropoff,...c.display.dropoff},passenger_count:c.reservation_request.passenger_count,accessibility_feature_count:[],fare:c.display.fare,vehicle:c.display.vehicle,created_at:r.createdAt};}
export function candidateQuery(body:Json){validateContract('postReservationsCandidates','request',body);if(body.service_ids.length!==1||body.service_ids[0]!==serviceId||body.preferred_time.type!=='pickup'||body.pickup.type!=='fixed_stop'||body.dropoff.type!=='fixed_stop'||body.passenger_count.length!==1||body.passenger_count[0].passenger_type_id!==passengerType||body.accessibility_feature_count.length)fail(422,'検証対象は、指定乗降点・乗車時刻指定・一般区分・補助設備指定なしです。未設定の条件は予約できません。');return {date:inputDate(body.preferred_time.datetime).slice(0,10),fromStop:body.pickup.stop_id,toStop:body.dropoff.stop_id,count:body.passenger_count[0].count,wheelchairs:0};}
export function standardWrite(s:State,p:Principal,operation:string,body:Json,proposalId:string,reservationId?:string){validateContract(operation,'request',body);if(body.passenger_id!==p.subject)fail(403,'本人の予約のみ変更できます。');const a=getProposal(s,p,proposalId);let expected:unknown;
 if(operation==='postReservations'){if(a.action!=='prepare_ride_booking')fail(403,'乗車予約の承認が必要です。');expected={...candidate(s,String(a.args.tripId),Number(a.args.count)).reservation_request,passenger_id:p.subject};}
 else {if(a.action!=='prepare_ride_cancellation'||a.args.reservationId!==reservationId)fail(403,'対象予約の取消承認が必要です。');const r=standardReservation(s,p,String(reservationId));expected={passenger_id:r.passenger_id,status:'cancelled',service_id:r.service_id,pickup:r.pickup,dropoff:r.dropoff,passenger_count:r.passenger_count,accessibility_feature_count:r.accessibility_feature_count,...(body.vehicle?{vehicle:r.vehicle}:{})};}
 if(canonical(expected)!==canonical(body))fail(403,'乗降場所・日時・人数・車両が確認した内容と一致しません。');return a;
}
// Query decoding follows the pinned OpenAPI form/explode=false contract.
export function standardQuery(operation:string,query:URLSearchParams):Json {
 const definition=Object.values(demandDocument.paths).flatMap((path:any)=>Object.values(path)).find((op:any)=>op.operationId===operation) as Json|undefined;
 const params=(definition?.parameters??[]).filter((p:Json)=>p.in==='query');const result:Json={};
 for(const [name,value] of query){
  const spec=params.find((p:Json)=>p.name===name);if(!spec||Object.hasOwn(result,name))fail(400,'未定義、または重複した検索条件です。');
  const type=spec.schema.type;
  if(type==='integer'){if(!/^-?\d+$/.test(value)||!Number.isSafeInteger(Number(value)))fail(400,'整数の検索条件を確認してください。');result[name]=Number(value);}
  else if(type==='array'){const values=value.split(',');if(values.some(v=>v===''))fail(400,'空の検索条件は指定できません。');result[name]=values;}
  else result[name]=value;
 }
 validateContract(operation,'query',result);return result;
}
export function standardList(s:State,p:Principal,query:URLSearchParams){
 const q=standardQuery('getPassengersIdReservations',query),offset=q.offset??0,limit=q.limit??20;
 const from=q.pickup_date_from,to=q.pickup_date_to;if(from&&to&&from>to)fail(400,'日付範囲を確認してください。');
 const items=ownReservations(s,p).map(r=>standardReservation(s,p,r.ticketId)).filter(r=>(!q.status||q.status.includes(r.status))&&(!q.reservation_ids||q.reservation_ids.includes(r.id))&&(!from||inputDate(r.pickup.datetime).slice(0,10)>=from)&&(!to||inputDate(r.pickup.datetime).slice(0,10)<=to));
 return {reservations:items.slice(offset,offset+limit),total:items.length,offset,limit};
}
function activeStatus(item:Json,clock:string){return Date.parse(item.start_datetime)>Date.parse(clock)?'upcoming':item.end_datetime&&Date.parse(item.end_datetime)<=Date.parse(clock)?'ended':'active';}
function page(key:string,items:Json[],q:Json){const offset=q.offset??0,limit=q.limit??20;return {[key]:items.slice(offset,offset+limit),total:items.length,offset,limit};}
function services(s:State,q:Json){
 const items=serviceCatalogue(s).services.filter(service=>(!q.service_ids||q.service_ids.includes(service.id))&&(!q.name||service.name.includes(q.name))&&(!q.prefecture_code||service.cities.some(c=>c.prefecture_code===q.prefecture_code))&&(!q.municipality_code||service.cities.some(c=>c.municipalities.some(m=>m.code===q.municipality_code)))&&(q.status??['upcoming','active']).includes(activeStatus(service,s.clock)));
 return page('services',items.map(({operation_settings,reservable_areas,area_transitions,...summary})=>{void operation_settings;void reservable_areas;void area_transitions;return summary;}),q);
}
function metresBetween(a:number[],b:number[]){const rad=Math.PI/180,lat=(b[1]-a[1])*rad,lon=(b[0]-a[0])*rad;const h=Math.sin(lat/2)**2+Math.cos(a[1]*rad)*Math.cos(b[1]*rad)*Math.sin(lon/2)**2;return 6371008.8*2*Math.asin(Math.sqrt(Math.min(1,h)));}
function standardStops(s:State,q:Json){
 if(q.radius!==undefined&&!q.location)fail(400,'半径と一緒に経度・緯度を指定してください。');
 const point=q.location?.split(',').map(Number) as number[]|undefined;
 if(point&&(Math.abs(point[0])>180||Math.abs(point[1])>90))fail(400,'位置は経度,緯度の順で範囲内の値を指定してください。');
 const items=serviceCatalogue(s).stops.filter(stop=>(!q.stop_ids||q.stop_ids.includes(stop.id))&&(!q.service_ids||stop.service_ids.some(id=>q.service_ids.includes(id)))&&(!q.name||stop.name.includes(q.name))&&(q.status??['upcoming','active']).includes(activeStatus(stop,s.clock))&&(!point||metresBetween(point,stop.location.coordinates)<=(q.radius??500)));
 return page('stops',items,q);
}
function payment(s:State,p:Principal,id:string){
 const r=ownReservations(s,p).find(r=>r.ticketId===id);if(!r)fail(404,'予約が見つかりません。');
 if(r.fare!==0||r.status==='unavailable')fail(503,'実決済の状態は連携されていません。');
 return {id:r.ticketId,amount:0,payment_status:r.status==='cancelled'?'cancelled':'excluded',created_at:r.createdAt};
}
export function standardRead(s:State,p:Principal,path:string,query:URLSearchParams,origin:string):{operation:string;result:Json}|null {
 // All catalogue and passenger reads require the same delegated read scope as the normal API.
 permit(p,'get_service_catalog');requireDemo(s);
 let operation:string,result:Json;const parts=path.split('/');let id='';
 try{id=decodeURIComponent(parts[2]??'');}catch{fail(400,'識別子の形式を確認してください。');}
 if(path==='/terms'){operation='getTerms';const q=standardQuery(operation,query);result={terms:!q.category||q.category==='platform'?[{id:'demo-guide-v1',category:'platform',name:'検証版の利用案内（実運行なし）',url:new URL('/demo-guide',origin).toString(),agreement_required:false}]:[]};}
 else if(path==='/services'){operation='getServices';result=services(s,standardQuery(operation,query));}
 else if(/^\/services\/[^/]+$/.test(path)){operation='getServicesId';standardQuery(operation,query);const found=serviceCatalogue(s).services.find(service=>service.id===id);if(!found)fail(404,'サービスが見つかりません。');result=found;}
 else if(/^\/passengers\/[^/]+\/services$/.test(path)){operation='getPassengersIdServices';if(id!==p.subject)fail(404,'利用者が見つかりません。');result=services(s,standardQuery(operation,query));}
 else if(/^\/passengers\/[^/]+\/reservations$/.test(path)){operation='getPassengersIdReservations';if(id!==p.subject)fail(404,'予約が見つかりません。');result=standardList(s,p,query);}
 else if(path==='/stops'){operation='getStops';result=standardStops(s,standardQuery(operation,query));}
 else if(/^\/reservations\/[^/]+\/payment$/.test(path)){operation='getReservationsIdPayment';standardQuery(operation,query);result=payment(s,p,id);}
 else return null;
 validateContract(operation,'200',result);return {operation,result};
}
export const implementedOperations=['getTerms','getServices','getServicesId','getPassengersIdServices','getPassengersIdReservations','getStops','postReservationsCandidates','postReservations','putReservationsId','getReservationsIdPayment'];
