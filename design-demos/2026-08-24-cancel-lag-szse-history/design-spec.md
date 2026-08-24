# SZSE cancel-lag history evidence viewer

## Purpose

Present the complete 2024-01-02 through 2026-06-30 SZSE Open5m submit-to-cancel lag study as a direct-view artifact inside the quantitative-results website. The viewer must make fixed-delay structure, persistence, and change over time visible without requiring the reader to infer patterns from cumulative totals.

## Audience and viewing distance

The primary audience is a quantitative researcher reviewing the page on a laptop inside the existing daily-results site. The embedded viewport is approximately 1000×580px, with secondary verification at 1440×900 and 390×844. Labels must remain legible in the embedded viewport; explanatory text is concise and subordinate to the charts.

## Content architecture

Use a fixed-height horizontal deck rather than a vertically scrolling report. Each section occupies one viewport. The sections are: conclusion cover, native 10ms frequency, volume-normalized comparison, daily structure, monthly change, peak evidence, and interpretation/quality. Period comparisons remain inside their relevant section: 2024, 2025, and 2026H1 frequency views are displayed together; daily structure uses one continuous 601-day heatmap with year boundaries; monthly evidence is one grouped section.

## Visual system

- Paper: white with warm-gray grid and rules.
- Ink: near black for titles and axes.
- Primary accent: SZSE blue `#174f78`.
- Period accents: three distinguishable blue/gray tones that retain sufficient contrast without suggesting different markets.
- Typography: editorial Chinese sans-serif stack with a monospace numeric stack for axes, dates, and evidence values.
- Charts: Canvas, 10ms raw curves without smoothing, 50ms daily heatmap aggregation, explicit shared scales where direct comparison is claimed.

## Interaction

Top tabs, bottom previous/next controls, keyboard left/right/Home/End, and horizontal touch swipe all change sections. The current section is persisted locally. No page-level horizontal or vertical scrolling is allowed in the viewer. All controls require visible focus states and accessible labels.

## Evidence constraints

All numbers come from the accepted formal artifact. The page states that 485 dates were computed and 116 accepted 2026H1 dates were reused with hash and quality verification. It displays raw frequency and descriptive changes only. Fixed-delay peaks may be described as compatible with automated timing, batch processing, or common risk clocks, but not identified as institutional activity without participant labels.
