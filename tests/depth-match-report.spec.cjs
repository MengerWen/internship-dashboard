const {test,expect}=require('@playwright/test');
const path=require('path'),fs=require('fs'),{pathToFileURL}=require('url');
const web='http://127.0.0.1:8767/content/daily/2026-09-07.show.html';
const offline=pathToFileURL(path.resolve(__dirname,'../content/daily/2026-09-07.html')).href;
const card=(page,c)=>page.locator('.detail[data-column="'+c+'"]');
const key=(root,k)=>root.locator('[data-key="'+k+'"]');

test('report exposes grouped atlas, aligned side charts and structured formulas',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(web);
 await expect(page.locator('#results #ranking')).toHaveCount(0);
 await expect(page.locator('#factors #ranking tr[data-column]')).toHaveCount(24);
 await expect(page.locator('#factor-list .factor-family')).toHaveCount(4);
 await expect(page.locator('#factor-list .factor-variant')).toHaveCount(12);
 await expect(page.locator('#factor-list .factor-item')).toHaveCount(24);
 await expect(page.locator('#detail-period option')).toHaveCount(44);
 await expect(page.locator('#detail-cards .detail')).toHaveCount(2);
 await expect(page.locator('#families math')).toHaveCount(12);
 const charts=page.locator('#overview-plot figure');await expect(charts).toHaveCount(2);
 const aligned=await charts.evaluateAll(nodes=>nodes.map(n=>({side:n.dataset.side,y:n.getBoundingClientRect().y,x:n.getBoundingClientRect().x,max:n.querySelector('svg').dataset.axisMax,columns:[...n.querySelectorAll('rect[data-column]')].map(r=>r.dataset.column)})));
 expect(aligned.map(x=>x.side)).toEqual(['buy','sell']);expect(aligned[0].y).toBe(aligned[1].y);expect(aligned[0].x).toBeLessThan(aligned[1].x);expect(aligned[0].max).toBe(aligned[1].max);
 expect(aligned[0].columns.map(c=>c.replace('_buy',''))).toEqual(aligned[1].columns.map(c=>c.replace('_sell','')));
 await page.locator('#overview-plot').screenshot({path:'test-results/depth-match-overview.png'});
 await charts.nth(1).locator('button').click();await expect(page.locator('#figure-download')).toHaveAttribute('download','depth-match-sell-full-rank-ic.svg');await page.keyboard.press('Escape');
 expect(errors).toEqual([]);
});

test('titles select exact scopes and arrows retain independent expanded state',async({page})=>{
 await page.goto(web);
 await page.locator('.factor-item[data-id="dm06_soft_under_sell"]').click();
 await expect(page.locator('.detail')).toHaveCount(1);await expect(card(page,'dm06_soft_under_sell')).toBeVisible();
 const group=page.locator('[data-branch="logic-quantity"]');
 await group.locator(':scope > summary .tree-toggle').click();await expect(group).not.toHaveAttribute('open','');
 await expect(card(page,'dm06_soft_under_sell')).toBeVisible();
 await group.locator(':scope > summary .tree-title').click();await expect(group).not.toHaveAttribute('open','');await expect(page.locator('.detail')).toHaveCount(8);
 await group.locator(':scope > summary .tree-toggle').click();await expect(page.locator('.detail')).toHaveCount(8);
 await page.locator('.tree-title[data-kind="definition"][data-key="dm06_soft_under"]').click();await expect(page.locator('.detail')).toHaveCount(2);
 await page.selectOption('#detail-period','2025');
 const metrics=await page.locator('.factor-item').evaluateAll(nodes=>{
  const d=JSON.parse(document.getElementById('report-data').textContent);return nodes.every(n=>['ic','rank'].every(k=>{
   const v=d.period_summary.find(r=>r.formal_column===n.dataset.id&&r.period==='2025'&&r.metric===(k==='ic'?'pearson_ic':'rank_ic')).mean;
   return n.querySelector('.'+k+'-value').textContent===(v>0?'+':'')+v.toFixed(6);
  }));
 });expect(metrics).toBe(true);
 for(const side of ['buy','sell'])await expect(key(card(page,'dm06_soft_under_'+side),'detail-coverage')).toContainText('2025');
 await page.locator('#factor-controls').scrollIntoViewIfNeeded();await page.screenshot({path:'test-results/depth-match-atlas-controls.png'});
 await page.locator('.factor-navigation').screenshot({path:'test-results/depth-match-grouped-navigation.png'});
 const ids=await page.locator('[id]').evaluateAll(nodes=>nodes.map(n=>n.id));expect(new Set(ids).size).toBe(ids.length);
});

