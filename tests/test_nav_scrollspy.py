"""Every daily show page with an in-page nav must track the section being read."""
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

import add_nav_scrollspy as spy  # noqa: E402


@pytest.mark.parametrize('name', sorted(spy.PAGES))
def test_page_carries_the_shared_scrollspy(name):
    page = (spy.DAILY / name).read_text(encoding='utf-8')
    assert page.count(f'<script {spy.MARKER}>') == 1
    assert "classList.toggle('active'" in page
    # Each nav link must point at an element that actually exists on the page.
    nav = re.search(r'<nav[^>]*>.*?</nav>', page, re.S).group(0)
    anchors = re.findall(r'href="#([^"]+)"', nav)
    assert len(anchors) >= 2
    for anchor in anchors:
        assert f'id="{anchor}"' in page, (name, anchor)


@pytest.mark.parametrize('name', sorted(spy.PAGES))
def test_active_tab_has_a_visible_style(name):
    page = (spy.DAILY / name).read_text(encoding='utf-8')
    assert re.search(r'(\.nav|\.chapter-nav|(?<![\w.])nav) a[^{]*\.active[^{]*\{', page) \
        or re.search(r'\.active[^{]*\{[^}]*\}', page)


def test_injection_is_idempotent_and_self_healing():
    """Re-running must be a no-op, and --check must agree with that."""
    for name, css in spy.PAGES.items():
        current = (spy.DAILY / name).read_text(encoding='utf-8')
        assert spy.render(current, css, name) == current, name
    result = subprocess.run(
        [sys.executable, str(ROOT / 'scripts/add_nav_scrollspy.py'), '--check'],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_every_daily_page_with_an_in_page_nav_is_covered():
    """A new page that grows a nav must be added to the patch list, not forgotten."""
    missing = []
    for path in sorted(spy.DAILY.glob('*.show.html')):
        page = path.read_text(encoding='utf-8', errors='replace')
        navs = re.findall(r'<nav[^>]*>.*?</nav>', page, re.S)
        anchors = [a for nav in navs for a in re.findall(r'href="#([^"]+)"', nav)]
        resolved = [a for a in anchors if f'id="{a}"' in page]
        if len(resolved) >= 2 and path.name not in spy.PAGES:
            missing.append(path.name)
    assert missing == [], f'add to add_nav_scrollspy.PAGES: {missing}'
