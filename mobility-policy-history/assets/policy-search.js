(() => {
  'use strict';
  const main = document.getElementById('main');
  if (!main || document.body.matches('[data-municipal="true"]')) return;
  const mobile = window.matchMedia('(max-width: 720px)');
  const forms = 'form#filters, form#source-search';
  const controls = new WeakSet();
  const live = document.createElement('p');
  live.className = 'p-find-sr-only';
  live.setAttribute('role','status');
  live.setAttribute('aria-atomic','true');
  main.before(live);
  let intent = null;

  function node(tag, className, label) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (label) el.textContent = label;
    return el;
  }
  function focusResults(results) {
    if (!results?.isConnected) return;
    results.focus({ preventScroll:true });
    results.scrollIntoView({ block:'start' });
  }
  function enhance(form) {
    if (controls.has(form)) return;
    controls.add(form);
    const isSource = form.id === 'source-search';
    const search = form.querySelector('.search-line');
    if (!search) return;
    const query = form.elements.namedItem('q');
    const grid = form.querySelector('.filters');
    const tools = form.querySelector('.filter-tools');
    const visibleSelections = Array.from(form.querySelectorAll('select')).filter(el=>el.value);
    const checked = Array.from(form.querySelectorAll('input[type="checkbox"]:checked'));
    const params = new URLSearchParams(location.hash.split('?')[1]);
    const hasFilters = Boolean(params.get('q') || params.get('status') || visibleSelections.length || checked.length);
    const labels = [
      ...(params.get('q') ? ['検索：' + params.get('q')] : []),
      ...visibleSelections.map(el=>el.selectedOptions[0]?.label).filter(Boolean),
      ...checked.map(el=>el.closest('label')?.textContent.trim()).filter(Boolean)
    ];
    if (params.get('status')) {
      const status = form.ownerDocument.querySelector('[aria-current="page"][data-status], [data-status].selected');
      labels.push(status?.textContent.trim() || '状態で絞り込み中');
    }
    if (!isSource && grid) {
      const details = node('details','p-find-options');
      details.append(node('summary','','条件で絞り込む（年度・省庁など）'));
      grid.before(details);
      details.append(grid);
      if (tools?.childElementCount) details.append(tools);
      details.open = !mobile.matches || Boolean(visibleSelections.length || checked.length || intent?.expanded);
    }

    const actions = node('div','p-find-actions');
    if (labels.length) {
      const list = node('ul','p-find-tags');
      list.setAttribute('aria-label','適用中の条件');
      labels.forEach(label=>list.append(node('li','',label)));
      actions.append(list);
    }
    const notice = node('p','p-find-hint','');
    notice.id = isSource ? 'p-find-source-hint' : 'p-find-query-hint';
    if (isSource) {
      query.placeholder = '例：資料名、S001';
      notice.textContent = '資料名や出典番号から探せます。';
    } else if (form.dataset.view === 'programs') {
      query.placeholder = '例：自動運転、MaaS';
      notice.textContent = '名称で検索するか、条件を選んで「検索」を押してください。';
    } else {
      query.placeholder = '例：自動運転、採択';
      notice.textContent = 'キーワードで検索するか、条件を選んで「検索」を押してください。';
    }
    query.setAttribute('aria-describedby',[query.getAttribute('aria-describedby'), notice.id].filter(Boolean).join(' '));
    const submit = search.querySelector('button[type=submit]');
    if (submit && !isSource) submit.textContent = '検索';

    let reset = form.querySelector('button[data-reset]');
    if (isSource && hasFilters) {
      reset = node('a','reset','検索を解除');
      reset.href = '#sources?section=source-list';
    }
    if (reset) {
      reset.dataset.policyReset = '';
      reset.classList.add('p-find-reset');
      if (hasFilters) actions.append(reset);
      else reset.hidden = true;
    }

    const results = form.closest('.filter-area')?.parentElement.querySelector(':scope > .result-heading');
    if (results) {
      const count = results.querySelector(':scope > div');
      results.classList.add('p-find-results');
      results.setAttribute('role','group');
      results.setAttribute('aria-label','検索結果：' + (count?.textContent.replace(/\s+/g,' ').trim() || '一覧'));
      count?.removeAttribute('aria-live');
      results.tabIndex = -1;
      const resultLink = node('button','p-find-jump','検索結果へ ↓');
      resultLink.type = 'button';
      resultLink.addEventListener('click',()=>focusResults(results));
      actions.append(resultLink);
    }
    search.after(notice, actions);
    return { results, query };
  }

  function update() {
    const form = main.querySelector(forms);
    if (!form || controls.has(form)) return;
    const state = enhance(form);
    if (!state || !intent || (form.dataset.view || 'sources') !== intent.view) return;
    const request = intent;
    intent = null;
    if (performance.now() - request.at > 5000) return;
    // Run after the history router's restoration of main focus and scroll.
    requestAnimationFrame(() => {
      if (!form.isConnected || !state.query?.isConnected) return;
      if (state.results) live.textContent = state.results.getAttribute('aria-label');
      if (request.reset) {
        state.query.focus({ preventScroll:true });
        state.query.scrollIntoView({ block:'nearest' });
      } else {
        focusResults(state.results);
      }
    });
  }
  document.addEventListener('submit', event => {
    const form = event.target;
    if (!form.matches(forms) || !main.contains(form)) return;
    intent = { view:form.dataset.view || 'sources', at:performance.now(), expanded:Boolean(form.querySelector('.p-find-options[open]')) };
  }, true);
  document.addEventListener('click', event => {
    const button = event.target.closest?.('[data-policy-reset]');
    if (!button || !main.contains(button) || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    intent = { view:button.closest('form')?.dataset.view || 'sources', at:performance.now(), reset:true };
  }, true);
  new MutationObserver(update).observe(main,{ childList:true, subtree:true });
  update();
})();
