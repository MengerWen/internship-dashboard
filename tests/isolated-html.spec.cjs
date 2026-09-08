const { test, expect } = require('@playwright/test');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const host = 'https://dashboard.test/';

async function embed(page, html) {
  const documentRequests = [];
  await page.route(`${host}**`, route => {
    if (route.request().isNavigationRequest()) {
      documentRequests.push(route.request().url());
      return route.fulfill({
        contentType: 'text/html',
        headers: { 'X-Frame-Options': 'DENY' },
        body: '<iframe sandbox="allow-scripts" style="width:1200px;height:650px"></iframe>',
      });
    }
    const asset = new URL(route.request().url()).pathname.slice(1);
    const assetPath = path.join(root, 'site', asset);
    if (asset.endsWith('.js') && fs.existsSync(assetPath)) {
      return route.fulfill({ path: assetPath, contentType: 'text/javascript' });
    }
    return route.fulfill({ status: 204, body: '' });
  });
  await page.goto(`${host}#/daily/2026-09-06/show`);
  // Load the production helper after DOMContentLoaded, without booting the dashboard.
  await page.evaluate(fs.readFileSync(path.join(root, 'site/js/router.js'), 'utf8'));
  await page.evaluate(html => {
    document.querySelector('iframe').srcdoc = window.DashboardApp.prepareIsolatedHtml(html);
  }, html);
  const frame = page.frames().find(frame => frame.parentFrame());
  await frame.waitForLoadState('domcontentloaded');
  return { frame, documentRequests };
}

test('all six report sections stay inside the sandboxed preview', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const html = fs.readFileSync(path.join(root, 'content/daily/2026-09-06.show.html'), 'utf8');
  const { frame, documentRequests } = await embed(page, html);
  await expect(frame.locator('#factor-list .factor-item')).toHaveCount(24);
  for (const id of ['definition', 'contract', 'results', 'factors', 'evidence', 'inspiration']) {
    await frame.locator(`nav a[href="#${id}"]`).click();
    await expect.poll(() => frame.url()).toBe(`about:srcdoc#${id}`);
    await expect(frame.locator(`#${id}`)).toBeInViewport();
  }
  await frame.selectOption('#family-filter', '7');
  await expect(frame.locator('#factor-list .factor-item')).toHaveCount(2);
  expect(page.url()).toBe(`${host}#/daily/2026-09-06/show`);
  expect(documentRequests).toHaveLength(1);
  expect(errors).toEqual([]);
  await expect(page.locator('iframe')).toHaveAttribute('sandbox', 'allow-scripts');
});

test('keyboard and dynamic anchors retain native fragment and hashchange behavior', async ({ page }) => {
  const { frame, documentRequests } = await embed(page, `<!doctype html><html><head></head><body>
    <a id="jump" href="#%E7%BB%93%E6%9E%9C%3A1"><span>Jump</span></a>
    <div style="height:1400px"></div><h2 id="结果:1">Result</h2>
    <div style="height:800px"></div>
    <script>window.hashes = []; addEventListener('hashchange', () => hashes.push(location.hash));</script>
  </body></html>`);
  await frame.locator('#jump').focus();
  await page.keyboard.press('Enter');
  await expect(frame.locator('[id="结果:1"]')).toBeInViewport();
  await expect.poll(() => frame.evaluate(() => window.hashes.length)).toBe(1);
  await frame.evaluate(() => scrollTo(0, 0));
  await frame.locator('#jump span').click();
  await expect(frame.locator('[id="结果:1"]')).toBeInViewport();
  await frame.evaluate(() => {
    document.body.insertAdjacentHTML('beforeend', '<a id="dynamic" href="#"><span>Top</span></a>');
  });
  await frame.locator('#dynamic span').click();
  await expect.poll(() => frame.evaluate(() => scrollY)).toBe(0);
  await frame.evaluate(() => {
    document.body.insertAdjacentHTML('beforeend', '<a id="missing" href="#missing">Missing</a>');
  });
  await frame.locator('#missing').click();
  await expect.poll(() => frame.url()).toBe('about:srcdoc#missing');
  expect(documentRequests).toHaveLength(1);
});

test('external links, downloads and modified clicks keep their existing handling', async ({ page }) => {
  const { frame } = await embed(page, '<a id="link" href="#section">Link</a>');
  await frame.waitForSelector('#link');
  const prevented = await frame.evaluate(() => {
    const link = document.getElementById('link');
    return [
      { href: 'https://example.com/' },
      { href: 'report.html#section' },
      { href: '#section', target: '_blank' },
      { href: '#section', download: '' },
      { href: '#section', ctrlKey: true },
      { href: '#section', metaKey: true },
      { href: '#section', shiftKey: true },
      { href: '#section', altKey: true },
    ].map(({ href, target, download, ...modifiers }) => {
      link.setAttribute('href', href);
      link.removeAttribute('target');
      link.removeAttribute('download');
      if (target) link.setAttribute('target', target);
      if (download !== undefined) link.setAttribute('download', download);
      let wasPrevented;
      // Observe the production document handler, then suppress the test's navigation.
      window.addEventListener('click', event => {
        wasPrevented = event.defaultPrevented;
        event.preventDefault();
      }, { once: true });
      link.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true, ...modifiers }));
      return wasPrevented;
    });
  });
  expect(prevented).toEqual(Array(8).fill(false));
});
