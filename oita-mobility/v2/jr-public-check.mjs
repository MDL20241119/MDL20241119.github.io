import {CHECK_DATE,CITY_STATIONS,NEAR_STATIONS,roundtripCheck} from '../data/rail/public-checks.mjs';
const el=id=>document.getElementById(id);
export function mount(){
  const menu=el('jr-proof-origin');
  for(const name of [...CITY_STATIONS,...NEAR_STATIONS]){
    const option=document.createElement('option');option.value=name;option.textContent=name+'駅';menu.append(option);
  }
  menu.value='中判田';
  el('jr-proof-form').addEventListener('submit',e=>{
    e.preventDefault();
    const status=roundtripCheck({date:CHECK_DATE,station:menu.value,depart:el('jr-proof-depart').value,activityFrom:'11:00',activityTo:'11:05',stay:Number(el('jr-proof-stay').value),deadline:el('jr-proof-deadline').value});
    el('jr-proof-result').textContent=status==='candidate'?'JRとバスで往復候補あり（時刻表上）':'この条件の往復は未確認。行けないという意味ではありません。';
  });
}
