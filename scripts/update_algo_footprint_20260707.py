from __future__ import annotations

from html import escape
from pathlib import Path

import matplotlib as mpl
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from bs4 import BeautifulSoup


DASHBOARD = Path(r"D:\MG\！Internship\BUILD\汇报")
ALGO = Path(r"D:\MG\_GitLinked\Quant_Research-Trading\26 Summer\❗思瑞投资\因子\algobench")
HTML = DASHBOARD / "content" / "daily" / "2026-07-07.show.html"
ASSETS = DASHBOARD / "site" / "assets" / "algo-footprint-2026-07-07"


METRIC_CLUSTERS = {
    "短生命/快速撤单": [
        "ee__step1_share",
        "ee__hft_ratio",
        "ee__flag_qty_share",
        "kx__short_cancel_lt_1s",
        "kx__short_cancel_lt_10s",
        "kx__life_p10",
        "kx__life_p25",
        "kx__life_p50",
        "kx__life_p75",
        "kx__life_p90",
        "ccp__fleet",
    ],
    "链式重复下单": ["ccp__sruns", "gb__seed_pos"],
    "消息强度/OTR": ["kx__otr_day", "ccp__mess", "ccp__can", "hjm__msg_per_volume"],
    "盘口扰动/簇发": ["kx__burst_count", "kx__burst_seconds", "ccp__quoteint", "ccp__flick"],
    "事件响应速度": ["ccp__sresp", "kkst__newlevel_maker_lift"],
    "主动成交/知情性": [
        "ccp__ioc",
        "kkst__aggressive_ratio_flagged",
        "kkst__snipe_taker_lift",
        "kkst__flow_price_beta_lag0",
        "kkst__flow_price_beta_lag1",
        "kkst__flow_price_beta_lag2",
        "kkst__flow_price_beta_lag3",
        "kkst__flow_price_beta_lag4",
        "kkst__flow_price_beta_lag5",
        "kkst__flow_price_beta0",
    ],
    "成交经济后果": ["hjm__espread_bps", "hjm__rspread_bps", "hjm__advsel_bps", "hjm__trade_size"],
    "撤单-成交交互(fade)": ["kx__fade_full_prob", "kx__fade_partial_prob"],
    "GB 模型综合": ["gb__sum_p", "gb__sum_p_amount", "gb__seed_neg"],
}


CAPTIONS_TABLE = [
    "这五个文件是整条流水线的\"产出清单\"：日级指标面板、分钟级面板、评估记分卡、GB 模型规则、GB 灰区诊断。行数与 15 股 × 10 天对得上，说明管道完整跑通了。",
    "本次实验的边界：15 只股票、10 个交易日（2024 年 1 月和 2025 年 1 月各 5 天）、6 套方法同时开启。后面所有图表都出自这个范围。",
    "15 只股票按流动性高/中/低分三档、每档 5 只，主板和创业板都有。这样设计是为了检验：算法痕迹指标在冷门股和热门股上是否表现一致。",
    "每一行是一笔真实委托的\"一生\"：什么时候挂单、挂了多少股、活了多久、成交了几成、最后是成交完还是被撤掉，以及有没有被某个方法打上\"疑似算法\"的标记。对照着看很直观：有的订单 0.06 秒就成交了，有的挂了近两个小时才撤单，还有的挂到收盘也没等到对手方（expired_eod）。",
    "相关系数超过 0.9 的\"跨类\"指标对清单。排最前的几对接近 1：有的是构造上注定的（GB 的正种子本来就从 fleet 类事件里选），有的说明两个看似不同的指标实际在度量同一属性。",
    "两只股票 × 10 天的指标原始值。重点看各列的数量级：有的是 0.03 这样的比例，有的是几万的计数，还有十亿级的金额——原始值不能直接放在一起比，所以后面所有跨指标比较都先做了标准化。",
    "把 15 只股票按 EE 标记活动从高到低排队，曲线是\"前 k 名合计占了全部活动的百分之几\"。第 1 名（002311）一家就占了两成，前 5 名占一半——算法活动确实集中在少数股票上，但没有极端到一家独大。",
    "上图的数字版：被标记订单撤单延迟中位数 40 毫秒、61.6% 快于 200ms；未标记订单中位数约 3 分钟、没有一笔快于 200ms。",
    "把\"被标记\"拆开看每个方法各自抓到的订单：SRuns 链上的订单 95% 是闪电撤单，EE 第一步 85%；EE 第二步靠\"关联传染\"扩散标记，抓的是同伙而不全是快手，所以只有 44%。未标记组为 0%，对照非常干净。",
    "给 25 个指标从四个角度打分：符不符合\"算法多在活跃股\"的先验、跨日排名稳不稳、是不是只在重复别的指标、控制其他指标后还剩多少独立信息。没有指标四项全优——这正是需要多方法互相印证的原因。",
    "给 25 个指标从四个角度打分：符不符合\"算法多在活跃股\"的先验、跨日排名稳不稳、是不是只在重复别的指标、控制其他指标后还剩多少独立信息。没有指标四项全优——这正是需要多方法互相印证的原因。",
    "模型在训练日和留出日复现种子标签的能力（PPV/NPV 都接近 1）。注意这说明模型学会了种子规则，不等于能识别真算法——种子本身就是规则生成的。",
    "把 GB 模型压成一棵可读的决策树。第一刀就是\"寿命是否超过 1 秒\"，其后依次看终态、相对报单量、挂单档位——模型自己学到的判别逻辑与手工聚类的类 1/类 2 完全一致。",
    "把模型没见过标签的\"灰区\"订单按分数分箱，检查分数高的箱子是否真的更常撤单、活得更短。结论是部分及格：大趋势对，但分数挤在很窄的区间、个别高分箱回落——GB 分数当排序用可以，当概率用不行。",
    "\"今天的股票排名\"和\"1~4 天后的排名\"做相关。GB 金额分、SResp、fade 的曲线又高又平——量的是股票的长期属性；SRuns 和逆向选择成本又低又抖——前者事件太稀疏，后者本来就该逐日波动。",
    "用 2024 年 1 月给股票排一次名、2025 年 1 月再排一次，看两次像不像。订单寿命、消息强度这类\"股票体质\"指标隔一年依然稳定；EE 快撤占比几乎重排了一遍——它更像随市场环境变化的\"状态\"，不是固定属性。",
    "同一批交易日，只用上午数据排一次名、只用下午再排一次。所有桶级指标两次排名都高度一致（0.65~0.98），说明它们量到的不是半天的噪声。",
    "把 25 个指标压缩成两条主轴后，每个指标在两条轴上的\"话语权\"。第一轴几乎被计数类指标平分——就是前面反复出现的\"活跃度\"；第二轴被 EE 快撤系列主导——\"快撤占比\"。数据自己也认为这两件事是主要矛盾。",
]


