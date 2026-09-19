'use strict';
const $ = id => document.getElementById(id);
const state = {user:null,csrf:null,snapshot:null,draft:null,pending:null,busy:false,refreshing:false,editing:null,catalog:null,candidates:[],observationDisconnected:false,observationReceivedAt:0,filter:'active',authEpoch:0,loggingIn:false};
const labels = {rider:'ユーザー',driver:'ドライバー',admin:'管理者'};
const statusLabels = {requested:'引受待ち',assigned:'迎車中',arrived:'到着',onboard:'乗車中',completed:'降車完了',cancelled:'取消済み'};
const paymentLabels={uncollected:'未収',received:'受領済み',excluded:'決済対象外',cancelled:'決済キャンセル'};
const paymentReviews={refund_review_required:'受領記録が残っています。返金確認が必要です。返金は実行されていません。',cancellation_update_required:'予約は取消済みです。管理者による決済情報の確認・更新が必要です。',fare_update_required:'確定運賃と記録額が異なります。管理者による確認が必要です。',fare_unknown:'現在の運賃を確認できません。管理者へお問い合わせください。'};
const e = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const date = value => new Date(value).toLocaleTimeString('ja-JP',{hour:'2-digit',minute:'2-digit',second:'2-digit',timeZone:'Asia/Tokyo'});
const plannedDate=value=>new Date(value).toLocaleString('ja-JP',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',timeZone:'Asia/Tokyo'});
const fare = value => value?.amount == null ? '運賃未設定' : `${value.amount.toLocaleString('ja-JP')}円${value.basis==='synthetic_test_only'?'（架空のテスト運賃）':''}`;
let messageTimer;
function message(text,error=false){ $('message').textContent=text; $('message').classList.toggle('error',error); $('message').hidden=false; clearTimeout(messageTimer); messageTimer=setTimeout(()=>{$('message').hidden=true;},error?14000:6000); }
async function api(path,body){
  const options={method:body===undefined?'GET':'POST',headers:{'Accept':'application/json'},credentials:'same-origin',signal:AbortSignal.timeout(12000)};
  if(body!==undefined){options.headers['Content-Type']='application/json';options.headers['X-Requested-With']='YokoLocal';if(state.csrf)options.headers['X-CSRF-Token']=state.csrf;options.body=JSON.stringify(body);}
  const response=await fetch(path,options);
  const data=await response.json();
  if(!response.ok){const error=new Error(data.error?.message || '接続を確認してください');error.status=response.status;error.code=data.error?.code;throw error;}
  return data;
}
function pendingKey(){return `yoko-demo-pending:v1:${state.user.id}`;}
function savePending(){ if(state.pending) sessionStorage.setItem(pendingKey(),JSON.stringify(state.pending));else sessionStorage.removeItem(pendingKey()); renderRecovery(); }
function renderRecovery(){
  $('recovery').hidden=!state.pending;
  $('recovery-id').textContent=state.pending?`操作ID：${state.pending.body.operation_id}`:'';
  $('prepare-request').disabled=Boolean(state.pending)||state.busy;
  $('search-candidates').disabled=Boolean(state.pending)||state.busy||Boolean(state.editing);
}
function signedIn(result){
  state.authEpoch++;state.refreshing=false;state.filter='active';$('ride-search').value='';
  state.user=result.user;state.csrf=result.csrf;
  try{state.pending=JSON.parse(sessionStorage.getItem(pendingKey()) || 'null');}catch{state.pending=null;}
  $('login').hidden=true;$('workspace').hidden=false;
  $('account').innerHTML=`<span>${e(labels[state.user.role])}<small>${e(state.user.id)}</small></span><button id="logout" class="text-button" type="button">入口へ戻る</button>`;
  $('logout').addEventListener('click',async()=>{if(state.busy){message('操作結果を確認してからログアウトしてください。',true);return;}try{await api('/api/logout',{});signedOut();}catch(err){message(err.message,true);}});
  $('role-kicker').textContent={rider:'RIDER / いつもの移動を、もっと気軽に',driver:'DRIVER / 安全に、確実に届ける',admin:'OPERATIONS / 地域の移動を見守る'}[state.user.role];
  $('role-title').textContent={rider:'今日は、どこへ？',driver:'送迎の状況',admin:'運行ダッシュボード'}[state.user.role];
  $('rides-title').textContent=state.user.role==='rider'?'あなたの依頼':'依頼・運行の状況';
  $('request-panel').hidden=state.user.role!=='rider';$('driver-safety').hidden=state.user.role!=='driver';$('admin-stats').hidden=state.user.role!=='admin';$('vehicles-panel').hidden=state.user.role==='rider';
  $('profile-panel').hidden=state.user.role!=='rider';
  $('work-grid').className='work-grid'+(state.user.role==='rider'?'':' operations');
  const links=state.user.role==='rider'?[['request-panel','車を呼ぶ'],['rides-section','依頼の状況'],['profile-panel','利用登録']]:[['rides-section','依頼の状況'],['vehicles-panel','車両の状況']];
  $('workspace-nav').innerHTML=links.map(([id,label])=>`<a href="#${id}">${label}</a>`).join('');
  // Keep the primary ride flow above the optional registration/settings panel.
  $('work-grid').after($('profile-panel'));
  $('connection-notice').hidden=true;
  document.title=`${labels[state.user.role]}｜横のエレベーター`;
  renderRecovery();refresh(true);
}
function signedOut(){
  state.authEpoch++;state.filter='active';$('ride-search').value='';$('workspace-nav').replaceChildren();
  $('ride-count').textContent='';$('connection-notice').hidden=true;$('stopped').checked=false;
  document.title='横のエレベーター｜Webアプリ';
  $('payment-dialog').close();$('payment-form').dataset.ride='';
  $('payment-target').textContent='';$('payment-amount').value='';
  for(const id of ['rides','vehicles','admin-stats'])$(id).replaceChildren();
  stopEditing();
  state.candidates=[];$('candidates').replaceChildren();$('offers-list').replaceChildren();$('offer-pickup').value='';
  state.catalog=null;$('profile-first-name').value='';$('profile-last-name').value='';$('terms-list').replaceChildren();$('profile-status').textContent='登録状況を確認中';
  state.user=null;state.csrf=null;state.snapshot=null;state.draft=null;state.pending=null;
  state.refreshing=false;
  $('confirm-dialog').close();$('login').hidden=false;$('workspace').hidden=true;$('account').replaceChildren();
}
function setServices(){
  const services=state.snapshot.services;
  $('service').innerHTML=services.map(s=>`<option value="${e(s.id)}">${e(s.name)}</option>`).join('');
  if(!services.length){$('request-panel').hidden=true;$('work-grid').classList.add('single');return;}
  fillStops();
}
function fillStops(){
  const service=state.snapshot.services.find(s=>s.id===$('service').value);
  if(!service)return;
  const stops=service.stops.filter(s=>s.active);
  const options=stops.map(s=>`<option value="${e(s.id)}">${e(s.name)}</option>`).join('');
  $('origin').innerHTML=options;$('destination').innerHTML=options;
  if(stops[1])$('destination').value=stops[1].id;
  $('service-fare').textContent= fare(service.fare);
  state.candidates=[];$('candidates').replaceChildren();
}
function stopEditing(){
  state.editing=null;$('request-title').textContent='どこへ行きますか？';$('stop-editing').hidden=true;
  for(const id of ['service','origin','destination'])$(id).disabled=false;
}
function editRide(ride){
  state.candidates=[];$('candidates').replaceChildren();
  state.editing=ride.id;$('service').value=ride.service_id;fillStops();
  $('origin').value=ride.origin_stop_id;$('destination').value=ride.destination_stop_id;$('passengers').value=String(ride.passengers);
  $('service').disabled=true;
  $('origin').disabled=$('destination').disabled=ride.status==='assigned';
  $('request-title').textContent=ride.status==='assigned'?'人数を変更する':'依頼内容を変更する';
  $('stop-editing').hidden=false;$('passengers').focus();
}
function rideProgress(ride){
  if(ride.status==='cancelled')return '<p class="cancelled-note">この依頼は取り消されています。</p>';
  const steps=[['requested','受付'],['assigned','迎車'],['arrived','到着'],['onboard','乗車'],['completed','完了']];
  const current=steps.findIndex(([status])=>status===ride.status);
  return `<ol class="ride-progress" aria-label="送迎の進み方">${steps.map(([status,label],i)=>`<li class="${i<=current?'reached':''}"${i===current?' aria-current="step"':''}><span aria-hidden="true">${i<current?'✓':i+1}</span>${label}</li>`).join('')}</ol>`;
}
function paymentCard(ride){
  const payment=ride.payment;if(!payment)return '';
  const record=payment.record;
  const canEdit=state.user.role==='admin'&&ride.status!=='requested'&&payment.expected_amount!==null&&payment.review_reason!=='refund_review_required';
  return `<div class="payment-summary"><p class="small"><b>決済情報（架空の台帳）</b><br>${record?`${e(paymentLabels[record.payment_status])} / ${record.amount.toLocaleString('ja-JP')}円（記録額）`:'未登録'}</p>${payment.review_required?`<p class="unknown">${e(paymentReviews[payment.review_reason])}</p>`:''}${canEdit?`<button type="button" class="secondary" data-payment="${e(ride.id)}">決済情報を記録・更新</button>`:''}</div>`;
}
const observationLabels={not_configured:'取得元未設定',not_acquired:'未取得',stale:'古い情報・更新待ち',expired:'有効期限切れ・解消未確認',stopped:'取得停止中',source_changed:'取得元変更・再取得待ち',not_operating:'現在の便なし'};
function observationBody(value){
  if(!value)return '<p class="unknown">車両位置：未取得　/　到着予測：未取得</p>';
  const now=Date.parse(state.snapshot.as_of)+Math.max(0,performance.now()-state.observationReceivedAt);
  function quality(kind){
    if(state.observationDisconnected)return '未接続・現在の状況は不明';
    const status=value[kind+'_status'];
    if(status!=='fresh')return observationLabels[status]||'未取得';
    return now>=Date.parse(value[kind+'_valid_until'])?'古い情報・更新待ち':null;
  }
  const locationProblem=quality('location'),delayProblem=quality('delay');
  const position=locationProblem||`架空位置：緯度 ${value.location.coordinates[1].toFixed(5)} / 経度 ${value.location.coordinates[0].toFixed(5)}`;
  const active=value.delays.filter(d=>d.status==='active');
  const delay=delayProblem||(active.length?active.map(d=>d.delay_minutes===undefined?'遅延あり・分数不明':`遅延 ${d.delay_minutes}分（架空）`).join(' / '):'進行中の遅延報告なし（観測時点）');
  return `<p class="small"><b>車両位置・遅延（架空の試験情報）</b><br>位置：${e(position)}<br>遅延：${e(delay)}<br>到着予測：未取得</p><p class="hint">取得元：${e(value.source?.label||'未設定')}${value.observed_at?`<br>観測：${e(new Date(value.observed_at).toLocaleString('ja-JP',{timeZone:'Asia/Tokyo'}))}（日本時間）`:''}</p>`;
}
function observationCard(value){return `<div class="observation" ${value?`data-observation="${e(value.vehicle_id)}"`:''}>${observationBody(value)}</div>`;}
function refreshObservationDisplays(){
  if(!state.user||!state.snapshot)return;
  const values=new Map([...state.snapshot.vehicles.map(v=>v.observation),...state.snapshot.rides.map(r=>r.observation)].filter(Boolean).map(v=>[v.vehicle_id,v]));
  document.querySelectorAll('[data-observation]').forEach(node=>{node.innerHTML=observationBody(values.get(node.dataset.observation));});
}
function card(ride){
  const role=state.user.role;
  let action='';
  if(role==='rider'&&['requested','assigned','arrived'].includes(ride.status)) action=`<button type="button" class="text-button cancel" data-action="cancel" data-ride="${e(ride.id)}">依頼を取り消す</button>`;
  if(role==='rider'&&['requested','assigned'].includes(ride.status)) action=`<button type="button" class="secondary" data-action="change" data-ride="${e(ride.id)}">${ride.status==='assigned'?'人数を変更する':'内容を変更する'}</button>`+action;
  if(role==='driver'){
    const next={requested:['accept','この依頼を引き受ける'],assigned:['arrive','到着を記録'],arrived:['board','乗車を記録'],onboard:['complete','降車を記録']}[ride.status];
    if(next)action=`<button type="button" class="primary" data-action="${next[0]}" data-ride="${e(ride.id)}">${next[1]}</button>`;
  }
  return `<article class="ride-card" data-ride-card="${e(ride.id)}"><div class="ride-top"><span class="badge ${e(ride.status)}">${e(ride.status_label)}</span><span class="ride-id">${e(ride.id.slice(-8))} / ${e(date(ride.created_at))}</span></div><div class="ride-route"><span>${e(ride.origin_name)}</span><span class="arrow" aria-label="から">→</span><span>${e(ride.destination_name)}</span></div><div class="ride-meta"><span>${ride.passengers}名</span><span>${e(fare(ride.fare))}</span>${ride.vehicle_id?`<span>車両 ${e(ride.vehicle_id)}</span>`:''}</div>${rideProgress(ride)}<p class="next">${e(ride.next_action)}</p>${ride.booking?`<p class="hint">架空の計画：乗車 ${e(plannedDate(ride.booking.pickup_at))} → 降車 ${e(plannedDate(ride.booking.dropoff_at))}（日本時間）</p>`:''}${!['completed','cancelled'].includes(ride.status)?observationCard(ride.observation):''}${paymentCard(ride)}${action?`<div class="ride-actions">${action}</div>`:''}<details><summary>受付・運行の記録</summary><p>予約：${{pending:'引受前・未成立',confirmed:'成立',cancelled:'取消済み'}[ride.reservation_status]} / 割当：${{unassigned:'未割当',assigned:'割当済み',released:'解放済み'}[ride.assignment_status]}</p><ol class="event-list">${ride.events.map(ev=>`<li>${e(date(ev.created_at))}　${e(statusLabels[ev.status])}</li>`).join('')}</ol></details></article>`;
}
function render(){
  const snap=state.snapshot;
  renderOffers();
  $('search-candidates').hidden=state.user.role!=='rider'||!snap.services.find(s=>s.id===$('service').value)?.routes.length;
  renderRides();
  const c=snap.counts;
  $('admin-stats').innerHTML=[['引受待ち',c.requested],['送迎中',c.assigned+c.arrived+c.onboard],['降車完了',c.completed],['取消',c.cancelled]].map(([label,count])=>`<div class="stat"><span>${label}</span><b>${count}</b></div>`).join('');
  $('vehicles').innerHTML=snap.vehicles.map(v=>`<article class="vehicle"><h3>${e(v.id)}</h3><strong>${v.reserved}</strong> / ${v.capacity}名<p>確保済み座席 / 定員</p><p>${v.accepting?'引受可能（乗降場所・空席を照合）':'現在の便は追加引受を停止'}</p>${observationCard(v.observation)}</article>`).join('');
  if(state.user.role==='admin')$('vehicles').insertAdjacentHTML('beforeend',`<p class="hint">テスト通知の未処理：${snap.outbox_pending}件<br>実際の通知送信は接続していません。</p>`);
  $('sync-state').textContent=`${date(snap.as_of)} 更新（このブラウザー）`;$('sync-state').classList.remove('disconnected');
}
function renderRides(){
  if(!state.snapshot||!state.user)return;
  const rides=state.snapshot.rides,finished=ride=>['completed','cancelled'].includes(ride.status);
  const counts={active:rides.filter(r=>!finished(r)).length,history:rides.filter(finished).length,all:rides.length};
  $('ride-filters').querySelectorAll('[data-filter]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.filter===state.filter)));
  $('ride-filters').querySelectorAll('[data-count]').forEach(n=>{n.textContent=counts[n.dataset.count];});
  const query=$('ride-search').value.trim().normalize('NFKC').toLocaleLowerCase('ja-JP');
  const ordered=rides.filter(r=>(state.filter==='all'||((state.filter==='history')===finished(r)))&&(!query||[r.id,r.origin_name,r.destination_name,r.vehicle_id||''].join(' ').normalize('NFKC').toLocaleLowerCase('ja-JP').includes(query)))
    .sort((a,b)=>Number(finished(a))-Number(finished(b)));
  const total=counts[state.filter];
  const countLabel=`${{active:'進行中',history:'完了・取消',all:'すべて'}[state.filter]} ${ordered.length}件${query?` / ${total}件`:''}（取得済みの最新200件から表示）`;
  if($('ride-count').textContent!==countLabel)$('ride-count').textContent=countLabel;
  const title=query?'該当する依頼がありません':state.filter==='history'?'完了・取消の履歴はありません':state.filter==='active'?'進行中の依頼はありません':'まだ依頼はありません';
  const detail=query?'場所の名前や受付番号を変えて探してください。':state.filter==='history'?'降車を記録した依頼や、取り消した依頼はここに残ります。':state.user.role==='rider'?'乗る場所・降りる場所・人数を選んで、内容を確認してください。':'利用者からの依頼を受け付けると、ここに表示されます。';
  // Polling keeps keyboard focus and expanded records on the same ride.
  const focused=document.activeElement,rideId=focused?.closest('[data-ride-card]')?.dataset.rideCard;
  const action=focused?.dataset.action,payment=focused?.dataset.payment,isSummary=focused?.tagName==='SUMMARY';
  const open=new Set([...$('rides').querySelectorAll('[data-ride-card] details[open]')].map(n=>n.closest('[data-ride-card]').dataset.rideCard));
  $('rides').innerHTML=ordered.length?ordered.map(card).join(''):`<div class="empty"><span class="empty-icon" aria-hidden="true">↔</span><h3>${title}</h3><p class="small">${detail}</p></div>`;
  for(const node of $('rides').querySelectorAll('[data-ride-card]')){
    if(open.has(node.dataset.rideCard))node.querySelector('details').open=true;
    if(node.dataset.rideCard===rideId){const target=[...node.querySelectorAll('button,summary')].find(n=>(action&&n.dataset.action===action)||(payment&&n.dataset.payment===payment)||(isSummary&&n.tagName==='SUMMARY'));target?.focus({preventScroll:true});}
  }
}
async function refresh(initial=false){
  if(!state.user||state.refreshing)return;
  state.refreshing=true;
  const epoch=state.authEpoch,requestedAt=performance.now();
  try{const snap=await api('/api/snapshot');if(state.authEpoch!==epoch)return;
    if(snap.user.id!==state.user.id||snap.user.role!==state.user.role||snap.user.tenant_id!==state.user.tenant_id){signedOut();message('別のタブでアカウントが変わりました。使う役割で入り直してください。',true);return;}
    state.snapshot=snap;state.observationDisconnected=false;state.observationReceivedAt=requestedAt;$('connection-notice').hidden=true;if(initial)setServices();render();if(state.user.role==='rider')await loadCatalog();}
  catch(err){if(state.authEpoch!==epoch)return;if(err.status===401){signedOut();message('ログインし直してください。結果不明の操作はログイン後に照合できます。',true);}else{state.observationDisconnected=true;$('connection-notice').hidden=false;refreshObservationDisplays();$('sync-state').textContent='未接続・表示は更新されていません';$('sync-state').classList.add('disconnected');if(initial)message(err.message,true);}}
  finally{if(state.authEpoch===epoch)state.refreshing=false;}
}
function renderOffers(){
  const routes=state.snapshot.services.flatMap(s=>(s.routes||[]).map(r=>({...r,label:`${s.stops.find(x=>x.id===r.origin_stop_id)?.name} → ${s.stops.find(x=>x.id===r.destination_stop_id)?.name}`})));
  $('offer-panel').hidden=state.user.role!=='driver'||!routes.length;
  const old=$('offer-route').value;$('offer-route').innerHTML=routes.map(r=>`<option value="${e(r.id)}">${e(r.label)}</option>`).join('');
  if(routes.some(r=>r.id===old))$('offer-route').value=old;
  if(!$('offer-pickup').value)$('offer-pickup').value=new Date(Date.now()+600000).toLocaleString('sv-SE',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}).replace(' ','T');
  const offers=state.snapshot.offers||[];$('offers-panel').hidden=!offers.length;
  $('offers-list').innerHTML=offers.map(o=>`<article class="vehicle"><b>${e(o.origin_name)} → ${e(o.destination_name)}</b><p>${e(o.vehicle_name)} / 確保済み${o.reserved}名</p><p>計画乗車 ${e(plannedDate(o.pickup_at))} → 降車 ${e(plannedDate(o.dropoff_at))}（日本時間）</p><p>${o.accepting?'候補の受付中':'受付終了・期限切れ'}</p>${state.user.role==='driver'&&o.can_close?`<button class="secondary" type="button" data-close-offer="${e(o.id)}">受付を終了する</button>`:''}</article>`).join('');
}
$('offer-form').addEventListener('submit',event=>{
  event.preventDefault();if(!$('stopped').checked){message('安全な場所に停車していることを確認してください。',true);return;}
  const route=state.snapshot.services.flatMap(s=>s.routes||[]).find(r=>r.id===$('offer-route').value);if(!route)return;
  const at=new Date($('offer-pickup').value+':00+09:00');if(!Number.isFinite(at.getTime())){message('計画時刻を入力してください。',true);return;}
  prepareCatalog('offer_open',{service_id:route.service_id,origin_stop_id:route.origin_stop_id,destination_stop_id:route.destination_stop_id,pickup_at:at.toISOString(),vehicle_name:$('offer-name').value,stopped:true});
});
$('offers-list').addEventListener('click',event=>{
  const button=event.target.closest('[data-close-offer]');if(!button)return;
  if(!$('stopped').checked){message('安全な場所に停車していることを確認してください。',true);return;}
  prepareCatalog('offer_close',{offer_id:button.dataset.closeOffer,stopped:true});
});
$('search-candidates').addEventListener('click',async()=>{
  if(state.busy||state.pending||state.editing)return;
  state.busy=true;renderRecovery();
  try{
    const result=await api('/api/candidates',{service_id:$('service').value,origin_stop_id:$('origin').value,destination_stop_id:$('destination').value,passengers:Number($('passengers').value),preferred_pickup_at:new Date().toISOString(),vehicle_id:null});
    state.candidates=result.candidates;
    const reasons={capacity_full:'必要な空席がありません。',no_active_offers:'現在、引受済みの提示便はありません。',service_closed:'現在は運行時間外です。',stops_suspended:'この乗降場所は利用を休止しています。'};
    $('candidates').innerHTML=result.candidates.length?'<p class="hint">架空の計画時刻です。候補の表示だけでは席を確保しません。</p>'+result.candidates.map(c=>`<article class="vehicle"><b>${e(c.origin_name)} → ${e(c.destination_name)}</b><p>計画乗車 ${e(plannedDate(c.pickup_at))} → 降車 ${e(plannedDate(c.dropoff_at))}（日本時間）</p><p>${e(c.vehicle_name)} / ${c.passengers}名 / ${e(fare(c.fare))}</p><p>候補の期限 ${e(date(c.expires_at))}</p><button class="secondary" type="button" data-candidate="${e(c.id)}">この便を確認する</button></article>`).join(''):`<p class="hint">${e(reasons[result.availability_reason]||'現在の条件では候補がありません。')}</p>`;
  }catch(err){state.candidates=[];$('candidates').replaceChildren();message(err.message,true);}
  finally{state.busy=false;renderRecovery();}
});
$('candidates').addEventListener('click',async event=>{
  const button=event.target.closest('[data-candidate]');if(!button||state.busy||state.pending)return;
  state.busy=true;renderRecovery();
  try{showDraft(await api('/api/drafts/book',{candidate_id:button.dataset.candidate}));}catch(err){message(err.message,true);}
  finally{state.busy=false;renderRecovery();}
});
for(const id of ['origin','destination','passengers'])$(id).addEventListener('change',()=>{state.candidates=[];$('candidates').replaceChildren();});
async function mutate(kind,payload){
  if(state.pending){message('前の操作の結果を先に確認してください。',true);return;}
  const id=crypto.randomUUID();
  state.pending={path:`/api/actions/${kind}`,body:{operation_id:id,idempotency_key:id,payload}};
  savePending();await sendPending();
}
async function sendPending(){
  if(!state.pending||state.busy)return;
  state.busy=true;$('commit').disabled=true;renderRecovery();
  const kind=state.pending.path.split('/').at(-1);
  try{
    const result=await api(state.pending.path,state.pending.body);
    if(kind==='request'||kind==='book'){if(state.filter==='history')state.filter='active';$('ride-search').value='';}
    state.pending=null;savePending();state.draft=null;stopEditing();$('confirm-dialog').close();$('stopped').checked=false;
    if(kind==='profile_delete'){signedOut();message('登録情報と規約への同意を削除しました。再利用時はログインして新たに登録してください。');}
    else {state.candidates=[];$('candidates').replaceChildren();message(kind==='payment_update'?'決済情報を記録しました。実際の請求・返金は行っていません。':kind.startsWith('offer_')?'提示便の情報を保存しました。':result.current.resource_type?'登録・同意情報を保存しました。':`現在の状態：${result.current.status_label}`);await refresh();}
  }catch(err){
    if(err.status&&err.status<500&&err.status!==429&&err.status!==401){state.pending=null;savePending();state.draft=null;$('confirm-dialog').close();}
    else{$('confirm-dialog').close();}
    message(err.status?err.message:'応答を確認できません。新しい依頼を作らず、結果を照合してください。',true);
    if(err.status===401)signedOut();
  }finally{state.busy=false;$('commit').disabled=false;if(state.user)renderRecovery();}
}
function showDraft(draft){
  state.draft=draft;const d=draft.details;const cancelling=draft.kind==='cancel';
  if(draft.kind==='book'){
    $('confirm-title').textContent='この便を予約しますか？';
    $('confirm-details').innerHTML=`<p><b>${e(d.origin_name)} → ${e(d.destination_name)}</b></p><p>計画乗車：${e(plannedDate(d.pickup_at))}<br>計画降車：${e(plannedDate(d.dropoff_at))}（日本時間）</p><p>${d.passengers}名 / ${e(fare(d.fare))}</p><p>車両：${e(d.vehicle_name)}</p><p class="hint">架空の設定に基づく計画時刻です。実際の到着予測は未取得です。確定時に空席を再確認します。</p>`;
    $('confirm-expiry').textContent=`候補・確認の期限：${date(draft.expires_at)}（日本時間）`;
    $('commit').textContent='確認して予約';$('confirm-dialog').showModal();return;
  }
  if(d.input){
    const kind=draft.kind;
    $('confirm-title').textContent={profile_create:'この内容で登録しますか？',profile_update:'登録内容を更新しますか？',profile_delete:'登録情報を削除しますか？',agreements_register:'選んだ規約に同意しますか？'}[kind]||'内容を確認してください';
    if(kind==='payment_update'){
      const previous=d.dependencies[0].previous;const ride=state.snapshot.rides.find(r=>r.id===d.input.ride_id);
      $('confirm-title').textContent='この決済情報を記録しますか？';
      $('confirm-details').innerHTML=`<p><b>${e(ride?`${ride.origin_name} → ${ride.destination_name}`:d.input.ride_id)}</b></p><p>予約ID：${e(d.input.ride_id)}</p><p>現在：${previous?`${e(paymentLabels[previous.payment_status])} / ${previous.amount.toLocaleString('ja-JP')}円`:'未登録'}</p><p>記録する内容：<b>${e(paymentLabels[d.input.payment_status])} / ${d.input.amount.toLocaleString('ja-JP')}円</b></p><p class="hint">台帳への記録のみです。実際の請求・返金を実行しません。予約や記録が変わっている場合は確認し直します。</p>`;
    }
    else if(kind==='offer_open'){
      const plan=d.dependencies[0];$('confirm-title').textContent='この便の引受を提示しますか？';
      $('confirm-details').innerHTML=`<p>${e(plan.context.origin.name)} → ${e(plan.context.destination.name)}</p><p>計画乗車：${e(plannedDate(plan.pickup_at))}<br>計画降車：${e(plannedDate(plan.dropoff_at))}（日本時間）</p><p>${e(plan.vehicle_name)} / 定員${plan.capacity}名</p><p class="hint">停車を確認済みです。利用者が承認して予約すると、空席を確保して担当便へ割り当てます。架空の試験用です。</p>`;
    }
    else if(kind==='offer_close'){$('confirm-title').textContent='この便の受付を終了しますか？';$('confirm-details').innerHTML='<p>以後の候補検索と追加予約を停止します。成立済みの予約は保持し、乗降を記録できます。</p>';}
    else if(kind==='profile_delete')$('confirm-details').innerHTML='<p>利用者情報と規約への同意を削除します。進行中の依頼がある場合は実行できません。</p><p>ログインと委任は失効します。運行履歴・決済情報・操作IDの記録は残ります。</p>';
    else if(kind==='agreements_register')$('confirm-details').innerHTML=d.input.agreements.map(a=>`<p>${e(state.catalog.terms.find(t=>t.id===a.terms_id)?.name||a.terms_id)}</p>`).join('');
    else{const names={first_name:'名',last_name:'姓',first_name_kana:'名（フリガナ）',last_name_kana:'姓（フリガナ）',gender:'性別',birthdate:'生年月日',phone_number:'電話番号',email:'メール',home_address:'住所'};$('confirm-details').innerHTML=Object.entries(d.input).map(([k,v])=>`<p><b>${e(names[k]||k)}</b>：${e(typeof v==='object'?Object.values(v).map(x=>typeof x==='object'?JSON.stringify(x):x).join(' '):v)}</p>`).join('');}
    $('confirm-expiry').textContent=`この確認は ${date(draft.expires_at)}（日本時間）まで有効です。`;
    $('commit').textContent=kind==='profile_delete'?'確認して削除':'確認して保存';$('confirm-dialog').showModal();return;
  }
  const changing=draft.kind==='change';
  const ride=cancelling?state.snapshot.rides.find(r=>r.id===d.ride_id):null;
  $('confirm-title').textContent=cancelling?'この依頼を取り消しますか？':changing?'この内容に変更しますか？':'この内容で依頼しますか？';
  $('confirm-details').innerHTML=`<div class="confirm-route"><small>乗る場所</small>${e(cancelling?ride.origin_name:d.origin_name)}<small>↓ 降りる場所</small>${e(cancelling?ride.destination_name:d.destination_name)}</div><p>${d.passengers}名</p><p>${cancelling?'取消料：':''}${e(fare(cancelling?d.cancellation_fee:d.fare))}</p>${cancelling?'':'<p class="muted">受付後は引受待ちです。ドライバーが引き受けると予約が成立し、車両が割り当てられます。</p>'}`;
  $('confirm-expiry').textContent=`この確認は ${date(draft.expires_at)}（日本時間）まで有効です。`;
  if(cancelling&&ride?.payment?.record?.payment_status==='received'&&ride.payment.record.amount>0)$('confirm-details').insertAdjacentHTML('beforeend','<p class="unknown">受領済みの記録が残ります。予約を取り消しても返金は実行されません。運営担当者による返金確認が必要です。</p>');
  if(changing){const note=$('confirm-details').querySelector('.muted');if(note)note.textContent='変更時にも空席・運賃・受付条件を確認します。条件が変わった場合は、もう一度確認が必要です。';}
  $('commit').textContent=cancelling?'確認して取り消す':changing?'確認して変更':'確認して依頼';$('confirm-dialog').showModal();
}
async function login(username,password){
  if(state.loggingIn)return;
  state.loggingIn=true;state.authEpoch++;
  const controls=[...document.querySelectorAll('[data-login],#login-form button')];controls.forEach(b=>{b.disabled=true;});
  try{signedIn(await api('/api/session',{username,password}));}catch(err){message(err.message,true);}
  finally{state.loggingIn=false;controls.forEach(b=>{b.disabled=false;});}
}
$('login-form').hidden=true;
$('other-login').addEventListener('click',()=>{const expanded=$('login-form').hidden;$('login-form').hidden=!expanded;$('other-login').setAttribute('aria-expanded',String(expanded));if(expanded)$('username').focus();});
$('web-entry').addEventListener('click',event=>{const button=event.target.closest('[data-login]');if(button)login(button.dataset.login,'local-test-only');});
$('login-form').addEventListener('submit',event=>{event.preventDefault();login($('username').value,$('password').value);});
$('ride-filters').addEventListener('click',event=>{const button=event.target.closest('[data-filter]');if(!button)return;state.filter=button.dataset.filter;renderRides();});
$('ride-search').addEventListener('input',renderRides);
$('clear-search').addEventListener('click',()=>{$('ride-search').value='';renderRides();$('ride-search').focus();});
$('swap-stops').addEventListener('click',()=>{if(state.busy||state.pending||$('origin').disabled||$('destination').disabled)return;const origin=$('origin').value;$('origin').value=$('destination').value;$('destination').value=origin;state.candidates=[];$('candidates').replaceChildren();});
$('workspace-nav').addEventListener('click',event=>{const link=event.target.closest('a');if(!link)return;const target=$(link.hash.slice(1));if(target?.tagName==='DETAILS')target.open=true;});
$('request-form').addEventListener('submit',async event=>{event.preventDefault();if(state.pending||state.busy)return;state.busy=true;renderRecovery();try{const input={service_id:$('service').value,origin_stop_id:$('origin').value,destination_stop_id:$('destination').value,passengers:Number($('passengers').value)};if(state.editing)input.ride_id=state.editing;showDraft(await api('/api/drafts/'+(state.editing?'change':'request'),input));}catch(err){message(err.message,true);}finally{state.busy=false;renderRecovery();}});
$('stop-editing').addEventListener('click',()=>{if(!state.busy&&!state.pending)stopEditing();});
async function loadCatalog(){
  const user=state.user?.id;const catalog=await api('/api/catalog');if(state.user?.id!==user)return;
  state.catalog=catalog;
  $('profile-status').textContent=catalog.passenger?'利用者情報を登録済みです。':'利用者情報は未登録です。';
  $('prepare-profile-delete').hidden=!catalog.passenger;
  if(!['profile-last-name','profile-first-name'].includes(document.activeElement?.id)){
    $('profile-last-name').value=catalog.passenger?.last_name||'';$('profile-first-name').value=catalog.passenger?.first_name||'';
  }
  const selected=new Set([...$('terms-list').querySelectorAll('input:checked')].map(x=>x.value));
  const agreed=new Set(catalog.agreements.map(a=>a.terms_id));
  $('terms-list').innerHTML=catalog.terms.length?catalog.terms.map(t=>`<label class="check"><input type="checkbox" value="${e(t.id)}" ${agreed.has(t.id)?'checked disabled':selected.has(t.id)?'checked':''}><span>${e(t.name)}${t.agreement_required?'（利用に同意が必要）':''} ${agreed.has(t.id)?'／同意済み':''} <a href="${e(t.url)}" target="_blank" rel="noopener noreferrer">規約を開く</a></span></label>`).join(''):'<p class="hint">このテスト事業者の規約はまだ登録されていません。</p>';
}
async function prepareCatalog(kind,data){
  if(state.busy||state.pending){message('前の操作の結果を先に確認してください。',true);return;}
  state.busy=true;try{showDraft(await api('/api/drafts/'+kind,data));}catch(err){message(err.message,true);}finally{state.busy=false;renderRecovery();}
}
$('profile-form').addEventListener('submit',event=>{
  event.preventDefault();if(!state.catalog)return;
  const previous=state.catalog.passenger||{};const input=Object.fromEntries(Object.entries(previous).filter(([k])=>!['id','created_at','updated_at'].includes(k)));
  input.first_name=$('profile-first-name').value;input.last_name=$('profile-last-name').value;
  prepareCatalog(previous.id?'profile_update':'profile_create',input);
});
$('prepare-agreements').addEventListener('click',()=>{
  const agreements=[...$('terms-list').querySelectorAll('input:checked:not(:disabled)')].map(x=>({terms_id:x.value,agreed_at:new Date().toISOString()}));
  if(!agreements.length){message('新しく同意する規約を選んでください。',true);return;}
  prepareCatalog('agreements_register',{agreements});
});
$('prepare-profile-delete').addEventListener('click',()=>prepareCatalog('profile_delete',{}));
$('service').addEventListener('change',fillStops);
$('commit').addEventListener('click',()=>{if(state.draft&&!state.busy)mutate(state.draft.kind,{draft_id:state.draft.id,details:state.draft.details});});
$('close-dialog').addEventListener('click',()=>{$('confirm-dialog').close();state.draft=null;});
$('confirm-dialog').addEventListener('cancel',()=>{state.draft=null;});
$('refresh').addEventListener('click',()=>refresh());
function beginPayment(ride){
  if(state.user.role!=='admin'||state.busy||state.pending)return;
  const p=ride.payment;if(!p||p.expected_amount===null||p.review_reason==='refund_review_required')return;
  $('payment-form').dataset.ride=ride.id;
  $('payment-target').textContent=`${ride.origin_name} → ${ride.destination_name} / ${ride.id}`;
  $('payment-amount').value=String(p.expected_amount);
  $('payment-status').value=ride.status==='cancelled'?'cancelled':p.record?.payment_status||(p.expected_amount===0?'excluded':'uncollected');
  $('payment-dialog').showModal();
}
$('close-payment').addEventListener('click',()=>$('payment-dialog').close());
$('payment-form').addEventListener('submit',event=>{
  event.preventDefault();if(state.busy||state.pending)return;
  const input={ride_id:$('payment-form').dataset.ride,amount:Number($('payment-amount').value),payment_status:$('payment-status').value};
  $('payment-dialog').close();prepareCatalog('payment_update',input);
});
$('rides').addEventListener('click',event=>{
  const button=event.target.closest('[data-payment]');if(!button)return;
  const ride=state.snapshot.rides.find(r=>r.id===button.dataset.payment);if(ride)beginPayment(ride);
});
$('rides').addEventListener('click',async event=>{
  const button=event.target.closest('[data-action]');if(!button||state.busy)return;
  if(state.pending){message('前の操作の結果を先に確認してください。',true);return;}
  const kind=button.dataset.action;const ride=state.snapshot.rides.find(r=>r.id===button.dataset.ride);
  if(!ride)return;
  if(kind==='change'){editRide(ride);return;}
  if(kind==='cancel'){button.disabled=true;try{showDraft(await api('/api/drafts/cancel',{ride_id:ride.id}));}catch(err){message(err.message,true);}finally{button.disabled=false;}}
  else{if(!$('stopped').checked){message('安全な場所に停車していることを確認してください。',true);$('stopped').focus();return;}await mutate(kind,{ride_id:ride.id,version:ride.version,stopped:true});}
});
$('reconcile').addEventListener('click',async()=>{if(!state.pending||state.busy)return;try{const result=await api(`/api/operations/${state.pending.body.operation_id}`);state.pending=null;savePending();stopEditing();message(result.current.resource_type?'台帳操作の結果を確認しました。':`保存済みです。現在の状態：${result.current.status_label}`);await refresh();}catch(err){message(err.message,true);}});
$('retry').addEventListener('click',sendPending);
setInterval(()=>{if(state.user&&!state.busy&&!$('confirm-dialog').open&&!document.hidden)refresh();},5000);
window.addEventListener('online',()=>refresh());
const initialAuthEpoch=state.authEpoch;
api('/api/me').then(result=>{if(state.authEpoch===initialAuthEpoch)signedIn(result);}).catch(()=>{});

setInterval(refreshObservationDisplays,1000);
window.addEventListener('offline',()=>{state.observationDisconnected=true;if(state.user)$('connection-notice').hidden=false;refreshObservationDisplays();});
document.addEventListener('visibilitychange',()=>{if(!document.hidden){refreshObservationDisplays();refresh();}});

// Demo-only entry switching; production authentication remains in the server app.
const demoRoleNames={'rider-a1':'user','driver-a1':'driver','admin-a1':'admin'};
const demoSignedIn=signedIn;
signedIn=function(result){
  demoSignedIn(result);
  const role=demoRoleNames[result.user.id];
  const url=new URL(location.href);url.searchParams.set('role',role);url.hash='';history.replaceState(null,'',url);
  document.querySelectorAll('[data-demo-role]').forEach(link=>{if(link.dataset.demoRole===result.user.id)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');});
};
const demoSignedOut=signedOut;
signedOut=function(){demoSignedOut();const url=new URL(location.href);url.searchParams.delete('role');url.hash='';history.replaceState(null,'',url);document.querySelectorAll('[data-demo-role]').forEach(link=>link.removeAttribute('aria-current'));};
$('demo-roles').addEventListener('click',event=>{
  const link=event.target.closest('[data-demo-role]');if(!link)return;event.preventDefault();
  if(state.busy||state.pending||state.loggingIn){message('前の操作の結果を確認してから、役割を切り替えてください。',true);return;}
  if(state.user?.id===link.dataset.demoRole)return;
  signedOut();login(link.dataset.demoRole,'local-test-only');
});
$('reset-demo').addEventListener('click',()=>{if(state.busy||state.pending){message('操作の結果を照合してから、最初に戻してください。',true);return;}$('reset-dialog').showModal();});
$('reset-back').addEventListener('click',()=>$('reset-dialog').close());
$('reset-confirm').addEventListener('click',async()=>{
  if(state.busy)return;state.busy=true;$('reset-confirm').disabled=true;
  try{await api('/demo/reset',{});for(let i=sessionStorage.length-1;i>=0;i--){const key=sessionStorage.key(i);if(key.startsWith('yoko-demo-pending:v1:'))sessionStorage.removeItem(key);}
    $('reset-dialog').close();signedOut();message('デモを初期状態に戻しました。入口を選んで体験できます。');
  }catch(error){message('初期化できませんでした。'+error.message,true);}
  finally{state.busy=false;$('reset-confirm').disabled=false;}
});
window.addEventListener('popstate',()=>{const actor=Object.keys(demoRoleNames).find(id=>demoRoleNames[id]===new URL(location.href).searchParams.get('role'));if(!state.busy&&!state.pending&&actor&&state.user?.id!==actor){signedOut();login(actor,'local-test-only');}});

// Alternative input surface; all reservations still use the shared form/Core.
const journey=window.YokoJourney.create({getState:()=>state,notify:message});
const journeySignedIn=signedIn;
signedIn=function(result){journeySignedIn(result);journey.enter(result.user);if(result.user.role==='rider'){$('workspace-nav').innerHTML='<a href="#journey-panel">地図・チャットで呼ぶ</a><a href="#rides-section">依頼の状況</a>';}};
const journeySignedOut=signedOut;
signedOut=function(){journeySignedOut();journey.leave();};
const journeyRender=render;
render=function(){journeyRender();journey.sync();};
const journeyRecovery=renderRecovery;
renderRecovery=function(){journeyRecovery();journey.renderSelection();};
const journeyEdit=editRide;
editRide=function(ride){journeyEdit(ride);journey.edit(ride);};
const journeyDraft=showDraft;
showDraft=function(draft){journeyDraft(draft);journey.renderSelection();};
$('confirm-dialog').addEventListener('close',()=>journey.renderSelection());

// Manual-inspired operation surfaces. Roles, versions and mutations remain in Core.
function showOperationRecord(id){state.filter='all';$('ride-search').value=id;renderRides();$('rides-section').scrollIntoView({block:'start',behavior:'smooth'});}
const driverConsole=window.YokoDriver.create({getState:()=>state,notify:message,perform:async(kind,ride)=>{await mutate(kind,{ride_id:ride.id,version:ride.version,stopped:true});if(state.user)await refresh();},setHistory:showOperationRecord});
const adminConsole=window.YokoAdmin.create({getState:()=>state,showRecord:showOperationRecord});
const operationsSignedIn=signedIn;
signedIn=function(result){operationsSignedIn(result);driverConsole.enter(result.user);adminConsole.enter(result.user);if(result.user.role==='driver'){state.filter='history';$('role-title').textContent='ドライバー運行画面';}if(result.user.role==='admin')$('role-title').textContent='運行を見守る';};
const operationsSignedOut=signedOut;
signedOut=function(){driverConsole.leave();adminConsole.leave();operationsSignedOut();};
const operationsRender=render;
render=function(){operationsRender();driverConsole.sync();adminConsole.sync();};
const operationsRecovery=renderRecovery;
renderRecovery=function(){operationsRecovery();driverConsole.controls();adminConsole.controls();};
