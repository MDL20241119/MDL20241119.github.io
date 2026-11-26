// The 9/8 visualization stays a historical snapshot. Live searches use the
// current feed's stop coordinates and hash for automatic feed selection.
export async function currentTransport(transport,catalog,fetcher=fetch){
  const feedIndex=transport.feeds.findIndex(f=>f.id==='9c3c2dbb');
  const feed=catalog.find(f=>f.name==='大分バス');
  if(feedIndex<0||!feed)throw Error('大分バスの出典を確認できません');
  if(feed.sha256===transport.feeds[feedIndex].sha256)return transport;
  const r=await fetcher('data/gtfs/oitabus-stops-20261001.json');
  if(!r.ok)throw Error('大分バスの停留所データを読み込めません');
  const index=await r.json();
  if(index.feedId!==transport.feeds[feedIndex].id||index.sha256!==feed.sha256||index.stops.length!==feed.stopCount)throw Error('大分バスの停留所と時刻表の版が一致しません');
  return {...transport,
    feeds:transport.feeds.map((f,i)=>i===feedIndex?{...f,sha256:feed.sha256,validFrom:feed.validFrom,validTo:feed.validTo}:f),
    stops:[...transport.stops.filter(s=>s.feedIndex!==feedIndex),...index.stops.map(s=>({...s,feedIndex}))]};
}
export function currentFeedFiles(files,catalog){
  const previous='440001_gtfs01_oitabus__9c3c2dbb.zip';
  const current=catalog.find(f=>f.name==='大分バス')?.file;
  return [...new Set(files.map(x=>current&&x===previous?current:x))];
}
