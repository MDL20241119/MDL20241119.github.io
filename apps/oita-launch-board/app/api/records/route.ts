import {readBoundedJson} from '@/lib/request-body';
import {authorize,response,errorResponse,checkOrigin,readRecords,ApiError} from '@/lib/board-server';
import {mutationSchema,dependencyError} from '@/lib/validate';
import {TASK_GROUPS,groupKey} from '@/lib/hierarchy';
import {taskNumber,taskLabel} from '@/lib/model';
import {GRAPH_SIGNATURE_SQL,graphSignature} from '@/lib/graph-state';
async function mutate(request:Request,create:boolean){
 try{
  checkOrigin(request);const {user,db}=await authorize(true);
  const parsed=mutationSchema.safeParse(await readBoundedJson(request,65536));
  if(!parsed.success)throw new ApiError(400,parsed.error.issues[0]?.message||'入力形式を確認してください。');
  const {record,revision,archived}=parsed.data;const all=await readRecords(db),old=all.find(x=>x.id===record.id);
  if(create&&old)throw new ApiError(409,'同じIDが保存済みです。再読み込みして確認してください。');
  if(!create&&!old)throw new ApiError(404,'対象が見つかりません。');
  if(old&&old.kind!==record.kind)throw new ApiError(400,'項目の種類は変更できません。');
  if(!create&&old?.revision!==revision)throw new ApiError(409,'別の画面で更新されています。入力を残したまま、最新の内容と確認してください。');
  if(record.kind==='task'){const stable=old?taskNumber(old):Math.max(0,...all.filter(r=>r.kind==='task').map(r=>taskNumber(r)||0))+1;if(stable)record.taskNumber=stable;else delete record.taskNumber;if(create){const prefix=TASK_GROUPS.findIndex(g=>g.children.some(s=>s.id===groupKey(record as any)))+1||5;const n=Math.max(0,...all.filter(r=>r.kind==='task').map(r=>taskLabel(r)).filter(code=>code.startsWith(prefix+'-')).map(code=>Number(code.split('-')[1])||0))+1;record.taskCode=`${prefix}-${String(n).padStart(2,'0')}`;}else if(old?.taskCode)record.taskCode=old.taskCode;else delete record.taskCode;}
  const depError=dependencyError(record,all);if(depError)throw new ApiError(400,depError);
  const at=new Date().toISOString(),mutation=crypto.randomUUID(),actor=user.displayName;
  const graphChanged=create||JSON.stringify(record.dependencies)!==JSON.stringify(old?.dependencies);
  const guard=graphChanged?` AND ${GRAPH_SIGNATURE_SQL}=?`:'';
  const values=create?[record.id,record.kind,JSON.stringify(record),at,actor,mutation]:[JSON.stringify(record),archived===undefined?(old?.archived?1:0):(archived?1:0),at,actor,mutation,record.id,revision];
  if(graphChanged)values.push(graphSignature(all));
  const update=create?db.prepare(`INSERT INTO records (id,kind,payload,revision,archived,updated_at,updated_by,mutation_id) SELECT ?,?,?,1,0,?,?,? WHERE 1=1${guard}`).bind(...values):db.prepare(`UPDATE records SET payload=?,revision=revision+1,archived=?,updated_at=?,updated_by=?,mutation_id=? WHERE id=? AND revision=?${guard}`).bind(...values);
  const action=create?'追加':archived!==undefined?(archived?'アーカイブ':'復元'):record.status!==old?.status?`状態変更：${record.status}`:'更新';
  const log=db.prepare('INSERT INTO history (id,record_id,title,action,actor,at,revision,before_payload,after_payload) SELECT ?,id,?,?,?,?,revision,?,? FROM records WHERE id=? AND mutation_id=?').bind(mutation,record.title,action,actor,at,old?JSON.stringify(old):null,JSON.stringify({...record,archived:archived??old?.archived??false}),record.id,mutation);
  const result=await db.batch([update,log]);
  if(!result[0].meta.changes)throw new ApiError(409,'同時に更新がありました。入力を残したまま、最新の内容と確認してください。');
  return response({record:{...record,revision:create?1:revision+1,archived:archived??old?.archived??false,updatedAt:at,updatedBy:actor}},create?201:200);
 }catch(e){return errorResponse(e)}
}
export async function POST(request:Request){return mutate(request,true)}
export async function PATCH(request:Request){return mutate(request,false)}
