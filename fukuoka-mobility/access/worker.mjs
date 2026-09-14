import {scopeFeed} from '../lab/feed-scope.mjs';
import {partitionAnalysisFeeds} from '../assets/transport-coverage.mjs';
import {importGTFS} from '../lab/gtfs.mjs';
import {prepareAccess,evaluateActivity} from './engine.mjs';
import {loadWalkingGraph} from './walking.mjs';
const feeds=new Map();let network=null,networkKey='';
self.onmessage=async({data})=>{
  const {id,files,date,home,facilities,options,conditions}=data;
  try{
    const list=[];for(const file of files){if(!feeds.has(file.file)){self.postMessage({id,progress:file.name+'の時刻表を読み込んでいます'});const r=await fetch('../data/gtfs/'+encodeURIComponent(file.file));if(!r.ok)throw Error('時刻表を読み込めません');const f=await importGTFS(await r.arrayBuffer(),file.name,file.file);if(f.hash!==file.sha256)throw Error(file.name+'のデータ照合に失敗しました');f.source=file.source;feeds.set(file.file,scopeFeed(f,file));}list.push(feeds.get(file.file));}
    const {usable,health}=partitionAnalysisFeeds(list,date);
    const cache=date+'|'+files.map(f=>f.file).sort().join('|');if(cache!==networkKey){network=prepareAccess(usable,date);self.postMessage({id,progress:'OSMの道路を準備しています'});network.walkingGraph=await loadWalkingGraph();networkKey=cache;}
    const dataEvidence={feeds:health,excluded:network.excluded,walking:network.walkingGraph.meta};
    const omittedNotes=health.filter(f=>!f.usedInCalculation).map(f=>f.name+'：'+(f.analysisSnapshot?'通常ダイヤの比較対象日外':f.coverage==='outside'?'対象日は時刻表の有効期間外':'時刻表の有効期間を確認できない')+'ため計算対象外');
    const results=[];for(let i=0;i<facilities.length;i++){self.postMessage({id,progress:(i+1)+' / '+facilities.length+'件：'+facilities[i].name+'の往復を確認'});const result=evaluateActivity(network,home,facilities[i],options,conditions[facilities[i].id]??{});result.unknowns=[...new Set([...result.unknowns,...omittedNotes])];if(omittedNotes.length&&result.status==='feasible')result.status='conditional';results.push({...result,dataEvidence});}
    self.postMessage({id,results,sources:usable.map(f=>({name:f.name,hash:f.hash,source:f.source})),health,excluded:network.excluded});
  }catch(e){self.postMessage({id,error:e.message});}
};
