(() => {
  const nav = document.querySelector('.oa-region-tabs');
  if (!nav) return;
  const links = [...nav.querySelectorAll('a')], panels = [...document.querySelectorAll('[data-oa-panel]')];
  function apply() {
    const id = location.hash.slice(1);
    const canonical = ['recent'].includes(id) ? 'citywide' : ['weekday','observed','reports'].includes(id) ? 'previous' : id;
    const active = panels.find(x => x.id === canonical)?.id || 'citywide';
    for (const p of panels) p.hidden = p.id !== active;
    for (const l of links) if (l.hash === '#'+active) l.setAttribute('aria-current','location'); else l.removeAttribute('aria-current');
  }
  nav.addEventListener('click', e => {
    const a=e.target.closest('a'); if(!a || e.button || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey)return;
    e.preventDefault(); if(location.hash!==a.hash)history.pushState(null,'',a.hash); apply();
  });
  for (const ev of ['hashchange','popstate']) window.addEventListener(ev,apply);
  apply();
  const raw = document.querySelector('#oa-hour-data');
  const data = raw ? JSON.parse(raw.textContent) : [];
  if (data.length !== 16 || data.some(x=>x.length!==2||x.some(n=>!Number.isInteger(n)||n<0))) return;
  const range = document.querySelector('#oa-hour'), chart = document.querySelector('#oa-bars');
  const max = Math.max(...data.map(([b,r])=>b+r));
  const pad = h => String(h).padStart(2,'0')+':00';
  const buttons = data.map(([bus,rail], i)=>{
    const h=i+6,b=document.createElement('button');
    b.type='button';b.setAttribute('aria-label',pad(h)+'台、'+(bus+rail)+'区域');
    const col=document.createElement('span');col.className='oa-hour-bar';col.style.height=(100*(bus+rail)/max)+'%';col.setAttribute('aria-hidden','true');b.append(col);
    const label=document.createElement('span');label.textContent=h;b.append(label);
    b.addEventListener('click',()=>select(h));chart.append(b);return b;
  });
  function select(h){
    const [bus,rail]=data[h-6],slot=pad(h)+'–'+pad(h+1);
    range.value=h;range.setAttribute('aria-valuetext',slot);
    document.querySelector('#oa-time').textContent=slot;
    document.querySelector('#oa-total').textContent=(bus+rail).toLocaleString('ja-JP');
    document.querySelector('#oa-modes').textContent='バス'+bus+' ／ JRのみ'+rail;
    buttons.forEach((b,i)=>b.setAttribute('aria-pressed',String(i+6===h)));
  }
  range.disabled=false;range.addEventListener('input',()=>select(Number(range.value)));select(16);
})();
