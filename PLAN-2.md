# PLAN-2 — 增量需求:每日展示版 + 精确发布时间

> **性质**:这是对已按 PLAN.md 完成实施的 `internship-dashboard` 代码库的**增量变更单**,不是重写。
> **执行前置**:先通读现有 `build.py`、`site/js/`(router/daily/showcase/search)、`templates/`、`manifest.json` 的实际结构,理解现状后再动手。所有改动不得破坏 PLAN.md 第 11 节已通过的验收项(交付前须全量回归一遍)。
> 未定义细节沿用 PLAN.md 第 1.2 节技术原则裁决;本文件与 PLAN.md 冲突时以本文件为准。新决策记入 `DECISIONS.md`。

---

## 1. 需求 A:每日页面双 Tab(文档 / 展示)

### 1.1 动机(理解意图,别做偏)

主展示板(Showcase)呈现的是**多天打磨后的最终形态**;但每一天的工作本身也可能很复杂,仅靠文档难以看懂。因此每天的页面要能同时提供两种视图:
- **文档**:现有的 md 渲染结果(维持不变);
- **展示**:该天专属的、单独撰写的**迷你交互展示板**——主 Showcase 的简化版,只展示当天内容。

"展示"是**每天单独定制撰写**的,不是从文档自动生成的。允许某些天没有展示版(尤其历史日期),此时该 Tab 呈禁用态。

### 1.2 内容层:文件约定

`content/daily/` 下,每一天最多三个文件:

| 文件 | 作用 | 必需性 |
|---|---|---|
| `YYYY-MM-DD.md` | 文档 Tab(现状不变) | 必需 |
| `YYYY-MM-DD.show.md` | 展示 Tab,标准写法 | 可选 |
| `YYYY-MM-DD.show.html` | 展示 Tab,完全定制写法 | 可选 |

- `.show.md` 与 `.show.html` **二选一**;两者同时存在时 `.show.html` 生效,构建时打印警告;
- 只有 `.show.*` 而没有主 `.md` 的日期:警告并跳过该展示文件(展示必须依附于文档存在);
- 构建时 `build.py` 扫描并将结果写入 manifest(见 1.5)。

#### `.show.md` 结构约定(标准写法)

```markdown
---
title: "撤单生存时间指标:当日成果"   # 可选,缺省用日期
---

## 幕一:问题与思路
(正文,可用折叠块、表格、代码块,语法与 showcase md 完全一致)

## 幕二:指标构建
??? note "构建方法细节"
    ...

## 幕三:当日运行结果
...
```

- **每个 H2 = 一"幕"(sub-screen)**,构建时按 H2 切分为若干片段;
- 幕内支持 PLAN.md 3.4 节定义的全部 Markdown 能力(折叠块/admonition/代码高亮/表格);
- 无 H2 的文件视为单幕。

#### `.show.html` 约定(定制写法,逃生舱)

- 一个**自包含**的 HTML 片段或完整文档:自带 `<style>`/`<script>`,不依赖主站 CSS/JS,不引用任何外部 CDN(离线约束);
- 前端通过 **iframe `srcdoc`** 呈现(见 1.4),因此其脚本可自由执行且与主站完全隔离;
- 在 `templates/`(或 `docs/` 内合适位置)提供一个 `show-html-starter.html` 示例模板:内含主站深色 token 的一份**拷贝**(CSS 变量段,注释注明"与 tokens.css 手动保持同步"),让定制页默认视觉与主站一致。

### 1.3 前端:每日页面的 Tab 结构

- Daily 视图文档区顶部增加一组**局部 Tab**:「文档」「展示」(注意与右上角全局双 Tab 在视觉层级上区分开——局部 Tab 更小、位于内容卡片头部);
- 路由扩展:
  - `#/daily/<date>` → 文档 Tab(向后兼容,现有深链全部不变);
  - `#/daily/<date>/show` → 展示 Tab;
  - 切 Tab 更新 hash,前进后退可用;
