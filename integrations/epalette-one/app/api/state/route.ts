import { identity,readState,responseError } from '@/lib/store';
export async function GET(){try{const who=await identity();const state=await readState(who.owner);return Response.json({state,user:{name:who.actor,role:'管理者'},connection:{mode:'demo',label:'実車未接続'}},{headers:{'Cache-Control':'no-store'}});}catch(e){return responseError(e);}}
