# 后期研究链与交付链逐项审计

审计日期：2026-10-21，Asia/Shanghai。范围为指定的 16 条现有链、以它们为 `from` 的 11 条现有交接线、这些链的逐日记录及报告出口，并追查当前源仓中 10 月 20 日之后的延续。本文件只提出修订，不修改生产登记表、日卡或研究代码。

## 1. 固定版本、模型与证据口径

| 对象 | 本次固定版本 / 范围 |
| --- | --- |
| 看板仓 `D:/MG/！Internship/BUILD/汇报` | `0910a201154aa02b6889ad77899943a2eb656d1c`，下文记为 D |
| 研究仓 `D:/MG/_GitLinked/Quant_Research-Trading/26 Summer/❗思瑞投资/sirui-quant-research` | `9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6`，下文记为 R |
| 父仓 `D:/MG/_GitLinked/Quant_Research-Trading` | `e63c0d3726d03245724fd15e59ecf8ff0000a825`；只允许 `26 Summer/❗思瑞投资/` |
| 既有 `_evidence` 研究采集版本 | `e488eaa6a3fe547c871ea396cfeef7761e6d8883` |
| 既有 `_evidence` 父仓采集版本 | `ee956d57ef3bd8e8c3290ba84a294b0409f824c8` |
| 既有 `_evidence` 看板采集版本 | `d55c7f6a227aead85f7c1a620def73c91370fbfa` |

旧采集版本来自 D 的 `scripts/journal_repos.json`。它不是本次 R、D 的当前版本。`content/journal/_evidence/2026-10-20.json` 仍只列研究旧采集版本下的 51 次当日提交；本次查到的 v3/v4/v5 回放、344 重定参和沪市 v3 不能冒充该 JSON 已采集内容。这里既保留旧版本当时的历史结论，也单列新版本的适用性变化。

模型配置已核对 `C:/Users/19927/.codex/config.toml`：主模型和审阅模型均为 `gpt-6.1-sol`，主推理强度和计划强度均为 `xhigh`。本子代理原始记录为 `C:/Users/19927/.codex/sessions/2026/10/21/rollout-2026-10-21T09-32-49-01a15c16-ed56-7bc0-a361-16eb19a2f3a6.jsonl`；`turn_context` ordinal 9、时间 `2026-10-21T01:32:51.364Z`，明确记录 `model=gpt-6.1-sol`、`effort=xhigh`，collaboration settings 也相同。没有再开子代理，没有外部模型请求。已阅读项目 AGENTS 与 `shuorenhua`。

本次直接读取原计划、研究结果、决议、关键提交的改动路径与相关 diff；旧 Codex 审计仅用于定位。下文引用的 R/D 文件均绑定上述完整 SHA，文末给出路径与行号。文件名日期、commit 日期、服务器运行时间、报告归档日期分别看待；不能仅因报告名含某日就认定该日存在研究记录。本次没有连接服务器、重新执行训练、重定参、全历史计算或部署；运行结果是对已提交原始回执和结果报告的核查，不能称为本次服务器现场复验。

## 2. 需要优先修正的结论

1. `wangly-env → old-factor-bank` 的“依赖解除”缺少依据，并存在账户反证。旧因子 9 月 7 日 PLAN、9 月 10 日执行记录和 9 月 11 日正式 Python 环境都在 **wenjie**。不能把 9 月 4 日 wangly 环境建好当成旧库开跑前提。[R04][R05][R06]
2. `doris-efficiency` 把已经实现并真实测量的工作压成“主要是一份计划”。公共 L2 reader 已接入，真实 SQL、解析、分页和 Linux 回归证据均存在。应补实施与有界验收，保留未迁移旧入口的限制。[R03]
3. `wangly-env` 也不只有“结果同步计划”。9 月 4 日已做大小文件 canary、重复传输与篡改拒绝验收；这些证据不等于所有研究结果都实际同步过。[R01][R02]
4. `depth-match` 把已交付的 24 列深度因子与已放弃的 C3.3 跨股同步放在同一链。两者目标、产物和终态不同，应拆链；9 月 18 日的 dropped 点只属于 C3.3。[R07][R08][R09]
5. `old-factor-bank` 漏 9 月 8 日实现与 F40 验证；当前只列 9/7、9/10、9/11、9/12。9 月 17 日原报告明确“实际评价完成”，也不能只留“发布”而丢掉研究验收。[R10][D01]
6. `grouped-calibration` 结束在 10 月 11 日，但结构参数 v2 于 **10 月 12 日 02:36:46** 完成、02:38:16 封存，应该补入 10/12；不能让交接早于上游完成。并且“601 日结构定标”不是九组全为 601 日：七组重估，z12 与 λRV 保留 R19 的 200 日来源。[R11][R12]
7. 10/9 日卡把核参数包封存写在 10/9；原成果报告明确封存实际为 **10/10 00:31:50**。开发/估计可在 10/9，最终封存应放在 10/10；归档日期仍保留 10/9。[D02]
8. 当前 R 明确拒绝旧参数直接用于修正回放下的正式全量计算。`grouped-calibration`、`szse-model328` 的历史验收仍成立，但其 `landed` 缺少“旧回放版本、不能直接复用为当前生产输入”的后续说明。[R13][R14]
9. 10/20—10/21 的 **344 列独立范围重新定参** 应新增链，不能写成旧 328 列补跑。六核 601 日正式采集已启动，八组结构及冻结、消费者验收还没完成，也没有启动 344 列全期因子生产。[R15]
10. `sse-v2` 后续已经出现逻辑分类 v2 和可见口径 v3 候选实现。它们优先补入现链延续：版本升级本身不足以新建任务。v3 触发一小时速度停止门，29/30 股完成，最终构造只有单股检查，未全市场验收；不能由链条级 `landed` 模糊各阶段未验收范围，也不能写成沪市正式生产完成。[R16]
11. 至少六处报告出口有错位或只表示共用载体：wangly→9/4、Doris→10/9、replay→10/18、老库→9/7、tags→9/7、深市328→10/14。它们不能作为该链成果的直接证据，逐项见下文。
12. `visual-b → report-tags` 和 `report-tags → model-report` 的原文已自称只表示页面演进/交付顺序，应删除。另一个 inferred `onboarding → lv2-snapshot` 不在本组出边范围，但其登记原文也只给先后顺序；应与两条一起删除，除非另找到真正输入依赖。
13. `ml-330` 的9/20全候选实现与9/21固定第15折单次因果复算需要分开。后者没有证明133候选完整运行/选优已经结束；model-report实际消费的是单次r03复算。未跟踪9/20草稿只作补充需求，不能计固定R执行证据。[R34][R35][R36]

## 2.1 全部16链结论矩阵

| 链 | 当前记录数 / 日期 | 本次裁定 |
| --- | --- | --- |
| `wangly-env` | 1；09-04 | 补传输真实canary；移除错误报告/出边；环境后续修复需续段 |
| `doris-efficiency` | 1；10-09 | 将只有计划改为实现+实测；重连真实成果 |
| `storage-cleanup` | 3；10-14, 10-15, 10-16 | 各批完成边界有效；早期治理候选另核，禁止合并回收量 |
| `replay` | 4；10-17, 10-18, 10-19, 10-20 | 保留主链，续10/20晚与10/21；旧参数拒绝与新定参分开 |
| `depth-match` | 5；09-05, 09-08, 09-09, 09-10, 09-18 | 必拆C7.1交付与C3.3放弃；后者不是深度因子续作 |
| `old-factor-bank` | 4；09-07, 09-10, 09-11, 09-12 | 确定漏9/8；补9/17评价验收证据；删除9/7错误出口 |
| `grouped-calibration` | 5；10-07, 10-08, 10-09, 10-10, 10-11 | 确定漏10/12；改跨午夜封存归属；补当前来源限制 |
| `szse-model328` | 6；10-10, 10-12, 10-13, 10-14, 10-16, 10-18 | 保留旧版本601日完成；性能未过门；当前回放生产需新准入 |
| `sse-v2` | 10；09-23, 10-08, 10-09, 10-10, 10-11, 10-13, 10-14, 10-15, 10-16, 10-17 | 同链补10/20—21；版本不是拆链充分条件；分阶段停止状态 |
| `ml-330` | 2；09-20, 09-21 | 9/20候选研究与9/21单拟合分别记；不认候选全量选优完成 |
| `dashboard-build` | 5；07-07, 07-08, 07-09, 07-10, 07-13 | 初建段结束合理；两条直接源码延续边可留 |
| `report-publish` | 22；07-23, 07-31, 08-02, 08-03, 08-05, 08-06, 08-09, 08-10, 08-20, 08-24, 09-04, 09-05, 09-08, 09-11, 09-17, 09-18, 10-07, 10-09, 10-10, 10-14, 10-16, 10-20 | 22点发布/功能/治理逐项分清；研究日志建设可单独管理 |
| `visual-b` | 1；08-11 | 保留批准/实施；删除仅顺序的下游标签边 |
| `report-tags` | 2；09-07, 09-09 | 标签API与方向报告浏览分功能记录；删顺序模型边 |
| `model-report` | 3；09-19, 09-20, 09-21 | 9/19初版与9/21数据替换分别保留历史；补报告出口 |
| `report328` | 1；10-18 | 10/18发布成立；保留线上导航/下载未完成验证限制 |

