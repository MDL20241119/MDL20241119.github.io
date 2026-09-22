import {buildNetwork,distance,key,seconds,validDate} from '../lab/gtfs.mjs';

export const ACCESS_VERSION='activity-access-1.0';
const unique=a=>[...new Set(a)];
export function prepareAccess(feeds,date){
  if(!validDate(date))throw Error('分析日を確認してください');
  const n=buildNetwork(feeds,date);n.rawStops={};n.rawTrips={};
  for(const f of feeds){for(const s of f.tables.stops)n.rawStops[key(f.id,s.stop_id)]=s;for(const t of f.tables.trips)n.rawTrips[key(f.id,t.trip_id)]=t;}
  n.walkCache=new Map();return n;
}
export function validateOptions(o){
  for(const k of ['departure','deadline','activityFrom','activityTo','dwell','legMinutes','maxWalk','totalWalk','walkSpeed','walkFactor','maxTransfers'])if(!Number.isFinite(o[k]))throw Error('時刻・滞在時間・徒歩条件を確認してください');
  if(o.departure<0||o.deadline>86400||o.departure>=o.deadline||o.activityFrom>o.activityTo||o.activityTo>o.deadline||o.dwell<1||o.dwell>720||o.legMinutes<1||o.legMinutes>240||o.maxWalk<0||o.maxWalk>2000||o.totalWalk<0||o.totalWalk>12000||o.walkSpeed<1||o.walkSpeed>8||o.walkFactor<1||o.walkFactor>3||o.maxTransfers<0||o.maxTransfers>2)throw Error('条件の範囲を確認してください。出発・帰宅は同じ日の範囲で指定します。');
}
function accessibility(n,stop){const r=n.rawStops[stop]??{};let v=r.wheelchair_boarding;if(!v||v==='0')v=n.rawStops[n.stops[stop]?.parent]?.wheelchair_boarding;return v==='1'?'yes':v==='2'?'no':'unknown';}
function transfer(n,l,to,t){let best=null,score=-1;const from=n.stops[l.fromStop],dest=n.stops[to];if(!from||!dest)return null;
  for(const r of n.transfers){if(r.feed!==from.feed||r.feed!==dest.feed)continue;if(r.from_stop_id&&![from.id,n.stops[from.parent]?.id].includes(r.from_stop_id)||r.to_stop_id&&![dest.id,n.stops[dest.parent]?.id].includes(r.to_stop_id))continue;
    if(r.from_trip_id&&r.from_trip_id!==l.lastTripId||r.to_trip_id&&r.to_trip_id!==t.id||r.from_route_id&&r.from_route_id!==l.lastRouteId||r.to_route_id&&r.to_route_id!==t.routeId)continue;
    const s=(r.from_trip_id&&r.to_trip_id?6:r.from_trip_id&&r.to_route_id||r.to_trip_id&&r.from_route_id?5:r.from_trip_id||r.to_trip_id?4:r.from_route_id&&r.to_route_id?3:r.from_route_id||r.to_route_id?2:1)*10+(r.from_stop_id===from.id?1:0)+(r.to_stop_id===dest.id?1:0);if(s>score){best=r;score=s;}}
  return best;
}
function walkLinks(n,o){const cacheKey=o.maxWalk+':'+o.walkFactor;if(n.walkCache.has(cacheKey))return n.walkCache.get(cacheKey);
  const grid=new Map(),step=.01;for(const s of Object.values(n.stops)){const k=Math.floor(s.lat/step)+','+Math.floor(s.lon/step);if(!grid.has(k))grid.set(k,[]);grid.get(k).push(s);}
  const result=new Map(),radius=Math.ceil(o.maxWalk/800)+1;
  for(const s of Object.values(n.stops)){const rows=[],a=Math.floor(s.lat/step),b=Math.floor(s.lon/step);for(let x=-radius;x<=radius;x++)for(let y=-radius;y<=radius;y++)for(const d of grid.get((a+x)+','+(b+y))??[]){const meters=distance(s,d)*o.walkFactor;if(meters<=o.maxWalk+1e-6)rows.push({stop:d.key,meters});}result.set(s.key,rows);}
  if(n.walkCache.size>3)n.walkCache.clear();n.walkCache.set(cacheKey,result);return result;
}
function dominates(a,b){return a.arrival<=b.arrival+.001&&a.walk<=b.walk+.001&&a.uncertain<=b.uncertain;}
function insert(map,k,label,ctx,sameIncoming=true){
  const list=map.get(k)??[],same=x=>!sameIncoming||x.lastTripKey===label.lastTripKey&&x.fromStop===label.fromStop;
  if(list.some(x=>same(x)&&dominates(x,label)))return;
  const kept=list.filter(x=>!same(x)||!dominates(label,x));kept.push(label);
  if(kept.length>120){ctx.truncated=true;kept.sort((a,b)=>a.uncertain-b.uncertain||a.arrival-b.arrival||a.walk-b.walk);kept.length=120;}
  map.set(k,kept);
}
function walkPath(from,to,meters,start,speed){return {mode:'walk',from,to,meters,departure:start,arrival:start+meters/(speed*1000/3600)};}

