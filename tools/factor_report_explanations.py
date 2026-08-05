from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "factor-formula-guide-v2-all-order-summary"
REPORT_DATA_RE = re.compile(
    r'(<script id="report-data" type="application/json">)(.*?)(</script>)',
    flags=re.DOTALL,
)
RANKING_SECTION_RE = re.compile(
    r'<section class="shell chapter" id="ranking"(?: [^>]*)?>.*?</section>',
    flags=re.DOTALL,
)


def _term(symbol: str, definition: str, unit: str, source: str) -> dict[str, str]:
    return {
        "symbol": symbol,
        "definition": definition,
        "unit": unit,
        "source": source,
    }


# This glossary deliberately separates observed quantities, deterministic transforms, and
# frozen parameters.  A factor card selects the entries it uses, so readers never need to
# infer a symbol from a different chapter.
FORMULA_GLOSSARY: dict[str, dict[str, str]] = {
    "order_score": _term(
        "$s_i$",
        "订单 $i$ 的原始行为得分；先逐订单计算，再回填或聚合到股票日。",
        "通常为 $[0,1]$",
        "确定性公式输出；不是回测统计量。",
    ),
    "edge_score": _term(
        "$s_{\\mathrm{edge}}$ / $L_{ij}$",
        "旧订单 $i$ 与候选新订单 $j$ 的连接或响应得分；$i,j$ 是订单编号，不是参数。",
        "$[0,1]$",
        "由候选门、时间、数量、价格及所需响应证据确定。",
    ),
    "group_score": _term(
        "$s_{\\mathrm{group}}$",
        "一组拆分或合并订单的联合得分，随后回填给组内参与订单。",
        "$[0,1]$",
        "由当天局部最优分组确定。",
    ),
    "cluster_score": _term(
        "$s_{\\mathrm{cluster}}$",
        "同侧、相邻动作构成的成交簇或撤挂簇得分。",
        "$[0,1]$",
        "由当天事件序列确定。",
    ),
    "chain_score": _term(
        "$s_{\\mathrm{chain}}$ / $s_{\\mathrm{run}}$",
        "多条撤挂边串成的订单链或运行序列得分。",
        "$[0,1]$",
        "由当天局部最优边和链规则确定。",
    ),
    "submit_qty": _term(
        "$q_i^{\\mathrm{submit}}$ / $Q_i$",
        "订单 $i$ 的原始申报数量。",
        "股",
        "逐笔订单事件重放得到。",
    ),
    "cancel_qty": _term(
        "$q_i^{\\mathrm{cancel}}$ / $X_i$",
        "订单 $i$ 生命周期内累计真正撤掉的数量。",
        "股",
        "逐笔撤单事件加总；不是原始申报量的替代写法。",
    ),
    "cancel_fraction": _term(
        "$C_i$",
        "$C_i=q_i^{\\mathrm{cancel}}/q_i^{\\mathrm{submit}}$；未撤为 0，整单撤回为 1。",
        "$[0,1]$",
        "由订单生命周期运行时计算。",
    ),
    "execution_fraction": _term(
        "$E_i$",
        "$E_i=q_i^{\\mathrm{fill}}/q_i^{\\mathrm{submit}}$，表示订单最终成交比例。",
        "$[0,1]$",
        "由订单生命周期运行时计算。",
    ),
    "unfilled_fraction": _term(
        "$1-E_i$ / $U_i$",
        "订单没有成交的比例；不是缺失值。",
        "$[0,1]$",
        "由 $E_i$ 确定性计算。",
    ),
    "wall_distance": _term(
        "$\\Delta t$",
        "两个指定动作时间戳的绝对墙钟差；f03 中是报单到首次撤单。",
        "秒",
        "交易所 data_time 运行时计算。",
    ),
    "event_distance": _term(
        "$\\Delta e$",
        "两个动作序号之间夹着的事件条数，即事件序号差扣除端点后取非负值。",
        "条事件",
        "通道内确定性事件序号运行时计算。",
    ),
    "theta_wall": _term(
        "$\\theta_{\\mathrm{wall}}$",
        "墙钟指数核的衰减尺度；它不是超时硬阈值。距离等于该尺度时，单个墙钟核为 $e^{-1}\\approx0.368$。",
        "秒",
        "先验校准冻结值 1.990919 秒；正距离中位数 1.38 秒除以 $\\ln2$，未使用本轮 IC。",
    ),
    "theta_event": _term(
        "$\\theta_{\\mathrm{event}}$",
        "事件时钟指数核的衰减尺度；它不是最多允许事件数。距离等于该尺度时，单个事件核为 $e^{-1}\\approx0.368$。",
        "条事件",
        "先验校准冻结值 38,342.506102 条；正距离中位数 26,577 条除以 $\\ln2$，未使用本轮 IC。",
    ),
    "kernel_shape": _term(
        "$p$",
        "指数核形状：$K(x)=\\exp[-(x/\\theta)^p]$。当前 $p=1$，因此是普通指数衰减。",
        "无量纲",
        "实现默认冻结值 1；没有按本轮 IC 调整。",
    ),
    "hybrid_kernel": _term(
        "$K_{\\mathrm{hybrid}}$",
        "$K_{\\mathrm{hybrid}}=\\sqrt{K_{\\mathrm{wall}}K_{\\mathrm{event}}}$，其中 $K_{\\mathrm{wall}}=\\exp[-(\\Delta t/\\theta_{\\mathrm{wall}})^p]$，$K_{\\mathrm{event}}=\\exp[-(\\Delta e/\\theta_{\\mathrm{event}})^p]$。两个时钟任一很远都会降分。",
        "$[0,1]$",
        "确定性公共组件；使用本表冻结尺度。",
    ),
    "wall_50ms": _term(
        "$50\\,\\mathrm{ms}$",
        "f04 专用墙钟核尺度；是软衰减尺度，不是“50ms 内命中、之外为 0”的硬门。",
        "0.05 秒",
        "预注册规格 f04_50ms_v1；覆盖公共墙钟尺度。",
    ),
    "bbo_distance": _term(
        "$d_{i,\\mathrm{BBO}}$",
        "订单有效价格到报单前同侧最优报价的绝对标准化 tick 距离。",
        "tick",
        "动作前订单簿与逐股票 quote tick 元数据运行时计算。",
    ),
    "theta_bbo": _term(
        "$\\theta_{\\mathrm{BBO}}$",
        "BBO 距离或 BBO 跟随残差的指数衰减尺度。",
        "tick",
        "先验校准冻结值 11.541560327 tick；未使用本轮 IC。",
    ),
    "time_kernel": _term(
        "$K_{\\mathrm{time}}$",
        "配对动作的时间相似度；当前 hybrid 规格等于公共 $K_{\\mathrm{hybrid}}$。",
        "$[0,1]$",
        "由墙钟差、事件差及两个冻结尺度运行时计算。",
    ),
    "qty_kernel": _term(
        "$K_{\\mathrm{qty}}$",
        "$K_{\\mathrm{qty}}=\\exp[-|\\ln(q_{\\mathrm{new}}/q_{\\mathrm{ref}})|/\\theta_{\\mathrm{qty}}]$；数量越接近越接近 1。每条边此前还必须通过 10% 对称硬门。",
        "$[0,1]$",
        "先验冻结 $\\theta_{\\mathrm{qty}}=0.104336660$；硬门为人工批准固定政策。",
    ),
    "price_kernel": _term(
        "$K_{\\mathrm{price}}$",
        "普通限价单为 $\\exp(-d_{\\mathrm{tick}}/\\theta_{\\mathrm{price}})$；特殊或可成交指令改用可成交性 $M$。",
        "$[0,1]$",
        "先验冻结 $\\theta_{\\mathrm{price}}=23.083120654$ tick；不设普通限价最大价格距离硬门。",
    ),
    "kernel_weights": _term(
        "$w_t,w_q,w_p$",
        "时间、数量、价格三个核的指数权重；不是样本权重。当前均为 1。",
        "无量纲",
        "实现默认冻结值 $w_t=w_q=w_p=1$；没有按本轮 IC 校准。",
    ),
    "pair_score": _term(
        "$L_{ij}$",
        "$L_{ij}=K_{\\mathrm{time}}^{w_t}K_{\\mathrm{qty}}^{w_q}K_{\\mathrm{price}}^{w_p}$；表示行为连接相似度，不是同账户概率。",
        "$[0,1]$",
        "候选边通过 3 秒范围与 10% 数量硬门后确定性计算。",
    ),
    "time_qty_score": _term(
        "$L_{\\mathrm{time,qty}}$",
        "$K_{\\mathrm{time}}^{w_t}K_{\\mathrm{qty}}^{w_q}$；有意不使用价格核，避免随后价格方向证据被重复计算。",
        "$[0,1]$",
        "公共软配对分数的时间×数量子组件。",
    ),
    "quantity_reference": _term(
        "$q_{\\mathrm{ref}}$",
        "在本次撤单量 $q_{\\mathrm{cancel}}$ 与撤前剩余量 $q_{\\mathrm{residual}}$ 中，选择与新单量对数距离更近者。",
        "股",
        "逐候选边运行时选择；不是调参。",
    ),
    "quantity_candidates": _term(
        "$q_{\\mathrm{new}},q_{\\mathrm{cancel}},q_{\\mathrm{residual}}$",
        "分别是替代新单原始量、旧单本次撤掉的量、旧单撤前剩余量。",
        "股",
        "订单生命周期和候选边运行时读取。",
    ),
    "price_tick_change": _term(
        "$\\Delta p_{\\mathrm{ticks}}$",
        "新旧报价的标准化 tick 差；f13 取绝对值，只奖励同价或近同价。",
        "tick",
        "新旧订单价格与 quote tick 元数据运行时计算。",
    ),
    "theta_same": _term(
        "$\\theta_{\\mathrm{same}}$",
        "同价刷新因子的价格差衰减尺度。",
        "tick",
        "未单独校准的实现默认值 1.0；应视为稳健性检查对象。",
    ),
    "directed_price": _term(
        "$\\Delta p_{\\mathrm{directed}}$",
        "$\\mathrm{side}_i(p_{\\mathrm{new}}-p_{\\mathrm{old}})$；买单抬价、卖单降价为正（更激进），反向为负（更省价）。",
        "标准化价格或 tick",
        "买卖方向与新旧报价运行时计算。",
    ),
    "saturation": _term(
        "$\\operatorname{sat}(x;c)$",
        "$1-\\exp(-x/c)$；把非负证据压到 $[0,1)$，避免极端值无限主导。公式省略 $c$ 时使用对应实现默认尺度。",
        "$[0,1)$",
        "确定性公共变换；多数未单独登记的 $c_*$ 默认 1.0。",
    ),
    "c_price": _term(
        "$c_{\\mathrm{price}}$",
        "省价或激进改价幅度的饱和尺度。",
        "tick",
        "当前继承 $\\theta_{\\mathrm{price}}=23.083120654$ tick；没有按本轮 IC 调整。",
    ),
    "queue_ahead": _term(
        "$q_{\\mathrm{ahead}}^{\\mathrm{old/new}}$ / $A_{\\mathrm{old/new}}$",
        "旧单撤前、新单报出前，在 FIFO 队列中排在该订单前面的可见同价数量。",
        "股",
        "严格动作前订单簿运行时计算；不可观察时为 NA。",
    ),
    "queue_improve": _term(
        "$\\operatorname{queueImprove}$ / $K_{\\mathrm{queue}}$",
        "先取 $\\max(A_{\\mathrm{old}}-A_{\\mathrm{new}},0)$，再以队列尺度做饱和；只有前方数量减少才算改善。",
        "$[0,1]$",
        "确定性变换；队列饱和尺度当前为实现默认 1.0。",
    ),
    "geometric_mean": _term(
        "$\\operatorname{GM}(x_1,\\ldots,x_k)$",
        "$\\exp[k^{-1}\\sum_r\\ln x_r]$；任一完整可观察环节为 0 时整体为 0，所需环节不可观察时保留 NA。",
        "$[0,1]$",
        "确定性公共组合规则。",
    ),
    "edge_quality": _term(
        "$Q_{\\mathrm{edge}}$ / $Q_e$ / $L_{\\mathrm{link}}$",
        "组、簇或链中参与边的连接质量；基本来源是 $L_{ij}$，再按具体结构取均值、低分位或局部最优。",
        "$[0,1]$",
        "由当天合格候选边确定。",
    ),
    "quantity_conservation": _term(
        "$C_{\\mathrm{qty}}$",
        "撤单/剩余任务总量与替代单总量的守恒相似度；总量越接近越高。",
        "$[0,1]$",
        "拆分、合并或链内订单数量运行时计算。",
    ),
    "marketability": _term(
        "$M_i$ / $M_{\\mathrm{new}}$",
        "报单前可成交性：直接可成交或穿价时为 1，否则按离对手最优价的不利 tick gap 连续衰减。",
        "$[0,1]$",
        "先验冻结 $\\theta_{\\mathrm{marketability}}=5.770780164$ tick；动作前 BBO 运行时计算。",
    ),
    "execution_speed": _term(
        "$v_i^{\\mathrm{exec}}$",
        "订单各笔成交量加权的 submit→trade 混合时间核；越快成交越接近 1。",
        "$[0,1]$",
        "真实成交与公共混合时间核运行时计算。",
    ),
    "trade_quantity": _term(
        "$q_{ik}^{\\mathrm{trade}}$",
        "订单 $i$ 的第 $k$ 笔真实成交数量；$k$ 是成交序号。",
        "股",
        "逐笔成交事件读取。",
    ),
    "depth_reference": _term(
        "$D_i$",
        "订单提交前对手侧可见盘口深度；只允许使用动作前状态。",
        "股",
        "严格动作前订单簿运行时计算。",
    ),
    "fast_fill_qty": _term(
        "$q_i^{\\mathrm{fast\\ fill}}$",
        "订单数量乘执行速度得到的快速成交等效量。",
        "股",
        "申报数量与 $v_i^{\\mathrm{exec}}$ 确定性计算。",
    ),
    "depth_scale": _term(
        "$c_{\\mathrm{depth}}$",
        "快速成交量相对可见深度的饱和尺度。",
        "无量纲比例尺度",
        "未单独校准的实现默认值 1.0。",
    ),
    "price_levels": _term(
        "$n_i^{\\mathrm{price\\ levels}}$",
        "订单快速成交覆盖的不同成交价位数量；1 表示没有跨档。",
        "档",
        "逐笔真实成交价格去重计数。",
    ),
    "length_strength": _term(
        "$\\ell$ / $S_{\\mathrm{length}}$",
        "簇或链长度的连续饱和证据；报告公式中的 $\\ell$ 不是任意常数，也不是总样本数。",
        "$[0,1]$",
        "由节点/边数量按冻结饱和规则运行时计算。",
    ),
    "cluster_qualities": _term(
        "$Q_{\\mathrm{time}},Q_{\\mathrm{qty}},Q_{\\mathrm{depth}},Q_{\\mathrm{cluster}}$",
        "簇内相邻子单的时间接近度、数量稳定性、深度消耗证据及其联合质量。",
        "$[0,1]$",
        "簇内订单、成交与动作前深度运行时计算。",
    ),
    "state_response": _term(
        "$R_{\\mathrm{state}}$",
        "链或簇在动作前是否出现可识别市场状态冲击、且动作方向与冲击一致的综合响应强度。",
        "$[0,1]$",
        "统一 market-impact 响应引擎运行时计算；只向动作前回看。",
    ),
    "volume_alignment": _term(
        "$A_{\\mathrm{volume}}$ / $A_{\\mathrm{market\\ volume}}$",
        "子单节奏与严格先验市场成交活跃度的对齐程度。",
        "$[0,1]$",
        "当天成交与严格先验 activity 基线运行时计算。",
    ),
    "switch_components": _term(
        "$P_{\\mathrm{start}},A_{\\mathrm{finish}},S_{\\mathrm{switch}}$",
        "链起点的被动性、终点的主动性，以及链上可成交性正向提升强度。",
        "$[0,1]$",
        "链首尾动作前 BBO 与 marketability 运行时计算。",
    ),
    "completion": _term(
        "$C_{\\mathrm{complete}}$",
        "链所代表任务最终完成的比例；只使用证据窗口内可观察成交。",
        "$[0,1]$",
        "链生命周期与真实成交运行时计算。",
    ),
    "incident_quality": _term(
        "$\\sum_{e\\ni i}Q_e$",
        "与节点 $i$ 相连的所有合格边质量之和；$e\\ni i$ 表示边 $e$ 连接该节点。",
        "非负",
        "当天订单图运行时计算。",
    ),
    "theta_incident": _term(
        "$\\theta_{\\mathrm{incident}}$",
        "相邻边证据和的饱和尺度。",
        "边质量单位",
        "未单独校准的实现默认值 1.0。",
    ),
    "edge_mean": _term(
        "$\\overline Q_{\\mathrm{edge}}$ / $Q_{\\mathrm{chain}}$",
        "链内边质量的算术平均；允许强边部分补偿弱边。",
        "$[0,1]$",
        "链内 $L_{ij}$ 运行时汇总。",
    ),
    "edge_q20": _term(
        "$Q_{\\mathrm{edge}}^{(0.20)}$",
        "链内边质量的 20% 分位数；专门惩罚链中的弱连接。",
        "$[0,1]$",
        "链内 $L_{ij}$ 运行时汇总；20% 为预先冻结诊断/归约规则。",
    ),
    "node_count": _term(
        "$n_{\\mathrm{node}}$ / $|V|$",
        "链中的订单节点数；$n_{\\mathrm{node}}-1$ 是可形成的连续边步数。",
        "个节点",
        "当天订单图运行时计数。",
    ),
    "theta_length": _term(
        "$\\theta_{\\mathrm{length}}$",
        "链长度饱和尺度。",
        "步",
        "未单独校准的实现默认值 1.0。",
    ),
    "reprice_fraction": _term(
        "$f_{\\mathrm{reprice}}$",
        "链内发生实际改价的边占比。",
        "$[0,1]$",
        "链内新旧报价运行时计算。",
    ),
    "direction_consistency": _term(
        "$D_{\\mathrm{consistent}}$ / $D_{\\mathrm{save}}$ / $D_{\\mathrm{aggressive}}$",
        "链内改价是否大多朝同一方向，以及该方向是否符合省价或加急定义。",
        "$[0,1]$",
        "买卖方向与逐边有向改价运行时计算。",
    ),
    "price_path": _term(
        "$|\\Delta p|$ / $S_{\\mathrm{price}}$ / $\\Delta p_{\\mathrm{aggressive}}$",
        "链首尾或逐边累计的绝对、省价或激进方向改价幅度。",
        "tick",
        "链内标准化报价运行时计算后再饱和。",
    ),
    "bbo_follow_residual": _term(
        "$r_{\\mathrm{follow}}$",
        "订单改价与同侧 BBO 同期移动之间的残差；越小越像机械跟随最优价。",
        "tick",
        "动作前 BBO 路径与订单改价运行时计算。",
    ),
    "delta_marketability": _term(
        "$\\Delta M$",
        "链首尾或相邻步骤可成交性的正向变化。",
        "$[0,1]$",
        "逐节点 marketability 运行时计算。",
    ),
    "shock_strength": _term(
        "$S_{\\mathrm{shock}}$ / $S_h$",
        "动作发生前某类盘口或成交冲击的标准化强度。",
        "$[0,1]$",
        "统一 market-impact 工件运行时计算；响应窗固定向前 1 秒。",
    ),
    "response_kernel": _term(
        "$K_{\\mathrm{response}}$",
        "冲击到动作的响应时延核；冲击越接近动作权重越高。",
        "$[0,1]$",
        "动作前 1 秒冻结回看窗与公共时间核运行时计算。",
    ),
    "action_consistency": _term(
        "$A_{\\mathrm{consistent}}$ / $D_{\\mathrm{match}}$",
        "冲击方向与改单方向是否符合该因子的经济定义；不一致时不给响应证据。",
        "$[0,1]$",
        "预注册方向规则与运行时动作确定。",
    ),
    "dilution_strength": _term(
        "$S_{\\mathrm{dilution}}$",
        "动作前排队位置被新增同价/更优价数量稀释的标准化冲击强度。",
        "$[0,1]$",
        "动作前统一 market-impact 或冻结旧版 queue_ahead 逻辑计算。",
    ),
    "queue_response": _term(
        "$Q_{\\mathrm{improve}}$",
        "冲击后订单是否通过撤挂改善排队位置的动作证据。",
        "$[0,1]$",
        "旧、新订单动作前 FIFO 队列运行时计算。",
    ),
    "trade_pressure": _term(
        "$S_{\\mathrm{trade\\ pressure}}$",
        "动作前档位耗尽或大额真实成交相对正常成交/深度的冲击强度。",
        "$[0,1]$",
        "严格前序成交与动作前盘口运行时计算。",
    ),
    "spread_shocks": _term(
        "$S_{\\mathrm{narrow}},S_{\\mathrm{wide}}$",
        "动作前价差收窄或扩大的标准化冲击强度；两个规格只启用各自方向。",
        "$[0,1]$",
        "动作前 bid/ask 与当时 spread 运行时计算。",
    ),
    "response_actions": _term(
        "$A_{\\mathrm{aggressive}},A_{\\mathrm{retreat}}$",
        "动作是否表现为更积极拿流动性，或撤退/降低可成交性。",
        "$[0,1]$",
        "有向改价、撤单与 marketability 运行时计算。",
    ),
    "imbalance_flip": _term(
        "$S_{\\mathrm{flip}}$",
        "动作前买卖盘不平衡发生方向翻转的深度归一化强度。",
        "$[0,1]$",
        "严格动作前盘口深度运行时计算。",
    ),
    "volatility_jump": _term(
        "$S_{\\mathrm{volatility\\ jump}}$",
        "动作前短窗波动相对严格先验正常波动的跳升强度。",
        "$[0,1]$",
        "严格前序市场状态基线运行时计算。",
    ),
    "cycle_components": _term(
        "$B_{\\mathrm{BBO}},C_{\\mathrm{cancel}},I_{\\mathrm{cost/queue}},R_{\\mathrm{response}}$",
        "分别是贴近 BBO、真实撤单、成本或排队改善、以及状态响应证据；与 $L_{ij}$ 一起构成五环。",
        "各为 $[0,1]$",
        "对应动作前盘口、订单生命周期、配对与响应引擎运行时计算。",
    ),
    "cost_improvement": _term(
        "$I_{\\mathrm{cost}}^+$",
        "链后续真实成交 VWAP 相对撤单前可得基准成本的正向改善；买得更低或卖得更高才为正。",
        "$[0,1]$",
        "因果成交参考、真实成交与 spread/局部波动归一化运行时计算。",
    ),
    "periodicity": _term(
        "$P_{\\mathrm{periodic}}$",
        "$1/(1+\\mathrm{CV}_{\\mathrm{interval}})$；子单间隔越稳定越接近 1。",
        "$[0,1]$",
        "簇内动作间隔运行时计算。",
    ),
    "quantity_stability": _term(
        "$Q_{\\mathrm{stable}}$",
        "簇内子单数量越接近固定手数，稳定性越高。",
        "$[0,1]$",
        "簇内申报数量运行时计算。",
    ),
    "repost_evidence": _term(
        "$L_{\\mathrm{repost}}$",
        "簇内最大或代表性撤挂连接证据；固定手数对照用 $1-L_{\\mathrm{repost}}$ 排除明显改单链。",
        "$[0,1]$",
        "公共配对边运行时计算。",
    ),
    "nonperiodic": _term(
        "$N_{\\mathrm{nonperiodic}}$",
        "动作间隔偏离固定节拍的程度；与状态响应同高才支持事件驱动解释。",
        "$[0,1]$",
        "簇/链间隔运行时计算。",
    ),
    "one_shot": _term(
        "$\\mathbf1\\{\\mathrm{one\\ shot},E_i=1,C_i=0\\}$",
        "仅当该侧为一次性报单、完全成交且没有撤单时取 1，否则取 0。",
        "$\\{0,1\\}$",
        "订单生命周期和同侧报单计数运行时判定。",
    ),
}


