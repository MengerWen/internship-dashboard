const {defineConfig} = require('@playwright/test');
module.exports = defineConfig({
  testDir: '.', testMatch: 'report-tags.spec.cjs', workers: 1,
  timeout: 45000, expect: {timeout: 12000},
  use: {baseURL:'http://127.0.0.1:8788', headless:true, viewport:{width:1440,height:1000}, trace:'retain-on-failure', screenshot:'only-on-failure'},
  webServer: {command:'npx wrangler dev --config tests/wrangler.test.jsonc --ip 127.0.0.1 --port 8788 --persist-to .wrangler/test-state', cwd:require('path').resolve(__dirname,'..'),url:'http://127.0.0.1:8788/__test/health',timeout:120000,reuseExistingServer:false},
});
