from __future__ import annotations

import argparse
import base64
import copy
import csv
import hashlib
import json
import math
import re
import statistics
import struct
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "artifacts" / "factor-report-2026-07-31"
SELF_CONTAINED_HTML = ROOT / "content" / "daily" / "2026-08-01.html"
WEBSITE_HTML = ROOT / "content" / "daily" / "2026-08-01.show.html"
ASSET_DIR = ROOT / "content" / "assets" / "factor-report-2026-08-01"
ASSET_URL_PREFIX = "assets/factor-report-2026-08-01"
ASSET_MANIFEST = ASSET_DIR / "manifest.json"
CLOUDFLARE_SINGLE_ASSET_LIMIT = 25 * 1024 * 1024
EXPECTED_RECORDS = 165
EXPECTED_IDEAS = 55
EXPECTED_IMAGES_PER_NOTEBOOK = 4
REPORT_DATA_RE = re.compile(
    r'(<script id="report-data" type="application/json">)(.*?)(</script>)',
    flags=re.DOTALL,
)
INLINE_IMAGE_RUNTIME = "img.src='data:image/png;base64,'+im.data;"
WEBSITE_IMAGE_RUNTIME = "img.src=im.url||('data:image/png;base64,'+im.data);"
METRICS = {
    "ic": "mean_pearson",
    "rank_ic": "mean_ic",
    "icir": "icir_raw",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def text_value(value: str | list[str] | None) -> str | None:
    if value is None:
        return None
    return "".join(value) if isinstance(value, list) else value


def scalar(value: str) -> int | float | str | None:
    value = value.strip()
    if value in {"", "NaN", "nan", "None"}:
        return None
    try:
        number = float(value)
    except ValueError:
        return value
    return int(number) if number.is_integer() else number


class TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table_depth = 0
        self._rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if tag == "table":
            self._table_depth += 1
            if self._table_depth == 1:
                self._rows = []
        elif self._table_depth == 1 and tag == "tr":
            self._row = []
        elif self._table_depth == 1 and tag in {"th", "td"}:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._table_depth == 1 and tag in {"th", "td"}:
            if self._row is None or self._cell is None:
                raise RuntimeError("malformed notebook HTML table cell")
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif self._table_depth == 1 and tag == "tr":
            if self._row:
                self._rows.append(self._row)
            self._row = None
        elif tag == "table":
            if self._table_depth == 1:
                self.tables.append(self._rows)
            self._table_depth -= 1


def parse_html_table(html: str) -> tuple[list[str], list[dict[str, Any]]]:
    parser = TableParser()
    parser.feed(html)
    if len(parser.tables) != 1 or not parser.tables[0]:
        raise RuntimeError("expected one HTML table per notebook table output")
    header = parser.tables[0][0]
    rows: list[dict[str, Any]] = []
    for values in parser.tables[0][1:]:
        if len(values) != len(header):
            raise RuntimeError(
                f"notebook HTML table width mismatch: {len(values)} != {len(header)}"
            )
        rows.append(dict(zip(header, (scalar(value) for value in values))))
    return header, rows


def find_table(
    tables: list[tuple[list[str], list[dict[str, Any]]]],
    required: set[str],
    alias: str,
) -> list[dict[str, Any]]:
    matches = [rows for header, rows in tables if required <= set(header)]
    if len(matches) != 1:
        headers = [header for header, _ in tables]
        raise RuntimeError(
            f"{alias}: expected one table with {sorted(required)}, found headers={headers}"
        )
    return matches[0]


def png_dimensions(data: bytes) -> tuple[int, int]:
    if not data.startswith(b"\x89PNG\r\n\x1a\n") or data[12:16] != b"IHDR":
        raise RuntimeError("decoded notebook image is not a PNG with an IHDR chunk")
    return struct.unpack(">II", data[16:24])


def finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one replacement target, found {count}")
    return text.replace(old, new, 1)


def extract_template() -> tuple[Path, str, dict[str, Any], re.Match[str]]:
    sources = list(TEMPLATE_DIR.glob("*.current.self-contained.html"))
    if len(sources) != 1:
        raise RuntimeError(f"expected one frozen self-contained template: {sources}")
    source = sources[0]
    html = source.read_text(encoding="utf-8")
    match = REPORT_DATA_RE.search(html)
    if match is None or len(REPORT_DATA_RE.findall(html)) != 1:
        raise RuntimeError("frozen template must contain exactly one report-data block")
    if html.count(INLINE_IMAGE_RUNTIME) != 1:
        raise RuntimeError("frozen template image runtime no longer matches")
    payload = json.loads(match.group(2))
    if len(payload.get("records", [])) != EXPECTED_RECORDS:
        raise RuntimeError("frozen template does not contain 165 records")
    if len(payload.get("ideas", [])) != EXPECTED_IDEAS:
        raise RuntimeError("frozen template does not contain 55 ideas")
    return source, html, payload, match


def load_evidence(source_root: Path) -> dict[str, Any]:
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

    contract = read_json(paths["contract"])
    result = read_json(paths["result"])
    resume = read_json(paths["resume"])
    manifest = read_json(manifest_path)
    if contract.get("status") != "accepted":
        raise RuntimeError("interval contract is not accepted")
    if contract.get("business_semantics_changed") is not False:
        raise RuntimeError("business semantics changed; frozen explanations cannot be reused")
    if result.get("status") != "complete" or result.get("factor_count") != EXPECTED_RECORDS:
        raise RuntimeError("interval report is not a complete 165-factor result")
    if resume.get("status") != "complete":
        raise RuntimeError("interval resume result is not complete")
    if manifest.get("status") != "complete":
        raise RuntimeError("notebook execution manifest is not complete")
    for key in ("expected", "generated", "executed"):
        if manifest.get(key) != EXPECTED_RECORDS:
            raise RuntimeError(f"notebook manifest {key} != {EXPECTED_RECORDS}")
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

    expected_hashes = {
        paths["contract"]: resume["interval_contract"]["sha256"],
        paths["result"]: resume["interval_report"]["sha256"],
        paths["archive"]: resume["notebook_archive"]["sha256"],
        manifest_path: resume["notebooks"]["sha256"],
        paths["metrics"]: result["files"]["all_period_csv"]["sha256"],
    }
    for path, expected in expected_hashes.items():
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"evidence hash mismatch for {path}: {actual} != {expected}")

    with paths["metrics"].open(encoding="utf-8-sig", newline="") as handle:
        metric_rows = list(csv.DictReader(handle))
    if len(metric_rows) != EXPECTED_RECORDS:
        raise RuntimeError("all-period metric CSV does not contain 165 rows")
    return {
        "paths": paths,
        "manifest_path": manifest_path,
        "contract": contract,
        "result": result,
        "resume": resume,
        "manifest": manifest,
        "metric_by_record": {row["record_id"]: row for row in metric_rows},
    }