IDEA_TERM_KEYS: dict[str, list[str]] = {
    "f01_cancel": ["order_score", "cancel_qty"],
    "f02_cfrac": ["order_score", "cancel_fraction", "cancel_qty", "submit_qty"],
    "f03_curg_hybrid": ["order_score", "cancel_fraction", "hybrid_kernel", "wall_distance", "event_distance", "theta_wall", "theta_event", "kernel_shape"],
    "f04_subhuman_50ms": ["order_score", "cancel_fraction", "wall_distance", "wall_50ms", "kernel_shape"],
    "f05_fleet": ["order_score", "hybrid_kernel", "cancel_fraction", "execution_fraction", "unfilled_fraction"],
    "f06_touchfleet": ["order_score", "hybrid_kernel", "cancel_fraction", "unfilled_fraction", "bbo_distance", "theta_bbo"],
    "f07_pfexit": ["order_score", "cancel_fraction", "execution_fraction", "hybrid_kernel", "wall_distance", "event_distance"],
    "f10_repost_both": ["edge_score", "pair_score", "time_kernel", "qty_kernel", "price_kernel", "kernel_weights", "quantity_reference", "quantity_candidates"],
    "f10_repost_cf": ["edge_score", "pair_score", "time_kernel", "qty_kernel", "price_kernel", "kernel_weights", "quantity_reference", "quantity_candidates"],
    "f10_repost_rf": ["edge_score", "pair_score", "time_kernel", "qty_kernel", "price_kernel", "kernel_weights", "quantity_reference", "quantity_candidates"],
    "f11_urgentrep": ["edge_score", "pair_score", "hybrid_kernel", "wall_distance", "event_distance"],
    "f12_residrep": ["edge_score", "quantity_reference", "quantity_candidates", "qty_kernel", "pair_score"],
    "f13_refresh": ["edge_score", "time_qty_score", "price_tick_change", "theta_same"],
    "f14_pricesave": ["edge_score", "time_qty_score", "directed_price", "saturation", "c_price"],
    "f15_aggrep": ["edge_score", "time_qty_score", "directed_price", "saturation", "c_price"],
    "f16_queueimp": ["edge_score", "time_qty_score", "queue_ahead", "queue_improve"],
    "f17_split": ["group_score", "edge_quality", "quantity_conservation", "geometric_mean"],
    "f18_merge": ["group_score", "edge_quality", "quantity_conservation", "geometric_mean"],
    "f19_c2mkt": ["edge_score", "time_qty_score", "marketability", "execution_speed"],
    "f20_fillre": ["chain_score", "execution_fraction", "hybrid_kernel", "edge_quality", "geometric_mean"],
    "f21_repburst": ["cluster_score", "length_strength", "edge_quality"],
    "f22_mktfill": ["order_score", "marketability", "execution_speed"],
    "f23_instfill": ["order_score", "trade_quantity", "hybrid_kernel", "submit_qty"],
    "f24_depth": ["order_score", "marketability", "fast_fill_qty", "depth_reference", "depth_scale"],
    "f25_sweep": ["order_score", "marketability", "execution_speed", "price_levels", "saturation"],
    "f26_aggburst": ["cluster_score", "length_strength", "cluster_qualities", "geometric_mean"],
    "f27_childseq": ["cluster_score", "length_strength", "cluster_qualities", "state_response", "volume_alignment"],
    "f28_liqswitch": ["chain_score", "edge_q20", "length_strength", "switch_components", "completion", "geometric_mean"],
    "f29_softrun": ["order_score", "incident_quality", "theta_incident", "saturation"],
    "f30_longrun": ["chain_score", "edge_mean", "node_count", "theta_length", "saturation"],
    "f31_hcrun": ["chain_score", "edge_q20", "node_count", "saturation"],
    "f32_reprice": ["chain_score", "edge_mean", "length_strength", "reprice_fraction", "direction_consistency", "price_path", "saturation"],
    "f33_bbofollow": ["chain_score", "edge_q20", "length_strength", "reprice_fraction", "bbo_follow_residual", "theta_bbo"],
    "f34_queueopt": ["chain_score", "edge_q20", "length_strength", "quantity_conservation", "queue_improve"],
    "f35_costsave": ["chain_score", "edge_mean", "length_strength", "quantity_conservation", "completion", "direction_consistency", "price_path", "saturation"],
    "f36_escalate": ["chain_score", "edge_mean", "length_strength", "quantity_conservation", "direction_consistency", "price_path", "delta_marketability"],
    "f37_complete": ["chain_score", "edge_mean", "length_strength", "quantity_conservation", "completion"],
    "f38_adaptive": ["chain_score", "edge_q20", "length_strength", "state_response"],
    "f40_iceberg": ["chain_score", "time_kernel", "price_kernel", "qty_kernel", "geometric_mean", "edge_quality"],
    "f41_reactive": ["chain_score", "edge_q20", "length_strength", "state_response", "nonperiodic"],
    "f42_bq_opp": ["edge_score", "pair_score", "shock_strength", "response_kernel", "action_consistency"],
    "f42_bq_own": ["edge_score", "pair_score", "shock_strength", "response_kernel", "action_consistency"],
    "f43_qdformal": ["edge_score", "dilution_strength", "response_kernel", "pair_score", "queue_response"],
    "f43_qdilute": ["edge_score", "dilution_strength", "response_kernel", "pair_score", "queue_response"],
    "f44_deplete": ["edge_score", "pair_score", "trade_pressure", "response_kernel", "action_consistency"],
    "f45_spread_nar": ["edge_score", "spread_shocks", "response_actions"],
    "f45_spread_wid": ["edge_score", "spread_shocks", "response_actions"],
    "f46_imbflip": ["edge_score", "pair_score", "imbalance_flip", "response_kernel", "action_consistency"],
    "f47_voljump": ["edge_score", "pair_score", "volatility_jump", "response_kernel", "response_actions"],
    "f51_revcycle": ["edge_score", "cycle_components", "pair_score", "geometric_mean"],
    "f52_costcycle": ["chain_score", "edge_q20", "completion", "cost_improvement", "geometric_mean"],
    "c01_periodic": ["cluster_score", "length_strength", "periodicity", "state_response"],
    "c02_fixed": ["cluster_score", "length_strength", "quantity_stability", "state_response", "repost_evidence"],
    "c03_volpart": ["cluster_score", "length_strength", "volume_alignment"],
    "c04_oneshot": ["order_score", "one_shot", "execution_fraction", "cancel_fraction", "marketability", "execution_speed"],
}


