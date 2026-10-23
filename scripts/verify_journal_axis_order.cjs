// 先构建 dist 并启动本地静态预览，再运行本脚本。
const {chromium} = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const vm = require('node:vm');
const {execFileSync} = require('node:child_process');

const base = process.env.JOURNAL_BASE_URL || 'http://127.0.0.1:8030/';
const output = path.resolve('artifacts/journal-axis-order');
const baselineCommit = execFileSync('git', ['rev-parse', 'HEAD'], {encoding: 'utf8'}).trim();
const before = {module: {exports: {}}};
vm.runInNewContext(execFileSync('git', ['show', `${baselineCommit}:site/js/journal-notes.js`], {encoding: 'utf8'}), before);

function inspect() {
  const view = window.JournalView, notes = view.floatingNotes, config = notes.config;
  const cards = notes.rects.map(({node, ...r}) => ({...r, x: node.offsetLeft, y: node.offsetTop, w: node.offsetWidth, h: node.offsetHeight}));
  const routes = [...document.querySelectorAll('.journal-note-route')].map(n => ({id: n.dataset.noteRoute, points: JSON.parse(n.dataset.routePoints)}));
  const hits = (a, b, r) => Math.abs(a.x - b.x) < .1 ? a.x > r.x + .1 && a.x < r.x + r.w - .1 && Math.max(a.y, b.y) > r.y + .1 && Math.min(a.y, b.y) < r.y + r.h - .1 : Math.abs(a.y - b.y) < .1 && a.y > r.y + .1 && a.y < r.y + r.h - .1 && Math.max(a.x, b.x) > r.x + .1 && Math.min(a.x, b.x) < r.x + r.w - .1;
  const violations = [];
  for (const [i, a] of cards.entries()) {
    if (a.x < 0 || a.x + a.w > view.atlas.width + .1 || a.y < 0 || a.y + a.h > Number(config.svg.getAttribute('height')) + .1) violations.push(['bounds', a.id]);
    if (!routes.some(r => r.id === a.id)) violations.push(['missing-route', a.id]);
    for (const b of cards.slice(i + 1)) {
      if (a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y) violations.push(['overlap', a.id, b.id]);
      const axis = config.mode === 'chain' ? 'y' : 'x', anchor = axis === 'x' ? 'anchorX' : 'anchorY', size = axis === 'x' ? 'w' : 'h';
      if ((a[anchor] - b[anchor]) * (a[axis] + a[size] / 2 - b[axis] - b[size] / 2) < -.1) violations.push(['order', a.id, b.id]);
    }
  }
  for (const route of routes) for (let i = 1; i < route.points.length; i++) for (const c of cards) {
    if (route.id !== c.id && hits(route.points[i - 1], route.points[i], c)) violations.push(['crossed-card', route.id, c.id]);
  }
  return {mode: config.mode, cards, violations, bounds: {left: Math.max(view.atlas.dateWidth + 10, config.scroller.scrollLeft + 10), right: Math.min(view.atlas.width - 10, config.scroller.scrollLeft + config.scroller.clientWidth - 10), top: 10, bottom: view.atlas.height}, anchorY: view.atlas.y(config.day.date)};
}

