// Re-capture the actual, unchanged Explorer DOM; no CSS, image or data editing.
// Run from repository root with docs/ served at 127.0.0.1:18884.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { chromium } = require('playwright');
const sha = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const output = 'paper/naacl2027/figures/evidence-explorer.png';
const receiptPath = 'paper/naacl2027/revision_20261003_raw/FIGURE_CAPTURE.json';
const selection = { study: 'presentation_robustness', model: 'qwen3.6-35b-a3b', dataset: 'JCoLA', item: 'jcola:in_domain_valid:1030', a: 'baseline', b: 'display_reverse' };
const url = 'http://127.0.0.1:18884/explorer/#' + new URLSearchParams(selection);

(async () => {
  if (fs.existsSync(receiptPath)) throw Error('Refusing to overwrite capture receipt');
  const priorSha = sha(output);
  const browser = await chromium.launch();
  try {
    const page = await browser.newPage({ viewport: { width: 1600, height: 1400 }, deviceScaleFactor: 2 });
    const errors = [];
    page.on('pageerror', error => errors.push(String(error)));
    await page.goto(url);
    await page.locator('#workspace').waitFor({ state: 'visible' });
    await page.getByText('Panel SHA-256 verified against the published index.', { exact: false }).waitFor();
    await page.evaluate(() => document.fonts.ready);
    const actual = await page.evaluate(() => Object.fromEntries(new URLSearchParams(location.hash.slice(1))));
    if (JSON.stringify(actual) !== JSON.stringify(selection)) throw Error('Unexpected source selection');
    await page.locator('#comparison').scrollIntoViewIfNeeded();
    const geometry = await page.locator('#comparison').evaluate(root => {
      const plain = r => ({ x: r.x + scrollX, y: r.y + scrollY, width: r.width, height: r.height, right: r.right + scrollX, bottom: r.bottom + scrollY });
      const rectangles = [plain(root.getBoundingClientRect())];
      for (const element of root.querySelectorAll('*')) {
        if (!element.checkVisibility({ visibilityProperty: true })) continue;
        for (const rect of element.getClientRects()) if (rect.width && rect.height) rectangles.push(plain(rect));
      }
      // Text may extend past its containing element; include actual glyph ranges.
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      while (walker.nextNode()) {
        if (!walker.currentNode.textContent.trim() || !walker.currentNode.parentElement.checkVisibility({ visibilityProperty: true })) continue;
        const range = document.createRange(); range.selectNodeContents(walker.currentNode);
        for (const rect of range.getClientRects()) if (rect.width && rect.height) rectangles.push(plain(rect));
      }
      const left = Math.min(...rectangles.map(r => r.x)), top = Math.min(...rectangles.map(r => r.y));
      const right = Math.max(...rectangles.map(r => r.right)), bottom = Math.max(...rectangles.map(r => r.bottom));
      return { root: plain(root.getBoundingClientRect()), content: { left, top, right, bottom }, rectangles: rectangles.length,
        deltas: [...root.querySelectorAll('.delta')].map(e => ({ text: e.innerText, rect: plain(e.getBoundingClientRect()) })),
        document_width: document.documentElement.scrollWidth, viewport_width: innerWidth };
    });
    const padding = 12;
    const clip = { x: Math.max(0, Math.floor(geometry.content.left) - padding), y: Math.max(0, Math.floor(geometry.content.top)),
      width: Math.ceil(geometry.content.right) - Math.max(0, Math.floor(geometry.content.left) - padding) + padding,
      height: Math.ceil(geometry.content.bottom) - Math.max(0, Math.floor(geometry.content.top)) + 6 };
    if (clip.x + clip.width > 1600) throw Error('Content exceeds the widened viewport');
    if (geometry.deltas.length !== 2 || errors.length) throw Error('Incomplete comparison or runtime error');
    const png = await page.screenshot({ clip, fullPage: true, animations: 'disabled', caret: 'hide' });
    if (png.readUInt32BE(16) !== clip.width * 2 || png.readUInt32BE(20) !== clip.height * 2) throw Error('Screenshot dimensions clipped to viewport');
    fs.writeFileSync(output, png);
    const homeChecks = [];
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 1100 });
      await page.goto('http://127.0.0.1:18884/');
      await page.evaluate(() => document.fonts.ready);
      homeChecks.push(await page.evaluate(() => ({ viewport: innerWidth, document_width: document.documentElement.scrollWidth,
        horizontal_overflow: document.documentElement.scrollWidth > innerWidth,
        public_links: [...document.querySelectorAll('a')].filter(a => /raw|workflow|json|record|compar/i.test(a.textContent)).map(a => ({ text: a.textContent.trim(), href: a.getAttribute('href') })) })));
    }
    const receipt = { schema_version: 1, captured_at_utc: new Date().toISOString(), selection, source_url: url,
      method: 'Actual Playwright browser screenshot of unchanged local docs. Clip contains comparison element and every visible descendant rectangle and text range, with 12 CSS px horizontal and 6 px bottom margin. Hidden content in closed details is excluded.',
      viewport: { width: 1600, height: 1400, device_scale_factor: 2 }, clip, geometry,
      source_files: Object.fromEntries(['docs/explorer/index.html','docs/explorer/app.js','docs/explorer/explorer.css'].map(file => [file, sha(file)])),
      previous_figure_sha256: priorSha, output, output_sha256: sha(output), png_pixels: { width: png.readUInt32BE(16), height: png.readUInt32BE(20) },
      screenshot_script: path.relative(process.cwd(), __filename), script_sha256: sha(__filename), browser_version: browser.version(),
      home_checks: homeChecks, page_errors: errors, image_edited: false, ui_or_data_changed: false, new_model_calls: 0,
      scope: 'Recorded observation re-captured without clipping; not a new model observation or human usability check.' };
    fs.writeFileSync(receiptPath, JSON.stringify(receipt, null, 2) + '\n');
    console.log(JSON.stringify({ receipt: receiptPath, output, pixels: receipt.png_pixels, clip, geometry, home_checks: homeChecks, sha256: receipt.output_sha256 }, null, 2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