CAPTIONS_FIGURES = [
    None,  # filled with N_total after plotting
    "把每只股票的全部委托按寿命切成六段，看结构占比：颜色越深代表寿命越短。一眼可以回答\"哪只股票的秒撤单最多\"——不同股票的深色段宽度差别很大，而且即使在同一个流动性层内也不整齐。这正是要逐股票计算指标的原因：算法活动的浓度是每只股票自己的属性，不能用全市场平均代替。",
    "42 个指标两两算相关（红 = 同涨同跌，蓝 = 反向），黑线框出 9 个\"构造逻辑类\"。对角线附近一块块深红说明同类指标基本在重复讲同一件事；而跨类的大片红色（集中在几组计数类指标之间）暴露出它们背后是同一个东西——股票的活跃度。",
    "把 25 个指标全部换算成\"相对位置分\"（红 = 在 15 只股票里偏高，蓝 = 偏低）再拼成一张表。横着看是一只股票的\"体检报告\"，竖着看是一个指标偏爱哪类股票。左边一大片计数类指标基本\"越活跃越红\"——这是规模效应；右边比例类指标的冷暖分布明显不同，说明\"算法活动的总量\"和\"算法活动的占比\"是两回事。",
    "把 15 只股票按 EE 标记活动从高到低排队，曲线是\"前 k 名合计占了全部活动的百分之几\"。第 1 名（002311）一家就占了两成，前 5 名占一半——算法活动确实集中在少数股票上，但没有极端到一家独大。",
    "同一只股票同一天，被任一方法标记的订单（红）和未被标记的订单（蓝）从挂单到撤单花的时间。两个群体几乎不重叠：被标记的集中在几十毫秒，未标记的以分钟、小时计。200ms 虚线是人类反应速度的下限——比它更快的动作不可能是人手点出来的。",
    "把\"被标记\"拆开看每个方法各自抓到的订单：SRuns 链上的订单 95% 是闪电撤单，EE 第一步 85%；EE 第二步靠\"关联传染\"扩散标记，抓的是同伙而不全是快手，所以只有 44%。未标记组为 0%，对照非常干净。",
    "上表的图形版。所有格子都是 −1 到 1 的相关/秩系数，同一把尺子，可以放心横竖对比。",
    "四个评估维度各排一次序。看点：计数类指标包揽\"分层一致性\"和\"稳定性\"前排，但在\"独特性\"上垫底；EE 快撤占比正好反过来——最独特、独立信息最多，但与流动性先验方向相反。",
    "横轴是\"有多像别的指标\"（越靠左越独特），纵轴是\"是否符合活跃股先验\"。计数类指标在右上抱团——一荣俱荣的规模族；EE 系列在左下独树一帜——独特但方向为负。两类证据正好互补。",
    "把模型没见过标签的\"灰区\"订单按分数分箱，检查分数高的箱子是否真的更常撤单、活得更短。结论是部分及格：大趋势对，但分数挤在很窄的区间、个别高分箱回落——GB 分数当排序用可以，当概率用不行。",
    "\"今天的股票排名\"和\"1~4 天后的排名\"做相关。GB 金额分、SResp、fade 的曲线又高又平——量的是股票的长期属性；SRuns 和逆向选择成本又低又抖——前者事件太稀疏，后者本来就该逐日波动。",
    "用 2024 年 1 月给股票排一次名、2025 年 1 月再排一次，看两次像不像。订单寿命、消息强度这类\"股票体质\"指标隔一年依然稳定；EE 快撤占比几乎重排了一遍——它更像随市场环境变化的\"状态\"，不是固定属性。",
    "同一批交易日，只用上午数据排一次名、只用下午再排一次。所有桶级指标两次排名都高度一致（0.65~0.98），说明它们量到的不是半天的噪声。",
    "每成交一笔对应的报撤消息数在一天内的变化：开盘后最高、收盘前翘尾、午间平稳。这个形态与\"算法在开收盘最忙\"的业界常识吻合，日内形态本身就是算法活动的间接证据。",
    "把 25 个指标压缩成两条主轴后，每个指标在两条轴上的\"话语权\"。第一轴几乎被计数类指标平分——就是前面反复出现的\"活跃度\"；第二轴被 EE 快撤系列主导——\"快撤占比\"。数据自己也认为这两件事是主要矛盾。",
    "每个点是一个股票-日，横轴 ≈ 活跃度、纵轴 ≈ 快撤强度。同一只股票的 10 个点大致聚在一起，说明这两个坐标是股票的稳定画像；远离本队的离群点值得单独调查。",
]


