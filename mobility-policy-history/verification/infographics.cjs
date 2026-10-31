const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const root=path.resolve(__dirname,'..');
const ctx={window:{},location:{hash:'#home'},URLSearchParams,console};
vm.createContext(ctx);
for(const f of ['data/view-data.js','data/japan-map.js','assets/infographics.js','assets/history.js'])
  vm.runInContext(fs.readFileSync(path.join(root,f),'utf8'),ctx);
const D=ctx.window.MOBILITY_DATA,U=ctx.window.MOBILITY_UI,V=U.graphics,G=ctx.window.MOBILITY_JAPAN_MAP;
const results=[];
function check(name,fn){try{fn();results.push({name,result:'pass'});}catch(err){results.push({name,result:'fail',reason:err.message});}}
check('Map has 47 unique prefectures with finite vector coordinates',()=>{
 assert.equal(G.length,47);assert.equal(new Set(G.map(g=>g.name)).size,47);
 for(const g of G){assert(/^JP-\d\d$/.test(g.code));assert(/^M/.test(g.d));assert(!/NaN|undefined|Infinity/.test(g.d));}
 const svg=V.mapSvg(D.cases);assert.equal([...svg.matchAll(/data-prefecture=/g)].length,47);
 assert(!/data-count=/.test(svg),'Global header-count update must not overwrite SVG children');
 assert.equal([...svg.matchAll(/<path d="M/g)].length,50);
});
check('Every prefecture map count agrees with independent case memberships',()=>{
 const actual=V.counts(D.cases);
 for(const g of G){const expected=D.cases.filter(c=>c.prefectures.includes(g.name)).length;assert.equal(actual[g.name],expected);}
 assert.equal(G.filter(g=>actual[g.name]>0).length,36);
 assert.equal(D.cases.filter(c=>c.prefectures.includes('広域・全国等')).length,7);
});
check('Map year and theme combinations agree with original event and theme records',()=>{
 for(const year of ['2016','2024','2026'])for(const theme of ['','MaaS','自動運転'])for(const pref of ['','福岡県','静岡県','大分県','岩手県']){
  const expected=D.cases.filter(c=>(!theme||c.themes.includes(theme))&&(!pref||c.prefectures.includes(pref))&&c.events.some(ev=>ev.date_precision!=='unknown'&&String(ev.event_date).match(/(?:19|20)\d{2}/)?.[0]===year));
  assert.equal(V.mapCases({year,theme,pref}).map(c=>c.id).join(),expected.map(c=>c.id).join());
 }
});
check('Map selected area, empty state, wide-area records and pagination render',()=>{
 const oita=V.mapPage({pref:'大分県'});assert(oita.includes('大分MaaS'));assert(oita.includes('由布院ノルク'));assert(!oita.includes('data-case-id="meti_eiheiji"'));
 assert(V.mapPage({pref:'岩手県'}).includes('この条件の事例は収録されていません'));
 assert(V.mapPage({pref:'広域・全国等'}).includes('広域・全国等'));
 const first=V.mapPage({}),second=V.mapPage({page:'2'});
 assert.equal([...first.matchAll(/data-case-id=/g)].length,12);assert.equal([...second.matchAll(/data-case-id=/g)].length,12);
 const ids=s=>[...s.matchAll(/data-case-id="([^"]+)"/g)].map(m=>m[1]);
 assert(!ids(first).some(id=>ids(second).includes(id)));
});
check('All new map routes and source-backed policy milestone event IDs resolve',()=>{
 const htmls=[V.homeMap(),V.mapPage({}),V.milestones(),V.timelineIntro({year:'2026'}),V.mapPage({pref:'大分県',year:'2024',theme:'MaaS'})];
 const eventIds=new Set(U.findEvents().map(x=>x.event_id));
 for(const html of htmls)for(const m of html.matchAll(/href="(#[^"]+)"/g)){
  const r=U.readRoute(m[1].replaceAll('&amp;','&').slice(1));
  assert(['home','map','timeline','case'].includes(r.view));
  if(r.p.event)assert(eventIds.has(r.p.event),'Unknown milestone '+r.p.event);
  if(r.p.pref)assert(G.some(g=>g.name===r.p.pref)||r.p.pref==='広域・全国等');
 }
});
check('Annual stacked chart counts agree with independent 2016–2026 event totals',()=>{
 const all=[...D.cases.flatMap(c=>c.events),...D.policy_events];
 const html=V.decade();assert.equal([...html.matchAll(/class="decade-column(?: selected)?"/g)].length,11);
 for(let y=2016;y<=2026;y++){
  const es=all.filter(ev=>ev.date_precision!=='unknown'&&String(ev.event_date).match(/(?:19|20)\d{2}/)?.[0]===String(y));
  const local=es.filter(ev=>ev.case_id).length,policy=es.length-local;
  assert(html.includes(`${y}年・年度：地域${local}件、政策${policy}件`));
 }
 assert(V.timelineIntro({year:'pre'}).includes('2015年以前（前史）'));
 assert(V.timelineIntro({year:'undated'}).includes('日付未確定'));
});
check('Both timeline lanes retain every original event and no duplicate IDs',()=>{
 for(let y=2016;y<=2026;y++){
  const es=U.findEvents({year:String(y)}),h=V.yearLanes(String(y),es,{year:String(y)});
  const ids=[...h.matchAll(/data-event-id="([^"]+)"/g)].map(m=>m[1]);
  assert.equal(ids.length,es.length);assert.equal(new Set(ids).size,es.length);
  assert.equal(new Set(ids).size,new Set(es.map(ev=>ev.event_id)).size);
  assert(h.includes('national-lane'));assert(h.includes('regional-lane'));
 }
});
check('Case year markers only link to actual recorded events',()=>{
 const allIds=new Set(U.findEvents().map(ev=>ev.event_id));
 for(const c of D.cases){
  const h=V.caseTrace(c,{from:'map?pref=福岡県'});
  for(const m of h.matchAll(/href="(#[^"]+)"/g)){
   const r=U.readRoute(m[1].replaceAll('&amp;','&').slice(1));assert.equal(r.id,c.id);assert(allIds.has(r.p.event));assert.equal(r.p.from,'map?pref=福岡県');
  }
 }
});
const summary={passed:results.filter(x=>x.result==='pass').length,failed:results.filter(x=>x.result==='fail').length,checks:results};
fs.writeFileSync(path.join(__dirname,'infographics-results.json'),JSON.stringify(summary,null,2)+'\n');
console.log(JSON.stringify(summary,null,2));if(summary.failed)process.exit(1);
