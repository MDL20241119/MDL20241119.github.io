(function(root){'use strict';
const STATUS={unconfirmed:'状況未確認',incomplete:'未完了（着手状況未確認）',policy:'方針決定済み（細則未決）',todo:'未着手',doing:'進行中',waiting:'相手待ち',review:'作業完了・確認待ち',confirmed:'確認済み完了',hold:'保留',unnecessary:'不要',done:'旧完了（確認記録未確認）'};
const dayPattern=/^\d{4}-\d{2}-\d{2}$/;
function validDay(day){return typeof day==='string'&&dayPattern.test(day)&&!Number.isNaN(Date.parse(day+'T12:00:00Z'))&&new Date(day+'T12:00:00Z').toISOString().startsWith(day)}
function todayJST(now=new Date()){return new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'}).format(now)}
function addDays(day,n){return new Date(Date.parse(day+'T12:00:00Z')+n*86400000).toISOString().slice(0,10)}
function weekStart(day){return addDays(day,-((new Date(day+'T12:00:00Z').getUTCDay()+6)%7))}
function closed(t){return !!t.archived||['done','confirmed','unnecessary'].includes(t.status)}
function deadline(t){return t.status==='review'&&t.review?.dueDate?t.review.dueDate:t.dueDate}
function overdue(t,today){return !closed(t)&&t.status!=='hold'&&!!deadline(t)&&deadline(t)<today}
function thisWeek(t,today){if(closed(t)||t.status==='hold')return false;const start=weekStart(today),end=addDays(start,6);return (!!t.plannedWeek&&t.plannedWeek<=start)||(!!t.dueDate&&t.dueDate>=start&&t.dueDate<=end)||overdue(t,today)||t.status==='review'||(t.status==='doing'&&!t.plannedWeek)}
function urgency(t,today){if(overdue(t,today))return 0;if(t.status==='review')return deadline(t)&&deadline(t)<=addDays(today,3)?1:2;return t.status==='waiting'?3:t.status==='doing'?4:5}
function selected(tasks,filters={},today=todayJST()) {
 const q=(filters.query||'').trim().toLocaleLowerCase('ja'),bucket=filters.view||'all',exactNumber=/^\d{2}-\d{2}$/.test(q);
 return tasks.filter(t=>{
  const inView=bucket==='completed'?closed(t):bucket==='hold'?!closed(t)&&t.status==='hold':!closed(t)&&t.status!=='hold'&&(bucket==='week'?thisWeek(t,today):bucket==='overdue'?overdue(t,today):bucket==='review'?t.status==='review':bucket==='unscheduled'?!t.plannedWeek&&!t.dueDate:true);
  return inView&&(!filters.phase||t.phase===filters.phase)&&(!filters.owner||(t.ownerTeam||'未定')===filters.owner)&&(!filters.region||(t.region||'未定')===filters.region)&&(!filters.status||t.status===filters.status)&&(!q||(exactNumber?t.id===q:[t.title,t.detail,t.counterparty,t.municipality,t.ownerTeam,t.id,t.number,...(t.legacyIds||[]),...(t.themes||[])].join(' ').toLocaleLowerCase('ja').includes(q)));
 }).sort((a,b)=>{
  const sort=filters.sort||'attention';
  return (sort==='number'?a.id.localeCompare(b.id):sort==='title'?a.title.localeCompare(b.title,'ja'):sort==='owner'?(a.ownerTeam||'未定').localeCompare(b.ownerTeam||'未定','ja'):sort==='due'?(a.dueDate||'9999').localeCompare(b.dueDate||'9999'):urgency(a,today)-urgency(b,today))||a.id.localeCompare(b.id);
 });
}
function nextAction(t){if(t.taskKind==='lecture-invitation')return t.sendStatus==='送信済み'?'送信済み。重複送信しない。':t.nextAction||'案内メールを送る';if(t.municipality&&t.briefingStatus==='説明済み')return t.followUpAction||'聞き取った課題を確認し、次の面談日を決める。';return t.nextAction||t.detail||'未定'}
function dueText(t,today){if(t.taskKind==='lecture-invitation'&&t.dueDate&&weekStart(today)!==t.plannedWeek)return t.dueDate.replaceAll('-','/')+'まで（指定週の期限）';return t.dueLabel||(validDay(t.dueDate)?`${Number(t.dueDate.slice(5,7))}/${Number(t.dueDate.slice(8,10))}`:'未定')}
function safeLink(value){if(typeof value!=='string'||!value||/[\u0000-\u0020\\]/.test(value))return null;if(value.startsWith('/')&&!value.startsWith('//'))return value;try{const url=new URL(value);if(['https:','http:'].includes(url.protocol)&&!url.username&&!url.password)return url.href}catch(_){}return null}
function validate(data){if(!data||data.kind!=='approved-readonly-snapshot'||data.schemaVersion!==2||!Array.isArray(data.tasks)||!Array.isArray(data.checklist)||!Array.isArray(data.operations)||!data.sync||data.sync.sharedEditingEnabled!==false||data.sync.writeEndpoint!==null)throw Error('未対応の表示データです');const ids=new Set();for(const t of data.tasks){if(!t.id||ids.has(t.id)||!STATUS[t.status]||!t.title)throw Error('重複または未対応のタスクです');ids.add(t.id);if(data.groups&&(!data.groups.some(g=>g.id===t.goalId)||t.number!==t.id||!/^\d{2}-\d{2}$/.test(t.id)||!t.id.startsWith(t.goalId+'-')))throw Error('固定番号・分類を確認してください');for(const key of ['dueDate','plannedWeek','businessSendTarget'])if(t[key]&&!validDay(t[key]))throw Error('日付の形式を確認してください');if(t.plannedWeek&&weekStart(t.plannedWeek)!==t.plannedWeek)throw Error('実施予定週は月曜日です');if(t.review?.dueDate&&!validDay(t.review.dueDate))throw Error('確認期限の形式を確認してください');if(t.resume?.date&&!validDay(t.resume.date))throw Error('再開日の形式を確認してください');if(t.ownerTeam&&!['TCO','MDL','その他'].includes(t.ownerTeam))throw Error('担当主体を確認してください');}return data}
const Core=Object.freeze({STATUS,validDay,todayJST,addDays,weekStart,closed,deadline,overdue,thisWeek,urgency,selected,nextAction,dueText,safeLink,validate});if(typeof module!=='undefined'&&module.exports)module.exports=Core;if(!root.document)return;
const $=id=>document.getElementById(id),el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==null&&text!==undefined)n.textContent=String(text);if(cls)n.className=cls;return n};
let data=null,view='all',lastDay=todayJST();
function labelDate(day){return validDay(day)?`${Number(day.slice(5,7))}/${Number(day.slice(8,10))}`:'未定'}
function link(text,url){const a=el('a',text),safe=safeLink(url);if(safe)a.href=safe;else a.removeAttribute('href');if(safe&&/^https?:/.test(safe)){a.target='_blank';a.rel='noreferrer noopener'}return a}
function td(row,label){const cell=el('td');cell.dataset.label=label;row.append(cell);return cell}
function table(headers,cls){const wrap=el('div',null,'table-wrap'),t=el('table',null,'board-table '+cls),thead=el('thead'),head=el('tr'),tbody=el('tbody');for(const name of headers){const th=el('th',name);th.scope='col';head.append(th)}thead.append(head);t.append(thead,tbody);wrap.append(t);return {wrap,tbody}}
function appendReferences(container,t){
 const refs=t.referenceLinks||[];
 for(const ref of refs){const url=safeLink(ref.url);if(url){container.append(link('参考：'+(ref.label||'資料')+' ↗',url));if(ref.verificationNote){const note=el('details',null,'reference-note');note.append(el('summary','資料の確認状況'),el('small',ref.verificationNote));container.append(note)}}}
 if(t.source&&!refs.some(r=>r.url===t.source))container.append(link((t.sourceLabel||'既存の参考資料')+' ↗',t.source));
 const proof=(t.evidenceLinks||[]).map(safeLink).filter(Boolean);
 if(proof.length){proof.forEach((url,i)=>container.append(link('完了・成果物の根拠 '+(i+1)+' ↗',url)))}else container.append(el('small','資料リンク未確認（完了を裏付ける資料）'));
}
function taskTable(tasks,today,context='all'){
 const {wrap,tbody}=table(['番号','何を','誰に','誰が','いつまでに','状況'],'task-table');
 for(const t of tasks){
  const row=el('tr');row.id=context==='weekly'?'weekly-'+t.id:t.id;row.dataset.taskId=t.id;
  if(overdue(t,today))row.classList.add('task-overdue');
  if(!closed(t)&&t.status!=='hold'&&deadline(t)&&deadline(t)>=today&&deadline(t)<=addDays(today,3))row.classList.add('task-soon');
  if(t.status==='review'&&urgency(t,today)<=1)row.classList.add('task-urgent');
  td(row,'番号').append(el('b',t.number||t.id,'task-number'));
  const name=td(row,'何を');name.append(el('b',t.title,'task-title'));
  if(t.summary)name.append(el('small',t.summary));
  if(!closed(t))name.append(el('p','次の行動：'+nextAction(t),'next-action'));
  if(closed(t))appendReferences(name,t);
  if(t.completedSteps?.length)for(const step of t.completedSteps)name.append(el('small','✓ '+step.title+'：確認済み'));
  const detail=el('details',null,'task-detail');detail.append(el('summary','詳細・参考資料'),el('p',t.detail));
  if(t.entryTheme)detail.append(el('p','以前の相談の入口：'+t.entryTheme+'（未合意・送信タスクとは別）'));
  if(t.event){const eventLabel=typeof t.event==='string'?t.event:`開催予定：${t.event.date} ${t.event.startTime}〜${t.event.endTime} ／ ${t.event.venue}`;name.append(el('small',eventLabel));}
  detail.append(el('small',`${t.phase==='after'?'設立後':'設立前'} ／ ${t.region||'地域未定'}`),el('small',`実施予定週：${t.plannedWeek?labelDate(t.plannedWeek)+'〜':'未定'}`));
  if(t.plannedWeek&&t.plannedWeek<weekStart(today))detail.append(el('em','前週以前から継続'));
  const helpers=(t.collaborators||[]).map(x=>typeof x==='string'?x:[x.team,x.name].filter(Boolean).join(' '));
  detail.append(el('small','協力者：'+(helpers.length?helpers.join('、'):'未定')));
  if(t.themes?.length)detail.append(el('small','テーマ別：'+t.themes.join(' ／ ')));
  if(t.statusNote)detail.append(el('small',t.statusNote));
  if(t.privateDetailsPending)detail.append(el('p','相手先・協議内容は非公開保存先未接続のため表示していません。'));
  if(!closed(t))appendReferences(detail,t);
  name.append(detail);
  td(row,'誰に').append(el('span',t.municipality?t.municipality+'（窓口：'+(t.counterparty||'未定')+'）':t.counterparty||'未定'));
  const owner=td(row,'誰が');owner.append(el('b',t.ownerTeam||'未定'));if(t.ownerName)owner.append(el('small',t.ownerName));
  const due=td(row,'いつまでに');due.append(el('b',dueText(t,today)));
  if(t.targetMonth&&!t.dueDate&&!t.dueLabel)due.append(el('small',t.targetMonth.replace('-','年')+'月目標・正式日未定'));
  if(t.businessSendTarget)due.append(el('small',t.businessSendTargetLabel||'営業日の送信目安：'+labelDate(t.businessSendTarget),'send-target'));
  if(t.dueDate&&t.dueCertainty!=='confirmed')due.append(el('small','仮置き'));
  if(overdue(t,today))due.append(el('em','期限超過'));else if(row.classList.contains('task-soon'))due.append(el('em','期限間近'));
  const state=td(row,'状況');state.append(el('span',STATUS[t.status],'status'));
  if(t.sendStatus)state.append(el('small','送信：'+t.sendStatus));
  if(t.statusNote&&(closed(t)||t.privateDetailsPending))state.append(el('small',t.statusNote));
  if(closed(t)&&t.completionBasis)detail.append(el('small',typeof t.completionBasis==='string'?t.completionBasis:t.completionBasis.summary||t.completionBasis.note||'本人の最新指示で完了を確認'));
  if(t.status==='review'){
   const review=el('div',null,'review-detail');review.append(el('b','確認内容：'+(t.review?.request||'未定')),el('span','判断：'+(t.review?.reviewerLabel||'未定')),el('span','確認期限：'+labelDate(t.review?.dueDate)));
   if(t.review?.artifactLink&&safeLink(t.review.artifactLink))review.append(link('確認する成果物 ↗',t.review.artifactLink));else review.append(el('small','成果物リンク：未定'));
   state.append(review);
  }
  if(t.status==='hold')state.append(el('small',`再開日：${labelDate(t.resume?.date)} ／ 条件：${t.resume?.condition||'未定'}`));
  tbody.append(row);
 }
 return wrap;
}
function filters(){return {view,query:$('search').value,phase:$('phase').value,owner:$('owner').value,region:$('region').value,status:$('status').value,sort:$('sort').value}}
function draw(){
 if(!data)return;const today=todayJST(),start=weekStart(today);lastDay=today;
 const f=filters(),tasks=selected(data.tasks,f,today),completed=selected(data.tasks,{...f,view:'completed'},today);
 $('week-label').textContent=`${labelDate(start)}–${labelDate(addDays(start,6))} ／ 日本時間`;
 const groups=el('div',null,'task-groups');
 for(const group of data.groups||[]){
  const section=el('section',null,'goal-section');section.id='goal-'+group.id;
  const heading=el('div',null,'goal-heading'),h=el('h2');h.append(el('b',group.id,'number'),el('span',group.title));heading.append(h);
  if(group.subtitle)heading.append(el('p',group.subtitle));
  section.append(heading);
  const active=tasks.filter(t=>t.goalId===group.id),done=completed.filter(t=>t.goalId===group.id);
  section.append(active.length?taskTable(active,today):el('p','この条件の未完了タスクはありません。','group-empty'));
  const finished=el('div',null,'completed-tasks');finished.append(el('h3','完了・資料 '+done.length+'件'));
  finished.append(done.length?taskTable(done,today):el('p','該当なし','group-empty'));section.append(finished);groups.append(section);
 }
 $('items').replaceChildren(groups);
 const weekTasks=selected(data.tasks,{...f,view:'week'},today);
 $('weekly-items').replaceChildren(weekTasks.length?taskTable(weekTasks,today,'weekly'):el('p','この条件で今週に該当するタスクはありません。','weekly-empty'));
 $('weekly-total').textContent=weekTasks.length+'件';
 $('weekly-note').textContent='下の一覧と同じタスクを抽出。予定週と締切は別管理。期限超過・確認待ちは翌週も残ります。';
 $('count').textContent=`表示：未完了 ${tasks.length}件 ／ 完了・資料 ${completed.length}件　（登録 ${data.tasks.length}件）`;
 $('empty').hidden=tasks.length+completed.length!==0;
 $('show-unscheduled').hidden=view!=='week'||!selected(data.tasks,{...f,view:'unscheduled'},today).length;
 for(const v of ['week','overdue','review','all','unscheduled','hold'])$(v+'-count').textContent=String(selected(data.tasks,{...f,view:v},today).length);
 document.querySelectorAll('[data-view]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.view===view)));
 revealSection();
}
function drawChecklist(){const {wrap,tbody}=table(['項目','決めること／用意するもの','担当／確認状況','最新版リンク／既存資料'],'check-table');for(const c of data.checklist){const row=el('tr');row.id=c.id;td(row,'項目').append(el('b',c.title,'task-title'),el('small',c.id));const prep=td(row,'決めること／用意するもの');prep.append(el('b','決めること'),el('p',c.decide),el('b','用意するもの'),el('p',c.prepare));const details=el('details');details.append(el('summary','法令・契約上の確認：'+c.legalStatus),el('p',c.legalNote));prep.append(details);const status=td(row,'担当／確認状況');status.append(el('b',c.ownerTeam||'未定'),el('br'),el('span',c.status,'status'),el('small','関連タスク：'+(c.relatedTaskIds||[]).join('、')));const refs=td(row,'最新版リンク／既存資料');if(c.latestLink)refs.append(link('最新版 ↗',c.latestLink));else refs.append(el('span','最新版リンク未登録','muted'));refs.append(el('br'),link(c.sourceLabel+' ↗',c.source),el('small','旧公開論点の参照ID：'+c.sourceIds.join('、')));tbody.append(row)}$('checklist').replaceChildren(wrap)}
function drawOperations(){const grid=el('div',null,'operation-grid');data.operations.forEach((op,i)=>{const article=el('article');article.id=op.id;article.append(el('span',String(i+1).padStart(2,'0'),'number'),el('h3',op.title),el('p',op.detail),el('small',`担当：${op.ownerTeam||'未定'} ／ ${op.status}`),el('br'),el('small','関連：'+op.relatedTaskIds.join('、')));grid.append(article)});$('operation-items').replaceChildren(grid)}
function drawHistory(){const box=el('div',null,'history-list');let n=0;for(const snapshot of data.history||[]){const group=el('details');group.append(el('summary',snapshot.asOf.slice(0,10)+' 更新前の記録 '+snapshot.tasks.length+'件'));for(const t of snapshot.tasks||[]){const article=el('article');article.append(el('small',t.id+' ／ '+(t.group||t.goal||'')+' ／ '+(STATUS[t.status]||t.status)),el('h3',t.title),el('p',t.detail),el('small','当時の担当：'+(t.ownerTeam||t.owner||'未定')+' ／ 当時の期限：'+(t.due||labelDate(t.dueDate))));if(t.source)article.append(link('当時の参照資料 ↗',t.source));group.append(article);n++}box.append(group)}$('history-items').replaceChildren(box);$('history-count').textContent=String(n)}
function drawOutreach(){const {wrap,tbody}=table(['企業・団体名','窓口','主担当','状況','次の行動','期限'],'outreach-table');const row=el('tr'),cell=el('td','非公開保存先の接続後に表示します。');cell.colSpan=6;row.append(cell);tbody.append(row);$('outreach-list').replaceChildren(wrap)}
function drawProgramme(){const schedule=el('div',null,'schedule-months');for(const month of data.programmeSchedule?.months||[]){const article=el('article');article.append(el('b',month.month),el('p',month.activity));schedule.append(article)}$('programme-schedule').replaceChildren(el('p','月別の進め方案（未合意・締切ではありません）','small-note'),schedule);const {wrap,tbody}=table(['テーマ','実施条件・確認内容','担当','状況','期限'],'theme-table');for(const theme of data.themePlans||[]){const row=el('tr');td(row,'テーマ').append(el('b',theme.title));td(row,'実施条件・確認内容').append(el('p',theme.detail));td(row,'担当').append(el('span',theme.ownerTeam||'未定'));td(row,'状況').append(el('span',theme.status,'status'));td(row,'期限').append(el('span',labelDate(theme.dueDate)));tbody.append(row)}$('theme-plans').replaceChildren(wrap)}
for(const id of ['search','phase','owner','region','status','sort'])$(id).addEventListener(id==='search'?'input':'change',draw);
document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>{view=button.dataset.view;draw()}));$('show-unscheduled').addEventListener('click',()=>{view='unscheduled';draw();$('list-title').scrollIntoView({block:'start'})});$('reset').addEventListener('click',()=>{for(const id of ['search','phase','owner','region','status'])$(id).value='';$('sort').value='number';view='all';draw();$('search').focus()});
fetch('./tasks.json',{cache:'no-store',credentials:'omit'}).then(r=>{if(!r.ok)throw Error('表示データを取得できません');return r.json()}).then(value=>{data=validate(value);$('data-date').textContent='整理日 '+value.asOf.slice(0,10).replaceAll('-','.');for(const [key,label] of Object.entries(STATUS)){const o=el('option',label);o.value=key;$('status').append(o)}for(const region of [...new Set(data.tasks.map(t=>t.region).filter(Boolean))]){const o=el('option',region);o.value=region;$('region').append(o)}draw();drawChecklist();drawOperations();drawHistory();drawOutreach();drawProgramme()}).catch(()=>{$('count').textContent='表示データを読み込めませんでした。再読み込みするか、構想説明書をご確認ください。'});
setInterval(()=>{if(document.visibilityState==='visible'&&todayJST()!==lastDay)draw()},30000);document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')draw()});
function revealSection(){let id;try{id=decodeURIComponent(location.hash.slice(1))}catch(_){return}const target=document.getElementById(id);if(!target)return;let parent=target.parentElement;while(parent){if(parent.tagName==='DETAILS')parent.open=true;parent=parent.parentElement}}window.addEventListener('hashchange',revealSection);revealSection();
})(globalThis);
