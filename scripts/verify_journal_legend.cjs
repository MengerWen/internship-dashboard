const {chromium} = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const base = process.env.JOURNAL_BASE_URL || 'http://127.0.0.1:8034/dist/';
const output = path.resolve(process.env.JOURNAL_ARTIFACT_DIR || 'artifacts/journal-legend');
const offlineDir = process.env.JOURNAL_OFFLINE_DIR || 'dist-offline';
const types = ['延续', '派生', '依赖解除', '收口'];

async function settled(page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    await Promise.all(document.getAnimations().filter(a => a.effect?.getTiming().iterations !== Infinity).map(a => a.finished.catch(() => {})));
  });
}

async function selection(page, type) {
  await settled(page);
  assert.deepEqual(await page.locator('[data-journal-handoff][aria-pressed="true"]').evaluateAll(nodes => nodes.map(n => n.dataset.journalHandoff)), type ? [type] : []);
  const edges = await page.locator('.journal-handoff').evaluateAll(nodes => nodes.map(n => ({
    type: n.dataset.type, opacity: Number(getComputedStyle(n).opacity),
    stroke: getComputedStyle(n.querySelector('.journal-handoff-path')).stroke,
    width: Number.parseFloat(getComputedStyle(n.querySelector('.journal-handoff-path')).strokeWidth)
  })));
  const focus = await page.locator('.journal-atlas').evaluate(svg => getComputedStyle(svg).getPropertyValue('--focus').trim());
  const rgb = /^#([\da-f]{2})([\da-f]{2})([\da-f]{2})$/i.exec(focus);
  const color = `rgb(${rgb.slice(1).map(s => Number.parseInt(s, 16)).join(', ')})`;
  assert(edges.some(e => e.type === type) || !type, '真实数据中应有匹配交接');
  for (const edge of edges) {
    assert.equal(edge.opacity, !type || edge.type === type ? 1 : .13);
    assert.equal(edge.width, type && edge.type === type ? 2.6 : 1);
    if (type && edge.type === type) assert.equal(edge.stroke, color);
  }
  return edges.length;
}

async function verify(page, url, width) {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(url);
  await page.waitForSelector('.journal-atlas');
  const button = type => page.locator(`[data-journal-handoff="${type}"]`);
  await selection(page, null);
  for (const type of types) {
    await button(type).click();
    await selection(page, type);
    assert.equal(await button(type).evaluate(n => n === document.activeElement), true, '点击后保留按钮焦点');
  }
  await page.locator('.journal-scroller').evaluate(n => { n.scrollLeft = n.scrollWidth - n.clientWidth; });
  await settled(page);
  await page.screenshot({path: path.join(output, `${url.startsWith('file:') ? 'offline-' : ''}${width}-report-highlight.png`)});
  await button('收口').click();
  await selection(page, null);
  await button('派生').focus();
  await page.keyboard.press('Enter');
  await selection(page, '派生');
  await page.keyboard.press('ArrowDown');
  await selection(page, '派生');
  await page.keyboard.press('Space');
  await selection(page, null);
  await button('延续').click();
  await page.keyboard.press('Escape');
  await selection(page, null);
  await button('依赖解除').click();
  await page.locator('#journal-density').selectOption('7');
  await selection(page, '依赖解除');
  await page.locator('#journal-window').selectOption('3m');
  await selection(page, '依赖解除');
  await page.setViewportSize({width: width + 20, height: 1000});
  await selection(page, '依赖解除');
  await page.locator('#journal-clear').click();
  await selection(page, null);
  await button('延续').click();
  await page.locator('#journal-title').click();
  await selection(page, null);
  await page.locator('.journal-chain-label[data-journal-chain="algobench"]').click();
  assert.equal(await page.locator('.journal-chain-card').count(), 1);
  await button('派生').click();
  await selection(page, '派生');
  assert.equal(await page.locator('.journal-chain-card').count(), 0);
  await page.locator('.journal-day-hit[data-journal-day="2026-08-03"]').click();
  assert.equal(await page.locator('[data-journal-handoff][aria-pressed="true"]').count(), 0);
  assert.equal(await page.locator('[data-selected-date="2026-08-03"]').count(), 1);
  await button('收口').click();
  await selection(page, '收口');
  assert.equal(await page.locator('.journal-annotation').count(), 0);
  assert(await page.locator('[data-journal-handoff]').evaluateAll(nodes => nodes.every(n => n.getBoundingClientRect().height >= 44)));
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), '窄屏页面不溢出');
  assert.deepEqual(errors, []);
  return {width, edges: await page.locator('.journal-handoff').count(), errors};
}

(async () => {
  await fs.mkdir(output, {recursive: true});
  const browser = await chromium.launch({headless: true, channel: 'chrome'});
  const results = [];
  try {
    for (const width of [1440, 768, 390]) {
      const page = await browser.newPage({viewport: {width, height: 1000}, reducedMotion: 'reduce'});
      results.push(await verify(page, base + '#/journal?view=atlas', width));
      await page.close();
    }
    const page = await browser.newPage({viewport: {width: 1440, height: 1000}, reducedMotion: 'reduce'});
    const requests = [];
    page.on('request', r => { if (/^https?:/.test(r.url())) requests.push(r.url()); });
    results.push({offline: await verify(page, pathToFileURL(path.resolve(offlineDir, 'index.html')).href + '#/journal?view=atlas', 1440)});
    assert.deepEqual(requests, []);
    await fs.writeFile(path.join(output, 'results.json'), JSON.stringify(results, null, 2));
    console.log(JSON.stringify(results, null, 2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
