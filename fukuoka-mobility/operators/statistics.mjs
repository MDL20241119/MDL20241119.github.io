import {esc,fmt,csvText} from './model.mjs';
import {OBSERVATION_STATUS,observation,stationRows,coverage,operatingMargin} from './statistics-model.mjs';
const $=s=>document.querySelector(s);
let stations,finance,selected=[],visible=[],accounts=[],page=0,onChange=()=>{};
const SIZE=15;
const money=v=>Number.isFinite(v)?v.toLocaleString('ja-JP',{maximumFractionDigits:3}):'未反映';
const sourceLink=(url,title)=>`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(title)} ↗</a>`;
function download(name,rows){const url=URL.createObjectURL(new Blob([csvText(rows)],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function change(s){const prev=observation(s,s.current.year-1);return s.current.value!==null&&prev.value>0&&(s.current.note??'')===(prev.note??'')?s.current.value/prev.value*100-100:null;}
function render(){
  if(!stations)return;
  const year=Number($('#stats-year').value),ids=selected.map(r=>r.id);
  visible=stationRows(stations,ids,year,$('#station-query').value.trim());
  const c=coverage(visible);page=Math.min(page,Math.max(0,Math.ceil(visible.length/SIZE)-1));
  $('#station-coverage').textContent=`${year}年度：駅・路線レコード ${fmt(c.records)}件／公表値 ${fmt(c.available)}件／データなし・非公表 ${fmt(c.missing)}件／他線計上・駅なし ${fmt(c.other)}件。`;
  $('#station-table-body').innerHTML=visible.slice(page*SIZE,(page+1)*SIZE).map(s=>{const delta=change(s);return `<tr><td><button data-station="${s.id}">${esc(s.name)}</button><small>${esc(s.operator)}／${esc(s.line)}</small></td><td>${s.current.value===null?'—':fmt(s.current.value)}</td><td>${esc(OBSERVATION_STATUS[s.current.status])}<small>${esc(s.current.note)}</small></td><td>${delta===null?'算出対象外':(delta>0?'+':'')+delta.toFixed(1)+'%'}</td></tr>`}).join('')||'<tr><td colspan="4">選択した事業者・駅名で収録された駅別実績はありません。バス停別の実績は未収録です。</td></tr>';
  $('#station-prev').disabled=page===0;$('#station-next').disabled=(page+1)*SIZE>=visible.length;
  $('#station-page').textContent=`${visible.length?page+1:0} / ${Math.ceil(visible.length/SIZE)}ページ`;
  accounts=finance.accounts.filter(a=>a.operatorIds.some(id=>ids.includes(id))).sort((a,b)=>b.year-a.year||a.name.localeCompare(b.name,'ja'));
  $('#finance-count').textContent=`選択した主体に関連する ${accounts.length}件の年度・事業区分。各社単体とグループの値を含みます。`;
  $('#finance-table-body').innerHTML=accounts.map(a=>`<tr><td><strong>${esc(a.name)}</strong><small>${esc(a.scope)}</small><small>${sourceLink(a.sourceUrl,a.sourceTitle)} ${esc(a.sourcePage)}</small></td><td>${a.year}年度</td><td>${a.passengersValue===null?'未反映':fmt(a.passengersValue)}<small>${esc(a.passengersUnit)}</small></td><td>${money(a.revenueMillionYen)}</td><td>${money(a.expensesMillionYen)}<small>${esc(a.expensesMethod)}</small></td><td>${money(a.profitMillionYen)}<small>営業利益率 ${operatingMargin(a)===null?'算出不可':operatingMargin(a).toFixed(1)+'%'}</small></td></tr>`).join('')||'<tr><td colspan="6">選択した事業者の収支・年間実績は未反映です。</td></tr>';
  $('#station-history').hidden=true;
  onChange();
}
export function renderStatistics(rows){selected=rows;page=0;render();}
export async function setupStatistics(options){
  onChange=options.onChange??(()=>{});
  try {
    [stations,finance]=await Promise.all(['data/station-ridership.json','data/operator-finance.json'].map(options.json));
    if(stations.schemaVersion!==1||finance.schemaVersion!==1)throw Error('統計データの形式が一致しません');
    $('#stats-year').innerHTML=stations.years.toReversed().map(y=>`<option value="${y}">${y}年度</option>`).join('');
    const params=new URLSearchParams(location.search);if(stations.years.includes(Number(params.get('year'))))$('#stats-year').value=params.get('year');$('#station-query').value=params.get('station')??'';
    $('#statistics-loading').hidden=true;
    $('#statistics-controls').hidden=false;
    $('#station-source').innerHTML=sourceLink(stations.source.url,stations.source.name)+' ／ '+esc(stations.source.license)+'<br>'+stations.notes.map(esc).join('<br>');
    $('#finance-notes').innerHTML=finance.notes.map(n=>`<li>${esc(n)}</li>`).join('');
    for(const id of ['stats-year','station-query'])$('#'+id).addEventListener(id==='station-query'?'input':'change',()=>{page=0;render()});
    $('#station-prev').addEventListener('click',()=>{page--;render()});$('#station-next').addEventListener('click',()=>{page++;render()});
    $('#station-table-body').addEventListener('click',event=>{
      const id=event.target.closest('[data-station]')?.dataset.station,s=stations.stations.find(s=>s.id===id);if(!s)return;
      $('#station-history').hidden=false;
      $('#station-history').innerHTML=`<h3>${esc(s.name)}／${esc(s.line)}の推移</h3><p>${esc(s.operator)}。駅名は原典の現行表記。各年度の計上条件・注記を確認してください。</p><div class="op-table-wrap"><table class="op-table"><thead><tr><th>年度</th><th>乗降客数（人／日）</th><th>状態・原典注記</th></tr></thead><tbody>${s.observations.map(o=>`<tr><td>${o.year}</td><td>${o.value===null?'—':fmt(o.value)}</td><td>${OBSERVATION_STATUS[o.status]} ${esc(o.note)}</td></tr>`).join('')}</tbody></table></div>`;
      $('#station-history').scrollIntoView({block:'nearest'});
    });
    $('#station-export').addEventListener('click',()=>download('fukuoka-station-ridership-all-years.csv',[
      ['駅名','事業者','路線','年度','乗降客数_人日','状態','計上コード','データ有無コード','原典数値','注記','駅コード','原典URL'],
      ...visible.flatMap(s=>s.observations.map(o=>[s.name,s.operator,s.line,o.year,o.value,OBSERVATION_STATUS[o.status],o.duplicateCode,o.presenceCode,o.sourceValue,o.note,s.stationCode,stations.source.url]))]));
    $('#finance-export').addEventListener('click',()=>download('fukuoka-operator-finance.csv',[
      ['事業者または事業区分','年度','集計範囲','年間輸送量','輸送量の単位','営業収益_百万円','営業費用_百万円','費用の種別','営業利益_百万円','営業利益率_pct','元資料の金額単位','出典','原表の位置'],
      ...accounts.map(a=>[a.name,a.year,a.scope,a.passengersValue,a.passengersUnit,a.revenueMillionYen,a.expensesMillionYen,a.expensesMethod,a.profitMillionYen,operatingMargin(a),a.sourceMoneyUnit,a.sourceUrl,a.sourcePage])]));
    render();
  }catch(error){stations=null;$('#statistics-loading').textContent='実績・収支データの読み込みは未完了です。'+error.message;$('#statistics-loading').classList.add('op-error');}
}
