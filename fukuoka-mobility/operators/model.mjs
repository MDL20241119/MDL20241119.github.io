export const STATUS = {
  timetable: {label:'時刻表反映（収録分）', className:'available'},
  location: {label:'時刻表未反映・位置あり', className:'missing'},
  unusable: {label:'時刻表利用不可', className:'unusable'},
};
export const MODES = {bus:'バス・地域交通',rail:'鉄道',ferry:'渡船'};
export const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const fmt = value => Number(value).toLocaleString('ja-JP');
export function selectOperators(data,{operator='all',mode='all',status='all',query=''}={}) {
  const group = data.priorityGroups.find(g=>g.id===operator);
  const q = query.normalize('NFKC').toLocaleLowerCase('ja');
  return data.operators.filter(r=>(operator==='all'||r.id===operator||group?.operatorIds.includes(r.id))
    && (mode==='all'||r.mode===mode) && (status==='all'||r.status===status||status==='missing'&&r.status!=='timetable')
    && (!q||[r.name,...r.sourceNames,...r.routes].join(' ').normalize('NFKC').toLocaleLowerCase('ja').includes(q)));
}
export function summarize(rows) {
  return {providers:rows.length,bus:rows.reduce((n,r)=>n+r.busIndices.length,0),
    stations:rows.reduce((n,r)=>n+r.stationCount,0),stops:rows.reduce((n,r)=>n+r.gtfsStopCount,0),
    timetable:rows.filter(r=>r.timetable).length};
}
export function csvText(rows) {
  const cell = value => '"'+(typeof value==='number'&&Number.isFinite(value)?String(value):String(value??'').replace(/^[=+@-]/,"' $&")).replaceAll('"','""')+'"';
  return '\uFEFF'+rows.map(row=>row.map(cell).join(',')).join('\r\n');
}
