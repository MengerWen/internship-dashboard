// 本地服务：python -m http.server 8029 --bind 127.0.0.1
const {chromium} = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const base = process.env.JOURNAL_BASE_URL || 'http://127.0.0.1:8029/dist/';
const output = path.resolve(process.env.JOURNAL_ARTIFACT_DIR || 'artifacts/journal-column-v2');
const offlineDir = process.env.JOURNAL_OFFLINE_DIR || 'dist-offline';

async function settled(page) {
  await page.evaluate(async () => {
    await document.fonts.ready;
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    await Promise.all(document.getAnimations().filter(a => a.effect?.getTiming().iterations !== Infinity).map(a => a.finished.catch(() => {})));
  });
}

async function atTop(page) {
  await page.evaluate(() => {
    document.documentElement.style.scrollBehavior = 'auto';
    document.documentElement.style.overflowAnchor = 'none';
    scrollTo({top: 0, behavior: 'instant'});
  });
  await settled(page);
}

async function containedAnnotations(page, vertical = false) {
  const boxes = await page.locator('.journal-annotation').evaluateAll(nodes => nodes.map(n => {
    const r = n.getBoundingClientRect(), parent = n.closest('.journal-canvas').getBoundingClientRect();
    return {left: r.left - parent.left, top: r.top - parent.top, right: r.right - parent.left, bottom: r.bottom - parent.top, width: parent.width, height: parent.height};
  }));
  boxes.forEach(b => {
    assert(b.left >= -.1 && b.right <= b.width + .1, JSON.stringify(b));
    assert(b.top >= -.1 && b.bottom <= b.height + .1, JSON.stringify(b));
  });
  for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) {
    const a = boxes[i], b = boxes[j];
    assert(a.right <= b.left || b.right <= a.left || a.bottom <= b.top || b.bottom <= a.top, '注解不能互相重叠');
    if (vertical) assert(a.bottom <= b.top, '纵向注解按日期向下排列');
  }
}

async function capture(page, name, fullPage = false) {
  if (fullPage) await atTop(page);
  await settled(page);
  await page.screenshot({path: path.join(output, name + '.png'), fullPage});
}

async function restDayBands(page) {
  const bands = await page.locator('.journal-rest-day').evaluateAll(nodes => nodes.map(n => ({date: n.dataset.date, label: n.dataset.restDay, height: Number(n.getAttribute('height')), pointerEvents: getComputedStyle(n).pointerEvents})));
  assert.equal(new Set(bands.map(b => b.date)).size, bands.length, '每个休息日只着一次底纹');
  for (const date of ['2026-09-25', '2026-09-26', '2026-09-27']) assert.equal(bands.find(b => b.date === date)?.label, '中秋节', date);
  for (let day = 1; day <= 7; day++) assert.equal(bands.find(b => b.date === `2026-10-0${day}`)?.label, '国庆节');
  for (const date of ['2026-09-20', '2026-09-28', '2026-09-30', '2026-10-08', '2026-10-10']) assert(!bands.some(b => b.date === date), date);
  assert.equal(bands.find(b => b.date === '2026-10-11')?.label, '周末');
  const density = Number(await page.locator('#journal-density').inputValue());
  assert(bands.every(b => b.height === density && b.pointerEvents === 'none'), '底纹随密度变化且不拦截点击');
  return bands.length;
}

