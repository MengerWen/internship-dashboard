const {chromium} = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const {pathToFileURL} = require('node:url');

(async () => {
  const output = __dirname, base = 'http://127.0.0.1:8031/dist/';
  const tags = JSON.parse(await fs.readFile('content/report-tags.json', 'utf8'));
  const browser = await chromium.launch({headless:true, channel:'chrome'});
  const results = [], errors = [];
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1080}});
    page.on('pageerror', e => errors.push(e.message));
    await page.route('**/api/report-tags', route => route.fulfill({json:{data:tags,revision:0,canEdit:false}}));
    for (const width of [2560,1440,1024,860,768,390,320]) {
      await page.setViewportSize({width,height:1080});
      await page.goto(base + '#/journal/2026-10-20?view=atlas');
      await page.waitForSelector('.journal-task-list > li');
      await page.waitForSelector('#journal-body [data-source-kind="file"]');
      await page.evaluate(() => document.fonts.ready);
      assert.equal(await page.locator('.journal-task-list > li').count(),5);
      assert.equal(await page.locator('.journal-card-columns').count(),0);
      assert.equal(await page.locator('#journal-body h2').count(),0);
      assert.equal(await page.locator('.journal-annotation').filter({hasText:'当天发布'}).count(),0);
      assert.equal(await page.locator('#journal-day-context').count(),1);
      assert.equal(await page.locator('#journal-day-context').isVisible(),true);
      const geometry = await page.locator('.journal-day-card').evaluate(n => ({
        width:n.clientWidth,scrollWidth:n.scrollWidth,
        overflow:document.documentElement.scrollWidth>innerWidth,
        rowColumns:getComputedStyle(n.querySelector('.journal-task-list > li')).gridTemplateColumns,
        headings:[...n.querySelectorAll('h2,h3')].map(h=>({text:h.textContent,size:getComputedStyle(h).fontSize})),
      }));
      assert(!geometry.overflow,`${width}px 页面横向溢出`);
      assert(geometry.scrollWidth<=geometry.width,`${width}px 日卡横向溢出`);
      await page.locator('.journal-day-card').evaluate(n => scrollTo({top:n.getBoundingClientRect().top+scrollY-136,behavior:'instant'}));
      await page.screenshot({path:path.join(output,`day-${width}.png`)});
      if (width===1440 || width===390) {
        await page.locator('#journal-body h3').filter({hasText:'原始依据'}).evaluate(n=>scrollTo({top:n.getBoundingClientRect().top+scrollY-146,behavior:'instant'}));
        await page.screenshot({path:path.join(output,`sources-${width}.png`)});
      }
      results.push({viewportWidth:width,...geometry});
    }
    await page.setViewportSize({width:1440,height:1080});
    await page.goto(base+'#/journal/2026-10-20?view=atlas');
    await page.locator('.journal-evidence > summary').click();
    await page.waitForSelector('.journal-repo');
    await page.locator('.journal-repo > summary').first().click();
    assert(await page.locator('.journal-repo [data-source-kind="commit"]').count()>0);
    assert(await page.locator('.journal-attribution-group [data-source-kind="commit"]').count()>0);
    await page.locator('.journal-repo').first().evaluate(n=>scrollTo({top:n.getBoundingClientRect().top+scrollY-146,behavior:'instant'}));
    await page.screenshot({path:path.join(output,'commits-1440.png')});
    await page.locator('.journal-relations > summary').click();
    assert(await page.locator('.journal-flow-grid').isVisible());
    await page.locator('.journal-task-chain [data-journal-chain="replay"]').click();
    await page.waitForSelector('.journal-chain-card');
    assert.equal(await page.locator('#journal-day-context').isVisible(),false);
    await page.goto(base+'#/journal/2026-10-18?view=atlas');
    await page.waitForSelector('.journal-annotation');
    await page.locator('.journal-day-hit[data-journal-day="2026-10-18"]').click();
    assert.equal(await page.locator('.journal-annotation').count(),4);
    assert((await page.locator('#journal-day-context').textContent()).includes('周日有相关汇报当天发布 1 篇'));
    await page.locator('.journal-day-hit[data-journal-day="2026-10-18"]').scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(output,'atlas-1440.png')});
    await page.locator('#journal-clear').click();
    assert.equal(await page.locator('#journal-day-context').isVisible(),false);
    const offline = await browser.newPage({viewport:{width:1440,height:1080}});
    const remote = [];
    offline.on('request',r=>{if(/^https?:/.test(r.url())) remote.push(r.url());});
    offline.on('pageerror',e=>errors.push(e.message));
    await offline.goto(pathToFileURL(path.resolve('dist-offline/index.html')).href+'#/journal/2026-10-20?view=list');
    await offline.waitForSelector('#journal-body [data-source-kind="file"]');
    await offline.locator('.journal-evidence > summary').click();
    await offline.waitForSelector('.journal-repo');
    assert.equal(await offline.locator('.journal-task-list > li').count(),5);
    assert.deepEqual(remote,[]);
    assert.deepEqual(errors,[]);
    await fs.writeFile(path.join(output,'verification.json'),JSON.stringify({results,errors,offlineRequests:remote,checks:['日期公共信息集中显示','任务行与来源分类','证据懒加载及提交入口','任务关系展开','链条跳转','日选中与取消','离线内联证据']},null,2));
    console.log(JSON.stringify({widths:results.map(r=>r.viewportWidth),errors,offlineRequests:remote,output},null,2));
  } finally { await browser.close(); }
})().catch(e=>{console.error(e);process.exitCode=1;});