(async () => {
  await fs.mkdir(output, {recursive: true});
  const browser = await chromium.launch({headless: true, channel: 'chrome'});
  const results = [], errors = [];
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1000}, reducedMotion: 'reduce'});
    page.on('pageerror', e => errors.push(e.message));
    await page.route('**/api/report-tags', r => r.fulfill({json: {data: {tags: [], assignments: {}}, revision: 0, canEdit: false}}));
    await page.goto(base + '#/journal/2026-10-20?view=atlas');
    await page.waitForSelector('.journal-floating-note');
    await page.evaluate(() => document.fonts.ready);
    for (const [width, density] of process.env.JOURNAL_INTERACTIONS_ONLY ? [] : [[1440, 14], [1024, 14], [768, 14], [1440, 7]]) {
      await page.setViewportSize({width, height: 1000});
      await page.evaluate(density => {const v = window.JournalView; v.density = density; v.chain = ''; v.selection = null; v.render();}, density);
      const dates = await page.locator('.journal-day-hit').evaluateAll(nodes => nodes.map(n => n.dataset.journalDay));
      const chains = await page.locator('.journal-chain-label').evaluateAll(nodes => nodes.map(n => n.dataset.journalChain));
      let dayCards = 0, chainCards = 0, oldInversions = 0;
      for (const [mode, ids] of [['day', density === 14 ? dates : []], ['chain', chains]]) {
        for (const id of ids) {
          await page.evaluate(({mode, id}) => {const v = window.JournalView; if (mode === 'day') v.select(id); else v.focusChain(id);}, {mode, id});
          const state = await page.evaluate(inspect);
          assert.deepEqual(state.violations, [], `${width}px / ${density}px / ${mode} / ${id}: ${JSON.stringify(state.violations)}`);
          if (mode === 'day') dayCards += state.cards.length; else chainCards += state.cards.length;
          const old = before.module.exports[mode === 'day' ? 'placeCards' : 'placeChainCards'](state.cards, {bounds: state.bounds, anchorY: state.anchorY}).cards;
          for (const [i, a] of old.entries()) for (const b of old.slice(i + 1)) {
            const axis = mode === 'day' ? 'x' : 'y', size = mode === 'day' ? 'w' : 'h', anchor = mode === 'day' ? 'anchorX' : 'anchorY';
            if ((a[anchor] - b[anchor]) * (a[axis] + a[size] / 2 - b[axis] - b[size] / 2) < -.1) oldInversions++;
          }
        }
      }
      results.push({width, density, days: density === 14 ? dates.length : 0, chains: chains.length, dayCards, chainCards, oldInversions});
      console.log(JSON.stringify(results.at(-1)));
    }
    await page.setViewportSize({width: 1440, height: 1000});
    await page.evaluate(() => {const v = window.JournalView; v.density = 14; v.select('2026-10-20'); v.scrollAtlasDay('2026-10-20');});
    await page.screenshot({path: path.join(output, 'day-1440.png')});
    await page.locator('.journal-floating-note.is-focused summary').click();
    await page.evaluate(() => window.JournalView.floatingNotes.layout());
    assert.deepEqual((await page.evaluate(inspect)).violations, [], '展开依据后保序和避让');
    await page.locator('[data-note-action="arrange"]').click();
    const head = page.locator('.journal-floating-note.is-focused .journal-floating-head');
    const oldX = await head.evaluate(n => n.parentElement.offsetLeft);
    await head.press('ArrowRight');
    assert.equal(await head.evaluate(n => n.parentElement.offsetLeft), oldX + 12);
    await head.dblclick();
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const resetState = await page.evaluate(inspect);
    if (resetState.violations.length) await fs.writeFile(path.join(output, 'reset-failure.json'), JSON.stringify({...resetState, routes: await page.locator('.journal-note-route').evaluateAll(nodes => nodes.map(n => ({id:n.dataset.noteRoute, points:JSON.parse(n.dataset.routePoints)})))}, null, 2));
    assert.deepEqual(resetState.violations, [], '双击复位后恢复自动保序');
    await page.locator('[data-note-action="toggle"]').click();
    assert(await page.locator('.journal-floating-notes').isHidden());
    await page.locator('[data-note-action="toggle"]').click();
    const longest = await page.evaluate(() => {const v = window.JournalView; return [...v.chains.keys()].sort((a,b) => v.days.filter(d=>d.chains.includes(b)).length-v.days.filter(d=>d.chains.includes(a)).length)[0];});
    await page.evaluate(id => window.JournalView.focusChain(id), longest);
    await page.locator('.journal-floating-note.is-focused').scrollIntoViewIfNeeded();
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    assert(await page.locator('.journal-floating-note.is-focused').isVisible());
    await page.screenshot({path: path.join(output, 'chain-1440.png')});
    await page.locator('.journal-floating-note.is-focused summary').click();
    await page.evaluate(() => window.JournalView.floatingNotes.layout());
    assert.deepEqual((await page.evaluate(inspect)).violations, [], '长链展开依据后保序和避让');
    await page.setViewportSize({width: 390, height: 844});
    await page.evaluate(() => window.JournalView.select('2026-10-20', true));
    assert.equal(await page.locator('.journal-floating-note:visible').count(), 1);
    await page.locator('[data-note-action="next"]').click();
    assert.equal(await page.locator('.journal-floating-note:visible').count(), 1);
    await page.screenshot({path: path.join(output, 'day-390.png')});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    assert.deepEqual(errors, []);
    if (process.env.JOURNAL_INTERACTIONS_ONLY) results.push(...JSON.parse(await fs.readFile(path.join(output, 'verification.json'), 'utf8')).results);
    await fs.writeFile(path.join(output, 'verification.json'), JSON.stringify({baselineCommit, results, interactions: ['依据展开', '键盘移动', '双击复位', '重新排布', '收放', '手机逐项切换'], errors}, null, 2));
    console.log('交互及截图检查通过');
  } finally {await browser.close();}
})().catch(e => {console.error(e); process.exitCode = 1;});
