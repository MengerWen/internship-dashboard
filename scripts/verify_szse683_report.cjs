const {chromium}=require('@playwright/test');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),zlib=require('node:zlib');
const root=path.resolve(__dirname,'..'),artifacts=path.join(root,'.local/runs/szse683-atlas-20261101/browser');
let browser,page;
(async()=>{
 fs.mkdirSync(artifacts,{recursive:true});
 browser=await chromium.launch({headless:true});
 page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[],requests=[];
 let rejectContextOnce=false,rejectFileOnce=false;
 page.on('pageerror',e=>errors.push(e.message));page.on('requestfailed',r=>requests.push(r.url()));
 await page.route('https://dashboard.test/**',route=>{
  const pathname=new URL(route.request().url()).pathname,asset=path.join(root,'dist',pathname.slice(1));
  if(rejectContextOnce&&pathname.endsWith('/increment-close/summary.js')){rejectContextOnce=false;return route.fulfill({contentType:'text/javascript',body:'window.szseAtlasLoaded("increment-close","invalid-gzip");'})}
  if(rejectFileOnce&&pathname.endsWith('/definitions.json.js')){rejectFileOnce=false;return route.fulfill({contentType:'text/javascript',body:'window.rawbankFileLoaded("definitions.json","invalid-gzip","application/json");'})}
  if(route.request().isNavigationRequest()&&pathname==='/')return route.fulfill({contentType:'text/html',body:'<div id="report"></div><style>iframe{width:100%;height:940px;border:0}</style>'});
  if(fs.existsSync(asset)&&fs.statSync(asset).isFile())return route.fulfill({path:asset,contentType:pathname.endsWith('.js')?'text/javascript':undefined});
  return route.fulfill({status:404,body:'missing asset'});
 });
 await page.goto('https://dashboard.test/#/daily/2026-11-01/show');
 await page.evaluate(fs.readFileSync(path.join(root,'site/js/router.js'),'utf8'));
 await page.evaluate(fs.readFileSync(path.join(root,'site/js/daily.js'),'utf8'));
 const manifest=JSON.parse(fs.readFileSync(path.join(root,'dist/manifest.json'),'utf8')),item=manifest.daily.find(r=>r.date==='2026-11-01');
 assert.equal(item.show_path,'daily/2026-11-01.show.html');
 await page.evaluate(async item=>{window.DailyView.showEl=document.querySelector('#report');window.DailyView.app=window.DashboardApp;await window.DailyView.renderShow(item)},item);
 assert.equal(await page.locator('iframe').getAttribute('sandbox'),'allow-scripts allow-downloads');
 const frame=page.frames().find(f=>f.parentFrame());
 const ready=()=>frame.waitForFunction(()=>document.body.dataset.detailReady==='true'&&[...document.querySelectorAll('#detail-cards .detail')].every(c=>c.dataset.ready==='true'),{},{timeout:60000});
 await ready();
 const cards=()=>frame.locator('#detail-cards .detail');
 assert.equal(await frame.locator('#factor-list .factor-item').count(),344);
 assert.equal(await frame.locator('#all-results tbody tr').count(),344);
 assert.equal(await frame.locator('#category-comparison tbody tr').count(),4);
 assert.equal(await frame.locator('#overlap-comparison tbody tr').count(),10);
 assert.equal(await frame.locator('#price-coverage tbody tr').count(),9);
 rejectContextOnce=true;
 await frame.selectOption('#sample-context','increment');await frame.waitForFunction(()=>document.body.dataset.context==='increment-10m');await ready();
 await frame.selectOption('#horizon-context','close');await frame.locator('#context-retry').waitFor({state:'visible'});
 assert.equal(await frame.locator('#context-status').innerText(),'数据解码失败，请重试。');
 await frame.locator('#context-retry').click();await frame.waitForFunction(()=>document.body.dataset.context==='increment-close');await ready();
 for(const sample of ['full','base','increment'])for(const horizon of ['10m','lunch','close']){
  const change=async(id,value,key)=>{if(await frame.inputValue(id)!==value){await frame.selectOption(id,value);await frame.waitForFunction(key=>document.body.dataset.context===key,key);await ready()}};
  let oldH=await frame.inputValue('#horizon-context');
  await change('#sample-context',sample,sample+'-'+oldH);
  await change('#horizon-context',horizon,sample+'-'+horizon);
  const info=await frame.evaluate(()=>({days:rawbankReport.data.dates.length,label:rawbankReport.data.label,context:rawbankReport.data.dataset_context,periods:rawbankReport.data.periods.length}));
  assert.deepEqual(info,{days:{full:683,base:601,increment:82}[sample],label:'ret_'+horizon,context:sample+'-'+horizon,periods:{full:50,base:44,increment:8}[sample]});
  for(const tab of ['ic','monthly','groups','scatter','shape','periods','definition']){
   await cards().first().locator('[data-tab="'+tab+'"]').click();
   assert.equal(await cards().first().locator('[data-key="pane-'+tab+'"]').isVisible(),true);
  }
  const downloadEvent=page.waitForEvent('download');
  await cards().first().locator('[data-key="download-factor"]').click();
  const download=await downloadEvent,data=JSON.parse(fs.readFileSync(await download.path(),'utf8'));
  assert.equal(data.dates.length,info.days);assert.equal(data.label,'ret_'+horizon);
  assert.equal(data.factor.details.ols.n,data.factor.distribution.pairs);
  assert.equal(data.factor.periods.length,info.periods);
 }
 await frame.selectOption('#sample-context','full');await frame.waitForFunction(()=>document.body.dataset.context==='full-close');await ready();
 await frame.selectOption('#horizon-context','10m');await frame.waitForFunction(()=>document.body.dataset.context==='full-10m');await ready();
 rejectFileOnce=true;
 await frame.locator('a[data-file-download="definitions.json"]').click();
 await frame.waitForFunction(()=>document.querySelector('a[data-file-download="definitions.json"]').textContent==='下载失败，点击重试');
 for(const filename of ['definitions.json','evaluation-contract.json','factor-overlap.json','factor-assets.json','column-mapping.csv','all-context-performance.csv.gz']){
  const event=page.waitForEvent('download');await frame.locator('a[data-file-download="'+filename+'"]').click();
  const download=await event;assert.equal(download.suggestedFilename(),filename);
  const bytes=fs.readFileSync(await download.path()),expected=fs.readFileSync(path.join(root,'content/assets/szse683-2026-11-01',filename));
  assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'),crypto.createHash('sha256').update(expected).digest('hex'));
  if(filename.endsWith('.gz'))assert.equal(zlib.gunzipSync(bytes).toString('utf8').trim().split('\r\n').length,105265);
  assert.equal(frame.url(),'about:srcdoc');
 }
 await frame.selectOption('#view-mode','separate');await frame.selectOption('#side-filter','sell');
 assert.equal(await frame.locator('#factor-list .factor-item').count(),172);
 await frame.locator('#reset-filters').click();await frame.selectOption('#factor-scope','depth');
 assert.equal(await frame.locator('#factor-list .factor-item').count(),24);
 await frame.locator('#factor-list .factor-item').first().click();await ready();
 const selectedLeaf=await frame.evaluate(()=>rawbankSelectedFactor),selectedTitle=await frame.locator('#scope-summary h3').innerText();
 await frame.selectOption('#sample-context','increment');await frame.waitForFunction(()=>document.body.dataset.context==='increment-10m');await ready();
 assert.equal(await frame.evaluate(()=>rawbankSelectedFactor),selectedLeaf);assert.equal(await frame.locator('#scope-summary h3').innerText(),selectedTitle);
 await frame.selectOption('#sample-context','full');await frame.waitForFunction(()=>document.body.dataset.context==='full-10m');await ready();
 await frame.locator('#factor-list .tree-title[data-kind="definition"]').first().click();await ready();
 assert.equal(await cards().count(),2);
 await frame.selectOption('#sample-context','increment');await frame.waitForFunction(()=>document.body.dataset.context==='increment-10m');await ready();
 assert.equal(await frame.inputValue('#factor-scope'),'depth');assert.equal(await cards().count(),2);
 await frame.selectOption('#sample-context','full');await frame.waitForFunction(()=>document.body.dataset.context==='full-10m');await ready();
 await frame.selectOption('#factor-arrangement','flat');await frame.selectOption('#factor-sort','rank_value');await ready();
 const indices=await frame.locator('#factor-list .factor-item').evaluateAll(bs=>bs.map(b=>+b.dataset.index));
 const values=await frame.evaluate(indices=>indices.map(i=>rawbankReport.data.factors[i].periods[0].ic[1][0]),indices);
 assert.ok(values.every((v,i)=>!i||v===null||values[i-1]===null||values[i-1]>=v));
 const csvEvent=page.waitForEvent('download');await frame.locator('#download-explorer').click();
 const csv=fs.readFileSync(await (await csvEvent).path(),'utf8');assert.equal(csv.trim().split('\r\n').length,25);
 await cards().first().locator('[data-tab="groups"]').click();
 const groupEvent=page.waitForEvent('download');await cards().first().locator('[data-key="download-groups"]').click();
 assert.equal(fs.readFileSync(await (await groupEvent).path(),'utf8').trim().split('\r\n').length,11);
 await cards().first().locator('[data-tab="ic"]').click();
 await cards().first().locator('[data-key="date-start"]').fill('2026-10-01');await cards().first().locator('[data-key="date-start"]').dispatchEvent('change');
 const dailyEvent=page.waitForEvent('download');await cards().first().locator('[data-key="download-daily"]').click();
 const daily=fs.readFileSync(await (await dailyEvent).path(),'utf8');assert.ok(daily.includes('2026-10-30'));assert.ok(!daily.includes('2024-01-02'));
 await cards().first().locator('[data-tab="scatter"]').click();
 await cards().first().locator('[data-key="pane-scatter"] [data-zoom]').first().click();
 assert.equal(await frame.locator('#figure-dialog').isVisible(),true);
 const svgEvent=page.waitForEvent('download');await frame.locator('#figure-download').click();
 assert.match(fs.readFileSync(await (await svgEvent).path(),'utf8'),/<svg/);await frame.locator('#figure-close').click();
 await frame.locator('#factor-search').fill('no-matching-factor');assert.equal(await cards().count(),0);
 await frame.locator('#reset-filters').click();await ready();
 for(const id of ['definition','contract','results','factors','evidence']){
  await frame.locator('nav a[href="#'+id+'"]').click();assert.equal(frame.url(),'about:srcdoc#'+id);
 }
 await frame.evaluate(()=>{document.documentElement.style.scrollBehavior='auto';document.querySelector('#factors').scrollIntoView({behavior:'instant'})});
 await page.screenshot({path:path.join(artifacts,'desktop.png')});
 await page.setViewportSize({width:390,height:844});
 for(const tab of ['ic','monthly','groups','scatter','shape','periods','definition']){
  await cards().first().locator('[data-tab="'+tab+'"]').click();
  assert.equal(await frame.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2),false,'mobile overflow '+tab);
 }
 for(const id of ['definition','contract','results','factors','evidence'])assert.ok(await frame.locator('#'+id+' h2').evaluate(el=>el.getBoundingClientRect().width)>=200,'mobile heading width '+id);
 await frame.evaluate(()=>document.querySelector('#results').scrollIntoView({behavior:'instant'}));
 await page.screenshot({path:path.join(artifacts,'mobile.png')});
 assert.deepEqual(errors,[]);assert.deepEqual(requests,[]);
 fs.writeFileSync(path.join(artifacts,'verification.json'),JSON.stringify({passed:true,contexts:9,tabs:7,columns:344,desktop:[1440,1000],mobile:[390,844],errors,requests,downloads:['9 factor JSON','filtered CSV','group CSV','date CSV','SVG','6 static attachments with exact SHA and retry']},null,2));
 await browser.close();console.log('PASS: 9 contexts, 7 tabs, counts, filters/order, Buy/Sell, CSV/JSON/SVG, mobile, sandbox');
})().catch(async e=>{console.error(e);for(const frame of page?.frames()||[])try{console.error(await frame.evaluate(()=>({url:location.href,body:document.body.dataset,status:document.querySelector('#context-status')?.textContent,context:window.rawbankReport?.data.dataset_context,ready:document.body.dataset.detailReady})));}catch{}await browser?.close();process.exitCode=1});
