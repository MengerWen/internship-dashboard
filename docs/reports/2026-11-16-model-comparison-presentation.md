# 2026-11-16 模型汇报的布局与收益口径

11.9 与 11.16 展示页依次呈现收益图、分段集成成绩、累计 IC／RankIC。收益图上的“绝对／超额”按钮同时控制成绩表全部指标，包括日均收益、累计收益、Sharpe、回撤、卡玛、波动、胜率、赔率和 t 值。

11.9 沿用策略绝对收益及现有基准差额：L 对比同市场同周期成分池等权中间价收益，A 对比同市场、周期、选股比例及税费口径的全市场 A。全市场页保留超额按钮禁用状态。11.16 的绝对收益包含底仓和做 T；日超额为做 T 增量损益除以昨日底仓，分段累计超额按该市场初始底仓折算。表格说明同步解释胜率的统计对象。

## 实现复用

| 入口 | 决定 |
| --- | --- |
| `build_20261109_fill_rules.replace/render` | 复用唯一锚点替换与现有生成路径，新增共用的 `comparison_layout` 排列顺序和按钮文案；两种生成器均调用。 |
| 11.9 内嵌 `returnPoint/stageMetrics/updateScoreRows/refreshReturns` | 直接复用口径切换与统计；补充表头和基准、胜率说明。 |
| `csi2000_market_comparison.timelineFor/updateScoreRows/changeFilters` | 直接复用两条收益序列与全部统计，仅调整公开名称和说明。 |
| `build_20261116_base_position.render/comparison_script` | 复用冻结模板及已签收的内嵌数据生成页面，保持图表容器、日期联动和数据内容。 |
| `check_csi2000_market_comparison.cjs` | 复用现有离线脚本检查；增加胜率、Sharpe 与口径标识核对。 |

## 设计技能核对

已按当前全局、项目及插件清单定位并读取下列技能入口。此任务是既有研究页面的指定调整，采用现有纸墨体系、数字对齐、原生按钮和 `aria-pressed` 状态。通用技能的新建视觉方向、多稿选择、素材生成、浏览器截图等流程不适用于本次交付范围；按项目汇报发布规则进行源码、生成和脚本检查。

- 界面：frontend-design、design-taste-frontend、impeccable、ui-ux-pro-max、emil-design-eng、web-design-guidelines。
- 原型与视觉：huashu-design、prototype、figma-implement-design、canvas-design。
- 图片：imagegen、autoglm-generate-image、autoglm-search-image。
- 图表：diagram-design。
- 演示与排版：presentations:Presentations、google-drive:google-slides、visualize:visualize、documents:documents、pdf:pdf、spreadsheets:Spreadsheets、spreadsheets:excel-live-control。
- 交付流程：brainstorming、sites:sites、sites:sites-remix、template-creator:template-creator、work-pets:create-pet、work-pets:update-pet、work-pets:pets。
- 架构：architecture-designer、codebase-design、domain-modeling；另核对当前清单新增的 improve-codebase-architecture。当前任务无需架构重构。

主要采用 frontend-design 的既有视觉约束、impeccable 的 Operate／Read 布局和文案原则、emil-design-eng 的即时状态反馈，以及 Code 和 shuorenhua。未调用图片生成、文档排版、网站注册或研究计算。

## 产物

唯一正式来源为本仓库的两篇日报、展示页和生成脚本。本任务临时日志位于 `.local/runs/model-comparison-presentation-20261116/`，预算 20 MiB；消费者为本次脚本检查和发布回执，关键结果入库后释放可重建日志。复查日期为 2026-11-23。部署复用现有 `dist/` 与资源缓存。

## 检查结果

生成与展示路径相关测试通过 7 项及 6 个子用例。11.16 离线脚本通过 64 组筛选，核对未看段的均值、累计收益、Sharpe、胜率和口径说明，并沿用日期、曲线、放大与恢复的原有脚本检查。11.9 通过真实按钮回调切换两种收益口径，在两种排序、两种税费口径下核对 768 行成绩的均值、累计收益、Sharpe 和胜率。

两份 HTML 的标记闭合、ID 唯一性及 JavaScript 语法检查通过；收益图、成绩表、信号图均保留在共用交互容器中。两页所有内嵌数据块与修改前逐字一致。以上均为源码和脚本检查，未进行浏览器或发布后页面检查。
