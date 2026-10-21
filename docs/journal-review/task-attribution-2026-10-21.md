# 研究日志任务提交归属复核

2026-10-21。用户选择按“任务归属的提交量”表示点的重量。本次保留32条链、89张人工日卡及182个任务点，增加逐条提交归属层并替换点径取数。没有把提交数解释成工时、复杂度或成果价值。

## 范围与计量

- `sirui-quant-research`：`9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6`。
- `Quant_Research-Trading`：`e63c0d3726d03245724fd15e59ecf8ff0000a825`。父仓仅采集既有思瑞子目录白名单。
- `internship-dashboard`：`0910a201154aa02b6889ad77899943a2eb656d1c`。

完整枚举各固定版本自6月1日以来有范围内文件变更的提交，读取作者时间、完整文件变更状态和标题。作者时间转Asia/Shanghai，不按报告/PLAN文件名挪动提交量。逐天逐仓与原固定采集核对，89天全部一致；新增清单不受旧证据“每天只列前10条”限制。

一条提交共一份。仅服务一个目标时整份计入；确实分别交付多个独立目标时等分，份额用有理数保存。等分是计数约定，不表示两项工作各耗一半时间。消费者、公共模块、测试依赖或旧任务名字的出现不构成拆分理由。修复、尝试、撤销、验收和记录都可能产生提交，计数不能据此认证结果已成功。

维护/规约、子仓状态同步、重复导入历史和范围外事项另列。证据不足的提交暂不计重，也不平均摊进当天任务。提交归属与人工工作日是两个层次：同一链有归属提交但当日未设图点时，明细标“当日未设图点”，不自动改写日卡或制造工作日事实。

## 全量清单与审阅层级

| 处置 | 条数 |
|---|---:|
| 单一任务 | 2722 |
| 明确跨任务 | 26 |
| 待核 | 8 |
| 规约/维护/同步 | 55 |
| 既有历史导入 | 2 |
| 本次范围外 | 1 |
| 合计 | 2814 |

逐SHA专项处置共256条，包括共享依赖、跨度异常、看板功能与报告目标，以及最初规则无法判定的公共改动。其余使用明确主题/专用文件规则与受计划、代码阶段限定的上下文规则。页面逐条显示依据层级：主题与专用文件2092条、阶段上下文466条、专项复核256条。

专项处置记录审阅依据，区分路径/主题/目标复核与相关差异复核；这不是对2814条提交逐字代码审查，也不认证原研究每行实现或全部运行结果。既有审计只作定位，归属清单中的SHA、变更文件、时间和相关差异来自本次重新读取的原始Git对象。

分类规则和逐SHA修正见[`journal_attribution_rules.json`](../../scripts/journal_attribution_rules.json)，完整逐日提交身份、理由、锚点与精确份额见[`_attribution`](../../content/journal/_attribution/)。本地完整盘点与相关原始差异留在`artifacts/journal-task-weight/`，不把旧审计的候选标记直接提升为已确认归属。

## 32条链的计入边界

下表为整个固定快照的归属量，包含明细中未设当日图点的提交；图上每个点只读取自己的日期/链组合，不使用本表总量。原始任务定义和固定证据仍见[链条登记](chains-and-handoffs.md)。