// Resource labels keep shorter-walk and fewer-unknown alternatives, including incoming-trip rules.
export function pointJourneys(n,origin,destination,start,o,walkBudget=o.totalWalk){
  const limit=Math.min(start+o.legMinutes*60,o.deadline),ctx={truncated:false,unsupported:false,operations:0},all=new Map(),initial=new Map(),links=walkLinks(n,o),speed=o.walkSpeed*1000/3600;
  const direct=distance(origin,destination)*o.walkFactor;
  if(direct<=o.maxWalk+1e-6&&direct<=walkBudget&&start+direct/speed<=limit)insert(all,'destination',{arrival:start+direct/speed,walk:direct,uncertain:0,unknowns:[],path:[walkPath(origin,destination,direct,start,o.walkSpeed)],boardings:0},ctx,false);
  for(const s of Object.values(n.stops)){const meters=distance(origin,s)*o.walkFactor;if(meters>o.maxWalk+1e-6||meters>walkBudget||start+meters/speed>limit)continue;insert(initial,s.key,{arrival:start+meters/speed,walk:meters,uncertain:0,unknowns:[],path:[walkPath(origin,s,meters,start,o.walkSpeed)],lastTripId:null,lastTripKey:null,lastRouteId:null,fromStop:s.key,rideArrival:start},ctx);}
  let previous=initial;
  for(let round=1;round<=o.maxTransfers+1;round++){
    const arrivals=new Map();
    for(const t of n.trips){const wheelchair=n.rawTrips[t.baseKey]?.wheelchair_accessible;if(o.wheelchair&&wheelchair==='2')continue;let onboard=[];
      for(const c of t.calls){if(++ctx.operations>2500000){ctx.truncated=true;break;}if(c.arrival>limit)break;
        const drop=c.drop_off_type??'0',pickup=c.pickup_type??'0';
        if(onboard.length&&drop!=='1'){
          if(o.wheelchair&&accessibility(n,c.stopKey)==='no'){}else if(['2','3'].includes(drop)&&o.reservation==='no'){}else for(const board of onboard){
            const unknowns=unique([...board.unknowns,...(['2','3'].includes(drop)?['降車の事前手配']:[]),...(o.wheelchair&&accessibility(n,c.stopKey)==='unknown'?['降車場所の車いす対応']:[])]);
            const leg={mode:'bus',trip:t.baseKey,tripKey:t.key,boardSequence:board.boardSequence,alightSequence:c.stop_sequence,route:t.route,routeName:n.routes[t.route]?.name??t.route,from:n.stops[board.boardStop],to:n.stops[c.stopKey],departure:board.boardTime,arrival:c.arrival,wait:board.boardTime-board.arrival};
            insert(arrivals,c.stopKey,{arrival:c.arrival,rideArrival:c.arrival,walk:board.walk,uncertain:unknowns.length,unknowns,path:[...board.path,leg],lastTripKey:t.key,lastTripId:t.id,lastRouteId:t.routeId,fromStop:c.stopKey,boardings:round},ctx);
          }
        }
        if(pickup==='1'||c.departure<start||c.departure>limit||o.wheelchair&&accessibility(n,c.stopKey)==='no'||['2','3'].includes(pickup)&&o.reservation==='no')continue;
        for(const l of previous.get(c.stopKey)??[]){if(l.lastTripKey===t.key)continue;const rule=l.lastTripId?transfer(n,l,c.stopKey,t):null;if(rule?.transfer_type==='3')continue;if(['4','5'].includes(rule?.transfer_type)){ctx.unsupported=true;continue;}
          const ready=l.lastTripId?(rule?.transfer_type==='2'?Math.max(l.arrival,l.rideArrival+Number(rule.min_transfer_time||0)):l.arrival+(rule?.transfer_type==='1'?0:180)):l.arrival;if(ready>c.departure)continue;
          const unknowns=unique([...l.unknowns,...(['2','3'].includes(pickup)?['乗車の事前手配']:[]),...(o.wheelchair&&wheelchair!=='1'?['車両の車いす対応']:[]),...(o.wheelchair&&accessibility(n,c.stopKey)==='unknown'?['乗車場所の車いす対応']:[])]);
          const candidate={...l,boardStop:c.stopKey,boardTime:c.departure,boardSequence:c.stop_sequence,unknowns,uncertain:unknowns.length};
          if(!onboard.some(b=>b.walk<=candidate.walk+.001&&b.uncertain<=candidate.uncertain))onboard=[...onboard.filter(b=>!(candidate.walk<=b.walk+.001&&candidate.uncertain<=b.uncertain)),candidate];
        }
      }
      if(ctx.truncated&&ctx.operations>2500000)break;
    }
    const next=new Map();
    for(const [stop,labels]of arrivals)for(const l of labels){
      const meters=distance(n.stops[stop],destination)*o.walkFactor;
      if(meters<=o.maxWalk+1e-6&&l.walk+meters<=walkBudget&&l.arrival+meters/speed<=limit)insert(all,'destination',{...l,arrival:l.arrival+meters/speed,walk:l.walk+meters,path:[...l.path,walkPath(n.stops[stop],destination,meters,l.arrival,o.walkSpeed)]},ctx,false);
      for(const w of links.get(stop)??[]){if(l.walk+w.meters>walkBudget||l.arrival+w.meters/speed>limit)continue;insert(next,w.stop,{...l,arrival:l.arrival+w.meters/speed,walk:l.walk+w.meters,path:w.meters?[...l.path,walkPath(n.stops[stop],n.stops[w.stop],w.meters,l.arrival,o.walkSpeed)]:l.path},ctx);}
    }
    previous=next;if(!previous.size||ctx.operations>2500000)break;
  }
  return {journeys:(all.get('destination')??[]).sort((a,b)=>a.uncertain-b.uncertain||a.arrival-b.arrival||a.walk-b.walk),...ctx,excluded:n.excluded};
}

