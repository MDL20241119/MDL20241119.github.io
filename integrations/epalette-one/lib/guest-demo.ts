import {newId} from './id.js';
import {seedState,applyCommand,Command,DomainError} from './model';
import {State,Principal,parseInput,readAction,prepare,publicProposal,getProposal,approve,commitApproved} from './integration/core';

// A separate, explicitly synthetic tab-local sandbox. Never send this state or
// its local approvals to D1, credentials, external services or production APIs.
export const DEMO_KEY='epalette-one:guest:v1';
export const DEMO_EVENT='epalette-demo-change';
export const demoPrincipal:Principal={workspace:'tab-local-demo',subject:'demo-visitor',role:'manager',channel:'web',scopes:['read','proposals:write','approved:execute']};
let cached:State|null=null;
let durable=true;
export function demoState():State {
 if(cached)return cached;
 try{const text=sessionStorage.getItem(DEMO_KEY);if(text){const envelope=JSON.parse(text);const s=envelope.state;if(envelope.format===1&&s.mode==='demo'&&Number.isInteger(s.version)&&Array.isArray(s.vehicles)&&s.vehicles.length===3&&Array.isArray(s.bookings)&&Array.isArray(s.tickets)&&Array.isArray(s.tasks)){cached=s;return s;}}}catch{durable=false;}
 cached=seedState();return cached;
}
export function saveDemo(s:State){cached=s;try{sessionStorage.setItem(DEMO_KEY,JSON.stringify({format:1,state:s}));durable=true;}catch{durable=false;}if(typeof window!=='undefined')window.dispatchEvent(new Event(DEMO_EVENT));return s;}
export function demoSavedInTab(){return durable;}
export function demoCommand(command:Command){return saveDemo(applyCommand(demoState(),command,'体験利用者（端末内）') as State);}
export function demoAction(name:string,raw:unknown){
 const args=parseInput(name,raw),s=demoState(),now=new Date().toISOString();
 if(name.startsWith('prepare_')){const id='demo-'+newId();const next=prepare(s,demoPrincipal,name,args,id,now);saveDemo(next);return {...publicProposal(getProposal(next,demoPrincipal,id)),approvalUrl:'/try/approvals/'+id};}
 // Public anonymous clients can inspect/prepare only; confirmation is a
 // separate local UI gesture, never an authenticated server approval.
 if(name==='execute_approved')throw new DomainError(403,'体験用の内容確認画面で確定してください。');
 return readAction(s,demoPrincipal,name,args,now);
}
export function confirmDemo(id:string,csrf:string,version:number,decision:'approve'|'reject'){
 const s=demoState(),existing=getProposal(s,demoPrincipal,id);
 // Exact local confirmation retries return the same outcome, never a second ticket.
 if(existing.csrf===csrf&&((existing.status==='executed'&&decision==='approve')||(existing.status==='rejected'&&decision==='reject')))return publicProposal(existing);
 if(s.version!==version)throw new DomainError(409,'予定が更新されました。内容をもう一度確認してください。');
 const now=new Date().toISOString(),next=approve(s,demoPrincipal,id,csrf,decision,now);
 const done=decision==='approve'?commitApproved(next,demoPrincipal,id,now):next;saveDemo(done);return publicProposal(getProposal(done,demoPrincipal,id));
}
export function demoCsv(){const cell=(v:unknown)=>{let text=String(v??'');if(/^[=+@-]/.test(text))text="'"+text;return '"'+text.replaceAll('"','""')+'"';};const rows=[['データ種別','車両','予定','開始','終了','状態'],...demoState().bookings.map(b=>['端末内の模擬データ',b.vehicleId,b.title,b.start,b.end,b.status])];return '\uFEFF'+rows.map(row=>row.map(cell).join(',')).join('\r\n');}
