(() => {
  'use strict';
  const base = '/oita-mirai-mobility-consortium/';
  const configUrl = base + 'entry-verifier.json';
  const namespace = 'oita-password-entry-v1';
  const url = new URL(location.href);
  // Browser-session scope only: no password, persistent expiry, domain widening or URL token.
  const cookieName = namespace + '-session';
  const cookieScope = location.protocol === 'https:' && location.pathname.startsWith(base);
  const readSession = () => {
    if (!cookieScope) return null;
    try { const value = document.cookie.split('; ').find(part => part.startsWith(cookieName + '=')); return value ? decodeURIComponent(value.slice(cookieName.length + 1)) : null; } catch (_) { return null; }
  };
  const writeSession = value => {
    if (!cookieScope) return;
    document.cookie = cookieName + '=' + encodeURIComponent(value) + '; Path=' + base + '; SameSite=Strict; Secure';
  };
  const remember = id => { try { sessionStorage.setItem(namespace,id); } catch (_) {} try { writeSession(id); } catch (_) {} };
  const reset = () => {
    try { sessionStorage.removeItem(namespace); } catch (_) {}
    // A session-only tombstone also invalidates older tab-local admission markers.
    try { writeSession('signed-out'); } catch (_) {}
  };
  document.querySelectorAll('[data-entry-reset]').forEach(a => a.addEventListener('click', reset));
  if (url.searchParams.get('entry') === '1') {
    reset(); url.searchParams.delete('entry');
    history.replaceState(null,'',url.pathname+url.search+url.hash);
  }
  const dialog=document.createElement('dialog');
  dialog.className='oita-entry-dialog';
  dialog.setAttribute('aria-labelledby','oita-entry-title');
  dialog.setAttribute('aria-describedby','oita-entry-description');
  const documents = [
    {title:'構想説明書・設立趣意書',label:'構想・設立趣意書',web:'read/main/',pdf:'main',pages:8},
    {title:'発起人・会員・役員名簿',label:'発起人・会員・役員',web:'members/',pdf:'members',pages:3},
    {title:'規約',label:'規約',web:'rules/',pdf:'rules',pages:6},
    {title:'事務局の役割分担・会計',label:'事務局・会計',web:'secretariat/',pdf:'secretariat',pages:4},
    {title:'参加申込・承諾書',label:'参加申込・承諾書',web:null,pdf:'participants',pages:1},
    {title:'設立準備・補助事業の参考資料',label:'設立準備・補助事業',web:'reference/administrative-checks/',pdf:'administrative-checks',pages:3},
    {title:'参加・連携候補と根拠資料',label:'参加・連携候補（別紙）',web:'read/annex/',pdf:'annex',pages:29}
  ];
  const directoryPaths = ['', 'guide/', 'concept/', 'organization/', ...documents.filter(d=>d.web).map(d=>d.web)];
  const showDirectory = directoryPaths.some(path=>location.pathname===base+path);
  let destination = location.href;
  const currentDocument=documents.find(d=>d.web && location.pathname===base+d.web);
  const currentTitle=currentDocument?.label || ({'guide/':'資料一覧','concept/':'構想紹介','organization/':'組織・役割・会費'}[location.pathname.slice(base.length)] || 'ホームページ');
  if (showDirectory) {
    dialog.classList.add('oita-entry-with-directory');
    const rows=documents.map((d,i)=>{
      const label=`<span class="oita-entry-doc-number">${String(i+1).padStart(2,'0')}</span><span class="oita-entry-doc-title">${d.label}</span>`;
      const choice=d.web ? `<button type="button" class="oita-entry-doc-choice" data-entry-destination="${base+d.web}" data-entry-label="${d.label}" aria-pressed="${d===currentDocument}" aria-label="${d.title}をWebで読む">${label}<span class="oita-entry-doc-format">Web</span></button>` : `<span class="oita-entry-doc-choice oita-entry-doc-static">${label}<span class="oita-entry-doc-format">様式</span></span>`;
      return `<li>${choice}<a class="oita-entry-doc-pdf" href="${base}documents/${d.pdf}.pdf?v=20261110-final-draft" target="_blank" rel="noopener" aria-label="${d.title}のPDF・${d.pages}ページを開く">PDF <small>${d.pages}p</small></a></li>`;
    }).join('');
    dialog.innerHTML=`<div class="oita-entry-inner"><header class="oita-entry-directory-header"><p class="oita-entry-eyebrow">大分未来モビリティコンソーシアム</p><h1 id="oita-entry-title" tabindex="-1" autofocus>資料を、ここから。</h1></header><div class="oita-entry-directory-layout"><nav class="oita-entry-directory" aria-labelledby="oita-entry-directory-title"><div class="oita-entry-directory-heading"><h2 id="oita-entry-directory-title">資料一覧</h2><p id="oita-entry-description">Webを選んでログイン。PDFはそのまま開けます。</p></div><ol class="oita-entry-docs">${rows}</ol></nav><section class="oita-entry-auth" aria-labelledby="oita-entry-auth-title"><div class="oita-entry-auth-heading"><h2 id="oita-entry-auth-title">ログイン</h2><p>閲覧先：<strong id="oita-entry-selected" aria-live="polite">${currentTitle}</strong></p></div><form autocomplete="off" novalidate><label class="oita-entry-password-label" for="oita-entry-password">パスワード</label><input id="oita-entry-password" class="oita-entry-password" type="password" autocomplete="off" maxlength="128" required aria-describedby="oita-entry-error"><label class="oita-entry-check"><input id="oita-entry-accept" type="checkbox" required><span>設立準備案・資料の取扱いに同意</span></label><p id="oita-entry-error" class="oita-entry-error" role="status" aria-live="polite">入口を読み込んでいます…</p><button class="oita-entry-submit" type="submit" disabled>同意して閲覧する →</button></form></section></div><p class="oita-entry-fine">設立準備案です。参画・就任・費用負担は了承後に確定します。本文・PDFは直リンクでも閲覧できます。</p></div>`;
  } else {
  dialog.innerHTML=`<div class="oita-entry-inner"><span class="oita-entry-mark" aria-hidden="true">O.</span><p class="oita-entry-eyebrow">OITA MIRAI MOBILITY CONSORTIUM</p><h1 id="oita-entry-title">関係者向け<br>パスワード入力</h1><p class="oita-entry-copy" id="oita-entry-description">検討用ドラフトです。共有されたパスワードを入力してお進みください。同じブラウザーのセッション中は、このコンソーシアム内の資料でも入力を引き継ぎます。</p><p class="oita-entry-fine">TCO・MDL案。参画・役割・費用負担等は未合意です。簡易な入口のため、本文・PDF・写真は直リンクからも閲覧できます。</p><form autocomplete="off" novalidate><label class="oita-entry-password-label" for="oita-entry-password">パスワード</label><input id="oita-entry-password" class="oita-entry-password" type="password" autocomplete="off" maxlength="128" required aria-describedby="oita-entry-error"><label class="oita-entry-check"><input id="oita-entry-accept" type="checkbox" required><span>検討用ドラフトであることと、取扱いの注意に同意します</span></label><p id="oita-entry-error" class="oita-entry-error" role="status" aria-live="polite">入口を読み込んでいます…</p><button class="oita-entry-submit" type="submit" disabled>同意して閲覧する →</button></form></div>`;
  }
  document.body.append(dialog);
  const input=dialog.querySelector('#oita-entry-password'),accept=dialog.querySelector('#oita-entry-accept'),form=dialog.querySelector('form'),button=dialog.querySelector('.oita-entry-submit'),error=dialog.querySelector('[role="status"]');
  let config=null,busy=false;
  dialog.querySelectorAll('[data-entry-destination]').forEach(choice=>choice.addEventListener('click',()=>{
    if(busy)return;
    destination=new URL(choice.dataset.entryDestination,location.origin).href;
    dialog.querySelectorAll('[data-entry-destination]').forEach(item=>item.setAttribute('aria-pressed',String(item===choice)));
    dialog.querySelector('#oita-entry-selected').textContent=choice.dataset.entryLabel;
  }));
  accept.addEventListener('change',()=>{button.disabled=!config||!accept.checked||busy;});
  function finish(navigate=false){input.value='';dialog.close();dialog.remove();if(navigate && destination!==location.href){location.assign(destination);return;}const heading=document.querySelector('main h1,h1');if(heading){heading.tabIndex=-1;heading.focus({preventScroll:true});}}
  dialog.addEventListener('cancel',event=>event.preventDefault());
  dialog.showModal(); (showDirectory?dialog.querySelector('#oita-entry-title'):input).focus({preventScroll:true});
  form.addEventListener('submit',async event=>{
    event.preventDefault();
    if (busy || !config) return;
    if (!accept.checked) {error.textContent='取扱いの注意への同意を確認してください。';accept.focus();return;}
    if (!input.value.trim()) {error.textContent='パスワードを入力してください。';input.focus();return;}
    busy=true;button.disabled=true;accept.disabled=true;error.textContent='確認しています…';
    try {
      const accepted=await OitaEntryCrypto.verify(input.value,config);
      input.value='';
      if (accepted && accept.checked) {remember(config.id);finish(true);return;}
      error.textContent='パスワードが違います。もう一度入力してください。';input.focus();
    } catch (_) {input.value='';error.textContent='確認できませんでした。ページを再読み込みしてお試しください。';}
    finally {busy=false;accept.disabled=false;button.disabled=!accept.checked;}
  });
  fetch(configUrl,{cache:'no-store',credentials:'omit'})
    .then(response=>{if(!response.ok)throw new Error('configuration');return response.json();})
    .then(value=>{
      if(!window.OitaEntryCrypto || !OitaEntryCrypto.valid(value))throw new Error('configuration');
      config=value;
      let admitted=false;const shared=readSession();
      if(shared!==null){admitted=shared===config.id;if(!admitted){try{sessionStorage.removeItem(namespace);}catch(_){}}}
      else {try{admitted=sessionStorage.getItem(namespace)===config.id;}catch(_){}}
      if(admitted)remember(config.id);
      if(admitted){finish();return;}
      error.textContent='';button.disabled=!accept.checked;
    }).catch(()=>{error.textContent='入口の設定を読み込めませんでした。ページを再読み込みしてください。';button.disabled=true;});
})();
