import {newId} from '../id.js';
import { z } from 'zod';
import {stops,serviceId,passengerType,transportBookings,serviceCatalogue,validCalendarDate} from './network';
export {stops,serviceId,passengerType} from './network';
import { AppState, Command, DomainError, applyCommand, estimate, nextBooking, readiness, inputDate } from '../model';

export type Role = 'passenger'|'driver'|'manager';
export type Principal = {workspace:string;subject:string;role:Role;channel:'web'|'api'|'mcp'|'a2a'|'commmmons';scopes:string[];delegationId?:string};
export type Proposal = {id:string;subject:string;role:Role;channel:string;action:string;args:Record<string,unknown>;command:Command;summary:Record<string,unknown>;createdAt:string;expiresAt:string;baseVersion:number;status:'pending'|'approved'|'executed'|'rejected';approvedBy?:string;approvedAt?:string;executedAt?:string;approvedVersion?:number;result?:unknown;csrf:string};
export type PassengerRecord = {ticketId:string;subject:string;tripId:string;fromStop:string;toStop:string;count:number;fare:number;createdAt:string};
export type AgentTask = {id:string;subject:string;contextId:string;messageId:string;request:string;messages?:{id:string;request:string}[];state:'completed'|'input-required'|'canceled'|'failed';proposalId?:string;result:unknown;createdAt:string;updatedAt?:string};
export type IntegrationData = {proposals:Proposal[];reservations:PassengerRecord[];agentTasks:AgentTask[]};
export type State = AppState & {integration?:IntegrationData};
export const data=(s:State):IntegrationData=>s.integration??{proposals:[],reservations:[],agentTasks:[]};
export function fail(status:number,message:string):never {throw new DomainError(status,message);}
export function canonical(value:unknown):string {if(Array.isArray(value))return '['+value.map(canonical).join(',')+']';if(value&&typeof value==='object')return '{'+Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>JSON.stringify(k)+':'+canonical(v)).join(',')+'}';return JSON.stringify(value);}
const id=z.string().min(1).max(100);
const strict=(shape:z.ZodRawShape)=>z.object(shape).strict();
export const inputs={
 get_service_catalog:strict({}),
 search_trips:strict({date:z.string().regex(/^\d{4}-\d{2}-\d{2}$/),fromStop:z.enum(['oita-station','community-hub']),toStop:z.enum(['oita-station','community-hub']),count:z.number().int().min(1).max(8),wheelchairs:z.number().int().min(0).max(1).default(0)}),
 get_my_reservations:strict({}),
 get_vehicle_status:strict({vehicleId:id.optional()}),
 get_charge_plan:strict({vehicleId:id}),
 get_today_actions:strict({}),
 prepare_ride_booking:strict({tripId:id,count:z.number().int().min(1).max(8),fromStop:z.literal('oita-station'),toStop:z.literal('community-hub')}),
 prepare_ride_cancellation:strict({reservationId:id}),
 prepare_charge_request:strict({vehicleId:id,bookingId:id,stationId:id,owner:id}),
 prepare_vehicle_booking:strict({vehicleId:id,driverId:id,title:z.string().min(1).max(100),purpose:z.enum(['shuttle','ondemand','shop','charge']),start:z.string().datetime({offset:true}),end:z.string().datetime({offset:true}),route:z.string().min(1).max(200),distance:z.number().min(0).max(500),targetSoc:z.number().min(0).max(100)}),
 prepare_on_demand_request:strict({fromStop:z.literal('oita-station'),toStop:z.literal('community-hub'),start:z.string().datetime({offset:true}),count:z.number().int().min(1).max(8)}),
 get_proposal:strict({proposalId:id}),
 execute_approved:strict({proposalId:id}),
} as const;
export type ToolName=keyof typeof inputs;
export function parseInput(name:string,args:unknown):Record<string,unknown>{const schema=inputs[name as ToolName];if(!schema)fail(404,'この機能は公開されていません。');const result=schema.safeParse(args);if(!result.success)fail(400,'必要な入力、型、日時を確認してください。未定義の項目は指定できません。');if(name==='search_trips'&&!validCalendarDate(String((result.data as Record<string,unknown>).date)))fail(400,'実在する利用日を指定してください。');return result.data;}
export function permit(p:Principal,name:string){const management=['get_vehicle_status','get_charge_plan','get_today_actions','prepare_charge_request','prepare_vehicle_booking'];if(management.includes(name)&&p.role!=='manager')fail(403,'管理者の権限が必要です。');if(name.startsWith('prepare_')&&p.role==='driver')fail(403,'運転者の委任には予約変更の権限がありません。');const scope=name.startsWith('prepare_')?'proposals:write':name==='execute_approved'?'approved:execute':'read';if(!p.scopes.includes(scope))fail(403,'この接続に必要な権限がありません。');}
export function tripRecords(s:State){return transportBookings(s).map(b=>{const used=s.tickets.filter(t=>t.bookingId===b.id&&t.status!=='cancelled'&&t.from===0&&t.to>=1).reduce((n,t)=>n+t.count,0);return {id:b.id,name:b.title,start:b.start,end:b.end,status:b.status,vehicleId:b.vehicleId,fromStop:stops[0].id,toStop:stops[1].id,available:Math.max(0,b.seats-used),fare:0,currency:'JPY',quality:'synthetic',serviceId,preparation:readiness(s,s.vehicles.find(v=>v.id===b.vehicleId)!,b)};});}
export function ownReservations(s:State,p:Principal){return data(s).reservations.filter(r=>r.subject===p.subject).map(r=>({...r,status:s.tickets.find(t=>t.id===r.ticketId)?.status??'unavailable',trip:tripRecords(s).find(t=>t.id===r.tripId)}));}
export function getProposal(s:State,p:Principal,id:string){const a=data(s).proposals.find(a=>a.id===id&&a.subject===p.subject);if(!a)fail(404,'確認内容が見つかりません。');return a;}
export function publicProposal(a:Proposal){const {csrf,command,...rest}=a;void csrf;void command;return {...rest,approvalUrl:`/approvals/${encodeURIComponent(a.id)}`,notice:'本人または権限を持つ担当者が確認するまで、予約・依頼は確定しません。'};}
export function readAction(s:State,p:Principal,name:string,args:Record<string,unknown>,now:string):unknown{
 permit(p,name);
 if(name==='get_service_catalog')return serviceCatalogue(s);
 if(name==='search_trips'){
  if(args.wheelchairs!==0)fail(422,'車いす設備は未設定です。対応可能として予約を受け付けられません。');
  return {mode:'demo',asOf:s.clock,serviceId,stops,notice:'合成データです。実際の送迎は予約されません。',trips:tripRecords(s).filter(t=>inputDate(t.start).slice(0,10)===args.date&&t.fromStop===args.fromStop&&t.toStop===args.toStop&&t.available>=Number(args.count)&&t.status==='confirmed'&&t.start>=s.clock&&!['blocked','unknown'].includes(t.preparation.type))};
 }
 if(name==='get_my_reservations')return {mode:'demo',reservations:ownReservations(s,p)};
 if(name==='get_vehicle_status')return {mode:s.mode,asOf:s.clock,vehicles:s.vehicles.filter(v=>!args.vehicleId||v.id===args.vehicleId).map(v=>({id:v.id,soc:v.soc,charging:v.charging,location:v.location,readiness:readiness(s,v,nextBooking(s,v.id))}))};
 if(name==='get_charge_plan'){const v=s.vehicles.find(v=>v.id===args.vehicleId);if(!v)fail(404,'車両が見つかりません。');const b=nextBooking(s,v.id);if(!b)return {mode:s.mode,calculable:false,reason:'次の利用予定が登録されていません。'};return {mode:s.mode,asOf:s.clock,vehicleId:v.id,bookingId:b.id,nextUse:b.start,soc:v.soc,usableKwh:v.usableKwh,model:v.profileVersion,quality:'estimated_from_synthetic_inputs',plans:s.stations.map(st=>({mode:st.type,...estimate(s,v,b,st.id)}))};}
 if(name==='get_today_actions')return {mode:s.mode,asOf:s.clock,vehicles:s.vehicles.map(v=>({id:v.id,...readiness(s,v,nextBooking(s,v.id))})),tasks:s.tasks.filter(t=>t.status!=='completed')};
 if(name==='get_proposal')return {...publicProposal(getProposal(s,p,String(args.proposalId))),expired:getProposal(s,p,String(args.proposalId)).expiresAt<=now};
 fail(404,'読み取り機能が見つかりません。');
}
export function prepare(s:State,p:Principal,name:string,args:Record<string,unknown>,proposalId:string,now:string):State{
 permit(p,name);let command:Command;let summary:Record<string,unknown>;
 if(name==='prepare_ride_booking'){
  const trip=tripRecords(s).find(t=>t.id===args.tripId);if(!trip||trip.status!=='confirmed'||trip.start<s.clock)fail(422,'受付可能な便が見つかりません。');if(args.count as number>trip.available)fail(409,'空席が不足しています。');if(['blocked','unknown'].includes(trip.preparation.type))fail(422,'車両の準備状態を確認できません。');
  command={type:'create_ticket',bookingId:trip.id,count:args.count,from:0,to:1};summary={title:'乗車予約',tripId:trip.id,from:'大分駅前',to:'地域拠点',start:trip.start,end:trip.end,count:args.count,amount:trip.fare,currency:'JPY',payment:'検証用の無料運行。課金されません。',preparation:trip.preparation.label};
 } else if(name==='prepare_ride_cancellation'){
  const r=ownReservations(s,p).find(r=>r.ticketId===args.reservationId);if(!r)fail(404,'自分の予約が見つかりません。');if(!r.trip||r.trip.start<s.clock)fail(422,'乗車時刻を過ぎた予約は担当者へ連絡してください。');command={type:'ticket_action',id:r.ticketId,action:'cancel'};summary={title:'乗車予約の取消',reservationId:r.ticketId,from:stops.find(x=>x.id===r.fromStop)?.name,to:stops.find(x=>x.id===r.toStop)?.name,start:r.trip.start,count:r.count,amount:0,currency:'JPY',payment:'検証用の無料運行。取消による課金はありません。'};
 } else if(name==='prepare_charge_request'){command={type:'assign_charge',...args};summary={title:'充電の担当者への依頼',...args,notice:'実機の充電開始・充電器の外部予約は行いません。'};
 } else if(name==='prepare_vehicle_booking'){command={type:'create_booking',...args};summary={title:'車両の利用予約',...args};
 } else if(name==='prepare_on_demand_request'){command={type:'create_ride',from:stops[0].name,to:stops[1].name,start:args.start,count:args.count};summary={title:'オンデマンドの乗車依頼',...args,notice:'担当者の配車確定まで未割当です。送迎の成立ではありません。'};
 } else fail(404,'変更案を作成できません。');
 applyCommand(s,command,p.subject); // Validate against exactly the same rules as the human UI; discard this preview.
 const next=structuredClone(s);next.integration=data(next);const a:Proposal={id:proposalId,subject:p.subject,role:p.role,channel:p.channel,action:name,args,command,summary,createdAt:now,expiresAt:new Date(Date.parse(now)+10*60000).toISOString(),baseVersion:s.version+1,status:'pending',csrf:newId()};next.integration.proposals.push(a);return event(next,p,'内容確認を依頼',now);
}
function event(s:State,p:Principal,label:string,now:string){s.version++;s.events.unshift({id:newId(),time:now,label,actor:p.subject});s.events=s.events.slice(0,100);return s;}
export function approve(s:State,p:Principal,proposalId:string,csrf:string,decision:'approve'|'reject',now:string):State{
 if(p.channel!=='web')fail(403,'本人が確認画面で承認してください。');const a=getProposal(s,p,proposalId);
 if(a.status!=='pending'||a.csrf!==csrf||a.expiresAt<=now)fail(403,'確認内容が無効、または期限切れです。新しい内容を確認してください。');
 if(a.baseVersion!==s.version)fail(409,'予定・空席などが更新されました。新しい内容を確認してください。');
 if(a.role==='manager'&&p.role!=='manager')fail(403,'管理者の確認が必要です。');
 const next=structuredClone(s);const target=getProposal(next,p,proposalId);target.status=decision==='approve'?'approved':'rejected';target.approvedBy=p.subject;target.approvedAt=now;target.approvedVersion=s.version+1;return event(next,p,decision==='approve'?'内容を確認して承認':'内容を確認して見送り',now);
}
export function commitApproved(s:State,p:Principal,proposalId:string,now:string):State{
 permit(p,'execute_approved');const a=getProposal(s,p,proposalId);
 if(a.status==='executed')return s;
 if(a.status!=='approved'||!a.approvedBy||a.expiresAt<=now)fail(403,'有効な本人承認が必要です。');
 if(a.approvedVersion!==s.version)fail(409,'承認後に内容が更新されました。再確認してください。');
 if(p.role!==a.role&&!(p.channel==='web'&&p.role==='manager'))fail(403,'承認時の役割と一致しません。');
 let next=applyCommand(s,a.command,`${a.approvedBy}（${p.channel}・承認済み）`) as State;next.integration=data(next);const target=getProposal(next,p,proposalId);target.status='executed';target.executedAt=now;
 if(a.action==='prepare_ride_booking'){const t=next.tickets[next.tickets.length-1];const record:PassengerRecord={ticketId:t.id,subject:p.subject,tripId:t.bookingId,fromStop:String(a.args.fromStop),toStop:String(a.args.toStop),count:t.count,fare:Number(a.summary.amount),createdAt:now};next.integration.reservations.push(record);target.result={reservationId:t.id,status:t.status};}
 else if(a.action==='prepare_ride_cancellation')target.result={reservationId:a.args.reservationId,status:'cancelled'};
 else if(a.action==='prepare_on_demand_request')target.result={requestId:next.rides.at(-1)!.id,status:'waiting'};
 else target.result={saved:true,version:next.version};return next;
}
