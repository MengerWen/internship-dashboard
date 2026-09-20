// Checks that every daily show page highlights the nav tab you are reading.
// Serve the repo first:  python -m http.server 8019 --bind 127.0.0.1
const { chromium } = require('@playwright/test');
const assert = require('node:assert/strict');

const PAGES = [
  '2026-07-08', '2026-07-31', '2026-08-01', '2026-08-02', '2026-08-04',
  '2026-08-07', '2026-09-06', '2026-09-07', '2026-09-16', '2026-09-18',
];

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  const results = [];
  for (const viewport of [{ width: 1440, height: 900 }, { width: 390, height: 844 }]) {
    for (const day of PAGES) {
      const page = await browser.newPage({ viewport });
      const errors = [];
      page.on('pageerror', e => errors.push(e.message));
      await page.goto(`http://127.0.0.1:8019/content/daily/${day}.show.html`, { waitUntil: 'load' });
      // These pages scroll smoothly; sample only once the position has settled.
      await page.addStyleTag({ content: 'html{scroll-behavior:auto!important}' });
      await page.waitForTimeout(500);
      const settle = async () => {
        let last = -1;
        for (let i = 0; i < 40; i += 1) {
          const y = await page.evaluate(() => Math.round(scrollY));
          if (y === last) return;
          last = y;
          await page.waitForTimeout(60);
        }
      };
      const ids = await page.$$eval('nav a[href^="#"]', as => as.map(a => a.getAttribute('href').slice(1)));
      const missed = [];
      for (const id of ids) {
        await page.evaluate(i => document.getElementById(i)?.scrollIntoView({ block: 'start', behavior: 'instant' }), id);
        await settle();
        await page.waitForTimeout(120);
        const active = await page.$$eval('nav a.active', as => as.map(a => a.getAttribute('href').slice(1)));
        // A section near the foot of a short page cannot be scrolled to the top;
        // there the most-visible section wins instead, which is not a failure.
        const reachable = await page.evaluate(i => {
          const box = document.getElementById(i).getBoundingClientRect();
          const nav = document.querySelector('nav');
          return box.top <= Math.max(0, nav.getBoundingClientRect().bottom) + 12;
        }, id);
        if (reachable && (active.length !== 1 || active[0] !== id)) missed.push({ id, active });
      }
      await page.evaluate(() => scrollTo({ top: document.documentElement.scrollHeight, behavior: 'instant' }));
      await settle();
      await page.waitForTimeout(160);
      const atBottom = await page.$$eval('nav a.active', as => as.map(a => a.getAttribute('href').slice(1)));
      // A tab that scrolled out of a narrow nav must be pulled back into view.
      const visible = await page.$$eval('nav a.active', as => as.every(a => {
        const box = a.getBoundingClientRect();
        return box.right > 0 && box.left < innerWidth;
      }));
      results.push({
        viewport: viewport.width, day, tabs: ids.length, missed,
        bottomIsLast: atBottom[0] === ids[ids.length - 1], activeVisible: visible, errors,
      });
      await page.close();
    }
  }
  await browser.close();
  const bad = results.filter(r => r.missed.length || !r.bottomIsLast || !r.activeVisible || r.errors.length);
  console.log(JSON.stringify(bad.length ? bad : results.map(r => ({ ...r, missed: 0 })), null, 1));
  assert.deepEqual(bad, [], 'every nav tab must light up for its own section');
  console.log(`OK — ${PAGES.length} pages x 2 viewports`);
})();
