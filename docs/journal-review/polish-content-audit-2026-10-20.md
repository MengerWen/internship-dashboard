# 研究日志内容核查与文案修订

核查日期：2026-10-20。范围是当前研究日志、任务关系与其展示的汇报摘要。原有逐月审阅保留为历史，本文件补充本次查出的遗漏和修订。

逐日核对 88 个日期、28 条任务链；140 条旧注解修订后为 151 条，新增 11 条来自原来漏列的并行工作。另改写 32 篇真实汇报的摘要，逐份比较后确认报告正文未变。两个示例日报继续标为示例，不用作真实工作的覆盖依据；用户原有未跟踪的 10 月 10 日草稿保持原样。

## 证据范围

按以下固定版本检索了 88 天、2740 次提交的标题、路径和日期，再与每一天的摘要、计划和报告对照。涉及“完成”“停止”和性能结果的重点项，另读取原始计划或已提交验收报告。这里没有声称逐行审阅全部提交差异，也没有重新运行研究、训练模型或复验服务器历史结果。

| 仓库 | 固定版本 |
|---|---|
| sirui-quant-research | `e488eaa6a3fe547c871ea396cfeef7761e6d8883` |
| Quant_Research-Trading | `ee956d57ef3bd8e8c3290ba84a294b0409f824c8` |
| internship-dashboard | `d55c7f6a227aead85f7c1a620def73c91370fbfa` |

看板版本更新到本轮开始前已完成 v2 的 `d55c7f6`，研究仓与父仓仍保持原来的固定版本，避免把运行中的新研究混入这次整理。现有证据展示每仓前 10 条提交；当天计数使用全部提交，包含父仓子模块更新，不能当成独立成果数或工时。

## 影响事实表达的修正

| 原问题 | 本次处置与根据 |
|---|---|
| 7 月 6 日真实工作指向“示例日报：快照重放原型” | 原文明确写“所有数值均为虚构占位”。移除它的真实工作覆盖，改关联实际说明六篇论文指标的 7 月 7 日报告。发布记录仍如实记录示例文件曾被发布。 |
| 6 月 30 日快照注解把因子 Notebook 修复混写为快照修复 | `aa08efcf` 实际修改快照数据说明，Notebook 的修复在 factor_lab；两项分别写清。 |
| 9 月 1 日把 A_clean_max 计划写成已实现 | 当日主要是方案和预注册修改，改为“制定方案”；已实现的撤单相位统计另列。 |
| 跨股票同步 C3.3 被整条“深度匹配”链的完成状态掩盖 | 原计划注明 9 月 11 日已放弃，`9e26b6ed` 于 9 月 18 日补记及清理。补入停止记录；深度匹配 601 日结果保留。 |
| 10 月 13 日只列沪市工作，漏掉深市恢复和压力日验收 | `d119b3a3` 是五个压力日验收；`910bb8c2` 记录 Doris 恢复后 21/601 日状态。不能提前写成全期完成。 |
| 9 月 4/10/18 日与 10 月 9/11/13/14/15/16 日漏列并行工作 | 根据相应日期原始提交补入报告、机械撤单、跨股预查、沪市适配、深市续算等 11 个（日、链）组合。逐日索引见下表。 |
| 10 月 15 日“停止后续研究”可能被误写成全部结果废弃 | `2497d417` 将生命周期标为 `retired_after_point_estimate_acceptance`，现有因子入口仍独立工作。只写后续生成停止，不新增“未采用”叉号。 |
| 计算提速被写成因子表现变好 | 8 月 6/7 日等项改写为读取、回放、评分的速度修改，预测效果另看评价。9 月 3 日保留未达到 60 秒目标。 |
| 链条成果链接串到其他报告 | 深度匹配指向 9 月 7 日；模型执行指向 8 月 19 日；撤单分布指向 8 月 16 日。移除 10 月 10 日未入库草稿等不适合作成果的链接。 |
| “沪市工作→深市回放”仅因同日并行被当成承接 | 改为早期订单簿快照→后续深市回放核验；版式→标签、标签→模型报告等仅按交付顺序相连的边注明推断及限制。 |
| 整条链的后续去向被自动复制到所有早期日期 | 普通已记录和并入后续工作的说明只显示在链条卡，不再伪装成当天结果；局部未采用说明继续逐点保存。 |
| 每日详细说明被短注解覆盖 | 当天工作显示已核对的完整说明，“各项记录”另列每条链的短注解与局部去留；两者都可读到。 |

## 日期与状态的读法

- “记录日”表示有采集记录；首条至末条是记录跨度，不表示期间每天都投入相同工时。
- 实心点只表示有关联汇报；不再据此认定点上每项工作都在同一篇汇报中详述。提交数是当天各采集仓库合计。
- 实心方块表示此段记录结束，不等于任务永久完成。链条卡展示具体状态说明，不把所有默认值写成“已采用”。
- 计划、代码、启动、运行完成、验收和发布分开表达。报告归档日、真实工作日及首次发布日保持各自含义。
- 正式内容有五个局部未采用点，其他试验回退不自动升级成研究方向废弃。

## 88 个日期的逐日索引

下列提交链接是便于人工定位的代表根据，不替代该日完整的证据计数、计划和报告。每一天的完整改写保存在对应日志源文件中。

