from __future__ import annotations

import html
import math
import shutil
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ALGO_ROOT = Path(r"D:\MG\！Internship\26 Summer\❗思瑞投资\因子\algobench")
OUT = ALGO_ROOT / "outputs"
IMAGE_SRC = Path(r"D:\MG\==OBrepository==\Quant & Internship\26 Summer\！思瑞投资\因子\找算法痕迹\6docs\6docs修改后结果_files")
ASSET_DIR = ROOT / "site" / "assets" / "algo-footprint-2026-07-07"
OUTPUT_HTML = ROOT / "content" / "daily" / "2026-07-07.show.html"


IMAGE_NAMES = [
    "cell_0007_output_0002.png",
    "cell_0010_output_0003.png",
    "cell_0013_output_0002.png",
    "cell_0014_output_0002.png",
    "cell_0017_output_0003.png",
    "cell_0017_output_0004.png",
    "cell_0020_output_0005.png",
    "cell_0020_output_0006.png",
    "cell_0020_output_0007.png",
    "cell_0020_output_0008.png",
    "cell_0023_output_0002.png",
    "cell_0024_output_0002.png",
    "cell_0025_output_0003.png",
    "cell_0025_output_0004.png",
    "cell_0027_output_0002.png",
    "cell_0027_output_0003.png",
]


PAPERS = {
    "hjm": ("HJM", "Hendershott, Jones & Menkveld (2011, JF)", "https://faculty.haas.berkeley.edu/hender/Algo.pdf"),
    "kx": ("KX", "Stanton-Cook et al. (KX 监察白皮书)", "https://code.kx.com/q/wp/surveillance/"),
    "ccp": ("CCP", "Chakrabarty, Comerton-Forde & Pascual (2023)", "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4551238"),
    "ee": ("EE", "Ersan & Ekinci (2017)", "https://www.sciencedirect.com/science/article/pii/S1544612317303926"),
    "kkst": ("KKST", "Kirilenko, Kyle, Samadi & Tuzun (2017, JF)", "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1686004"),
    "gb": ("GB", "Goudarzi & Bazzana (2023)", "https://www.sciencedirect.com/science/article/pii/S0275531923002040"),
}


METRIC_CLUSTERS = {
    "短生命/快速撤单": [
        "ee__step1_share", "ee__hft_ratio", "ee__flag_qty_share",
        "kx__short_cancel_lt_1s", "kx__short_cancel_lt_10s",
        "kx__life_p10", "kx__life_p25", "kx__life_p50", "kx__life_p75", "kx__life_p90",
        "ccp__fleet",
    ],
    "链式重复下单": ["ccp__sruns", "gb__seed_pos"],
    "消息强度/OTR": ["kx__otr_day", "ccp__mess", "ccp__can", "hjm__msg_per_volume"],
    "盘口扰动/簇发": ["kx__burst_count", "kx__burst_seconds", "ccp__quoteint", "ccp__flick"],
    "事件响应速度": ["ccp__sresp", "kkst__newlevel_maker_lift"],
    "主动成交/知情性": [
        "ccp__ioc", "kkst__aggressive_ratio_flagged", "kkst__snipe_taker_lift",
        "kkst__flow_price_beta_lag0", "kkst__flow_price_beta_lag1", "kkst__flow_price_beta_lag2",
        "kkst__flow_price_beta_lag3", "kkst__flow_price_beta_lag4", "kkst__flow_price_beta_lag5",
        "kkst__flow_price_beta0",
    ],
    "成交经济后果": ["hjm__espread_bps", "hjm__rspread_bps", "hjm__advsel_bps", "hjm__trade_size"],
    "撤单-成交交互(fade)": ["kx__fade_full_prob", "kx__fade_partial_prob"],
    "GB 模型综合": ["gb__sum_p", "gb__sum_p_amount", "gb__seed_neg"],
}


METRIC_TIPS = {
    "ee__hft_ratio": "EE 两步法（快撤并关联传染）标记订单占全部订单的比例",
    "ee__step1_share": "提交后 1 秒内撤单的订单比例（EE 第一步）",
    "ee__flag_qty_share": "EE 标记订单的报单量占全部报单量的比例",
    "kx__otr_day": "全天（报单+撤单）除以成交笔数，消息-成交比",
    "kx__burst_count": "L1 盘口变动突破阈值的簇发事件个数（quote stuffing 候选）",
    "kx__burst_seconds": "上述簇发状态的累计持续秒数",
    "kx__fade_full_prob": "成交后短窗口内同侧同价撤单量不小于成交量的概率（完全 fade）",
    "kx__fade_partial_prob": "成交后短窗口内出现任何同侧同价撤单的概率（部分 fade）",
    "kx__short_cancel_lt_1s": "寿命小于 1 秒且被撤订单的比例",
    "kx__short_cancel_lt_10s": "寿命小于 10 秒且被撤订单的比例",
    "kx__life_p10": "订单寿命分布的 10 分位数（秒）；本样本恒为 0，已退化",
    "kx__life_p25": "订单寿命分布的 25 分位数（秒）；本样本恒为 0，已退化",
    "kx__life_p50": "订单寿命分布的 50 分位数（秒）",
    "kx__life_p75": "订单寿命分布的 75 分位数（秒）",
    "kx__life_p90": "订单寿命分布的 90 分位数（秒）",
    "ccp__mess": "BBO 附近的报单+撤单消息计数（未归一化）",
    "ccp__can": "BBO 附近的撤单计数（mess 的子集）",
    "ccp__fleet": "寿命小于 1 秒且被撤的闪现订单计数",
    "ccp__ioc": "主动吃单（taker）订单计数",
    "ccp__sresp": "报价改善后短窗口内的快速响应事件计数",
    "ccp__sruns": "撤单后快速重挂形成的策略性链条数",
    "ccp__quoteint": "L1 盘口发生变动的秒数计数（报价强度）",
    "ccp__flick": "桶内 1 秒中间价标准差（报价闪烁幅度）",
    "kkst__aggressive_ratio_flagged": "被标记订单的主动成交量占全部主动成交量的比例",
    "kkst__snipe_taker_lift": "不利价格变动前，可疑 taker 成交占比相对基准的提升",
    "kkst__newlevel_maker_lift": "盘口变动后，被标记订单在新报单中的占比相对基准的提升",
    "kkst__flow_price_beta_lag0": "被标记订单带符号成交流对未来 0 秒中间价变动的回归系数",
    "kkst__flow_price_beta_lag1": "被标记订单带符号成交流对未来 1 秒中间价变动的回归系数",
    "kkst__flow_price_beta_lag2": "被标记订单带符号成交流对未来 2 秒中间价变动的回归系数",
    "kkst__flow_price_beta_lag3": "被标记订单带符号成交流对未来 3 秒中间价变动的回归系数",
    "kkst__flow_price_beta_lag4": "被标记订单带符号成交流对未来 4 秒中间价变动的回归系数",
    "kkst__flow_price_beta_lag5": "被标记订单带符号成交流对未来 5 秒中间价变动的回归系数",
    "kkst__flow_price_beta0": "等于 beta_lag0 的代码级复制（冗余）",
    "hjm__espread_bps": "有效价差（成交价相对当时中间价的偏离，bps）",
    "hjm__rspread_bps": "已实现价差（成交价相对未来中间价，bps）",
    "hjm__advsel_bps": "逆向选择成本 = espread - rspread（恒等式）",
    "hjm__trade_size": "平均单笔成交量（算法拆单的间接证据）",
    "hjm__msg_per_volume": "每单位成交量承载的消息数",
    "gb__sum_p": "GB 模型订单级“算法概率”之和",
    "gb__sum_p_amount": "同上，按订单金额加权",
    "gb__seed_pos": "GB 训练正种子订单数（簿记量，非因子）",
    "gb__seed_neg": "GB 训练负种子订单数（簿记量，非因子）",
}


