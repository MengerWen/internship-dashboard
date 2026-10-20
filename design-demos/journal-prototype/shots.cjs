// 原型截图（throwaway）：node design-demos/journal-prototype/shots.cjs [方向号...]
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const ROOT = path.resolve(__dirname, "../..");
const OUT = path.join(ROOT, "design-demos/screenshots");
const BASE = "http://127.0.0.1:8732/design-demos/journal-prototype/";

const PAGES = [
  { id: "1", file: "direction-1-ledger.html", name: "journal-1-ledger" },
  { id: "2", file: "direction-2-chain-rail.html", name: "journal-2-chain-rail" },
  { id: "3", file: "direction-3-atlas.html", name: "journal-3-atlas" },
];

(async () => {
  const want = process.argv.slice(2);
  const pages = want.length ? PAGES.filter((p) => want.includes(p.id)) : PAGES;
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();

  for (const p of pages) {
    if (!fs.existsSync(path.join(__dirname, p.file))) { console.log("skip", p.file); continue; }
    for (const [tag, w, h] of [["", 1440, 1180], ["-mobile", 390, 1000]]) {
      const ctx = await browser.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
      const page = await ctx.newPage();
      await page.goto(BASE + p.file, { waitUntil: "networkidle" });
      await page.waitForTimeout(700);
      const file = path.join(OUT, p.name + tag + ".png");
      await page.screenshot({ path: file });
      console.log("top   ", path.basename(file));

      // 再截一张密集区（9 月初，最宽处并行）
      await page.evaluate(() => {
        const t = document.querySelector('[data-date="2026-09-07"]')
          || document.querySelector('[data-date="2026-09-08"]');
        if (t) { t.scrollIntoView({ block: "center" }); window.scrollBy(0, -200); }
        else window.scrollTo(0, document.body.scrollHeight * 0.55);
      });
      await page.waitForTimeout(500);
      const file2 = path.join(OUT, p.name + tag + "-dense.png");
      await page.screenshot({ path: file2 });
      console.log("dense ", path.basename(file2));

      if (!tag) {
        // 选中一条链之后的样子
        await page.evaluate(() => {
          const b = document.querySelector('button[data-chain="open5m"], .ovbar[data-chain="open5m"]');
          if (b) { b.click(); return; }
          const s = document.getElementById('chainpick');
          if (s) { s.value = 'open5m'; s.dispatchEvent(new Event('change')); }
        });
        await page.waitForTimeout(500);
        const file3 = path.join(OUT, p.name + "-chain.png");
        await page.screenshot({ path: file3 });
        console.log("chain ", path.basename(file3));

        // 清单视图（只有方向三有）
        const hasList = await page.$("#v-list");
        if (hasList) {
          await page.evaluate(() => {
            const c = document.getElementById("clearfocus");
            if (c && !c.hidden) c.click();
            document.getElementById("v-list").click();
            window.scrollTo(0, 0);
          });
          await page.waitForTimeout(400);
          const f4 = path.join(OUT, p.name + "-list.png");
          await page.screenshot({ path: f4 });
          console.log("list  ", path.basename(f4));

          // 收窄时间窗
          await page.evaluate(() => {
            document.getElementById("v-atlas").click();
            const b = document.querySelector('[data-range="90"]');
            if (b) b.click();
          });
          await page.waitForTimeout(400);
          const f6 = path.join(OUT, p.name + "-zoom.png");
          await page.screenshot({ path: f6, clip: { x: 60, y: 260, width: 1320, height: 640 } });
          console.log("zoom  ", path.basename(f6));

          // 悬停读数
          await page.evaluate(() => {
            const b = document.querySelector('[data-range="all"]');
            if (b) b.click();
            document.getElementById("v-atlas").click();
          });
          await page.waitForTimeout(300);
          const box = await page.$('.hit[data-date="2026-09-03"]');
          if (box) { await box.hover(); await page.waitForTimeout(350); }
          const f5 = path.join(OUT, p.name + "-readout.png");
          await page.screenshot({ path: f5, clip: { x: 60, y: 300, width: 1320, height: 700 } });
          console.log("read  ", path.basename(f5));
        }
      }
      await ctx.close();
    }
  }
  await browser.close();
})();
