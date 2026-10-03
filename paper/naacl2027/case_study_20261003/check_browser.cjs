// Replays saved observations through the public importer. No model execution.
const {chromium, firefox} = require('playwright');
const fs = require('fs');
const path = require('path');
const http = require('http');
const assert = require('assert/strict');
const crypto = require('crypto');
const here = __dirname, root = path.resolve(here, '../../..');
const docs = path.join(root, 'docs');
const mime = {'.html':'text/html; charset=utf-8','.mjs':'application/javascript; charset=utf-8','.js':'application/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.md':'text/plain; charset=utf-8'};
const server = http.createServer((req,res) => {
  let pathname = decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  if (pathname.endsWith('/')) pathname += 'index.html';
  const file = path.resolve(docs, '.'+pathname);
  if (!file.startsWith(docs+path.sep) || !fs.existsSync(file)) {res.writeHead(404);res.end();return;}
  res.writeHead(200, {'Content-Type':mime[path.extname(file)]||'application/octet-stream'});fs.createReadStream(file).pipe(res);
});
const softmax = z => {const e=z.map(x=>Math.exp(x-Math.max(...z)));const sum=e.reduce((a,b)=>a+b,0);return e.map(x=>x/sum);};
(async()=>{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const url=`http://127.0.0.1:${server.address().port}/explorer/import/`;
  const rows=fs.readFileSync(path.join(here,'diagnostic_import.jsonl'),'utf8').trim().split('\n').map(JSON.parse);
  const byItem=new Map();for(const row of rows){if(!byItem.has(row.item_id))byItem.set(row.item_id,[]);byItem.get(row.item_id).push(row);}
  const out=path.join(here,'verification');fs.mkdirSync(out,{recursive:true});const results=[];
  for (const [name,type] of [['chromium',chromium],['firefox',firefox]]) {
    const browser=await type.launch({headless:true});
    try {
      const context=await browser.newContext({viewport:{width:1360,height:1000},acceptDownloads:true});
      const page=await context.newPage();const errors=[],requests=[];
      page.on('pageerror',e=>errors.push(String(e)));await page.goto(url);await page.waitForLoadState('networkidle');
      page.on('request',r=>requests.push(r.url()));
      await page.locator('#file').setInputFiles(path.join(here,'diagnostic_import.jsonl'));
      await page.locator('#workspace').waitFor({state:'visible'});
      assert.match(await page.locator('#status').innerText(),/48 physical records across 12/);
      const options=await page.locator('#group option').evaluateAll(nodes=>nodes.map(x=>({value:x.value,text:x.textContent})));
      const cases=[];
      for(const option of options){
        await page.locator('#group').selectOption(option.value);
        const item=[...byItem.keys()].find(key=>option.text.includes(key+' ('));assert(item);
        for(const pair of [['diagnostic_last_position_only','diagnostic_stock_full_position'],['repeat_stock_full_position_a','repeat_stock_full_position_b']]) {
          await page.locator('#a').selectOption({label:pair[0]});await page.locator('#b').selectOption({label:pair[1]});
          await page.waitForTimeout(1100); // Pace separate user download actions; not a timing benchmark.
          const downloadP=page.waitForEvent('download');await page.locator('#download').click();const download=await downloadP;
          const saved=path.join(out,`${name}-${item}-${pair[0]}.json`);await download.saveAs(saved);
          const comparison=JSON.parse(fs.readFileSync(saved,'utf8'));
          const sourceA=byItem.get(item).find(r=>r.condition===pair[0]),sourceB=byItem.get(item).find(r=>r.condition===pair[1]);
          assert.deepEqual(comparison.source_records,[sourceA,sourceB]);
          const logitsA=sourceA.logits,logitsB=sourceB.logits;
          const pa=softmax(logitsA),pb=softmax(logitsB);let maxError=0;
          for(const c of comparison.candidates){const ai=sourceA.candidate_keys.indexOf(c.key),bi=sourceB.candidate_keys.indexOf(c.key);maxError=Math.max(maxError,Math.abs(c.a-pa[ai]),Math.abs(c.b-pb[bi]),Math.abs(c.delta-(pb[bi]-pa[ai])));}
          assert(maxError<1e-12);assert.equal(comparison.label_changed,false);assert.equal(comparison.reference,null);
          assert.equal(comparison.a.recorded_latency_ms,null);assert.equal(comparison.b.recorded_latency_ms,null);
          assert.match(await page.locator('#reference').innerText(),/Reference unknown/);
          const maxDelta=Math.max(...comparison.candidates.map(c=>Math.abs(c.delta)));
          if(pair[0].startsWith('repeat'))assert.equal(maxDelta,0);
          cases.push({item,pair,max_delta:maxDelta,largest_delta_display:await page.locator('#metrics').innerText(),export_numeric_max_error:maxError,source_records_exact:true});
          if(item==='synthetic-choice-1' && pair[0].startsWith('diagnostic')){
            await page.locator('#workspace').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(out,`${name}-failure.png`),fullPage:true});
          }
        }
      }
      assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);
      results.push({browser:name,version:browser.version(),records:rows.length,groups:options.length,comparisons:cases.length,cases,page_errors:errors,post_load_requests:requests});
    } finally {await browser.close();}
  }
  fs.writeFileSync(path.join(here,'BROWSER_CHECKS.json'),JSON.stringify({passed:true,scope:'AI/software replay of retained observations; no new inference or human usability measurement',fixture_sha256:crypto.createHash('sha256').update(fs.readFileSync(path.join(here,'diagnostic_import.jsonl'))).digest('hex'),results},null,2)+'\n');
  console.log(JSON.stringify({passed:true,browsers:results.map(r=>r.browser),comparisons:results.reduce((n,r)=>n+r.comparisons,0)}));
})().catch(e=>{console.error(e);process.exitCode=1;}).finally(()=>server.close());
