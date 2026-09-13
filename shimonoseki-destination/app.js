"use strict";
const courses={
 strait:{title:"市場の活気と、海峡を渡る時間。",places:["station","karato","mojiko"],stops:[["駅前","車と荷物を預け、旅を始める"],["唐戸市場","市場を楽しみ、港を歩く"],["門司港","関門連絡船で、海峡の向こうへ"],["駅前へ","港で見つけた食を、ライブ食堂でもう一度"]]},
 family:{title:"親子で、海に出会い、船乗りになる。",places:["station","aquarium","karato"],stops:[["駅前","必要な荷物を整え、バスへ"],["海響館","海の生きものとの出会いを楽しむ"],["唐戸周辺","休憩しながら、水辺を散歩"],["駅前へ","海峡の航海ゲームに挑戦し、家族で食事"]]},
 history:{title:"長府で見つけた問いを、夜の劇場へ。",stops:[["新下関駅","新幹線から、城下町長府へ"],["城下町長府","忌宮神社・功山寺など、その日の章の舞台へ"],["下関駅前","港の食卓を囲み、物語の手紙を受け取る"],["ものがたり劇場","昼の発見を手がかりに参加し、予約した宿へ"]]},
 evening:{title:"小倉から海峡へ。物語を楽しみ、関門に泊まる。",places:["station","karato","mojiko"],stops:[["小倉・門司港","城下町や港を楽しみ、夜の帰路を確認"],["下関駅前","ライブ食堂で食べ、参加型の劇場を楽しむ"],["関門の宿へ","予約した下関・門司港・小倉の宿へ戻る連携案"],["翌朝も街へ","物語で気になった場所へ、もう一度"]]}
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
function mapFromHash(){
 const target=document.getElementById(location.hash.slice(1));
 const parentPanel=target&&target.closest('.atlas-panel');
 return parentPanel&&mapTabs.find(t=>t.getAttribute('aria-controls')===parentPanel.id);
}
if(mapTabs.length)selectMap(mapFromHash()||mapTabs[0]);
window.addEventListener('hashchange',()=>{const tab=mapFromHash();if(tab)selectMap(tab);});

// A floor or source link also reveals its containing map and disclosures.
function revealLinkedContent(hash=location.hash){
 const target=document.getElementById(hash.slice(1));
 if(!target)return;
 const parentPanel=target.closest('.atlas-panel');
 if(parentPanel)selectMap(mapTabs.find(t=>t.getAttribute('aria-controls')===parentPanel.id));
 for(let node=target;node;node=node.parentElement){if(node.tagName==='DETAILS')node.open=true;}
}
revealLinkedContent();
window.addEventListener('hashchange',()=>revealLinkedContent());
document.querySelectorAll('a[href^="#"]').forEach(link=>link.addEventListener('click',()=>revealLinkedContent(link.getAttribute('href'))));
