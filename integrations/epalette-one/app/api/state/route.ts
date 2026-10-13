import { identity,readState,responseError } from '@/lib/store';
import {ROLE_LABELS} from '@/lib/permissions';
export async function GET(){try{const who=await identity();const state=await readState(who.owner);return Response.json({state,user:{id:who.subject,name:who.name,role:who.role,roleLabel:ROLE_LABELS[who.role],workspace:who.owner},connection:{mode:state.mode,label:state.mode==='demo'?'保存した体験データ':'車両APIなし・現場手入力'}},{headers:{'Cache-Control':'no-store'}});}catch(e){return responseError(e);}}
