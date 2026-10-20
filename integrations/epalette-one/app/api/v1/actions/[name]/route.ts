import { authenticate,action,jsonBody,json,errorResponse } from '@/lib/integration/service';
export async function POST(request:Request,{params}:{params:Promise<{name:string}>}){try{const p=await authenticate(request,'api');return json(await action(p,(await params).name,await jsonBody(request),request.headers.get('Idempotency-Key')));}catch(e){return errorResponse(e);}}
