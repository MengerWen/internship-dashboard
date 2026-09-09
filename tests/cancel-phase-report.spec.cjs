const { test, expect } = require('@playwright/test');
const path = require('path');
const { pathToFileURL } = require('url');
const offline = pathToFileURL(path.resolve(__dirname, '../content/daily/2026-09-06.html')).href;

test('offline report supports evidence, factor exploration, interval changes and export', async ({ page }) => {
  const errors = [], network = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.route(/^https?:/, route => { network.push(route.request().url()); return route.abort(); });
  await page.goto(offline+'?view=separate');
  await expect(page.locator('h1')).toContainText('固定的等待节奏');
  await expect(page.locator('#factor-list .factor-item')).toHaveCount(24);
  await expect(page.locator('#pre-periods tr')).toHaveCount(3);
  await expect(page.locator('#ranking tbody tr')).toHaveCount(24);
  await expect(page.locator('#report-validation')).toContainText('1,212'.replace(',', ''));
  await page.screenshot({ path: 'test-results/cancel-phase-desktop.png' });
  await page.selectOption('#family-filter', '7');
  await expect(page.locator('#factor-list .factor-item')).toHaveCount(2);
  await page.locator('[data-id="F24"]').click();
  await expect(page.locator('#detail-id')).toContainText('F24 / cph07');
  await page.selectOption('#detail-period', '2026Q2');
  await page.click('#tab-groups');
  await expect(page.locator('#group-period-label')).toHaveText('2026Q2');
  const groups = await page.locator('#group-counts tr').count();
  expect(groups).toBe(10);
  const plotted = await page.locator('#group-chart svg').getAttribute('aria-label');
  expect(plotted).toContain('F24');
  const download = page.waitForEvent('download');
  await page.click('#download-groups');
  expect((await download).suggestedFilename()).toBe('total-F24-2026Q2-deciles.csv');
  await page.click('#reset-filters');
  await page.fill('#factor-search', 'cph03');
  await expect(page.locator('#factor-list .factor-item')).toHaveCount(4);
  await page.fill('#factor-search', 'no-such-factor');
  await expect(page.locator('#factor-count')).toHaveText('0 / 24 个方向因子');
  await page.click('#reset-filters');
  await page.selectOption('#demo-case', 'half');
  await page.selectOption('#demo-period', '1000');
  await expect(page.locator('#demo-result')).toContainText('620ms');
  await page.selectOption('#demo-period', '500');
  await expect(page.locator('#demo-result')).toHaveText('相位：120ms、120ms、120ms');
  await page.locator('[data-figure="overview"]').click();
  await expect(page.locator('#lightbox')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator('#lightbox')).not.toBeVisible();
  const loaded = await page.evaluate(async () => {
    const figs = JSON.parse(document.getElementById('figure-data').textContent);
    return Promise.all(Object.values(figs).map(src => new Promise(resolve => {
      const img = new Image(); img.onload = () => resolve(img.naturalWidth > 0);
      img.onerror = () => resolve(false); img.src = 'data:image/webp;base64,' + src;
    })));
  });
  expect(loaded.length).toBe(378);
  expect(loaded.every(Boolean)).toBe(true);
  expect(network).toEqual([]);
  expect(errors).toEqual([]);
});

test('mobile layout and web companion preserve readable content and local figures', async ({ page }) => {
  const errors = [], failed = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('response', r => { if (r.status() >= 400 && !r.url().endsWith('favicon.ico')) failed.push(r.url()); });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('http://127.0.0.1:8766/content/daily/2026-09-06.show.html?view=separate#factor-F01');
  await expect(page.locator('#detail-id')).toContainText('F01');
  await expect(page.locator('#detail-daily')).toBeVisible();
  expect(await page.locator('#detail-daily').evaluate(img => img.complete && img.naturalWidth > 0)).toBe(true);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
  expect(overflow).toBe(false);
  await page.locator('#factor-detail').scrollIntoViewIfNeeded();
  await page.screenshot({ path: 'test-results/cancel-phase-mobile-detail.png' });
  await page.click('#tab-scatter');
  await expect(page.locator('#pane-scatter')).toBeVisible();
  await expect(page.locator('#pane-daily')).not.toBeVisible();
  await expect(page.locator('#ols-equation')).toContainText('因子原值');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.click('#tab-groups');
  await expect(page.locator('#group-errorbars svg')).toHaveCount(2);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.locator('#group-errorbars').scrollIntoViewIfNeeded();
  await page.screenshot({path:'test-results/cancel-phase-errorbars-mobile.png'});
  await page.evaluate(() => scrollTo({ top: 0, behavior: 'instant' }));
  await page.screenshot({ path: 'test-results/cancel-phase-mobile.png' });
  expect(errors).toEqual([]); expect(failed).toEqual([]);
});

