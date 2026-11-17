import {authenticate,mutate,jsonBody,json,errorResponse,validKey} from '@/lib/integration/service';
import {readState} from '@/lib/store';
import {State,data,fail} from '@/lib/integration/core';
import {sendTask,taskView,cancelTask} from '@/lib/integration/a2a';
import {rpcError} from '@/lib/integration/mcp';
import {DomainError} from '@/lib/model';
export async function POST(request:Request){let id:unknown;try{const p=await authenticate(request,'a2a');const b=await jsonBody(request);id=b.id;if(b.jsonrpc!=='2.0'||!['string','number'].includes(typeof id))return rpcError(id,-32600,'Invalid JSON-RPC request');if(request.headers.get('A2A-Version')!=='1.0')return rpcError(id,-32009,'Version not supported',400,{supportedVersions:['1.0']});const now=new Date().toISOString();let result;
 if(b.method==='SendMessage'){const msgId=b.params?.message?.messageId;validKey(msgId);const s=await mutate(p,'a2a-'+msgId,{type:'a2a_send',params:b.params},before=>sendTask(before,p,b.params,now).state);const t=data(s).agentTasks.find(t=>t.subject===p.subject&&(t.messageId===msgId||t.messages?.some(m=>m.id===msgId)));if(!t)fail(409,'タスクの記録を確認してください。');result={task:taskView(s,p,t)};}
 else if(b.method==='GetTask'){const s=await readState(p.workspace) as State;const t=data(s).agentTasks.find(t=>t.id===b.params?.id&&t.subject===p.subject);if(!t)return rpcError(id,-32001,'Task not found',404);result=taskView(s,p,t);}
 else if(b.method==='CancelTask'){const tid=String(b.params?.id??'');const s=await mutate(p,validKey(request.headers.get('Idempotency-Key')),{type:'a2a_cancel',id:tid},before=>cancelTask(before,p,tid,now));result=taskView(s,p,data(s).agentTasks.find(t=>t.id===tid)!);}
 else return rpcError(id,-32601,'This protocol operation is not supported',404);
 return json({jsonrpc:'2.0',id,result});
 }catch(e){return rpcError(id,e instanceof DomainError&&e.status===404?-32001:-32602,e instanceof DomainError?e.message:'Service unavailable',e instanceof DomainError?e.status:503);}}