SPECIAL_READINGS = {
    "f03_curg_hybrid": (
        "先算撤单比例 $C_i$；再分别计算报单到首次撤单的墙钟核和事件核；"
        "取两者几何平均得到 $K_{\\mathrm{hybrid}}$；最后相乘。"
        "因此同样是 100ms 撤单，在消息极密与消息稀疏时不会被机械地判成同一种紧迫度。"
    ),
    "f10_repost_both": "先过候选资格与 10% 数量硬门，再计算三个软核并相乘；最后在双顺序 lane 内选本地最优边。",
    "f10_repost_cf": "只在撤单先、新单后的候选中，先过硬门，再计算时间×数量×价格软连接并选本地最优边。",
    "f10_repost_rf": "只在新单先、撤单后的候选中，先过硬门，再计算时间×数量×价格软连接并选本地最优边。",
    "f43_qdformal": "只使用统一 market-impact 引擎产生的排队稀释冲击；再检查一秒内的配对动作是否改善队列。",
    "f43_qdilute": "使用冻结旧版 queue_ahead 增幅逻辑形成稀释冲击；不要把它与 formal_v2 的统一冲击定义混用。",
    "f45_spread_nar": "本规格只启用“价差收窄→动作更激进”这一支；页面同时展示 widening 公式是为了说明同族对照。",
    "f45_spread_wid": "本规格只启用“价差扩大→动作撤退”这一支；页面同时展示 narrowing 公式是为了说明同族对照。",
}


