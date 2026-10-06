import { env } from 'cloudflare:workers';
import { getChatGPTUser } from '@/app/chatgpt-auth';
import projectMetadata from '@/data/project.json';
import { readSharedSession } from '@/lib/shared-auth';
import { headers } from 'next/headers';
import type { RecordItem } from './model';
export class ApiError extends Error {constructor(public status:number,message:string){super(message)}}
export function rawDb(){if(!env.DB)throw new ApiError(503,'保存先に接続できません。時間を置いて再試行してください。');return env.DB}
export async function authorize(write=false){const db=rawDb();const user=await getChatGPTUser();if(user){const member=await db.prepare('SELECT role FROM members WHERE user_id=?').bind(user.userId).first<{role:string}>();if(member){if(write&&!['owner','editor'].includes(member.role))throw new ApiError(403,'閲覧専用です。');return {user,role:member.role,db,csrf:null,shared:false}}}const session=await readSharedSession(db);if(session){if(write){if(session.role!=='editor')throw new ApiError(403,'閲覧専用です。');const h=await headers();if(h.get('x-omc-csrf')!==session.csrf)throw new ApiError(403,'画面を読み直してから保存してください。')}return {user:{userId:'shared-session',displayName:'共有メンバー',email:'',fullName:null},role:session.role==='editor'?'shared_editor':'shared_viewer',db,csrf:session.csrf,shared:true}}throw new ApiError(user?403:401,'関係者用パスワードでログインしてください。')}
export async function authorizeOwner(){const access=await authorize();if(access.role!=='owner')throw new ApiError(403,'この設定は管理者のみ利用できます。');return access}
export function response(data:unknown,status=200){return Response.json(data,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}})}
export function errorResponse(error:unknown){if(error instanceof ApiError)return response({error:error.message},error.status);console.error('board failure',error);return response({error:'読み込み・保存に失敗しました。入力はそのまま再試行できます。'},503)}
export function checkOrigin(request:Request){const origin=request.headers.get('origin');if(!origin || origin!==new URL(request.url).origin)throw new ApiError(403,'別のサイトからの更新は受け付けていません。');if(request.headers.get('content-type')?.split(';')[0]!=='application/json')throw new ApiError(415,'JSON形式で送信してください。');if(request.headers.get('sec-fetch-site')==='cross-site')throw new ApiError(403,'更新元を確認できません。')}
export async function readRecords(db:D1Database){const rows=await db.prepare('SELECT * FROM records ORDER BY updated_at DESC,id ASC').all<any>();return rows.results.map(r=>({...JSON.parse(r.payload),revision:r.revision,archived:!!r.archived,updatedAt:r.updated_at,updatedBy:r.updated_by})) as RecordItem[]}
export const project=projectMetadata;
