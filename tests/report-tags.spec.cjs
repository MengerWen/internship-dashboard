const {test,expect} = require('@playwright/test');
const seed = require('../content/report-tags.json');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const base='http://127.0.0.1:8788';
const saved=async(page)=>expect(page.locator('#tag-save-status')).toHaveText('已保存');
async function setData(request,data) {
  const current=await (await request.get('/api/report-tags')).json();
  const response=await request.put('/api/report-tags',{headers:{Origin:base},data:{revision:current.revision,mutationId:crypto.randomUUID(),data}});
  expect(response.ok()).toBeTruthy();
}
async function open(page,route='/#/daily/2026-07-05') {
  await page.goto(route);
  await expect(page.locator('#daily-content')).toContainText('数据');
  await expect(page.locator('#tag-sync-status')).toHaveText('已同步');
}
test.beforeEach(async({request,page})=>{
  await setData(request,seed);
  page.testErrors=[]; page.on('pageerror',error=>page.testErrors.push(error.message));
});
test.afterEach(async({page})=>{expect(page.testErrors).toEqual([]);});

test('filter controls, OR/AND, search, collapse, navigation and share URL',async({page,request})=>{
  const data=structuredClone(seed);
  data.assignments={'2026-07-05':['speed','precheck'],'2026-07-06':['speed'],'2026-07-09':['precheck']};
  await setData(request,data); await open(page);
  const total=await page.locator('.timeline-item').count(); expect(total).toBeGreaterThan(20);
  await page.locator('[data-tag-filter="speed"]').click();
  await expect(page.locator('.timeline-item')).toHaveCount(2);
  await expect(page.locator('#reports-all')).toHaveAttribute('aria-pressed','false');
  await page.locator('#tag-filter-mode').selectOption('all');
  await page.locator('[data-tag-filter="precheck"]').click();
  await expect(page.locator('.timeline-item')).toHaveCount(1);
  await page.locator('#tag-filter-mode').selectOption('any');
  await expect(page.locator('.timeline-item')).toHaveCount(3);
  await page.locator('#report-list-search').fill('2026-07-09');
  await expect(page.locator('.timeline-item')).toHaveCount(1);
  await expect(page.locator('#report-current-outside')).toBeVisible();
  await expect(page.locator('#daily-next')).toBeDisabled();
  const url=page.url();
  await page.goto(url); await expect(page.locator('.timeline-item')).toHaveCount(1);
  await page.locator('#reports-all').click(); await expect(page.locator('.timeline-item')).toHaveCount(total);
  await page.locator('#reports-all').click(); await expect(page.locator('.timeline-item')).toHaveCount(0);
  await expect(page.locator('#daily-content')).toContainText('数据');
  await page.locator('[data-tag-filter="speed"]').click(); await expect(page.locator('.timeline-item')).toHaveCount(2);
  await page.locator('#daily-next').click();
  await expect(page).toHaveURL(/2026-07-06.*tags=speed/);
  await page.locator('#report-list-search').fill('不存在的检索');
  await expect(page.locator('#daily-timeline')).toContainText('没有匹配的搜索结果');
  await page.locator('#tags-reset').click();
  await page.locator('[data-tag-filter="_untagged"]').click();
  await expect(page.locator('.timeline-item')).toHaveCount(total-3);
  await page.screenshot({path:'test-results/tags-desktop.png',fullPage:false});
});

