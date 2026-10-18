'use strict';
const {chromium,expect}=require('@playwright/test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const {createHash}=require('node:crypto');
const root=path.resolve(__dirname,'../..');
const report=fs.readFileSync(path.join(root,'content/daily/2026-10-18.show.html'),'utf8');
const expected=JSON.parse(fs.readFileSync(path.join(root,'content/assets/model328-2026-10-18/report-data.json'),'utf8'));
const host='https://dashboard.test/';
async function textOf(download){const stream=await download.createReadStream();let out='';for await(const chunk of stream)out+=chunk.toString('utf8');return out}
(async()=>{
 const browser=await chromium.launch({headless:true,channel:'chrome'}),results=[];
 try{
  for(const viewport of [{width:1440,height:960},{width:390,height:844}]){
   const page=await browser.newPage({viewport,acceptDownloads:true}),errors=[],requests=[];
   page.on('pageerror',e=>errors.push(e.message));
   await page.route('**/*',route=>{const url=route.request().url();requests.push(url);if(url.startsWith(host))return route.fulfill({contentType:'text/html',body:'<!doctype html><html><body style="margin:0"><iframe title="报告" sandbox="allow-scripts allow-downloads" style="display:block;border:0;width:100%;height:100vh"></iframe></body></html>'});return route.abort()});
   await page.goto(host+'#/daily/2026-10-18/show');
   await page.evaluate(fs.readFileSync(path.join(root,'site/js/router.js'),'utf8'));
   await page.evaluate(html=>document.querySelector('iframe').srcdoc=window.DashboardApp.prepareIsolatedHtml(html),report);
   const frame=page.frames().find(f=>f.parentFrame());
   await frame.waitForFunction(()=>document.body.dataset.reportReady==='true',{timeout:30000});
   await frame.addStyleTag({content:'html{scroll-behavior:auto!important}'});
   await expect(frame.locator('#all-results tbody tr')).toHaveCount(328);
   assert.equal(await frame.locator('#global-period option').count(),44);
   await frame.locator('#source-filter').selectOption('depth');
   await expect(frame.locator('#all-results tbody tr')).toHaveCount(24);
   await frame.locator('#side-filter').selectOption('buy');
   await expect(frame.locator('#factor-list .factor-item')).toHaveCount(12);
   await frame.locator('#factor-search').fill('dm01_exact');
   await expect(frame.locator('#all-results tbody tr')).toHaveCount(1);
   assert.equal(await frame.locator('#result-search').inputValue(),'dm01_exact');
   if(viewport.width===1440){
    const download=page.waitForEvent('download');await frame.locator('#download-results').click();const csv=await textOf(await download);
    assert(csv.includes('depth__dm01_exact_buy'));assert(csv.includes('4999'));assert(csv.includes('99.709294887451'));
    const full=page.waitForEvent('download');await frame.locator('#download-proof').click();assert.deepEqual(JSON.parse(await textOf(await full)),expected);
   }
   await frame.locator('[data-reset]').first().click();
   await expect(frame.locator('#all-results tbody tr')).toHaveCount(328);
   const definition=expected.features.find(f=>f.source==='cancel_buy'&&f.original_column.startsWith('cph03')).definition;
   await frame.locator('#family-filter').selectOption(definition);
   await expect(frame.locator('#factor-list .factor-item')).toHaveCount(2);
   await frame.locator('[data-definition]').click();
   await expect(frame.locator('#detail-cards article')).toHaveCount(2);
   await frame.locator('#view-mode').selectOption('tabs');
   await frame.locator('#detail-cards [data-tab="definition"]').first().click();
   await expect(frame.locator('#detail-cards [data-pane="definition"]').first()).toBeVisible();
   assert.equal(await frame.locator('#detail-cards [data-pane="definition"] math').count(),2);
   await frame.locator('#detail-cards [data-tab="definition"]').first().press('ArrowRight');
   await expect(frame.locator('#detail-cards [data-pane="identity"]').first()).toBeVisible();
   await frame.locator('#global-period').selectOption('2025');
   await expect(frame.locator('#result-count')).toContainText('696,637');
   await frame.locator('#detail-cards [data-tab="daily"]').first().click();
   await frame.locator('[data-range="start"]').first().fill('2026-06-30');
   await frame.locator('[data-range="start"]').first().dispatchEvent('change');
   await expect(frame.locator('#detail-cards')).toContainText('起始日期晚于结束日期');
   await frame.locator('[data-reset]').first().click();
   await frame.locator('#factor-search').fill('no_matching_factor_xyz');
   await expect(frame.locator('#all-results .empty')).toBeVisible();
   await frame.locator('[data-reset]').first().click();
   await frame.locator('#timing-scope').selectOption('fresh');
   await expect(frame.locator('#timing-table tbody tr')).toHaveCount(328);
   await frame.locator('#timing-scope').selectOption('new');
   await expect(frame.locator('#timing-table tbody tr')).toHaveCount(330);
   await frame.locator('#timing-scope').selectOption('all');
   await expect(frame.locator('#timing-table tbody tr')).toHaveCount(601);
   await frame.locator('#timing-sort').selectOption('seconds');
   await expect(frame.locator('#timing-table tbody tr').first()).toContainText('2024-12-30');
   await frame.locator('button[data-zoom]').first().click();
   await expect(frame.locator('#figure-dialog')).toBeVisible();
   if(viewport.width===1440){const dl=page.waitForEvent('download');await frame.locator('#figure-download').click();assert((await textOf(await dl)).includes('<svg'))}
   await page.keyboard.press('Escape');await expect(frame.locator('#figure-dialog')).not.toBeVisible();
   for(const id of ['definition','contract','results','factors','performance','evidence']){
    await frame.locator('nav a[href="#'+id+'"]').click();
    await expect.poll(()=>frame.url()).toBe('about:srcdoc#'+id);
    await expect.poll(()=>frame.locator('nav a.active').getAttribute('href')).toBe('#'+id);
   }
   assert.equal(page.url(),host+'#/daily/2026-10-18/show');
   const overflow=await frame.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,bad:[...document.body.querySelectorAll('*')].filter(e=>{if(['SCRIPT','STYLE','OPTION','DIALOG'].includes(e.tagName)||e.closest('dialog')||e.closest('.table-scroll')||e.closest('.nav')||e.closest('math'))return false;const b=e.getBoundingClientRect();return b.width&&b.right>innerWidth+2}).slice(0,10).map(e=>({tag:e.tagName,class:e.className,width:e.getBoundingClientRect().width}))}));
   assert(overflow.scroll<=overflow.width+2,JSON.stringify(overflow));
   const visual=await browser.newPage({viewport});
   await visual.goto(pathToFileURL(path.join(root,'content/daily/2026-10-18.show.html')).href);
   await visual.waitForFunction(()=>document.body.dataset.reportReady==='true');
   await visual.addStyleTag({content:'html{scroll-behavior:auto!important}'});
   await visual.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
   const hero=await visual.screenshot({path:path.join(__dirname,'desktop-'+viewport.width+'-hero.png')});
   await visual.locator('#view-mode').selectOption('tabs');
   await visual.evaluate(()=>document.getElementById('atlas-controls').scrollIntoView({behavior:'instant',block:'start'}));
   await visual.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
   assert(await visual.evaluate(()=>scrollY)>1000);
   const atlas=await visual.screenshot({path:path.join(__dirname,'desktop-'+viewport.width+'-atlas.png')});
   assert.notEqual(createHash('sha256').update(hero).digest('hex'),createHash('sha256').update(atlas).digest('hex'));
   await visual.close();
   results.push({viewport:viewport.width,columns:328,periods:44,filters:true,paired_definition:true,tabs_and_keyboard:true,date_validation:true,timing:true,downloads:viewport.width===1440,modal:true,scrollspy:true,iframe_isolation:true,overflow,errors,requests});
   assert.deepEqual(errors,[]);assert(requests.every(u=>u.startsWith(host)));await page.close();
  }
 }finally{await browser.close()}
 fs.writeFileSync(path.join(__dirname,'browser-verification.json'),JSON.stringify({passed:true,results},null,2));
 console.log(JSON.stringify({passed:true,viewports:results.map(r=>r.viewport),checks:'filters, pairing, tabs, dates, CSV/JSON/SVG, timing, modal, nav, sandbox, overflow'}));
})().catch(e=>{console.error(e);process.exit(1)});