此表的记录数是当前日卡归属数，不是研究工作总天数。缺日与跨午夜等修订在逐链段落给出；组织层级的可选拆分与有原始证据的确实漏项分开处理。

## 3. 16 条链逐项复核

### 3.1 `wangly-env`：环境建设与传输实现应分清

**当前登记：** 1 日，9/4；done / landed；出口 daily 9/4。

**边界结论：** 保留为基础设施链，目的改成“配置 wangly 独立研究环境，建立并验收 wangly→wenjie 的结果传输合同”。环境配置、传输实现、传输 canary 是不同验收对象；可以在链内分阶段，也可以拆成环境与传输两个子任务。不能只写成方案，更不能把 canary 可用外推为全量研究结果已回传。

| 日期 | 当前归属 | 原始证据及结论 |
| --- | --- | --- |
| 9/4 | 环境、同步方案 | `a96ac59535a0101b476bff66c9828e6a50d2e9e9` 实际修改 `server-env.sh` 的账户默认值、合同测试及两个操作 prompt；环境 PLAN 的步骤本身不是完成回执。[R01] `5f268360b4e021550294472299f543d231fea3ca` 提交真实传输验收：256 MiB 大文件、1002 小文件、重复执行 already_verified、目标篡改后不生成 marker。[R02] |

**覆盖和状态：** 9/4 日期成立；“传输方案”低估已完成部分。环境 PLAN 第 25–37 行要求 freeze/pip-check/exact revision，当前登记没有链接独立环境回执，因此不要仅凭 PLAN 新增“全部环境终验通过”的断言。10/20 新报告又记录两账户默认环境故障、重建及独立 RECORD 校验，应单列环境修复续段，不能仍让单日 done 被理解为当前环境始终无故障。[R14]

**报告出口：** `content/daily/2026-09-04.md` 是“Open5m 新因子机制预检”，不覆盖环境配置/传输 canary。删除这个直接成果出口，改连 R 的传输验收报告及环境证据。现有出边到老因子库应删除，见 H01。

### 3.2 `doris-efficiency`：计划之外已有代码和真实实测

**当前登记：** 1 日，10/9；done / landed；fate_note 称“主要是一份通用效率计划”；出口 daily 10/9。

| 日期 | 原始事实 | 需修正处 |
| --- | --- | --- |
| 10/9 | `3e88b4df49fa2e63295e88114206af0ac676f8dd` 新增 page_processing 与 benchmark；`7df629de0c0ae16370a10bb2b5e18e5fe136ba2e` 直接修改 IO、QueryPlan、scheduler 并接入校准 runner。原结果报告记录 18 SQL 客户端比较、27 SQL 完整读取、固定/自适应页复测、Windows/Linux 回归及准确版本。[R03] | 日卡 note/headline/highlights 和 chain purpose/fate_note 应补“实现公共有界取数、比较解析/分组和页宽，保存有界实测及规约”。 |

**验收边界：** 36.6% 是解析与分组子阶段，完整读调用减少 21.9%—30.4% 是三段样本；自适应沪市复测反而慢 6.1%。不能改写成全流程同幅提速或全部历史入口迁移。原报告 74–80 行明确已迁移与仍待迁移入口。[R03]

**出口：** daily 10/9 是六核参数包，不是本项性能验收。改用 `reports/2026-10/2026-10-09-general-compute-efficiency.md`。现有没有出边；若补到分组定标，只能定位为共享 reader 的代码依赖，不能把此前已运行全部预检都说成靠本次优化完成。

### 3.3 `storage-cleanup`：保留各批口径，补足之前遗漏的清理

**当前登记：** 3 日，10/14—10/16；done / landed；出口 10/14、10/16。

| 日期 | 应保留的事实与验收边界 |
| --- | --- |
| 10/14 | wangly 已清系统盘旧 IDE、tmpfs 副本和 S3 重复日桶；分别为 670,715,904 分配字节、2,381,451,264 分配字节、3,825,407,878 对象逻辑字节，不能相加成配额回收量。保留恢复映射与基线。[R17] 同日沪市 v2 热清理属于另一任务，不能全部归因深市328。 |
| 10/15 | 五类材料退役、4201 个 S3 对象、303,951,350,119 逻辑字节；271 日摘要继续保留；此时普通 S3 写入仍因配额失败。不能用已删字节宣布配额恢复或原历史定参全过程仍可恢复。[R18] |
| 10/16 | 深市328失败暂存/性能材料清理，明确 15.73 GB tmp 分配量与约2.08 GB S3净逻辑减少；保留271日、规范基线和160个去重恢复来源，未动另一会话的运行材料。[R19] 另完成542对象凭证补存及回读；当时完整科学环境仍有失败，不能写“两台完整回归通过”。[R20] |

**漏项：** 既有广义“存储盘点、归档与重复文件清理”并不是从10/14才开始：R 中有9/9、9/10校准存储清理、9/11旧因子/服务器清理、9/12全历史启动与64.85 GB清理、10/10和10/12校准清理、10/13 cache reclaim。它们须纳入全量补点清单，或把现链明确改名为“10月双账户存储集中治理”，避免暗示此前没有存储工作。仅凭这里列出的文件名不批量认定实际删除日；逐个按原始报告正文及提交时间核对。[R21]

**终态：** 这几批限定目标完成可保留 done。存储治理是持续工作，10/18报告生成还清理6.20 GB临时量，10/20—21新定参也有预算、归档与到期复查；建议存储治理总链持续、各清理批次各自结束。原料退役不自动使当时冻结参数无效；10/20参数不适用的证据是旧回放来源缺失，不能归因于“删了旧文件”。[R13][R18]

**出口：** 10/16报告确实包含本链；10/14报告主要沪市提速/缓存清理，只能覆盖相应子批次，不能替代整个wangly存储清理报告。

### 3.4 `replay`：正确性、生产接口与参数准入不宜混成一次完成

**当前登记：** 4 日，10/17—10/20；active / landed；出口 daily 10/18。

| 日期 | 原始事实 | 阶段与限制 |
| --- | --- | --- |
| 10/17 | 单日撮合规则、成交价、事件态和快照对齐；A+C+B 下256列需重算，80列明显变化，302132缺引用单列。[R22] | 诊断/修复/单日检查，不是全历史通过。 |
| 10/18 | 三日生产数值内核对照；当时原回放仍默认；2024有一个300股截止块未发布；固定偏移留出仍有差异。[R23] | 显式新版本与三日验收；100%区间可匹配不是唯一时间对齐已解决。 |
| 10/19 | adopted决议把核心归 snapshot.replay，研究单向依赖，并拆正式执行阶段。[R24] | 架构实施与兼容性，属于同主线独立工程阶段；不能由重构推断科学正确性。 |
| 10/20 | 核心/阶段交付、默认环境修复、小样本试算、参数适用性核验。[R14][R25] | 原日卡仅写小样本/全量条件，漏掉旧参数被正式入口拒绝这一关键结论。 |
| 10/20晚—10/21 | v4规则认证撤单，v5限价终端闭合；95f9f8b6记录3个完整日及601日六核采集启动。[R15] | 旧_evidence之外的新快照；应续入10/20/21，参数采集另建新链。 |

