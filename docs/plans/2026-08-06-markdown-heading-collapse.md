# Markdown Heading Collapse Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let readers expand or collapse every rendered Markdown heading from both the document outline and the document body.

**Architecture:** Enhance each rendered `.markdown-body` in the browser by grouping its top-level headings and following content into nested sections according to heading level. A shared section state drives the triangle button beside the heading and the matching tree node in the daily-document outline, so either control stays synchronized and parent sections hide their descendants.

**Tech Stack:** Vanilla JavaScript, semantic HTML/ARIA, existing CSS design tokens, Python static-site builder and tests.

---

### Task 1: Specify the browser behavior

**Files:**
- Test: `tests/test_heading_collapse.py`

**Steps:**
1. Add assertions for the shared heading enhancer, accessible expanded state, nested outline controls, and cache-busted assets.
2. Run the focused test and confirm it fails before implementation.

### Task 2: Add collapsible Markdown sections

**Files:**
- Modify: `site/js/content-enhance.js`
- Modify: `site/css/base.css`
- Modify: `build.py`

**Steps:**
1. Group direct-child `h1` through `h6` elements into nested section containers without changing heading IDs or text.
2. Add a keyboard-accessible triangle button to every heading and expose shared expand/collapse helpers.
3. Style expanded, collapsed, hover, focus, mobile, and reduced-motion states.
4. Mark downloadable daily HTML as Markdown content so it receives the same enhancement.

### Task 3: Add a collapsible synchronized outline

**Files:**
- Modify: `site/js/daily.js`
- Modify: `site/css/daily.css`

**Steps:**
1. Replace the flat heading list with a nested outline based on heading levels.
2. Add a triangle button to every outline entry and synchronize it with the corresponding body section.
3. Expand hidden ancestors before navigating to a heading and preserve active-heading observation.

### Task 4: Verify and publish

**Files:**
- Modify: `site/index.html`

**Steps:**
1. Update asset version query strings and run the focused test, full test suite, JavaScript syntax checks, and static-site build.
2. Verify expanded and collapsed states in a real browser at desktop and narrow widths.
3. Inspect the final diff, stage only this feature, commit once, push `main`, and confirm local and remote HEADs match.