- 该日期无展示版时:「展示」Tab 置灰禁用,悬停提示"当天未撰写展示版";直接访问 `…/show` 深链时回落到文档 Tab 并短暂提示;
- **时间轴节点**上,为有展示版的日期加一个小标识(如一个与阶段色协调的小图标/角标),让"哪些天有展示版"一眼可见。

### 1.4 前端:展示 Tab 的渲染

**`.show.md`(迷你展示板)**:
- 在文档区内呈现为**幕式翻页**:一次显示一幕,底部(或侧边)有「上一幕/下一幕」箭头 + 幕点指示器(dots,当前幕高亮,可点击直达);
- 键盘 ←/→ 切幕(注意与主 Showcase 的 ↑/↓ 翻屏语义区分,且仅在展示 Tab 激活时监听,避免全局键盘冲突);
- 幕的切换动画克制(横向滑动或淡入,遵守 `prefers-reduced-motion`);
- 幕内容超高时幕内滚动;
- 折叠块/卡片/表格样式**直接复用**主站现有 CSS(tokens/showcase 的类),不新造一套;
- 不需要左侧全局 stepper(那是主 Showcase 的);幕点指示器就是它的简化对应物。

**`.show.html`(定制页)**:
- 以 `<iframe srcdoc="…">` 注入(sandbox 属性:允许 `allow-scripts`,不加 `allow-same-origin`;若现有功能因此受限,在 DECISIONS.md 记录取舍);
- iframe 占满文档区宽度,高度策略:默认固定为文档区可视高度、iframe 内部自行滚动;
- **技术要点(必须这样做)**:定制页的 `<script>` 若用 innerHTML 直接注入是不会执行的,srcdoc iframe 是本方案选定的执行机制,不要改用动态 createElement('script') 重放等 hack。

### 1.5 manifest 扩展

`daily` 数组每条新增字段:

```json
{
  "date": "2026-07-07",
  "...": "现有字段不变",
  "has_show": true,
  "show_type": "md",            // "md" | "html" | null
  "show_path": "daily/2026-07-07.show.html或渲染产物路径"
}
```

`.show.md` 的构建产物为切幕后的 HTML 片段(结构由实施者定,如单文件内以 `<section data-scene>` 分幕);`.show.html` 原样(或最小处理后)拷入产物目录。

### 1.6 离线模式

- `.show.md` 产物与现有内容一样内联进 `<template>`;
- `.show.html` 内容内联(如放入 `<script type="text/html">` 或 template)后在运行时赋给 iframe 的 `srcdoc` 属性——**断网 + file:// 下展示 Tab(含定制页脚本交互)必须完整可用**,列入验收。

### 1.7 搜索

- `.show.md` 的内容也生成 Pagefind 可索引页,`data-pagefind-meta` 增加 `view: 展示`,搜索结果跳转到 `#/daily/<date>/show`;
- `.show.html` **不索引**(内容结构不可控,跳过并在构建摘要中注明数量)。

---

## 2. 需求 B:精确发布时间(年-月-日 时:分:秒)

### 2.1 时间来源(严格按此优先级)

对每篇日报(以主 `.md` 文件为准)确定两个时间戳:

**`published_at`(首次上传时间)**:
1. frontmatter 显式字段 `published: 2026-07-07 21:34:12`(手动覆盖,最高优先);
2. **git 中该文件首次被 commit 的 author 时间**:`git log --follow --diff-filter=A --format=%aI -- <file>` 取最早一条;
3. 文件系统 mtime 兜底,并在构建摘要中警告"该篇时间来自 mtime,可能不准"。

**`updated_at`(最后更新时间)**:
1. git 中该文件最后一次 commit 时间;
2. mtime 兜底(同样警告)。

### 2.2 实现要点

