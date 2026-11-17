import {confirm,jsonBody,json,errorResponse} from '@/lib/integration/service';
import {z} from 'zod';
export async function POST(request:Request,{params}:{params:Promise<{id:string}>}){try{const b=z.object({csrf:z.string(),expectedVersion:z.number().int(),decision:z.enum(['approve','reject'])}).strict().parse(await jsonBody(request));return json(await confirm(request,(await params).id,b,request.headers.get('Idempotency-Key')??''));}catch(e){return errorResponse(e);}}
