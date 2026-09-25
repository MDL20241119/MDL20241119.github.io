import { ZodError } from 'zod';
import { getChatGPTUser } from '@/app/chatgpt-auth';
import { db,digest,execute,identity,readState,checkOrigin } from '../store';
import { Command,DomainError } from '../model';
import { Principal,State,Role,parseInput,permit,readAction,prepare,approve,commitApproved,getProposal,publicProposal,canonical,data,fail } from './core';
export const scopes=['read','proposals:write','approved:execute'];
export async function authenticate(request:Request,channel:Principal['channel']):Promise<Principal>{
 checkOrigin(request);
 const authorization=request.headers.get('authorization');
 if(authorization){const m=/^Bearer epo\.([a-f0-9-]{36})\.([a-f0-9]{64})$/.exec(authorization);if(!m)fail(401,'認証情報を確認してください。');const row=await db().prepare('SELECT * FROM integration_credentials WHERE id = ?').bind(m[1]).first<{owner:string;subject:string;role:Role;token_hash:string;expires_at:string;revoked:number}>();if(!row||row.revoked||row.expires_at<=new Date().toISOString()||await digest(m[2])!==row.token_hash)fail(401,'接続キーが無効、期限切れ、または解除済みです。');return {workspace:row.owner,subject:row.subject,role:row.role,channel,scopes:row.role==='driver'?['read']:scopes,delegationId:m[1]};}
 const user=await getChatGPTUser();if(user)return {workspace:user.userId,subject:user.userId,role:'manager',channel,scopes};
 // Preview-only identity is never enabled in the production Worker.
 if(process.env.NODE_ENV==='development'){const who=await identity();return {workspace:who.owner,subject:who.owner,role:'manager',channel,scopes};}
 fail(401,'サインインまたは許可された接続が必要です。');
}
export async function browserPrincipal():Promise<Principal>{const who=await identity();return {workspace:who.owner,subject:who.owner,role:'manager',channel:'web',scopes};}
export function validKey(key:string|null){if(!key||!/^[\w.-]{8,100}$/.test(key))fail(400,'8〜100文字の Idempotency-Key が必要です。');return key;}
export async function mutate(p:Principal,key:string,command:Command,reducer:(state:State)=>State,expected?:number){const s=await readState(p.workspace);return execute(p.workspace,p.subject,`integration:${p.subject}:${key}`,expected??s.version,command,reducer) as Promise<State>;}
export async function action(p:Principal,name:string,raw:unknown,key:string|null,now=new Date().toISOString()):Promise<unknown>{
 const args=parseInput(name,raw);permit(p,name);const s=await readState(p.workspace) as State;
 if(name.startsWith('prepare_')){const k=validKey(key);const proposalId='proposal-'+(await digest(`${p.workspace}:${p.subject}:${k}`)).slice(0,32);const after=await mutate(p,k,{type:name,args},before=>prepare(before,p,name,args,proposalId,now));return publicProposal(getProposal(after,p,proposalId));}
 if(name==='execute_approved'){const k=validKey(key);const after=await mutate(p,k,{type:name,args},before=>commitApproved(before,p,String(args.proposalId),now));return publicProposal(getProposal(after,p,String(args.proposalId)));}
 return readAction(s,p,name,args,now);
}
export async function confirm(request:Request,id:string,body:{csrf:string;expectedVersion:number;decision:'approve'|'reject'},key:string){
 checkOrigin(request);if(request.headers.has('authorization'))fail(403,'接続キーで本人の確認を代行できません。');const p=await browserPrincipal();
 const after=await mutate(p,validKey(key),{type:'human_confirmation',proposalId:id,decision:body.decision},s=>{const approved=approve(s,p,id,body.csrf,body.decision,new Date().toISOString());return body.decision==='approve'?commitApproved(approved,p,id,new Date().toISOString()):approved;},body.expectedVersion);return publicProposal(getProposal(after,p,id));
}
export async function jsonBody(request:Request){const raw=await request.text();if(raw.length>32000)fail(413,'入力が長すぎます。');try{return JSON.parse(raw);}catch{fail(400,'JSON形式を確認してください。');}}
export function errorResponse(e:unknown){if(e instanceof ZodError)e=new DomainError(400,'入力項目・型・必須条件を確認してください。');return Response.json({error:{code:e instanceof DomainError?`HTTP_${e.status}`:'UNAVAILABLE',message:e instanceof DomainError?e.message:'連携処理に失敗しました。成立したとは扱わず、再照会してください。'}},{status:e instanceof DomainError?e.status:503,headers:{'Cache-Control':'no-store'}});}
export function json(value:unknown,status=200){return Response.json(value,{status,headers:{'Cache-Control':'no-store','X-Data-Mode':'synthetic-demo'}});}
export async function mintCredential(p:Principal,role:Role){if(p.channel!=='web'||p.role!=='manager')fail(403,'管理者が画面から設定してください。');const token=Array.from(crypto.getRandomValues(new Uint8Array(32))).map(v=>v.toString(16).padStart(2,'0')).join('');const id=crypto.randomUUID();const expiresAt=new Date(Date.now()+86400000).toISOString();await db().batch([db().prepare('INSERT INTO integration_credentials (id,owner,subject,role,token_hash,expires_at,revoked) VALUES (?,?,?,?,?,?,0)').bind(id,p.workspace,p.subject,role,await digest(token),expiresAt),db().prepare('INSERT INTO audit (id,owner,actor,action,payload,time) VALUES (?,?,?,?,?,?)').bind(crypto.randomUUID(),p.workspace,p.subject,'create_integration_credential',JSON.stringify({id,role,expiresAt}),new Date().toISOString())]);return {id,token:`epo.${id}.${token}`,expiresAt,notice:'本人確認の公開ゲート設定は別途必要です。このキーだけで外部AIの接続完了にはなりません。'};}
export async function listCredentials(p:Principal){return (await db().prepare('SELECT id,role,expires_at,revoked FROM integration_credentials WHERE owner = ?').bind(p.workspace).all()).results;}
export async function revokeCredential(p:Principal,id:string){await db().batch([db().prepare('UPDATE integration_credentials SET revoked = 1 WHERE id = ? AND owner = ?').bind(id,p.workspace),db().prepare('INSERT INTO audit (id,owner,actor,action,payload,time) VALUES (?,?,?,?,?,?)').bind(crypto.randomUUID(),p.workspace,p.subject,'revoke_integration_credential',JSON.stringify({id}),new Date().toISOString())]);}
export const taskData=data;
export {canonical};
