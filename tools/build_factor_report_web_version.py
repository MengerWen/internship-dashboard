from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "artifacts"
    / "factor-report-2026-07-31"
    / "2026-07-31-算法行为因子构建链路与165口径实测全景报告.current.self-contained.html"
)
WEB_HTML = ROOT / "content" / "daily" / "2026-07-31.show.html"
ASSET_DIR = ROOT / "content" / "assets" / "factor-report-2026-07-31"
ASSET_URL_PREFIX = "assets/factor-report-2026-07-31"
ASSET_MANIFEST = ASSET_DIR / "manifest.json"
CLOUDFLARE_SINGLE_ASSET_LIMIT = 25 * 1024 * 1024
REPORT_DATA_RE = re.compile(
    r'(<script id="report-data" type="application/json">)(.*?)(</script>)',
    flags=re.DOTALL,
)
INLINE_IMAGE_RUNTIME = "img.src='data:image/png;base64,'+im.data;"
WEB_IMAGE_RUNTIME = "img.src=im.url||('data:image/png;base64,'+im.data);"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(f"self-contained source is missing: {SOURCE}")

    source_html = SOURCE.read_text(encoding="utf-8")
    match = REPORT_DATA_RE.search(source_html)
    if match is None:
        raise RuntimeError("report-data JSON script was not found")
    if len(REPORT_DATA_RE.findall(source_html)) != 1:
        raise RuntimeError("expected exactly one report-data JSON script")
    if source_html.count(INLINE_IMAGE_RUNTIME) != 1:
        raise RuntimeError("inline image runtime no longer matches the audited source")

    payload = json.loads(match.group(2))
    records = payload.get("records")
    ideas = payload.get("ideas")
    if not isinstance(records, list) or len(records) != 165:
        raise RuntimeError("expected 165 report records")
    if not isinstance(ideas, list) or len(ideas) != 55:
        raise RuntimeError("expected 55 report ideas")

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    expected_assets: set[str] = set()
    references: list[dict[str, object]] = []
    decoded_bytes = 0
    max_asset_bytes = 0

    for record in records:
        alias = str(record.get("short_alias", ""))
        images = record.get("images")
        if not re.fullmatch(r"[a-z0-9_]+", alias):
            raise RuntimeError(f"unsafe or missing record alias: {alias!r}")
        if not isinstance(images, list) or len(images) != 4:
            raise RuntimeError(f"{alias} does not contain exactly four images")

        for index, image in enumerate(images, start=1):
            encoded = image.pop("data", None)
            if not isinstance(encoded, str):
                raise RuntimeError(f"{alias} image {index} has no base64 payload")
            decoded = base64.b64decode(encoded, validate=True)
            if not decoded.startswith(b"\x89PNG\r\n\x1a\n"):
                raise RuntimeError(f"{alias} image {index} is not a PNG")

            digest = sha256_bytes(decoded)
            filename = f"{digest[:24]}.png"
            path = ASSET_DIR / filename
            expected_assets.add(filename)
            if path.exists():
                if sha256_file(path) != digest:
                    raise RuntimeError(f"existing asset hash mismatch: {path}")
            else:
                path.write_bytes(decoded)

            size = len(decoded)
            decoded_bytes += size
            max_asset_bytes = max(max_asset_bytes, size)
            image["url"] = f"{ASSET_URL_PREFIX}/{filename}"
            image["sha256"] = digest
            references.append(
                {
                    "record": alias,
                    "position": index,
                    "name": image.get("name"),
                    "url": image["url"],
                    "sha256": digest,
                    "bytes": size,
                    "width": image.get("width"),
                    "height": image.get("height"),
                }
            )

    actual_assets = {path.name for path in ASSET_DIR.glob("*.png")}
    unexpected = sorted(actual_assets - expected_assets)
    missing = sorted(expected_assets - actual_assets)
    if unexpected or missing:
        raise RuntimeError(
            f"asset directory is not deterministic; unexpected={unexpected}, missing={missing}"
        )

    payload_json = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    web_html = (
        source_html[: match.start(2)]
        + payload_json
        + source_html[match.end(2) :]
    )
    web_html = web_html.replace(INLINE_IMAGE_RUNTIME, WEB_IMAGE_RUNTIME, 1)
    web_html = web_html.replace(
        '<meta name="color-scheme" content="light">',
        '<meta name="color-scheme" content="light">\n'
        '<meta name="report-build" content="website-external-assets-v1">',
        1,
    )
    WEB_HTML.write_text(web_html, encoding="utf-8", newline="\n")

    web_size = WEB_HTML.stat().st_size
    if web_size > CLOUDFLARE_SINGLE_ASSET_LIMIT:
        raise RuntimeError(
            f"website HTML is still too large for Cloudflare: {web_size} bytes"
        )
    if max_asset_bytes > CLOUDFLARE_SINGLE_ASSET_LIMIT:
        raise RuntimeError(
            f"one extracted image exceeds the Cloudflare limit: {max_asset_bytes} bytes"
        )

    manifest = {
        "schema_version": 1,
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_bytes": SOURCE.stat().st_size,
        "source_sha256": sha256_file(SOURCE),
        "website_html": WEB_HTML.relative_to(ROOT).as_posix(),
        "website_html_bytes": web_size,
        "website_html_sha256": sha256_file(WEB_HTML),
        "records": len(records),
        "ideas": len(ideas),
        "image_references": len(references),
        "unique_png_assets": len(expected_assets),
        "decoded_reference_bytes": decoded_bytes,
        "max_png_bytes": max_asset_bytes,
        "cloudflare_single_asset_limit_bytes": CLOUDFLARE_SINGLE_ASSET_LIMIT,
        "references": references,
    }
    ASSET_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({key: value for key, value in manifest.items() if key != "references"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
