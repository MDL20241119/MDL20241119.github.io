(()=>{'use strict';
 const query=new URLSearchParams(location.search);
 const reading=document.querySelector('[data-case-lenses]');
 if(reading){
  const lenses=reading.dataset.caseLenses.split(' ');
  const show=lens=>{
   if(!lenses.includes(lens))lens=lenses[0];
   reading.querySelectorAll('[data-reading-lens]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.readingLens===lens)));
   reading.querySelectorAll('[data-reading-panel]').forEach(p=>p.hidden=p.dataset.readingPanel!==lens);
   document.querySelectorAll('[data-return-cases]').forEach(a=>a.href='../../?lens='+lens+'#explore');
   return lens;
  };
  show(query.get('lens'));
  reading.querySelectorAll('[data-reading-lens]').forEach(b=>b.addEventListener('click',()=>{const lens=show(b.dataset.readingLens),p=new URLSearchParams(location.search);p.set('lens',lens);history.replaceState(null,'',location.pathname+'?'+p+location.hash);}));
 }
 const compare=document.querySelector('[data-atlas-compare]');
 if(compare){
  const cards=[...compare.querySelectorAll('[data-compare-id]')];
  const search=document.querySelector('#compare-search'),unit=document.querySelector('#compare-unit'),only=document.querySelector('#compare-selected-only');
  const validLenses=['co','place','cross'];let lens=validLenses.includes(query.get('lens'))?query.get('lens'):'cross';
  const known=new Set(cards.map(c=>c.dataset.compareId));const selected=new Set((query.get('selected')||'').split(',').filter(id=>known.has(id)));
  search.value=query.get('q')||'';unit.value=query.get('unit')||'';only.checked=query.get('only')==='1';
  const norm=s=>String(s||'').normalize('NFKC').toLowerCase();
  const texts=new Map(cards.map(c=>[c.dataset.compareId,norm(c.dataset.search)]));
  cards.forEach(c=>{const box=c.querySelector('[data-compare-select]');box.checked=selected.has(c.dataset.compareId);box.addEventListener('change',()=>{if(box.checked)selected.add(c.dataset.compareId);else selected.delete(c.dataset.compareId);render();});});
  function render(){
   const terms=norm(search.value).trim().split(/\s+/).filter(Boolean);let count=0;
   cards.forEach(c=>{const visible=(lens==='cross'||c.dataset.lenses.split(' ').includes(lens))&&(!unit.value||c.dataset.unit===unit.value)&&(!only.checked||selected.has(c.dataset.compareId))&&terms.every(t=>texts.get(c.dataset.compareId).includes(t));c.hidden=!visible;if(visible)count++;c.querySelectorAll('[data-compare-fields]').forEach(f=>f.hidden=f.dataset.compareFields!==lens);c.querySelectorAll('[data-compare-case]').forEach(a=>{const u=new URL(a.href);if(lens!=='cross')u.searchParams.set('lens',lens);else u.searchParams.delete('lens');a.href=u.pathname+u.search+u.hash;});});
   compare.querySelectorAll('[data-compare-lens]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.compareLens===lens)));
   document.querySelector('#compare-count').textContent=count+'件を表示 / '+selected.size+'件を選択';document.querySelector('#compare-empty').hidden=count>0;
   document.querySelector('[data-compare-return]').href='../../'+(lens==='cross'?'':'?lens='+lens)+'#explore';
   const p=new URLSearchParams({lens});if(search.value.trim())p.set('q',search.value.trim());if(unit.value)p.set('unit',unit.value);if(selected.size)p.set('selected',[...selected].join(','));if(only.checked)p.set('only','1');history.replaceState(null,'',location.pathname+'?'+p+location.hash);
  }
  compare.querySelectorAll('[data-compare-lens]').forEach(b=>b.addEventListener('click',()=>{lens=b.dataset.compareLens;render();}));
  search.addEventListener('input',render);unit.addEventListener('change',render);only.addEventListener('change',render);
  document.querySelector('#compare-reset').addEventListener('click',()=>{search.value='';unit.value='';only.checked=false;selected.clear();cards.forEach(c=>c.querySelector('[data-compare-select]').checked=false);render();});
  render();
 }
})();
