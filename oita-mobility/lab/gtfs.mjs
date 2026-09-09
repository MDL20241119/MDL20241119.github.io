import {parseCSV,csvText,unzip,zip,sha256} from './io.mjs';
export const ENGINE_VERSION='oita-planning-1.0';
export const key=(feed,id)=>`${feed}::${id}`;
export function seconds(v){if(!/^\d{1,3}:\d{2}:\d{2}$/.test(v??''))return null;const [h,m,s]=v.split(':').map(Number);return h<168&&m<60&&s<60?h*3600+m*60+s:null}
export function clock(s){if(!Number.isFinite(s)||s<0)return '';return `${String(Math.floor(s/3600)).padStart(2,'0')}:${String(Math.floor(s/60)%60).padStart(2,'0')}:${String(Math.round(s)%60).padStart(2,'0')}`}
export function dateKey(v){return String(v).replaceAll('-','')}
export function validDate(v){v=dateKey(v);if(!/^\d{8}$/.test(v))return false;const d=new Date(`${v.slice(0,4)}-${v.slice(4,6)}-${v.slice(6,8)}T00:00:00Z`);return Number.isFinite(+d)&&d.toISOString().slice(0,10).replaceAll('-','')===v}
export function addDate(v,days){v=dateKey(v);const d=new Date(`${v.slice(0,4)}-${v.slice(4,6)}-${v.slice(6,8)}T00:00:00Z`);d.setUTCDate(d.getUTCDate()+days);return d.toISOString().slice(0,10).replaceAll('-','')}
export function activeServices(tables,date){
  date=dateKey(date);if(!validDate(date))throw Error('運行日が不正です');const weekday=['sunday','monday','tuesday','wednesday','thursday','friday','saturday'][new Date(`${date.slice(0,4)}-${date.slice(4,6)}-${date.slice(6,8)}T00:00:00Z`).getUTCDay()];
  const active=new Set((tables.calendar??[]).filter(r=>r.start_date<=date&&date<=r.end_date&&r[weekday]==='1').map(r=>r.service_id));
  for(const r of tables.calendar_dates??[])if(r.date===date){if(r.exception_type==='1')active.add(r.service_id);if(r.exception_type==='2')active.delete(r.service_id)}return active;
}
export async function importGTFS(buffer,name,id){
  const entries=await unzip(buffer),tables={},extra={},emptyFiles={};
  for(const [file,bytes]of Object.entries(entries)){
    if(file.endsWith('.txt')){tables[file.slice(0,-4)]=parseCSV(new TextDecoder('utf-8',{fatal:true}).decode(bytes));if(!tables[file.slice(0,-4)].length)emptyFiles[file]=Array.from(bytes)}
    else extra[file]=Array.from(bytes);
  }
  return {id,name,hash:await sha256(buffer),tables,extra,emptyFiles,importedAt:new Date().toISOString()};
}
export function validateFeeds(feeds){
  const issues=[];let errors=0,warnings=0;
  const note=(level,f,code,message)=>{level==='error'?errors++:warnings++;if(issues.length<200)issues.push({level,feed:f.name,code,message})};
  for(const f of feeds){
    const t=f.tables;
    for(const name of ['agency','routes','trips','stops','stop_times'])if(!t[name]?.length)note('error',f,'required',`${name}.txt が空または未収録です`);
    const ids={};for(const [name,col]of [['agency','agency_id'],['routes','route_id'],['trips','trip_id'],['stops','stop_id']]){ids[name]=new Set();for(const r of t[name]??[]){if(!r[col]&&!(name==='agency'&&t.agency.length===1))note('error',f,'empty_id',`${name}: IDが空です`);if(ids[name].has(r[col]))note('error',f,'duplicate_id',`${name}: ID重複 ${r[col]}`);ids[name].add(r[col])}}
    const serviceIds=new Set([...(t.calendar??[]).map(r=>r.service_id),...(t.calendar_dates??[]).map(r=>r.service_id)]);if(!serviceIds.size)note('error',f,'calendar','カレンダー・例外日がありません');
    const seenDates=new Set();for(const r of t.calendar_dates??[]){const k=r.service_id+'|'+r.date;if(seenDates.has(k))note('error',f,'calendar_duplicate',`同じ例外日が重複 ${k}`);seenDates.add(k);if(!validDate(r.date)||!['1','2'].includes(r.exception_type))note('error',f,'calendar_value','例外日・例外種別が不正です')}
    for(const r of t.calendar??[])if(!validDate(r.start_date)||!validDate(r.end_date)||r.start_date>r.end_date)note('error',f,'calendar_range','運行期間が不正です');
    for(const r of t.trips??[]){if(!ids.routes.has(r.route_id))note('error',f,'route_reference',`便 ${r.trip_id} の路線がありません`);if(!serviceIds.has(r.service_id))note('error',f,'service_reference',`便 ${r.trip_id} の運行日がありません`)}
    for(const r of t.stops??[])if(!r.stop_lat||!r.stop_lon||!Number.isFinite(Number(r.stop_lat))||!Number.isFinite(Number(r.stop_lon))||Math.abs(Number(r.stop_lat))>90||Math.abs(Number(r.stop_lon))>180)note('error',f,'coordinate',`停留所 ${r.stop_id} の緯度経度が不正です`);
    const calls=new Map();for(const r of t.stop_times??[]){if(!ids.trips.has(r.trip_id)||!ids.stops.has(r.stop_id))note('error',f,'stop_reference',`時刻表の便・停留所IDが不一致 ${r.trip_id} / ${r.stop_id}`);if(!/^\d+$/.test(r.stop_sequence??''))note('error',f,'sequence',`停車順が不正 ${r.trip_id}`);if(!calls.has(r.trip_id))calls.set(r.trip_id,[]);calls.get(r.trip_id).push(r)}
    let untimed=0,conditional=0;for(const [trip,rows]of calls){rows.sort((a,b)=>Number(a.stop_sequence)-Number(b.stop_sequence));let last=-1;const seq=new Set();for(const r of rows){if(seq.has(r.stop_sequence))note('error',f,'sequence_duplicate',`便 ${trip} の停車順が重複`);seq.add(r.stop_sequence);const a=seconds(r.arrival_time),d=seconds(r.departure_time);if(a===null||d===null){untimed++;continue}if(a<last||d<a)note('error',f,'time_order',`便 ${trip} の時刻が逆転（${r.stop_sequence}）`);last=d;if(['2','3'].includes(r.pickup_type)||['2','3'].includes(r.drop_off_type))conditional++}}
    if(untimed)note('warning',f,'untimed',`${untimed}行が未時刻・不正時刻。該当便は時刻表分析から除外します`);
    if(conditional)note('warning',f,'conditional',`${conditional}行に予約等が必要。通常乗降の到達分析から除外します`);
    for(const [name,rows]of Object.entries(t))if(name!=='stop_times')for(const row of rows){
      for(const col of ['trip_id','from_trip_id','to_trip_id'])if(row[col]&&!ids.trips.has(row[col]))note('error',f,'ancillary_trip_reference',`${name}: ${col}=${row[col]} の参照先がありません`);
      for(const col of ['from_stop_id','to_stop_id','parent_station'])if(row[col]&&!ids.stops.has(row[col]))note('error',f,'ancillary_stop_reference',`${name}: ${col}=${row[col]} の参照先がありません`);
      if(name==='translations'&&['trips','stop_times'].includes(row.table_name)&&row.record_id&&!ids.trips.has(row.record_id))note('error',f,'translation_reference','翻訳の便参照先がありません');
    }
    for(const r of t.frequencies??[])if(seconds(r.start_time)===null||seconds(r.end_time)===null||seconds(r.start_time)>=seconds(r.end_time)||!Number.isFinite(Number(r.headway_secs))||Number(r.headway_secs)<=0)note('error',f,'frequency_value','頻度運行の時間帯・間隔が不正です');
    if(t.frequencies?.some(r=>r.exact_times!=='1'))note('warning',f,'headway','時刻未確定の頻度運行は到達分析から除外します');
    if((t.transfers??[]).some(r=>['4','5'].includes(r.transfer_type)))note('warning',f,'inseat','直通継続・再乗車の特殊乗換は未評価です');
    if((t.agency??[]).some(r=>r.agency_timezone!=='Asia/Tokyo'))note('error',f,'timezone','この分析画面はAsia/Tokyoの運行を対象にしています');
    if(t.locations||t.location_groups||t.booking_rules)note('warning',f,'flex','GTFS Flex・予約型運行は未対応です');
  }
  return {errors,warnings,issues,partialCheck:true};
}
export function scenarioFeeds(base,edits=[]){
  const feeds=structuredClone(base);
  for(const edit of edits){
    const f=feeds.find(x=>x.id===edit.feed);if(!f)throw Error('変更対象のデータがありません');const t=f.tables;
    if(edit.type==='new_stop'){if(!edit.values.stop_id||t.stops.some(r=>r.stop_id===edit.values.stop_id))throw Error('追加停留所のIDが重複しています');t.stops.push({...edit.values,location_type:'0'});continue}
    if(edit.type==='stop'){const row=t.stops.find(r=>r.stop_id===edit.id);if(!row)throw Error('停留所がありません');Object.assign(row,edit.values);continue}
    if(edit.type==='route'){const row=t.routes.find(r=>r.route_id===edit.id);if(!row)throw Error('路線がありません');Object.assign(row,edit.values);continue}
    const trip=t.trips.find(r=>r.trip_id===edit.trip);if(!trip)throw Error('変更対象の便がありません');
    if(edit.type==='duplicate'&&(t.transfers??[]).some(r=>r.from_trip_id===edit.trip||r.to_trip_id===edit.trip))throw Error('便固有の乗換ルールを持つ便は自動複製できません。元GTFSで新しい便の乗換条件を定義してください');
    if(edit.type==='cancel'){t.trips=t.trips.filter(r=>r.trip_id!==edit.trip);for(const name of Object.keys(t))if(name!=='trips')t[name]=t[name].filter(r=>r.trip_id!==edit.trip&&r.from_trip_id!==edit.trip&&r.to_trip_id!==edit.trip&&!(name==='translations'&&['trips','stop_times'].includes(r.table_name)&&r.record_id===edit.trip));continue}
    if(edit.type==='shift'||edit.type==='duplicate'){
      if((t.frequencies??[]).some(r=>r.trip_id===edit.trip))throw Error('頻度運行便の時刻変更は原GTFS側で行ってください');
      const rows=t.stop_times.filter(r=>r.trip_id===edit.trip),delta=Number(edit.minutes)*60;if(!Number.isFinite(delta))throw Error('変更分が不正です');
      const newRows=rows.map(r=>{const out={...r};for(const field of ['arrival_time','departure_time']){const n=seconds(r[field]);if(n===null||n+delta<0||n+delta>=168*3600)throw Error('変更後の時刻が範囲外です');out[field]=clock(n+delta)}return out});
      if(edit.type==='shift'){for(const [i,r]of rows.entries())Object.assign(r,newRows[i])}else{if(!edit.newId||t.trips.some(r=>r.trip_id===edit.newId))throw Error('追加便IDが空または重複しています');t.trips.push({...trip,trip_id:edit.newId,block_id:''});t.stop_times.push(...newRows.map(r=>({...r,trip_id:edit.newId})))}continue;
    }
    if(edit.type==='stop_time'){const row=t.stop_times.find(r=>r.trip_id===edit.trip&&String(r.stop_sequence)===String(edit.sequence));if(!row)throw Error('停車順がありません');Object.assign(row,edit.values);continue}
    if(edit.type==='calls'){trip.shape_id='';if(t.translations)t.translations=t.translations.filter(r=>!(r.table_name==='stop_times'&&r.record_id===edit.trip));if(!edit.rows?.length)throw Error('停車列が空です');t.stop_times=t.stop_times.filter(r=>r.trip_id!==edit.trip).concat(edit.rows.map((r,i)=>({...r,trip_id:edit.trip,stop_sequence:String(i+1),shape_dist_traveled:''})));continue}
    throw Error('未対応の変更種別です');
  }return feeds;
}
export function exportFeed(feed){const entries={};for(const [name,rows]of Object.entries(feed.tables))if(rows.length)entries[name+'.txt']=csvText(rows);for(const [name,bytes]of Object.entries(feed.emptyFiles??{}))if(!entries[name])entries[name]=new Uint8Array(bytes);for(const [name,bytes]of Object.entries(feed.extra??{}))entries[name]=new Uint8Array(bytes);return zip(entries)}
export function distance(a,b){const rad=Math.PI/180,x=(b.lat-a.lat)*rad,y=(b.lon-a.lon)*rad,s=Math.sin(x/2)**2+Math.cos(a.lat*rad)*Math.cos(b.lat*rad)*Math.sin(y/2)**2;return 6371000*2*Math.atan2(Math.sqrt(s),Math.sqrt(Math.max(0,1-s)))}
export function buildNetwork(feeds,date,{includeOvernight=true}={}){
  date=dateKey(date);const stops={},routes={},trips=[],transfers=[];let excluded=0;
  for(const f of feeds){
    const t=f.tables,calls=new Map();for(const r of t.stops??[])stops[key(f.id,r.stop_id)]={key:key(f.id,r.stop_id),id:r.stop_id,feed:f.id,name:r.stop_name,lat:Number(r.stop_lat),lon:Number(r.stop_lon),parent:r.parent_station?key(f.id,r.parent_station):''};
    for(const r of t.routes??[])routes[key(f.id,r.route_id)]={...r,key:key(f.id,r.route_id),feed:f.id,name:r.route_long_name||r.route_short_name||r.route_id};
    for(const r of t.stop_times??[]){if(!calls.has(r.trip_id))calls.set(r.trip_id,[]);calls.get(r.trip_id).push(r)}for(const list of calls.values())list.sort((a,b)=>Number(a.stop_sequence)-Number(b.stop_sequence));
    for(const r of t.transfers??[])transfers.push({...r,feed:f.id});
    let prior=0;if(includeOvernight)for(const r of t.stop_times??[])prior=Math.max(prior,Math.floor((seconds(r.departure_time)??0)/86400));
    for(let offset=-Math.min(prior,6);offset<=0;offset++){
      const serviceDate=addDate(date,offset),active=activeServices(t,serviceDate);
      for(const raw of t.trips??[]){if(!active.has(raw.service_id))continue;const rr=calls.get(raw.trip_id)??[];if(rr.length<2||rr.some(r=>seconds(r.arrival_time)===null||seconds(r.departure_time)===null)){excluded++;continue}
        const frequency=(t.frequencies??[]).filter(r=>r.trip_id===raw.trip_id),offsets=[];
        if(frequency.length){for(const fr of frequency){if(fr.exact_times!=='1'){excluded++;continue}const start=seconds(fr.start_time),end=seconds(fr.end_time),step=Number(fr.headway_secs);if(start===null||end===null||step<=0){excluded++;continue}for(let n=start;n<end&&offsets.length<10000;n+=step)offsets.push(n-seconds(rr[0].departure_time))}}else offsets.push(0);
        for(const shift of offsets){const parsed=rr.map(r=>({...r,stopKey:key(f.id,r.stop_id),arrival:seconds(r.arrival_time)+offset*86400+shift,departure:seconds(r.departure_time)+offset*86400+shift,pickup:!r.pickup_type||r.pickup_type==='0',dropoff:!r.drop_off_type||r.drop_off_type==='0'}));if(parsed.at(-1).arrival<0)continue;
          trips.push({key:key(f.id,raw.trip_id)+'@'+serviceDate+'@'+shift,baseKey:key(f.id,raw.trip_id),id:raw.trip_id,feed:f.id,route:key(f.id,raw.route_id),routeId:raw.route_id,direction:raw.direction_id??'',serviceDate,calls:parsed,headsign:raw.trip_headsign,shape:raw.shape_id,offset,shift})}
      }
    }
  }return {date,stops,routes,trips,transfers,excluded};
}
export function supply(network,{route='all',direction='all',start=0,end=172800}={}){
  const eligible=network.trips.filter(t=>t.offset===0&&(route==='all'||t.route===route)&&(direction==='all'||t.direction===direction)),selected=eligible.filter(t=>t.calls[0].departure>=start&&t.calls[0].departure<end),byStop={},hours=Array.from({length:48},()=>0);let vehicleHours=0;
  for(const t of selected){vehicleHours+=(t.calls.at(-1).arrival-t.calls[0].departure)/3600;const hour=Math.floor(t.calls[0].departure/3600);if(hour<hours.length)hours[hour]++}
  for(const t of eligible)for(const c of t.calls)if(c.pickup&&c.departure>=start&&c.departure<end){const s=byStop[c.stopKey]??{departures:0,first:Infinity,last:-Infinity};s.departures++;s.first=Math.min(s.first,c.departure);s.last=Math.max(s.last,c.departure);byStop[c.stopKey]=s}
  return {trips:selected.length,stops:Object.keys(byStop).length,vehicleHours,byStop,hours,selected};
}
function transferRule(network,label,to,trip){
  const from=network.stops[label.fromStop],dest=network.stops[to];if(!from||!dest)return null;let best=null,score=-1;
  for(const r of network.transfers){if(r.feed!==from.feed||r.feed!==dest.feed)continue;if(r.from_stop_id&&![from.id,network.stops[from.parent]?.id].includes(r.from_stop_id))continue;if(r.to_stop_id&&![dest.id,network.stops[dest.parent]?.id].includes(r.to_stop_id))continue;
    if(r.from_trip_id&&r.from_trip_id!==label.lastTripId||r.to_trip_id&&r.to_trip_id!==trip.id||r.from_route_id&&r.from_route_id!==label.lastRouteId||r.to_route_id&&r.to_route_id!==trip.routeId)continue;
    const n=(r.from_trip_id&&r.to_trip_id?6:r.from_trip_id&&r.to_route_id||r.to_trip_id&&r.from_route_id?5:r.from_trip_id||r.to_trip_id?4:r.from_route_id&&r.to_route_id?3:r.from_route_id||r.to_route_id?2:1)*10+(r.from_stop_id===from.id?1:0)+(r.to_stop_id===dest.id?1:0);if(n>score){best=r;score=n}}
  return best;
}
function walkingNeighbors(network,maxWalk,speed){
  const stops=Object.values(network.stops),grid=new Map(),step=.01,out=new Map();for(const s of stops){const k=Math.floor(s.lat/step)+','+Math.floor(s.lon/step);if(!grid.has(k))grid.set(k,[]);grid.get(k).push(s)}
  const radius=Math.ceil(maxWalk/800)+1;
  for(const s of stops){const nearby=[];const x=Math.floor(s.lat/step),y=Math.floor(s.lon/step);for(let i=-radius;i<=radius;i++)for(let j=-radius;j<=radius;j++)for(const d of grid.get((x+i)+','+(y+j))??[]){const m=distance(s,d);if(m<=maxWalk)nearby.push({stop:d.key,seconds:m/(speed*1000/3600),meters:m})}out.set(s.key,nearby)}return out;
}
export function reachability(network,{origin,departure=32400,budget=3600,maxTransfers=1,maxWalk=250,walkSpeed=4,transferMinutes=3}={}){
  if(!network.stops[origin])throw Error('起点を選んでください');if(![departure,budget,maxTransfers,maxWalk,walkSpeed,transferMinutes].every(Number.isFinite)||budget<0||maxWalk<0||maxWalk>1000||walkSpeed<=0||maxTransfers<0||maxTransfers>3||transferMinutes<0)throw Error('到達条件が不正です');
  const limit=departure+budget,neighbors=walkingNeighbors(network,maxWalk,walkSpeed),best={},rounds=[],initial=new Map();
  for(const w of neighbors.get(origin)??[]){const label={arrival:departure+w.seconds,rideArrival:departure,walkSeconds:w.seconds,fromStop:origin,lastTripId:null,lastTripKey:null,lastRouteId:null,round:0,path:[]};if(label.arrival<=limit){initial.set(w.stop,[label]);best[w.stop]={arrival:label.arrival,transfers:0,path:[],walkOnly:true}}}
  let previous=initial;
  for(let round=1;round<=maxTransfers+1;round++){
    const arrivals=new Map();
    for(const trip of network.trips){let onboard=null;
      for(let i=0;i<trip.calls.length;i++){
        const call=trip.calls[i];if(call.arrival>limit)break;
        if(onboard&&call.dropoff){const path=[...onboard.path,{trip:trip.baseKey,tripId:trip.id,route:trip.route,from:onboard.boardStop,to:call.stopKey,departure:onboard.boardTime,arrival:call.arrival}];const label={arrival:call.arrival,rideArrival:call.arrival,walkSeconds:0,fromStop:call.stopKey,lastTripId:trip.id,lastTripKey:trip.key,lastRouteId:trip.routeId,round,path};
          if(!arrivals.has(call.stopKey))arrivals.set(call.stopKey,[]);const list=arrivals.get(call.stopKey),same=list.findIndex(x=>x.lastTripKey===trip.key);if(same<0)list.push(label);else if(list[same].arrival>label.arrival)list[same]=label;
          if(!best[call.stopKey]||best[call.stopKey].arrival>call.arrival)best[call.stopKey]={arrival:call.arrival,transfers:round-1,path,walkOnly:false};
        }
        if(!onboard&&call.pickup&&call.departure>=departure&&call.departure<=limit){
          for(const label of previous.get(call.stopKey)??[]){if(label.lastTripKey===trip.key&&round>1)continue;const rule=label.lastTripId?transferRule(network,label,call.stopKey,trip):null;if(rule?.transfer_type==='3'||['4','5'].includes(rule?.transfer_type))continue;
            const ready=label.lastTripId?(rule?.transfer_type==='2'?Math.max(label.arrival,label.rideArrival+Number(rule.min_transfer_time||0)):label.arrival+(rule?.transfer_type==='1'?0:transferMinutes*60)):label.arrival;
            if(ready<=call.departure){onboard={...label,boardStop:call.stopKey,boardTime:call.departure};break}
          }
        }
      }
    }
    rounds.push(arrivals.size);const next=new Map();
    for(const [stop,labels]of arrivals)for(const label of labels)for(const w of neighbors.get(stop)??[]){const moved={...label,arrival:label.arrival+w.seconds,walkSeconds:w.seconds};if(moved.arrival>limit)continue;if(!next.has(w.stop))next.set(w.stop,[]);next.get(w.stop).push(moved);if(!best[w.stop]||best[w.stop].arrival>moved.arrival)best[w.stop]={arrival:moved.arrival,transfers:round-1,path:label.path,walkOnly:false}}
    previous=next;if(!previous.size)break;
  }return {best,rounds,options:{origin,departure,budget,maxTransfers,maxWalk,walkSpeed,transferMinutes},excludedTrips:network.excluded};
}
export function compareReach(before,after,stops){
  const keys=new Set([...Object.keys(before.best),...Object.keys(after.best)]),rows=[];
  for(const k of keys){const a=before.best[k],b=after.best[k];rows.push({stop:k,name:stops[k]?.name??k,before:a?Math.round((a.arrival-before.options.departure)/60*10)/10:null,after:b?Math.round((b.arrival-after.options.departure)/60*10)/10:null,change:!a?'新たに到達':!b?'到達不可':b.arrival<a.arrival-.1?'短縮':b.arrival>a.arrival+.1?'延長':'変化なし'})}return rows;
}