F03_EXPANDED_FORMULA = (
    "$$s_i=C_i\\sqrt{"
    "\\exp\\!\\left[-\\left(\\frac{\\Delta t_i}{\\theta_{\\mathrm{wall}}}\\right)^p\\right]"
    "\\exp\\!\\left[-\\left(\\frac{\\Delta e_i}{\\theta_{\\mathrm{event}}}\\right)^p\\right]}$$"
)


AGGREGATION_NOTE = (
    "卡片公式先产生订单、边、簇或链级得分。卡片内 c/q/a 是历史报告的条件分母输出；"
    "2026-08-05 起主研究口径只保留笔数型 c，并用全部有效去重新委托数作统一分母，详见汇总章。"
)

ZERO_NA_NOTE = (
    "完整可观察且行为未发生时记 0；定义所需生命周期、动作前盘口、成交、队列或后续观察期不足时记 NA。"
    "NA 不会被填成 0 进入分母。"
)


def apply_formula_explanations(payload: dict[str, Any]) -> dict[str, Any]:
    ideas = payload.get("ideas")
    if not isinstance(ideas, list):
        raise RuntimeError("factor report payload has no idea list")
    idea_ids = {str(idea.get("idea_id")) for idea in ideas}
    expected = set(IDEA_TERM_KEYS)
    if idea_ids != expected:
        raise RuntimeError(
            "formula explanation inventory mismatch: "
            f"missing={sorted(expected - idea_ids)} extra={sorted(idea_ids - expected)}"
        )
    unknown_keys = sorted(
        {key for keys in IDEA_TERM_KEYS.values() for key in keys} - set(FORMULA_GLOSSARY)
    )
    if unknown_keys:
        raise RuntimeError(f"formula explanation references unknown terms: {unknown_keys}")

    payload["formula_explanation_schema"] = SCHEMA_VERSION
    payload["formula_glossary"] = FORMULA_GLOSSARY
    for idea in ideas:
        idea_id = str(idea["idea_id"])
        description = idea.get("description")
        if not isinstance(description, dict):
            raise RuntimeError(f"{idea_id}: missing description")
        formula = str(description.get("formula", ""))
        formula = formula.replace("\\theta_{t}", "\\theta_{\\mathrm{wall}}")
        formula = formula.replace("\\theta_{e}", "\\theta_{\\mathrm{event}}")
        if idea_id == "f03_curg_hybrid":
            formula = F03_EXPANDED_FORMULA
        description["formula"] = formula
        idea["formula_guide"] = {
            "reading": SPECIAL_READINGS.get(idea_id, str(description.get("build", ""))),
            "term_keys": IDEA_TERM_KEYS[idea_id],
            "aggregation": AGGREGATION_NOTE,
            "zero_na": ZERO_NA_NOTE,
        }
    return payload


