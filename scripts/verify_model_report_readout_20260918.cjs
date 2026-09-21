const { chromium } = require('@playwright/test');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto('http://127.0.0.1:8019/content/daily/2026-09-18.show.html');
  await page.waitForFunction(() => window.__readoutReady === true);

  // 1. The overlay's data-to-pixel mapping must land on the marks matplotlib drew.
  const drift = await page.evaluate(() => {
    const specs = JSON.parse(document.getElementById('readout-data').textContent);
    const rectOf = svg => svg.querySelector('g[id$="-axes_1"] g[id*="-patch_"] > path').getBoundingClientRect();
    const centres = nodes => [...nodes].map(n => {
      const b = n.getBoundingClientRect();
      return [b.left + b.width / 2, b.top + b.height / 2];
    });
    const worst = (wanted, drawn) => {
      let far = 0;
      for (const [x, y] of wanted) {
        let best = Infinity;
        for (const [dx, dy] of drawn) best = Math.min(best, Math.hypot(x - dx, y - dy));
        far = Math.max(far, best);
      }
      return far;
    };
    const out = {};

    const scatter = document.querySelector('#ic-scatter svg');
    const sr = rectOf(scatter);
    const sa = specs['ic-scatter'].axes[0];
    out.scatter = {
      points: specs['ic-scatter'].items.length,
      drawn: scatter.querySelectorAll('g[id$="-PathCollection_1"] use').length,
      drift: worst(specs['ic-scatter'].items.map(i => [
        sr.left + (i.x - sa.xlim[0]) / (sa.xlim[1] - sa.xlim[0]) * sr.width,
        sr.bottom - (i.y - sa.ylim[0]) / (sa.ylim[1] - sa.ylim[0]) * sr.height,
      ]), centres(scatter.querySelectorAll('g[id$="-PathCollection_1"] use'))),
    };

    // tail-breadth carries a second y axis; its Sharpe markers prove axis 1 maps too.
    const twin = document.querySelector('#tail-breadth svg');
    const tr = rectOf(twin);
    const ta = specs['tail-breadth'].axes;
    const sharpeMarks = specs['tail-breadth'].items.map(item => item.marks.find(m => m[3] === 1));
    out.twin = {
      marks: sharpeMarks.length,
      drawn: twin.querySelectorAll('g[id$="-axes_2"] g[id$="-line2d_18"] use').length,
      drift: worst(sharpeMarks.map(([x, y, , axis]) => [
        tr.left + (x - ta[0].xlim[0]) / (ta[0].xlim[1] - ta[0].xlim[0]) * tr.width,
        tr.bottom - (y - ta[axis].ylim[0]) / (ta[axis].ylim[1] - ta[axis].ylim[0]) * tr.height,
      ]), centres(twin.querySelectorAll('g[id$="-axes_2"] g[id$="-line2d_18"] use'))),
    };
    return out;
  });

  // 2. Hovering each figure must name the value under the cursor.
  const keys = await page.evaluate(() =>
    Object.keys(JSON.parse(document.getElementById('readout-data').textContent)));
  assert.equal(keys.length, 27);
  const checked = [];
  for (const key of keys) {
    const target = await page.evaluate(k => {
      const specs = JSON.parse(document.getElementById('readout-data').textContent);
      const spec = specs[k];
      const figure = document.getElementById(k);
      figure.scrollIntoView({ block: 'center', behavior: 'instant' });
      const svg = figure.querySelector('svg');
      const r = svg.querySelector('g[id$="-axes_1"] g[id*="-patch_"] > path').getBoundingClientRect();
      const ax = spec.axes[0];
      const toX = v => r.left + (v - ax.xlim[0]) / (ax.xlim[1] - ax.xlim[0]) * r.width;
      const toY = v => r.bottom - (v - ax.ylim[0]) / (ax.ylim[1] - ax.ylim[0]) * r.height;
      const clamp = (v, lo, hi) => Math.min(hi - 3, Math.max(lo + 3, v));
      if (spec.mode === 'x') {
        const i = Math.floor(spec.x.length / 2);
        return { x: clamp(toX(spec.x[i]), r.left, r.right), y: (r.top + r.bottom) / 2, head: spec.head[i] };
      }
      if (spec.mode === 'point') {
        const item = spec.items[Math.floor(spec.items.length / 2)];
        return { x: toX(item.x), y: toY(item.y), head: item.head };
      }
      const item = spec.items[Math.floor(spec.items.length / 2)];
      const mid = (item.low + item.high) / 2;
      return spec.mode === 'bandy'
        ? { x: (r.left + r.right) / 2, y: clamp(toY(mid), r.top, r.bottom), head: item.head }
        : { x: clamp(toX(mid), r.left, r.right), y: (r.top + r.bottom) / 2, head: item.head };
    }, key);
    await page.mouse.move(target.x, target.y);
    const tip = page.locator(`#${key} .readout.on .tip`);
    await tip.waitFor({ state: 'visible', timeout: 2000 });
    const head = await tip.locator('b').textContent();
    assert.equal(head, target.head, `${key}: tooltip head`);
    const rows = await tip.locator('p').count();
    assert.ok(rows >= 1, `${key}: tooltip rows`);
    checked.push({ key, head, rows });
  }

  // 3. The enlarge dialog's clone gets the same readout.
  await page.locator('#deciles .enlarge').click();
  const dialogHead = await page.evaluate(async () => {
    const svg = document.querySelector('#dialog-chart svg');
    const r = svg.querySelector('g[id$="-axes_1"] g[id*="-patch_"] > path').getBoundingClientRect();
    const spec = JSON.parse(document.getElementById('readout-data').textContent).deciles;
    const ax = spec.axes[0];
    const item = spec.items[4];
    const mid = (item.low + item.high) / 2;
    const x = r.left + (mid - ax.xlim[0]) / (ax.xlim[1] - ax.xlim[0]) * r.width;
    document.getElementById('dialog-chart').dispatchEvent(new PointerEvent('pointermove', {
      clientX: x, clientY: (r.top + r.bottom) / 2, bubbles: true,
    }));
    return { shown: document.querySelector('#dialog-chart .readout.on .tip b').textContent, want: item.head };
  });
  assert.equal(dialogHead.shown, dialogHead.want);
  await page.locator('#close-dialog').click();

  // 4. On a phone the chart scrolls sideways inside its box; the overlay must
  //    stay pinned to the plot rather than to the scroll container.
  const narrow = await browser.newPage({ viewport: { width: 390, height: 844 } });
  const narrowErrors = [];
  narrow.on('pageerror', e => narrowErrors.push(e.message));
  await narrow.goto('http://127.0.0.1:8019/content/daily/2026-09-18.show.html');
  await narrow.waitForFunction(() => window.__readoutReady === true);
  const scrolled = await narrow.evaluate(() => {
    const figure = document.getElementById('validation-sharpe');
    figure.scrollIntoView({ block: 'center', behavior: 'instant' });
    const scroll = figure.querySelector('.chart-scroll');
    scroll.scrollLeft = scroll.scrollWidth - scroll.clientWidth;
    const spec = JSON.parse(document.getElementById('readout-data').textContent)['validation-sharpe'];
    const r = figure.querySelector('g[id$="-axes_1"] g[id*="-patch_"] > path').getBoundingClientRect();
    const ax = spec.axes[0];
    const i = spec.x.length - 40;
    const x = r.left + (spec.x[i] - ax.xlim[0]) / (ax.xlim[1] - ax.xlim[0]) * r.width;
    const y = (r.top + r.bottom) / 2;
    scroll.dispatchEvent(new PointerEvent('pointermove', { clientX: x, clientY: y, bubbles: true }));
    const dot = figure.querySelector('.readout.on .dot').getBoundingClientRect();
    return {
      scrollLeft: scroll.scrollLeft,
      head: figure.querySelector('.readout.on .tip b').textContent,
      want: spec.head[i],
      dotOffset: Math.abs(dot.left + dot.width / 2 - x),
    };
  });
  assert.equal(scrolled.head, scrolled.want);
  assert.ok(scrolled.scrollLeft > 20, 'the narrow viewport must actually scroll the chart');
  assert.ok(scrolled.dotOffset < 1.5, `scrolled dot drift ${scrolled.dotOffset}`);
  assert.deepEqual(narrowErrors, []);

  assert.deepEqual(errors, []);
  assert.ok(drift.scatter.drift < 1.5, `scatter drift ${drift.scatter.drift}`);
  assert.ok(drift.twin.drift < 1.5, `twin-axis drift ${drift.twin.drift}`);
  console.log(JSON.stringify({ drift, dialog: dialogHead, scrolled, checked }, null, 2));
  await browser.close();
})().catch(error => { console.error(error); process.exitCode = 1; });
