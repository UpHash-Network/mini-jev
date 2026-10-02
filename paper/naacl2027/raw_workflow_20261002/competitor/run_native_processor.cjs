// Execute the supplied JavaScript through ChainForge's actual Processor UI.
// No evaluation function or result cache is injected into application state.
const fs=require('fs'),path=require('path'),assert=require('assert/strict'),crypto=require('crypto');
const {chromium,firefox}=require('playwright');
const args=process.argv.slice(2),get=(k,d)=>args.includes(k)?args[args.indexOf(k)+1]:d;
const here=__dirname;
const fixture=path.resolve(get('--fixture',path.join(here,'raw-records.cfzip')));
const out=path.resolve(get('--out','work/chainforge-raw-native-new'));
if(fs.existsSync(out))throw Error('Refusing to overwrite earlier outputs');
fs.mkdirSync(out,{recursive:true});
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const browserName=get('--browser','chrome');
if(!['chrome','firefox'].includes(browserName))throw Error('Expected --browser chrome or firefox');
const activate=async locator=>locator.press('Enter');
(async()=>{
 const browser=browserName==='firefox'?await firefox.launch({headless:true}):await chromium.launch({headless:false,channel:'chrome'});
 const page=await browser.newPage({viewport:{width:1600,height:1100},acceptDownloads:true});
 page.setDefaultTimeout(60000);
 const errors=[],requests=[],screenshots=[];
 page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>{if(r.method()!=='GET')requests.push({url:r.url(),method:r.method()});});
 async function exportFlow(filename){
  const [download]=await Promise.all([page.waitForEvent('download'),activate(page.getByRole('button',{name:'Export',exact:true}))]);
  const file=path.join(out,filename);await download.saveAs(file);
  return JSON.parse(fs.readFileSync(file));
 }
 try{
  await page.goto(get('--url','http://127.0.0.1:18883/'),{waitUntil:'networkidle'});
  const [chooser]=await Promise.all([page.waitForEvent('filechooser'),activate(page.getByRole('button',{name:'Import',exact:true}))]);
  await chooser.setFiles(fixture);
  await page.locator('[data-id="compute_raw"]').waitFor();
  const before=await exportFlow('before.cforge');
  // Native export emits {} for every uncached node; this is not a result.
  assert.deepEqual(before.cache['compute_raw.json']??{},{});
  const computeBefore=before.flow.nodes.find(n=>n.id==='compute_raw');
  assert.ok(!Object.hasOwn(computeBefore.data,'fields'));
  const source=before.flow.nodes.find(n=>n.id==='raw_input');
  const expectedIds=source.data.fields.map(f=>f.fill_history.case_id);
  assert.equal(new Set(expectedIds).size,expectedIds.length);
  const codeHash=sha(Buffer.from(computeBefore.data.code));
  const started=new Date().toISOString();
  // This keyboard event activates the normal visible Run button and its handler.
  await activate(page.locator('[data-id="compute_raw"]').getByRole('button',{name:'▶',exact:true}));
  await page.waitForFunction(ids=>{
   const text=document.querySelector('[data-id="result_inspect"]')?.innerText??'';
   return ids.every(id=>text.includes(id));
  },expectedIds,{timeout:120000});
  const visible=await page.locator('[data-id="result_inspect"]').innerText();
  fs.writeFileSync(path.join(out,'result-inspector-visible.txt'),visible);
  // A screenshot failure is recorded as an automation limitation, not a product defect.
  try{await page.screenshot({path:path.join(out,'computed-results.png'),timeout:5000});screenshots.push({file:'computed-results.png',status:'saved'});}
  catch(e){screenshots.push({file:'computed-results.png',status:'not_captured',error:String(e)});}
  const after=await exportFlow('after.cforge');
  assert.ok(Object.hasOwn(after.cache,'compute_raw.json'));
  const strings=after.cache.__s??[],resolve=x=>typeof x==='number'?strings[x]:x;
  const outputs=after.cache['compute_raw.json'].map(r=>JSON.parse(resolve(r.responses[0])));
  assert.deepEqual(outputs.map(o=>o.case_id).sort(),expectedIds.slice().sort());
  fs.writeFileSync(path.join(out,'computed_outputs.json'),JSON.stringify(outputs,null,2)+'\n');
  const report={schema_version:1,status:'pass',checked_at_utc:new Date().toISOString(),execution_started_utc:started,
   browser:browserName==='firefox'?'Playwright Firefox, headless, fresh profile, unmodified user agent':'Installed Google Chrome, headed, fresh profile',browser_version:browser.version(),
   fixture_sha256:sha(fs.readFileSync(fixture)),processor_sha256:codeHash,
   native_ui_activation:'Keyboard Enter on Import, Run and Export buttons; normal application handlers',
   source_input_count:expectedIds.length,output_count:outputs.length,case_ids:expectedIds,
   before_output_cache_empty:true,before_export_placeholder:'Native export returns {} for an uncached node',
   before_output_fields_absent:true,after_output_cache_populated:true,
   result_inspector_contains_all_case_identifiers:true,computed_outputs_sha256:sha(fs.readFileSync(path.join(out,'computed_outputs.json'))),
   before_flow_sha256:sha(fs.readFileSync(path.join(out,'before.cforge'))),after_flow_sha256:sha(fs.readFileSync(path.join(out,'after.cforge'))),
   numerical_correctness:'Separate independent oracle check required; browser execution alone does not establish correctness.',
   page_errors:errors,non_get_requests:requests,screenshots,new_model_calls:0,human_participants:0,
   scope:'Supplied custom diagnostic code executed in unmodified ChainForge JavaScript Processor; not a built-in domain-specific feature, human-efficiency measurement or model-inference experiment.'};
  fs.writeFileSync(path.join(out,'NATIVE_PROCESSOR_RUN.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({status:report.status,outputCount:outputs.length,beforeOutputEmpty:true,afterOutputPopulated:true,pageErrors:errors}));
 }catch(e){
  fs.writeFileSync(path.join(out,'FAILURE.json'),JSON.stringify({error:String(e),page_errors:errors,non_get_requests:requests},null,2));
  throw e;
 }finally{await browser.close();}
})();