def configure_chinese_font():
    candidates = [
        Path(r"C:/Windows/Fonts/msyh.ttc"),      # Microsoft YaHei
        Path(r"C:/Windows/Fonts/simhei.ttf"),    # SimHei
        Path(r"C:/Windows/Fonts/simsun.ttc"),    # SimSun
        Path(r"C:/Windows/Fonts/Deng.ttf"),      # DengXian
    ]
    loaded = None
    for font_path in candidates:
        if font_path.exists():
            fm.fontManager.addfont(str(font_path))
            loaded = fm.FontProperties(fname=str(font_path)).get_name()
            break
    fallback_names = [name for name in [loaded, "Microsoft YaHei", "SimHei", "SimSun", "DengXian", "Arial Unicode MS"] if name]
    mpl.rcParams["font.family"] = "sans-serif"
    mpl.rcParams["font.sans-serif"] = fallback_names + mpl.rcParams.get("font.sans-serif", [])
    mpl.rcParams["axes.unicode_minus"] = False
    return loaded


def metric_class(metric: str) -> str:
    prefix = metric.split("__", 1)[0]
    return {
        "ee": "metric-ee",
        "kx": "metric-kx",
        "ccp": "metric-ccp",
        "hjm": "metric-hjm",
        "kkst": "metric-kkst",
        "gb": "metric-gb",
    }.get(prefix, "")


def metric_span(metric: str) -> str:
    klass = metric_class(metric)
    return f'<span class="metric {klass}">{escape(metric)}</span>' if klass else escape(metric)


def fmt_value(value) -> str:
    if pd.isna(value):
        return ""
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    if isinstance(value, (bool, np.bool_)):
        return "True" if value else "False"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.3g}"
    return str(value)


def caption_tag(soup: BeautifulSoup, text: str):
    p = soup.new_tag("p", attrs={"class": "explain-caption"})
    p.string = text
    return p


def load_stock_order() -> list[dict[str, str]]:
    cfg = yaml.safe_load((ALGO / "configs" / "default.yaml").read_text(encoding="utf-8"))
    return cfg["universe"]["stocks"]


