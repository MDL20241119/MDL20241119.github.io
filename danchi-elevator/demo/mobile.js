/* Phone navigation is a presentation layer. All inputs and records stay in Core's original UI. */
(function(){
  'use strict';
  const $=id=>document.getElementById(id);
  const icons={map:'<path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3Z"/><path d="M9 3v15M15 6v15"/>',chat:'<path d="M21 11a8 8 0 0 1-8 8H8l-5 3V11a9 9 0 0 1 18 0Z"/><path d="M7 10h10M7 14h6"/>',review:'<rect x="5" y="3" width="14" height="18" rx="1"/><path d="m8 12 3 3 5-6"/>',rides:'<path d="M6 3v14a4 4 0 0 0 8 0V7"/><circle cx="6" cy="3" r="2"/><circle cx="14" cy="5" r="2"/>',queue:'<path d="M9 5h12M9 12h12M9 19h12"/><circle cx="3" cy="5" r="1"/><circle cx="3" cy="12" r="1"/><circle cx="3" cy="19" r="1"/>',drive:'<path d="m5 8 2-5h10l2 5 2 3v7H3v-7Z"/><path d="M5 8h14M6 18v3M18 18v3M6 13h2M16 13h2"/>',overview:'<path d="M4 21V11h4v10M10 21V3h4v18M16 21V7h4v14"/>',records:'<rect x="4" y="3" width="16" height="18" rx="1"/><path d="M8 8h8M8 12h8M8 16h5"/>'};
  const configs={
    rider:{default:'map',tabs:[['map','地図','地図で場所を選ぶ','乗る場所 → 降りる場所の順にタップ'],['chat','チャット','チャットで入力','場所の名前と人数を送ってください'],['review','内容確認','場所と人数を確認','最後の確認で、依頼が送られます'],['rides','依頼状況','あなたの依頼','進み具合・内容変更・取消はこちら']],parts:{'.journey-heading':[],'.journey-steps':['review','rides'],'#journey-status':['rides'],'.journey-grid':['map','chat'],'.map-panel':['map'],'.chat-panel':['chat'],'.journey-summary':['review'],'#mobile-continue':['map','chat'],'#work-grid':['rides'],'#offers-panel':['rides']}},
    driver:{default:'queue',tabs:[['queue','受付','届いている依頼','依頼を選んで、乗降場所を確認'],['drive','運行','次の操作を確認','安全な場所に停車して操作してください'],['map','地図','乗降場所を確認','ピンから、その場所の依頼を選べます'],['chat','チャット','チャットで探す','場所の名前・受付番号で探せます']],parts:{'.driver-context':['drive'],'.driver-flow':['drive'],'.driver-board':['queue','map'],'.driver-board .driver-map-panel':['map'],'.driver-queue-column':['queue'],'.driver-confirmed':['drive'],'#driver-operation':['drive'],'.driver-chat':['chat'],'#driver-history':['queue'],'#mobile-driver-selection':['map'],'#offer-panel':['queue'],'#offers-panel':['queue']}},
    admin:{default:'overview',tabs:[['overview','状況','いまの運行状況','待っている人と、車両の状況を確認'],['map','地図','地域を地図で見る','ピンを押すと、下に依頼が表示されます'],['chat','チャット','チャットで確認','場所・状態・受付番号で探せます'],['records','依頼一覧','依頼・運行の記録','受付番号で探し、詳しい記録を確認']],parts:{'.admin-board':['overview','map'],'.admin-board .driver-map-panel':['map'],'.admin-overview':['overview'],'.admin-find-grid':['map','chat'],'.admin-chat':['chat'],'.admin-results':['map','chat'],'.admin-fleet':['overview'],'#work-grid':['records']}}
  };
  window.YokoMobile={create({getState}){
    const media=window.matchMedia?.('(max-width: 700px)')||{matches:false};
    let role=null,view=null,firstSnapshot=true,activeId=null,parts=[],selection=null;
    const heading=document.createElement('div');heading.id='mobile-heading';heading.className='mobile-heading';heading.hidden=true;
    heading.innerHTML='<div><p id="mobile-section-label" class="mobile-section-label"></p><h1 id="mobile-view-title" tabindex="-1"></h1><p id="mobile-view-help"></p></div><button id="mobile-refresh" type="button" aria-label="最新の状況に更新">↻</button>';
    $('workspace-nav').after(heading);
    const nav=document.createElement('nav');nav.id='mobile-nav';nav.className='mobile-nav';nav.setAttribute('aria-label','スマートフォンの画面切り替え');nav.hidden=true;document.body.append(nav);
    function clearParts(){parts.forEach(node=>node.removeAttribute('data-mobile-hidden'));parts=[];}
    function setView(next,{scroll=false,focus=false}={}){
      const config=configs[role];if(!config||!config.tabs.some(t=>t[0]===next))return false;
      view=next;document.body.dataset.mobileView=next;
      clearParts();
      for(const [selector,views]of Object.entries(config.parts))for(const node of document.querySelectorAll(selector)){parts.push(node);if(!views.includes(view))node.setAttribute('data-mobile-hidden','');}
      nav.querySelectorAll('[data-mobile-view]').forEach(button=>{if(button.dataset.mobileView===view)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');});
      const tab=config.tabs.find(t=>t[0]===view),index=config.tabs.indexOf(tab);
      $('mobile-section-label').textContent=String(index+1).padStart(2,'0')+' / '+({rider:'ユーザー',driver:'ドライバー',admin:'管理者'}[role]);
      $('mobile-view-title').textContent=tab[2];$('mobile-view-help').textContent=tab[3];
      $('mobile-refresh').textContent=view==='map'?'全体':'更新';$('mobile-refresh').setAttribute('aria-label',view==='map'?'地図全体を表示':'最新の状況に更新');
      if(media.matches){
        if(scroll)heading.scrollIntoView({block:'start',behavior:'instant'});
        if(focus)$('mobile-view-title').focus({preventScroll:true});
        requestAnimationFrame(()=>{
          // Maps recalculate even after being hidden at the same width.
          const fit={rider:'map-fit',driver:'driver-map-fit',admin:'admin-map-fit'}[role];if(view==='map')$(fit).click();
          if(view==='chat'){const log=$(role==='rider'?'journey-messages':role+'-chat-log');log.scrollTop=log.scrollHeight;}
        });
      }
      return media.matches;
    }
    function layout(){
      const enabled=!!role&&media.matches;document.body.classList.toggle('mobile-ui',enabled);heading.hidden=!enabled;nav.hidden=!enabled;
      if(!enabled)document.body.classList.remove('mobile-input-focus');
      if(role)setView(view);
    }
    function enter(user){
      leave();role=configs[user.role]?user.role:null;if(!role)return;
      const config=configs[role];
      nav.innerHTML=config.tabs.map(([key,label])=>`<button type="button" data-mobile-view="${key}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[key]}</svg><span>${label}</span></button>`).join('');
      view=config.default;firstSnapshot=true;activeId=null;layout();
    }
    function leave(){clearParts();role=null;view=null;selection=null;heading.hidden=true;nav.hidden=true;document.body.classList.remove('mobile-ui','mobile-input-focus');delete document.body.dataset.mobileView;}
    function sync(){
      const s=getState();if(!role||s.user?.role!==role||!s.snapshot)return;
      const active=s.snapshot.rides.find(r=>!['completed','cancelled'].includes(r.status));
      if(firstSnapshot){firstSnapshot=false;if(role==='rider'&&active)setView('rides');if(role==='driver'&&s.snapshot.rides.some(r=>!['requested','completed','cancelled'].includes(r.status)))setView('drive');}
      else if(role==='rider'&&active&&!activeId&&!s.editing)setView('rides',{scroll:media.matches,focus:media.matches});
      activeId=active?.id||null;
      const badge=role==='rider'?nav.querySelector('[data-mobile-view=rides]'):role==='driver'?nav.querySelector('[data-mobile-view=queue]'):null;
      if(badge){const count=s.snapshot.rides.filter(r=>role==='driver'?r.status==='requested':!['completed','cancelled'].includes(r.status)).length;badge.classList.toggle('has-update',count>0);badge.setAttribute('aria-label',(role==='driver'?'受付':'依頼状況')+(count?'、'+count+'件':''));}
      refreshSelection();
    }
    function refreshSelection(next){
      if(next)selection=next;
      if(role!=='rider')return;
      const button=$('mobile-continue'),s=getState(),hasRoute=selection?.origin&&selection?.destination&&selection.origin!==selection.destination;
      const active=s.snapshot?.rides.some(r=>!['completed','cancelled'].includes(r.status));
      button.disabled=!!s.busy||!!s.pending||(!active&&!hasRoute);button.textContent=active&&!s.editing?'いまの依頼を見る →':!hasRoute?'乗る場所と降りる場所を選択':selection?.passengers?'次へ：内容を確認する →':'次へ：人数を選ぶ →';
    }
    nav.addEventListener('click',event=>{const button=event.target.closest('[data-mobile-view]');if(button)setView(button.dataset.mobileView,{scroll:true,focus:true});});
    $('mobile-refresh').addEventListener('click',()=>$(view==='map'?{rider:'map-fit',driver:'driver-map-fit',admin:'admin-map-fit'}[role]:'refresh').click());
    $('mobile-continue').addEventListener('click',()=>{const s=getState(),active=s.snapshot?.rides.some(r=>!['completed','cancelled'].includes(r.status));setView(active&&!s.editing?'rides':'review',{scroll:true,focus:true});});
    $('mobile-driver-open').addEventListener('click',()=>setView('drive',{scroll:true,focus:true}));
    for(const id of ['summary-origin','summary-destination'])$(id).addEventListener('click',()=>{if(media.matches)setView('map',{scroll:true,focus:true});});
    document.addEventListener('focusin',event=>{if(media.matches&&role&&event.target.matches('input:not([type=checkbox]):not([type=radio]),textarea'))document.body.classList.add('mobile-input-focus');});
    document.addEventListener('focusout',()=>{queueMicrotask(()=>{if(!document.activeElement?.matches('input:not([type=checkbox]):not([type=radio]),textarea'))document.body.classList.remove('mobile-input-focus');});});
    for(const id of ['journey-chat-form','driver-chat-form','admin-chat-form'])$(id).addEventListener('submit',()=>{if(media.matches)$(id).querySelector('input').blur();refreshSelection();});
    media.addEventListener?.('change',layout);
    return {enter,leave,sync,refreshSelection,open(next){return setView(next,{scroll:media.matches,focus:media.matches});}};
  }};
})();
