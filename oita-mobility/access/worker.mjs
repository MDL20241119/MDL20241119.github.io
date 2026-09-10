import {feedCoverage} from '../gaps/engine.mjs';
import {importGTFS} from '../lab/gtfs.mjs';
import {prepareAccess,evaluateActivity} from './engine.mjs';
const feeds=new Map();let network=null,networkKey='';
self.onmessage=async({data})=>{
  const {id,files,date,home,facilities,options,conditions}=data;
  try{
    const list=[];for(const file of files){if(!feeds.has(file.file)){self.postMessage({id,progress:file.name+'の時刻表を読み込んでいます'});const r=await fetch('../data/gtfs/'+encodeURIComponent(file.file));if(!r.ok)throw Error('時刻表を読み込めません');const f=await importGTFS(await r.arrayBuffer(),file.name,file.file);if(f.hash!==file.sha256)throw Error(file.name+'のデータ照合に失敗しました');f.source=file.source;feeds.set(file.file,f);}list.push(feeds.get(file.file));}
    const cache=date+'|'+files.map(f=>f.file).sort().join('|');if(cache!==networkKey){network=prepareAccess(list,date);networkKey=cache;}
    const dataEvidence={feeds:list.map(f=>({name:f.name,hash:f.hash,coverage:feedCoverage(f,date)})),excluded:network.excluded};
    const results=[];for(let i=0;i<facilities.length;i++){self.postMessage({id,progress:(i+1)+' / '+facilities.length+'件：'+facilities[i].name+'の往復を確認'});results.push({...evaluateActivity(network,home,facilities[i],options,conditions[facilities[i].id]??{}),dataEvidence});}
    self.postMessage({id,results,sources:list.map(f=>({name:f.name,hash:f.hash,source:f.source})),excluded:network.excluded});
  }catch(e){self.postMessage({id,error:e.message});}
};
