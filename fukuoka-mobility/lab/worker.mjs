import {scenarioFeeds,validateFeeds,buildNetwork,supply,reachability,compareReach} from './gtfs.mjs';
import {feedCoverage} from '../gaps/engine.mjs?v=20260915-2';
let feeds=[],edits=[],date='',baseline=null,changed=null;
self.onmessage=async({data})=>{
  const {id,type,payload}=data;
  try{
    if(type==='prepare'){
      feeds=payload.feeds;edits=payload.edits;date=payload.date;
      const unverified=feeds.filter(f=>f.tables.feed_info?.[0]?.feed_version?.startsWith('analysis-snapshot-')&&feedCoverage(f,date)!=='known');
      if(unverified.length)throw Error('分析日が時刻表の収録対象日ではありません：'+unverified.map(f=>f.name).join('・')+'。運行なしとは判定しません。収録対象日を選んでください。');
      const scenario=scenarioFeeds(feeds,edits),quality=validateFeeds(scenario);
      if(quality.errors)throw Error(`変更後データに${quality.errors}件のエラーがあります。${quality.issues.find(r=>r.level==='error')?.message??''}`);
      baseline=buildNetwork(feeds,date);changed=buildNetwork(scenario,date);const clean=n=>{const s=supply(n,payload.filter);delete s.selected;return s};
      self.postMessage({id,result:{before:clean(baseline),after:clean(changed),stops:changed.stops,routes:changed.routes,excluded:changed.excluded,quality}});
    }else if(type==='reach'){
      if(!baseline||!changed)throw Error('先に運行データを計算してください');const before=reachability(baseline,payload),after=reachability(changed,payload);self.postMessage({id,result:{before,after,comparison:compareReach(before,after,{...baseline.stops,...changed.stops})}});
    }else throw Error('未知の分析要求です');
  }catch(e){self.postMessage({id,error:e.message})}
};
