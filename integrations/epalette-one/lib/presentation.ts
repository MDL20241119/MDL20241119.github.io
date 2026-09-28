import {AppState,clockText,fresh,nextBooking,readiness,neededSoc,estimate} from './model';

export function nextAction(s:AppState){
 const issue=s.vehicles.find(v=>readiness(s,v,nextBooking(s,v.id)).type==='blocked')??s.vehicles.find(v=>readiness(s,v,nextBooking(s,v.id)).type==='unknown');
 if(issue){const r=readiness(s,issue,nextBooking(s,issue.id));return {tone:r.type==='blocked'?'danger':'warning',label:r.type==='blocked'?'利用を止めて確認':'情報を確認',title:r.type==='blocked'?issue.id+'は利用できません':issue.id+'の状態が分かりません',description:r.reason,deadline:null,vehicleId:issue.id,button:'車両の状態を確認',modal:'vehicle',id:issue.id,kind:'issue'};}
 const v=s.vehicles.find(v=>{const b=nextBooking(s,v.id);return b&&fresh(v.soc,s.clock)&&v.soc.value!<neededSoc(v,b);});
 if(v){const b=nextBooking(s,v.id)!,task=s.tasks.find(t=>t.vehicleId===v.id&&t.kind==='charge'&&t.status!=='completed'),e=estimate(s,v,b,'dc1');
  if(task)return {tone:'blue',label:'依頼後の確認',title:task.status==='requested'?'充電担当者の受領を確認':'充電の進み具合を確認',description:`${v.id} · ${clockText(b.start)}から${b.title}`,deadline:task.deadline,vehicleId:v.id,button:'充電の引継ぎを確認',modal:'tasks',id:task.id,kind:'handover'};
  return {tone:e.valid&&e.possible?'blue':'warning',label:'次の利用に備える',title:e.valid&&e.possible?'充電の準備をしてください':'充電・利用予定の見直しが必要です',description:`${v.id} · ${clockText(b.start)}から${b.title}`,deadline:e.valid?e.leaveAt:null,vehicleId:v.id,button:'間に合う充電を確認',modal:'charge',id:v.id,kind:'charge',estimate:e};
 }
 const task=s.tasks.filter(t=>t.status!=='completed').sort((a,b)=>a.deadline.localeCompare(b.deadline))[0];
 if(task)return {tone:'blue',label:'次の担当者へ',title:'引継ぎの確認が残っています',description:task.title,deadline:task.deadline,vehicleId:task.vehicleId,button:'引継ぎを確認',modal:'tasks',id:task.id,kind:'handover'};
 return {tone:'calm',label:'次の利用へ',title:'開始前の確認に進みましょう',description:'車両データだけでは、現場の安全確認は完了しません。',deadline:null,vehicleId:'',button:'次の利用を確認',modal:'schedule',id:'',kind:'ready'};
}
export function durationText(minutes:number){const h=Math.floor(minutes/60),m=minutes%60;return h?`${h}時間${m?`${m}分`:''}`:`${m}分`;}
export function durationRange(min:number,max:number){return min===max?durationText(max):durationText(min)+'〜'+durationText(max);}
