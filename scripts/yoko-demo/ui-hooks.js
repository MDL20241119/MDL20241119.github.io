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
const journey=window.YokoJourney.create({getState:()=>state,notify:message,onSelection:selection=>experience.refreshSelection(selection)});
const journeySignedIn=signedIn;
signedIn=function(result){journeySignedIn(result);journey.enter(result.user);if(result.user.role==='rider'){$('workspace-nav').innerHTML='<a href="#map-title">地図で選ぶ</a><a href="#chat-title">チャットで入力</a>';}};
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
function showOperationRecord(id){state.filter='all';$('ride-search').value=id;renderRides();experience.open('records');$('rides-section').scrollIntoView({block:'start',behavior:'smooth'});}
const driverConsole=window.YokoDriver.create({getState:()=>state,notify:message,perform:async(kind,ride)=>{await mutate(kind,{ride_id:ride.id,version:ride.version,stopped:true});if(state.user)await refresh();},setHistory:showOperationRecord,onSelect:()=>experience.open('operation'),preferredRide:()=>experience.preferredRide()});
const adminConsole=window.YokoAdmin.create({getState:()=>state,showRecord:showOperationRecord});
const operationsSignedIn=signedIn;
signedIn=function(result){operationsSignedIn(result);driverConsole.enter(result.user);adminConsole.enter(result.user);if(result.user.role==='driver'){state.filter='history';$('role-title').textContent='ドライバー運行画面';$('workspace-nav').innerHTML='<a href="#driver-map-title">地図で選ぶ</a><a href="#driver-chat-title">チャットで探す</a>';}if(result.user.role==='admin'){$('role-title').textContent='運行を見守る';$('workspace-nav').innerHTML='<a href="#admin-map-title">地図で見る</a><a href="#admin-chat-title">チャットで確認</a>';}};
const operationsSignedOut=signedOut;
signedOut=function(){driverConsole.leave();adminConsole.leave();operationsSignedOut();};
const operationsRender=render;
render=function(){operationsRender();driverConsole.sync();adminConsole.sync();};
const operationsRecovery=renderRecovery;
renderRecovery=function(){operationsRecovery();driverConsole.controls();adminConsole.controls();};

// One manual-style experience shares the same inputs and Core records.
const experience=window.YokoExperience.create({getState:()=>state});
const experienceSignedIn=signedIn;
signedIn=function(result){experienceSignedIn(result);experience.enter(result.user);};
const experienceSignedOut=signedOut;
signedOut=function(){experience.leave();experienceSignedOut();};
const experienceRender=render;
render=function(){experienceRender();experience.sync();};
const experienceRecovery=renderRecovery;
renderRecovery=function(){experienceRecovery();experience.refreshSelection();};
const experienceEdit=editRide;
editRide=function(ride){experienceEdit(ride);experience.open('review');};
