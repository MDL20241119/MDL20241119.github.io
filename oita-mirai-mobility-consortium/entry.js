(() => {
  'use strict';
  const base = '/oita-mirai-mobility-consortium/';
  const configUrl = base + 'entry-verifier.json';
  const namespace = 'oita-password-entry-v1';
  const url = new URL(location.href);
  const reset = () => { try { sessionStorage.removeItem(namespace); } catch (_) {} };
  document.querySelectorAll('[data-entry-reset]').forEach(a => a.addEventListener('click', reset));
  if (url.searchParams.get('entry') === '1') {
    reset(); url.searchParams.delete('entry');
    history.replaceState(null,'',url.pathname+url.search+url.hash);
  }
  const dialog=document.createElement('dialog');
  dialog.className='oita-entry-dialog';
  dialog.setAttribute('aria-labelledby','oita-entry-title');
  dialog.setAttribute('aria-describedby','oita-entry-description');
  dialog.innerHTML=`<div class="oita-entry-inner"><span class="oita-entry-mark" aria-hidden="true">O.</span><p class="oita-entry-eyebrow">OITA MIRAI MOBILITY CONSORTIUM</p><h1 id="oita-entry-title">関係者向け<br>パスワード入力</h1><p class="oita-entry-copy" id="oita-entry-description">検討用ドラフトです。共有されたパスワードを入力してお進みください。</p><p class="oita-entry-fine">TCO・MDL案。参画・役割・費用負担等は未合意です。簡易な入口のため、本文・PDF・写真は直リンクからも閲覧できます。</p><form autocomplete="off" novalidate><label class="oita-entry-password-label" for="oita-entry-password">パスワード</label><input id="oita-entry-password" class="oita-entry-password" type="password" autocomplete="off" maxlength="128" required aria-describedby="oita-entry-error"><label class="oita-entry-check"><input id="oita-entry-accept" type="checkbox" required><span>検討用ドラフトであることと、取扱いの注意に同意します</span></label><p id="oita-entry-error" class="oita-entry-error" role="status" aria-live="polite">入口を読み込んでいます…</p><button class="oita-entry-submit" type="submit" disabled>同意して閲覧する →</button></form></div>`;
  document.body.append(dialog);
  const input=dialog.querySelector('#oita-entry-password'),accept=dialog.querySelector('#oita-entry-accept'),form=dialog.querySelector('form'),button=dialog.querySelector('button'),error=dialog.querySelector('[role="status"]');
  let config=null,busy=false;
  accept.addEventListener('change',()=>{button.disabled=!config||!accept.checked||busy;});
  function finish(){input.value='';dialog.close();dialog.remove();const heading=document.querySelector('main h1,h1');if(heading){heading.tabIndex=-1;heading.focus({preventScroll:true});}}
  dialog.addEventListener('cancel',event=>event.preventDefault());
  dialog.showModal(); input.focus({preventScroll:true});
  form.addEventListener('submit',async event=>{
    event.preventDefault();
    if (busy || !config) return;
    if (!accept.checked) {error.textContent='取扱いの注意への同意を確認してください。';accept.focus();return;}
    if (!input.value.trim()) {error.textContent='パスワードを入力してください。';input.focus();return;}
    busy=true;button.disabled=true;accept.disabled=true;error.textContent='確認しています…';
    try {
      const accepted=await OitaEntryCrypto.verify(input.value,config);
      input.value='';
      if (accepted && accept.checked) {try{sessionStorage.setItem(namespace,config.id);}catch(_){}finish();return;}
      error.textContent='パスワードが違います。もう一度入力してください。';input.focus();
    } catch (_) {input.value='';error.textContent='確認できませんでした。ページを再読み込みしてお試しください。';}
    finally {busy=false;accept.disabled=false;button.disabled=!accept.checked;}
  });
  fetch(configUrl,{cache:'no-store',credentials:'omit'})
    .then(response=>{if(!response.ok)throw new Error('configuration');return response.json();})
    .then(value=>{
      if(!window.OitaEntryCrypto || !OitaEntryCrypto.valid(value))throw new Error('configuration');
      config=value;
      let admitted=false;try{admitted=sessionStorage.getItem(namespace)===config.id;}catch(_){}
      if(admitted){finish();return;}
      error.textContent='';button.disabled=!accept.checked;
    }).catch(()=>{error.textContent='入口の設定を読み込めませんでした。ページを再読み込みしてください。';button.disabled=true;});
})();
