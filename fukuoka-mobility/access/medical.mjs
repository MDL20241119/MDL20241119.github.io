import {readJSON} from '../assets/read-json.mjs';
import {esc} from '../operators/model.mjs';
const safeLink=(url,label)=>/^https?:\/\//.test(url??'')?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)} ↗</a>`:esc(label);
const hours=new Map();
const kinds={hospital:'病院',clinic:'診療所',dental:'歯科診療所',maternity:'助産所',pharmacy:'薬局'};
const range=v=>v?.some(Boolean)?v.map(t=>t??'未記載').join('〜'):'未記載';
export async function renderMedical(container,id,file){
  if(!container)return;
  container.textContent='公表された診療・受付時刻を読み込んでいます…';
  try{
    if(!hours.has(file))hours.set(file,readJSON(file).catch(e=>{hours.delete(file);throw e;}));
    const data=await hours.get(file),f=data.facilities[id];
    if(!f){container.textContent='公表時刻の対応データはありません。';return;}
    container.innerHTML=`<details><summary>公表された曜日別の${f.category==='pharmacy'?'営業時間':'診療・受付時刻'}</summary><p>${esc(f.asOf)}時点の通常週。祝日・特定週・臨時休診・受入条件は施設へ確認してください。下の時刻は往復条件へ自動適用していません。</p>${f.schedules.length?f.schedules.map(s=>`<h3>${esc(s.department)}</h3><div class="medical-table-scroll" role="region" aria-label="公表された医療施設情報" tabindex="0"><table><thead><tr><th>曜日</th><th>${f.category==='pharmacy'?'営業':'診療'}</th>${f.category==='pharmacy'?'':'<th>外来受付</th>'}</tr></thead><tbody>${Object.entries(s.days).flatMap(([day,slots])=>slots.map(slot=>`<tr><th>${esc(day)}</th><td>${esc(range(slot.care))}</td>${f.category==='pharmacy'?'':`<td>${esc(range(slot.reception))}</td>`}</tr>`)).join('')}</tbody></table></div>`).join(''):'<p>通常週の時刻は原典に記載がありません。</p>'}<p>${safeLink(f.hoursSourceResourceUrl,'時刻の原典データ')} · ${safeLink(f.sourceUrl,'厚生労働省の公開元')}</p></details>`;
  }catch(e){container.textContent='診療・受付時刻を取得できませんでした。';}
}
export async function renderMedicalAudit(container){
  if(!container)return;
  try{const r=await fetch('data/medical-audit.json');if(!r.ok)throw Error();const a=await r.json();
    container.innerHTML=`<h2>医療施設データの収録状況</h2><p>厚労省の2026年6月1日データから福岡県の全行を取得。${a.located.toLocaleString('ja-JP')}施設を地図・往復計算へ接続しました。原典の位置等を確認できない${a.unlocated.length}施設は以下に掲載し、地図の計算には使いません。</p><div class="medical-table-scroll" role="region" aria-label="公表された医療施設情報" tabindex="0"><table><thead><tr><th>区分</th><th>原典件数</th><th>地図に反映</th><th>位置等の確認が必要</th></tr></thead><tbody>${Object.entries(a.counts).map(([k,c])=>`<tr><th>${kinds[k]}</th><td>${c.sourceRows}</td><td>${c.located}</td><td>${c.unlocated}</td></tr>`).join('')}</tbody></table></div><details><summary>位置等の確認が必要な全${a.unlocated.length}施設</summary><ul>${a.unlocated.map(f=>`<li><b>${esc(f.name)}</b>（${kinds[f.category]}）<br>${esc(f.address)} · ${safeLink(f.sourceUrl,'原典')}<br>${esc(f.reason)}</li>`).join('')}</ul></details>`;
  }catch{container.textContent='医療施設の収録状況を取得できませんでした。';}
}