FIELD_TIPS = {
    "etype": "事件类型，订单 / 成交 / 撤单",
    "ts": "时间戳",
    "code": "股票代码；页面中统一补零到 6 位",
    "side": "买卖方向",
    "price_tick": "价格（tick 整数）",
    "qty": "数量",
    "order_id": "订单 ID",
    "bid_id": "成交里买方订单 ID",
    "ask_id": "成交里卖方订单 ID",
    "event_pos": "事件在当天的顺序",
    "submit_ts": "订单提交时间",
    "cancel_ts": "订单撤单时间；NaT 表示未撤",
    "submit_price_tick": "提交价格",
    "submit_qty": "提交数量",
    "life_s": "订单寿命（秒）；挂到连续竞价结束按 14:57 计算",
    "life_ms": "订单寿命（毫秒）",
    "bbo_diff_ticks": "订单价格离同侧最优报价的真实档位数",
    "depth_rank": "订单挂在订单簿第几档",
    "qty_scaled": "数量相对当天中位数的倍数",
    "fill_ratio": "成交比例",
    "is_taker": "是否主动吃单",
    "end_state": "最终状态：filled / cancelled / partial_cancelled / expired_eod",
    "tod_bucket": "早盘、盘中还是尾盘",
    "flag_ee_step1": "EE 第一步：1 秒内快撤标记",
    "flag_ee_step2": "EE 第二步：与快撤单同码同向同量关联标记",
    "flag_ee": "EE 两步法并集标记",
    "flag_ccp_sruns": "CCP 策略性重挂链成员",
    "gb_seed_label": "GB 弱监督种子标签：1 正种子，0 负种子，-1 灰区",
}


SCORE_TIPS = {
    "quasi_kendall_stratum": "指标是否符合“HFT 更集中在高流动性股”的弱先验",
    "stability_spearman": "今天的股票排名明天是否仍成立；测持续属性还是噪声",
    "redundancy_abs_spearman": "是否只是在重复其他指标；越低越独特",
    "consequence__hjm__advsel_bps": "与 HJM 逆向选择后果的相关，需看方向是否符合机制",
    "consequence__hjm__trade_size": "与 HJM 拆单/成交规模后果的相关，需看方向是否符合机制",
    "incremental_label_corr": "控制其余全部指标后，还剩多少独立信号",
    "threshold_sensitivity_spearman": "改动构建阈值后排名是否稳定",
}


STOCKS = [
    ("000001", "high", 0, "平安银行"),
    ("000002", "high", 0, "万科A"),
    ("002962", "high", 0, "五方光电"),
    ("002241", "high", 0, "歌尔股份"),
    ("300364", "high", 30, "中文在线"),
    ("002884", "medium", 0, "凌霄泵业"),
    ("301421", "medium", 30, "波长光电"),
    ("002141", "medium", 0, "贤丰控股（原蓉胜超微）"),
    ("002344", "medium", 0, "海宁皮城"),
    ("002899", "medium", 0, "英派斯"),
    ("002867", "low", 0, "周大生"),
    ("300637", "low", 30, "扬帆新材"),
    ("002311", "low", 0, "海大集团"),
    ("300078", "low", 30, "思创智联（原思创医惠）"),
    ("300111", "low", 30, "向日葵"),
]


