const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const root=path.resolve(__dirname,'..');
const context={window:{},location:{hash:'#home'},URLSearchParams,console,Map,Set,Array,String,Object,Number,JSON,Math};
vm.createContext(context);
vm.runInContext(fs.readFileSync(root+'/data/view-data.js','utf8'),context);
vm.runInContext(fs.readFileSync(root+'/assets/history.js','utf8'),context);
const {window:W}=context,D=W.MOBILITY_DATA,U=W.MOBILITY_UI;
const rows=[];
function check(name,f){try{f();rows.push({name,result:'pass'});}catch(err){rows.push({name,result:'fail',reason:err.message});}}
check('All 111 case detail screens render with original status and IDs',()=>{
 assert.equal(D.cases.length,111);
 for(const c of D.cases){const h=U.caseDetail(c.id,{});assert(h.includes(c.id));assert(h.includes(c.name.replaceAll('&','&amp;')));assert(h.includes(c.status.replaceAll('&','&amp;').replaceAll('>','&gt;').replaceAll('<','&lt;')));for(const ev of c.events)assert(h.includes('data-event-id="'+ev.event_id+'"'));}
});
check('All 66 policy detail screens render',()=>{assert.equal(D.programs.length,66);for(const p of D.programs)assert(U.programDetail(p.id,{}).includes(p.id));});
check('All 341 source detail screens render and point to original URLs',()=>{assert.equal(D.sources.length,341);for(const s of D.sources){const h=U.sourceDetail(s.source_id,{});assert(h.includes(s.source_id));assert(h.includes(s.url.replaceAll('&','&amp;')));}});
check('All 467 events are reachable and preserve raw date display',()=>{
 assert.equal(U.findEvents().length,467);
 for(const ev of U.findEvents()){
   const h=U.eventHtml(ev);assert(h.includes(ev.event_id));assert(h.includes(String(ev.event_date_display||ev.event_date||'日付未確認').replaceAll('&','&amp;')));
   if(ev.date_precision==='month'&&!ev.event_date.includes('/'))assert(!h.includes('>'+ev.date_sort_bounds?.start+'</time>'));
 }
});
check('Canonical old case and policy IDs resolve',()=>{for(const [old,id] of Object.entries(D.id_mapping.cases))assert(U.caseDetail(old,{}).includes('class="id-label">'+id));for(const [old,id] of Object.entries(D.id_mapping.programs))assert(U.programDetail(old,{}).includes('class="id-label">'+id));});
check('Old name, alias and alternate notation searches resolve',()=>{
 assert(U.findCases({q:'MaeMaaS'}).some(c=>c.id==='mlit_gunma'));
 assert(U.findCases({q:'GunMaaS'}).some(c=>c.id==='mlit_gunma'));
 assert(U.findCases({q:'meti_komono'}).some(c=>c.id==='mlit_komono'));
 assert(U.findCases({q:'ＺＥＮ　drive'}).some(c=>c.id==='meti_eiheiji'));
 assert.equal(U.findCases({deep:'1'}).length,25);
});
check('Every theme, ministry, prefecture, status and year filter has exact selector behavior',()=>{
 for(const k of ['theme','agency','pref','state']){
  const field={theme:'themes',agency:'agencies',pref:'prefectures',state:'states'}[k];
  for(const v of new Set(D.cases.flatMap(c=>c[field]))) {
   const found=U.findCases({[k]:v});assert(found.length);assert(found.every(c=>c[field].includes(v)));
  }
 }
 for(let y=2016;y<=2026;y++){assert(U.findEvents({year:String(y)}).every(x=>U.eventYear(x)===String(y)));}
 assert.equal(U.findEvents({kind:'case'}).length,378);assert.equal(U.findEvents({kind:'policy'}).length,89);
 assert.equal(U.findCases({q:'NO_MATCH__0x0499'}).length,0);
 assert.equal(U.findCases({q:'MaeMaaS',pref:'北海道'}).length,0);
 assert.equal(U.findCases({q:'',year:'',theme:'',state:'',pref:'',agency:''}).length,111);
});
check('Unknown and non-day precisions remain distinct',()=>{
 const undated=U.findEvents({year:'undated'});assert.equal(undated.length,2);assert(undated.every(e=>e.date_precision==='unknown'));
 for(const precision of new Set(U.findEvents().map(e=>e.date_precision)))assert(U.findEvents().filter(e=>e.date_precision===precision).every(e=>U.eventHtml(e).includes(e.event_id)));
 assert(U.eventHtml(U.findEvents().find(e=>e.date_precision==='retrieval_day')).includes('資料確認日'));
 const c=D.cases.find(c=>c.id==='mlit_nishikata');assert(!c.states.includes('運行・実装等を記録'));
});
check('Merged events retain all source observations and event IDs',()=>{
 const merged=U.findEvents().filter(e=>e.source_observations);
 for(const ev of merged)for(const o of ev.source_observations){const h=U.eventHtml(ev);assert(h.includes(o.event_id));assert(h.includes(o.origin_record_id));}
 assert.equal(D.source_case_event_records,384);
});
check('Separate services remain separate; subsidy and related-only records differ',()=>{
 for(const group of D.id_mapping.related_not_merged){const ids=group.ids.filter(id=>D.cases.some(c=>c.id===id));assert(new Set(ids).size===ids.length);}
 const s=D.cases.find(c=>c.id==='ENV-C07');assert.equal(s.program_ids.length,0);assert(s.program_attribution_text.length);
 assert(U.programDetail('ENV-P04',{}).includes('関連記述のみ'));
});
check('Financial bases and primary report case pages are retained',()=>{
 const h=U.caseDetail('meti_mitoyo',{});assert(h.includes('20,031,176'));assert(h.includes('-104,078'));assert(h.includes('サービス活動増減差額'));
 assert.equal(Object.keys(D.detail_pages).length,25);
 assert.equal(D.detail_pages.meti_eiheiji.join(','),'15,16');
});
check('Internal hash routes and every generated local asset reference resolve',()=>{
 let links=0;
 const htmls=[U.pageHtml({view:'home',p:{}}),U.pageHtml({view:'cases',p:{}}),U.pageHtml({view:'programs',p:{}}),U.pageHtml({view:'timeline',p:{}}),U.pageHtml({view:'sources',p:{}}),...D.cases.map(c=>U.caseDetail(c.id,{})),...D.programs.map(p=>U.programDetail(p.id,{})),...D.sources.map(s=>U.sourceDetail(s.source_id,{}))];
 for(const html of htmls)for(const m of html.matchAll(/href="([^"]+)"/g)){
  const url=m[1].replaceAll('&amp;','&');if(url.startsWith('#')){
   const r=U.readRoute(url.slice(1));assert(['home','cases','programs','timeline','sources','case','program','source'].includes(r.view));
   if(r.view==='case')assert(D.cases.some(c=>c.id===(D.id_mapping.cases[r.id]||r.id)));
   if(r.view==='program')assert(D.programs.some(p=>p.id===(D.id_mapping.programs[r.id]||r.id)));
   if(r.view==='source')assert(D.sources.some(s=>s.source_id===r.id));links++;
  }else if(!url.startsWith('https://'))assert(fs.existsSync(root+'/'+url.split('#')[0]),url);
 }
 rows.push({name:'Resolved internal route references',result:'pass',references:links});
});
check('Canonical JSON bytes remain unchanged',()=>{assert.equal(require('crypto').createHash('sha256').update(fs.readFileSync(root+'/data/mobility_history_data.json')).digest('hex'),JSON.parse(fs.readFileSync(root+'/verification/data-audit.json','utf8')).canonical_sha256);});
const result={passed:rows.filter(x=>x.result==='pass').length,failed:rows.filter(x=>x.result==='fail').length,checks:rows};
fs.writeFileSync(__dirname+'/acceptance-results.json',JSON.stringify(result,null,2));
console.log(JSON.stringify(result,null,2));if(result.failed)process.exit(1);
