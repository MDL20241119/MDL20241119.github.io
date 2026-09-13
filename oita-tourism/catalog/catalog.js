const dialog=document.querySelector('#screen-dialog');
const picture=document.querySelector('#dialog-image');
let trigger=null;
document.querySelectorAll('[data-photo]').forEach(button=>button.addEventListener('click',()=>{
  trigger=button;
  picture.src=button.dataset.photo;
  picture.alt=button.dataset.caption+'の拡大画面';
  document.querySelector('#screen-caption').textContent=button.dataset.caption;
  document.querySelector('#dialog-feature').href=button.dataset.url;
  dialog.showModal();
  document.querySelector('.image-scroll').scrollLeft=0;
  document.querySelector('.image-scroll').scrollTop=0;
}));
document.querySelector('#close-dialog').addEventListener('click',()=>dialog.close());
dialog.addEventListener('close',()=>trigger?.focus({preventScroll:true}));
