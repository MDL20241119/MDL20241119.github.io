export const VERSION='oita-atlas-2.0.0';
export const PURPOSES={hospital:'病院・通院',shopping:'買物',school:'学校・学び',library:'図書館・交流',civic:'公共施設',other:'その他'};
export const GAP_TYPES=[['space','空間空白','近くに乗れる交通がない'],['time','時間空白','必要な時間に間に合わない'],['destination','目的地空白','必要な用事の場所へ届かない'],['return','帰宅空白','用事の後に帰れない'],['use','利用空白','身体・予約・費用の条件が合わない']];
export const STATES={candidate:{label:'時刻表上の往復候補あり',color:'#13745e'},not_found:{label:'収録条件では見つからない',color:'#c64551'},unknown:{label:'データ不足・判定保留',color:'#75808c'},conditional:{label:'往復候補あり・利用条件を確認',color:'#b77a12'}};
export const normalizeCategory=c=>c==='clinic'?'hospital':Object.hasOwn(PURPOSES,c)?c:'other';
export function classify(r){
 if(!r)return 'unknown';
 if(r.outbound&&r.inbound)return 'candidate';
 const e=r.dataEvidence;
 if(!e?.feeds?.length||r.searchIncomplete||e.excluded>0||e.feeds.some(f=>f.coverage!=='known'))return 'unknown';
 return 'not_found';
}
export function diagnosis(r){
 if(classify(r)==='unknown')return [];
 const tags=[];const text=(r?.reasons??[]).join(' ');
 if(/行きの経路/.test(text))tags.push('time','destination');
 if(/時間帯|滞在/.test(text))tags.push('time');
 if(/帰りの経路/.test(text))tags.push('return');
 if(/利用条件|予算|受入れ|本人|車いす/.test(text))tags.push('use');
 return [...new Set(tags)];
}
export function populationSummary(cells,results){
 let knownPopulation=0,candidatePopulation=0,notFoundPopulation=0,unknownPopulation=0,missingPopulationCells=0;const counts={candidate:0,not_found:0,unknown:0};
 for(const c of cells){const p=c.properties??c,r=results instanceof Map?results.get(p.id):results[p.id],s=r?.state??classify(r);counts[s]++;if(p.population2020===null||p.population2020===undefined||!Number.isFinite(p.population2020)){missingPopulationCells++;continue;}const n=Math.max(0,p.population2020);knownPopulation+=n;if(s==='candidate')candidatePopulation+=n;else if(s==='not_found')notFoundPopulation+=n;else unknownPopulation+=n;}
 return {knownPopulation,candidatePopulation,notFoundPopulation,unknownPopulation,missingPopulationCells,counts,rate:knownPopulation?candidatePopulation/knownPopulation*100:null,unknownRate:knownPopulation?unknownPopulation/knownPopulation*100:null};
}
export function comparePopulation(cells,before,after){let gained=0,lost=0,uncertain=0;for(const c of cells){const p=c.properties??c,n=p.population2020;if(!Number.isFinite(n))continue;const a=before[p.id]?.state??classify(before[p.id]),b=after[p.id]?.state??classify(after[p.id]);if(a==='unknown'||b==='unknown'){uncertain+=n;continue;}if(a!=='candidate'&&b==='candidate')gained+=n;if(a==='candidate'&&b!=='candidate')lost+=n;}return {gained,lost,uncertain,net:gained-lost};}
export function policyCost({cost,gained}){return Number.isFinite(cost)&&cost>=0&&Number.isFinite(gained)&&gained>0?cost/gained:null;}
export function opportunitySummary(rows,limit){const candidates=rows.filter(r=>Number.isFinite(r.minutes)&&r.minutes<=limit).length;const unknown=rows.filter(r=>r.unknown&&(!Number.isFinite(r.minutes)||r.minutes>limit)).length;return {candidates,unknown,label:!candidates&&unknown?'判定保留':String(candidates)};}
export function localDay(now=new Date()){return new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'}).format(now);}
export function timeBand(seconds){const h=Math.floor(seconds/3600);return h<6?'00–06':h<9?'06–09':h<12?'09–12':h<15?'12–15':h<18?'15–18':'18–24';}
// No coordinates, destination names, exact dates, device IDs or free text enter this record.
export function demandRecord({cityCode,category,hour,state,kind='search',month=localDay().slice(0,7)}){if(!/^44\d{3}$/.test(cityCode))throw Error('大分県内の出発エリアを選んでください');if(!['candidate','not_found','unknown'].includes(state)||!['search','reported_unmet','reported_met'].includes(kind))throw Error('記録の区分が不正です');return {cityCode,category:normalizeCategory(category),hour:timeBand(hour),state,kind,month:String(month).slice(0,7)};}
export function aggregateDemand(records,{threshold=1}={}){const groups=new Map();for(const r of records){const k=[r.cityCode,r.category,r.hour,r.state,r.kind,r.month].join('|');if(!groups.has(k))groups.set(k,{...r,count:0});groups.get(k).count++;}return [...groups.values()].filter(r=>r.count>=threshold).sort((a,b)=>b.count-a.count);}
export function pointInGeometry(point,geometry){const ring=(xy)=>{let inside=false;for(let i=0,j=xy.length-1;i<xy.length;j=i++){const [xi,yi]=xy[i],[xj,yj]=xy[j];if((yi>point.lat)!==(yj>point.lat)&&point.lon<(xj-xi)*(point.lat-yi)/(yj-yi)+xi)inside=!inside;}return inside;};const polygon=rs=>ring(rs[0])&&!rs.slice(1).some(ring);return geometry.type==='Polygon'?polygon(geometry.coordinates):geometry.type==='MultiPolygon'&&geometry.coordinates.some(polygon);}
export function cityAt(point,features){return features.find(f=>pointInGeometry(point,f.geometry))?.properties??null;}
export function validPoint(p){return p&&Number.isFinite(p.lat)&&Number.isFinite(p.lon)&&p.lat>=32.5&&p.lat<=34&&p.lon>=130.5&&p.lon<=132.3;}
