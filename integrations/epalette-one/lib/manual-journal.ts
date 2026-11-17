import type {AppState,Command} from './model';
export type SaveStatus='local'|'pending'|'syncing'|'synced'|'conflict'|'rejected';
export type JournalEntry={id:string;scope:string;createdAt:string;command:Command;expectedVersion:number;status:SaveStatus;message?:string;acceptedVersion?:number;photo?:Blob;photoExpiresAt?:string};
export const PHOTO_DAYS=7;
export const workspaceScope=(user:{id:string;workspace:string})=>'user:'+user.id+':'+user.workspace;
export function recoverEntry(e:JournalEntry,now=Date.now()):JournalEntry{const next={...e,status:e.status==='syncing'?'pending' as const:e.status};if(e.photoExpiresAt&&Date.parse(e.photoExpiresAt)<=now){delete next.photo;delete next.photoExpiresAt;}return next;}
export function summaryStatus(status:SaveStatus){return ({local:'この端末だけ',pending:'同期待ち',syncing:'同期中',synced:'サーバー保存済み',conflict:'競合・確認が必要',rejected:'未保存・入力を確認'})[status];}
export async function syncEntry(entry:JournalEntry,send:(key:string,version:number,command:Command)=>Promise<Response>):Promise<{entry:JournalEntry;state?:AppState}>{
 if(!['pending','syncing'].includes(entry.status))return {entry};
 try{const response=await send(entry.id,entry.expectedVersion,entry.command);const body=await response.json() as {state?:AppState;error?:string};
 if(response.ok&&body.state&&Number.isInteger(body.state.version))return {entry:{...entry,status:'synced',acceptedVersion:body.state.version,message:undefined},state:body.state};
 const status:SaveStatus=response.ok?'pending':response.status===409?'conflict':response.status>=500||[401,403,408,429].includes(response.status)?'pending':'rejected';
 return {entry:{...entry,status,message:body.error??'保存結果を確認できません。記録は端末に残っています。'}};
 }catch{return {entry:{...entry,status:'pending',message:'通信を確認できません。端末の記録を残して再試行します。'}};}
}
const DB_NAME='epalette-manual-review-v1';
let opened:Promise<IDBDatabase>|null=null;
function database(){if(opened)return opened;opened=new Promise<IDBDatabase>((resolve,reject)=>{const request=indexedDB.open(DB_NAME,2);request.onupgradeneeded=()=>{const db=request.result;if(!db.objectStoreNames.contains('records')){const records=db.createObjectStore('records',{keyPath:'id'});records.createIndex('scope','scope');}if(!db.objectStoreNames.contains('states'))db.createObjectStore('states');};request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(new Error('端末へ保存できません。ブラウザーの保存設定と空き容量を確認してください。'));});return opened;}
export async function journalPut(entry:JournalEntry,state?:AppState){const db=await database();await new Promise<void>((resolve,reject)=>{const t=db.transaction(['records','states'],'readwrite');t.objectStore('records').put(entry);if(state)t.objectStore('states').put(state,'demo');t.oncomplete=()=>resolve();t.onerror=()=>reject(new Error('端末への保存に失敗しました。入力は閉じずに残してください。'));t.onabort=()=>reject(new Error('端末への保存が中断しました。'));});}
export async function journalList(scope:string){const db=await database();const rows=await new Promise<JournalEntry[]>((resolve,reject)=>{const t=db.transaction('records','readonly'),r=t.objectStore('records').index('scope').getAll(scope);r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});const recovered=rows.map(e=>recoverEntry(e));for(let i=0;i<rows.length;i++)if(rows[i].status!==recovered[i].status||rows[i].photo!==recovered[i].photo)await journalPut(recovered[i]);return recovered.sort((a,b)=>a.createdAt.localeCompare(b.createdAt));}
export async function stripPhotoMetadata(file:File):Promise<Blob>{
 if(!['image/jpeg','image/png','image/webp'].includes(file.type)||file.size>8*1024*1024)throw new Error('写真は JPEG・PNG・WebP、8 MB以内で選んでください。');
 const bitmap=await createImageBitmap(file);try{if(bitmap.width*bitmap.height>40000000)throw new Error('写真が大きすぎます。小さい画像を選んでください。');const scale=Math.min(1,1280/Math.max(bitmap.width,bitmap.height));const canvas=document.createElement('canvas');canvas.width=Math.round(bitmap.width*scale);canvas.height=Math.round(bitmap.height*scale);canvas.getContext('2d')!.drawImage(bitmap,0,0,canvas.width,canvas.height);return await new Promise<Blob>((resolve,reject)=>canvas.toBlob(b=>b?resolve(b):reject(new Error('写真を処理できませんでした。')),'image/jpeg',.8));}finally{bitmap.close();}
}

export async function guestSnapshot():Promise<AppState|undefined>{const db=await database();return new Promise((resolve,reject)=>{const r=db.transaction('states').objectStore('states').get('demo');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});}
