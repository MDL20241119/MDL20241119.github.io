/* Browser-side encrypted publication. This is not server-side authentication. */
(() => {
  'use strict';
  const body = document.body;
  const storeName = 'mdl-yufuin-mec-key-v1';
  const root = document.querySelector('#access-gate');
  const viewer = document.querySelector('#access-viewer');
  const form = document.querySelector('#access-form');
  const input = document.querySelector('#access-password');
  const submit = document.querySelector('#access-submit');
  const status = document.querySelector('#access-status');
  const manifestURL = new URL(body.dataset.manifest, location.href);
  let manifest, key, frame, busy = false, pdfObjectURL = null;
  let channel = null, sharedRequest = null, generation = 0;
  const tabId = typeof crypto.randomUUID === 'function' ? crypto.randomUUID() : Array.from(crypto.getRandomValues(new Uint8Array(16)), b => b.toString(16).padStart(2, '0')).join('');
  const decode = b64 => Uint8Array.from(atob(b64), c => c.charCodeAt(0));
  const encode = data => btoa(String.fromCharCode(...new Uint8Array(data)));
  const hex = bytes => Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2, '0')).join('');
  const message = text => { status.textContent = text; };
  function storedKey() {
    try {
      const value = JSON.parse(sessionStorage.getItem(storeName) || 'null');
      if (!value || value.id !== manifest.key_id || !/^[A-Za-z0-9+/]{43}=$/.test(value.key)) return null;
      return decode(value.key);
    } catch (_) { return null; }
  }
  function clearKey() { try { sessionStorage.removeItem(storeName); } catch (_) {} }
  function saveKey(bytes) {
    try { sessionStorage.setItem(storeName, JSON.stringify({id: manifest.key_id, key: encode(bytes)})); } catch (_) {}
  }
  function publish(value) { try { if (channel) channel.postMessage({version: 1, from: tabId, ...value}); } catch (_) {} }
  function openChannel() {
    if (channel || typeof BroadcastChannel === 'undefined') return;
    try {
      channel = new BroadcastChannel('mdl-yufuin-mec-session-v1');
      channel.onmessage = event => {
        const data = event.data;
        if (!data || data.version !== 1 || typeof data.from !== 'string' || data.from === tabId) return;
        if (data.kind === 'lock') { lock(false); return; }
        if (!manifest || data.id !== manifest.key_id) return;
        if (data.kind === 'request' && key && frame && typeof data.nonce === 'string' && /^[a-f0-9]{32}$/.test(data.nonce)) {
          const bytes = storedKey();
          if (bytes) {
            publish({kind: 'key', id: manifest.key_id, to: data.from, nonce: data.nonce, key: encode(bytes)});
            bytes.fill(0);
          }
        }
        if (data.kind === 'key' && sharedRequest && data.to === tabId && data.nonce === sharedRequest.nonce
            && typeof data.key === 'string' && /^[A-Za-z0-9+/]{43}=$/.test(data.key)) {
          const pending = sharedRequest; sharedRequest = null;
          clearTimeout(pending.timeout); pending.resolve(decode(data.key));
        }
      };
    } catch (_) { channel = null; }
  }
  function requestSharedKey() {
    if (!channel) return Promise.resolve(null);
    return new Promise(resolve => {
      const nonce = Array.from(crypto.getRandomValues(new Uint8Array(16)), b => b.toString(16).padStart(2, '0')).join('');
      const timeout = setTimeout(() => {
        if (sharedRequest?.nonce !== nonce) return;
        sharedRequest = null; resolve(null);
      }, 800);
      sharedRequest = {nonce, resolve, timeout};
      publish({kind: 'request', id: manifest.key_id, nonce});
    });
  }
  function cancelSharedRequest() {
    if (!sharedRequest) return;
    const pending = sharedRequest; sharedRequest = null;
    clearTimeout(pending.timeout); pending.resolve(null);
  }
  function supported() {
    return isSecureContext && !!crypto.subtle && typeof DecompressionStream !== 'undefined';
  }
  function validManifest(value) {
    return value && value.version === 1 && value.kdf === 'PBKDF2-SHA256'
      && value.iterations === 600000 && value.cipher === 'AES-256-GCM'
      && /^[a-f0-9]{32}$/.test(value.key_id) && typeof value.salt === 'string'
      && value.assets?.content && value.assets?.proposal;
  }
  async function decryptAsset(name, decryptKey) {
    const asset = manifest.assets[name];
    if (!asset || !Array.isArray(asset.chunks) || asset.chunks.length < 1
        || !Number.isSafeInteger(asset.bytes) || asset.bytes < 16 || asset.bytes > 67108864) throw Error('asset');
    const chunks = new Array(asset.chunks.length);
    let nextIndex = 0;
    async function fetchWorker() {
      while (nextIndex < asset.chunks.length) {
        const index = nextIndex++;
        const url = new URL(asset.chunks[index], manifestURL);
        if (url.origin !== manifestURL.origin || !url.pathname.startsWith(manifestURL.pathname.replace(/[^/]*$/, 'payload/'))) throw Error('path');
        const response = await fetch(url, {credentials: 'omit', cache: 'force-cache', referrerPolicy: 'no-referrer'});
        if (!response.ok) throw Error('network');
        chunks[index] = new Uint8Array(await response.arrayBuffer());
      }
    }
    await Promise.all(Array.from({length: Math.min(4, asset.chunks.length)}, fetchWorker));
    if (chunks.reduce((n, c) => n + c.byteLength, 0) !== asset.bytes) throw Error('length');
    const ciphertext = new Uint8Array(asset.bytes);
    let offset = 0;
    for (const chunk of chunks) { ciphertext.set(chunk, offset); offset += chunk.byteLength; }
    const digest = hex(await crypto.subtle.digest('SHA-256', ciphertext));
    if (digest !== asset.sha256) throw Error('digest');
    const compressed = await crypto.subtle.decrypt({name: 'AES-GCM', iv: decode(asset.iv), additionalData: new TextEncoder().encode('yufuin-mec-v1:' + name)}, decryptKey, ciphertext);
    const stream = new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'));
    return new Uint8Array(await new Response(stream).arrayBuffer());
  }
  async function getKey(password) {
    const passwordBytes = new TextEncoder().encode(password);
    try {
      const material = await crypto.subtle.importKey('raw', passwordBytes, 'PBKDF2', false, ['deriveBits']);
      return new Uint8Array(await crypto.subtle.deriveBits({name: 'PBKDF2', hash: 'SHA-256', salt: decode(manifest.salt), iterations: manifest.iterations}, material, 256));
    } finally { passwordBytes.fill(0); }
  }
  const importKey = bytes => crypto.subtle.importKey('raw', bytes, 'AES-GCM', false, ['decrypt']);
  function bridgeHTML(html) {
    const base = new URL('../../', manifestURL).href;
    const initHash = location.hash;
    const bridge = `<script>(function(){'use strict';const initialHash=${JSON.stringify(initHash).replace(/</g, '\\u003c')};function go(hash){try{const target=document.getElementById(decodeURIComponent(hash.slice(1)));if(target){target.scrollIntoView();parent.postMessage({type:'yufuin-hash',hash},'*');}}catch(_){}}document.addEventListener('click',function(e){const anchor=e.target.closest('a[href]');if(anchor){const href=anchor.getAttribute('href');if(href.startsWith('#')){e.preventDefault();go(href);return;}if(/(?:^|\\/)yufuin\\/pdf\\.html(?:[?#]|$)/.test(href)){e.preventDefault();parent.postMessage({type:'yufuin-download',key:'proposal'},'*');return;}}const node=e.target.closest('[data-yufuin-pdf],[data-yufuin-lock],[data-yufuin-print]');if(!node)return;e.preventDefault();if(node.hasAttribute('data-yufuin-pdf'))parent.postMessage({type:'yufuin-download',key:'proposal'},'*');if(node.hasAttribute('data-yufuin-lock'))parent.postMessage({type:'yufuin-lock'},'*');if(node.hasAttribute('data-yufuin-print'))window.print();});document.querySelectorAll('a[href^="http"],a[href^="/"]').forEach(a=>{a.target='_blank';a.rel='noopener noreferrer';});if(initialHash){const ready=()=>{const fonts=document.fonts?document.fonts.ready:Promise.resolve();fonts.then(()=>requestAnimationFrame(()=>go(initialHash)));};if(document.readyState==='complete')ready();else window.addEventListener('load',ready,{once:true});}})();<\/script>`;
    // A base resolves existing relative links only; it does not expose the decrypted document.
    html = html.replace(/<head([^>]*)>/i, '<head$1><base href="' + base.replace(/"/g, '&quot;') + '">');
    return /<\/body\s*>/i.test(html) ? html.replace(/<\/body\s*>/i, bridge + '</body>') : html + bridge;
  }
  async function showContent(decryptKey, expectedGeneration = generation) {
    const htmlBytes = await decryptAsset('content', decryptKey);
    if (expectedGeneration !== generation) throw Error('cancelled');
    const html = new TextDecoder('utf-8', {fatal: true}).decode(htmlBytes);
    if (!/^<!doctype html/i.test(html.trim())) throw Error('html');
    const next = document.createElement('iframe');
    next.title = '湯布院 MEC Hub 企画';
    next.sandbox = 'allow-scripts allow-downloads allow-modals allow-popups allow-popups-to-escape-sandbox';
    next.referrerPolicy = 'no-referrer';
    next.srcdoc = bridgeHTML(html);
    viewer.replaceChildren(next); frame = next; key = decryptKey;
    root.hidden = true; viewer.hidden = false; body.classList.add('unlocked');
    document.title = '湯布院 MEC Hub｜MOBILITY DESIGN LAB';
    if (body.dataset.view === 'pdf') { document.querySelector('#pdf-action').hidden = false; }
    // A user click is required for a mobile browser download; the PDF launch page provides that click.
  }
  function lock(broadcast = true) {
    generation += 1;
    cancelSharedRequest();
    if (broadcast) publish({kind: 'lock'});
    clearKey(); key = null;
    if (frame) { frame.srcdoc = ''; frame.remove(); } frame = null;
    viewer.replaceChildren(); viewer.hidden = true;
    if (pdfObjectURL) { URL.revokeObjectURL(pdfObjectURL); pdfObjectURL = null; }
    root.hidden = false; body.classList.remove('unlocked');
    document.querySelector('#pdf-action').hidden = true;
    input.value = ''; message(''); input.focus();
  }
  async function downloadPDF() {
    if (!key || busy) return;
    busy = true;
    document.querySelector('#pdf-action').hidden = false;
    const action = document.querySelector('#pdf-download');
    const expectedGeneration = generation;
    action.disabled = true; action.textContent = 'PDFを開いています…';
    try {
      const bytes = await decryptAsset('proposal', key);
      if (expectedGeneration !== generation || !key) return;
      if (new TextDecoder().decode(bytes.slice(0, 5)) !== '%PDF-') throw Error('pdf');
      if (pdfObjectURL) URL.revokeObjectURL(pdfObjectURL);
      pdfObjectURL = URL.createObjectURL(new Blob([bytes], {type: 'application/pdf'}));
      const a = document.createElement('a'); a.href = pdfObjectURL;
      a.download = 'Yufuin-MEC-Hub-Proposal.pdf'; a.rel = 'noopener';
      document.body.append(a); a.click(); a.remove();
      action.textContent = 'PDFをダウンロード';
    } catch (_) { action.textContent = '取得できませんでした。もう一度開く'; }
    finally { busy = false; action.disabled = false; }
  }
  window.addEventListener('message', e => {
    if (!frame || e.source !== frame.contentWindow || !e.data || typeof e.data !== 'object') return;
    if (e.data.type === 'yufuin-download' && e.data.key === 'proposal') downloadPDF();
    if (e.data.type === 'yufuin-lock') lock();
    if (e.data.type === 'yufuin-hash' && typeof e.data.hash === 'string' && /^#[\w%\-]*$/.test(e.data.hash)) history.replaceState(null, '', location.pathname + location.search + e.data.hash);
  });
  document.querySelector('#pdf-download').addEventListener('click', downloadPDF);
  document.querySelector('#password-show').addEventListener('change', e => { input.type = e.target.checked ? 'text' : 'password'; });
  document.querySelector('#pdf-lock').addEventListener('click', lock);
  window.addEventListener('storage', e => { if (e.key === storeName && e.newValue === null) lock(); });
  window.addEventListener('pagehide', () => {
    generation += 1; cancelSharedRequest();
    if (channel) channel.close(); channel = null;
    key = null;
    if (frame) { frame.srcdoc = ''; frame.remove(); } frame = null;
    viewer.replaceChildren(); viewer.hidden = true; root.hidden = false;
    body.classList.remove('unlocked');
    if (pdfObjectURL) { URL.revokeObjectURL(pdfObjectURL); pdfObjectURL = null; }
  });
  window.addEventListener('pageshow', event => { if (event.persisted) initialize(); });
  form.addEventListener('submit', async e => {
    e.preventDefault(); if (busy || !manifest) return;
    busy = true; submit.disabled = true; message('資料を開いています…');
    const expectedGeneration = generation;
    let bytes;
    try {
      bytes = await getKey(input.value); input.value = '';
      if (expectedGeneration !== generation) throw Error('cancelled');
      const imported = await importKey(bytes);
      await showContent(imported, expectedGeneration); saveKey(bytes); message('');
    } catch (_) { clearKey(); message('パスワードが違うか、資料を取得できませんでした。'); input.value = ''; input.focus(); }
    finally { if (bytes) bytes.fill(0); busy = false; submit.disabled = false; }
  });
  async function initialize() {
    if (!supported()) { message('最新版のSafari、Chrome、Edgeで開いてください。'); return; }
    openChannel();
    const expectedGeneration = generation;
    try {
      const response = await fetch(manifestURL, {cache: 'no-store', credentials: 'omit', referrerPolicy: 'no-referrer'});
      if (!response.ok) throw Error('manifest');
      const value = await response.json(); if (!validManifest(value)) throw Error('manifest'); manifest = value;
      if (new URL(location.href).searchParams.get('lock') === '1') {
        lock(); history.replaceState(null, '', location.pathname + location.hash);
        message(''); submit.disabled = false; return;
      }
      let bytes = storedKey();
      if (!bytes) bytes = await requestSharedKey();
      if (bytes) {
        try {
          await showContent(await importKey(bytes), expectedGeneration);
          saveKey(bytes); return;
        } catch (_) { clearKey(); }
        finally { bytes.fill(0); }
      }
      message(''); submit.disabled = false;
    } catch (_) { message('資料を読み込めませんでした。再読み込みしてください。'); }
  }
  initialize();
})();
