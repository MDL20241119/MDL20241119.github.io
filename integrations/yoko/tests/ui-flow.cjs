// DOM + real HTTP integration. No browser renderer, CSS layout or visual claim.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const os=require('node:os');
const {spawn,spawnSync}=require('node:child_process');
const {once}=require('node:events');
const {randomUUID}=require('node:crypto');
const {JSDOM,VirtualConsole}=require('jsdom');
const root=path.resolve(__dirname,'..');
const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'yoko-ui-'));
const html=fs.readFileSync(path.join(root,'app/static/index.html'),'utf8');
const script=fs.readFileSync(path.join(root,'app/static/app.js'),'utf8');
// Opt in to a nonzero synthetic fare so receipt/cancellation UI is meaningful.
const setup=spawnSync(process.env.PYTHON || 'python',['scripts/configure_payment_demo.py','--db',path.join(tmp,'ui.sqlite3')],{cwd:root,encoding:'utf8'});
assert.equal(setup.status,0,setup.stderr);
const server=spawn(process.env.PYTHON || 'python',['-m','app','--port','0','--db',path.join(tmp,'ui.sqlite3')],{cwd:root,stdio:['ignore','pipe','pipe']});
let origin,readyResolve,readyReject;
const ready=new Promise((resolve,reject)=>{readyResolve=resolve;readyReject=reject;});
server.stdout.on('data',b=>{const match=b.toString().match(/http:\/\/127\.0\.0\.1:\d+/);if(match){origin=match[0];readyResolve();}});
server.on('error',readyReject);
server.on('exit',code=>{if(!origin)readyReject(new Error(`Server exited: ${code}`));});
server.stderr.on('data',b=>process.stderr.write(b));
const windows=[];
const checks=[];
async function wait(check,label){const end=Date.now()+5000;while(Date.now()<end){if(check())return;await new Promise(r=>setTimeout(r,10));}throw new Error('Timed out: '+label);}
function passed(name){checks.push(name);console.log('PASS '+name);}

async function client(username,{quick=false,restore=null}={}){
  const errors=[];
  const vc=new VirtualConsole();vc.on('jsdomError',err=>errors.push(String(err)));
  const dom=new JSDOM(html,{url:origin,runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc,...(restore?{cookieJar:restore.dom.cookieJar}:{})});
  windows.push(dom.window);
  const w=dom.window;
  const ctl={dropNextAction:false,lastAction:null,inflight:0,intervals:new Set(),failSnapshot:false,advanceMs:0,loginRequests:0,paths:[]};
  const realNow=w.performance.now.bind(w.performance);
  Object.defineProperty(w.performance,'now',{value:()=>realNow()+ctl.advanceMs});
  const interval=w.setInterval.bind(w);
  w.setInterval=(...args)=>{const id=interval(...args);ctl.intervals.add(id);return id;};
  w.AbortSignal=AbortSignal;
  if(!w.crypto.randomUUID)w.crypto.randomUUID=randomUUID;
  w.HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};
  w.HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
  w.fetch=async(url,options={})=>{
    ctl.paths.push(url);if(url==='/api/session')ctl.loginRequests++;
    ctl.inflight++;
    try{
    if(ctl.failSnapshot&&url==='/api/snapshot')throw new Error('Synthetic disconnected observation view');
    const headers={...options.headers,Origin:origin};
    const cookie=dom.cookieJar.getCookieStringSync(origin);if(cookie)headers.Cookie=cookie;
    const response=await fetch(new URL(url,origin),{...options,headers});
    for(const c of response.headers.getSetCookie())dom.cookieJar.setCookieSync(c,origin);
    if(url.startsWith('/api/actions/')){ctl.lastAction={url,options};if(ctl.dropNextAction){ctl.dropNextAction=false;await response.text();throw new Error('Synthetic response loss after server commit');}}
    const json=response.json.bind(response);
    response.json=async()=>{ctl.inflight++;try{return await json();}finally{ctl.inflight--;}};
    return response;
    }finally{ctl.inflight--;}
  };
  w.eval(script);
  const get=id=>w.document.getElementById(id);
  if(!restore){
    if(quick){const button=w.document.querySelector(`[data-login="${username}"]`);button.click();button.click();}
    else {get('other-login').click();get('username').value=username;get('login-form').dispatchEvent(new w.SubmitEvent('submit',{bubbles:true,cancelable:true,submitter:get('login-form').querySelector('button')}));}
  }
  await wait(()=>!get('workspace').hidden&&get('sync-state').textContent.includes('時点'),username+' login');
  assert.equal(w.document.querySelector('[data-filter="active"]').getAttribute('aria-pressed'),'true');
  // Existing full-ledger regression checks intentionally inspect every status.
  w.document.querySelector('[data-filter="all"]').click();
  return {w,get,ctl,errors,dom};
}
async function refresh(c,status){
  c.get('refresh').click();
  await wait(()=>Boolean(c.w.document.querySelector('.badge.'+status)),'refresh '+status);
}
async function create(c){
  await wait(()=>!c.get('commit').disabled&&!c.get('confirm-dialog').open&&c.ctl.inflight===0,'previous action finished before new request');
  c.get('request-form').dispatchEvent(new c.w.SubmitEvent('submit',{bubbles:true,cancelable:true,submitter:c.get('prepare-request')}));
  await wait(()=>c.get('confirm-dialog').open,'confirmation visible');
  assert.match(c.get('confirm-details').textContent,/テスト乗降場所A/);
  c.get('commit').click();
  await wait(()=>!c.get('confirm-dialog').open&&!c.get('commit').disabled,'commit response');
}