| 链ID | 全期归属量 | 本轮采用的边界 |
|---|---:|---|
| `onboarding` | 8 | 米筐示例、最初交易规则资料；后续公开因子中的交易规则核验随当次沪市目标。 |
| `doris-migration` | 1.5 | 最初Doris网关、查询计划与迁移；10月有界取数归效率，交易时窗归冻结恢复。 |
| `wangly-env` | 20.5 | 环境构建、默认Python、完整性与结果传输能力；账户名只是操作对象时不另计环境建设。 |
| `doris-efficiency` | 9 | 公共有界分页、读取预算与代表样本；不把每个使用Doris的研究都算成效率建设。 |
| `storage-cleanup` | 89 | 明确的盘点、退役、容量和恢复目标；研究内普通缓存或错误收尾随该研究。 |
| `lv2-snapshot` | 21.5 | 最初100ms/3秒快照工程；后期沪市重建和原生回放核验按各自新目标。 |
| `replay` | 159 | 当前原生回放、撮合、终态证明及正确性/执行接口整改；消费者回归不自动复活旧任务。 |
| `literature` | 28.5 | 论文整理、复现及首个评价框架；六篇比较/关注度面板归algobench。 |
| `algobench` | 46 | 早期六篇指标比较及主动关注度面板；之后同名algobench目录不继续自动归本链。 |
| `formal-engine` | 190.5 | 7月正式引擎、订单配对、行为评分与该轮运行支撑；后续公共代码按本次目标。 |
| `gates` | 130 | 7月底数量/报价门与区间研究；五分钟定标或生产内的门修正随本次任务。 |
| `fixed-history` | 33 | 固定历史来源、补算与结果解释；不因为后续任务也用历史样本就计入。 |
| `open5m` | 388.5 | 五分钟因子、早期连续核定标和机制/标签预查；机械撤单、C3.3、分组、344等专用目标分开。 |
| `cancel-phase` | 84.5 | 等待时间、相位和机械撤单实际研究及交付；沪市检查相位输入可见性归沪市。 |
| `depth-match` | 27 | C7盘口深度匹配与24列因子，以及比例尺寸线尝试；C3.3单列，后期公开dm列审查归沪市。 |
| `old-factor-bank` | 155 | 旧库定义、F40修复、整库验收和对应研究；按模型合同生成256个来源输出归328生产。 |
| `grouped-calibration` | 157 | 股票/市场状态分组、六核/结构参数采集与封存；328消费这些参数不使每项定标同时计入生产。 |
| `szse-model328` | 136.5 | 固定328列四来源计算、日面板、发布、验收与性能；来源代码旧库/模型接口不重复计研究。 |
| `sse-v2` | 346 | 沪市委托还原、时钟/通道、公开可见及G1/v3定义；版本号不机械增链。 |
| `ml-count` | 0.5 | 两份早期模型计划的可追溯入库；名义8/4、8/6没有同日提交时不挪移8/10的提交量。 |
| `ml-exec` | 506 | 多模型执行、调度、数值/资源及该轮环境支撑；后期330或基础整改按新目标。 |
| `ml-330` | 13 | 330候选设施及328单次因果复算；没有把所有候选记作完成，也不按selection一词误认早期RF。 |
| `dashboard-build` | 23 | 最初建站与阅读/下载能力；研究内容发布和后续独立功能另分。 |
| `report-publish` | 71.5 | 报告内容、图表、证据附件制作与通用阅读维护；不回记为报告所述研究的再次计算。 |
| `visual-b` | 1 | 已选研究编辑台的壳层版式；不作为标签或模型研究的输入贡献重复计重。 |
| `report-tags` | 7.5 | 标签持久化，以及既定链范围内的方向/范围选择、层级排序、成对浏览与公式展示；纯结果附件归发布。 |
| `model-report` | 8 | 9/18模型报告的9/19—21制作和因果结果替换；8月全模型结果页仍在一般发布链。 |
| `report328` | 5 | 10/18的601日328成果报告；10/16提速报告另归一般发布，不按328字样误并。 |
| `corrected-replay-344` | 11.5 | 独立344清单、修正盘口六核/结构采集和定参准入；通用账本证明的修复本身归回放。 |
| `trading-window-freeze` | 16 | 交易日、冻结/恢复、在途SQL和有效时钟的独立能力；普通guard回归按其实际服务目标。 |
| `research-journal` | 35 | 日志设计、证据、审阅、任务链和交互；仅改旧日报字段的提交归一般维护发布。 |
| `cross-stock-sync` | 19 | C3.3跨股票同步预查、停止及补记；不和C7单股盘口深度匹配混合。 |

## 关键取舍与纠正

