import {distance} from '../lab/gtfs.mjs';

const point=p=>Number.isFinite(p?.lat)&&Number.isFinite(p?.lon);
export const FIRST={
 near:['徒歩圏内に停留所あり','#13745e'],
 far:['徒歩上限内に停留所なし','#c64551'],
 unknown:['未計算・データ不足','#75808c']
};
export const SECOND={
 candidate:['時刻表上の往復候補あり','#13745e'],
 not_found:['用事に合う往復候補なし','#c64551'],
 walk:['停留所を使わず徒歩で往復候補あり','#3858bf'],
 outside:['徒歩圏外（②の集計外）','#75808c'],
 unknown:['未計算・判定保留','#a16b10']
};

// Physical coverage is independent of trips running on the chosen weekday.
export function stopPlaces(feeds){
 return feeds.flatMap(f=>{
   const calls=f.tables.stop_times??[],last=new Map(),board=new Set();
   for(const c of calls)last.set(c.trip_id,Math.max(last.get(c.trip_id)??-Infinity,Number(c.stop_sequence)));
   for(const c of calls)if(Number(c.stop_sequence)<last.get(c.trip_id)&&c.pickup_type!=='1')board.add(c.stop_id);
   return (f.tables.stops??[]).filter(s=>board.has(s.stop_id)&&(!s.location_type||s.location_type==='0')).flatMap(s=>{
     const p={name:s.stop_name,lat:Number(s.stop_lat),lon:Number(s.stop_lon)};
     return s.stop_lat?.trim()&&s.stop_lon?.trim()&&point(p)&&Math.abs(p.lat)<=90&&Math.abs(p.lon)<=180?[p]:[];
   });
 });
}
export function walkAccess(home,stops,o,incomplete=false){
 let nearest=null,meters=Infinity;
 if(point(home))for(const s of stops){
   const m=distance(home,s)*o.walkFactor;
   if(m<meters){nearest=s;meters=m;}
 }
 const mins=nearest?meters/(o.walkSpeed*1000/60):null;
 const state=!nearest?'unknown':meters<=o.maxWalk+1e-6?'near':incomplete?'unknown':'far';
 return {state,name:nearest?.name??null,minutes:mins,meters:nearest?meters:null};
}
export function purposeAccess(result){
 const first=result?.stopAccess?.state??'unknown';
 if(result?.state==='candidate'&&result.outbound?.boardings===0&&result.inbound?.boardings===0)return 'walk';
 if(first==='far')return 'outside';
 if(first!=='near')return 'unknown';
 return ['candidate','not_found'].includes(result?.state)?result.state:'unknown';
}
export function stageSummary(cells,results){
 const first={near:0,far:0,unknown:0},second={candidate:0,not_found:0,walk:0,unknown:0};
 let population=0,missing=0,walkOutside=0;
 for(const c of cells){
   const p=c.properties??c,n=p.population2020,r=results.get(p.id);
   if(!Number.isFinite(n)||n<0){missing++;continue;}
   const state=r?.stopAccess?.state??'unknown',purpose=purposeAccess(r);
   population+=n;first[state]+=n;
   if(state==='near')second[purpose]+=n;
   else if(purpose==='walk')walkOutside+=n;
 }
 return {population,missing,first,second,walkOutside};
}
