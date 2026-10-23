"""Check the report contract and build bounded fixtures with the site's real Builder."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "content/daily/2026-10-23.show.html"
ARTIFACTS = ROOT / "artifacts/sse-reconstruction-report-20261023"


def check() -> dict:
    text = REPORT.read_text(encoding="utf-8")
    script = re.findall(r"<script(?:\s[^>]*)?>(.*?)</script>", text, flags=re.S)[-1]
    parsed = subprocess.run(["node", "--check"], input=script, text=True, encoding="utf-8", capture_output=True)
    if parsed.returncode:
        raise ValueError(parsed.stderr)
    data = json.loads(re.search(r'<script type="application/json" id="report-data">(.*?)</script>', text, re.S).group(1))
    assert len(data["errors"]) == 352 and len(data["source"]) == 9
    assert len(data["mechanisms"]) == 20
    assert not re.search(r"<(?:script|link|img)\b[^>]*(?:src|href)=[\"'](?:https?:|\.\./)", text)
    assert not re.search(r"url\([\"']?(?:https?:|\.\./)", text)
    assert "localStorage" not in script and "fetch(" not in script
    assert "方案初稿" not in text and "dir-a.html" not in text
    assert text.count("data:font/woff2;base64,") == 2
    assert "report-font-fingerprint" in text
    primary = (ROOT / "content/daily/2026-10-23.md").read_text(encoding="utf-8")
    assert "date: 2026-10-23" in primary
    return {"sha256": hashlib.sha256(REPORT.read_bytes()).hexdigest(), "bytes": REPORT.stat().st_size, "error_columns": len(data["errors"]), "evidence_topics": len(data["source"]), "source_revision": data["provenance"]["revision"], "external_runtime_assets": 0}


def preview() -> dict:
    spec = importlib.util.spec_from_file_location("dashboard_builder", ROOT / "build.py")
    module = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    fixture = ARTIFACTS / "fixture-content"
    expected = {"2026-10-23.md", "2026-10-23.show.html"}
    if fixture.exists():
        if {p.name for p in (fixture / "daily").iterdir()} != expected:
            raise ValueError("Unexpected files in this task's fixture")
    fixture.joinpath("daily").mkdir(parents=True, exist_ok=True)
    for name in ("2026-10-23.md", "2026-10-23.show.html"):
        shutil.copyfile(ROOT / "content/daily" / name, fixture / "daily" / name)
    module.CONTENT_DIR = fixture
    result = {}
    for offline in (False, True):
        target = ARTIFACTS / ("offline" if offline else "online")
        builder = module.Builder(offline=offline, tags_snapshot=ROOT / "content/report-tags.json")
        builder.out_dir = target
        if target.exists():
            previous = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
            if len(previous["daily"]) != 1 or previous["daily"][0]["date"] != "2026-10-23":
                raise ValueError("Refusing to overwrite an unrelated preview")
            shutil.copyfile(ROOT / "site/index.html", target / "index.html")
            builder.inject_asset_versions()
        else:
            builder.prepare_output()
        daily = builder.build_daily()
        assert len(daily) == 1
        manifest = builder.manifest([], daily)
        builder.write_security_files()
        if offline:
            builder.inline_offline_data(manifest)
        entry = manifest["daily"][0]
        assert entry["date"] == "2026-10-23" and entry["has_show"] and entry["show_type"] == "html"
        assert entry["show_allow_downloads"] is False
        result["offline" if offline else "online"] = {"path": target.relative_to(ROOT).as_posix(), "show_path": entry["show_path"], "registered": True, "warnings": builder.warnings}
    result["scope"] = "Real daily registration, manifest, runtime asset injection and offline inlining; other dates, 701.7 MiB of unrelated content assets and Pagefind excluded."
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    result = check()
    if args.preview:
        result["build"] = preview()
    ARTIFACTS.mkdir(exist_ok=True)
    (ARTIFACTS / "contract-check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
