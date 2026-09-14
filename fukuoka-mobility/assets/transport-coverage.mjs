import {feedCoverage} from '../gaps/engine.mjs?v=20260915-2';

// The feed calendar cannot override a publisher's declared validity period.
export function partitionAnalysisFeeds(feeds,date){
  const usable=[],omitted=[],health=[];
  for(const feed of feeds){
    const coverage=feedCoverage(feed,date),usedInCalculation=coverage==='known';
    health.push({name:feed.name,id:feed.id,hash:feed.hash,source:feed.source,coverage,usedInCalculation,analysisSnapshot:feed.tables.feed_info?.[0]?.feed_version?.startsWith('analysis-snapshot-')??false});
    (usedInCalculation?usable:omitted).push(feed);
  }
  return {usable,omitted,health};
}

// Deselecting a timetable limits the analysis; it does not remove that service
// from the real world. Keep its known positions as evidence of incomplete data.
export function unselectedTransportReferences(transport,selectedSources){
  if(!Array.isArray(transport?.feeds)||!Array.isArray(transport?.stops))throw Error('交通データの収録範囲を確認できません');
  const hashes=new Set(selectedSources.map(f=>f.sha256).filter(Boolean));
  const omitted=new Map(transport.feeds.map((feed,index)=>[index,feed]).filter(([,feed])=>!hashes.has(feed.sha256)));
  const stops=[];
  for(const stop of transport.stops){
    if(!transport.feeds[stop.feedIndex])throw Error('乗車地点の時刻表出典を確認できません');
    const feed=omitted.get(stop.feedIndex);if(!feed)continue;
    stops.push({id:'unselected-gtfs-'+feed.id+'::'+stop.id,name:stop.name,lat:stop.lat,lon:stop.lon,operator:feed.name,mode:'public_transport',coverage:'unselected',source:feed.downloadUrl??feed.sourceUrl,sourceHash:feed.sha256,validFrom:feed.validFrom??null,validTo:feed.validTo??null});
  }
  return {stops,feeds:[...omitted.values()].map(feed=>({id:feed.id,name:feed.name,hash:feed.sha256,source:feed.downloadUrl??feed.sourceUrl,coverage:'unselected',usedInCalculation:false}))};
}
