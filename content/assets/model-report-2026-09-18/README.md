# 2026-09-18 模型报告：2026-09-21 复算

展示版 `content/daily/2026-09-18.show.html` 与主日报 `content/daily/2026-09-18.md` 记录 328 因子模型的修正后结果。f97 买侧、卖侧不参与训练；09:35 固定选股预算；进场未成交的名额持有现金；出场窗口未成交的已进场股票保留在逐股账本，使用 09:46 前最后一笔有效成交价估值。

`report-data.json` 保存训练/测试指标、1000 轮 validation 曲线、176 日 test 日度及月度结果、328 列映射、运行路径和生成输入的 SHA-256。页面自包含相同 JSON 和 SVG 图，不依赖外部 CDN。完整逐股账本、模型权重、guard 记录、业务日志和哈希证据保存在服务器各运行目录；页面仅汇总账本状态。

在仓库根目录用只读下载的训练与测试产物生成：

```powershell
python scripts/download_model_report_20260921.py --output artifacts/model-report-2026-09-21/input
python scripts/build_model_report_20260921.py --input artifacts/model-report-2026-09-21/input
python -m pytest tests/test_model_report_20260918.py -q
python build.py
```

浏览器核对时，在仓库根目录启动 `python -m http.server 8019 --bind 127.0.0.1`，运行 `node scripts/verify_model_report_20260918.cjs`；脚本检查桌面与手机视口、下载、控制台报错和看板内嵌展示。

输入目录不提交 Git。`run_paths.json` 指明业务 revision、训练与测试运行目录。生成器验证模型列数、f97 排除、validation 选轮、测试天数、账本状态数与逐股收益之和，然后覆盖日报和展示版。测试还从页面嵌入的逐日序列重算 Sharpe 和 RankIC。

日度收益是固定窗口毛估值，不是已平仓的连续资金净值；未模拟交易费用、后续卖出或跨日持仓。此次 test 使用已在先前报告中观察过的日期，不是新盲测；旧新结果同时改变了输入和会计口径，属于观察性对照。
