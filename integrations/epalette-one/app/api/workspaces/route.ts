import {getChatGPTUser} from '@/app/chatgpt-auth';
import {db,checkOrigin,digest,membership,responseError} from '@/lib/store';
import {DomainError} from '@/lib/model';
import {newOperationalState} from '@/lib/operations';
import {ROLE_LABELS,TeamRole} from '@/lib/permissions';
const json=(x:unknown,workspace?:string)=>Response.json(x,{headers:{'Cache-Control':'no-store',...(workspace?{'Set-Cookie':`epalette-workspace=${encodeURIComponent(workspace)}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=2592000`}:{})}});
async function user(){const u=await getChatGPTUser();if(!u)throw new DomainError(401,'サインインしてください。');return u;}
const audit=(owner:string,actor:string,action:string,payload:unknown)=>db().prepare('INSERT INTO audit (id,owner,actor,action,payload,time) VALUES (?,?,?,?,?,?)').bind(crypto.randomUUID(),owner,actor,action,JSON.stringify(payload),new Date().toISOString());
export async function GET(request:Request){try{const u=await user();const teams=(await db().prepare('SELECT o.id,o.name,m.role FROM organizations o JOIN memberships m ON o.id = m.workspace WHERE m.subject = ? AND m.active = 1').bind(u.userId).all()).results;const selected=new URL(request.url).searchParams.get('workspace');let members:unknown[]=[];if(selected){await membership(selected,u.userId);members=(await db().prepare('SELECT subject,display_name,role,active FROM memberships WHERE workspace = ?').bind(selected).all()).results;}return json({personal:{id:u.userId,name:'自分の保存した体験',role:'manager'},teams,members});}catch(e){return responseError(e)}}
export async function POST(request:Request){try{checkOrigin(request);const u=await user();if(request.headers.has('authorization'))throw new DomainError(403,'本人の画面から操作してください。');const raw=await request.text();if(raw.length>4000)throw new DomainError(413,'入力が長すぎます。');const c=JSON.parse(raw);const now=new Date().toISOString();
 if(c.action==='create'){
  if(typeof c.name!=='string'||!c.name.trim()||c.name.length>80)throw new DomainError(422,'チーム名を入力してください。');
  const key=request.headers.get('Idempotency-Key');if(!key||!/^[a-f0-9-]{36}$/.test(key))throw new DomainError(400,'操作キーが必要です。');const id='org:'+(await digest(u.userId+':'+key)).slice(0,32);const s=newOperationalState(c.name,u.userId,u.displayName,Number(c.count));
  await db().batch([db().prepare('INSERT OR IGNORE INTO organizations (id,name,created_by,created_at) VALUES (?,?,?,?)').bind(id,c.name.trim(),u.userId,now),db().prepare('INSERT OR IGNORE INTO workspaces (owner,state,version) VALUES (?,?,?)').bind(id,JSON.stringify(s),s.version),db().prepare('INSERT OR IGNORE INTO memberships (workspace,subject,display_name,role,active) VALUES (?,?,?,?,1)').bind(id,u.userId,u.displayName,'manager'),audit(id,u.userId,'create_workspace',{name:c.name})]);return json({workspace:id},id);
 }
 if(c.action==='select'){await membership(String(c.workspace),u.userId);return json({workspace:c.workspace},c.workspace);}
 if(c.action==='invite'){
  const p=await membership(String(c.workspace),u.userId);if(p.role!=='manager'||!String(c.workspace).startsWith('org:'))throw new DomainError(403,'チーム管理者が招待を作成してください。');
  if(!Object.keys(ROLE_LABELS).includes(c.role))throw new DomainError(422,'役割を選んでください。');const token=Array.from(crypto.getRandomValues(new Uint8Array(24))).map(x=>x.toString(16).padStart(2,'0')).join('');const id=crypto.randomUUID();const expiresAt=new Date(Date.now()+86400000).toISOString();await db().batch([db().prepare('INSERT INTO invitations (id,workspace,token_hash,role,expires_at,created_by,revoked) VALUES (?,?,?,?,?,?,0)').bind(id,c.workspace,await digest(token),c.role,expiresAt,u.userId),audit(c.workspace,u.userId,'create_invitation',{id,role:c.role,expiresAt})]);return json({code:id+'.'+token,expiresAt,role:c.role});
 }
 if(c.action==='join'){
  if(typeof c.code!=='string'||!/^[a-f0-9-]{36}\.[a-f0-9]{48}$/.test(c.code))throw new DomainError(422,'招待コードを確認してください。');const [id,token]=c.code.split('.');const invite=await db().prepare('SELECT * FROM invitations WHERE id = ?').bind(id).first<{workspace:string;token_hash:string;role:TeamRole;expires_at:string;accepted_by:string|null;revoked:number}>();if(!invite||invite.revoked||invite.expires_at<=now||await digest(token)!==invite.token_hash||invite.accepted_by&&invite.accepted_by!==u.userId)throw new DomainError(403,'招待は無効・期限切れ・使用済みです。');
  await db().batch([db().prepare('INSERT OR IGNORE INTO memberships (workspace,subject,display_name,role,active) SELECT workspace,?,?,role,1 FROM invitations WHERE id = ? AND revoked = 0 AND expires_at > ? AND (accepted_by IS NULL OR accepted_by = ?)').bind(u.userId,u.displayName,id,now,u.userId),db().prepare('UPDATE invitations SET accepted_by = ? WHERE id = ? AND accepted_by IS NULL AND EXISTS (SELECT 1 FROM memberships WHERE workspace = ? AND subject = ? AND active = 1)').bind(u.userId,id,invite.workspace,u.userId),audit(invite.workspace,u.userId,'accept_invitation',{id})]);await membership(invite.workspace,u.userId);return json({workspace:invite.workspace},invite.workspace);
 }
 if(c.action==='revoke'){
  const p=await membership(String(c.workspace),u.userId);if(p.role!=='manager'||c.subject===u.userId)throw new DomainError(403,'他のメンバーの利用停止は管理者が行ってください。');await db().batch([db().prepare('UPDATE memberships SET active = 0 WHERE workspace = ? AND subject = ?').bind(c.workspace,c.subject),db().prepare('UPDATE integration_credentials SET revoked = 1 WHERE owner = ? AND subject = ?').bind(c.workspace,c.subject),audit(c.workspace,u.userId,'revoke_member',{subject:c.subject})]);return json({ok:true});
 }
 throw new DomainError(422,'未対応の操作です。');
 }catch(e){return responseError(e)}}