test('flat and grouped ordering share filters, period metrics and CSV output',async({page})=>{
 await page.goto(web);
 const sameOrder=()=>page.evaluate(()=>JSON.stringify([...document.querySelectorAll('#ranking tr[data-column]')].map(n=>n.dataset.column))===JSON.stringify([...document.querySelectorAll('.factor-item')].map(n=>n.dataset.id)));
 expect(await sameOrder()).toBe(true);
 await page.selectOption('#factor-arrangement','flat');await expect(page.locator('#factor-sort')).toHaveValue('ic');
 await expect(page.locator('#factor-list details')).toHaveCount(0);await expect(page.locator('.detail')).toHaveCount(1);
 await page.selectOption('#detail-period','2026Q2');
 for(const sort of ['ic','ic_abs','rank_value','rank','spread']){
  await page.selectOption('#factor-sort',sort);expect(await sameOrder()).toBe(true);
  const sorted=await page.locator('#ranking tr[data-column]').evaluateAll((nodes,sort)=>{
   const d=JSON.parse(document.getElementById('report-data').textContent),values=nodes.map(n=>{
    const c=n.dataset.column,v=sort==='spread'?d.decile_spread_summary.find(r=>r.formal_column===c&&r.period==='2026Q2').mean:d.period_summary.find(r=>r.formal_column===c&&r.period==='2026Q2'&&r.metric===(sort.startsWith('ic')?'pearson_ic':'rank_ic')).mean;
    return ['rank','ic_abs','spread'].includes(sort)?Math.abs(v):v;
   });return values.every((v,i)=>!i||v<=values[i-1]);
  },sort);expect(sorted).toBe(true);
 }
 await page.selectOption('#logic-filter','time');await expect(page.locator('.factor-item')).toHaveCount(4);
 await page.fill('#factor-search','近期');await expect(page.locator('.factor-item')).toHaveCount(2);
 await page.locator('#factor-controls .view-mode-select').selectOption('separate');
 await page.locator('#factor-controls .direction-select').selectOption('buy');await expect(page.locator('.factor-item')).toHaveCount(1);
 await expect(card(page,'dm11_recent_buy')).toBeVisible();await expect(page.locator('#overview-plot figure')).toHaveCount(1);
 expect(await page.locator('#year-table tbody tr td:first-child').allTextContents()).toEqual(expect.arrayContaining([expect.stringContaining('_buy')]));
 expect((await page.locator('#year-table tbody tr td:first-child').allTextContents()).every(c=>c.endsWith('_buy'))).toBe(true);
 await expect(page.locator('#correlation tbody tr')).toHaveCount(12);
 expect(await page.locator('#pair-table').innerText()).not.toContain('_sell');
 const pending=page.waitForEvent('download');await page.click('#download-summary');const download=await pending;
 const rows=fs.readFileSync(await download.path(),'utf8').trim().split(/\r?\n/);expect(rows).toHaveLength(2);expect(rows[1]).toContain('"dm11_recent_buy","buy","2026Q2"');
 await page.fill('#factor-search','no_matching_factor');await expect(page.locator('.detail')).toHaveCount(0);await expect(page.locator('#download-summary')).toBeDisabled();
 await page.click('#reset-filters');await expect(page.locator('.factor-item')).toHaveCount(12);
 await page.locator('#factor-controls .view-mode-select').selectOption('all');await expect(page.locator('.factor-item')).toHaveCount(24);
 await page.locator('.factor-navigation').screenshot({path:'test-results/depth-match-flat-navigation.png'});
 await page.selectOption('#factor-arrangement','grouped');await expect(page.locator('#factor-list .factor-family')).toHaveCount(4);expect(await sameOrder()).toBe(true);
});

test('paired cards synchronize topics and dates while preserving factor identity in exports and zooms',async({page})=>{
 await page.goto(web);const buy=card(page,'dm11_recent_buy'),sell=card(page,'dm11_recent_sell');
 for(const pane of ['daily','monthly','groups','scatter','distribution','definition']){
  await buy.locator('[data-pane="'+pane+'"]').click();await expect(page.locator('.detail-pane:visible')).toHaveCount(2);
  for(const root of [buy,sell])await expect(key(root,'pane-'+pane)).toBeVisible();
 }
 await buy.locator('[data-pane="groups"]').click();
 let pending=page.waitForEvent('download');await key(buy,'download-groups').click();let download=await pending;
 let rows=fs.readFileSync(await download.path(),'utf8').trim().split(/\r?\n/);expect(rows).toHaveLength(11);expect(rows.slice(1).every(r=>r.startsWith('"dm11_recent_buy","full",'))).toBe(true);
 await buy.locator('.groups-wrap').nth(1).click();await expect(page.locator('#figure-download')).toHaveAttribute('download','dm11_recent_buy-full-within-dispersion.svg');await page.keyboard.press('Escape');
 await buy.locator('[data-pane="scatter"]').click();pending=page.waitForEvent('download');await key(sell,'download-ols').click();download=await pending;
 const ols=JSON.parse(fs.readFileSync(await download.path(),'utf8'));expect(ols.formal_column).toBe('dm11_recent_sell');expect(ols.side).toBe('sell');
 await key(sell,'pane-scatter').locator('.figure-button').click();await expect(page.locator('#figure-download')).toHaveAttribute('download','dm11_recent_sell-scatter.png');await page.keyboard.press('Escape');
 await buy.locator('[data-pane="daily"]').click();
 await key(buy,'date-start').fill('2025-01-02');await key(buy,'date-start').dispatchEvent('change');
 await key(sell,'date-end').fill('2025-01-10');await key(sell,'date-end').dispatchEvent('change');
 await expect(key(sell,'date-start')).toHaveValue('2025-01-02');await expect(key(buy,'date-end')).toHaveValue('2025-01-10');
 const expected=await page.evaluate(()=>JSON.parse(document.getElementById('report-data').textContent).daily_ic.filter(r=>r.formal_column==='dm11_recent_buy'&&r.date>='2025-01-02'&&r.date<='2025-01-10'));
 await expect(key(buy,'daily-table').locator('tbody tr')).toHaveCount(expected.length);
 expect(await key(buy,'daily-table').locator('tbody tr').first().locator('td').nth(4).textContent()).toBe(expected[0].pearson_ic_cumulative.toFixed(5));
 pending=page.waitForEvent('download');await key(buy,'download-daily').click();download=await pending;rows=fs.readFileSync(await download.path(),'utf8').trim().split(/\r?\n/);expect(rows.length).toBe(expected.length+1);
 await page.selectOption('#detail-period','2026Q2');await expect(key(buy,'detail-coverage')).toContainText('2026Q2');await expect(key(buy,'date-start')).toHaveValue('2026-04-01');
 await key(buy,'date-end').fill('2025-01-01');await key(buy,'date-end').dispatchEvent('change');await expect(key(buy,'download-daily')).toBeDisabled();await expect(key(sell,'daily-count')).toContainText('起始日期晚于结束日期');
});