- git 调用用 `subprocess`,cwd 指向仓库根(注意父路径含空格与 emoji,沿用 pathlib,参数列表形式调用避免 shell 转义问题);
- **浅克隆防御**:构建环境(Cloudflare Pages)可能浅克隆导致首次 commit 时间不可得。build.py 须:检测 `.git/shallow` 存在 → 先尝试 `git fetch --unshallow`(失败不中断)→ 仍拿不到完整历史时按 2.1 的降级链走并在摘要中说明。DEPLOY.md 增补一节:如需在 CF Pages 上稳定获得 git 时间,可在构建命令前置 `git fetch --unshallow || true`,或干脆建议用户在 frontmatter 里补 `published`;
- git 不可用/不在 git 仓库中(如用户把 content 拷出来单独构建):整体降级 mtime,一次性警告;
- 所有时间戳统一转为 **Asia/Shanghai** 时区,manifest 中存 ISO8601(含时区偏移),前端显示格式 `YYYY-MM-DD HH:MM:SS`。

### 2.3 呈现位置

- **文档 Tab 头部 meta 行**:`发布于 2026-07-07 21:34:12 · 最后更新 2026-07-08 09:12:03`(两者同一分钟内则只显示发布时间);meta 行用金属灰次级文字样式;
- **时间轴节点**:悬停提示(现有 summary tooltip)中追加发布时间一行;
- manifest `daily` 条目新增 `published_at`、`updated_at`、`time_source`("frontmatter"|"git"|"mtime",便于排查)。

---

## 3. 连带更新(不要遗漏)

1. **README.md**:日常写作流程增补——如何为某天撰写展示版(两种写法、模板位置)、published 字段何时需要手填;
2. **DEPLOY.md**:增补 2.2 的浅克隆说明;
3. **示例内容**:现有示例日报中,一篇配 `.show.md`(≥3 幕,含折叠块与表格,演示标准写法),一篇配 `.show.html`(含一个简单可交互元素——如一个点击切换的图表占位或可排序表格,演示脚本在 srcdoc 中确实执行),一篇不配(演示禁用态)。示例内容延续 PLAN.md 第 8 节的"明显虚构"约束;
4. **构建摘要**扩展:展示版统计(md 几篇 / html 几篇 / 无展示几篇)、时间来源统计(git/frontmatter/mtime 各几篇)。

---

## 4. 明确不做

- 不做"从文档自动生成展示版"——展示版永远是人工撰写;
- 不改动主 Showcase 的任何交互与结构;
- 不做展示版的编辑器/预览工具;
- `.show.html` 不做任何内容净化/安全过滤(全站在 Access 门禁内、内容为用户自产,iframe sandbox 已提供隔离)。

---

## 5. 验收标准(在 PLAN.md 第 11 节全量回归通过的基础上,新增)

1. 三篇示例日报分别验证:`.show.md` 幕式翻页(箭头/键盘/dots 均可用,折叠块正常)、`.show.html` iframe 内脚本交互确实可执行、无展示版日期的 Tab 禁用态与 `/show` 深链回落;
2. `#/daily/<date>` 与 `#/daily/<date>/show` 双向切换 hash 正确,浏览器前进后退可用;现有旧深链行为不变;
3. 时间轴上有展示版的日期出现标识;
4. 文档头部 meta 行显示精确到秒的发布/更新时间;git 环境下 `time_source == "git"`,人为制造浅克隆或移出 git 目录时降级链生效且有警告;frontmatter `published` 能覆盖 git 时间;
5. 离线版:断网 + file:// 下,展示 Tab(含 `.show.html` 的脚本交互)完整可用;
6. 搜索:`.show.md` 内容可被中文关键词命中且结果跳到展示 Tab;`.show.html` 未被索引;
7. 主 Showcase 键盘翻屏与展示 Tab 键盘切幕互不干扰;
8. 构建摘要包含第 3.4 条要求的新统计;README/DEPLOY 增补到位;
9. 浏览器 console 两种模式下均无报错。

---

## 6. 实施顺序建议

M1 内容层与构建(扫描 .show.* / 切幕 / manifest 扩展 / 时间戳采集含降级链)→ M2 每日局部 Tab 与路由 → M3 迷你展示板交互(.show.md)→ M4 iframe srcdoc 通道(.show.html)与离线内联 → M5 时间显示、时间轴标识、搜索接入 → M6 示例内容、文档增补、全量回归自检。
