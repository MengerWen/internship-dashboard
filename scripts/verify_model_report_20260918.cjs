const { chromium } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  const output = path.join(__dirname, '../test-results/model-report-20260918');
  fs.mkdirSync(output, { recursive: true });
  const checks = [];
  for (const viewport of [{ width: 1440, height: 1000 }, { width: 390, height: 844 }]) {
    const page = await browser.newPage({ viewport, acceptDownloads: true });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto('http://127.0.0.1:8019/content/daily/2026-09-18.show.html');
    assert.equal(await page.locator('figure svg').count(), 3);
    assert.equal(await page.locator('#ledger').count(), 1);
    const data = await page.locator('#report-data').textContent();
    assert.equal(JSON.parse(data).feature_mapping.length, 328);
    assert.equal(JSON.parse(data).test_daily.length, 176);
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1);
    assert.equal(overflow, false, 'document must not overflow horizontally');
    const download = page.waitForEvent('download');
    await page.locator('#download-data').click();
    const file = await download;
    await file.saveAs(path.join(output, `report-${viewport.width}.json`));
    assert.equal(JSON.parse(fs.readFileSync(path.join(output, `report-${viewport.width}.json`), 'utf8')).feature_mapping.length, 328);
    await page.screenshot({ path: path.join(output, `page-${viewport.width}.png`), fullPage: true });
    assert.deepEqual(errors, []);
    checks.push({ viewport, figures: 3, overflow, downloaded: true, errors });
    await page.close();
  }
  const dashboard = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const dashboardErrors = [];
  dashboard.on('pageerror', error => dashboardErrors.push(error.message));
  await dashboard.goto('http://127.0.0.1:8019/dist/#/daily/2026-09-18/show');
  await dashboard.waitForSelector('#daily-show-content iframe');
  const iframe = dashboard.locator('#daily-show-content iframe');
  assert.equal(await iframe.getAttribute('sandbox'), 'allow-scripts allow-downloads');
  const frame = await (await iframe.elementHandle()).contentFrame();
  assert.equal(await frame.locator('figure svg').count(), 3);
  await dashboard.screenshot({ path: path.join(output, 'dashboard-1440.png') });
  assert.deepEqual(dashboardErrors, []);
  checks.push({ dashboardRoute: dashboard.url(), sandbox: 'allow-scripts allow-downloads', errors: dashboardErrors });
  await browser.close();
  fs.writeFileSync(path.join(output, 'browser-checks.json'), JSON.stringify(checks, null, 2));
  console.log(JSON.stringify(checks, null, 2));
})().catch(error => { console.error(error); process.exitCode = 1; });
