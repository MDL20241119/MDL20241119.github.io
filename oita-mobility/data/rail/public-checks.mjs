// Independent verification results only. No timetable rows, train IDs or exact train times.
export const CHECK_DATE='2026-11-28';
export const STATION_CHECKS=Object.freeze([8,10,16,20].map(h=>({date:CHECK_DATE,station:'中判田',from:String(h).padStart(2,'0')+':00',to:String(h+1).padStart(2,'0')+':00',source:'https://www.jrkyushu-timetable.jp/cgi-bin/jr-k_time/tt_dep.cgi?c=28782'})));
export const CITY_STATIONS=Object.freeze(['西大分','牧','高城','鶴崎','大在','坂ノ市','幸崎','古国府','南大分','賀来','豊後国分','滝尾','敷戸','大分大学前','中判田','竹中']);
export const NEAR_STATIONS=Object.freeze(['東別府','向之原','佐志生','犬飼','豊後竹田']);
export function stationCheck(date,station,window){
 if(!window)return null;
 return STATION_CHECKS.find(w=>w.date===date&&w.station===station&&window.start<=w.from&&window.end>=w.to)??null;
}
export function roundtripCheck({date,station,depart,activityFrom,activityTo,stay,deadline}){
 if(date!==CHECK_DATE||!/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(depart??'')||!/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(deadline??'')||!/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(activityFrom??'')||!/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(activityTo??'')||!Number.isFinite(stay)||stay<=0)return 'unverified';
 // Compare user restrictions to the checked conditions conservatively.
 const isCity=CITY_STATIONS.includes(station),isNearby=NEAR_STATIONS.includes(station);
 if(!isCity&&!isNearby)return 'unverified';
 if(depart>(isCity?'08:50':'08:40')||deadline<'17:30'||activityFrom>'11:00'||activityTo<'11:05'||stay>(station==='豊後竹田'?50:170))return 'unverified';
 return 'candidate';
}
