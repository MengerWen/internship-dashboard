from __future__ import annotations

import argparse
import base64
from collections import defaultdict
from io import BytesIO
import hashlib
import html
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable, Mapping

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "artifacts" / "open5m-report-2026-08-07"
DEFAULT_RESEARCH_REPO = ROOT.parent.parent / "26 Summer" / "❗思瑞投资" / "sirui-quant-research"
DEFAULT_OUTPUT = ROOT / "content" / "daily" / "2026-08-07.html"
DEFAULT_WEBSITE_OUTPUT = ROOT / "content" / "daily" / "2026-08-07.show.html"
DEFAULT_ASSET_DIR = ROOT / "content" / "assets" / "open5m-factor-report-2026-08-07"
DEFAULT_ASSET_URL_PREFIX = "assets/open5m-factor-report-2026-08-07"
OLD_SELF_CONTAINED = ROOT / "content" / "daily" / "2026-08-04.html"
EXPECTED_FACTORS = 495
EXPECTED_FORMAL = 490
EXPECTED_DIAGNOSTICS = 5
EXPECTED_IMAGES = EXPECTED_FACTORS * 4
CLOUDFLARE_SINGLE_ASSET_LIMIT = 25 * 1024 * 1024
INLINE_IMAGE_RUNTIME = 'src="data:${im.mime};base64,${im.data}"'
WEBSITE_IMAGE_RUNTIME = 'src="${im.url}"'
METRICS = {"ic": "IC", "rank_ic": "Rank_IC", "icir": "ICIR"}
PERIODS = {"full_history": "完整历史", "q2": "2026Q2"}
LAYER_LABELS = {
    "L1": "老 scorer 的五方向投影",
    "L1_diagnostic": "市场行为诊断",
    "L2": "多证据共识",
    "L3": "订单级微观结构情境",
    "L4": "股票日窗口状态",
    "L5": "算法目的与流动性机制",
}
LAYER_COLORS = {
    "L1": "#315b7d",
    "L1_diagnostic": "#6e6962",
    "L2": "#aa352c",
    "L3": "#2f6964",
    "L4": "#9b6925",
    "L5": "#653e65",
}
PROJECTION_LABELS = {
    "total": "总活动",
    "buy": "买方向",
    "sell": "卖方向",
    "net": "买减卖净方向",
    "absnet": "买卖绝对不平衡",
    "purpose_specific": "目的专属",
    "": "目的专属",
}
KIND_LABELS = {
    "base_scorer_projection": "老 scorer 新口径",
    "market_behavior_diagnostic": "诊断列",
    "continuous_consensus": "连续共识",
    "order_context_interaction": "算法证据 × 订单情境",
    "window_state_interaction": "算法证据 × 窗口状态",
    "algorithm_purpose": "目的/机制复合",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def finite(value: Any) -> bool:
    return isinstance(value, (int, float, np.integer, np.floating)) and math.isfinite(float(value))


def clean_scalar(value: Any) -> Any:
    if value is None or value is pd.NA:
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def clean_mapping(row: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): clean_scalar(value) for key, value in row.items()}


def safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def normalize_source_alias(alias: str) -> str:
    return re.sub(r"^ctrl(\d+)", r"c\1", alias)


def factor_source_alias(factor_id: str) -> str:
    value = factor_id.split("__side_", 1)[0]
    value = value.split("__status_diagnostic", 1)[0]
    return normalize_source_alias(value)


def parse_markdown_code_rows(text: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        cells = [cell.strip() for cell in line[1:-1].split("|")]
        if len(cells) < 2:
            continue
        key = cells[0].strip().strip("`")
        if not re.fullmatch(r"(?:f\d+|c\d+|ctrl\d+|cons_[a-z0-9_]+|x\d+_[a-z0-9_]+|z\d+_[a-z0-9_]+|p\d+_[a-z0-9_]+)[A-Za-z0-9_/-]*", key):
            continue
        result.setdefault(key, cells[1:])
    return result


def extract_katex_assets(path: Path) -> tuple[str, str, str]:
    source = path.read_text(encoding="utf-8")
    css_match = re.search(r'<style id="katex-self-contained">(.*?)</style>', source, flags=re.S)
    js_match = re.search(r'<script id="katex-runtime">(.*?)</script>', source, flags=re.S)
    auto_match = re.search(r'<script id="katex-auto-render">(.*?)</script>', source, flags=re.S)
    if not css_match or not js_match or not auto_match:
        raise RuntimeError("frozen report does not contain embedded KaTeX assets")
    return css_match.group(1), js_match.group(1), auto_match.group(1)


def load_registry_metadata(research_repo: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, list[str]], str]:
    registry_path = research_repo / "PLAN" / "factor_preregister_intraday_open5m_count_proxy_v2.yaml"
    index_path = (
        research_repo
        / "因子"
        / "algobench"
        / "research"
        / "新factors_open5m_count_proxy_v2"
        / "NOTEBOOK_INDEX.json"
    )
    plan_path = research_repo / "PLAN" / "2026-08-06-高频量价与微观结构新因子批量构建实施计划.md"
    for path in (registry_path, index_path, plan_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    document = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    index = read_json(index_path)
    if index.get("factor_count") != EXPECTED_FACTORS:
        raise RuntimeError("Notebook index does not contain 495 factors")
    rows = index.get("notebooks", [])
    if len(rows) != EXPECTED_FACTORS:
        raise RuntimeError("Notebook index inventory is incomplete")
    plan_text = plan_path.read_text(encoding="utf-8")
    return document["count_proxy_registry"], rows, parse_markdown_code_rows(plan_text), plan_text


def component_maps(registry: Mapping[str, Any]) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    logical_to_component: dict[str, str] = {}
    components: dict[str, dict[str, Any]] = {}
    for section in ("consensus", "contexts", "window_states", "purposes"):
        for row in registry.get(section, []):
            logical_to_component[str(row["factor_id"])] = str(row["id"])
            components[str(row["id"])] = dict(row)
    return logical_to_component, components


def projection_formula(projection: str) -> str:
    return {
        "total": r"$(U^B+U^S)/N$",
        "buy": r"$U^B/N$",
        "sell": r"$U^S/N$",
        "net": r"$(U^B-U^S)/N$",
        "absnet": r"$|U^B-U^S|/N$",
        "purpose_specific": "按该目的因子的专属公式直接除以全部有效去重订单数 $N$",
        "": "按该目的因子的专属公式直接除以全部有效去重订单数 $N$",
    }[projection]


def projection_interpretation(projection: str) -> str:
    return {
        "total": "高值表示买卖两侧合计的该类算法痕迹更强；不提供净买卖方向。",
        "buy": "高值表示买方向订单贡献更强；分母仍是全部订单，不是买单内部占比。",
        "sell": "高值表示卖方向订单贡献更强；分母仍是全部订单，不是卖单内部占比。",
        "net": "正值偏买、负值偏卖，绝对值反映方向差；0 可能是两侧都弱，也可能是强度相抵。",
        "absnet": "高值表示买卖两侧高度不平衡，但不保留究竟偏买还是偏卖。",
        "purpose_specific": "保留该机制定义本身的经济方向；正负含义由具体公式决定。",
        "": "保留该机制定义本身的经济方向；正负含义由具体公式决定。",
    }[projection]


def layer_construction(layer: str, component: str, formula: str) -> list[str]:
    if layer == "L1":
        return [
            r"从冻结的老 scorer 取得每张订单连续分数 $s_{k,i}\in[0,1]$。",
            "不可观察值贡献 0，并单独保留覆盖率遥测；不再创造阈值、平方等 evidence 版本。",
            f"按买卖侧累计后使用 {formula}，公共分母是窗口内全部有效去重订单数。",
            "这只是老逻辑的新窗口/新分母/方向投影，不占用新的 f 序号。",
        ]
    if layer == "L1_diagnostic":
        return [
            "复用市场行为 scorer 的订单级连续分数。",
            "按全部订单分母生成状态诊断，检查快速成交、深度消耗、扫档或一次性吃单。",
            "该列可以参与其他复合因子的上下文，但不进入 490 个正式候选排名。",
        ]
    if layer == "L2":
        return [
            "先在订单级形成生命周期 $L$、pair $P$、订单链 $C$、市场响应 $R$ 四个证据族。",
            "族内高度相关 scorer 取最大值，避免一张订单因为近似规则重复加分。",
            f"对四族统计量应用 `{component}` 的冻结公式：{formula}。",
            "结果仍除以全部订单数；它描述证据共识，不是已知算法账户概率。",
        ]
    if layer == "L3":
        return [
            r"对每张订单先得到唯一联合算法证据 $A_i=\max(L_i,P_i,C_i,R_i)$。",
            f"在动作发生前读取 `{component}` 微观结构上下文，官方定义为：{formula}。",
            "形成订单贡献 $u_i=A_i x_i$，因此裸价差、裸 OFI、裸波动不会冒充算法因子。",
            "最后按五种方向投影除以共同分母 $N$。",
        ]
    if layer == "L4":
        return [
            "只用 09:30–09:35 全窗口事件构造一次股票日状态 $Z_{d}$。",
            f"状态 `{component}` 的冻结定义为：{formula}。",
            "把同一股票日状态与订单级联合证据相乘：$u_i=A_i Z_d$。",
            "再做五方向投影；状态不读取 09:35 后价格或收益标签。",
        ]
    return [
        "复用联合证据、生命周期、pair/chain、动作前盘口与共享响应触发器。",
        f"按照 `{component}` 的专属订单贡献公式计算：{formula}。",
        "同一订单命中多个相近 scorer 时优先取最大值，避免重复计数。",
        "按全部订单数归约，直接解释算法目的、流动性供给/索取或冲击后的行为。",
    ]


def layer_boundary(layer: str) -> str:
    return {
        "L1": "这是原因子定义的工程化投影，不能称为独立的新经济逻辑；pair/chain scorer 的高值也不等同于已知同账户。",
        "L1_diagnostic": "诊断列只刻画市场行为状态，不进入正式 Alpha 比较；NA 与 0 必须区分。",
        "L2": "四族共识降低单规则误命中，但仍只是可观察痕迹强度，不是算法订单真实概率。",
        "L3": "它衡量算法痕迹所处的市场状态，不证明该状态由算法造成，也不发布纯市场 Alpha。",
        "L4": "窗口状态在同一股票日内对所有订单相同，预测力可能来自状态本身、算法关注或二者交互，不能直接作结构因果解释。",
        "L5": "目的标签来自行为机制代理；做市、执行、撤退、羊群等名称是研究解释，不代表账户身份或监管定性。",
    }[layer]


def build_factor_metadata(
    item: Mapping[str, Any],
    logical_to_component: Mapping[str, str],
    components: Mapping[str, Mapping[str, Any]],
    plan_rows: Mapping[str, list[str]],
) -> dict[str, Any]:
    factor_id = str(item["factor_id"])
    logical = str(item["logical_factor_id"])
    layer = str(item["layer"])
    projection = str(item.get("projection", ""))
    if layer in {"L1", "L1_diagnostic"}:
        component = factor_source_alias(factor_id)
    else:
        component = logical_to_component.get(logical, logical)
    cells = list(plan_rows.get(component, []))
    if layer == "L1" or layer == "L1_diagnostic":
        description = cells[0] if cells else "冻结 scorer 的订单级连续行为证据。"
        formula = r"$u_i=s_{k,i}$"
        whitepaper = "六篇算法痕迹文献/KX 白皮书迁移后的老 scorer 底座"
    elif layer == "L2":
        description = {
            "cons_union": "四个机制证据族中最强一族的订单级并集强度。",
            "cons_breadth": "四个机制证据族的平均支持广度。",
            "cons_top2": "第二强证据族，要求至少两类机制同时支持。",
            "cons_top3": "第三强证据族，更严格地排除单一规则偶然命中。",
        }.get(component, "多证据共识强度。")
        formula = cells[0] if cells else str(components.get(component, {}).get("formula", ""))
        whitepaper = "证据工程层；不是白皮书单一指标的直接复制"
    elif layer == "L3":
        formula = cells[0] if cells else str(components.get(component, {}).get("formula", ""))
        description = cells[1] if len(cells) > 1 else "订单级微观结构上下文与算法证据交互。"
        whitepaper = "价差、深度、盘口不平衡、OFI/成交流、趋势、波动、跳跃与订单簿形态"
    elif layer == "L4":
        formula = cells[0] if cells else "窗口状态与联合算法证据交互"
        description = cells[1] if len(cells) > 1 else "股票日窗口量价或流动性状态。"
        whitepaper = description
    else:
        formula = cells[0] if cells else "算法目的或流动性机制的专属贡献公式"
        description = cells[1] if len(cells) > 1 else "算法目的或流动性机制复合因子。"
        whitepaper = "做市/主动执行、订单流吸收、撤单冲击、韧性、羊群与非流动性机制"
    display_name = logical if layer not in {"L1", "L1_diagnostic"} else component
    return {
        "record_id": factor_id,
        "logical_factor_id": logical,
        "display_name": display_name,
        "component_id": component,
        "kind": str(item["kind"]),
        "kind_label": KIND_LABELS[str(item["kind"])],
        "layer": layer,
        "layer_label": LAYER_LABELS[layer],
        "layer_color": LAYER_COLORS[layer],
        "projection": projection,
        "projection_label": PROJECTION_LABELS.get(projection, projection or "目的专属"),
        "description": description,
        "formula": formula,
        "aggregation_formula": projection_formula(projection),
        "projection_interpretation": projection_interpretation(projection),
        "construction_steps": layer_construction(layer, component, formula),
        "interpretation_boundary": layer_boundary(layer),
        "whitepaper_link": whitepaper,
        "notebook_template_path": str(item.get("relative_path", "")),
        "diagnostic": layer == "L1_diagnostic",
    }


def set_plot_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.titlesize": 10,
            "axes.labelsize": 8,
            "axes.edgecolor": "#a9a095",
            "axes.linewidth": 0.7,
            "axes.facecolor": "#fffdf8",
            "figure.facecolor": "#fffdf8",
            "grid.color": "#ddd6ca",
            "grid.linewidth": 0.5,
            "xtick.color": "#5f686c",
            "ytick.color": "#5f686c",
            "axes.labelcolor": "#3c484e",
            "text.color": "#17242d",
        }
    )


