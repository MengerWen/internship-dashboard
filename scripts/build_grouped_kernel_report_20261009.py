"""Build the six-kernel interim report from sealed aggregate evidence."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSET = "assets/grouped-kernel-calibration-2026-10-09"
DATA = ROOT / "content" / ASSET
NAMES = {
    "theta_wall_seconds": "时间",
    "theta_events": "序号",
    "theta_qty": "数量",
    "theta_price_ticks": "价格",
    "theta_bbo_ticks": "BBO",
    "theta_marketability_ticks": "marketability",
}
FEATURES = {
    "model.activity_slim": "时间精简模型预测中心",
    "model.price_slim": "价格精简模型预测中心",
    "model.bbo_slim": "BBO精简模型预测中心",
    "log_trades_20d": "前20日成交笔数",
    "log_lots_per_trade_20d": "前20日单笔成交手数",
    "log_prev_close": "前收盘价",
}


def read_json(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def read_csv(name):
    with (DATA / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def table(headers, rows):
    def line(values):
        return "| " + " | ".join(str(x).replace("|", "\\|") for x in values) + " |"
    return "\n".join([line(headers), line(["---"] * len(headers)), *(line(row) for row in rows)])


def link(name, label):
    return f"[{label}]({ASSET}/{name})"


def main():
    source, result, manifest, seal = map(read_json, ["source.json", "RESULT.json", "run_manifest.json", "SEALED.json"])
    for entry in source["files"]:
        if hashlib.sha256((DATA / entry["path"]).read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"source hash mismatch: {entry['path']}")
    if result["status"] != "complete" or result["canary"] or not seal["sealed"]:
        raise ValueError("report requires a sealed full result")
    if result["date_count"] != 601 or result["stock_days"] != 1719612:
        raise ValueError("unexpected full-panel identity")
    if not all(result["acceptance"][key] is True for key in result["critical_checks"]):
        raise ValueError("critical acceptance is incomplete")
    pack = read_json("pack/grouped_kernel_scales_szse_v1.json")
    cells = read_csv("pack/cells.csv")
    complete = [row for row in cells if row["level"] == "cell"]
    if len(complete) != 94 or len(cells) != 155:
        raise ValueError("unexpected parameter inventory")
    shared = read_csv("acceptance/shared_centers.csv")
    model_rows = read_csv("models/coefficients.csv")
    models = {row["model"]: row for row in model_rows}
    errors = read_csv("acceptance/tracking_error.csv")
    fallback = read_csv("pack/fallback_usage.csv")
    support = read_csv("acceptance/support.csv")
    low = [row for row in support if row["level"] == "cell" and row["low_support"] == "True"]
    guard = read_json("evidence/guard_manifest.actual.json")
    elapsed = (datetime.fromisoformat(guard["end_ts"]) - datetime.fromisoformat(guard["start_ts"])).total_seconds()
    peak = result["guard"]["scope_memory_peak_bytes"] / 1024 ** 3
    sealed_local = datetime.fromisoformat(seal["sealed_at_utc"]).astimezone(timezone(timedelta(hours=8)))
    groups = table(["核", "股票层依据", "股票档×市场档", "完整单元"], [
        [NAMES[key], FEATURES[value["stock_layer"]["feature"]],
         f'{value["stock_layer"]["k"]}×{(value["market_layer"] or {}).get("k", 1)}',
         sum(row["kernel"] == key for row in complete)] for key, value in pack["kernels"].items()
    ])
    centers = table(["核", "正距离中心 m", "衰减尺度 θ=m/ln(2)", "与规格中心差值"], [
        [NAMES[row["kernel"]], row["m"], repr(float(row["m"]) / math.log(2)), row["difference"]] for row in shared
    ])
    fits = table(["模型", "全样本训练股票日", "股票数", "拟合秒数"], [
        [name, f'{int(row["train_stock_days"]):,}', row["train_stocks"], f'{float(row["fit_seconds"]):.3f}'] for name, row in models.items()
    ])
    tracking = table(["核", "深市共用", "只分股票层", "只分市场层", "完整方案"], [
        [NAMES[key], *[f'{float(next(row["stock_equal_mean_abs_log_error"] for row in errors if row["kernel"] == key and row["scenario"] == level)):.6f}' for level in ("shared", "stock_only", "market_only", "full")]] for key in NAMES
    ])
    usage = table(["核", "完整单元", "只分股票层", "只分市场层", "深市共用"], [
        [NAMES[key], *[f'{sum(int(row["stock_days"]) for row in fallback if row["kernel"] == key and row["level"] == level):,}' for level in ("cell", "stock_only", "market_only", "shared")]] for key in NAMES
    ])
    low_table = table(["核", "股票档", "市场档", "有效日", "股票日", "每日最少股票", "正配对数"], [
        [NAMES[row["kernel"]], row["stock_bucket"], row["market_bucket"], row["days"], row["stock_days"], row["stocks_per_day_min"], row["positive_pairs"]] for row in low
    ])
    stages = table(["阶段", "全量实测秒数"], [[key, f'{value["wall_seconds"]:.3f}'] for key, value in manifest["stages"].items()])
    theta_tables = []
    for key in NAMES:
        selected = [row for row in complete if row["kernel"] == key]
        markets = sorted({int(row["market_bucket"]) for row in selected})
        stocks = sorted({int(row["stock_bucket"]) for row in selected})
        lookup = {(int(row["stock_bucket"]), int(row["market_bucket"])): row["theta"] for row in selected}
        theta_tables.append(f'### {NAMES[key]}（{key}）\n\n' + table(["股票档", *[f"市场档 {market}" for market in markets]], [[stock, *[lookup[(stock, market)] for market in markets]] for stock in stocks]))
    title = "六核分组定标阶段成果：参数包已封存，正式计算待接入"
    date_note = f'本页归档日期为 **2026-10-09**，标签为 **interim**。全量封存实际时间为 **{sealed_local:%Y-%m-%d %H:%M:%S}（北京时间）**。'
    intro = f'深市六核参数包 `grouped_kernel_scales_szse_v1` 已完成 **601日、1,719,612个股票日、94个完整单元**的估计；含回退中心共155行。A1–A5、A9通过，参数和汇总证据已封存。\n\n{date_note}\n\n**当前成果是六核参数包。正式因子计算尚未接入这套分组尺度；结构参数处理和真实因子验收也未完成。**'
    why = """这次约16分钟的计时从已封存预检面板开始。前面已经从原始逐笔数据形成候选配对、计算距离，并生成每只股票每天的正距离中位数；本次复用这些结果，不重新取L2、查询Doris或米筐。

