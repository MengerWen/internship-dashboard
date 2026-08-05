from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import factor_report_explanations as explanations


ROOT = Path(__file__).resolve().parents[1]
DAILY_DIR = ROOT / "content" / "daily"
EXPECTED_REPORTS = {
    "2026-07-31.show.html",
    "2026-08-01.html",
    "2026-08-01.show.html",
    "2026-08-02.html",
    "2026-08-02.show.html",
    "2026-08-04.html",
    "2026-08-04.show.html",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_reports() -> list[Path]:
    reports = []
    for path in sorted(DAILY_DIR.glob("*.html")):
        found = False
        with path.open(encoding="utf-8") as handle:
            while chunk := handle.read(16384):
                if 'id="report-data"' in chunk:
                    found = True
                    break
        if found:
            reports.append(path)
    names = {path.name for path in reports}
    if names != EXPECTED_REPORTS:
        raise RuntimeError(
            f"factor report inventory changed: missing={sorted(EXPECTED_REPORTS-names)} "
            f"extra={sorted(names-EXPECTED_REPORTS)}"
        )
    return reports


def refresh_manifests() -> list[Path]:
    changed: list[Path] = []
    for path in sorted((ROOT / "content" / "assets").glob("factor-report-*/manifest.json")):
        manifest = json.loads(path.read_text(encoding="utf-8"))
        touched = False
        for field in ("template", "self_contained_html", "website_html"):
            relative = manifest.get(field)
            if not isinstance(relative, str):
                continue
            target = ROOT / relative
            if not target.is_file():
                continue
            hash_field = f"{field}_sha256"
            bytes_field = f"{field}_bytes"
            digest = sha256_file(target)
            size = target.stat().st_size
            if manifest.get(hash_field) != digest:
                manifest[hash_field] = digest
                touched = True
            if bytes_field in manifest and manifest.get(bytes_field) != size:
                manifest[bytes_field] = size
                touched = True
        if manifest.get("formula_explanation_schema") != explanations.SCHEMA_VERSION:
            manifest["formula_explanation_schema"] = explanations.SCHEMA_VERSION
            touched = True
        if touched:
            path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            changed.append(path)
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add self-contained formula explanations to every factor report HTML."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that rewriting is idempotent without changing files.",
    )
    args = parser.parse_args()
    changed: list[Path] = []
    for path in discover_reports():
        original = path.read_text(encoding="utf-8")
        enriched = explanations.enrich_report_html(original)
        if enriched != original:
            if args.check:
                raise RuntimeError(f"formula explanations are stale: {path}")
            path.write_text(enriched, encoding="utf-8", newline="\n")
            changed.append(path)
    if not args.check:
        changed.extend(refresh_manifests())
    print(
        json.dumps(
            {
                "schema": explanations.SCHEMA_VERSION,
                "reports": len(EXPECTED_REPORTS),
                "changed": [path.relative_to(ROOT).as_posix() for path in changed],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
