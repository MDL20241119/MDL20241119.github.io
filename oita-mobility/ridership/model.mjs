import {parseCSV, csvText} from '../lab/io.mjs';
import {validDate} from '../lab/gtfs.mjs';

export const headers = {
  boarding:['date','agency_id','route_id','trip_id','stop_id','stop_sequence','count_geton','count_getoff'],
  od:['date','agency_id','route_id','stopid_geton','stopid_getoff','count'],
};
const text=(row,k)=>String(row[k]??'').trim();
const integer=(v)=>/^\d+$/.test(v)&&Number.isSafeInteger(Number(v))&&Number(v)<=1000000000;
const key=(...parts)=>JSON.stringify(parts);
function date(v){
  if(!/^\d{8}$|^\d{4}-\d{2}-\d{2}$/.test(v)||!validDate(v))return '';
  return v.replaceAll('-','');
}
export function readAggregate(csv){
  const data=parseCSV(csv);if(!data.length)throw Error('データ行がありません。');
  if(data.length>100000)throw Error('10万行を超えています。期間を分けてください。');
  const cols=Object.keys(data[0]);
  const kind=Object.keys(headers).find(k=>cols.length===headers[k].length&&headers[k].every(x=>cols.includes(x)));
  if(!kind)throw Error('LINKS Mobilysの乗降集計またはOD集計の列構成を確認してください。個人別の乗降記録は受け付けません。');
  const unique=new Set(), rows=[];
  for(const [i,row] of data.entries()){
    const e=()=>{throw Error((i+2)+'行目：必須項目・日付・整数を確認してください。');};
    const vals=Object.fromEntries(headers[kind].map(k=>[k,text(row,k)]));
    vals.date=date(vals.date);
    if(!vals.date||Object.values(vals).some(v=>!v||v.length>250||/[\u0000-\u001f]/.test(v)))e();
    const fields=kind==='boarding'?['stop_sequence','count_geton','count_getoff']:['count'];
    if(fields.some(k=>!integer(vals[k])))e();
    for(const k of fields)vals[k]=Number(vals[k]);
    const ids=kind==='boarding'?['date','agency_id','route_id','trip_id','stop_id','stop_sequence']:['date','agency_id','route_id','stopid_geton','stopid_getoff'];
    const id=key(...ids.map(k=>vals[k]));
    if(unique.has(id))throw Error((i+2)+'行目：同一条件の集計行が重複しています。二重計上を避けるため処理を止めました。');
    unique.add(id);rows.push(vals);
  }
  return {kind,rows};
}
export function summarize(input,{agency='',route='',start='',end='',query='',trip=''}={}){
  const rows=input.rows.filter(r=>(!agency||r.agency_id===agency)&&(!route||r.route_id===route)&&(!trip||r.trip_id===trip)&&(!start||r.date>=start)&&(!end||r.date<=end));
  const grouped=new Map(),trips=new Map();
  for(const r of rows){
    const id=input.kind==='boarding'?key(r.agency_id,r.stop_id):key(r.agency_id,r.stopid_geton,r.stopid_getoff);
    const value=grouped.get(id)??(input.kind==='boarding'?{agency_id:r.agency_id,stop_id:r.stop_id,boardings:0,alightings:0}:{agency_id:r.agency_id,origin:r.stopid_geton,destination:r.stopid_getoff,trips:0});
    if(input.kind==='boarding'){
      value.boardings+=r.count_geton;value.alightings+=r.count_getoff;
      const tid=key(r.date,r.agency_id,r.route_id,r.trip_id);if(!trips.has(tid))trips.set(tid,[]);trips.get(tid).push(r);
    }else value.trips+=r.count;
    grouped.set(id,value);
  }
  const items=[...grouped.values()].filter(v=>!query||Object.values(v).join(' ').toLowerCase().includes(query.toLowerCase()));
  const metric=r=>input.kind==='boarding'?r.boardings+r.alightings:r.trips;
  items.sort((a,b)=>metric(b)-metric(a)||JSON.stringify(a).localeCompare(JSON.stringify(b),'ja'));
  const totals=input.kind==='boarding'?[items.reduce((s,r)=>s+r.boardings,0),items.reduce((s,r)=>s+r.alightings,0)]:[items.reduce((s,r)=>s+r.trips,0)];
  const tripRows=trip&&trips.size===1?[...trips.values()][0].slice().sort((a,b)=>a.stop_sequence-b.stop_sequence):[];
  let onboard=0;const detail=tripRows.map(r=>{onboard+=r.count_geton-r.count_getoff;return {...r,net:onboard};});
  return {items,totals,rows:rows.length,tripCount:trips.size,detail};
}
export function downloadRows(rows,kind){
  // Keep displayed and exported data in the browser; this guard alone is
  // not anonymization. Do not export small positive cells.
  const allowed=rows.filter(r=>(kind==='od'?[r.trips]:[r.boardings,r.alightings]).every(v=>v===0||v>=5));
  return {count:allowed.length, csv:csvText(allowed,{safe:true,headers:kind==='boarding'?['agency_id','stop_id','boardings','alightings']:['agency_id','origin','destination','trips']})};
}