| 环节 | 状态 |
| --- | --- |
| 原始逐笔数据 → 股票日距离摘要与股票特征 | 前面的601日预检已完成，本次复用 |
| 已有面板 → 全样本模型、分组边界、六核参数包 | 本次完成 |
| 分组尺度 → 正式引擎、结构参数依赖与实际因子输出 | 尚待接入和验收 |

六核估计顺序为：股票日正距离中位数 → 同组当日跨股票中位数 → 跨交易日中位数m → θ=m/ln(2)。已有摘要保留了这一估计公式需要的信息。θ控制距离衰减；距离等于m时，指数核权重为0.5。它不保证每只股票恰好一半配对权重大于0.5。"""
    readiness = """1. 按股票日将模型预测、档位边界和四级回退接入正式引擎，并验证参数身份、缺失特征与重复边界等情况。
2. 落实时间尺度与回看、连边上限的联动，检查f16、f31、f40门限与θ40_L、λ40、λ42、f85、p03的依赖，明确哪些重新定标、哪些保留及理由。
3. 验证正式计算的每日米筐、日线和市场成交笔数输入，完成真实因子金丝雀的输出、计数、回归和资源验收，再决定全量计算。

本次没有完成因子重算、模型重训、IC或收益评价。同期间距离跟踪误差的改善不构成因子有效性或未来样本外表现的证明。"""
    downloads = "\n\n".join([
        link("pack/grouped_kernel_scales_szse_v1.json", "六核参数包：系数、特征、边界与回退规则"),
        link("pack/cells.csv", "全部155行中心、θ、支持量与分年中心（CSV）") + "；" + link("pack/cells.parquet", "同表Parquet"),
        link("models/coefficients.csv", "全样本模型系数") + "；" + link("models/coefficients_vs_precheck.csv", "与预检五折系数对照"),
        link("acceptance/tracking_error.csv", "四种方案的完整跟踪误差") + "；" + link("pack/fallback_usage.csv", "回退级别、原因与计数"),
        link("acceptance/support.csv", "单元支持量") + "；" + link("acceptance/annual_centers.csv", "2024、2025、2026H1分年中心"),
        link("RESULT.json", "计算验收") + "；" + link("SEALED.json", "封存记录") + "；" + link("source.json", "本页附件的来源与SHA-256清单"),
    ])
    body = f"""---
title: "{title}"
date: 2026-10-09
stage: algo-footprint
show_allow_downloads: true
summary: "interim：601日、171.96万股票日的六核分组参数包已封存；94个完整单元，三个模型全样本拟合，耗时16分14.6秒。正式引擎接入、结构参数处理和真实因子验收尚未完成。"
---

# {title}

{intro}

## 为什么这次只用了约16分钟

{why}

## 六个核的固定分组

{groups}

市场层使用前一日深市普通A股总成交笔数的log值。等频方案按股票等权取边界；预测值等距方案用股票等权的1%—99%预测分位区间切档。等于边界归低档，重复边界合并；完整数值保存在参数包。本次不重新选择档数。

## 全样本拟合与参数中心

{fits}

三个模型使用全部目标与特征均有限的股票日，按股票等权做中位数回归：quantile=0.5、alpha=0、highs-ipm，不抽样。三个进程并行，每个数值库内部线程为1。2日、61日运行用于测速；最终参数来自不限制日期的601日运行。

{centers}

六个深市共用中心与规格逐值相等；序号、数量和marketability的只分股票层中心与预检逐值相等。有模型方案中，价格最高股票档的中心由预检36.5 tick变为全样本37 tick，其余已列股票层中心相等；系数差异完整保存在附件。

