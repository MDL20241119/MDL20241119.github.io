import { DomainError } from '../model';
import { tools } from './catalog';
export const MCP_VERSION='2026-07-28';
type Invoke=(name:string,args:unknown,key:string|null)=>Promise<unknown>;
function rpc(id:unknown,result:unknown,status=200){return Response.json({jsonrpc:'2.0',...(id===undefined?{}:{id}),result},{status,headers:{'Cache-Control':'no-store'}});}
export function rpcError(id:unknown,code:number,message:string,status=400,data?:unknown){return Response.json({jsonrpc:'2.0',...(id===undefined?{}:{id}),error:{code,message,...(data?{data}:{})}},{status,headers:{'Cache-Control':'no-store'}});}
function decodeHeader(value:string|null){if(value===null)return null;if(value.startsWith('=?base64?')&&value.endsWith('?=')){try{return new TextDecoder('utf-8',{fatal:true}).decode(Uint8Array.from(atob(value.slice(9,-2)),c=>c.charCodeAt(0)));}catch{return null;}}return /^[\x20-\x7e]*$/.test(value)&&value.trim()===value?value:null;}
export async function handleMcp(request:Request,invoke:Invoke,visible=tools){
 if(request.method!=='POST')return new Response(null,{status:405,headers:{Allow:'POST'}});
 const origin=request.headers.get('origin');if(origin&&origin!==new URL(request.url).origin)return rpcError(undefined,-32600,'Origin is not allowed',403);
 if(!request.headers.get('content-type')?.startsWith('application/json'))return rpcError(undefined,-32600,'Content-Type must be application/json',415);
 const accept=request.headers.get('accept')??'';if(!accept.includes('application/json')||!accept.includes('text/event-stream'))return rpcError(undefined,-32600,'Accept must include application/json and text/event-stream',406);
 let body;try{const raw=await request.text();if(raw.length>32000)return rpcError(undefined,-32600,'Request too large',413);body=JSON.parse(raw);}catch{return rpcError(undefined,-32700,'Invalid JSON');}
 if(!body||Array.isArray(body)||body.jsonrpc!=='2.0'||typeof body.method!=='string'||!['string','number'].includes(typeof body.id))return rpcError(undefined,-32600,'A single JSON-RPC request with an id is required');
 const meta=body.params?._meta;const version=request.headers.get('MCP-Protocol-Version');
 if(!version||meta?.['io.modelcontextprotocol/protocolVersion']!==version||request.headers.get('Mcp-Method')!==body.method||(body.method==='tools/call'&&decodeHeader(request.headers.get('Mcp-Name'))!==body.params?.name))return rpcError(body.id,-32020,'Header mismatch');
 if(version!==MCP_VERSION)return rpcError(body.id,-32022,'Unsupported protocol version',400,{requested:version,supported:[MCP_VERSION]});
 if(!meta?.['io.modelcontextprotocol/clientCapabilities']||typeof meta['io.modelcontextprotocol/clientCapabilities']!=='object'||Array.isArray(meta['io.modelcontextprotocol/clientCapabilities']))return rpcError(body.id,-32602,'Per-request clientCapabilities is required');
 const resultMeta={'io.modelcontextprotocol/serverInfo':{name:'epalette-one',version:'1.1.0'}};
 if(body.method==='server/discover')return rpc(body.id,{resultType:'complete',supportedVersions:[MCP_VERSION],capabilities:{tools:{}},_meta:resultMeta,cacheScope:'private',ttlMs:0,instructions:'Synthetic sandbox. Search and planning use the shared business core. Proposals require human approval at approvalUrl. No vehicle control.'});
 if(body.method==='tools/list'){if(body.params?.cursor)return rpcError(body.id,-32602,'Cursor is not supported');return rpc(body.id,{resultType:'complete',tools:visible,cacheScope:'private',ttlMs:0,_meta:resultMeta});}
 if(body.method!=='tools/call')return rpcError(body.id,-32601,'Method not found',404);
 if(!visible.some(t=>t.name===body.params?.name))return rpcError(body.id,-32602,'Unknown or unavailable tool');
 const args={...(body.params.arguments??{})};let key=request.headers.get('Idempotency-Key');
 if(body.params.name.startsWith('prepare_')||body.params.name==='execute_approved'){if(typeof args.requestId!=='string'||decodeHeader(request.headers.get('Mcp-Param-Request-Id'))!==args.requestId)return rpcError(body.id,-32020,'Request-Id header mismatch');key=args.requestId;delete args.requestId;}
 try{const result=await invoke(body.params.name,args,key);return rpc(body.id,{resultType:'complete',content:[{type:'text',text:JSON.stringify(result)}],structuredContent:result,isError:false,_meta:resultMeta});}
 catch(e){return rpc(body.id,{resultType:'complete',content:[{type:'text',text:e instanceof DomainError?e.message:'処理に失敗しました。予約成立とは扱わず、再確認してください。'}],isError:true,_meta:resultMeta});}
}
