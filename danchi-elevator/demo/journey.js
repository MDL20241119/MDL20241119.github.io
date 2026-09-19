/* Map/chat presentation only. The existing confirmation form and Core save rides. */
(function(){
  'use strict';
  const points={'stop-a':[33.1968,131.5718],'stop-b':[33.2024,131.5784],'stop-c':[33.2028,131.5652]};
  const $=id=>document.getElementById(id);
  const terminal=new Set(['completed','cancelled']);
  const empty=()=>({origin:null,destination:null,passengers:null});
  const names={origin:'乗る場所',destination:'降りる場所'};
  window.YokoJourney={create({getState,notify}){
    let person=null,stops=[],selection=empty(),target='origin',undo=[],map=null,route=null,markerKey='',lastActiveId=null,lastCompletion=null,editingId=null;
    const markers=new Map(),announced=new Set();
    const panel=$('journey-panel');
    const activeRide=()=>getState().snapshot?.rides.find(r=>!terminal.has(r.status))||null;
    const editingRide=()=>getState().snapshot?.rides.find(r=>r.id===getState().editing)||null;
    const fixedStops=()=>editingRide()?.status==='assigned';
    const locked=()=>!person||getState().user?.role!=='rider'||!getState().snapshot||getState().busy||!!getState().pending||!!(activeRide()&&!getState().editing);
    const stopName=id=>stops.find(s=>s.id===id)?.name||'未選択';
    const complete=()=>selection.origin&&selection.destination&&selection.origin!==selection.destination&&[1,2,3].includes(selection.passengers);
    function say(text,kind='guide'){
      const row=document.createElement('div');row.className='chat-row '+kind;
      if(kind!=='user'){const avatar=document.createElement('span');avatar.className='guide-avatar';avatar.setAttribute('aria-hidden','true');avatar.textContent='↔';row.append(avatar);}
      const bubble=document.createElement('div');bubble.className='chat-bubble';bubble.textContent=text;row.append(bubble);
      $('journey-messages').append(row);
      // Keep the visible conversation bounded; no text is sent to an external AI.
      while($('journey-messages').children.length>40)$('journey-messages').firstElementChild.remove();
      $('journey-messages').scrollTop=$('journey-messages').scrollHeight;
    }
    function prompt(){
      if(!selection.origin)return 'どこから乗りますか？\n地図の緑のピンか、場所名で教えてください。';
      if(!selection.destination)return stopName(selection.origin)+'からですね。\n次は、どこで降りますか？';
      if(!selection.passengers)return '何人で乗りますか？\n1〜3人から選ぶか、「2人」のように送ってください。';
      return '場所と人数がそろいました。\n下の「内容を確認する」から、最後に確認しましょう。';
    }
    function writeForm(){
      for(const [field,id] of [['origin','origin'],['destination','destination'],['passengers','passengers']]){
        $(id).value=selection[field]===null?'':String(selection[field]);
        $(id).dispatchEvent(new Event('change',{bubbles:true}));
      }
    }
    function nextTarget(){target=!selection.origin?'origin':!selection.destination?'destination':'passengers';}
    function apply(update,text){
      if(locked()){notify('いまの依頼は、下の「あなたの依頼」で確認・変更・取消できます。',true);return false;}
      if(fixedStops()&&(('origin'in update&&update.origin!==selection.origin)||('destination'in update&&update.destination!==selection.destination))){say('車両確定後は人数を変更できます。乗降場所の変更はできません。','error');return false;}
      const next={...selection,...update};
      if(next.origin&&next.origin===next.destination){say('乗る場所と降りる場所は、別の場所を選んでください。','error');return false;}
      if(Object.entries(update).some(([k,v])=>k!=='passengers'&&!stops.some(s=>s.id===v))){say('その乗降場所は選べません。表示されている場所から選んでください。','error');return false;}
      if(next.passengers!==null&&![1,2,3].includes(next.passengers)){say('このデモでは1〜3人で選んでください。','error');return false;}
      undo.push({...selection});selection=next;lastCompletion=null;nextTarget();writeForm();
      if(text)say(text,'user');say(prompt());renderSelection();return true;
    }
    function chooseStop(id){
      if(!['origin','destination'].includes(target)){say('変更する場合は、地図の上の「乗る場所」か「降りる場所」を選んでください。');return;}
      apply({[target]:id},names[target]+'：'+stopName(id));
    }
    function setTarget(field){
      if(locked()||fixedStops())return;
      target=field;say(names[field]+'を選び直せます。地図のピンか、場所名で教えてください。');renderSelection();
    }
    function reset(){
      if(locked()||fixedStops())return;
      undo.push({...selection});selection=empty();target='origin';lastCompletion=null;writeForm();say('入力を選び直します。\n'+prompt());renderSelection();
    }
    function back(){
      if(locked()||!undo.length)return;
      selection=undo.pop();nextTarget();writeForm();say('一つ前の入力に戻しました。\n'+prompt());renderSelection();
    }
    function makeMap(){
      if(map){requestAnimationFrame(()=>map.invalidateSize());return;}
      if(!window.L){$('map-error').hidden=false;return;}
      map=L.map('journey-map',{scrollWheelZoom:false,zoomControl:false,minZoom:12,maxZoom:18,zoomAnimation:false,fadeAnimation:false});
      L.control.zoom({position:'bottomright',zoomInTitle:'地図を拡大',zoomOutTitle:'地図を縮小'}).addTo(map);
      const tiles=L.tileLayer('https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png',{maxZoom:18,attribution:'<a href="https://maps.gsi.go.jp/development/ichiran.html" target="_blank" rel="noopener noreferrer">地理院タイル</a>'}).addTo(map);
      tiles.on('tileerror',()=>{$('map-error').hidden=false;});
      tiles.on('load',()=>{const images=[...$('journey-map').querySelectorAll('.leaflet-tile')];if(images.length&&images.every(img=>img.complete&&img.naturalWidth>0))$('map-error').hidden=true;});
      map.setView([33.1998,131.5718],15);
      if(window.ResizeObserver)new ResizeObserver(()=>map.invalidateSize({pan:false})).observe($('journey-map'));
    }
    function fit(){if(map&&markers.size)map.fitBounds([...markers.values()].map(m=>m.getLatLng()),{padding:[78,46],maxZoom:15,animate:false});}
    function buildMarkers(){
      if(!map)return;
      const key=JSON.stringify(stops.map(s=>[s.id,s.name]));if(key===markerKey)return;markerKey=key;
      markers.forEach(m=>m.remove());markers.clear();
      for(const stop of stops){
        if(!points[stop.id])continue;
        const button=document.createElement('button');button.type='button';button.setAttribute('aria-label','地図で'+stop.name+'を選ぶ');
        const badge=document.createElement('small');badge.className='pin-kind';const label=document.createElement('span');label.textContent=stop.name;button.append(badge,label);
        button.addEventListener('click',event=>{event.preventDefault();event.stopPropagation();chooseStop(stop.id);});
        const icon=L.divIcon({className:'stop-pin',html:button,iconSize:[130,48],iconAnchor:[65,24]});
        const marker=L.marker(points[stop.id],{icon,keyboard:false}).addTo(map);markers.set(stop.id,marker);
      }
      fit();
    }
    function paintMap(){
      if(!map)return;
      for(const [id,marker]of markers){
        const button=marker.getElement()?.querySelector('button');if(!button)continue;
        const selected=selection.origin===id?'origin':selection.destination===id?'destination':'';
        button.dataset.selected=selected;button.setAttribute('aria-pressed',String(Boolean(selected)));button.disabled=locked()||fixedStops();
        button.querySelector('.pin-kind').textContent=selected?names[selected]:'乗降場所';
      }
      if(route){route.remove();route=null;}
      if(points[selection.origin]&&points[selection.destination])route=L.polyline([points[selection.origin],points[selection.destination]],{color:'#204e83',weight:3,dashArray:'7 9',opacity:.65,interactive:false}).addTo(map);
    }
    function renderChoices(){
      const choices=$('journey-choices');choices.replaceChildren();
      if(locked())return;
      if(target==='passengers'||fixedStops()){
        for(let n=1;n<=3;n++){const b=document.createElement('button');b.type='button';b.textContent=n+'人';b.setAttribute('aria-label','チャットで'+n+'人を選ぶ');b.addEventListener('click',()=>apply({passengers:n},n+'人'));choices.append(b);}
      }else for(const stop of stops){const b=document.createElement('button');b.type='button';b.textContent=stop.name;b.setAttribute('aria-label','チャットで'+stop.name+'を選ぶ');b.addEventListener('click',()=>chooseStop(stop.id));choices.append(b);}
    }
    function setStep(step){panel.querySelectorAll('[data-journey-step]').forEach(node=>{const n=Number(node.dataset.journeyStep);node.classList.toggle('step-done',n<step);if(n===step)node.setAttribute('aria-current','step');else node.removeAttribute('aria-current');});}
    function renderSelection(){
      if(!person)return;
      for(const field of ['origin','destination']){
        $('chosen-'+field).textContent=selection[field]?stopName(selection[field]):'選んでください';
        $('summary-'+field+'-name').textContent=stopName(selection[field]);
        $('pick-'+field).setAttribute('aria-pressed',String(target===field));
      }
      const active=activeRide(),frozen=locked(),fixed=fixedStops();
      $('map-prompt').textContent=frozen&&active?'依頼した乗降場所を確認できます。':fixed?'車両確定後は、乗る人数を変更できます。':target==='passengers'?'乗降場所を選びました。次は人数を選んでください。':'緑のピンを押して、'+names[target]+'を選んでください。';
      for(const id of ['pick-origin','pick-destination','summary-origin','summary-destination'])$(id).disabled=frozen||fixed;
      for(const b of $('journey-passengers').querySelectorAll('button')){b.setAttribute('aria-pressed',String(Number(b.dataset.people)===selection.passengers));b.disabled=frozen;}
      $('journey-chat-input').disabled=frozen;$('journey-chat-send').disabled=frozen;
      $('journey-undo').disabled=frozen||!undo.length;$('journey-clear').disabled=frozen||fixed;
      $('journey-edit-cancel').hidden=!getState().editing;$('journey-edit-cancel').disabled=!!getState().busy||!!getState().pending;
      $('journey-confirm').disabled=frozen||!complete();
      $('journey-confirm').textContent=getState().editing?'変更内容を確認する →':active?'依頼を受付済み':'内容を確認する →';
      $('journey-summary-hint').textContent=getState().pending?'送信結果を確認しています。重ねて依頼せず、結果を照合してください。':active&&!getState().editing?'変更・取消は、下の「あなたの依頼」から行えます。':complete()?`${selection.passengers}人 / ${$('service-fare').textContent}。次に確認画面へ進みます。`:'乗る場所・降りる場所・人数を選んでください。';
      const step=active?({requested:2,assigned:3,arrived:4,onboard:4}[active.status]||1):lastCompletion?4:1;setStep(step);
      if(getState().draft&&['request','change'].includes(getState().draft.kind))setStep(2);
      paintMap();renderChoices();
    }
    function showStatus(ride){
      $('journey-status').hidden=!ride;if(!ride)return;
      const text={requested:['依頼を受け付けました','ドライバーの引受を待っています。上の「ドライバー用」に切り替えると、この依頼を引き受けられます。'],assigned:['車が確定しました','指定した乗降場所でお待ちください。到着予測は未取得です。'],arrived:['車が到着しました','乗る場所と車両を確認してください。'],onboard:['乗車を記録しました','降車までお待ちください。'],completed:['降車完了。ありがとうございました','履歴は下の「完了・取消」で確認できます。次の依頼も作れます。'],cancelled:['依頼を取り消しました','必要なときに、もう一度場所と人数を選べます。']}[ride.status];
      $('journey-status-title').textContent=text[0];$('journey-status-text').textContent=text[1];
    }
    function sync(){
      const s=getState();if(!person||s.user?.role!=='rider'||!s.snapshot)return;
      stops=s.snapshot.services.find(item=>item.id===$('service').value)?.stops.filter(stop=>stop.active)||[];
      makeMap();buildMarkers();
      const active=activeRide();
      if(active){
        lastActiveId=active.id;lastCompletion=null;
        if(!s.editing){selection={origin:active.origin_stop_id,destination:active.destination_stop_id,passengers:active.passengers};writeForm();}
        const announcement=active.id+':'+active.status;
        if(!announced.has(announcement)){announced.add(announcement);say({requested:'依頼を受け付けました。ドライバーが引き受けるまでお待ちください。',assigned:'車が確定しました。地図で乗る場所を確認してください。',arrived:'車が到着しました。乗る場所と車両を確認してください。',onboard:'乗車を記録しました。降車までお待ちください。'}[active.status]);}
        const vehicleKey=active.id+':vehicle';
        if(['assigned','arrived','onboard'].includes(active.status)&&!announced.has(vehicleKey)&&!$('confirm-dialog').open&&!s.editing){
          announced.add(vehicleKey);$('journey-vehicle-name').textContent=active.vehicle_id==='vehicle-a1'?'デモ車両 1':active.vehicle_id==='vehicle-a2'?'デモ車両 2':'割当済みの車両';
          $('journey-vehicle-pickup').textContent='乗る場所：'+active.origin_name+' / '+active.passengers+'人';$('journey-vehicle-dialog').showModal();
        }
      }else if(lastActiveId){
        const finished=s.snapshot.rides.find(r=>r.id===lastActiveId&&terminal.has(r.status));
        if(finished){lastCompletion=finished;selection=empty();undo=[];target='origin';writeForm();say(finished.status==='completed'?'降車完了です。ご利用ありがとうございました。':'依頼を取り消しました。');}
        lastActiveId=null;
      }
      if(editingId&&!s.editing){editingId=null;if(!active){selection=empty();target='origin';writeForm();}}
      showStatus(active||lastCompletion);renderSelection();
    }
    function enter(user){
      person=user.role==='rider'?user.id:null;document.body.classList.toggle('rider-ui',!!person);panel.hidden=!person;
      selection=empty();target='origin';undo=[];announced.clear();lastActiveId=null;lastCompletion=null;editingId=null;stops=[];
      $('journey-messages').replaceChildren();$('journey-chat-input').value='';$('journey-status').hidden=true;
      if(person){say('こんにちは。\n'+prompt());renderSelection();}
    }
    function leave(){person=null;panel.hidden=true;document.body.classList.remove('rider-ui');$('journey-vehicle-dialog').close();$('journey-messages').replaceChildren();}
    function edit(ride){selection={origin:ride.origin_stop_id,destination:ride.destination_stop_id,passengers:ride.passengers};undo=[];editingId=ride.id;target=ride.status==='assigned'?'passengers':'origin';say(ride.status==='assigned'?'人数を変更できます。変更後に確認してください。':'依頼内容を変更できます。地図かチャットで選び直してください。');renderSelection();panel.scrollIntoView({block:'start',behavior:'smooth'});}
    $('pick-origin').addEventListener('click',()=>setTarget('origin'));$('summary-origin').addEventListener('click',()=>setTarget('origin'));
    $('pick-destination').addEventListener('click',()=>setTarget('destination'));$('summary-destination').addEventListener('click',()=>setTarget('destination'));
    $('journey-passengers').addEventListener('click',event=>{const b=event.target.closest('[data-people]');if(b)apply({passengers:Number(b.dataset.people)},b.dataset.people+'人');});
    $('journey-chat-form').addEventListener('submit',event=>{
      event.preventDefault();if(locked())return;
      const text=$('journey-chat-input').value.trim();if(!text)return;
      $('journey-chat-input').value='';
      const result=YokoJourneyInput.parse(text,{stops,selection,target});
      if(!result.ok){say(text,'user');say(result.message,'error');return;}
      if(result.command){say(text,'user');if(fixedStops()){say('車両確定後は人数を変更するか、「変更をやめる」を選んでください。');return;}result.command==='reset'?reset():back();return;}
      apply(result.update,text);
    });
    $('journey-undo').addEventListener('click',back);$('journey-clear').addEventListener('click',reset);
    $('journey-edit-cancel').addEventListener('click',()=>{$('stop-editing').click();sync();});
    $('journey-confirm').addEventListener('click',()=>{if(!locked()&&complete()){writeForm();$('request-form').requestSubmit();}});
    $('map-fit').addEventListener('click',fit);$('journey-vehicle-close').addEventListener('click',()=>$('journey-vehicle-dialog').close());
    return {enter,leave,sync,edit,renderSelection};
  }};
})();
