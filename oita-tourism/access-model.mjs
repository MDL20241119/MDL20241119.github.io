// Exact same-trip calls only. No invented transfers, road paths or missing services.
export function directCalls(network,anchors,feed,day,radius=300){
 const rad=Math.PI/180;
 const dist=(a,b)=>{const h=Math.sin((b.lat-a.lat)*rad/2)**2+Math.cos(a.lat*rad)*Math.cos(b.lat*rad)*Math.sin((b.lon-a.lon)*rad/2)**2;return 6371000*2*Math.atan2(Math.sqrt(h),Math.sqrt(Math.max(0,1-h)))};
 const near=new Map(Object.values(network.stops).map(s=>[s.key,anchors.map(a=>({id:a.id,distance:Math.round(dist(a,s))})).filter(a=>a.distance<=radius)]));
 const result=[];
 for(const trip of network.trips){const best=new Map();
  for(let i=0;i<trip.calls.length-1;i++){const from=trip.calls[i];if(!from.pickup||from.departure<0||from.departure>=86400)continue;
   for(const a of near.get(from.stopKey)??[])for(let j=i+1;j<trip.calls.length;j++){const to=trip.calls[j];if(!to.dropoff||to.arrival<from.departure||to.arrival>=86400)continue;
    for(const b of near.get(to.stopKey)??[]){if(a.id===b.id)continue;const k=a.id+'|'+b.id,score=a.distance+b.distance,old=best.get(k);if(old&&old.score<=score)continue;
     best.set(k,{score,day,from:a.id,to:b.id,feedId:feed.id,trip:trip.key,route:network.routes[trip.route]?.name??trip.routeId,departure:from.departure,arrival:to.arrival,board:{id:from.stop_id,name:network.stops[from.stopKey].name,lat:network.stops[from.stopKey].lat,lon:network.stops[from.stopKey].lon,distance:a.distance},alight:{id:to.stop_id,name:network.stops[to.stopKey].name,lat:network.stops[to.stopKey].lat,lon:network.stops[to.stopKey].lon,distance:b.distance}});
    }
   }
  }
  result.push(...best.values());
 }
 return result.map(({score,...r})=>r);
}
export const minutes=t=>{const [h,m]=t.split(':').map(Number);return h*60+m};
export const clock=s=>String(Math.floor(s/3600)).padStart(2,'0')+':'+String(Math.floor(s/60)%60).padStart(2,'0');
export function packAccess(data){
 const places=[],trips=[],routes=[],stops=[];
 const intern=(list,value)=>{const key=JSON.stringify(value),i=list.findIndex(x=>JSON.stringify(x)===key);if(i>=0)return i;list.push(value);return list.length-1};
 return {...data,encoding:'indexed-calls-v1',places,trips,routes,stops,columns:['day','from','to','feed','trip','route','departure','arrival','board','boardDistance','alight','alightDistance'],calls:data.calls.map(c=>[c.day,intern(places,c.from),intern(places,c.to),data.feeds.findIndex(f=>f.id===c.feedId),intern(trips,c.trip),intern(routes,c.route),c.departure,c.arrival,intern(stops,{id:c.board.id,name:c.board.name,lat:c.board.lat,lon:c.board.lon}),c.board.distance,intern(stops,{id:c.alight.id,name:c.alight.name,lat:c.alight.lat,lon:c.alight.lon}),c.alight.distance])};
}
export function unpackAccess(data){if(data.encoding!=='indexed-calls-v1')return data;return {...data,calls:data.calls.map(c=>({day:c[0],from:data.places[c[1]],to:data.places[c[2]],feedId:data.feeds[c[3]].id,trip:data.trips[c[4]],route:data.routes[c[5]],departure:c[6],arrival:c[7],board:{...data.stops[c[8]],distance:c[9]},alight:{...data.stops[c[10]],distance:c[11]}}))};}
export function accessOptions(calls,state){
 const selected=calls.filter(c=>c.day===state.day),start=minutes(state.departure)*60,end=minutes(state.deadline)*60;
 if(start>=end)return {invalid:true,outbound:[],returns:[],pairs:[]};
 const eligible=c=>c.arrival-c.departure<=state.maxMinutes*60;
 const outbound=selected.filter(c=>c.from===state.origin&&c.to===state.anchor&&c.departure>=start&&c.arrival<=end&&eligible(c)).sort((a,b)=>a.departure-b.departure||a.arrival-b.arrival);
 const returns=selected.filter(c=>c.from===state.anchor&&c.to===state.origin&&c.departure>=start&&c.arrival<=end&&eligible(c)).sort((a,b)=>a.departure-b.departure);
 // A visible 20-minute margin covers neither a measured walk nor guaranteed boarding.
 const pairs=outbound.map(out=>({out,back:returns.find(back=>back.departure>=out.arrival+state.dwell*60+20*60)})).filter(p=>p.back);
 return {outbound,returns,pairs,invalid:false};
}
export function directionsUrl(from,to,mode='transit'){
 const u=new URL('https://www.google.com/maps/dir/');u.searchParams.set('api','1');u.searchParams.set('origin',`${from.lat},${from.lon}`);u.searchParams.set('destination',`${to.lat},${to.lon}`);u.searchParams.set('travelmode',['transit','walking','driving'].includes(mode)?mode:'transit');return u.href;
}
