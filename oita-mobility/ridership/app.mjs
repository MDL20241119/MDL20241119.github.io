import {readAggregate,summarize,downloadRows} from './model.mjs';
import {download} from '../lab/io.mjs';
const $=id=>document.getElementById(id), els=['from','to','agency','route','trip','query'];
const demo={
boarding:'date,agency_id,route_id,trip_id,stop_id,stop_sequence,count_geton,count_getoff\n20261127,DEMO,架空A,01,架空中央,1,24,0\n20261127,DEMO,架空A,01,架空病院,2,3,17\n20261127,DEMO,架空A,01,架空終点,3,0,10\n20261128,DEMO,架空B,02,架空中央,1,16,0\n20261128,DEMO,架空B,02,架空終点,2,0,16',
od:'date,agency_id,route_id,stopid_geton,stopid_getoff,count\n2026-11-27,DEMO,架空A,架空中央,架空病院,17\n2026-11-27,DEMO,架空A,架空中央,架空終点,7\n2026-11-27,DEMO,架空A,架空病院,架空終点,3\n2026-11-28,DEMO,架空B,架空中央,架空終点,16'
};
let input=null,isDemo=false,request=0,shown=[];
const fmt=v=>typeof v==='number'?v.toLocaleString('ja-JP'):v;
const date=v=>v.replaceAll('-','');
const make=(tag,text)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e;};
const options=(id,values)=>{$(id).replaceChildren(new Option('すべて',''),...values.map(x=>new Option(x,x)));};
function issue(text=''){const err=$('err');err.textContent=text;err.hidden=!text;}
function clear(){request++;input=null;isDemo=false;shown=[];$('file').value='';$('analysis').hidden=true;$('status').textContent='ファイルを選ぶか、架空データで試してください。';issue();}
function render(){
 if(!input)return; issue();$('trip-detail').hidden=true;const start=date($('from').value),end=date($('to').value);
 if(start&&end&&start>end){issue('終了日は開始日以降にしてください。');$('metrics').replaceChildren();$('tbody').replaceChildren();$('bars').replaceChildren();$('scope').textContent='日付の条件が不正です。';shown=[];$('export').disabled=true;return;}
 const result=summarize(input,{start,end,agency:$('agency').value,route:$('route').value,trip:$('trip').value,query:$('query').value.trim()});
 const board=input.kind==='boarding';shown=result.items;
 const cells=board?['agency_id','stop_id','boardings','alightings']:['agency_id','origin','destination','trips'];
 const labels=board?['事業者','停留所ID','乗車','降車']:['事業者','乗車停留所ID','降車停留所ID','移動回数'];
 $('scope').textContent=(isDemo?'架空データ・実績ではありません。':'読み込んだファイルの集計。')+' 対象 '+fmt(result.rows)+'行、表示条件に合う集計 '+fmt(shown.length)+'件。';
 $('metrics').replaceChildren(...result.totals.map((val,i)=>{const e=make('div',board?['乗車回数','降車回数'][i]:'移動回数');e.append(make('strong',fmt(val)));return e;}));
 $('caption').textContent='集計件数の多い順（画面は最大100行）';
 const header=make('tr');for(const k of labels){const h=make('th',k);h.scope='col';header.append(h);}$('thead').replaceChildren(header);
 $('tbody').replaceChildren(...shown.slice(0,100).map(item=>{const tr=make('tr');for(const k of cells)tr.append(make('td',fmt(item[k])));return tr;}));
 const measure=v=>board?v.boardings+v.alightings:v.trips;
 const top=Math.max(1,...shown.slice(0,6).map(measure));
 $('bars').replaceChildren(...shown.slice(0,6).map(row=>{const p=make('p');const label=board?row.stop_id:row.origin+' → '+row.destination;const meter=make('meter');meter.max=top;meter.value=measure(row);meter.setAttribute('aria-label',label);p.append(make('span',label),meter,make('b',fmt(measure(row))));return p;}));
 $('trip-detail').hidden=!result.detail.length;
 $('trip-rows').replaceChildren(...result.detail.slice(0,100).map(row=>{const tr=make('tr');for(const k of ['stop_sequence','stop_id','count_geton','count_getoff','net'])tr.append(make('td',fmt(row[k])));return tr;}));
 $('export').disabled=!shown.length;
}
function load(csv,demoMode){
  input=readAggregate(csv);isDemo=demoMode;shown=[];const values=input.rows,keys=k=>[...new Set(values.map(r=>r[k]))].sort();
  options('agency',keys('agency_id'));options('route',keys('route_id'));options('trip',input.kind==='boarding'?keys('trip_id'):[]);$('trip-field').hidden=input.kind!=='boarding';for(const k of ['from','to','query'])$(k).value='';
  $('analysis').hidden=false;$('status').textContent=(isDemo?'架空データ：':'読み込み完了：')+(input.kind==='boarding'?'乗降集計':'停留所間OD')+' '+fmt(values.length)+'行。';render();
}
$('file').addEventListener('change',async()=>{const f=$('file').files?.[0];if(!f)return;const id=++request;input=null;shown=[];$('analysis').hidden=true;$('status').textContent='読み込み中';issue();try{if(f.size>20*1024*1024)throw Error('20MBを超えています。ファイルを分けてください。');const csv=new TextDecoder('utf-8',{fatal:true}).decode(await f.arrayBuffer());if(request===id)load(csv,false);}catch(e){if(request===id){$('status').textContent='読み込みできませんでした。';issue(e instanceof TypeError?'UTF-8のCSVを用意してください。':e.message);}}});
for(const k of ['boarding','od'])$('demo-'+k).addEventListener('click',()=>{clear();load(demo[k],true);});
$('reset').addEventListener('click',clear);for(const k of els)$(k).addEventListener(k==='query'?'input':'change',render);
$('export').addEventListener('click',()=>{if(!input||!shown.length)return;const r=downloadRows(shown,input.kind);if(!r.count){issue('共有に適さない少数件のみのため、出力できません。');return;}download((isDemo?'sample-':'')+'atlas-'+input.kind+'.csv','\uFEFF'+r.csv,'text/csv;charset=utf-8');});