def generate_life_figures() -> tuple[int, dict[str, int]]:
    configure_chinese_font()
    ASSETS.mkdir(parents=True, exist_ok=True)
    files = sorted((ALGO / "outputs" / "lifecycle").glob("code=*/date=*/lifecycle.parquet"))
    if len(files) != 150:
        raise RuntimeError(f"expected 150 lifecycle files, found {len(files)}")

    hist_bins = np.linspace(-3, np.log10(20000), 80)
    hist_counts = np.zeros(len(hist_bins) - 1, dtype=np.int64)
    segment_names = ["<0.2s", "0.2–1s", "1–10s", "10–60s", "1–30min", ">30min（含挂到收盘）"]
    segment_counts: dict[str, np.ndarray] = {}
    stock_counts: dict[str, int] = {}
    total = 0

    for path in files:
        df = pd.read_parquet(path, columns=["code", "life_s"])
        code = str(df["code"].iloc[0]).zfill(6) if len(df) else path.parent.parent.name.split("=", 1)[1]
        life = pd.to_numeric(df["life_s"], errors="coerce").dropna().to_numpy(dtype=float)
        total += len(life)
        stock_counts[code] = stock_counts.get(code, 0) + len(life)
        hist_counts += np.histogram(np.log10(np.clip(life, 1e-3, None)), bins=hist_bins)[0]
        counts = np.array(
            [
                np.sum(life < 0.2),
                np.sum((life >= 0.2) & (life < 1)),
                np.sum((life >= 1) & (life < 10)),
                np.sum((life >= 10) & (life < 60)),
                np.sum((life >= 60) & (life < 1800)),
                np.sum(life >= 1800),
            ],
            dtype=np.int64,
        )
        segment_counts[code] = segment_counts.get(code, np.zeros(6, dtype=np.int64)) + counts
        del df, life

    fig, ax = plt.subplots(figsize=(9, 4.5))
    widths = np.diff(hist_bins)
    ax.bar(hist_bins[:-1], hist_counts, width=widths, align="edge", color="#4C78A8", edgecolor="#ffffff", linewidth=0.25)
    tick_seconds = [1e-3, 1e-2, 1e-1, 1, 10, 60, 600, 3600, 18000]
    tick_labels = ["1ms", "10ms", "100ms", "1s", "10s", "1min", "10min", "1h", "5h"]
    ax.set_xticks(np.log10(tick_seconds), tick_labels)
    ax.set_xlabel("订单寿命")
    ax.set_ylabel("订单数")
    ax.set_title("订单寿命分布（15 股 × 10 日全样本，log10 时间轴）")
    for sec, label in [(0.2, "0.2s"), (1, "1s"), (10, "10s")]:
        x = np.log10(sec)
        ax.axvline(x, color="#C44E52", linestyle="--", linewidth=1.1)
        ax.text(x, ax.get_ylim()[1] * 0.95, label, rotation=90, va="top", ha="right", color="#8B1E2D", fontsize=9)
    ax.grid(axis="y", color="#d0d7de", alpha=0.45, linewidth=0.7)
    fig.tight_layout()
    fig.savefig(ASSETS / "life_hist_all.png", dpi=180)
    plt.close(fig)

    stocks = load_stock_order()
    rows = []
    for stock in stocks:
        code = str(stock["code"]).zfill(6)
        counts = segment_counts.get(code, np.zeros(6, dtype=np.int64))
        rows.append((code, stock["stratum"], counts, stock_counts.get(code, 0)))

    labels = [f"{code}({stratum})" for code, stratum, _, _ in rows]
    counts_matrix = np.vstack([counts for _, _, counts, _ in rows]).astype(float)
    shares = counts_matrix / np.maximum(counts_matrix.sum(axis=1, keepdims=True), 1)
    colors = ["#08306B", "#08519C", "#2171B5", "#6BAED6", "#9ECAE1", "#C6DBEF"]

    fig, ax = plt.subplots(figsize=(10, 6))
    y = np.arange(len(rows))
    left = np.zeros(len(rows))
    for idx, name in enumerate(segment_names):
        ax.barh(y, shares[:, idx] * 100, left=left * 100, color=colors[idx], edgecolor="white", linewidth=0.4, label=name)
        left += shares[:, idx]
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 112)
    ax.set_xlabel("占比")
    ax.set_title("各股票订单寿命结构（六个寿命段占比）")
    ax.xaxis.set_major_formatter(lambda x, _: f"{x:.0f}%")
    for sep in [4.5, 9.5]:
        ax.axhline(sep, color="#6b7280", linewidth=0.9, alpha=0.7)
    for yi, (_, _, _, n) in enumerate(rows):
        ax.text(101, yi, f"{n / 10000:.1f}万笔", va="center", ha="left", fontsize=9, color="#1f2937")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=False)
    ax.grid(axis="x", color="#d0d7de", alpha=0.5, linewidth=0.7)
    fig.tight_layout(rect=[0, 0.07, 1, 1])
    fig.savefig(ASSETS / "life_structure_by_stock.png", dpi=180)
    plt.close(fig)

    print(f"N_total={total}")
    for code in [str(stock["code"]).zfill(6) for stock in stocks]:
        print(f"{code}={stock_counts.get(code, 0)}")
    return total, stock_counts


def build_order_case_table(soup: BeautifulSoup):
    life = pd.read_parquet(ALGO / "outputs" / "lifecycle" / "code=000001" / "date=2024-01-02" / "lifecycle.parquet")
    flags = pd.read_parquet(ALGO / "outputs" / "flags" / "code=000001" / "date=2024-01-02" / "order_flags.parquet")
    cols = [
        "order_id",
        "side",
        "submit_ts",
        "cancel_ts",
        "life_s",
        "end_state",
        "submit_qty",
        "fill_ratio",
        "qty_scaled",
        "bbo_diff_ticks",
        "depth_rank",
        "flag_ee",
        "flag_ccp_sruns",
        "gb_seed_label",
    ]
    df = life.merge(flags, on="order_id", how="left")[cols].head(12)
    ids = df["order_id"].tolist()
    if ids[0] != 425121 or ids[-1] != 434924:
        raise RuntimeError(f"unexpected order_id range: {ids[0]}..{ids[-1]}")

    tooltips = {
        "order_id": "订单 ID",
        "side": "买卖方向",
        "submit_ts": "订单提交时间",
        "cancel_ts": "订单撤单时间；NaT 表示未撤",
        "life_s": "订单寿命（秒）；挂到连续竞价结束按 14:57 计算",
        "end_state": "最终状态：filled / cancelled / partial_cancelled / expired_eod",
        "submit_qty": "提交时报单的股数",
        "fill_ratio": "最终成交量占报单量的比例（1=全部成交，0=一股未成）",
        "qty_scaled": "报单量相对当天全市场中位数报单量的倍数（>1 = 比典型订单大）",
        "bbo_diff_ticks": "订单价格离同侧最优报价的真实档位数",
        "depth_rank": "订单挂在订单簿第几档",
        "flag_ee": "EE 两步法并集标记",
        "flag_ccp_sruns": "CCP 策略性重挂链成员",
        "gb_seed_label": "GB 弱监督种子标签：1 正种子，0 负种子，-1 灰区",
    }

    table = soup.new_tag("table", attrs={"class": "data-table"})
    thead = soup.new_tag("thead")
    tr = soup.new_tag("tr")
    for col in cols:
        th = soup.new_tag("th", attrs={"title": tooltips[col]})
        th.string = col
        tr.append(th)
    thead.append(tr)
    tbody = soup.new_tag("tbody")
    for _, row in df.iterrows():
        tr = soup.new_tag("tr")
        for col in cols:
            td = soup.new_tag("td", attrs={"title": ""})
            td.string = fmt_value(row[col])
            tr.append(td)
        tbody.append(tr)
    table.append(thead)
    table.append(tbody)
    return table


