# PLAN-3 — 增量变更单:展示 Tab 布局修复 + 审阅问题清单

> **性质**:这是对已按 PLAN.md / PLAN-2.md 完成实施的 `internship-dashboard` 代码库的**增量变更单**,不是重写。
> **执行前置**:动手前先通读 `site/css/daily.css`、`site/js/daily.js`、`site/js/router.js`、`site/js/search.js`、`build.py` 的现状。所有改动不得破坏 PLAN.md 第 11 节与 PLAN-2.md 第 5 节已通过的验收项(交付前全量回归)。
> 未定义细节沿用 PLAN.md 1.2 节技术原则裁决;本文件与 PLAN/PLAN-2 冲突时以本文件为准。新决策记入 `DECISIONS.md`。
> 每节标注优先级:**P0 = 必须修(用户可见故障)**,P1 = 应修(真实内容上线前会踩),P2 = 建议修(健壮性/维护性)。

---

## 1. 【P0】展示 Tab 布局塌缩:内容被挤进左侧窄列

### 1.1 现象

`#/daily/<date>/show` 下(`.show.md` 幕式播放器与 `.show.html` iframe 两种都受影响),展示内容只占据页面左侧约 190px 宽的一条,文档区中部大面积留白。文档 Tab 正常。

### 1.2 根因(已确诊,按此修,不要重新猜)

`site/css/daily.css` 中:

```css
.daily-mainline {
  display: grid;
  grid-template-columns: 190px minmax(0, 1fr);  /* 列1: TOC,列2: 内容 */
}
```

`.daily-mainline` 的两个子元素依次为 `<nav id="daily-toc">` 与 `<div class="daily-content-frame">`。切换到展示模式时,`daily.js` 的 `switchMode()` 执行 `this.tocEl.hidden = true`;带 `hidden` 的元素 `display: none`,**不再生成网格项**,于是 `.daily-content-frame` 顺位落入第一列(190px 窄列),第二列 `1fr` 整列空置。

### 1.3 修复方案

采用**显式模式类**,不要依赖 `:has()` 选择器(避免兼容性讨论,且状态已由 JS 管理):

1. `daily.js` 的 `switchMode(mode, updateHash)` 中,在设置 `tocEl.hidden` 的同一处,对 `.daily-mainline` 容器切换类:

   ```js
   this.mainlineEl.classList.toggle("is-show-mode", mode === "show");
   ```

   `mainlineEl` 在 `init()` 里一次性 `document.querySelector(".daily-mainline")` 取得并存为实例字段(与现有 `timelineEl`/`contentEl` 等字段风格一致)。

2. `daily.css` 增加:

   ```css
   .daily-mainline.is-show-mode {
     grid-template-columns: minmax(0, 1fr);
   }
   ```

3. 不改动 HTML 结构,不改动文档模式的任何样式。

### 1.4 注意点

- **深链直达**:`#/daily/<date>/show` 首次加载路径走的是 `show()` → `switchMode("show", false)`,类切换写在 `switchMode` 内即可同时覆盖"点 Tab"与"深链直达"两条路径;不要只写在 Tab 的 click 回调里。
- **回切**:切回文档 Tab 必须移除该类,恢复两列。
- **移动端**:`@media (max-width: 900px)` 下 `.daily-mainline` 已是单列 `1fr`,新增规则不得使其回归两列(单列下加不加该类效果应相同,验证即可)。
- **两种展示类型都要验证**:`.show.md`(2026-07-07,幕式播放器)与 `.show.html`(2026-07-06,iframe)都应占满 `.daily-mainline` 整行宽度(右侧时间轴列不受影响,那是外层 `.daily-view` 网格的事,本节不动它)。
- **幕内容宽度**:塌缩修复后幕/iframe 自然铺满内容区,无需再给 `.daily-show-scene` 设额外宽度;**不要**顺手加 `max-width` 限制(需求就是充分利用空间)。
- 离线版复用同一套 CSS/JS,自动同步修复,但要按 6.2 回归。

