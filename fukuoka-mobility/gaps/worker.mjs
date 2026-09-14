import {importGTFS} from '../lab/gtfs.mjs';
import {GAP_VERSION,validateProfile,prepareGapNetwork,measureSupply,activityCriterion,finalizeCell} from './engine.mjs';
const feeds=new Map();let cache=null,cacheKey='';
self.onmessage=async({data})=>{
  const {id,profile,files,cells,facilities,activityBounds}=data;
  try{
    validateProfile(profile);const list=[];
    for(const f of files){if(!feeds.has(f.file)){self.postMessage({id,progress:'交通データを準備：'+f.name,percent:0});const r=await fetch('../data/gtfs/'+encodeURIComponent(f.file));if(!r.ok)throw Error(f.name+'を読み込めません');const v=await importGTFS(await r.arrayBuffer(),f.name,f.file);v.source=f.source;if(v.hash!==f.sha256)throw Error(f.name+'のデータ照合に失敗しました');feeds.set(f.file,v);}list.push(feeds.get(f.file));}
    const k=profile.date+'|'+files.map(f=>f.file).sort().join('|');if(k!==cacheKey){cache=prepareGapNetwork(list,profile.date);cacheKey=k;}
    self.postMessage({id,health:cache.health,excluded:cache.network.excluded,engine:GAP_VERSION});
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
