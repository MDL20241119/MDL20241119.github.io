'use strict';
(() => {
  const motion = document.querySelector('#motion-toggle');
  const media = matchMedia('(prefers-reduced-motion: reduce)');
  let manual = false;
  function setMotion(off) { document.body.dataset.motion = off ? 'off' : 'on'; motion.setAttribute('aria-pressed', String(off)); motion.textContent = off ? '動きを再生' : '動きを止める'; }
  setMotion(media.matches);
  media.addEventListener('change', e => { if (!manual) setMotion(e.matches); });
  motion.addEventListener('click', () => { manual = true; setMotion(document.body.dataset.motion !== 'off'); });
  if ('IntersectionObserver' in window) {
    const io = new IntersectionObserver(entries => entries.forEach(entry => { if (entry.isIntersecting) { entry.target.classList.add('in-view'); io.unobserve(entry.target); } }), {threshold:.12});
    document.querySelectorAll('.primary-grid,.bars,.foreign-grid,.circle-grid').forEach(node => io.observe(node));
  }
  let ticking = false;
  function progress() { const max = document.documentElement.scrollHeight - innerHeight; document.querySelector('.reading-progress').style.width = (max > 0 ? Math.max(0,Math.min(100,scrollY/max*100)) : 0) + '%'; ticking = false; }
  addEventListener('scroll',()=>{if(!ticking){requestAnimationFrame(progress);ticking=true;}},{passive:true});
  addEventListener('resize',progress); progress();
  const dialog = document.querySelector('#photo-dialog');
  let opener;
  function closePhoto() { dialog.close(); if (opener) opener.focus(); }
  document.querySelectorAll('[data-photo]').forEach(button => button.addEventListener('click', () => {
    opener = button;
    const source = button.querySelector('img');
    dialog.querySelector('img').src = source.getAttribute('src');
    dialog.querySelector('img').alt = source.alt;
    dialog.querySelector('p').textContent = button.closest('figure').querySelector('figcaption').textContent;
    dialog.showModal();
  }));
  dialog.querySelector('.dialog-close').addEventListener('click',closePhoto);
  dialog.addEventListener('cancel',e=>{e.preventDefault();closePhoto();});
  dialog.addEventListener('click',e=>{if(e.target===dialog){const r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)closePhoto();}});
  dialog.querySelector('a').addEventListener('click',()=>dialog.close());
})();

(() => {
  const presets = document.querySelector('#journey-presets');
  const result = document.querySelector('#journey-remaining');
  const equation = document.querySelector('#journey-equation');
  if (!presets || !result || !equation) return;
  function update() {
    const selected = presets.querySelector('input:checked');
    if (!selected) return;
    const minutes = Number(selected.value);
    const unit = document.createElement('span');
    unit.textContent = '分';
    result.replaceChildren(`${minutes - 60}〜${minutes - 50}`, unit);
    equation.textContent = `${minutes}分 − 往復徒歩50〜60分`;
  }
  presets.addEventListener('change', update);
  update();
})();

(() => {
  const section = document.getElementById('nolc-data');
  if (!section) return;
  const { stops, matrix } = JSON.parse(section.querySelector('#od-matrix').textContent);
  const picker = section.querySelector('#od-stop');
  const rows = Array.from(section.querySelectorAll('.od-table tbody tr'));

  function update() {
    const point = Number(picker.value);
    const routes = stops.map((stop, i) => ({
      stop, index: i, out: matrix[point][i], inbound: matrix[i][point],
    })).filter(route => route.index !== point)
      .sort((a, b) => (b.out + b.inbound) - (a.out + a.inbound) || a.index - b.index);
    rows.forEach((row, i) => {
      const route = routes[i];
      row.cells[0].textContent = route.stop;
      [route.out, route.inbound].forEach((count, j) => {
        const cell = row.cells[j + 1];
        cell.querySelector('b').textContent = count;
        cell.querySelector('progress').value = count;
      });
    });
    section.querySelector('[data-od-active]').textContent = stops[point];
    section.querySelector('[data-od-out]').textContent = matrix[point].reduce((sum, n) => sum + n, 0);
    section.querySelector('[data-od-in]').textContent = matrix.reduce((sum, row) => sum + row[point], 0);
  }

  picker.addEventListener('change', update);
  update();
  section.querySelector('.od-picker').hidden = false;
})();
