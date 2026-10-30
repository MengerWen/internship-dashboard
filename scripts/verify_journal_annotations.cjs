// 先构建并启动静态预览，再运行本脚本；可用 JOURNAL_BASE_URL 指定预览地址。
const {chromium} = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');

const base = process.env.JOURNAL_BASE_URL || 'http://127.0.0.1:8029/dist/';
const output = require('./artifact_paths.cjs').artifactDirectory('journal-annotations');

async function checkAnnotations(page, label) {
  const boxes = await page.locator('.journal-annotation').evaluateAll(nodes => nodes.map(node => {
    const box = node.getBoundingClientRect(), canvas = node.closest('.journal-canvas').getBoundingClientRect();
    return {
      chain: node.dataset.annotationChain,
      left: box.left - canvas.left, right: box.right - canvas.left,
      top: box.top - canvas.top, bottom: box.bottom - canvas.top,
      width: canvas.width, height: canvas.height,
      textFits: node.scrollWidth <= node.clientWidth,
    };
  }));
  assert(boxes.length, `${label}：应显示注解`);
  for (const box of boxes) {
    assert(box.left >= 0 && box.right <= box.width + 0.1, `${label}：注解超出左右边界 ${JSON.stringify(box)}`);
    assert(box.top >= 0 && box.bottom <= box.height + 0.1, `${label}：注解超出上下边界 ${JSON.stringify(box)}`);
    assert(box.textFits, `${label}：文字应完整换行`);
  }
  for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
    const a = boxes[i], b = boxes[j];
    assert(a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top, `${label}：注解互相遮挡`);
  }
  return boxes.length;
}

(async () => {
  await fs.mkdir(output, {recursive: true});
  const tags = JSON.parse(await fs.readFile(path.join(__dirname, '../content/report-tags.json'), 'utf8'));
  const browser = await chromium.launch({headless: true, channel: 'chrome'});
  try {
    const page = await browser.newPage({viewport: {width: 2560, height: 1270}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/api/report-tags', route => route.fulfill({json: {data: tags, revision: 0, canEdit: false}}));
    await page.goto(base + '#/journal/2026-10-20?view=atlas');
    await page.waitForSelector('.journal-annotation');
    await page.evaluate(() => document.fonts.ready);
    await page.locator('.journal-day-hit[data-journal-day="2026-10-20"]').scrollIntoViewIfNeeded();
    await page.screenshot({path: path.join(output, '2026-10-20.png')});
    await checkAnnotations(page, '截图原场景 2560px / 2026-10-20');

    const results = [];
    for (const width of [2560, 1920, 1440, 1024, 860, 768, 640, 390]) {
      await page.setViewportSize({width, height: 1000});
      await page.evaluate(() => { window.JournalView.renderAtlas(); });
      const dates = await page.locator('.journal-day-hit').evaluateAll(nodes => nodes.map(node => node.dataset.journalDay));
      let checked = 0;
      for (const date of dates) {
        await page.evaluate(date => window.JournalView.select(date), date);
        checked += await checkAnnotations(page, `${width}px / ${date}`);
      }
      for (const cid of await page.evaluate(() => {
        const day = window.JournalView.days.find(day => day.date === '2026-10-20');
        return [day.chains[0], day.chains.at(-1)];
      })) {
        await page.evaluate(cid => window.JournalView.select('2026-10-20', false, cid), cid);
        await checkAnnotations(page, `${width}px / 单点 ${cid}`);
      }
      await page.evaluate(() => window.JournalView.select('2026-10-20'));
      await page.locator('.journal-day-hit[data-journal-day="2026-10-20"]').scrollIntoViewIfNeeded();
      await page.screenshot({path: path.join(output, `2026-10-20-${width}.png`)});
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, '页面不能出现横向溢出');
      results.push({width, days: dates.length, annotations: checked});
    }
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({results, errors, screenshots: output}, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
