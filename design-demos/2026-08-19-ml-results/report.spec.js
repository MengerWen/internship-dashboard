const { test, expect } = require('@playwright/test');
const path = require('path');

test.use({ channel: 'chrome', viewport: { width: 1440, height: 1000 } });

test('full report renders, filters, and preserves audited metrics', async ({ page }) => {
  const errors = [];
  page.on('pageerror', error => errors.push(String(error)));
  await page.goto('file:///' + path.resolve('D:/MG/！Internship/BUILD/汇报/content/daily/2026-08-19.show.html').replace(/\\/g, '/'));
  await expect(page.locator('#seriesCount')).toHaveText('16 series');
  await expect(page.locator('#rowCount')).toHaveText('显示 58 / 58 行');
  await expect(page.locator('.legend-item')).toHaveCount(16);

  const integrity = await page.evaluate(() => {
    const row = (id, phase, contract) => REPORT.rows.find(r => r.series_id === id && r.phase === phase && r.contract === contract);
    return {
      families: REPORT.families.length,
      hasRF: REPORT.families.includes('random_forest'),
      full: REPORT.meta.full_lifecycle_complete,
      valid: REPORT.meta.validator_passed,
      bridge: REPORT.meta.bridge_executed,
      finalCount: REPORT.meta.final_evaluation_count,
      weighted: row('weighted_pls', 'T', 'fractional').x.sr,
      lgbCuda: row('lightgbm_cuda', 'T', 'fractional').x.sr,
      lgbCpu: row('lightgbm_cpu_audit', 'T', 'fractional').x.sr,
      ridge: row('raw_ridge', 'T', 'fractional').rankic,
    };
  });
  expect(integrity.families).toBe(14);
  expect(integrity.hasRF).toBe(false);
  expect(integrity.full).toBe(true);
  expect(integrity.valid).toBe(true);
  expect(integrity.bridge).toBe(false);
  expect(integrity.finalCount).toBe(1);
  expect(integrity.weighted).toBeCloseTo(10.176, 3);
  expect(integrity.lgbCuda).toBeCloseTo(0.226, 3);
  expect(integrity.lgbCpu).toBeCloseTo(4.944, 3);
  expect(integrity.ridge).toBeCloseTo(0.00704, 5);

  await page.locator('#selectNone').click();
  await expect(page.locator('#visibleCount')).toHaveText('0 / 16');
  await page.locator('#selectAll').click();
  await expect(page.locator('#visibleCount')).toHaveText('16 / 16');
  await page.locator('[data-metric="l"]').click();
  await expect(page.locator('#chartTitle')).toContainText('纯多');
  await page.locator('[data-contract="floor"]').click();
  await expect(page.locator('[data-contract="floor"]')).toHaveClass(/active/);

  await page.locator('#phaseFilter').selectOption('T');
  await page.locator('#contractFilter').selectOption('fractional');
  await expect(page.locator('#rowCount')).toHaveText('显示 15 / 58 行');
  await page.locator('#phaseFilter').selectOption('D');
  await expect(page.locator('#rowCount')).toHaveText('显示 14 / 58 行');

  await page.locator('#phaseFilter').selectOption('all');
  await page.locator('#contractFilter').selectOption('all');
  await page.locator('#tableSearch').fill('lightgbm');
  await expect(page.locator('#rowCount')).toHaveText('显示 6 / 58 行');
  expect(errors).toEqual([]);
});
