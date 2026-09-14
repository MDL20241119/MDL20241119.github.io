import {esc,csvText} from './model.mjs';
import {distance} from '../lab/gtfs.mjs';
const $=s=>document.querySelector(s),PAGE=30;
let data,rows=[],page=0;
const params=new URLSearchParams(location.search);
const num=k=>params.has(k)&&params.get(k).trim()!==''?Number(params.get(k)):NaN;
const origin=Number.isFinite(num('lat'))&&Number.isFinite(num('lon'))&&num('lat')>=32&&num('lat')<=35&&num('lon')>=129&&num('lon')<=133?{lat:num('lat'),lon:num('lon')}:null;
const link=(u,text)=>u?`<a href="${esc(u)}" target="_blank" rel="noopener noreferrer">${esc(text)} ↗</a>`:'';
const groupName=id=>data.groups.find(g=>g.id===id)?.name??id;
function filtered(){
  const q=$('#tt-query').value.normalize('NFKC').toLowerCase().trim(),group=$('#tt-group').value;
  return data.entries.filter(e=>(group==='all'||group===e.group)&&(!q||[e.name,e.reading,e.line,e.city,groupName(e.group)].join(' ').normalize('NFKC').toLowerCase().includes(q)))
    .map(e=>({...e,meters:origin&&Number.isFinite(e.lat)&&Number.isFinite(e.lon)?distance(origin,e):null}))
    .sort((a,b)=>origin?(a.meters??Infinity)-(b.meters??Infinity):0);
}
function urlState(){const url=new URL(location.href);url.searchParams.delete('group');url.searchParams.delete('q');if($('#tt-group').value!=='all')url.searchParams.set('group',$('#tt-group').value);if($('#tt-query').value.trim())url.searchParams.set('q',$('#tt-query').value.trim());history.replaceState(null,'',url);}
function render(){
  rows=filtered();page=Math.max(0,Math.min(page,Math.ceil(rows.length/PAGE)-1));urlState();
  $('#tt-count').textContent=`${rows.length.toLocaleString('ja-JP')}件${origin?'。選択区域の代表点から近い順（直線距離）。':''}`;
  $('#tt-body').innerHTML=rows.slice(page*PAGE,(page+1)*PAGE).map(e=>`<tr><td><strong>${esc(e.name)}</strong><small>${esc(groupName(e.group))}</small>${e.meters!==null?`<small>代表点から約${Math.round(e.meters).toLocaleString('ja-JP')}m（直線）</small>`:''}</td><td>${esc(e.line)}<small>${esc(e.city)}</small>${e.positionDate?`<small>位置：${esc(e.positionDate)}</small>`:''}</td><td>${link(e.url,e.kind)}${e.pdfUrl?`<br>${link(e.pdfUrl,'駅の時刻表PDF')}`:''}${e.downloadUrl?`<br><a href="${esc(e.downloadUrl)}" download>時刻表データ ZIP</a>`:''}<small>${e.analysisReady?'計算に収録（収録路線・有効日の範囲）':'公式参照用。計算用の全便データは未接続。'}</small></td></tr>`).join('')||'<tr><td colspan="3">この条件の案内はありません。事業者・公式検索から確認してください。</td></tr>';
  $('#tt-page').textContent=`${rows.length?page+1:0} / ${Math.ceil(rows.length/PAGE)}ページ`;$('#tt-prev').disabled=page===0;$('#tt-next').disabled=(page+1)*PAGE>=rows.length;
  const g=$('#tt-group').value;$('#tt-documents').innerHTML=data.documents.filter(d=>g==='all'||g===d.group).map(d=>`<a class="tt-document" href="${esc(d.url)}" target="_blank" rel="noopener noreferrer"><strong>${esc(d.label)}</strong><span>公式時刻表 PDF ↗${d.revision?' ／ '+esc(d.revision)+'改正':''}</span></a>`).join('');
}
async function start(){
  const r=await fetch('data/official-timetables.json?v=20260915-1');if(!r.ok)throw Error('時刻表案内を読み込めません');data=await r.json();
  $('#tt-group').innerHTML='<option value="all">すべての事業者・公表主体</option>'+data.groups.map(g=>`<option value="${esc(g.id)}">${esc(g.name)}</option>`).join('');
  if(data.groups.some(g=>g.id===params.get('group')))$('#tt-group').value=params.get('group');$('#tt-query').value=params.get('q')??'';
  $('#tt-priority').innerHTML=data.groups.slice(0,4).map((g,i)=>`<article class="tt-card"><span class="operator-kicker">0${i+1} / ${g.mode==='rail'?'TRAIN':'BUS'}</span><h2>${esc(g.name)}</h2><p>${esc(g.description)}</p><div class="tt-card-actions"><button type="button" data-group="${esc(g.id)}">駅・停留所から探す ↓</button>${link(g.timetableUrl,'公式時刻表')}${link(g.mapUrl,'路線案内')}</div><small>${esc(g.analysis)}</small></article>`).join('');
  $('#tt-priority').addEventListener('click',e=>{const b=e.target.closest('[data-group]');if(!b)return;$('#tt-group').value=b.dataset.group;$('#tt-query').value='';page=0;render();$('#tt-directory').scrollIntoView({block:'start'});$('#tt-query').focus({preventScroll:true});});
  for(const id of ['tt-group','tt-query'])$('#'+id).addEventListener(id==='tt-query'?'input':'change',()=>{page=0;render()});
  $('#tt-prev').addEventListener('click',()=>{page--;render()});$('#tt-next').addEventListener('click',()=>{page++;render()});
  $('#tt-reset').addEventListener('click',()=>{$('#tt-group').value='all';$('#tt-query').value='';page=0;render()});
  $('#tt-export').addEventListener('click',()=>{const text=csvText([['事業者','駅・停留所・資料','路線・方面','地域','公式時刻表URL','PDF','位置基準日','確認日','計算収録'],...rows.map(e=>[groupName(e.group),e.name,e.line,e.city,e.url,e.pdfUrl??'',e.positionDate??'',e.checkedAt,e.analysisReady?'収録分・有効日のみ':'公式参照用・全便計算未接続'])]);const u=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=u;a.download='fukuoka-official-timetables.csv';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);});
  if(origin){$('#tt-nearby').hidden=false;$('#tt-nearby').textContent='交通空白マップで選んだ区域周辺の時刻表を表示しています。距離は直線で、徒歩で行ける距離ではありません。';}
  render();$('#tt-loading').hidden=true;document.documentElement.dataset.timetableReady='true';
}
start().catch(e=>{$('#tt-loading').textContent=e.message+'。上の公式リンクからも確認できます。';$('#tt-loading').setAttribute('role','alert');});
