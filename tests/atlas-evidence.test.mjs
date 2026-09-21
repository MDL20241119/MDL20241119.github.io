import assert from 'node:assert/strict';
import fs from 'node:fs';
import {safeURL,escapeHTML,displayValue,filterCases,caseClaims,usedIn,calculatePercentage,sourceFilter,gapCounts} from '../mobility-training/atlas-model.js';
const file=new URL('../mobility-training/data/atlas.json',import.meta.url);
const d=JSON.parse(fs.readFileSync(file,'utf8')),sources=new Map(d.sources.map(s=>[s.id,s])),claims=d.cases.flatMap(caseClaims),claimIds=new Set(claims.map(f=>f.id));
assert.equal(d.cases.length,98);assert.equal(d.cases.filter(c=>c.dataset==='traffic').length,37);assert.equal(d.cases.filter(c=>c.dataset==='training').length,61);
assert.equal(new Set(d.cases.map(c=>c.id)).size,98);assert.equal(sources.size,d.sources.length);assert.equal(claimIds.size,claims.length);
for(const c of d.cases){
 assert(c.name&&c.region&&c.operator);assert(c.sources.length);
 for(const id of c.sources)assert(sources.has(id),c.id+' unknown source '+id);
 assert.equal(c.graph.nodes.length,8);assert.equal(c.graph.edges.length,7);
 const nodeIds=new Set(c.graph.nodes.map(n=>n.id));
 for(const n of c.graph.nodes)for(const ref of n.field_refs)assert(claimIds.has(ref),'graph reference '+ref);
 for(const e of c.graph.edges){assert(nodeIds.has(e.from_id)&&nodeIds.has(e.to_id));assert(['SOURCE_CONFIRMED','MDL_ANALYSIS','HYPOTHESIS'].includes(e.relation_type));if(e.relation_type!=='SOURCE_CONFIRMED')assert.equal(e.causal,false);}
 for(const f of Object.values(c.fields)){
  assert(['FACT','CALCULATION','ANALYSIS','HYPOTHESIS'].includes(f.kind),f.id);
  assert(['IMPLEMENTED','PLANNED','NOT_CONFIRMED','NOT_IMPLEMENTED','NOT_APPLICABLE'].includes(f.status),f.id);
  for(const key of ['value','source_id','source_ids','evidence_level','verification_status','last_verified'])assert(key in f,f.id+' missing '+key);
  if(f.value===null)assert(!['IMPLEMENTED','PLANNED'].includes(f.status),f.id+' unknown value marked implemented');
  if(typeof f.value==='number'){assert(f.unit,f.id+' missing unit');assert(f.source_ids.length,f.id+' numeric claim missing source');}
  if(f.kind==='CALCULATION'){assert.equal(f.evidence_level,'D');assert(f.formula,f.id+' missing formula');}
  if(f.kind==='ANALYSIS')assert.equal(f.evidence_level,'D');
 }
 for(const g of c.gaps){assert.equal(g.kind,'ANALYSIS');assert.equal(g.evidence_level,'D');assert(g.source_fact&&g.source_ids.length);}
 for(const t of c.tags){assert(['SOURCE_TAG','ANALYSIS_TAG'].includes(t.tag_type));if(t.tag_type==='ANALYSIS_TAG')assert.equal(t.kind,'ANALYSIS');}
}
for(const f of [...claims,...d.headline_metrics,...d.social_issues]){
 assert(f.last_verified,f.id+' missing checked date');
 for(const id of f.source_ids||[])assert(sources.has(id),f.id+' missing source '+id);
}
for(const q of d.quality_issues){if(q.field_id)assert(claimIds.has(q.field_id),q.id+' dangling issue');if(q.source_id)assert(sources.has(q.source_id));}
const oita=d.cases.find(c=>c.id==='r7-058');
assert.equal(oita.fields.activity_count.value,35);assert.equal(oita.activities.length,35);
assert.equal(oita.fields.participants.value,750);assert.equal(oita.fields.participants.qualifier,'at_least');assert.equal(oita.fields.participants.verification_status,'USER_REPORTED');assert.equal(oita.fields.participants.status,'IMPLEMENTED');
assert(oita.fields.participants.source_ids.includes('mdl-oita-report'));assert(!oita.fields.participants.source_ids.includes('r7-058-s1'));
assert.equal(oita.fields.lecture.status,'IMPLEMENTED');assert.equal(oita.fields.lecture.kind,'ANALYSIS');assert(oita.fields.lecture.source_fact.includes('専門家の講演'));
assert.equal(oita.fields.social_implementation.value,null);assert.equal(oita.fields.social_implementation.status,'NOT_CONFIRMED');

assert.deepEqual(d.collections.map(c=>c.id),['traffic','training','mdl']);
assert.equal(d.collections.find(c=>c.id==='mdl').case_id,oita.id);assert.equal(oita.dataset,'training');
assert.deepEqual(['operating_days','actual_users','total_rides'].map(k=>oita.fields[k].value),[10,72,342]);
assert.equal(oita.fields.total_rides.unit,'人回');
for(const c of d.cases){
 const url=new URL(c.official_url);
 assert(['kotsu-kuhaku.jp','www.mlit.go.jp'].includes(url.hostname),c.id+' non-official case link');
 assert(sources.has(c.official_source_id),c.id+' missing official source');
 assert(c.official_link_checked_at,c.id+' unchecked official link');
 if(c.official_link_type==='CASE_DETAIL')assert(url.pathname.endsWith('/detail.php')&&url.searchParams.has('CN'));
 else {assert.equal(c.official_link_type,'ADOPTION_LIST');assert(url.pathname.endsWith('/001889172.pdf'));assert(c.official_link_label.includes('PDF'));}
}
assert.equal(d.cases.filter(c=>c.official_link_type==='CASE_DETAIL').length,40);
assert.equal(d.cases.filter(c=>c.dataset==='traffic'&&c.official_link_type==='CASE_DETAIL').length,37);

