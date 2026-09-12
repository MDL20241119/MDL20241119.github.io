(() => {
  const dialog = document.querySelector('#case-lightbox');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  const image = dialog.querySelector('.lightbox-image');
  const caption = dialog.querySelector('#lightbox-caption');
  const original = dialog.querySelector('.lightbox-original');
  let previousFocus;
  document.querySelectorAll('a.zoom-image').forEach(link => {
    link.addEventListener('click', event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      previousFocus = link;
      image.src = link.href;
      image.alt = link.querySelector('img')?.alt || '';
      caption.textContent = link.dataset.caption || image.alt;
      original.href = link.href;
      dialog.showModal();
    });
  });
  dialog.querySelector('.lightbox-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
  });
  dialog.addEventListener('close', () => previousFocus?.focus());
})();
