from __future__ import annotations

import json
from pathlib import Path

import build_factor_report_20260801 as base


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_HTML = ROOT / "content" / "daily" / "2026-08-01.html"
EXPECTED_TEMPLATE_SHA256 = (
    "c53948749e8d63038646370f38b70d9a53fc47c41d5df4cfa7aa76650175a776"
)


def extract_template() -> tuple[Path, str, dict, object]:
    if base.sha256_file(TEMPLATE_HTML) != EXPECTED_TEMPLATE_SHA256:
        raise RuntimeError("the frozen 2026-08-01 explanatory template changed")
    html = TEMPLATE_HTML.read_text(encoding="utf-8")
    match = base.REPORT_DATA_RE.search(html)
    if match is None or len(base.REPORT_DATA_RE.findall(html)) != 1:
        raise RuntimeError("frozen template must contain exactly one report-data block")
    if html.count(base.INLINE_IMAGE_RUNTIME) != 1:
        raise RuntimeError("frozen template image runtime no longer matches")
    payload = json.loads(match.group(2))
    if len(payload.get("records", [])) != base.EXPECTED_RECORDS:
        raise RuntimeError("frozen template does not contain 165 records")
    if len(payload.get("ideas", [])) != base.EXPECTED_IDEAS:
        raise RuntimeError("frozen template does not contain 55 ideas")
    return TEMPLATE_HTML, html, payload, match


