const q=new URLSearchParams(location.search);
const frame=document.querySelector('#start-map-frame');
const mapView=document.querySelector('.start-map');
const tripView=document.querySelector('#trip-view');
let city=/^44\d{3}$/.test(q.get('city')||'')?q.get('city'):'44201';
function refresh(code){
  city=code;
  const cityLabel=document.querySelector("#start-city");
  const name=frame.contentDocument?.querySelector("#municipality option:checked")?.textContent || document.querySelector("#area-city option:checked")?.textContent;
  if(name && !name.includes("…"))cityLabel.textContent=name;
  else if(code!=="44201")cityLabel.textContent="選んだ地域";
  else cityLabel.textContent="大分市";
  document.querySelector('#tab-trip').href='journey.html?city='+city;
  document.querySelector('#tab-map').href='index.html?city='+city;
  for(const a of document.querySelectorAll('[data-city-link]')){
    const url=new URL(a.href);url.searchParams.set('city',city);a.href=url.href;
  }
}
refresh(city);
if(location.hash==='#atlas-toc')document.querySelector('#atlas-toc').open=true;
{
  if(location.hash==='#opportunity-section')document.querySelector('.trip-extras').open=true;
  mapView.hidden=true;
  frame.remove();
  tripView.hidden=false;
  document.querySelector('#tab-map').removeAttribute('aria-current');
  document.querySelector('#tab-trip').setAttribute('aria-current','page');
  document.addEventListener('atlas:start-city',e=>refresh(e.detail.code));
  import('./people.mjs?v=jr1').catch(()=>{
    const box=document.querySelector('#error');box.hidden=false;box.textContent='検索を読み込めませんでした。再読み込みしてください。';
  });
}
