// Independently checked service presence by hour; no timetable rows, exact minutes, train IDs or destination data.
export const CHECK_DATE='2026-11-28';
const official='https://www.jrkyushu-timetable.jp/cgi-bin/jr-k_time/tt_dep.cgi?c=';
const stations=[
 ['大分','28742'],
 ['大在','28745'],
 ['賀来','28751',13],
 ['幸崎','28759'],
 ['坂ノ市','28761'],
 ['敷戸','28764'],
 ['高城','28770'],
 ['滝尾','28771'],
 ['竹中','28772'],
 ['鶴崎','28776'],
 ['中判田','28782'],
 ['西大分','28784'],
 ['古国府','28793'],
 ['豊後国分','28798',13],
 ['牧','28807'],
 ['南大分','28809'],
 ['大分大学前','29381']
];
const checks=new Map(stations.map(([name,code,noServiceHour])=>[name,{code,noServiceHour}]));
export const CHECKED_CITY_STATIONS=Object.freeze(stations.map(([name])=>name));
export const CITY_STATIONS=Object.freeze(['西大分','牧','高城','鶴崎','大在','坂ノ市','幸崎','古国府','南大分','賀来','豊後国分','滝尾','敷戸','大分大学前','中判田','竹中']);
export const NEAR_STATIONS=Object.freeze(['東別府','向之原','佐志生','犬飼','豊後竹田']);
export function stationAvailability(date,station,window){
 if(date!==CHECK_DATE||!window||!checks.has(station))return 'unknown';
 if(!/^\d{2}:00$/.test(window.start)||!/^\d{2}:00$/.test(window.end))return 'unknown';
 const first=Number(window.start.slice(0,2)),end=Number(window.end.slice(0,2));
 if(first<6||end>22||end<=first)return 'unknown';
 return end-first===1&&checks.get(station).noServiceHour===first?'none':'yes';
}
export function stationCheck(date,station,window){
 return stationAvailability(date,station,window)==='yes'?{date,station,from:window.start,to:window.end,source:official+checks.get(station).code}:null;
}
export function roundtripCheck({date,station,depart,activityFrom,activityTo,stay,deadline}){
 if(date!==CHECK_DATE||!/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(depart??'')||!/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(deadline??'')||!/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(activityFrom??'')||!/^(?:[01]\d|2[0-3]):[0-5]\d$/.test(activityTo??'')||!Number.isFinite(stay)||stay<=0)return 'unverified';
 // Compare user restrictions to the checked conditions conservatively.
 const isCity=CITY_STATIONS.includes(station),isNearby=NEAR_STATIONS.includes(station);
 if(!isCity&&!isNearby)return 'unverified';
 if(depart>(isCity?'08:50':'08:40')||deadline<'17:30'||activityFrom>'11:00'||activityTo<'11:05'||stay>(station==='豊後竹田'?50:170))return 'unverified';
 return 'candidate';
}
