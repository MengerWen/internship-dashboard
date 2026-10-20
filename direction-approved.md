# 设计方向批准记录

## 已展示方向

- 方向 A「信号切面」
  - 原型：`design-demos/direction-a-signal-slice.html`
  - 截图：`design-demos/screenshots/direction-a-signal-slice.png`
- 方向 B「研究编辑台」
  - 原型：`design-demos/direction-b-research-desk.html`
  - 截图：`design-demos/screenshots/direction-b-research-desk.png`
- 方向 C「数据旅程图谱」
  - 原型：`design-demos/direction-c-data-atlas.html`
  - 截图：`design-demos/screenshots/direction-c-data-atlas.png`

## 用户选择原话

> 实施方案B，对当前项目进行修改

## 批准结论

以方向 B「研究编辑台」作为当前项目的正式视觉方向。实施范围包括：站点顶栏、全局设计令牌、正式成果页、每日报告阅读页、搜索对话框、表格、代码块、折叠内容和响应式样式。保留现有路由、内容构建、全文搜索、展示模式、下载、阶段导航及键盘操作。

记录日期：2026-08-11

## 2026-09-18 模型报告

用户于 2026-09-19 确认：

> 沿用现有样式，直接完成并发布

模型报告沿用研究编辑台及 2026-09-16 展示页的纸色、青绿/赭红配色、章节导航和图表放大方式。新增数据图表，不重新探索视觉方向。桌面与手机均需验证可读性；不加入装饰性图片。

## 2026-10-18 深市328列成果报告

用户要求“详细参照这份之前的报告”，确认交付“看板展示页＋Markdown”，并补充“看板展示页请尽量参照以前的展示页的实现方式和细节”。本篇沿用2026-09-16展示页及研究编辑台的既定方向，复用导航、筛选、逐列查看、放大、下载与响应式约定。新结果使用本次328列验收汇总，不沿用旧报告的收益统计。

## 2026-10-20 新栏目「研究日志」

就新栏目做了三个方向的真实原型（同一份 92 天真实数据，`design-demos/journal-prototype/`）：

- 方向一「研究台历」
  - 原型：`design-demos/journal-prototype/direction-1-ledger.html`
  - 截图：`design-demos/screenshots/journal-1-ledger*.png`
- 方向二「链轨」
  - 原型：`design-demos/journal-prototype/direction-2-chain-rail.html`
  - 截图：`design-demos/screenshots/journal-2-chain-rail*.png`
- 方向三「推进图谱」
  - 原型：`design-demos/journal-prototype/direction-3-atlas.html`
  - 截图：`design-demos/screenshots/journal-3-atlas*.png`

用户选择原话：

> 我想在方向三的基础上推进。但方向三本身还是否能再polish？再细化设计

结论：新栏目采用方向三「推进图谱」。视觉仍在研究编辑台体系内，不新增颜色令牌。
同日按该选择做了第二轮细化（横轴改真实日期、时间窗、直接标注、每日汇报刻度行、
链条聚焦、清单孪生视图、键盘换日），原型即 `direction-3-atlas.html` 当前版本，
设计说明见 `docs/plans/2026-10-20-journal-column-design.md` 与
`design-demos/journal-prototype/README.md`。
