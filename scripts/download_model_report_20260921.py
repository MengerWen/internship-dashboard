"""Read published run artifacts from the approved wenjie checkout's output root."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess


REVISION = "0cedf22d5d531d6ac3e88e87966d6afae1429c0b"
BASE = "/home/wenjie/hdd-store/outputs/sirui/ml-single-fit-causal"
TRAIN = f"{BASE}/ml-causal-328-20260921-r03-train"
TEST = f"{BASE}/ml-causal-328-20260921-r03-test"
BASELINE = "/home/wenjie/hdd-store/outputs/sirui/ml-single-fit-test/ml-single-fit-cpu-l2-test-lssharpe-i0659-20260918-r01"
TRAIN_FILES = (
    "timing_resource_summary.json", "dataset_summary.json", "effective_parameters.json",
    "feature_mapping_328.json", "per_round_metrics.parquet", "resource_samples.parquet",
    "environment.json", "code_identity.json", "trade_vwap_consistency.json",
)
TEST_FILES = (
    "test_summary.json", "validation_selection_receipt.json", "frozen_model_identity.json",
    "test_daily_metrics.parquet", "test_monthly_metrics.parquet", "test_positions.parquet",
    "test_predictions.parquet", "test_daily_input_audit.parquet", "trade_vwap_consistency.json",
)


def main(destination: Path):
    destination.mkdir(parents=True, exist_ok=True)
    for section, root, files in (("train", TRAIN, TRAIN_FILES), ("test", TEST, TEST_FILES)):
        folder = destination / section
        folder.mkdir(exist_ok=True)
        for name in files:
            target = folder / name
            with target.open("wb") as out:
                subprocess.run(["ssh", "sirui-server", "cat", f"{root}/output/{name}"], stdout=out, check=True)
            if not target.stat().st_size:
                raise RuntimeError(f"empty source artifact: {name}")
    baseline = destination / "baseline"
    baseline.mkdir(exist_ok=True)
    with (baseline / "test_summary.json").open("wb") as out:
        subprocess.run(["ssh", "sirui-server", "cat", f"{BASELINE}/test_summary.json"], stdout=out, check=True)
    (destination / "run_paths.json").write_text(json.dumps({
        "business_revision": REVISION,
        "train_run_root": TRAIN,
        "test_run_root": TEST,
        "observational_baseline_root": BASELINE,
    }, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.output)