GUIDE_CSS = r"""
.formula-guide{margin:16px 0 22px;border:1px solid #cfc6b8;background:#f5f0e7}
.formula-guide-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:16px;align-items:start;padding:16px 18px;border-bottom:1px solid #d8d0c4}
.formula-guide-head b{font:800 11px var(--mono);letter-spacing:.09em;color:var(--red)}
.formula-guide-head p{margin:7px 0 0;color:#3f4d54;font-size:13px}.formula-guide-badge{font:700 9px var(--mono);letter-spacing:.08em;color:#fff;background:var(--teal);padding:6px 8px;white-space:nowrap}
.formula-term-table{width:100%;border-collapse:collapse;table-layout:fixed}
.formula-term-table th,.formula-term-table td{padding:11px 12px;border-bottom:1px solid #ded7cd;text-align:left;vertical-align:top;font-size:12px;white-space:normal}
.formula-term-table th{background:#e9e2d7;font:700 10px var(--mono);letter-spacing:.05em;color:#586269}
.formula-term-table th:nth-child(1){width:17%}.formula-term-table th:nth-child(2){width:43%}.formula-term-table th:nth-child(3){width:13%}.formula-term-table th:nth-child(4){width:27%}
.formula-term-table td:first-child{font-weight:700;color:#1d2d36}.formula-term-table .katex{font-size:1em}
.formula-guide-notes{display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:12px 16px 16px}.formula-guide-notes div{border-left:3px solid var(--gold);padding:7px 10px;color:#566168;font-size:11px;background:rgba(255,255,255,.55)}
@media(max-width:720px){.formula-guide-head{grid-template-columns:1fr}.formula-guide-badge{justify-self:start}.formula-guide-table-wrap{overflow:auto}.formula-term-table{min-width:760px}.formula-guide-notes{grid-template-columns:1fr}}
""".strip()


