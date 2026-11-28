// Query indexes correspond to the exact GTFS bytes in the current catalogue.
const LEGACY_OITABUS='440001_gtfs01_oitabus__9c3c2dbb.zip';
function currentRecords(catalog){
  return catalog.flatMap(f=>f.currentStopIndex?[f]:f.name==='大分バス'&&f.stopCount?[{...f,supersedes:LEGACY_OITABUS,snapshotId:'9c3c2dbb',currentStopIndex:'oitabus-stops-20261001.json'}]:[]);
}
export async function currentTransport(transport,catalog,fetcher=fetch){
  const updated=await Promise.all(currentRecords(catalog).map(async feed=>{
    const feedIndex=transport.feeds.findIndex(f=>f.id===feed.snapshotId);
    if(feedIndex<0)throw Error(feed.name+'の停留所出典を確認できません');
    if(feed.sha256===transport.feeds[feedIndex].sha256)return null;
    const r=await fetcher('data/gtfs/'+feed.currentStopIndex);
    if(!r.ok)throw Error(feed.name+'の停留所を読み込めません');
    const index=await r.json();
    if(index.feedId!==feed.snapshotId||index.sha256!==feed.sha256||index.stops.length!==feed.stopCount)throw Error(feed.name+'の停留所と時刻表の版が一致しません');
    return {feed,feedIndex,stops:index.stops.map(s=>({...s,feedIndex})),shapes:(index.shapes??[]).map(s=>({...s,feedIndex}))};
  }));
  const replacements=new Map(updated.filter(Boolean).map(v=>[v.feedIndex,v]));
  return {...transport,feeds:transport.feeds.map((f,i)=>{
    const p=replacements.get(i)?.feed;
    return p?{...f,sha256:p.sha256,validFrom:p.validFrom,validTo:p.validTo}:f;
  }),shapes:[...(transport.shapes??[]).filter(s=>!replacements.has(s.feedIndex)),...Array.from(replacements.values()).flatMap(v=>v.shapes)],stops:[...transport.stops.filter(s=>!replacements.has(s.feedIndex)),...Array.from(replacements.values()).flatMap(v=>v.stops)]};
}
export function currentFeedFiles(files,catalog){
  const aliases=new Map(currentRecords(catalog).map(f=>[f.supersedes,f.file]));
  return [...new Set(files.map(x=>aliases.get(x)??x))];
}
