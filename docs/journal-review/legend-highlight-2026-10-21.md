# 研究日志图例高亮验收

2026-10-21，在 `902b03b` 基线上加入图例交互。实现、样式、验收脚本和本记录随同一个功能提交保存。验证时 `site/js/journal.js` 的 SHA256 为 `FCEE975D557C7A47F923969C8CFAC785D6BC4409A5C868438C42BF9069D9E8A8`。

四项图例分别匹配交接数据的延续、派生、依赖解除、收口。匹配线使用焦点色、2.6px 线宽及完整不透明度；其他交接降低不透明度，链内记录保留作背景。单选切换、重复点击取消、Esc、空白和“取消选中”均有效。按钮有 `aria-pressed`，键盘焦点在重绘后保留，Enter／空格可操作。

本地验证使用 `.codex-vet-journal-legend/source`：从已提交基线导出源码，只覆盖本次 JS／CSS 后构建在线版和离线版，未带入主目录中未提交的研究材料。浏览器使用本机 Chrome。

- `npm test`：14 项通过。
- `scripts/verify_journal_legend.cjs`：1440、768、390px 和离线版通过；四类关系的匹配样式、切换／取消、键盘、密度、时间窗、尺寸变化和旧选择切换均通过，页面错误为 0。离线版 HTTP 请求为 0。
- `scripts/verify_journal.cjs`：三种宽度下均为 88 个日志日、28 条链、151 条注解；日期／链条／单点交互、底纹、缩放、模拟未采用／暂搁状态与离线证据读取通过，页面错误为 0。
- Impeccable 机械检测：空结果；JS 语法和 Git 空白检查通过。

浏览器结果见 `artifacts/journal-legend/results.json`、`artifacts/journal-legend/regression/verification.json`；有效桌面和手机截图为该目录中的 `1440-report-highlight.png` 和 `390-report-highlight.png`。采用当前视口截图，避免 Chrome 长图中固定刊头错位及 SVG 重绘造成的失真。

主会话原始运行记录确认为 `gpt-6.1-sol / xhigh`。未派生子代理，未调用设计技能示例中的外部模型。图片、演示、宠物和模板创建工作流不适用于本次既有页面交互；保留已批准的推进图谱方向，采用原生按钮、既有颜色令牌和真实浏览器验证。

本记录确认本地实施与验收，不据此推断线上发布状态。