test('scope, grouping, filters, interval and active topic survive refresh',async({page})=>{
 await page.goto(web);await page.selectOption('#detail-period','2025');await page.selectOption('#logic-filter','adaptation');
 await page.locator('.tree-title[data-kind="definition"][data-key="dm08_adaptive_repeat"]').click();
 await card(page,'dm08_adaptive_repeat_buy').locator('[data-pane="definition"]').click();
 await page.reload();await expect(page.locator('#logic-filter')).toHaveValue('adaptation');await expect(page.locator('#detail-period')).toHaveValue('2025');await expect(page.locator('.detail')).toHaveCount(2);
 await expect(key(card(page,'dm08_adaptive_repeat_sell'),'pane-definition')).toBeVisible();
 await page.selectOption('#factor-arrangement','flat');await page.selectOption('#factor-sort','rank_value');await page.reload();
 await expect(page.locator('#factor-arrangement')).toHaveValue('flat');await expect(page.locator('#factor-sort')).toHaveValue('rank_value');await expect(page.locator('.detail')).toHaveCount(1);
});

test('offline math, all displayed figures and mobile layouts work without network',async({page})=>{
 const errors=[],network=[];page.on('pageerror',e=>errors.push(e.message));await page.route(/^https?:/,r=>{network.push(r.request().url());return r.abort()});await page.goto(offline);
 const decoded=await page.evaluate(async()=>{const figs=JSON.parse(document.getElementById('figure-data').textContent);return Promise.all(Object.values(figs).map(value=>new Promise(resolve=>{const img=new Image();img.onload=()=>resolve(img.naturalWidth>0&&img.naturalHeight>0);img.onerror=()=>resolve(false);img.src='data:image/png;base64,'+value}))) });
 expect(decoded).toHaveLength(120);expect(decoded.every(Boolean)).toBe(true);
 const fractions=await page.locator('#definition mfrac, #contract mfrac').evaluateAll(nodes=>nodes.map(n=>{const a=n.children[0].getBoundingClientRect(),b=n.children[1].getBoundingClientRect();return n.namespaceURI==='http://www.w3.org/1998/Math/MathML'&&a.bottom<=b.top+1}));expect(fractions.length).toBeGreaterThan(8);expect(fractions.every(Boolean)).toBe(true);
 await page.locator('.tree-title[data-kind="definition"][data-key="dm12_persistent"]').click();const root=card(page,'dm12_persistent_buy');await root.locator('[data-pane="definition"]').click();
 await expect(key(root,'pane-definition')).toContainText('不再除以 N');await expect(key(root,'pane-definition').locator('math[data-equation="DM12"]')).toBeVisible();
 await page.locator('#families').screenshot({path:'test-results/depth-match-formulas.png'});
 await page.locator('#detail-cards').screenshot({path:'test-results/depth-match-paired-definition.png'});
 expect(await page.locator('body').innerText()).not.toContain('Pearson IC');
 await page.setViewportSize({width:390,height:844});await page.selectOption('#factor-arrangement','flat');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await page.locator('.factor-navigation').screenshot({path:'test-results/depth-match-mobile.png'});
 const overview=await page.locator('#overview-plot').evaluate(n=>({client:n.clientWidth,scroll:n.scrollWidth,sides:[...n.querySelectorAll('figure')].map(x=>x.dataset.side)}));expect(overview.sides).toEqual(['buy','sell']);expect(overview.scroll).toBeGreaterThan(overview.client);
 expect(errors).toEqual([]);expect(network).toEqual([]);
});
