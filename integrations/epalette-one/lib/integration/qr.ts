import * as validators from './contracts/validators.mjs';
import {State,fail,canonical} from './core';
import {applyCommand} from '../model';
export type QrLedger={rights:{commonId:string;ticketId:string;partner:string;used:boolean}[];events:{id:string;digest:string}[]};
export function acceptQrNotice(state:State,ledger:QrLedger,body:Record<string,unknown>,partner:string,now:string){
 const validate=(validators as Record<string,(v:unknown)=>boolean>).qr_maas_putNotify_authenticated_ticket_request;
 if(!validate(body))fail(400,'QR標準の入力形式を確認してください。');
 const fields=['request_id','exec_datetime_at','datetime_at','location','terminal_type','common_ticket_id','use_type'];if(fields.some(k=>typeof body[k]!=='string'||!body[k])||Object.keys(body).some(k=>!fields.includes(k)))fail(400,'通知に必要な項目を確認してください。');
 if(!Number.isFinite(Date.parse(String(body.exec_datetime_at)))||!Number.isFinite(Date.parse(String(body.datetime_at)))||Math.abs(Date.parse(now)-Date.parse(String(body.exec_datetime_at)))>300000)fail(400,'認証通知の時刻が古すぎます。');
 const right=ledger.rights.find(r=>r.commonId===body.common_ticket_id&&r.partner===partner);if(!right)fail(404,'利用権利が見つかりません。');
 const signature=canonical(body);const old=ledger.events.find(e=>e.id===body.request_id);if(old){if(old.digest!==signature)fail(409,'同じ通知IDで内容が異なります。');return {state,ledger,result:{result:true}};}
 if(body.use_type!=='entry')fail(501,'本版の検証対象は単回乗車の entry 通知です。他の権利状態は未設定です。');if(right.used)fail(409,'この利用権利は使用済みです。');
 const next=applyCommand(state,{type:'ticket_action',id:right.ticketId,action:'board'},'許可されたQR認証結果') as State;const updated=structuredClone(ledger);updated.rights.find(r=>r.commonId===right.commonId)!.used=true;updated.events.push({id:String(body.request_id),digest:signature});return {state:next,ledger:updated,result:{result:true}};
}
