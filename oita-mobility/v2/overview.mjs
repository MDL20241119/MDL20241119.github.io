const q = new URLSearchParams(location.search);
const city = /^44\d{3}$/.test(q.get('city') ?? '') ? q.get('city') : '44201';
const mapURL = code => 'atlas.html?city='+encodeURIComponent(code)+'#atlas-time-gaps';
if(document.documentElement.classList.contains('atlas-detail-mode')){
  document.querySelector('#detail-back').href=mapURL(city);
  import('./atlas.mjs?v=two-gaps1');
}else{
  const frame=document.querySelector('#overview-frame');
  const setLinks=code=>{
    document.querySelector('#overview-detail').href='atlas.html?view=detail&city='+encodeURIComponent(code);
    document.querySelector('#overview-criteria').href='transport-gaps.html?city='+encodeURIComponent(code);
  };
  let observer;
  frame.addEventListener('load',()=>{
    observer?.disconnect();
    const doc=frame.contentDocument;
    if(!doc?.querySelector('#main'))return;
    const resize=()=>{
      const target=doc.querySelector('#main');
      const style=doc.defaultView.getComputedStyle(target);
      const height=Math.ceil(target.getBoundingClientRect().bottom+Number.parseFloat(style.marginBottom||0)+4);
      if(height>0 && frame.height!==String(height))frame.height=height;
    };
    observer=new ResizeObserver(resize);
    observer.observe(doc.querySelector('#main'));
    doc.addEventListener('atlas:city',e=>setLinks(e.detail.code));
    resize();
  });
  setLinks(city);
  frame.src='transport-gaps.html?embed=atlas&city='+encodeURIComponent(city);
}
