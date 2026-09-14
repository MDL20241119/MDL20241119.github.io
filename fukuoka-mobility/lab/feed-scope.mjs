// Keep complete journeys on selected routes, including their out-of-prefecture calls.
// The downloaded ZIP and its hash remain unchanged; selection is recorded in the catalog.
export function scopeFeed(feed, source) {
  if (!source.analysisRouteIds) return feed;
  const t=feed.tables, routes=new Set(source.analysisRouteIds);
  if (!routes.size || [...routes].some(id=>!t.routes.some(r=>r.route_id===id))) throw Error('分析対象路線の指定が原典と一致しません');
  const trips=new Set(t.trips.filter(r=>routes.has(r.route_id)).map(r=>r.trip_id));
  const calls=t.stop_times.filter(r=>trips.has(r.trip_id)), stops=new Set(calls.map(r=>r.stop_id));
  // Retain parent stations as references, even if no trip calls at the parent itself.
  let changed=true;
  while(changed){changed=false;for(const r of t.stops)if(stops.has(r.stop_id)&&r.parent_station&&!stops.has(r.parent_station)){stops.add(r.parent_station);changed=true;}}
  const shapes=new Set(t.trips.filter(r=>trips.has(r.trip_id)).map(r=>r.shape_id));
  const services=new Set(t.trips.filter(r=>trips.has(r.trip_id)).map(r=>r.service_id));
  const agencies=new Set(t.routes.filter(r=>routes.has(r.route_id)).map(r=>r.agency_id));
  const byTable={routes, trips, stops, shapes, calendar:services, agency:agencies};
  const ids={routes:'route_id', trips:'trip_id', stops:'stop_id', shapes:'shape_id', calendar:'service_id', agency:'agency_id'};
  const tables={};
  for(const [name, rows] of Object.entries(t)) tables[name]=rows.filter(r=>{
    if(name==='agency'&&t.agency.length===1)return true;
    if(byTable[name]&&!byTable[name].has(r[ids[name]]))return false;
    for(const k of ['trip_id','from_trip_id','to_trip_id'])if(r[k]&&!trips.has(r[k]))return false;
    for(const k of ['route_id','from_route_id','to_route_id'])if(r[k]&&!routes.has(r[k]))return false;
    for(const k of ['stop_id','from_stop_id','to_stop_id','parent_station'])if(r[k]&&!stops.has(r[k]))return false;
    if(r.service_id&&!services.has(r.service_id))return false;
    if(name==='translations'&&r.record_id){const table=r.table_name==='stop_times'?'trips':r.table_name;if(byTable[table]&&!byTable[table].has(r.record_id))return false;}
    return true;
  });
  return {...feed,tables,analysisScope:source.analysisScope,analysisRouteIds:[...routes]};
}