**拆合建议：** 保留“回放规则与正确性”主链；若需要表达工程工作量，将10/19—20“原生回放核心与正式执行阶段”独立成子链，用R24明确的模块依赖连接。344重定参必须独立，不塞入回放修复的 done。

**报告出口：** daily10/18是旧参数328列单因子评价，不是回放验证报告，应删除该出口或改成“同日并行成果”。真实出口为R22、R23、R25及当前v5证明。当前active比done谨慎，但landed须附所指具体版本与未通过范围。

### 3.5 `depth-match`：把C7.1与C3.3拆开

**当前登记：** 5日，9/5、9/8、9/9、9/10、9/18；done / landed；出口daily9/7。

| 日期 | 现点应如何拆分 |
| --- | --- |
| 9/5 | C7.1真实描述性预检，不构造因子、不读收益。[R07] 归“深度匹配预检→24列因子”。 |
| 9/8 | C7.1独立注册24列、完整单日27.16秒、601日/14,424因子日独立复算、24notebook与浏览器检查；业务版本147ab55c，结果accepted且未同步wenjie。[R08] 当日另写/推进C3.3，必须形成第二点。 |
| 9/9 | C3.3性能诊断、暂停交接，不能继续当作深度匹配因子改进。 |
| 9/10 | C3.3原生输出/发布时间分析，仍归跨股同步。 |
| 9/18 | 原计划标明9/11放弃C3.3；9e26b6ed于9/18补记并移除执行证据。[R09] 点标记“放弃决定日期9/11，补记/清理日期9/18”，不回溯声称9/18才决定放弃。 |

**边界与去向：** C7.1保留landed，结束在9/8实际交付；C3.3独立链的终态为dropped。两者同用预态/生命周期不构成C7.1成果派生出C3.3的直接证据，不因拆链自动补交接。C3.3预检为描述性，不应写成已验证预测力。[R09]

**报告覆盖：** daily9/7在正文明确归档9/7、实际验收9/8，适合作为C7.1成果；不能用于9/9、9/10、9/18的C3.3覆盖。拆链后这些日的report关系应各自审核。后续328的depth24有直接输入引用，现图反而缺这条有产物血缘的边。[R26]

### 3.6 `old-factor-bank`：实现、全期启动与全期评价应补全

**当前登记：** 4日，9/7、9/10、9/11、9/12；done / folded；出口9/7、9/16。

| 日期 | 结论 |
| --- | --- |
| 9/7 | PLAN明确待执行，完整日≤300秒含import/JIT/取数/发布；此日不能写300秒已验收。[R04] |
| **9/8漏点** | 0105f016实际接入结构参数、F42完整响应候选；F40验证从1174.44秒到432.50秒，匹配及支持精确一致。这个结果仍不证明整库300秒、正式200日参数或601日完成。[R10] |
| 9/10 | 执行入口、preflight、单股canary及等价性修复，单股guard97.12秒不等于整日；失败与未完成reference保留。[R05] |
| 9/11 | F40/响应长尾与整库性能、正式Python依赖副本及资源检查；环境验收不等于300秒达标。[R06] |
| 9/12 | 完整601日生产于18:33:49启动，284正式+4诊断；启动回执明确全期尚未完成，labels_built=false。[R21] |
| **9/17待补研究完成点** | 原公开结果正文19–21行明确601日数值/逐日审核/独立检查已覆盖，评价实际完成9/17，原生产guard最终汇总曾超时。当前日卡只归report-publish，会把已发生评价验收删成“只是发布”。补本链或独立“老库全期评价”链，不冒写生产guard正常退出。[D01] |

**出口：** daily9/7是DM，移除；daily9/16是正确的老因子全期评价，但展示它时保留实际完成9/17、R19参数、样本内、原生产guard超时这些限制。模型输入及后续256老输出可形成folded；不能因为被模型使用就把历史300秒目标视为全日统一达成。

**后续：** 10/19旧因子性能对照虽可并入回放/性能分支，若链保留done，需注明只结束9月旧R19生产段。10/20旧R19/分组参数来源不适用当前回放，历史数值不被追溯抹掉。[R13]

### 3.7 `grouped-calibration`：核、参数表、结构三阶段分别收口

**当前登记：** 5日，10/7—10/11；done / folded；出口10/7、10/9。

| 日期 | 原始阶段及纠正 |
| --- | --- |
| 10/7 | 分类与评价设计。名为9/29的报告首次进入git是10/7的be040e3f，不据文件名凭空新增9/29工作日。[R27] |
| 10/8 | 桶预检、共享输入与历史中心核对、预检计算；不写已冻结最终核包。 |
| 10/9 | 601日控制/预检、尺度估计及规约；启动报告明确当时运行中、未封存。[R28] 参数包最终封存在10/10零点，不提前一天标完成。[D02] |
| 10/10 | 六核包完成；601日逐股票日参数表、绑定回归与结构采集接入。[R11][R29] 生成参数表不是重新训练/估计核。 |
| 10/11 | F40支持与精确归约、结构全期续算，不能提前称最终runtime已发布。 |
| **10/12漏点** | 02:36:46计算结束，02:38:16封存；runtime_v2和正式入口交接完成。七组601日、两组200日；本任务未启动因子生产。[R12] |

**拆合建议：** 一个链可保留，但至少阶段化为“预检/核尺度包→601日参数表→结构v2/runtime”，在图上以10/12为最后记录。若拆链，参数表应标定值应用，避免和核定标混作一次估计。

**报告覆盖：** daily10/7是预检报告，10/9是核参数包，二者都不覆盖10/12结构runtime最终验收。追加原R12而不是把旧公开报告标题改成“全部参数完成”。

**当前适用性：** R13真实读取的旧runtime、包与表哈希都完整，但缺当前回放观测来源。该链成果保留为旧回放版本，新增“当前生产需重新定参”的显式限制。新344采用全局共享六核、八组均601日，与旧分组股票日核/九组混合日期不同，不宜直接延长为同一科学合同。[R13][R15]

### 3.8 `szse-model328`：历史完成成立，当前生产资格须补说明

**当前登记：** 6日，10/10、10/12、10/13、10/14、10/16、10/18；done / landed。

| 日期 | 核验结论 |
| --- | --- |
| 10/10 | 对冻结模型列、老因子消费与结构参数准备，既是本链前置也涉及分组定标；应允许两链归属，不把所有准备吞进深市生产。 |
| 10/12 | 由冻结r03模型的全部328输入映射生成精确清单，256 old+24 cancel-buy+24 cancel-sell+24 depth；不按树分裂次数只留325列。压力日生产启动。[R26] |
| 10/13 | 五压力日及数据库恢复后进度；21/601的时点不是全期完成。 |
| 10/14 | 提速/暂停/资源与结果发布，不写全601已完成；public10/14主要为SSE提速，不能作为本链直接成果。 |
| 10/16 | fastest验证、生产继续、存储收尾各自记录。最快完整日337.622秒，不把它说成300秒，record_only不是性能通过。[R19][R26] |
| 10/18 | 601/601、1,719,612股票日、328列全部科学验收，复用271补330；全期性能未达门、采用record_only。之后独立评价，无新SQL、因子重算或模型训练。[R26][R30] |

**边界：** 旧328和未来344独立。328是冻结模型输入合同，不是“所有因子仅剩328”，不能把模型未分裂、历史缺失、f97研究范围等排除理由统一改成无效因子。新参数也未对旧模型重训。[R26]

**出口：** factor showcase可作为概括；daily10/16确为本链性能报告；daily10/18确为单因子历史评价；daily10/14主要SSE，应删去或限定为跨任务综合记录。`done`必须写“10/18旧参数/旧回放版本已验收”，并追加10/20当前默认回放下旧包不具生产准入的说明。[R13]

### 3.9 `sse-v2`：补齐延续，分别说明阶段验收

**当前登记：** 10日，9/23、10/8、10/9、10/10、10/11、10/13、10/14、10/15、10/16、10/17；**active / landed**。active本身正确，问题是缺10/20—21延续、各阶段验收范围及landed所指对象。

