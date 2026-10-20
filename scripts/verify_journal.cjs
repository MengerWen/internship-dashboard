// 本地服务：python -m http.server 8029 --bind 127.0.0.1
const {chromium} = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
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
      // Python 静态预览没有既有标签 API；仅为该接口提供仓库快照。
      const tags = JSON.parse(await fs.readFile(path.resolve('content/report-tags.json'), 'utf8'));
      await page.route('**/api/report-tags', route => route.fulfill({json: {...tags, can_edit: false}}));
      page.on('pageerror', e => errors.push(e.message));
      page.on('console', e => { if (e.type() === 'error') errors.push(e.text()); });
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
      await page.goto(base + '#/journal');
      await page.waitForSelector('.journal-atlas', {state: 'attached'});
      assert.equal(await page.locator('#journal-list').isVisible(), width < 860);
      await page.locator('[data-journal-view="atlas"]').click();
      assert.equal(await page.locator('.journal-atlas').getAttribute('data-days'), '88');
      assert.equal(await page.locator('.journal-day-hit').count(), 88);
      assert(await page.locator('.journal-pause').count());
      const types = await page.locator('.journal-handoff').evaluateAll(nodes => [...new Set(nodes.map(n => n.dataset.type))].sort());
      assert.deepEqual(types, ['依赖解除', '延续', '收口', '派生'].sort());
      const ys = await page.locator('[data-chain-y]').evaluateAll(nodes => nodes.map(n => n.dataset.chainY));
      assert.equal(new Set(ys).size, 28);
      const ratios = await page.locator('.journal-day-hit').evaluateAll(nodes => {
        const x = d => Number(nodes.find(n => n.dataset.journalDay === d).getAttribute('x'));
        return (x('2026-10-07') - x('2026-09-23')) / (x('2026-10-08') - x('2026-10-07'));
      });
      assert(Math.abs(ratios - 14) < .0001, 'date gaps must retain real width');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      if (width === 1440) {
        const indexed = await page.evaluate(async () => {
          const search = await import('./pagefind/pagefind.js');
          const hits = await search.search('回测');
          const data = await Promise.all(hits.results.map(hit => hit.data()));
          return data.some(hit => hit.meta.type === 'journal' && hit.url.includes('journal-'));
        });
        assert(indexed, 'Pagefind must search journal content');
      }
      await page.screenshot({path: path.join(output, `p2-atlas-${width}.png`)});
      for (const route of ['#/journal', '#/journal/2026-10-14', '#/journal?chain=szse-model328', '#/journal?view=list']) {
        await page.goto(base + route);
        await page.waitForSelector('#view-journal.is-active');
        if (route.includes('/2026-10-14')) assert.equal(await page.locator('[data-selected-date]').getAttribute('data-selected-date'), '2026-10-14');
        if (route.includes('chain=')) assert(await page.locator('.journal-chain-card').isVisible());
      }
      await page.goto(base + '#/journal/2026-10-14?view=atlas');
      await page.waitForSelector('[data-selected-date="2026-10-14"]');
      const evidenceRequests = [];
      page.on('request', r => { if (r.url().includes('/journal/_evidence/')) evidenceRequests.push(r.url()); });
      assert.equal(evidenceRequests.length, 0);
      await page.locator('.journal-evidence > summary').click();
      await page.waitForSelector('.journal-repo');
      assert.equal(evidenceRequests.length, 1);
      assert.equal(await page.locator('.journal-repo[open]').count(), 0);
      await page.locator('.journal-repo > summary').first().click();
      assert(await page.locator('.journal-repo a[href^="https://github.com/"]').count());
      await page.locator('[data-selected-date]').scrollIntoViewIfNeeded();
      await page.screenshot({path: path.join(output, `day-evidence-${width}.png`), fullPage: true});
      await page.locator('.journal-atlas').focus();
      await page.keyboard.press('ArrowRight');
      assert.equal(await page.locator('[data-selected-date]').getAttribute('data-selected-date'), '2026-10-15');
      assert(await page.locator('.journal-atlas').evaluate(n => n === document.activeElement));
      assert.notEqual(await page.locator('.journal-atlas').evaluate(n => getComputedStyle(n).outlineStyle), 'none');
      await page.keyboard.press('ArrowLeft');
      assert.equal(await page.locator('[data-selected-date]').getAttribute('data-selected-date'), '2026-10-14');
      await page.locator('#journal-chain').selectOption('szse-model328');
      assert(await page.locator('.journal-chain-card').isVisible());
      assert(await page.locator('.journal-unit.is-dimmed').count());
      assert(await page.locator('.journal-unit.is-focused').count());
      await page.locator('#journal-detail').scrollIntoViewIfNeeded();
      await page.screenshot({path: path.join(output, `chain-${width}.png`)});
      await page.locator('.journal-atlas').focus();
      await page.keyboard.press('Escape');
      assert.equal(await page.locator('#journal-chain').inputValue(), '');
      await page.locator('#journal-window').selectOption('1m');
      const windowCount = Number(await page.locator('.journal-atlas').getAttribute('data-days'));
      assert(windowCount < 88 && windowCount > 0);
      await page.locator('[data-journal-view="list"]').click();
      assert.equal(await page.locator('#journal-list tbody tr').count(), windowCount);
      await page.locator('#journal-window').selectOption('all');
      await page.locator('#journal-list a[data-journal-day="2026-10-14"]').first().click();
      assert(await page.locator('#journal-figure').isVisible());
      assert.equal(await page.locator('[data-selected-date]').getAttribute('data-selected-date'), '2026-10-14');
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      assert.deepEqual(errors, []);
      results.push({width, days: 88, overflow, errors});
      await page.close();
    }
    const offline = await browser.newPage();
    const offlineRequests = [], offlineErrors = [];
    offline.on('request', r => { if (/^https?:/.test(r.url())) offlineRequests.push(r.url()); });
    offline.on('pageerror', e => offlineErrors.push(e.message));
    await offline.goto(pathToFileURL(path.resolve('dist-offline/index.html')).href + '#/journal/2026-10-14');
    await offline.waitForSelector('.journal-evidence');
    await offline.locator('.journal-evidence > summary').click();
    await offline.waitForSelector('.journal-repo');
    assert.deepEqual(offlineRequests, []);
    assert.deepEqual(offlineErrors, []);
    results.push({offline: true, requests: offlineRequests, errors: offlineErrors});
    await offline.close();
    await fs.writeFile(path.join(output, 'verification.json'), JSON.stringify(results, null, 2));
    console.log(JSON.stringify(results));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