def update_visible_facts(prefix: str, facts: dict) -> str:
    start = facts["actual_start"]
    end = facts["actual_end"]
    days = facts["trading_days"]
    source = facts["source"]
    replacements = [
        (
            "真实评估：2026-03-30 至 2026-07-16，共 72 个交易日",
            f"真实评估：{start} 至 {end}，共 {days} 个交易日",
            "hero evaluation interval",
        ),
        (
            '<span>数值有效口径</span><b>162</b>',
            f'<span>数值有效口径</span><b>{facts["valid_records"]}</b>',
            "valid record count",
        ),
        (
            "<div><b>04 · 锁定后评估</b>2026 年 3 月 30 日至2026 年 7 月 16 日只读取冻结值，不重新估计参数。</div>",
            "<div><b>04 · 固定参数历史评估</b>2026 年 1 月 5 日至2026 年 7 月 31 日统一读取冻结值，不重新估计参数；校准日前属于回溯计算。</div>",
            "parameter flow evaluation dates",
        ),
        (
            '<tr><td>日期切分</td><td><span class="origin human">人为冻结</span> 校准 03-23 至 03-27；评估 03-30 至 07-16</td><td>前三个校准日用于估计，后两个校准日用于稳定性检查；评估期与校准期完全分离。</td><td>否；评估开始后不滚动重估。</td></tr>',
            '<tr><td>日期切分</td><td><span class="origin human">人为冻结</span> 校准 03-23 至 03-27；评估 01-05 至 07-31（排除校准日与证据不完整日）</td><td>评估不使用校准期标签重估参数；校准日前区间是固定参数回溯，不是纯样本外。</td><td>否；评估期间不滚动重估。</td></tr>',
            "parameter table evaluation dates",
        ),
        (
            "跨三项都进入“思路并和 Top 20”的 13 条更适合作为第一轮候选池。",
            f"跨三项都进入“思路并和 Top 20”的 {facts['overlap_count']} 条更适合作为第一轮候选池。",
            "top-20 overlap count",
        ),
        (
            "<dt>区间扩展控制 / 执行 revision</dt><dd>9fa7ed90269486db8939209aceb19c846ae168f3（只用于区间扩展、报告和验证控制；Notebook metadata 的 business_revision 仍为上项）</dd>",
            f'<dt>固定参数历史评估控制 / 执行 revision</dt><dd>{source["execution_revision"]}（只用于历史区间扩展、报告和验证控制；Notebook metadata 的 business_revision 仍为上项）</dd>',
            "execution revision audit",
        ),
        (
            "<dt>当前量化仓库本地 HEAD</dt><dd>9fa7ed90269486db8939209aceb19c846ae168f3；区间合同明确记录 business_semantics_changed=false，因子定义沿用业务 revision。</dd>",
            f'<dt>当前量化仓库本地 HEAD</dt><dd>{source["current_local_head"]}；区间合同明确记录 business_semantics_changed=false，因子定义沿用业务 revision。</dd>',
            "local revision audit",
        ),
        (
            "<dt>运行结果</dt><dd>expected=generated=executed=165，failed=0；72 个交易日，208,154 个股票日面板行；每日约 2,799–2,891 只股票。</dd>",
            '<dt>运行结果</dt><dd>expected=generated=executed=165，failed=0；'
            f'{days} 个交易日，{facts["panel_sample_count"]:,} 个股票日面板行；'
            f'每日约 {facts["daily_min"]:,}–{facts["daily_max"]:,} 只股票。</dd>',
            "run result audit",
        ),
        (
            "<dt>Notebook archive SHA256</dt><dd>e28e781460b37e6b7cda6d544d1efb9dc753dccdb525db91881df7f92a6b4bb0</dd>",
            f'<dt>Notebook archive SHA256</dt><dd>{source["notebook_archive_sha256"]}</dd>',
            "notebook archive audit",
        ),
        (
            "<dt>提取数据 SHA256</dt><dd>24b424e10863dab6f52c5ddab0e78793e540d12a4ef98bf22cb7b40293b3906b</dd>",
            f'<dt>提取数据 SHA256</dt><dd>{source["notebook_data_sha256"]}</dd>',
            "notebook data audit",
        ),
        (
            "<dt>区间汇总指标 CSV SHA256</dt><dd>0a99a86e72dd2d62eb6313140b9461607d8a4f607fd97d61d07f19884feb5389</dd>",
            f'<dt>区间汇总指标 CSV SHA256</dt><dd>{source["interval_metrics_sha256"]}</dd>',
            "ranking evidence audit",
        ),
        (
            "<dt>区间合同 SHA256</dt><dd>582909cd936efacd425f4f41abfdc949a0deca49a4fb7314b324b8e80ab04226</dd>",
            f'<dt>区间合同 SHA256</dt><dd>{source["interval_contract_sha256"]}</dd>',
            "interval contract audit",
        ),
        (
            "<dt>正确性结论</dt><dd>Notebook 清单、业务列、指标字段和四图数量完整对齐；这里没有重新跑业务面板，也没有把探索结果自动判成“有效/无效”。</dd>",
            "<dt>正确性结论</dt><dd>Notebook 清单、业务列、指标字段和四图数量完整对齐；这里没有重新跑业务面板，也没有把探索结果自动判成“有效/无效”。本次是固定参数历史评估，校准日前区间属于回溯计算而非纯样本外。</dd>",
            "evaluation nature audit",
        ),
    ]
    for old, new, label in replacements:
        prefix = base.replace_once(prefix, old, new, label)
    return prefix


def build_self_contained(template_html: str, match, payload: dict, facts: dict) -> str:
    prefix = update_visible_facts(template_html[: match.start(2)], facts)
    return prefix + base.serialize_payload(payload) + template_html[match.end(2) :]


def main() -> None:
    base.SELF_CONTAINED_HTML = ROOT / "content" / "daily" / "2026-08-02.html"
    base.WEBSITE_HTML = ROOT / "content" / "daily" / "2026-08-02.show.html"
    base.ASSET_DIR = ROOT / "content" / "assets" / "factor-report-2026-08-02"
    base.ASSET_URL_PREFIX = "assets/factor-report-2026-08-02"
    base.ASSET_MANIFEST = base.ASSET_DIR / "manifest.json"
    base.extract_template = extract_template
    base.update_visible_facts = update_visible_facts
    base.build_self_contained = build_self_contained
    base.main()


if __name__ == "__main__":
    main()
