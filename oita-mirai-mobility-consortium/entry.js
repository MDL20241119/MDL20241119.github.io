(() => {
  'use strict';
  // A local acknowledgement only. This is not authentication or access control.
  const key = 'oita-draft-handling-20261009';
  const url = new URL(location.href);
  const reset = () => { try { sessionStorage.removeItem(key); } catch (_) {} };
  document.querySelectorAll('[data-entry-reset]').forEach(a => a.addEventListener('click', reset));
  if (url.searchParams.get('entry') === '1') {
    reset();
    url.searchParams.delete('entry');
    history.replaceState(null, '', url.pathname + url.search + url.hash);
  }
  let confirmed = false;
  try { confirmed = sessionStorage.getItem(key) === 'acknowledged'; } catch (_) {}
  if (confirmed) return;
  const dialog = document.createElement('dialog');
  dialog.className = 'oita-entry-dialog';
  dialog.setAttribute('aria-labelledby', 'oita-entry-title');
  dialog.setAttribute('aria-describedby', 'oita-entry-description');
  dialog.innerHTML = `<div class="oita-entry-inner"><span class="oita-entry-mark" aria-hidden="true">O.</span><p class="oita-entry-eyebrow">OITA MIRAI MOBILITY CONSORTIUM</p><h1 id="oita-entry-title">検討用ドラフト<br>関係者向けの閲覧資料</h1><p class="oita-entry-copy" id="oita-entry-description">TCO・MDLによる検討たたき台です。<br>記載する参画・役割・費用負担等は未合意です。<br>資料のお取り扱いにご注意ください。</p><p class="oita-entry-fine">この入口は取扱いの確認です。アクセスを制限する認証ではなく、本文・PDF・写真は直リンクからも閲覧できます。</p><form><label class="oita-entry-check"><input type="checkbox" name="acknowledge" required><span>検討用ドラフトであることと、取扱いの注意を確認しました</span></label><button class="oita-entry-submit" type="submit" disabled>確認して閲覧する →</button></form></div>`;
  document.body.append(dialog);
  const form = dialog.querySelector('form');
  const check = dialog.querySelector('input');
  const button = dialog.querySelector('button');
  check.addEventListener('change', () => { button.disabled = !check.checked; });
  form.addEventListener('submit', event => {
    event.preventDefault();
    if (!check.checked) return;
    try { sessionStorage.setItem(key, 'acknowledged'); } catch (_) {}
    dialog.close();
    dialog.remove();
    const heading = document.querySelector('main h1, h1');
    if (heading) { heading.tabIndex = -1; heading.focus({ preventScroll: true }); }
  });
  dialog.addEventListener('cancel', event => event.preventDefault());
  dialog.showModal();
  check.focus({ preventScroll: true });
})();
