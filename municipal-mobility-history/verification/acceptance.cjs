/* Validate data-to-screen correspondence using independent input controls. */
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert'),crypto=require('crypto');
const root=path.resolve(__dirname,'..'),repo=path.dirname(root),results=[],requestedUrls=[];
const read=p=>JSON.parse(fs.readFileSync(path.join(root,'data',p),'utf8'));
const context={window:{MOBILITY_RESULTS_SUMMARY:JSON.parse(fs.readFileSync(path.join(root,'data/bootstrap.js'),'utf8').replace(/^window.MOBILITY_RESULTS_SUMMARY=/,'').replace(/;\s*$/,''))},document:{body:{dataset:{}},addEventListener(){}},location:{hash:'#records'},URLSearchParams,console,fetch:async url=>{
  requestedUrls.push(String(url));const p=path.resolve(repo,'mobility-policy-history',String(url).split(/[?#]/)[0]);assert(p.startsWith(root+'/'));return {ok:fs.existsSync(p),status:fs.existsSync(p)?200:404,json:async()=>JSON.parse(fs.readFileSync(p,'utf8'))};
}};
vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(repo,'mobility-policy-history/data/japan-map.js'),'utf8'),context);vm.runInContext(fs.readFileSync(path.join(root,'assets/results.js'),'utf8'),context);
const ui=context.window.MOBILITY_RESULTS;
const batchControlPath=path.join(__dirname,'current-batch-controls.json'),batchControls=fs.existsSync(batchControlPath)?JSON.parse(fs.readFileSync(batchControlPath,'utf8')):null;
const expected=batchControls?.expected||{deep:83,claims:786,events:364};
async function check(name,fn){try{const detail=await fn();results.push({name,result:'pass',...detail});}catch(e){results.push({name,result:'fail',message:e.message});}}
(async()=>{
 await check('Every original record ID has exactly one indexed detail in its own layer',async()=>{
   const controls={deep:expected.deep,selection:2120,reference:497,review:343,local:100,legacy:111,history:3041};
   for(const [layer,count] of Object.entries(controls)){const ix=read('index-'+layer+'.json');assert.equal(ix.length,count);assert.equal(new Set(ix.map(r=>r.id)).size,count);for(const row of ix){const sh=JSON.parse(fs.readFileSync(path.join(root,row.detail),'utf8'));assert(sh[row.id],layer+':'+row.id);assert.equal(sh[row.id].provenance.original_id,row.id);}}
   return {controls};
 });
 await check('All result screens retain independently expected claim IDs, event IDs, sources and raw dates',async()=>{
   let claims=0,events=0;for(const r of read('index-deep.json')){const c=JSON.parse(fs.readFileSync(path.join(root,r.detail),'utf8'))[r.id];const html=await ui.content({view:'case',id:r.id,p:{}});for(const cl of c.claims){assert(html.includes(cl.claim_id),cl.claim_id);claims++;}for(const ev of c.events){assert(html.includes('id="event-'+ev.event_id+'"'));assert(html.includes(ev.date_label.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;')));events++;}for(const s of c.sources)assert(html.includes('id="source-'+s.source_id+'"'));}
   assert.equal(claims,expected.claims);assert.equal(events,expected.events);return {claims,events};
 });
 await check('Original 72 details are field-identical to recovered branch; all original 724 claims and 313 events remain',async()=>{
   const golden=JSON.parse(fs.readFileSync(path.join(__dirname,'baseline-continuation-controls.json'),'utf8'));
   const canonical=x=>Array.isArray(x)?x.map(canonical):x&&typeof x==='object'?Object.fromEntries(Object.keys(x).sort().map(k=>[k,canonical(x[k])])):x;
   const ix=read('index-deep.json');let claims=0,events=0;
   assert.equal(Object.keys(golden.baseline_cases).length,72);
   for(const [id,g] of Object.entries(golden.baseline_cases)){const row=ix.find(r=>r.id===id);assert(row);const detail=JSON.parse(fs.readFileSync(path.join(root,row.detail),'utf8'))[id];assert.equal(crypto.createHash('sha256').update(JSON.stringify(canonical(detail))).digest('hex'),g.detail_sha256,id);claims+=g.claim_ids.length;events+=g.event_ids.length;}
   assert.equal(claims,724);assert.equal(events,313);return {cases:72,claims,events};
 });
 await check('Prior 11 cases, 84 metrics and 51 events match independently frozen research controls and all source anchors render',async()=>{
   const golden=JSON.parse(fs.readFileSync(path.join(__dirname,'baseline-continuation-controls.json'),'utf8')).continuation;
   assert.equal(golden.case_ids.length,11);assert.equal(golden.metrics.length,84);assert.equal(golden.events.length,51);assert.equal(golden.municipality_codes.length,13);
   const ix=read('index-deep.json');let renderedMetrics=0,renderedEvents=0;
   for(const id of golden.case_ids){const row=ix.find(r=>r.id===id);assert(row);const detail=JSON.parse(fs.readFileSync(path.join(root,row.detail),'utf8'))[id];const html=await ui.content({view:'case',id,p:{}});assert(html.indexOf('id="results"')<html.indexOf('公募・採択の背景'));const summary=detail.claims.find(c=>c.claim_id.endsWith(':summary'));assert(summary);const firstMetric=detail.metrics[0];if(firstMetric)assert(html.indexOf(summary.claim_id)<html.indexOf(firstMetric.metric_id));for(const c of detail.claims.filter(c=>c.section==='result'&&c!==summary))assert(html.indexOf(summary.claim_id)<html.indexOf(c.claim_id));for(const m of detail.metrics){const g=golden.metrics.find(x=>x.id===m.metric_id);assert(g,m.metric_id);for(const k of ['value','unit','period','definition','phase'])assert.deepEqual(m[k],g[k],m.metric_id+':'+k);assert(html.includes(m.metric_id));assert(html.includes('id="source-'+m.source.document_id+'"'));assert(html.includes('section=source-'+m.source.document_id));renderedMetrics++;}for(const e of detail.events){const g=golden.events.find(x=>x.id===e.event_id);assert(g);assert.equal(e.date_label,g.date);assert.equal(e.phase,g.phase);renderedEvents++;}}
   assert.equal(renderedMetrics,84);assert.equal(renderedEvents,51);return {cases:11,metrics:renderedMetrics,events:renderedEvents,municipalities:13};
 });
 await check('Latest-batch entry preserves original featured cases and reaches every independently expected new/update case',async()=>{
   assert(batchControls,'Independent current-batch controls required');const ids=batchControls.current_case_ids,rows=read('index-deep.json'),found=ui.filter(rows,{batch:'latest'});assert.deepEqual(Array.from(found,r=>r.id).sort(),ids);assert.deepEqual(Array.from(ui.filter(rows,{batch:'continuation'}),r=>r.id).sort(),ids);
   const home=await ui.content({view:'home',id:'',p:{}});for(const id of ['NORTH-R-01','central_toyono_ai','central_tottori_torimobi','west-44211-15'])assert(home.includes(id));assert(home.includes('batch=latest'));
   const seen=new Set();for(let page=1;page<=Math.ceil(ids.length/12);page++){const html=await ui.content({view:'projects',id:'',p:{batch:'latest',page:String(page)}});[...html.matchAll(/data-record-id="([^"]+)"/g)].forEach(m=>seen.add(m[1]));assert(html.includes('name="batch"'));assert(html.includes('全国の案件総数ではありません'));}
   assert.deepEqual([...seen].sort(),ids);const summary=read('summary.json');assert.equal(summary.current_batch.new_cases,batchControls.new_case_ids.length);assert.equal(summary.current_batch.updated_cases,batchControls.updated_case_ids.length);return {latest_cases:ids.length,new:batchControls.new_case_ids.length,updates:batchControls.updated_case_ids.length};
 });
 await check('Prior published detailed/legacy snapshots stay byte-identical; cumulative ledger metrics and phases match independent controls',async()=>{
   assert(batchControls);for(const [file,hash] of Object.entries(batchControls.previous_file_hashes))assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex'),hash,file);
   const rows=read('index-deep.json');let metrics=0,events=0;
   for(const id of batchControls.case_ids){const row=rows.find(r=>r.id===id);assert(row);const detail=JSON.parse(fs.readFileSync(path.join(root,row.detail),'utf8'))[id];for(const m of detail.metrics){const golden=batchControls.metrics.find(x=>x.metric_id===m.metric_id);assert(golden);for(const k of ['value','unit','period','definition','phase','verification'])assert.deepEqual(m[k],golden[k]);metrics++;}for(const e of detail.events){const golden=batchControls.events.find(x=>x.event_id===e.event_id);assert(golden);assert.equal(e.date_label,golden.date_label);assert.equal(e.phase,golden.phase);assert.equal(Boolean(e.evidence_conflict),Boolean(golden.evidence_conflict));if(golden.evidence_conflict){assert.equal(e.original_phase,golden.original_phase);const html=await ui.content({view:'case',id,p:{}});assert(html.includes('原典間の相違あり・確定実績として扱わない'));assert(!detail.last_documented_event?.evidence_conflict);}events++;}}
   assert.equal(metrics,batchControls.metrics.length);assert.equal(events,batchControls.events.length);for(const id of batchControls.updated_case_ids){const legacy=await ui.content({view:'record',id,p:{layer:'legacy'}});assert(legacy.includes('最新の結果詳査・旧記録との照合'));const html=await ui.content({view:'case',id,p:{}});assert(html.includes('新規事業として数えません'));}
   return {snapshots:Object.keys(batchControls.previous_file_hashes).length,metrics,events};
 });
 await check('Every selection, reference, review and local record screen renders',async()=>{
   let rendered=0;for(const layer of ['selection','reference','review','local','history'])for(const r of read('index-'+layer+'.json')){const html=await ui.content({view:'record',id:r.id,p:{layer}});assert(html.includes(r.id));assert(!html.includes('undefined'));rendered++;}return {rendered};
 });
 await check('Official report classification remains separate from result evidence',async()=>{
   const counts={};for(const row of read('index-review.json'))counts[row.evidence]=(counts[row.evidence]||0)+1;
   assert.deepEqual(counts,{outcome_result:153,outcome_not_obtained:186,partial_implementation_result:1,termination_only:1,study_result:1,interim_result:1});
   const corrections=read('classification-corrections.json');assert.equal(corrections.length,343);
   const ix=read('index-selection.json');for(const o of corrections){const row=ix.find(x=>x.id===o.target_selection_record_id);assert(row);const r=JSON.parse(fs.readFileSync(path.join(root,row.detail),'utf8'))[row.id];assert.equal(r.classification_correction.overlay_id,o.overlay_id);}
   return {counts};
 });
 await check('Review event sources all have matching visible source anchors',async()=>{
   let refs=0;for(const row of read('index-review.json')){const r=JSON.parse(fs.readFileSync(path.join(root,row.detail),'utf8'))[row.id];const html=await ui.content({view:'record',id:row.id,p:{layer:'review'}});for(const ev of r.events){assert(html.includes('id="source-'+ev.source_id+'"'),ev.source_id);refs++;}}assert.equal(refs,216);return {refs};
 });
 await check('Result context, evaluation, challenges and target gaps appear on every reviewed detail',async()=>{
   let checked=0;for(const row of read('index-review.json')){const r=JSON.parse(fs.readFileSync(path.join(root,row.detail),'utf8'))[row.id];const html=await ui.content({view:'record',id:row.id,p:{layer:'review'}});for(const k of ['result_context','user_evaluation','challenges','target_gap']){if(typeof r[k]==='string'&&r[k]){const escaped=r[k].replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));assert(html.includes(escaped),row.id+':'+k);checked++;}}}return {checked};
 });
 await check('Filters return exact input memberships and keep training separate',async()=>{
   const rows=read('index-deep.json');for(const prop of ['pref','year','theme','state','evidence','municipality']){
     const field={pref:'prefectures',year:'years',theme:'themes',municipality:'codes'}[prop]||prop;const values=new Set(rows.flatMap(r=>r[field]));
     for(const value of values){const got=ui.filter(rows,{[prop]:value});const expected=rows.filter(x=>Array.isArray(x[field])?x[field].includes(value):x[field]===value);assert.deepEqual(Array.from(got,x=>x.id),expected.map(x=>x.id));}}
   assert.equal(ui.filter(read('index-selection.json'),{state:'training'}).length,339);
   assert.equal(ui.filter(read('index-review.json'),{evidence:'outcome_result'}).length,153);
   const masters=read('municipalities.json');assert.equal(masters.length,1741);const misato=masters.filter(x=>x.municipality_name==='美里町');assert(misato.length>1);const found=ui.filter(rows,{municipality:'43348'},masters);assert(found.every(r=>r.codes.includes('43348')));
 });
 await check('Pagination reaches every selection and reference without truncation',async()=>{
   for(const layer of ['selection','reference','review','history']){const rows=read('index-'+layer+'.json'),seen=new Set();for(let page=1;page<=Math.ceil(rows.length/12);page++){const html=await ui.content({view:'records',id:'',p:{layer,page:String(page)}});const ids=[...html.matchAll(/data-record-id="([^"]+)"/g)].map(m=>m[1]);assert(ids.length<=12);ids.forEach(x=>{assert(!seen.has(x));seen.add(x);});}assert.equal(seen.size,rows.length);}
 });
 await check('Plans do not become results; corrected cross-year rates and latency denominator stay intact',async()=>{
   const html=await ui.content({view:'case',id:'west-45203-17',p:{}});assert(html.includes('年度が異なるため達成率は計算しない'));const results=html.split('id="results"')[1].split('id="changes"')[0];assert(!results.includes('29.4%相当（計算）'));assert(html.includes('訂正前：'));
   const saga=await ui.content({view:'case',id:'west-41201-07',p:{}});assert(saga.includes('25/35'));assert(saga.includes('35測定ポイント')||saga.includes('25/35'));
   const tarama=await ui.content({view:'case',id:'west-47375-20',p:{}});assert(tarama.includes('再開'));assert(tarama.includes('別'));
 });
 await check('Public projections have no Drive links, private input ids, credentials, external scripts or source maps',async()=>{
   const scan=dir=>fs.readdirSync(dir,{withFileTypes:true}).flatMap(d=>d.isDirectory()?scan(path.join(dir,d.name)):[path.join(dir,d.name)]);
   for(const p of scan(path.join(root,'data'))){const s=fs.readFileSync(p,'utf8');assert(!/https?:\/\/(?:drive|docs)\.google\.com/.test(s),p);const manifest=path.resolve(repo,'../inputs/manifest.json');if(fs.existsSync(manifest))for(const f of JSON.parse(fs.readFileSync(manifest,'utf8')))assert(!s.includes(f.id),p);assert(!/-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|github_pat_|ghp_[A-Za-z0-9]{30}/.test(s),p);}
   const html=fs.readFileSync(path.join(root,'index.html'),'utf8');assert(!/<script[^>]+src="https?:/i.test(html));assert(!/<iframe|\.map"/.test(html));
 });
 await check('Default data requests stay below 100KB and never load raw 24MB JSON',async()=>{
   const ix=fs.statSync(path.join(root,'data/index-deep.json')).size;const boot=fs.statSync(path.join(root,'data/bootstrap.js')).size;const classification=context.window.MOBILITY_RESULTS_SUMMARY.classification?fs.statSync(path.join(root,'data/classification/deep.json')).size:0;assert(ix+boot+classification<100000);const source=fs.readFileSync(path.join(root,'assets/results.js'),'utf8');assert(!source.includes('統合拡張データ_20261101.json'));return {bootstrap_plus_deep_index_bytes:ix+boot,classification_bytes:classification,total_initial_data_bytes:ix+boot+classification};
 });
 await check('Oversized number emphasis preserves original text, units and dates',async()=>{
   const values=['予約1,979件、延べ乗車2,190人、乗合284件。','報告書支出計9,724,321円、収支率6.36%。','2024-10-15〜2025-02-11、毎日9:00〜16:30','R4年度115人/日。R5年度26人/日。','2023年実績2,645乗車。2025年目標9,000乗車。','<script> & "quoted" 17.1%'];
   for(const value of values){const html=ui.numberMarkup(value);const decoded=html.replace(/<[^>]+>/g,'').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&amp;/g,'&');assert.equal(decoded,value);}
   for(const [id,count] of [['NORTH-R-01',3],['central_toyono_ai',3],['central_tottori_torimobi',3],['west-44211-15',1]]){const row=read('index-deep.json').find(r=>r.id===id),c=JSON.parse(fs.readFileSync(path.join(root,row.detail),'utf8'))[id];const html=ui.resultFigures(c,{});assert.equal([...html.matchAll(/class="m-figure-value"/g)].length,count);for(const m of html.matchAll(/class="m-figure-value">([^<]+)/g))assert(c.claims.some(x=>x.statement.includes(m[1])));}
 });
 await check('Release query is synchronized across both pages, bootstrap and data requests; stale counts fail closed',async()=>{
   const release=context.window.MOBILITY_RESULTS_SUMMARY.release;assert(release,'bootstrap release is required for deployment');
   for(const page of ['municipal-mobility-history','mobility-policy-history']){const html=fs.readFileSync(path.join(repo,page,'index.html'),'utf8');for(const asset of ['data/bootstrap.js','assets/results.js']){const refs=[...html.matchAll(/<script[^>]+src="([^"]+)"/g)].map(m=>m[1]).filter(u=>u.split('?')[0].endsWith(asset));assert.equal(refs.length,1,page+':'+asset);assert.equal(new URLSearchParams(refs[0].split('?')[1]).get('v'),release);}}
   assert(requestedUrls.length>0);for(const u of requestedUrls)assert.equal(new URLSearchParams(u.split('?')[1]).get('v'),release,u);
   assert.equal(new URLSearchParams(ui.releaseUrl('verification/data-reconciliation.json').split('?')[1]).get('v'),release);
   assert.throws(()=>ui.validateData('index-deep.json',Array(72)),/版が一致/);assert.throws(()=>ui.validateData('summary.json',{counts:{deep:72}}),/版が一致/);
   assert.equal(ui.validateData('index-deep.json',Array(expected.deep)).length,expected.deep);return {release,request_count:requestedUrls.length};
 });
 const report={passed:results.filter(x=>x.result==='pass').length,failed:results.filter(x=>x.result==='fail').length,checks:results};fs.writeFileSync(path.join(__dirname,'acceptance-results.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));if(report.failed)process.exitCode=1;
})();
