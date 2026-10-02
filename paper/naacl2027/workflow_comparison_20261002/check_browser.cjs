// Browser-level evidence access checks; no people, inference, or timing study.
// Requires Playwright and its Chromium runtime; run with a fresh output folder.
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto');
const {chromium}=require('playwright');
const here=__dirname, root=path.resolve(here,'../../..');
const args=process.argv.slice(2),get=(k,d)=>args.includes(k)?args[args.indexOf(k)+1]:d;
const out=path.resolve(get('--out','work/workflow-browser-new'));
const base=get('--base-url','http://127.0.0.1:18880');
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const tasksBytes=fs.readFileSync(path.join(here,'tasks.json'));
assert.equal(sha(tasksBytes),'d629475e55bdc8c5d35cfb813a982925e65485a6a21b27d0a34e0c4fefc829a7');
assert.equal(sha(fs.readFileSync(path.join(here,'protocol.json'))),'237ce0e6dc1dea51a0928d43a5167441e4b1dbf21d2438e806f80622d8d8bad0');
if(fs.existsSync(out))throw Error('Refusing to overwrite earlier browser check: '+out);
fs.mkdirSync(out,{recursive:true});
const tasks=JSON.parse(tasksBytes).tasks;
function eqExport(actual,expected){for(const k of ['conditions','candidate_comparison','physical_members','sources','mappings','archive','reference','model','canonical_keys','score_values','shared_physical_calls','unique_physical_calls'])assert.deepEqual(actual[k],expected[k],k);}
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const results=[];
 try{
  for(const task of tasks){
   const ev=JSON.parse(task.evidence_json),exp=task.expected_answers,record={id:task.id,questions:task.prompts.map(p=>p.id),presenters:{}};
   for(const [name,route] of [['logittrail','docs/explorer/'],['formatted_json','paper/naacl2027/inspection_audit_20261002/json_baseline.html'],['public_json','docs/explorer/json/']]){
    await page.goto(base+'/'+route+'?workflow_case='+task.id+'#'+task.explorer_fragment,{waitUntil:'networkidle'});
    await page.locator('#status').filter({hasText:'SHA-256 verified'}).waitFor();
    assert.equal(await page.locator('#item').inputValue(),task.selection.item);
    let exportRecord;
    if(name==='logittrail'){
     const d=page.waitForEvent('download');await page.locator('#download').click();const download=await d;
     const downloadPath=path.join(out,task.id+'-logittrail-export.json');await download.saveAs(downloadPath);exportRecord=JSON.parse(fs.readFileSync(downloadPath));
     const metricText=await page.locator('#metrics').innerText();
     assert.ok(metricText.includes(`${exp.physical_call_accounting.shared_calls} shared; ${exp.physical_call_accounting.union_calls} distinct calls`));
     assert.ok(metricText.includes('A '+exp.basic_typed_decision.a.label));assert.ok(metricText.includes('B '+exp.basic_typed_decision.b.label));
     const displayed=await page.locator('#probabilities .number').allTextContents();
     const expected=ev.comparison_export.candidate_comparison.flatMap(c=>[c.a,c.b]);
     assert.equal(displayed.length,expected.length);
     displayed.forEach((s,i)=>assert.ok(Math.abs(Number(s.replaceAll(',','').replace('%',''))/100-expected[i])<=5.1e-9));
     await page.getByText('Answer frequencies across this full panel',{exact:true}).click();
     const freq=await page.locator('#reference details').innerText();
     for(const key of ev.comparison_export.canonical_keys)assert.ok(freq.includes(`A: ${exp.full_panel_distribution.a.label_counts[key]}/200; B: ${exp.full_panel_distribution.b.label_counts[key]}/200`));
     await page.locator('#comparison').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,task.id+'-logittrail.png')});
     await page.getByText('Trace this comparison to the source records',{exact:true}).click();
     const prov=await page.locator('#provenance').innerText();
     for(const ref of exp.source_trace.physical_member_union){assert.ok(prov.includes(ref.member));assert.ok(prov.includes('line '+ref.line_1based));assert.ok(prov.includes(ref.member_sha256));}
     await page.locator('#provenance').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,task.id+'-source.png')});
     fs.writeFileSync(path.join(out,task.id+'-logittrail-visible.txt'),await page.locator('#workspace').innerText());
     record.presenters[name]={export_exact:true,visible_probability_rounding_verified:true,visible_labels_and_call_counts_verified:true,full_panel_counts_verified:true,source_member_line_hash_verified:true,rounding:'6 decimal places in displayed percentages; exact JSON export retained',scope:'No task-time, human correctness, or superiority result. Score expectation-mode gap requires subtraction; maximum label share/used-label count are in complete metadata or require arithmetic.'};
    }else{
     exportRecord=JSON.parse(await page.locator('#comparison').innerText());
     const descriptor=JSON.parse(await page.locator('#summary').innerText());assert.deepEqual(descriptor,ev.panel_descriptor);
     await page.getByText('Complete selected panel, including every source item',{exact:true}).click();
     assert.deepEqual(JSON.parse(await page.locator('#all-items').innerText()),ev.complete_panel);
     await page.getByText('Complete shared index, including all source definitions',{exact:true}).click();
     assert.deepEqual(JSON.parse(await page.locator('#index').innerText()),ev.complete_index);
     if(name==='formatted_json'){await page.locator('#comparison').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,task.id+'-json.png')});}
     record.presenters[name]={export_exact:true,complete_panel_exact:true,complete_index_exact:true,all_condition_summaries_exact:true,scope:'Native formatted-JSON access; mathematical interpretation or externally supplied derived fields are not human outcomes.'};
    }
    eqExport(exportRecord,ev.comparison_export);
   }
   results.push(record);console.log(task.id+' exact browser export and source access verified');
  }
  await page.setViewportSize({width:390,height:844});await page.goto(base+'/docs/explorer/json/',{waitUntil:'networkidle'});
  const mobileOverflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);assert.equal(mobileOverflow,false);
  assert.deepEqual(errors,[]);
  const report={status:'pass',date:new Date().toISOString(),protocol_sha256:sha(fs.readFileSync(path.join(here,'protocol.json'))),tasks_sha256:sha(tasksBytes),browser_version:browser.version(),browser_kind:'Playwright Chromium headless for LogitTrail and formattedJSON only',case_count:6,question_inventory_count:32,results,page_errors:errors,public_json_mobile_overflow:mobileOverflow,human_participants:0,new_model_calls:0,interpretation:'These are functional browser access and fidelity observations, not32 independent usability successes or superiority findings. ChainForge is checked in a separate actualChrome script.'};
  fs.writeFileSync(path.join(out,'BROWSER_RESULTS.json'),JSON.stringify(report,null,2)+'\n');
 }finally{await browser.close();}
})();
