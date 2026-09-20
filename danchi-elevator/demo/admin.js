/* Administrative read-only overview. Existing records/payment controls stay below. */
(function(){
  'use strict';
  const $=id=>document.getElementById(id),O=window.YokoOps;
  window.YokoAdmin={create({getState,showRecord}){
    let active=false,filter={kind:'requested'},selectedId=null;
    const rides=()=>getState().snapshot?.rides||[],stops=()=>getState().snapshot?.services.flatMap(s=>s.stops.filter(t=>t.active))||[];
    const map=O.mapView({id:'admin-map',errorId:'admin-map-error',onPick:id=>{filter={kind:'stop',value:id};selectedId=null;sync();O.say('admin-chat-log',`${stops().find(s=>s.id===id)?.name}の依頼を表示しました。`);}});
    function html(id,content){if($(id).innerHTML===content)return;const focused=document.activeElement?.dataset.adminRide;$(id).innerHTML=content;if(focused)[...$(id).querySelectorAll('[data-admin-ride]')].find(b=>b.dataset.adminRide===focused)?.focus({preventScroll:true});}
    function sync(){
      if(!active||getState().user?.role!=='admin'||!getState().snapshot)return;
      const all=rides(),snap=getState().snapshot,waiting=all.filter(r=>['requested','assigned','arrived'].includes(r.status));
      $('admin-waiting-orders').innerHTML=all.filter(r=>r.status==='requested').length+'<small>件</small>';$('admin-waiting-people').innerHTML=waiting.reduce((n,r)=>n+r.passengers,0)+'<small>名</small>';
      $('admin-onboard').textContent=all.filter(r=>r.status==='onboard').reduce((n,r)=>n+r.passengers,0)+'名';$('admin-completed').textContent=snap.counts.completed+'件';$('admin-cancelled').textContent=snap.counts.cancelled+'件';
      const found=all.filter(r=>O.matches(r,filter)).sort((a,b)=>Number(O.terminal(a))-Number(O.terminal(b)));const selected=found.find(r=>r.id===selectedId)||found.find(r=>!O.terminal(r))||null;
      const label=filter.kind==='stop'?stops().find(s=>s.id===filter.value)?.name:filter.kind==='receipt'?'受付番号 '+filter.value:({all:'すべて',requested:'引受待ち',running:'運行中',history:'完了・取消'}[filter.kind]);$('admin-result-label').textContent=`${label} / ${found.length}件`;
      html('admin-result-list',found.length?found.map(r=>`<button class="admin-result" type="button" data-admin-ride="${O.esc(r.id)}"><span class="admin-result-top"><b class="driver-status">${O.status[r.status]}</b><strong>${r.passengers}名</strong></span><span class="admin-result-route">${O.esc(r.origin_name)} <span>→</span> ${O.esc(r.destination_name)}</span><span class="admin-result-foot">${O.esc(r.id.slice(-8))} / ${O.vehicle(r.vehicle_id)} <b>記録を見る →</b></span></button>`).join(''):'<p class="driver-empty">該当する依頼はありません。</p>');
      html('admin-fleet-list',snap.vehicles.map(v=>{const onboard=all.filter(r=>r.vehicle_id===v.id&&r.status==='onboard').reduce((n,r)=>n+r.passengers,0);return `<article class="admin-vehicle"><h3>${O.vehicle(v.id)}</h3><dl><div><dt>確保済み / 定員</dt><dd>${v.reserved} / ${v.capacity}<small>名</small></dd></div><div><dt>乗車中</dt><dd>${onboard}<small>名</small></dd></div></dl><p>${v.accepting?'追加引受の受付中':'追加引受を停止中'}</p><p class="admin-vehicle-note">現在位置・到着予測：未取得</p></article>`;}).join(''));
      $('admin-quick-filters').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.adminFilter===filter.kind)));
      map.draw(stops(),all,selected);controls();
    }
    function controls(){if(!active)return;const locked=getState().busy||!!getState().pending;$('admin-chat-input').disabled=locked;$('admin-chat-send').disabled=locked;}
    function enter(user){leave();if(user.role!=='admin')return;active=true;document.body.classList.add('admin-ui');$('admin-panel').hidden=false;$('admin-chat-log').replaceChildren();O.say('admin-chat-log','地図のピンか、場所名・受付番号で依頼を確認できます。「処理待ち」と入力すると、引受待ちを表示します。');}
    function leave(){active=false;filter={kind:'requested'};selectedId=null;document.body.classList.remove('admin-ui');$('admin-panel').hidden=true;}
    $('admin-map-fit').addEventListener('click',map.fit);$('admin-show-all').addEventListener('click',()=>{filter={kind:'all'};selectedId=null;sync();});
    $('admin-quick-filters').addEventListener('click',event=>{const button=event.target.closest('[data-admin-filter]');if(!button)return;filter={kind:button.dataset.adminFilter};selectedId=null;sync();});
    $('admin-result-list').addEventListener('click',event=>{const b=event.target.closest('[data-admin-ride]');if(!b||getState().busy||getState().pending)return;selectedId=b.dataset.adminRide;sync();showRecord(selectedId);});
    $('admin-chat-form').addEventListener('submit',event=>{event.preventDefault();if(getState().busy||getState().pending)return;const text=$('admin-chat-input').value.trim();if(!text)return;$('admin-chat-input').value='';O.say('admin-chat-log',text,'user');const next=O.find(text,stops());if(next.kind==='unknown'){O.say('admin-chat-log','登録された場所名、受付番号、または「処理待ち」「運行中」「履歴」で確認できます。');return;}filter=next;selectedId=null;sync();O.say('admin-chat-log',$('admin-result-label').textContent+'。選んだ依頼から詳細な記録を確認できます。');});
    return {enter,leave,sync,controls};
  }};
})();
