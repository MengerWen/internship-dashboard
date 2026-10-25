const { chromium } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const out = __dirname;
const base = 'http://127.0.0.1:8876/';
const result = { pages: [], cases: [], errors: [], previewServiceWarnings: [], embedded: [] };

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    page.on('pageerror', error => result.errors.push(error.message));
    page.on('console', message => {
      if (message.type() === 'error') {
        const entry = { text: message.text(), location: message.location() };
        if (entry.location.url.endsWith('/api/report-tags')) result.previewServiceWarnings.push(entry);
        else result.errors.push(entry);
      }
    });
    await page.goto(base + 'content/daily/2026-10-25.show.html');
    await page.locator('#app h1').waitFor();
    assert.match(await page.title(), /26\.10\.25/);
    assert.equal(await page.locator('.chapter-nav button').count(), 14);
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      for (let i = 0; i < 14; i++) {
        await page.locator(`.chapter-nav [data-value="${i}"]`).click();
        assert.match(await page.locator('#reading-state').innerText(), new RegExp(`${i + 1} / 14`));
        const geometry = await page.evaluate(() => ({
          width: innerWidth, scroll: document.documentElement.scrollWidth,
          heading: document.querySelector('#app h1').textContent
        }));
        assert.ok(geometry.scroll <= width + 1, `Overflow at ${width}, scene ${i}: ${geometry.scroll}`);
        result.pages.push({ width, scene: i + 1, ...geometry });
        if ([0, 9, 11, 12].includes(i)) {
          await page.screenshot({ path: path.join(out, `scene-${i + 1}-${width}.png`), fullPage: true });
        }
      }
      assert.equal(await page.locator('[data-action="page"][data-value="1"]').isDisabled(), true);
      await page.keyboard.press('ArrowLeft');
      assert.match(await page.locator('#reading-state').innerText(), /13 \/ 14/);
      await page.locator('.chapter-nav [data-value="11"]').click();
      for (let i = 0; i < 5; i++) {
        await page.locator(`[data-action="calibration"][data-value="${i}"]`).click();
        assert.ok(await page.locator('.inspector').innerText());
      }
      await page.locator('.method-details summary').click();
      assert.equal(await page.locator('.method-details tbody tr').count(), 8);
      await page.locator('[data-action="evidence"][data-value="next"]').click();
      assert.equal(await page.locator('#evidence-dialog').isVisible(), true);
      assert.match(await page.locator('#evidence-body').innerText(), /第六核绑定与代码修复、小样本、P75 试算已获批准并实施/);
      await page.locator('[data-action="close-dialog"]').click();
      await page.locator('[data-action="view"][data-value="cases"]').click();
      for (let i = 0; i < 6; i++) {
        await page.locator(`[data-action="case"][data-value="${i}"]`).click();
        assert.match(await page.locator('#reading-state').innerText(), new RegExp(`案例 ${i + 1} / 6`));
        const scroll = await page.evaluate(() => document.documentElement.scrollWidth);
        assert.ok(scroll <= width + 1, `Case ${i} overflow at ${width}`);
        result.cases.push({ width, case: i + 1, scroll });
      }
      await page.locator('[data-action="view"][data-value="story"]').click();
    }
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.locator('[data-action="sources"]').click();
    await page.getByText('本次补充的来源与审核状态', { exact: true }).click();
    assert.match(await page.locator('#evidence-body').innerText(), /local-plan-review/);
    await page.screenshot({ path: path.join(out, 'sources.png'), fullPage: true });
    await page.locator('[data-action="close-dialog"]').click();
    for (const kind of ['online', 'offline']) {
      await page.goto(base + `artifacts/sse-report-update-20261025/${kind}/index.html#/daily/2026-10-25/show`);
      const iframe = page.locator('iframe');
      await iframe.waitFor({ timeout: 20000 });
      const frame = await iframe.elementHandle().then(handle => handle.contentFrame());
      await frame.locator('#app h1').waitFor();
      assert.equal(await frame.locator('.chapter-nav button').count(), 14);
      await frame.locator('.chapter-nav [data-value="11"]').click();
      await frame.locator('.method-details summary').click();
      assert.equal(await frame.locator('.method-details tbody tr').count(), 8);
      result.embedded.push({ kind, sandbox: await iframe.getAttribute('sandbox'), title: await frame.title(), scene: await frame.locator('#reading-state').innerText() });
      assert.equal(await iframe.getAttribute('sandbox'), 'allow-scripts');
      await page.screenshot({ path: path.join(out, `embedded-${kind}.png`), fullPage: true });
    }
    assert.deepEqual(result.errors, []);
    result.status = 'passed';
  } catch (error) {
    result.status = 'failed'; result.failure = error.stack;
    throw error;
  } finally {
    fs.writeFileSync(path.join(out, 'browser-checks.json'), JSON.stringify(result, null, 2));
    await browser.close();
  }
  console.log(JSON.stringify({ status: result.status, pages: result.pages.length, cases: result.cases.length, embedded: result.embedded, errors: result.errors }, null, 2));
})().catch(error => { console.error(error); process.exitCode = 1; });
