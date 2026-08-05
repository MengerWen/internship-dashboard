from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import build_factor_report_20260801 as base


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_HTML = ROOT / "content" / "daily" / "2026-08-02.html"
EXPECTED_TEMPLATE_SHA256 = (
    "23891297d19a4986778ae8d089211c765ddf21f59e7f23894ee19d53abcab18a"
)


def extract_template() -> tuple[Path, str, dict, object]:
    if base.sha256_file(TEMPLATE_HTML) != EXPECTED_TEMPLATE_SHA256:
        raise RuntimeError("the frozen 2026-08-02 explanatory template changed")
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


def load_evidence(source_root: Path) -> dict[str, Any]:
    """Load both the original and the independently accepted report schemas."""
    paths = {
        "contract": source_root / "INTERVAL_CONTRACT.json",
        "result": source_root / "INTERVAL_REPORT_RESULT.json",
        "resume": source_root / "INTRADAY_INTERVAL_RESUME_RESULT.json",
        "archive": source_root / "formal_notebooks.tar.gz",
        "metrics": source_root / "ALL_PERIOD_FACTOR_METRICS.csv",
        "notebooks": source_root / "extracted" / "notebooks",
    }
    for label, path in paths.items():
        if not path.exists():
            raise FileNotFoundError(f"missing {label} evidence: {path}")
    manifest_path = paths["notebooks"] / "NOTEBOOK_EXECUTION_MANIFEST.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"missing notebook manifest: {manifest_path}")

    contract = base.read_json(paths["contract"])
    result = base.read_json(paths["result"])
    resume = base.read_json(paths["resume"])
    manifest = base.read_json(manifest_path)
    if contract.get("status") != "accepted":
        raise RuntimeError("interval contract is not accepted")
    if contract.get("business_semantics_changed") is not False:
        raise RuntimeError("business semantics changed; frozen explanations cannot be reused")
    if contract.get("parameter_recalibration") is not False:
        raise RuntimeError("parameters were recalibrated; frozen interpretation cannot be reused")
    if contract.get("factor_selection") is not False:
        raise RuntimeError("factor selection occurred during the evaluation")
    if result.get("status") != "complete" or result.get("factor_count") != base.EXPECTED_RECORDS:
        raise RuntimeError("interval report is not a complete 165-factor result")
    if resume.get("status") != "complete":
        raise RuntimeError("interval resume result is not complete")
    if manifest.get("status") != "complete":
        raise RuntimeError("notebook execution manifest is not complete")
    for key in ("expected", "generated", "executed"):
        if manifest.get(key) != base.EXPECTED_RECORDS:
            raise RuntimeError(f"notebook manifest {key} != {base.EXPECTED_RECORDS}")
    if manifest.get("failed") != 0:
        raise RuntimeError("notebook manifest contains failures")

    business_revisions = {
        contract.get("business_revision"),
        resume.get("business_revision"),
        manifest.get("revision"),
    }
    if len(business_revisions) != 1 or None in business_revisions:
        raise RuntimeError(f"business revision mismatch: {business_revisions}")
    execution_revision = resume.get("execution_revision")
    provenance = manifest.get("revision_provenance", {})
    if not execution_revision or provenance.get("execution_revision") != execution_revision:
        raise RuntimeError("execution revision provenance mismatch")
    if provenance.get("control_revision") != resume.get("control_revision"):
        raise RuntimeError("control revision provenance mismatch")

    result_files = result.get("files", {})
    metric_file = result_files.get("all_period_csv") or result_files.get(
        "all_period_factor_metrics_csv"
    )
    if not metric_file:
        raise RuntimeError("interval report does not declare the all-period metric CSV")
    expected_hashes = {
        paths["contract"]: resume["interval_contract"]["sha256"],
        paths["result"]: resume["interval_report"]["sha256"],
        paths["archive"]: resume["notebook_archive"]["sha256"],
        manifest_path: resume["notebooks"]["sha256"],
        paths["metrics"]: metric_file["sha256"],
    }
    for path, expected in expected_hashes.items():
        actual = base.sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"evidence hash mismatch for {path}: {actual} != {expected}")

    with paths["metrics"].open(encoding="utf-8-sig", newline="") as handle:
        metric_rows = list(csv.DictReader(handle))
    if len(metric_rows) != base.EXPECTED_RECORDS:
        raise RuntimeError("all-period metric CSV does not contain 165 rows")
    if {row.get("period") for row in metric_rows} != {"full_2025_to_2026-07-31"}:
        raise RuntimeError("all-period metric CSV is not the requested full-history period")
    return {
        "paths": paths,
        "manifest_path": manifest_path,
        "contract": contract,
        "result": result,
        "resume": resume,
        "manifest": manifest,
        "metric_by_record": {row["record_id"]: row for row in metric_rows},
    }


