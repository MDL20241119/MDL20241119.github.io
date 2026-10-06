import {authenticate,action,errorResponse} from '@/lib/integration/service';
import {handleMcp} from '@/lib/integration/mcp';
import {tools} from '@/lib/integration/catalog';
import {permit} from '@/lib/integration/core';
export async function POST(request:Request){try{const p=await authenticate(request,'mcp');const visible=tools.filter(t=>{try{permit(p,t.name);return true;}catch{return false;}});return handleMcp(request,(n,a,k)=>action(p,n,a,k),visible);}catch(e){return errorResponse(e);}}
export async function GET(){return new Response(null,{status:405,headers:{Allow:'POST'}});}
export const DELETE=GET;
