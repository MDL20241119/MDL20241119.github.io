import {authenticate,action,jsonBody,json} from '@/lib/integration/service';
import {readState} from '@/lib/store';
import {State,fail} from '@/lib/integration/core';
import {DomainError} from '@/lib/model';
import {candidate,candidateQuery,standardWrite,standardReservation,standardRead,validateContract,demandDocument} from '@/lib/integration/commmmons';
type Json=Record<string,any>;
async function handle(request:Request,{params}:{params:Promise<{path:string[]}>}){try{const p=await authenticate(request,'commmmons');const path='/'+(await params).path.join('/');const s=await readState(p.workspace) as State;let result:Json;let op:string;let status=200;const read=request.method==='GET'?standardRead(s,p,path,new URL(request.url).searchParams,new URL(request.url).origin):null;
 if(read){op=read.operation;result=read.result;}
 else if(path==='/reservations/candidates'&&request.method==='POST'){op='postReservationsCandidates';const body=await jsonBody(request);const q=candidateQuery(body);const found=await action(p,'search_trips',q,null) as Json;result={candidates:found.trips.filter((t:Json)=>t.start>=new Date(body.preferred_time.datetime).toISOString()&&(!body.vehicle_id||t.vehicleId===body.vehicle_id)).map((t:Json)=>candidate(s,t.id,q.count))};}
 else if((path==='/reservations'&&request.method==='POST')||(/^\/reservations\/[^/]+$/.test(path)&&request.method==='PUT')){op=request.method==='POST'?'postReservations':'putReservationsId';const body=await jsonBody(request);const proposalId=request.headers.get('X-Proposal-ID');if(!proposalId)fail(403,'X-Proposal-ID に本人が確認した内容を指定してください。');standardWrite(s,p,op,body,proposalId,path.split('/')[2]);const done=await action(p,'execute_approved',{proposalId},request.headers.get('Idempotency-Key')) as Json;const after=await readState(p.workspace) as State;result=standardReservation(after,p,String(done.result.reservationId));status=request.method==='POST'?201:200;}
 else {const exists=Object.keys(demandDocument.paths).some(template=>new RegExp('^'+template.replaceAll('{id}','[^/]+')+'$').test(path));fail(exists?501:404,exists?'この標準操作は本版では未実装です。適合表を確認してください。':'未定義の標準操作です。');}
 validateContract(op,String(status),result);return json(result,status);
 }catch(e){const status=e instanceof DomainError?e.status:503;return Response.json({type:'about:blank',title:status>=500?'連携処理を完了できません':'要求を処理できません',status,detail:e instanceof DomainError?e.message:'予約成立とは扱わず、再照会してください。'},{status,headers:{'Cache-Control':'no-store'}});}}
export const GET=handle;export const POST=handle;export const PUT=handle;export const DELETE=handle;
