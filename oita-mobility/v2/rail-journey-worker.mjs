import {importGTFS,validDate} from '../lab/gtfs.mjs';
import {validateOptions} from '../access/engine.mjs';
import {judgeOitaRoundTrip,prepareOitaRoundTrips} from '../gaps/rail-roundtrip.mjs';

export async function runRailJourney(d, send, get=fetch){
  if(!validDate(d.date)||!d.home||!d.facilities?.[0])throw Error('日付・出発地・目的地をご確認ください。');
  validateOptions(d.options);
  if(!d.railFile?.size||d.railFile.size>20*1024*1024)throw Error('利用可能な鉄道GTFS ZIP（20MB以下）を指定してください。');
  if(!Array.isArray(d.files)||d.files.length<1||d.files.length>16)throw Error('使うバスの時刻表を選んでください。');
  send({progress:'JRとバスの時刻表を確認しています…'});
  const rail=await importGTFS(await d.railFile.arrayBuffer(),'手元の鉄道データ','rail-local');
  rail.dataUse='authorized'; // User confirms permission before opening the file.
  const bus=[];
  for(const f of d.files){
    const r=await get(new URL('../data/gtfs/'+encodeURIComponent(f.file),import.meta.url));
    if(!r.ok)throw Error('公開バス時刻表を取得できません。');
    const parsed=await importGTFS(await r.arrayBuffer(),f.name,f.file);
    if(parsed.hash!==f.sha256)throw Error('公開バス時刻表の照合に失敗しました。');
    bus.push(parsed);
  }
  // A manually supplied file does not establish coverage of all 3 lines or all operators.
  const ctx=prepareOitaRoundTrips({busFeeds:bus,railFeeds:[rail],date:d.date});
  if(!ctx.railHealth[0]?.usable){
    return {status:'rail_unavailable',reason:ctx.railHealth[0]?.coverage==='known'?'format':'date'};
  }
  return judgeOitaRoundTrip(ctx,d.home,d.facilities[0],{cityCode:'44201',date:d.date},d.options);
}
if(typeof self!=='undefined')self.onmessage=async({data:d})=>{
  const send=payload=>self.postMessage({id:d.id,...payload});
  try{send({done:true,verdict:await runRailJourney(d,send)});}
  catch{send({error:'JR＋バスの判定を完了できません。GTFS ZIP、日付、バス時刻表をご確認ください。'});}
};
