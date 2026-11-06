(()=>{'use strict';
  const header=document.querySelector('.atlas-topbar');if(!header)return;
  const researchHref='/co-creation-atlas/research/';
  header.querySelectorAll('.atlas-nav-links').forEach(menu=>{
    if(menu.querySelector('a[href="/co-creation-atlas/learn/workbook/"]')&&!menu.querySelector('a[href="'+researchHref+'"]')){
      const link=document.createElement('a');link.href=researchHref;
      link.innerHTML='<strong>共創とイノベーションの研究</strong><span>動く力を掛け合わせる7つの論点</span>';
      menu.prepend(link);
    }
  });
  const entrance=document.querySelector('.step-home');
  if(entrance&&!document.getElementById('co-creation-research-feature')){
    const card=document.createElement('aside');card.className='frontier-entry';card.id='co-creation-research-feature';
    card.innerHTML='<div><p class="eyebrow">CO-CREATION × RESEARCH</p><h2>共創は、動く力のかけざん。</h2><p>対等・行動・挑戦・多様性。実践思想を世界の研究と照らし合わせる。</p></div><a href="'+researchHref+'">7つの論点と論文を読む ↗</a>';
    const grid=entrance.querySelector('.step-home-grid');entrance.insertBefore(card,grid);
  }
  const mobile=header.querySelector('.atlas-mobile-menu');
  const groups=[...header.querySelectorAll('.atlas-nav-group')];
  const mobileToggle=mobile.querySelector('summary');
  const closeGroups=()=>groups.forEach(group=>group.open=false);
  function closeAll(){closeGroups();mobile.open=false;}
  for(const group of groups){group.addEventListener('toggle',()=>{
    if(!group.open)return;
    groups.filter(other=>other!==group&&other.parentElement===group.parentElement).forEach(other=>other.open=false);
  });}
  header.querySelectorAll('a').forEach(link=>link.addEventListener('click',closeAll));
  document.addEventListener('click',event=>{if(!header.contains(event.target))closeAll();});
  document.addEventListener('keydown',event=>{
    if(event.key!=='Escape')return;
    if(mobile.open){closeAll();mobileToggle.focus();event.preventDefault();return;}
    const open=header.querySelector('.atlas-nav-group[open]');
    if(open){open.open=false;open.querySelector('summary').focus();event.preventDefault();}
  });
  window.addEventListener('pageshow',closeAll);
  window.addEventListener('popstate',closeAll);
  window.addEventListener('hashchange',closeAll);
  matchMedia('(max-width:1180px)').addEventListener('change',closeAll);
  // Match exact route and its filters; do not mark every link to the hub current.
  for(const link of header.querySelectorAll('.atlas-nav-links a')){
    const url=new URL(link.href,location.href);
    if(url.pathname===location.pathname&&url.search===location.search&&url.hash===location.hash)link.setAttribute('aria-current','page');
  }
})();
