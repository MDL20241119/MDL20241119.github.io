export const OBSERVATION_STATUS = {
  available:'公表値', 'no-data':'データなし', nonpublic:'非公表',
  'other-line':'他線に計上', 'no-station':'当該年度は駅なし',
};
export function observation(station, year) {
  return station.observations.find(o=>o.year===Number(year)) ?? {year:Number(year),value:null,status:'no-data'};
}
export function stationRows(data, operatorIds, year, query='') {
  const q=query.normalize('NFKC').toLowerCase();
  return data.stations.filter(s=>operatorIds.includes(s.operatorId)
    && (!q||[s.name,s.line,s.operator].join(' ').normalize('NFKC').toLowerCase().includes(q)))
    .map(s=>({...s,current:observation(s,year)}))
    .sort((a,b)=>(b.current.value??-1)-(a.current.value??-1)||a.name.localeCompare(b.name,'ja')||a.id.localeCompare(b.id));
}
export function coverage(stations) {
  return {records:stations.length, available:stations.filter(s=>s.current.status==='available').length,
    missing:stations.filter(s=>['no-data','nonpublic'].includes(s.current.status)).length,
    other:stations.filter(s=>['other-line','no-station'].includes(s.current.status)).length};
}
export function operatingMargin(account) {
  return Number.isFinite(account.revenueMillionYen)&&account.revenueMillionYen>0&&Number.isFinite(account.profitMillionYen)
    ?account.profitMillionYen/account.revenueMillionYen*100:null;
}
