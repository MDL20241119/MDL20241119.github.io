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
