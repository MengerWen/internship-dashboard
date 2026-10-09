"""Render the 601-day calibration report from sealed aggregate results."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSET = "assets/grouped-calibration-2026-10-07"
DATA = ROOT / "content" / ASSET / "aggregates.json.gz"
KERNELS = {
    "theta_wall_seconds": "时间",
    "theta_events": "序号",
    "theta_qty": "数量",
    "theta_price_ticks": "价格",
    "theta_bbo_ticks": "BBO",
    "theta_marketability_ticks": "marketability",
}
SCHEMES = {
    "shared": "深市共用", "single_stock": "单股参照",
    "single_stock_price": "单股×价格档参照", "board": "板块",
    "rq_industry": "申万行业", "size_liquidity_grid": "市值×流动性 2×3",
    "rq_one_month_share_turnover": "月换手率", "log_amount_20d": "20日成交额",
    "log_trades_20d": "20日成交笔数", "pred_slim": "精简预测中心",
    "pred_full": "完整预测中心", "pred_daily": "日线预测中心",
    "log_prev_close": "前收盘价", "log_lots_per_trade_20d": "20日每笔成交手数",
    "rq_size": "米筐市值", "price_fixed": "固定价格边界", "log_tick_move": "风险×价格/tick",
}
FEATURES = {
    "log_trades_t1": "前一日总成交笔数", "log_amount_t1": "前一日总成交额",
    "log_range_t1": "前一日振幅", "log_gap_t1": "前一日跳空绝对值",
    "log_lots_t1": "前一日每笔成交量", "log_trades_mean5_t1": "前5日成交笔数",
    "log_amount_mean5_t1": "前5日成交额", "log_range_mean5_t1": "前5日振幅",
    "log_gap_mean5_t1": "前5日跳空绝对值", "log_lots_mean5_t1": "前5日每笔成交量",
}
MODES = {"reference": "参照", "equal_frequency": "等频", "prediction_equal_width": "预测值等距"}


def num(value, places=4):
    return "—" if value is None else f"{value:.{places}f}"


def count(value):
    return "—" if value is None else f"{int(value):,}"


def percent(value, places=2):
    return "—" if value is None else f"{100 * value:.{places}f}%"


def table(headers, rows):
    def line(row):
        return "| " + " | ".join(str(x).replace("|", "\\|") for x in row) + " |"
    return "\n".join([line(headers), line(["---"] * len(headers)), *(line(row) for row in rows)])


def folded(title, body):
    return f'??? note "{title}"\n' + "\n".join("    " + line if line else "" for line in body.splitlines())


def image(name, caption):
    return f"![{caption}]({ASSET}/{name}.png)"


def one(rows, **keys):
    selected = [row for row in rows if all(row.get(key) == value for key, value in keys.items())]
    if len(selected) != 1:
        raise ValueError(f"Expected one aggregate row: {keys}; got {len(selected)}")
    return selected[0]


def render():
    data = json.loads(gzip.decompress(DATA.read_bytes()))
    source = data["source"]
    seal = source["seal"]
    assert seal["sealed"] and seal["hash_check_exit_code"] == 0 and all(source["checks"].values())
    assert source["date_count"] == 601 and source["stock_days"] == 1719612
    assert len(data["stock_curves"]) == 360 and len(data["cell_errors"]) == 6240
    for path, sha in source["plot_sha256"].items():
        local = ROOT / "content" / ASSET / Path(path).name
        assert hashlib.sha256(local.read_bytes()).hexdigest() == sha

    distribution = table(
        ["尺度", "单位", "正值中心股票日", "占全部股票日", "m 的 P10", "m 的中位数", "m 的 P90", "零距离配对占比"],
        [[KERNELS[row["kernel"]], {"theta_wall_seconds": "秒", "theta_events": "事件序号", "theta_qty": "log数量距离"}.get(row["kernel"], "tick"),
          count(row["positive_days"]), percent(row["positive_days"] / source["stock_days"]),
          *(num(row[key], 6 if row["kernel"] == "theta_qty" else 2) for key in ["p10", "p50", "p90"]),
          percent(row["zero_pairs"] / (row["positive_pairs"] + row["zero_pairs"]))] for row in data["distributions"]],
    )
    slopes = table(["尺度", "前收盘价区间", "log-log 斜率", "有效股票日"],
                   [[KERNELS[row["kernel"]], "低于5元" if row["price_range"] == "lt5" else "不低于5元", num(row["slope"]), count(row["stock_days"])] for row in data["price_slopes"]])
    mechanism = table(["尺度/目标", "股票特征", "Spearman相关", "有效股票日"],
                      [[KERNELS[row["kernel"]] + ("零值比例" if row["outcome"] == "qty_zero_fraction" else "中心"),
                        SCHEMES.get(row["feature"], row["feature"]), num(row["spearman"]), count(row["stock_days"])] for row in data["mechanism_correlations"]])
    atoms = table(["数量距离 m", "股票日", "是否对应 ln((k+1)/k)"],
                  [[num(row["median"], 8), count(row["stock_days"]), "k=" + str(int(row["ln_ratio_k"])) if row["ln_ratio_k"] is not None else "未命中"] for row in data["quantity_atoms"]])
    variance = table(["尺度", "日期效应", "股票效应", "残差", "协方差余项"],
                     [[KERNELS[row["kernel"]], *(percent(row[key]) for key in ["date_effect_share", "stock_effect_share", "residual_share", "covariance_remainder_share"])]
                      for row in data["variance"] if row["stock_key"] == "code" and row["weighting"] == "stock_equal"])
    predictions = table(["尺度", "精简版", "完整版本", "日线版", "精简版+市场成交笔数"],
                        [[KERNELS[kernel], *(num(next((row["oof_fit"] for row in data["prediction_scores"] if row["kernel"] == kernel and row["model"] == model and row["selected_penalty"]), None))
                                            for model in ["slim", "full", "daily", "slim_market"])] for kernel in list(KERNELS)[:5]])
    penalties = table(["尺度", "完整版本的惩罚强度", "样本外拟合度"],
                      [[KERNELS[row["kernel"]], row["alpha"], num(row["oof_fit"])] for row in data["prediction_scores"] if row["model"] == "full" and row["selected_penalty"]])
    coefficient_ranges = table(["尺度", "市场成交笔数系数，5折最小值", "5折最大值"],
                               [[KERNELS[kernel], num(min(row["coefficient"] for row in data["coefficients"] if row["kernel"] == kernel and row["feature"] == "log_trades_t1")),
                                 num(max(row["coefficient"] for row in data["coefficients"] if row["kernel"] == kernel and row["feature"] == "log_trades_t1"))] for kernel in list(KERNELS)[:2]])
    stock_examples = []
    for kernel in KERNELS:
        candidates = ["shared"] + (["log_trades_20d", "pred_slim"] if kernel in list(KERNELS)[:2]
                                   else ["log_prev_close", "pred_slim"] if kernel != "theta_marketability_ticks" else ["log_prev_close"])
        for scheme in candidates:
            row = one(data["stock_curves"], kernel=kernel, scheme_id=scheme, mode="reference" if scheme == "shared" else "equal_frequency", requested_k=1 if scheme == "shared" else 6)
            stock_examples.append([KERNELS[kernel], SCHEMES[scheme], "1" if scheme == "shared" else "6", num(row["stock_equal__abs_e_median"]), num(row["stock_equal__abs_e_p90"]),
                                   num(row["stock_equal__abs_v_median"]), percent(row["stock_equal__v_zero_fraction"]), count(row["distinct_centers"])])
    stock_table = table(["尺度", "方案", "请求档数", "|e|中位数", "|e| P90", "|v|中位数", "v=0股票占比", "不同组中心数"], stock_examples)
    annual_examples = []
    for kernel in KERNELS:
        scheme = "log_prev_close" if kernel == "theta_marketability_ticks" else "pred_slim"
        rows = [row for row in data["annual_centers"] if row["kernel"] == kernel and row["scheme_id"] == scheme
                and row["requested_k"] == 6 and row["mode"] == "equal_frequency"]
        for group in dict.fromkeys(row["group"] for row in rows):
            values = []
            for year in ["2024", "2025", "2026"]:
                row = next((row for row in rows if row["group"] == group and row["year"] == year), None)
                values.append(num(row["center"], 6 if kernel == "theta_qty" else 3) + " / " + count(row["stock_count"]) if row else "—")
            annual_examples.append([KERNELS[kernel], count(group), *values])
    annual_table = table(["尺度", "组（原表编号）", "2024：m / 正值股票数", "2025：m / 正值股票数", "2026H1：m / 正值股票数"], annual_examples)
    complete_stock = []
    for kernel in KERNELS:
        rows = [row for row in data["stock_curves"] if row["kernel"] == kernel]
        identities = list(dict.fromkeys((row["scheme_id"], row["mode"]) for row in rows))
        matrix = []
        for scheme, mode in identities:
            group = [row for row in rows if (row["scheme_id"], row["mode"]) == (scheme, mode)]
            label = SCHEMES.get(scheme, scheme)
            if len(group) == 1 and group[0]["actual_k"] is not None:
                label += f"（实际{int(group[0]['actual_k'])}档）"
            matrix.append([label, MODES[mode], *(num(next((row["stock_equal__abs_e_median"] for row in group if row["requested_k"] == k), None)) for k in [1, 2, 3, 4, 5, 6, 8, 10, 12])])
        complete_stock.append("### " + KERNELS[kernel] + "\n\n" + table(["方案", "边界", "参照/1", "2", "3", "4", "5", "6", "8", "10", "12"], matrix))
    market_curve = table(["尺度", "相关系数", "Kₘ=1", "2", "3", "4", "5", "6", "8"],
                         [[KERNELS[kernel], num(one(data["market_correlations"], kernel=kernel, feature="log_trades_t1")["pearson"]),
                           *(num(one(data["market_curves"], kernel=kernel, feature="log_trades_t1", requested_k=k)["quarter_loo_abs_log_error"]) for k in [1, 2, 3, 4, 5, 6, 8])] for kernel in KERNELS])
    all_market = []
    for kernel in KERNELS:
        all_market.append("### " + KERNELS[kernel] + "\n\n" + table(["市场特征", "相关系数", "Kₘ=1", "2", "3", "4", "5", "6", "8"],
                         [[label, num(one(data["market_correlations"], kernel=kernel, feature=feature)["pearson"]),
                           *(num(one(data["market_curves"], kernel=kernel, feature=feature, requested_k=k)["quarter_loo_abs_log_error"]) for k in [1, 2, 3, 4, 5, 6, 8])] for feature, label in FEATURES.items()]))
    cells = []
    for kernel in KERNELS:
        scheme = "log_prev_close" if kernel == "theta_marketability_ticks" else "pred_slim"
        for market_k in [1, 4]:
            keys = dict(kernel=kernel, scheme_id=scheme, requested_k=6, mode="equal_frequency", market_feature="log_trades_t1", market_k=market_k)
            row = one(data["cell_errors"], **keys)
            support = one(data["cell_support_summary"], **keys)
            cells.append([KERNELS[kernel], "6×" + str(market_k), num(row["stock_equal__abs_e_median"]), num(row["stock_equal__abs_e_p90"]), percent(row["fallback_stock_day_fraction"]),
                          count(support["stocks_min"]), count(support["pairs_min"]), count(support["unsupported_cell_days"])])
    cell_table = table(["尺度", "股票档×市场档", "|e|中位数", "|e| P90", "回退股票日占比", "单元日最少正值股票", "最少正值配对", "无支持单元日"], cells)
    coverage = table(["输入", "覆盖率", "缺失股票日"],
                     [[label, percent(source["input_coverage"][key], 4), count(round(source["stock_days"] * (1 - source["input_coverage"][key])))]
                      for label, key in [("前收盘价", "log_prev_close"), ("申万行业", "rq_industry"), ("特异风险", "log_specific_risk"), ("沪深300 beta", "raw_beta"), ("十项市场变量", "log_trades_t1")]])
    timing = table(["分析阶段", "原版实测", "提速版实测"], [
        ["预测中心拟合", "40.91分钟", "27.78分钟"], ["股票层", "3.14分钟", "2.87分钟"],
        ["机制检查", "运行约67分钟，仍未完成", "9.02分钟"], ["市场层", "未执行", "0.71秒"],
        ["交叉单元", "未执行", "9.07分钟"], ["方差与结果写出", "未执行", "112.10秒"],
        ["绘图", "未执行", "2.37秒"], ["完整分析guard", "约111分钟，停止时仍未完成", "51.60分钟"],
    ])
    sections = []
    sections.append("""## 这次预检回答什么

