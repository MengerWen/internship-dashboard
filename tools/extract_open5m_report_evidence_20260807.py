from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
from typing import Any

import numpy as np
import pandas as pd


LABEL_COLUMN = "ret_intraday_vwap_0944_0945_from_d1_0935_last"
GROUP_COUNT = 40
BIN_COUNT = 100
EXPECTED_FACTORS = 495
EXPECTED_DAYS = 354


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require_new_output(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise FileExistsError(f"output directory must be new or empty: {path}")
    path.mkdir(parents=True, exist_ok=True)


def load_day(
    panel_path: Path,
    label_path: Path,
    factor_ids: list[str],
) -> tuple[pd.DataFrame, np.ndarray]:
    panel = pd.read_parquet(panel_path, columns=["date", "code", *factor_ids])
    label = pd.read_parquet(label_path, columns=["date", "code", LABEL_COLUMN])
    if panel.duplicated(["date", "code"]).any():
        raise ValueError(f"duplicate panel keys: {panel_path}")
    if label.duplicated(["date", "code"]).any():
        raise ValueError(f"duplicate label keys: {label_path}")
    merged = panel[["date", "code"]].merge(
        label,
        on=["date", "code"],
        how="left",
        sort=False,
        validate="one_to_one",
    )
    if len(merged) != len(panel):
        raise ValueError(f"panel/label row mismatch: {panel_path.name}")
    values = panel[factor_ids].to_numpy(dtype=np.float64, na_value=np.nan)
    returns = merged[LABEL_COLUMN].to_numpy(dtype=np.float64, na_value=np.nan)
    return panel[["date", "code"]], values, returns


def update_group_accumulators(
    values: np.ndarray,
    returns: np.ndarray,
    group_count: np.ndarray,
    group_factor_sum: np.ndarray,
    group_return_count: np.ndarray,
    group_return_sum: np.ndarray,
) -> None:
    rank_frame = pd.DataFrame(values).rank(
        axis=0,
        method="average",
        pct=True,
        na_option="keep",
    )
    ranks = rank_frame.to_numpy(dtype=np.float64, na_value=np.nan)
    for column in range(values.shape[1]):
        x = values[:, column]
        r = ranks[:, column]
        valid = np.isfinite(x) & np.isfinite(r)
        if not valid.any():
            continue
        groups = np.ceil(r[valid] * GROUP_COUNT).astype(np.int16) - 1
        groups = np.clip(groups, 0, GROUP_COUNT - 1)
        group_count[column] += np.bincount(groups, minlength=GROUP_COUNT)
        group_factor_sum[column] += np.bincount(
            groups,
            weights=x[valid],
            minlength=GROUP_COUNT,
        )
        valid_return = valid & np.isfinite(returns)
        if valid_return.any():
            return_groups = np.ceil(r[valid_return] * GROUP_COUNT).astype(np.int16) - 1
            return_groups = np.clip(return_groups, 0, GROUP_COUNT - 1)
            group_return_count[column] += np.bincount(
                return_groups,
                minlength=GROUP_COUNT,
            )
            group_return_sum[column] += np.bincount(
                return_groups,
                weights=returns[valid_return],
                minlength=GROUP_COUNT,
            )


def update_distribution_accumulators(
    values: np.ndarray,
    minimum: np.ndarray,
    maximum: np.ndarray,
    finite_count: np.ndarray,
    zero_count: np.ndarray,
    value_sum: np.ndarray,
    value_sumsq: np.ndarray,
) -> None:
    for column in range(values.shape[1]):
        x = values[:, column]
        valid = np.isfinite(x)
        if not valid.any():
            continue
        v = x[valid]
        minimum[column] = min(minimum[column], float(v.min()))
        maximum[column] = max(maximum[column], float(v.max()))
        finite_count[column] += len(v)
        zero_count[column] += int(np.count_nonzero(v == 0.0))
        value_sum[column] += float(v.sum(dtype=np.float64))
        value_sumsq[column] += float(np.square(v, dtype=np.float64).sum(dtype=np.float64))


def update_bin_accumulators(
    values: np.ndarray,
    returns: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    bin_count: np.ndarray,
    bin_return_count: np.ndarray,
    bin_return_sum: np.ndarray,
) -> None:
    for column in range(values.shape[1]):
        x = values[:, column]
        valid = np.isfinite(x)
        if not valid.any():
            continue
        width = upper[column] - lower[column]
        if not math.isfinite(width) or width <= 0:
            width = 1.0
        bins = np.floor((x[valid] - lower[column]) / width * BIN_COUNT).astype(np.int16)
        bins = np.clip(bins, 0, BIN_COUNT - 1)
        bin_count[column] += np.bincount(bins, minlength=BIN_COUNT)
        valid_return = valid & np.isfinite(returns)
        if valid_return.any():
            return_bins = np.floor(
                (x[valid_return] - lower[column]) / width * BIN_COUNT
            ).astype(np.int16)
            return_bins = np.clip(return_bins, 0, BIN_COUNT - 1)
            bin_return_count[column] += np.bincount(
                return_bins,
                minlength=BIN_COUNT,
            )
            bin_return_sum[column] += np.bincount(
                return_bins,
                weights=returns[valid_return],
                minlength=BIN_COUNT,
            )


def write_outputs(
    output_dir: Path,
    factor_ids: list[str],
    day_count: int,
    total_panel_rows: int,
    group_count: np.ndarray,
    group_factor_sum: np.ndarray,
    group_return_count: np.ndarray,
    group_return_sum: np.ndarray,
    bin_count: np.ndarray,
    bin_return_count: np.ndarray,
    bin_return_sum: np.ndarray,
    lower: np.ndarray,
    upper: np.ndarray,
    minimum: np.ndarray,
    maximum: np.ndarray,
    finite_count: np.ndarray,
    zero_count: np.ndarray,
    value_sum: np.ndarray,
    value_sumsq: np.ndarray,
) -> dict[str, Path]:
    group_rows: list[dict[str, object]] = []
    for factor_index, record_id in enumerate(factor_ids):
        for group_id in range(GROUP_COUNT):
            count = int(group_count[factor_index, group_id])
            return_count = int(group_return_count[factor_index, group_id])
            group_rows.append(
                {
                    "record_id": record_id,
                    "group_id": group_id,
                    "count": count,
                    "avg_size": count / day_count,
                    "factor_mean": (
                        group_factor_sum[factor_index, group_id] / count
                        if count
                        else np.nan
                    ),
                    "return_bps": (
                        group_return_sum[factor_index, group_id] / return_count * 1e4
                        if return_count
                        else np.nan
                    ),
                    "return_count": return_count,
                }
            )
    group_frame = pd.DataFrame(group_rows)

    bin_rows: list[dict[str, object]] = []
    for factor_index, record_id in enumerate(factor_ids):
        edges = np.linspace(lower[factor_index], upper[factor_index], BIN_COUNT + 1)
        for bin_id in range(BIN_COUNT):
            return_count = int(bin_return_count[factor_index, bin_id])
            bin_rows.append(
                {
                    "record_id": record_id,
                    "bin_id": bin_id,
                    "left_edge": float(edges[bin_id]),
                    "right_edge": float(edges[bin_id + 1]),
                    "count": int(bin_count[factor_index, bin_id]),
                    "return_bps": (
                        bin_return_sum[factor_index, bin_id] / return_count * 1e4
                        if return_count
                        else np.nan
                    ),
                    "return_count": return_count,
                }
            )
    bin_frame = pd.DataFrame(bin_rows)

    distribution_rows: list[dict[str, object]] = []
    for factor_index, record_id in enumerate(factor_ids):
        count = int(finite_count[factor_index])
        mean = value_sum[factor_index] / count if count else np.nan
        variance = (
            max(value_sumsq[factor_index] / count - mean * mean, 0.0)
            if count
            else np.nan
        )
        distribution_rows.append(
            {
                "record_id": record_id,
                "panel_rows": total_panel_rows,
                "finite_count": count,
                "coverage": count / total_panel_rows if total_panel_rows else np.nan,
                "zero_share": zero_count[factor_index] / count if count else np.nan,
                "mean": mean,
                "std": math.sqrt(variance) if math.isfinite(variance) else np.nan,
                "minimum": minimum[factor_index] if count else np.nan,
                "maximum": maximum[factor_index] if count else np.nan,
                "bin_lower": lower[factor_index],
                "bin_upper": upper[factor_index],
                "unit_interval_bins": bool(
                    count
                    and minimum[factor_index] >= 0.0
                    and maximum[factor_index] <= 1.0
                ),
            }
        )
    distribution_frame = pd.DataFrame(distribution_rows)

    paths = {
        "groups": output_dir / "group_40.parquet",
        "bins": output_dir / "bins_100.parquet",
        "distribution": output_dir / "factor_distribution.csv",
    }
    group_frame.to_parquet(paths["groups"], index=False)
    bin_frame.to_parquet(paths["bins"], index=False)
    distribution_frame.to_csv(paths["distribution"], index=False)
    return paths


def extract(run_root: Path, output_dir: Path) -> dict[str, Any]:
    run_root = run_root.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    require_new_output(output_dir)

    evaluation_path = run_root / "evaluation" / "EVALUATION_RESULT.json"
    formal_path = run_root / "FORMAL_STUDY_RESULT.json"
    period_path = run_root / "evaluation" / "period_summary.parquet"
    daily_path = run_root / "evaluation" / "daily_ic.parquet"
    for path in (evaluation_path, formal_path, period_path, daily_path):
        if not path.is_file():
            raise FileNotFoundError(path)

    evaluation = read_json(evaluation_path)
    formal = read_json(formal_path)
    if evaluation.get("status") != "success" or formal.get("status") != "complete":
        raise RuntimeError("formal panel or evaluation is incomplete")
    if evaluation.get("factor_count") != EXPECTED_FACTORS:
        raise RuntimeError("evaluation factor count differs from 495")
    if evaluation.get("day_count") != EXPECTED_DAYS:
        raise RuntimeError("evaluation day count differs from 354")

    period = pd.read_parquet(period_path)
    daily = pd.read_parquet(daily_path)
    full = period.loc[period["period"].eq("full_history")].copy()
    factor_ids = full["record_id"].astype(str).tolist()
    if len(factor_ids) != EXPECTED_FACTORS or len(set(factor_ids)) != EXPECTED_FACTORS:
        raise RuntimeError("full-history period does not contain 495 unique factors")
    if set(daily["record_id"].astype(str)) != set(factor_ids):
        raise RuntimeError("daily and period factor inventories disagree")

    panel_dir = run_root / "output" / "panel_win0930_0935" / "shards"
    label_dir = (
        run_root
        / "output"
        / "intraday_labels"
        / "intraday_vwap_0944_0945_from_0935_v1"
        / "shards"
    )
    panel_paths = sorted(panel_dir.glob("date=*.parquet"))
    if len(panel_paths) != EXPECTED_DAYS:
        raise RuntimeError(f"expected 354 panel shards, found {len(panel_paths)}")
    label_paths = {path.name: path for path in label_dir.glob("date=*.parquet")}
    if set(label_paths) != {path.name for path in panel_paths}:
        raise RuntimeError("panel and label day inventories disagree")

    factor_count = len(factor_ids)
    group_count = np.zeros((factor_count, GROUP_COUNT), dtype=np.int64)
    group_factor_sum = np.zeros((factor_count, GROUP_COUNT), dtype=np.float64)
    group_return_count = np.zeros((factor_count, GROUP_COUNT), dtype=np.int64)
    group_return_sum = np.zeros((factor_count, GROUP_COUNT), dtype=np.float64)
    minimum = np.full(factor_count, np.inf, dtype=np.float64)
    maximum = np.full(factor_count, -np.inf, dtype=np.float64)
    finite_count = np.zeros(factor_count, dtype=np.int64)
    zero_count = np.zeros(factor_count, dtype=np.int64)
    value_sum = np.zeros(factor_count, dtype=np.float64)
    value_sumsq = np.zeros(factor_count, dtype=np.float64)
    total_panel_rows = 0

    print(json.dumps({"phase": "group-pass", "days": len(panel_paths)}), flush=True)
    for position, panel_path in enumerate(panel_paths, start=1):
        _, values, returns = load_day(panel_path, label_paths[panel_path.name], factor_ids)
        total_panel_rows += len(values)
        update_distribution_accumulators(
            values,
            minimum,
            maximum,
            finite_count,
            zero_count,
            value_sum,
            value_sumsq,
        )
        update_group_accumulators(
            values,
            returns,
            group_count,
            group_factor_sum,
            group_return_count,
            group_return_sum,
        )
        if position == 1 or position % 10 == 0 or position == len(panel_paths):
            print(
                json.dumps(
                    {
                        "phase": "group-pass",
                        "complete_days": position,
                        "total_days": len(panel_paths),
                        "panel_rows": total_panel_rows,
                    }
                ),
                flush=True,
            )

    unit_interval = (
        (finite_count > 0)
        & (minimum >= 0.0)
        & (maximum <= 1.0)
    )
    lower = np.where(unit_interval, 0.0, minimum)
    upper = np.where(unit_interval, 1.0, maximum)
    invalid_range = (~np.isfinite(lower)) | (~np.isfinite(upper)) | (upper <= lower)
    lower[invalid_range] = np.where(np.isfinite(lower[invalid_range]), lower[invalid_range], 0.0)
    upper[invalid_range] = lower[invalid_range] + 1.0

    bin_count = np.zeros((factor_count, BIN_COUNT), dtype=np.int64)
    bin_return_count = np.zeros((factor_count, BIN_COUNT), dtype=np.int64)
    bin_return_sum = np.zeros((factor_count, BIN_COUNT), dtype=np.float64)
    print(json.dumps({"phase": "bin-pass", "days": len(panel_paths)}), flush=True)
    for position, panel_path in enumerate(panel_paths, start=1):
        _, values, returns = load_day(panel_path, label_paths[panel_path.name], factor_ids)
        update_bin_accumulators(
            values,
            returns,
            lower,
            upper,
            bin_count,
            bin_return_count,
            bin_return_sum,
        )
        if position == 1 or position % 10 == 0 or position == len(panel_paths):
            print(
                json.dumps(
                    {
                        "phase": "bin-pass",
                        "complete_days": position,
                        "total_days": len(panel_paths),
                    }
                ),
                flush=True,
            )

    outputs = write_outputs(
        output_dir,
        factor_ids,
        len(panel_paths),
        total_panel_rows,
        group_count,
        group_factor_sum,
        group_return_count,
        group_return_sum,
        bin_count,
        bin_return_count,
        bin_return_sum,
        lower,
        upper,
        minimum,
        maximum,
        finite_count,
        zero_count,
        value_sum,
        value_sumsq,
    )

    copied = {
        "period_summary": output_dir / "period_summary.parquet",
        "daily_ic": output_dir / "daily_ic.parquet",
        "evaluation_result": output_dir / "EVALUATION_RESULT.json",
        "formal_result": output_dir / "FORMAL_STUDY_RESULT.json",
    }
    for source, target in (
        (period_path, copied["period_summary"]),
        (daily_path, copied["daily_ic"]),
        (evaluation_path, copied["evaluation_result"]),
        (formal_path, copied["formal_result"]),
    ):
        shutil.copy2(source, target)

    all_outputs = {**outputs, **copied}
    manifest = {
        "schema_version": "open5m-report-evidence-v1",
        "status": "complete",
        "source_run_root": str(run_root),
        "source_revision": formal.get("revision"),
        "registry_hash": evaluation.get("registry_hash"),
        "start": evaluation.get("start"),
        "end": evaluation.get("end"),
        "day_count": len(panel_paths),
        "panel_rows": total_panel_rows,
        "factor_count": len(factor_ids),
        "formal_factor_count": 490,
        "diagnostic_factor_count": 5,
        "label": LABEL_COLUMN,
        "group_method": (
            "daily cross-sectional average percentile rank; "
            "ceil(percentile*40)-1; ties retained in the same band"
        ),
        "bin_method": (
            "100 equal-width pooled bins; fixed [0,1] when observed range "
            "is within [0,1], otherwise observed min-max"
        ),
        "outputs": {
            name: {
                "path": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for name, path in all_outputs.items()
        },
    }
    manifest_path = output_dir / "REPORT_EVIDENCE_MANIFEST.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=True, sort_keys=True), flush=True)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    extract(args.run_root, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
