/* Driver presentation. Every mutation goes through the original app/Core. */
(function(){
  'use strict';
  const $=id=>document.getElementById(id),O=window.YokoOps;
  const steps={requested:{kind:'accept',label:'引き受ける',step:1,prompt:'乗車場所・降車場所・人数を確認して引き受けてください。',confirm:'この依頼を引き受けますか？',note:'確定すると担当車両が割り当てられます。'},assigned:{kind:'arrive',label:'到着通知',step:2,prompt:'乗車場所に着いたら、安全に停車して到着を知らせます。',confirm:'乗車場所への到着を記録しますか？',note:'指定された場所に到着し、利用者を迎えられる状態か確認してください。'},arrived:{kind:'board',label:'乗車を確認',step:3,prompt:'乗る方・人数・行き先を確かめ、乗車を確認してください。',confirm:'乗車を記録しますか？',note:'表示された人数が乗車したことを確認してください。'},onboard:{kind:'complete',label:'降車',step:4,prompt:'降車場所に着いたら、全員が降りたことを目視で確認します。',confirm:'降車を記録して完了しますか？',note:'全員の降車と、車内の忘れ物を確認してください。'}};
  window.YokoDriver={create({getState,notify,perform,setHistory}){
    let active=false,selectedId=null,pendingAction=null,lastKey='';
    const historyParent=$('rides-section').parentElement,historyNext=$('rides-section').nextElementSibling;
    const rides=()=>getState().snapshot?.rides||[];
    const selected=()=>rides().find(r=>r.id===selectedId&&!O.terminal(r));
    const stops=()=>getState().snapshot?.services.flatMap(s=>s.stops.filter(t=>t.active))||[];
    const busy=()=>getState().busy||!!getState().pending||getState().user?.role!=='driver';
    const map=O.mapView({id:'driver-map',errorId:'driver-map-error',onPick:id=>choosePlace(id)});
    function setHtml(id,html){if($(id).innerHTML!==html){const focused=document.activeElement?.dataset.driverSelect;$(id).innerHTML=html;if(focused)[...$(id).querySelectorAll('[data-driver-select]')].find(b=>b.dataset.driverSelect===focused)?.focus({preventScroll:true});}}
    function pick(id,scroll=true){if(busy())return;const ride=rides().find(r=>r.id===id);if(!ride)return;
      if(O.terminal(ride)){setHistory(ride.id);$('driver-history').open=true;$('driver-history').scrollIntoView({block:'start',behavior:'smooth'});return;}
      selectedId=id;$('stopped').checked=false;sync();if(scroll)$('driver-operation').scrollIntoView({block:'start',behavior:'smooth'});
    }
    function choosePlace(id){const matches=rides().filter(r=>!O.terminal(r)&&(r.origin_stop_id===id||r.destination_stop_id===id));if(!matches.length){notify('この場所を乗降する進行中の依頼はありません。');return;}pick(matches.find(r=>r.id===selectedId)?.id||matches[0].id,false);O.say('driver-chat-log',`${stops().find(s=>s.id===id)?.name}の依頼は${matches.length}件です。操作する依頼を選べます。`,'guide',matches.map(r=>({id:r.id,label:`${r.id.slice(-8)} / ${r.passengers}名 / ${O.status[r.status]}`})));}
    function controls(){
      if(!active)return;const ride=selected(),step=ride&&steps[ride.status],blocked=busy();
      $('driver-next').disabled=blocked||!step;$('driver-next').textContent=step?.label||'依頼を選んでください';
      $('driver-action-confirm').disabled=blocked||!pendingAction;
      $('driver-chat-input').disabled=blocked;$('driver-chat-send').disabled=blocked;
      $('driver-exceptions').querySelectorAll('button').forEach(b=>b.disabled=blocked);
      $('driver-action-hint').textContent=getState().pending?'前の操作の結果を照合してください。':'次の確認画面で確定します。';
    }
    function sync(){
      if(!active||getState().user?.role!=='driver'||!getState().snapshot)return;
      const snap=getState().snapshot,live=rides().filter(r=>!O.terminal(r)),waiting=live.filter(r=>r.status==='requested').sort((a,b)=>a.created_at.localeCompare(b.created_at)),running=live.filter(r=>r.status!=='requested');
      if(pendingAction){const r=rides().find(r=>r.id===pendingAction.id);if(!r||r.version!==pendingAction.version||r.status!==pendingAction.status){pendingAction=null;$('driver-action-dialog').close();$('stopped').checked=false;notify('依頼の内容が更新されました。最新の場所・人数・状態を確認してください。',true);}}
      if(!selected())selectedId=running[0]?.id||waiting[0]?.id||null;
      const ride=selected(),step=ride&&steps[ride.status],v=snap.vehicles[0];
      $('driver-area').textContent=snap.services.map(s=>s.name).join(' / ');$('driver-vehicle').textContent=v?O.vehicle(v.id):'担当なし';$('driver-seats').textContent=v?`${Math.max(0,v.capacity-v.reserved)} / ${v.capacity}名`:'—';
      $('driver-total').textContent=live.length+'件';$('driver-queue-count').textContent=waiting.length+'件';$('driver-requested-count').innerHTML=waiting.length+'<small>件</small>';$('driver-active-count').innerHTML=running.length+'<small>件</small>';
      setHtml('driver-queue-list',waiting.length?waiting.map(r=>`<button class="driver-request" type="button" data-driver-select="${O.esc(r.id)}" aria-pressed="${r.id===selectedId}"><span class="driver-request-top"><span>受付 ${O.time(r.created_at)}</span><strong>${r.passengers}名</strong></span><span class="driver-request-route"><b>${O.esc(r.origin_name)}</b><span>→</span><b>${O.esc(r.destination_name)}</b></span><span class="driver-request-foot"><span>${O.esc(r.id.slice(-8))}</span><span>内容を確認 →</span></span></button>`).join(''):'<p class="driver-empty">引受待ちの依頼はありません。</p>');
      $('driver-confirmed-count').textContent=`${running.length}件 / ${running.reduce((n,r)=>n+r.passengers,0)}名`;
      setHtml('driver-runs',running.length?running.map(r=>`<article class="driver-run ${r.id===selectedId?'selected':''}"><div class="driver-run-heading"><span class="driver-status">${O.status[r.status]}</span><span>${O.esc(r.id.slice(-8))} / ${O.vehicle(r.vehicle_id)}</span></div><div class="driver-route-pair"><button type="button" class="driver-leg ${r.status==='onboard'?'done':''}" data-driver-select="${O.esc(r.id)}" ${r.status!=='onboard'?'aria-current="step"':''}><small>${r.status==='onboard'?'乗車済み':'乗車場所'}</small><b>${O.esc(r.origin_name)}</b><span>${r.passengers}名</span></button><button type="button" class="driver-leg dropoff" data-driver-select="${O.esc(r.id)}" ${r.status==='onboard'?'aria-current="step"':''}><small>降車場所</small><b>${O.esc(r.destination_name)}</b><span>${r.passengers}名</span></button></div></article>`).join(''):'<p class="driver-empty">引き受けると、ここに乗車・降車の順で表示されます。</p>');
      $('driver-operation-prompt').textContent=step?.prompt||'処理待ちの依頼を選んでください。';$('driver-selected-status').textContent=ride?O.status[ride.status]:'';setHtml('driver-selected-route',ride?O.route(ride):'');
      $('driver-exceptions').hidden=!ride||!['assigned','arrived'].includes(ride.status);
      $('driver-panel').querySelectorAll('[data-driver-step]').forEach(n=>{if(Number(n.dataset.driverStep)===step?.step)n.setAttribute('aria-current','step');else n.removeAttribute('aria-current');});
      const key=ride?ride.id+':'+ride.version:'';if(key!==lastKey){lastKey=key;$('stopped').checked=false;}
      map.draw(stops(),live,ride);controls();
    }
    function review(expected){
      if(busy())return;const r=selected(),step=r&&steps[r.status];if(!step)return;
      if(expected&&expected!==step.kind){O.say('driver-chat-log','いまの状態ではその操作はできません。画面に表示された次の操作を確認してください。');return;}
      if(!$('stopped').checked){notify('安全な場所に停車していることを確認してください。',true);$('stopped').focus();return;}
      pendingAction={id:r.id,version:r.version,status:r.status,kind:step.kind};$('driver-action-title').textContent=step.confirm;$('driver-action-details').innerHTML=O.route(r);$('driver-action-confirm-note').textContent=step.note;$('driver-action-confirm').textContent=step.kind==='accept'?'確認して引き受ける':step.kind==='arrive'?'到着を記録する':step.kind==='board'?'乗車を記録する':'降車を記録する';controls();$('driver-action-dialog').showModal();
    }
    function enter(user){leave();if(user.role!=='driver')return;active=true;document.body.classList.add('driver-ui');$('driver-panel').hidden=false;$('driver-history-slot').append($('rides-section'));$('driver-history').open=false;$('rides-title').textContent='受付・運行の記録';$('driver-chat-log').replaceChildren();O.say('driver-chat-log','場所名や受付番号で依頼を探せます。「中央広場の依頼」のように入力してください。');controls();}
    function leave(){active=false;selectedId=null;pendingAction=null;lastKey='';document.body.classList.remove('driver-ui');$('driver-panel').hidden=true;$('driver-action-dialog').close();$('driver-help-dialog').close();if($('rides-section').parentElement!==historyParent)historyParent.insertBefore($('rides-section'),historyNext);}
    $('driver-panel').addEventListener('click',event=>{const select=event.target.closest('[data-driver-select],[data-ops-ride]');if(select)pick(select.dataset.driverSelect||select.dataset.opsRide);});
    $('driver-map-fit').addEventListener('click',map.fit);$('driver-next').addEventListener('click',()=>review());
    $('driver-action-back').addEventListener('click',()=>{$('driver-action-dialog').close();pendingAction=null;});$('driver-action-dialog').addEventListener('cancel',()=>{pendingAction=null;});
    $('driver-action-confirm').addEventListener('click',async()=>{if(busy()||!pendingAction)return;const task=pendingAction,r=selected();if(!$('stopped').checked||!r||r.id!==task.id||r.version!==task.version||r.status!==task.status){pendingAction=null;$('driver-action-dialog').close();notify('依頼の内容と停車状態を確認し直してください。',true);return;}pendingAction=null;$('driver-action-dialog').close();await perform(task.kind,r);$('stopped').checked=false;sync();});
    $('driver-exceptions').addEventListener('click',event=>{const b=event.target.closest('[data-driver-help]'),r=selected();if(!b||!r||busy())return;$('driver-help-title').textContent=b.dataset.driverHelp==='capacity'?'乗せられないとき':'乗せる人がいないとき';$('driver-help-route').textContent=`${r.origin_name} → ${r.destination_name} / ${r.passengers}名`;$('driver-help-message').textContent=b.dataset.driverHelp==='capacity'?'空席、担当車両、乗車条件を再確認してください。無理に乗せず、運営の指示を確認します。':'乗車場所、人数、受付番号を再確認してください。利用者の乗車や降車として記録せず、運営の指示を確認します。';$('driver-help-dialog').showModal();});$('driver-help-close').addEventListener('click',()=>$('driver-help-dialog').close());
    $('driver-chat-form').addEventListener('submit',event=>{event.preventDefault();if(busy())return;const text=$('driver-chat-input').value.trim();if(!text)return;$('driver-chat-input').value='';O.say('driver-chat-log',text,'user');const action={'引き受ける':'accept','到着通知':'arrive','乗車確認':'board','乗車を確認':'board','降車':'complete'}[text.normalize('NFKC')];if(action){review(action);return;}
      const filter=O.find(text,stops());if(filter.kind==='unknown'){O.say('driver-chat-log','登録された場所名、受付番号、または「処理待ち」「運行中」「履歴」で探せます。');return;}
      const found=rides().filter(r=>O.matches(r,filter)).sort((a,b)=>Number(O.terminal(a))-Number(O.terminal(b)));O.say('driver-chat-log',found.length?`${found.length}件あります。操作・確認する依頼を選んでください。`:'該当する依頼はありません。','guide',found.slice(0,8).map(r=>({id:r.id,label:`${r.origin_name} → ${r.destination_name} / ${r.passengers}名 / ${r.id.slice(-8)}`})));
    });
    return {enter,leave,sync,controls};
  }};
})();
