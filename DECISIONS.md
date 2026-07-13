# DECISIONS

- 2026-07-07: 阶段色采用低饱和冷灰到极昧黄序列,保证深色底上可区分且不过度偏离 PLAN 指定色板。
- 2026-07-07: Noto Serif SC 与 Libre Baskerville 使用本地 woff2 文件自托管,避免在线字体 CDN 依赖。
- 2026-07-07: 离线构建保留 CSS/JS/字体为同文件夹资源,将 manifest 与内容片段内联进 index.html,满足 file:// 双击使用。
- 2026-07-07: Showcase 为 config.json 中没有 Markdown 的阶段自动生成规划中占位片段,确保 stepper 始终覆盖全部阶段。
- 2026-07-07: `.show.html` 使用 sandbox iframe `srcdoc` 且只允许 `allow-scripts`,不加 `allow-same-origin`,以隔离定制页脚本。
- 2026-07-07: Daily 展示模式单列布局采用 JS 显式模式类 `.is-show-mode`,不使用 `:has()`,避免兼容性差异并复用现有状态管理。
- 2026-07-07: 离线 `.show.html` 改用 JSON script 载体内联完整 HTML,避免 `<template>` 经 HTML 解析后剥离 doctype、`html`、`head`、`body` 等结构标签。
- 2026-07-13: Mermaid 11.16.0 浏览器运行时随站点自托管；Markdown 构建期输出 `.mermaid` 容器，动态内容插入后由 `ContentEnhancer` 显式调用 `mermaid.run()`，保证正式站、下载页和离线版一致可用。