def build_cross_corr_table(soup: BeautifulSoup):
    panel = pd.read_parquet(ALGO / "outputs" / "panel" / "panel_stock_day.parquet")
    metric_to_cluster = {metric: cluster for cluster, metrics in METRIC_CLUSTERS.items() for metric in metrics}
    metrics = [m for cluster in METRIC_CLUSTERS.values() for m in cluster if m in panel.columns]
    corr = panel[metrics].apply(pd.to_numeric, errors="coerce").corr(method="spearman")
    rows = []
    for i, a in enumerate(metrics):
        for b in metrics[i + 1 :]:
            if metric_to_cluster[a] == metric_to_cluster[b]:
                continue
            rho = corr.loc[a, b]
            if pd.notna(rho) and abs(rho) >= 0.9:
                rows.append((a, b, metric_to_cluster[a], metric_to_cluster[b], rho))
    rows = sorted(rows, key=lambda row: abs(row[4]), reverse=True)[:10]

    table = soup.new_tag("table", attrs={"class": "data-table compact"})
    thead = soup.new_tag("thead")
    tr = soup.new_tag("tr")
    heads = ["metric_a", "metric_b", "cluster_a", "cluster_b", "spearman"]
    tips = ["", "", "", "", "跨类 Spearman 相关；这里只展示 |rho|>=0.9 的前 10 对"]
    for h, tip in zip(heads, tips):
        th = soup.new_tag("th", attrs={"title": tip})
        th.string = h
        tr.append(th)
    thead.append(tr)
    tbody = soup.new_tag("tbody")
    for a, b, ca, cb, rho in rows:
        tr = soup.new_tag("tr")
        for value, is_metric in [(a, True), (b, True), (ca, False), (cb, False), (fmt_value(rho), False)]:
            td = soup.new_tag("td", attrs={"title": ""})
            if is_metric:
                frag = BeautifulSoup(metric_span(value), "html.parser")
                td.append(frag)
            else:
                td.string = value
            tr.append(td)
        tbody.append(tr)
    table.append(thead)
    table.append(tbody)
    return table


def html_fragment(soup: BeautifulSoup, html: str):
    return BeautifulSoup(html, "html.parser")


