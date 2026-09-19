# 2026-09-18 模型试验图表数据

`report-data.json` 保存 176 日聚合结果、1000 轮 validation 曲线、十分组统计、资源采样、完整参数、330 列映射和诊断证据。未包含完整逐股预测或模型权重；诊断证据中保留少量极端股票日的聚合核查示例。

页面为自包含 HTML，内嵌同一份 JSON 和 18 张 SVG；无需外部 CDN。主日报与展示版必须同时存在，才能进入看板索引。

## 生成

```powershell
python scripts/build_model_report_20260918.py --input artifacts/model-report-2026-09-18/input --audit <研究仓库的2026-09-18-rankic-sharpe-audit-evidence目录>
python -m pytest tests/test_model_report_20260918.py -q
python build.py
```

输入目录不提交 Git。训练源为服务器 `ml-single-fit-benchmark/ml-single-fit-cpu-l2-20260918-r04`，test 源为 `ml-single-fit-test/ml-single-fit-cpu-l2-test-lssharpe-i0659-20260918-r01`。生成器读取既有文件，无数据库查询、因子计算或训练调用。源文件哈希见 JSON 的 `source_files`；训练脚本、依赖、模型身份另列在对应字段。

## 浏览器验证

在仓库根目录启动 `python -m http.server 8019 --bind 127.0.0.1`，再运行 `node scripts/verify_model_report_20260918.cjs`。使用本机 Chrome 无头模式，检查 1440px / 390px 视口、图表数量、放大、因子检索、下载、控制台及横向溢出。截图写入忽略的 `test-results/`。

## 统计定义

正式组合：先按进场可选基数取比例，边界同分全纳入，再执行方向封板过滤；对有效标签计算均值。十分组诊断：同一基数按平均秩分组，不执行方向封板过滤；先算每日组内均值、中位数和截面样本标准差，再对日期等权。超额序列减去同日可选基数内有效标签的等权收益。各层统计不得混作同一指标。
