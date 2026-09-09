// Navigation helpers only: calculations, data and saved conditions remain in their existing modules.
const reduced=()=>matchMedia('(prefers-reduced-motion: reduce)').matches;
const jump=(selector,focus=false)=>{const node=document.querySelector(selector);if(!node)return;node.scrollIntoView({block:'start',behavior:reduced()?'auto':'smooth'});if(focus){if(!node.hasAttribute('tabindex')&&!node.matches('button,input,select,a'))node.setAttribute('tabindex','-1');node.focus({preventScroll:true});}};
const ready=()=>document.querySelectorAll('[data-ui-jump]').forEach(button=>button.disabled=false);
if(document.documentElement.dataset.atlasReady==='true')ready();
document.addEventListener('atlas:ready',ready);
document.addEventListener('click',event=>{
  const button=event.target.closest('[data-ui-jump]');if(!button)return;
  const tab=button.dataset.uiTab;if(tab)document.querySelector(`.side-tabs [data-tab="${tab}"],.panel-tabs [data-tab="${tab}"]`)?.click();
  jump(button.dataset.uiJump,true);
});