(async () => {
  await fs.mkdir(output, {recursive: true});
  const manifest = JSON.parse(await fs.readFile('dist/manifest.json', 'utf8'));
  const tags = JSON.parse(await fs.readFile('content/report-tags.json', 'utf8'));
  const days = manifest.journal;
  assert.equal(days.length, 88);
  assert.equal(manifest.chains.chains.length, 28);
  const noteCount = days.reduce((n, d) => n + Object.keys(d.chain_notes).length, 0);
  assert.equal(noteCount, 151);
  assert(days.every(d => d.chains.every(cid => d.chain_notes[cid].note.length > 0 && d.chain_notes[cid].note.length <= 24)));
  const dropped = days.flatMap(d => d.chains.filter(cid => d.chain_notes[cid].outcome === 'dropped').map(cid => ({date: d.date, cid})));
  assert.equal(dropped.length, 5);
  assert(days.every(d => d.highlights.length > 0 && d.highlights.length <= 3));
  assert.deepEqual(days.find(d => d.date === '2026-07-06').reports_covering, ['2026-07-07']);
  assert(!days.some(d => d.reports_covering.includes('2026-07-06')), '示例日报不能作为真实工作的根据');
  const browser = await chromium.launch({headless: true, channel: 'chrome'});
  const results = [];
  try {
    for (const width of [1440, 768, 390]) {
      const context = await browser.newContext({viewport: {width, height: 900}});
      // 静态预览没有标签 API；只对既有接口提供只读快照。
      await context.route('**/api/report-tags', route => route.fulfill({json: {data: tags, revision: 0, canEdit: false}}));
      const page = await context.newPage(), errors = [];
      page.on('pageerror', e => errors.push(e.message));
      page.on('console', e => { if (e.type() === 'error') errors.push(e.text()); });
      await page.goto(base + '#/journal');
      await page.waitForSelector('#view-journal.is-active');
      assert.equal(await page.locator('#journal-list').isVisible(), width < 860);
      await page.locator('[data-journal-view="list"]').click();
      assert.equal(await page.locator('#journal-list tbody tr').count(), days.length);
      await page.locator('#journal-find').fill('2026-10-14');
      assert.equal(await page.locator('#journal-list tbody tr').count(), 1);
      await page.locator('#journal-find').fill('不存在的关键词');
      assert(await page.locator('.journal-empty').isVisible());
      await page.locator('#journal-find').fill('');
      await capture(page, `list-${width}`);
      await page.locator('[data-journal-view="atlas"]').click();
      await settled(page);
      assert.equal(await page.locator('.journal-chain-label').count(), 28);
      assert.equal(await page.locator('.journal-chain-unit').count(), 28);
      assert.equal(await page.locator('.journal-day-hit').count(), days.length);
      assert.equal(await page.locator('.journal-point-hit').count(), noteCount);
      assert.equal(await page.locator('.journal-annotation').count(), 0);
      const restDays = await restDayBands(page);
      assert.equal(await page.locator('.journal-handoff[data-chains="ml-330 model-report"]').getAttribute('data-date'), '2026-09-21');
      assert.deepEqual(await page.locator('.journal-handoff').evaluateAll(nodes => [...new Set(nodes.map(n => n.dataset.type))].sort()), ['依赖解除', '延续', '收口', '派生'].sort());
      const columns = await page.locator('.journal-chain-unit').evaluateAll(nodes => nodes.map(n => Number(n.dataset.chainX)).sort((a, b) => a - b));
      assert.equal(new Set(columns).size, 28);
      const minimumGap = Math.min(...columns.slice(1).map((v, i) => v - columns[i]));
      if (width === 1440) assert(minimumGap >= 35, `最小列距 ${minimumGap}`);
      const labels = await page.locator('.journal-chain-label').evaluateAll(nodes => nodes.map(n => {
        const r = n.getBoundingClientRect(); return {left: r.left, right: r.right, top: r.top, bottom: r.bottom};
      }));
      for (let i = 0; i < labels.length; i++) for (let j = i + 1; j < labels.length; j++) {
        assert(labels[i].right <= labels[j].left || labels[j].right <= labels[i].left, '列头名字不能重叠');
      }
      const ratios = await page.locator('.journal-day-hit').evaluateAll(nodes => {
        const y = d => Number(nodes.find(n => n.dataset.journalDay === d).getAttribute('y'));
        return (y('2026-10-07') - y('2026-09-23')) / (y('2026-10-08') - y('2026-10-07'));
      });
      assert(Math.abs(ratios - 14) < .0001, '时间空档保持真实日期间距');
      assert.equal(await page.locator('.journal-report-tick').count(), days.filter(d => d.reports_published.length).length);
      for (const entry of dropped) {
        assert.equal(await page.locator(`path.journal-cross[data-date="${entry.date}"][data-chain="${entry.cid}"]`).count(), 1);
        assert.equal(await page.locator(`circle.journal-dot[data-date="${entry.date}"][data-chain="${entry.cid}"]`).count(), 0);
      }
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      await atTop(page);
      await capture(page, `atlas-standard-${width}`, true);
      assert.equal(await page.locator('.journal-heading p').count(), 0);
      for (const selector of [
        '.journal-day-hit[data-journal-day="2026-07-08"]',
        '.journal-chain-label[data-journal-chain="algobench"]',
        '.journal-point-hit[data-date="2026-07-08"][data-journal-point="algobench"]',
      ]) {
        await page.locator(selector).click();
        assert(await page.locator('#journal-clear').isVisible());
        await page.locator('.journal-annotation').first().click();
        assert(await page.locator('#journal-clear').isVisible(), '阅读说明卡不应取消选中');
        await page.locator('.journal-scroller').evaluate(n => { n.scrollLeft = 0; });
        const y = Number(await page.locator('.journal-day-hit[data-journal-day="2026-07-08"]').getAttribute('y')) + 5;
        await page.locator('.journal-atlas').click({position: {x: 110, y}});
        assert.equal(await page.locator('.journal-annotation').count(), 0, '工作日行上的图内空白也能取消选中');
        assert.equal(await page.locator('#journal-clear').isVisible(), false);
        assert(!page.url().includes('/2026-') && !page.url().includes('chain=') && !page.url().includes('point='));
        await page.locator(selector).click();
        await atTop(page);
        await page.mouse.click(5, 200);
        assert.equal(await page.locator('.journal-annotation').count(), 0, '页面外侧空白可取消三种选择');
      }
      const hoverBefore = await page.locator('#journal-figure').innerHTML();
      await page.locator('.journal-day-hit[data-journal-day="2026-07-08"]').hover({position: {x: 30, y: 5}});
      await page.mouse.move(150, 200);
      assert.equal(await page.locator('#journal-figure').innerHTML(), hoverBefore, '鼠标移动不改变图或说明');
      const date = '2026-07-08', day = days.find(d => d.date === date);
      await page.locator(`.journal-day-hit[data-journal-day="${date}"]`).click({position: {x: 30, y: 5}});
      assert.equal(await page.locator('[data-selected-date]').getAttribute('data-selected-date'), date);
      assert.equal(await page.locator('.journal-annotation').count(), day.chains.length);
      assert.equal(await page.locator('.journal-selection-ring').count(), day.chains.length);
      assert((await page.locator('#journal-highlights').textContent()).includes(day.highlights[0]));
      assert(!(await page.locator('#journal-highlights').textContent()).includes('研究台架与注意力面板接入正式因子引擎'));
      const line = await page.locator('.journal-selection-line').getAttribute('d');
      assert(line.startsWith('M86,'));
      await containedAnnotations(page);
      await capture(page, `day-${width}`);
      if (width === 1440) {
        const initialWidth = Number(await page.locator('.journal-atlas').getAttribute('width'));
        await page.setViewportSize({width: 1280, height: 900});
        await page.waitForFunction(w => Number(document.querySelector('.journal-atlas').getAttribute('width')) < w, initialWidth);
        assert.equal(await page.locator('.journal-chain-label').first().evaluate(n => getComputedStyle(n).fontSize), '12.5px');
        assert.equal(await page.locator('.journal-selection-ring').count(), day.chains.length);
        await containedAnnotations(page);
        await page.setViewportSize({width, height: 900});
        await page.waitForFunction(w => Number(document.querySelector('.journal-atlas').getAttribute('width')) === w, initialWidth);
        await page.evaluate(() => scrollTo({top: 800, behavior: 'instant'}));
        await settled(page);
        assert(Math.abs((await page.locator('.journal-atlas-header').boundingBox()).y - 126) < 2, '列头应在固定刊头下吸顶');
        await capture(page, 'sticky-header-1440');
        await atTop(page);
      }
      for (const density of ['7', '17', '11']) {
        await page.locator('#journal-density').selectOption(density);
        await restDayBands(page);
        assert.equal(await page.locator('[data-selected-date]').getAttribute('data-selected-date'), date);
        assert.equal(await page.locator('.journal-selection-ring').count(), day.chains.length);
        await containedAnnotations(page);
      }
      await page.locator('#journal-clear').click();
      await page.locator(`.journal-point-hit[data-date="${date}"][data-journal-point="algobench"]`).click();
      assert.equal(await page.locator('.journal-annotation').count(), 1);
      assert.equal(await page.locator('.journal-selection-ring').count(), 1);
      assert.equal(await page.locator('.journal-chain-label.is-selected').count(), 1);
      await containedAnnotations(page);
      await capture(page, `point-${width}`);
      await page.reload();
      await page.waitForSelector('.journal-selection-ring');
      assert.equal(await page.locator('.journal-annotation').count(), 1, '单点深链刷新后保持选中');
      const canvasHeight = Number(await page.locator('.journal-atlas').getAttribute('height'));
      await page.locator('.journal-atlas').click({position: {x: 12, y: canvasHeight - 5}});
      assert.equal(await page.locator('.journal-annotation').count(), 0, '点击空白取消选中');
      await page.locator('.journal-chain-label[data-journal-chain="open5m"]').click();
      await settled(page);
      assert(await page.locator('.journal-chain-card').isVisible());
      assert.equal(await page.locator('.journal-chain-annotation').count(), days.filter(d => d.chains.includes('open5m')).length);
      const opacity = await page.locator('.journal-chain-label').evaluateAll(nodes => nodes.map(n => ({id: n.dataset.journalChain, opacity: Number(getComputedStyle(n).opacity)})));
      assert.equal(opacity.find(v => v.id === 'open5m').opacity, 1);
      assert(opacity.filter(v => v.id !== 'open5m').every(v => v.opacity <= .3));
      assert(await page.locator('.journal-chain-unit.is-dimmed').evaluateAll(nodes => nodes.every(n => Number(getComputedStyle(n).opacity) <= .2)));
      await containedAnnotations(page, true);
      if (width === 390) assert(await page.locator('.journal-chain-annotation').evaluateAll(nodes => nodes.every(n => {
        const r = n.getBoundingClientRect(), viewport = n.closest('.journal-scroller').getBoundingClientRect();
        return r.left >= viewport.left && r.right <= viewport.right;
      })), '窄屏选中链条后，注解应直接出现在可见范围');
      await capture(page, `chain-${width}`, true);
      await page.locator('.journal-chain-label[data-journal-chain="open5m"]').press('Escape');
      assert.equal(await page.locator('.journal-annotation').count(), 0);
      await page.locator(`.journal-day-hit[data-journal-day="${date}"]`).press('Enter');
      assert.equal(await page.locator('[data-selected-date]').getAttribute('data-selected-date'), date);
      await page.locator(`.journal-day-hit[data-journal-day="${date}"]`).press('ArrowDown');
      assert.equal(await page.locator('[data-selected-date]').getAttribute('data-selected-date'), '2026-07-09');
      await page.locator('.journal-day-hit[data-journal-day="2026-07-08"]').press('ArrowUp');
      assert.equal(await page.locator('[data-selected-date]').getAttribute('data-selected-date'), date);
      await page.locator(`.journal-day-hit[data-journal-day="${date}"]`).press('ArrowRight');
      assert.equal(await page.locator('.journal-selection-ring').count(), 1);
      await page.locator('.journal-atlas').press('Escape');
      await page.locator('#journal-density').selectOption('7');
      await atTop(page);
      const compactHeight = await page.locator('.journal-atlas').evaluate(n => n.getBoundingClientRect().height + document.querySelector('.journal-atlas-header').getBoundingClientRect().height);
      assert(compactHeight <= 1000, `紧凑整图高度 ${compactHeight}`);
      await capture(page, `atlas-compact-${width}`, true);
      await page.locator('#journal-density').selectOption('17');
      await capture(page, `atlas-relaxed-${width}`, true);
      await page.locator('#journal-window').selectOption('1m');
      await page.locator('.journal-chain-label[data-journal-chain="onboarding"]').click();
      assert((await page.locator('#journal-count').textContent()).startsWith('0 个记录日'));
      assert(await page.locator('.journal-chain-card .journal-window-empty').isVisible());
      assert.equal(await page.locator('.journal-selection-line').count(), 0);
      await page.locator('#journal-clear').click();
      await page.locator('#journal-density').selectOption('7');
      const fresh = await context.newPage();
      await fresh.goto(base + '#/journal');
      await fresh.waitForSelector('#view-journal.is-active');
      await fresh.locator('[data-journal-view="atlas"]').click();
      assert.equal(await fresh.locator('#journal-density').inputValue(), '7');
      assert.equal(await fresh.locator('#journal-window').inputValue(), '1m');
      await restDayBands(fresh);
      await fresh.close();
      await page.locator('#journal-window').selectOption('all');
      await page.goto(base + '#/journal/2026-10-14?view=atlas');
      await page.waitForSelector('[data-selected-date="2026-10-14"]');
      const evidenceRequests = [];
      page.on('request', r => { if (r.url().includes('/journal/_evidence/')) evidenceRequests.push(r.url()); });
      assert.equal(evidenceRequests.length, 0);
      await page.locator('.journal-evidence > summary').click();
      await page.waitForSelector('.journal-repo');
      assert.equal(evidenceRequests.length, 1);
      await page.locator('.journal-repo > summary').first().click();
      assert(await page.locator('.journal-repo a[href^="https://github.com/"]').count());
      await capture(page, `evidence-${width}`);
      await page.locator('.journal-day-nav [data-journal-nav="后一天"]').press('Enter');
      assert.equal(await page.locator('[data-selected-date]').getAttribute('data-selected-date'), '2026-10-15');
      assert.equal(await page.evaluate(() => document.activeElement?.dataset.journalNav), '后一天');
      await page.goto(base + '#/journal/2026-08-07?view=atlas');
      await page.waitForSelector('[data-selected-date="2026-08-07"]');
      await page.locator('.journal-evidence > summary').click();
      await page.waitForSelector('.journal-repo');
      assert((await page.locator('#journal-evidence-content').textContent()).includes('本日回滚'));
      if (width === 1440) {
        const indexed = await page.evaluate(async () => {
          const search = await import('./pagefind/pagefind.js');
          const hits = await search.search('价格硬筛选');
          const data = await Promise.all(hits.results.map(hit => hit.data()));
          return data.some(hit => hit.meta.type === 'journal');
        });
        assert(indexed, '搜索应包含逐点注解');
      }
      for (const route of ['#/daily/2026-10-18/show', '#/showcase/factor', '#/journal?view=list']) {
        await page.goto(base + route);
        await settled(page);
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
      }
      assert.deepEqual(errors, []);
      results.push({width, days: days.length, chains: 28, notes: noteCount, restDays, minimumGap, compactHeight, errors});
      await context.close();
    }
    const context = await browser.newContext({viewport: {width: 1440, height: 900}, reducedMotion: 'reduce'});
    const fixture = structuredClone(manifest);
    fixture.chains.chains.find(c => c.id === 'onboarding').fate = 'dropped';
    fixture.chains.chains.find(c => c.id === 'doris-migration').fate = 'parked';
    fixture.journal.filter(d => d.chains.includes('onboarding')).forEach(d => { d.chain_notes.onboarding.outcome = 'dropped'; });
    await context.route('**/manifest.json', route => route.fulfill({json: fixture}));
    await context.route('**/api/report-tags', route => route.fulfill({json: {data: tags, revision: 0, canEdit: false}}));
    const synthetic = await context.newPage();
    await synthetic.goto(base + '#/journal?view=atlas&window=all');
    await synthetic.waitForSelector('.journal-chain-label.is-dropped');
    assert((await synthetic.locator('.journal-chain-label[data-journal-chain="onboarding"] .journal-chain-name').evaluate(n => getComputedStyle(n).textDecorationLine)).includes('line-through'));
    assert.equal(await synthetic.locator('.journal-chain-unit[data-chains="onboarding"] circle.journal-dot').count(), 0);
    assert.equal(await synthetic.locator('.journal-chain-unit[data-chains="onboarding"] path.journal-cross').count(), 2);
    assert.equal(await synthetic.locator('.journal-chain-unit[data-chains="doris-migration"] .journal-seal.is-parked').count(), 1);
    assert(await synthetic.locator('.journal-seal.is-parked').evaluate(n => getComputedStyle(n).fill !== getComputedStyle(n).stroke));
    await capture(synthetic, 'synthetic-dropped-parked', true);
    await synthetic.locator('.journal-day-hit[data-journal-day="2026-07-15"]').click({position: {x: 30, y: 5}});
    const reduced = await synthetic.locator('.journal-day-card').evaluate(n => ({name: getComputedStyle(n).animationName, transform: getComputedStyle(n).transform}));
    assert(['none', 'journal-opacity'].includes(reduced.name), JSON.stringify(reduced));
    assert.equal(reduced.transform, 'none');
    results.push({synthetic: true, droppedHeader: true, parkedSeal: true, reducedMotion: true});
    await context.close();
    const offline = await browser.newPage();
    const offlineRequests = [], offlineErrors = [];
    offline.on('request', r => { if (/^https?:/.test(r.url())) offlineRequests.push(r.url()); });
    offline.on('pageerror', e => offlineErrors.push(e.message));
    await offline.goto(pathToFileURL(path.resolve(offlineDir, 'index.html')).href + '#/journal/2026-10-14?view=atlas');
    await offline.waitForSelector('.journal-evidence');
    await offline.locator('.journal-evidence > summary').click();
    await offline.waitForSelector('.journal-repo');
    assert.equal(await offline.locator('.journal-chain-label').count(), 28);
    await restDayBands(offline);
    assert.equal(await offline.locator('.journal-annotation').count(), days.find(d => d.date === '2026-10-14').chains.length);
    assert.deepEqual(offlineRequests, []);
    assert.deepEqual(offlineErrors, []);
    results.push({offline: true, requests: offlineRequests, errors: offlineErrors});
    await offline.close();
    await fs.writeFile(path.join(output, 'verification.json'), JSON.stringify(results, null, 2) + '\n');
    console.log(JSON.stringify(results, null, 2));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