| 日期 | 当前点应覆盖的目标与状态 |
| --- | --- |
| 9/23 | 原始订单重建与公司字段审计，保持可观察量与原始申报属性的区别。名义9/22报告实际10/8才入库；不能仅凭文件名新增9/22提交日。[R31] |
| 10/8 | 原生回放、输入可观察性反例、统一输入保护；原公式无损迁移未通过，228本地回归不等于服务器真股日生产。[R31][R32] |
| 10/9 | 沪深适配/消息距离，属于原始格式与时钟合同，不等于公开可见因子定义已定。 |
| 10/10 | 开盘空窗、序列和reference；源数据缺字段不能靠补虚拟委托当成识别真值。 |
| 10/11 | 正式时钟及输入覆盖，允许沿重建子链。 |
| 10/13 | 订单号、前向概率与缓存/评分，这是v2重建工程。 |
| 10/14 | 输入覆盖、规则/feasible sets/模型和性能报告；计算性能的完整样本不等于所有因子科学迁移通过。 |
| 10/15 | 公开可见因子审计，研究对象已从原始订单重建转为因子定义适用性。 |
| 10/16 | visible合同、G0/G1与三值逻辑，单列该阶段目标与验收；只有独立管理交付时才拆子链。[R33] |
| 10/17 | 57成员/266列退化通过；270列联合入口发布未运行；真实分层速度未过一小时门，停止50股扰动/真值/全市场定义差。[R33] |
| **10/20—21漏延续** | 同一公开可见因子目标继续完成逻辑分类v2→可见v3候选。352源列/540候选身份、单股构造，29/30速度试算后停止，未全市场验收、未发布生产面板。[R16] |

**拆合建议：** 首选保留现链并改进名称为“沪市原生订单重建与公开可见因子”，补齐10/20—21及各阶段终态。现purpose已经包含可见因子口径，不能仅因v3升级另建一条。内部可区分“原生订单重建/时钟与输入工程”“公开可见因子定义与实现”，前者交付原生事件/账本与可观察量，后者选择公开属性下的因子数学定义、独立列身份及逐列科学验收；只有需要单独管理这些可独立交付目标时才拆子链。这是整理层级的选项，不属于已证实漏链。v3明确不采用旧G1 v2统一三值/仅A幅度规则，须保留替换原因与候选身份，而不是把两版混作完整实现。[R16]

**反证保留：** R31证明同可见行情可对应不同原限价，dm03/dm04原式不能被唯一恢复；R32对old f13/f15也有实际原评分器反例。早期“高秩相关可复用”只是测试口径下的近似影响，不推翻不可识别性。v3保留单股E2差异，不能以相关高抹掉定义差。

### 3.10 `ml-330`：候选、选模、因果复算与新样本外须分清

**当前登记：** 2日，9/20—9/21；done / landed；出口model showcase。

| 日期 | 核验结论 |
| --- | --- |
| 9/20 | fffb32f5、938a2825、5ae111a6分别实现候选manifest、Development自动选择和连续runner；tracked候选代码明确133 method rows。[R35][R36] 这是实现证据，尚无全部133方法×树候选×15折完整跑完的原始结果，不写“全部候选已选优完成”；也不能被9/19初版模型报告倒算成此前成果。 |
| 9/21 | 761e46bd排除f97双侧，6e95f1ee修正预算和未退出持仓；最终沿既有第15折、1000轮和176日测试区间重训328输入，先锁09:35池和预算，再按09:35—36成交决定建仓、不补仓，09:46估值保留open_marked。[R34] |

**两项目标是否混写：** 9/20全候选比较目标与9/21固定第15折单次因果重算并非同一个已验收产出。R34明确延续9/18 CPU LightGBM，不是宣称从133方法的全部OOF结果选出该模型；tracked全候选runner第3–5行仍写独立Development选择和monthly_test_refit_prediction阶段。[R34][R36] 当前“330候选到328列模型的选择与重算”容易让读者误以为前者完整选优已产生后者。至少将日点和fate拆成两项目标，或分出“全候选研究实现”与“单次拟合因果账本复算”两链；只有后者由9/21报告交付证明完成。

另读到工作树未跟踪草稿 `PLAN/2026-09-20-open5m-330-lightgbm-full-candidate-study.md`，字节SHA256为 `4f2eb941c3478d686a3eb9237b3ee29e406dcbb325b2e10897816fbb0714268b`，git status明确 `??`。草稿5–7行规定133目标/历史组合与独立合同，15行明确当前只写计划，31行把9/18报告当粗浅canary，35–42行要求完整Development/冻结Test。它不是固定R树内文件，不能拿来证明9/20已完整运行，更不能把其中冻结Test合同与tracked runner中的monthly-refit自动视为一致；主报告应将草稿需求和已提交实现分层。这里不访问其引用的历史聊天，也不据草稿判定实际运行授权。

**边界：** 原测试区间已被9/18结果观察，9/21是观察性复算，不能称新封存test；09:46估值不是所有仓位完成退出的净值；未覆盖交易费用、库存与跨日实际退出。[R34] 这条链的done最多证明相应单次研究重算和报告发布，不能替133候选全研究签收。

**交接：** 到model-report只定位9/21单次因果复算修订，不能把9/19初版或133候选全研究当本边产出。到深市328尚缺一条更强的直接输入边：R26第19–38行用这份r03的feature_mapping和booster哈希冻结范围，建议补“模型输入合同→因子重算清单”，不声称重新训练模型。

### 3.11 `dashboard-build`：初建范围可以保留，发布不自动代表研究完成

**当前登记：** 5日，7/7、7/8、7/9、7/10、7/13；done / landed。

| 日期 | 事实与边界 |
| --- | --- |
| 7/7 | `1b792246376fa7a0cdd20025642d3be0c9a85544`建立看板、材料和构建入口。 |
| 7/8 | `e6b80f52c3b33ffb61be34915eb8d03ad4f024a8`加入重复撤挂单展示/快照图；是交付内容，不意味着当天再做全研究。 |
| 7/9 | `3da1015e2b4eef06685d31555dd619ef9594aa8a`发布算法痕迹评价。 |
| 7/10 | 修订前日评价报告；应留在初建阶段的发布修订，但与研究转向区别。 |
| 7/13 | `b92a19bd69f60382e890320978823990f25a04b0`补图示和日报时间。 |

**边界与出口：** 当前初建阶段结束合理，同一仓后续维护不能因此结束。9月后的标签、模型报告并非本链仍未完成，而是后续独立功能。示例日报只保留发布事实，不能当真实研究覆盖。下游report-publish和visual-b两条边都有同一站点源码的直接修改，可保留；无须用时间邻接辩护。

### 3.12 `report-publish`：发布、浏览功能、项目规则、研究日志应拆清

**当前登记：** 22日，7/23—10/20；active / landed。下面逐日核对均以D固定历史的实际变更文件为依据，不能从同日发布推断同日重跑研究。

