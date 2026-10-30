const {chromium}=require('@playwright/test');
const fs=require('fs');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const audit=[];
 for(const width of [1440,390]){
  const page=await browser.newPage({viewport:{width,height:1000}});
  const failures=[];
  page.on('pageerror',e=>failures.push(e.message));
  await page.goto('http://127.0.0.1:8029/#/daily/2026-10-09');
  await page.locator('#daily-meta').filter({hasText:'2026-10-09'}).waitFor({state:'visible'});
  await page.locator('#daily-content .enhanced-table-scroll').first().waitFor({state:'attached'});
  const text=await page.locator('#daily-content').innerText();
  if(!text.includes('六核分组定标阶段成果')||!text.includes('结构参数处理和真实因子验收也未完成'))throw new Error('report identity or boundary missing');
  await page.locator('#report-tag-buttons').getByRole('button',{name:/^interim/}).click();
  await page.waitForFunction(()=>document.querySelector('#daily-timeline').textContent.includes('2026-10-09'));
  await page.locator('#daily-meta').filter({hasText:'2026-10-09'}).waitFor({state:'visible'});
  const layout=await page.evaluate(()=>({width:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth}));
  if(layout.scrollWidth>layout.width+1)throw new Error('horizontal overflow: '+JSON.stringify(layout));
  await page.screenshot({path:`artifacts/grouped-kernel-report-2026-10-09/report-${width}.png`});
  await page.goto('http://127.0.0.1:8029/#/daily/2026-10-09/show');
  await page.locator('#daily-show-content').getByText('六核参数包已封存',{exact:true}).waitFor({state:'visible'});
  await page.screenshot({path:`artifacts/grouped-kernel-report-2026-10-09/show-${width}.png`});
  if(failures.length)throw new Error(failures.join('\n'));
  audit.push({width,report:true,show:true,interim_filter:true,layout,page_errors:failures});
  await page.close();
 }
 await browser.close();
 fs.writeFileSync('artifacts/grouped-kernel-report-2026-10-09/browser-validation.json',JSON.stringify(audit,null,2));
 console.log(JSON.stringify(audit));
})().catch(e=>{console.error(e);process.exit(1)});
