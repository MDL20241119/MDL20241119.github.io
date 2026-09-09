import {scenarioFeeds,validateFeeds,buildNetwork,supply,reachability,compareReach} from './gtfs.mjs';
let feeds=[],edits=[],date='',baseline=null,changed=null;
self.onmessage=async({data})=>{
  const {id,type,payload}=data;
  try{
    if(type==='prepare'){
      feeds=payload.feeds;edits=payload.edits;date=payload.date;const scenario=scenarioFeeds(feeds,edits),quality=validateFeeds(scenario);
      if(quality.errors)throw Error(`変更後データに${quality.errors}件のエラーがあります。${quality.issues.find(r=>r.level==='error')?.message??''}`);
      baseline=buildNetwork(feeds,date);changed=buildNetwork(scenario,date);const clean=n=>{const s=supply(n,payload.filter);delete s.selected;return s};
      self.postMessage({id,result:{before:clean(baseline),after:clean(changed),stops:changed.stops,routes:changed.routes,excluded:changed.excluded,quality}});
    }else if(type==='reach'){
      if(!baseline||!changed)throw Error('先に運行データを計算してください');const before=reachability(baseline,payload),after=reachability(changed,payload);self.postMessage({id,result:{before,after,comparison:compareReach(before,after,{...baseline.stops,...changed.stops})}});
    }else throw Error('未知の分析要求です');
  }catch(e){self.postMessage({id,error:e.message})}
};
