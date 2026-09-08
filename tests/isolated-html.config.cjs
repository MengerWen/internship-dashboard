const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: '.',
  testMatch: 'isolated-html.spec.cjs',
  workers: 1,
  use: { headless: true, viewport: { width: 1440, height: 1000 } },
});