def image_payload(fig: plt.Figure, name: str, description: str) -> dict[str, Any]:
    png = BytesIO()
    fig.savefig(png, format="png", dpi=100, bbox_inches="tight", facecolor="#fffdf8")
    plt.close(fig)
    png.seek(0)
    image = Image.open(png).convert("RGB")
    webp = BytesIO()
    image.save(webp, format="WEBP", quality=76, method=4)
    data = webp.getvalue()
    return {
        "name": name,
        "description": description,
        "mime": "image/webp",
        "width": image.width,
        "height": image.height,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "data": base64.b64encode(data).decode("ascii"),
    }


def empty_axes(ax: plt.Axes, message: str) -> None:
    ax.set_axis_off()
    ax.text(0.5, 0.5, message, ha="center", va="center", color="#7b7770", transform=ax.transAxes)


def daily_figure(frame: pd.DataFrame) -> plt.Figure:
    fig, axes = plt.subplots(2, 1, figsize=(10.8, 5.4), sharex=True, gridspec_kw={"height_ratios": [1.6, 1.0]})
    if frame.empty or not frame[["pearson_ic", "rank_ic"]].notna().any().any():
        empty_axes(axes[0], "No computable daily cross-sectional correlation")
        empty_axes(axes[1], "No cumulative evidence")
        return fig
    dates = pd.to_datetime(frame["date"])
    rank = frame["rank_ic"].astype(float)
    pearson = frame["pearson_ic"].astype(float)
    axes[0].plot(dates, rank, color="#315b7d", lw=0.65, alpha=0.48, label="daily RankIC")
    axes[0].plot(dates, rank.rolling(20, min_periods=5).mean(), color="#aa352c", lw=1.8, label="20d mean RankIC")
    axes[0].plot(dates, pearson.rolling(20, min_periods=5).mean(), color="#2f6964", lw=1.25, label="20d mean IC")
    axes[0].axhline(0, color="#756f68", lw=0.7)
    axes[0].grid(axis="y", alpha=0.65)
    axes[0].set_ylabel("correlation")
    axes[0].legend(loc="upper left", ncol=3, frameon=False, fontsize=7.5)
    axes[0].set_title("Daily cross-sectional IC / RankIC and 20-day stability", loc="left", fontweight="bold")
    axes[1].plot(dates, rank.fillna(0).cumsum(), color="#315b7d", lw=1.4, label="cum RankIC")
    axes[1].plot(dates, pearson.fillna(0).cumsum(), color="#2f6964", lw=1.1, label="cum IC")
    axes[1].axhline(0, color="#756f68", lw=0.7)
    axes[1].grid(axis="y", alpha=0.65)
    axes[1].set_ylabel("cumulative sum")
    axes[1].legend(loc="upper left", ncol=2, frameon=False, fontsize=7.5)
    axes[1].xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    axes[1].tick_params(axis="x", rotation=35)
    fig.tight_layout()
    return fig


def weekly_figure(frame: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10.8, 4.0))
    clean = frame.dropna(subset=["rank_ic"]).copy()
    if clean.empty:
        empty_axes(ax, "No computable weekly RankIC")
        return fig
    dates = pd.to_datetime(clean["date"])
    iso = dates.dt.isocalendar()
    clean["iso_week"] = iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)
    weekly = clean.groupby("iso_week", sort=True)["rank_ic"].agg(["mean", "size", lambda x: float((x > 0).mean())]).reset_index()
    weekly.columns = ["iso_week", "mean", "n_days", "pos_share"]
    x = np.arange(len(weekly))
    colors = np.where(weekly["mean"].to_numpy() >= 0, "#2f6964", "#aa352c")
    ax.bar(x, weekly["mean"], color=colors, alpha=0.78, width=0.76, label="weekly mean RankIC")
    ax.axhline(0, color="#756f68", lw=0.7)
    ax.grid(axis="y", alpha=0.65)
    ax.set_ylabel("mean RankIC")
    step = max(1, math.ceil(len(weekly) / 14))
    ticks = x[::step]
    ax.set_xticks(ticks, weekly["iso_week"].iloc[::step], rotation=40, ha="right")
    ax2 = ax.twinx()
    ax2.plot(x, weekly["pos_share"], color="#9b6925", lw=1.1, marker="o", ms=2.1, label="positive-day share")
    ax2.set_ylim(0, 1)
    ax2.set_ylabel("positive-day share")
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc="upper left", ncol=2, frameon=False, fontsize=7.5)
    ax.set_title("ISO-week RankIC stability", loc="left", fontweight="bold")
    fig.tight_layout()
    return fig


def group_figure(frame: pd.DataFrame) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10.8, 4.0))
    clean = frame.sort_values("group_id")
    valid = clean["count"].fillna(0).astype(float) > 0
    if clean.empty or not valid.any():
        empty_axes(ax, "No valid factor observations for 40 groups")
        return fig
    x = clean.loc[valid, "group_id"].to_numpy(dtype=float) + 1
    returns = clean.loc[valid, "return_bps"].to_numpy(dtype=float)
    colors = np.where(np.nan_to_num(returns) >= 0, "#2f6964", "#aa352c")
    ax.bar(x, returns, color=colors, alpha=0.78, width=0.78, label="mean forward return")
    ax.axhline(0, color="#756f68", lw=0.7)
    ax.grid(axis="y", alpha=0.65)
    ax.set_xlabel("daily average-rank group (low → high)")
    ax.set_ylabel("return (bps)")
    ax2 = ax.twinx()
    ax2.plot(x, clean.loc[valid, "factor_mean"], color="#17242d", lw=1.2, ls="--", label="factor mean")
    ax2.set_ylabel("factor mean")
    lines, labels = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines + lines2, labels + labels2, loc="upper left", ncol=2, frameon=False, fontsize=7.5)
    ax.set_title("40 cross-sectional rank groups: return and factor level", loc="left", fontweight="bold")
    fig.tight_layout()
    return fig


def bin_figure(frame: pd.DataFrame) -> plt.Figure:
    fig, axes = plt.subplots(2, 1, figsize=(10.2, 6.4), sharex=True, gridspec_kw={"height_ratios": [1.0, 1.45]})
    clean = frame.sort_values("bin_id")
    if clean.empty or clean["count"].fillna(0).sum() <= 0:
        empty_axes(axes[0], "No factor distribution")
        empty_axes(axes[1], "No return-by-value evidence")
        return fig
    centers = (clean["left_edge"].to_numpy(dtype=float) + clean["right_edge"].to_numpy(dtype=float)) / 2
    width = clean["right_edge"].to_numpy(dtype=float) - clean["left_edge"].to_numpy(dtype=float)
    axes[0].bar(centers, clean["count"], width=width, color="#315b7d", alpha=0.34, edgecolor="#315b7d", linewidth=0.35)
    axes[0].set_ylabel("stock-days")
    axes[0].grid(axis="y", alpha=0.55)
    axes[0].set_title("100 equal-width bins: factor distribution and mean forward return", loc="left", fontweight="bold")
    shown = (clean["count"].fillna(0) >= 5) & clean["return_bps"].notna()
    shown_values = clean.loc[shown, "return_bps"].to_numpy(dtype=float)
    shown_centers = centers[shown.to_numpy()]
    shown_width = width[shown.to_numpy()]
    colors = np.where(np.nan_to_num(shown_values) >= 0, "#2f6964", "#aa352c")
    axes[1].bar(shown_centers, shown_values, width=shown_width, color=colors, alpha=0.78)
    axes[1].axhline(0, color="#756f68", lw=0.7)
    axes[1].grid(axis="y", alpha=0.55)
    axes[1].set_ylabel("return (bps)")
    axes[1].set_xlabel("factor value")
    occupied = clean["count"].to_numpy(dtype=float) > 0
    if occupied.any():
        lo = clean.loc[occupied, "left_edge"].min()
        hi = clean.loc[occupied, "right_edge"].max()
        padding = max((hi - lo) * 0.025, 1e-12)
        axes[1].set_xlim(lo - padding, hi + padding)
    fig.tight_layout()
    return fig


def chart_bundle(daily: pd.DataFrame, groups: pd.DataFrame, bins: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        image_payload(
            daily_figure(daily),
            "逐日 IC / RankIC 与累计稳定性",
            "检查日度横截面相关的符号、20 日滚动均值、异常日和累计是否被少数时期支配。",
        ),
        image_payload(
            weekly_figure(daily),
            "逐周 RankIC 稳定性",
            "按 ISO 周压缩日噪声，同时观察周均 RankIC 与正 RankIC 日期占比。",
        ),
        image_payload(
            group_figure(groups),
            "40 组分组收益",
            "每天按平均百分位秩分为 40 组，观察因子均值与后续收益是否单调、是否仅由头尾驱动。",
        ),
        image_payload(
            bin_figure(bins),
            "100 等宽分箱",
            "上图展示股票日因子值分布，下图展示每个数值区间的平均后续收益；低于 5 个样本的箱不画收益柱。",
        ),
    ]


