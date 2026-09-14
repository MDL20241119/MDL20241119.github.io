import {scopeFeed} from '../lab/feed-scope.mjs';
import {loadWalkingGraph} from '../access/walking.mjs';
import {importGTFS} from '../lab/gtfs.mjs';
import {GAP_VERSION,validateProfile,prepareGapNetwork,measureSupply,activityCriterion,finalizeCell} from './engine.mjs?v=20260915-2';
import {unselectedTransportReferences} from '../assets/transport-coverage.mjs';
const feeds=new Map();let cache=null,cacheKey='',referenceStops=null,transportInventory=null;
self.onmessage=async({data})=>{
  const {id,profile,files,cells,facilities,activityBounds}=data;
  try{
    validateProfile(profile);const list=[];
    for(const f of files){if(!feeds.has(f.file)){self.postMessage({id,progress:'交通データを準備：'+f.name,percent:0});const r=await fetch('../data/gtfs/'+encodeURIComponent(f.file));if(!r.ok)throw Error(f.name+'を読み込めません');const v=await importGTFS(await r.arrayBuffer(),f.name,f.file);v.source=f.source;if(v.hash!==f.sha256)throw Error(f.name+'のデータ照合に失敗しました');feeds.set(f.file,scopeFeed(v,f));}list.push(feeds.get(f.file));}
    if(!referenceStops){const r=await fetch('data/reference-stops.json');if(!r.ok)throw Error('時刻表未確認の停留所・駅資料を取得できません');referenceStops=(await r.json()).stops;}
    if(!transportInventory){const r=await fetch('../data/map-data.json?v=20260915-2');if(!r.ok)throw Error('選択外の交通データの位置資料を取得できません');transportInventory=await r.json();}
    const k=profile.date+'|'+files.map(f=>f.file).sort().join('|');if(k!==cacheKey){const unselected=unselectedTransportReferences(transportInventory,files);cache=prepareGapNetwork(list,profile.date,[...referenceStops,...unselected.stops]);cache.unselectedFeeds=unselected.feeds;cache.unselectedStopCount=unselected.stops.length;self.postMessage({id,progress:'OSMの道路を準備しています',percent:0});cache.network.walkingGraph=await loadWalkingGraph();cacheKey=k;}
    self.postMessage({id,health:cache.health,excluded:cache.network.excluded,unselectedFeeds:cache.unselectedFeeds,unselectedStopCount:cache.unselectedStopCount,engine:GAP_VERSION});
    let batch=[],activityCount=0;
    for(let i=0;i<cells.length;i++){
      const c=cells[i],point={lat:c.lat,lon:c.lon,name:c.id};let result=measureSupply(cache,point,profile);
      const inBounds=!activityBounds||point.lat>=activityBounds.south&&point.lat<=activityBounds.north&&point.lon>=activityBounds.west&&point.lon<=activityBounds.east;
      if(profile.activityOn&&inBounds){result=finalizeCell(result,activityCriterion(cache,point,facilities,profile),profile);activityCount++;}
      batch.push({id:c.id,...result});
      if(batch.length>=(profile.activityOn?1:30)||i===cells.length-1){self.postMessage({id,batch,progress:(i+1)+' / '+cells.length+'区域を確認',percent:Math.round((i+1)/cells.length*100),activityCount});batch=[];}
    }
    self.postMessage({id,done:true,activityCount,total:cells.length});
  }catch(e){self.postMessage({id,error:e.message??String(e)});}
};
