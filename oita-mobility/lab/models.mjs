import {key,activeServices,validDate,dateKey,seconds} from './gtfs.mjs';
export function num(value,{blank=false,negative=false,integer=false}={}){
  if(value===null||value===undefined||String(value).trim()===''){if(blank)return null;throw Error('必須の数値が空です')}
  const n=Number(value);if(!Number.isFinite(n)||(!negative&&n<0)||(integer&&!Number.isSafeInteger(n)))throw Error(`数値・単位が不正です：${String(value).slice(0,30)}`);return n;
}
export function analyzeRidership(rows,feeds,meta){
  const errors=[],matched=[],unmatched=[],seen=new Set(),groups=new Map();let boardings=0,alightings=0;
  if(!meta.source||!meta.from||!meta.to||!meta.scope)errors.push('出典・開始日・終了日・対象範囲を入力してください');
  if(!validDate(meta.from)||!validDate(meta.to)||dateKey(meta.from)>dateKey(meta.to))errors.push('観測期間が不正です');
  const required=['service_date','feed_id','trip_id','stop_sequence','stop_id','boardings','alightings'];
  for(const [i,r]of rows.entries()){
    try{
      for(const c of required)if(!(c in r))throw Error(`列 ${c} がありません`);
      const allowed=new Set([...required,'trip_start_time']);if(Object.keys(r).some(c=>!allowed.has(c)))throw Error('対応外の列があります。個人単位の履歴は取り込めません');
      const date=dateKey(r.service_date);if(!validDate(date)||date<dateKey(meta.from)||date>dateKey(meta.to))throw Error('観測日と対象期間が一致しません');
      const b=num(r.boardings,{integer:meta.basis!=='estimate'}),a=num(r.alightings,{integer:meta.basis!=='estimate'}),seq=String(num(r.stop_sequence,{integer:true}));
      const natural=[date,r.feed_id,r.trip_id,r.trip_start_time??'',seq].join('|');if(seen.has(natural))throw Error('同じ便・停車順の重複です');seen.add(natural);
      const feed=feeds.find(f=>f.id===r.feed_id);if(!feed)throw Error('feed_id が未取込です');
      const trip=feed.tables.trips.find(t=>t.trip_id===r.trip_id),call=feed.tables.stop_times.find(t=>t.trip_id===r.trip_id&&String(Number(t.stop_sequence))===seq);
      if(!trip||!call||call.stop_id!==r.stop_id)throw Error('GTFSの便・停車順・停留所と不一致です');if(!activeServices(feed.tables,date).has(trip.service_id))throw Error('GTFSでは観測日に運行しない便です。観測当時のGTFSを確認してください');
      const frequencies=(feed.tables.frequencies??[]).filter(x=>x.trip_id===r.trip_id);if(frequencies.length&&!r.trip_start_time)throw Error('頻度運行はtrip_start_timeが必要です');
      if(frequencies.length){const t=seconds(r.trip_start_time);if(t===null||!frequencies.some(f=>f.exact_times==='1'&&t>=seconds(f.start_time)&&t<seconds(f.end_time)&&(t-seconds(f.start_time))%Number(f.headway_secs)===0))throw Error('頻度運行の便開始時刻を特定できません')}
      const out={...r,boardings:b,alightings:a,row:i+2,stopKey:key(r.feed_id,r.stop_id),route:key(r.feed_id,trip.route_id)};matched.push(out);boardings+=b;alightings+=a;
      const group=[date,r.feed_id,r.trip_id,r.trip_start_time??''].join('|');if(!groups.has(group))groups.set(group,{key:group,feed:feed.id,trip:r.trip_id,rows:[],expected:feed.tables.stop_times.filter(t=>t.trip_id===r.trip_id).length});groups.get(group).rows.push(out);
    }catch(e){unmatched.push({...r,row:i+2,error:e.message})}
  }
  const loads=[];
  for(const group of groups.values()){
    group.rows.sort((a,b)=>Number(a.stop_sequence)-Number(b.stop_sequence));let state=meta.complete==='yes'&&meta.initialEmpty==='yes'&&group.expected===group.rows.length&&unmatched.length===0&&meta.basis!=='estimate'&&errors.length===0?'valid':'incomplete',onboard=0,peak=0;const series=[];
    for(const r of group.rows){onboard+=r.boardings-r.alightings;if(onboard<0)state='invalid';peak=Math.max(peak,onboard);series.push({...r,load:onboard})}
    if(meta.finalEmpty==='yes'&&onboard!==0&&state==='valid')state='invalid';loads.push({...group,state,peak:state==='valid'?peak:null,series:series.map(r=>({...r,load:state==='valid'?r.load:null}))});
  }
  const byStop={};for(const r of matched){byStop[r.stopKey]??={stop:r.stopKey,boardings:0,alightings:0};byStop[r.stopKey].boardings+=r.boardings;byStop[r.stopKey].alightings+=r.alightings}
  return {errors,matched,unmatched,boardings,alightings,observedTrips:groups.size,loads,byStop:Object.values(byStop),meta,complete:errors.length===0&&unmatched.length===0};
}
export function analyzeOD(rows,feeds,meta){
  const cells=[],errors=[],seen=new Set(),stopIndex=new Map();for(const f of feeds)for(const s of f.tables.stops)stopIndex.set(key(f.id,s.stop_id),s);
  for(const [i,r]of rows.entries())try{
    const allowed=['origin_feed_id','origin_stop_id','destination_feed_id','destination_stop_id','count','status'];if(Object.keys(r).some(c=>!allowed.includes(c))||allowed.some(c=>!(c in r)))throw Error('ODの列名がテンプレートと異なります');
    const origin=key(r.origin_feed_id,r.origin_stop_id),destination=key(r.destination_feed_id,r.destination_stop_id),pair=origin+'|'+destination;if(!stopIndex.has(origin)||!stopIndex.has(destination))throw Error('起点・終点のIDがGTFSにありません');if(seen.has(pair))throw Error('同じODペアが重複しています');seen.add(pair);
    if(!['observed','suppressed','missing'].includes(r.status))throw Error('statusはobserved/suppressed/missingです');const count=r.status==='observed'?num(r.count,{integer:meta.basis!=='estimate'}):null;if(r.status!=='observed'&&String(r.count).trim())throw Error('非表示・欠測セルには人数を入力しません');
    cells.push({...r,origin,destination,count,originName:stopIndex.get(origin).stop_name,destinationName:stopIndex.get(destination).stop_name});
  }catch(e){errors.push({...r,row:i+2,error:e.message})}
  if(!meta.source||!validDate(meta.from)||!validDate(meta.to)||meta.from>meta.to||!meta.scope)errors.push({error:'出典・観測期間・対象範囲を入力してください'});
  const observed=cells.filter(r=>r.status==='observed'),suppressed=cells.filter(r=>r.status==='suppressed').length;return {cells,errors,total:observed.reduce((s,r)=>s+r.count,0),observed:observed.length,suppressed,meta};
}
function linear(values,h){const n=values.length,m=(n-1)/2,mean=values.reduce((a,b)=>a+b,0)/n;let top=0,bottom=0;for(let i=0;i<n;i++){top+=(i-m)*(values[i]-mean);bottom+=(i-m)**2}return Math.max(0,mean+(bottom?top/bottom:0)*(n-1+h-m))}
function predict(values,frequency,method,h){
  const n=values.length;if(frequency==='annual')return method==='baseline'?values.at(-1):linear(values.slice(-Math.min(5,n)),h);
  const base=values[n-12+(h-1)%12];if(base===undefined)return null;
  if(method==='baseline')return base;let sum=0,count=0;for(let i=12;i<n;i++){sum+=values[i]-values[i-12];count++}return Math.max(0,base+(count?sum/count:0));
}
export function forecast(rows,frequency='annual',horizon=3){
  if(!['annual','monthly'].includes(frequency))throw Error('集計間隔が不正です');horizon=num(horizon,{integer:true});if(horizon<1||horizon>(frequency==='monthly'?12:10))throw Error('予測期間が範囲外です');
  const sorted=rows.map(r=>({period:String(r.period),value:num(r.value)})).sort((a,b)=>a.period.localeCompare(b.period)),seen=new Set();let prev=null;
  for(const r of sorted){if(seen.has(r.period))throw Error('同じ期間が重複しています');seen.add(r.period);if(!new RegExp(frequency==='annual'?'^\\d{4}$':'^\\d{4}-\\d{2}$').test(r.period))throw Error('年次はYYYY、月次はYYYY-MMで入力してください');const n=frequency==='annual'?Number(r.period):Number(r.period.slice(0,4))*12+Number(r.period.slice(5))-1;if(frequency==='monthly'&&(Number(r.period.slice(5))<1||Number(r.period.slice(5))>12))throw Error('月が不正です');if(prev!==null&&n!==prev+1)throw Error('期間が連続していません。欠測を0で埋めず、連続する期間で入力してください');prev=n}
  const values=sorted.map(r=>r.value),minimum=frequency==='annual'?3:24;if(values.length<(frequency==='annual'?2:12))throw Error('年次2期間・月次12期間以上が必要です');
  const folds=[];for(let origin=minimum;origin<values.length;origin++){const train=values.slice(0,origin);folds.push({period:sorted[origin].period,actual:values[origin],baseline:predict(train,frequency,'baseline',1),trend:predict(train,frequency,'trend',1)})}
  const score=method=>folds.length?folds.reduce((s,r)=>s+Math.abs(r.actual-r[method]),0)/folds.length:null;
  const sufficient=folds.length>=3,scores={baseline:score('baseline'),trend:score('trend')},chosen=sufficient&&scores.trend<scores.baseline?'trend':'baseline';
  const future=Array.from({length:horizon},(_,i)=>{const h=i+1,p=frequency==='annual'?String(Number(sorted.at(-1).period)+h):(()=>{const n=prev+h;return Math.floor(n/12)+'-'+String(n%12+1).padStart(2,'0')})();return {period:p,baseline:predict(values,frequency,'baseline',h),trend:values.length>=minimum?predict(values,frequency,'trend',h):null}});
  return {history:sorted,future,folds,scores,sufficient,chosen,frequency,horizon,scope:'期間・路線・定義が継続する仮定。施策の因果効果は未検証'};
}
export function demandSensitivity({baseline,f0,f1,elasticities=[.1,.4,.7],method='constant'}){
  baseline=num(baseline);f0=num(f0);f1=num(f1);elasticities=elasticities.map(e=>num(e));if(f0===0)return {available:false,reason:'現行供給が0の新規サービスは、この方法で予測できません'};
  if(f1===0)return {available:true,cancelled:true,values:elasticities.map(e=>({elasticity:e,demand:0})),low:0,high:0,reason:'当該サービスの輸送は0。必要な移動・潜在需要は未推定'};
  const values=elasticities.map(e=>({elasticity:e,demand:Math.max(0,method==='linear'?baseline*(1+e*(f1-f0)/f0):baseline*(f1/f0)**e)}));return {available:true,values,low:Math.min(...values.map(r=>r.demand)),high:Math.max(...values.map(r=>r.demand)),ratio:f1/f0,method};
}
export function economics(rows,{rate=.04,baseYear=2026,vot=36.948}={}){
  rate=num(rate);vot=num(vot);baseYear=num(baseYear,{integer:true});if(rate>1)throw Error('割引率は0〜1で入力してください');const years=new Set();let pvUser=0,pvProvider=0,pvExternal=0,pvResidual=0,pvCapital=0,pvOperating=0,pvRevenue=0;
  const cashflows=rows.map(r=>{
    const year=num(r.year,{integer:true});if(years.has(year)||year<baseYear)throw Error('年の重複・評価基準年より前の年があります');years.add(year);
    const values={};for(const c of ['q0','q1','time0','time1','fare0','fare1','opex0','opex1','capital','replacement','decommission','residual'])values[c]=num(r[c]);
    const external=r.external===''||r.external==null?null:num(r.external,{negative:true}),discount=1/(1+rate)**(year-baseYear),q=(values.q0+values.q1)/2,timeBenefit=q*(values.time0-values.time1)*vot,fareBenefit=q*(values.fare0-values.fare1),user=timeBenefit+fareBenefit,revenue=values.q1*values.fare1-values.q0*values.fare0,operating=values.opex1-values.opex0,provider=revenue-operating,capital=values.capital+values.replacement+values.decommission,benefit=user+provider+(external??0)+values.residual,cost=capital;
    pvUser+=user*discount;pvProvider+=provider*discount;pvExternal+=(external??0)*discount;pvResidual+=values.residual*discount;pvCapital+=capital*discount;pvOperating+=operating*discount;pvRevenue+=revenue*discount;
    return {year,...values,external,discount,timeBenefit,fareBenefit,userBenefit:user,providerBenefit:provider,operatorBalance0:values.q0*values.fare0-values.opex0,operatorBalance1:values.q1*values.fare1-values.opex1,incrementalRevenue:revenue,incrementalOperating:operating,benefit,cost,pvBenefit:benefit*discount,pvCost:cost*discount,npv:(benefit-cost)*discount};
  }).sort((a,b)=>a.year-b.year);
  const benefit=pvUser+pvProvider+pvExternal+pvResidual,cost=pvCapital,resourceBenefit=pvUser+pvRevenue+pvExternal+pvResidual,resourceCost=pvCapital+pvOperating;
  return {cashflows,pvBenefit:benefit,pvCost:cost,npv:benefit-cost,bc:cost>0?benefit/cost:null,resourceBC:resourceCost>0?resourceBenefit/resourceCost:null,resourceBenefit,resourceCost,pvUser,pvProvider,pvExternal,pvResidual,pvCapital,pvOperating,externalUnassessed:cashflows.some(r=>r.external===null),options:{rate,baseYear,vot}};
}
export function economicSensitivity(rows,options){
  const cases=[['基準条件',1,1,1,1,options.rate],['需要−10%',.9,1,1,1,options.rate],['需要＋10%',1.1,1,1,1,options.rate],['投資費＋10%',1,1.1,1,1,options.rate],['変更案の運行費＋10%',1,1,1.1,1,options.rate],['時間価値−20%',1,1,1,.8,options.rate],['複合下振れ',.9,1.1,1.1,.8,options.rate],['割引率1%',1,1,1,1,.01],['割引率2%',1,1,1,1,.02]];
  return cases.map(([name,q,c,o,v,rate])=>{const changed=rows.map(r=>({...r,q0:Number(r.q0)*q,q1:Number(r.q1)*q,capital:Number(r.capital)*c,replacement:Number(r.replacement)*c,decommission:Number(r.decommission)*c,opex1:Number(r.opex1)*o}));const result=economics(changed,{...options,rate,vot:options.vot*v});return {name,npv:result.npv,bc:result.bc,resourceBC:result.resourceBC}});
}
export function switchingDemand(rows,options){const at=m=>economics(rows.map(r=>({...r,q0:Number(r.q0)*m,q1:Number(r.q1)*m})),options).npv,a=at(0),slope=at(1)-a;const root=slope===0?null:-a/slope;return root!==null&&root>=0?{multiplier:root,npv:at(root)}:null}
export function generatedCashflow(p){
  const baseYear=num(p.baseYear,{integer:true}),opening=num(p.opening,{integer:true}),years=num(p.years,{integer:true});if(opening<=baseYear||years<1||years>50)throw Error('供用開始は基準年より後、評価期間は1〜50年で入力してください');const growth=num(p.growth,{negative:true})/100;if(growth<=-1||growth>1)throw Error('需要増減率が範囲外です');
  const rows=[];for(let year=baseYear;year<opening+years;year++){const active=year>=opening,factor=active?(1+growth)**(year-opening):0;rows.push({year,q0:active?num(p.q0)*factor:0,q1:active?num(p.q1)*factor:0,time0:active?num(p.time0):0,time1:active?num(p.time1):0,fare0:active?num(p.fare0):0,fare1:active?num(p.fare1):0,opex0:active?num(p.opex0)*10000:0,opex1:active?num(p.opex1)*10000:0,capital:year===baseYear?num(p.capital)*10000:0,replacement:active&&Number(p.replaceEvery)>0&&year>opening&&(year-opening)%Number(p.replaceEvery)===0?num(p.replacement)*10000:0,decommission:0,residual:year===opening+years-1?num(p.residual)*10000:0,external:active&&String(p.external).trim()!==''?num(p.external,{negative:true})*10000:''})}return rows;
}
