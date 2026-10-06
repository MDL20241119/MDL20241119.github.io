import {rawDb,response,errorResponse} from '@/lib/board-server';
export async function GET(){try{const config=await rawDb().prepare('SELECT enabled FROM shared_access WHERE id=1').first<{enabled:number}>();return response({configured:!!config?.enabled})}catch(e){return errorResponse(e)}}
