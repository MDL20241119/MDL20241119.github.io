/* Non-modal disclosure: native Enter/Space, normal Tab order, no body scroll lock. */
(() => {
  const header = document.querySelector('.consortium-head');
  const menu = header?.querySelector('.consortium-menu');
  if (!menu) return;
  const toggle = menu.querySelector('summary');
  const measure = () => document.documentElement.style.setProperty('--consortium-header-height', `${Math.ceil(header.getBoundingClientRect().height)}px`);
  const placePanel = () => menu.style.setProperty('--menu-top', `${Math.max(0, Math.ceil(header.getBoundingClientRect().bottom))}px`);
  const update = () => { measure(); placePanel(); };
  update();
  new ResizeObserver(update).observe(header);
  addEventListener('scroll', placePanel, {passive:true});
  addEventListener('resize', update);
  const close = (restoreFocus = false) => {
    menu.open = false;
    if (restoreFocus) toggle.focus({preventScroll:true});
  };
  menu.addEventListener('toggle', () => toggle.setAttribute('aria-expanded', String(menu.open)));
  toggle.setAttribute('aria-expanded', String(menu.open));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && menu.open) { event.preventDefault(); close(true); }
  });
  document.addEventListener('click', event => {
    if (menu.open && !menu.contains(event.target)) close();
  });
  menu.addEventListener('focusout', () => {
    requestAnimationFrame(() => { if (menu.open && !menu.contains(document.activeElement)) close(); });
  });
  header.addEventListener('click', event => {
    const link = event.target.closest('a');
    if (!link || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    close();
    const url = new URL(link.href, location.href);
    if (url.origin !== location.origin || url.pathname !== location.pathname || url.search !== location.search || !url.hash) return;
    let id;
    try { id = decodeURIComponent(url.hash.slice(1)); } catch { return; }
    const target = document.getElementById(id);
    if (!target) return;
    if (!target.hasAttribute('tabindex')) { target.setAttribute('tabindex', '-1'); target.addEventListener('blur', () => target.removeAttribute('tabindex'), {once:true}); }
    target.focus({preventScroll:true});
    // Native anchor navigation retains history, reduced-motion, and scroll-margin behavior.
  });
})();
