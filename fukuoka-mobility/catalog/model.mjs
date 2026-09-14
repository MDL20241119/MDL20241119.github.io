// Pure presentation semantics shared by the catalog and existing analyses.
export const STATUS = {USED:'分析・表示に利用中', PARTIAL:'一部利用・条件あり', AVAILABLE:'利用可能・未実装', PLANNED:'今後の収録候補', UNKNOWN:'確認が必要'};
export const CLASSES = {OPEN:'OPEN DATA', VERIFIED:'VERIFIED DATA', PARTNER:'PARTNER DATA'};
export const GAP = {AVAILABLE:{mark:'●',label:'収録確認'},PARTIAL:{mark:'△',label:'一部収録'},NOT_AVAILABLE:{mark:'×',label:'未収録'},UNKNOWN:{mark:'?',label:'未確認'}};
export const OUTCOMES = {
 AVAILABLE:{label:'条件下で移動可能',color:'#087852'},
 CONDITIONAL:{label:'条件付きで可能',color:'#94610d'},
 NOT_FOUND:{label:'登録条件で成立する経路なし',color:'#b44c3e'},
 INSUFFICIENT_DATA:{label:'データ不足により判定保留',color:'#66727c'}
};
export const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const fmt=v=>Number.isFinite(v)?v.toLocaleString('ja-JP'):'—';
export const dateText=v=>v?String(v).replace(/^(\d{4})(\d{2})(\d{2})$/,'$1-$2-$3').replace(/T.*$/,''):'未確認';
export const httpURL=v=>{try{const u=new URL(v);return ['https:','http:'].includes(u.protocol)?u.href:null;}catch{return null;}};
export const sourceLink=(url,name)=>httpURL(url)?`<a href="${esc(httpURL(url))}" target="_blank" rel="noopener noreferrer">${esc(name)} ↗</a>`:esc(name);
export function catalogURL(id){return 'data-catalog.html'+(id?'?dataset='+encodeURIComponent(id):'')+'#catalog';}
export function usedDatasets(catalog,{kind,sources=[],facilityIds=[],includePopulation=false,includeBoundary=false,allDestinations=false}={}){
 const hashes=new Set(sources.map(s=>s.hash??s.sha256).filter(Boolean)),files=new Set(sources.map(s=>s.file).filter(Boolean)),ids=new Set(facilityIds);
 return catalog.datasets.filter(d=>hashes.has(d.sha256)||(d.scope==='バス時刻表'&&d.localFiles.some(f=>files.has(f.split('/').at(-1))))||d.recordIds?.some(id=>ids.has(id))||allDestinations&&d.scope==='目的地'||includePopulation&&d.id==='population-2020'||includeBoundary&&d.id==='geo-boundaries'||['access','gaps'].includes(kind)&&d.id==='osm-walking'||kind==='gaps'&&d.id==='reference-unverified-stops');
}
export function outcome(r){
 if(!r)return 'INSUFFICIENT_DATA';
 // A known rejection is a condition failure, not evidence that no service exists.
 if(r.status==='not_met')return 'NOT_FOUND';
 const evidence=r.dataEvidence;
 const uncertain=r.searchIncomplete||!evidence||evidence.excluded>0||!evidence.feeds?.length||evidence.feeds.some(f=>f.coverage!=='known');
 if(r.outbound&&r.inbound)return r.status==='feasible'&&!uncertain?'AVAILABLE':'CONDITIONAL';
 return uncertain?'INSUFFICIENT_DATA':'NOT_FOUND';
}
export function outcomeLabel(r){return OUTCOMES[outcome(r)].label;}
export function matchDatasets(catalog,{category='all',status='all',dataClass='all',query=''}={}){
 const q=query.trim().toLocaleLowerCase('ja');
 return catalog.datasets.filter(d=>(category==='all'||d.categories.includes(category))&&(status==='all'||d.status===status)&&(dataClass==='all'||(d.dataClass??'UNCLASSIFIED')===dataClass)&&(!q||[d.name,d.provider,d.coverage,...d.categories].join(' ').toLocaleLowerCase('ja').includes(q)));
}
export function overview(c){const real=c.datasets.filter(d=>d.localFiles.length);return {datasets:real.length,open:real.filter(d=>d.dataClass==='OPEN').length,transport:real.filter(d=>d.category==='transport').length,municipalities:c.municipalities.length,destinations:c.overview.destinations};}
