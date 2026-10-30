// 启动本地预览后运行；复现 10 月 22 日同日工作点集中在右侧的场景。
const {chromium} = require('@playwright/test');
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const {execFileSync} = require('node:child_process');

const base = process.env.JOURNAL_BASE_URL || 'http://127.0.0.1:8030/';
const output = require('./artifact_paths.cjs').artifactDirectory('journal-space-use');
const baseline = '35ea1ee8cdde19c89fdbddf7d597ff3dbcf708c4';

function measure() {
  const v = window.JournalView, notes = v.floatingNotes;
  const cards = notes.rects.map(r => ({id:r.id, anchorX:r.anchorX, x:r.node.offsetLeft, y:r.node.offsetTop, w:r.node.offsetWidth, h:r.node.offsetHeight})).sort((a,b) => a.anchorX-b.anchorX);
  const scroller = document.querySelector('.journal-scroller');
  const left = Math.max(v.atlas.dateWidth+10, scroller.scrollLeft+10), right = Math.min(v.atlas.width-10,scroller.scrollLeft+scroller.clientWidth-10);
  const required = cards.reduce((sum,r) => sum+r.w,0)+Math.max(0,cards.length-1)*14;
  const overlaps = cards.slice(1).filter((r,i) => cards[i].x+cards[i].w+13>r.x).map(r=>r.id);
  return {cards,left,right,required,available:right-left,occupied:Math.max(...cards.map(r=>r.x+r.w))-Math.min(...cards.map(r=>r.x)),marginDifference:Math.min(...cards.map(r=>r.x))-left-(right-Math.max(...cards.map(r=>r.x+r.w))),verticalSpan:Math.max(...cards.map(r=>r.y+r.h))-Math.min(...cards.map(r=>r.y)),horizontalOverlaps:overlaps};
}

(async () => {
  await fs.mkdir(output,{recursive:true});
  const browser=await chromium.launch({headless:true,channel:'chrome'}), errors=[], results=[];
  try {
    for (const old of [true,false]) {
      const context=await browser.newContext({viewport:{width:2560,height:1249},deviceScaleFactor:1.5,reducedMotion:'reduce'});
      const page=await context.newPage();
      page.on('pageerror',e=>errors.push(e.message));
      await page.route('**/api/report-tags',r=>r.fulfill({json:{data:{tags:[],assignments:{}},revision:0,canEdit:false}}));
      if(old) await page.route('**/js/journal-notes.js*',r=>r.fulfill({contentType:'text/javascript',body:execFileSync('git',['show',`${baseline}:site/js/journal-notes.js`],{encoding:'utf8'})}));
      await page.goto(base+'#/journal/2026-10-22?view=atlas');
      await page.waitForSelector('.journal-floating-note',{state:'attached'});
      await page.evaluate(()=>document.fonts.ready);
      await page.evaluate(()=>window.JournalView.select('2026-10-22',true));
      await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
      await page.waitForTimeout(250);
      const state=await page.evaluate(measure);
      results.push({old,width:2560,...state});
      if(old) assert(state.horizontalOverlaps.length,'旧版应复现横向空间未利用的堆叠');
      else {assert(state.required<=state.available);assert.deepEqual(state.horizontalOverlaps,[]);assert(Math.abs(state.marginDifference)<=1);}
      await page.screenshot({path:path.join(output,old?'before-2026-10-22.png':'after-2026-10-22.png'),animations:'disabled'});
      if(!old) {
        for(const width of [1440,1024,768]) {
          await page.setViewportSize({width,height:1000});
          await page.evaluate(()=>window.JournalView.select('2026-10-22',true));
          const state=await page.evaluate(measure);
          if(state.required<=state.available) assert.deepEqual(state.horizontalOverlaps,[]);
          assert(state.cards[0].x<state.cards.at(-1).x);
          results.push({old:false,width,...state});
        }
      }
      await context.close();
    }
    assert.deepEqual(errors,[]);
    await fs.writeFile(path.join(output,'space-verification.json'),JSON.stringify({baseline,results,errors},null,2));
    console.log(JSON.stringify(results.map(({old,width,available,required,occupied,verticalSpan,horizontalOverlaps})=>({old,width,available,required,occupied,verticalSpan,horizontalOverlaps})),null,2));
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
