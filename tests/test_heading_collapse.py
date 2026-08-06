from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_shared_enhancer_builds_accessible_collapsible_heading_sections() -> None:
    script = read("site/js/content-enhance.js")

    assert "prepareCollapsibleSections" in script
    assert "collapsible-section-body" in script
    assert "heading-collapse-toggle" in script
    assert 'setAttribute("aria-expanded"' in script
    assert "expandSectionAncestors" in script


def test_async_markdown_container_can_be_enhanced_after_initial_page_load() -> None:
    script = read("site/js/content-enhance.js")

    assert "delete container.dataset.collapsibleReady" in script
    assert "if (!children.some((child) => child.matches?.(HEADING_SELECTOR))) return" in script


def test_daily_outline_has_nested_synchronized_collapse_controls() -> None:
    script = read("site/js/daily.js")

    assert "daily-toc-list" in script
    assert "toc-collapse-toggle" in script
    assert "content-section-toggle" in script
    assert "setSectionExpanded" in script


def test_downloadable_html_is_enhanced_as_markdown_content() -> None:
    builder = read("build.py")

    assert '<main class="markdown-body">' in builder


def test_changed_browser_assets_are_cache_busted() -> None:
    index = read("site/index.html")

    assert 'base.css?v=20260806' in index
    assert 'daily.css?v=20260806' in index
    assert 'content-enhance.js?v=20260806' in index
    assert 'daily.js?v=20260806' in index
