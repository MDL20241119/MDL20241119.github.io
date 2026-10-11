(()=>{'use strict';
  const header=document.querySelector('.atlas-topbar');if(!header)return;
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