def update_visible_facts(prefix: str, facts: dict) -> str:
    start = facts["actual_start"]
    end = facts["actual_end"]
    days = facts["trading_days"]
    source = facts["source"]
    replacements = [
        (
            "真实评估：2026-01-05 至 2026-07-31，共 131 个交易日",
            f"真实评估：{start} 至 {end}，共 {days} 个交易日",
            "hero evaluation interval",
        ),
        (
            '<span>数值有效口径</span><b>162</b>',
            f'<span>数值有效口径</span><b>{facts["valid_records"]}</b>',
            "valid record count",
        ),
        (
            "<div><b>04 · 固定参数历史评估</b>2026 年 1 月 5 日至2026 年 7 月 31 日统一读取冻结值，不重新估计参数；校准日前属于回溯计算。</div>",
            "<div><b>04 · 固定参数历史评估</b>2025 年 1 月 2 日至 2026 年 7 月 31 日统一读取冻结值，不重新估计参数；校准日前属于回溯计算。</div>",
            "parameter flow evaluation dates",
        ),
        (
            '<tr><td>日期切分</td><td><span class="origin human">人为冻结</span> 校准 03-23 至 03-27；评估 01-05 至 07-31（排除校准日与证据不完整日）</td><td>评估不使用校准期标签重估参数；校准日前区间是固定参数回溯，不是纯样本外。</td><td>否；评估期间不滚动重估。</td></tr>',
            '<tr><td>日期切分</td><td><span class="origin human">人为冻结</span> 校准 2026-03-23 至 2026-03-27；评估 2025-01-02 至 2026-07-31（排除校准日与证据不完整日）</td><td>评估不使用校准期标签重估参数；校准日前区间是固定参数回溯，不是纯样本外。</td><td>否；评估期间不滚动重估。</td></tr>',
            "parameter table evaluation dates",
        ),
        (
            "跨三项都进入“思路并和 Top 20”的 10 条更适合作为第一轮候选池。",
            f"跨三项都进入“思路并和 Top 20”的 {facts['overlap_count']} 条更适合作为第一轮候选池。",
            "top-20 overlap count",
        ),
        (
            "<dt>固定参数历史评估控制 / 执行 revision</dt><dd>38d654851299190be3fb487e5017d74d1598ebeb（只用于历史区间扩展、报告和验证控制；Notebook metadata 的 business_revision 仍为上项）</dd>",
            f'<dt>固定参数历史评估执行 revision</dt><dd>{source["execution_revision"]}；控制 revision {source["control_revision"]}（只用于历史区间扩展、报告和验证控制；Notebook metadata 的 business_revision 仍为上项）</dd>',
            "execution revision audit",
        ),
        (
            "<dt>当前量化仓库本地 HEAD</dt><dd>38d654851299190be3fb487e5017d74d1598ebeb；区间合同明确记录 business_semantics_changed=false，因子定义沿用业务 revision。</dd>",
            f'<dt>当前量化仓库本地 HEAD</dt><dd>{source["current_local_head"]}；区间合同明确记录 business_semantics_changed=false，因子定义沿用业务 revision。</dd>',
            "local revision audit",
        ),
        (
            "<dt>运行结果</dt><dd>expected=generated=executed=165，failed=0；131 个交易日，378,366 个股票日面板行；每日约 2,799–2,891 只股票。</dd>",
            '<dt>运行结果</dt><dd>expected=generated=executed=165，failed=0；'
            f'{days} 个交易日，{facts["panel_sample_count"]:,} 个股票日面板行；'
            f'每日约 {facts["daily_min"]:,}–{facts["daily_max"]:,} 只股票。</dd>',
            "run result audit",
        ),
        (
            "<dt>Notebook archive SHA256</dt><dd>f1c22731b87f5f205b836f0f2f69b432ba8e5f9b5ed95e067facfeb8ba850429</dd>",
            f'<dt>Notebook archive SHA256</dt><dd>{source["notebook_archive_sha256"]}</dd>',
            "notebook archive audit",
        ),
        (
            "<dt>提取数据 SHA256</dt><dd>99f9f4fd25e106ad498b1752a77c27208562a8f3baa9236d1ac72543ec01956b</dd>",
            f'<dt>提取数据 SHA256</dt><dd>{source["notebook_data_sha256"]}</dd>',
            "notebook data audit",
        ),
        (
            "<dt>区间汇总指标 CSV SHA256</dt><dd>a39adfa92287c4a63dce085be07b808359df02f15beb8257d5cfe271b10495f7</dd>",
            f'<dt>区间汇总指标 CSV SHA256</dt><dd>{source["interval_metrics_sha256"]}</dd>',
            "ranking evidence audit",
        ),
        (
            "<dt>区间合同 SHA256</dt><dd>fba67c067a224a0e385981f241cc51c5cc8af0a68c2b291ac385c86a1c5d5579</dd>",
            f'<dt>区间合同 SHA256</dt><dd>{source["interval_contract_sha256"]}</dd>',
            "interval contract audit",
        ),
    ]
    for old, new, label in replacements:
        prefix = base.replace_once(prefix, old, new, label)
    return prefix


def build_self_contained(template_html: str, match, payload: dict, facts: dict) -> str:
    prefix = update_visible_facts(template_html[: match.start(2)], facts)
    return prefix + base.serialize_payload(payload) + template_html[match.end(2) :]


def main() -> None:
    base.SELF_CONTAINED_HTML = ROOT / "content" / "daily" / "2026-08-04.html"
    base.WEBSITE_HTML = ROOT / "content" / "daily" / "2026-08-04.show.html"
    base.ASSET_DIR = ROOT / "content" / "assets" / "factor-report-2026-08-04"
    base.ASSET_URL_PREFIX = "assets/factor-report-2026-08-04"
    base.ASSET_MANIFEST = base.ASSET_DIR / "manifest.json"
    base.extract_template = extract_template
    base.load_evidence = load_evidence
    base.update_visible_facts = update_visible_facts
    base.build_self_contained = build_self_contained
    base.main()


if __name__ == "__main__":
    main()