def cluster_details() -> dict[str, str]:
    return {
        "1": """
<h4>类 1｜短生命 / 快速撤单</h4>
<p>核心：订单寿命 $\\ell_i$ 的左尾</p>
<p>记每笔订单 $i$ 的寿命 $\\ell_i$（提交到撤单/成交完/收盘终止的秒数），$N$ 为当日订单总数，$q_i$ 为报单量。</p>
<ul class="cluster-metric-points">
<li><span class="metric metric-ee">ee__step1_share</span>：提交后 1 秒内被撤的订单占比。$\\dfrac{1}{N}\\sum_i \\mathbf{1}\\{\\text{被撤}_i \\wedge \\ell_i &lt; 1\\text{s}\\}$</li>
<li><span class="metric metric-kx">kx__short_cancel_lt_1s</span> / <span class="metric metric-kx">lt_10s</span>：与上式同构，阈值分别取 $\\tau = 1$ 秒和 $10$ 秒。备注：1 秒版与 <span class="metric metric-ee">ee__step1_share</span> 几乎是同一个数，只差寿命口径细节。</li>
<li><span class="metric metric-ccp">ccp__fleet</span>：同一事件不做归一化的<strong>日内计数</strong> $\\sum_i \\mathbf{1}\\{\\text{被撤}_i \\wedge \\ell_i &lt; 1\\text{s}\\}$。备注：≈ <span class="metric metric-ee">ee__step1_share</span> × 当日订单总数，因此强烈受股票活跃度影响。</li>
<li><span class="metric metric-kx">kx__life_p10/p25/p50/p75/p90</span>：寿命分布的五个分位数 $Q_{10\\%}(\\ell), \\dots, Q_{90\\%}(\\ell)$。备注："阈值处的占比"和"分位数"是同一分布的两种读法；本样本中 p10、p25 恒为 0（大量订单瞬间成交），已退化。</li>
<li><span class="metric metric-ee">ee__hft_ratio</span>：EE 两步标记的并集占比 $|S_1 \\cup S_2| / N$，其中 $S_1$ 为快撤集合、$S_2$ 为关联扩散集合（见类 2）。</li>
<li><span class="metric metric-ee">ee__flag_qty_share</span>：同一并集换成量加权 $\\sum_{i \\in S_1 \\cup S_2} q_i \\big/ \\sum_i q_i$。</li>
</ul>
<p>本类真正的自由度约 2 个："寿命左尾多重"＋"快撤单占多少报单量"，其余是阈值/归一化变体。</p>
""",
        "2": """
<h4>类 2｜链式重复下单 / 订单簇</h4>
<p>核心：相似订单 + 时间邻近 → 连成链</p>
<ul class="cluster-metric-points">
<li><span class="metric metric-ee">EE step2</span>：以每个快撤单 $i \\in S_1$ 为种子，在 $[t_i - w,\\ t_i + w]$（$w = 1$ 秒）内寻找<strong>同代码、同方向、同数量</strong>（默认还要求同通道）的其他订单，全部并入 $S_2$——"抓到一个快手，顺藤摸出同伙"。</li>
<li><span class="metric metric-ccp">ccp__sruns</span>：把"撤单 → 毫秒级间隔内重新挂单"连成链，链上订单数 $\\ge$ 阈值（run_min_len）记一条 run；指标 = 当日 run 条数——同一算法反复报撤的直接证据。</li>
<li><span class="metric metric-gb">gb__seed_pos</span>：$|\\{i : \\text{flag\\_ee\\_step1}_i \\vee \\text{flag\\_ccp\\_sruns}_i\\}|$。备注：类 1 与类 2 的机械并集，是 GB 训练的簿记量，不是独立因子。</li>
</ul>
""",
        "3": """
<h4>类 3｜消息强度 / 订单成交比（OTR）</h4>
<p>核心：单位成交承载的消息量</p>
<ul class="cluster-metric-points">
<li><span class="metric metric-kx">kx__otr_day</span>：$\\dfrac{\\#\\text{报单} + \\#\\text{撤单}}{\\max(\\#\\text{成交}, 1)}$——每撮合成一笔交易，市场要"喊"多少嗓子。</li>
<li><span class="metric metric-ccp">ccp__mess</span>：距同侧最优报价 $\\le k$ 档（配置 near_bbo_ticks）的报单+撤单<strong>计数</strong>；<span class="metric metric-ccp">ccp__can</span>：其中撤单的计数。备注：can ⊂ mess，机械相关；两者都未归一化，横截面上被活跃度主导。</li>
<li><span class="metric metric-hjm">hjm__msg_per_volume</span>：$\\dfrac{\\#\\text{全部事件}}{\\sum_{\\text{成交}} q}$。备注：OTR 的近亲，分母从笔数换成股数。</li>
</ul>
""",
        "4": """
<h4>类 4｜盘口报价扰动 / 簇发</h4>
<p>核心：L1 序列的变动频率与幅度</p>
<p>令 $x_t = \\mathbf{1}\\{\\text{第 } t \\text{ 秒买一/卖一价或量发生变动}\\}$。</p>
<ul class="cluster-metric-points">
<li><span class="metric metric-ccp">ccp__quoteint</span>：$\\sum_t x_t$——盘口变动的总秒数。</li>
<li><span class="metric metric-kx">kx__burst_count</span> / <span class="metric metric-kx">kx__burst_seconds</span>：对同一计数做 $w$ 秒滚动和，$\\sum_{s \\in (t-w, t]} x_s \\ge m$ 记为"簇发状态"；count = 进入簇发的次数，seconds = 处于簇发的累计秒数——quote stuffing（报价轰炸）视角。</li>
<li><span class="metric metric-ccp">ccp__flick</span>：桶内 1 秒中间价的标准差 $\\mathrm{std}(m_t)$——前三个量"变动多不多"，这个量"晃动大不大"。</li>
</ul>
""",
        "5": """
<h4>类 5｜事件响应速度</h4>
<p>模板：盘口事件 → 开短窗 → 数跟随行为</p>
<ul class="cluster-metric-points">
<li><span class="metric metric-ccp">ccp__sresp</span>：每次报价改善（买一上抬或卖一下压）后开一个响应窗口，找到第一个响应事件（同侧追单 / 同侧撤单 / 对改善价的成交）计 1，全日累计——市场对新报价的整体反应速度。</li>
<li><span class="metric metric-kkst">kkst__newlevel_maker_lift</span>：L1 发生不利变动后，$\\mathrm{mean}\\Big(\\dfrac{\\text{窗口内新报单中被标记订单的占比}}{\\text{全日被标记订单占比}}\\Big)$——大于 1 说明被标记群体在盘口变化后<strong>抢先</strong>重新报价。</li>
</ul>
""",
        "6": """
<h4>类 6｜主动成交 / 知情性</h4>
<p>核心：taker 行为与价格变动的先后关系</p>
<ul class="cluster-metric-points">
<li><span class="metric metric-ccp">ccp__ioc</span>：主动吃单订单计数 $\\#\\{i : \\text{is\\_taker}_i\\}$。</li>
<li><span class="metric metric-kkst">kkst__aggressive_ratio_flagged</span>：$\\dfrac{\\sum_{\\text{主动方被标记的成交}} q}{\\sum_{\\text{全部主动成交}} q}$——被标记群体吃掉了多大比例的主动成交量。</li>
<li><span class="metric metric-kkst">kkst__snipe_taker_lift</span>：每次不利价格变动<strong>之前</strong>取最近 $k$ 笔成交，算可疑 taker 的量占比，再除以全日基准占比后取平均——大于 1 = 价格要动之前，可疑资金先动手（狙击旧报价）。</li>
<li><span class="metric metric-kkst">kkst__flow_price_beta_lag0</span>~<span class="metric metric-kkst">lag5</span>：令 $f_t$ 为第 $t$ 秒被标记订单的带符号成交量（买 $+$ 卖 $-$），$\\beta_\\ell = \\dfrac{\\mathrm{Cov}(f_t,\\ \\Delta m_{t+\\ell})}{\\mathrm{Var}(f_t)}$，$\\ell = 0, \\dots, 5$——被标记资金流对未来中间价变动的预测系数。</li>
<li><span class="metric metric-kkst">kkst__flow_price_beta0</span>：备注：代码级复制 = <span class="metric metric-kkst">beta_lag0</span>，纯冗余。</li>
</ul>
""",
        "7": """
<h4>类 7｜成交经济后果</h4>
<p>核心：成交价相对当前/未来中间价的偏离；HJM 验证器</p>
<p>对每笔成交 $i$（价格 $p_i$，成交时中间价 $m_0$，$\\Delta$ 秒后中间价 $m_1$，方向 $d_i = +1$ 买方主动 / $-1$ 卖方主动）：</p>
<ul class="cluster-metric-points">
<li><span class="metric metric-hjm">hjm__espread_bps</span>：有效价差 $ES_i = d_i\\,\\dfrac{p_i - m_0}{m_0}$——成交那一刻付出的即时成本。</li>
<li><span class="metric metric-hjm">hjm__rspread_bps</span>：已实现价差 $RS_i = d_i\\,\\dfrac{p_i - m_1}{m_0}$——扣掉后续价格漂移后，做市方真正赚到的部分。</li>
<li><span class="metric metric-hjm">hjm__advsel_bps</span>：逆向选择成本 $AS_i = ES_i - RS_i$。备注：<strong>恒等式差值</strong>，三者只有两个自由度。面板值均为成交量加权平均 × $10^4$（bps）。</li>
<li><span class="metric metric-hjm">hjm__trade_size</span>：平均单笔成交股数——算法拆单越狠，这个数越小。</li>
</ul>
""",
        "8": """
<h4>类 8｜撤单–成交交互（fade / spoof 形态）</h4>
<p>每笔成交（时刻 $t$、价格 $p$、量 $q$）后开 $w$ 秒窗口，统计 maker 同侧、同价（或 ± 价格带）的撤单总量 $C$：</p>
<ul class="cluster-metric-points">
<li><span class="metric metric-kx">kx__fade_partial_prob</span>：$\\Pr(C &gt; 0)$——成交后同侧同价"缩手"的概率。</li>
<li><span class="metric metric-kx">kx__fade_full_prob</span>：$\\Pr(C \\ge q)$——撤掉的比成交的还多。备注：嵌套关系，恒有 partial ≥ full。</li>
</ul>
<p>备注：与类 1 的区别在于这里看撤单与<strong>成交事件的时间排布</strong>，是本项目唯一直接刻画 spoofing 形态的指标，逻辑独立性较高。</p>
""",
        "9": """
<h4>类 9｜弱监督模型综合（GB）</h4>
<p>用 11 个订单特征（寿命、离盘口档数、相对报单量、成交比例、是否主动、终态、时段……）训练梯度提升模型：正种子 = EE step1 ∪ SRuns 命中订单，负种子 = 长寿 + 正常完结 + 不超过中位数量的"类人"订单，其余为灰区。模型输出每笔订单的"疑似算法概率" $\\hat p_i$。</p>
<ul class="cluster-metric-points">
<li><span class="metric metric-gb">gb__sum_p</span>：$\\sum_i \\hat p_i$——全日"算法嫌疑总量"（按笔）。</li>
<li><span class="metric metric-gb">gb__sum_p_amount</span>：$\\sum_i \\hat p_i \\cdot (q_i \\times p_i)$——按订单金额加权的嫌疑总量。</li>
<li><span class="metric metric-gb">gb__seed_pos</span> / <span class="metric metric-gb">gb__seed_neg</span>：正/负种子订单数。备注：训练簿记量；由于训练标签来自类 1+2，GB 分数天然与那些类共线，是"非线性重组"而非独立信号源。</li>
</ul>
""",
    }