| 日期 | 代表原始commit与文件 | 归属结论 |
| --- | --- | --- |
| 7/23 | `11d42ebed84aa734e189b30d63c782f7cb816f1b`，daily/2026-07-23.md公式渲染 | 发布/解释成立。 |
| 7/31 | `34928c6fc93f23a2045ce934e4f29e39c5d1dff7`，7/31构建链路与165口径show | 报告交付成立；不补算研究。 |
| 8/2 | `356f0f7631d653a64c8a4a2e1e268c1fdc71f456`，8/1日报与show、factor showcase、生成器 | 实际发布8/1归档报告，应与8/2名义报告分清。 |
| 8/3 | `cb9e929f06a2370c3d08ec01b23afc2d1898fc3b`，8/2历史评价报告 | 发布归档前日结果成立。 |
| 8/5 | `fa6c660461cb57b930d6ae4743ea8adbbd9f99d4`、cc85e15，长历史报告及全委托分母解释 | 发布+公式修订成立。 |
| 8/6 | `7a138f8e059847e32cd5c13d7a94c89152cd348f`，heading-collapse计划、构建、JS/CSS、测试 | 是通用浏览功能，建议移入看板功能维护子链。 |
| 8/9 | `9471617ba9a1d91f5d8dd7aa461d1c35c3533693`，daily/2026-08-06.md | 提速说明归档，不是8/9重新计算。 |
| 8/10 | `ac48af21d30459e6861847a5cbf54c0f774ae800`，8/7因子研究报告/证据；b15e2d0图表放大 | 报告发布和通用功能两件事。 |
| 8/20 | `b43c9c8ace83be3223bc93fdc24d4047ed64d43e`，8/16撤单频率报告；81bc1c7章节viewer | 发布和展示交互并行。 |
| 8/24 | `1255769a94769277e4ce132f39121daec9b82e1e`，8/24历史撤单报告 | 发布成立。 |
| 9/4 | `a86755c07bd656ce66696b2a41194f35049a6fab`，9/2预检show | 更新旧归档，不能据此认9/4所有链都有报告。 |
| 9/5 | `03348187348b5c6835687b5f220f4f02167abf70`，9/2show的C7预检发现 | 发布新子节成立。 |
| 9/8 | `7c47a36c52d0a573deb1d802c00636932a0822d4`，DM报告及原验收报告；7565078导航 | 发布C7.1与导航功能分别记。 |
| 9/11 | `3f8b9c3be0082193ab8bfd1320590789a0fbd723`，机械预检资产、8/24show | 只是机械预检发布，不证明后续逐股稳定性完成。 |
| 9/17 | `4cb93168c391f1851d498ddd2d29247a7a73623e`，9/16原老库评价；ef4cc9f、9c9e108定义/筛选诊断 | 发布成立；原正文另证明实际评价9/17完成，应补研究链点。[D01] |
| 9/18 | `6bcb0ae6f3ee5ea7073b4f5233cf6283d7c877ca`，9/17标签软压缩预检 | 归发布；不是模型重训。 |
| 10/7 | `d720d487a9eb3b2a25600f675d42ea3caea2450c`，AGENTS/CLAUDE | 项目协作规则，和“汇报发布”主题不相同，应移项目治理或维护规则子链。 |
| 10/9 | `c6efd4396be7a80afb8d3eb3d314fc812671dca7`，10/7六尺度预检报告 | 报告实际发布日期10/9，保留归档10/7。 |
| 10/10 | `ef248d3170112c5424e8949bb86341bef012c564`，10/9六核包阶段成果及资产 | 保留实际封存10/10零点、正式引擎待接入。[D02] |
| 10/14 | `9c6af730713829d3e46d0669c831800ebac2f4e3`等，沪市v2提速与来源权限核查 | 独立性能报告发布；不能覆盖深市328全期完成。 |
| 10/16 | `05b66c7ac43fdec916c90725f3b2ad96c1f09135`、89ed348、da94946，深市提速复盘及发布验收 | 本链发布成立，研究性能/清理原始结果归对应研究链。 |
| 10/20 | `a97222421b3dc38eaaef8c6c05b7497ac2791716`，新journal JS/CSS/源码；之后内容/交接审计和节假日 | 已超出日常报告发布，应独立“研究日志建设与内容维护”链。 |

**10/21漏延续：** b58b636f制定每日九点更新与证据归并；902b03b4支持Ctrl滚轮；0910a201支持图例高亮。都属于研究日志功能/维护规则，当前日卡止于10/20。应补10/21卡；若单独管理新栏目建设，则归日志链，若仍用现维护总链则加明确子任务。不能让一切网站工作都没有具体目标。

**拆合方案：** 保留纯“研究报告发布与修订”；通用浏览功能可与report-tags合成“看板浏览与交互”，但保留各独立功能/日期；项目规则独立治理；10/20—21研究日志独立。model-report/report328仍保留具体交付链，避免同一报告同时被两条链无差别记成两份成果。closes_into选列的日子只是部分报告，不应暗示所有22点都由这8篇日报覆盖。

### 3.13 `visual-b`：保留已批准版式，删去伪交接

**当前登记：** 1日8/11；done / landed；无报告出口。

方向批准记录保留用户“实施方案B，对当前项目进行修改”，范围包括全局令牌、顶栏、阅读/展示与窄屏；实施计划明确在既有纯HTML/CSS/JS上改造。[D03][D04] c9ecdcf23e06b2092eb9837e391c6e6b85794f49确实修改tokens、base/daily/showcase样式、site/index、showcase.js及相关测试/截图。此项作为版式迭代结束合理；不是“标签算法前提”。

原截图和计划中的Expected不足以单独证明每项验收已实际通过；当前fate_note只写“已提交、后续沿用”可以保留。9/19模型报告批准记录明确沿用既定研究编辑台，证明视觉规范的复用，但不能据此把中间tags列为模型报告的必要输入。H09删除。

### 3.14 `report-tags`：标签与方向浏览是两个功能，不是一项算法

**当前登记：** 2日9/7、9/9；done / landed；出口daily9/7。

| 日期 | 原始事实和建议 |
| --- | --- |
| 9/7 | 7896f7d9新增report-tags/tag-model、worker、报告标签JSON、持久接口与测试。标签可保存/主题筛选是本链核心；同日发布撤单相位报告应归发布链。 |
| 9/9 | 买卖方向对照、筛选/排序、公式与导航属于因子报告浏览器，和tag持久逻辑目标不同。可拆“标签管理”与“报告探索器”，或归上节提议的统一浏览交互链，逐功能保留。 |

**出口：** daily9/7是DM因子研究，不是标签功能说明或验收。可以作为“被功能服务的报告样例”，不能作为功能成果本身；建议换到worker/API/浏览器验收原件。现有到model-report边只有交付先后，应删除；模型页直接复用9/16原始报告模板/导航/图表，不能由9/7标签推导模型报告。

### 3.15 `model-report`：发布初版与9/21替换的时间正确，但初版会被当前正文覆盖

**当前登记：** 3日9/19—9/21；done / landed；无单篇出口。

| 日期 | 原始commit与结论 |
| --- | --- |
| 9/19 | a4f5af84182616227fe6d21c86c7a29e00631b63发布名义9/18报告、模型设置/test/18图。原始初版在这个commit读取，不能只看当前被9/21替换的同名路径。 |
| 9/20 | 1265d59e、22e2bd86、0a94bd52细分15折扩张验证、子池/贡献/组内RankIC、Sharpe；8988c1ea为全部show加导航高亮。模型统计解释与通用导航应分别归属。 |
| 9/21 | bc1098eb8bc950290a83e37b92ad6da1c730d67d导入因果328复算；8349892245fd5eb076b76af7b7b29dd7304ada7a恢复原展示样式、更新相同数据图；不是撤销因果结果。README精确指向r03训练/test目录、0cedf22d业务版本和source_files。[D05] |

**边界：** 15折是设计时间边界，实际当前结果只跑第15折，不能写“15折验证全部完成”；176日test是已经观察过的复算。[D05][R34] 当前无closes_into使具体成果不容易找到，应加daily9/18，并附真实初发9/19、因果修订9/21。history links分别指初版commit与修订commit，保留被覆盖的原结果身份。

**交接：** ML到此的9/21收口可保留；tags到此删除。没有现有出边，本组不凭同站点顺序再连report328。

### 3.16 `report328`：报告已发布，在线浏览器两项限制不能写没了

**当前登记：** 1日10/18；done / landed；出口daily10/18。

R研究报告直接引用看板`content/daily/2026-10-18.md`，说明新参数328列601日评价，无新SQL/因子重算/训练；D报告PLAN反向绑定研究入口、标签SHA和验收SHA，数据血缘很强。[R30][D06] 1a0fefd809d4dad0410cc02640fc5f086a94f209实际发布328份按需统计、14,432行分期CSV、展示页和Markdown；Cloudflare发布回执记录构建成功和100%部署版本。

**验收边界：** D06第37行明确本地功能与97项Python通过，但浏览器扩展未返下载完成事件、线上导航超时，这两项不记通过。第39行确认云构建/流量切换，不等于线上导航现场操作通过。当前fate_note“报告已发布”可保留，不能扩写“线上所有交互全部验收”。[D06]

**科学边界：** 这是历史单因子评价，毛收益未扣成本、原方向保留，不是模型328重训、更不是新样本外策略。后续新回放使部分原因子需重算；原报告作为旧版本历史成果保留，附后续版本限制，不覆盖正文里的原验收身份。[R13][R22]

## 4. 全部11条现有出边逐条裁定

证据等级：A=直接文件引用/机器输入与哈希；B=直接代码修改或同一产物身份；C=内容支持但缺直接依赖；D=只有顺序。`confirmed`只是旧登记字段，不作为证据。

