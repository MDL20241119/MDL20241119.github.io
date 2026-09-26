(() => {
  'use strict';
  const resources = JSON.parse(document.getElementById('resource-config').textContent);
  const frame = document.getElementById('tool-frame');
  const loading = document.getElementById('tool-loading');
  const links = [...document.querySelectorAll('[data-view]')];
  let current;
  let slowTimer;

  function show(view, push = false) {
    const resource = resources.find(item => item.id === view) || resources[0];
    if (push) {
      const url = new URL(location.href);
      url.searchParams.set('view', resource.id);
      history.pushState(null, '', url);
    }
    links.forEach(link => {
      if (link.dataset.view === resource.id) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    document.getElementById('tool-title').textContent = resource.name;
    document.getElementById('tool-kicker').textContent = `${resource.number} / ${resource.label}`;
    document.getElementById('tool-description').textContent = resource.description;
    document.getElementById('tool-direct').href = resource.source;
    document.title = `${resource.name}｜大分未来モビリティ・コンソーシアム`;
    if (current === resource.id) return;
    current = resource.id;
    frame.title = resource.name;
    loading.hidden = false;
    loading.textContent = 'ページを読み込んでいます…';
    clearTimeout(slowTimer);
    slowTimer = setTimeout(() => {
      loading.textContent = '表示に時間がかかる場合は「画面を大きく開く」からご覧ください。';
    }, 15000);
    frame.src = resource.source;
  }

  frame.addEventListener('load', () => {
    if (frame.src === 'about:blank') return;
    loading.hidden = true;
    clearTimeout(slowTimer);
  });
  links.forEach(link => link.addEventListener('click', event => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    show(link.dataset.view, true);
  }));
  window.addEventListener('popstate', () => show(new URL(location.href).searchParams.get('view')));
  show(new URL(location.href).searchParams.get('view'));
})();
