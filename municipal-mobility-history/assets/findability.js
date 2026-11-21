(() => {
  'use strict';
  if (!document.body.matches('[data-municipal="true"]')) return;
  const main = document.getElementById('main');
  if (!main) return;
  const advancedMedia = window.matchMedia('(max-width: 720px)');
  const live = document.createElement('p');
  live.className = 'm-find-sr-only';
  live.setAttribute('role', 'status');
  live.setAttribute('aria-atomic', 'true');
  main.before(live);
  const enhanced = new WeakSet();
  let pending = null;
  let changingSelect = null;

  const make = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  };
  function route() {
    const [path, query] = location.hash.slice(1).split('?');
    return { path, params: new URLSearchParams(query) };
  }
  function formContext(form) {
    const parent = form.parentElement;
    const counts = Array.from(parent.querySelectorAll(':scope > .m-results-count, :scope > #m-atlas-results > .m-results-count'));
    return counts.at(-1) || null;
  }
  function describeFilters(form, params) {
    const labels = [];
    for (const field of form.querySelectorAll('select,input[type="search"]')) {
      const value = params.get(field.name);
      if (!value) continue;
      if (field.type === 'search') labels.push('検索：' + value);
      else if (field.selectedOptions[0]?.value === value) labels.push(field.selectedOptions[0].label);
    }
    if (params.get('topics')) {
      const matching = Array.from(main.querySelectorAll('[data-topic-button][aria-pressed="true"]'));
      if (matching.length) labels.push(...matching.map(button => button.firstElementChild?.firstChild?.textContent.trim()).filter(Boolean));
      else labels.push('テーマ選択中');
    }
    return labels;
  }
  function reveal(node) {
    for (let ancestor = node.parentElement; ancestor && ancestor !== main; ancestor = ancestor.parentElement) {
      if (ancestor.tagName === 'DETAILS') ancestor.open = true;
    }
  }
  function showResults(count) {
    if (!count) return;
    reveal(count);
    count.focus({ preventScroll: true });
    count.scrollIntoView({ block: 'start' });
  }
  function enhance(form) {
    const { path, params } = route();
    const grid = form.querySelector(':scope > .m-filter-grid');
    const search = form.querySelector(':scope > .m-search-row');
    const count = formContext(form);
    const labels = describeFilters(form, params);
    if (search && grid) {
      const controls = make('details', 'm-find-options');
      controls.append(make('summary', '', '条件で絞り込む（地域・年度など）'));
      grid.before(controls);
      for (const node of [grid, ...form.querySelectorAll(':scope > .m-more-filters, :scope > .m-catalog-theme, :scope > .m-program-filter')]) controls.append(node);
      controls.open = !advancedMedia.matches || !!pending?.expanded ||
        Array.from(controls.querySelectorAll('select, input[type="checkbox"]')).some(field => field.type === 'checkbox' ? field.checked : Boolean(params.get(field.name)));
    }
    const active = ['q','topics','kind','pref','municipality','year','agency','theme','state','evidence','program','purpose','lifecycle','class_status','review','batch']
      .filter(k => params.get(k) && !(k === 'kind' && form.dataset.view === 'catalog'));
    const actions = make('div','m-find-actions');
    if (labels.length) {
      const tags = make('ul','m-find-tags');
      tags.setAttribute('aria-label','適用中の検索条件');
      for (const label of labels) tags.append(make('li','',label));
      actions.append(tags);
    }
    if (active.length && path && !(form.dataset.view === 'catalog' && !count)) {
      const keep = new URLSearchParams();
      for (const key of form.dataset.view === 'catalog' ? ['kind'] : ['layer']) {
        if (params.get(key)) keep.set(key, params.get(key));
      }
      const reset = make('a','m-find-reset','絞り込みを解除');
      reset.href = '#' + path + (keep.size ? '?' + keep : '');
      reset.dataset.mnav = '';
      reset.dataset.findReset = '';
      actions.append(reset);
      if (count) {
        // Only remove the duplicate catalog reset, not the general research scope link.
        const duplicate = Array.from(count.querySelectorAll('a')).find(a => a.textContent.trim() === '絞り込みを解除');
        if (duplicate) duplicate.hidden = true;
      }
    }
    if (count) {
      const countLabel = count.querySelectorAll('p');
      count.classList.add('m-find-result');
      count.tabIndex = -1;
      count.setAttribute('role','group');
      count.setAttribute('aria-label','検索結果：' + Array.from(countLabel, el => el.textContent.replace(/\s+/g, ' ').trim()).join('、'));
      if (search && enabledJump(form)) {
        const jump = make('button','m-find-jump','検索結果へ ↓');
        jump.type = 'button';
        jump.addEventListener('click', () => showResults(count));
        actions.append(jump);
      }
    }
    if (actions.childElementCount) (search || grid || form.firstElementChild)?.after(actions);
    return count;
  }
  function enabledJump(form) {
    return form.dataset.view !== 'prefectures';
  }
  function sync() {
    const host = main.querySelector('[data-results-host]');
    if (!host || host.getAttribute('aria-busy') !== 'false' || enhanced.has(host)) return;
    enhanced.add(host);
    const forms = [...host.querySelectorAll('form[data-mfilter]')];
    const counts = forms.map(enhance);
    if (!pending) return;
    const work = pending;
    pending = null;
    if (performance.now() - work.at > 8000) return;
    const index = forms.findIndex(form => form.dataset.view === work.view);
    const form = index < 0 ? forms[0] : forms[index];
    const result = index < 0 ? counts[0] : counts[index];
    if (result) live.textContent = result.getAttribute('aria-label');
    if (work.topic) {
      const button = Array.from(host.querySelectorAll('[data-topic-code]')).find(el => el.dataset.topicCode === work.topic);
      if (button) {
        reveal(button);
        button.focus({preventScroll:true});
        button.scrollIntoView({block:'nearest'});
      }
    } else if (work.jump && result && form && enabledJump(form)) {
      showResults(result);
    } else if (work.focus && form) {
      const choices = Array.from(form.elements).filter(field => field.name === work.focus && field.type !== 'hidden');
      const target = choices.find(field => field.type === 'checkbox' && field.value === work.value) || choices[0];
      if (target) {
        reveal(target);
        target.focus({ preventScroll: true });
      }
    }
  }
  document.addEventListener('change', ev => {
    const field = ev.target;
    if (!main.contains(field) || !field.matches('form[data-mfilter] select')) return;
    changingSelect = field;
    queueMicrotask(() => { if (changingSelect === field) changingSelect = null; });
  }, true);
  document.addEventListener('submit', ev => {
    const form = ev.target;
    if (!main.contains(form) || !form.matches('[data-mfilter]')) return;
    const focused = changingSelect || document.activeElement;
    const selected = form.contains(focused) && focused.matches('select, input[type="checkbox"]');
    pending = { at:performance.now(), view:form.dataset.view, jump:!selected,
      focus:selected ? focused.name : null, value:selected ? focused.value : '',
      expanded: Boolean(form.querySelector('.m-find-options[open]')) };
  }, true);
  document.addEventListener('click', ev => {
    const a = ev.target.closest?.('[data-find-reset], [data-topic-code]');
    if (!a || !main.contains(a) || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
    pending = { at:performance.now(), view:a.closest('form')?.dataset.view, focus:a.hasAttribute('data-find-reset') ? 'q' : null,
      topic:a.dataset.topicCode };
  }, true);
  new MutationObserver(sync).observe(main, { childList:true, subtree:true, attributes:true, attributeFilter:['aria-busy'] });
  sync();
})();
