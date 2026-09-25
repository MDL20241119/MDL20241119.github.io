import {AppState,inputDate,DomainError} from '../model';

// Explicit synthetic network configuration shared by UI, API, MCP, A2A and GTFS.
export const stops=[
 {id:'oita-station',name:'大分駅前',kana:'おおいたえきまえ',lat:33.2328,lon:131.6067},
 {id:'community-hub',name:'地域拠点',kana:'ちいききょてん',lat:33.223,lon:131.594},
] as const;
export const serviceId='mdl-demo-fixed-stops';
export const passengerType='demo-general';
export const transportBookings=(s:AppState)=>s.bookings.filter(b=>['shuttle','ondemand'].includes(b.purpose)&&b.route==='大分駅前 → 地域拠点');
export const weekdays=['monday','tuesday','wednesday','thursday','friday','saturday','sunday','holidays'];
export function validCalendarDate(value:string){const parsed=Date.parse(value+'T00:00:00Z');return /^\d{4}-\d{2}-\d{2}$/.test(value)&&Number.isFinite(parsed)&&new Date(parsed).toISOString().slice(0,10)===value;}
export function serviceCatalogue(s:AppState){
 requireDemo(s);
 const bookings=transportBookings(s).filter(b=>b.status!=='cancelled').sort((a,b)=>a.start.localeCompare(b.start));
 if(!bookings.length)return {mode:s.mode,asOf:s.clock,timezone:'Asia/Tokyo',services:[],stops:[],notice:'公開対象の運行予定がありません。'};
 const first=bookings[0].start,last=bookings.reduce((last,b)=>b.end>last?b.end:last,bookings[0].end);
 const days=new Map<string,{start_time_offset_sec:number;end_time_offset_sec:number}[]>();
 for(const b of bookings){const day=inputDate(b.start).slice(0,10),midnight=Date.parse(day+'T00:00:00+09:00');const slots=days.get(day)??[];slots.push({start_time_offset_sec:(Date.parse(b.start)-midnight)/1000,end_time_offset_sec:(Date.parse(b.end)-midnight)/1000});days.set(day,slots);}
 const special=[...days].map(([date,slots])=>{const merged:typeof slots=[];for(const slot of slots.sort((a,b)=>a.start_time_offset_sec-b.start_time_offset_sec)){const prev=merged.at(-1);if(prev&&prev.end_time_offset_sec>=slot.start_time_offset_sec)prev.end_time_offset_sec=Math.max(prev.end_time_offset_sec,slot.end_time_offset_sec);else merged.push({...slot});}return {date,time_slots:merged};});
 const service={id:serviceId,name:'e-Palette ONE 検証用送迎（実運行なし）',access_scope:'private',operation_type:'fixed_time_fixed_route',allow_ridepooling:true,start_datetime:first,end_datetime:last,
 cities:[{prefecture_code:'44',prefecture_name:'大分県',municipalities:[{code:'44201',name:'大分市'}]}],service_terms:[],available_passenger_types:[{passenger_type_id:passengerType,name:'一般（検証用）',order:1}],supported_accessibility_features:[],
 operating_hours:Object.fromEntries(weekdays.map(day=>[day,[]])),special_operating_hours:special,announcements:[],
 operation_settings:{time_specifiable:{departure:true,arrival:false},max_advance_reservable_days:Math.max(0,Math.round((Date.parse(inputDate(bookings.at(-1)!.start).slice(0,10)+'T00:00:00Z')-Date.parse(inputDate(s.clock).slice(0,10)+'T00:00:00Z'))/86400000)),min_advance_reservable_minutes:0,cancel_deadline_minutes:0,search_passenger_limit:8,search_accessibility_limit:0,reservable_location_types:['fixed_stop']},
 reservable_areas:[],area_transitions:{areas:[],rules:[]}};
 return {mode:s.mode,asOf:s.clock,timezone:'Asia/Tokyo',services:[service],stops:stops.map((stop,i)=>({id:stop.id,service_ids:[serviceId],name:stop.name,search_words:[stop.kana],location:{type:'Point',coordinates:[stop.lon,stop.lat]},start_datetime:first,end_datetime:last,is_boarding_available:i===0,is_alighting_available:i===1,suspensions:[],pictures:[]})),notice:'合成の2点間ネットワークです。実運行・実停留所のデータではありません。固定した便のみ検索できます。'};
}
export function requireDemo(s:AppState){if(s.mode!=='demo')throw new DomainError(503,'正式な運行サービス設定が必要です。');}