- **共享实现随本次目标。** 7月的formal、8月五分钟、9月旧库、10月328/344可能改同一个模块。最初脚本/目录名不能决定之后几个月的归属；阶段规则有明确仓库、日期和代码路径限制，只在没有其他专用目标证据时采用。
- **输入和消费者不互相复制贡献。** 沪市可见性检查相位/dm定义归沪市；328生成256个旧库来源输出归328；344复用旧定标器归344。公共接口整改涉及多个旧消费者，通常仍是同一次整改目标。
- **定标与生产分开。** 10/10结构采集、F40匹配、核/结构参数包归分组定标；旧库2220数值列单日不变性归旧库；328准备、按列生成与日面板验收归328。不能把下游将使用某参数当作下游已经完成计算。
- **研究与报告分开。** 看板发布相位、深度匹配或328结果只给发布/报告任务计量；9/9的方向筛选、范围选择、层级排序和成对浏览归既定结果页功能链。10/16提速报告不混到10/18成果报告，8月全模型页不混到9/18模型报告。
- **研究目标与所需规则分开。** 10月的交易规则/订单可行集是沪市公开定义研究，不能因“交易规则”一词归最初上手；股票代码300344不能命中344重新定参；RF selection也不能命中后来330选择任务。
- **归档、改路径与重复导入不制造新研究。** 研究仓初始导入、父仓子仓指针、搬动旧PLAN及agent规约单列。多个任务的文件因一次接口迁移被触及，不据文件数给每条链一份完整提交。

## 仍待核的8条提交

这些差异可以确认修改了什么，但在当前证据下不足以可靠指定唯一研究任务。公共对象发布、哈希/清单、guard计时与调度通知可能服务多个并行目标。保留待核，不用时间接近某个任务来硬分。