export function evaluateActivity(n,home,facility,o,conditions={}){
  validateOptions(o);const unknowns=[],reasons=[];
  const base={facilityId:facility.id,facilityName:facility.name,conditions,options:o,home,facility,status:'unknown',reasons,unknowns};
  if(conditions.acceptance==='no')return {...base,status:'not_met',reasons:['この用事の受入れ条件を満たさない（入力値）']};
  if(o.wheelchair&&conditions.entry==='no')return {...base,status:'not_met',reasons:['施設入口の車いす条件を満たさない（入力値）']};
  const opening=conditions.open?seconds(conditions.open+':00'):null,closing=conditions.close?seconds(conditions.close+':00'):null;
  if(opening!==null&&closing!==null&&opening>=closing)throw Error('施設の開始・終了時刻を確認してください');
  const departureSearch=pointJourneys(n,home,facility,o.departure,o);let incomplete=departureSearch.truncated||departureSearch.unsupported,activityPossible=false,best=null;
  let tested=0;for(const out of departureSearch.journeys){if(++tested>25){incomplete=true;break;}
    const earliest=Math.max(out.arrival,o.activityFrom,opening??0),latest=Math.min(o.activityTo,(closing??86400)-o.dwell*60,o.deadline-o.dwell*60);
    if(earliest>latest)continue;activityPossible=true;
    const begins=new Set([earliest,latest]);
    for(const t of n.trips)for(const c of t.calls){if(c.pickup_type==='1')continue;const meters=distance(facility,n.stops[c.stopKey])*o.walkFactor;if(meters>o.maxWalk)continue;const candidate=c.departure-meters/(o.walkSpeed*1000/3600)-o.dwell*60;if(candidate>=earliest&&candidate<=latest)begins.add(candidate);}
    let count=0;for(const begin of [...begins].sort((a,b)=>a-b)){if(++count>80){incomplete=true;break;}const end=begin+o.dwell*60;
      const backSearch=pointJourneys(n,facility,home,end,o,o.totalWalk-out.walk);incomplete||=backSearch.truncated||backSearch.unsupported;
      for(const back of backSearch.journeys){if(back.arrival>o.deadline)continue;const candidate={outbound:out,inbound:back,begin,end,homeAt:back.arrival,walk:out.walk+back.walk,uncertain:out.uncertain+back.uncertain};if(!best||candidate.uncertain<best.uncertain||candidate.uncertain===best.uncertain&&(candidate.homeAt<best.homeAt||candidate.homeAt===best.homeAt&&candidate.walk<best.walk))best=candidate;}
    }
  }
  if(!best){const reason=!departureSearch.journeys.length?'この時刻・徒歩条件で、行きの経路が見つからない':!activityPossible?'指定時間帯の用事・滞在時間が収まらない':'用事の後、指定時刻までの帰りの経路が見つからない';return {...base,reasons:[reason],searchIncomplete:incomplete,unknowns:['未収録の交通・道路条件を含めた代替手段は未確認',...(n.excluded?['算定対象外の便あり']:[]),...(incomplete?['探索の一部が未完了']:[])]};}
  unknowns.push(...best.outbound.unknowns,...best.inbound.unknowns);
  if(facility.needsCoordinateConfirmation&&!conditions.positionConfirmed)unknowns.push('目的地は公式地図の概略位置・入口位置未確認');
  if(opening===null||closing===null)unknowns.push('当日の営業時間・受付時間');
  if(conditions.acceptance!=='yes')unknowns.push('用事の受入れ・予約枠・利用資格');
  if(conditions.walking!=='yes')unknowns.push('歩道・坂・信号・入口までの実経路');
  if(o.wheelchair&&conditions.entry!=='yes')unknowns.push('施設入口の車いす対応');
  if(conditions.comfort!=='yes')unknowns.push('待ち時間・暑熱・荷物・安心の許容');
  const cost=conditions.roundCost===''||conditions.roundCost===null||conditions.roundCost===undefined?null:Number(conditions.roundCost);
  if(cost===null)unknowns.push('この往復の交通費');else if(!Number.isFinite(cost)||cost<0)throw Error('往復の交通費は0以上で入力してください');
  if(cost!==null&&o.budget!==null&&cost>o.budget)reasons.push('入力した往復費用が予算を超える（安い代替経路は未探索）');
  if(conditions.walking==='no'||conditions.comfort==='no')reasons.push('この経路の徒歩・待ち時間などを本人が利用できない（入力値）');
  return {...base,...best,status:reasons.length?'conditional':unknowns.length?'conditional':'feasible',unknowns:unique(unknowns),reasons,cost,searchIncomplete:incomplete,waitMinutes:(best.outbound.path.concat(best.inbound.path).reduce((s,l)=>s+(l.wait??0),0)+best.begin-best.outbound.arrival)/60};
}
