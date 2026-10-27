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
  let trigger, photos = [], currentIndex = 0;
  const previous = modal.querySelector('[data-sd-prev]');
  const next = modal.querySelector('[data-sd-next]');
  const showPhoto = index => {
    currentIndex = (index + photos.length) % photos.length;
    const photo = photos[currentIndex];
    const image = modal.querySelector('img');
    image.src = photo.src;
    image.alt = photo.alt;
    modal.querySelector('h2').textContent = photo.title;
    modal.querySelector('[data-caption]').textContent = photo.caption;
    modal.querySelector('[data-credit]').textContent = photo.credit;
    const creditLinks = modal.querySelector('[data-credit-links]');
    creditLinks.replaceChildren();
    (photo.creditLinks || []).forEach((credit, i) => {
      if (i) creditLinks.append(' · ');
      const a = document.createElement('a');
      a.href = credit.url;
      a.textContent = credit.label + ' ↗';
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      creditLinks.append(a);
    });
    creditLinks.hidden = !photo.creditLinks?.length;
    const originalTitle = modal.querySelector('[data-original-title]');
    originalTitle.textContent = photo.photoTitle ? '原題：' + photo.photoTitle : '';
    originalTitle.hidden = !photo.photoTitle;
    modal.querySelector('[data-photo-meta]').textContent = photo.meta || '';
    modal.querySelector('[data-kind-label]').textContent = photo.kindLabel || '写真';
    const usage = modal.querySelector('[data-usage]');
    usage.textContent = photo.usage || '';
    usage.hidden = !photo.usage;
    modal.querySelector('[data-source]').href = photo.source;
    const license = modal.querySelector('[data-license]');
    license.href = photo.licenseUrl;
    license.textContent = photo.license + ' ↗';
    modal.querySelector('[data-sd-count]').textContent = `${currentIndex + 1} / ${photos.length}`;
    previous.hidden = next.hidden = photos.length < 2;
  };
  document.querySelectorAll('[data-sd-photo]').forEach(anchor => {
    anchor.addEventListener('click', event => {
      const payload = anchor.closest('[data-sd-gallery]')?.querySelector('[data-sd-photo-set]');
      let set;
      try { set = JSON.parse(payload?.textContent || 'null'); } catch { return; }
      if (!set || set.projectId !== anchor.dataset.sdProject || !Array.isArray(set.photos)) return;
      const index = set.photos.findIndex(photo => photo.id === anchor.dataset.sdPhotoId);
      if (index < 0) return;
      event.preventDefault();
      trigger = anchor;
      photos = set.photos;
      showPhoto(index);
      modal.showModal();
    });
  });
  previous.addEventListener('click', () => showPhoto(currentIndex - 1));
  next.addEventListener('click', () => showPhoto(currentIndex + 1));
  modal.addEventListener('keydown', event => {
    if (!modal.open || event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
    event.preventDefault();
    showPhoto(currentIndex + (event.key === 'ArrowLeft' ? -1 : 1));
  });
  modal.querySelector('[data-sd-close]').addEventListener('click', () => modal.close());
  modal.addEventListener('close', () => {
    modal.querySelector('img').removeAttribute('src');
    photos = [];
    if (trigger?.isConnected) trigger.focus();
  });
  modal.addEventListener('click', event => {
    if (event.target !== modal) return;
    const box = modal.getBoundingClientRect();
    if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) modal.close();
  });
})();