CURRENT_RESEARCH_CSS = r"""
.research-update{margin-top:22px;border:1px solid #c9c0b3;background:linear-gradient(145deg,#f7f2e9 0%,#fff 58%,#edf3f1 100%);box-shadow:0 16px 40px rgba(29,45,54,.08)}
.research-update-head{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:20px;align-items:start;padding:22px 24px;border-bottom:1px solid #d8d0c4}
.research-update-head .stamp{font:800 10px var(--mono);letter-spacing:.09em;color:#fff;background:var(--red);padding:7px 9px;white-space:nowrap}
.research-update-head h3{margin:4px 0 8px;font-size:22px;line-height:1.28;color:var(--ink)}
.research-update-head p{margin:0;max-width:980px;color:#44535b;font-size:13px;line-height:1.8}
.research-verdict{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;background:#d8d0c4;border-bottom:1px solid #d8d0c4}
.research-verdict article{padding:18px 20px;background:#fff}
.research-verdict b{display:block;margin-bottom:6px;font:800 10px var(--mono);letter-spacing:.07em;color:var(--teal)}
.research-verdict strong{display:block;margin-bottom:7px;font-size:18px;line-height:1.35;color:var(--ink)}
.research-verdict p{margin:0;color:#536169;font-size:12px;line-height:1.7}
.research-block{padding:20px 24px;border-bottom:1px solid #ddd5ca}
.research-block:last-child{border-bottom:0}
.research-block h3{margin:0 0 9px;font-size:17px;color:var(--ink)}
.research-block>p{margin:0 0 12px;color:#4d5b63;font-size:12px;line-height:1.75}
.definition-grid{display:grid;grid-template-columns:1.05fr .95fr;gap:14px}
.definition-card{padding:15px 17px;border:1px solid #d8d0c4;background:rgba(255,255,255,.78)}
.definition-card b{display:block;margin-bottom:8px;color:var(--red);font-size:12px}
.definition-card code{font-family:var(--mono);font-size:11px;color:#163b44;overflow-wrap:anywhere}
.definition-card p{margin:7px 0 0;color:#536169;font-size:11px;line-height:1.7}
.research-table-wrap{overflow:auto;border:1px solid #d8d0c4;background:#fff}
.research-table{width:100%;min-width:980px;border-collapse:collapse;table-layout:auto}
.research-table th,.research-table td{padding:9px 10px;border-right:1px solid #e3ddd4;border-bottom:1px solid #e3ddd4;text-align:right;font-size:11px;white-space:nowrap}
.research-table th{background:#eae3d8;font:700 10px var(--mono);letter-spacing:.03em;color:#4c5960}
.research-table th:first-child,.research-table th:nth-child(2),.research-table td:first-child,.research-table td:nth-child(2){text-align:left}
.research-table tbody tr[data-period="q2"] td{background:#f3f7f5}
.research-table .all{font-weight:800;color:#0d5e62}
.research-table .neg{color:#9a3c31}
.research-foot{margin:10px 0 0;color:#68757b;font-size:10px;line-height:1.65}
.q2-grid{display:grid;grid-template-columns:1.05fr .95fr;gap:14px;align-items:start}
.q2-card{padding:16px 18px;border-left:4px solid var(--red);background:#f5eee5}
.q2-card strong{display:block;margin-bottom:7px;color:var(--ink);font-size:15px}
.q2-card p{margin:0;color:#4e5d64;font-size:12px;line-height:1.75}
.coverage-list{margin:0;padding-left:18px;color:#4e5d64;font-size:11px;line-height:1.75}
.coverage-list li+li{margin-top:4px}
.research-next{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.research-next div{padding:14px 16px;border-top:3px solid var(--gold);background:#fff}
.research-next b{display:block;margin-bottom:6px;color:var(--ink);font-size:12px}
.research-next p{margin:0;color:#56646b;font-size:11px;line-height:1.7}
.legacy-ranking{margin-top:18px;border:1px dashed #b7ada0;background:#f4efe7}
.legacy-ranking>summary{cursor:pointer;padding:14px 16px;font-weight:800;color:#5e4c43}
.legacy-ranking-body{padding:0 16px 16px}
.legacy-warning{margin:0 0 14px;padding:12px 14px;border-left:4px solid var(--gold);background:#fff;color:#5d676c;font-size:11px;line-height:1.7}
@media(max-width:820px){.research-update-head,.definition-grid,.q2-grid{grid-template-columns:1fr}.research-verdict,.research-next{grid-template-columns:1fr}.research-update-head .stamp{justify-self:start}.research-block{padding:17px}.research-update-head{padding:19px}}
""".strip()


