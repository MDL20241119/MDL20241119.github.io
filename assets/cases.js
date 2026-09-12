(() => {
  const dialog = document.querySelector('#case-lightbox');
  if (!dialog || typeof dialog.showModal !== 'function') return;
  const image = dialog.querySelector('.lightbox-image');
  const caption = dialog.querySelector('#lightbox-caption');
  const original = dialog.querySelector('.lightbox-original');
  const status = dialog.querySelector('.lightbox-status');
  image.addEventListener('load', () => { if (status) status.textContent = ''; });
  image.addEventListener('error', () => {
    if (status) status.textContent = '画像を読み込めませんでした。「画像だけで開く」からご確認ください。';
  });
  let previousFocus;
  document.querySelectorAll('a.zoom-image').forEach(link => {
    link.addEventListener('click', event => {
      if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      previousFocus = link;
      const thumbnail = link.querySelector('img');
      image.width = thumbnail?.naturalWidth || Number(thumbnail?.getAttribute('width')) || 1536;
      image.height = thumbnail?.naturalHeight || Number(thumbnail?.getAttribute('height')) || 864;
      if (status) status.textContent = '画像を読み込んでいます…';
      image.src = link.href;
      image.alt = link.querySelector('img')?.alt || '';
      caption.textContent = link.dataset.caption || image.alt;
      original.href = link.href;
      if (image.complete && image.naturalWidth && status) status.textContent = '';
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
