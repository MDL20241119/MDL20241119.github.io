// Starting points for local discussion, not national or municipal designations.
export const TIME_BANDS=Object.freeze({
 morning:Object.freeze({label:'朝',start:'06:00',end:'09:00'}),
 daytime:Object.freeze({label:'昼',start:'09:00',end:'16:00'}),
 evening:Object.freeze({label:'夕方',start:'16:00',end:'19:00'}),
 night:Object.freeze({label:'夜',start:'19:00',end:'22:00'}),
});
export function timeBandKey(p){
 if(!p?.distanceOn||!p.frequencyOn||p.activityOn||p.combine!=='any'||p.distanceM!==p.frequencyRadius||p.minimumTrips!==1)return null;
 return Object.keys(TIME_BANDS).find(key=>TIME_BANDS[key].start===p.serviceStart&&TIME_BANDS[key].end===p.serviceEnd)??null;
}
export function dayBandProfile(p,key,distance){
 if(!Object.hasOwn(TIME_BANDS,key)||![250,500,750].includes(distance))throw Error('時間帯または徒歩圏の条件を確認してください');
 const b=TIME_BANDS[key];
 return {...p,distanceOn:true,distanceM:distance,frequencyOn:true,frequencyRadius:distance,minimumTrips:1,serviceStart:b.start,serviceEnd:b.end,activityOn:false,combine:'any'};
}
export function timeGapState(record){
 const d=record?.criteria.find(c=>c.id==='distance')?.state;
 const t=record?.criteria.find(c=>c.id==='frequency')?.state;
 if(d==='fail')return 'far';
 if(d!=='pass')return 'unknown';
 return t==='fail'?'noTrips':t==='pass'?'pass':'unknown';
}