def parse_notebook(
    path: Path,
    relative_path: str,
    old_record: dict[str, Any],
    manifest_entry: dict[str, Any],
    metric_row: dict[str, str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    notebook = read_json(path)
    metadata = notebook.get("metadata", {}).get("sirui", {})
    alias = metadata.get("short_alias")
    if alias != old_record["short_alias"]:
        raise RuntimeError(f"notebook alias mismatch at {relative_path}: {alias}")
    for key in ("record_id", "formal_column", "specification_id", "base_logic"):
        if metadata.get(key) != old_record[key]:
            raise RuntimeError(f"{alias}: frozen {key} changed")
    if manifest_entry.get("relative_path") != relative_path:
        raise RuntimeError(f"{alias}: manifest relative path mismatch")
    actual_notebook_hash = sha256_file(path)
    if actual_notebook_hash != manifest_entry.get("sha256"):
        raise RuntimeError(f"{alias}: notebook hash mismatch")

    tables: list[tuple[list[str], list[dict[str, Any]]]] = []
    encoded_images: list[str] = []
    for cell in notebook.get("cells", []):
        for output in cell.get("outputs", []):
            data = output.get("data", {})
            html = text_value(data.get("text/html"))
            if html:
                tables.append(parse_html_table(html))
            image = text_value(data.get("image/png"))
            if image:
                encoded_images.append(image)

    summary_row = find_table(
        tables, {"n_days", "mean_ic", "icir_raw", "mean_pearson"}, alias
    )[0]
    availability_row = find_table(
        tables,
        {"factor_sample_count", "panel_sample_count", "factor_coverage"},
        alias,
    )[0]
    diagnostic_rows = find_table(tables, {"metric", "mean", "min", "max"}, alias)
    diagnostics_by_name = {
        str(row["metric"]): {
            "mean": row["mean"],
            "min": row["min"],
            "max": row["max"],
        }
        for row in diagnostic_rows
    }

    summary = {key: summary_row[key] for key in old_record["summary"]}
    availability = {
        key: availability_row[key] for key in old_record["availability"]
    }
    diagnostics = {
        key: diagnostics_by_name[key] for key in old_record["diagnostics"]
    }
    csv_rank_ic = metric_row.get("mean_rank_ic", "")
    csv_rank_value = None if csv_rank_ic == "" else float(csv_rank_ic)
    notebook_rank_value = summary["mean_ic"]
    if (csv_rank_value is None) != (notebook_rank_value is None):
        raise RuntimeError(f"{alias}: interval CSV and notebook Rank_IC null mismatch")
    if csv_rank_value is not None and not math.isclose(
        csv_rank_value,
        float(notebook_rank_value),
        rel_tol=0,
        abs_tol=5e-7,
    ):
        raise RuntimeError(f"{alias}: interval CSV and notebook Rank_IC mismatch")

    if len(encoded_images) != EXPECTED_IMAGES_PER_NOTEBOOK:
        raise RuntimeError(
            f"{alias}: expected four PNG outputs, found {len(encoded_images)}"
        )
    images: list[dict[str, Any]] = []
    image_hashes: list[str] = []
    for old_image, encoded in zip(old_record["images"], encoded_images):
        raw = base64.b64decode(encoded, validate=True)
        width, height = png_dimensions(raw)
        image_hashes.append(sha256_bytes(raw))
        images.append(
            {
                "name": old_image["name"],
                "data": encoded,
                "width": width,
                "height": height,
            }
        )

    new_record = copy.deepcopy(old_record)
    new_record["notebook_sha256"] = actual_notebook_hash
    new_record["summary"] = summary
    new_record["availability"] = availability
    new_record["diagnostics"] = diagnostics
    new_record["images"] = images
    evidence = {
        "short_alias": alias,
        "record_id": old_record["record_id"],
        "notebook_relative_path": relative_path,
        "notebook_sha256": actual_notebook_hash,
        "summary": summary,
        "availability": availability,
        "diagnostics": diagnostics,
        "image_sha256": image_hashes,
    }
    return new_record, evidence


def ranked_ids(items: list[dict[str, Any]], value_key: str, id_key: str) -> list[str]:
    valid = [item for item in items if finite(item[value_key])]
    return [
        item[id_key]
        for item in sorted(
            valid,
            key=lambda item: (-float(item[value_key]), str(item[id_key])),
        )[:20]
    ]


def refresh_payload(
    old_payload: dict[str, Any],
    evidence: dict[str, Any],
    quant_local_head: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    notebook_root = evidence["paths"]["notebooks"]
    old_by_alias = {record["short_alias"]: record for record in old_payload["records"]}
    manifest_entries = {
        entry["relative_path"]: entry for entry in evidence["manifest"]["notebooks"]
    }
    if len(manifest_entries) != EXPECTED_RECORDS:
        raise RuntimeError("notebook manifest entry count is not 165")

    paths = sorted(notebook_root.rglob("*.ipynb"))
    if len(paths) != EXPECTED_RECORDS:
        raise RuntimeError(f"expected 165 notebooks, found {len(paths)}")
    new_by_alias: dict[str, dict[str, Any]] = {}
    extracted_evidence: list[dict[str, Any]] = []
    business_revisions: set[str] = set()
    for path in paths:
        relative_path = path.relative_to(notebook_root).as_posix()
        notebook = read_json(path)
        metadata = notebook.get("metadata", {}).get("sirui", {})
        alias = metadata.get("short_alias")
        if alias not in old_by_alias:
            raise RuntimeError(f"unexpected new notebook alias: {alias}")
        business_revisions.add(metadata.get("business_revision"))
        record, record_evidence = parse_notebook(
            path,
            relative_path,
            old_by_alias[alias],
            manifest_entries[relative_path],
            evidence["metric_by_record"][old_by_alias[alias]["record_id"]],
        )
        if alias in new_by_alias:
            raise RuntimeError(f"duplicate notebook alias: {alias}")
        new_by_alias[alias] = record
        extracted_evidence.append(record_evidence)

    if set(new_by_alias) != set(old_by_alias):
        raise RuntimeError(
            f"alias mismatch missing={sorted(set(old_by_alias)-set(new_by_alias))} "
            f"extra={sorted(set(new_by_alias)-set(old_by_alias))}"
        )
    business_revision = evidence["contract"]["business_revision"]
    if business_revisions != {business_revision}:
        raise RuntimeError(f"notebook business revision mismatch: {business_revisions}")

    payload = copy.deepcopy(old_payload)
    payload["generated_at"] = evidence["resume"]["created_at"]
    payload["records"] = [
        new_by_alias[record["short_alias"]] for record in old_payload["records"]
    ]
    record_map = {record["short_alias"]: record for record in payload["records"]}

    for idea in payload["ideas"]:
        variants = [record_map[alias] for alias in idea["variant_aliases"]]
        averages: dict[str, float | None] = {}
        best: dict[str, list[str]] = {}
        for metric_name, record_key in METRICS.items():
            values = [
                (record["short_alias"], record["summary"][record_key])
                for record in variants
                if finite(record["summary"][record_key])
            ]
            averages[metric_name] = (
                statistics.fmean(float(value) for _, value in values)
                if values
                else None
            )
            if values:
                maximum = max(float(value) for _, value in values)
                best[metric_name] = [
                    alias for alias, value in values if float(value) == maximum
                ]
            else:
                best[metric_name] = []
        idea["averages"] = averages
        idea["best"] = best

    metric_stats: dict[str, dict[str, Any]] = {}
    for metric_name, record_key in METRICS.items():
        values = [
            float(record["summary"][record_key])
            for record in payload["records"]
            if finite(record["summary"][record_key])
        ]
        metric_stats[metric_name] = {
            "n": len(values),
            "positive": sum(value > 0 for value in values),
            "negative": sum(value < 0 for value in values),
            "mean": statistics.fmean(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
        }
    payload["metric_stats"] = metric_stats

    factor_rows = [
        {
            "short_alias": record["short_alias"],
            **{
                metric_name: record["summary"][record_key]
                for metric_name, record_key in METRICS.items()
            },
        }
        for record in payload["records"]
    ]
    idea_rows = [
        {"idea_id": idea["idea_id"], **idea["averages"]}
        for idea in payload["ideas"]
    ]
    payload["top_factor"] = {
        metric_name: ranked_ids(factor_rows, metric_name, "short_alias")
        for metric_name in METRICS
    }
    payload["top_idea"] = {
        metric_name: ranked_ids(idea_rows, metric_name, "idea_id")
        for metric_name in METRICS
    }
    payload["top20_overlap"] = sorted(
        set(payload["top_idea"]["ic"])
        & set(payload["top_idea"]["rank_ic"])
        & set(payload["top_idea"]["icir"])
    )

    notebook_data = json.dumps(
        sorted(extracted_evidence, key=lambda item: item["short_alias"]),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    source = {
        "business_revision": business_revision,
        "execution_revision": evidence["resume"]["execution_revision"],
        "control_revision": evidence["resume"]["control_revision"],
        "current_local_head": quant_local_head,
        "notebook_archive_sha256": sha256_file(evidence["paths"]["archive"]),
        "notebook_data_sha256": sha256_bytes(notebook_data),
        "interval_contract_sha256": sha256_file(evidence["paths"]["contract"]),
        "interval_metrics_sha256": sha256_file(evidence["paths"]["metrics"]),
        "server_notebook_root": evidence["resume"]["notebooks"]["official_root"],
    }
    payload["source"] = source

    valid_day_counts = {
        int(record["summary"]["n_days"])
        for record in payload["records"]
        if int(record["summary"]["n_days"] or 0) > 0
    }
    if valid_day_counts != {int(evidence["contract"]["trading_date_count"])}:
        raise RuntimeError(f"notebook trading-day mismatch: {valid_day_counts}")
    panel_counts = {
        int(record["availability"]["panel_sample_count"])
        for record in payload["records"]
    }
    if len(panel_counts) != 1:
        raise RuntimeError(f"panel sample counts differ across notebooks: {panel_counts}")
    daily_min = min(int(record["diagnostics"]["n"]["min"]) for record in payload["records"])
    daily_max = max(int(record["diagnostics"]["n"]["max"]) for record in payload["records"])
    facts = {
        "actual_start": evidence["contract"]["actual_start"],
        "actual_end": evidence["contract"]["actual_end"],
        "trading_days": next(iter(valid_day_counts)),
        "valid_records": metric_stats["ic"]["n"],
        "panel_sample_count": next(iter(panel_counts)),
        "daily_min": daily_min,
        "daily_max": daily_max,
        "overlap_count": len(payload["top20_overlap"]),
        "source": source,
    }
    return payload, facts


def chinese_date(iso_date: str) -> str:
    year, month, day = (int(part) for part in iso_date.split("-"))
    return f"{year} 年 {month} 月 {day} 日"


def update_visible_facts(prefix: str, facts: dict[str, Any]) -> str:
    start = facts["actual_start"]
    end = facts["actual_end"]
    days = facts["trading_days"]
    source = facts["source"]
    prefix = replace_once(
        prefix,
        "真实评估：2026-04-01 至 2026-06-30，共 60 个交易日",
        f"真实评估：{start} 至 {end}，共 {days} 个交易日",
        "hero evaluation interval",
    )
    prefix = replace_once(
        prefix,
        '<span>数值有效口径</span><b>162</b>',
        f'<span>数值有效口径</span><b>{facts["valid_records"]}</b>',
        "valid record count",
    )
    replacements = [
        (
            "4 月 1 日至 6 月 30 日只读取冻结值，不重新估计参数。",
            f"{chinese_date(start)}至{chinese_date(end)}只读取冻结值，不重新估计参数。",
            "parameter flow evaluation dates",
        ),
        (
            "校准 03-23 至 03-27；评估 04-01 至 06-30",
            f"校准 03-23 至 03-27；评估 {start[5:]} 至 {end[5:]}",
            "parameter table evaluation dates",
        ),
        (
            "再跨 60 日求均值",
            f"再跨 {days} 日求均值",
            "metric aggregation days",
        ),
        (
            "汇总 60 天均值、标准差和原始 ICIR",
            f"汇总 {days} 天均值、标准差和原始 ICIR",
            "pipeline aggregation days",
        ),
        (
            "再在 60 日上求均值",
            f"再在 {days} 日上求均值",
            "IC definition days",
        ),
        (
            "跨三项都进入“思路并和 Top 20”的 12 条更适合作为第一轮候选池。",
            f"跨三项都进入“思路并和 Top 20”的 {facts['overlap_count']} 条更适合作为第一轮候选池。",
            "top-20 overlap count",
        ),
    ]
    for old, new, label in replacements:
        prefix = replace_once(prefix, old, new, label)

    prefix = replace_once(
        prefix,
        "<dt>业务运行 revision</dt><dd>a429f9f99b2e5a1475ea39d9529f64003461b423</dd>",
        f'<dt>业务运行 revision</dt><dd>{source["business_revision"]}</dd>',
        "business revision audit",
    )
    prefix = replace_once(
        prefix,
        "<dt>续跑控制 / 执行 revision</dt><dd>bed5da052ce2e3835f436259ffe8ebd4e3a4d7f3（只用于恢复与验证控制；Notebook metadata 的 business_revision 仍为上项）</dd>",
        f'<dt>区间扩展控制 / 执行 revision</dt><dd>{source["execution_revision"]}（只用于区间扩展、报告和验证控制；Notebook metadata 的 business_revision 仍为上项）</dd>',
        "execution revision audit",
    )
    prefix = replace_once(
        prefix,
        "<dt>当前本地 HEAD</dt><dd>9fa7ed90269486db8939209aceb19c846ae168f3；与业务 revision 相比，相关因子 src/config 没有定义变更，差异落在 factor_lab 报告层。</dd>",
        f'<dt>当前量化仓库本地 HEAD</dt><dd>{source["current_local_head"]}；区间合同明确记录 business_semantics_changed=false，因子定义沿用业务 revision。</dd>',
        "local revision audit",
    )
    old_runtime = (
        "<dt>运行结果</dt><dd>expected=generated=executed=165，failed=0；"
        "60 个交易日，173,429 个股票日面板行；每日约 2,886–2,894 只股票。</dd>"
    )
    new_runtime = (
        "<dt>运行结果</dt><dd>expected=generated=executed=165，failed=0；"
        f'{days} 个交易日，{facts["panel_sample_count"]:,} 个股票日面板行；'
        f'每日约 {facts["daily_min"]:,}–{facts["daily_max"]:,} 只股票。</dd>'
    )
    prefix = replace_once(prefix, old_runtime, new_runtime, "run result audit")
    prefix = replace_once(
        prefix,
        "<dt>Notebook archive SHA256</dt><dd>e19dcc42cdea795cad0830e4b8b4c59393289d16f5451d5553d95e713779db0d</dd>",
        f'<dt>Notebook archive SHA256</dt><dd>{source["notebook_archive_sha256"]}</dd>',
        "notebook archive audit",
    )
    prefix = replace_once(
        prefix,
        "<dt>提取数据 SHA256</dt><dd>0eb1853e21afe7740726cb068c8040e62f10d41ae7910414b5edf07da007edeb</dd>",
        f'<dt>提取数据 SHA256</dt><dd>{source["notebook_data_sha256"]}</dd>',
        "notebook data audit",
    )
    prefix = replace_once(
        prefix,
        "<dt>已有排名工作簿 SHA256</dt><dd>6287246AAA30D957A10FE3F5503B465CCE0C68D17DE1E681AED250537411B299</dd>",
        f'<dt>区间汇总指标 CSV SHA256</dt><dd>{source["interval_metrics_sha256"]}</dd>',
        "ranking evidence audit",
    )
    prefix = replace_once(
        prefix,
        "<dt>排名工作簿</dt><dd>D:\\MG\\！Internship\\26 Summer\\❗思瑞投资\\outputs\\019fb610-f78e-7e82-b023-48b8b31fc088\\因子_IC_RankIC_ICIR_详尽排名_20260731.xlsx</dd>",
        f'<dt>区间合同 SHA256</dt><dd>{source["interval_contract_sha256"]}</dd>',
        "interval contract audit",
    )
    return prefix


def serialize_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace(
        "</", "<\\/"
    )


def build_self_contained(
    template_html: str,
    match: re.Match[str],
    payload: dict[str, Any],
    facts: dict[str, Any],
) -> str:
    prefix = update_visible_facts(template_html[: match.start(2)], facts)
    prefix = replace_once(
        prefix,
        '<meta name="color-scheme" content="light">',
        '<meta name="color-scheme" content="light">\n'
        '<meta name="report-build" content="self-contained-interval-refresh-v1">',
        "self-contained build metadata",
    )
    html = prefix + serialize_payload(payload) + template_html[match.end(2) :]
    return replace_once(
        html,
        "    if(reveal(hash))history.replaceState(null,'',hash);",
        "    if(reveal(hash) && location.origin !== 'null')history.replaceState(null,'',hash);",
        "factor-link history guard",
    )


def build_website(self_html: str) -> tuple[str, dict[str, Any]]:
    match = REPORT_DATA_RE.search(self_html)
    if match is None:
        raise RuntimeError("generated self-contained HTML has no report data")
    payload = json.loads(match.group(2))
    expected_assets: set[str] = set()
    references: list[dict[str, Any]] = []
    decoded_reference_bytes = 0
    max_png_bytes = 0
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    for record in payload["records"]:
        alias = record["short_alias"]
        if not re.fullmatch(r"[a-z0-9_]+", alias):
            raise RuntimeError(f"unsafe report alias: {alias!r}")
        images = record["images"]
        if len(images) != EXPECTED_IMAGES_PER_NOTEBOOK:
            raise RuntimeError(f"{alias}: website build did not receive four images")
        for position, image in enumerate(images, start=1):
            encoded = image.pop("data", None)
            if not isinstance(encoded, str):
                raise RuntimeError(f"{alias} image {position}: missing base64 payload")
            decoded = base64.b64decode(encoded, validate=True)
            png_dimensions(decoded)
            digest = sha256_bytes(decoded)
            filename = f"{digest[:24]}.png"
            path = ASSET_DIR / filename
            expected_assets.add(filename)
            if path.exists():
                if sha256_file(path) != digest:
                    raise RuntimeError(f"existing website asset hash mismatch: {path}")
            else:
                path.write_bytes(decoded)
            size = len(decoded)
            decoded_reference_bytes += size
            max_png_bytes = max(max_png_bytes, size)
            image["url"] = f"{ASSET_URL_PREFIX}/{filename}"
            image["sha256"] = digest
            references.append(
                {
                    "record": alias,
                    "position": position,
                    "name": image["name"],
                    "url": image["url"],
                    "sha256": digest,
                    "bytes": size,
                    "width": image["width"],
                    "height": image["height"],
                }
            )

    actual_assets = {path.name for path in ASSET_DIR.glob("*.png")}
    unexpected = sorted(actual_assets - expected_assets)
    missing = sorted(expected_assets - actual_assets)
    if unexpected or missing:
        raise RuntimeError(
            f"website asset set is not deterministic: unexpected={unexpected}, missing={missing}"
        )

    web_html = (
        self_html[: match.start(2)]
        + serialize_payload(payload)
        + self_html[match.end(2) :]
    )
    web_html = replace_once(
        web_html, INLINE_IMAGE_RUNTIME, WEBSITE_IMAGE_RUNTIME, "website image runtime"
    )
    web_html = replace_once(
        web_html,
        'content="self-contained-interval-refresh-v1"',
        'content="website-external-assets-interval-refresh-v1"',
        "website build metadata",
    )
    web_html = replace_once(
        web_html,
        "报告内数字和图片来自同一批已执行 Notebook；所有图片以 base64 内嵌，CSS 和 JavaScript 也都在一个文件中，断网可读。",
        "报告内数字和图片来自同一批已执行 Notebook；图片按内容哈希拆为同站静态 PNG，CSS、JavaScript 与公式运行时仍随报告本地部署，不依赖外部网络资源。",
        "website audit delivery description",
    )
    web_html = replace_once(
        web_html,
        "SELF-CONTAINED RESEARCH REPORT · NO EXTERNAL ASSETS",
        "WEBSITE RESEARCH REPORT · HASHED LOCAL IMAGE ASSETS",
        "website footer",
    )
    web_size = len(web_html.encode("utf-8"))
    if web_size > CLOUDFLARE_SINGLE_ASSET_LIMIT:
        raise RuntimeError(f"website HTML exceeds 25 MiB: {web_size}")
    if max_png_bytes > CLOUDFLARE_SINGLE_ASSET_LIMIT:
        raise RuntimeError(f"website PNG exceeds 25 MiB: {max_png_bytes}")
    stats = {
        "website_html_bytes": web_size,
        "image_references": len(references),
        "unique_png_assets": len(expected_assets),
        "decoded_reference_bytes": decoded_reference_bytes,
        "max_png_bytes": max_png_bytes,
        "references": references,
    }
    return web_html, stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh the frozen 2026-07-31 factor report with interval notebooks."
    )
    parser.add_argument(
        "--source-root",
        required=True,
        type=Path,
        help="Local evidence directory containing the downloaded interval files and extracted/notebooks.",
    )
    parser.add_argument(
        "--quant-local-head",
        required=True,
        help="Audited local sirui-quant-research HEAD to show in the report.",
    )
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    if not re.fullmatch(r"[0-9a-f]{40}", args.quant_local_head):
        raise RuntimeError("--quant-local-head must be a lowercase 40-character Git hash")

    template_path, template_html, old_payload, match = extract_template()
    evidence = load_evidence(source_root)
    payload, facts = refresh_payload(old_payload, evidence, args.quant_local_head)
    self_html = build_self_contained(template_html, match, payload, facts)
    SELF_CONTAINED_HTML.write_text(self_html, encoding="utf-8", newline="\n")
    website_html, website_stats = build_website(self_html)
    WEBSITE_HTML.write_text(website_html, encoding="utf-8", newline="\n")

    manifest = {
        "schema_version": 1,
        "template": template_path.relative_to(ROOT).as_posix(),
        "template_sha256": sha256_file(template_path),
        "self_contained_html": SELF_CONTAINED_HTML.relative_to(ROOT).as_posix(),
        "self_contained_html_bytes": SELF_CONTAINED_HTML.stat().st_size,
        "self_contained_html_sha256": sha256_file(SELF_CONTAINED_HTML),
        "website_html": WEBSITE_HTML.relative_to(ROOT).as_posix(),
        "website_html_bytes": WEBSITE_HTML.stat().st_size,
        "website_html_sha256": sha256_file(WEBSITE_HTML),
        "business_revision": facts["source"]["business_revision"],
        "execution_revision": facts["source"]["execution_revision"],
        "actual_start": facts["actual_start"],
        "actual_end": facts["actual_end"],
        "trading_days": facts["trading_days"],
        "records": len(payload["records"]),
        "ideas": len(payload["ideas"]),
        "valid_records": facts["valid_records"],
        "notebook_archive_sha256": facts["source"]["notebook_archive_sha256"],
        "notebook_data_sha256": facts["source"]["notebook_data_sha256"],
        "interval_contract_sha256": facts["source"]["interval_contract_sha256"],
        "interval_metrics_sha256": facts["source"]["interval_metrics_sha256"],
        "cloudflare_single_asset_limit_bytes": CLOUDFLARE_SINGLE_ASSET_LIMIT,
        **website_stats,
    }
    ASSET_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {key: value for key, value in manifest.items() if key != "references"},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
