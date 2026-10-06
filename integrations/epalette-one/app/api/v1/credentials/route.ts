import {browserPrincipal,listCredentials,mintCredential,revokeCredential,jsonBody,json,errorResponse} from '@/lib/integration/service';
import {checkOrigin} from '@/lib/store';
import {z} from 'zod';
export async function GET(){try{return json(await listCredentials(await browserPrincipal()));}catch(e){return errorResponse(e);}}
export async function POST(request:Request){try{checkOrigin(request);if(request.headers.has('authorization'))return json({error:'確認画面から設定してください。'},403);const body=z.object({role:z.enum(['passenger','driver','manager'])}).strict().parse(await jsonBody(request));return json(await mintCredential(await browserPrincipal(),body.role),201);}catch(e){return errorResponse(e);}}
export async function DELETE(request:Request){try{checkOrigin(request);if(request.headers.has('authorization'))return json({error:'確認画面から設定してください。'},403);const body=z.object({id:z.string().uuid()}).strict().parse(await jsonBody(request));await revokeCredential(await browserPrincipal(),body.id);return json({revoked:true});}catch(e){return errorResponse(e);}}
