import {authorize,checkOrigin,response,errorResponse} from '@/lib/board-server';
import {readSharedSession,sessionCookie} from '@/lib/shared-auth';
export async function POST(request:Request){try{checkOrigin(request);const {db}=await authorize(true);const session=await readSharedSession(db);if(session)await db.prepare('DELETE FROM shared_sessions WHERE token_hash=?').bind(session.tokenHash).run();return Response.json({ok:true},{headers:{'Cache-Control':'no-store','Set-Cookie':sessionCookie('',0)}})}catch(e){return errorResponse(e)}}
