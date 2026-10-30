# 2026-10-25 沪市第六核方法选择与 f26 观察资格

## 结论

**建议采用 B：按每张有公开挂出、且初始主动成交量为零的订单，采一次首个公开动作前对手 BBO 的正向 tick gap，独立估计 `theta_marketability_ticks`。** 股票日、日期、全期三级正中位数与 `m/ln(2)` 沿用最近六核的估计形式；样本总体和每单一次的权重作为沪市新合同明确登记。A（绑定本包 `theta_bbo_ticks`）保留为有界验收中的方法对照，不作为科学主方案。C（旧单 at-new gap）保留为响应位置的诊断分布；目前不拆成两套尺度，也不把 M 改成成交概率模型。

理由是项目要测量公开行为，M 的原始定义又明确锚在订单入场前。B 的样本恰是当前 M 真正需要软衰减的订单分支。A 的参数来自“后来存在撤重挂关系、附近有数量相似订单”的候选边，并按候选边重复计数；这与每张订单的入场位置并非同一总体。绑定没有数学错误，但缺少本任务测量目标所需要的总体对应关系。深市两个冻结值相等、既有批准或实现方便，都不能补上这项依据。

这是一项**方法推荐，不是实测最优结论**。当前固定提交仍实施 A，本报告没有切换代码或参数。本次只读原始定义、固定提交源码和已有签收材料；没有取数、回放、定参、因子计算或服务器操作，没有获得 B 的沪市数值、支持率或性能结果。正式沪市 601 日尚未开始，适合现在明确合同。后续先完成用户要求的提速验收，再按批准的方法开展研究与真实验收。

## 证据版本与范围