test('detail navigation exposes one panel and preserves the selected topic across factors', async ({ page }) => {
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(offline + '?view=separate#factor-F22');
  await expect(page.locator('.detail-pane:visible')).toHaveCount(1);
  await expect(page.locator('#cumulative-reading')).toContainText('-5.620478');
  await page.locator('#tab-daily').focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.locator('#tab-monthly')).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('#pane-monthly')).toBeVisible();
  await page.click('#tab-scatter');
  await expect(page.locator('#ols-metrics')).toContainText('1,705,782');
  await expect(page.locator('#ols-metrics')).toContainText('散点绘制全部 1,705,782 个真实股票日');
  await page.locator('#tab-scatter').scrollIntoViewIfNeeded();
  await page.screenshot({ path: 'test-results/cancel-phase-desktop-tabs.png' });
  await page.locator('[data-id="F01"]').click();
  await expect(page.locator('#pane-scatter')).toBeVisible();
  await expect(page.locator('#detail-scatter')).toHaveAttribute('src', /^data:image\/webp/);
  const download = page.waitForEvent('download');
  await page.click('#download-ols');
  expect((await download).suggestedFilename()).toBe('total-F01-full-ols.json');
  await page.click('#tab-groups');
  await expect(page.locator('#diagnosis-groups tr')).toHaveCount(10);
  await expect(page.locator('#group-errorbars svg')).toHaveCount(2);
  await page.selectOption('#detail-period','2026Q2');
  await expect(page.locator('#dispersion-reading')).toContainText('2026Q2');
  const errorbarDownload = page.waitForEvent('download');
  await page.click('#download-errorbars');
  expect((await errorbarDownload).suggestedFilename()).toBe('total-F01-2026Q2-errorbars.csv');
  await page.click('#errorbars-full-button');
  await expect(page.locator('#lightbox')).toBeVisible();
  await expect(page.locator('#lightbox-title')).toContainText('全部 601 日');
  await page.keyboard.press('Escape');
  await page.locator('#group-errorbars').scrollIntoViewIfNeeded();
  await page.screenshot({path:'test-results/cancel-phase-errorbars.png'});
  await expect(page.locator('.detail-pane:visible')).toHaveCount(1);
  expect(errors).toEqual([]);
});


test('buy and sell switch the complete report, preserve factor and interval, and export side identity', async ({ page }) => {
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8766/content/daily/2026-09-06.show.html?view=separate#factor-F22');
  await page.selectOption('#detail-period','2026Q2');
  for(const side of ['buy','sell','total']){
    await page.locator('.direction-select').last().selectOption(side);
    await expect(page.locator('#detail-id')).toContainText(side==='total'?'Total':side==='buy'?'Buy':'Sell');
    await expect(page.locator('#detail-id')).toContainText('F22');
    await expect(page.locator('#detail-period')).toHaveValue('2026Q2');
    for(const select of await page.locator('.direction-select').all())await expect(select).toHaveValue(side);
    const verified=await page.evaluate(side=>{
      const bundle=JSON.parse(document.getElementById('report-data').textContent);
      const data=side==='total'?bundle:bundle.directions[side];
      const f=data.factors.find(f=>f.id==='F22');
      return {n:f.stats['2026Q2'].paired,rank:f.stats['2026Q2'].rank,root:data.audit.run_root};
    },side);
    await expect(page.locator('#detail-coverage')).toContainText(verified.n.toLocaleString('zh-CN'));
    await expect(page.locator('#run-root')).toHaveText(verified.root);
    for(const tab of ['daily','monthly','groups','scatter','distribution','definition']){
      await page.click('#tab-'+tab);await expect(page.locator('#pane-'+tab)).toBeVisible();
      await expect(page.locator('.detail-pane:visible')).toHaveCount(1);
    }
    const images=await page.locator('#factor-detail img').evaluateAll((imgs,side)=>Promise.all(imgs.map(img=>new Promise(resolve=>{
      const check=()=>resolve(img.naturalWidth>0&&(side==='total'?!img.src.includes('/buy/')&&!img.src.includes('/sell/'):img.src.includes('/'+side+'/')));
      if(img.complete)check();else{img.onload=check;img.onerror=()=>resolve(false)}
    }))),side);
    expect(images.every(Boolean)).toBe(true);
    await page.click('#tab-scatter');
    const downloadPromise=page.waitForEvent('download');await page.click('#download-ols');
    const download=await downloadPromise;expect(download.suggestedFilename()).toBe(side+'-F22-full-ols.json');
    const fs=require('fs');const exported=JSON.parse(fs.readFileSync(await download.path(),'utf8'));
    expect(exported.direction).toBe(side);
    await page.click('#tab-groups');
    await page.locator('#factor-detail').scrollIntoViewIfNeeded();
    await page.screenshot({path:'test-results/cancel-phase-'+side+'-groups.png'});
  }
  expect(errors).toEqual([]);
});

