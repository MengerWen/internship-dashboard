# 2026-07-31 算法行为因子报告双版本

本目录保存“当前版本”——完整、自包含、可以直接离线打开的 HTML：

`2026-07-31-算法行为因子构建链路与165口径实测全景报告.current.self-contained.html`

- 该文件保留原始 165 个口径、55 个思路、660 张 Notebook 图片以及内嵌 KaTeX 资源。
- SHA256：`D632D167EF5AF0E5F1EC573FB4A4598E071B949CB3F78952F80A97ADB0648BC1`。
- 文件约 46.63 MiB，超过 Cloudflare Workers Static Assets 的 25 MiB 单文件限制，因此不参与网站构建。

网站部署版本位于：

`content/daily/2026-07-31.show.html`

它与当前版本使用同一份报告数据，只把内嵌 PNG 拆分到
`content/assets/factor-report-2026-07-31/`，不会删图、改指标或改变报告交互。

重新生成网站版本：

```powershell
python tools/build_factor_report_web_version.py
```

生成后的 `manifest.json` 记录两个 HTML 的 SHA256、图片引用数、去重后资源数与单文件体积检查结果。