## 跟踪误差、支持量与回退

逐日误差为|log(实际使用中心)−log(当日正值中位数)|，先对每只股票的有效日取均值，再对股票等权汇总。下表保留六位小数，附件保存完整精度；这与预检的股票留一长期偏差指标不同。

{tracking}

{usage}

六个核各解析1,719,612个股票日；每个股票日恰好使用一个级别。缺失股票特征使用只分市场层，没有市场层时使用深市共用；缺失市场特征使用只分股票层；空单元按规格回退。各级使用量之和守恒。

每天最少正值股票低于5的完整单元共{len(low)}个，只标记，不剔除：

{low_table}

分年中心和全部单元支持量随附件保存。稀疏支持和同期间误差需要与正式因子输出分开判断。

## 计算验收与性能

本地14项相关测试通过；A1输入身份、A2共用中心、A3无模型中心对照、A4计数守恒、A5市场边界嵌套、A9运行均通过。A6模型差异、A7支持量、A8跟踪误差按规格报告，不作为失败条件。市场2档边界与4档中间边界相等。

全量guard墙钟 **{elapsed:.3f}秒**，scope峰值内存 **{peak:.3f}GiB**。guard与sentinel退出码均为0，无新增OOM事件，无watchdog终止；launcher和计算子进程均退出。

{stages}

两轮金丝雀机械外推为499.392秒、31.137GiB；实际总耗时是外推的1.951倍。实测仍满足总墙钟60分钟、单模型40分钟、峰值60GiB的关卡。未改求解器、特征、档数或输出合同。

全量封存核对22个文件；全量加两轮金丝雀共64个回传文件哈希通过，CSV与Parquet参数表逐值一致。前段人工SSH采样存在超过50秒的间隔；随后约40秒间隔监控至guard退出。guard内存与watchdog覆盖整个scope，此执行限制随结果保留。

## 正式计算前仍需完成

{readiness}

## 全部完整单元的θ

档位从0开始。无市场层的核以市场档0表示；股票层、市场层和共用回退中心另见完整CSV。下表保持源文件精度。

{chr(10).join(theta_tables)}

## 参数与汇总证据下载

{downloads}

## 版本与复现位置

| 对象 | 版本 / SHA-256 |
| --- | --- |
| 科学定义版本 | `{pack['science_revision']}` |
| 业务执行版本（wangly已运行） | `{pack['execution_revision']}` |
| 研究证据归档commit | `{source['source_commit']}` |
| 配置SHA-256 | `{pack['config_sha256']}` |
| 预检面板SHA-256 | `{pack['panel_sha256']}` |

输入日期2024-01-02—2026-06-30。[原始结果报告]({source['source_repository']}/blob/{source['source_commit']}/{source['source_report']})。

服务器结果目录：

```text
{result['output_root']}
```

正式结果索引：

```text
/home/wangly/hdd-store/outputs/sirui/formal-results/grouped-kernel-scales-szse-v1
```

本页只发布聚合参数、模型系数、支持量和验收统计。原始L2、预检面板和逐股票日明细保留在服务器。wenjie未同步本次结果，未启动正式因子计算。
"""
    show = f"""---
title: "六核分组定标 · interim"
---

## 六核参数包已封存

{intro}

## 16分钟计算的是哪一段

{why}

## 六核分组与全样本模型

{groups}

{fits}

601日全样本拟合，不抽样；2日与61日仅用于测速。三个模型并行，最慢模型拟合922.278秒。

## 跟踪误差与支持量

{tracking}

误差先按股票取逐日绝对log误差均值，再跨股票等权汇总；只描述同期间距离中心的贴合程度。

{low_table}

该低支持单元按规格标记并保留。完整单元94个，含回退中心155行；六核各解析1,719,612个股票日，级别计数守恒。

## 验收与运行证据

14项测试通过，A1–A5与A9通过；全量guard墙钟{elapsed:.3f}秒，峰值{peak:.3f}GiB，无OOM或watchdog终止。输入哈希、计数和市场边界嵌套核对通过。

机械外推499.392秒，实测为其1.951倍；实测仍在关卡内。全量封存22个文件，含金丝雀的64个回传文件哈希通过。人工监控前段存在超过50秒的间隔，限制已记录。

## 正式因子计算仍待接入与验收

{readiness}

## 查看全部参数与汇总证据

{downloads}

业务执行版本`{pack['execution_revision'][:8]}`，科学版本`{pack['science_revision'][:8]}`。正文保留完整版本、全部94个完整单元的θ、计数、分年中心附件与复现位置。
"""
    daily = ROOT / "content/daily"
    (daily / "2026-10-09.md").write_text(body, encoding="utf-8")
    (daily / "2026-10-09.show.md").write_text(show, encoding="utf-8")
    print(json.dumps({"date": "2026-10-09", "complete_cells": len(complete), "all_rows": len(cells), "files_verified": len(source["files"]), "guard_seconds": elapsed}, ensure_ascii=False))


if __name__ == "__main__":
    main()
