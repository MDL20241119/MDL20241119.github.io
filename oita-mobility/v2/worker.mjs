import {importGTFS,scenarioFeeds} from '../lab/gtfs.mjs';
import {prepareAccess,evaluateActivity,pointJourneys,validateOptions} from '../access/engine.mjs?v=20260922.7';
import {feedCoverage} from '../gaps/engine.mjs';
import {classify} from './model.mjs';
import {indexShapes,attachRouteGeometry} from './route-geometry.mjs';
const feeds=new Map();let network,key='';
async function load(files,date,edits,send){const list=[];for(const f of files){if(!feeds.has(f.file)){send({progress:f.name+'を準備しています'});const r=await fetch('../data/gtfs/'+encodeURIComponent(f.file));if(!r.ok)throw Error(f.name+'の時刻表を取得できません');const parsed=await importGTFS(await r.arrayBuffer(),f.name,f.file);if(parsed.hash!==f.sha256)throw Error('時刻表の照合に失敗しました');parsed.source=f.source;feeds.set(f.file,parsed);}list.push(feeds.get(f.file));}const usable=list.filter(f=>feedCoverage(f,date)==='known');const k=JSON.stringify([date,usable.map(f=>f.id).sort(),edits]);if(k!==key){network=prepareAccess(edits?.length?scenarioFeeds(usable,edits):usable,date);key=k;}return {network,evidence:{feeds:list.map(f=>({name:f.name,hash:f.hash,coverage:feedCoverage(f,date)})),excluded:network.excluded}};}
self.onmessage=async({data:d})=>{const send=r=>self.postMessage({id:d.id,...r});try{
 if(!d.files?.length)throw Error('使う時刻表を1つ以上選んでください');
 const {network:n,evidence}=await load(d.files,d.date,d.edits??[],send);
 if(d.mode==='trips'){const seen=new Set();const trips=n.trips.filter(t=>t.offset===0&&!seen.has(t.baseKey)&&seen.add(t.baseKey)).map(t=>({feed:t.feed,id:t.id,route:n.routes[t.route]?.name??'',departure:t.calls[0].departure,from:n.stops[t.calls[0].stopKey]?.name,to:n.stops[t.calls.at(-1).stopKey]?.name}));send({done:true,trips,evidence});return;}
 validateOptions(d.options);const results=[];
 const shapes=d.mode==='journey'?indexShapes([...feeds.values()]):null;
 if(d.mode==='opportunities'){
  for(let i=0;i<d.facilities.length;i++){const f=d.facilities[i],r=pointJourneys(n,d.home,f,d.options.departure,{...d.options,legMinutes:60});const best=r.journeys[0];results.push({id:f.id,name:f.name,category:f.category,minutes:best?(best.arrival-d.options.departure)/60:null,unknown:r.truncated||r.unsupported||evidence.excluded>0||evidence.feeds.some(f=>f.coverage!=='known')});if(i%5===0)send({progress:(i+1)+' / '+d.facilities.length+'施設の行きの候補を確認'});}send({done:true,results,evidence});return;
 }
 const cases=d.cases??d.facilities.map(f=>({id:f.id,home:d.home,facility:f}));
 for(let i=0;i<cases.length;i++){const c=cases[i];const result={...evaluateActivity(n,c.home,c.facility,d.options,d.conditions??{}),dataEvidence:evidence};if(shapes)attachRouteGeometry(result,n,shapes);result.state=classify(result);results.push({id:c.id,result});send({batch:[{id:c.id,result}],progress:(i+1)+' / '+cases.length+'件を確認',percent:Math.round((i+1)/cases.length*100)});}
 send({done:true,results,evidence});
}catch(e){send({error:e.message??String(e)});}};