CURRENT_RESEARCH_HTML = r"""<section class="shell chapter" id="ranking" data-research-summary="all-order-denominator-v1">
<div class="chapter-head"><div class="chapter-no">04</div><div><div class="kicker">Current research conclusion · 2026-08-05</div><h2>因子表现的总结性报告</h2><p class="chapter-lead">本章已按统一全订单分母重写。当前主研究只比较 54 个可计算的笔数型因子，并把 IC、Rank_IC、ICIR 放在一起；下方旧 165 口径排名仅作为历史审计存档。</p></div></div>
<div class="research-update">
  <div class="research-update-head"><div><h3>全订单分母修正后：Q2 异常依然存在，且不是 coverage 制造的</h3><p>复用现有 09:30–09:33 因子面板直接派生，没有重读原始 L2、没有重建订单生命周期、也没有重跑 scorer。正式样本覆盖 2025-01-02 至 2026-07-31，共 364 个交易日、1,046,287 个股票日；55 个 <code>_c</code> 因子中预注册排除无有效横截面 IC 的 <code>c04_oneshot_c</code>，正式比较 54 个。</p></div><span class="stamp">CURRENT PRIMARY RESULT</span></div>
  <div class="research-verdict">
    <article><b>口径结论</b><strong><code>_c_all</code> 应作为主口径</strong><p>它统一回答“全部有效去重新委托中出现多少可识别算法痕迹”，避免各 scorer 的可判断条件改变分母。</p></article>
    <article><b>异常归因</b><strong>换分母不能解释 2026Q2</strong><p>Q2 相对非 Q2 的中位 Rank_IC 溢价仍约 5.8%–6.5%；分母变更对该溢价的中位贡献只有 -0.00051 至 -0.00014。</p></article>
    <article><b>经济边界</b><strong>代理 / 下界，不是真实订单占比</strong><p>高值表示“可观察算法痕迹更多”。同一订单可能命中多个因子，因此 54 列不能直接相加。</p></article>
  </div>
  <div class="research-block">
    <h3>1 · 当前口径与三个 target</h3>
    <div class="definition-grid">
      <div class="definition-card"><b>统一分母</b><code>_c_cond = activity_count / determinable_total_count</code><br><code>coverage_count = determinable_total_count / window_total_count</code><br><code>_c_all = activity_count / window_total_count = _c_cond × coverage_count</code><p><code>window_total_count</code> 是 [09:30,09:33) 内全部有效、去重后的新委托订单数；成交、撤单及其他生命周期消息不重复计作新订单。最大恒等式误差为 1.11×10<sup>-16</sup>。</p></div>
      <div class="definition-card"><b>收益标签</b><code>D2 open / D1 09:33 L1 close - 1</code><br><code>D2 09:30–09:33 L1 VWAP / D1 09:33 L1 close - 1</code><br><code>D1 09:44–09:45 VWAP / D1 09:33 last - 1</code><p>分别在 2026Q2（60 日）、2026 年至 07-31（131 日）、2025 年至 2026-07-31（364 日）比较。</p></div>
    </div>
  </div>
  <div class="research-block">
    <h3>2 · 54 个因子的横截面中位数：IC / Rank_IC / ICIR</h3>
    <p>以下每个数字都是“54 个逐因子统计量的横截面中位数”，不是把 54 个因子合成后得到的 IC。<span class="all">all</span> 为当前主口径，cond 为旧条件分母对照。</p>
    <div class="research-table-wrap"><table class="research-table">
      <thead><tr><th rowspan="2">target</th><th rowspan="2">period</th><th colspan="2">IC</th><th colspan="2">Rank_IC</th><th colspan="2">ICIR</th><th rowspan="2">中位 ΔRank<br>all−cond</th></tr><tr><th>cond</th><th>all</th><th>cond</th><th>all</th><th>cond</th><th>all</th></tr></thead>
      <tbody>
        <tr data-period="q2"><td>D2 open</td><td>2026Q2 · 60 日</td><td>+0.04561</td><td class="all">+0.05265</td><td>+0.02186</td><td class="all">+0.03008</td><td>+0.13781</td><td class="all">+0.20797</td><td>+0.00326</td></tr>
        <tr><td>D2 open</td><td>2026 至 07-31 · 131 日</td><td>+0.00002</td><td class="all">+0.00555</td><td class="neg">-0.02507</td><td class="all neg">-0.01822</td><td class="neg">-0.18537</td><td class="all neg">-0.11353</td><td>+0.00063</td></tr>
        <tr><td>D2 open</td><td>2025 至 2026-07-31 · 364 日</td><td class="neg">-0.00846</td><td class="all">+0.00038</td><td class="neg">-0.03303</td><td class="all neg">-0.02617</td><td class="neg">-0.25002</td><td class="all neg">-0.19118</td><td>+0.00098</td></tr>
        <tr data-period="q2"><td>D2 09:30–09:33 VWAP</td><td>2026Q2 · 60 日</td><td>+0.04912</td><td class="all">+0.05294</td><td>+0.02637</td><td class="all">+0.03264</td><td>+0.17727</td><td class="all">+0.24392</td><td>+0.00309</td></tr>
        <tr><td>D2 09:30–09:33 VWAP</td><td>2026 至 07-31 · 131 日</td><td>+0.00145</td><td class="all">+0.00586</td><td class="neg">-0.02298</td><td class="all neg">-0.01768</td><td class="neg">-0.15920</td><td class="all neg">-0.11591</td><td>+0.00062</td></tr>
        <tr><td>D2 09:30–09:33 VWAP</td><td>2025 至 2026-07-31 · 364 日</td><td class="neg">-0.00380</td><td class="all">+0.00371</td><td class="neg">-0.02802</td><td class="all neg">-0.02111</td><td class="neg">-0.21836</td><td class="all neg">-0.15821</td><td>+0.00097</td></tr>
        <tr data-period="q2"><td>D1 09:44–09:45 VWAP</td><td>2026Q2 · 60 日</td><td>+0.04759</td><td class="all">+0.04604</td><td>+0.03751</td><td class="all">+0.03302</td><td>+0.30108</td><td class="all">+0.27790</td><td class="neg">-0.00099</td></tr>
        <tr><td>D1 09:44–09:45 VWAP</td><td>2026 至 07-31 · 131 日</td><td>+0.01437</td><td class="all">+0.01349</td><td class="neg">-0.00177</td><td class="all neg">-0.00299</td><td class="neg">-0.00994</td><td class="all neg">-0.01696</td><td class="neg">-0.00084</td></tr>
        <tr><td>D1 09:44–09:45 VWAP</td><td>2025 至 2026-07-31 · 364 日</td><td>+0.00706</td><td class="all">+0.00701</td><td class="neg">-0.01472</td><td class="all neg">-0.01495</td><td class="neg">-0.11563</td><td class="all neg">-0.12058</td><td>+0.00004</td></tr>
      </tbody>
    </table></div>
    <p class="research-foot">IC 为 mean Pearson；Rank_IC 为 mean Spearman；ICIR 为日度 IC 均值 / 日度 IC 标准差。三项在表内相邻展示。正负号均按“痕迹越多”为因子正方向，未为了提高结果而翻转。</p>
  </div>
  <div class="research-block">
    <h3>3 · 为什么不能把 Q2 的好结果归因于新分母</h3>
    <div class="q2-grid">
      <div class="research-table-wrap"><table class="research-table" style="min-width:700px"><thead><tr><th>target</th><th>Q2−304 日 non-Q2<br>cond Rank_IC</th><th>Q2−304 日 non-Q2<br>all Rank_IC</th><th>分母贡献<br>逐因子中位数</th><th>Q2 正 / 长期负</th></tr></thead><tbody><tr><td>D2 open</td><td>+0.06365</td><td class="all">+0.06260</td><td>-0.00014</td><td>41 / 54</td></tr><tr><td>D2 09:30–09:33 VWAP</td><td>+0.06094</td><td class="all">+0.05842</td><td>-0.00014</td><td>38 / 54</td></tr><tr><td>D1 09:44–09:45 VWAP</td><td>+0.06458</td><td class="all">+0.05822</td><td>-0.00051</td><td>45 / 54</td></tr></tbody></table></div>
      <div class="q2-card"><strong>这是跨 target、跨因子的普遍符号翻转</strong><p>Q2 的异常不只出现在隔日标签，也出现在原始日内 09:44–09:45 标签。用 2026 年内 71 个 non-Q2 交易日复核，分母对 Rank_IC 溢价的中位贡献也只有 +0.00003、+0.00001、-0.00042。表中的“分母贡献”是逐因子贡献的中位数，因此不要求等于前两列中位数之差。</p></div>
    </div>
  </div>
  <div class="research-block">
    <h3>4 · Coverage 的真实作用与经济解释</h3>
    <div class="definition-grid">
      <div class="definition-card"><b>Coverage 在 Q2 确实更高，但量级不够</b><ul class="coverage-list"><li>54 因子的 Q2−长期 coverage gap：股票日等权平均 +2.08 个百分点；订单数加权平均 +1.81 个百分点。</li><li>order-weighted：f18 长期 42.97% → Q2 49.61%；f20 17.68% → 19.78%；f52 14.72% → 17.10%。</li><li>Q2 coverage gap 与分母导致的 Q2 premium 变化关联很弱：订单加权 Pearson 为 0.189 / 0.130 / -0.020，Spearman 为 0.054 / 0.034 / 0.112。</li></ul></div>
      <div class="definition-card"><b>个别低 coverage 因子仍会显著改写</b><p>例如 Q2、D2 open 的 Rank_IC：<code>f17_split_c</code> -0.0029 → +0.0250，<code>f18_merge_c</code> +0.0096 → +0.0334，<code>f21_repburst_c</code> -0.0003 → +0.0175。因此全订单分母不是“小修饰”，只是它无法解释整个 Q2 的约 6% Rank_IC 溢价。</p></div>
    </div>
  </div>
  <div class="research-block">
    <h3>5 · 当前可接受的研究结论与下一步</h3>
    <div class="research-next"><div><b>低关注流动性折价：方向上有长期证据，但尚未完成识别</b><p>长期 <code>_c_all</code> 中位 Rank_IC 在三个 target 上分别为 -0.0262、-0.0211、-0.0150，与“低算法关注标的获得流动性折价 / 风险补偿”方向一致；但 Q2 全部翻正，不能据此宣称存在稳定机制。</p></div><div><b>根因诊断应转向风格与市场状态</b><p>优先对市值、价格、换手、成交额、买卖价差、波动率、开盘 gap、停牌与涨跌停做横截面中性化，并检查滚动日度 IC 与底部 5% / 10% / 20% 非线性分组。</p></div><div><b>保留 cond 与 coverage 作为诊断列</b><p><code>_c_all</code> 是主因子；<code>_c_cond</code> 与 <code>coverage_count</code> 用于区分行为浓度和可判断状态。coverage 本身也携带市场状态，不应被当作纯技术噪声。</p></div><div><b>综合关注度必须避免重复计数</b><p>最佳方案是在订单级保存 54 类痕迹 bitmask / 分数向量，用 <code>any(trace)</code>、逐订单 max 或校准 union 后再除以全订单数。只有面板时可按经济行为族做 rank-PCA，但只能称关注强度潜变量。</p></div></div>
  </div>
</div>
<details class="legacy-ranking"><summary>展开历史 165 口径排名（旧条件分母，仅供审计）</summary><div class="legacy-ranking-body"><p class="legacy-warning">以下互动表来自各日期原报告：同时包含 c/q/a，使用“可判断订单”条件分母，且只有原 09:44–09:45 target。它们不再代表当前主研究结论；保留仅为追溯当时的计算和说明。</p><div class="grid-3" id="ranking-leaders"></div><div id="ranking-tables"></div><div class="callout"><div><strong>历史 Top 20 交集不再用于当前候选池判断。</strong><p>当前筛选应以 54 个 <code>_c_all</code> 因子的三 target、三时期对照和后续中性化结果为准。</p><div class="overlap" id="overlap"></div></div></div></div></details>
</section>"""


