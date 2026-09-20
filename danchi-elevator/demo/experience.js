/* Manual-based demo guidance. Input and all writes still use the original Core UI. */
(function(){
  'use strict';
  const $=id=>document.getElementById(id),key='yoko-demo-experience:ride';
  const finished=r=>['completed','cancelled'].includes(r.status);
  window.YokoExperience={create({getState}){
    let role=null,selection={},lastActive=null,first=true,tracked=null;
    const records=$('rides-section'),home=$('work-grid');
    const recordTools=document.createElement('details');recordTools.id='record-tools';recordTools.className='manual-details';recordTools.innerHTML='<summary>表示範囲・受付番号で探す</summary>';$('ride-filters').before(recordTools);
    for(const node of [$('ride-filters'),records.querySelector('.search-label'),records.querySelector('.ride-search'),$('ride-count')])recordTools.append(node);
    const riderRecords=document.createElement('details');riderRecords.id='rider-records';riderRecords.className='manual-details';riderRecords.hidden=true;
    riderRecords.innerHTML='<summary>いまの依頼・これまでの履歴</summary>';$('journey-panel').after(riderRecords);
    const adminRecords=document.createElement('details');adminRecords.id='admin-records';adminRecords.className='manual-details';adminRecords.hidden=true;
    adminRecords.innerHTML='<summary>依頼の詳しい記録・決済情報</summary>';home.before(adminRecords);adminRecords.append(home);
    const next=document.createElement('section');next.id='experience-next';next.className='experience-next';next.hidden=true;
    next.innerHTML='<div><span class="experience-tag">3つの役割を体験</span><p id="experience-next-text"></p></div><button id="experience-next-button" class="secondary" type="button"></button>';$('workspace-nav').after(next);
    const dock=document.createElement('div');dock.id='user-action-dock';dock.className='user-action-dock';dock.hidden=true;
    dock.innerHTML='<p id="user-action-caption" aria-live="polite"></p><button id="user-next" class="primary" type="button" disabled>乗る場所を選ぶ</button>';
    document.body.append(dock);
    function preferredRide(){try{return localStorage.getItem(key);}catch{return tracked;}}
    function remember(id){tracked=id;try{localStorage.setItem(key,id);}catch{/* Navigation still works without optional storage. */}}
    function go(node){node.scrollIntoView({block:'start',behavior:'auto'});const title=node.matches('h1,h2,h3')?node:node.querySelector('h1,h2,h3,summary');if(title){title.setAttribute('tabindex','-1');title.focus({preventScroll:true});}}
    function open(target){
      if(target==='review'&&role==='rider'){$('journey-selection-details').open=true;go($('journey-selection-details'));return true;}
      if(target==='operation'&&role==='driver'){go($('driver-operation'));return true;}
      if(target==='records'){
        if(role==='driver'){$('driver-history').open=true;go($('driver-history'));}
        else if(role==='admin'){adminRecords.open=true;go(adminRecords);}
        else{riderRecords.open=true;go(riderRecords);}return true;
      }
      return false;
    }
    function enter(user){
      leave();role=user.role;document.body.classList.add('manual-experience');document.body.dataset.experienceRole=role;first=true;lastActive=null;
      dock.hidden=role!=='rider';riderRecords.hidden=role!=='rider';adminRecords.hidden=role!=='admin';
      if(role==='rider'){riderRecords.append(records);riderRecords.open=false;$('journey-selection-details').open=false;}
      if(role==='admin')adminRecords.open=false;
      $('driver-chat-details').open=false;$('admin-chat-details').open=false;refreshSelection();
    }
    function leave(){
      if(riderRecords.contains(records))home.append(records);
      role=null;selection={};next.hidden=true;dock.hidden=true;riderRecords.hidden=true;adminRecords.hidden=true;
      document.body.classList.remove('manual-experience','is-typing','has-user-action');delete document.body.dataset.experienceRole;delete document.body.dataset.hasActive;
    }
    function refreshSelection(value){
      if(value)selection=value;
      const s=getState();$('experience-next-button').disabled=!!s.busy||!!s.pending;
      if(role!=='rider')return;
      const active=s.snapshot?.rides.find(r=>!finished(r)),locked=!!s.busy||!!s.pending||!s.snapshot;
      dock.hidden=!active&&!(selection.origin&&selection.destination&&selection.passengers);
      document.body.classList.toggle('has-user-action',!dock.hidden);
      const stops=s.snapshot?.services.flatMap(service=>service.stops)||[],name=id=>stops.find(stop=>stop.id===id)?.name||'未選択';
      $('journey-example').disabled=locked||!!(active&&!s.editing);
      $('user-next').disabled=locked;
      $('user-next').textContent=active&&!s.editing?'依頼の状況を見る':!selection.origin?'① 乗る場所を選ぶ':!selection.destination?'② 降りる場所を選ぶ':!selection.passengers?'③ 人数を選ぶ':s.editing?'変更内容を確認する →':'内容を確認する →';
      $('user-action-caption').textContent=active&&!s.editing?`${active.origin_name} → ${active.destination_name} / ${active.passengers}人`:selection.origin?`${name(selection.origin)} → ${name(selection.destination)}${selection.passengers?' / '+selection.passengers+'人':''}`:'地図をタップ、またはチャットで入力';
    }
    function sync(){
      const s=getState();if(!role||s.user?.role!==role||!s.snapshot)return;
      const active=s.snapshot.rides.find(r=>!finished(r));
      if(role==='rider'){
        document.body.dataset.hasActive=String(!!active);
        if(active){remember(active.id);riderRecords.open=true;if(!first&&!lastActive)go($('journey-status'));}
        lastActive=active?.id||null;
      }
      const ride=s.snapshot.rides.find(r=>r.id===preferredRide());
      next.hidden=true;$('experience-next-button').disabled=!!s.busy||!!s.pending;
      if(role==='rider'&&ride?.status==='requested'){
        next.hidden=false;$('experience-next-text').textContent='依頼できました。次はドライバー役で、この依頼を引き受けてみましょう。';
        $('experience-next-button').textContent='ドライバー用で引き受ける';$('experience-next-button').dataset.actor='driver-a1';
      }else if(role==='driver'&&ride&&finished(ride)){
        next.hidden=false;$('experience-next-text').textContent=ride.status==='completed'?'降車まで記録できました。管理者の画面でも確認できます。':'この体験の依頼は取り消されています。管理者の画面で記録を確認できます。';
        $('experience-next-button').textContent='管理者用で確認する';$('experience-next-button').dataset.actor='admin-a1';
      }else if(role==='admin'&&ride){
        next.hidden=false;$('experience-next-text').textContent=`今回の体験：${ride.origin_name} → ${ride.destination_name} / ${ride.passengers}人 / ${YokoOps.status[ride.status]}`;
        $('experience-next-button').textContent='この依頼の記録を見る';delete $('experience-next-button').dataset.actor;
      }
      first=false;refreshSelection();
    }
    $('user-next').addEventListener('click',()=>{
      const s=getState();if(s.busy||s.pending||!s.snapshot||role!=='rider')return;
      if(s.snapshot.rides.some(r=>!finished(r))&&!s.editing){open('records');return;}
      if(!selection.origin||!selection.destination){go(document.querySelector('.map-panel'));return;}
      if(!selection.passengers){go(document.querySelector('.chat-panel'));$('journey-choices').querySelector('button')?.focus({preventScroll:true});return;}
      if(!$('journey-confirm').disabled)$('journey-confirm').click();
    });
    $('journey-example').addEventListener('click',()=>{if($('journey-chat-input').disabled)return;$('journey-chat-input').value='中央広場から駅前へ1人';$('journey-chat-form').requestSubmit();go(document.querySelector('.chat-panel'));});
    $('experience-next-button').addEventListener('click',()=>{
      const s=getState();if(s.busy||s.pending)return;const actor=$('experience-next-button').dataset.actor;
      if(actor){$('demo-roles').querySelector(`[data-demo-role="${actor}"]`).click();return;}
      if(role==='admin'){const ride=s.snapshot?.rides.find(r=>r.id===preferredRide());if(ride){$('ride-search').value=ride.id;$('ride-filters').querySelector('[data-filter=all]').click();open('records');}}
    });
    for(const id of ['summary-origin','summary-destination'])$(id).addEventListener('click',()=>go(document.querySelector('.map-panel')));
    document.addEventListener('focusin',event=>{if(role==='rider'&&event.target===$('journey-chat-input'))document.body.classList.add('is-typing');});
    document.addEventListener('focusout',()=>queueMicrotask(()=>{if(document.activeElement!==$('journey-chat-input'))document.body.classList.remove('is-typing');}));
    for(const id of ['journey-chat-form','driver-chat-form','admin-chat-form'])$(id).addEventListener('submit',()=>$(id).querySelector('input').blur());
    return {enter,leave,sync,refreshSelection,open,preferredRide};
  }};
})();