### 1.5 验收

1. `#/daily/2026-07-07/show`:幕式播放器占满内容区整宽(左边不再有空 TOC 槽位,右侧时间轴不变),翻幕、dots、键盘 ←/→ 均正常;
2. `#/daily/2026-07-06/show`:iframe 占满内容区整宽,内部按钮交互正常;
3. 文档 ↔ 展示反复切换,布局无残留错位;TOC 在文档模式恢复显示且位置正确;
4. 窗口 ≤900px 时两种模式均为单列,无回归;
5. 离线版 `file://` 下重复 1–4。

---

## 2. 【P0】TOC 点击对"数字开头标题"抛异常

### 2.1 根因

`daily.js` 的 `renderToc()` 中点击回调用 CSS 选择器查目标:

```js
const target = this.contentEl.querySelector(link.getAttribute("href"));
```

标题写成 `## 1. 目标` 时 slug 为 `1-目标`,`querySelector("#1-目标")` 是非法 CSS 选择器(ID 以数字开头),抛 `SyntaxError`,点击无响应;即使选择器合法,查不到时 `target` 为 `null`,`target.scrollIntoView` 也会抛 `TypeError`。当前示例内容全是中文开头标题所以未暴露,真实日报几乎必踩。

### 2.2 修复方案

`renderToc()` 本来就持有 `headings` 数组且链接是按它逐一生成的——**让每个链接直接闭包引用自己的 heading 元素**,彻底不再二次查询:

- 生成链接时改为逐个 `createElement("a")`(或保留模板字符串但绑定监听时按索引取 `headings[index]`),click 回调中直接 `headings[index].scrollIntoView({behavior: "smooth", block: "start"})`;
- 保留 `event.preventDefault()`(防止 `#slug` 进入 hash 路由);
- 不要改用 `document.getElementById`:showcase 视图的内容常驻 DOM,与日报标题 slug 可能撞 ID,按 ID 全局查有取错元素的风险。

### 2.3 验收

1. 在任一示例日报临时加一节 `## 1. 数字开头标题` 重新构建,TOC 出现该项,点击平滑滚动到位,console 无报错(验完可还原示例内容);
2. 中文标题项点击行为不变;高亮跟随(IntersectionObserver)不受影响。

---

## 3. 【P1】build.py:date_key 与文件名一致性 + 重复日期防护

### 3.1 现状问题

`build_daily()` 中 `date_key` 取自 frontmatter `date`(缺省才用文件名 stem),但:

- 配套展示版按 `{date_key}.show.md` / `.show.html` 查找,而孤儿检查(`primary_dates`)用的是**文件名 stem** 集合——frontmatter 日期与文件名不一致时,展示版查找错位、孤儿误报;
- 两个文件若解析出同一 `date_key`,会**静默互相覆盖** `daily/<date>.html`,manifest 中出现重复日期,时间轴上两个节点指向同一内容。

### 3.2 修复方案

1. **以文件名为准**:若 frontmatter `date` 解析结果与 `path.stem` 不一致,打警告(`"{file} frontmatter date 与文件名不一致,以文件名为准"`),`date_key = path.stem`(先校验 stem 是合法 `YYYY-MM-DD`,不合法则维持现有"日期解析失败,已跳过"路径);
2. **重复防护**:维护已见 `date_key` 集合,遇到重复打警告并跳过后者;
3. 保持"警告不中断构建"的既有哲学,只加警告与确定性行为,不新增失败退出。

### 3.3 验收

1. 构造文件名 `2026-07-08.md` + frontmatter `date: 2026-07-09`:构建出警告,产物与 manifest 均按 `2026-07-08` 归档,配套 `2026-07-08.show.md` 能被找到(验完删除测试文件);
2. 现有三篇示例日报构建结果与改动前逐字节一致(manifest 时间字段除外);
3. 两文件同 date 场景:警告 + 后者被跳过,无覆盖。

---

## 4. 【P1】build.py:Windows 控制台中文输出乱码