全部算法判断固定到研究仓库提交 [`1c9a095c813dfecaeb4b356d9f020445eea718b0`](https://github.com/MengerWen/sirui-quant-research/tree/1c9a095c813dfecaeb4b356d9f020445eea718b0)。审阅中工作区 HEAD 已前进，且若干文件有其他任务改动，因此源码均通过 `git show <固定提交>:<路径>` 读取，不用工作区新内容替代这份结论。文末记录固定提交原字节 SHA-256 和审阅时本地文件 SHA-256。

最近的比较基准是深市 601 日六核 v7，加 10 月 24 日 F40 定参。原始定义只用于辨认研究目标，不把 7 月旧算法当作现行标准。六核冻结包文件 SHA 为 `3a34afb0fc9303580e6b1a915539552093c316925e202f90b533b0ebe508dbac`；其中 BBO 和 marketability 两字段均为 `2.8853900817779268`。这是两项已有估计的数值事实，不证明两者应当绑定。[六核签收](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/reports/2026-10/2026-10-22-kernel-601-v7-complete.md#L69)，[冻结包](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/reports/2026-10/2026-10-22-kernel-601-v7-complete-evidence/formal-r01/FROZEN_KERNEL_SCALE_BUNDLE.json)，[F40 签收](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/reports/2026-10/2026-10-24-f40-full-period-completion.md#L1)。

## 1. 先决定 M 要测什么

项目总目标是依据 L2 可观察行为定义算法单代理，用订单软占比刻画关注度，再检验股票因子的样本外预测能力。它不识别真实账户身份，也不逐笔确认真实生成机制。[CONTEXT](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/CONTEXT.md#L1)。最初因子定义把问题表述为订单是否细致管理执行成本、排队、盘口变化和成交节奏；并明确 M 在“订单进入前，根据盘口”定义，离对手最优价越远，值越接近零，实际成交速度另由 X 表达。[最初研究目标](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/PLAN/最初构建因子.md#L22)，[M 与 X 原始定义](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/PLAN/最初构建因子.md#L723)。

由此，本任务最适合把 M 解释为：**公开报价或已证实初始执行在可执行前沿上的主动位置坐标**。M 越大，公开行为越靠近或已经到达立即执行；`1−M` 表示该坐标上的被动程度。它是行为强度的公共积木，不是“这张订单由算法生成”的概率，也不是隐藏原始愿付价、真实委托类型或未来一定成交的概率。

“离对手报价越近通常越容易成交”是该坐标的经济直觉，不能把指数值直接读成校准过的成交概率。真实成交还受队列、数量、后续市场路径和观察时长影响；同样的 gap 不保证相同成交率。F（拟合成交概率）需要另定预测终点、删失处理、信息集及训练验证协议，会更换被测对象，不能作为本轮给第六字段找正样本的办法。

最初说明书只适用于深市；沪市采用公开行为定义，是在可辨认的公开事实范围内重建该测量坐标，不能借原始深市委托类型推断隐藏意图。当前沪市适配层保留 `has_add`、公开价格和初始成交量，把 public 输入的 `ord_type` 统一设为 L；这里的 L 是输入表示，不是原始类型证据。[公开事实](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/sse_public_adapter.py#L16)，[输入投影](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/sse_visible_input.py#L68)。

## 2. 推荐 B 的精确定义

本报告以 `E0` 表示 `visible_initial_quantity`，即公开初始主动成交股数；它**不是**最初 PLAN §3.3 的累计成交比例 `E_i`，也不是股票日结束时的 `traded_qty`。初始成交来自重建后的初始撮合段，公开挂出后的被动成交不改变 E0。[字段来源](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/sse_public_adapter.py#L24)。

本报告下文的“入场”指首个公开动作这一可观察时间代理，不声称已恢复不可见的原始申报时点。对证据窗口内每张合格公开订单 i，设方向 `z=+1`（买）、`z=−1`（卖），公开挂出价为 P，首个公开动作前对手最优价为 O，证券日真实报价单位为 u：

```text
has_add = true 且 E0 = 0：
    d_i = max[z_i × (O_i(t_i−) − P_i) / u_i, 0]
    M_i = exp(−d_i / theta_marketability_ticks)

E0 > 0 或纯执行、无公开挂出：
    M_i = 1，均不进入该软分支尺度的 gap 样本
```

现行 public M 已作相同覆盖：有挂出时按对手 BBO 算指数，无挂出为 1；v4/v5 的 `visible_initial_quantity>0` 再置 1。[公开 M 实现](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/formal_factor_input.py#L109)。推荐不更改这些资格，只替换软分支的尺度来源。

B 的样本为全部符合上述软分支资格的订单，每 `(date, code, order_id)` 一次。保留当前 point-in-time 市场源总体、日期与 `[09:30,09:35)` 逻辑窗口，买卖合池生成一个尺度，同时分侧审计。按订单等权，不按数量、金额、候选度数或被多少消费者调用加权；这样所有 count/qty/amount 因子共用一个可比较的位置坐标，各自的业务权重留在聚合层。这里选择的是典型股票日内典型公开软分支订单的位置，不是全市场按成交量加权的典型交易。

这项来源无需附加撤重挂的 3.11 秒完整候选窗或数量相似门：那些条件定义配对样本，不定义一张订单的入场位置。09:35 前已公开挂出的 E0=0 订单，即使以后未撤、未成交或没有替代单，也有可观测入场 gap。各因子自己的后续观察窗与可判定合同仍分别执行，不能为了定标方便把它们统一前移到本样本上。

### 没有参数循环，也不能暗含未来筛选

B 的样本资格由公开挂出、初始段和动作前盘口决定，不由当前 θ、核分数、matching 胜负或因子表现决定，所以没有“先用 θ 挑样本，再用样本估 θ”的循环。`d>0` 是预声明软衰减支持的选择；它不依赖 θ。

`has_add=true、E0=0` 在该订单公开挂出时即可从已发生的初始段确认，后续是否被动成交不应回改其资格。实现必须使用已认证的初始段端点和动作前 pre-state，不能用全日成交量为零、最后是否撤单、未来是否存活、未来 matching 或未来收益来筛样本；右边界未闭合且尚无挂出的初始段不能冒充 E0=0 公开订单。重建字段若实际上不能在该时点证明这些事实，应保留不可定义并停止相应样本，而不是宣称因果已经满足。

这仍有明确的观测条件：尺度只代表“确有公开挂出且无初始主动成交”的软分支，不代表所有投资者原始意图。公开显示选择不是对隐藏总体无偏的保证，却正好对应本项目公开行为坐标的适用域。

## 3. 六种方法的测量取舍

| 方案 | 实际估计对象 | 对本任务的判断 |
| --- | --- | --- |
| A 同包绑定 θ_bbo | 普通候选边中新单自身入场到对手 BBO 的距离，保留结构条件与逐边次数 | 可复现、可作对照；不足以成为所有公开订单 M 的默认尺度 |
| B 公开挂出且 E0=0、每单一次 | 当前 M 软分支在自身入场时的报价位置 | **主推荐**；明确改变深市候选边来源，不冒称逐项复制深市样本合同 |
| C 旧单价格 at-new 正 gap、逐候选边 | 在响应发生时旧报价距当时前沿的差距 | 对响应有意义；受存活、后续撤单、市场移动和候选度数条件影响，不适合作为公共 M 的唯一基准 |
| D 全部 public 订单几何 gap | 包含 E0>0 挂余、甚至纯执行虚拟价格的混合距离 | E0>0 实际 M 已固定 1，正几何 gap 并非它的软衰减暴露；混入会让与 θ 无关的分支决定 θ |
| E 拆入场尺度与响应尺度 | 两个不同的统计分布各自归一 | 可作为未来新假设；当前目标需要公共主动位置坐标，尚无证据要求分裂 |
| F 用数据拟合未来成交概率 | 指定终点与信息集下的结果概率 | 另一个研究目标，本轮不采用 |

B 优于 A 的依据是总体与测量对象相符，不是 B 必定产生更好的 IC。候选边门会偏向撤改活跃、数量相似或多候选的订单；同一新单连接十个旧单就可能贡献十次距离，而没有候选的公开订单不贡献。三级中位数只削弱股票间及日期间的数量支配，不消除股票日内部这类重复权重。即使 B 与 A 最后数值恰相等，也仍需按各自真实来源登记。

C 对 `1−M_old_at_new` 的解释最直接，但“直接对应某个响应公式”不等于最适合所有消费者。它条件于订单后来出现撤单及附近替代候选，不能解释为无条件入场位置。响应发生前的信息可以合法用于当时的响应分数；本报告反对的是借该条件分布给所有入场坐标定尺，并非断言响应 at-new 本身偷看未来。

E 并非必然错误。目前先用一把报价位置尺，对自身入场位置和响应时的旧报价反事实位置作同函数映射，更符合 M 的公共积木定位。对响应计算，旧、新报价应在同一个新单入场前 BBO 下比较，以免把市场自身移动误写成订单动作；共享 θ 则让增量有统一尺度。用入场样本定尺不意味着旧单 at-new gap 与入场 gap 同分布，也不保证响应增量的中位数为某个常数。若后续研究明确要测“相对于典型响应的异常强度”，再预声明 E，不能仅因两种分布不同就自动增加一个参数。

## 4. 为什么深市 special 正支持不能照搬

最新深市定标规定：全部结构合格且未评分、未 matching 的候选边；时间/事件/数量用全候选，价格/BBO 用 ordinary lane，第六核用 special/marketable lane；六项分别取股票日、日期、全期正中位数。源码明确 `theta_marketability_ticks` 来源是 `special_marketability_tick_gap`。[现行来源合同](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/scripts/calibrate_kernel_scales.py#L97)，[三级规则](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/PLAN/2026-08-27-2024-2026Q2因子定标与3.11秒硬门实施计划.md#L92)。

special lane 不只含立即可成交订单，还含旧新类型不同、新单 U 等。因而某些非 M 特殊类型候选可以离对手 BBO 有正 gap；M 自身的 gap 记零。ordinary 则要求旧新均 L、对手/有效价可观测且新单不立即可成交。[lane 定义](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/formal_pairing.py#L2912)，[special gap](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/formal_pairing.py#L3231)。

沪市 public 全 L 后，类型不同与 U 分支消失，special 剩下几何上立即可成交的新单，其有向 adverse gap 恒为零。这是表示与候选定义合成后的识别退化，不是已证明“沪市没有市场性差异”，更不是应把零填成正尺度的理由。E0>0 的行为证书虽然让消费者 M=1，也不能凭空恢复原始类型的 special 正样本。

同样，在全 L、同一候选库存与有效价格合同下，所有新单入场正几何 gap 都落入 ordinary，其绝对 BBO 距离恰等于该正 gap。因此“把所有候选的新单正 gap 再估一次”会代数上重现 θ_bbo。**B 不等于这项恒等改名**：它排除 E0>0、按订单去重并纳入没有撤重挂候选的公开软分支订单，故没有与 θ_bbo 必等的定理。

## 5. 零、缺失和全期归约必须写进合同

以下互斥计数按公开订单身份形成，先保留源总体，再作 eligibility。数据错误不得通过计入普通 missing 后静默消失。

| 类别 | 处理及统计 |
| --- | --- |
| 无公开挂出、仅初始执行 | 记录 `pure_execution_count`；M=1；不进入 gap 样本，不与 E0>0 挂余重复计数 |
| 有公开挂出且 E0>0 | 记录 `displayed_initial_execution_count`；M=1；不进入 gap 样本 |
| 有公开挂出且 E0=0、有效对手 BBO、d>0 | 记录正支持数，每单一次进入中位数 |
| 同上、d=0 | 记录零 gap 数，M=1；不进入正中位数，不当缺失 |
| 有公开挂出且 E0=0、合法缺少对手 BBO | 记录盘口不可定义数及市场状态；该 M 缺失，不造零或默认 gap |
| 非法侧别、非正价格/报价单位、负初始量、身份重复、无法认证的 pre-state 等 | 单列字段/质量错误，按原数据契约拒绝或阻断；不能算作合法单侧盘口缺失 |

至少核对 `E0=0 有挂出总数 = 正gap + 零gap + 合法盘口不可定义 + 该组非法/质量项`，再核对它与两组已排除订单构成公开输入的完整分解。买卖、板块、日期分别出审计计数；不因为买卖分布不同就未经研究另估两套参数。

价格 gap 按证券日 `raw_units_per_tick` 换算，不能把字段名 `*_tick` 当作已经处于真实 tick 的证明；也不能为所有股票硬编码 100。[现行 raw-unit 转换](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/formal_pairing.py#L2920)。零价差在已认证合法盘口中不造成除零，因为 B 的分母是报价单位 u，并非 spread。合法锁盘在有有效对手报价时仍按同一有向 gap 计算；是否允许该状态，由交易阶段及回放合同判断，不能把所有零价差一律判错，也不能给连续竞价异常交叉簿开例外。涨跌停造成的合法单侧盘口应保留：E0=0 缺对手报价时 M 不可定义；已证实初始执行则可凭行为证书 M=1，不依赖补造缺失盘口。不得因涨跌停、ST 或低流动性临时新增总体过滤。

对每个股票日 s,d，只对有限正 d 取中位数 `m_sd`；没有正值时，该参数的 `m_sd` 缺失，零支持与缺失原因照记。每日期对已定义股票日的 `m_sd` 取中位数 `m_d`；当日全部股票日均无正支持时，该日期 `m_d` 缺失。全期对已定义 `m_d` 取中位数 m，再令 θ=m/ln2。

**合法无正支持不等于整个任务失败。** 当前三级归约允许某股票日或某日期对此参数未定义；只有全期没有任何已定义日期才因不能估计正尺度而失败。601 日期必须完整登记并完成应做检查，不等于每项参数在每个日期都必须有正支持。不得删去无支持日期后声称601日全部可定义，也不得填0/1、跨市场借值或用 θ_bbo 补齐。[股票日统计](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/scripts/calibrate_kernel_scales.py#L546)，[日期覆盖及归约](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/scripts/calibrate_kernel_scales.py#L602)。

这项允许缺失的合同也有边界：若大量股票日没有有效盘口，或者支持仅来自极少日期，数学上可归约不等于科学上已充分验收。应先检查缺失来源和代表性，预声明需要的支持披露与审阅规则；本报告不凭空规定最少订单/日期阈值，也不将数量充足当成无选择偏差证明。

## 6. 中位数半衰点是一项建模约定

正样本中位数不需要指定 gap 的参数分布，但 `exp(−d/θ)`、p=1、典型正距离处权重0.5、三级顺序、零值不入定尺及买卖合池，都是研究者选择。它们既不是非参数估计的必然结论，也不是能从业务目标唯一推导的真理。

三级中位数强调典型股票日和典型日期，避免活跃股票仅凭订单数量支配尺度；它并不等于所有订单的 pooled 中位数。`K(m)=0.5` 只在全期三级中位距离 m 上成立，不保证全市场一半订单的 M 大于0.5，也不保证每股每天恰好一半。排除零值是为了估计“离开完全可执行边界后如何衰减”，并非认定零值没有经济意义。B 沿用这组约定，有利于保持现行六核的尺度解释；其合理性仍应通过无收益的支持、稳定性和消费者检查评估。

## 7. 只换第六核时，哪些实际依赖需要重做

前提是其余五核、public 输入定义、候选门、报价单位、回放版本和结构算法均保持固定。不能以 bundle 身份改变为由，把数值无关的阶段一概重算。

| 对象 | 处理结论与来源 |
| --- | --- |
| θ_marketability | 必须按 B 独立采样、归约并发布新来源合同；保留正/零/缺失及全期支持身份 |
| θ_bbo 及另外四核 | 不因 B 更换而重估；当前五项仍按既有候选源统计。若实现改动污染候选库存，则另作影响判断 |
| `lambda42` 的 px、act 两版 | **两版都需重采 `lambda42.best_R` 并归约**。响应幅度先用 θ_mkt，随后形成正候选及每锚点最佳值，再取正分布p05；支持身份与所选最大值都可能变化。不能只缩放旧lambda，也不能因act有额外覆盖就假定px无影响。[双版本收集](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/formal_sse_calibration.py#L159)，[p05归约](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/formal_calibration_statistics.py#L747) |
| F16 priority scales、F31 bottleneck | 在上述前提下无须因 θ_mkt 重采：源是 local-best pair 边及盘口几何；普通边不读取该 θ，public L/L special 为 gap0且价分量1；residual_no_price 路径更直接去掉价格项。先用支持数组/身份证明复用，不强行重跑。[边分量](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/formal_pairing.py#L2276)，[结构源](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/formal_structural_calibration.py#L1365) |
| F40 episode/search/price gates、lambda40、theta40_L | 无须因 θ_mkt 重采。F40独立从成交episode与后继订单生成候选；W消费wall/event/price/qty四核，不消费θ_mkt。匹配依赖lambda40和W，其链长再决定长度尺度；不能把其他撤重挂链的M消费者误算成F40定参依赖。[W公式](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/formal_structural_calibration.py#L696)，[独立候选](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/formal_structural_calibration.py#L720) |
| depth、P03 depletion、RV等结构支持 | 在只有第六字段改变的前提下无新增θ_mkt数值依赖；保留原支持及回放身份，作显式兼容绑定，不宣称所有结构组都重估。[收集闭包](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/formal_structural_calibration.py#L1846) |
| 订单M、near-touch被动项、链节点/升级/切换、x06 context及其投影 | θ_mkt数值消费者；未来正式因子计算必须读取新包，重建相应投影与缓存。当前尚无正式沪市因子，不能称已重算或宣称需要重跑全库历史 |
| 通用response、BBO response、21-template response bank | 更新动作与缓存身份，并验证所有实际分支用同一新θ和单位；bank的参数影响不等于它有独立lambda42定参组 |
| bundle、runtime、manifest、兼容证据 | 移除“θ_mkt必须等于本包θ_bbo”的验证约束；以新来源/样本/估计身份替代。对复用的数值无关组登记真实来源与兼容证明，不能伪造其新跑记录 |

固定提交的 `collect_structural` 仍显式拒绝两字段不相等，这是实施 B 必须修改的合同点。[绑定限制](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/formal_sse_calibration.py#L194)。当前 special 候选价分量内部仍用 θ=1；在沪市全 L、special gap0的限定下，它不构成此次第六核变化的数值传导，但应如实登记，不能称所有候选价分量都动态使用包内 θ。[候选 special 分量](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/formal_pairing.py#L3007)。

本固定提交已经把 response bank 的 θ_mkt、价格尺度、报价元数据纳入缓存键，并向动作构建器传递 θ_mkt 与 raw单位。[实际接线](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/formal_scorers.py#L741)。应从这份源码验证现状，不能沿用本地未提交旧评审中“bank始终固定常量”的结论。保留的默认常量本身不证明正式路径未传参；必须沿调用链核对。该接线是否经过本次真实沪市数据验收，本报告未验证。

## 8. 不靠正式601日收益或IC，怎样比较方法

方法比较应先检验被测对象与实现合同，避免把尺度来源变成按收益调参。本轮不运行，后续可按以下顺序做有界验收：

1. **人工已知答案。** 买卖镜像、0/1/2tick、E0=0/E0>0挂余/纯执行、缺对手报价、合法单侧涨跌停、证券日不同u；验证资格、单位、缺失、单调方向及M=1证书。给相同订单复制候选边：B的样本和θ必须不变。
2. **样本与总体对照。** 在已授权少量普通/压力股票日，列B六类计数、去重身份、买卖和状态分布；并列A候选度数权重与B每单权重、C旧单at-new gap。比较不同方法造成的差异，不把差异本身判为错误。
3. **有限支持与稳定性。** 披露股票日/日期支持率、正gap分位数、极端日期、买卖及板块差异，检查正支持是否仅来自少量状态；日期或股票日分块复核/重抽样只评估估计波动，不使用收益决定取舍。不得先看结果再隐去合法缺失或新增过滤。
4. **真实消费者接线。** 用与旧值明显不同的θ哨兵，穿过M、`1−M`、old_at_new增量、px/act、context、链和response bank；核对缓存身份及向量/参考一致。M对θ增大而增大，但`1−M_old`会减小，链内增量及max选择不必对θ单调，不能按一个笼统方向签收。
5. **依赖与性能。** 两版lambda42重采；F16/F31/F40等复用组核对支持数组、候选身份与数值闭包。B采样可在既有回放的订单投影上按股日线性扫描，无需另建候选边库存；这只是实现复杂度判断，实际CPU、IO、端到端耗时与16核利用率必须另测，不能从源码推出提速已通过。

正式因子收益/IC仍是项目最终预测能力评价，但不是本轮为一个公共报价位置尺挑定义的前置条件。B若支持失败或实现不能遵守公开因果合同，应先查明测量范围和数据证据；不能悄悄退回绑定并把它称为B。

## 9. f26：提速完成后研究怎样保留已可判定的订单

用户已明确先完成当前定参代码优化，再开展 f26 研究。本节只固定研究目标和优先次序，没有实施新规则或运行诊断。第六核的样本选择与 f26 的尾部观察规则是两个问题：固定版本的主动簇连接使用 wall/event 核，f26 评分使用簇长、时间质量、数量稳定和深度消耗，并不直接读取 theta_marketability。不能用更换第六核代替尾部问题的解决。[主动簇构建](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/formal_chains.py#L386)，[f26/f27评分](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/formal_scorers.py#L1260)。

### 研究目标：证明哪些内容仍未知，而非把等待时间本身当目的

原始 §8.5 给足观察时间，是为了防止把“尚未看到后续动作”当成有效零分；它还要求不可观察状态保留，并报告订单数、数量和金额覆盖。这个原则应保留。当前实现却为整个簇的成员统一分配簇分数，再把整组最后主动成交时间作为观察锚点；即使早期已有正证据，后继连接也能把所有成员一并推到尾部之外。一般删失概念说明结果没有完整观察，不代表此前已发生的事实消失。[原始观察目的](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/PLAN/最初构建因子.md#L2339)，[锚点投射](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/formal_scorers.py#L3027)，[NIST删失说明](https://www.itl.nist.gov/div898/handbook/apr/section1/apr131.htm)。

不过，“有正证据”不保证“当前整簇分数已经固定”。后来的成员会改变数量稳定性、簇长、时间质量和累计深度消耗，部分项可能升、部分可能降。因此，不能把未结束组的当前得分当作最终得分，也不能未经证明称它为最终分数下界。研究应区分以下三类。

| 内容 | 研究与验收重点 |
| --- | --- |
| 已可确定的零分 | 检查正常交易机制和已闭合初始撮合证书，能否证明某些订单不会成为正式主动成交节点。例如无初始主动执行的公开被动挂单，若合同能排除其今后成为主动节点，就无需再用等待期确认一个已知的零。这是待证明、待验收的资格分支，不能只凭字段当前为0就采用。 |
| 已完整结束的组 | 优先研究窗口内已有的闭合事实，避免已经知道组结束后仍机械等足整段H。应同时证明组成员不再延伸、成员所需执行事实已完整、评分输入在截止时点可得。 |
| 未结束组中的局部正证据 | 如果完整组仍不可判定，再研究固定局部时域或截至时点的证据定义，保留早期订单已有的信息。该定义须有新的因子身份，不能把截断簇静默当成原完整簇。 |

### 优先研究可证明的闭合，再研究局部证据定义

固定代码按同侧首笔主动成交顺序排列节点，只连接相邻节点；连接要求时间门和事件门同时满足。由这个结构出发，有三项值得先核验的闭合候选条件：已观察到下一同侧节点且明确断边；完整时间轴已使后续节点不可能通过时间门；完整消息轴已使后续节点不可能通过事件门。双门为AND时，只要一道门已能证明未来相邻节点不能连接，就可能无须继续等另一道门。

上述是研究候选，尚未成为本项目的闭合证明。必须核实源消息及节点提取完整性、顺序和时间戳合同、初始执行段闭合、跨节点执行是否交叠等条件；不能仅因已经看到某条新消息就认为组已闭合。还应特别核对：连接使用相邻节点的首笔主动成交端点，现有观察锚点却取组内最后主动成交时间。两者是否产生额外等待，需要依据当前端点与执行完整性合同判断。[连接端点与双门](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/formal_chains.py#L488)，[组统计与末端](https://github.com/MengerWen/sirui-quant-research/blob/1c9a095c813dfecaeb4b356d9f020445eea718b0/因子/algobench/src/algobench/formal_chains.py#L558)。

如果这些证明能恢复部分组的完整评分，就先作最小的观察资格扩展，而不急于更换整套 f26 评分公式。剩余未闭合组，再比较局部邻接证据、固定订单时点的活动密度、截至09:35的公开前缀等定义。局部定义需要明确其对应订单、时间范围、数量权重和分母，并检查尾端是否仍有不必要的证据损失；软化边权后若仍使用整组末端锚点，原问题可能仍在。

### 后续研究的验收对象

提速验收完成后，沿用已有有界样本和真实尾部案例，按同一订单轴核对：哪些订单恢复为可判定、恢复的是零还是正贡献、count/qty/amount分子分母怎样变化、是否由少数组影响大量订单、各类观察不足是否仍正确保留。共用主动簇的f27同步核对。先比较当前规则与可证明的资格扩展；只有后者不足以满足测量目标时，再比较局部证据新定义。

原计划的时间核与消息核各±5%、双门联合边界、真实消息轴对照、极值与覆盖检查可复用，但判断标准应增加“恢复的订单是否有充分窗口内证据”，不能只按纳入数量增多或相关系数更高判优。完整输入或经认证等价的节点只构建一次，后续对照复用；当前省略逐笔子事件的定参快投影不能直接供主动簇诊断使用。

所有方案都在09:35前的证据内判断，不读取其后数据补当前分数。若更换f26定义，应在沪深同口径的有界样本上比较，保留旧定义身份和参考结果；本轮不改既有正式深市面板。f26研究仍不以单独敏感性预警阻断整套参数签收，具体用途及共享消费者的验收分别处理。

## 10. 证据边界与待决事项

这份推荐建立在原始M入场语义、当前public分支资格及实际调用链上；它没有证明真实参与者意图，也没有证明B的数值稳定性、收益优势或完整601日运行可承受。当前最有价值的下一步是冻结B的总体、唯一订单身份、互斥计数与缺失合同，把双版lambda42和兼容复用边界接好，再按用户顺序验收。

若业务目标日后改为“相对于典型响应行为的异常幅度”，C/E可以重新成为主方案；若改为预测成交概率，F需要独立协议。那是目标变更，不应以本轮保留或替换第六尺度的便利性代替研究判断。

## 附录：原始模型记录与文件身份

开始时读取本子代理正式会话日志中的 `turn_context`：`turn_id=01a171b4-0930-7442-9701-22f1f4444a85`，`model=gpt-6.1-sol`，`effort=xhigh`，collaboration settings 同为 `gpt-6.1-sol/xhigh`。日志路径为 `C:/Users/19927/.codex/sessions/2026/10/25/rollout-2026-10-25T14-16-26-01a171b4-0822-7c72-9135-f8d2409fb54f.jsonl`。核对的是本轮实际记录，不以默认配置代替。结束核对及文件身份附在下方。




结束时重读同一原始日志，1条 `turn_context` 均为 `gpt-6.1-sol / xhigh`，模型核对通过。以下为本次实际读取的原字节哈希；`different`表示本地文件已有其他改动，不是本报告使用的算法版本。

| 源文件 | 固定提交内容 SHA-256 | 审阅结束时本地文件 SHA-256 | 原字节比较 |
| --- | --- | --- | --- |
| `reports/2026-10/2026-10-22-kernel-601-v7-complete.md` | `21ed7b3a90598a25738473086cc59113f5431d276955dbda1946638d7223c1d1` | `21ed7b3a90598a25738473086cc59113f5431d276955dbda1946638d7223c1d1` | same |
| `reports/2026-10/2026-10-22-kernel-601-v7-complete-evidence/formal-r01/FROZEN_KERNEL_SCALE_BUNDLE.json` | `3a34afb0fc9303580e6b1a915539552093c316925e202f90b533b0ebe508dbac` | `3a34afb0fc9303580e6b1a915539552093c316925e202f90b533b0ebe508dbac` | same |
| `reports/2026-10/2026-10-24-f40-full-period-completion.md` | `a5444c5b398730580485e2202145f663a49fdc77b05f9efeddee43582182488a` | `a5444c5b398730580485e2202145f663a49fdc77b05f9efeddee43582182488a` | same |
| `CONTEXT.md` | `f31b45155ac1a43f3a489ff21ad4699769abb1820bb697233cda29416661d330` | `f31b45155ac1a43f3a489ff21ad4699769abb1820bb697233cda29416661d330` | same |
| `PLAN/最初构建因子.md` | `823cfcc142f0ac947a83dbdc2ed0da0e17457e78f58f12bcf42c6d33b1137c05` | `823cfcc142f0ac947a83dbdc2ed0da0e17457e78f58f12bcf42c6d33b1137c05` | same |
| `因子/algobench/src/algobench/sse_public_adapter.py` | `43ccce2f02d0b9eccad0decf2d13236ee866b68c2a2eb5649446c6a6eba54369` | `43ccce2f02d0b9eccad0decf2d13236ee866b68c2a2eb5649446c6a6eba54369` | same |
| `因子/algobench/src/algobench/sse_visible_input.py` | `209837007b88a67cf776b8316493f25d57231fe96833a27e716e71bc143235c9` | `209837007b88a67cf776b8316493f25d57231fe96833a27e716e71bc143235c9` | same |
| `因子/algobench/src/algobench/formal_factor_input.py` | `593aaa97fec1ef3c9c0cbb07778a2912aeb127c68a3b694f845f6dae51dadfaa` | `593aaa97fec1ef3c9c0cbb07778a2912aeb127c68a3b694f845f6dae51dadfaa` | same |
| `scripts/calibrate_kernel_scales.py` | `9baa0f132e65d33735dad085d702b7b407975dedc4ec27f34089633d4413092b` | `9baa0f132e65d33735dad085d702b7b407975dedc4ec27f34089633d4413092b` | same |
| `PLAN/2026-08-27-2024-2026Q2因子定标与3.11秒硬门实施计划.md` | `f3d0728628dea4c6084d7bff71618ee60122cb8e111ee770880ac2125bc62b9f` | `f3d0728628dea4c6084d7bff71618ee60122cb8e111ee770880ac2125bc62b9f` | same |
| `因子/algobench/src/algobench/formal_pairing.py` | `34236c85d10b9bd85751421f68830e87602adc6866f152cc65083b43fea4cba8` | `34236c85d10b9bd85751421f68830e87602adc6866f152cc65083b43fea4cba8` | same |
| `因子/algobench/src/algobench/formal_sse_calibration.py` | `d8cd46de7d4c732da6a31b785e311f2cffc6b06e8c2f5ba2a8cd1e1e80273c55` | `d8cd46de7d4c732da6a31b785e311f2cffc6b06e8c2f5ba2a8cd1e1e80273c55` | same |
| `因子/algobench/src/algobench/formal_calibration_statistics.py` | `1685c4bb6e61dd61c370d3f9f7e6b93e43c6fd880786b7900ac67194f42141ec` | `1685c4bb6e61dd61c370d3f9f7e6b93e43c6fd880786b7900ac67194f42141ec` | same |
| `因子/algobench/src/algobench/formal_structural_calibration.py` | `2661472d34031d59e99f74213f856a75c68d158d3a2b7120d9a864f868defe51` | `2661472d34031d59e99f74213f856a75c68d158d3a2b7120d9a864f868defe51` | same |
| `因子/algobench/src/algobench/formal_scorers.py` | `9547e8ea16a657edfa4c29dc30d116b91399e2ece20b8ba4496cd6d69752d89e` | `a6d636a114804456d1688fcab8cc42d37490a38a25d26b4222206cc201be8713` | different |