| 入库日 | 原始提交 | 修改对象 |
|---|---|---|
| 2026-10-12 | [1ef6e5d612](https://github.com/MengerWen/sirui-quant-research/commit/1ef6e5d6122e2227fed6275d6bcf5612e6472d08) | 以精确对象列举核实缺失回执并保留存储失败 |
| 2026-10-12 | [7780f72239](https://github.com/MengerWen/sirui-quant-research/commit/7780f7223988b18a54bc47979a07b634f0112269) | 记录受限业务命令从进程创建到退出的完整墙钟 |
| 2026-10-12 | [477d4469c5](https://github.com/MengerWen/sirui-quant-research/commit/477d4469c52e82c7c6d00078407e3661af7d620d) | Release verified day-bucket copies within the bounded publication queue |
| 2026-10-12 | [c8f4b959a3](https://github.com/MengerWen/sirui-quant-research/commit/c8f4b959a341e884e72f8d9cb2c110f8cd1be245) | Reuse bounded native integer-array hashing for persisted exactness audits |
| 2026-10-12 | [815945eb1c](https://github.com/MengerWen/sirui-quant-research/commit/815945eb1c2053f1981a9de4c04e93710af00d85) | Verify each exactness column is hashed once across shared projections |
| 2026-10-14 | [3d6900bc06](https://github.com/MengerWen/sirui-quant-research/commit/3d6900bc06bf76f17f7c6e1fdfc2965e0d407ab9) | 使对象发布按命名空间定位并免除挂载目录查询 |
| 2026-10-14 | [7d4c224b9a](https://github.com/MengerWen/sirui-quant-research/commit/7d4c224b9a793a9b6cead6274d34cc13d4e2cb6d) | 通过公共入口还原分布统计的日桶元数据 |
| 2026-10-16 | [5d004f8f76](https://github.com/MengerWen/sirui-quant-research/commit/5d004f8f7681a4b14a956c02eb9c82f9179b91e4) | 按实际提取状态验证股票完成通知 |

## 明确跨任务的提交

每条合计一份。部分记录同时交付生产和独立存储治理，部分分别保存回放验收和新定参启动；保留原始身份与理由，不能把等分解释成精确投入比例。

| 入库日 | 原始提交 | 归属 |
|---|---|---|
| 2026-07-08 | [15b41275ac](https://github.com/MengerWen/Quant_Research-Trading/commit/15b41275ac1c5a9c0fbd172d03aa0035743d4cd8) | literature、lv2-snapshot，各1/2 |
| 2026-07-16 | [9e4260f442](https://github.com/MengerWen/sirui-quant-research/commit/9e4260f4425b3b158b6d71fdf7a9b410ace8bf38) | doris-migration、formal-engine，各1/2 |
| 2026-08-10 | [2318d2ff29](https://github.com/MengerWen/sirui-quant-research/commit/2318d2ff29815213e6f108cb3308629dfa601869) | ml-count、open5m，各1/2 |
| 2026-09-06 | [5a99501615](https://github.com/MengerWen/sirui-quant-research/commit/5a99501615c59e68138b5ad4bf86e8dcfa1fc6d3) | cancel-phase、storage-cleanup，各1/2 |
| 2026-09-08 | [58173176f8](https://github.com/MengerWen/internship-dashboard/commit/58173176f8acfcb9e863250501fb66ea56b6ef19) | report-publish、report-tags，各1/2 |
| 2026-09-10 | [94c27f2054](https://github.com/MengerWen/sirui-quant-research/commit/94c27f205428e08e59e3bf069bf4aff56afe6823) | old-factor-bank、storage-cleanup，各1/2 |
| 2026-09-12 | [38863c3b52](https://github.com/MengerWen/sirui-quant-research/commit/38863c3b5242988cf501685bd92c36f791af275d) | old-factor-bank、storage-cleanup，各1/2 |
| 2026-10-10 | [ccadbf7bb3](https://github.com/MengerWen/sirui-quant-research/commit/ccadbf7bb3ef11a212ef0e3fc3e21f116019ff7b) | sse-v2、storage-cleanup，各1/2 |
| 2026-10-11 | [aea059550e](https://github.com/MengerWen/sirui-quant-research/commit/aea059550e93f56062c4a001f7f348db0c4818ec) | grouped-calibration、sse-v2，各1/2 |
| 2026-10-12 | [4beb8237ee](https://github.com/MengerWen/sirui-quant-research/commit/4beb8237eebea20630cf3198de4c252f8c572ec0) | grouped-calibration、szse-model328，各1/2 |
| 2026-10-14 | [5e674b8917](https://github.com/MengerWen/sirui-quant-research/commit/5e674b891724c06424f13dca6d67b12fa8613d7a) | storage-cleanup、szse-model328，各1/2 |
| 2026-10-15 | [14de5d97b1](https://github.com/MengerWen/sirui-quant-research/commit/14de5d97b17efc535196b2d487e79db16fe30a77) | storage-cleanup、szse-model328，各1/2 |
| 2026-10-15 | [1cde2f6107](https://github.com/MengerWen/sirui-quant-research/commit/1cde2f6107b1f23419e57ed21d62b20e3fb7ac63) | storage-cleanup、szse-model328，各1/2 |
| 2026-10-15 | [edd6683568](https://github.com/MengerWen/sirui-quant-research/commit/edd6683568de1cc83ff3b4d545249708a554360d) | storage-cleanup、szse-model328，各1/2 |
| 2026-10-15 | [d50d5bb2a8](https://github.com/MengerWen/sirui-quant-research/commit/d50d5bb2a8758f15455cc865ac5a35ba790e6544) | storage-cleanup、szse-model328，各1/2 |
| 2026-10-15 | [5e068c27f6](https://github.com/MengerWen/sirui-quant-research/commit/5e068c27f6540ce357764ab085cc15f7bd1c414c) | storage-cleanup、szse-model328，各1/2 |
| 2026-10-15 | [2053570fbf](https://github.com/MengerWen/sirui-quant-research/commit/2053570fbf74ceb33696c11fb8ff7ceed689c849) | storage-cleanup、szse-model328，各1/2 |
| 2026-10-15 | [10ef70b895](https://github.com/MengerWen/sirui-quant-research/commit/10ef70b895e55c00688ad531cc466bc0fc810b14) | storage-cleanup、szse-model328，各1/2 |
| 2026-10-15 | [530962e7f2](https://github.com/MengerWen/sirui-quant-research/commit/530962e7f29bafb8bdecee69e3deed64824a02ab) | storage-cleanup、szse-model328，各1/2 |
| 2026-10-16 | [6e244a79aa](https://github.com/MengerWen/sirui-quant-research/commit/6e244a79aa5f78f9276df2b64124acb720602578) | storage-cleanup、szse-model328，各1/2 |
| 2026-10-16 | [25545c3c58](https://github.com/MengerWen/sirui-quant-research/commit/25545c3c58eaec59f2edb097339148c16f05029f) | storage-cleanup、szse-model328，各1/2 |
| 2026-10-16 | [91e76c8aa2](https://github.com/MengerWen/sirui-quant-research/commit/91e76c8aa251c14bf78417a9818d3c12c793981c) | storage-cleanup、szse-model328，各1/2 |
| 2026-10-17 | [f222f25907](https://github.com/MengerWen/sirui-quant-research/commit/f222f2590788290ce3304787d6b65626df051cdb) | sse-v2、storage-cleanup，各1/2 |
| 2026-10-17 | [ec565dddb2](https://github.com/MengerWen/sirui-quant-research/commit/ec565dddb273fb4c4b97934be0d88f7e76d1d684) | sse-v2、storage-cleanup，各1/2 |
| 2026-10-20 | [61bf9f93ff](https://github.com/MengerWen/sirui-quant-research/commit/61bf9f93ff6b005489151081439abecc3df476df) | replay、wangly-env，各1/2 |
| 2026-10-21 | [95f9f8b68d](https://github.com/MengerWen/sirui-quant-research/commit/95f9f8b68d5042b9905926e4aa2d1cecbeb2f181) | replay、corrected-replay-344，各1/2 |

## 图表与可复核性

点径固定为`2.4 + 0.58 × log2(1 + 归属量)`，所有日期、链条、时间窗和密度共用同一刻度。收口方块采用与对应圆点相同的面积。没有已归属提交时保留最小定位点；缺少清单时显示待核，均不回退到当天总量。原有空实、去留和交接语义保持。

点卡与各项记录显示归属量及跨链份额数量。展开“原始记录”可见“任务归属明细”：全部提交按任务分组，给出仓库、固定SHA链接、份额、理由、锚点文件与依据层级；维护、历史导入和待核另列。旧的前10条提交摘录仍可作为简短索引，但不能替代完整明细。

10/20的五个已有图点分别为回放64.5、环境16.5、沪市12、344定参10、研究日志32；此外一般发布有1份当日未设图点，4条维护不计重。合计136份归属量加4条维护等于140条提交。修改前五个点全部用140，现场半径均为7；修改后按各自数值计算。

规则以`reviewed_through: 2026-10-21`限定本轮已审阅日期，新日期提交先进入待核，不能让旧关键词自动产生已确认重量。完成新一轮核对后再推进该日期。

构建只消费本仓已保存清单，不调用源仓采集。逐仓总数、唯一身份、日期、链ID与份额必须通过检查；来源配置或分类规则指纹变化但清单未刷新时构建失败。离线版内嵌相同完整证据，不依赖打开GitHub才显示归属。

## 设计流程与模型范围

沿用已批准的研究编辑台/推进图谱，这是同项目迭代；没有重新选择视觉方向。遵循现有字体、颜色、文字入口和键盘行为，补统一数值图例。设计技能已逐项核对当前全局、项目与插件目录，记录实际文件身份与适用摘录于本地`skill-inventory.json`；文档、演示、图片、模板及宠物等流程只核对其适用范围，本任务没有另行创建这些产物。通用“重做三方向/新建站点”的建议不覆盖已选方案的本次计量修改。机械设计检测无发现。

主会话配置及原始`turn_context`核对为`gpt-6.1-sol / xhigh`。未派生子代理，未调用其他模型接口。记忆生成/使用入口在配置中关闭。应用不公开的后台辅助调用没有本轮可审计记录，不能据主配置声称存在强制模型白名单。

## 验证与交付记录

归属采集`--check`为89天、差异0；逐条有理数核对归属量守恒，逐日逐仓计数与固定证据一致。Python/JavaScript、正式/离线构建及浏览器记录见同目录的`task-attribution-acceptance-2026-10-21.json`。原有未跟踪10/10汇报草稿造成的两条mtime警告仍属于既有材料，不纳入本项提交。

只改本看板的计量、证据和维护说明，没有修改源研究仓、同步服务器或启动训练/回测/全历史业务计算。Git提交、GitHub推送与自动发布完成状态以本轮最终回执为准，本报告不预填发布成功。
