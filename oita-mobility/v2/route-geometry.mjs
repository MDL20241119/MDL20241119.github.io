import {distance,key} from '../lab/gtfs.mjs';

const point = p => ({lat:Number(p.shape_pt_lat),lon:Number(p.shape_pt_lon)});
const valid = p => Number.isFinite(p.lat)&&Number.isFinite(p.lon)&&Math.abs(p.lat)<=90&&Math.abs(p.lon)<=180;
const interpolate = (a,b,t) => ({lat:a.lat+(b.lat-a.lat)*t,lon:a.lon+(b.lon-a.lon)*t});

export function indexShapes(feeds){
  const index=new Map();
  for(const f of feeds)for(const row of f.tables.shapes??[]){
    const id=key(f.id,row.shape_id);
    if(!index.has(id))index.set(id,[]);
    index.get(id).push(row);
  }
  for(const [id,rows]of index){
    rows.sort((a,b)=>Number(a.shape_pt_sequence)-Number(b.shape_pt_sequence));
    const points=rows.map(point);
    if(points.length<2||points.some(p=>!valid(p))){index.delete(id);continue;}
    const measures=rows.map(r=>r.shape_dist_traveled?.trim()?Number(r.shape_dist_traveled):NaN);
    index.set(id,{points,measures:measures.every((d,i)=>Number.isFinite(d)&&(!i||d>measures[i-1]))?measures:null});
  }
  return index;
}

function at(points,position){const i=Math.min(points.length-2,Math.floor(position));return interpolate(points[i],points[i+1],position-i);}
function slice(points,from,to){
  if(!Number.isFinite(from)||!Number.isFinite(to)||to<=from)return null;
  return [at(points,from),...points.slice(Math.floor(from)+1,Math.ceil(to)),at(points,to)].map(p=>[p.lat,p.lon]);
}
function measuredPosition(values,d){
  if(d<values[0]||d>values.at(-1))return null;
  let i=0;while(i<values.length-2&&values[i+1]<d)i++;
  return i+(d-values[i])/(values[i+1]-values[i]);
}
function candidatePositions(points,p){
  const candidates=[];
  for(let i=0;i<points.length-1;i++){
    const a=points[i],b=points[i+1],x=(b.lon-a.lon)*Math.cos(p.lat*Math.PI/180),y=b.lat-a.lat;
    const px=(p.lon-a.lon)*Math.cos(p.lat*Math.PI/180),py=p.lat-a.lat;
    const t=Math.max(0,Math.min(1,(px*x+py*y)/(x*x+y*y||1)));
    const meters=distance(p,interpolate(a,b,t));
    if(meters<=200){
      const position=i+t,last=candidates.at(-1);
      if(last&&Math.abs(last.position-position)<1e-8){if(meters<last.meters)last.meters=meters;}
      else candidates.push({position,meters});
    }
  }
  return candidates;
}

// Keep competing positions until later calls resolve loops and retraced roads.
// A greedy nearest-point choice can jump to the return half of the same trip.
function alignCalls(shape,trip,network,last){
  let previous=[];
  for(let i=0;i<=last;i++){
    const stop=network.stops[trip.calls[i].stopKey];if(!stop)return null;
    const candidates=candidatePositions(shape.points,stop);if(!candidates.length)return null;
    const current=[];let j=0,best=null;
    for(const candidate of candidates){
      while(j<previous.length&&previous[j].position<=candidate.position){
        const state=previous[j++];if(!best||state.cost<best.cost)best=state;
      }
      if(i===0||best)current.push({...candidate,cost:(best?.cost??0)+candidate.meters**2,previous:best});
    }
    if(!current.length)return null;
    previous=current;
  }
  let best=previous.reduce((a,b)=>a.cost<=b.cost?a:b),positions=[];
  while(best){positions.push(best.position);best=best.previous;}
  return positions.reverse();
}

// Only use the selected trip's shape. Uncertain alignment falls back to an explicitly approximate line.
export function geometryForLeg(leg,network,shapes){
  const fallback={kind:leg.mode==='walk'?'walk-estimate':'approximate',points:[[leg.from.lat,leg.from.lon],[leg.to.lat,leg.to.lon]]};
  if(leg.mode!=='bus')return fallback;
  const trip=network.trips.find(t=>t.key===leg.tripKey);
  const shape=trip?.shape&&shapes.get(key(trip.feed,trip.shape));
  if(!shape)return fallback;
  const first=trip.calls.findIndex(c=>String(c.stop_sequence)===String(leg.boardSequence));
  const last=trip.calls.findIndex(c=>String(c.stop_sequence)===String(leg.alightSequence));
  if(first<0||last<=first)return fallback;
  const a=trip.calls[first],b=trip.calls[last];let from,to;
  if(shape.measures&&a.shape_dist_traveled?.trim()&&b.shape_dist_traveled?.trim()){
    from=measuredPosition(shape.measures,Number(a.shape_dist_traveled));
    to=measuredPosition(shape.measures,Number(b.shape_dist_traveled));
  }else{
    const positions=alignCalls(shape,trip,network,last);
    if(!positions)return fallback;
    from=positions[first];to=positions[last];
  }
  const points=slice(shape.points,from,to);
  if(!points||distance(leg.from,{lat:points[0][0],lon:points[0][1]})>200||distance(leg.to,{lat:points.at(-1)[0],lon:points.at(-1)[1]})>200)return fallback;
  return {kind:'gtfs-shape',points,shapeId:trip.shape};
}

export function attachRouteGeometry(result,network,shapes){
  for(const direction of ['outbound','inbound'])if(result[direction]){
    result[direction]={...result[direction],path:result[direction].path.map(leg=>({...leg,geometry:geometryForLeg(leg,network,shapes)}))};
  }
  return result;
}
