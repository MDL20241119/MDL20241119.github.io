import {esc,number} from './model.mjs';
import {clock,accessOptions,directionsUrl,unpackAccess} from './access-model.mjs';
let request,revision=0;
const load=()=>request??=fetch('data/access.json').then(r=>{if(!r.ok)throw Error('アクセスの時刻表を読み込めませんでした。');return r.json()}).then(unpackAccess).catch(e=>{request=null;throw e});
const options=(anchors,current)=>anchors.map(a=>`<option value="${a.id}" ${a.id===current?'selected':''}>${esc(a.area+'｜'+a.name)}</option>`).join('');
const option=(v,label,current)=>`<option value="${v}" ${v===current?'selected':''}>${label}</option>`;
const mapLink=(from,to,mode,label)=>`<a class="button" href="${esc(directionsUrl(from,to,mode))}" target="_blank" rel="noopener noreferrer">${label} ↗</a>`;
export async function renderAccess(data,state,onState){
 const renderId=++revision;
 const host=document.querySelector('#panel-access'),from=data.anchors.find(a=>a.id===state.origin),to=data.anchors.find(a=>a.id===state.anchor);
 const destinations=data.anchors.filter(a=>state.area==='all'||a.area===state.area);
 host.innerHTML=`<div class="section-head"><div><span class="eyebrow">GETTING THERE / ACCESSIBILITY</span><h2>観光地へのアクセスを調べる</h2><p>駅や空港から観光地へ。行き・滞在・帰りを、ひと続きで考えます。</p></div></div>
 <div class="example-chips"><span>例から始める</span><button data-trip-example="beppu">別府駅 → 地獄エリア</button><button data-trip-example="hiji">暘谷駅 → ハーモニーランド</button><button data-trip-example="yufu">由布院駅 → 岳本</button></div>
 <div class="panel access-form"><div class="route-selects"><label><span><b>1</b> 出発地</span><select id="access-origin">${options(data.anchors,state.origin)}</select></label><span class="route-arrow" aria-hidden="true">→</span><label><span><b>2</b> 行き先の周辺</span><select id="access-destination">${options(destinations,state.anchor)}</select></label></div>
 <p class="footnote">収録した13地点から選択。どちらも停留所の位置を基準にしています。</p>
 <div class="external-routes"><div><h3>旅行当日の経路・時刻を確認</h3><p>選んだ２地点をGoogle マップへ引き継ぎます。</p></div><div>${mapLink(from,to,'transit','公共交通の経路')}${mapLink(from,to,'driving','車の経路')}</div></div><p class="footnote">旅行日・出発時刻・施設の入口は、開いた地図で指定・確認してください。この下の分析条件は外部地図へ引き継ぎません。</p></div>
 <div class="section-head"><div><span class="eyebrow">CAN I GO, STAY AND RETURN?</span><h2>行って、過ごして、帰れる？</h2><p>アクセシビリティ＝目的地へ行き、必要な時間を過ごして帰れること。</p></div></div>
 <div class="panel"><div class="access-conditions"><label>時刻表の対象日<select id="access-day">${data.transport.dates.map((d,i)=>option(i,d,state.day)).join('')}</select></label><label>出発は何時以降？<input id="access-departure" type="time" value="${state.departure}"></label><label>何時までに帰る？<input id="access-deadline" type="time" value="${state.deadline}"></label><label>現地で過ごす時間<select id="access-dwell">${[60,120,180,240].map(v=>option(v,v/60+'時間',state.dwell)).join('')}</select></label><label>片道の乗車時間<select id="access-limit">${[30,60,90,120].map(v=>option(v,v+'分以内',state.maxMinutes)).join('')}</select></label></div>
 <p class="footnote">公開時刻表の直通バスを照合します。帰路の乗車まで「滞在時間＋20分の余裕」を置きます。徒歩の実測や施設の営業時間は含みません。</p></div>
 <div id="access-result" aria-live="polite"><div class="empty">公開時刻表を照合しています…</div></div>
 <div class="next-action"><div><strong>着いてから、どう回る？</strong><p>行き先周辺の乗り場や、次の立ち寄り先を調べられます。</p></div><button class="button primary" data-navigate="mobility">観光地でのアクセスを調べる →</button></div>`;
 const fields={'access-origin':['origin',String],'access-destination':['anchor',String],'access-day':['day',Number],'access-departure':['departure',String],'access-deadline':['deadline',String],'access-dwell':['dwell',Number],'access-limit':['maxMinutes',Number]};
 for(const [id,[key,cast]]of Object.entries(fields))document.getElementById(id).addEventListener('change',e=>{if(e.target.value)onState({[key]:cast(e.target.value)},id)});
 try{const timetable=await load();if(renderId!==revision||!host.querySelector('#access-result')||host.hidden)return;
 const target=host.querySelector('#access-result');if(from.id===to.id){target.innerHTML='<div class="notice">出発地と行き先が同じです。別の地点を選んでください。</div>';return;}
 const result=accessOptions(timetable.calls,state),feed=id=>timetable.feeds.find(f=>f.id===id);
 if(result.invalid){target.innerHTML='<div class="notice error">帰着時刻は、出発時刻より後にしてください。</div>';return;}
 const journey=c=>`<div class="journey-leg"><div class="journey-time"><b>${clock(c.departure)}</b><span aria-hidden="true">→</span><b>${clock(c.arrival)}</b><small>乗車 ${number((c.arrival-c.departure)/60)}分</small></div><p><strong>${esc(c.board.name)}</strong> → <strong>${esc(c.alight.name)}</strong></p><p class="footnote">${esc(feed(c.feedId)?.name)}｜${esc(c.route)}<br>基準点〜乗降場：直線 ${c.board.distance}m / ${c.alight.distance}m</p></div>`;
 const selected=result.pairs.slice(0,3);
 target.innerHTML=`<div class="access-outcome ${selected.length?'found':''}"><span class="outcome-icon" aria-hidden="true">${selected.length?'↔':'?'}</span><div><span class="eyebrow">${esc(data.transport.dates[state.day])} / 時刻表の候補</span><h3>${selected.length?'この条件で直通の往復候補があります':'この条件の直通往復は見つかりません'}</h3><p>${selected.length?`滞在${state.dwell/60}時間＋余裕20分、${state.deadline}までに出発側の停留所へ到着。`:'時間条件を変えるか、公共交通の経路から鉄道・乗り換えも確認してください。'}</p></div></div>
 ${selected.length?`<div class="journey-cards">${selected.map((p,i)=>`<article class="panel"><span class="tag blue">往復候補 ${i+1}</span><h4>行き</h4>${journey(p.out)}<div class="dwell-strip">現地で${state.dwell/60}時間 ＋ 移動などの余裕20分</div><h4>帰り</h4>${journey(p.back)}</article>`).join('')}</div>`:''}
 <p class="footnote">停留所間の候補です。実際の徒歩、待ち時間、営業・受付時間、予約・空席、バリアフリー対応を確認して初めて旅行の成立を判断できます。候補なしは「行けない」の判定ではありません。</p>
 <details class="panel"><summary>片道の直通便を確認する（行き${result.outbound.length}候補／帰り${result.returns.length}候補）</summary><div class="two-col"><div><h3>行き｜${esc(from.name)}発</h3>${result.outbound.slice(0,8).map(journey).join('')||'<p class="footnote">条件に合う直通候補なし</p>'}</div><div><h3>帰り｜${esc(to.name)}発</h3>${result.returns.slice(0,8).map(journey).join('')||'<p class="footnote">条件に合う直通候補なし</p>'}</div></div><p class="footnote">各８件まで。片道一覧は独立した候補です。すべての組合せで滞在時間が確保できるわけではありません。</p></details>
 <details><summary>使った交通データと計算の範囲</summary><p class="subtle">${esc(timetable.method)} 対象は2026年9月8日取得の16件。元の交通マップと同じ時刻表・停留所IDを使っています。推測で便を補っていません。鉄道・乗換・運賃はこの照合に含みません。</p><ul class="source-list">${[...new Set([...result.outbound,...result.returns].map(c=>c.feedId))].map(id=>{const f=feed(id);return `<li><a href="${esc(f.sourceUrl)}" target="_blank" rel="noopener noreferrer">${esc(f.name)}・原時刻表 ↗</a></li>`}).join('')}</ul></details>`;
 }catch(e){host.querySelector('#access-result').innerHTML='<div class="notice error">'+esc(e.message)+'</div>';}
}
