// Verify the newly linked complete-JSON route using real browser navigation.
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const {chromium}=require('playwright');
const args=process.argv.slice(2),get=(k,d)=>args.includes(k)?args[args.indexOf(k)+1]:d;
const base=get('--base','http://127.0.0.1:18880/docs/'),out=get('--out','work/workflow-routes-new');
if(fs.existsSync(out))throw Error('Refusing to overwrite earlier output');fs.mkdirSync(out,{recursive:true});
const tasks=JSON.parse(fs.readFileSync(path.join(__dirname,'../workflow_comparison_20261002/tasks.json'))).tasks;
(async()=>{
 const browser=await chromium.launch({headless:true}),page=await browser.newPage();
 const errors=[],checks=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  for(const width of [1440,390]){
   await page.setViewportSize({width,height:1000});
   const task=tasks[width===1440?2:5];
   await page.goto(base+'explorer/?routecheck='+width+'#'+task.explorer_fragment);
   await page.waitForFunction(()=>document.querySelector('#status')?.textContent.includes('Panel SHA-256 verified'));
   const original=new URL(page.url()).hash;
   await page.locator('#json-view').click();
   await page.waitForFunction(()=>document.querySelector('#status')?.textContent.includes('Panel SHA-256 verified'));
   assert.equal(new URL(page.url()).hash,original);
   const record=JSON.parse(await page.locator('#comparison').textContent());
   const expected=JSON.parse(task.evidence_json).comparison_export;
   for(const key of ['conditions','candidate_comparison','sources','physical_members','shared_physical_calls','unique_physical_calls'])assert.deepEqual(record[key],expected[key]);
   const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);assert.equal(overflow,false);
   await page.screenshot({path:path.join(out,'json-'+width+'.png')});
   await page.locator('#explorer').click();
   await page.waitForFunction(()=>document.querySelector('#status')?.textContent.includes('Panel SHA-256 verified'));
   assert.equal(new URL(page.url()).hash,original);
   assert.equal(await page.locator('#item').inputValue(),task.selection.item);
   await page.screenshot({path:path.join(out,'explorer-'+width+'.png')});
   checks.push({width,case:task.id,selection_preserved_both_directions:true,comparison_fields_exact:true,json_horizontal_overflow:false});
  }
  assert.deepEqual(errors,[]);
  const report={status:'pass',base,checked_at_utc:new Date().toISOString(),checks,page_errors:errors};
  fs.writeFileSync(path.join(out,'ROUTE_CHECK.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
 }finally{await browser.close();}
})();
