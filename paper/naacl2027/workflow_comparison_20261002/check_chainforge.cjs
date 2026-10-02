// Actual unmodified ChainForge GUI import/table/search/export check, not a user study.
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto');
const {chromium}=require('playwright');
const here=__dirname,args=process.argv.slice(2),get=(k,d)=>args.includes(k)?args[args.indexOf(k)+1]:d;
const out=path.resolve(get('--out','work/chainforge-browser-new'));
const fixture=path.resolve(get('--fixture',path.join(here,'competitor/logittrail-frozen-evidence.cfzip')));
const tasks=JSON.parse(fs.readFileSync(path.join(here,'tasks.json'))).tasks;
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
if(fs.existsSync(out))throw Error('Refusing to overwrite earlier output');fs.mkdirSync(out,{recursive:true});
(async()=>{
 const browser=await chromium.launch({headless:false,channel:'chrome'});
 const page=await browser.newPage({viewport:{width:1600,height:1100},acceptDownloads:true});
 const errors=[],requests=[];page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>{if(r.method()!=='GET')requests.push({url:r.url(),method:r.method()});});
 try{
  await page.goto(get('--url','http://127.0.0.1:18881/'),{waitUntil:'networkidle'});
  const chooser=page.waitForEvent('filechooser');await page.getByRole('button',{name:'Import',exact:true}).click();await (await chooser).setFiles(fixture);
  const inspector=page.locator('[data-id="condition_inspector"]');await inspector.waitFor();
  await page.waitForFunction(()=>document.querySelector('[data-id="condition_inspector"]')?.innerText.includes('option_3'));
  const grip=await inspector.getByTitle('Drag to resize',{exact:true}).boundingBox();
  await page.mouse.move(grip.x+8,grip.y+8);await page.mouse.down();await page.mouse.move(1530,940,{steps:12});await page.mouse.up();
  const search=inspector.locator('input[placeholder="Search responses"]:visible');
  const cases=[];
  for(const task of tasks){
   await search.fill('"task_id": "'+task.id+'"');
   await page.waitForFunction(id=>{const e=document.querySelector('[data-id="condition_inspector"] tbody');return e?.innerText.includes(id)&&!e.innerText.includes(id==='W01'?'W02':'W01');},task.id);
   const text=await inspector.innerText();assert.ok(text.includes(task.selection.item));
   for(const side of ['a','b']){assert.ok(text.includes('"side": "'+side+'"'));assert.ok(text.includes('"label": "'+task.expected_answers.basic_typed_decision[side].label+'"'));}
   const lightboxChecks=[];
   for(let i=0;i<2;i++){
    await inspector.locator('.cf-table-resp-text').nth(i).click();
    const dialog=page.locator('[role="dialog"]:visible');await dialog.waitFor();
    const raw=await dialog.locator('[style*="white-space: pre-wrap"]').first().textContent();
    const record=JSON.parse(raw),e=JSON.parse(task.evidence_json).comparison_export;
    assert.equal(record.task_id,task.id);assert.deepEqual(record.condition,e.conditions[record.side]);assert.deepEqual(record.sources,e.sources);
    lightboxChecks.push({side:record.side,complete_compact_response_json_exact:true});
    if(i===0&&['W03','W06'].includes(task.id))await page.screenshot({path:path.join(out,task.id+'-chainforge-fulltext.png')});
    await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});
   }
   assert.deepEqual(lightboxChecks.map(x=>x.side).sort(),['a','b']);
   await page.screenshot({path:path.join(out,task.id+'-chainforge.png')});
   fs.writeFileSync(path.join(out,task.id+'-visible.txt'),text);
   cases.push({id:task.id,search_filtered_actual_inspector:true,matching_item_and_two_conditions_visible:true,probability_named_scores_present:true,exact_response_text_available:true,lightbox_checks:lightboxChecks,notes:'Native table/filter with adapter-supplied labels, typed values, named candidate scores and compact fullprecision response text. Derived differences/call unions were supplied, not recomputed by ChainForge.'});
  }
  await search.fill('');
  const dl=page.waitForEvent('download');await inspector.getByRole('button',{name:'Export data',exact:true}).click();const spreadsheet=await dl;await spreadsheet.saveAs(path.join(out,'conditions.xlsx'));
  const full=page.waitForEvent('download');await page.getByRole('button',{name:'Export',exact:true}).click();const flow=await full;const flowPath=path.join(out,'exported.cforge');await flow.saveAs(flowPath);
  const exported=JSON.parse(fs.readFileSync(flowPath));const strings=exported.cache.__s??[];
  const resolve=x=>typeof x==='number'?strings[x]:x;
  const complete=exported.cache['frozen_complete.json'];assert.equal(complete.length,6);
  const fullChecks=[];for(let i=0;i<6;i++){const raw=resolve(complete[i].responses[0]);assert.equal(raw,tasks[i].evidence_json);fullChecks.push({id:tasks[i].id,sha256:sha(Buffer.from(raw)),exact:true});}
  const compact=exported.cache['frozen_conditions.json'];assert.equal(compact.length,12);
  for(const row of compact){const record=JSON.parse(resolve(row.responses[0])),task=tasks.find(t=>t.id===record.task_id),e=JSON.parse(task.evidence_json).comparison_export;assert.deepEqual(record.condition,e.conditions[record.side]);assert.deepEqual(record.candidate_comparison,e.candidate_comparison);assert.deepEqual(record.sources,e.sources);}
  const report={status:'pass',checked_at_utc:new Date().toISOString(),browser_version:browser.version(),browser:'Installed Google Chrome, headed, fresh profile',fixture:path.basename(fixture),fixture_sha256:sha(fs.readFileSync(fixture)),tasks_sha256:sha(fs.readFileSync(path.join(here,'tasks.json'))),cases,complete_payload_flow_export:fullChecks,compact_records_exact:12,spreadsheet_downloaded:true,spreadsheet_numeric_verification:'See separately generated SPREADSHEET_CHECK.json',page_errors:errors,non_get_requests:requests,human_participants:0,new_model_calls:0,scope:'Finite imported frozen-evidence workflow. This does not test Ollama decision inference or establish GUI superiority/human efficiency. Generic import/visualization is real; adapter-derived values are not native computation. Full evidence is accessed through flow export/common payload rather than inferred from visible compact rows.'};
  fs.writeFileSync(path.join(out,'CHAINFORGE_RESULTS.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({status:'pass',cases:cases.length,fullPayloadsExact:fullChecks.length,compactRowsExact:12,pageErrors:errors}));
 }catch(e){fs.writeFileSync(path.join(out,'FAILURE.json'),JSON.stringify({error:String(e),errors},null,2));await page.screenshot({path:path.join(out,'failure.png')}).catch(()=>{});throw e;}
 finally{await browser.close();}
})();
