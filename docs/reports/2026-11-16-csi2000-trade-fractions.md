# 2026-11-16 做T比例筛选

11.16汇报增加每只入选股票昨收底仓市值的10%、20%、30%三档做T比例。每档覆盖原有64配置、566日，共192配置。默认10%；比例切换更新收益曲线、全部分段指标和悬浮读数，当前比例同时出现在图题和成绩说明。底仓及IC沿用共同来源。

## 实现与数据

复用`build_20261116_base_position.pack/render/comparison_markup`，严格核对三档配置及实际交易金额覆盖；复用`timelineFor/updateScoreRows/changeFilters`和原日期、图例、放大交互，只增加配置键的比例维度。`refreshSelection`缓存身份纳入比例，避免固定读数在切换后沿用旧值。原生select沿用既有label、字体、间距、焦点及换行方式。

数据来自研究仓库`1e74e18b154a71a8548b42284e3d46cdc066032d`实际运行，签收对象SHA-256为`cccc7033c09e85bd4e4f1a5c7d1712d3acbb8bd04a2cb836f537b6a3217ecb4c`。三档独立连续回放，费用与库存约束逐档生效。原10%的36,224行曲线和交易金额、全部共用底仓与原已发布页面逐格一致。

## 设计技能核对

本次按全局、项目及插件清单核对设计入口，沿用[既有汇报设计清单](2026-11-16-model-comparison-presentation.md#设计技能核对)的类别：界面六项；原型四项；图片三项；diagram-design；演示、可视化、文档与表格；brainstorming、sites、template-creator、work-pets；architecture-designer、codebase-design、domain-modeling。按当前安装路径读取相关SKILL.md，另读design-taste-frontend的app-screens参考。当前任务为既有页面的控件迭代，主要采用frontend-design的上下文复用、impeccable的操作与读数对应、emil-design-eng的即时状态反馈，以及brainstorming的范围与方案核对。

沿用已确定的视觉方向，控件放在选股比例与阶段之间。相较独立三页或同时叠加12条曲线，比例筛选更便于逐档保持相同配置。无需新建视觉稿、图片、演示文稿、数据库或系统架构。用户对汇报发布的明确交付规则优先于技能默认的浏览器和截图流程。

## 检查与产物

生成测试5项通过，核对三档覆盖、实际费率和交易金额、配置缺失拒绝、保护模板路径及JavaScript语法。离线脚本执行192组筛选与收益口径组合，按实际数据核对均值、交易净收益、Sharpe、胜率、累计收益和比例标签，并检查日期、图例、放大、恢复和IC交互；均通过。以上属于源码、数据和脚本检查。

正式来源为日报、展示页、生成脚本与上述测试；完整数据由研究仓库签收对象保留。临时目录为`.local/runs/csi2000-ratios-20261116`，预算100MiB，消费者为本次生成与发布；关键收据入库后释放可重建材料，复查日期2026-11-23。发布复用现有dist、附件、日报渲染及资源哈希，收据保存于`artifacts/csi2000-ratios-20261116/release-receipt.json`。

本次参考：Code、shuorenhua、frontend-design、design-taste-frontend、impeccable、ui-ux-pro-max、emil-design-eng、brainstorming。
