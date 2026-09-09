import {buildNetwork,supply,scenarioFeeds,validateFeeds,clock} from './gtfs.mjs';

// This example computes against an immutable public feed, never the user's working plan.
export function exampleComparison(feed,added=false){
  const date='2026-09-08',beforeNetwork=buildNetwork([feed],date);
  const trip=beforeNetwork.trips.filter(t=>t.offset===0&&t.calls[0].departure>=9*3600&&t.calls[0].departure<15*3600&&!feed.tables.frequencies?.some(f=>f.trip_id===t.id)&&!feed.tables.transfers?.some(r=>r.from_trip_id===t.id||r.to_trip_id===t.id)).sort((a,b)=>a.calls[0].departure-b.calls[0].departure)[0];
  if(!trip)throw Error('体験用の便を見つけられませんでした。');
  const edits=added?[{type:'duplicate',feed:feed.id,trip:trip.id,newId:trip.id+'__guided_example',minutes:30}]:[];
  const changed=scenarioFeeds([feed],edits),quality=validateFeeds(changed);
  if(quality.errors)throw Error('体験用の変更案を計算できませんでした。');
  const afterNetwork=buildNetwork(changed,date),before=supply(beforeNetwork,{route:trip.route}),after=supply(afterNetwork,{route:trip.route});
  const rows=[...new Set(trip.calls.filter(c=>c.pickup).map(c=>c.stopKey))].map(k=>({...beforeNetwork.stops[k],before:before.byStop[k]?.departures??0,after:after.byStop[k]?.departures??0}));
  return {date,trip,route:beforeNetwork.routes[trip.route].name,first:beforeNetwork.stops[trip.calls[0].stopKey].name,last:beforeNetwork.stops[trip.calls.at(-1).stopKey].name,time:clock(trip.calls[0].departure).slice(0,5),newTime:clock(trip.calls[0].departure+1800).slice(0,5),before:before.trips,after:after.trips,rows,added,feedName:feed.name};
}