| 编号 | 当前边 | 证据、反证与裁定 |
| --- | --- | --- |
| H01 | wangly-env→old-factor-bank / 依赖解除 / confirmed | **删除，C且有反证。** 旧PLAN236/252/279–300和9/10执行记录15行均为wenjie，9/11依赖副本也在wenjie；没有wangly环境输入到旧库的直接回执。[R04][R05][R06] 公共server-env改成HOME相对只能证明通用实现，不证明这次新账户环境是旧库必要前置。 |
| H02 | old-factor-bank→sse-v2 / 派生 / confirmed | **保留，但收窄为旧库原式在SSE可见输入下的适用性/迁移。B。** R31共享入口直接保护old生命周期及depth，R32指定v5旧库并调用实际原scorer，f13/f15反例与union传递是直接代码对象。不是“完整沪市原因子已算通”；最早交接日期应按原9/23源码commit核实，不拿名为9/22但10/8才提交的报告日期代替。[R31][R32] |
| H03 | old-factor-bank→szse-model328 / 延续 / confirmed | **保留，A。** 10/12 PLAN第7、19–29、63–67行精确选择256旧输出、v5定义与必要依赖。不是所有284旧列原样全搬，也不是模型只用325分裂列。[R26] |
| H04 | grouped-calibration→szse-model328 / 延续 / confirmed | **保留历史交接，A。** 10/12 PLAN第71–81行直接绑定runtime_v2、六核表与精确SHA，R12有完成回执。交接不能早于10/12 02:38；新增日期或说明。[R12][R26] 当前默认回放下该旧包已拒收，另加版本限制；不能删历史边伪装从未采用。[R13] |
| H05 | szse-model328→storage-cleanup / 派生 / confirmed / 10/16 | **保留并收窄，A。** R19第3、17–35行直接列328失败目录、替代正式签收、性能载荷及受保护恢复源。10/16定位正确。10/14沪市热清理及其他账户治理不能全部算这一条边的产物。 |
| H06 | szse-model328→report328 / 收口 / confirmed | **保留，A。** R30第12行指看板结果；D06第7、17、21行绑定研究评价入口/验收SHA/聚合输入。研究10bca944与看板1a0fefd8对应的是相同328评价。交接日期可明确10/18；不能泛化为模型训练结果。 |
| H07 | dashboard-build→report-publish / 延续 / confirmed | **保留，B。** 后续commit直接改同站点content/daily、生成器与showcase，7/23 11d42eb对原看板管线改公式。证据是相同载体/构建实现继续交付，不只日期先后。建议把目标收窄到报告发布，将新日志另列。 |
| H08 | dashboard-build→visual-b / 延续 / confirmed | **保留，B。** c9ecdcf2直接重构既有tokens/base/daily/showcase/站点壳层；D04明确保留既有路由/构建结构，D03有用户方向批准。 |
| H09 | visual-b→report-tags / 延续 / inferred | **删除，D。** c9ecdcf2是视觉壳层，7896f7d9新增标签存储/API/worker；后者使用现有网页不意味着由版式成果派生。旧note自己注明“只表示页面演进、不是技术前提”。可分别挂到站点基础链，不制造标签算法依赖。 |
| H10 | report-tags→model-report / 延续 / inferred | **删除，D。** 模型页原批准与生成器复用研究编辑台、9/16展示页及导航图表，未引用tag服务作为研究/发布前提。旧note自己注明“只表示交付顺序”。 |
| H11 | ml-330→model-report / 收口 / confirmed / 9/21 | **保留但收窄来源目标，A。** R34明确单次因果328复算，未声称133候选完整研究产出；D05第16行直接消费r03训练/test文件、0cedf22d和source_files；bc1098eb实际替换数据。日期9/21正确，9/19初版绝不能并为本边产物。 |

本组11边结论：**8条保留（其中多条收窄/加版本或日期限制），3条删除**。本组两条inferred均应删；全图第三条inferred onboarding→lv2-snapshot由前期组负责，当前登记说明只有先后顺序，同一规则也应删。没有以“推断置信度低”保留一个禁止表达的顺序关系。

### 4.1 可新增、但不得凭时间自动生成的关系

| 候选关系 | 原始依据 | 决定 |
| --- | --- | --- |
| wangly-env→depth-match | R07/08的C7.1入口和完整交付明确在wangly、同科学环境/公共取数；R08有精确运行revision与clean/guard | 可补环境前置关系，但链应定位为wangly环境可用，不把所有传输动作算已发生。 |
| ml-330→szse-model328 | R26第19–38行明确读取9/21 r03冻结mapping与booster，两个SHA固定 | **建议补A类“冻结模型输入合同”边**。这是当前图漏掉的真实依赖。 |
| depth-match→szse-model328 | R26第23–27、63–67行明确depth24及原合同，不能误给旧库唯一来源 | **建议补A类来源输入边**；反向C7.1科学结果仍独立。 |
| cancel-phase→szse-model328 | R26精确列buy24/sell24以及各自参数 | 建议主审计合并前期证据后补A类来源边。 |
| replay→corrected-344-calibration（新链） | R13旧包拒收→R15当前回放来源要求与六核/八组定参，PLAN及scope源码直接实现 | **建议补**，类型写“修正后的回放作为新定参输入合同”，不是“收益变好后再定参”。 |
| grouped-calibration→corrected-344-calibration | 新旧范围/全局核/分组核/九组或八组不同；R15明确保留旧身份独立校验 | 可表示“替换/重新研究”，不能写旧参数被直接复用；若现图只有延续/依赖解除，宁可在新链说明而不强塞错误类型。 |
| corrected-344-calibration→344因子生产 | R15第39–41、123–127行明确未冻结、无可启动正式生产PLAN | **暂不建已交接边**。可以登记待办/阻塞条件，不能把计划中的未来任务画成已交接。 |
| sse-visible-v1/g1→sse-visible-v3 | R16明确不采用旧G1统一三值/仅A幅度，保留部分共享原语、独立540候选身份 | 若拆链，用定义替换与代码复用分别表达，不能把旧G1所有验收沿用成v3验收。 |

## 5. 10月20日之后的版本变化与缺失续段

| 对象 | 旧采集时点仍可保留的结论 | 当前R新增事实 | 日志处理 |
| --- | --- | --- | --- |
| 旧六核/结构v2 | 当时包、参数表与runtime完成、哈希完整 | 当前原生修正回放缺来源绑定，实际正式探针拒绝，新增SQL与因子计算均0。[R13] | 保留历史landed，补“当前生产不准直接复用”后续说明。 |
| 旧328列 | 601日科学验收和评价成立，性能未过门 | 默认回放正确性后续影响256列；旧包不能为新盘口生产背书。[R22][R13] | 保留版本化成果；新增定参/重算链，不追溯删除旧报告。 |
| replay | 10/17单日、10/18三日，10/20整改/小样本 | v4规则认证撤单、v5限价不可成交终端闭合；完整3日及并发/恢复证据 | 补10/20晚和10/21点，点的源SHA必须用新R而不是旧_evidence。 |
| 344定参 | 旧采集中没有此独立范围 | 805652dc冻结344清单；b0b18ae1为最终业务；95f9f8b6记录10/21 00:50:52启动601日六核。结构、冻结与消费者未完成。[R15] | 新链active；记录显示六核于该时点已启动、结构未启动，不能据此认证当前仍活跃。不能标“601日定参完成”或“344因子生产已启动”。 |
| SSE v3 | 旧sse-v2/G1部分实现与速度停止证据 | 352源列/540候选；定义、原生回放/公开视图隔离与单股检查；速度门停，W2全市场未跑。[R16] | 优先补现链延续、改名并记速度停止；若另管理可独立交付目标才拆子链，不写landed生产。 |
| 环境 | 9/4环境计划和账户化代码成立 | 10/20两账户S3FS环境阻塞，默认本地完整venv重建并独立108包/34780文件校验。[R14] | 新增环境修复续段；9/4done不等于10/20仍可用。 |
| 研究日志 | 10/20新栏目实施、内容与交接审计 | 10/21规则、缩放、图例高亮，D已到0910a201 | 独立journal建设维护链，补10/21；避免归进纯发布。 |

## 6. 可直接审查的修订清单

以下是建议的最小内容变更集合，本文件未实施。

