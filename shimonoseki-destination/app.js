"use strict";
const courses={
 strait:{title:"市場の活気と、海峡を渡る時間。",places:["station","karato","mojiko"],stops:[["駅前","車と荷物を預け、旅を始める"],["唐戸市場","市場を楽しみ、港を歩く"],["門司港","関門連絡船で、海峡の向こうへ"],["駅前へ","下関の食とお土産で締めくくる"]]},
 family:{title:"親子で、海の世界とおいしい発見。",places:["station","aquarium","karato"],stops:[["駅前","必要な荷物を整え、バスへ"],["海響館","海の生きものとの出会いを楽しむ"],["唐戸周辺","休憩しながら、水辺を散歩"],["駅前へ","家族で食事。買い物も一度に"]]},
 history:{title:"新幹線の入口から、城下町と海峡の街へ。",stops:[["新下関駅","新幹線から、市内の旅へ"],["城下町長府","武家屋敷や土塀の町並みを歩く"],["赤間神宮・唐戸","歴史と、港の風景に出会う"],["下関駅前","夜の食と文化を楽しみ、関門の宿へ"]]},
 evening:{title:"関門を楽しみ、もう一泊したくなる夜へ。",places:["station","karato","mojiko"],stops:[["関門の港へ","夕景を楽しみ、夜の帰路を確認"],["下関駅前","地元の食と文化を楽しむ夜の構想"],["関門の宿へ","下関・門司港・小倉の宿泊施設との連携案"],["翌朝も街へ","朝食・街歩き・買い物で、もう一つの発見"]]}
};
const tabs=Array.from(document.querySelectorAll('.route-tabs [role="tab"]'));
const panel=document.getElementById('route-panel');
function selectCourse(tab,focus=false){
 const course=courses[tab.dataset.course];if(!course)return;
 tabs.forEach(t=>{const selected=t===tab;t.setAttribute('aria-selected',String(selected));t.tabIndex=selected?0:-1;});
 document.getElementById('route-name').textContent=course.title;
 document.getElementById('route-stops').replaceChildren(...course.stops.map(([name,description])=>{const li=document.createElement('li');const b=document.createElement('b');const span=document.createElement('span');b.textContent=name;span.textContent=description;li.append(b,span);return li;}));
 panel.setAttribute('aria-labelledby',tab.id);
 if(focus)tab.focus();
}
tabs.forEach((tab,index)=>{tab.addEventListener('click',()=>selectCourse(tab));tab.addEventListener('keydown',event=>{let target;if(event.key==='ArrowRight')target=(index+1)%tabs.length;else if(event.key==='ArrowLeft')target=(index-1+tabs.length)%tabs.length;else if(event.key==='Home')target=0;else if(event.key==='End')target=tabs.length-1;else return;event.preventDefault();selectCourse(tabs[target],true);});});
if(tabs.length)selectCourse(tabs[0]);

// Independent map tabs. With JavaScript disabled, all maps remain readable.
const mapTabs=Array.from(document.querySelectorAll('.atlas-tabs [role="tab"]'));
function selectMap(tab,focus=false,updateHash=false){
 if(!tab)return;
 mapTabs.forEach(t=>{
  const selected=t===tab;
  t.setAttribute('aria-selected',String(selected));
  t.tabIndex=selected?0:-1;
  document.getElementById(t.getAttribute('aria-controls')).hidden=!selected;
 });
 if(updateHash)history.replaceState(null,'','#'+tab.getAttribute('aria-controls'));
 if(focus)tab.focus();
}
mapTabs.forEach((tab,index)=>{
 tab.addEventListener('click',()=>selectMap(tab,false,true));
 tab.addEventListener('keydown',event=>{
  let target;
  if(event.key==='ArrowRight')target=(index+1)%mapTabs.length;
  else if(event.key==='ArrowLeft')target=(index-1+mapTabs.length)%mapTabs.length;
  else if(event.key==='Home')target=0;
  else if(event.key==='End')target=mapTabs.length-1;
  else return;
  event.preventDefault();selectMap(mapTabs[target],true,true);
 });
});
document.querySelectorAll('[data-map-link]').forEach(link=>link.addEventListener('click',()=>{
 selectMap(mapTabs.find(t=>t.dataset.map===link.dataset.mapLink));
}));
function mapFromHash(){return mapTabs.find(t=>'#'+t.getAttribute('aria-controls')===location.hash);}
if(mapTabs.length)selectMap(mapFromHash()||mapTabs[0]);
window.addEventListener('hashchange',()=>{const tab=mapFromHash();if(tab)selectMap(tab);});
