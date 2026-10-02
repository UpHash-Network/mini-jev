// Capture the actual static Explorer UI. No model, API key, or dataset text.
// Requires Playwright with installed Chromium. Serve docs on localhost first.
const {chromium}=require('playwright');
const fs=require('node:fs/promises'), path=require('node:path');
(async()=>{
 const root=process.cwd(), out=path.resolve(process.argv[2]||'work/revision_20261002/capture');
 await fs.mkdir(out,{recursive:true});
 const browser=await chromium.launch({headless:true});
 const context=await browser.newContext({viewport:{width:1280,height:640},deviceScaleFactor:1,recordVideo:{dir:out,size:{width:1280,height:640}},acceptDownloads:true});
 const page=await context.newPage(), events=[], errors=[];
 page.on('pageerror', e=>errors.push(e.message));
 const start=performance.now();
 const mark=(name)=>{const e={name,seconds:(performance.now()-start)/1000}; events.push(e); console.log(JSON.stringify(e));};
 async function hold(n){await page.waitForTimeout(n*1000);}
 async function scroll(selector){await page.locator(selector).evaluate(el=>el.scrollIntoView({block:'start',behavior:'instant'}));}
 async function shot(name){await page.screenshot({path:path.join(out,name+'.png')});}
 await page.goto(process.env.EXPLORER_URL||'http://127.0.0.1:18879/explorer/');
 await page.getByText('Panel SHA-256 verified against the published index.',{exact:false}).waitFor();
 mark('overview'); await shot('01-overview'); await hold(7);
 await page.getByRole('button',{name:'Same item, different decision',exact:false}).click();
 mark('order-comparison'); await shot('02-order'); await hold(9);
 await scroll('#probabilities'); mark('order-probabilities'); await shot('03-probabilities'); await hold(9);
 await page.getByRole('button',{name:'More calls can be worse',exact:false}).click();
 mark('averaging-comparison'); await shot('04-averaging'); await hold(10);
 await scroll('#probabilities'); mark('averaging-reference'); await shot('05-reference'); await hold(8);
 await page.getByText('Trace this comparison to the source records',{exact:true}).click();
 await scroll('#provenance'); mark('source-trace'); await shot('06-source'); await hold(10);
 await page.getByRole('button',{name:'Download this comparison',exact:false}).scrollIntoViewIfNeeded();
 const downloaded=page.waitForEvent('download'); await page.getByRole('button',{name:'Download this comparison',exact:false}).click();
 const file=await downloaded; await file.saveAs(path.join(out,'comparison.json'));
 mark('export'); await shot('07-export'); await hold(5);
 await page.getByRole('button',{name:'Expected score is not the mode',exact:false}).click();
 await page.locator('#item-context').filter({hasText:'jsts:valid:1054'}).waitFor(); await scroll('#comparison'); mark('score'); await shot('08-score'); await hold(10);
 // An unmodified element screenshot for the paper, showing all metrics/bars/reference.
 await page.locator('#comparison').screenshot({path:path.join(out,'08-score-full.png')});
 await page.getByRole('button',{name:'Concentrated labels need context',exact:false}).click();
 mark('collapse-comparison'); await hold(6);
 await scroll('#reference'); mark('full-panel'); await shot('09-panel'); await hold(10);
 await page.getByRole('button',{name:'Next item',exact:true}).click();
 await page.getByText('Answer frequencies across this full panel',{exact:true}).click(); await scroll('#reference'); mark('next-item-same-panel'); await shot('10-next'); await hold(6);
 await page.getByText('Scope, example selection, and reproducibility',{exact:true}).click();
 await scroll('#methodology'); mark('scope'); await shot('11-scope'); await hold(6);
 mark('end');
 const video=page.video();await context.close();const vp=await video.path();await browser.close();
 await fs.writeFile(path.join(out,'capture.json'),JSON.stringify({viewport:[1280,640],events,errors,video:path.basename(vp),download:'comparison.json',scope:'Real browser interactions with saved records; no new inference; illustrative outcome-selected examples, not a user study.'},null,2)+'\n');
 if(errors.length)throw new Error(errors.join('\n'));
})();