GUIDE_JS = r"""
function formulaGuide(idea){
  const guide=idea.formula_guide,glossary=R.formula_glossary;
  if(!guide||!glossary)throw new Error(`${idea.idea_id}: formula guide is missing`);
  const rows=guide.term_keys.map(key=>{
    const term=glossary[key];
    if(!term)throw new Error(`${idea.idea_id}: unknown formula term ${key}`);
    return `<tr><td>${esc(term.symbol)}</td><td>${esc(term.definition)}</td><td>${esc(term.unit)}</td><td>${esc(term.source)}</td></tr>`;
  }).join('');
  return `<section class="formula-guide"><div class="formula-guide-head"><div><b>公式逐项解释 · 可独立阅读</b><p>${esc(guide.reading)}</p></div><span class="formula-guide-badge">${rows?guide.term_keys.length:0} 项已定义</span></div>
    <div class="formula-guide-table-wrap"><table class="formula-term-table"><thead><tr><th>符号 / 组件</th><th>精确定义与计算方式</th><th>单位 / 范围</th><th>本报告取值与来源</th></tr></thead><tbody>${rows}</tbody></table></div>
    <div class="formula-guide-notes"><div><b>聚合口径：</b>${esc(guide.aggregation)}</div><div><b>0 与 NA：</b>${esc(guide.zero_na)}</div></div></section>`;
}
""".strip()


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one target, found {count}")
    return text.replace(old, new, 1)


def patch_formula_runtime(html: str) -> str:
    html = re.sub(
        r'\n?<meta name="formula-explanations" content="[^"]+">',
        "",
        html,
    )
    html = _replace_once(
        html,
        '<meta name="color-scheme" content="light">',
        '<meta name="color-scheme" content="light">\n'
        f'<meta name="formula-explanations" content="{SCHEMA_VERSION}">',
        "formula explanation build metadata",
    )
    if ".formula-guide{" not in html:
        html = _replace_once(
            html,
            ".evidence-tags strong{display:block;font:800 10px var(--mono);color:var(--ink);margin-bottom:4px}",
            ".evidence-tags strong{display:block;font:800 10px var(--mono);color:var(--ink);margin-bottom:4px}\n"
            + GUIDE_CSS
            + "\n"
            + CURRENT_RESEARCH_CSS,
            "formula guide styles",
        )
    elif ".research-update{" not in html:
        html = _replace_once(
            html,
            GUIDE_CSS,
            GUIDE_CSS + "\n" + CURRENT_RESEARCH_CSS,
            "current research summary styles",
        )
    if "function formulaGuide(idea){" not in html:
        html = _replace_once(
            html,
            "function variantTable(idea){",
            GUIDE_JS + "\n\nfunction variantTable(idea){",
            "formula guide renderer",
        )
    if "${formulaGuide(idea)}" not in html:
        html = _replace_once(
            html,
            "      </div>\n      ${variantTable(idea)}${evidenceBlocks(idea)}",
            "      </div>\n      ${formulaGuide(idea)}\n      ${variantTable(idea)}${evidenceBlocks(idea)}",
            "formula guide placement",
        )
    html = html.replace("\\theta_{t}", "\\theta_{\\mathrm{wall}}")
    html = html.replace("\\theta_{e}", "\\theta_{\\mathrm{event}}")
    return html


def patch_current_research_summary(html: str) -> str:
    matches = list(RANKING_SECTION_RE.finditer(html))
    if len(matches) != 1:
        raise RuntimeError(f"expected one ranking section, found {len(matches)}")
    match = matches[0]
    return html[: match.start()] + CURRENT_RESEARCH_HTML + html[match.end() :]


def serialize_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )


def enrich_report_html(html: str) -> str:
    matches = list(REPORT_DATA_RE.finditer(html))
    if len(matches) != 1:
        raise RuntimeError(f"expected one report-data block, found {len(matches)}")
    match = matches[0]
    payload = json.loads(match.group(2))
    apply_formula_explanations(payload)
    html = html[: match.start(2)] + serialize_payload(payload) + html[match.end(2) :]
    html = patch_formula_runtime(html)
    return patch_current_research_summary(html)


def enrich_report_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    enriched = enrich_report_html(original)
    if enriched == original:
        return False
    path.write_text(enriched, encoding="utf-8", newline="\n")
    return True
