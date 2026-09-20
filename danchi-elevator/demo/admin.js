/* Administrative read-only overview. Existing records/payment controls stay below. */
(function(){
  'use strict';
  const $=id=>document.getElementById(id),O=window.YokoOps;
  window.YokoAdmin={create({getState,showRecord}){
    let active=false,filter={kind:'requested'},selectedId=null,days=7,schedule=null;
    const percent=n=>n===null?'—':n.toFixed(1)+'%';
    const number=n=>n<1&&n>0?'<1':Math.round(n).toLocaleString('ja-JP');
    const rides=()=>getState().snapshot?.rides||[],stops=()=>getState().snapshot?.services.flatMap(s=>s.stops.filter(t=>t.active))||[];
    const map=O.mapView({id:'admin-map',errorId:'admin-map-error',onPick:id=>{filter={kind:'stop',value:id};selectedId=null;sync();O.say('admin-chat-log',`${stops().find(s=>s.id===id)?.name}の依頼を表示しました。`);}});
    function html(id,content){if($(id).innerHTML===content)return;const focused=document.activeElement?.dataset.adminRide;$(id).innerHTML=content;if(focused)[...$(id).querySelectorAll('[data-admin-ride]')].find(b=>b.dataset.adminRide===focused)?.focus({preventScroll:true});}
    function analytics(){
      const snap=getState().snapshot;if(!snap)return;
      const m=YokoInsights.metrics(snap,days,schedule);
      $('admin-live-waiting').textContent=snap.rides.filter(r=>r.status==='requested').length+'件';$('admin-live-onboard').textContent=m.onboard+'人';$('admin-live-running').textContent=m.assignedVehicles+'台';
      $('admin-updated').textContent=O.time(snap.as_of)+' 更新 / 架空データ';
      $('admin-assignment-rate').textContent=percent(m.assignmentRate);$('admin-assignment-basis').textContent=`担当あり ${m.assignedVehicles}台 / 登録 ${m.totalVehicles}台`;
      $('admin-occupancy-rate').textContent=percent(m.occupancyRate);$('admin-occupancy-basis').textContent=`乗車中 ${m.onboard}人 / 総定員 ${m.capacity}人`;
      $('admin-time-rate').textContent=m.utilization?percent(m.utilization.rate):'未設定';
      $('admin-time-basis').textContent=m.utilization?`記録 ${number(m.utilization.busyMinutes)}分 / 稼働枠 ${number(m.utilization.availableMinutes)}分（${days}日間・経過分）`:'「稼働時間帯」を設定すると計算します';
      for(const[k,v]of [['assignment',m.assignmentRate],['occupancy',m.occupancyRate],['time',m.utilization?.rate]])$('admin-'+k+'-bar').style.width=Math.max(0,Math.min(100,v||0))+'%';
      $('admin-analysis-scope').textContent=`${m.period} / このブラウザーの取得済み ${m.recordCount}件から集計。`+(m.possiblyTruncated?' 最新200件のみのため、全期間の実績・稼働率を表しません。':'')+(m.utilization?.missing?` 時刻不足 ${m.utilization.missing}件は時間計算から除外。`:'');
      for(const[k,v,unit]of [['requested',m.requested,'件'],['completed',m.completed,'件'],['people',m.people,'人'],['cancelled',m.cancelled,'件']])$('analysis-'+k).innerHTML=v.toLocaleString('ja-JP')+'<small>'+unit+'</small>';
      $('analysis-completion-rate').textContent=percent(m.completionRate);$('analysis-wait').textContent=m.waitMinutes===null?'—':number(m.waitMinutes)+'分';$('analysis-wait-samples').textContent=m.waitSamples?`平均 / 乗車記録 ${m.waitSamples}件`:'期間内の乗車記録なし';
      $('admin-period').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.days)===days)));
      const trendMax=Math.max(1,...m.trend.map(row=>row.people));
      $('analysis-trend-caption').textContent=`降車完了の人数 / ${days}日間`;
      html('analysis-trend',m.trend.map(row=>`<div class="trend-column" title="${row.day}: ${row.people}人 / ${row.rides}件"><strong>${row.people}</strong><div><i style="height:${row.people/trendMax*100}%"></i></div><span>${row.day.slice(5).replace('-','/')}</span></div>`).join(''));
      $('analysis-trend').setAttribute('aria-label',m.trend.map(row=>row.day+' '+row.people+'人').join('、'));
      const top=m.routes.slice(0,5),max=Math.max(1,...top.map(row=>row.people));
      html('analysis-routes',top.length?top.map((row,index)=>`<div class="route-bar"><span><b>${index+1}</b> ${O.esc(row.origin)} → ${O.esc(row.destination)}</span><strong>${row.people}人 <small>/ ${row.rides}件</small></strong><div><i style="width:${row.people/max*100}%"></i></div></div>`).join(''):'<p class="empty-analysis">期間内に完了した送迎はありません。</p>');
      const peak=Math.max(1,...m.hours.map(row=>row.requests));
      html('analysis-hours',m.hours.map(row=>`<div title="${row.hour}時台: ${row.requests}件"><b>${row.requests||''}</b><div><i style="height:${row.requests/peak*100}%"></i></div><span>${row.hour%6===0?row.hour+'時':''}</span></div>`).join(''));
      $('analysis-hours').setAttribute('aria-label',m.hours.map(row=>row.hour+'時台 '+row.requests+'件').join('、'));
    }
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
      map.draw(stops(),all,selected);analytics();controls();
    }
    function controls(){if(!active)return;const locked=getState().busy||!!getState().pending;$('admin-chat-input').disabled=locked;$('admin-chat-send').disabled=locked;}
    function enter(user){leave();if(user.role!=='admin')return;active=true;document.body.classList.add('admin-ui');$('admin-panel').hidden=false;$('admin-chat-log').replaceChildren();O.say('admin-chat-log','地図のピンか、場所名・受付番号で依頼を確認できます。「処理待ち」と入力すると、引受待ちを表示します。');}
    function leave(){active=false;filter={kind:'requested'};selectedId=null;document.body.classList.remove('admin-ui');$('admin-panel').hidden=true;}
    $('admin-period').addEventListener('click',event=>{const b=event.target.closest('[data-days]');if(b){days=Number(b.dataset.days);analytics();}});
    $('admin-schedule-form').addEventListener('submit',event=>{event.preventDefault();const start=$('admin-schedule-start').value,end=$('admin-schedule-end').value;if(!start||!end||start===end){$('admin-schedule-message').textContent='開始と終了を、異なる時刻で入力してください。';return;}schedule={start,end};$('admin-schedule-message').textContent=`分析用の稼働枠：毎日 ${start} 〜 ${end}（登録車両すべて）。`+(end<start?'翌日までの枠として計算します。':'');analytics();});
    $('admin-schedule-clear').addEventListener('click',()=>{schedule=null;$('admin-schedule-form').reset();$('admin-schedule-message').textContent='時間稼働率の条件を解除しました。';analytics();});
    $('admin-map-fit').addEventListener('click',map.fit);$('admin-show-all').addEventListener('click',()=>{filter={kind:'all'};selectedId=null;sync();});
    $('admin-quick-filters').addEventListener('click',event=>{const button=event.target.closest('[data-admin-filter]');if(!button)return;filter={kind:button.dataset.adminFilter};selectedId=null;sync();});
    $('admin-result-list').addEventListener('click',event=>{const b=event.target.closest('[data-admin-ride]');if(!b||getState().busy||getState().pending)return;selectedId=b.dataset.adminRide;sync();showRecord(selectedId);});
    $('admin-chat-form').addEventListener('submit',event=>{event.preventDefault();if(getState().busy||getState().pending)return;const text=$('admin-chat-input').value.trim();if(!text)return;$('admin-chat-input').value='';O.say('admin-chat-log',text,'user');const next=O.find(text,stops());if(next.kind==='unknown'){O.say('admin-chat-log','登録された場所名、受付番号、または「処理待ち」「運行中」「履歴」で確認できます。');return;}filter=next;selectedId=null;sync();O.say('admin-chat-log',$('admin-result-label').textContent+'。選んだ依頼から詳細な記録を確認できます。');});
    return {enter,leave,sync,controls};
  }};
})();