test('direction deep links and mobile side changes load real side figures',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await page.goto('http://127.0.0.1:8766/content/daily/2026-09-06.show.html?view=separate&direction=sell#factor-F03');
  await expect(page.locator('#detail-id')).toContainText('Sell');
  await expect(page.locator('#detail-id')).toContainText('F03');
  await page.locator('.direction-select').last().selectOption('buy');
  await page.click('#tab-groups');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.locator('#factor-detail').scrollIntoViewIfNeeded();
  await page.screenshot({path:'test-results/cancel-phase-buy-mobile.png'});
});

test('all view exposes 72 accurate hierarchical Rank IC entries and numeric IC sorting', async ({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(offline);
  await expect(page.locator('.view-mode-select').first()).toHaveValue('all');
  await expect(page.locator('#ranking tbody tr')).toHaveCount(72);
  await expect(page.locator('#factor-list .factor-family')).toHaveCount(7);
  await expect(page.locator('#factor-list .factor-time')).toHaveCount(14);
  await expect(page.locator('#factor-list .factor-item')).toHaveCount(72);
  await page.selectOption('#nav-period','2026Q2');
  const audit=await page.evaluate(()=>{
    const bundle=JSON.parse(document.getElementById('report-data').textContent);
    return [...document.querySelectorAll('#factor-list .factor-item')].every(button=>{
      const side=button.dataset.side,data=side==='total'?bundle:bundle.directions[side];
      const f=data.factors.find(f=>f.id===button.dataset.id),rank=f.stats['2026Q2'].rank;
      return button.querySelector('.rank-value').textContent===(rank>0?'+':'')+rank.toFixed(6)
        &&button.closest('.factor-family').dataset.family===String(f.family)
        &&button.closest('.factor-time').dataset.time===f.family+'-'+f.period;
    });
  });
  expect(audit).toBe(true);
  await page.selectOption('#overview-period','2026Q2');
  for(const sort of ['ic','ic_abs','rank_value','rank','spread']){
    await page.selectOption('#rank-sort',sort);
    const sorted=await page.evaluate(sort=>{
      const bundle=JSON.parse(document.getElementById('report-data').textContent);
      const values=[...document.querySelectorAll('#ranking tbody tr')].map(row=>{
        const data=row.dataset.side==='total'?bundle:bundle.directions[row.dataset.side];
        const stats=data.factors.find(f=>f.id===row.dataset.factor).stats['2026Q2'];
        const v=stats[sort==='spread'?'spread_bps':sort.startsWith('rank')?'rank':'ic'];
        return ['ic_abs','rank','spread'].includes(sort)?Math.abs(v):v;
      });return values.every((v,i)=>!i||values[i-1]>=v);
    },sort);expect(sorted).toBe(true);
  }
  const pending=page.waitForEvent('download');await page.click('#download-summary');
  const download=await pending;expect(download.suggestedFilename()).toBe('all-cancel-phase-2026Q2.csv');
  const csv=require('fs').readFileSync(await download.path(),'utf8').trim().split(/\r?\n/);
  expect(csv).toHaveLength(73);
  for(const side of ['total','buy','sell'])expect(csv.filter(line=>line.startsWith('"'+side+'",'))).toHaveLength(24);
  await page.locator('#factor-list [data-id="F03"][data-side="buy"]').click();
  await expect(page.locator('#detail-id')).toContainText('F03 / cph01 · Buy');
  await expect(page.locator('#factor-comparison tbody tr')).toHaveCount(3);
  await expect(page.locator('.detail-stack .detail')).toHaveCount(3);
  await page.evaluate(()=>{document.documentElement.style.scrollBehavior='auto';document.getElementById('factor-comparison').scrollIntoView()});
  await page.screenshot({path:'test-results/cancel-phase-all-navigation.png'});
  expect(errors).toEqual([]);
});

test('all direction cards synchronize topics and keep companion exports and images attached to their side',async({page})=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(offline+'?view=all&direction=sell#factor-F02');
  await page.selectOption('#detail-period','2025');
  await expect(page.locator('#nav-period')).toHaveValue('2025');
  for(const side of ['total','buy','sell']){
    const card=page.locator('.detail-stack .detail[data-side="'+side+'"]');
    await expect(card.locator('[data-detail-key="detail-period"]')).toHaveValue('2025');
    await expect(card.locator('[data-detail-key="detail-id"]')).toContainText('F02');
  }
  for(const pane of ['daily','monthly','groups','scatter','distribution','definition']){
    await page.click('#tab-'+pane);
    await expect(page.locator('.detail-stack .detail-pane:visible')).toHaveCount(3);
    await expect(page.locator('.detail-stack [data-detail-key="pane-'+pane+'"]:visible')).toHaveCount(3);
  }
  const buy=page.locator('.detail-stack .detail[data-side="buy"]');
  await page.click('#tab-groups');
  const pending=page.waitForEvent('download');await buy.locator('[data-detail-key="download-groups"]').click();
  const download=await pending;expect(download.suggestedFilename()).toBe('buy-F02-2025-deciles.csv');
  const csv=require('fs').readFileSync(await download.path(),'utf8').trim().split(/\r?\n/);
  expect(csv.slice(1).every(line=>line.startsWith('"buy",'))).toBe(true);
  await page.click('#tab-scatter');
  const olsPending=page.waitForEvent('download');await buy.locator('[data-detail-key="download-ols"]').click();
  const olsDownload=await olsPending;expect(JSON.parse(require('fs').readFileSync(await olsDownload.path(),'utf8')).direction).toBe('buy');
  await buy.locator('[data-detail-key="scatter-button"]').click();
  await expect(page.locator('#lightbox-title')).toContainText('Buy');
  await expect(page.locator('#image-download')).toHaveAttribute('download','buy-F02-scatter.webp');
  await page.keyboard.press('Escape');
  await page.locator('.view-mode-select').first().selectOption('separate');
  await expect(page.locator('#ranking tbody tr')).toHaveCount(24);
  await expect(page.locator('#factor-list .factor-item')).toHaveCount(24);
  await expect(page.locator('.detail-stack .detail')).toHaveCount(1);
  await expect(page.locator('#pane-scatter')).toBeVisible();
  await expect(page.locator('#detail-period')).toHaveValue('2025');
  await page.locator('.direction-select').first().selectOption('buy');
  await page.locator('.view-mode-select').first().selectOption('all');
  await expect(page.locator('#factor-list .factor-item')).toHaveCount(72);
  await expect(page.locator('#detail-id')).toContainText('Buy');
  await expect(page.locator('.detail-stack [data-detail-key="pane-scatter"]:visible')).toHaveCount(3);
  const duplicates=await page.evaluate(()=>{const ids=[...document.querySelectorAll('[id]')].map(e=>e.id);return ids.length-new Set(ids).size});
  expect(duplicates).toBe(0);expect(errors).toEqual([]);
});

test('all view is readable on mobile and searchable by Chinese logic, ID and direction',async({page})=>{
  await page.setViewportSize({width:390,height:844});await page.goto(offline+'?view=all#factor-F03');
  await page.fill('#factor-search','跨周期');await expect(page.locator('#factor-list .factor-item')).toHaveCount(24);
  await page.fill('#factor-search','F03');await expect(page.locator('#factor-list .factor-item')).toHaveCount(3);
  await page.fill('#factor-search','buy');await expect(page.locator('#factor-list .factor-item')).toHaveCount(24);
  await page.click('#reset-filters');
  await page.click('#collapse-tree');await expect(page.locator('#factor-list .factor-family[open]')).toHaveCount(0);
  await page.click('#expand-tree');await expect(page.locator('#factor-list .factor-family[open]')).toHaveCount(7);
  await page.click('#tab-groups');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.evaluate(()=>{document.documentElement.style.scrollBehavior='auto';document.querySelector('.factor-navigation').scrollIntoView()});
  await page.screenshot({path:'test-results/cancel-phase-all-mobile.png'});
});
