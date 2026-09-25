import {zipSync,strToU8,unzipSync,strFromU8} from 'fflate';
import {State,tripRecords,stops,fail} from './core';
import {inputDate} from '../model';
export type Feed=Record<string,string>;
const cell=(v:unknown)=>'"'+String(v??'').replaceAll('"','""')+'"';
const csv=(header:string[],rows:unknown[][])=>[header,...rows].map(row=>row.map(cell).join(',')).join('\r\n')+'\r\n';
function serviceTime(iso:string,date:string){const midnight=Date.parse(date+'T00:00:00+09:00');const sec=Math.floor((Date.parse(iso)-midnight)/1000);return [Math.floor(sec/3600),Math.floor(sec%3600/60),sec%60].map(n=>String(n).padStart(2,'0')).join(':');}
export function exportFeed(s:State,origin:string):Feed {
 const trips=tripRecords(s).filter(t=>t.status!=='cancelled');if(!trips.length)fail(422,'公開できる運行予定がありません。');
 const days=[...new Set(trips.map(t=>inputDate(t.start).slice(0,10)))].sort();
 // This app has allocated trips with exact stops/times. It must not invent a Flex area/window.
 return {
 'agency.txt':csv(['agency_id','agency_name','agency_url','agency_timezone','agency_lang'],[['mdl-demo','MDL 合成データ・実運行なし',origin,'Asia/Tokyo','ja']]),
 'feed_info.txt':csv(['feed_publisher_name','feed_publisher_url','feed_lang','feed_start_date','feed_end_date','feed_version'],[['MDL 検証専用',origin,'ja',days[0].replaceAll('-',''),days.at(-1)!.replaceAll('-',''),`SYNTHETIC-${s.version}`]]),
 'stops.txt':csv(['stop_id','stop_name','stop_lat','stop_lon','zone_id'],stops.map(s=>[s.id,s.name,s.lat,s.lon,'demo-zone'])),
 'routes.txt':csv(['route_id','agency_id','route_short_name','route_long_name','route_type'],[['demo-route','mdl-demo','EP','大分駅前・地域拠点（検証用）',3]]),
 'trips.txt':csv(['route_id','service_id','trip_id','trip_headsign'],trips.map(t=>['demo-route','day-'+inputDate(t.start).slice(0,10),t.id,'地域拠点'])),
 'stop_times.txt':csv(['trip_id','arrival_time','departure_time','stop_id','stop_sequence','pickup_type','drop_off_type'],trips.flatMap(t=>{const day=inputDate(t.start).slice(0,10);return [[t.id,serviceTime(t.start,day),serviceTime(t.start,day),stops[0].id,1,2,1],[t.id,serviceTime(t.end,day),serviceTime(t.end,day),stops[1].id,2,1,2]];})),
 'calendar_dates.txt':csv(['service_id','date','exception_type'],days.map(day=>['day-'+day,day.replaceAll('-',''),1])),
 'fare_attributes.txt':csv(['fare_id','price','currency_type','payment_method','transfers','agency_id'],[['demo-free',0,'JPY',0,0,'mdl-demo']]),
 'fare_rules.txt':csv(['fare_id','route_id'],[['demo-free','demo-route']]),
 'translations.txt':csv(['table_name','field_name','language','translation','record_id'],stops.map(s=>['stops','stop_name','ja-Hrkt',s.kana,s.id])),
 };
}
export function applyFlexWindows(feed:Feed,windows:{tripId:string;stopId:string;start:string;end:string;pickup:boolean}[],bookingUrl:string):Feed {
 validateFeed(feed);if(!windows.length||!/^https:\/\//.test(bookingUrl))fail(400,'運行時間帯と予約先が必要です。');const result={...feed};const rows=parseCsv(feed['stop_times.txt']);const ids=new Set(windows.map(w=>w.tripId));
 for(const w of windows){if(!rows.some(r=>r.trip_id===w.tripId&&r.stop_id===w.stopId)||!/^\d{2,}:[0-5]\d:[0-5]\d$/.test(w.start)||!/^\d{2,}:[0-5]\d:[0-5]\d$/.test(w.end)||w.start>=w.end)fail(400,'Flexの参照・時間帯が不正です。');}
 result['stop_times.txt']=csv(['trip_id','arrival_time','departure_time','stop_id','stop_sequence','pickup_type','drop_off_type','start_pickup_drop_off_window','end_pickup_drop_off_window','pickup_booking_rule_id','drop_off_booking_rule_id'],rows.map(r=>{const w=windows.find(w=>w.tripId===r.trip_id&&w.stopId===r.stop_id);if(ids.has(r.trip_id)&&!w)fail(400,'Flexの全乗降点の時間帯を設定してください。');return w?[r.trip_id,'','',r.stop_id,r.stop_sequence,w.pickup?2:1,w.pickup?1:2,w.start,w.end,w.pickup?'demo-booking':'',w.pickup?'':'demo-booking']:[r.trip_id,r.arrival_time,r.departure_time,r.stop_id,r.stop_sequence,r.pickup_type,r.drop_off_type,'','','',''];}));
 result['booking_rules.txt']=csv(['booking_rule_id','booking_type','message','booking_url'],[['demo-booking',0,'検証用。検索・空席確認・本人確認後に予約。',bookingUrl]]);return result;
}
export function zipFeed(feed:Feed){return zipSync(Object.fromEntries(Object.entries(feed).map(([name,contents])=>[name,strToU8(contents)])));}
export function parseCsv(text:string){const rows:string[][]=[];let row:string[]=[],field='',quote=false;for(let i=0;i<text.length;i++){const ch=text[i];if(ch==='"'){if(quote&&text[i+1]==='"'){field+='"';i++;}else quote=!quote;}else if(!quote&&(ch===','||ch==='\n')){row.push(field);field='';if(ch==='\n'){rows.push(row);row=[];}}else if(ch!=='\r'||quote)field+=ch;}if(quote)fail(400,'CSVの引用符が閉じられていません。');if(field||row.length){row.push(field);rows.push(row);}const header=rows.shift()??[];if(new Set(header).size!==header.length)fail(400,'CSVの列名が重複しています。');return rows.filter(r=>r.length>1).map(row=>{if(row.length!==header.length)fail(400,'CSVの列数が一致しません。');return Object.fromEntries(header.map((h,i)=>[h,row[i]]));});}
export function validateFeed(feed:Feed){const required=['agency.txt','feed_info.txt','stops.txt','routes.txt','trips.txt','stop_times.txt','calendar_dates.txt','fare_attributes.txt','fare_rules.txt','translations.txt'];for(const name of required)if(!feed[name])fail(400,`${name} が不足しています。`);const rows=Object.fromEntries(Object.entries(feed).map(([k,v])=>[k,parseCsv(v)]));const ids=(file:string,key:string)=>new Set(rows[file]?.map(r=>r[key]));const stopIds=ids('stops.txt','stop_id'),routeIds=ids('routes.txt','route_id'),tripIds=ids('trips.txt','trip_id'),serviceIds=ids('calendar_dates.txt','service_id'),fareIds=ids('fare_attributes.txt','fare_id');
 for(const [file,key]of [['stops.txt','stop_id'],['trips.txt','trip_id'],['routes.txt','route_id']])if(ids(file,key).size!==rows[file].length)fail(400,'識別子が重複しています。');
 for(const r of rows['stops.txt'])if(!r.stop_name||!Number.isFinite(Number(r.stop_lat))||!Number.isFinite(Number(r.stop_lon))||Math.abs(Number(r.stop_lat))>90||Math.abs(Number(r.stop_lon))>180)fail(400,'停留所の名前・座標を確認してください。');
 for(const t of rows['trips.txt'])if(!routeIds.has(t.route_id)||!serviceIds.has(t.service_id))fail(400,'便の路線・営業日参照が不正です。');
 for(const d of rows['calendar_dates.txt'])if(!/^\d{8}$/.test(d.date)||!['1','2'].includes(d.exception_type))fail(400,'営業日を確認してください。');
 for(const t of rows['stop_times.txt']){if(!tripIds.has(t.trip_id)||!stopIds.has(t.stop_id))fail(400,'停留所時刻の参照が不正です。');for(const field of ['arrival_time','departure_time'])if(!/^\d{2,}:[0-5]\d:[0-5]\d$/.test(t[field]))fail(400,'時刻を確認してください。24時以降も HH:MM:SS で指定します。');}
 for(const f of rows['fare_rules.txt'])if(!fareIds.has(f.fare_id)||!routeIds.has(f.route_id))fail(400,'運賃の参照が不正です。');
 for(const f of rows['fare_attributes.txt'])if(!Number.isFinite(Number(f.price))||Number(f.price)<0||f.currency_type!=='JPY')fail(400,'運賃・通貨を確認してください。');
 const info=rows['feed_info.txt'][0];if(!info?.feed_version||!/^\d{8}$/.test(info.feed_start_date)||!/^\d{8}$/.test(info.feed_end_date)||info.feed_start_date>info.feed_end_date)fail(400,'配布版・有効期間を確認してください。');
 return {valid:true,profile:'Limited local Schedule checks; GTFS-JP v4 full conformance unverified',synthetic:info.feed_version.startsWith('SYNTHETIC-'),version:info.feed_version,startDate:info.feed_start_date,endDate:info.feed_end_date,trips:tripIds.size,stops:stopIds.size,externalImportVerified:false};
}
export function inspectZip(bytes:Uint8Array){if(bytes.byteLength>2000000)fail(413,'ZIPは2MB以内で指定してください。');let total=0,count=0;const entries=unzipSync(bytes,{filter:f=>{total+=f.originalSize;count++;if(total>5000000||count>64||f.name.includes('/')||f.name.includes('..'))fail(400,'ZIPの構成・展開サイズを確認してください。');return f.name.endsWith('.txt');}});return validateFeed(Object.fromEntries(Object.entries(entries).map(([k,v])=>[k,strFromU8(v)])));}