### 4.1 现状问题

`build.py` 的构建摘要为中文,在 Windows GBK 控制台(PowerShell 默认 cp936)下全部 mojibake。

### 4.2 修复方案

`main()` 开头加:

```python
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
```

不引入环境变量方案(PYTHONIOENCODING),不改 print 内容。

### 4.3 验收

Windows PowerShell 下运行 `build.py`,摘要中文可读;Cloudflare CI(UTF-8 环境)行为不变。

---

## 5. 【P2】杂项健壮性与维护性修复

### 5.1 离线版隐藏搜索按钮

`search.js` 的 `init()` 在 `data-offline` 时提前 return,但右上角搜索按钮仍显示、点击无响应。改为:

```js
if (document.body.dataset.offline === "true") { open.hidden = true; return; }
```

**验收**:离线版无搜索按钮;在线版按钮与搜索功能不变。

### 5.2 缓存戳自动化

`site/index.html` 中 CSS/JS 引用带手写 `?v=20260708`,更新前端资源时容易忘记升版本导致用户命中旧缓存。改为构建时注入:

- `build.py` 在 `prepare_output()` 拷贝完成后,对 **输出目录** 的 `index.html` 做正则替换:`\?v=\d+` → `?v=<本次构建时间 YYYYMMDDHHMMSS(CN_TZ)>`;
- 源文件 `site/index.html` 保持手写占位值不动(dev 时直接开 site/ 目录不受影响);
- 在线与离线构建都执行(离线注入需发生在 `inline_offline_data()` 读取 index.html 之前或之后皆可,但注意两步都对同一文件读写,别互相覆盖——建议把替换并入现有读写链)。

**验收**:`dist/index.html` 与 `dist-offline/index.html` 中所有 `?v=` 均为本次构建时间;两次构建值不同;页面加载无 404。

### 5.3 时间轴/meta 的 innerHTML 转义

`daily.js` 中 `renderTimeline()` 与 `renderMeta()` 把 `item.title`、`item.summary`、`stage.label` 直接拼入 `innerHTML`,标题含 `<`、`&` 时渲染损坏。加一个模块内 `escapeHtml(text)` 工具(替换 `& < > " '` 五个字符),对所有拼入 HTML 的**内容字段**套用;`item.date`、`item.has_show` 等构建器生成字段可不处理。`title` 属性(tooltip)拼接处同样注意引号。

**验收**:临时构造标题含 `<b>x</b> & "q"` 的日报,时间轴与 meta 行按字面显示、不渲染为标签、无属性溢出(验完还原)。

### 5.4 离线版 `.show.html` 保真内联

现状:完整 HTML 文档被内联进 `<template>`,HTML 解析器会剥离 doctype/`<html>`/`<head>`/`<body>` 结构标签(`<style>`/`<script>` 保留,但 `<meta charset>`、`<title>`、viewport 丢失),离线版 srcdoc 拿到的是降解后的文档,与在线版行为存在差异。

修复:`.show.html` 类型改用 **JSON 载体**内联,绕过 HTML 解析:

- `inline_offline_data()` 中,`show_type == "html"` 的页面不再写 `<template>`,改写:

  ```html
  <script type="application/json" id="daily-show-html-<date>">…json.dumps(content)…</script>
  ```

  注意用 `json.dumps(content).replace("</", "<\\/")` 防止内容中的 `</script>` 提前终结载体(JSON 允许 `\/` 转义,`JSON.parse` 结果不变);
- `daily.js` 的 `renderShow()`(或 `loadFragment` 内)对 html 类型优先查 `daily-show-html-<date>` 的 JSON script,命中则 `JSON.parse(textContent)` 后赋给 `srcdoc`;未命中(在线模式)维持现有 fetch 路径;
- `.show.md` 类型的 `<template>` 内联机制**不动**;
- 在 README 的 `.show.html` 约定处补一句:定制页应自包含,不要依赖 `<head>` 中的外部引用(现状约束重申)。

