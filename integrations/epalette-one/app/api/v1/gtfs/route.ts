import {authenticate,json,errorResponse} from '@/lib/integration/service';
import {readState} from '@/lib/store';
import {permit} from '@/lib/integration/core';
import {exportFeed,zipFeed,validateFeed,inspectZip} from '@/lib/integration/gtfs';
export async function GET(request:Request){try{const p=await authenticate(request,'api');permit(p,'get_today_actions');const feed=exportFeed(await readState(p.workspace),new URL(request.url).origin);validateFeed(feed);const bytes=zipFeed(feed);return new Response(bytes as unknown as BodyInit,{headers:{'Content-Type':'application/zip','Content-Disposition':'attachment; filename="epalette-SYNTHETIC-gtfs.zip"','Cache-Control':'no-store','X-Data-Mode':'synthetic-demo'}});}catch(e){return errorResponse(e);}}
export async function POST(request:Request){try{const p=await authenticate(request,'api');permit(p,'get_today_actions');return json(inspectZip(new Uint8Array(await request.arrayBuffer())));}catch(e){return errorResponse(e);}}
