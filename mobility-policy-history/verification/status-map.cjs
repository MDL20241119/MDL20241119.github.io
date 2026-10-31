const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path'),crypto=require('crypto');
const root=path.resolve(__dirname,'..');
const ctx={window:{},location:{hash:'#map'},URLSearchParams,console};vm.createContext(ctx);
for(const f of ['data/view-data.js','data/japan-map.js','data/case-status.js','assets/infographics.js','assets/history.js'])vm.runInContext(fs.readFileSync(root+'/'+f,'utf8'),ctx);
const D=ctx.window.MOBILITY_DATA,S=ctx.window.MOBILITY_CASE_STATUS,U=ctx.window.MOBILITY_UI,V=U.graphics;
const rows=[];
function check(name,fn){try{fn();rows.push({name,result:'pass'});}catch(err){rows.push({name,result:'fail',reason:err.message});}}
check('111 classifications retain original states, date provenance and valid source/event references',()=>{
 assert.equal(Object.keys(S.by_case).length,111);
 assert.equal(S.canonical_sha256,crypto.createHash('sha256').update(fs.readFileSync(root+'/data/mobility_history_data.json')).digest('hex'));
 const sources=new Set(D.sources.map(s=>s.source_id)),events=new Set(U.findEvents().map(ev=>ev.event_id));
 for(const c of D.cases){const s=S.by_case[c.id];assert(s);assert.equal(s.raw_status,c.status);assert.equal(s.evidence_as_of,c.status_as_of||'根拠時点未確認');assert(s.scope&&s.reason);assert(S.groups.some(g=>g.id===s.category));for(const id of s.source_ids)assert(sources.has(id));for(const id of s.event_ids)assert(events.has(id));}
});
check('Six exclusive groups cover all cases with reviewed counts',()=>{
 const expected={continuing:17,ended:3,paused:4,testing:16,completed:17,unconfirmed:54};
 for(const [id,n] of Object.entries(expected))assert.equal(U.findCases({status:id}).length,n);
 assert.equal(Object.values(expected).reduce((a,b)=>a+b,0),111);
});
check('Only explicit service closures are red; trial ends and selection withdrawals stay separate',()=>{
 assert.equal(U.findCases({status:'ended'}).map(c=>c.id).join(','),'mlit_miyama,ENV-C05,V-C04');
 for(const id of ['mlit_izuko','mlit_dento','meti_yatomi','ENV-C12','DIG-C10'])assert.equal(S.by_case[id].category,'completed');
 for(const id of ['mlit_iinan','mlit_iyo','meti_eiheiji','V-C03'])assert.equal(S.by_case[id].category,'paused');
});
check('Mixed technology/service states and negated or planned endings are handled explicitly',()=>{
 assert.equal(S.by_case['V-C02'].category,'continuing');assert(S.by_case['V-C02'].reason.includes('普通車'));
 assert.equal(S.by_case.meti_ina.category,'continuing');assert(S.by_case.meti_ina.reason.includes('ドローン配送'));
 assert.equal(S.by_case.mlit_showa.category,'unconfirmed');assert(S.by_case.mlit_showa.reason.includes('終了予定'));
 assert.equal(S.by_case['V-C03'].category,'paused');assert(S.by_case['V-C03'].reason.includes('別系統'));
});
check('Older operating records and republished results do not become current operation confirmations',()=>{
 for(const id of ['mlit_kamikoani','mlit_okueigenji','mlit_fukuyama','mlit_gunma','ENV-C07','OTHER-C04','OTHER-C05','V-C12'])assert.equal(S.by_case[id].category,'unconfirmed');
 assert.equal(S.by_case['DIG-C15'].category,'unconfirmed');
 for(const c of U.findCases({status:'continuing'}))assert(/2026/.test(c.status_as_of),'Missing 2026 evidence context '+c.id);
});
check('Comparison maps show both statuses without treating a whole prefecture as one status',()=>{
 const html=V.mapPage({});assert.equal([...html.matchAll(/class="japan-map"/g)].length,2);assert(html.includes('map-grid-continuing'));assert(html.includes('map-grid-ended'));
 const keep=V.counts(U.findCases({status:'continuing'})),end=V.counts(U.findCases({status:'ended'}));
 assert.equal(keep['神奈川県'],1);assert.equal(end['神奈川県'],1);
 const filtered=V.mapPage({pref:'福岡県',status:'ended'});assert(filtered.includes('data-case-id="mlit_miyama"'));assert.equal([...filtered.matchAll(/data-case-id=/g)].length,1);
});
check('Status persists through map filters, pagination, timeline links and case return routes',()=>{
 const html=V.mapPage({status:'unconfirmed',theme:'MaaS'});assert(html.includes('name="status" value="unconfirmed"'));
 for(const m of html.matchAll(/href="(#[^"]+)"/g)){
  const r=U.readRoute(m[1].replaceAll('&amp;','&').slice(1));
  if(r.view==='timeline')assert.equal(r.p.status,'unconfirmed');
  if(r.p.page)assert.equal(r.p.status,'unconfirmed');
 }
 assert(U.pageHtml({view:'timeline',p:{status:'ended',year:'2024'}}).includes('name="status" value="ended"'));
 assert(U.findEvents({status:'ended'}).every(ev=>ev.case_id&&S.by_case[ev.case_id].category==='ended'));
});
check('Historical event-year filters retain latest status semantics and exact original dates',()=>{
 const cases=U.findCases({status:'ended',year:'2018',pref:'福岡県'});assert.equal(cases.length,1);assert.equal(cases[0].id,'mlit_miyama');
 assert(V.mapPage({status:'ended',year:'2018',pref:'福岡県'}).includes('選んだ年に記録がある事例の、最終確認状況を表示'));
 assert(V.mapPage({status:'ended',year:'2018',pref:'福岡県'}).includes('2024-03-31'));
});
check('Each detail keeps its original wording and exposes scope, reason and evidence date',()=>{
 for(const c of D.cases){const h=U.caseDetail(c.id,{}),s=S.by_case[c.id];assert(h.includes('data-life="'+s.category+'"'));assert(h.includes(s.scope));assert(h.includes(s.reason));assert(h.includes(c.status.replaceAll('&','&amp;')));}
});
const result={passed:rows.filter(r=>r.result==='pass').length,failed:rows.filter(r=>r.result==='fail').length,checks:rows};
fs.writeFileSync(__dirname+'/status-map-results.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));if(result.failed)process.exit(1);
