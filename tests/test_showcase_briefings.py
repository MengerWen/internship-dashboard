from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_showcase_briefing_navigation_routes_synchronously():
    source = (ROOT / "site" / "js" / "showcase.js").read_text(encoding="utf-8")

    assert 'window.history.pushState(null, "", `#/daily/${briefing.dataset.date}`);' in source
    assert "this.app.route();" in source