def top_ids(records: list[dict[str, Any]], field: str, *, absolute: bool = False, limit: int = 20) -> list[str]:
    valid = [record for record in records if not record["diagnostic"] and finite(record["periods"]["full_history"].get(field))]
    valid.sort(
        key=lambda record: abs(float(record["periods"]["full_history"][field])) if absolute else float(record["periods"]["full_history"][field]),
        reverse=True,
    )
    return [record["record_id"] for record in valid[:limit]]


def summary_stats(records: list[dict[str, Any]], key: str) -> dict[str, Any]:
    values = [float(record["periods"]["full_history"][key]) for record in records if not record["diagnostic"] and finite(record["periods"]["full_history"].get(key))]
    if not values:
        return {"n": 0, "mean": None, "median": None, "positive": 0, "negative": 0}
    return {
        "n": len(values),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "positive": int(np.count_nonzero(np.asarray(values) > 0)),
        "negative": int(np.count_nonzero(np.asarray(values) < 0)),
    }


def grouped_performance(records: list[dict[str, Any]], field: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    layer_rows: list[dict[str, Any]] = []
    projection_rows: list[dict[str, Any]] = []
    for key, output, labels in (
        ("layer", layer_rows, LAYER_LABELS),
        ("projection", projection_rows, PROJECTION_LABELS),
    ):
        groups: dict[str, list[float]] = defaultdict(list)
        for record in records:
            value = record["periods"]["full_history"].get(field)
            if record["diagnostic"] or not finite(value):
                continue
            groups[str(record[key])].append(float(value))
        for group, values in groups.items():
            output.append(
                {
                    "id": group,
                    "label": labels.get(group, group or "目的专属"),
                    "n": len(values),
                    "mean": float(np.mean(values)),
                    "median": float(np.median(values)),
                    "positive_share": float(np.mean(np.asarray(values) > 0)),
                    "mean_abs": float(np.mean(np.abs(values))),
                }
            )
        output.sort(key=lambda row: row["mean"], reverse=True)
    return layer_rows, projection_rows


def build_payload(evidence: Path, research_repo: Path) -> dict[str, Any]:
    manifest = read_json(evidence / "REPORT_EVIDENCE_MANIFEST.json")
    evaluation = read_json(evidence / "EVALUATION_RESULT.json")
    formal = read_json(evidence / "FORMAL_STUDY_RESULT.json")
    if manifest.get("status") != "complete":
        raise RuntimeError("report evidence is incomplete")
    if manifest.get("factor_count") != EXPECTED_FACTORS:
        raise RuntimeError("report evidence factor count differs from 495")
    for declaration in manifest["outputs"].values():
        path = evidence / declaration["path"]
        if not path.is_file() or sha256_file(path) != declaration["sha256"]:
            raise RuntimeError(f"evidence hash mismatch: {path}")

    period = pd.read_parquet(evidence / "period_summary.parquet")
    daily = pd.read_parquet(evidence / "daily_ic.parquet")
    groups = pd.read_parquet(evidence / "group_40.parquet")
    bins = pd.read_parquet(evidence / "bins_100.parquet")
    distribution = pd.read_csv(evidence / "factor_distribution.csv")
    registry, index_rows, plan_rows, plan_text = load_registry_metadata(research_repo)
    logical_to_component, components = component_maps(registry)

    factor_ids = [str(item["factor_id"]) for item in index_rows]
    if len(factor_ids) != EXPECTED_FACTORS or set(factor_ids) != set(period["record_id"].astype(str)):
        raise RuntimeError("registry and evaluation factor inventories disagree")
    if manifest.get("registry_hash") != read_json(
        research_repo / "因子" / "algobench" / "research" / "新factors_open5m_count_proxy_v2" / "NOTEBOOK_INDEX.json"
    ).get("registry_hash"):
        raise RuntimeError("evidence registry hash differs from local factor index")

    period_lookup = {
        (str(row["record_id"]), str(row["period"])): clean_mapping(row)
        for row in period.to_dict("records")
    }
    distribution_lookup = {
        str(row["record_id"]): clean_mapping(row)
        for row in distribution.to_dict("records")
    }
    daily_groups = {str(key): frame.copy() for key, frame in daily.groupby("record_id", sort=False)}
    group_groups = {str(key): frame.copy() for key, frame in groups.groupby("record_id", sort=False)}
    bin_groups = {str(key): frame.copy() for key, frame in bins.groupby("record_id", sort=False)}

    set_plot_style()
    records: list[dict[str, Any]] = []
    for position, item in enumerate(index_rows, start=1):
        metadata = build_factor_metadata(item, logical_to_component, components, plan_rows)
        factor_id = metadata["record_id"]
        period_rows = {
            period_id: period_lookup.get((factor_id, period_id), {})
            for period_id in PERIODS
        }
        metadata["periods"] = period_rows
        metadata["distribution"] = distribution_lookup.get(factor_id, {})
        metadata["images"] = chart_bundle(
            daily_groups.get(factor_id, pd.DataFrame()),
            group_groups.get(factor_id, pd.DataFrame()),
            bin_groups.get(factor_id, pd.DataFrame()),
        )
        records.append(metadata)
        if position == 1 or position % 10 == 0 or position == len(index_rows):
            print(json.dumps({"phase": "charts", "complete": position, "total": len(index_rows)}), flush=True)

    image_count = sum(len(record["images"]) for record in records)
    if image_count != EXPECTED_IMAGES:
        raise RuntimeError(f"expected 1980 images, found {image_count}")
    formal_count = sum(not record["diagnostic"] for record in records)
    diagnostic_count = sum(record["diagnostic"] for record in records)
    if (formal_count, diagnostic_count) != (EXPECTED_FORMAL, EXPECTED_DIAGNOSTICS):
        raise RuntimeError("formal/diagnostic record counts differ from contract")

    metric_stats = {key: summary_stats(records, field) for key, field in METRICS.items()}
    rankings = {
        key: {
            "top": top_ids(records, field),
            "absolute": top_ids(records, field, absolute=True),
        }
        for key, field in METRICS.items()
    }
    layer_rankic, projection_rankic = grouped_performance(records, "Rank_IC")

    logical_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        # L1 preserves the requested “原因子序号 + 备注” naming: every frozen
        # scorer alias is its own displayed family.  L2–L5 collapse only the
        # five directional projections of the same newly numbered factor.
        logical_key = record["display_name"] if record["layer"] in {"L1", "L1_diagnostic"} else record["logical_factor_id"]
        logical_groups[logical_key].append(record)
    logical_catalog: list[dict[str, Any]] = []
    for logical, members in logical_groups.items():
        valid = [member for member in members if not member["diagnostic"] and finite(member["periods"]["full_history"].get("Rank_IC"))]
        best = max(valid, key=lambda member: float(member["periods"]["full_history"]["Rank_IC"])) if valid else members[0]
        logical_catalog.append(
            {
                "logical_factor_id": logical,
                "display_name": members[0]["display_name"],
                "layer": members[0]["layer"],
                "layer_label": members[0]["layer_label"],
                "description": members[0]["description"],
                "output_count": len(members),
                "best_record_id": best["record_id"],
                "best_rank_ic": best["periods"]["full_history"].get("Rank_IC"),
            }
        )
    logical_catalog.sort(key=lambda row: (list(LAYER_LABELS).index(row["layer"]), row["logical_factor_id"]))

    whitepaper_rows = []
    section = plan_text.split("## 9. 白皮书方法与本计划因子的对应关系", 1)[-1].split("## 10.", 1)[0]
    for line in section.splitlines():
        cells = [cell.strip() for cell in line.strip()[1:-1].split("|")] if line.strip().startswith("|") and line.strip().endswith("|") else []
        if len(cells) == 2 and cells[0] not in {"白皮书方向", "---"} and not set(cells[0]) <= {"-", ":"}:
            whitepaper_rows.append({"direction": cells[0], "implementation": cells[1]})

    return {
        "schema_version": "open5m-count-proxy-html-report-v1",
        "report_date": "2026-08-07",
        "source": {
            "run_root": manifest["source_run_root"],
            "revision": formal.get("revision"),
            "registry_hash": manifest.get("registry_hash"),
            "evidence_manifest_sha256": sha256_file(evidence / "REPORT_EVIDENCE_MANIFEST.json"),
            "start": evaluation.get("start"),
            "end": evaluation.get("end"),
            "day_count": evaluation.get("day_count"),
            "panel_rows": manifest.get("panel_rows"),
            "daily_rows": evaluation.get("daily_row_count"),
            "label": evaluation.get("label"),
            "ic_definition": evaluation.get("ic_definition"),
            "rank_ic_definition": evaluation.get("rank_ic_definition"),
            "icir_definition": evaluation.get("icir_definition"),
            "group_method": manifest.get("group_method"),
            "bin_method": manifest.get("bin_method"),
        },
        "counts": {
            "formal": formal_count,
            "diagnostic": diagnostic_count,
            "total": len(records),
            "new_logical": 80,
            "old_projection_columns": 250,
            "new_output_columns": 240,
            "images": image_count,
            "logical_catalog": len(logical_catalog),
        },
        "metric_stats": metric_stats,
        "rankings": rankings,
        "layer_rankic": layer_rankic,
        "projection_rankic": projection_rankic,
        "logical_catalog": logical_catalog,
        "whitepaper_rows": whitepaper_rows,
        "records": records,
    }


HTML_TEMPLATE = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light">
<title>开盘五分钟算法痕迹新因子：490 个正式候选全景报告</title>
<style id="katex-self-contained">__KATEX_CSS__</style>
<style>
:root{
  --paper:#f2ecdf;--paper2:#fbf8f1;--ink:#17242d;--muted:#667076;--line:#d5ccbc;
  --red:#a9362e;--teal:#2f6964;--gold:#93601f;--blue:#315b7d;--violet:#653e65;
  --good:#16664e;--bad:#a3352d;--shadow:0 24px 70px rgba(36,43,43,.12);
  --serif:"Iowan Old Style","Noto Serif CJK SC","Source Han Serif SC","Songti SC","STSong",serif;
  --sans:"Avenir Next","Noto Sans CJK SC","Source Han Sans SC","Microsoft YaHei UI",sans-serif;
  --mono:"JetBrains Mono","Cascadia Code","SFMono-Regular","Consolas",monospace;
}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;color:var(--ink);font-family:var(--sans);line-height:1.68;background-color:var(--paper);background-image:linear-gradient(rgba(23,36,45,.026) 1px,transparent 1px),linear-gradient(90deg,rgba(23,36,45,.026) 1px,transparent 1px);background-size:26px 26px}
a{color:inherit}.shell{width:min(1560px,calc(100% - 42px));margin:auto}code{font-family:var(--mono);overflow-wrap:anywhere}.mono{font-family:var(--mono)}
h1,h2,h3,h4{font-family:var(--serif);font-weight:600;letter-spacing:-.028em;margin:0}.micro{font-size:12px;color:var(--muted)}
.mast{min-height:88vh;display:grid;grid-template-columns:minmax(0,1.45fr) minmax(330px,.55fr);gap:76px;align-items:center;padding:92px 0 74px;border-bottom:1px solid var(--line);position:relative}
.mast:after{content:"";position:absolute;width:240px;height:240px;border:38px solid rgba(169,54,46,.07);right:23%;top:7%;transform:rotate(12deg);pointer-events:none}
.eyebrow,.kicker{font:800 11px/1.3 var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--red)}h1{font-size:clamp(54px,7.1vw,114px);line-height:.92;max-width:1050px}.dek{font:400 clamp(18px,2vw,27px)/1.55 var(--serif);max-width:880px;color:#3f4c52;margin:30px 0}.stamp{border-left:5px solid var(--red);padding:12px 0 12px 20px;font:650 12px/1.8 var(--mono);color:#4d565a}
.cover{background:rgba(251,248,241,.93);border:1px solid var(--line);box-shadow:var(--shadow);padding:32px;position:relative;z-index:1}.cover:before{content:"FORMAL RESEARCH NOTE · 2026·08·07";position:absolute;right:-1px;top:-31px;background:var(--ink);color:#fff;padding:7px 12px;font:800 9px var(--mono);letter-spacing:.12em}.cover-big{font:650 90px/.88 var(--serif);color:var(--red)}.cover-label{font:800 11px var(--mono);letter-spacing:.12em;color:var(--muted);margin:12px 0 26px}.cover dl{margin:0;display:grid;gap:10px}.cover dl div{display:flex;justify-content:space-between;gap:20px;border-bottom:1px dotted #c9bead;padding-bottom:8px}.cover dt{font-size:12px;color:var(--muted)}.cover dd{margin:0;font:750 12px var(--mono);text-align:right}
.nav-wrap{position:sticky;top:0;z-index:50;background:rgba(242,236,223,.94);backdrop-filter:blur(16px);border-bottom:1px solid var(--line)}.nav{display:flex;gap:3px;overflow:auto;padding:8px 0;scrollbar-width:none}.nav::-webkit-scrollbar{display:none}.nav a{padding:10px 14px;text-decoration:none;white-space:nowrap;font:800 10px var(--mono);letter-spacing:.07em}.nav a:hover,.nav a.active{background:#050505;color:#fff}
main{padding-bottom:90px}.chapter{padding:96px 0;border-bottom:1px solid var(--line);scroll-margin-top:58px}.chapter-head{display:grid;grid-template-columns:145px minmax(0,1fr);gap:30px;margin-bottom:44px}.chapter-no{font:500 64px/1 var(--serif);color:var(--red);border-top:5px solid var(--red);padding-top:12px}.chapter h2{font-size:clamp(38px,5vw,72px);line-height:1.02}.chapter-lead{font:400 20px/1.7 var(--serif);max-width:970px;color:#46545a;margin:15px 0 0}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.stat,.paper,.layer-card{background:rgba(251,248,241,.93);border:1px solid var(--line);padding:24px}.stat small{display:block;font:750 10px var(--mono);letter-spacing:.07em;color:var(--muted)}.stat strong{display:block;font:650 clamp(34px,4vw,56px)/1 var(--serif);margin:9px 0}.stat.accent{background:var(--ink);color:#fff}.stat.accent small{color:#d7dedf}.callout{display:grid;grid-template-columns:10px 1fr;gap:20px;background:#efe0d1;border:1px solid #d9bca4;padding:24px;margin:24px 0}.callout:before{content:"";background:var(--red)}.callout strong{font-family:var(--serif);font-size:22px}.callout p{margin:6px 0 0;color:#4d4c48}
.chain{display:grid;grid-template-columns:repeat(6,1fr);gap:11px;counter-reset:step}.chain article{position:relative;background:var(--paper2);border:1px solid var(--line);padding:22px 17px;min-height:190px}.chain article:before{counter-increment:step;content:counter(step,decimal-leading-zero);display:block;font:800 10px var(--mono);color:var(--red);margin-bottom:25px}.chain article:not(:last-child):after{content:"→";position:absolute;right:-12px;top:50%;z-index:2;color:var(--red);font-weight:900}.chain b{font-family:var(--serif);font-size:18px}.chain p{font-size:12px;color:var(--muted);margin:7px 0 0}
.grid-2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}.grid-3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:15px}.brick{min-width:0;background:rgba(251,248,241,.94);border:1px solid var(--line);padding:24px}.brick.wide{grid-column:1/-1}.brick h3{font-size:25px;margin-bottom:8px}.brick h4{font:800 10px var(--mono);letter-spacing:.08em;color:var(--red);margin:18px 0 6px}.brick p{margin:0;color:#46535a}.formula{background:var(--ink);color:#f9f4e9;padding:15px 17px;margin:15px 0;overflow:auto}.formula .katex-display{text-align:left;margin:.2em 0}.formula .katex-display>.katex{display:block;text-align:left;white-space:nowrap}.katex-display{overflow-x:auto;overflow-y:hidden}
.layer-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px}.layer-card{border-top:5px solid var(--layer);position:relative}.layer-card .index{font:650 42px/1 var(--serif);color:var(--layer)}.layer-card h3{font-size:24px;margin:12px 0 5px}.layer-card p{font-size:13px;color:#4b575d;margin:0}.layer-card .count{position:absolute;right:18px;top:18px;font:800 10px var(--mono);color:var(--muted)}
.table-scroll{overflow:auto;background:#fff;border:1px solid var(--line)}table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}th,td{padding:11px 12px;border-bottom:1px solid #e5ded3;text-align:right;font-size:12px;white-space:nowrap}th{background:#eae2d5;font:800 9px var(--mono);letter-spacing:.06em;color:#596269;position:sticky;top:0;z-index:2}th:first-child,td:first-child{text-align:left}.data{min-width:980px}.factor-link{color:inherit;text-decoration:none;border-bottom:1px dotted currentColor;font-family:var(--mono);font-weight:700}.factor-link:hover{color:var(--red);border-bottom-style:solid}.metric.pos{color:var(--good);font-weight:750}.metric.neg{color:var(--bad);font-weight:750}.metric.na{color:#96938c}.rank{font:800 12px var(--mono);color:var(--red)}
.rank-tabs,.filters{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:16px 0}.rank-tabs button,.filters button,.filters select,.filters input{border:1px solid var(--line);background:var(--paper2);color:var(--ink);padding:11px 13px;font:750 11px var(--mono)}.rank-tabs button,.filters button{cursor:pointer}.rank-tabs button:hover,.rank-tabs button.active,.filters button:hover{background:var(--ink);color:#fff;border-color:var(--ink)}.filters input{min-width:min(460px,100%);flex:1;font-family:var(--sans)}
.performance-grid{display:grid;grid-template-columns:1fr 1fr;gap:15px;margin-top:28px}.bar-list{display:grid;gap:10px}.bar-row{display:grid;grid-template-columns:180px 1fr 92px;gap:12px;align-items:center;font-size:12px}.bar-track{height:10px;background:#e7e0d4;position:relative}.bar-track i{display:block;height:100%;background:var(--teal);position:absolute;left:50%}.bar-track i.neg{right:50%;left:auto;background:var(--red)}.bar-row b{font-family:var(--mono);font-size:11px;text-align:right}
.catalog-layer{margin:18px 0}.catalog-layer>summary{cursor:pointer;list-style:none;background:var(--paper2);border:1px solid var(--line);border-left:7px solid var(--layer);padding:17px 19px;font:650 22px var(--serif);display:flex;justify-content:space-between}.catalog-layer>summary::-webkit-details-marker{display:none}.catalog-layer>summary span{font:750 10px var(--mono);color:var(--muted)}.catalog-table td:nth-child(2){white-space:normal;text-align:left;min-width:420px}.catalog-table td:last-child{font-family:var(--mono)}
.explorer{display:grid;grid-template-columns:minmax(480px,.85fr) minmax(0,1.15fr);gap:20px;align-items:start}.inventory{max-height:78vh;overflow:auto;border:1px solid var(--line);background:#fff}.inventory table{min-width:790px}.inventory tbody tr{cursor:pointer}.inventory tbody tr:hover,.inventory tbody tr.selected{background:#eee6da}.inventory td:nth-child(2){max-width:390px;overflow:hidden;text-overflow:ellipsis}.detail{position:sticky;top:74px;max-height:calc(100vh - 92px);overflow:auto;background:rgba(251,248,241,.98);border:1px solid var(--line);box-shadow:var(--shadow);padding:25px}.detail-empty{min-height:360px;display:grid;place-items:center;color:var(--muted);font-family:var(--serif);font-size:22px;text-align:center}.detail-title{font-size:clamp(31px,3.2vw,52px);line-height:1.05;overflow-wrap:anywhere}.chips{display:flex;flex-wrap:wrap;gap:7px;margin:13px 0}.chip{padding:5px 8px;background:#e9e1d5;border:1px solid var(--line);font:750 9px var(--mono);letter-spacing:.04em}.chip.layer{background:var(--layer);color:#fff;border-color:var(--layer)}.metric-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:18px 0}.mini-stat{background:#fff;border:1px solid var(--line);padding:12px}.mini-stat small{display:block;font:750 8px var(--mono);color:var(--muted);letter-spacing:.07em}.mini-stat strong{display:block;font:650 23px var(--serif);margin-top:4px}.section-label{font:800 10px var(--mono);letter-spacing:.12em;color:var(--red);margin:24px 0 8px}.detail-copy{color:#46535a}.steps{counter-reset:mini;display:grid;gap:7px;padding:0;margin:10px 0}.steps li{list-style:none;display:grid;grid-template-columns:30px 1fr;gap:8px}.steps li:before{counter-increment:mini;content:counter(mini,decimal-leading-zero);font:800 9px var(--mono);color:var(--red);padding-top:4px}.figure-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.figure-card{margin:0;background:#fff;border:1px solid var(--line);padding:9px}.figure-card img{display:block;width:100%;height:auto;background:#fff;cursor:zoom-in;user-select:none;-webkit-user-drag:none;-webkit-touch-callout:none;touch-action:manipulation}.figure-card img:focus-visible{outline:4px solid var(--red);outline-offset:3px}.figure-card figcaption{font:800 9px var(--mono);padding:8px 3px 2px;color:#4c585d}.figure-card p{font-size:11px;color:var(--muted);margin:5px 3px}.detail-nav{display:flex;justify-content:space-between;gap:10px;margin-top:20px}.detail-nav button{border:1px solid var(--line);background:#fff;padding:9px 12px;font:750 10px var(--mono);cursor:pointer}.detail-nav button:hover{background:var(--ink);color:#fff}
.lightbox-open{overflow:hidden}.lightbox{position:fixed;inset:0;z-index:300;display:grid;grid-template-rows:auto minmax(0,1fr) auto;background:rgba(7,15,21,.96);color:#f8f3e8;visibility:hidden;opacity:0;pointer-events:none;transition:opacity .18s ease,visibility .18s ease;backdrop-filter:blur(14px)}.lightbox.is-open{visibility:visible;opacity:1;pointer-events:auto}.lightbox-bar,.lightbox-foot{display:flex;align-items:center;justify-content:space-between;gap:18px;padding:16px 22px;border-color:rgba(255,255,255,.16);border-style:solid}.lightbox-bar{border-width:0 0 1px}.lightbox-foot{border-width:1px 0 0;font:700 10px/1.5 var(--mono);letter-spacing:.05em;color:#c9d0d3}.lightbox-heading{min-width:0}.lightbox-heading small{display:block;font:800 9px var(--mono);letter-spacing:.16em;color:#e85a4f}.lightbox-heading strong{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font:600 clamp(16px,2.2vw,28px)/1.2 var(--serif)}.lightbox-close,.lightbox-control{border:1px solid rgba(255,255,255,.28);background:#111e27;color:#fff;cursor:pointer}.lightbox-close{flex:0 0 44px;width:44px;height:44px;font:300 28px/1 var(--sans)}.lightbox-close:hover,.lightbox-control:hover,.lightbox-close:focus-visible,.lightbox-control:focus-visible{background:var(--red);border-color:var(--red);outline:none}.lightbox-stage{min-height:0;display:grid;grid-template-columns:58px minmax(0,1fr) 58px;align-items:center;gap:14px;padding:16px 22px}.lightbox-canvas{min-width:0;min-height:0;height:100%;display:grid;place-items:center}.lightbox-image{display:block;max-width:100%;max-height:calc(100vh - 170px);width:auto;height:auto;background:#fff;box-shadow:0 28px 80px rgba(0,0,0,.55)}.lightbox-control{width:52px;height:72px;font:500 30px/1 var(--serif)}.lightbox-description{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.lightbox-count{white-space:nowrap;color:#fff}
.audit{display:grid;grid-template-columns:220px minmax(0,1fr);gap:13px 24px;border-top:1px solid var(--line);padding-top:18px}.audit dt{font:800 9px var(--mono);letter-spacing:.07em;color:var(--muted)}.audit dd{margin:0;font:650 11px/1.7 var(--mono);overflow-wrap:anywhere}.foot{padding:48px 0 70px;color:var(--muted);font:650 10px/1.7 var(--mono)}
@media(max-width:1100px){.mast{grid-template-columns:1fr;min-height:auto}.stats,.layer-grid{grid-template-columns:repeat(2,1fr)}.chain{grid-template-columns:repeat(3,1fr)}.chain article:after{display:none}.explorer{grid-template-columns:1fr}.detail{position:relative;top:auto;max-height:none}.performance-grid{grid-template-columns:1fr}}
@media(max-width:720px){.shell{width:min(100% - 24px,1560px)}.chapter{padding:66px 0}.chapter-head{grid-template-columns:1fr}.chapter-no{font-size:38px}.stats,.grid-2,.grid-3,.layer-grid,.metric-grid,.figure-grid{grid-template-columns:1fr}.chain{grid-template-columns:1fr}.explorer{display:block}.inventory{max-height:60vh}.detail{margin-top:16px}.bar-row{grid-template-columns:120px 1fr 70px}.mast:after{display:none}.lightbox-bar,.lightbox-foot{padding:12px}.lightbox-stage{grid-template-columns:40px minmax(0,1fr) 40px;gap:6px;padding:10px 6px}.lightbox-control{width:38px;height:58px;font-size:24px}.lightbox-image{max-height:calc(100vh - 150px)}.lightbox-description{display:none}}
</style>
</head>
<body>
<header class="shell mast" id="top">
  <div><div class="eyebrow">Formal factor study · intraday open 5 minutes</div><h1>算法痕迹<br>新因子全景</h1><p class="dek">从 50 个老 scorer 的方向投影，到多证据共识、微观结构情境、窗口量价状态与算法目的：把 2025-01-02 至 2026-06-30 的 495 列正式结果、双区间评价和每列四张诊断图收进一个可离线检索的研究档案。</p><div class="stamp">09:30–09:35 因子证据窗<br>09:35 锚价 → 09:44–09:45 VWAP<br>count / all valid deduplicated new orders</div></div>
  <aside class="cover"><div class="cover-big">490</div><div class="cover-label">FORMAL CANDIDATES</div><dl><div><dt>真正新增逻辑</dt><dd>f54–f133 / 80</dd></div><div><dt>老 scorer 投影</dt><dd>250 columns</dd></div><div><dt>诊断列</dt><dd>5</dd></div><div><dt>评价图片</dt><dd>1,980</dd></div><div><dt>交易日</dt><dd>354</dd></div></dl></aside>
</header>
<div class="nav-wrap"><nav class="shell nav" aria-label="章节"><a href="#scope">口径与结论</a><a href="#chain">完整链路</a><a href="#new">新增内容</a><a href="#ranking">表现总结</a><a href="#catalog">逻辑目录</a><a href="#factors">逐因子四图</a><a href="#audit">审计与限制</a></nav></div>
<main>
<section class="shell chapter" id="scope"><div class="chapter-head"><div class="chapter-no">01</div><div><div class="kicker">Scope and answer</div><h2>先分清 490、495 与 80</h2><p class="chapter-lead">文件夹名写“490 factors”是因为正式候选只有 490；面板实际有 495 列，另外 5 列是市场行为诊断。真正占用新序号的逻辑只有 f54–f133 共 80 个，展开后产生 240 列；其余 250 列保留老 scorer 编号，只改变窗口、公共分母与买卖方向投影。</p></div></div><div class="stats" id="headline-stats"></div><div class="callout"><div><strong>受白皮书启发的新因子已经包含，而且不是裸市场指标。</strong><p>L3–L5 把价差、深度、OFI、主动成交、趋势、波动跳跃、非流动性、韧性与羊群等方向，全部条件化在可观察算法证据上；纯价差、纯 OFI、纯波动不会被单独包装成“算法占比”。</p></div></div><div class="grid-2"><article class="brick"><h3>评价数值怎么读</h3><div class="formula">$$IC_d=Corr_{Pearson}(F_{i,d},r_{i,d}),\quad RankIC_d=Corr_{Spearman}(F_{i,d},r_{i,d})$$<br>$$ICIR_{raw}=\overline{RankIC}/Std_{ddof=1}(RankIC_d)$$</div><p>先逐日做横截面相关，再跨日求均值；ICIR 未年化。报告同时保留完整历史和 2026Q2，避免只看一个窗口。</p></article><article class="brick"><h3>这不是正式准入结论</h3><p>490 个候选存在显著的多重检验、同源投影与近重复问题。本页按冻结数据忠实排序并解释，但没有做行业/市值/流动性中性化、交易成本、换手、容量、相关性聚类或真正滚动样本外组合测试。</p><h4>诊断列</h4><p><code>f22_mktfill</code>、<code>f23_instfill</code>、<code>f24_depth</code>、<code>f25_sweep</code>、<code>ctrl04_oneshot</code>只用于状态解释，不进入正式排名。</p></article></div></section>
<section class="shell chapter" id="chain"><div class="chapter-head"><div class="chapter-no">02</div><div><div class="kicker">From events to evidence</div><h2>完整构建与评价链路</h2><p class="chapter-lead">昂贵的逐笔回放、生命周期、pair、chain 和 response 只在正式计算中做过一次；本报告只消费已经完成的股票日面板和标签。图表补建属于面板归约，不会重新枚举任何 pair。</p></div></div><div class="chain"><article><b>逐笔事件回放</b><p>冻结动作前 BBO、Top-N 深度、队列前量、成交方向与微价格。</p></article><article><b>四族算法证据</b><p>生命周期 L、pair P、订单链 C、响应 R；族内取最大值。</p></article><article><b>联合证据 A</b><p>$A_i=\max(L_i,P_i,C_i,R_i)$，表示痕迹并集强度。</p></article><article><b>状态与目的交互</b><p>订单级 $x$、窗口级 $Z$ 和专属目的公式共同形成新逻辑。</p></article><article><b>五方向/专属归约</b><p>所有占比共享全部有效去重新订单分母 $N$。</p></article><article><b>双区间评价</b><p>完整历史与 2026Q2 的 IC、RankIC、ICIR、分组和分箱。</p></article></div><div class="grid-2" style="margin-top:18px"><article class="brick"><h3>公共分母与五投影</h3><div class="formula">$$Total=(U^B+U^S)/N,\ Buy=U^B/N,\ Sell=U^S/N$$<br>$$Net=(U^B-U^S)/N,\ AbsNet=|U^B-U^S|/N$$</div><p>买、卖列不是各自侧内占比；它们仍除以全部订单。必须满足 <code>total = buy + sell</code> 与 <code>absnet = abs(buy - sell)</code>。</p></article><article class="brick"><h3>时间和标签边界</h3><div class="formula">$$W=[09{:}30,09{:}35),\quad P_0=P_{last\ valid\ trade,t&lt;09{:}35}$$<br>$$P_1=VWAP_{09{:}44\le t&lt;09{:}45},\quad r=P_1/P_0-1$$</div><p>订单情境使用动作前最新状态；窗口状态只用 09:35 前事件；响应 trigger 严格早于 action。标签不得反向参与因子构建。</p></article><article class="brick"><h3>10% 数量硬门</h3><p>pair 候选使用固定 10% 对称数量门、3 秒候选窗和无普通价格硬门。价格差只进入连续分数，不再作为提前截断候选的硬门。</p><div class="formula">$$\max(q_{new},q_{ref})\le1.10\min(q_{new},q_{ref})$$</div></article><article class="brick"><h3>四张图的职责</h3><p>逐日图检查异常日和累计稳定；逐周图检查周际反转；40 组图检查横截面单调性；100 分箱图检查 0 堆积、极端值、阈值和非线性。四图均由正式面板重新归约，不是 Notebook 截图。</p></article></div></section>
<section class="shell chapter" id="new"><div class="chapter-head"><div class="chapter-no">03</div><div><div class="kicker">What is actually new</div><h2>五层因子体系与白皮书迁移</h2><p class="chapter-lead">L1 保留旧编号；L2–L5 才是本轮真正新增的 f54–f133。新内容不仅是“多算几个 scorer”，还加入统一算法证据、订单级微观结构条件、股票日量价状态、算法目的和冲击后韧性。</p></div></div><div class="layer-grid" id="layer-cards"></div><div class="grid-2" style="margin-top:22px"><article class="brick"><h3>白皮书方向如何落地</h3><div class="table-scroll"><table class="data"><thead><tr><th>白皮书方向</th><th>当前实现</th></tr></thead><tbody id="whitepaper-body"></tbody></table></div></article><article class="brick"><h3>两类“白皮书来源”</h3><h4>KX 监察白皮书与六篇算法痕迹文献</h4><p>主要进入 L1 scorer 底座，形成生命周期、撤挂、订单链和响应证据；本轮只对其改公共分母并增加买卖投影。</p><h4>高频量价与微观结构方法</h4><p>主要进入 L3–L5：OFI/成交流、盘口形态、收益分布、价量共振、波动跳跃、撤单冲击、流动性恢复和羊群/逆向吸收。</p><h4>关键改造</h4><p>不做全日分钟桶，不使用 amount，不依赖跨日正常基准；市场状态必须与算法证据交互，避免把通用高频 Alpha 冒充算法身份。</p></article></div></section>
<section class="shell chapter" id="ranking"><div class="chapter-head"><div class="chapter-no">04</div><div><div class="kicker">Cross-sectional results</div><h2>完整历史表现总结</h2><p class="chapter-lead">以下排序只覆盖 490 个正式候选，使用原始有符号 IC、RankIC、ICIR。每个上榜因子都可以点击并跳到其完整定义、完整历史/Q2 指标和四张评价图。</p></div></div><div class="stats" id="metric-stats"></div><div class="rank-tabs"><button class="active" data-metric="rank_ic">Rank_IC Top20</button><button data-metric="ic">IC Top20</button><button data-metric="icir">ICIR Top20</button><button data-metric="abs_rank_ic">|Rank_IC| Top20</button></div><div class="table-scroll"><table class="data"><thead><tr><th>#</th><th>正式因子列</th><th>层级</th><th>投影</th><th>IC</th><th>Rank_IC</th><th>ICIR</th><th>NW t</th><th>正日占比</th><th>Q2 Rank_IC</th><th>覆盖率</th></tr></thead><tbody id="ranking-body"></tbody></table></div><div class="performance-grid"><article class="brick"><h3>各层平均 Rank_IC</h3><div class="bar-list" id="layer-performance"></div></article><article class="brick"><h3>各投影平均 Rank_IC</h3><div class="bar-list" id="projection-performance"></div></article></div><div class="callout"><div><strong>排名是候选发现，不是可交易性证明。</strong><p>同一逻辑的 total/buy/sell/net/absnet 高度相关；L3/L4 又共享联合算法证据 A。进入下一轮前应先按逻辑组和相关性去重，再做中性化、滚动样本外、成本和容量。</p></div></div></section>
<section class="shell chapter" id="catalog"><div class="chapter-head"><div class="chapter-no">05</div><div><div class="kicker">Logical inventory</div><h2>135 个逻辑家族目录</h2><p class="chapter-lead">495 列并不等于 495 个互相独立的经济逻辑。这里先按逻辑家族合并方向投影，展示每个家族的解释、输出数和完整历史中最佳 Rank_IC 投影；点击最佳列可进入逐因子档案。</p></div></div><div id="logical-catalog"></div></section>
<section class="shell chapter" id="factors"><div class="chapter-head"><div class="chapter-no">06</div><div><div class="kicker">495 records / 1,980 figures</div><h2>逐因子定义、指标与四图</h2><p class="chapter-lead">左侧可按层级、投影和指标筛选 495 列；右侧只在选中时解码四张图片，避免浏览器一次渲染 1,980 图。排名链接、逻辑目录和 URL hash 都会定位到同一份档案。</p></div></div><div class="filters"><input id="factor-search" type="search" placeholder="搜索 f 序号、正式列、逻辑、公式或经济含义…"><select id="layer-filter"><option value="all">全部层级</option></select><select id="projection-filter"><option value="all">全部投影</option></select><select id="sort-filter"><option value="rank_ic">按 Rank_IC 降序</option><option value="ic">按 IC 降序</option><option value="icir">按 ICIR 降序</option><option value="abs_rank_ic">按 |Rank_IC| 降序</option><option value="registry">按注册表顺序</option></select><button id="diagnostic-toggle" type="button">包含诊断列</button><span class="micro" id="inventory-count"></span></div><div class="explorer"><div class="inventory"><table><thead><tr><th>#</th><th>因子列</th><th>层级</th><th>投影</th><th>IC</th><th>Rank_IC</th><th>ICIR</th></tr></thead><tbody id="inventory-body"></tbody></table></div><aside class="detail" id="factor-detail"><div class="detail-empty">从左侧选择一个因子<br><span class="micro">或点击表现榜/逻辑目录中的因子链接</span></div></aside></div></section>
<section class="shell chapter" id="audit"><div class="chapter-head"><div class="chapter-no">07</div><div><div class="kicker">Evidence and limitations</div><h2>证据追溯、图表口径与限制</h2><p class="chapter-lead">本页没有执行或落盘任何 Jupyter Notebook。四图由正式股票日面板、正式标签、日度评价和区间汇总直接重建，并为每张 WebP 图片保存 SHA-256。</p></div></div><dl class="audit" id="audit-list"></dl><div class="grid-2" style="margin-top:28px"><article class="brick"><h3>图表补建的精确口径</h3><p>40 组图每天先做横截面平均百分位秩，再按 $\lceil percentile\times40\rceil-1$ 分组，保留并列；100 分箱对观测范围位于 [0,1] 的列固定用 [0,1]，其余使用完整历史 min–max。分箱内标签少于 5 个样本时不画收益柱，但计数仍保留。</p></article><article class="brick"><h3>仍需后续完成</h3><p>多重检验修正、相关性聚类、行业/市值/价格/流动性中性化、滚动样本外、交易成本和容量。本页的正负号由数据决定，不自动翻转，也不会根据 IC 自动修改 f 序号或有效性状态。</p></article></div></section>
</main><footer class="shell foot">OPEN5M COUNT PROXY BANK · SELF-CONTAINED HTML · NO EXTERNAL NETWORK ASSETS · REPORT DATE 2026-08-07</footer>
<div class="lightbox" id="image-lightbox" role="dialog" aria-modal="true" aria-hidden="true" aria-labelledby="lightbox-title"><header class="lightbox-bar"><div class="lightbox-heading"><small>EVALUATION FIGURE · CLICK OR LONG PRESS</small><strong id="lightbox-title">评价图放大查看</strong></div><button class="lightbox-close" id="lightbox-close" type="button" aria-label="关闭放大图片">×</button></header><div class="lightbox-stage" id="lightbox-stage"><button class="lightbox-control" id="lightbox-prev" type="button" aria-label="上一张图片">‹</button><div class="lightbox-canvas"><img class="lightbox-image" id="lightbox-image" alt=""></div><button class="lightbox-control" id="lightbox-next" type="button" aria-label="下一张图片">›</button></div><footer class="lightbox-foot"><span class="lightbox-description" id="lightbox-description"></span><span class="lightbox-count" id="lightbox-count" aria-live="polite"></span></footer></div>
<script id="katex-runtime">__KATEX_JS__</script>
<script id="katex-auto-render">__KATEX_AUTO_RENDER_JS__</script>
<script id="report-data" type="application/json">__REPORT_DATA__</script>
<script>
const R=JSON.parse(document.getElementById('report-data').textContent);
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const recMap=new Map(R.records.map((r,i)=>[r.record_id,{...r,index:i}]));
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const finite=x=>Number.isFinite(Number(x));
const fmt=(x,n=4)=>finite(x)?Number(x).toFixed(n):'NA';
const pct=x=>finite(x)?`${(Number(x)*100).toFixed(1)}%`:'NA';
const metric=x=>`<span class="metric ${!finite(x)?'na':Number(x)>=0?'pos':'neg'}">${fmt(x)}</span>`;
const number=x=>finite(x)?Number(x).toLocaleString():'NA';
const factorLink=(id,label)=>`<a class="factor-link" href="#factor-${encodeURIComponent(id)}" data-factor="${esc(id)}">${label??`<code>${esc(id)}</code>`}</a>`;
const full=r=>r.periods.full_history||{}, q2=r=>r.periods.q2||{};
function renderMath(host=document.body){if(typeof renderMathInElement!=='function')return;renderMathInElement(host,{delimiters:[{left:'$$',right:'$$',display:true},{left:'$',right:'$',display:false}],ignoredTags:['script','noscript','style','textarea','pre','code'],throwOnError:false,strict:'ignore',trust:false})}
function renderHead(){const c=R.counts,s=R.source;$('#headline-stats').innerHTML=[['正式候选',c.formal,'排除 5 个诊断列'],['真正新增逻辑',c.new_logical,'f54–f133'],['股票日面板',s.panel_rows,'354 日 × 全市场'],['逐因子评价图',c.images,'495 × 4']].map((x,i)=>`<article class="stat ${i===1?'accent':''}"><small>${esc(x[2])}</small><strong>${number(x[1])}</strong><div>${esc(x[0])}</div></article>`).join('')}
function renderLayers(){const counts={};R.records.forEach(r=>counts[r.layer]=(counts[r.layer]||0)+1);const text={L1:'50 个老 scorer × 五方向；沿用原因子序号。',L1_diagnostic:'快速成交、深度消耗、扫档等状态，只做诊断。',L2:'四族并集、广度、第二强和第三强共识。',L3:'A × 28 个动作前微观结构情境 × 五方向。',L4:'A × 12 个 09:30–09:35 窗口状态 × 五方向。',L5:'36 个做市、执行、吸收、撤退、韧性和净差。'};$('#layer-cards').innerHTML=Object.keys(counts).map((layer,i)=>`<article class="layer-card" style="--layer:${esc(R.records.find(r=>r.layer===layer).layer_color)}"><span class="count">${counts[layer]} columns</span><div class="index">${esc(layer.replace('_diagnostic','D'))}</div><h3>${esc(R.records.find(r=>r.layer===layer).layer_label)}</h3><p>${esc(text[layer])}</p></article>`).join('');$('#whitepaper-body').innerHTML=R.whitepaper_rows.map(x=>`<tr><td>${esc(x.direction)}</td><td style="text-align:left;white-space:normal">${esc(x.implementation)}</td></tr>`).join('')}
function renderMetricStats(){const cards=[['IC','ic'],['Rank_IC','rank_ic'],['ICIR','icir']].map(([label,key],i)=>{const s=R.metric_stats[key];return `<article class="stat ${i===1?'accent':''}"><small>${s.n} 个有效 · ${s.positive} 正 / ${s.negative} 负</small><strong>${fmt(s.mean)}</strong><div>平均 ${label} · 中位数 ${fmt(s.median)}</div></article>`});const best=recMap.get(R.rankings.rank_ic.top[0]);cards.push(`<article class="stat"><small>完整历史 Rank_IC 最高</small><strong>${fmt(full(best).Rank_IC)}</strong>${factorLink(best.record_id,`<code>${esc(best.display_name)}</code>`)}</article>`);$('#metric-stats').innerHTML=cards.join('')}
function rankingIds(metricName){if(metricName==='abs_rank_ic')return R.rankings.rank_ic.absolute;return R.rankings[metricName].top}
function renderRanking(metricName='rank_ic'){const ids=rankingIds(metricName);$('#ranking-body').innerHTML=ids.map((id,i)=>{const r=recMap.get(id),s=full(r),v=q2(r);return `<tr><td class="rank">${i+1}</td><td>${factorLink(id)}</td><td>${esc(r.layer)}</td><td>${esc(r.projection_label)}</td><td>${metric(s.IC)}</td><td>${metric(s.Rank_IC)}</td><td>${metric(s.ICIR)}</td><td>${metric(s.t_nw_lag1)}</td><td>${pct(s.pos_share)}</td><td>${metric(v.Rank_IC)}</td><td>${pct(s.coverage)}</td></tr>`}).join('')}
function barRows(rows){const max=Math.max(...rows.map(x=>Math.abs(x.mean)),1e-9);return rows.map(x=>{const p=Math.abs(x.mean)/max*50,neg=x.mean<0;return `<div class="bar-row"><span>${esc(x.label)} <span class="micro">n=${x.n}</span></span><span class="bar-track"><i class="${neg?'neg':''}" style="width:${p}%"></i></span><b class="${neg?'metric neg':'metric pos'}">${fmt(x.mean)}</b></div>`}).join('')}
function renderPerformance(){$('#layer-performance').innerHTML=barRows(R.layer_rankic);$('#projection-performance').innerHTML=barRows(R.projection_rankic)}
function renderCatalog(){const by={};R.logical_catalog.forEach(x=>(by[x.layer]??=[]).push(x));$('#logical-catalog').innerHTML=Object.entries(by).map(([layer,rows])=>{const sample=R.records.find(r=>r.layer===layer);return `<details class="catalog-layer" style="--layer:${esc(sample.layer_color)}" ${['L2','L3','L4','L5'].includes(layer)?'open':''}><summary>${esc(sample.layer_label)}<span>${rows.length} logical families / ${rows.reduce((a,b)=>a+b.output_count,0)} columns</span></summary><div class="table-scroll"><table class="data catalog-table"><thead><tr><th>逻辑 ID</th><th>定义/研究含义</th><th>输出数</th><th>最佳 Rank_IC 列</th><th>Rank_IC</th></tr></thead><tbody>${rows.map(x=>`<tr><td><code>${esc(x.display_name)}</code></td><td>${esc(x.description)}</td><td>${x.output_count}</td><td>${factorLink(x.best_record_id)}</td><td>${metric(x.best_rank_ic)}</td></tr>`).join('')}</tbody></table></div></details>`}).join('')}
let includeDiagnostics=false,selectedId=null,currentList=[];
let lightboxImages=[],lightboxIndex=0,lightboxTrigger=null,longPressTimer=null,longPressOrigin=null,suppressLightboxClick=false;
function populateFilters(){const layers=[...new Set(R.records.map(r=>r.layer))],projs=[...new Set(R.records.map(r=>r.projection))];$('#layer-filter').innerHTML+=[...layers].map(x=>`<option value="${esc(x)}">${esc(x)} · ${esc(R.records.find(r=>r.layer===x).layer_label)}</option>`).join('');$('#projection-filter').innerHTML+=projs.map(x=>`<option value="${esc(x)}">${esc(R.records.find(r=>r.projection===x).projection_label)}</option>`).join('')}
function recordScore(r,sort){const s=full(r);if(sort==='registry')return -r.index;if(sort==='abs_rank_ic')return finite(s.Rank_IC)?Math.abs(Number(s.Rank_IC)):-Infinity;return finite(s[{ic:'IC',rank_ic:'Rank_IC',icir:'ICIR'}[sort]])?Number(s[{ic:'IC',rank_ic:'Rank_IC',icir:'ICIR'}[sort]]):-Infinity}
function renderInventory(){const q=$('#factor-search').value.trim().toLowerCase(),layer=$('#layer-filter').value,proj=$('#projection-filter').value,sort=$('#sort-filter').value;currentList=R.records.map((r,i)=>({...r,index:i})).filter(r=>(includeDiagnostics||!r.diagnostic)&&(layer==='all'||r.layer===layer)&&(proj==='all'||r.projection===proj)&&(!q||[r.record_id,r.logical_factor_id,r.display_name,r.component_id,r.description,r.formula,r.layer_label,r.projection_label].join(' ').toLowerCase().includes(q))).sort((a,b)=>recordScore(b,sort)-recordScore(a,sort));$('#inventory-count').textContent=`${currentList.length} / ${includeDiagnostics?495:490} 列`;$('#inventory-body').innerHTML=currentList.map((r,i)=>{const s=full(r);return `<tr data-factor="${esc(r.record_id)}" class="${r.record_id===selectedId?'selected':''}"><td>${i+1}</td><td><code>${esc(r.record_id)}</code></td><td>${esc(r.layer)}</td><td>${esc(r.projection_label)}</td><td>${metric(s.IC)}</td><td>${metric(s.Rank_IC)}</td><td>${metric(s.ICIR)}</td></tr>`}).join('')}
function metricCards(s,label){return `<div class="section-label">${esc(label)}</div><div class="metric-grid"><article class="mini-stat"><small>IC</small><strong class="${finite(s.IC)&&s.IC<0?'metric neg':'metric pos'}">${fmt(s.IC)}</strong></article><article class="mini-stat"><small>Rank_IC</small><strong class="${finite(s.Rank_IC)&&s.Rank_IC<0?'metric neg':'metric pos'}">${fmt(s.Rank_IC)}</strong></article><article class="mini-stat"><small>ICIR RAW</small><strong class="${finite(s.ICIR)&&s.ICIR<0?'metric neg':'metric pos'}">${fmt(s.ICIR)}</strong></article><article class="mini-stat"><small>N DAYS / COVERAGE</small><strong>${s.n_days??'NA'} · ${pct(s.coverage)}</strong></article></div>`}
function openFactor(id,{scroll=false}={}){const r=recMap.get(id);if(!r)return;selectedId=id;const s=full(r),v=q2(r),d=r.distribution||{};$('#factor-detail').innerHTML=`<div class="kicker">${esc(r.kind_label)} · ${esc(r.component_id)}</div><h3 class="detail-title">${esc(r.display_name)}</h3><div class="chips"><span class="chip layer" style="--layer:${esc(r.layer_color)}">${esc(r.layer)} · ${esc(r.layer_label)}</span><span class="chip">${esc(r.projection_label)}</span><span class="chip">${r.diagnostic?'DIAGNOSTIC':'FORMAL'}</span></div><p class="micro"><code>${esc(r.record_id)}</code></p>${metricCards(s,'完整历史 · 2025-01-02 至 2026-06-30')}${metricCards(v,'2026Q2 · 2026-04-01 至 2026-06-30')}<div class="section-label">定义与经济含义</div><p class="detail-copy">${esc(r.description)}</p><div class="formula">${esc(r.formula)}<br>${esc(r.aggregation_formula)}</div><div class="section-label">从逐笔证据到股票日列</div><ol class="steps">${r.construction_steps.map(x=>`<li>${esc(x)}</li>`).join('')}</ol><div class="grid-2"><div><div class="section-label">高值/低值怎么读</div><p class="detail-copy">${esc(r.projection_interpretation)}</p></div><div><div class="section-label">解释边界</div><p class="detail-copy">${esc(r.interpretation_boundary)}</p></div></div><div class="section-label">白皮书/方法来源</div><p class="detail-copy">${esc(r.whitepaper_link)}</p><div class="section-label">股票日分布</div><div class="metric-grid"><article class="mini-stat"><small>FINITE COUNT</small><strong>${number(d.finite_count)}</strong></article><article class="mini-stat"><small>ZERO SHARE</small><strong>${pct(d.zero_share)}</strong></article><article class="mini-stat"><small>MEAN ± STD</small><strong>${fmt(d.mean)} ± ${fmt(d.std)}</strong></article><article class="mini-stat"><small>MIN / MAX</small><strong>${fmt(d.minimum)} / ${fmt(d.maximum)}</strong></article></div><div class="section-label">四张评价图（点击或长按可放大）</div><div class="figure-grid">${r.images.map(im=>`<figure class="figure-card"><img src="data:${im.mime};base64,${im.data}" width="${im.width}" height="${im.height}" loading="lazy" draggable="false" tabindex="0" role="button" aria-label="放大查看：${esc(im.name)}" alt="${esc(r.display_name)} · ${esc(im.name)}"><figcaption>${esc(im.name)}</figcaption><p>${esc(im.description)}</p></figure>`).join('')}</div><div class="detail-nav"><button type="button" id="prev-factor">← 上一个</button><button type="button" id="next-factor">下一个 →</button></div>`;renderMath($('#factor-detail'));renderInventory();history.replaceState(null,'',`#factor-${encodeURIComponent(id)}`);$('#prev-factor').onclick=()=>stepFactor(-1);$('#next-factor').onclick=()=>stepFactor(1);if(scroll)$('#factors').scrollIntoView({behavior:'smooth',block:'start'})}
function stepFactor(delta){const list=currentList.length?currentList:R.records,index=Math.max(0,list.findIndex(r=>r.record_id===selectedId)),next=list[(index+delta+list.length)%list.length];openFactor(next.record_id)}
function renderAudit(){const s=R.source,rows=[['正式运行 revision',s.revision],['Registry hash',s.registry_hash],['证据清单 SHA-256',s.evidence_manifest_sha256],['服务器结果目录',s.run_root],['评价区间',`${s.start} 至 ${s.end}；${s.day_count} 个交易日`],['股票日面板行数',number(s.panel_rows)],['日度 IC 行数',number(s.daily_rows)],['标签',s.label],['IC 定义',s.ic_definition],['Rank_IC 定义',s.rank_ic_definition],['ICIR 定义',s.icir_definition],['40 组口径',s.group_method],['100 分箱口径',s.bin_method]];$('#audit-list').innerHTML=rows.map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}
function updateLightbox(){const source=lightboxImages[lightboxIndex];if(!source)return;const figure=source.closest('.figure-card'),title=figure?.querySelector('figcaption')?.textContent||source.alt,description=figure?.querySelector('p')?.textContent||'';$('#lightbox-image').src=source.currentSrc||source.src;$('#lightbox-image').alt=source.alt;$('#lightbox-title').textContent=title;$('#lightbox-description').textContent=description;$('#lightbox-count').textContent=`${lightboxIndex+1} / ${lightboxImages.length}`}
function openLightbox(source){const images=$$('#factor-detail .figure-card img'),index=images.indexOf(source);if(index<0)return;lightboxImages=images;lightboxIndex=index;lightboxTrigger=source;updateLightbox();const box=$('#image-lightbox');box.classList.add('is-open');box.setAttribute('aria-hidden','false');document.body.classList.add('lightbox-open');$('#lightbox-close').focus({preventScroll:true})}
function closeLightbox(){const box=$('#image-lightbox');if(!box.classList.contains('is-open'))return;box.classList.remove('is-open');box.setAttribute('aria-hidden','true');document.body.classList.remove('lightbox-open');$('#lightbox-image').removeAttribute('src');if(lightboxTrigger?.isConnected)lightboxTrigger.focus({preventScroll:true})}
function stepLightbox(delta){if(!lightboxImages.length)return;lightboxIndex=(lightboxIndex+delta+lightboxImages.length)%lightboxImages.length;updateLightbox()}
function clearLongPress(){if(longPressTimer!==null)clearTimeout(longPressTimer);longPressTimer=null;longPressOrigin=null;if(suppressLightboxClick)setTimeout(()=>{suppressLightboxClick=false},500)}
function setupLightbox(){$('#lightbox-close').onclick=closeLightbox;$('#lightbox-prev').onclick=()=>stepLightbox(-1);$('#lightbox-next').onclick=()=>stepLightbox(1);$('#lightbox-stage').addEventListener('click',e=>{if(e.target.id==='lightbox-stage'||e.target.classList.contains('lightbox-canvas'))closeLightbox()});document.addEventListener('click',e=>{const image=e.target.closest('.figure-card img');if(!image)return;if(suppressLightboxClick){suppressLightboxClick=false;e.preventDefault();return}openLightbox(image)});document.addEventListener('pointerdown',e=>{const image=e.target.closest('.figure-card img');if(!image||e.button!==0)return;clearLongPress();longPressOrigin={x:e.clientX,y:e.clientY};longPressTimer=setTimeout(()=>{suppressLightboxClick=true;openLightbox(image);longPressTimer=null},450)});document.addEventListener('pointermove',e=>{if(longPressOrigin&&Math.hypot(e.clientX-longPressOrigin.x,e.clientY-longPressOrigin.y)>12)clearLongPress()});document.addEventListener('pointerup',clearLongPress);document.addEventListener('pointercancel',clearLongPress);document.addEventListener('contextmenu',e=>{if(e.target.closest('.figure-card img'))e.preventDefault()});document.addEventListener('keydown',e=>{const box=$('#image-lightbox'),image=e.target.closest?.('.figure-card img');if(image&&(e.key==='Enter'||e.key===' ')){e.preventDefault();openLightbox(image);return}if(!box.classList.contains('is-open'))return;if(e.key==='Escape'){e.preventDefault();closeLightbox()}else if(e.key==='ArrowLeft'){e.preventDefault();stepLightbox(-1)}else if(e.key==='ArrowRight'){e.preventDefault();stepLightbox(1)}})}
function setup(){renderHead();renderLayers();renderMetricStats();renderRanking();renderPerformance();renderCatalog();populateFilters();renderInventory();renderAudit();renderMath();setupLightbox();$$('.rank-tabs button').forEach(b=>b.onclick=()=>{$$('.rank-tabs button').forEach(x=>x.classList.remove('active'));b.classList.add('active');renderRanking(b.dataset.metric)});['#factor-search','#layer-filter','#projection-filter','#sort-filter'].forEach(sel=>$(sel).addEventListener('input',renderInventory));$('#diagnostic-toggle').onclick=e=>{includeDiagnostics=!includeDiagnostics;e.currentTarget.classList.toggle('active',includeDiagnostics);renderInventory()};document.addEventListener('click',e=>{const link=e.target.closest('[data-factor]');if(!link)return;const id=link.dataset.factor;if(recMap.has(id)){e.preventDefault();openFactor(id,{scroll:!link.closest('#inventory-body')})}});const hash=decodeURIComponent(location.hash.replace(/^#factor-/,''));if(recMap.has(hash))openFactor(hash);else openFactor(R.rankings.rank_ic.top[0]);const sections=$$('section[id]'),links=$$('.nav a');const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){links.forEach(a=>a.classList.toggle('active',a.getAttribute('href')===`#${entry.target.id}`))}}),{rootMargin:'-30% 0px -60% 0px'});sections.forEach(s=>observer.observe(s))}
setup();
</script>
</body></html>
"""


def build_html(payload: dict[str, Any], old_report: Path) -> str:
    katex_css, katex_js, katex_auto = extract_katex_assets(old_report)
    result = (
        HTML_TEMPLATE.replace("__KATEX_CSS__", katex_css)
        .replace("__KATEX_JS__", katex_js)
        .replace("__KATEX_AUTO_RENDER_JS__", katex_auto)
        .replace("__REPORT_DATA__", safe_json(payload))
    )
    if any(token in result for token in ("__KATEX_CSS__", "__KATEX_JS__", "__KATEX_AUTO_RENDER_JS__", "__REPORT_DATA__")):
        raise RuntimeError("HTML template replacement is incomplete")
    return result


def extract_report_payload(source: str) -> tuple[re.Match[str], dict[str, Any]]:
    match = re.search(
        r'(<script id="report-data" type="application/json">)(.*?)(</script>)',
        source,
        flags=re.S,
    )
    if not match:
        raise RuntimeError("report-data block is missing")
    return match, json.loads(match.group(2))


def atomic_write_text(path: Path, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(source, encoding="utf-8", newline="\n")
    temporary.replace(path)


def build_website_html(
    self_contained_source: str,
    asset_dir: Path,
    asset_url_prefix: str,
) -> tuple[str, dict[str, Any]]:
    match, payload = extract_report_payload(self_contained_source)
    expected_assets: set[str] = set()
    references: list[dict[str, Any]] = []
    decoded_reference_bytes = 0
    max_asset_bytes = 0
    asset_dir.mkdir(parents=True, exist_ok=True)

    for record in payload["records"]:
        images = record.get("images", [])
        if len(images) != 4:
            raise RuntimeError(f'{record["record_id"]}: website build did not receive four images')
        for position, image in enumerate(images, start=1):
            encoded = image.pop("data", None)
            if not isinstance(encoded, str):
                raise RuntimeError(f'{record["record_id"]} image {position}: base64 payload is missing')
            decoded = base64.b64decode(encoded, validate=True)
            digest = hashlib.sha256(decoded).hexdigest()
            if digest != image.get("sha256") or len(decoded) != image.get("bytes"):
                raise RuntimeError(f'{record["record_id"]} image {position}: payload audit mismatch')
            with Image.open(BytesIO(decoded)) as observed:
                observed.verify()
            with Image.open(BytesIO(decoded)) as observed:
                if observed.format != "WEBP" or observed.size != (image["width"], image["height"]):
                    raise RuntimeError(f'{record["record_id"]} image {position}: WebP metadata mismatch')

            filename = f"{digest[:24]}.webp"
            asset_path = asset_dir / filename
            expected_assets.add(filename)
            if asset_path.exists():
                if sha256_file(asset_path) != digest:
                    raise RuntimeError(f"existing website asset hash mismatch: {asset_path}")
            else:
                asset_path.write_bytes(decoded)
            image["url"] = f"{asset_url_prefix}/{filename}"
            decoded_reference_bytes += len(decoded)
            max_asset_bytes = max(max_asset_bytes, len(decoded))
            references.append(
                {
                    "record_id": record["record_id"],
                    "position": position,
                    "name": image["name"],
                    "url": image["url"],
                    "sha256": digest,
                    "bytes": len(decoded),
                    "width": image["width"],
                    "height": image["height"],
                }
            )

    actual_assets = {path.name for path in asset_dir.glob("*.webp")}
    unexpected = sorted(actual_assets - expected_assets)
    missing = sorted(expected_assets - actual_assets)
    if unexpected or missing:
        raise RuntimeError(
            f"website asset set is not deterministic: unexpected={unexpected}, missing={missing}"
        )

    website_source = (
        self_contained_source[: match.start(2)]
        + safe_json(payload)
        + self_contained_source[match.end(2) :]
    )
    if website_source.count(INLINE_IMAGE_RUNTIME) != 1:
        raise RuntimeError("self-contained image runtime signature differs from one")
    website_source = website_source.replace(INLINE_IMAGE_RUNTIME, WEBSITE_IMAGE_RUNTIME, 1)
    website_source = website_source.replace(
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        '<meta name="report-build" content="website-hashed-local-assets-v1">',
        1,
    )
    website_source = website_source.replace(
        "一个可离线检索的研究档案",
        "一个可在线检索的研究档案",
        1,
    )
    website_source = website_source.replace(
        "OPEN5M COUNT PROXY BANK · SELF-CONTAINED HTML · NO EXTERNAL NETWORK ASSETS",
        "OPEN5M COUNT PROXY BANK · WEBSITE HTML · HASHED LOCAL IMAGE ASSETS",
        1,
    )
    website_bytes = len(website_source.encode("utf-8"))
    if website_bytes > CLOUDFLARE_SINGLE_ASSET_LIMIT:
        raise RuntimeError(f"website HTML exceeds 25 MiB: {website_bytes}")
    if max_asset_bytes > CLOUDFLARE_SINGLE_ASSET_LIMIT:
        raise RuntimeError(f"website image exceeds 25 MiB: {max_asset_bytes}")

    manifest = {
        "schema_version": "open5m-factor-report-web-assets-v1",
        "status": "complete",
        "factor_count": EXPECTED_FACTORS,
        "image_references": len(references),
        "unique_assets": len(expected_assets),
        "decoded_reference_bytes": decoded_reference_bytes,
        "website_html_bytes": website_bytes,
        "max_asset_bytes": max_asset_bytes,
        "asset_url_prefix": asset_url_prefix,
        "references": references,
    }
    atomic_write_text(asset_dir / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return website_source, manifest


def validate_html(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    if source.count('<script id="report-data" type="application/json">') != 1:
        raise RuntimeError("report-data block count differs from one")
    match = re.search(r'<script id="report-data" type="application/json">(.*?)</script>', source, flags=re.S)
    if not match:
        raise RuntimeError("report-data block is missing")
    observed = json.loads(match.group(1))
    if len(observed.get("records", [])) != EXPECTED_FACTORS:
        raise RuntimeError("HTML payload does not contain 495 records")
    image_count = sum(len(record.get("images", [])) for record in observed["records"])
    if image_count != EXPECTED_IMAGES:
        raise RuntimeError("HTML payload does not contain 1980 images")
    if re.search(r'<(?:script|link|img)[^>]+(?:src|href)=["\']https?://', source, flags=re.I):
        raise RuntimeError("HTML contains an external network asset")
    for section in ("scope", "chain", "new", "ranking", "catalog", "factors", "audit"):
        if f'id="{section}"' not in source:
            raise RuntimeError(f"HTML section is missing: {section}")
    return {
        "status": "complete",
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "records": len(observed["records"]),
        "formal": sum(not row["diagnostic"] for row in observed["records"]),
        "diagnostics": sum(row["diagnostic"] for row in observed["records"]),
        "images": image_count,
        "external_assets": 0,
        "payload_schema": payload["schema_version"],
    }


def validate_website_html(path: Path, asset_dir: Path) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    _, payload = extract_report_payload(source)
    images = [image for record in payload.get("records", []) for image in record.get("images", [])]
    if len(payload.get("records", [])) != EXPECTED_FACTORS or len(images) != EXPECTED_IMAGES:
        raise RuntimeError("website payload inventory is incomplete")
    if any("data" in image or not image.get("url") for image in images):
        raise RuntimeError("website payload still contains inline images or lacks URLs")
    if source.count(WEBSITE_IMAGE_RUNTIME) != 1 or INLINE_IMAGE_RUNTIME in source:
        raise RuntimeError("website image runtime was not replaced exactly once")
    if len(source.encode("utf-8")) > CLOUDFLARE_SINGLE_ASSET_LIMIT:
        raise RuntimeError("website HTML exceeds Cloudflare's single-asset limit")
    if re.search(r'<(?:script|link|img)[^>]+(?:src|href)=["\']https?://', source, flags=re.I):
        raise RuntimeError("website HTML contains an external network asset")
    for image in images:
        asset_path = asset_dir / Path(image["url"]).name
        if not asset_path.exists() or sha256_file(asset_path) != image["sha256"]:
            raise RuntimeError(f"website image asset is missing or corrupt: {asset_path}")
    return {
        "status": "complete",
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "records": len(payload["records"]),
        "images": len(images),
        "unique_assets": len({image["url"] for image in images}),
        "max_asset_bytes": max(path.stat().st_size for path in asset_dir.glob("*.webp")),
        "external_network_assets": 0,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--research-repo", type=Path, default=DEFAULT_RESEARCH_REPO)
    parser.add_argument("--old-report", type=Path, default=OLD_SELF_CONTAINED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--website-output", type=Path, default=DEFAULT_WEBSITE_OUTPUT)
    parser.add_argument("--asset-dir", type=Path, default=DEFAULT_ASSET_DIR)
    parser.add_argument("--asset-url-prefix", default=DEFAULT_ASSET_URL_PREFIX)
    parser.add_argument(
        "--website-only",
        action="store_true",
        help="Reuse the existing self-contained --output and only build the website assets/version.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.website_only:
        html_source = args.output.resolve().read_text(encoding="utf-8")
        _, payload = extract_report_payload(html_source)
    else:
        payload = build_payload(args.evidence.resolve(), args.research_repo.resolve())
        html_source = build_html(payload, args.old_report.resolve())
        atomic_write_text(args.output, html_source)
    self_contained_stats = validate_html(args.output, payload)
    website_source, website_manifest = build_website_html(
        html_source,
        args.asset_dir.resolve(),
        args.asset_url_prefix,
    )
    atomic_write_text(args.website_output, website_source)
    website_stats = validate_website_html(args.website_output, args.asset_dir.resolve())
    print(
        json.dumps(
            {
                "status": "complete",
                "self_contained": self_contained_stats,
                "website": website_stats,
                "website_manifest": {
                    key: website_manifest[key]
                    for key in (
                        "factor_count",
                        "image_references",
                        "unique_assets",
                        "decoded_reference_bytes",
                        "website_html_bytes",
                        "max_asset_bytes",
                    )
                },
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
