/* Read-only calculations over the shared Core snapshot. No generated trip data. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.YokoInsights=api;})(typeof window==='object'?window:this,function(){
  'use strict';
  const DAY=86400000,JST=9*3600000;
  const points={'stop-a':[33.1968,131.5718],'stop-b':[33.2024,131.5784],'stop-c':[33.2028,131.5652]};
  const stamp=v=>{const n=Date.parse(v);return Number.isFinite(n)?n:null;};
  const day=ms=>new Date(ms+JST).toISOString().slice(0,10);
  const midnight=key=>Date.parse(key+'T00:00:00+09:00');
  const event=(r,status)=>{const e=(r.events||[]).find(e=>e.status===status);return e?stamp(e.created_at):null;};
  const validNumber=n=>Number.isFinite(n)&&n>=0?n:0;
  function itinerary(rides,vehicleIds){
    const ids=new Set(vehicleIds),priority={onboard:0,arrived:1,assigned:2};
    return rides.filter(r=>r.vehicle_id&&ids.has(r.vehicle_id)&&r.status in priority).sort((a,b)=>priority[a.status]-priority[b.status]||(event(a,'assigned')??stamp(a.created_at)??0)-(event(b,'assigned')??stamp(b.created_at)??0)||a.id.localeCompare(b.id)).flatMap(r=>{
      const legs=[];if(r.status!=='onboard')legs.push({rideId:r.id,kind:'pickup',stopId:r.origin_stop_id,name:r.origin_name,people:r.passengers,status:r.status});
      legs.push({rideId:r.id,kind:'dropoff',stopId:r.destination_stop_id,name:r.destination_name,people:r.passengers,status:r.status});return legs;
    }).map((leg,index)=>({...leg,number:index+1}));
  }
  function navigation(stopId){if(!points[stopId])return null;const url=new URL('https://www.google.com/maps/dir/');url.search=new URLSearchParams({api:'1',destination:points[stopId].join(','),travelmode:'driving',dir_action:'navigate'}).toString();return url.href;}
  function union(intervals){let total=0,end=-Infinity;for(const[a,b]of intervals.filter(([a,b])=>Number.isFinite(a)&&Number.isFinite(b)&&b>a).sort((a,b)=>a[0]-b[0])){total+=Math.max(0,b-Math.max(a,end));end=Math.max(end,b);}return total;}
  function scheduleMinutes(value){if(!/^\d{2}:\d{2}$/.test(value||''))return null;const[h,m]=value.split(':').map(Number);return h<24&&m<60?h*60+m:null;}
  function metrics(snapshot,days=7,schedule=null){
    const now=stamp(snapshot.as_of);if(now===null)throw new Error('Snapshot timestamp is required');
    days=[1,7,30].includes(Number(days))?Number(days):7;
    const today=midnight(day(now)),since=today-(days-1)*DAY,until=now;
    const rides=snapshot.rides||[],vehicles=snapshot.vehicles||[],inPeriod=t=>t!==null&&t>=since&&t<=until;
    const requested=rides.filter(r=>inPeriod(stamp(r.created_at)));
    const completed=rides.filter(r=>inPeriod(event(r,'completed'))),cancelled=rides.filter(r=>inPeriod(event(r,'cancelled')));
    const boarded=rides.filter(r=>inPeriod(event(r,'onboard')));
    const waits=boarded.map(r=>{const a=stamp(r.created_at),b=event(r,'onboard');return a!==null&&b!==null&&b>=a?(b-a)/60000:null;}).filter(n=>n!==null);
    const trend=Array.from({length:days},(_,i)=>({day:day(since+i*DAY),people:0,rides:0}));
    for(const r of completed){const row=trend.find(d=>d.day===day(event(r,'completed')));if(row){row.people+=r.passengers;row.rides++;}}
    const routes=new Map();for(const r of completed){const key=r.origin_stop_id+'>'+r.destination_stop_id;const row=routes.get(key)||{origin:r.origin_name,destination:r.destination_name,people:0,rides:0};row.people+=r.passengers;row.rides++;routes.set(key,row);}
    const hours=Array.from({length:24},(_,hour)=>({hour,requests:0}));for(const r of requested)hours[new Date(stamp(r.created_at)+JST).getUTCHours()].requests++;
    const capacity=vehicles.reduce((n,v)=>n+validNumber(v.capacity),0),assignedVehicles=vehicles.filter(v=>v.reserved>0).length;
    const onboard=rides.filter(r=>r.status==='onboard').reduce((n,r)=>n+r.passengers,0);
    let utilization=null;const begin=scheduleMinutes(schedule?.start),finish=scheduleMinutes(schedule?.end);
    if(begin!==null&&finish!==null&&begin!==finish){
      const windows=[];for(let t=since-DAY;t<=until;t+=DAY){const a=t+begin*60000,b=t+(finish<=begin?finish+1440:finish)*60000;const x=Math.max(since,a),y=Math.min(until,b);if(y>x)windows.push([x,y]);}
      const byVehicle=new Map(vehicles.map(v=>[v.id,[]]));let missing=0;
      for(const r of rides){if(!byVehicle.has(r.vehicle_id))continue;const a=event(r,'assigned'),terminal=['completed','cancelled'].includes(r.status),b=terminal?event(r,r.status):until;
        if(a===null||b===null||b<a){if(inPeriod(stamp(r.created_at))||(!terminal&&r.vehicle_id))missing++;continue;}
        for(const[x,y]of windows){const lo=Math.max(a,x),hi=Math.min(b,y);if(hi>lo)byVehicle.get(r.vehicle_id).push([lo,hi]);}
      }
      const busyMs=[...byVehicle.values()].reduce((n,rows)=>n+union(rows),0),availableMs=union(windows)*vehicles.length;
      utilization={busyMinutes:busyMs/60000,availableMinutes:availableMs/60000,rate:availableMs?busyMs/availableMs*100:null,missing,start:schedule.start,end:schedule.end};
    }
    return {since,until,days,period:day(since)+' 〜 '+day(until),requested:requested.length,completed:completed.length,cancelled:cancelled.length,people:completed.reduce((n,r)=>n+r.passengers,0),completionRate:completed.length+cancelled.length?100*completed.length/(completed.length+cancelled.length):null,waitMinutes:waits.length?waits.reduce((a,b)=>a+b,0)/waits.length:null,waitSamples:waits.length,trend,routes:[...routes.values()].sort((a,b)=>b.people-a.people),hours,assignedVehicles,totalVehicles:vehicles.length,assignmentRate:vehicles.length?assignedVehicles/vehicles.length*100:null,onboard,capacity,occupancyRate:capacity?onboard/capacity*100:null,utilization,recordCount:rides.length,possiblyTruncated:rides.length>=(snapshot.limit||200)};
  }
  return {itinerary,navigation,metrics,union,points};
});
