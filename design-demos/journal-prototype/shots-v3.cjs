// 竖向链条图三种点击的截图（throwaway）：node design-demos/journal-prototype/shots-v3.cjs
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const OUT = path.resolve(__dirname, "../screenshots");
const URL = "http://127.0.0.1:8732/design-demos/journal-prototype/vertical-atlas.html";

async function shot(page, name, clip) {
  await page.screenshot(clip ? { path: path.join(OUT, name), clip } : { path: path.join(OUT, name) });
  console.log("shot", name);
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1180 } });
  const page = await ctx.newPage();
  await page.goto(URL, { waitUntil: "networkidle" });
  await page.waitForTimeout(800);
  await shot(page, "v3-atlas-idle.png");

  // 点日期：横线 + 横向排开的卡片
  await page.evaluate(() => {
    document.querySelector('.rowhit[data-day="2026-10-14"]').dispatchEvent(new MouseEvent("click", { bubbles: true }));
    document.querySelector('.hit[data-day="2026-10-14"]').scrollIntoView({ block: "center" });
  });
  await page.waitForTimeout(500);
  await shot(page, "v3-atlas-click-day.png");

  // 点链名：整列 + 纵向注解
  await page.evaluate(() => {
    document.querySelector('.tname[data-chain="open5m"]').click();
    window.scrollTo(0, 0);
  });
  await page.waitForTimeout(500);
  await shot(page, "v3-atlas-click-chain.png");

  // 点单个点：只出那一张
  await page.evaluate(() => {
    document.querySelector('.hit[data-day="2026-07-15"][data-chain="doris-migration"]')
      .dispatchEvent(new MouseEvent("click", { bubbles: true }));
    document.querySelector('.hit[data-day="2026-07-15"][data-chain="doris-migration"]').scrollIntoView({ block: "center" });
  });
  await page.waitForTimeout(500);
  await shot(page, "v3-atlas-click-point.png");

  // 图下方的完整日卡
  await page.evaluate(() => {
    document.querySelector('.rowhit[data-day="2026-10-14"]').dispatchEvent(new MouseEvent("click", { bubbles: true }));
    document.getElementById("detail").scrollIntoView({ block: "start" });
    window.scrollBy(0, -80);
  });
  await page.waitForTimeout(500);
  await shot(page, "v3-atlas-daycard.png");

  await ctx.close();
  await browser.close();
})();