| 文件/字段 | 建议变更 | 不得顺手改变的事实 |
| --- | --- | --- |
| `content/chains.json` / wangly-env purpose/fate_note/closes_into | 补“传输实现及canary验收”；移除9/4机制预检报告出口；另连原验收 | 不认定所有结果已同步、不凭PLAN认环境终验全部通过。 |
| 同文件 / doris-efficiency purpose/fate_note/closes_into | 从“主要一份计划”改成公共入口实现+有界实测+规约；改连general-compute-efficiency | 不写全部旧SQL迁移、不写全流程统一36.6%。 |
| 同文件 / depth-match 与新cross-stock-sync | C7.1与C3.3拆开；9/9、9/10、9/18移C3.3；9/8双归属；9/11决定/9/18补记明确 | C7.1 accepted不改dropped；C3.3停止不撤销DM601日结果。 |
| 同文件 / old-factor-bank review与出口 | 加9/8；补9/17评价点或独立评价链；移除9/7 DM出口 | 9/12是启动；原生产guard最终超时保留。 |
| 同文件 / grouped-calibration review/span/fate_note | 加10/12最终runtime交接；补七组601/两组200与旧回放适用性 | 不把9/29文件日期当实际提交日；不混成九组601。 |
| 同文件 / szse-model328 fate_note/closes_into | 旧版本历史验收+record_only性能限制+当前回放需新来源；去10/14SSE错误出口 | 不否认10/18已完成历史601日验收；不把344覆盖旧328。 |
| 同文件 / replay closes_into及点归属 | 去10/18单因子报告出口；接真实回放报告；补新版本日期 | 三日检查不是全历史；快照区间兼容不是精确唯一时点。 |
| 同文件 / sse-v2 | 优先同链补入10/20—21并改善名称，内部阶段区分原生重建、G1/公开口径、v3候选；可独立交付目标需要时才拆子链 | 不把代码入口已实现写成全市场验收，不把候选身份发布当生产面板发布。 |
| 同文件 / report-publish | 纯发布保留；浏览功能、治理规则和journal建设分离 | 实际发布日/报告归档日/研究完成日分别保留。 |
| 同文件 / ml-330 purpose/status/fate | 明确9/20全候选实现与9/21单次因果复算是两个目标；缺全候选运行验收时不能整链done代签 | 未跟踪133候选PLAN单列草稿身份，不用它认证运行。 |
| 同文件 / model-report closes_into | 指到daily9/18，附9/19初发和9/21修订 | 不把9/19初版当330复算产出，不用当前正文代替历史初版。 |
| 同文件 / handoffs | 删除H01/H09/H10；保留8条但加上述限定；补真实模型/四源到328以及新定参输入关系 | 不按先后补边，不把未冻结生产前置写成已交接。 |
| `content/journal/2026-09-04.md` | 同步“传输实现/真实canary” | 不能把别的报告变环境成果。 |
| `content/journal/2026-09-08.md` | 加old-factor-bank实现/F40验证；C7.1/C3.3分开 | 432.50秒仅F40调度验证。 |
| `content/journal/2026-09-17.md` | 依据已发布原报告加实际评价完成及异常说明 | 不宣称原生产guard正常退出；不凭日期推断其他运行。 |
| `content/journal/2026-10-09.md` | Doris改为实现+实测；核包最终封存移到10/10或明确跨午夜 | 10/9开发与估计可以保留。 |
| `content/journal/2026-10-12.md` | 加grouped-calibration最终结构v2/runtime交接点 | 不是本日开始重新估计核尺度。 |
| `content/journal/2026-10-20.md` 与新增10/21 | 分别加正确参数拒绝/344定参/可见v3/环境与journal续段 | 新R和旧_evidence分开采集，任何数字携来源SHA。 |
| `_evidence` 与采集配置 | 主任务统一刷新后重算，记录新snapshot；审计时保持旧文件不动 | 不只更新revision文字却沿用旧计数/旧日卡。 |

## 7. 审阅限制与仍须补核的项目

- 本文件覆盖16条指定链的全部当前日期、11条指定出边与报告出口；不是全部提交逐行审阅。早期链的目标与入边由其他审计分工合并。
- 原始计划中的授权/步骤不是实际执行证明。环境终验、标签功能线上持久化、历史各清理批次等，须以独立原回执补链接；本文件没有为没有读取的回执认证通过。
- 对关键研究结果读取已提交的原结果报告和所附参数身份，未逐字节重新下载服务器全部载荷。论文、交易规则等外部原件不在本次本地证据审计内重做文献核查。
- 9/17旧库实际评价完成由当时公开报告正文及原发布资产支持，研究仓这一时段没有独立同日提交；应据评价RESULT/guard原件补运行SHA和完成时间，而不是虚构9/17研究commit。
- 广义存储链的9月与10月早期候选已定位，未在本分工内逐项复验全部对象删除清单，不能把文件名清单当已确认总回收量。只有上文直接读取原结果的10/14—16批次作出具体结论。
- 截至R所保留的00:50:52启动回执，344六核处于运行中。本文件不把此历史回执称为现在仍活跃的服务器现场，也不推断后来完成；v3同理只报告已保存的停止状态。
- 本次只写此审计文件；未修改链条登记、日卡、源仓、标题；未commit/push，未同步服务器或启动研究计算。

## 7.1 已读关键diff与其实际含义

