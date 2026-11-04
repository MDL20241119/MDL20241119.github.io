(() => {
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const button = document.querySelector('#motion-toggle');
  let paused = reduced.matches;
  function update() {
    document.body.classList.toggle('motion-off', paused);
    button.setAttribute('aria-pressed', String(paused));
    button.textContent = paused ? '動き：停止中' : '動きを止める';
  }
  button.addEventListener('click', () => { paused = !paused; update(); });
  reduced.addEventListener('change', e => { if (e.matches) { paused = true; update(); } });
  update();
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => { if (entry.isIntersecting) { entry.target.classList.add('in-view'); observer.unobserve(entry.target); } });
    }, { threshold: .15 });
    document.querySelectorAll('.bars, .donut').forEach(el => observer.observe(el));
  }
  document.querySelector('#print-page').addEventListener('click', () => window.print());
})();

// Reveal source rows inside long statistical appendices before following the link.
document.addEventListener('click',event=>{const link=event.target.closest('a[href^="#record-"]');if(!link)return;const target=document.getElementById(link.getAttribute('href').slice(1));if(!target)return;let p=target.parentElement;while(p){if(p.tagName==='DETAILS')p.open=true;p=p.parentElement;}});