| 日期 | 改写后摘要 | 各项记录 | 代表原始提交 |
|---|---|---|---|
| [2026-06-23](../../content/journal/2026-06-23.md) | 配置米筐环境，跑出首份回测报告，整理沪深交易规则 | onboarding：配置米筐并运行示例策略 | [Quant_Research-Trading 79dbf994](https://github.com/MengerWen/Quant_Research-Trading/commit/79dbf994a6f66f0c612e7cac2e4b9bc2a1de69f6) |
| [2026-06-24](../../content/journal/2026-06-24.md) | 补充上交所交易规则和异常交易监控资料 | onboarding：补充交易规则与异常交易监控资料 | [Quant_Research-Trading b852739a](https://github.com/MengerWen/Quant_Research-Trading/commit/b852739ab5018ad30df1972dbbd5f7f96d9f613c) |
| [2026-06-25](../../content/journal/2026-06-25.md) | 用逐笔数据重建 100ms 盘口，修正与 3 秒行情的对照 | lv2-snapshot：实现百毫秒盘口并修正三秒对照 | [Quant_Research-Trading 4780c03a](https://github.com/MengerWen/Quant_Research-Trading/commit/4780c03af03bf9abedbe4c81ce32af5bb234f623) |
| [2026-06-26](../../content/journal/2026-06-26.md) | 完成沪深样本的快照对照，补充全天图表 | lv2-snapshot：核对沪深样本快照并补充图表 | [Quant_Research-Trading 9ddd8bc6](https://github.com/MengerWen/Quant_Research-Trading/commit/9ddd8bc6d23737ac5c567be7ebbc8708578e7317) |
| [2026-06-29](../../content/journal/2026-06-29.md) | 整理订单流失衡与价格冲击的参考论文 | literature：整理订单流失衡与冲击论文 | [Quant_Research-Trading 3ede8ad0](https://github.com/MengerWen/Quant_Research-Trading/commit/3ede8ad0afa58f2723b3d0a1f437a277b5b8e7b3) |
| [2026-06-30](../../content/journal/2026-06-30.md) | 搭建因子评价框架，运行首个订单流失衡因子 | lv2-snapshot：整理快照数据说明供因子研究使用；literature：搭建因子框架并运行首个因子 | [Quant_Research-Trading aa08efcf](https://github.com/MengerWen/Quant_Research-Trading/commit/aa08efcf40a893c537c8dcaa06412eec4ebf4301)；[Quant_Research-Trading 7024e3a9](https://github.com/MengerWen/Quant_Research-Trading/commit/7024e3a9f29a9193d809b925cf5cee6f4899d6a6) |
| [2026-07-01](../../content/journal/2026-07-01.md) | 转向算法交易痕迹研究，制定三篇论文的复现计划 | literature：制定三篇算法交易论文的复现计划 | [Quant_Research-Trading 59f75b29](https://github.com/MengerWen/Quant_Research-Trading/commit/59f75b29e4e20c7f719c6fdb692857ba6acb5f61) |
| [2026-07-03](../../content/journal/2026-07-03.md) | 扩展低延迟交易复现，修正 ClusterLOB 实现 | literature：扩展低延迟复现并修正订单簿聚类 | [Quant_Research-Trading fc642074](https://github.com/MengerWen/Quant_Research-Trading/commit/fc642074e109cf5cc278c764ed7671ff5131884b) |
| [2026-07-06](../../content/journal/2026-07-06.md) | 把六篇论文中的指标实现到 algobench | algobench：实现六篇论文中的算法痕迹指标 | [Quant_Research-Trading 14d25bf0](https://github.com/MengerWen/Quant_Research-Trading/commit/14d25bf0359553474596787ddfc553cba2106db7) |
| [2026-07-07](../../content/journal/2026-07-07.md) | 检查指标之间的相关性，建立研究成果看板 | algobench：补充指标相关性分析；dashboard-build：建立看板并加入研究材料 | [Quant_Research-Trading 73a83e47](https://github.com/MengerWen/Quant_Research-Trading/commit/73a83e47e57eccf1f9052050ab46affbdd20b863)；[internship-dashboard 1b792246](https://github.com/MengerWen/internship-dashboard/commit/1b792246376fa7a0cdd20025642d3be0c9a85544) |
| [2026-07-08](../../content/journal/2026-07-08.md) | 调整 SRuns 的参数与解释，补充快照图和展示页 | lv2-snapshot：补充百毫秒与三秒快照示意；algobench：调整重复撤挂单指标的参数与解释；dashboard-build：发布重复撤挂单指标展示页 | [Quant_Research-Trading 74bc62e6](https://github.com/MengerWen/Quant_Research-Trading/commit/74bc62e6e91e67d185b53ecf81927ac714dfa3b8)；[internship-dashboard e6b80f52](https://github.com/MengerWen/internship-dashboard/commit/e6b80f52c3b33ffb61be34915eb8d03ad4f024a8) |
| [2026-07-09](../../content/journal/2026-07-09.md) | 建立算法痕迹指标的评价流程，发布阶段报告 | algobench：增加相关性、事件和时间分布检验；dashboard-build：发布算法痕迹指标评价报告 | [Quant_Research-Trading 6f38cb7f](https://github.com/MengerWen/Quant_Research-Trading/commit/6f38cb7f9b8dc2300c2441750649e97b1d104bc6)；[internship-dashboard 3da1015e](https://github.com/MengerWen/internship-dashboard/commit/3da1015e2b4eef06685d31555dd619ef9594aa8a) |
| [2026-07-10](../../content/journal/2026-07-10.md) | 放弃旧研究方向，重写关注度因子计划并修正时间口径 | algobench：放弃旧方向并重写关注度因子计划；dashboard-build：修订前一天的评价报告 | [Quant_Research-Trading b5a03099](https://github.com/MengerWen/Quant_Research-Trading/commit/b5a0309931815295bd220545c9eb768cf2e78da5)；[Quant_Research-Trading 41c0f59b](https://github.com/MengerWen/Quant_Research-Trading/commit/41c0f59b5dc83a1b702a12de19c1287902159cbc) |
| [2026-07-11](../../content/journal/2026-07-11.md) | 实现可断点续算的关注度面板和按当时信息构建的股票池 | algobench：实现关注度面板、股票池与断点续算 | [Quant_Research-Trading 7ed013e9](https://github.com/MengerWen/Quant_Research-Trading/commit/7ed013e965f9a65651615aeec149a4fd9b5e638d) |
| [2026-07-12](../../content/journal/2026-07-12.md) | 把关注度研究限定到 2025 年 7 月，加入逐日并行计算 | algobench：限定单月样本并加入逐日并行 | [Quant_Research-Trading fe59a4c1](https://github.com/MengerWen/Quant_Research-Trading/commit/fe59a4c1e15cf8c49fce419f59d5f1337d2916ec) |
| [2026-07-13](../../content/journal/2026-07-13.md) | 发布关注度因子的阶段评价，补充图示和日报时间 | algobench：评价关注度因子的阶段结果；dashboard-build：补充图示并修正日报时间 | [Quant_Research-Trading b4f41375](https://github.com/MengerWen/Quant_Research-Trading/commit/b4f413755c07c9e482e24b96330197045f125567)；[internship-dashboard b92a19bd](https://github.com/MengerWen/internship-dashboard/commit/b92a19bd69f60382e890320978823990f25a04b0) |
| [2026-07-14](../../content/journal/2026-07-14.md) | 建立独立研究仓库，整理服务器所需的代码结构 | algobench：建立独立研究仓并连接父仓库 | [sirui-quant-research f451f232](https://github.com/MengerWen/sirui-quant-research/commit/f451f232c1d2b59b167b27bd13db14e38efbaacf)；[Quant_Research-Trading 811b25fa](https://github.com/MengerWen/Quant_Research-Trading/commit/811b25fa9a84da1cec6f1e64969587a672fbeb33) |
| [2026-07-15](../../content/journal/2026-07-15.md) | 制定服务器取数和正式因子计算方案 | doris-migration：编写后来被替换的数据库分批方案；formal-engine：编写正式因子计算方案 | [sirui-quant-research b87bd575](https://github.com/MengerWen/sirui-quant-research/commit/b87bd575bf7e96500f0dbfcdf3de346f010f19f6) |
| [2026-07-16](../../content/journal/2026-07-16.md) | 搭建正式因子计算流程，加入订单配对和行为评分 | formal-engine：实现订单生命周期、配对与行为评分 | [sirui-quant-research a214f26e](https://github.com/MengerWen/sirui-quant-research/commit/a214f26e0756739d7aedfe9b0eb909f2c3203ef3) |
| [2026-07-17](../../content/journal/2026-07-17.md) | 联调正式计算流程，修复内存保护和运行检查 | formal-engine：联调计算流程并修复内存保护 | [sirui-quant-research 6315b9cf](https://github.com/MengerWen/sirui-quant-research/commit/6315b9cf379b403bf6d112ab4e5f79508eafb1a2) |
| [2026-07-18](../../content/journal/2026-07-18.md) | 修复正式面板生成步骤，完善逐日股票池方案 | formal-engine：修复面板生成并完善逐日股票池 | [sirui-quant-research 78011228](https://github.com/MengerWen/sirui-quant-research/commit/7801122890d930f44db3878c7444add62c1e0da7) |
| [2026-07-19](../../content/journal/2026-07-19.md) | 排查正式计算的内存故障，测试单日耗时 | formal-engine：排查内存故障并测试单日耗时 | [sirui-quant-research bbb91259](https://github.com/MengerWen/sirui-quant-research/commit/bbb91259eed08256d01ee4574fd161869f61fcfe) |
| [2026-07-20](../../content/journal/2026-07-20.md) | 减少订单配对的重复计算，复用中间结果 | formal-engine：复用中间结果并改进订单配对计算 | [sirui-quant-research 0f96bd77](https://github.com/MengerWen/sirui-quant-research/commit/0f96bd77649760e0342e39482f830a0b57d08179)；[Quant_Research-Trading e52e7a9e](https://github.com/MengerWen/Quant_Research-Trading/commit/e52e7a9e03bd34a4fdd176fdc8ad0f18203183c3) |
| [2026-07-21](../../content/journal/2026-07-21.md) | 减少候选订单关系落盘，边计算边汇总结果 | formal-engine：减少候选关系落盘并逐日释放内存 | [sirui-quant-research 8cc57d9a](https://github.com/MengerWen/sirui-quant-research/commit/8cc57d9a56862cd947c0c9162da39a793ddcd609) |
| [2026-07-22](../../content/journal/2026-07-22.md) | 让隔日与日内因子共用取数，整理多日计算计划 | formal-engine：共用取数并支持两种收益评价窗口 | [sirui-quant-research 14387391](https://github.com/MengerWen/sirui-quant-research/commit/143873910e547677e11f81eabd158641e04c819f)；[Quant_Research-Trading ca653fcf](https://github.com/MengerWen/Quant_Research-Trading/commit/ca653fcf3cfa19b760060255e2d1bb3bd13eedc5)；[internship-dashboard 0aafa418](https://github.com/MengerWen/internship-dashboard/commit/0aafa4189b4a9ed5e996a64a76e423714d8efdfe) |
| [2026-07-23](../../content/journal/2026-07-23.md) | 修复参数和历史基准的传递，继续日内研究并发布因子说明 | formal-engine：修复参数传递并继续日内研究；report-publish：发布因子构造说明并修正公式 | [sirui-quant-research 6142b5b5](https://github.com/MengerWen/sirui-quant-research/commit/6142b5b5b53585b0f7a88be96b14cee91fa1b0b2)；[internship-dashboard 11d42ebe](https://github.com/MengerWen/internship-dashboard/commit/11d42ebed84aa734e189b30d63c782f7cb816f1b) |
| [2026-07-24](../../content/journal/2026-07-24.md) | 优化行为评分和冲击响应计算，加入单日验收入口 | formal-engine：优化行为评分与冲击响应计算 | [sirui-quant-research bc465c5b](https://github.com/MengerWen/sirui-quant-research/commit/bc465c5b7c06f4d221374f150d771e291b31ec6a)；[Quant_Research-Trading df409d9e](https://github.com/MengerWen/Quant_Research-Trading/commit/df409d9e22d9d3ef8f264507893a2f3b33520be6) |
| [2026-07-25](../../content/journal/2026-07-25.md) | 修正缺少有效观测时的股票判定和空结果报告 | formal-engine：修正不可观测股票与空结果的处理 | [sirui-quant-research f8c79c61](https://github.com/MengerWen/sirui-quant-research/commit/f8c79c61f754b9daed64c18b41ad799097118a35) |
| [2026-07-27](../../content/journal/2026-07-27.md) | 重构开盘前三分钟的行为评分，检查单日计算可行性 | gates：重构开盘三分钟评分并检查可行性 | [sirui-quant-research ccbe0b90](https://github.com/MengerWen/sirui-quant-research/commit/ccbe0b90827d79b61a2bdf2d3cd6010b672a0bf7) |
| [2026-07-28](../../content/journal/2026-07-28.md) | 按真实报价最小变动单位重新定标，减少重复评分 | gates：按真实报价单位定标并减少重复计算 | [sirui-quant-research ca9c872f](https://github.com/MengerWen/sirui-quant-research/commit/ca9c872f4e209edbe86d891249773a001a7ddea1) |
| [2026-07-29](../../content/journal/2026-07-29.md) | 取消价格硬筛选，保留 10% 数量门并修复计算验收 | gates：取消价格硬筛选，保留数量筛选 | [sirui-quant-research 3d8c981b](https://github.com/MengerWen/sirui-quant-research/commit/3d8c981b45cc21f75a27aa92f10b97676646e209) |
| [2026-07-30](../../content/journal/2026-07-30.md) | 恢复 Doris 取数后的计算，扩展因子评价日期范围 | doris-migration：数据库恢复后修复断点续算；gates：扩展固定数量门下的评价日期 | [sirui-quant-research 8d1f156b](https://github.com/MengerWen/sirui-quant-research/commit/8d1f156be817d917dd54e4dfef719a55a755fb45)；[internship-dashboard eed31e29](https://github.com/MengerWen/internship-dashboard/commit/eed31e290d997ccd947027d4b02d4c2d5c4904ae) |
| [2026-07-31](../../content/journal/2026-07-31.md) | 修复扩展区间的续算与历史基准，发布因子报告 | gates：修复长区间续算与历史基准限制；report-publish：发布因子定义、指标与评价图 | [sirui-quant-research 9fa7ed90](https://github.com/MengerWen/sirui-quant-research/commit/9fa7ed90269486db8939209aceb19c846ae168f3)；[internship-dashboard 34928c6f](https://github.com/MengerWen/internship-dashboard/commit/34928c6fc93f23a2045ce934e4f29e39c5d1dff7) |
| [2026-08-02](../../content/journal/2026-08-02.md) | 支持固定参数的历史评价，发布更长区间的结果 | gates：支持固定参数的历史区间评价；report-publish：发布扩展历史区间的评价结果 | [sirui-quant-research 92cf826c](https://github.com/MengerWen/sirui-quant-research/commit/92cf826cc5a1f630943dc33434d19548f6bfd3dc)；[internship-dashboard 356f0f76](https://github.com/MengerWen/internship-dashboard/commit/356f0f7631d653a64c8a4a2e1e268c1fdc71f456) |
| [2026-08-03](../../content/journal/2026-08-03.md) | 复用已完成日期，补算更早的历史区间 | fixed-history：复用已完成结果并补算更早日期；report-publish：发布固定参数历史评价报告 | [sirui-quant-research 405cfc8c](https://github.com/MengerWen/sirui-quant-research/commit/405cfc8c08a96b544e43badf3b5aec1ea1237bf3)；[internship-dashboard cb9e929f](https://github.com/MengerWen/internship-dashboard/commit/cb9e929f06a2370c3d08ec01b23afc2d1898fc3b) |
| [2026-08-04](../../content/journal/2026-08-04.md) | 加固历史结果的恢复检查，制定总量因子的模型研究计划 | fixed-history：核对恢复来源和收益标签兼容性；ml-count：制定总量因子的模型与结构诊断计划 | [sirui-quant-research 6a9a06c5](https://github.com/MengerWen/sirui-quant-research/commit/6a9a06c58bba1a814358bf2ca518fb34c2acc2f3) |
| [2026-08-05](../../content/journal/2026-08-05.md) | 发布长历史报告，解释因子分母和构造公式 | fixed-history：解释全委托分母与历史因子公式；report-publish：发布长历史结果并修订因子解释 | [internship-dashboard fa6c6604](https://github.com/MengerWen/internship-dashboard/commit/fa6c660461cb57b930d6ae4743ea8adbbd9f99d4) |
| [2026-08-06](../../content/journal/2026-08-06.md) | 加快开盘五分钟因子的计算，制定模型计划，加入标题折叠 | open5m：加快事件读取、回放与因子计算；ml-count：制定原始因子的模型计算计划；report-publish：给研究文档加入标题折叠 | [sirui-quant-research b598fe57](https://github.com/MengerWen/sirui-quant-research/commit/b598fe57b7f34763240a727cd3d41d9bad881b4b)；[internship-dashboard 7a138f8e](https://github.com/MengerWen/internship-dashboard/commit/7a138f8e059847e32cd5c13d7a94c89152cd348f) |
| [2026-08-07](../../content/journal/2026-08-07.md) | 继续优化逐笔读取和响应计算，回退部分未保留的尝试 | open5m：调整逐笔读取顺序与响应计算 | [sirui-quant-research e27b7b1d](https://github.com/MengerWen/sirui-quant-research/commit/e27b7b1d5dc168ed6bfcbcddf31dc79a78895022) |
| [2026-08-08](../../content/journal/2026-08-08.md) | 减少历史预检的重复扫描，启动带核验的历史计算 | open5m：减少历史预检的重复扫描 | [sirui-quant-research f80a4433](https://github.com/MengerWen/sirui-quant-research/commit/f80a443367582948dfffdcf4e05d1311ddd8d1ed) |
| [2026-08-09](../../content/journal/2026-08-09.md) | 加入历史计算续跑入口，补充报价例外和提速说明 | open5m：加入带资源保护的断点续算入口；report-publish：整理开盘因子计算提速说明 | [sirui-quant-research f2bd015f](https://github.com/MengerWen/sirui-quant-research/commit/f2bd015f7b72fb6162d4c113b6163c25827061f2)；[internship-dashboard 9471617b](https://github.com/MengerWen/internship-dashboard/commit/9471617ba9a1d91f5d8dd7aa461d1c35c3533693) |
| [2026-08-10](../../content/journal/2026-08-10.md) | 发布开盘五分钟因子报告，补充对照分析和图表放大 | open5m：增加开盘三分钟因子的对照分析；report-publish：发布因子报告并支持图表放大 | [sirui-quant-research 2318d2ff](https://github.com/MengerWen/sirui-quant-research/commit/2318d2ff29815213e6f108cb3308629dfa601869)；[Quant_Research-Trading 5af712a0](https://github.com/MengerWen/Quant_Research-Trading/commit/5af712a0fdf48c3bddbd077cc98f29e1d89028dd)；[internship-dashboard b15e2d0c](https://github.com/MengerWen/internship-dashboard/commit/b15e2d0ce95fa828dd114cf6772964d8d57b583c) |
| [2026-08-11](../../content/journal/2026-08-11.md) | 实现模型研究流程，应用看板的研究编辑台版式 | ml-exec：实现固定配置下的模型研究流程；visual-b：应用研究编辑台版式和窄屏样式 | [sirui-quant-research 97892497](https://github.com/MengerWen/sirui-quant-research/commit/9789249742b8bf8fc16b1cefe6951eac7a7ea0e0)；[internship-dashboard c9ecdcf2](https://github.com/MengerWen/internship-dashboard/commit/c9ecdcf23e06b2092eb9837e391c6e6b85794f49) |
| [2026-08-12](../../content/journal/2026-08-12.md) | 排查模型停止失败，加入 CPU 和 GPU 任务调度 | ml-exec：修复停止失败并加入资源调度 | [sirui-quant-research 754ae82e](https://github.com/MengerWen/sirui-quant-research/commit/754ae82e271c84c749138b37f57be9ea43686853) |
| [2026-08-13](../../content/journal/2026-08-13.md) | 让线性、树模型和 GPU 模型接入同一执行流程 | ml-exec：统一线性、树模型和GPU模型的执行 | [sirui-quant-research 45d9a965](https://github.com/MengerWen/sirui-quant-research/commit/45d9a965a2e235c540b41ec0280a6e4cc77c85a3) |
| [2026-08-14](../../content/journal/2026-08-14.md) | 修复混合调度试跑和 AdaBoost 检查点问题 | ml-exec：修复调度试跑和模型检查点隔离 | [sirui-quant-research cceea87f](https://github.com/MengerWen/sirui-quant-research/commit/cceea87fe0517c6078ddd7d92461d5634df6f4b7) |
| [2026-08-15](../../content/journal/2026-08-15.md) | 调整模型资源限制，补充随机森林的两阶段筛选 | ml-exec：调整资源规则并补充随机森林筛选 | [sirui-quant-research b68effb0](https://github.com/MengerWen/sirui-quant-research/commit/b68effb0486b04f7ce26e4bd106be9edd7fbc610) |
| [2026-08-16](../../content/journal/2026-08-16.md) | 固定不含随机森林的研究范围，核对试跑清单 | ml-exec：固定不含随机森林的模型范围 | [sirui-quant-research acb95ca5](https://github.com/MengerWen/sirui-quant-research/commit/acb95ca5d27383b67e341db8f1720abb15c79b73) |
| [2026-08-17](../../content/journal/2026-08-17.md) | 修正模型运行时间估计和调度准入条件 | ml-exec：按实际最长耗时判断模型能否运行 | [sirui-quant-research 75651200](https://github.com/MengerWen/sirui-quant-research/commit/75651200d7459d24ed83568e960e05b1ebe2ef6a) |
| [2026-08-18](../../content/journal/2026-08-18.md) | 并行执行模型归因，删除重复拟合，修正验证样本身份 | ml-exec：并行归因、减少重复拟合并核对样本 | [sirui-quant-research 9c2ff690](https://github.com/MengerWen/sirui-quant-research/commit/9c2ff690cdad588032bb51a1d1109871675c1f41) |
| [2026-08-19](../../content/journal/2026-08-19.md) | 继续不含随机森林的模型评价，开始研究撤单等待时间 | ml-exec：修复固定模型评价与恢复流程；cancel-phase：制定撤单等待时间分布研究方案 | [sirui-quant-research 0117ae9a](https://github.com/MengerWen/sirui-quant-research/commit/0117ae9a0c5ea4d8b04df2b12aa17b5d53c67353) |
| [2026-08-20](../../content/journal/2026-08-20.md) | 完成半年撤单延迟分析，发布撤单报告和各类模型结果 | ml-exec：增加全模型启动入口和只读预测保护；cancel-phase：分析上半年116日的撤单等待时间；report-publish：发布模型结果与撤单延迟报告 | [sirui-quant-research 051f0a35](https://github.com/MengerWen/sirui-quant-research/commit/051f0a35f85c5006b80e796bcd34d12ae1320b7b)；[Quant_Research-Trading b77d944a](https://github.com/MengerWen/Quant_Research-Trading/commit/b77d944ab8722cf5a530341f15a08441651bdf79)；[internship-dashboard b079822a](https://github.com/MengerWen/internship-dashboard/commit/b079822ac4ffabf9c29aa295b618e190f64e41be) |
| [2026-08-24](../../content/journal/2026-08-24.md) | 把深市撤单延迟分析扩到 601 日，压缩图表数据 | cancel-phase：扩展深市601日撤单等待时间分析；report-publish：发布历史撤单分布并压缩图表 | [sirui-quant-research 3870054b](https://github.com/MengerWen/sirui-quant-research/commit/3870054bd1a41b324c3539154faa23ea6deafcd3)；[Quant_Research-Trading 1bea211b](https://github.com/MengerWen/Quant_Research-Trading/commit/1bea211b04210f3871691b9a372a2887217c031e)；[internship-dashboard 1f221610](https://github.com/MengerWen/internship-dashboard/commit/1f2216100c2b39f6a441b0800cd8743f93ff125a) |
| [2026-08-27](../../content/journal/2026-08-27.md) | 重做连续评分尺度的定标，优化事件回放和中间存储 | open5m：重定标连续评分尺度并优化回放 | [sirui-quant-research fb7c1ab2](https://github.com/MengerWen/sirui-quant-research/commit/fb7c1ab2442ee55da158d2d27b1b750695c7ed21) |
| [2026-08-28](../../content/journal/2026-08-28.md) | 加快历史定标，核对因子在不同时期的表现反转 | open5m：加快历史定标并检查分时期表现 | [sirui-quant-research 564718a4](https://github.com/MengerWen/sirui-quant-research/commit/564718a4b12838d1e65b2d1c5da773eec6ca59de) |
| [2026-08-29](../../content/journal/2026-08-29.md) | 检查高度相关因子的新增信息，复核方向与定义 | open5m：检查相关因子的增量信息和方向 | [sirui-quant-research c4844da4](https://github.com/MengerWen/sirui-quant-research/commit/c4844da48fee2295caf371e033c9d8d23b7c05d8) |
| [2026-09-01](../../content/journal/2026-09-01.md) | 制定清洁算法痕迹指标方案，实现撤单相位因子 | open5m：制定清洁算法痕迹指标的分步方案；cancel-phase：实现撤单相位因子并共享统计 | [sirui-quant-research 3a1594cc](https://github.com/MengerWen/sirui-quant-research/commit/3a1594cc5b9c1a752e2e7d1013b0ca7065bd46dc)；[sirui-quant-research 741254cd](https://github.com/MengerWen/sirui-quant-research/commit/741254cdc80eb22919af9dac423e73459f35be83) |
| [2026-09-02](../../content/journal/2026-09-02.md) | 加快新行为机制的预查，加入真实数据定标 | open5m：加快行为预查并加入真实数据定标 | [sirui-quant-research 80ff87a6](https://github.com/MengerWen/sirui-quant-research/commit/80ff87a6eeeace03029c7827a6571b6901b3648b) |
| [2026-09-03](../../content/journal/2026-09-03.md) | 加快九组参数定标，支持按日期分片的行为预查 | open5m：定标改为流式汇总，不保存完整候选表 | [sirui-quant-research cd4e59f0](https://github.com/MengerWen/sirui-quant-research/commit/cd4e59f07f9900c11b5c778b82b50dba83ac5ac8)；[sirui-quant-research 194e93d4](https://github.com/MengerWen/sirui-quant-research/commit/194e93d49af114b48bdc8e340e608e3b179c5868) |
| [2026-09-04](../../content/journal/2026-09-04.md) | 配置 wangly 环境，分析订单股数分布和撤单相位 | wangly-env：配置计算环境并制定结果同步方案；open5m：统计开盘订单股数的真实分布；cancel-phase：准备并推进半年撤单相位评价；report-publish：更新行为预查报告与研究记录 | [sirui-quant-research ea60f4d5](https://github.com/MengerWen/sirui-quant-research/commit/ea60f4d53482d1a3cf2a4b6b7294bfdc1e8bc455)；[internship-dashboard a86755c0](https://github.com/MengerWen/internship-dashboard/commit/a86755c07bd656ce66696b2a41194f35049a6fab) |
| [2026-09-05](../../content/journal/2026-09-05.md) | 检查委托量与盘口深度的匹配，准备全历史相位评价 | depth-match：预查委托股数与盘口深度的匹配；cancel-phase：准备全历史撤单相位计算；report-publish：补充盘口匹配的预查发现 | [sirui-quant-research e4f11f94](https://github.com/MengerWen/sirui-quant-research/commit/e4f11f94037461d26be50554cebed2b7938f181c)；[internship-dashboard b9778f20](https://github.com/MengerWen/internship-dashboard/commit/b9778f20a2ce3c467fa07ccb037f4645c4c198cc) |
| [2026-09-06](../../content/journal/2026-09-06.md) | 完成 601 日撤单相位与收益标签评价，保留失败记录 | cancel-phase：完成601日撤单相位与标签评价 | [sirui-quant-research 9a60d105](https://github.com/MengerWen/sirui-quant-research/commit/9a60d105e494284570428b5cbb97ccf24b76fdce) |
| [2026-09-07](../../content/journal/2026-09-07.md) | 制定老因子重算方案，发布撤单相位报告和汇报标签 | old-factor-bank：制定老因子重算及300秒验收方案；report-tags：加入在线标签并发布撤单相位报告 | [sirui-quant-research f9fc062b](https://github.com/MengerWen/sirui-quant-research/commit/f9fc062b6878c605688a8ce3fdcd4cd5b680cb49)；[internship-dashboard c8a60da6](https://github.com/MengerWen/internship-dashboard/commit/c8a60da654b023db80117f331f7ded809a60da0c) |
| [2026-09-08](../../content/journal/2026-09-08.md) | 完成 601 日深度匹配评价，继续跨股票同步预查 | depth-match：完成深度匹配评价并研究跨股同步；report-publish：发布深度匹配结果并改进报告导航 | [sirui-quant-research 8d263af9](https://github.com/MengerWen/sirui-quant-research/commit/8d263af95dbe9b5331b10509a9922ac62ccd38cd)；[internship-dashboard 7c47a36c](https://github.com/MengerWen/internship-dashboard/commit/7c47a36c52d0a573deb1d802c00636932a0822d4) |
| [2026-09-09](../../content/journal/2026-09-09.md) | 补全撤单因子的买卖方向，优化跨股预查和报告浏览 | cancel-phase：补全相位买卖方向并预查机械撤单；depth-match：优化跨股票同步预查的统计计算；report-tags：加入买卖方向对照、筛选和排序 | [sirui-quant-research c1942169](https://github.com/MengerWen/sirui-quant-research/commit/c1942169979420855939f3bac76613d7a4c7ecf8)；[internship-dashboard 7fbff494](https://github.com/MengerWen/internship-dashboard/commit/7fbff494552b2abd13b104e2b1ec956be85d9a04) |
| [2026-09-10](../../content/journal/2026-09-10.md) | 核对老因子计算的一致性，验收机械撤单历史结果 | old-factor-bank：核对订单配对与响应评分的精确一致性；cancel-phase：核对机械撤单601日计算与独立验收；depth-match：调整跨股预查的暂存与统计复用 | [sirui-quant-research b9990a2a](https://github.com/MengerWen/sirui-quant-research/commit/b9990a2a2bb3baece535441ca123aee07d395a26)；[sirui-quant-research a8c1c7dd](https://github.com/MengerWen/sirui-quant-research/commit/a8c1c7dd8f108d4789cc701de924ed25fcaebfa4)；[sirui-quant-research aad38bdb](https://github.com/MengerWen/sirui-quant-research/commit/aad38bdbbb3bce1d774cdd13d9e5b103f7056f16) |
| [2026-09-11](../../content/journal/2026-09-11.md) | 整理老因子提速证据，发布机械撤单预查结果 | old-factor-bank：减少最优买卖价查找和F40索引开销；report-publish：发布机械撤单预查结果 | [sirui-quant-research d14a8331](https://github.com/MengerWen/sirui-quant-research/commit/d14a8331de162d0a6f02e5d90f15a3e4fd03161a)；[internship-dashboard 3f8b9c3b](https://github.com/MengerWen/internship-dashboard/commit/3f8b9c3be0082193ab8bfd1320590789a0fbd723) |
| [2026-09-12](../../content/journal/2026-09-12.md) | 清理老因子冗余文件，启动 601 日历史计算 | old-factor-bank：清理冗余文件并启动601日计算 | [sirui-quant-research dfba3c32](https://github.com/MengerWen/sirui-quant-research/commit/dfba3c32ae597fb1aca04614dad62cc4c463f88b) |
| [2026-09-17](../../content/journal/2026-09-17.md) | 发布 601 日老因子结果，补充筛选和诊断 | report-publish：发布601日老因子结果与筛选诊断 | [internship-dashboard 9c9e108f](https://github.com/MengerWen/internship-dashboard/commit/9c9e108fc9313b1e02fb78bccb4482848ea26bd9) |
| [2026-09-18](../../content/journal/2026-09-18.md) | 检查收益标签的极端值处理，补记跨股预查已停止 | open5m：检查收益标签的极端值与软压缩拐点；depth-match：补记跨股同步预查停止并清理材料；report-publish：发布601日收益标签诊断 | [sirui-quant-research 9e26b6ed](https://github.com/MengerWen/sirui-quant-research/commit/9e26b6ed8b131a9d387fe62078ef8aeae62b6076)；[sirui-quant-research 706cab7b](https://github.com/MengerWen/sirui-quant-research/commit/706cab7b60df55856a36444174f3bf166c75373c) |
| [2026-09-19](../../content/journal/2026-09-19.md) | 发布初版 LightGBM 结果和模型诊断图 | model-report：发布初版模型设置、结果与诊断图 | [internship-dashboard a4f5af84](https://github.com/MengerWen/internship-dashboard/commit/a4f5af84182616227fe6d21c86c7a29e00631b63) |
| [2026-09-20](../../content/journal/2026-09-20.md) | 建立 330 候选因子的模型选择流程，细化报告诊断 | ml-330：实现候选因子输入和自动模型选择；model-report：细化排序相关和多空收益诊断 | [sirui-quant-research 5ae111a6](https://github.com/MengerWen/sirui-quant-research/commit/5ae111a6ad241b4a2a87a2dbcd451d039104f2b4)；[internship-dashboard 8988c1ea](https://github.com/MengerWen/internship-dashboard/commit/8988c1eaf4176f47900adc9c8ff6769f1f1d4e9b) |
| [2026-09-21](../../content/journal/2026-09-21.md) | 按事先锁定选股名单的方式重算模型，发布修正结果 | ml-330：按因果时序重算并控制拟合内存；model-report：发布修正后的328因子模型结果 | [sirui-quant-research 0cedf22d](https://github.com/MengerWen/sirui-quant-research/commit/0cedf22d5d531d6ac3e88e87966d6afae1429c0b)；[internship-dashboard 83498922](https://github.com/MengerWen/internship-dashboard/commit/8349892245fd5eb076b76af7b7b29dd7304ada7a) |
| [2026-09-23](../../content/journal/2026-09-23.md) | 核对沪市委托还原方法及其可观测范围 | sse-v2：核对沪市委托还原与公司逐笔数据 | [sirui-quant-research fab4459c](https://github.com/MengerWen/sirui-quant-research/commit/fab4459c0ba108a8802380cca1cecdc5bc9e21f5) |
| [2026-10-07](../../content/journal/2026-10-07.md) | 明确分组定标的评价口径，统一代码提交与推送规则 | grouped-calibration：说明按什么分组以及怎样评价；report-publish：明确本地修改后逐项提交和推送 | [sirui-quant-research be040e3f](https://github.com/MengerWen/sirui-quant-research/commit/be040e3f0f554d6ecb474dadf4bc143a4c2a0e8d)；[Quant_Research-Trading ac4959cb](https://github.com/MengerWen/Quant_Research-Trading/commit/ac4959cbaaf63644d811a438f53013154676919d)；[internship-dashboard d720d487](https://github.com/MengerWen/internship-dashboard/commit/d720d487a9eb3b2a25600f675d42ea3caea2450c) |
| [2026-10-08](../../content/journal/2026-10-08.md) | 检查分组定标档数，分析沪市委托中的不可见信息 | grouped-calibration：检查分组档数及运行前条件；sse-v2：分析沪市残余委托并输出统一格式 | [sirui-quant-research a562d49a](https://github.com/MengerWen/sirui-quant-research/commit/a562d49aeb2df255e193274ab29e4f5040c743bb)；[Quant_Research-Trading 23a138db](https://github.com/MengerWen/Quant_Research-Trading/commit/23a138dbb045a320a03ceadf2fd8137e88684ba2) |
| [2026-10-09](../../content/journal/2026-10-09.md) | 封存六类核尺度参数，发布预检报告并核对沪市适配 | doris-efficiency：制定数据库取数的通用效率方案；grouped-calibration：生成六类尺度参数并保存验收结果；sse-v2：核对沪市适配和通道消息距离；report-publish：发布601日分组定标预检报告 | [sirui-quant-research 7a8735d4](https://github.com/MengerWen/sirui-quant-research/commit/7a8735d484e54ece3dcfed8a74a892d5d3de50fa)；[sirui-quant-research 8351566d](https://github.com/MengerWen/sirui-quant-research/commit/8351566d2a9093d00b50fd5c81375246e5328072)；[internship-dashboard c6efd439](https://github.com/MengerWen/internship-dashboard/commit/c6efd4396be7a80afb8d3eb3d314fc812671dca7) |
| [2026-10-10](../../content/journal/2026-10-10.md) | 推进结构参数计算，诊断沪市开盘数据缺口并发布参数报告 | szse-model328：准备模型输入因子的结构参数；grouped-calibration：记录结构参数采集与定标进度；sse-v2：诊断开盘缺口并试验消息排序；report-publish：发布六类尺度参数的阶段报告 | [sirui-quant-research 15363777](https://github.com/MengerWen/sirui-quant-research/commit/153637774d567018e93fe6a1703bd4e7cdd650b5)；[internship-dashboard 3744cff5](https://github.com/MengerWen/internship-dashboard/commit/3744cff5e3b3a7a585b28dbdaee23256a052f3d3) |
| [2026-10-11](../../content/journal/2026-10-11.md) | 继续 F40 结构定参，确认沪市正式时钟及覆盖限制 | grouped-calibration：优化F40定参并记录已完成日期；sse-v2：确认正式时钟并核对数据覆盖缺口 | [sirui-quant-research fce3ac88](https://github.com/MengerWen/sirui-quant-research/commit/fce3ac88adf4beafe9c8ffeedd7aa472ca69d680)；[sirui-quant-research 6f2b0d49](https://github.com/MengerWen/sirui-quant-research/commit/6f2b0d49b4f268794c9cf8eb632389f9996395ce) |
| [2026-10-12](../../content/journal/2026-10-12.md) | 启动深市 328 列全期计算，进行压力日验证 | szse-model328：启动328列历史生产并测试压力日 | [sirui-quant-research 69a1f8cc](https://github.com/MengerWen/sirui-quant-research/commit/69a1f8ccd84d5a18e2a85e2b32d84f8de25ea35b) |
| [2026-10-13](../../content/journal/2026-10-13.md) | 核对沪市订单号，恢复深市 328 列计算并验收五个压力日 | sse-v2：核对订单号并增加有界取数与缓存；szse-model328：验收五个压力日并在数据库恢复后续算 | [sirui-quant-research d119b3a3](https://github.com/MengerWen/sirui-quant-research/commit/d119b3a36e0a1d711b9d2cef98b7ddd564881294)；[sirui-quant-research 910bb8c2](https://github.com/MengerWen/sirui-quant-research/commit/910bb8c2a6e6397b2c4534f208bbe8de4a53b027)；[sirui-quant-research 2d124da7](https://github.com/MengerWen/sirui-quant-research/commit/2d124da73dfe9d3116b28821301089c75fa1c019) |
| [2026-10-14](../../content/journal/2026-10-14.md) | 加快沪市委托与深市因子计算，清理重复缓存并发布报告 | storage-cleanup：核验归档后清理重复热缓存；szse-model328：减少深市因子计算与发布开销；sse-v2：减少沪市委托重建和评分的重复计算；report-publish：发布沪市委托提速与缓存清理报告 | [sirui-quant-research 197323ff](https://github.com/MengerWen/sirui-quant-research/commit/197323ff5807553c041e42e9217f5092b33c7347)；[internship-dashboard 78ac2e09](https://github.com/MengerWen/internship-dashboard/commit/78ac2e094c5f2069590a0671602ee986b7d66597) |
| [2026-10-15](../../content/journal/2026-10-15.md) | 检查沪市因子输入资格，清理到期文件，停止稳定性后续研究 | storage-cleanup：盘点副本并按保留期限清理；sse-v2：逐列检查沪市因子的可计算条件；cancel-phase：停止机械撤单稳定性分析的后续生成 | [sirui-quant-research 2497d417](https://github.com/MengerWen/sirui-quant-research/commit/2497d417ee7a8f03d52ba6ccc1c4895c2fb46594)；[sirui-quant-research 4b509357](https://github.com/MengerWen/sirui-quant-research/commit/4b5093577df4b23b59d5b5c8539385c7878d4fc4) |
| [2026-10-16](../../content/journal/2026-10-16.md) | 续算深市 328 列，检查沪市可见口径，完成存储清理与报告 | storage-cleanup：清理失败暂存并补齐历史清理凭证；szse-model328：按已验收配置继续剩余日期计算；sse-v2：检查可见输入与三值判定，记录未过验收项；report-publish：发布深市328列提速与存储复盘 | [sirui-quant-research d0f99bc3](https://github.com/MengerWen/sirui-quant-research/commit/d0f99bc3b03d18f5a15ad5870a00313fffd8bd78)；[sirui-quant-research cacfada9](https://github.com/MengerWen/sirui-quant-research/commit/cacfada9c02bbbf3e3c00def1ab70b0430165188)；[internship-dashboard 89ed3481](https://github.com/MengerWen/internship-dashboard/commit/89ed348113b718caeb24147c5eb4ca95e45d9685) |
| [2026-10-17](../../content/journal/2026-10-17.md) | 检查深市回放与快照差异，交付沪市 G1 缺失与定义核对 | replay：诊断快照偏移并核验回放对因子的影响；sse-v2：核对G1缺失、定义差与恢复比例 | [sirui-quant-research 6c8bdd9f](https://github.com/MengerWen/sirui-quant-research/commit/6c8bdd9f796538ec8aaacff4159b1c50df95b0c9) |
| [2026-10-18](../../content/journal/2026-10-18.md) | 完成深市 328 列封存与收益评价，核验三日回放并发布报告 | replay：复核三日生产回放及输入与存储证据；szse-model328：封存601日结果并完成单因子评价；report328：发布328列因子的601日评价报告 | [sirui-quant-research 10bca944](https://github.com/MengerWen/sirui-quant-research/commit/10bca94476938371ca69e575b6f9e90f9f09490d)；[sirui-quant-research 6c39985f](https://github.com/MengerWen/sirui-quant-research/commit/6c39985f12e8ebd51de7799c5c4a6527ae7d9a09)；[internship-dashboard 1a0fefd8](https://github.com/MengerWen/internship-dashboard/commit/1a0fefd809d4dad0410cc02640fc5f086a94f209) |
| [2026-10-19](../../content/journal/2026-10-19.md) | 审计回放和成交价格的正确性，拆开数据准备与因子计算阶段 | replay：审计成交价格并拆分回放与因子执行 | [sirui-quant-research 1dc329b3](https://github.com/MengerWen/sirui-quant-research/commit/1dc329b35bfc7604cbbbf98b4fbf27f2b0162bde)；[Quant_Research-Trading 3650f66a](https://github.com/MengerWen/Quant_Research-Trading/commit/3650f66a67efe2d46f83fb44a6f4ff9ee480bfb8) |
| [2026-10-20](../../content/journal/2026-10-20.md) | 核对全量重算条件，验证回放整改并建设研究日志 | replay：验证回放整改并核对全量重算条件；report-publish：设计、实现并验收研究日志栏目 | [sirui-quant-research e488eaa6](https://github.com/MengerWen/sirui-quant-research/commit/e488eaa6a3fe547c871ea396cfeef7761e6d8883)；[internship-dashboard a9722242](https://github.com/MengerWen/internship-dashboard/commit/a97222421b3dc38eaaef8c6c05b7497ac2791716)；[internship-dashboard 9b8437bf](https://github.com/MengerWen/internship-dashboard/commit/9b8437bf2985a76ac97f3074e4a8109da9ba2308) |

## 28 条任务链的说明

| 任务 | 要解决的问题 | 结果与限制 |
|---|---|---|
| 上手：米筐环境与交易规则 | 配置米筐行情和回测环境，运行示例策略，整理沪深交易及异常交易监控规则，作为后续研究的基础。 | 米筐示例已运行，规则资料已入库。这里记录上手工作，不评价策略收益。 |
| Doris 取数与服务器迁移 | 把研究取数接到服务器上的 Doris 数据库，处理批量读取、内存限制和故障后的断点续算。 | 7 月 15 日的固定分批方案后来被替换；7 月 30 日继续处理数据库恢复后的续算。两者不能都称为最终采用方案。 |
| wangly 计算环境与结果同步方案 | 配置 wangly 的研究依赖和数据访问检查，编写向 wenjie 同步结果的方案。 | 有环境配置代码和结果同步计划；不能据此认定每份结果都已传回 wenjie。 |
| Doris 取数效率方案 | 整理数据库取数中可减少重复查询、传输和解析开销的做法，供后续任务使用。 | 这段记录主要是一份通用效率计划，不代表所有查询都已改完或获得同一提速幅度。 |
| 存储盘点、归档与重复文件清理 | 区分正式结果、可恢复副本、运行暂存和到期材料，核对归档与恢复证据后清理重复文件，并保留实际回收量。 | 已记录多次限定范围的清理及回读核验；没有把清理规则解释为任意删除其他任务文件的授权。 |
| 逐笔数据重建 100ms 盘口快照 | 按委托、成交和撤单的事件顺序重建订单簿，生成 100ms 与 3 秒快照，用米筐 3 秒行情核对样本，并为后续因子研究整理数据说明。 | 早期样本对照与图示已完成。后续回放审计另列一条链，早期样本一致不等于全部历史都已验证。 |
| 深市订单簿回放与正确性检查 | 重新检查深市撮合规则、成交价格、事件前后盘口和快照时间，核对它们如何影响正式因子，并整理可复用的生产入口。 | 截至记录版本，已有单日、三日和真实因子小样本核验；全量重算的前置条件仍单独检查，不能据此称全历史修正已经完成。 |
| 论文复现与首个因子评价框架 | 整理订单流失衡、低延迟交易和订单簿聚类等论文，复现其中的方法，并搭建可以计算、评价因子的 factor_lab。 | 其中的实现和评价方法继续用于 algobench；不把论文方法直接当成已经识别真实算法账户的证据。 |
| 论文指标与主动关注度面板 | 把六篇论文的方法写成可计算的指标，检查指标相关性，再研究股票上主动交易痕迹的关注度，并生成按日面板。 | 旧方向在 7 月 10 日调整；关注度面板和公共计算代码继续进入正式因子研究。 |
| 正式因子计算：订单配对与行为评分 | 把逐笔数据整理成订单生命周期，寻找相关订单，对队列行为和价格冲击评分，再生成因子、收益标签和评价结果。 | 订单配对、评分和共享中间结果继续用于后续筛选定标及历史评价；具体版本是否通过验收仍看当天记录。 |
| 数量和价格筛选规则、历史区间扩展 | 研究哪些订单关系需要保留、怎样按价格和数量连续评分，并把正式因子评价扩展到更长日期范围。 | 7 月 29 日取消价格硬筛选，保留 10% 数量门和连续价格评分；这套规则随后用于固定参数历史评价。 |
| 固定参数的历史补算与结果解释 | 保留一套已固定参数，复用已完成日期，补算更早的历史区间，核对恢复来源，并解释报告中的因子公式。 | 后续开盘五分钟研究复用这批历史输入。定标日前的回溯结果属于固定参数历史评价，不能自动算作样本外检验。 |
| 开盘五分钟：因子评价与参数定标 | 围绕开盘后五分钟的委托行为构建和评价因子，估计连续评分尺度与结构参数，并改进读取、回放和计算速度。 | 后续分出撤单相位、深度匹配和分组定标等研究；计算提速与预测表现分开评价，九参数定标曾未达到 60 秒目标。 |
| 撤单等待时间、相位与机械撤单研究 | 先统计委托经过多久撤单，再把等待节奏、买卖方向及机械撤单行为写成因子，检查它们与同日日内收益的关系。 | 撤单分布和相位因子已有历史报告；机械撤单逐股稳定性的后续生成于 10 月 15 日停止。局部停止不撤销已有相位结果。 |
| 盘口深度匹配与跨股票同步预查 | 检查委托股数是否贴近可见盘口深度，并完成买卖侧因子评价；另曾预查不同股票是否出现同步委托。 | 深度匹配有 601 日、24 列评价。跨股票同步 C3.3 于 9 月 11 日放弃，9 月 18 日补记并清理；两项工作的去向不同。 |
| 老因子重算与单日性能检查 | 核对老因子的定义和输入，减少配对与评分的重复计算，以单日 300 秒为性能目标，随后启动 601 日历史计算。 | 历史结果用于后续模型输入和深市 328 列计算；300 秒是验收目标，不是所有交易日都能达到的统一耗时。 |
| 按股票和市场状态分组定标 | 比较不同股票、市场状态下的行为尺度，确定分组方式，生成六类连续评分尺度和所需结构参数，供正式因子计算使用。 | 参数包与结构参数接入后续深市 328 列计算。601 日内估计和评价这些参数，仍属于历史样本内研究。 |
| 深市 328 列因子的计算、验收与评价 | 用固定的模型输入列和新参数计算深市历史因子，逐日核验四类来源及合并结果，最后封存并评价与日内收益的关系。 | 10 月 18 日记录 601 日、328 列全期验收与单因子评价；这是当时参数与回放版本的结果，后续正确性修正另有记录。 |
| 沪市委托还原与公开可见因子口径 | 根据沪市逐笔数据还原可观测委托，核对订单号、序列和成交价格，并逐项判断公开信息能支持哪些因子定义。 | 仍有版本迭代、缺失与定义差检查。G0/G1、270/350/356 等数目属于不同版本和范围，不汇总成一套已全部完成的因子。 |
| 总量因子的模型研究计划与结构诊断 | 早期从 count 因子出发规划机器学习和结构诊断；原计划文件名写 51 个，正文后来改为 127 个 total-only 因子。 | 这里主要记录模型研究的起步计划；实际执行和多模型结果在后续“模型执行”链中。 |
| 模型执行、任务调度与资源限制 | 让不同模型共用固定的数据与研究规则，按 CPU、GPU、内存和时间限制分配任务，支持失败恢复，并减少重复拟合与归因计算。 | 后续 330 候选研究沿用部分输入和执行基础。无随机森林的阶段报告是 8 月 19 日归档的模型报告，不是撤单延迟报告。 |
| 330 候选到 328 列模型的选择与重算 | 从 330 个因子候选建立 LightGBM 和排序研究，修正选股、成交与估值的先后顺序；排除 f97 买卖两列后，发布 328 列输入的重算结果。 | 9 月 21 日发布修正模型结果。自动选择、已使用历史样本和毛收益各有边界，不能直接认定已得到可实盘交易的策略。 |
| 研究成果看板建站 | 建立研究成果、每日汇报和展示页，加入公式、图示、离线阅读及部署配置，让研究材料可以集中浏览。 | 看板随后继续发布报告和增加功能；这里的记录段结束不表示网站不再维护。 |
| 汇报发布与看板日常维护 | 把研究结果、解释和图表发布到看板，修正文案和浏览功能，并维护构建及项目规则。 | 持续维护中。这里的提交可能只是报告或规则修改，不据此认定研究计算在同一天重跑。 |
| 研究编辑台版式改造 | 按已选定的研究编辑台方向调整字体、纸墨配色、页面结构和窄屏显示。 | 版式改造已提交。它改善阅读方式，不作为研究结果正确性的证明。 |
| 汇报标签与结果页浏览功能 | 为汇报加入可保存的主题标签和筛选，并改进撤单、深度匹配报告中的方向对照、排序、公式和导航。 | 标签功能与报告浏览改造分别记录；不能把报告中的买卖方向功能都称为标签算法。 |
| LightGBM 模型报告及结果修订 | 发布模型设置、测试结果和诊断图，进一步解释 RankIC、组间排序及多空收益，并替换为因果时序修正后的结果。 | 9 月 19 日的初版报告早于 330 候选研究；只有 9 月 21 日的修订接入相应重算结果。 |
| 328 列因子的 601 日结果报告 | 把深市新参数 328 列因子的 601 日评价发布为可筛选、比较和下载的报告，包含逐日相关性、分组收益与逐列诊断。 | 报告已发布。它是单因子历史评价，分组毛收益未扣成本，也不等于模型或策略已在新的样本外期间通过检验。 |

## 26 条前后关系

| 起点 | 后续任务 | 关系说明 | 根据级别 |
|---|---|---|---|
| `onboarding` | `lv2-snapshot` | 上手后开始开发快照。这里只按记录顺序相连，不把规则整理写成快照实现的技术依赖。 | 按记录顺序关联 |
| `lv2-snapshot` | `literature` | 快照数据说明和输入被首个因子框架使用；文献收集本身不依赖完成快照。 | 有输入、代码或报告关联 |
| `literature` | `algobench` | 后续 algobench 把论文中的算法痕迹度量写成统一指标。 | 有输入、代码或报告关联 |
| `algobench` | `formal-engine` | 论文指标和关注度研究之后，代码继续扩成正式订单配对与评分流程。 | 有输入、代码或报告关联 |
| `doris-migration` | `formal-engine` | 服务器的 Doris 逐笔输入供正式因子计算使用；7 月 15 日草稿后来改过，不能当成迁移已经验收。 | 有输入、代码或报告关联 |
| `formal-engine` | `gates` | 在正式配对和评分流程上继续调整数量、价格规则及评分尺度。 | 有输入、代码或报告关联 |
| `gates` | `fixed-history` | 保留固定规则，先复用已完成日期，再补算更早历史。 | 有输入、代码或报告关联 |
| `fixed-history` | `open5m` | 开盘五分钟研究继续使用历史输入和评价流程。 | 有输入、代码或报告关联 |
| `ml-count` | `ml-exec` | 早期总量因子模型计划继续发展为多模型执行与调度流程。 | 有输入、代码或报告关联 |
| `open5m` | `ml-exec` | 模型流程读取已固定的开盘五分钟因子历史输入，避免边选模型边改输入。 | 有输入、代码或报告关联 |
| `open5m` | `cancel-phase` | 撤单等待节奏从开盘五分钟的订单生命周期数据中单独展开研究。 | 有输入、代码或报告关联 |
| `open5m` | `depth-match` | 深度匹配使用提交前盘口、L2 订单和股数分布等输入，另行检验委托量与深度的关系。 | 有输入、代码或报告关联 |
| `wangly-env` | `old-factor-bank` | 老因子计算使用已配置的服务器环境，环境和取数检查是开跑前提。 | 有输入、代码或报告关联 |
| `old-factor-bank` | `sse-v2` | 相同因子移向沪市时，需要另做原始委托还原和输入可观测性检查。 | 有输入、代码或报告关联 |
| `old-factor-bank` | `szse-model328` | 深市 328 列中包含老因子，继续沿用其定义和输入核验。 | 有输入、代码或报告关联 |
| `open5m` | `grouped-calibration` | 分组定标继续估计老因子连续评分所需的六类尺度，比较不同股票和市场状态。 | 有输入、代码或报告关联 |
| `grouped-calibration` | `szse-model328` | 深市 328 列计算绑定已验收的六核表和结构参数，参数生成与因子生产分步核验。 | 有输入、代码或报告关联 |
| `szse-model328` | `storage-cleanup` | 深市生产及性能试验产生的暂存，在结果归档可恢复后按范围清理。 | 有输入、代码或报告关联 |
| `szse-model328` | `report328` | 10 月 18 日的报告发布这批 328 列全期因子的单因子评价。 | 有输入、代码或报告关联 |
| `ml-exec` | `ml-330` | 330 候选研究沿用既有模型输入和执行基础，再增加自动选择及因果时序修正。 | 有输入、代码或报告关联 |
| `lv2-snapshot` | `replay` | 后续回到深市逐笔回放，重新检查订单簿、成交价格和快照对齐对因子的影响。 | 有输入、代码或报告关联 |
| `dashboard-build` | `report-publish` | 建站后在同一看板继续发布、解释和修订研究报告。 | 有输入、代码或报告关联 |
| `dashboard-build` | `visual-b` | 在已有看板上应用选定的研究编辑台版式。 | 有输入、代码或报告关联 |
| `visual-b` | `report-tags` | 标签与浏览功能加入现有看板；连线只表示页面演进，版式并不是标签算法的技术前提。 | 按记录顺序关联 |
| `report-tags` | `model-report` | 模型报告使用现有看板的阅读与展示功能；连线只表示交付顺序，不表示模型研究依赖标签。 | 按记录顺序关联 |
| `ml-330` | `model-report` | 9 月 21 日模型报告换成重算结果；9 月 19 日初版不属于这次重算的产出。 | 有输入、代码或报告关联 |

## 汇报摘要

32 篇摘要分别改写；实际数值与范围保留在正文中。摘要对应的正文逐份与修改前 Git 版本比较一致。两个示例摘要不伪装为真实结果。

| 报告 | 新摘要 |
|---|---|
| [2026-06-25](../../content/daily/2026-06-25.md) | 把 Level 2 委托、成交、撤单逐条回放，生成每 100ms 一张的订单簿快照。另生成 3 秒快照，与米筐官方行情逐档比较；所测沪深样本在连续交易时段的盘口 100% 一致。 |
| [2026-06-26](../../content/daily/2026-06-26.md) | 回顾快照重建代码怎样用于后来的服务器研究：复用事件定义、因果排序、订单簿状态和成交状态，生成事件前盘口、订单生命周期、共享配对结果、495 列因子及日内收益标签，并完成相应历史计算。复用的是计算方法，原来的本地快照文件没有直接成为正式输入。 |
| [2026-07-07](../../content/daily/2026-07-07.md) | 把六篇论文中的方法实现为 42 个算法痕迹指标，在 15 只股票、10 个交易日的小样本上计算、聚类和评价，再用 PCA 组合。报告解释从 L2 数据到各项检验证据的全过程；算法痕迹仍是公开数据中的行为代理。 |
| [2026-07-08](../../content/daily/2026-07-08.md) | 说明 SRuns 重复撤挂单指标为什么这样选参数。Task 1/2 的阶段工作已完成：重建 placebo 对照，按结构读数固定参数；150 股票日的完整重跑仍暂缓。 |
| [2026-07-09](../../content/daily/2026-07-09.md) | 说明 evalv2 怎样检查算法痕迹因子：先排除流动性的影响，再比较三类参照指标、事件冲击、时间分布和稳定性，判断指标在反映什么，以及证据是否可靠。 |
| [2026-07-13](../../content/daily/2026-07-13.md) | 构建深市主动算法关注度的 27 个因子：9 类订单痕迹分别按笔数、股数和金额汇总。在 2025-07-01 至 2025-07-18 的 14 个交易日、39941 个股票日上，用 9 类未来收益、逐日 RankIC、Newey-West t 和分组收益做中期评价，并给出稳定性图表与可复现流程。 |
| [2026-07-22](../../content/daily/2026-07-22.md) | 记录 2026-07-11 至 2026-07-22 的计算提速：减少热点重复计算，复用缓存和数据库提取，调整并行与内存，把候选订单关系直接交给后续汇总，并让多个评价窗口共用输入。每项都说明解决什么问题及实测效果。 |
| [2026-07-23](../../content/daily/2026-07-23.md) | 解释 2026Q2 的 47 个主因子和 5 个配套对照。隔日研究用 open1h，日内研究用 open3m；两者分别计算和定标，收益标签分别为 formal9 隔日收益与 09:44—09:45 日内 VWAP 收益。 |
| [2026-07-29](../../content/daily/2026-07-29.md) | 记录 7 月 22 日后的性能修改：把 Response 和 Scorer 的热点改成列式计算，提前筛除不合格候选，限制定标内存，复用运行缓存，把中间数据暂存在本地。报告分别列出候选生成、正式因子计算和五日定标的耗时，保留每轮检查及真实数据结果。 |
| [2026-07-31](../../content/daily/2026-07-31.md) | 解释算法行为因子的公共计算步骤、50 种不同构造逻辑和 55 个规格思路，并比较 165 个实测口径的 IC、Rank_IC、ICIR，帮助读者对照定义与结果。 |
| [2026-08-01](../../content/daily/2026-08-01.md) | 保持因子定义不变，把评价区间扩为 2026-03-30 至 2026-07-16 的 72 个交易日。报告列出 165 个口径的 IC、Rank_IC、ICIR、排名、诊断及每项四张 Notebook 图。 |
| [2026-08-02](../../content/daily/2026-08-02.md) | 保持因子定义不变，在 2026-01-05 至 2026-07-31 的 131 个交易日上做固定参数评价，列出 165 个口径的 IC、Rank_IC、ICIR、排名、诊断和四张 Notebook 图。定标日前的回溯不属于纯样本外检验。 |
| [2026-08-04](../../content/daily/2026-08-04.md) | 保持因子定义不变，在 2025-01-02 至 2026-07-31 的 364 个交易日上做固定参数评价，列出 165 个口径的 IC、Rank_IC、ICIR、排名、诊断和四张 Notebook 图。参数没有重估，较早日期的结果属于固定参数回溯。 |
| [2026-08-05](../../content/daily/2026-08-05.md) | 把分母统一为全部委托后，检查 2026Q2 的异常、54 个因子的相关性、PCA 和买卖方向。结果显示 Q2 主要有风格共振；其中一组因子完全重复，PC1 解释 55.2%，9 个主成分解释 90%。拆分方向没有消除 Q2 异常，卖方痕迹与 SignedPressure 相对更稳定。 |
| [2026-08-06](../../content/daily/2026-08-06.md) | 记录 8 月 6 日至 9 日新增 Open5m 高频量价和微观结构因子时的计算优化：共用中间结果，批量计算 Pair/Response，前置 10% 数量门，修正 CPU 利用不足和历史预检的重复扫描，补充逐因子 Notebook 及受保护的续跑入口。最终所测 2026-04-01 的 495 列面板用时 300.657 秒。 |
| [2026-08-07](../../content/daily/2026-08-07.md) | 汇总 2025-01-02 至 2026-06-30 的 490 个正式候选因子、5 个诊断列和 135 个逻辑家族，每列配四张评价图。报告解释 L1–L5 各层定义、白皮书方法如何落入代码、两个区间的表现及结论边界。 |
| [2026-08-16](../../content/daily/2026-08-16.md) | 统计 2026 年上半年 5.62 亿条沪深匹配撤单，按原生 10ms 格点展示日均频数、逐日热图和月度变化。沪市最强峰在 6 秒，深市有 1—6 秒多个峰；这些是等待时间分布特征。 |
| [2026-08-19](../../content/daily/2026-08-19.md) | 记录不含随机森林的 14 类必需模型和 1,384 个候选配置：怎样切分数据、花了多少时间、怎样自动选择和固定方案，以及开发期折外评价和仅使用开发样本的 Final。另列 PCA/ICA/IPCA/CAE、PBO、Permutation、Native、SHAP、LOFO 诊断，并解释 LightGBM CUDA/CPU 的实现差异。 |
| [2026-08-24](../../content/daily/2026-08-24.md) | 统计 601 个深市交易日、10.42 亿条匹配撤单。2024 年最高频等待时间为 0ms，2025 年和 2026H1 为 3000ms；2026H1 的 5.5—6.5 秒频带明显增强。报告展示分布随时期的变化。 |
| [2026-09-02](../../content/daily/2026-09-02.md) | 说明新因子机制预查怎样减少 L2 查询、解析、状态构建、C1/C3/C7 计算和写入的耗时，并调整并行调度。取消 199 次随机对照后，2026-04-01 单日冷启动完整任务实测由 206.49 秒降到 29.91 秒；两次计时的研究范围变化一并说明。 |
| [2026-09-03](../../content/daily/2026-09-03.md) | 记录九组结构参数定标中最终保留的优化。代表日 2026-04-22 的首个完整正确版本用时 249.17 秒，r29 为 115.89 秒，结果逐值一致；仍未达到 60 秒目标。 |
| [2026-09-04](../../content/daily/2026-09-04.md) | 汇总 2024—2026H1 共 601 个交易日的六类机械行为痕迹预查，并补充 C7.1 委托量精确匹配盘口深度的订单级联合证据。这些检查描述行为分布，不直接证明收益预测能力。 |
| [2026-09-06](../../content/daily/2026-09-06.md) | 从撤单等待时间分布出发，构建 7 类、24 个相位因子，在 601 日上检验它们与同日 09:35 前最后成交价至 09:44—09:45 VWAP 收益的关系。整体排序关联较弱，端点收益和定义重复另作分析。 |
| [2026-09-07](../../content/daily/2026-09-07.md) | 用 12 类定义检查委托量是否接近盘口深度，买卖两侧共 24 列，完成 601 日评价。报告展示逐日 IC、Rank IC、累计曲线、44 个区间、十分组收益及完整验收记录。 |
| [2026-09-16](../../content/daily/2026-09-16.md) | 评价 284 列正式因子和 4 列诊断指标的 601 日结果。可筛选、排序和比较日度及月度 IC、分组收益、全样本 OLS、精确原值分位数，并下载完整精度数据。 |
| [2026-09-17](../../content/daily/2026-09-17.md) | 把 9:35→9:45 分钟 VWAP 标签逐日稳健标准化后，\|z\| 的全样本 p99 为 6.28，逐日 p99 中位数为 6.18，三个年度在 5.8–6.7。最极端的 1% 样本占 L2 平方误差的 37.4%（正态分布参照为 8.4%）。取 c=6 时压缩 1.12% 的样本，该误差占比降到 22.7%；取 c=4 时压缩 2.98%，降到 16.1%。 |
| [2026-09-18](../../content/daily/2026-09-18.md) | 328 因子 CPU LightGBM 在 15 折扩张验证的第 15 折、176 日 test 上，RankIC 为 0.0231，多空毛 Sharpe 为 7.05。97.61% 的 RankIC 来自十分组之间的排序；两腿收益相关 0.731，协方差抵消单腿方差和的 72.74%。选股名单在进场成交状态产生前锁定，未退出持仓保留估值；27 张图沿用原展示版。毛收益不等于扣成本后的可交易收益。 |
| [2026-10-07](../../content/daily/2026-10-07.md) | 在深市 601 日、171.96 万股票日上，比较六类尺度的股票分组、市场状态、预测中心和交叉分组的样本支持。预检已验收封存，分析用时 51.6 分钟；与历史归档中心的差异单独展示。 |
| [2026-10-09](../../content/daily/2026-10-09.md) | 阶段成果：601 日、171.96 万股票日的六类核尺度分组参数包已封存，有 94 个完整单元，三个模型用全样本拟合，耗时 16 分 14.6 秒。截至这份报告，正式引擎接入、结构参数处理和真实因子验收仍待完成。 |
| [2026-10-14](../../content/daily/2026-10-14.md) | 通过复用概率和撮合计算、列式抽样、逐页评分及共享 Arrow 调度，减少沪市委托 v2 的重复工作。所测整日评分快 3.96 倍，峰值内存降低 90.6%；真实前向撮合平均使用 15.89/15.95 核。各项数字对应报告中的具体阶段与测试范围。 |
| [2026-10-16](../../content/daily/2026-10-16.md) | 记录深市 328 列计算的提速和存储清理。2026-04-22 完整任务由 1258.56 秒降到 471.17 秒，后续生产版为 453.71 秒；2025-11-18 由 564.13 秒降到 337.62 秒。报告说明共享输入、精确计算、Arrow 审计、结果发布及内存配置的修改；数值和 NaN 位置保持精确一致。 |
| [2026-10-18](../../content/daily/2026-10-18.md) | 评价采用新参数的 328 列因子在 601 日上的表现，展示逐日 IC、Rank IC、44 个区间、10/40 分组毛收益及超额收益、全样本 OLS、散点密度和原值分布，并保留逐组诊断。这里是历史单因子评价，毛收益未扣交易成本。 |
