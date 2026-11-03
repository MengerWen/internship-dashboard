# 研究日志：五种展示方式

本轮目标：让用户直接操作五种不同结构，选择研究日志的展示方式。它们共用现有真实记录与「研究编辑台」的字体、纸墨配色和版线。

入口为 `index.html`，完整演示为 `demo.html?variant=A` 至 `E`。本目录是设计初稿，不替换正式页面；当前尚未选定方案。

| 方案 | 主要入口 | 用户可以体验的操作 |
| --- | --- | --- |
| A 方向总览 | 先看七个方向，再展开一个方向 | 切换时间范围、展开方向、选择链、读取具体进展 |
| B 按日日志 | 先看这一天做了什么 | 搜索、筛选方向、按月定位、打开一天与单链 |
| C 链条工作台 | 先找到一条具体研究链 | 搜索链、按方向筛选、阅读链的目标及完整时间线、查看承接 |
| D 阶段章节 | 先理解研究怎样走到现在 | 在五个研究阶段之间切换、展开阶段内任务、阅读链与工作点 |
| E 月历日程 | 先选日期，再看当天的并行工作 | 切换月份、点选日期、筛选方向、查看具体进展 |

五版统一使用截至最新记录日的内容源。计数由源数据计算，工作点展示本链注解；不把每日总标题当作单链进展，不将提交量解释为工作价值。日期筛选会明确显示范围。

设计取舍：本轮探索信息组织和交互结构，沿用既有视觉身份；用户要求至少五个可操作 Demo，故扩展默认三方向流程。真实日志本身承担视觉内容，不额外生成图片。按项目要求，本轮交付以文件、提交和远端包含目标提交为准，不额外安排浏览器验收或截图。

## 文件协作约定

`data.js` 由 `export_data.py` 从当前正式内容导出。`shared.js` 提供共同的链条、日期和工作点阅读层。五个方向分别在 `variants/` 中实现，各方向只维护自己的文件。

所有方向注册为 `window.JournalVariants.A` 至 `E`，值为 `function(root, api)`。调用后负责在 `root` 中绘制本方向，事件可在 root 上代理；不监听全局键盘，不改写其他方向状态。

`api` 提供：

- `data`：`{tracks, chains, days, handoffs, counts, asOf}`；day.chains 为 `{id, note, outcome}`。
- `esc(value)`：HTML 转义。
- `chain(id)`、`track(id)`、`day(date)`：查询数据。
- `dayTasks(day)`：当天各点，返回 `{date, note, chain, day, outcome}` 数组。
- `points({chainId, trackId, from, to, query, reverse=true})`：按条件取得相同结构的工作点。
- `chainLink(id, text?)`、`pointLink(point, text?)`：生成可打开共同阅读层的按钮。
- `openChain(id)`、`openDay(date)`、`openPoint(date,id)`：直接打开共同阅读层。
- `formatDate(date)`：显示月份与日期；`range('1m'|'3m'|'all')` 返回 `{from,to}`，以最后记录日为终点。

通用样式：`.button`、`.button.is-active`、`.subtle-button`、`.muted`、`.serif`、`.toolbar`、`.field`、`.empty`、`.section-heading`、`.chain-link`、`.task-note`、`.date-label`。各方向 CSS 以 `body[data-variant="A"]` 等限定范围。

## 复用与保存

本目录直接复用站点字体与颜色令牌，不增加依赖。可以直接打开 `index.html`。`build_inline.py --output 完整输出路径` 将相同五版打包为对话内预览，使用宿主提供的五版切换；不启动服务，不改变正式页面。

本轮完成了全部 JavaScript 语法解析、HTML 本地资源引用核对，以及五版在离线 DOM 占位环境中的初次内容生成检查。这些检查不代表浏览器实测，按本项目规则未另行安排浏览器验收或截图。

本轮尝试用 PowerShell `Start-Process python -m http.server 8765 --bind 127.0.0.1 -WindowStyle Hidden` 启动本地预览；外层执行请求被拦截，工具返回 `rejected: blocked by policy`，未启动进程。没有修改策略或换入口重试，改为直接文件与无服务内嵌预览。

复查日期：2026-11-10。方向未选定前保留五版；选定后记录用户原话，再实施正式页面。
