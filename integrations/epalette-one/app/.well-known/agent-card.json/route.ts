import {agentCard} from '@/lib/integration/a2a';
export async function GET(request:Request){return Response.json(agentCard(new URL(request.url).origin));}