test('bulk add/remove preserves other tags, selection clears on search, suggestions and current edit',async({page,request})=>{
  await open(page); await page.locator('#tags-edit').click();
  await page.locator('#tag-manager-search').fill('提速');
  await page.locator('#tag-select-all').check();
  const count=await page.locator('[data-report-check]:checked').count(); expect(count).toBeGreaterThan(2);
  await page.locator('#tag-bulk-target').selectOption('speed'); await page.locator('#tag-bulk-add').click(); await saved(page);
  let state=await (await request.get('/api/report-tags')).json();
  expect(Object.keys(state.data.assignments)).toHaveLength(count);
  await page.locator('#tag-bulk-target').selectOption('precheck'); await page.locator('#tag-bulk-add').click(); await saved(page);
  await page.locator('#tag-bulk-target').selectOption('speed'); await page.locator('#tag-bulk-remove').click(); await saved(page);
  state=await (await request.get('/api/report-tags')).json();
  expect(Object.values(state.data.assignments).every(v=>v.length===1 && v[0]==='precheck')).toBeTruthy();
  await page.locator('#tag-manager-search').fill('模型'); await expect(page.locator('[data-report-check]:checked')).toHaveCount(0);
  await page.locator('[data-manager-tab="suggest"]').click();
  await expect(page.locator('.tag-suggestion')).not.toHaveCount(0);
  await page.locator('#suggest-select-all').check(); await page.locator('#suggest-accept').click(); await saved(page);
  await expect(page.locator('.tag-suggestion')).toHaveCount(0);
  await page.locator('#tag-undo').click(); await saved(page);
  await expect(page.locator('.tag-suggestion')).not.toHaveCount(0);
  await page.locator('#tag-manager-close').click(); await page.locator('#tag-edit-current').click();
  await expect(page.locator('[data-report-check]:checked')).toHaveCount(1);
  await expect(page.locator('#tag-manager-search')).toHaveValue('2026-07-05');
});

