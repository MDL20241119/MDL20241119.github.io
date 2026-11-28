(() => {
  const shell=document.querySelector('.atlas-shell');
  if(!shell)return;
  const A='/oita-mobility/',T='/oita-tourism/';
  if(new URLSearchParams(location.search).get('embed')==='atlas'){
    document.documentElement.classList.add('atlas-frame');
    return;
  }
  const isHome=[A,A+'index.html'].includes(location.pathname);
  const p=location.pathname.replace(/index\.html$/,'');
  const groups={
    map:['地図',A,[
      ['行って帰れる？',A+'?view=trip'],['時間帯別に乗れる場所',A+'?view=map'],['観光地を探す',A+'?points=tourism']]],
    data:['交通を考える',A+'overview.html',[
      ['現状分析',A+'overview.html'],
      ['地域の移動の課題',A+'atlas.html?view=detail#city-form'],['増便などの効果を比べる',A+'policy.html'],['実際の乗り降り',A+'ridership.html'],['観光客の動き',T+'#overview']]],
    docs:['資料・出典',A+'tools.html#references',[
      ['データ・出典',A+'data-catalog.html'],['使い方マニュアル',A+'guide/'],['旧版アーカイブ',A+'analysis.html']]]
  };
  const link=(href,label)=>Object.assign(document.createElement('a'),{href,textContent:label});
  const dir=shell.querySelector('details'),panel=dir.querySelector('.atlas-shell__panel');
  const menu=[];
  for(const [key,[title,,items]] of Object.entries(groups)){
    const block=document.createElement('section');
    const h=document.createElement('h2');h.textContent=title;block.append(h);
    for(const [label,href] of items){const el=link(href,label);menu.push({key,href,el});block.append(el);}
    panel.append(block);
  }
  const all=link(A+'tools.html#area','全体の目次・資料');all.className='atlas-shell__all';panel.append(all);
  const validCity=c=>/^44\d{3}$/.test(c||'');
  let lastCity='';
  function cityFor(url){
    const city=url.searchParams.get('city');
    if(validCity(city)){lastCity=city;try{sessionStorage.setItem('atlas-nav-city',city);}catch{}}
    if(!lastCity)try{lastCity=sessionStorage.getItem('atlas-nav-city')||'';}catch{}
    return validCity(lastCity)?lastCity:'';
  }
  function scoped(href,city){
    const url=new URL(href,location.origin);
    if(city&&(![A+'guide/',A+'data-catalog.html',A+'analysis.html',T].includes(url.pathname)))url.searchParams.set('city',city);
    return url.pathname+url.search+url.hash;
  }
  function state(url){
    let group=shell.dataset.atlasGroup,label=shell.dataset.atlasLabel,key=shell.dataset.atlasLabelUrl,detail='';
    const hash=url.hash.slice(1);
    if(isHome){
      const view=url.searchParams.get('view'),selected=document.querySelector('.start-tabs a[aria-current]')?.id;
      const tour=view!=='trip'&&url.searchParams.get('points')==='tourism';
      const map=view==='map'||selected==='tab-map'||['atlas-time-gaps','tourism'].includes(hash);
      if(view==='trip'||['jr-check','jr-web-check','regional-transport','opportunity-section'].includes(hash)||(!tour&&!map)){
        label='行って帰れる？';key=A+'?view=trip';
        detail={ 'jr-check':'JRを含む判定','jr-web-check':'公開ダイヤでの確認例','regional-transport':'グリスロ・ふれあい交通','opportunity-section':'片道で行ける施設' }[hash]||'';
      } else if(tour){label='観光地を探す';key=A+'?points=tourism';}
      else {label='時間帯別に乗れる場所';key=A+'?view=map';}
    }
    if(p===T){
      const view=document.body.dataset.view||hash.split(/[?&]/)[0]||'overview';
      if(view==='access'||view==='mobility'){
        group='map';label='観光地を探す';key=A+'?points=tourism';detail=view==='access'?'観光地への行き方':'現地の周遊';
      }else if(view==='guide'){group='docs';label='観光マップの使い方';key=T+'catalog/';}
      else detail={compare:'地域・交通手段を比べる',issues:'観光の課題',data:'観光のデータを探す'}[view]||'';
    }
    if(p===A+'tools.html'){
      if(hash==='references'){group='docs';label='資料一覧';}
      if(hash==='trip'){group='map';label='地図の使い方';}
    }
    if(p===A+'atlas.html')detail=hash==='demand'?'実現しなかった移動':hash==='resources'?'地域の送迎・資源':'';
    if(p===A+'lab.html')detail=shell.dataset.atlasSection||'';
    if(p===A+'analysis.html')detail={map:'地図',ridership:'乗降',od:'出発地・到着地',forecast:'需要予測',cost:'費用',bc:'費用と効果',sources:'出典'}[hash]||'';
    return {group,label,key,detail};
  }
  function update(){
    const url=new URL(location.href),city=cityFor(url),s=state(url);
    shell.dataset.atlasActive=s.group;
    for(const tab of shell.querySelectorAll('[data-atlas-tab]')){
      tab.toggleAttribute('aria-current',tab.dataset.atlasTab===s.group);
      if(tab.hasAttribute('aria-current'))tab.setAttribute('aria-current','true');
      tab.href=scoped(groups[tab.dataset.atlasTab][1],city);
    }
    for(const m of menu){m.el.href=scoped(m.href,city);
      if(m.href===s.key&&m.key===s.group)m.el.setAttribute('aria-current','location');else m.el.removeAttribute('aria-current');
    }
    for(const tab of document.querySelectorAll('.oa-analytical-tabs a'))tab.href=scoped(tab.href,city);
    if(p===A+'tools.html')for(const card of document.querySelectorAll('.start-tool-grid a')){
      const target=new URL(card.href,url);
      if(target.origin===url.origin&&target.pathname.startsWith(A))card.href=scoped(target.href,city);
    }
    shell.querySelector('.atlas-shell__brand').href=scoped(A,city);
    const crumb=shell.querySelector('.atlas-shell__crumb');
    crumb.firstElementChild.href=scoped(A,city);
    const parent=crumb.querySelector('[data-atlas-parent]');
    parent.textContent=groups[s.group][0];parent.href=scoped(groups[s.group][1],city);
    const current=crumb.querySelector('[data-atlas-current]');
    current.textContent=s.detail?s.label+' / '+s.detail:s.label;current.title=current.textContent;
  }
  window.addEventListener('hashchange',update);
  window.addEventListener('popstate',update);
  document.addEventListener('atlas:navigation',update);
  if(p===T)new MutationObserver(update).observe(document.body,{attributes:true,attributeFilter:['data-view']});
  if(p===A+'lab.html'){
    const tabs=document.getElementById('lab-nav');
    if(tabs)new MutationObserver(()=>{
      const active=tabs.querySelector('[aria-current],[aria-selected="true"]');
      shell.dataset.atlasSection=active?.textContent.trim()||'';update();
    }).observe(tabs,{subtree:true,attributes:true,attributeFilter:['aria-current','aria-selected'],childList:true});
  }
  document.addEventListener('click',e=>{if(dir.open&&!dir.contains(e.target))dir.open=false;});
  panel.addEventListener('click',e=>{if(e.target.closest('a'))dir.open=false;});
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&dir.open){dir.open=false;dir.querySelector('summary').focus();}});
  update();
})();
