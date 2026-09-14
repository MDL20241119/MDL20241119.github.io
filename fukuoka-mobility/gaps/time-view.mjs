export const TIME_COLORS={pass:'#237b92',review:'#b87518',fail:'#c53635',unknown:'#788491'};
export const TIME_LABELS={pass:'収録便で便数条件内',review:'収録便では不足・要確認',fail:'網羅確認後の不足',unknown:'時刻表未確認・未計算'};
export function timeViewFromParams(params){
  const hour=Number(params.get('hour')),minimum=Number(params.get('hourlyMinimum'));
  return {mode:params.get('view')==='conditions'?'conditions':'hourly',hour:params.has('hour')&&Number.isInteger(hour)&&hour>=0&&hour<24?hour:8,minimumTrips:[1,2,3,4,6].includes(minimum)?minimum:1};
}
export function hourLabel(hour){return `${String(hour).padStart(2,'0')}:00〜${String(hour+1).padStart(2,'0')}:00`;}
export function hourlyAssessment(result,hour,minimumTrips=1){
  if(!Number.isInteger(hour)||hour<0||hour>23||!Number.isInteger(minimumTrips)||minimumTrips<1)throw Error('時間帯と必要便数を確認してください');
  const count=result?.departurePattern?.hourly?.[hour];
  if(!Number.isFinite(count)||count<0)return {state:'unknown',count:null};
  if(count>=minimumTrips)return {state:'pass',count};
  // A zero in an incomplete timetable collection is never proof of no service.
  return {state:result.networkCoverageComplete===true?'fail':'review',count};
}
export function hourlySummary(cells,results,hour,minimumTrips){
  const summary=Object.fromEntries(Object.keys(TIME_COLORS).map(state=>[state,{count:0,area:0}]));
  for(const cell of cells){const state=hourlyAssessment(results.get(cell.id),hour,minimumTrips).state;summary[state].count++;summary[state].area+=cell.properties.areaKm2;}
  return summary;
}
