import {distance} from '../lab/gtfs.mjs';

class Heap {
  constructor(){this.a=[];}
  push(v){const a=this.a;a.push(v);let i=a.length-1;while(i){const p=(i-1)>>1;if(a[p][0]<=v[0])break;a[i]=a[p];i=p;}a[i]=v;}
  pop(){const a=this.a,first=a[0],last=a.pop();if(a.length){let i=0;while(i*2+1<a.length){let c=i*2+1;if(c+1<a.length&&a[c+1][0]<a[c][0])c++;if(a[c][0]>=last[0])break;a[i]=a[c];i=c;}a[i]=last;}return first;}
}
export function createWalkingGraph(data){
  const count=data.count??data.nodes.length,edgeCount=data.edgeCount??data.edges.length,latitudes=new Float64Array(count),longitudes=new Float64Array(count),offset=new Uint32Array(count+1),active=new Uint8Array(count),grid=new Map(),step=.002,snaps=new Map(),cache=new Map();
  for(let i=0;i<count;i++){const p=data.node?data.node(i):data.nodes[i];latitudes[i]=p[0];longitudes[i]=p[1];}
  for(let i=0;i<edgeCount;i++){const [a,b,meters]=data.edge?data.edge(i):data.edges[i];if(a<0||b<0||a>=count||b>=count||!Number.isFinite(meters)||meters<=0)throw Error('道路データの参照・距離が不正です');offset[a+1]++;active[a]=active[b]=1;}
  for(let i=1;i<=count;i++)offset[i]+=offset[i-1];
  const cursor=offset.slice(),targets=new Uint32Array(edgeCount),lengths=new Float32Array(edgeCount),stairsFlags=new Uint8Array(edgeCount);
  for(let j=0;j<edgeCount;j++){const [a,b,meters,stairs]=data.edge?data.edge(j):data.edges[j];const i=cursor[a]++;targets[i]=b;lengths[i]=meters;stairsFlags[i]=stairs;}
  const nodePoint=i=>[latitudes[i],longitudes[i]];
  for(let i=0;i<count;i++){if(!active[i])continue;const key=Math.floor(latitudes[i]/step)+','+Math.floor(longitudes[i]/step);if(!grid.has(key))grid.set(key,[]);grid.get(key).push(i);}
  function snap(p){
    const key=p.lat+','+p.lon;if(snaps.has(key))return snaps.get(key);let best=null,minimum=75;
    const x=Math.floor(p.lat/step),y=Math.floor(p.lon/step);
    for(let a=-1;a<=1;a++)for(let b=-1;b<=1;b++)for(const i of grid.get((x+a)+','+(y+b))??[]){const d=distance(p,{lat:latitudes[i],lon:longitudes[i]});if(d<=minimum){minimum=d;best={node:i,meters:d};}}
    snaps.set(key,best);return best;
  }
  function search(start,limit,wheelchair){
    const key=start+':'+limit+':'+wheelchair;if(cache.has(key))return cache.get(key);
    const heap=new Heap(),dist=new Map([[start,0]]),previous=new Map();heap.push([0,start]);
    while(heap.a.length){const [d,i]=heap.pop();if(d!==dist.get(i))continue;for(let edge=offset[i];edge<offset[i+1];edge++){if(wheelchair&&stairsFlags[edge])continue;const j=targets[edge],v=d+lengths[edge];if(v<=limit&&v<(dist.get(j)??Infinity)){dist.set(j,v);previous.set(j,i);heap.push([v,j]);}}}
    const result={dist,previous};if(cache.size>=250)cache.delete(cache.keys().next().value);cache.set(key,result);return result;
  }
  function route(a,b,limit=2000,wheelchair=false,geometry=false){
    if(distance(a,b)<.1)return {meters:0,coordinates:[[a.lat,a.lon],[b.lat,b.lon]],connectorMeters:0};
    if(distance(a,b)>limit)return {meters:Infinity,reason:'distance_limit'};
    const from=snap(a),to=snap(b);if(!from||!to)return {meters:Infinity,reason:'unmatched_road'};
    const found=search(from.node,limit,wheelchair),networkMeters=found.dist.get(to.node);
    if(networkMeters===undefined)return {meters:Infinity,reason:'no_path_in_range'};
    const meters=from.meters+networkMeters+to.meters,coordinates=[];
    if(geometry){let i=to.node;coordinates.push(nodePoint(i));while(i!==from.node){i=found.previous.get(i);if(i===undefined)throw Error('道路経路の復元に失敗');coordinates.push(nodePoint(i));}coordinates.reverse();coordinates.unshift([a.lat,a.lon]);coordinates.push([b.lat,b.lon]);}
    return {meters,coordinates,connectorMeters:from.meters+to.meters};
  }
  return {route,meta:data.meta};
}
let pending;
export function decodeWalkingGraph(buffer){
  const view=new DataView(buffer),decoder=new TextDecoder();
  if(decoder.decode(new Uint8Array(buffer,0,8))!=='MDLWALK1')throw Error('道路データ形式が一致しません');
  const metaLength=view.getUint32(8,true),count=view.getUint32(12,true),edgeCount=view.getUint32(16,true),start=20+metaLength,edgeStart=start+count*8,lengthStart=edgeStart+edgeCount*8,flagStart=lengthStart+edgeCount*4;
  if(flagStart+edgeCount!==buffer.byteLength)throw Error('道路データが欠損しています');
  return {count,edgeCount,meta:JSON.parse(decoder.decode(new Uint8Array(buffer,20,metaLength))),node:i=>[view.getInt32(start+i*8,true)/1e7,view.getInt32(start+i*8+4,true)/1e7],edge:i=>[view.getUint32(edgeStart+i*8,true),view.getUint32(edgeStart+i*8+4,true),view.getUint32(lengthStart+i*4,true)/100,view.getUint8(flagStart+i)]};
}
export async function loadWalkingGraph(){
  if(!pending)pending=(async()=>{
    const url=new URL('../data/osm/walking-graph.json',import.meta.url),r=await fetch(url);
    if(!r.ok)throw Error('道路データを取得できません');
    if(typeof DecompressionStream==='undefined')throw Error('道路データの展開に対応したブラウザーが必要です');
    const manifest=await r.json();if(manifest.format!=='MDLWALK1/gzip-parts'||!manifest.parts?.length)throw Error('道路データの配信形式が一致しません');
    const parts=[];
    for(const p of manifest.parts){
      if(!/^walking-graph\.part\d+$/.test(p.file))throw Error('道路ファイル名が不正です');
      const response=await fetch(new URL(p.file,url));if(!response.ok)throw Error('道路データの一部を取得できません');
      const b=await response.arrayBuffer(),hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',b))].map(v=>v.toString(16).padStart(2,'0')).join('');
      if(b.byteLength!==p.bytes||hash!==p.sha256)throw Error('道路データの一部が一致しません');parts.push(b);
    }
    const blob=new Blob(parts);if(blob.size!==manifest.bytes)throw Error('道路データのサイズが一致しません');
    const buffer=await new Response(blob.stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
    return createWalkingGraph(decodeWalkingGraph(buffer));
  })().catch(e=>{pending=null;throw e;});
  return pending;
}