(async()=>{
  await ready;
  const rider=await client('rider-a1',{quick:true}),driver=await client('driver-a1',{quick:true}),admin=await client('admin-a1',{quick:true});
  for(const c of [rider,driver,admin]){assert.equal(c.ctl.loginRequests,1);assert.equal(c.ctl.paths.some(p=>p.includes('/auth/line')),false);}
  passed('three Web entry buttons authenticate through the local server once even on double click, without LINE');
  assert.equal(rider.get('request-panel').hidden,false);
  assert.equal(driver.get('request-panel').hidden,true);
  assert.equal(admin.get('admin-stats').hidden,false);
  passed('three isolated sessions show their role-specific controls');
  const originalOrigin=rider.get('origin').value,originalDestination=rider.get('destination').value;
  rider.get('swap-stops').click();assert.equal(rider.get('origin').value,originalDestination);assert.equal(rider.get('destination').value,originalOrigin);
  rider.get('swap-stops').click();assert.equal(rider.get('origin').value,originalOrigin);
  assert.equal(rider.ctl.lastAction,null);
  passed('Web route swap changes the form without creating a request');
  await create(rider);await refresh(rider,'requested');await refresh(driver,'requested');
  passed('rider confirms stops and passengers and server saves request');
  const restored=await client('rider-a1',{restore:rider});
  assert.equal(restored.ctl.loginRequests,0);assert.equal(restored.w.document.querySelectorAll('.ride-card').length,1);
  assert.equal(restored.w.document.querySelector('.ride-card').dataset.rideCard,rider.w.document.querySelector('.ride-card').dataset.rideCard);
  for(const id of restored.ctl.intervals)restored.w.clearInterval(id);
  await wait(()=>restored.ctl.inflight===0,'restored client drained');assert.deepEqual(restored.errors,[]);restored.w.close();
  passed('reloading the Web page restores the server session and saved request without another login');
  rider.w.document.querySelector('[data-action="change"]').click();
  rider.get('passengers').value='2';
  rider.get('request-form').dispatchEvent(new rider.w.SubmitEvent('submit',{bubbles:true,cancelable:true,submitter:rider.get('prepare-request')}));
  await wait(()=>rider.get('confirm-dialog').open,'change confirmation');
  assert.equal(rider.get('confirm-title').textContent,'この内容に変更しますか？');
  rider.get('commit').click();
  await wait(()=>!rider.get('confirm-dialog').open&&!rider.get('commit').disabled,'change saved');
  assert.match(rider.get('rides').textContent,/2名/);
  assert.equal(rider.w.document.querySelectorAll('.ride-card').length,1);
  passed('owner changes passenger count after distinct confirmation without a new reservation');
  driver.get('refresh').click();
  await wait(()=>driver.get('rides').textContent.includes('2名'),'driver sees current changed version');
  driver.w.document.querySelector('[data-action="accept"]').click();
  await wait(()=>driver.get('message').textContent.includes('停車'),'stop warning');
  assert.equal(driver.w.document.querySelector('.badge').textContent,'引受待ち');
  passed('driver cannot act until stopped confirmation');
  for(const [action,status] of [['accept','assigned'],['arrive','arrived'],['board','onboard'],['complete','completed']]){
    driver.get('stopped').checked=true;
    driver.w.document.querySelector(`[data-action="${action}"]`).click();
    await wait(()=>Boolean(driver.w.document.querySelector('.badge.'+status)),'driver '+status);
    await refresh(rider,status);await refresh(admin,status);
    assert.match(rider.w.document.querySelector('.ride-progress [aria-current="step"]').textContent,new RegExp({assigned:'迎車',arrived:'到着',onboard:'乗車',completed:'完了'}[status]));
    assert.equal(driver.get('stopped').checked,false);
    if(status==='assigned'){
      assert.match(rider.get('rides').textContent,/到着予測：未取得/);
      assert.equal(rider.w.document.querySelector('.badge').textContent,'迎車中');
      rider.w.document.querySelector('[data-action="change"]').click();
      assert.equal(rider.get('origin').disabled,true);assert.equal(rider.get('destination').disabled,true);
      rider.get('stop-editing').click();assert.equal(rider.get('origin').disabled,false);
      passed('assigned ride permits count editing while route fields remain locked');
    }
  }
  assert.match(admin.get('admin-stats').textContent,/降車完了1/);
  passed('acceptance, arrival, boarding and completion shared across all three clients');
  rider.w.document.querySelector('[data-filter="active"]').click();assert.equal(rider.w.document.querySelectorAll('.ride-card').length,0);
  rider.w.document.querySelector('[data-filter="history"]').click();assert.equal(rider.w.document.querySelectorAll('.ride-card').length,1);
  assert.match(rider.get('ride-count').textContent,/完了・取消 1件/);
  rider.get('ride-search').value='存在しない場所';rider.get('ride-search').dispatchEvent(new rider.w.Event('input'));
  assert.equal(rider.w.document.querySelectorAll('.ride-card').length,0);assert.match(rider.get('rides').textContent,/該当する依頼/);
  rider.get('clear-search').click();assert.equal(rider.w.document.querySelectorAll('.ride-card').length,1);
  rider.get('ride-search').value=rider.w.document.querySelector('.ride-card').dataset.rideCard.slice(-8);rider.get('ride-search').dispatchEvent(new rider.w.Event('input'));
  assert.equal(rider.w.document.querySelectorAll('.ride-card').length,1);rider.get('clear-search').click();
  rider.w.document.querySelector('[data-filter="all"]').click();
  passed('current progress, history, receipt-number search and clear show the persisted Web ledger correctly');
  const summary=admin.w.document.querySelector('.ride-card summary');summary.parentNode.open=true;summary.focus();
  const oldCard=admin.w.document.querySelector('.ride-card');admin.get('refresh').click();
  await wait(()=>oldCard!==admin.w.document.querySelector('.ride-card')&&admin.ctl.inflight===0,'focused record refreshed');
  assert.equal(admin.w.document.activeElement.tagName,'SUMMARY');assert.equal(admin.w.document.querySelector('.ride-card details').open,true);
  passed('refresh preserves keyboard focus and the expanded ride record');
  await create(rider);await refresh(rider,'requested');
  rider.w.document.querySelector('[data-action="cancel"]').click();
  await wait(()=>rider.get('confirm-dialog').open,'cancel confirmation');
  assert.equal(rider.get('confirm-title').textContent,'この依頼を取り消しますか？');
  rider.get('commit').click();await refresh(rider,'cancelled');
  passed('owner cancellation requires separate confirmation and persists');
  rider.ctl.dropNextAction=true;await create(rider);
  await wait(()=>!rider.get('recovery').hidden,'recovery panel');
  assert.equal(rider.get('prepare-request').disabled,true);
  const operation=JSON.parse(rider.ctl.lastAction.options.body).operation_id;
  assert.match(rider.get('recovery-id').textContent,new RegExp(operation));
  rider.get('reconcile').click();
  await wait(()=>rider.get('recovery').hidden,'operation reconciled');
  await refresh(rider,'requested');
  assert.equal(rider.w.document.querySelectorAll('.ride-card').length,3);
  passed('lost HTTP response blocks new request and resolves original operation without duplication');
  rider.w.document.querySelector('[data-action="change"]').click();rider.get('passengers').value='1';
  rider.get('request-form').dispatchEvent(new rider.w.SubmitEvent('submit',{bubbles:true,cancelable:true,submitter:rider.get('prepare-request')}));
  await wait(()=>rider.get('confirm-dialog').open,'second change confirmation');
  rider.ctl.dropNextAction=true;rider.get('commit').click();
  await wait(()=>!rider.get('confirm-dialog').open&&!rider.get('commit').disabled,'change response lost');
  assert.equal(rider.get('recovery').hidden,false);rider.get('reconcile').click();
  await wait(()=>rider.get('recovery').hidden,'change reconciled');
  assert.equal(rider.get('stop-editing').hidden,true);
  assert.equal(rider.w.document.querySelectorAll('.ride-card').length,3);
  passed('lost change response reconciles the same operation and exits edit mode');
  await wait(()=>rider.get('profile-status').textContent.includes('未登録'),'catalog loaded');
  rider.get('profile-last-name').value='架空';rider.get('profile-first-name').value='画面試験';
  rider.get('profile-form').dispatchEvent(new rider.w.SubmitEvent('submit',{bubbles:true,cancelable:true}));
  await wait(()=>rider.get('confirm-dialog').open,'profile confirmation');
  assert.match(rider.get('confirm-details').textContent,/画面試験/);
  rider.get('commit').click();
  await wait(()=>rider.get('profile-status').textContent.includes('登録済み'),'profile persisted');
  passed('profile registration requires displayed confirmation and persists through HTTP');
  // Publish the synthetic terms through the same owner HTTP confirmation route.
  const adminSession=await (await admin.w.fetch('/api/me')).json();
  async function adminPost(url,body){
    const response=await admin.w.fetch(url,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':adminSession.csrf,'X-Requested-With':'YokoLocal'},body:JSON.stringify(body)});
    const data=await response.json();assert.equal(response.status,200,JSON.stringify(data));return data;
  }
  const termDraft=await adminPost('/api/drafts/terms_publish',{service_id:null,category:'platform',name:'架空の利用規約・画面試験',url:'https://example.invalid/ui-terms',agreement_required:true});
  const termOp=randomUUID();
  await adminPost('/api/actions/terms_publish',{operation_id:termOp,idempotency_key:termOp,payload:{draft_id:termDraft.id,details:termDraft.details}});
  rider.get('refresh').click();
  await wait(()=>rider.get('terms-list').querySelector('input:not(:disabled)'),'new terms visible');
  rider.get('terms-list').querySelector('input').checked=true;
  rider.get('prepare-agreements').click();
  await wait(()=>rider.get('confirm-dialog').open,'consent confirmation');
  assert.match(rider.get('confirm-details').textContent,/画面試験/);
  rider.get('commit').click();
  await wait(()=>rider.get('terms-list').querySelector('input:checked:disabled'),'agreement persisted');
  passed('published terms appear in the rider screen and consent is confirmed and stored');
  rider.get('prepare-profile-delete').click();
  await wait(()=>rider.get('message').textContent.includes('進行中'),'active ride prevents deletion');
  assert.equal(rider.get('confirm-dialog').open,false);
  const cancel=rider.w.document.querySelector('[data-action="cancel"]');
  const cancelledId=cancel.dataset.ride;cancel.click();
  await wait(()=>rider.get('confirm-dialog').open,'final cancellation confirmation');
  rider.get('commit').click();
  await wait(()=>!rider.get('confirm-dialog').open&&!rider.get('commit').disabled,'final cancellation saved');
  const rides=await (await rider.w.fetch('/api/snapshot')).json();
  assert.equal(rides.rides.find(r=>r.id===cancelledId).status,'cancelled');
  rider.get('prepare-profile-delete').click();
  await wait(()=>rider.get('confirm-dialog').open,'deletion confirmation');
  assert.match(rider.get('confirm-details').textContent,/運行履歴/);
  rider.ctl.dropNextAction=true;rider.get('commit').click();
  await wait(()=>!rider.get('confirm-dialog').open&&!rider.get('commit').disabled,'deletion response lost');
  rider.get('refresh').click();
  await wait(()=>!rider.get('login').hidden,'deletion revokes session');
  assert.equal(rider.get('rides').childElementCount,0);
  assert.equal(rider.get('profile-first-name').value,'');
  assert.equal(rider.get('profile-last-name').value,'');
  rider.w.document.querySelector('[data-login="rider-a1"]').click();
  await wait(()=>!rider.get('workspace').hidden&&!rider.get('recovery').hidden,'relogin restores pending deletion');
  rider.get('reconcile').click();
  await wait(()=>rider.get('recovery').hidden&&rider.get('profile-status').textContent.includes('未登録'),'deletion receipt reconciled');
  assert.equal(rider.get('terms-list').querySelector('input').checked,false);
  assert.equal(rider.get('prepare-profile-delete').hidden,true);
  rider.w.document.querySelector('[data-filter="all"]').click();
  passed('active rides block deletion; after cancellation deletion clears consent, revokes sessions and reconciles a lost reply');
  async function configure(kind,data){
    const draft=await adminPost('/api/drafts/'+kind,data),key=randomUUID();
    return adminPost('/api/actions/'+kind,{operation_id:key,idempotency_key:key,payload:{draft_id:draft.id,details:draft.details}});
  }
  const catalog=JSON.parse(fs.readFileSync(path.join(root,'fixtures/synthetic-catalog.json'),'utf8'));
  const route=JSON.parse(fs.readFileSync(path.join(root,'fixtures/synthetic-booking.json'),'utf8')).routes[0];
  await configure('service_configure',catalog.service);
  for(const stop of catalog.stops)await configure('stop_configure',stop);
  await configure('route_configure',route);
  rider.get('profile-panel').open=true;rider.get('profile-last-name').value='架空';rider.get('profile-first-name').value='候補試験';
  rider.get('profile-form').dispatchEvent(new rider.w.SubmitEvent('submit',{bubbles:true,cancelable:true}));
  await wait(()=>rider.get('confirm-dialog').open,'register again');rider.get('commit').click();
  await wait(()=>rider.get('profile-status').textContent.includes('登録済み')&&!rider.get('commit').disabled,'registered again');
  rider.get('terms-list').querySelector('input').checked=true;rider.get('prepare-agreements').click();
  await wait(()=>rider.get('confirm-dialog').open,'agree again');rider.get('commit').click();
  await wait(()=>rider.get('terms-list').querySelector('input:checked:disabled')&&!rider.get('commit').disabled,'agreed again');
  driver.get('refresh').click();
  await wait(()=>!driver.get('offer-panel').hidden&&driver.get('offer-route').value,'configured route on driver screen');
  async function openOffer(){
    driver.get('offer-panel').open=true;driver.get('stopped').checked=true;
    driver.get('offer-form').dispatchEvent(new driver.w.SubmitEvent('submit',{bubbles:true,cancelable:true}));
    await wait(()=>driver.get('confirm-dialog').open,'offer confirmation');
    assert.match(driver.get('confirm-details').textContent,/計画乗車/);driver.get('commit').click();
    await wait(()=>!driver.get('confirm-dialog').open&&!driver.get('commit').disabled,'offer committed');
  }
  await openOffer();
  assert.match(driver.get('offers-list').textContent,/確保済み0名/);
  passed('driver confirms a stopped, planned offer with zero seats reserved');
  rider.get('passengers').value='1';rider.get('search-candidates').click();
  await wait(()=>rider.w.document.querySelector('[data-candidate]'),'candidate shown');
  assert.match(rider.get('candidates').textContent,/表示だけでは席を確保しません/);
  const beforeBooking=await (await admin.w.fetch('/api/snapshot')).json();
  assert.equal(beforeBooking.offers[0].reserved,0);
  rider.w.document.querySelector('[data-candidate]').click();
  await wait(()=>rider.get('confirm-dialog').open,'booking confirmation');
  assert.equal(rider.get('confirm-title').textContent,'この便を予約しますか？');
  rider.ctl.dropNextAction=true;rider.get('commit').click();
  await wait(()=>!rider.get('confirm-dialog').open&&!rider.get('commit').disabled,'booking reply lost');
  assert.equal(rider.get('recovery').hidden,false);rider.get('reconcile').click();
  await wait(()=>rider.get('recovery').hidden,'booking reconciled');
  await refresh(rider,'assigned');await refresh(driver,'assigned');await refresh(admin,'assigned');
  assert.match(rider.get('rides').textContent,/架空の計画/);
  assert.equal(rider.w.document.querySelectorAll('.badge.assigned').length,1);
  assert.equal((await (await admin.w.fetch('/api/snapshot')).json()).offers[0].reserved,1);
  passed('candidate approval reserves one seat and a lost booking reply reconciles across all three clients');
  for(const [action,status] of [['arrive','arrived'],['board','onboard'],['complete','completed']]){
    driver.get('stopped').checked=true;driver.w.document.querySelector(`[data-action="${action}"]`).click();
    await wait(()=>!driver.w.document.querySelector(`[data-action="${action}"]`),'planned ride '+action);
  }
  admin.get('refresh').click();await wait(()=>admin.get('admin-stats').textContent.includes('降車完了2'),'planned ride completed for admin');
  assert.equal((await (await admin.w.fetch('/api/snapshot')).json()).offers.length,0);
  passed('planned booking follows arrival, boarding and completion and releases its seat');
  await openOffer();driver.get('stopped').checked=true;driver.w.document.querySelector('[data-close-offer]').click();
  await wait(()=>driver.get('confirm-dialog').open,'offer close confirmation');
  driver.get('commit').click();await wait(()=>!driver.get('confirm-dialog').open&&!driver.get('commit').disabled,'offer closed');
  rider.get('search-candidates').click();await wait(()=>rider.get('candidates').textContent.includes('提示便はありません'),'no candidates after close');
  passed('driver can end offer acceptance and candidate search reports no active plans');
  async function preparePayment(id,status){
    admin.w.document.querySelector(`[data-payment="${id}"]`).click();
    await wait(()=>admin.get('payment-dialog').open,'payment form visible');
    assert.equal(admin.get('payment-amount').value,'820');
    assert.equal(admin.get('payment-amount').readOnly,true);
    admin.get('payment-status').value=status;
    admin.get('payment-form').dispatchEvent(new admin.w.SubmitEvent('submit',{bubbles:true,cancelable:true}));
    await wait(()=>admin.get('confirm-dialog').open,'payment approval visible');
    assert.equal(admin.get('confirm-title').textContent,'この決済情報を記録しますか？');
    assert.match(admin.get('confirm-details').textContent,/820円/);
    assert.match(admin.get('confirm-details').textContent,/実際の請求・返金を実行しません/);
  }
  const paidId=admin.w.document.querySelector('.badge.completed').closest('[data-ride-card]').dataset.rideCard;
  await preparePayment(paidId,'received');admin.ctl.dropNextAction=true;admin.get('commit').click();
  await wait(()=>!admin.get('confirm-dialog').open&&!admin.get('commit').disabled,'payment reply lost');
  assert.equal(admin.get('recovery').hidden,false);admin.get('reconcile').click();
  await wait(()=>admin.get('recovery').hidden&&admin.w.document.querySelector(`[data-ride-card="${paidId}"] .payment-summary`).textContent.includes('受領済み'),'payment reconciled');
  const paid=await (await admin.w.fetch('/api/payments/'+paidId)).json();
  assert.equal(paid.record.version,1);assert.equal(paid.record.amount,820);
  passed('admin confirms a nonzero ledger record and reconciles a lost reply without recording twice');
  rider.get('refresh').click();driver.get('refresh').click();
  await wait(()=>rider.w.document.querySelector(`[data-ride-card="${paidId}"] .payment-summary`).textContent.includes('受領済み'),'rider sees own recorded amount');
  assert.equal(rider.w.document.querySelectorAll('[data-payment]').length,0);
  assert.equal(driver.w.document.querySelectorAll('.payment-summary').length,0);
  passed('rider sees own payment information without update controls and driver receives no payment details');
  await create(rider);await refresh(driver,'requested');driver.get('stopped').checked=true;
  driver.w.document.querySelector('[data-action="accept"]').click();await refresh(admin,'assigned');await refresh(rider,'assigned');
  const cancellationId=admin.w.document.querySelector('.badge.assigned').closest('[data-ride-card]').dataset.rideCard;
  const observationFixture=JSON.parse(fs.readFileSync(path.join(root,'fixtures/synthetic-observations.json'),'utf8'));
  await configure('observation_configure',{...observationFixture.source,label:'架空の観測 <img src=x onerror=alert(1)>'});
  const observationSnapshot=await (await admin.w.fetch('/api/snapshot')).json();
  const observationVehicle=observationSnapshot.vehicles.find(v=>v.id==='vehicle-a1');
  const observedAt=new Date().toISOString();
  const incident={id:'ui-delay-1',status:'active',delay_minutes:5,delay_reason:'traffic',started_at:observedAt,closed_at:null,closed_reason:null,effective_end:new Date(Date.now()+300000).toISOString()};
  const observationInput={vehicle_id:'vehicle-a1',run_id:observationVehicle.observation.run_id,source_id:observationFixture.source.source_id,observed_at:observedAt,location:observationFixture.location,delays:[incident]};
  await configure('observation_publish',observationInput);
  for(const c of [rider,driver,admin]){
    c.get('refresh').click();await wait(()=>c.get('rides').textContent.includes('遅延 5分（架空）'),'shared observation');
    assert.match(c.get('rides').textContent,/緯度 35.60034 \/ 経度 139.70012/);
    assert.match(c.get('rides').textContent,/観測：/);assert.match(c.get('rides').textContent,/到着予測：未取得/);
    assert.equal(c.w.document.querySelectorAll('.observation img').length,0);
  }
  passed('three roles see authorized synthetic position, source and observed time without fabricating ETA or interpreting source text as HTML');
  await wait(()=>rider.ctl.inflight===0,'rider reads drained');
  rider.ctl.failSnapshot=true;rider.w.dispatchEvent(new rider.w.Event('offline'));
  assert.match(rider.get('rides').textContent,/未接続・現在の状況は不明/);
  assert.doesNotMatch(rider.get('rides').textContent,/139\.70012|遅延 5分/);
  rider.get('refresh').click();await wait(()=>rider.get('sync-state').textContent.includes('未接続'),'failed refresh remains unknown');
  passed('offline and failed refresh immediately remove current coordinates and delay claims');
  rider.ctl.failSnapshot=false;rider.get('refresh').click();await wait(()=>rider.get('rides').textContent.includes('139.70012'),'observations recover');
  Object.defineProperty(rider.w.document,'hidden',{configurable:true,value:true});
  rider.ctl.failSnapshot=true;rider.ctl.advanceMs=61000;
  await wait(()=>!rider.get('rides').textContent.includes('139.70012'),'position expires without refresh');
  assert.match(rider.get('rides').textContent,/古い情報・更新待ち/);assert.doesNotMatch(rider.get('rides').textContent,/139\.70012/);
  assert.match(rider.get('rides').textContent,/遅延 5分/);
  rider.ctl.advanceMs=301000;
  await wait(()=>!rider.get('rides').textContent.includes('遅延 5分'),'delay expires without refresh');
  assert.doesNotMatch(rider.get('rides').textContent,/遅延 5分/);
  assert.doesNotMatch(rider.get('rides').textContent,/進行中の遅延報告なし/);
  passed('monotonic elapsed time independently expires position and delay even without a new server response');
  rider.ctl.advanceMs=0;rider.ctl.failSnapshot=false;delete rider.w.document.hidden;
  const resolvedAt=new Date().toISOString();
  await configure('observation_publish',{...observationInput,observed_at:resolvedAt,delays:[{...incident,status:'resolved',closed_at:resolvedAt,closed_reason:'resolved'}]});
  rider.get('refresh').click();await wait(()=>rider.get('rides').textContent.includes('進行中の遅延報告なし（観測時点）'),'explicit resolution');
  passed('only an explicit persisted resolution changes active delay into no active report at observation time');
  await preparePayment(cancellationId,'received');admin.get('commit').click();
  await wait(()=>!admin.get('confirm-dialog').open&&!admin.get('commit').disabled,'second receipt saved');
  rider.get('refresh').click();await wait(()=>rider.w.document.querySelector(`[data-ride-card="${cancellationId}"] .payment-summary`).textContent.includes('受領済み'),'prepaid ride shared');
  rider.w.document.querySelector(`[data-ride="${cancellationId}"][data-action="cancel"]`).click();
  await wait(()=>rider.get('confirm-dialog').open,'prepaid cancellation confirmation');
  assert.match(rider.get('confirm-details').textContent,/返金は実行されません/);rider.get('commit').click();
  await wait(()=>!rider.get('confirm-dialog').open&&!rider.get('commit').disabled,'prepaid cancellation saved');
  admin.get('refresh').click();await wait(()=>admin.w.document.querySelector(`[data-ride-card="${cancellationId}"]`).textContent.includes('返金確認が必要'),'refund review visible');
  const cancelledCard=admin.w.document.querySelector(`[data-ride-card="${cancellationId}"]`);
  assert.match(cancelledCard.textContent,/受領済み \/ 820円/);assert.equal(cancelledCard.querySelector('[data-payment]'),null);
  assert.equal((await (await admin.w.fetch('/api/payments/'+cancellationId)).json()).record.payment_status,'received');
  rider.get('refresh').click();await wait(()=>rider.w.document.querySelector(`[data-ride-card="${cancellationId}"] .badge.cancelled`),'cancelled rider view');
  assert.equal(rider.w.document.querySelector(`[data-ride-card="${cancellationId}"] [data-observation]`),null);
  passed('cancellation preserves the 820 JPY receipt and displays refund review without claiming a refund');
  const outsider=await client('rider-b1');assert.equal(outsider.w.document.querySelectorAll('.ride-card').length,0);
  assert.equal(outsider.get('request-panel').hidden,true);
  passed('other tenant sees no requests, vehicles or services');
  // A second tab changes the shared cookie to another valid actor. The old
  // screen must not render that actor's snapshot under its previous role.
  await rider.w.fetch('/api/session',{method:'POST',headers:{'Content-Type':'application/json','X-Requested-With':'YokoLocal'},body:JSON.stringify({username:'admin-a1',password:'local-test-only'})});
  rider.get('refresh').click();await wait(()=>rider.get('workspace').hidden,'shared-cookie actor change detected');
  assert.equal(rider.get('workspace').hidden,true);assert.equal(rider.get('rides').textContent,'');assert.equal(rider.get('vehicles').textContent,'');
  assert.match(rider.get('message').textContent,/別のタブでアカウント/);
  passed('a shared-cookie account change clears the old Web workspace before displaying another actor data');
  // Stop refresh timers and drain fetch + response parsing before closing JSDOM.
  // Closing a window during refresh destroys document while its continuation runs.
  const clients=[rider,driver,admin,outsider];
  for(const c of clients)for(const id of c.ctl.intervals)c.w.clearInterval(id);
  await wait(()=>clients.every(c=>c.ctl.inflight===0),'all client responses drained');
  await new Promise(resolve=>setImmediate(resolve));
  for(const c of clients)assert.deepEqual(c.errors,[]);
  passed('application scripts complete without DOM runtime errors');
  const result={checked_at:new Date().toISOString(),scope:'DOM_WITH_REAL_HTTP_NOT_RENDERED_BROWSER',status:'PASS',checks,visual_layout:'NOT_TESTED',browser_e2e:'BLOCKED_LOCALHOST'};
  fs.mkdirSync(path.join(root,'artifacts/test-results'),{recursive:true});
  fs.writeFileSync(path.join(root,'artifacts/test-results/ui-dom.json'),JSON.stringify(result,null,2)+'\n');
  console.log(`${checks.length} DOM integration checks passed. Visual browser testing is NOT included.`);
})().catch(err=>{
  console.error(err);process.exitCode=1;
  fs.writeFileSync(path.join(root,'artifacts/test-results/ui-dom.json'),JSON.stringify({checked_at:new Date().toISOString(),scope:'DOM_WITH_REAL_HTTP_NOT_RENDERED_BROWSER',status:'FAIL',checks,error:String(err)},null,2)+'\n');
}).finally(async()=>{
  for(const w of windows)w.close();
  server.kill('SIGTERM');await once(server,'exit').catch(()=>{});
  fs.rmSync(tmp,{recursive:true,force:true});
});
