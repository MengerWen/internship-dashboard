# DECISIONS

- 2026-07-07: 阶段色采用低饱和冷灰到极昧黄序列,保证深色底上可区分且不过度偏离 PLAN 指定色板。
- 2026-07-07: Noto Serif SC 与 Libre Baskerville 使用本地 woff2 文件自托管,避免在线字体 CDN 依赖。
- 2026-07-07: 离线构建保留 CSS/JS/字体为同文件夹资源,将 manifest 与内容片段内联进 index.html,满足 file:// 双击使用。
- 2026-07-07: Showcase 为 config.json 中没有 Markdown 的阶段自动生成规划中占位片段,确保 stepper 始终覆盖全部阶段。
