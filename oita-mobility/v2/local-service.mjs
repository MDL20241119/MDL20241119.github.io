const get=id=>document.getElementById(id);
const hhmm=x=>String(Math.floor(x/60)).padStart(2,'0')+':'+String(x%60).padStart(2,'0');
const time=x=>/^\d\d:\d\d$/.test(x)?60*Number(x.slice(0,2))+Number(x.slice(3)):null;
const today=()=>new Date().toLocaleDateString('sv-SE',{timeZone:'Asia/Tokyo'});
const nextDate=x=>new Date(+new Date(x+'T00:00:00Z')+86400000).toISOString().slice(0,10);
export function scheduleFor(data,service,date){
  if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||date<service.start||date>service.end)return {status:'unverified',reason:'確認済みダイヤの期間外'};
  if(!Number.isFinite(+new Date(date+'T00:00:00Z')))return {status:'unverified',reason:'日付を確認できません'};
  if(service.blocked?.includes(date))return {status:'closed',reason:'市の公表による運休日'};
  if(service.restartUnconfirmed===date)return {status:'unverified',reason:'再開は予定。運行を要確認'};
  if(data.holidays.includes(date)||date.slice(5)>='12-29'||date.slice(5)<='01-03')return {status:'closed',reason:'祝日・年末年始の運休'};
  const dow=new Date(date+'T00:00:00Z').getUTCDay();
  const trips=service.lines.filter(l=>l.days.includes(dow)).flatMap(l=>l.trips.map((calls,i)=>({calls,name:l.name,id:l.name+'#'+i})));
  return trips.length?{status:'published',trips}:{status:'closed',reason:'この曜日の収録便はありません'};
}
export function stationNames(service){
  return [...new Set(service.lines.flatMap(l=>l.trips.flatMap(calls=>calls.map(call=>call[0]))))];
}
function move(trips,from,to,start,limit,maxTransfers){
  const choices=[];
  for(const a of trips)for(let i=0;i<a.calls.length-1;i++){
    const [board,depart]=a.calls[i];if(board!==from||depart<start||depart>limit)continue;
    for(let j=i+1;j<a.calls.length;j++){
      const [via,t]=a.calls[j];if(t>limit)break;
      const first={from,to:via,depart,arrive:t,line:a.name};
      if(via===to){choices.push([first]);continue;}if(!maxTransfers)continue;
      for(const b of trips){if(a.id===b.id)continue;
        for(let x=0;x<b.calls.length-1;x++){
          const [board2,depart2]=b.calls[x];if(board2!==via||depart2<t+3||depart2>limit)continue;
          for(let y=x+1;y<b.calls.length;y++){const [dest,arrive]=b.calls[y];if(dest===to&&arrive<=limit)choices.push([first,{from:via,to,depart:depart2,arrive,line:b.name}]);}
        }
      }
    }
  }
  return choices.sort((a,b)=>a.at(-1).arrive-b.at(-1).arrive||a.length-b.length||b[0].depart-a[0].depart);
}
export function regionalRoundtrip(data,service,q){
  const {date,from,to,depart,activity,duration,deadline}=q;
  if(!from||!to||from===to||![depart,activity,duration,deadline].every(Number.isFinite)||depart>activity||activity+duration>deadline||duration<1||duration>720)return {status:'input',reason:'停留所・時刻・滞在時間を見直してください。'};
  const s=scheduleFor(data,service,date);
  if(s.status!=='published')return s;
  const limit=Number.isFinite(q.legLimit)?q.legLimit:180;
  const there=move(s.trips,from,to,depart,Math.min(activity,depart+limit),1)[0];
  if(!there)return {status:'no_candidate',reason:'用事の開始時刻までに着く収録便がありません。'};
  const back=move(s.trips,to,from,activity+duration,Math.min(deadline,activity+duration+limit),1)[0];
  if(!back)return {status:'no_candidate',reason:'用事の後、指定時刻までに戻る収録便がありません。',there};
  return {status:service.kind==='reservation'?'conditional':'candidate',there,back};
}
export async function mountRegional(){
  const root=get('regional-transport');if(!root)return;
  const prov=get('regional-source'), service=get('regional-service'), origin=get('regional-origin'), dest=get('regional-dest'), date=get('regional-date'), result=get('regional-result');
  const response=await fetch('data/local/oita-local-20261128.json');
  if(!response.ok)throw Error('地域交通のデータを取得できません');
  const data=await response.json();
  const opt=(caption,value)=>{const el=document.createElement('option');el.textContent=caption;el.value=value;return el;};
  service.replaceChildren(...data.services.map(x=>opt(x.name,x.id)));date.value=get('date')?.value||today();
  function choose(){
    const s=data.services.find(x=>x.id===service.value);if(!s)return;
    const points=stationNames(s);
    origin.replaceChildren(...points.map(p=>opt(p,p)));dest.replaceChildren(...points.map(p=>opt(p,p)));
    dest.value=(s.id==='dainan'&&points.includes('天心堂へつぎ病院'))?'天心堂へつぎ病院':points[1];
    prov.href=s.source;prov.textContent='出典：大分市の運行案内 ↗';
    get('regional-note').textContent=s.note;
    result.textContent='';
  }
  service.onchange=choose;choose();get('regional-run').disabled=false;get('regional-next').disabled=false;
  get('regional-next').onclick=()=>{
    const s=data.services.find(x=>x.id===service.value);
    let d=date.value||today();if(d<s.start)d=s.start;
    for(let i=0;i<31;i++,d=nextDate(d)){if(scheduleFor(data,s,d).status==='published'){date.value=d;result.textContent='';return;}}
    result.textContent='確認済みの運行日が見つかりません。';
  };
  get('regional-form').addEventListener('submit',e=>{
    e.preventDefault();const s=data.services.find(x=>x.id===service.value);
    const q={date:date.value,from:origin.value,to:dest.value,depart:time(get('regional-depart').value),activity:time(get('regional-arrive').value),duration:Number(get('regional-stay').value),deadline:time(get('regional-home').value)};
    const r=regionalRoundtrip(data,s,q);
    const format=xs=>xs.map(p=>p.from+' '+hhmm(p.depart)+' → '+p.to+' '+hhmm(p.arrive)).join(' ／ ');
    const content=r.back?[r.status==='conditional'?'条件付きで往復候補あり（予約は未確認）':'時刻表上の往復候補あり','行き '+format(r.there),'帰り '+format(r.back)]:[r.reason,r.there?'行きの候補 '+format(r.there):'','他の交通手段を含めた判定ではありません。'].filter(Boolean);
    result.replaceChildren(...content.map((line,i)=>{const el=document.createElement(i===0?'strong':'p');el.textContent=line;return el;}));
  });
}