def esc(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def fmt(value: object) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    if isinstance(value, (int,)) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if math.isclose(value, round(value), abs_tol=1e-12) and abs(value) < 1_000_000:
            return str(int(round(value)))
        return f"{value:.3g}"
    return str(value)


def metric_html(name: str) -> str:
    prefix = name.split("__", 1)[0].lower()
    cls = f"metric metric-{prefix}" if prefix in PAPERS else "metric"
    return f'<span class="{cls}" title="{esc(METRIC_TIPS.get(name, ""))}">{esc(name)}</span>'


def table_html(df: pd.DataFrame, title_map: dict[str, str] | None = None, row_title_map: dict[str, str] | None = None, compact: bool = False) -> str:
    title_map = title_map or {}
    row_title_map = row_title_map or {}
    classes = "data-table compact" if compact else "data-table"
    head = "".join(f'<th title="{esc(title_map.get(str(col), ""))}">{metric_html(str(col)) if "__" in str(col) else esc(col)}</th>' for col in df.columns)
    rows = []
    for _, row in df.iterrows():
        cells = []
        for idx, col in enumerate(df.columns):
            raw = row[col]
            display = fmt(raw)
            tip = row_title_map.get(str(raw), "") if idx == 0 else ""
            if idx == 0 and "__" in display:
                body = metric_html(display)
            else:
                body = esc(display)
            cells.append(f'<td title="{esc(tip)}">{body}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return f'<div class="table-scroll"><table class="{classes}"><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def read_parquet(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path) if path.exists() else pd.DataFrame()


def ordered_metric_list(columns=None) -> list[str]:
    ordered = [metric for metrics in METRIC_CLUSTERS.values() for metric in metrics]
    if columns is None:
        return ordered
    colset = set(columns)
    return [metric for metric in ordered if metric in colset]


def metric_to_cluster_map() -> dict[str, str]:
    return {metric: cluster for cluster, metrics in METRIC_CLUSTERS.items() for metric in metrics}


def copy_assets() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    missing = []
    for name in IMAGE_NAMES:
        src = IMAGE_SRC / name
        if not src.exists():
            missing.append(name)
            continue
        shutil.copy2(src, ASSET_DIR / name)
    if missing:
        raise FileNotFoundError("缺失图片: " + ", ".join(missing))


def image(name: str, caption: str) -> str:
    return f'''
    <figure class="figure">
      <img src="assets/algo-footprint-2026-07-07/{esc(name)}" alt="{esc(caption)}" loading="lazy">
      <figcaption>{esc(caption)}</figcaption>
    </figure>
    '''


def build_tables() -> dict[str, str]:
    panel = read_parquet(OUT / "panel" / "panel_stock_day.parquet")
    bucket = read_parquet(OUT / "panel" / "panel_stock_bucket.parquet")
    scorecard = read_parquet(OUT / "eval" / "scorecard.parquet")
    loadings = read_parquet(OUT / "eval" / "fuse_loadings.parquet")
    gb_oos = read_parquet(OUT / "eval" / "gb_oos.parquet")
    gb_rules = read_parquet(OUT / "eval" / "gb_rules.parquet")
    gb_grayzone = read_parquet(OUT / "eval" / "gb_grayzone.parquet")

    life_files = sorted((OUT / "lifecycle").glob("code=*/date=*/lifecycle.parquet"))
    flag_files = sorted((OUT / "flags").glob("code=*/date=*/order_flags.parquet"))
    life = read_parquet(life_files[0]) if life_files else pd.DataFrame()
    flags = read_parquet(flag_files[0]) if flag_files else pd.DataFrame()

    stock_df = pd.DataFrame(STOCKS, columns=["code", "stratum", "board", "name"])
    stock_tip = {code: f"{code}：{name}" for code, _, _, name in STOCKS}
    stock_table = table_html(stock_df[["code", "stratum", "board"]], FIELD_TIPS, stock_tip)

    cache_df = pd.DataFrame([
        ("panel_stock_day.parquet", "150 行；15 只股票 × 10 个日期已有日级结果"),
        ("panel_stock_bucket.parquet", "35,546 行；已有分钟/时间桶级结果"),
        ("scorecard.parquet", "25 行；25 个 ee/kx/ccp/gb 方法指标进入评估"),
        ("gb_rules.parquet", "43 行；GB 模型已蒸馏出解释规则"),
        ("gb_grayzone.parquet", "19 行；GB 对灰区订单做了诊断"),
    ], columns=["缓存", "说明"])
    cache_table = table_html(cache_df, row_title_map={r["缓存"]: r["说明"] for _, r in cache_df.iterrows()})

    config_df = pd.DataFrame([
        ("默认聚合秒数", "1"),
        ("股票数", "15"),
        ("日期数", "10（2024-01-02~01-08 五天 + 2025-01-02~01-08 五天）"),
        ("启用方法", "m1_ee, m2_kx, m3_ccp, m4_kkst, m5_hjm, m6_gb"),
    ], columns=["项目", "值"])

    sample_cols = ["order_id", "side", "submit_ts", "cancel_ts", "life_s", "end_state", "bbo_diff_ticks", "depth_rank", "flag_ee", "flag_ccp_sruns", "gb_seed_label"]
    if not life.empty and not flags.empty:
        sample = life.merge(flags, on="order_id", how="left")
        sample = sample[[c for c in sample_cols if c in sample.columns]].head(12).copy()
    else:
        sample = pd.DataFrame(columns=sample_cols)
    sample_table = table_html(sample, FIELD_TIPS)

    panel_cols = ["code", "date"] + ordered_metric_list(panel.columns)
    panel_head = panel[panel_cols].head(20).copy()
    panel_head["code"] = panel_head["code"].astype(str).str.zfill(6)
    panel_table = table_html(panel_head, {**FIELD_TIPS, **METRIC_TIPS}, row_title_map=stock_tip, compact=True)

    if not panel.empty:
        cc = panel.groupby("code", as_index=False)["ee__hft_ratio"].sum()
        cc["code"] = cc["code"].astype(str).str.zfill(6)
        total = cc["ee__hft_ratio"].sum()
        cc = cc.sort_values("ee__hft_ratio", ascending=False).reset_index(drop=True)
        cc["rank"] = cc.index + 1
        cc["cum_share"] = cc["ee__hft_ratio"].cumsum() / total
        cc = cc[["rank", "code", "ee__hft_ratio", "cum_share"]]
    else:
        cc = pd.DataFrame(columns=["rank", "code", "ee__hft_ratio", "cum_share"])
    concentration_table = table_html(cc, {"code": FIELD_TIPS["code"], **METRIC_TIPS}, row_title_map={str(i): "" for i in range(1, 16)})

    high_pairs_table = ""
    if not panel.empty:
        metric_cols = ordered_metric_list(panel.columns)
        zero_var = [col for col in metric_cols if panel[col].std(skipna=True) == 0 or pd.isna(panel[col].std(skipna=True))]
        metric_cols = [col for col in metric_cols if col not in zero_var]
        corr = panel[metric_cols].corr(method="spearman")
        cluster_map = metric_to_cluster_map()
        pairs = []
        for i, metric_a in enumerate(metric_cols):
            for metric_b in metric_cols[i + 1:]:
                if cluster_map.get(metric_a) == cluster_map.get(metric_b):
                    continue
                rho = corr.loc[metric_a, metric_b]
                if pd.notna(rho) and abs(rho) >= 0.9:
                    pairs.append((metric_a, metric_b, cluster_map.get(metric_a, ""), cluster_map.get(metric_b, ""), rho))
        hp = pd.DataFrame(pairs, columns=["metric_a", "metric_b", "cluster_a", "cluster_b", "spearman"])
        if not hp.empty:
            hp = hp.reindex(hp["spearman"].abs().sort_values(ascending=False).index).head(10).reset_index(drop=True)
        high_pairs_table = table_html(hp, {**METRIC_TIPS, "spearman": "跨类 Spearman 相关；这里只展示 |rho|>=0.9 的前 10 对"}, compact=True)

    lat_table = ""
    share_table = ""
    if not life.empty and not flags.empty:
        flag_cols = [col for col in flags.columns if col.startswith("flag_")]
        compare = life.merge(flags[["order_id"] + flag_cols], on="order_id", how="left")
        compare = compare[compare["cancel_ts"].notna() & compare["submit_ts"].notna()].copy()
        compare["delta_ms"] = (pd.to_datetime(compare["cancel_ts"]) - pd.to_datetime(compare["submit_ts"])).dt.total_seconds() * 1000
        compare["any_flag"] = compare[flag_cols].fillna(False).astype(bool).any(axis=1)
        lat_rows = []
        for is_flagged, label in [(True, "flagged"), (False, "unflagged")]:
            vals = compare.loc[compare["any_flag"] == is_flagged, "delta_ms"]
            lat_rows.append({
                "group": label,
                "events": len(vals),
                "zero_ms_share": (vals == 0).mean() if len(vals) else float("nan"),
                "sub200_share": (vals < 200).mean() if len(vals) else float("nan"),
                "median_delta_ms": vals.median() if len(vals) else float("nan"),
                "phys_sub200_lift": "不展示：未标记组 sub-200ms 占比为 0，提升倍数不适用",
            })
        lat_table = table_html(pd.DataFrame(lat_rows))
        positive = compare[compare["delta_ms"] > 0].copy()
        bars = []
        base = positive.loc[~positive["any_flag"], "delta_ms"]
        bars.append({"组别": "未标记", "sub200_share": (base < 200).mean(), "n": len(base)})
        for col in flag_cols:
            vals = positive.loc[positive[col].fillna(False).astype(bool), "delta_ms"]
            if len(vals):
                bars.append({"组别": col, "sub200_share": (vals < 200).mean(), "n": len(vals)})
        share_table = table_html(pd.DataFrame(bars), FIELD_TIPS)

    score_cols = [
        "method", "quasi_kendall_stratum", "stability_spearman", "redundancy_abs_spearman",
        "consequence__hjm__advsel_bps", "consequence__hjm__trade_size",
        "incremental_label_corr", "threshold_sensitivity_spearman",
    ]
    score = scorecard[[c for c in score_cols if c in scorecard.columns]].copy()
    score_table = table_html(score, {**SCORE_TIPS, **METRIC_TIPS}, row_title_map=METRIC_TIPS, compact=True)

    eval_dim_df = pd.DataFrame([
        ("quasi_kendall_stratum（流动性分层 τ）", "指标是否符合“HFT 更集中在高流动性股”的弱先验", "越正越符合（但需警惕规模效应）"),
        ("stability_spearman（跨日稳定性）", "今天的股票排名明天还成立吗", "越高越好"),
        ("redundancy_abs_spearman（平均冗余度）", "是否只是在重复其他指标", "越低越独特"),
        ("consequence__hjm__advsel_bps / trade_size", "与 HJM 微观结构后果的关联", "有符号，看方向是否符合机制"),
        ("incremental_label_corr（增量判别力）", "控制其余指标后，还剩多少独立信号", "绝对值越大越好"),
        ("threshold_sensitivity_spearman", "改动构建阈值后排名是否稳定", "越高越稳健"),
    ], columns=["评估维度", "回答的问题", "方向"])

    gb_oos_table = table_html(gb_oos, compact=True)
    gb_rules_table = table_html(gb_rules.head(20), compact=True)
    gb_gray_table = table_html(gb_grayzone, compact=True)

    stability_table = ""
    year_table = ""
    split_table = ""
    if not panel.empty:
        reps = [
            "ee__step1_share", "ccp__sruns", "kx__otr_day", "kx__burst_seconds", "ccp__sresp",
            "kkst__snipe_taker_lift", "hjm__advsel_bps", "kx__fade_partial_prob", "gb__sum_p_amount",
        ]
        reps = [metric for metric in reps if metric in panel.columns]
        p = panel[["code", "date"] + reps].copy()
        p["date_dt"] = pd.to_datetime(p["date"])
        p["year"] = p["date_dt"].dt.year
        rows = []
        for metric in reps:
            for lag in [1, 2, 3, 4, 5]:
                pair_corrs = []
                for _, grp in p.groupby("year"):
                    pivot = grp.pivot_table(index="date_dt", columns="code", values=metric, aggfunc="mean").sort_index()
                    for i in range(len(pivot) - lag):
                        a = pivot.iloc[i]
                        b = pivot.iloc[i + lag]
                        mask = a.notna() & b.notna()
                        if mask.sum() >= 3:
                            rho = a[mask].corr(b[mask], method="spearman")
                            if pd.notna(rho):
                                pair_corrs.append(rho)
                rows.append({"metric": metric, "lag_days": lag, "stability_spearman": sum(pair_corrs) / len(pair_corrs) if pair_corrs else float("nan"), "n_pairs": len(pair_corrs)})
        stability_table = table_html(pd.DataFrame(rows), {**METRIC_TIPS, **SCORE_TIPS}, compact=True)

        method_cols = ordered_metric_list(panel.columns)
        p2 = panel[["code", "date"] + method_cols].copy()
        p2["year"] = pd.to_datetime(p2["date"]).dt.year
        years = sorted(p2["year"].dropna().unique())
        rows = []
        if len(years) >= 2:
            y0, y1 = years[0], years[-1]
            for metric in method_cols:
                a = p2[p2["year"].eq(y0)].groupby("code")[metric].mean()
                b = p2[p2["year"].eq(y1)].groupby("code")[metric].mean()
                common = a.index.intersection(b.index)
                rho = a.loc[common].corr(b.loc[common], method="spearman") if len(common) >= 3 else float("nan")
                rows.append({"metric": metric, "year_a": y0, "year_b": y1, "spearman": rho})
        year_table = table_html(pd.DataFrame(rows).sort_values("spearman"), {**METRIC_TIPS, "spearman": "2024-01 与 2025-01 股票排名 Spearman"}, compact=True)

    if not bucket.empty:
        b = bucket.copy()
        b["bucket_ts"] = pd.to_datetime(b["bucket_ts"])
        cols = [col for col in b.columns if col not in ["code", "date", "bucket_ts"] and pd.api.types.is_numeric_dtype(b[col])]
        morning = b[b["bucket_ts"].dt.time < pd.Timestamp("12:00").time()]
        afternoon = b[b["bucket_ts"].dt.time >= pd.Timestamp("12:00").time()]
        rows = []
        for metric in cols:
            a = morning.groupby("code")[metric].mean()
            c = afternoon.groupby("code")[metric].mean()
            common = a.index.intersection(c.index)
            rho = a.loc[common].corr(c.loc[common], method="spearman") if len(common) >= 3 else float("nan")
            rows.append({"metric": metric, "am_pm_spearman": rho})
        split_table = table_html(pd.DataFrame(rows).sort_values("am_pm_spearman"), {**METRIC_TIPS, "am_pm_spearman": "上午与下午股票排名 Spearman"}, compact=True)

    loadings_table = table_html(loadings, {**METRIC_TIPS, "pc1": "第一主轴载荷", "pc2": "第二主轴载荷"}, row_title_map=METRIC_TIPS, compact=True)

    return {
        "cache": cache_table,
        "config": table_html(config_df),
        "stock": stock_table,
        "sample": sample_table,
        "panel": panel_table,
        "concentration": concentration_table,
        "high_pairs": high_pairs_table,
        "lat": lat_table,
        "share": share_table,
        "eval_dims": table_html(eval_dim_df, SCORE_TIPS),
        "score": score_table,
        "gb_oos": gb_oos_table,
        "gb_rules": gb_rules_table,
        "gb_gray": gb_gray_table,
        "stability": stability_table,
        "year": year_table,
        "split": split_table,
        "loadings": loadings_table,
    }


def build_html(t: dict[str, str]) -> str:
    legend = "".join(
        f'<a class="legend-item legend-{key}" href="{esc(url)}" target="_blank" rel="noreferrer"><b>{esc(code)}</b><span>{esc(title)}</span></a>'
        for key, (code, title, url) in PAPERS.items()
    )
    cluster_cards = "".join(
        f'''<button class="cluster-card" data-cluster="{i}" type="button">
          <b>{esc(name)}</b>
          <span>{", ".join(metric_html(m) for m in metrics[:5])}{'...' if len(metrics) > 5 else ''}</span>
        </button>'''
        for i, (name, metrics) in enumerate(METRIC_CLUSTERS.items(), start=1)
    )
    cluster_panels = "".join(
        f'''<article class="cluster-detail" data-cluster-panel="{i}">
          <h4>{esc(name)}</h4>
          <p>{esc(cluster_text(name))}</p>
          <div class="metric-list">{"".join(metric_html(m) for m in metrics)}</div>
        </article>'''
        for i, (name, metrics) in enumerate(METRIC_CLUSTERS.items(), start=1)
    )

    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>寻找算法痕迹阶段成果看板 - 2026-07-07</title>
  <style>
    :root {{
      --bg: #0f1414;
      --panel: #18201f;
      --panel-2: #202a28;
      --line: #35504c;
      --text: #eef4ea;
      --muted: #aab8ae;
      --gold: #d6b35d;
      --red: #e76f51;
      --blue: #4ea5d9;
      --green: #63c38a;
      --violet: #b78cff;
      --pink: #f284b6;
      --orange: #f4a261;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at 18% -10%, rgba(214,179,93,.18), transparent 28rem),
        linear-gradient(135deg, #0f1414 0%, #131817 52%, #1a1511 100%);
      color: var(--text);
      font-family: "Noto Serif SC", "Microsoft YaHei", serif;
      line-height: 1.65;
    }}
    a {{ color: inherit; }}
    .report {{ min-height: 100vh; padding: 28px; }}
    .paper-legend {{
      position: sticky; top: 0; z-index: 10;
      display: grid; grid-template-columns: repeat(6, minmax(120px, 1fr));
      gap: 8px; padding: 10px; margin: -28px -28px 18px;
      border-bottom: 1px solid var(--line);
      background: rgba(15,20,20,.92); backdrop-filter: blur(12px);
    }}
    .legend-item {{ display: grid; gap: 2px; min-width: 0; padding: 8px 10px; border-left: 4px solid currentColor; background: rgba(255,255,255,.04); text-decoration: none; }}
    .legend-item b {{ font-size: 12px; letter-spacing: .04em; }}
    .legend-item span {{ overflow: hidden; color: var(--muted); font-size: 11px; text-overflow: ellipsis; white-space: nowrap; }}
    .legend-hjm, .metric-hjm {{ color: var(--pink); }}
    .legend-kx, .metric-kx {{ color: var(--blue); }}
    .legend-ccp, .metric-ccp {{ color: var(--orange); }}
    .legend-ee, .metric-ee {{ color: var(--green); }}
    .legend-kkst, .metric-kkst {{ color: var(--violet); }}
    .legend-gb, .metric-gb {{ color: var(--gold); }}
    .hero {{ display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 24px; align-items: end; padding: 34px 0 24px; }}
    h1 {{ margin: 0; font-size: clamp(30px, 5vw, 58px); line-height: 1.08; }}
    .hero p, .note, .caption {{ color: var(--muted); }}
    .guardrail {{ padding: 18px; border: 1px solid rgba(231,111,81,.45); background: rgba(231,111,81,.08); }}
    .flow {{ position: sticky; top: 78px; z-index: 9; display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; margin: 10px 0 24px; }}
    .flow button {{ min-height: 74px; padding: 10px; border: 1px solid var(--line); background: #101716; color: var(--muted); text-align: left; cursor: pointer; }}
    .flow button.is-active {{ border-color: var(--gold); background: #24302b; color: var(--text); box-shadow: 0 12px 34px rgba(0,0,0,.25); }}
    .flow b {{ display: block; color: var(--gold); font-size: 12px; }}
    .section {{ display: none; margin: 24px 0; padding: 24px; border: 1px solid var(--line); background: rgba(24,32,31,.88); box-shadow: 0 20px 70px rgba(0,0,0,.24); }}
    .section.is-active {{ display: block; }}
    h2, h3, h4 {{ line-height: 1.25; }}
    h2 {{ margin-top: 0; font-size: 28px; color: var(--gold); }}
    h3 {{ margin-top: 28px; color: #dbe7dc; }}
    .grid-2 {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; }}
    .grid-3 {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }}
    .tile {{ padding: 16px; border: 1px solid var(--line); background: rgba(255,255,255,.035); }}
    .tile strong {{ color: var(--gold); }}
    .figure {{ margin: 18px 0; padding: 10px; border: 1px solid var(--line); background: #f8faf7; color: #17201d; }}
    .figure img {{ display: block; width: 100%; height: auto; }}
    .figure figcaption {{ margin-top: 8px; color: #40524c; font-size: 13px; }}
    .table-scroll {{ max-width: 100%; overflow: auto; margin: 14px 0; border: 1px solid var(--line); }}
    table {{ width: 100%; border-collapse: collapse; min-width: 620px; background: rgba(255,255,255,.025); }}
    th, td {{ padding: 8px 10px; border-bottom: 1px solid rgba(255,255,255,.09); border-right: 1px solid rgba(255,255,255,.06); vertical-align: top; font-size: 13px; }}
    th {{ position: sticky; top: 0; z-index: 2; background: #22302d; color: #f4edd8; text-align: left; white-space: nowrap; }}
    .compact th, .compact td {{ padding: 6px 8px; font-size: 12px; }}
    .metric {{ font-family: Consolas, "Cascadia Mono", monospace; white-space: nowrap; }}
    .cluster-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
    .cluster-card {{ min-height: 116px; padding: 14px; border: 1px solid var(--line); background: #101716; color: var(--muted); text-align: left; cursor: pointer; }}
    .cluster-card b {{ display: block; margin-bottom: 8px; color: var(--text); }}
    .cluster-card.is-active {{ border-color: var(--gold); background: #24302b; color: var(--text); }}
    .cluster-detail {{ display: none; padding: 16px; margin-top: 14px; border: 1px solid var(--line); background: rgba(255,255,255,.04); }}
    .cluster-detail.is-active {{ display: block; }}
    .metric-list {{ display: flex; flex-wrap: wrap; gap: 7px; }}
    .metric-list .metric {{ padding: 3px 6px; border: 1px solid currentColor; background: rgba(0,0,0,.16); }}
    .tabs {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 18px 0; }}
    .tabs button {{ padding: 9px 12px; border: 1px solid var(--line); background: #101716; color: var(--muted); cursor: pointer; }}
    .tabs button.is-active {{ border-color: var(--gold); color: var(--text); }}
    .tab-panel {{ display: none; }}
    .tab-panel.is-active {{ display: block; }}
    .conclusion {{ display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 10px; margin-top: 24px; }}
    .conclusion .tile {{ border-color: rgba(214,179,93,.45); background: rgba(214,179,93,.08); }}
    code {{ color: var(--gold); }}
    @media (max-width: 980px) {{
      .report {{ padding: 16px; }}
      .paper-legend {{ grid-template-columns: repeat(2, 1fr); margin: -16px -16px 12px; }}
      .hero, .grid-2, .grid-3, .conclusion {{ grid-template-columns: 1fr; }}
      .flow {{ position: static; grid-template-columns: 1fr; }}
      .cluster-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
<main class="report">
  <nav class="paper-legend" aria-label="六篇论文颜色图例">{legend}</nav>
  <header class="hero">
    <div>
      <p class="caption">2026-07-07 / 寻找算法痕迹 / A 股 L2 小样本流程验证</p>
      <h1>寻找算法痕迹：六篇论文指标的落地、去冗余与证据链</h1>
      <p>本页只覆盖 15 只股票 × 10 个交易日的小样本，所有评估均为间接证据。它只讨论订单行为证据，不做收益预测或投资绩效解释。</p>
    </div>
    <aside class="guardrail">
      <strong>措辞红线</strong>
      <p>没有真标签；GB 种子复现只能说明规则复现能力。相关系数、排名一致性和 PCA 均需带小样本限定。</p>
    </aside>
  </header>
  <nav class="flow" aria-label="流程任务串">
    <button class="is-active" data-step="overview"><b>01</b>项目总况</button>
    <button data-step="lifecycle"><b>02</b>读取&标准化 L2 事件</button>
    <button data-step="metrics"><b>03</b>对每个股票-日期算指标</button>
    <button data-step="results"><b>04</b>最终真实计算结果</button>
    <button data-step="eval"><b>05</b>评估每个方法</button>
    <button data-step="pca"><b>06</b>PCA 融合</button>
  </nav>

  <section id="overview" class="section is-active">
    <h2>项目总况</h2>
    <div class="grid-2"><div><h3>产出缓存概览</h3>{t["cache"]}</div><div><h3>实验配置</h3>{t["config"]}</div></div>
    <h3>股票池（15 股 5/5/5 流动性分层）</h3>
    <p class="note">code 已补零到 6 位。high/medium/low 按成交活跃度/流动性分层；board=30 表示创业板，board=0 表示主板/中小板。名称已按行情与公司资料核实；300078 当前简称为思创智联，002141 当前简称为贤丰控股。</p>
    {t["stock"]}
  </section>

  <section id="lifecycle" class="section">
    <h2>读取&标准化 L2 事件&打标签</h2>
    <div class="grid-3">
      <div class="tile"><strong>第一步：事件统一</strong><p>把订单、成交、撤单统一到 etype、ts、code、side、price_tick、qty、order_id、bid_id/ask_id、event_pos 等标准字段。</p></div>
      <div class="tile"><strong>第二步：生命周期重建</strong><p>把同一 order_id 的所有事件串起来，得到 submit_ts、cancel_ts、life_s、bbo_diff_ticks、depth_rank、fill_ratio、end_state 等完整档案。</p></div>
      <div class="tile"><strong>第三步：弱监督标记</strong><p>生成 EE 快撤/关联、CCP SRuns 链，以及 GB seed label。所有标记都是候选行为，不是真标签。</p></div>
    </div>
    <h3>逐笔案例表</h3>{t["sample"]}
    <h3>订单寿命分布</h3>
    {image("cell_0007_output_0002.png", "订单寿命分布（log10 秒，000001 / 2024-01-02 单股票日样本）")}
    <p>横轴是 log10(life_s)，所以毫秒级、秒级、分钟级和挂到收盘的订单能同时被看见；0.2 秒、1 秒、10 秒三条参考线对应后续方法的关键阈值。寿命分布呈现多峰：一大批订单在 1 秒内消失（算法行为的候选区），另一大批挂到收盘（典型“人类/被动”区）。</p>
  </section>

  <section id="metrics" class="section">
    <h2>对每个股票-日期算指标</h2>
    <p>六篇论文共形成 42 个指标，进入记分卡的是 25 个 ee/kx/ccp/gb 方法指标。跨论文前缀看，真正独立的信息轴约 7 条：订单存活时间、订单链式关联、消息强度、盘口扰动、事件响应速度、主动成交/价格冲击、成交成本后果。</p>
    <h3>9 类构建逻辑卡片</h3>
    <div class="cluster-grid">{cluster_cards}</div>
    <div id="cluster-empty">{image("cell_0014_output_0002.png", "全部指标 Spearman 相关矩阵（按 9 类聚类排序）")}</div>
    {cluster_panels}
    <h3>跨类高相关指标对（前 10 / 共 30 对）</h3>
    {t["high_pairs"]}
    <p>跨类高相关暴露了一条隐藏公共轴：<code>ccp__mess/can/ioc/sresp/quoteint</code>、<code>kx__burst_count/seconds</code>、<code>gb__sum_p</code> 多数由股票规模/活跃度驱动。机械关系不构成发现；<code>kx__life_p10</code>、<code>kx__life_p25</code> 本样本零方差，已退化。</p>
  </section>

  <section id="results" class="section">
    <h2>这些指标的最终（真实计算）结果</h2>
    <h3>面板原始值示例（20 行 × 27 列）</h3>
    {t["panel"]}
    <p>这张表直接暴露量纲问题：比例型指标约 0.03，计数型约 10^5，金额加权约 10^9。原始值之间没有可比性，所以下面所有跨指标比较一律先做横截面标准化。</p>
    {image("cell_0010_output_0003.png", "股票×指标标准化热力图（横截面 z-score，日期均值）")}
    <p>颜色不是指标绝对水平，而是每只股票在该指标上的全样本横截面相对位置。计数型指标族在高流动性层整体偏红是规模效应，属预期，不是发现；同一层内部的例外才值得注意。比例型指标的红蓝分布与计数型明显不同，说明“算法活动占比”和“算法活动总量”是两件事。</p>
    <h3>EE 标记活动集中度</h3>
    {image("cell_0013_output_0002.png", "EE 标记活动集中度曲线")}
    {t["concentration"]}
    <p>当前样本中第 1 名（002311）占 20.3%，前 5 名占 52.0%，前 10 名占 82.3%；这是中等程度集中，与 EE 论文“HFT 活动集中在少数标的”的定性方向一致，但没有那么极端。</p>
  </section>

  <section id="eval" class="section">
    <h2>评估每个方法</h2>
    <div class="tabs">
      <button class="is-active" data-tab="phys" type="button">物理层证据</button>
      <button data-tab="score" type="button">记分卡</button>
      <button data-tab="gb" type="button">GB 模型质量</button>
      <button data-tab="robust" type="button">稳健性检验</button>
    </div>
    <article class="tab-panel is-active" data-tab-panel="phys">
      <h3>速度是最硬的证据</h3>
      {t["lat"]}
      {t["share"]}
      <div class="grid-2">{image("cell_0017_output_0003.png", "被标记 vs 未标记订单的报撤延迟分布")}{image("cell_0017_output_0004.png", "各 flag 组的 sub-200ms 报撤占比")}</div>
      <p>被标记订单（n=2,949）：撤单延迟中位数 40ms，61.6% 在 200ms 内完成，29.9% 的动作时间差为 0ms；未标记订单（n=18,991）：中位数 180 秒，sub-200ms 占比 0%。分方法看，<code>flag_ccp_sruns</code> 组 95.3%，<code>flag_ee_step1</code> 组 84.8%，<code>flag_ee_step2</code> 组 44.4%。未标记组 sub-200ms 占比为 0，提升倍数不适用。</p>
    </article>
    <article class="tab-panel" data-tab-panel="score">
      <h3>四个维度给 25 个指标打分</h3>
      {t["eval_dims"]}
      {t["score"]}
      <div class="grid-3">{image("cell_0020_output_0005.png", "四层证据记分卡热力图")}{image("cell_0020_output_0006.png", "四联条形图")}{image("cell_0020_output_0007.png", "有效性-独特性散点图")}</div>
      <p>分层一致性最高的是计数型指标（如 <code>gb__sum_p_amount</code> 0.544、<code>ccp__quoteint</code> 0.474），但这部分是规模效应重复。EE 比例型指标为负，不能直接读成“低流动性股算法更多”。增量判别力方面，<code>ee__step1_share</code> 0.639 与 <code>kx__short_cancel_lt_1s</code> 0.572 领先，说明控制计数型指标后，“1 秒内快撤占比”仍携带独立信息。</p>
    </article>
    <article class="tab-panel" data-tab-panel="gb">
      <h3>GB 模型质量</h3>
      <div class="grid-2"><div><h4>OOS 种子复现</h4>{t["gb_oos"]}</div><div><h4>蒸馏规则 head(20)</h4>{t["gb_rules"]}</div></div>
      <h4>灰区诊断/校准表</h4>{t["gb_gray"]}
      {image("cell_0020_output_0008.png", "GB 分数校准曲线（灰区订单）")}
      <p>train/oos 的 PPV=1.0、NPV≈0.99996 只说明模型能复现 EE/SRuns 生成的种子规则，不能说明真实标签层面的命中质量。首要分裂是 <code>life_s &lt;= 1.0</code>，模型学到的是“短寿命 + 撤单 + 近盘口”的组合。校准曲线不单调，GB 分数当前更像混合行为排序，而非校准概率。</p>
    </article>
    <article class="tab-panel" data-tab-panel="robust">
      <h3>稳健性与一致性检验</h3>
      {image("cell_0023_output_0002.png", "滞后稳定性曲线")}
      {t["stability"]}
      <div class="grid-2">{image("cell_0024_output_0002.png", "2024 vs 2025 股票排名一致性")}{image("cell_0025_output_0003.png", "上午 vs 下午股票排名一致性")}</div>
      {t["year"]}
      {t["split"]}
      {image("cell_0025_output_0004.png", "OTR 日内轮廓")}
      <p><code>gb__sum_p_amount</code>（0.97→0.95）、<code>ccp__sresp</code>（0.95→0.92）、<code>kx__fade_partial_prob</code>（0.91→0.91）几乎不衰减；<code>ee__step1_share</code> 从 0.76 衰减到 0.60，有持续成分但混噪声。跨年最高为 <code>gb__sum_p_amount</code> 0.850、<code>kx__life_p75</code> 0.846；最低为 <code>ee__flag_qty_share</code> -0.03。桶级上午/下午一致性全部为正且不低（0.65~0.98）。</p>
    </article>
  </section>

  <section id="pca" class="section">
    <h2>PCA 融合</h2>
    {t["loadings"]}
    <div class="grid-2">{image("cell_0027_output_0002.png", "PC1/PC2 载荷结构条形图")}{image("cell_0027_output_0003.png", "PCA PC1/PC2 平面散点")}</div>
    <p><strong>PC1 是“规模/消息强度轴”</strong>：<code>ccp__ioc</code> 0.316、<code>ccp__sresp</code> 0.316、<code>gb__sum_p</code> 0.315、<code>ccp__mess</code> 0.313、<code>kx__burst_count/seconds</code> 0.294/0.295 载荷接近且同号。</p>
    <p><strong>PC2 是“快速撤单/比例轴”</strong>：<code>ee__step1_share</code> 与 <code>kx__short_cancel_lt_1s</code> 各 0.416，<code>ee__hft_ratio</code> 0.398、<code>ccp__fleet</code> 0.367、<code>ee__flag_qty_share</code> 0.360 主导。当前 150 个样本点的 PCA 只能作为流程验证。</p>
  </section>

  <section class="conclusion" aria-label="本阶段诚实结论">
    <div class="tile"><strong>1</strong><p>42 个指标已在 15 股 × 10 日 A 股 L2 数据上落地。</p></div>
    <div class="tile"><strong>2</strong><p>有效信息轴少于指标数，核心是活动总量与快撤占比。</p></div>
    <div class="tile"><strong>3</strong><p>物理层最硬：标记订单中位撤单延迟 40ms，61.6% 低于 200ms。</p></div>
    <div class="tile"><strong>4</strong><p><code>ee__step1_share</code> 增量价值最强；<code>gb__sum_p_amount</code> 最稳定。</p></div>
    <div class="tile"><strong>5</strong><p>缺陷如实呈现：p10/p25 退化、GB 不单调、计数族强共线、无真标签。</p></div>
  </section>
</main>
<script>
  const flowButtons = [...document.querySelectorAll('.flow button')];
  const sections = [...document.querySelectorAll('.section')];
  flowButtons.forEach((button) => button.addEventListener('click', () => {{
    flowButtons.forEach((node) => node.classList.toggle('is-active', node === button));
    sections.forEach((section) => section.classList.toggle('is-active', section.id === button.dataset.step));
  }}));
  const clusterCards = [...document.querySelectorAll('.cluster-card')];
  const clusterDetails = [...document.querySelectorAll('.cluster-detail')];
  const clusterEmpty = document.getElementById('cluster-empty');
  clusterCards.forEach((card) => card.addEventListener('click', () => {{
    const id = card.dataset.cluster;
    clusterCards.forEach((node) => node.classList.toggle('is-active', node === card));
    clusterDetails.forEach((node) => node.classList.toggle('is-active', node.dataset.clusterPanel === id));
    clusterEmpty.hidden = true;
  }}));
  const tabButtons = [...document.querySelectorAll('.tabs button')];
  const tabPanels = [...document.querySelectorAll('.tab-panel')];
  tabButtons.forEach((button) => button.addEventListener('click', () => {{
    tabButtons.forEach((node) => node.classList.toggle('is-active', node === button));
    tabPanels.forEach((panel) => panel.classList.toggle('is-active', panel.dataset.tabPanel === button.dataset.tab));
  }}));
</script>
</body>
</html>
'''


def cluster_text(name: str) -> str:
    return {
        "短生命/快速撤单": "底层事件都是订单在提交后很短时间内被撤；核心自由度是 life_s 左尾和快撤单占比。",
        "链式重复下单": "通过同代码、同方向、同数量与时间邻近，把反复报撤的订单串成链或簇。",
        "消息强度/OTR": "衡量单位成交承载了多少报撤消息，以及这些消息是否集中在 BBO 附近。",
        "盘口扰动/簇发": "来自同一条 L1 时间序列，分别度量变动频次、持续时间和幅度。",
        "事件响应速度": "取一个盘口事件，开短窗口，统计窗口内的跟随行为。",
        "主动成交/知情性": "围绕 taker 行为及其与价格变动的先后关系构造。",
        "成交经济后果": "以成交价相对当前或未来中间价的偏离度量成本，是结果验证指标。",
        "撤单-成交交互(fade)": "看成交发生后短窗口内 maker 同侧同价撤单的概率，是 fade/spoof 形态的间接证据。",
        "GB 模型综合": "用类 1/2 的弱监督种子和订单特征学习复合排序，天然与快撤、链式重挂等信息共线。",
    }[name]


def main() -> None:
    copy_assets()
    tables = build_tables()
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(build_html(tables), encoding="utf-8", newline="\n")
    print(f"Wrote {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
