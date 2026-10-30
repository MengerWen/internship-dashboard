// 横竖两版对照截图（throwaway）：node design-demos/journal-prototype/shots-v2.cjs
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const OUT = path.resolve(__dirname, "../screenshots");
const BASE = "http://127.0.0.1:8732";

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();

  // 现状：已实现的横向图谱
  for (const [tag, w, h] of [["", 1440, 1200], ["-mobile", 390, 900]]) {
    const ctx = await browser.newContext({ viewport: { width: w, height: h } });
    const page = await ctx.newPage();
    await page.goto(BASE + "/dist/#/journal", { waitUntil: "networkidle" });
    await page.waitForTimeout(1200);
    const f = path.join(OUT, "v2-before-horizontal" + tag + ".png");
    await page.screenshot({ path: f });
    console.log("before", path.basename(f));
    await ctx.close();
  }

  // 提案：竖向推进流
  const vfile = path.join(__dirname, "vertical-proposal.html");
  if (fs.existsSync(vfile)) {
    for (const [tag, w, h] of [["", 1440, 1200], ["-mobile", 390, 900]]) {
      const ctx = await browser.newContext({ viewport: { width: w, height: h } });
      const page = await ctx.newPage();
      await page.goto(BASE + "/design-demos/journal-prototype/vertical-proposal.html", { waitUntil: "networkidle" });
      await page.waitForTimeout(900);
      await page.screenshot({ path: path.join(OUT, "v2-after-vertical" + tag + ".png") });
      console.log("after ", "v2-after-vertical" + tag + ".png");
      if (!tag) {
        // 滚到 10 月密集区
        await page.evaluate(() => {
          const r = document.querySelector('[data-date="2026-10-14"]');
          if (r) { r.scrollIntoView({ block: "center" }); window.scrollBy(0, -200); }
        });
        await page.waitForTimeout(500);
        await page.screenshot({ path: path.join(OUT, "v2-after-vertical-dense.png") });
        console.log("after ", "v2-after-vertical-dense.png");
        // 悬停一条链
        await page.evaluate(() => {
          const el = document.querySelector('[data-chain-hit="open5m"]');
          if (el) el.dispatchEvent(new MouseEvent("mouseover", { bubbles: true }));
          const r = document.querySelector('[data-date="2026-08-19"]');
          if (r) { r.scrollIntoView({ block: "center" }); window.scrollBy(0, -200); }
        });
        await page.waitForTimeout(500);
        await page.screenshot({ path: path.join(OUT, "v2-after-vertical-hover.png") });
        console.log("after ", "v2-after-vertical-hover.png");
      }
      await ctx.close();
    }
  }
  await browser.close();
})();
