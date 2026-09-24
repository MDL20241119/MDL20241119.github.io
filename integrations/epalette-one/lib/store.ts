import { env } from 'cloudflare:workers';
import { getChatGPTUser } from '@/app/chatgpt-auth';
import { AppState, seedState, applyCommand, Command, DomainError } from './model';
export function db():D1Database {const binding=(env as unknown as {DB?:D1Database}).DB;if(!binding)throw new DomainError(503,'保存先に接続できません。時間をおいて再度お試しください。');return binding;}
export async function identity(){const user=await getChatGPTUser();if(user)return {owner:user.userId,actor:user.displayName};if(process.env.NODE_ENV==='development')return {owner:'local-preview',actor:'検証管理者'};throw new DomainError(401,'サインインが必要です。');}
export async function readState(owner:string){let row=await db().prepare('SELECT state FROM workspaces WHERE owner = ?').bind(owner).first<{state:string}>();if(!row){const s=seedState();await db().prepare('INSERT OR IGNORE INTO workspaces (owner,state,version) VALUES (?,?,?)').bind(owner,JSON.stringify(s),s.version).run();row=await db().prepare('SELECT state FROM workspaces WHERE owner = ?').bind(owner).first<{state:string}>();}return JSON.parse(row!.state) as AppState;}
export async function digest(value:string){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value)))).map(x=>x.toString(16).padStart(2,'0')).join('');}
export async function execute(owner:string,actor:string,key:string,expected:number,command:Command){
 const hash=await digest(JSON.stringify(command));const prev=await db().prepare('SELECT digest FROM receipts WHERE owner = ? AND key = ?').bind(owner,key).first<{digest:string}>();if(prev){if(prev.digest!==hash)throw new DomainError(409,'同じ操作キーで異なる内容は保存できません。');return readState(owner);}
 const before=await readState(owner);if(before.version!==expected)throw new DomainError(409,'ほかの操作で更新されました。最新の内容を確認して、もう一度操作してください。');
 const after=applyCommand(before,command,actor);const commandId=crypto.randomUUID();const at=new Date().toISOString();
 try {const result=await db().batch([
  db().prepare('INSERT INTO receipts (owner,key,command_id,version,digest,created_at) SELECT ?,?,?,?,?,? WHERE EXISTS (SELECT 1 FROM workspaces WHERE owner = ? AND version = ?)').bind(owner,key,commandId,after.version,hash,at,owner,before.version),
  db().prepare('UPDATE workspaces SET state = ?, version = ? WHERE owner = ? AND version = ? AND EXISTS (SELECT 1 FROM receipts WHERE owner = ? AND key = ? AND command_id = ?)').bind(JSON.stringify(after),after.version,owner,before.version,owner,key,commandId),
  db().prepare('INSERT INTO audit (id,owner,actor,action,payload,time) SELECT ?,?,?,?,?,? WHERE EXISTS (SELECT 1 FROM receipts WHERE owner = ? AND key = ? AND command_id = ?)').bind(commandId,owner,actor,command.type,JSON.stringify(command),at,owner,key,commandId),
 ]);if(result[1].meta.changes!==1)throw new DomainError(409,'同時に別の更新がありました。最新の内容を確認してください。');}
 catch(error){const receipt=await db().prepare('SELECT digest FROM receipts WHERE owner = ? AND key = ?').bind(owner,key).first<{digest:string}>();if(receipt?.digest===hash)return readState(owner);throw error;}
 return after;
}
export function responseError(e:unknown){if(e instanceof DomainError)return Response.json({error:e.message},{status:e.status});console.error('application failure',e);return Response.json({error:'保存・読込に失敗しました。入力を残したまま、再度お試しください。'},{status:503});}
export function checkOrigin(request:Request){const origin=request.headers.get('origin');if(origin&&origin!==new URL(request.url).origin)throw new DomainError(403,'許可されていない送信元です。');}
