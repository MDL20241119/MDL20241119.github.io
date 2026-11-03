/* Dated supplement: preserve baseline identities, expose evidence, avoid double-counting. */
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert'),cp=require('child_process');
const root=path.resolve(__dirname,'..'),repo=path.dirname(root),read=p=>JSON.parse(fs.readFileSync(path.join(root,'data',p),'utf8'));
const updates=read('research-updates.json'),original=read('index-canonical.json');
const ctx={window:{},document:{body:{dataset:{}},addEventListener(){}},location:{hash:'#records'},URLSearchParams,console,fetch:async url=>{const p=path.resolve(repo,'mobility-policy-history',String(url).split(/[?#]/)[0]);assert(p.startsWith(root+'/'));return {ok:fs.existsSync(p),status:fs.existsSync(p)?200:404,json:async()=>JSON.parse(fs.readFileSync(p,'utf8'))};}};
vm.createContext(ctx);for(const p of ['data/bootstrap.js','assets/results.js'])vm.runInContext(fs.readFileSync(root+'/'+p,'utf8'),ctx);
const ui=ctx.window.MOBILITY_RESULTS,checks=[];async function check(name,fn){await fn();checks.push({name,result:'pass'});}
(async()=>{
 await check('260 canonical IDs and all frozen event/claim/source records are preserved',async()=>{
  const rows=await ui.index('canonical');assert.equal(rows.length,260);assert.equal(rows.map(r=>r.id).join(','),original.map(r=>r.id).join(','));
  for(const file of ['mobility-policy-history/data/mobility_history_data.json','mobility-policy-history/data/view-data.js','municipal-mobility-history/data/index-canonical.json',...new Set(original.map(r=>'municipal-mobility-history/'+r.detail))])assert(fs.readFileSync(repo+'/'+file).equals(cp.execFileSync('git',['show','HEAD:'+file],{cwd:repo,maxBuffer:20*1024*1024})),file);
 });
 await check('Four additions appear with source links and retain baseline evidence IDs',async()=>{
  for(const [id,u] of Object.entries(updates.cases)){
   const row=original.find(r=>r.id===id),c=JSON.parse(fs.readFileSync(root+'/'+row.detail,'utf8'))[id];
   const html=await ui.content({view:'case',id,p:{}});assert(html.includes('id="research-update"'));assert(html.includes(u.title));for(const source of u.sources)assert(html.includes(source.url));for(const ev of c.events)assert(html.includes(ev.event_id));for(const claim of c.claims)assert(html.includes(claim.claim_id));
  }
 });
 await check('Only verified status changes affect filters; technical trials and date disputes keep prior categories',async()=>{
  const rows=await ui.index('canonical');assert.equal(rows.find(r=>r.id==='P-28fda69d5a179f31').state,'pause');assert.equal(rows.find(r=>r.id==='P-93e05d17a0244580').state,'operation');
  for(const id of ['P-a46cf400d5648626','P-ded1674606a66ec9'])assert.equal(rows.find(r=>r.id===id).state,original.find(r=>r.id===id).state);
  assert.equal(read('summary.json').counts.canonical,260);assert.equal(read('summary.json').counts.canonical_events,898);
 });
 await check('Independent supplement preserves distinctions, limitations and legal chronology',async()=>{
  assert.equal(updates.policy_events.length,5);assert.deepEqual(updates.policy_events.map(e=>e.date),['2023-11-02','2023-12-28','2024-03-29','2024-04-26','2026-02-26']);
  const html=fs.readFileSync(repo+'/mobility-policy-history/updates/2026-11/index.html','utf8');for(const token of ['78条2号','78条3号','79条','51,307','19,961','43,124','2,213件','28.1%','17日間','代替車両','2027年3月','原典内で不一致','14件','prefers-reduced-motion'])assert(html.includes(token),token);
  for(const [id,u] of Object.entries(updates.cases))assert(html.includes('#case/'+id));
 });
 await check('Release and stale canonical guard remain effective',async()=>{assert.throws(()=>ui.validateData('index-canonical.json',Array(259)),/版が一致/);assert.throws(()=>ui.validateData('summary.json',{counts:{canonical:259}}),/版が一致/);assert.equal(ui.validateData('index-canonical.json',Array(260)).length,260);});
 const result={passed:checks.length,failed:0,checks};fs.writeFileSync(__dirname+'/research-updates-results.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
})().catch(e=>{console.error(e);process.exit(1)});