**验收**:断网 + `file://` 打开离线版,`#/daily/2026-07-06/show` 的 iframe 内脚本交互正常,且 iframe 文档保留完整 `<head>`(DevTools 检查 srcdoc 内容含 `<meta charset>`);在线版行为不变。

### 5.5 wrangler.jsonc 清理

删除指向不存在文件的 `"$schema": "./node_modules/wrangler/config-schema.json"` 行,其余不动。

---

## 6. 【P2】文档更新(不要遗漏)

1. **DEPLOY.md 第 2 节改写**:现部署形态是 **Workers 静态资产**(`wrangler.jsonc` 的 `assets.directory` + `npx wrangler deploy`),不是 Cloudflare Pages。按 Workers Builds 的实际路径重写:Workers & Pages → 导入 Git 仓库、Build command / Deploy command 填法维持现有命令、`PYTHON_VERSION` 环境变量说明保留;
2. **DEPLOY.md 第 3 节 Access 部分改写**:Worker 的 Access 启用路径是 Workers 项目 → Settings → Domains & Routes → workers.dev → Enable Cloudflare Access(而非 Pages 的 Access integration);明确写出:**必须确认 preview 版本 URL(`<version>-<name>.<subdomain>.workers.dev`)在保护范围内**;
3. **DECISIONS.md** 追加本次决策:展示模式单列布局采用 JS 模式类而非 `:has()`;离线 `.show.html` 改 JSON 载体内联的原因(HTML 解析器剥离结构标签);
4. **README.md**:`.show.html` 写作约定处补充 5.4 的自包含提醒。

---

## 7. 明确不做

- 不改主 Showcase 的任何交互、布局与键盘语义;
- 不改右侧时间轴列宽(`.daily-view` 外层网格维持 `minmax(280px, 30%)`);
- 不给展示幕内容加 `max-width` 阅读宽度限制;
- 不做 `.show.html` 的内容净化/安全过滤(沿用 PLAN-2 §4 的决策,sandbox iframe 已隔离);
- 不引入任何构建期或运行期新依赖(无新 npm 包、无新 pip 包);
- 不改 `?v=` 以外的 index.html 内容,不引入打包器。

---

## 8. 回归验收清单(全部通过才算完成)

1. 第 1–5 节各自的验收项逐条过;
2. PLAN.md 第 11 节 + PLAN-2.md 第 5 节原有验收项全量回归(尤其:双 Tab hash 前进后退、`.show.md` 键盘切幕与主 Showcase 翻屏互不干扰、无展示版日期的禁用态与 `/show` 深链回落、搜索命中展示内容跳转 `/show`);
3. 在线构建与离线构建各跑一次,构建摘要 0 警告(第 3 节新增警告仅在人为构造异常输入时出现);
4. 浏览器 console 在文档/展示两种模式、在线/离线两种构建下均无报错;
5. `git status` 干净:所有源文件改动已提交,`dist/`、`dist-offline/` 不入库(维持 .gitignore 现状)。

---

## 9. 实施顺序建议

M1 第 1 节布局修复(P0,先解用户可见故障)→ M2 第 2 节 TOC 修复(P0)→ M3 第 3、4 节 build.py(P1)→ M4 第 5 节杂项(P2,其中 5.4 最后做,改动面最大)→ M5 第 6 节文档 → M6 第 8 节全量回归。

---

## 附:人工核查项(非代码,codex 不处理,由维护者在 Cloudflare Dashboard 操作)

- 确认 Access 应用同时覆盖生产 workers.dev 域名与 preview 版本 URL;
- 登录后在浏览器 DevTools → Network 确认任意页面响应头含 `X-Robots-Tag: noindex, nofollow`(验证 `_headers` 在 Workers 静态资产上生效);
- 若生产构建走 Workers Builds CI:检查线上 `manifest.json` 的 `time_source` 是否为 `git`(浅克隆降级)、`dist/pagefind/` 是否生成(npx 首次拉取 pagefind 可能超时,构建只警告不失败,搜索会静默缺失)。
