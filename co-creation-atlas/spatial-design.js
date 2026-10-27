/* Progressive enhancement; all research, sources and real photo links work without JS. */
(() => {
  'use strict';
  const filters = document.querySelector('.sd-filters');
  if (filters) {
    const buttons = [...filters.querySelectorAll('[data-sd-company]')];
    const cards = [...document.querySelectorAll('.sd-index-card')];
    const count = document.querySelector('#sd-result-count');
    const select = value => {
      if (!buttons.some(b => b.dataset.sdCompany === value)) value = 'all';
      buttons.forEach(b => b.setAttribute('aria-pressed', String(b.dataset.sdCompany === value)));
      cards.forEach(card => { card.hidden = value !== 'all' && card.dataset.company !== value; });
      count.textContent = `${cards.filter(c => !c.hidden).length}件の実空間`;
    };
    const current = () => new URL(location.href).searchParams.get('company') || 'all';
    filters.hidden = false;
    select(current());
    buttons.forEach(button => button.addEventListener('click', () => {
      const value = button.dataset.sdCompany;
      select(value);
      const url = new URL(location.href);
      if (value === 'all') url.searchParams.delete('company');
      else url.searchParams.set('company', value);
      history.pushState(null, '', url.pathname + url.search + url.hash);
    }));
    addEventListener('popstate', () => select(current()));
  }

  const modal = document.querySelector('.sd-lightbox');
  if (!modal || typeof modal.showModal !== 'function') return;
  let trigger;
  document.querySelectorAll('[data-sd-photo]').forEach(anchor => {
    anchor.addEventListener('click', event => {
      event.preventDefault();
      trigger = anchor;
      const image = modal.querySelector('img');
      image.src = anchor.href;
      image.alt = anchor.querySelector('img').alt;
      modal.querySelector('h2').textContent = anchor.dataset.title;
      modal.querySelector('[data-caption]').textContent = anchor.dataset.caption;
      modal.querySelector('[data-credit]').textContent = anchor.dataset.credit;
      const source = modal.querySelector('[data-source]');
      source.href = anchor.dataset.source;
      const license = modal.querySelector('[data-license]');
      license.href = anchor.dataset.licenseUrl;
      license.textContent = anchor.dataset.license + ' ↗';
      modal.showModal();
    });
  });
  modal.querySelector('[data-sd-close]').addEventListener('click', () => modal.close());
  modal.addEventListener('close', () => {
    modal.querySelector('img').removeAttribute('src');
    if (trigger?.isConnected) trigger.focus();
  });
  modal.addEventListener('click', event => {
    if (event.target !== modal) return;
    const box = modal.getBoundingClientRect();
    if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) modal.close();
  });
})();
