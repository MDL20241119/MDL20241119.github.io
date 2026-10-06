import {authorize,response,errorResponse} from '@/lib/board-server';
export async function GET(){try{const {db,shared}=await authorize();const h=await db.prepare('SELECT * FROM history ORDER BY at DESC LIMIT 100').all<any>();return response(shared?h.results.map(x=>({...x,actor:x.actor==='共有メンバー'?'共有メンバー':'管理者'})):h.results);}catch(e){return errorResponse(e)}}
