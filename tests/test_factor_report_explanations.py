from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import factor_report_explanations as explanations  # noqa: E402


REPORTS = [
    ROOT / "content" / "daily" / "2026-07-31.show.html",
    ROOT / "content" / "daily" / "2026-08-01.html",
    ROOT / "content" / "daily" / "2026-08-01.show.html",
    ROOT / "content" / "daily" / "2026-08-02.html",
    ROOT / "content" / "daily" / "2026-08-02.show.html",
    ROOT / "content" / "daily" / "2026-08-04.html",
    ROOT / "content" / "daily" / "2026-08-04.show.html",
]


def payload_from(html: str) -> dict:
    matches = list(explanations.REPORT_DATA_RE.finditer(html))
    assert len(matches) == 1
    return json.loads(matches[0].group(2))


@pytest.mark.parametrize("path", REPORTS, ids=lambda path: path.name)
def test_every_factor_report_has_self_contained_formula_guides(path: Path) -> None:
    html = path.read_text(encoding="utf-8")
    payload = payload_from(html)
    assert payload["formula_explanation_schema"] == explanations.SCHEMA_VERSION
    assert len(payload["ideas"]) == 55
    assert len(payload["formula_glossary"]) == len(explanations.FORMULA_GLOSSARY)
    assert html.count("function formulaGuide(idea){") == 1
    assert html.count("${formulaGuide(idea)}") == 1
    assert html.count(f'content="{explanations.SCHEMA_VERSION}"') == 1

    glossary = payload["formula_glossary"]
    for idea in payload["ideas"]:
        guide = idea["formula_guide"]
        assert guide["reading"]
        assert guide["aggregation"]
        assert guide["zero_na"]
        assert len(guide["term_keys"]) >= 2
        assert not (set(guide["term_keys"]) - set(glossary)), idea["idea_id"]


@pytest.mark.parametrize("path", REPORTS, ids=lambda path: path.name)
def test_f03_is_expanded_and_uses_canonical_parameter_names(path: Path) -> None:
    payload = payload_from(path.read_text(encoding="utf-8"))
    f03 = next(idea for idea in payload["ideas"] if idea["idea_id"] == "f03_curg_hybrid")
    formula = f03["description"]["formula"]
    assert "K_{\\mathrm{hybrid}}" not in formula
    assert "\\theta_{\\mathrm{wall}}" in formula
    assert "\\theta_{\\mathrm{event}}" in formula
    assert "\\theta_{t}" not in formula
    assert "\\theta_{e}" not in formula
    assert f03["formula_guide"]["term_keys"] == explanations.IDEA_TERM_KEYS[
        "f03_curg_hybrid"
    ]
    assert "1.990919" in payload["formula_glossary"]["theta_wall"]["source"]
    assert "38,342.506102" in payload["formula_glossary"]["theta_event"]["source"]
    assert "当前 $p=1$" in payload["formula_glossary"]["kernel_shape"]["definition"]


def test_formula_enrichment_is_idempotent() -> None:
    html = REPORTS[-1].read_text(encoding="utf-8")
    assert explanations.enrich_report_html(html) == html


@pytest.mark.parametrize("path", REPORTS, ids=lambda path: path.name)
def test_every_factor_report_uses_the_current_all_order_summary(path: Path) -> None:
    html = path.read_text(encoding="utf-8")
    assert html.count('data-research-summary="all-order-denominator-v1"') == 1
    assert html.count(".research-update{") == 1
    assert "_c_all = activity_count / window_total_count" in html
    assert "_c_cond = activity_count / determinable_total_count" in html
    assert "IC</th><th colspan=\"2\">Rank_IC</th><th colspan=\"2\">ICIR" in html
    assert "+0.06365" in html
    assert "-0.00051" in html
    assert "41 / 54" in html
    assert "38 / 54" in html
    assert "45 / 54" in html
    assert html.count('id="ranking-leaders"') == 1
    assert html.count('id="ranking-tables"') == 1
    assert html.count('id="overlap"') == 1


def test_formula_inventory_covers_exactly_the_published_ideas() -> None:
    payload = payload_from(REPORTS[-1].read_text(encoding="utf-8"))
    published = {idea["idea_id"] for idea in payload["ideas"]}
    assert published == set(explanations.IDEA_TERM_KEYS)
    assert not (
        {key for keys in explanations.IDEA_TERM_KEYS.values() for key in keys}
        - set(explanations.FORMULA_GLOSSARY)
    )
