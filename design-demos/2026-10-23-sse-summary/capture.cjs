const { chromium } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');

(async () => {
  const root = __dirname;
  const shots = path.join(root, 'screenshots');
  fs.mkdirSync(shots, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const reviewOnly = process.argv.includes('--review-only');
  const results = reviewOnly ? JSON.parse(fs.readFileSync(path.join(root, 'preview-checks.json'), 'utf8')).results : [];
  const errors = [];
  const base = 'http://127.0.0.1:8769/design-demos/2026-10-23-sse-summary/';
  const page = await browser.newPage();
  page.on('pageerror', error => errors.push(error.message));
  for (const variant of reviewOnly ? [] : ['a', 'b', 'c']) {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto(base + `dir-${variant}.html`, { waitUntil: 'networkidle' });
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: path.join(shots, `${variant}-desktop.png`) });
    await page.screenshot({ path: path.join(shots, `${variant}-full.png`), fullPage: true });
    const desktop = await page.evaluate(() => ({
      title: document.querySelector('h1').textContent,
      sections: document.querySelectorAll('section.chapter').length,
      details: document.querySelectorAll('details').length,
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: innerWidth,
      scrollHeight: document.documentElement.scrollHeight,
      serif: document.fonts.check('16px ReportSerif'),
    }));
    await page.locator('.order-demo:visible button[data-order="pure"]').first().click();
    if (!await page.locator('.order-demo:visible .order-answer').first().textContent().then(x => x.includes('600'))) {
      throw new Error(`${variant}: order interaction failed`);
    }
    await page.locator('.order-demo:visible button[data-order="partial"]').first().click();
    const summary = page.getByText('研究模型线做过什么，为什么没有充当生产真值', { exact: true });
    await summary.click();
    if (!await summary.locator('..').getAttribute('open').then(x => x !== null)) throw new Error('Details did not open');
    await summary.click();
    for (const width of [768, 390, 375]) {
      await page.setViewportSize({ width, height: width === 768 ? 1024 : 844 });
      await page.goto(base + `dir-${variant}.html`, { waitUntil: 'networkidle' });
      const metrics = await page.evaluate(() => ({
        width: innerWidth, documentWidth: document.documentElement.scrollWidth,
        h1Width: document.querySelector('h1').getBoundingClientRect().width,
      }));
      if (metrics.documentWidth > width + 1) throw new Error(`${variant}: overflow at ${width}: ${metrics.documentWidth}`);
      await page.screenshot({ path: path.join(shots, `${variant}-${width}.png`), fullPage: width === 390 });
    }
    results.push({ variant, desktop, interactions: ['pure-order', 'partial-order', 'details-open-close'], widths: [1440, 768, 390, 375] });
  }
  await page.setViewportSize({ width: 1440, height: 1120 });
  await page.goto(base + 'thumbs.html', { waitUntil: 'networkidle' });
  await page.screenshot({ path: path.join(shots, 'six-directions.png'), fullPage: true });
  await page.goto(base + 'index.html?variant=A', { waitUntil: 'networkidle' });
  await page.screenshot({ path: path.join(shots, 'review.png') });
  await page.locator('[data-variant="C"]').click();
  if (!await page.locator('#preview').getAttribute('src').then(x => x === 'dir-c.html')) throw new Error('Switcher did not update iframe');
  if (!page.url().includes('variant=C')) throw new Error('Switcher did not update URL');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(base + 'index.html?variant=B', { waitUntil: 'networkidle' });
  if (await page.evaluate(() => document.documentElement.scrollWidth) > 391) throw new Error('Review page overflow');
  await page.screenshot({ path: path.join(shots, 'review-mobile.png'), fullPage: true });
  await page.goto('file:///' + path.join(root, 'dir-a.html').replaceAll('\\', '/'), { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  if (!await page.title().then(x => x.includes('沪市'))) throw new Error('File URL did not open');
  if (!await page.evaluate(() => document.fonts.check('16px ReportSerif'))) throw new Error('File URL font failed');
  if (errors.length) throw new Error(errors.join('\n'));
  const report = { results, consoleErrors: errors, reviewSwitcher: 'passed', fileUrl: 'passed', screenshotRoot: shots };
  fs.writeFileSync(path.join(root, 'preview-checks.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report));
  await browser.close();
})().catch(error => { console.error(error); process.exitCode = 1; });
