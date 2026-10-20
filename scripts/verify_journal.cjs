// 本地服务：python -m http.server 8029 --bind 127.0.0.1
const {chromium} = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const base = process.env.JOURNAL_BASE_URL || 'http://127.0.0.1:8029/dist/';
const output = path.resolve('artifacts/journal-column');

(async () => {
  await fs.mkdir(output, {recursive: true});
  const browser = await chromium.launch({headless: true, channel: 'chrome'});
  const results = [];
  try {
    for (const width of [1440, 390]) {
      const page = await browser.newPage({viewport: {width, height: 900}});
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      await page.goto(base + '#/journal?view=list');
      await page.waitForSelector('#journal-list tbody tr');
      assert.equal(await page.locator('#journal-list tbody tr').count(), 88);
      assert.equal(await page.locator('#tab-journal.is-active').count(), 1);
      assert(await page.locator('#journal-list a[href="#/daily/2026-10-14"]').count());
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
      assert.equal(overflow, false, `page overflow at ${width}`);
      await page.screenshot({path: path.join(output, `p1-list-${width}.png`)});
      await page.locator('#journal-find').fill('2026-10-14');
      assert.equal(await page.locator('#journal-list tbody tr').count(), 1);
      await page.locator('#journal-find').fill('没有这个关键词');
      assert(await page.locator('.journal-empty').isVisible());
      await page.locator('#journal-find').fill('');
      assert.equal(await page.locator('#journal-list tbody tr').count(), 88);
      assert.deepEqual(errors, []);
      results.push({width, days: 88, overflow, errors});
      await page.close();
    }
    await fs.writeFile(path.join(output, 'verification.json'), JSON.stringify(results, null, 2));
    console.log(JSON.stringify(results));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