老因子的衰减参数要由典型配对距离换算。若所有股票、所有市场状态共用一个尺度，就会把不同股价、活跃程度和市场状态混在一起。本次比较“股票分组 × 市场分组”后，尺度偏差是否缩小、每个分组是否有足够样本。

范围为 **2024-01-02 至 2026-06-30，深市普通 A 股，601 个交易日、1,719,612 个股票日**。原计划的200日抽样已经扩为全601日。六类尺度分别是时间、事件序号、数量、价格、BBO距离和marketability距离。这里只做定标结构预检，不计算因子收益或IC，不自动选定最终档数。

报告归档日期为2026-10-07。全期分析实际于2026-10-09 19:56完成，20:05验收封存。与2026-08-31历史归档相比，股票日数全部一致，但**261个日期的时间或序号日级中心不同**：时间235日，序号261日。以下结果来自本次冻结输入，不能称为与历史归档完全一致。
""")
    sections.append("""## 口径：先理解中心、误差和留一

每个股票日先取正距离的中位数，再取同组当天跨股票中位数，最后取全期中位数得到组中心m；衰减参数为 **θ=m/ln(2)**。下文分布表列的是m，不是已经换算的θ。数量距离的单位是log数量距离，整数距离的偶数样本中位数可以是半整数。

股票分组只使用开盘前已知的特征：米筐、日线取前一交易日，价格取当日已知的前收盘价。等频边界使每只股票的全期总权重相同；预测中心另做1%—99%区间内的等距边界。固定价格边界为5、10、20、40元。重复边界合并，缺失特征不填补，回退到深市共用中心。

