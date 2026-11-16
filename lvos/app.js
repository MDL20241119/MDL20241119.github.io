(()=>{
const cases=[...document.querySelectorAll('.case')];
const picks=[...document.querySelectorAll('.casepick')];
let all=false,timer=null;
function stop(){clearInterval(timer);timer=null;document.querySelectorAll('.play').forEach(b=>{b.textContent='▶ 流れを再生';b.setAttribute('aria-pressed','false')})}
function choose(id,move=false){stop();if(!cases.some(c=>c.id===id))id=cases[0].id;
 cases.forEach(c=>{c.hidden=!all&&c.id!==id});picks.forEach(a=>{a.classList.toggle('selected',a.hash==='#'+id);a.setAttribute('aria-current',a.hash==='#'+id?'true':'false')});
 if(move){history.replaceState(null,'','#'+id);document.getElementById(id).scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'})}
}
const toolbar=document.createElement('div');toolbar.className='explorer-tools';toolbar.innerHTML='<p>事例をタップして切替。図の各ステップも押せます。</p><button class="show-all" type="button" aria-pressed="false">5事例をすべて表示</button>';document.querySelector('.case-menu').after(toolbar);
toolbar.querySelector('button').onclick=e=>{all=!all;e.target.setAttribute('aria-pressed',String(all));e.target.textContent=all?'1事例ずつ見る':'5事例をすべて表示';choose(picks.find(a=>a.classList.contains('selected'))?.hash.slice(1)||cases[0].id)};
picks.forEach(a=>a.addEventListener('click',e=>{e.preventDefault();all=false;toolbar.querySelector('button').textContent='5事例をすべて表示';toolbar.querySelector('button').setAttribute('aria-pressed','false');choose(a.hash.slice(1),true)}));
cases.forEach(c=>{const flow=c.querySelector('.flow');const steps=[...flow.children];const controls=document.createElement('div');controls.className='flow-controls';controls.innerHTML='<button type="button" class="play" aria-pressed="false">▶ 流れを再生</button><span class="flow-status" aria-live="polite">ステップを選ぶと、その段階が強調されます。</span>';flow.before(controls);
 function activate(i){steps.forEach((s,j)=>{s.classList.toggle('active',j===i);s.querySelector('button').setAttribute('aria-pressed',String(j===i))});controls.querySelector('.flow-status').textContent=`${i+1} / ${steps.length}　${steps[i].querySelector('h4').textContent}`;c.dataset.step=i}
 steps.forEach((s,i)=>{const b=document.createElement('button');b.type='button';b.className='flow-step';b.setAttribute('aria-pressed','false');while(s.firstChild)b.append(s.firstChild);s.append(b);b.addEventListener('click',()=>{stop();activate(i)})});
 controls.querySelector('.play').onclick=e=>{if(timer){stop();return}activate(0);e.target.textContent='Ⅱ 停止';e.target.setAttribute('aria-pressed','true');timer=setInterval(()=>{let next=Number(c.dataset.step)+1;if(next>=steps.length){stop();return}activate(next)},2000)};
});
window.addEventListener('hashchange',()=>{if(cases.some(c=>'#'+c.id===location.hash)){all=false;choose(location.hash.slice(1))}});
choose(location.hash.slice(1));
})();