def update_html(n_total: int):
    soup = BeautifulSoup(HTML.read_text(encoding="utf-8"), "html.parser")
    head = soup.head

    if not soup.find("script", src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"):
        config = soup.new_tag("script")
        config.string = "\n  window.MathJax = { tex: { inlineMath: [['$', '$'], ['\\\\(', '\\\\)']] } };\n"
        loader = soup.new_tag("script", src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js")
        loader["async"] = ""
        style = head.find("style")
        style.insert_before(config)
        style.insert_before(loader)

    style = soup.find("style")
    css = style.string or ""
    if ".explain-caption" not in css:
        css = css.replace(
            "    .figure figcaption { margin-top: 8px; color: #40524c; font-size: 13px; }\n",
            "    .figure figcaption { margin-top: 8px; color: #40524c; font-size: 13px; }\n"
            "    .explain-caption { margin: 8px 0 16px; padding: 8px 10px 8px 12px; border-left: 3px solid var(--gold); color: var(--muted); background: rgba(255,255,255,.035); font-size: 13px; line-height: 1.7; }\n"
            "    .figure .explain-caption { margin: 10px 0 0; color: #40524c; background: #eef3ee; }\n"
            "    .cluster-metric-points { margin: 12px 0 0; padding-left: 20px; }\n"
            "    .cluster-metric-points li { margin: 9px 0; }\n",
        )
        style.string = css

    for node in soup.select(".explain-caption"):
        node.decompose()

    guardrail = soup.select_one(".guardrail")
    if guardrail:
        guardrail.decompose()

    conclusion = soup.select_one("section.conclusion")
    if conclusion:
        conclusion.decompose()

    lifecycle = soup.find("section", id="lifecycle")
    old_life_fig = lifecycle.find("img", src=lambda v: v and "cell_0007_output_0002.png" in v).find_parent("figure")
    for sib in list(old_life_fig.find_next_siblings()):
        if sib.name == "p":
            sib.decompose()
            break
        if sib.name:
            break
    fig_html = """
<figure class="figure">
<img src="assets/algo-footprint-2026-07-07/life_hist_all.png" alt="订单寿命分布（15 股 × 10 日全样本，log10 时间轴）" loading="lazy"/>
<figcaption>订单寿命分布（15 股 × 10 日全样本，log10 时间轴）</figcaption>
</figure>
<figure class="figure">
<img src="assets/algo-footprint-2026-07-07/life_structure_by_stock.png" alt="各股票订单寿命结构（六个寿命段占比）" loading="lazy"/>
<figcaption>各股票订单寿命结构（六个寿命段占比）</figcaption>
</figure>
"""
    old_life_fig.replace_with(html_fragment(soup, fig_html))

    order_h3 = lifecycle.find("h3", string=lambda s: s and "逐笔案例表" in s)
    order_scroll = order_h3.find_next("div", class_="table-scroll")
    order_scroll.clear()
    order_scroll.append(build_order_case_table(soup))

    metrics = soup.find("section", id="metrics")
    for article in metrics.select("article.cluster-detail"):
        panel = article.get("data-cluster-panel")
        article.clear()
        article.append(html_fragment(soup, cluster_details()[panel]))

    if not metrics.find("h3", string=lambda s: s and "跨类高相关指标对" in s):
        h3 = soup.new_tag("h3")
        h3.string = "跨类高相关指标对（前 10 / 共 30 对）"
        div = soup.new_tag("div", attrs={"class": "table-scroll"})
        div.append(build_cross_corr_table(soup))
        last_article = metrics.select("article.cluster-detail")[-1]
        last_article.insert_after(div)
        div.insert_before(h3)

    n_wan = f"{round(n_total / 10000)} 万"
    CAPTIONS_FIGURES[0] = f"把全部 150 个股票日、约 {n_wan}笔委托的寿命放进同一张对数时间轴的直方图里。三条虚线（0.2 秒 / 1 秒 / 10 秒）是后续各方法用到的关键阈值。这个分布明显不止一个山峰：最左边有一大群不到 1 秒就消失的\"秒撤\"订单，最右边有一大群从早挂到收盘的订单，中间才是普通的交易节奏。算法痕迹检测关心的就是最左边那一群——人类点鼠标做不到这个速度。"

    tables = soup.find_all("table")
    if len(tables) != len(CAPTIONS_TABLE):
        raise RuntimeError(f"table count mismatch: {len(tables)} vs {len(CAPTIONS_TABLE)}")
    for table, text in zip(tables, CAPTIONS_TABLE):
        scroll = table.find_parent("div", class_="table-scroll")
        scroll.insert_after(caption_tag(soup, text))

    figures = soup.find_all("figure")
    if len(figures) != len(CAPTIONS_FIGURES):
        raise RuntimeError(f"figure count mismatch: {len(figures)} vs {len(CAPTIONS_FIGURES)}")
    for figure, text in zip(figures, CAPTIONS_FIGURES):
        figure.append(caption_tag(soup, text))

    script = soup.find("script", string=lambda s: s and "clusterCards.forEach" in s)
    js = script.string
    if "MathJax.typesetPromise" not in js:
        js = js.replace(
            "    clusterEmpty.hidden = true;\n  }));",
            "    clusterEmpty.hidden = true;\n"
            "    const panel = clusterDetails.find((node) => node.dataset.clusterPanel === id);\n"
            "    if (window.MathJax && panel) MathJax.typesetPromise([panel]);\n"
            "  }));",
        )
        script.string = js

    HTML.write_text(str(soup), encoding="utf-8", newline="\n")


def main():
    n_total, _ = generate_life_figures()
    update_html(n_total)


if __name__ == "__main__":
    main()