| 固定commit | 实际改动 | 支持的结论 |
| --- | --- | --- |
| [a96ac595](https://github.com/MengerWen/sirui-quant-research/commit/a96ac59535a0101b476bff66c9828e6a50d2e9e9) | server-env.sh将output/scratch从固定wenjie路径改为HOME相对；并没有强制旧库转到wangly | 账户化实现成立，不能证明H01依赖。 |
| [7df629de](https://github.com/MengerWen/sirui-quant-research/commit/7df629de0c0ae16370a10bb2b5e18e5fe136ba2e) | QueryPlan新增for_research、默认单表并发/范围页/自适应，range producer按plan.tables查询并以Semaphore限制两页 | Doris工作确实已改公共实现，不只是PLAN。 |
| [9e26b6ed](https://github.com/MengerWen/sirui-quant-research/commit/9e26b6ed8b131a9d387fe62078ef8aeae62b6076) | C3.3计划新增“已取消（2026-09-11）”且删除原执行证据 | 决定日期与补记提交9/18分开；删除不是DM结果退役。 |
| [bc1098eb](https://github.com/MengerWen/internship-dashboard/commit/bc1098eb8bc950290a83e37b92ad6da1c730d67d) | README从330映射与旧single-fit源改为328/f97排除/固定预算及未退出估值，另消费r03产物生成器 | 9/21是已有报告数据和会计口径替换，非9/20全候选完整结果签收。 |
| [c9ecdcf2](https://github.com/MengerWen/internship-dashboard/commit/c9ecdcf23e06b2092eb9837e391c6e6b85794f49) | tokens从暗色改纸墨、顶栏126px、圆角2px并更新多页样式 | 版式具体改造成立。 |
| [7896f7d9](https://github.com/MengerWen/internship-dashboard/commit/7896f7d9782ce572cdb13f867733be9c6bd3b75d) | site/index引入tag-model/report-tags、标签条、管理dialog与筛选toolbar | 在站点上新增功能成立；diff未给版式成果→标签研究、标签→模型数据的产物依赖。 |

## 8. 原始证据索引

下表的链接均固定完整SHA，行号针对固定版本。R是研究仓，D是看板仓。精确commit的历史初版另在正文保留；不能把不同快照正文相互覆盖。

| 编号 | 原始文件（固定版本） | 核验行号 |
| --- | --- | --- |
| [R01] | `PLAN/2026-09-04-wangly-environment-bootstrap.md` | 5—43 |
| [R02] | `reports/2026-09/2026-09-04-wangly-result-transfer-acceptance.md` | 3—41 |
| [R03] | `reports/2026-10/2026-10-09-general-compute-efficiency.md` | 3—108 |
| [R04] | `PLAN/2026-09-07-old-factor-bank-implementation-and-300s-gate.md` | 15—369 |
| [R05] | `reports/2026-09/2026-09-10-old-factor-formal-execution.md` | 3—93 |
| [R06] | `reports/2026-09/2026-09-11-old-factor-company-python-runtime.md` | 3—15 |
| [R07] | `PLAN/2026-09-05-C7.1-exact-depth-market-pattern-prescreen.md` | 5—30 |
| [R08] | `reports/2026-09/2026-09-08-depth-match-full-history-completion.md` | 3—118 |
| [R09] | `PLAN/2026-09-08-C3.3-cross-stock-synchronization-prescreen.md` | 1—32 |
| [R10] | `reports/2026-09/2026-09-08-old-factor-repair-validation.md` | 3—51 |
| [R11] | `reports/2026-10/2026-10-10-grouped-kernel-calibration-v1.md` | 1—31 |
| [R12] | `reports/2026-10/2026-10-12-old-factor-recompute-preparation.md` | 3—37 |
| [R13] | `reports/2026-10/2026-10-20-frozen-parameter-replay-compatibility.md` | 3—62 |
| [R14] | `reports/2026-10/2026-10-20-full-recompute-admission.md` | 3—40 |
| [R15] | `reports/2026-10/2026-10-20-corrected-replay-344-recalibration.md` | 3—127 |
| [R16] | `reports/2026-10/2026-10-21-sse-visible-v3-implementation.md` | 3—126 |
| [R17] | `reports/2026-10/2026-10-14-wangly-storage-cleanup.md` | 3—42 |
| [R18] | `reports/2026-10/2026-10-15-wangly-final-artifact-retirement.md` | 3—33 |
| [R19] | `reports/2026-10/2026-10-16-szse-model328-storage-closeout.md` | 3—51 |
| [R20] | `reports/2026-10/2026-10-16-storage-principles-and-certificate-backfill.md` | 3—31 |
| [R21] | `reports/2026-09/2026-09-12-old-factor-full-history-launch.md` | 3—35 |
| [R22] | `reports/2026-10/2026-10-17-szse-replay-rule-verification.md` | 3—88 |
| [R23] | `reports/2026-10/2026-10-18-szse-replay-production-multiday.md` | 3—88 |
| [R24] | `decisions/2026-10-19-replay-core-and-execution-stages.md` | 3—40 |
| [R25] | `reports/2026-10/2026-10-20-replay-and-stages-delivery.md` | 3—40 |
| [R26] | `PLAN/2026-10-12-szse-model328-factor-recompute.md` | 5—107 |
| [R27] | `reports/2026-09/2026-09-29-grouped-calibration-classification-design.md` | 3—51 |
| [R28] | `reports/2026-10/2026-10-09-grouped-calibration-601d-launch.md` | 3—56 |
| [R29] | `reports/2026-10/2026-10-10-grouped-kernel-parameter-table.md` | 3—48 |
| [R30] | `reports/2026-10/2026-10-18-szse-model328-factor-performance.md` | 3—38 |
| [R31] | `reports/2026-09/2026-09-22-sse-replay-implementation.md` | 3—59 |
| [R32] | `reports/2026-09/2026-09-22-sse-cancel-phase-raw-bank-assessment.md` | 3—56 |
| [R33] | `reports/2026-10/2026-10-16-sse-visible-g1-v2.md` | 3—53 |
| [R34] | `PLAN/2026-09-21-causal-single-fit-recompute.md` | 1—9 |
| [D01] | `content/daily/2026-09-16.md` | 15—21 |
| [D02] | `content/daily/2026-10-09.md` | 9—23 |
| [D03] | `direction-approved.md` | 15—35 |
| [D04] | `docs/plans/2026-08-11-research-desk-visual-refresh.md` | 5—85 |
| [D05] | `content/assets/model-report-2026-09-18/README.md` | 3—30 |
| [D06] | `PLAN/2026-10-18-szse-model328-report.md` | 3—39 |
| [R35] | `因子/algobench/src/algobench/ml/open5m_330_candidates.py` | 1—8 |
| [R36] | `scripts/run_intraday_ml_open5m_330_study.py` | 1—10 |

[R01]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/PLAN/2026-09-04-wangly-environment-bootstrap.md#L5-L43
[R02]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-09/2026-09-04-wangly-result-transfer-acceptance.md#L3-L41
[R03]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-10/2026-10-09-general-compute-efficiency.md#L3-L108
[R04]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/PLAN/2026-09-07-old-factor-bank-implementation-and-300s-gate.md#L15-L369
[R05]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-09/2026-09-10-old-factor-formal-execution.md#L3-L93
[R06]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-09/2026-09-11-old-factor-company-python-runtime.md#L3-L15
[R07]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/PLAN/2026-09-05-C7.1-exact-depth-market-pattern-prescreen.md#L5-L30
[R08]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-09/2026-09-08-depth-match-full-history-completion.md#L3-L118
[R09]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/PLAN/2026-09-08-C3.3-cross-stock-synchronization-prescreen.md#L1-L32
[R10]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-09/2026-09-08-old-factor-repair-validation.md#L3-L51
[R11]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-10/2026-10-10-grouped-kernel-calibration-v1.md#L1-L31
[R12]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-10/2026-10-12-old-factor-recompute-preparation.md#L3-L37
[R13]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-10/2026-10-20-frozen-parameter-replay-compatibility.md#L3-L62
[R14]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-10/2026-10-20-full-recompute-admission.md#L3-L40
[R15]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-10/2026-10-20-corrected-replay-344-recalibration.md#L3-L127
[R16]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-10/2026-10-21-sse-visible-v3-implementation.md#L3-L126
[R17]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-10/2026-10-14-wangly-storage-cleanup.md#L3-L42
[R18]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-10/2026-10-15-wangly-final-artifact-retirement.md#L3-L33
[R19]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-10/2026-10-16-szse-model328-storage-closeout.md#L3-L51
[R20]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-10/2026-10-16-storage-principles-and-certificate-backfill.md#L3-L31
[R21]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-09/2026-09-12-old-factor-full-history-launch.md#L3-L35
[R22]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-10/2026-10-17-szse-replay-rule-verification.md#L3-L88
[R23]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-10/2026-10-18-szse-replay-production-multiday.md#L3-L88
[R24]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/decisions/2026-10-19-replay-core-and-execution-stages.md#L3-L40
[R25]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-10/2026-10-20-replay-and-stages-delivery.md#L3-L40
[R26]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/PLAN/2026-10-12-szse-model328-factor-recompute.md#L5-L107
[R27]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-09/2026-09-29-grouped-calibration-classification-design.md#L3-L51
[R28]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-10/2026-10-09-grouped-calibration-601d-launch.md#L3-L56
[R29]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-10/2026-10-10-grouped-kernel-parameter-table.md#L3-L48
[R30]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-10/2026-10-18-szse-model328-factor-performance.md#L3-L38
[R31]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-09/2026-09-22-sse-replay-implementation.md#L3-L59
[R32]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-09/2026-09-22-sse-cancel-phase-raw-bank-assessment.md#L3-L56
[R33]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/reports/2026-10/2026-10-16-sse-visible-g1-v2.md#L3-L53
[R34]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/PLAN/2026-09-21-causal-single-fit-recompute.md#L1-L9
[D01]: https://github.com/MengerWen/internship-dashboard/blob/0910a201154aa02b6889ad77899943a2eb656d1c/content/daily/2026-09-16.md#L15-L21
[D02]: https://github.com/MengerWen/internship-dashboard/blob/0910a201154aa02b6889ad77899943a2eb656d1c/content/daily/2026-10-09.md#L9-L23
[D03]: https://github.com/MengerWen/internship-dashboard/blob/0910a201154aa02b6889ad77899943a2eb656d1c/direction-approved.md#L15-L35
[D04]: https://github.com/MengerWen/internship-dashboard/blob/0910a201154aa02b6889ad77899943a2eb656d1c/docs/plans/2026-08-11-research-desk-visual-refresh.md#L5-L85
[D05]: https://github.com/MengerWen/internship-dashboard/blob/0910a201154aa02b6889ad77899943a2eb656d1c/content/assets/model-report-2026-09-18/README.md#L3-L30
[D06]: https://github.com/MengerWen/internship-dashboard/blob/0910a201154aa02b6889ad77899943a2eb656d1c/PLAN/2026-10-18-szse-model328-report.md#L3-L39

[R35]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/%E5%9B%A0%E5%AD%90/algobench/src/algobench/ml/open5m_330_candidates.py#L1-L8

[R36]: https://github.com/MengerWen/sirui-quant-research/blob/9d3e0a37ca0ecff805a0707b14d2b70f7cc18be6/scripts/run_intraday_ml_open5m_330_study.py#L1-L10
