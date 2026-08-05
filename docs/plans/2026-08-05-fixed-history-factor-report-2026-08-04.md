# 2026-08-04 Fixed-History Factor Report Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Publish offline and website-deployable 2026-08-04 factor reports from the 2025-01-02 to 2026-07-31 fixed-parameter historical evaluation while preserving the frozen explanatory content.

**Architecture:** Freeze the committed 2026-08-02 offline report as the explanatory template and reuse its generator pipeline. Replace only source evidence, sample-dependent metrics, rankings, diagnostics, images, interval facts, and audit hashes; externalize PNG assets only for the website version.

**Tech Stack:** Python 3, HTML/CSS/JavaScript, KaTeX, Jupyter Notebook JSON, Git, the existing static-site builder.

---

### Task 1: Verify source evidence and repository state

**Files:**
- Read: server fixed-history output and Notebook archive
- Read: `content/daily/2026-08-02.html`
- Read: `tools/build_factor_report_20260802.py`

**Steps:**
1. Confirm dashboard and quantitative-research branches, revisions, and worktree state.
2. Confirm the server output root, continuation, Notebook count, manifests, result JSON, and evidence hashes.
3. Confirm no formal or guarded heavy task is running.

### Task 2: Add a frozen-template generator

**Files:**
- Create: `tools/build_factor_report_20260804.py`
- Create: `content/daily/2026-08-04.html`
- Create: `content/daily/2026-08-04.show.html`
- Create: `content/assets/factor-report-2026-08-04/manifest.json`
- Create: `content/assets/factor-report-2026-08-04/*.png`

**Steps:**
1. Pin the SHA-256 of the committed 2026-08-02 template.
2. Parse all 165 executed Notebooks and fail closed on missing metrics or images.
3. Recompute 165-record and 55-idea rankings for IC, Rank_IC, and ICIR.
4. Generate the self-contained file and the equivalent asset-externalized website file.
5. Run the generator twice and require byte-identical outputs.

### Task 3: Publish the site entry

**Files:**
- Create: `content/daily/2026-08-04.md`
- Modify: `content/showcase/03-factor.md`

**Steps:**
1. Add the dated daily entry and route to the website report.
2. Make 2026-08-04 the latest factor report and retain 2026-08-02 as the previous version.

### Task 4: Verify correctness and rendering

**Files:**
- Test: `tests/*`
- Build output: `dist/`

**Steps:**
1. Compile the generator and run all unit tests.
2. Build the site and require zero warnings after commit.
3. Audit record counts, valid/NA counts, ranking order, image hashes, and offline/website payload equivalence.
4. Open the local built site and verify KaTeX rendering, navigation, ranking links, and four-image loading.

### Task 5: Commit and push

**Steps:**
1. Stage only the plan, generator, dated report files, dated assets, daily entry, and factor showcase update.
2. Run `git diff --cached --check` and inspect staged file sizes.
3. Commit with a focused message, rebuild after commit, and push `main`.
4. Fetch `origin/main`, require local/remote HEAD equality, and report any unverified server-cleanliness evidence separately.