const aomori=d.cases.find(c=>c.id==='gap-006');assert.equal(aomori.fields.activation.value,calculatePercentage(36,98));assert.equal(aomori.fields.activation.period,aomori.fields.actual_users.period);
assert.equal(calculatePercentage(1,0),null);assert.equal(calculatePercentage(null,98),null);
for(const [id,total] of [['r7-037',177],['r7-054',288],['r7-059',204],['r7-061',247]]){const f=d.cases.find(c=>c.id===id).fields.participants;assert.equal(f.kind,'CALCULATION');assert.equal(f.inputs.reduce((s,x)=>s+x.value,0),total);for(const input of f.inputs)assert(sources.has(input.source_id));}
assert.equal(safeURL(null),null);assert.equal(safeURL(''),null);assert.equal(safeURL('javascript:alert(1)'),null);assert.equal(safeURL('data:text/html,test'),null);
assert.equal(escapeHTML('<img src=x onerror="x">'),'&lt;img src=x onerror=&quot;x&quot;&gt;');
assert.equal(displayValue({value:null}),'未確認');assert.equal(displayValue({value:0,unit:'人'}),'0 人');
assert(displayValue(oita.fields.participants).includes('750 人以上'));
assert.equal(filterCases(d.cases,{dataset:'traffic'}).length,37);assert.equal(filterCases(d.cases,{dataset:'training'}).length,61);
assert(filterCases(d.cases,{query:'青森',gap:'PLACE'}).some(c=>c.id==='gap-006'));
assert(filterCases(d.cases,{dataset:'training',activity:'pbl',status:'PLANNED'}).every(c=>c.fields.pbl.status==='PLANNED'));
assert.equal(filterCases(d.cases,{query:'存在しない事業 xyz-987'}).length,0);
assert(filterCases(d.cases,{status:'IMPLEMENTED'}).length<98);
assert.equal(filterCases(d.cases,{status:'NOT_IMPLEMENTED'}).length,d.cases.filter(c=>['lecture','pbl','fieldwork','resident_participation','student_participation','demonstration','actual_operation','social_implementation','continuity'].some(k=>c.fields[k]?.status==='NOT_IMPLEMENTED')).length);
assert.deepEqual(d.cases.find(c=>c.id==='gap-004').gaps.map(g=>g.gap_id),['TIME','SUPPLY']);
assert(usedIn(d,'traffic-426557').some(x=>x.claim_id==='gap-006:actual_users'));
assert(usedIn(d,'mdl-oita-report').some(x=>x.claim_id==='r7-058:participants'));
assert(sourceFilter(sources.get('population-2024'),{category:'統計',dataset:'social',level:'A'}));
assert(gapCounts(d.cases.filter(c=>c.dataset==='traffic'),d.gaps).every(g=>g.count>=0&&g.count<=37));
const fields=d.cases.flatMap(c=>Object.values(c.fields));
const report={version:'1.0.0',checked_at:d.updated_at,structural_checks:'PASS',cases:d.cases.length,traffic_cases:37,training_projects:61,fields:fields.length,sources:d.sources.length,claims:claims.length,unknown_values:fields.filter(f=>f.value===null).length,needs_verification:d.quality_issues.length,source_links_reachable:d.sources.filter(s=>s.link_status==='REACHABLE').length,source_links_need_verification:d.sources.filter(s=>s.url&&s.link_status!=='REACHABLE').map(s=>({id:s.id,url:s.url,status:s.http_status||s.link_status})),non_public_sources:d.sources.filter(s=>!s.url).map(s=>({id:s.id,access:s.access})),checks:['37+61母集団・固有ID','全フィールドの証拠属性と出典参照','元資料→使用項目の逆引き','未確認のnull・計画/実施の分離','35活動・750人以上のMDL活動集計と定義','37交通事例のURL取得','計算入力・式・単位・対象期間','8段階Graphの参照・関係種別','URL安全性・表示エスケープ','検索・GAP・計画/実施フィルタ'],limits:['人材育成61事業の全原典の内容を今回再検証したものではありません。既存の確認記録を継承しています。','構造検査PASSは全ての事実・成果の検証完了を意味しません。','750人以上はMDL活動集計による延べ参加人数です。実証参加を含み、ユニーク参加者数とは区別します。','リンク到達確認は内容の根拠性の確認とは別です。'],ui_verification:fs.existsSync(new URL('../mobility-training/data/ui-verification.json',import.meta.url))?JSON.parse(fs.readFileSync(new URL('../mobility-training/data/ui-verification.json',import.meta.url),'utf8')):'公開画面で別途確認'};
fs.writeFileSync(new URL('../mobility-training/data/quality-report.json',import.meta.url),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));

