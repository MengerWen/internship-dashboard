"""Publish the causal-accounting Open5m run from read-only server artifacts."""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

import add_nav_scrollspy


ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "content/assets/model-report-2026-09-18"
PAGE = ROOT / "content/daily/2026-09-18.show.html"
DAILY = ROOT / "content/daily/2026-09-18.md"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe(value):
    if isinstance(value, dict):
        return {str(k): safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if math.isfinite(float(value)) else None
    if pd.isna(value):
        return None
    return value


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def records(path: Path):
    return safe(pd.read_parquet(path).to_dict("records"))


def number(value, places=3):
    return "—" if value is None else f"{value:,.{places}f}"


def pct(value, places=2):
    return "—" if value is None else f"{value * 100:,.{places}f}%"


def chart(rows, key, title, *, color="#117a76", y_percent=False, height=230):
    values = np.asarray([r.get(key, float("nan")) for r in rows], dtype=float)
    ok = np.isfinite(values)
    if not ok.any():
        return ""
    low, high = float(np.nanmin(values)), float(np.nanmax(values))
    low, high = min(low, 0.0), max(high, 0.0)
    pad = max((high - low) * .09, 1e-12)
    low, high = low - pad, high + pad
    left, right, top, bottom = 60, 865, 18, height - 37
    width = right - left
    scale = (bottom - top) / (high - low)
    zero = bottom - (0 - low) * scale
    points = [(left + i * width / max(len(rows) - 1, 1), bottom - (v - low) * scale)
              for i, v in enumerate(values)]
    series = " ".join(f"{x:.1f},{y:.1f}" for (x, y), valid in zip(points, ok) if valid)
    ticks = []
    for j in range(5):
        val = low + (high - low) * j / 4
        y = bottom - (val - low) * scale
        label = f"{val * 100:.1f}%" if y_percent else f"{val:.2f}"
        ticks.append(f'<line x1="{left}" x2="{right}" y1="{y:.1f}" y2="{y:.1f}" stroke="#dce3e0"/>'
                     f'<text x="{left-8}" y="{y+4:.1f}" text-anchor="end">{label}</text>')
    first = html.escape(str(rows[0].get("date", rows[0].get("iteration", ""))))
    last = html.escape(str(rows[-1].get("date", rows[-1].get("iteration", ""))))
    return (f'<figure><figcaption>{html.escape(title)}</figcaption>'
            f'<svg viewBox="0 0 900 {height}" role="img" aria-label="{html.escape(title)}">'
            f'<g class="ticks">{"".join(ticks)}<text x="{left}" y="{height-8}">{first}</text>'
            f'<text x="{right}" y="{height-8}" text-anchor="end">{last}</text></g>'
            f'<line x1="{left}" x2="{right}" y1="{zero:.1f}" y2="{zero:.1f}" stroke="#9daaa4"/>'
            f'<polyline points="{series}" fill="none" stroke="{color}" stroke-width="2.2" '
            f'stroke-linecap="round" stroke-linejoin="round"/></svg></figure>')


def make_report(source: Path):
    train_dir, test_dir = source / "train", source / "test"
    required = {
        "train/timing_resource_summary.json": train_dir / "timing_resource_summary.json",
        "train/dataset_summary.json": train_dir / "dataset_summary.json",
        "train/effective_parameters.json": train_dir / "effective_parameters.json",
        "train/feature_mapping_328.json": train_dir / "feature_mapping_328.json",
        "train/per_round_metrics.parquet": train_dir / "per_round_metrics.parquet",
        "test/test_summary.json": test_dir / "test_summary.json",
        "test/validation_selection_receipt.json": test_dir / "validation_selection_receipt.json",
        "test/frozen_model_identity.json": test_dir / "frozen_model_identity.json",
        "test/test_daily_metrics.parquet": test_dir / "test_daily_metrics.parquet",
        "test/test_monthly_metrics.parquet": test_dir / "test_monthly_metrics.parquet",
        "test/test_positions.parquet": test_dir / "test_positions.parquet",
        "run_paths.json": source / "run_paths.json",
        "baseline/test_summary.json": source / "baseline/test_summary.json",
    }
    missing = [name for name, path in required.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(", ".join(missing))
    train = load_json(required["train/timing_resource_summary.json"])
    dataset = load_json(required["train/dataset_summary.json"])
    params = load_json(required["train/effective_parameters.json"])
    mapping_file = load_json(required["train/feature_mapping_328.json"])
    mapping = [row for row in mapping_file if "source" in row]
    excluded = [row for row in mapping_file if "excluded_old_columns" in row]
    curve = records(required["train/per_round_metrics.parquet"])
    test = load_json(required["test/test_summary.json"])
    selection = load_json(required["test/validation_selection_receipt.json"])
    identity = load_json(required["test/frozen_model_identity.json"])
    daily = records(required["test/test_daily_metrics.parquet"])
    monthly = records(required["test/test_monthly_metrics.parquet"])
    positions = pd.read_parquet(required["test/test_positions.parquet"])
    paths = load_json(required["run_paths.json"])
    baseline = load_json(required["baseline/test_summary.json"])

    assert train["status"] == test["status"] == "complete"
    assert dataset["feature_count"] == test["feature_count"] == len(mapping) == 328
    assert len(curve) == train["actual_rounds"] == 1000
    assert len(daily) == test["test_date_count"] == 176
    assert selection["selected_iteration"] == test["selected_model_iteration"]
    assert identity["selected_iteration"] == selection["selected_iteration"]
    assert test["no_training_call"] and selection["selection_was_computed_before_test_read"]
    assert not any("f97" in json.dumps(row, ensure_ascii=False).lower() for row in mapping)
    assert len(excluded) == 1
    assert sum("f97" in name.lower() for name in excluded[0]["excluded_old_columns"]) == 2
    assert paths["business_revision"] and paths["train_run_root"] and paths["test_run_root"]
    assert baseline["feature_count"] == 330 and baseline["test_date_count"] == test["test_date_count"]
    assert baseline["test_start"] == test["test_start"] and baseline["test_end"] == test["test_end"]
    metric = selection["selection_metric"]
    finite_curve = [row for row in curve if row[metric] is not None and math.isfinite(row[metric])]
    best = max(finite_curve, key=lambda row: row[metric])
    assert best["iteration"] == selection["selected_iteration"]
    assert positions.groupby(["date", "portfolio"])["portfolio_contribution"].sum().size > 0
    assert positions["status"].value_counts().to_dict() == test["position_status_counts"]
    assert sum(d["long_missing_label_count"] + d["short_missing_label_count"]
               + d["ls_long_missing_label_count"] + d["ls_short_missing_label_count"]
               for d in daily) == int((positions["status"] == "open_marked").sum())
    ls = positions[positions["portfolio"].isin(["long_short_long", "long_short_short"])]
    leg_frame = ls.groupby(["date", "portfolio"])["portfolio_contribution"].sum().unstack(fill_value=0)
    leg_frame = leg_frame.reindex([r["date"] for r in daily], fill_value=0)
    actual = leg_frame.sum(axis=1)
    assert np.allclose(actual.to_numpy(), [r["long_short_return"] for r in daily], atol=1e-12, rtol=0)
    long_leg = leg_frame["long_short_long"].to_numpy(dtype=float)
    short_leg = leg_frame["long_short_short"].to_numpy(dtype=float)
    covariance = float(np.cov(long_leg, short_leg, ddof=1)[0, 1])
    variance_sum = float(np.var(long_leg, ddof=1) + np.var(short_leg, ddof=1))
    leg_dependence = {
        "signed_leg_correlation": float(np.corrcoef(long_leg, short_leg)[0, 1]),
        "covariance_variance_offset_fraction": float(-2 * covariance / variance_sum),
        "long_short_legs_daily": [
            {"date": row["date"], "long_contribution": float(l), "short_contribution": float(s)}
            for row, l, s in zip(daily, long_leg, short_leg)
        ],
    }
    source_hashes = {name: digest(path) for name, path in required.items()}
    data = {
        "report_contract": "2026-09-21 causal selection and fixed-budget valuation",
        "paths": paths,
        "source_sha256": source_hashes,
        "train_summary": train,
        "dataset": dataset,
        "effective_parameters": params,
        "feature_mapping": mapping,
        "excluded_old_columns": excluded[0]["excluded_old_columns"],
        "validation_curve": curve,
        "selection": selection,
        "frozen_model_identity": identity,
        "test_summary": test,
        "test_daily": daily,
        "test_monthly": monthly,
        "leg_dependence": leg_dependence,
        "position_status_counts": test["position_status_counts"],
        "observational_baseline": {
            "run_root": paths["observational_baseline_root"],
            "feature_count": baseline["feature_count"],
            "overall_metrics": baseline["overall_metrics"],
            "interpretation": "Different features, selection, accounting and trained model; observational only",
        },
        "position_rows": len(positions),
        "open_position_rows": int((positions["status"] == "open_marked").sum()),
    }
    metrics = test["overall_metrics"]
    old_sharpe = baseline["overall_metrics"]["long_short_sharpe"]
    old_ic = baseline["overall_metrics"]["mean_daily_rank_ic"]
    selected = selection["selected_iteration"]
    train_time = train["timings_seconds"]["whole_business_flow"]
    test_time = test["timings_seconds"]["whole_business_flow"]
    train_peak = train["resources"]["whole_flow_memory_peak_cgroup_bytes"] / 2**30
    test_peak = test["resources"]["task_memory_peak_bytes"] / 2**30
    status = test["position_status_counts"]
    status_cells = "".join(f"<tr><td>{html.escape(k)}</td><td>{v:,}</td></tr>" for k, v in sorted(status.items()))
    month_cells = "".join(
        f'<tr><td>{html.escape(row["month"])}</td><td>{number(row.get("mean_daily_rank_ic"), 4)}</td>'
        f'<td>{number(row.get("long_short_sharpe"), 2)}</td><td>{number(row.get("long_short_mean_daily_return"), 5)}</td></tr>'
        for row in monthly
    )
    embedded = json.dumps(safe(data), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>328 因子：修正选股时点与未退出估值后的真实数据结果</title>
<style>
:root{{--paper:#f4f2eb;--ink:#23343c;--teal:#117a76;--rust:#a94f37;--line:#c8d4d0}}*{{box-sizing:border-box}}
html{{scroll-behavior:smooth}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.75 "Microsoft YaHei","PingFang SC",sans-serif}}
.wrap{{max-width:1100px;margin:auto;padding:0 28px}}header{{padding:42px 0 38px;border-bottom:1px solid var(--line)}}.eyebrow{{color:var(--teal);font-size:13px;letter-spacing:.12em}}
h1,h2{{font-family:"Noto Serif CJK SC","Songti SC",serif;font-weight:normal;line-height:1.3}}h1{{font-size:clamp(32px,5vw,56px);margin:13px 0}}h2{{font-size:30px;margin:0 0 18px}}
.lead{{font-size:19px;max-width:780px}}nav{{position:sticky;top:0;background:#f4f2ebf5;border-bottom:1px solid var(--line);z-index:1;overflow:auto;white-space:nowrap}}
nav .wrap{{display:flex;gap:25px;padding-block:13px}}a{{color:var(--teal)}}nav a{{text-decoration:none;font-size:14px}}section{{padding:50px 0;border-bottom:1px solid var(--line)}}
.metrics{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:15px;margin:28px 0}}.metric,.note{{background:#fff;padding:17px 20px;border-top:3px solid var(--teal)}}.metric strong{{display:block;font:32px Georgia,serif;color:var(--teal)}}.metric span,small{{font-size:13px;color:#53636a}}.note{{border-color:var(--rust);margin:25px 0}}.note strong{{color:var(--rust)}}
.grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}}figure{{margin:25px 0;background:#fff;padding:18px}}figcaption{{font-size:15px;font-weight:bold}}svg{{width:100%;height:auto}}.ticks{{font:12px "Microsoft YaHei",sans-serif;fill:#5a6b70}}
table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}}th,td{{padding:9px 12px;border-bottom:1px solid var(--line);text-align:left}}.table-scroll{{overflow:auto}}
code{{overflow-wrap:anywhere}}details{{margin:20px 0}}summary{{cursor:pointer;color:var(--teal)}}.mono{{font:13px/1.65 Consolas,monospace;overflow-wrap:anywhere}}
@media(max-width:720px){{.metrics,.grid{{grid-template-columns:1fr 1fr}}.wrap{{padding:0 18px}}}}@media(max-width:480px){{.metrics,.grid{{grid-template-columns:1fr}}}}
</style></head><body>
<header><div class="wrap"><div class="eyebrow">2026-09-18 MODEL REPORT · 2026-09-21 RECOMPUTE</div><h1>修正选股时点与账本后，<br>重新看模型表现</h1>
<p class="lead">本次用服务器真实数据重新训练并测试 328 因子 CPU LightGBM。f97 买侧、卖侧两列都不作为输入；09:35 的排名不借用随后一分钟的成交状态；进入而未在出场窗口成交的股票仍在账本中估值。</p>
<div class="metrics"><div class="metric"><strong>{number(metrics['long_short_sharpe'],2)}</strong><span>test 多空毛 Sharpe · 固定窗口估值</span></div>
<div class="metric"><strong>{number(metrics['mean_daily_rank_ic'],4)}</strong><span>test 日均 RankIC</span></div>
<div class="metric"><strong>{selected}</strong><span>按 validation 选择的轮数</span></div>
<div class="metric"><strong>{data['open_position_rows']:,}</strong><span>账本中未退出而已估值的记录</span></div></div>
<p><small>业务 revision <code>{html.escape(paths['business_revision'])}</code>；单次第 15 折训练，176 日 test。指标不含手续费、冲击和持续持仓结算。</small></p></div></header>
<nav><div class="wrap"><a href="#contract">修正口径</a><a href="#validation">训练与验证</a><a href="#test">test 结果</a><a href="#ledger">持仓账本</a><a href="#evidence">证据与边界</a></div></nav>
<main class="wrap"><section id="contract"><h2>修正口径</h2><div class="grid"><div><h3>09:35 决策</h3><p>因子交集形成候选池，在可用分数上按分数排序并确定固定名额。09:35–09:36 的成交只决定已选股票能否进场；不能补选下一名。因进场无成交或方向封板而未成交的名额持有现金，组合分母不缩小。</p></div>
<div><h3>09:46 估值</h3><p>9:45–9:46 无成交的已进场股票，取 09:46 前最后有效成交价估值，并以 <code>open_marked</code> 保留在逐股账本。估值不是实际卖出；本研究没有模拟后续卖出或跨日资金占用。</p></div></div>
<div class="note"><strong>与旧试算的关系：</strong>旧页面展示的 330 列、按未来成交筛选/缩小分母的 test 毛 Sharpe 为 {number(old_sharpe,2)}，日均 RankIC 为 {number(old_ic,4)}。本次同时改变输入列、选股与估值口径并重新训练；两次结果只能作观察性对照，不能把差额归因于某一项修正。</div>
<p>进场仍采用 [09:35,09:36) 成交 VWAP，出场采用 [09:45,09:46) 成交 VWAP；收益序列是固定窗口估值，不是已平仓的连续净值。训练目标、日期划分和其余 328 列保持原试验设定。</p></section>
<section id="validation"><h2>一次真实数据训练与验证</h2><p>训练 {dataset['train_date_count']} 个交易日、{dataset['train_rows']:,} 行，2025 年 9 月验证 {dataset['validation_date_count']} 日。CPU LightGBM <code>regression_l2</code>，8 线程，固定种子 {params['booster_params']['seed']}，完整训练 {train['actual_rounds']} 轮；按 validation 固定预算多空毛 Sharpe 选择第 {selected} 轮，test 没有重训或重选。</p>
{chart(curve, metric, 'validation 各轮固定预算多空毛 Sharpe')}
<p>业务训练全流程实测 {number(train_time,1)} 秒，训练调用 {number(train['timings_seconds']['train_call_total'],1)} 秒；任务 cgroup 峰值 {number(train_peak,2)} GiB。结果只代表这一次配置的实测，不是其余 14 折的表现。</p></section>
<section id="test"><h2>176 日 test 结果</h2><p>2025-10-09 至 2026-06-30，共 {test['test_date_count']} 个交易日，股票日因子交集 {test['factor_intersection_rows']:,} 行，有效标签 {test['valid_label_rows']:,} 行。</p>
<div class="metrics"><div class="metric"><strong>{number(metrics['pure_long_sharpe'],2)}</strong><span>Pure Long 毛 Sharpe</span></div><div class="metric"><strong>{number(metrics['pure_short_sharpe'],2)}</strong><span>Pure Short 毛 Sharpe</span></div><div class="metric"><strong>{number(metrics['long_short_sharpe'],2)}</strong><span>Long-Short 毛 Sharpe</span></div><div class="metric"><strong>{number(metrics['daily_equal_mse'],4)}</strong><span>每日等权 MSE</span></div></div>
{chart(daily, 'long_short_return', '逐日多空固定窗口估值收益', y_percent=True, color='#a94f37')}
{chart(daily, 'rank_ic', '逐日 RankIC')}
<h3>逐月观察</h3><div class="table-scroll"><table><thead><tr><th>月份</th><th>日均 RankIC</th><th>多空毛 Sharpe</th><th>日均多空收益</th></tr></thead><tbody>{month_cells}</tbody></table></div>
<div class="note"><strong>为何 RankIC 小而 Sharpe 仍高？</strong>这两者统计的是不同对象：RankIC 衡量全池逐日排序；组合只取两端各 10%。本次多空两腿的有符号日收益相关系数为 {number(leg_dependence['signed_leg_correlation'],3)}，负协方差抵消了两腿方差和的 {pct(leg_dependence['covariance_variance_offset_fraction'])}。这有助于解释高 Sharpe，但只是从收益序列得到的描述，不能据此排除其他未来信息或执行偏差。</div>
<p>test 业务流程实测 {number(test_time,1)} 秒，任务 cgroup 峰值 {number(test_peak,2)} GiB。Sharpe 按逐日收益样本标准差和 √252 年化；尚未扣除交易成本。</p></section>
<section id="ledger"><h2>固定预算与逐股账本</h2><p>账本共有 {len(positions):,} 条“日期 × 组合 × 股票”记录；每条记录带入选权重、进场状态、收益贡献、未退出时的估值时间。逐股贡献相加已与逐日 Long-Short 序列逐日核对，误差不超过 1e-12。</p>
<div class="table-scroll"><table><thead><tr><th>状态</th><th>记录数</th></tr></thead><tbody>{status_cells}</tbody></table></div>
<p><code>entry_unfilled</code> 是被选中但未进场的预算，收益为 0；<code>exited</code> 用出场窗口 VWAP；<code>open_marked</code> 保留未退出仓位，以窗口截止前最后一笔有效成交价估值。记录数是四个组合视图的合计，不是去重股票数。</p></section>
<section id="evidence"><h2>证据与解释边界</h2><p>业务运行 revision：<code>{html.escape(paths['business_revision'])}</code>。训练与测试源目录如下；源文件哈希保存在本页内嵌 JSON 和同目录 <code>report-data.json</code>，服务器各运行目录的 <code>evidence/SHA256SUMS</code> 另行校验。</p>
<p class="mono">训练：{html.escape(paths['train_run_root'])}<br>测试：{html.escape(paths['test_run_root'])}<br>旧试算摘要：{html.escape(paths['observational_baseline_root'])}/test_summary.json</p>
<p>按全时段行情确定的核尺度、深度尺度等参数沿用既有因子生产结果；本次没有重新计算全部因子或隔离这些参数的时间影响。test 日期已在旧报告中被观察过，因此此次修正后的 test 不能视为全新盲测。这里只执行第 15 折，未验证跨折稳定性；无交易费用、冲击、涨跌停成交容量、跨日持仓与真实卖出模拟。</p>
<details><summary>查看运行身份与输入哈希</summary><pre class="mono">{html.escape(json.dumps({'paths': paths, 'source_sha256': source_hashes}, ensure_ascii=False, indent=2))}</pre></details>
<a id="download-data" href="#">下载本页数据 JSON</a></section></main>
<script id="report-data" type="application/json">{embedded}</script>
<script>document.querySelector('#download-data').addEventListener('click',e=>{{e.preventDefault();const blob=new Blob([document.querySelector('#report-data').textContent],{{type:'application/json'}});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='model-report-2026-09-18-causal.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}})</script>
</body></html>'''
    ASSET.mkdir(parents=True, exist_ok=True)
    (ASSET / "report-data.json").write_text(json.dumps(safe(data), ensure_ascii=False, indent=2), encoding="utf-8")
    PAGE.write_text(page, encoding="utf-8")
    add_nav_scrollspy.patch(PAGE, add_nav_scrollspy.PAGES[PAGE.name])
    DAILY.write_text(f'''---
title: "328 因子模型复算：修正选股时点与未退出持仓估值"
date: 2026-09-18
stage: model
summary: "剔除 f97 买卖两列后，在 09:35 固定选股预算，并保留未在出场窗口成交的持仓估值；真实数据重新训练与 176 日 test 已完成。"
show_allow_downloads: true
---

# 328 因子模型复算

本次从服务器真实数据重新训练，test 日均 RankIC 为 **{number(metrics['mean_daily_rank_ic'],4)}**，多空毛 Sharpe 为 **{number(metrics['long_short_sharpe'],2)}**。训练按 validation 选第 **{selected}** 轮，test 不重新训练。

选股名单在 09:35 的因子候选池上确定；随后一分钟未成交的名额留作现金。出场窗口未成交的已进场股票保留在账本中，以 09:46 前最后一笔有效成交价估值。f97 买侧和卖侧均未进入 328 列输入。完整方法、逐日结果、账本状态和运行证据见本日报的展示版。

这是固定窗口毛估值序列，不是已平仓净值；未计交易成本，也未完成其他 14 折。旧试算已用同一 test 日期，本次复算不能作为新盲测，旧新结果也不能用于识别单项改动的因果效果。

RankIC 衡量全池排序，多空组合只交易两端。本次两腿有符号日收益相关系数为 **{number(leg_dependence['signed_leg_correlation'],3)}**，负协方差抵消两腿方差和的 **{pct(leg_dependence['covariance_variance_offset_fraction'])}**；这是高 Sharpe 的一个描述性来源，不是无泄漏证明。
''', encoding="utf-8")
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    result = make_report(args.input)
    print(json.dumps({"selected_iteration": result["selection"]["selected_iteration"],
                      "test_metrics": result["test_summary"]["overall_metrics"],
                      "page": str(PAGE)}, ensure_ascii=False))