test('tag create, safe rendering, rename, color, keywords, reorder, merge/delete undo and import/export',async({page,request})=>{
  page.on('dialog',d=>d.accept());
  await open(page); await page.locator('#tags-edit').click(); await page.locator('[data-manager-tab="tags"]').click();
  await page.locator('#tag-new-name').fill('<测试标签>'); await page.locator('#tag-create-form button').click(); await saved(page);
  const row=page.locator('.tag-definition').filter({has:page.locator('input[value="<测试标签>"]')});
  await expect(row).toHaveCount(1);
  const id=await row.getAttribute('data-definition');
  await row.locator('[name="name"]').fill('合并来源'); await row.locator('[name="color"]').fill('#112233');
  await row.locator('[name="keywords"]').fill('量化, 预检'); await row.locator('[type=submit]').click(); await saved(page);
  const renamed=page.locator(`[data-definition="${id}"]`);
  await renamed.locator('[data-move="-1"]').click(); await saved(page);
  let state=await (await request.get('/api/report-tags')).json();
  expect(state.data.tags.at(-2).id).toBe(id);
  expect(state.data.tags.find(t=>t.id===id).keywords).toEqual(['量化','预检']);
  await renamed.locator('[name=merge]').selectOption('speed'); await renamed.locator('[data-merge]').click(); await saved(page);
  await expect(page.locator(`[data-definition="${id}"]`)).toHaveCount(0);
  await page.locator('#tag-undo').click(); await saved(page);
  await page.locator(`[data-definition="${id}"] [data-delete]`).click(); await saved(page);
  await page.locator('#tag-undo').click(); await saved(page);
  const downloadPromise=page.waitForEvent('download'); await page.locator('#tag-export').click();
  const download=await downloadPromise; const file=await download.path();
  const exported=JSON.parse(fs.readFileSync(file,'utf8')); expect(exported.tags.some(t=>t.id===id)).toBeTruthy();
  const imported={schemaVersion:1,tags:[{id:'imported',name:'导入标签',color:'#112233',keywords:[]}],assignments:{'2026-07-05':['imported']}};
  await page.locator('#tag-import-file').setInputFiles({name:'tags.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(imported))}); await saved(page);
  state=await (await request.get('/api/report-tags')).json(); expect(state.data.assignments['2026-07-05']).toContain('imported');
  await page.screenshot({path:'test-results/tags-manager.png'});
});

test('network failure retains draft across reload and retry saves exact mutation once',async({page,request})=>{
  await open(page); await page.locator('#tags-edit').click(); await page.locator('[data-manager-tab="tags"]').click();
  let fail=true;
  await page.route('**/api/report-tags',async route=>{
    if (route.request().method()==='PUT' && fail) { await route.fetch(); await route.abort(); }
    else await route.continue();
  });
  await page.locator('#tag-new-name').fill('失败草稿'); await page.locator('#tag-create-form button').click();
  await expect(page.locator('#tag-save-status')).toContainText('保存失败');
  const once=await (await request.get('/api/report-tags')).json();
  expect(once.data.tags.some(t=>t.name==='失败草稿')).toBeTruthy();
  page.on('dialog',d=>d.accept()); await page.reload();
  await expect(page.locator('#tag-sync-status')).toContainText('已恢复未保存草稿');
  fail=false; await page.locator('#tag-retry-inline').click();
  await expect(page.locator('#tag-sync-status')).toHaveText('已保存');
  const after=await (await request.get('/api/report-tags')).json(); expect(after.revision).toBe(once.revision);
});

test('concurrent writer conflict never overwrites server, draft can be exported and latest reloaded',async({page,request})=>{
  await open(page); await page.locator('#tags-edit').click(); await page.locator('[data-manager-tab="tags"]').click();
  const remote=structuredClone(seed); remote.tags[0].name='远端提速'; await setData(request,remote);
  await page.locator('#tag-new-name').fill('本地草稿'); await page.locator('#tag-create-form button').click();
  await expect(page.locator('#tag-save-status')).toContainText('线上已有新修改');
  const server=await (await request.get('/api/report-tags')).json(); expect(server.data.tags.some(t=>t.name==='本地草稿')).toBeFalsy();
  const dl=page.waitForEvent('download'); await page.locator('#tag-export').click();
  const draft=JSON.parse(fs.readFileSync(await (await dl).path(),'utf8')); expect(draft.tags.some(t=>t.name==='本地草稿')).toBeTruthy();
  page.on('dialog',d=>d.accept()); await page.locator('#tag-reload').click();
  await expect(page.locator('#tag-save-status')).toHaveText('已同步');
  await expect(page.locator('[data-definition="speed"] input[name=name]')).toHaveValue('远端提速');
});

test('edits made during an in-flight save are queued without losing either change',async({page,request})=>{
  await open(page); await page.locator('#tags-edit').click(); await page.locator('[data-manager-tab="tags"]').click();
  let release, intercepted; let first=true;
  const waiting=new Promise(resolve=>intercepted=resolve);
  const barrier=new Promise(resolve=>release=resolve);
  await page.route('**/api/report-tags',async route=>{
    if (route.request().method()==='PUT' && first) {first=false; intercepted(); await barrier;}
    await route.continue();
  });
  await page.locator('#tag-new-name').fill('第一批'); await page.locator('#tag-create-form button').click(); await waiting;
  await page.locator('#tag-new-name').fill('第二批'); await page.locator('#tag-create-form button').click();
  release(); await saved(page);
  const state=await (await request.get('/api/report-tags')).json();
  expect(state.data.tags.filter(t=>['第一批','第二批'].includes(t.name))).toHaveLength(2);
});

test('unavailable API preserves reading and exposes a usable reconnect action',async({page})=>{
  let unavailable=true;
  await page.route('**/api/report-tags',route=>unavailable?route.abort():route.continue());
  await page.goto('/#/daily/2026-07-05');
  await expect(page.locator('#daily-content')).toContainText('数据');
  await expect(page.locator('#tag-edit-current')).toBeDisabled();
  await expect(page.locator('#tag-retry-inline')).toBeVisible();
  unavailable=false; await page.locator('#tag-retry-inline').click();
  await expect(page.locator('#tag-sync-status')).toHaveText('已同步');
  await expect(page.locator('#tag-edit-current')).toBeEnabled();
});

test('mobile layout, keyboard close and offline file snapshot editing',async({page})=>{
  await page.setViewportSize({width:390,height:844}); await open(page);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
  await page.locator('#tags-edit').click();
  await page.locator('[data-manager-tab="tags"]').click();
  expect(await page.locator('#tag-manager').evaluate(el=>el.scrollWidth<=el.clientWidth)).toBeTruthy();
  await page.screenshot({path:'test-results/tags-mobile.png'});
  await page.keyboard.press('Escape'); await expect(page.locator('#tag-manager')).not.toBeVisible();
  await page.goto('file:///'+path.resolve('dist-offline/index.html').replaceAll('\\','/')+'#/daily/2026-07-05');
  await expect(page.locator('#tag-sync-status')).toContainText('离线副本');
  await page.locator('#tags-edit').click(); await page.locator('[data-manager-tab="tags"]').click();
  await page.locator('#tag-new-name').fill('离线测试'); await page.locator('#tag-create-form button').click();
  await expect(page.locator('#tag-save-status')).toContainText('已保存到此浏览器');
  await page.reload(); await expect(page.locator('[data-tag-filter]').filter({hasText:'离线测试'})).toHaveCount(1);
});