评价一只股票时先把它从组中心的估计中剔除，即股票留一。e先取该股逐日log尺度偏差的中位数，再跨股票汇总|e|；它衡量长期偏高或偏低，**不是逐日绝对误差的平均**。v检查归一化距离在1两侧是否覆盖中位数；整数距离用严格小于和小于等于两个比例处理并列。主结果股票等权，聚合文件同时保留按有效股票日数加权的结果。

股票层K网格为1、2、3、4、5、6、8、10、12；市场层为1、2、3、4、5、6、8；交叉单元为股票K={2,3,4,6,8} × 市场Kₘ={1,2,3,4,5,6}。所有方案按登记顺序展示。
""")
    sections.append("## 六类中心的分布与正值支持\n\n" + distribution + "\n\n数量配对中93%以上的距离为零；marketability的零距离配对占比超过99.9%，只有约12.6%的股票日存在正值中心。零距离与没有正值中心是不同统计，不能把缺失中心当成零来拟合。数量中心的常见值有明显离散结构，常见值与ln((k+1)/k)的对照见下表。\n\n" + folded("数量中心最常见的20个取值", atoms))
    sections.append("## 机制检查：股票活跃度、股价与tick\n\n时间中心与20日成交笔数的股票日Spearman相关为0.0884，序号为0.1648；这一截面关系弱于后文的市场日级关系。价格、BBO中心与前收盘价的相关分别为0.7387和0.7646。数量零值比例与股价相关0.6169，与每笔成交手数相关−0.7614。相关性描述共同变化，不证明因果。\n\n" + slopes + "\n\n5元以下两条中位数回归斜率均为0；不低于5元时，价格为0.7808，BBO为0.9882。该分段结果提示tick离散性需要单独观察，不能把高价区间的关系直接外推到低价区间。\n\n" + folded("全部机制相关与六类原图", mechanism + "\n\n" + "\n\n".join(image("mechanism_" + kernel, KERNELS[kernel] + "机制检查：20个等频箱中位数") for kernel in KERNELS)))
    sections.append("## 方差分解：股票差异与日期差异\n\n" + variance + "\n\n按物理股票代码、股票等权统计，价格和BBO的股票效应占比分别为53.26%和63.05%，时间只有3.00%；序号的日期效应占17.11%。价格、BBO和数量另有“股票×固定价格档”版本，及股票日等权版本，保存在聚合文件。这里的效应由中位数和均值构造，并非正交分解，所以保留协方差余项，余项可以为负；三项不能单独当作相加等于100%的解释度。")
    sections.append("## 预测中心：样本外拟合与系数稳定性\n\n用股票5折交叉拟合中位数回归，种子20261008；每折最多按股票权重抽60,000个训练股票日。本次各折实际达到这个上限。精简版、完整20项v2trd风格加行业、日线版均保留；时间和序号另加入前一日市场总成交笔数。下表拟合度为1−加权绝对残差/加权基准绝对残差，不是R²，也不是收益表现。\n\n" + predictions + "\n\n加入市场成交笔数后，时间的样本外拟合度从0.0118变为0.0264，序号从0.0219变为0.1620；价格和BBO的精简版分别为0.4225和0.4658。完整版没有在所有尺度上提高拟合度，不能以特征更多代替结果核对。\n\n" + penalties + "\n\n完整版在{0,0.0001,0.001,0.01}中按外层样本外拟合度选择惩罚强度，全部25组模型/惩罚组合均保留。这是拟合程序的既定选择规则，不是本报告对股票分组方案的推荐。市场成交笔数项的原量纲系数范围如下；其余系数、标准化系数和折间范围见聚合文件。\n\n" + coefficient_ranges)
    sections.append("## 股票层：档数、偏差与整数并列\n\n" + image("stock_curves", "六类股票层档数曲线；虚线为参照，纵轴为跨股票|e|中位数") + "\n\n为便于横向阅读，下表固定展示K=6和深市共用参照。**K=6仅是展示切片，不是建议档数**；全部档数和登记方案在折叠表与聚合文件中。\n\n" + stock_table + "\n\n价格、BBO、数量等离散中心的|e|中位数可能已经为0，但P90仍大于0，v=0也没有覆盖所有股票。请求6档还可能只有4或5个不同中心，所以不能仅凭中位数为0或请求档数判断分组已经充分。\n\n" + folded("全部股票层|e|中位数曲线，按登记顺序", "固定类别方案只有其实际分法，数值显示在“参照/1”列；空白表示未登记该档数，不是零。\n\n" + "\n\n".join(complete_stock)))
    sections.append("## 市场层：前一日成交笔数与季度留一曲线\n\n市场层先取每天跨股票中位数，再比较其log中心与开盘前市场变量。以下相关为601个日级观察的Pearson相关，和前面的股票日Spearman相关不同。误差为留出一个季度后的平均绝对log误差。\n\n" + market_curve + "\n\n前一日市场成交笔数与时间、序号日级中心相关分别为0.8173、0.8972。时间的季度留一误差从0.0581（1档）到0.0331（4档）；序号从0.2509到0.1253。其余尺度的曲线并非随档数单调下降，例如marketability的1档与2档都为0.1793，4档为0.1956；不能统一按档数越多越好处理。\n\n" + image("market_curves", "六类尺度对十项市场变量的季度留一分档误差") + "\n\n" + folded("十项市场变量的全部相关与档数曲线", "\n\n".join(all_market) + "\n\n" + image("market_scatter", "日级中心与市场变量散点，601个日级汇总点")))
    sections.append("## 股票层×市场层：误差改善与支持量同时检查\n\n本次完成6,240组交叉方案评价。下表统一取股票K=6、市场变量为前一日总成交笔数，比较市场1档和4档；时间、序号、数量、价格和BBO用精简预测中心，marketability用前收盘价。这个统一切片仅供阅读，其余市场变量、档数和边界方案全部保留。\n\n" + cell_table + "\n\nmarketability在这个切片中回退占比从1.63%升到7.29%，单元日最少只有3只正值股票、8个正值配对。表中“无支持单元日”按整个组检查，股票留一之后仍可能需要回退，两者不是同一指标。回退比例按全部股票日计；不能仅看|e|中位数为0就认为支持充足。")
    sections.append("## 年度中心与支持量\n\n各组中心分别按2024、2025、2026H1计算，使用同一全期分组边界。下面沿用前述K=6切片，列出每组的年度中心m和当年出现过正值中心的股票数。它用于观察年度变化，不是滚动重新拟合，也不构成年度稳定性已经通过的判定。全部方案的年度中心、有效股票日数、日期数、正值配对数及分档边界保存在聚合文件。\n\n" + folded("K=6年度中心与正值股票数", annual_table))
    sections.append("## 输入覆盖、运行效率与验收\n\n" + coverage + "\n\n四个米筐API的请求、返回日期均为对应t−1；601日日期检查通过。行业和特异风险各缺109个股票日，前收盘价缺54个；沪深300 beta缺111,170个。缺失保留，不补成0；用到缺失特征的方案记录回退。十项市场变量均为100%覆盖。\n\n" + timing + "\n\n提速复用了原L2、米筐和面板，只重跑分析。预测阶段减少32.1%的时间；价格段回归并行，同折标准化、抽样和重复中心计算复用。原版全量没有结束，因此不能给出整次运行的精确加速倍数。两日真实面板逐表对照中，20张表数值差异为零，价格斜率最大差异1.11×10⁻¹⁶；该对照不是601日原版全量重算。63项相关测试通过。\n\n正式guard限100GiB，账户16核；内存峰值29.80GiB、平均有效10.07核，guard与sentinel退出码均为0，无OOM。21张Parquet、21张CSV、9张图、5段恢复点完整；709个文件通过哈希核对后写入SEALED.json，封存后未修改运行根目录。")
    source_links = "[完整聚合指标（压缩JSON）](" + ASSET + "/aggregates.json.gz)"
    provenance = {
        "report_date": "2026-10-07", "actual_sealed_at_utc": seal["sealed_at_utc"],
        "source": source, "aggregate_gzip_sha256": hashlib.sha256(DATA.read_bytes()).hexdigest(),
        "privacy": "aggregate tables and figures only; no individual-stock predictions, errors, or raw L2 records",
    }
    (ROOT / "content" / ASSET / "source.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    identity_block = "\n".join([
        "科学版本=" + seal["revision"],
        "输入生产版本=" + seal["input_checkout_revision"],
        "分析执行版本=" + seal["checkout_revision"],
        "配置=因子/algobench/configs/grouped_calibration_precheck_szse_601_v1.yaml",
        "配置SHA-256=" + seal["config_sha256"],
        "面板SHA-256=" + seal["panel_sha256"],
        "wangly结果目录=" + source["run_root"],
    ])
    sections.append("## 复现位置与解释边界\n\n科学版本为`" + seal["revision"][:8] + "`，输入生产版本为`" + seal["input_checkout_revision"][:8] + "`，分析执行版本为`" + seal["checkout_revision"][:8] + "`。完整身份和位置如下：\n\n```text\n" + identity_block + "\n```\n\n页面附件：" + source_links + "；[来源、版本与哈希](" + ASSET + "/source.json)。\n\n网站只保存聚合表和图，不上传逐股票日预测、逐股误差、原始逐笔或面板。聚合数字序列化保留10位小数，页面再按表格精度显示；严格逐字节复核以服务器封存文件及其哈希为准。\n\n股票交叉拟合按股票分折，不按时间滚动；组中心和边界来自全期定标资料。这份预检用于比较定标结构，不构成历史样本外策略效果证明。收益、IC、核权重变化、101分位点和配对直方图不在本次计算范围内。最终股票档数、市场档数及边界仍由研究者结合误差、支持量和年度稳定性决定。")
    frontmatter = '''---
title: "六类尺度分组定标：深市601日预检"
date: 2026-10-07
published: 2026-10-07 12:00:00
stage: algo-footprint
summary: "601日、171.96万股票日的六类尺度预检已验收封存：比较股票分组、市场状态、预测中心与交叉单元支持；分析用时51.6分钟，历史归档中心差异单列。"
---

# 六类尺度分组定标：深市601日预检

'''
    daily = ROOT / "content/daily/2026-10-07.md"
    daily.write_text(frontmatter + "\n\n".join(sections) + "\n", encoding="utf-8", newline="\n")
    show = '''---
title: "深市601日：分组定标预检"
---

## 601日预检已完成，档数仍待判断

2024-01-02—2026-06-30，601个交易日、1,719,612个股票日；时间、序号、数量、价格、BBO和marketability六类尺度。

股票日数与历史归档一致，261日时间或序号中心不同。全量分析10月9日完成并封存，本页归档在10月7日。

研究问题是：相似股票在相似市场状态下分组，是否能减小尺度偏差，同时保留充分支持量。本次不选定最终K，不评价收益或IC。

## 正值支持差异很大

''' + distribution + "\n\n表中为正距离中位数m，衰减参数θ=m/ln(2)。marketability仅约12.6%的股票日有正值中心，数量零距离配对超过93%；缺失中心不填成零。\n\n## 股票层：不能只看中位数为零\n\n" + image("stock_curves", "六类股票层误差曲线") + "\n\n价格、BBO与股价的股票日相关分别为0.7387和0.7646；5元以上的log-log斜率为0.7808和0.9882。整数距离会出现并列中心，需要同时看P90、v和实际不同中心数。\n\n## 市场状态：时间与序号相关较强\n\n" + market_curve + "\n\n前一日市场成交笔数与时间、序号日级中心相关0.8173、0.8972。序号预测中心加入市场成交笔数后，样本外拟合度由0.0219变为0.1620。档数曲线不都单调，不能统一增加档数。\n\n## 交叉分组：误差与回退一起看\n\n" + cell_table + "\n\n统一展示股票6档、市场1/4档，不代表推荐。这一切片中marketability回退1.63%→7.29%，最少仅3只正值股票、8个配对；中位数为0并不代表支持充分。\n\n## 运行已验收，恢复点已保存\n\n" + timing + "\n\n21张表、9张图、5段恢复点，709个文件哈希通过；无OOM，内存峰值29.80GiB。分析总用时51.6分钟，预测阶段40.9→27.8分钟。只重跑分析，原取数与面板保留。\n\n## 查看正文与完整聚合指标\n\n正文包含方差分解、13个模型的预测中心比较、全部登记方案的K曲线、十项市场变量、输入覆盖和版本哈希。\n\n" + source_links + "\n\n股票分折与全期定标资料不构成按时间滚动的策略样本外验证；历史归档差异继续保留，最终档数由研究者判断。\n"
    (ROOT / "content/daily/2026-10-07.show.md").write_text(show, encoding="utf-8", newline="\n")
    print(json.dumps({"report": str(daily), "sections": len(sections), "show_scenes": 7, "figures": len(source["plot_sha256"]), "aggregate_bytes": DATA.stat().st_size}))


if __name__ == "__main__":
    render()
