# 2026-09-18 模型试验图表数据

`report-data.json` 保存 176 日聚合结果、1000 轮 validation 曲线、十分组统计与逐日 RankIC 分解、15 折扩张验证的日期边界、资源采样、完整参数、330 列映射和诊断证据。未包含完整逐股预测或模型权重；诊断证据中保留少量极端股票日的聚合核查示例。

页面为自包含 HTML，内嵌同一份 JSON 和 27 张 matplotlib SVG；公式使用 MathML，无需外部 CDN 或数学排版库。`figures/` 另存同一批图的 SVG 与 PNG，供单独查看和引用。新增诊断包括 RankIC/多空收益四象限、组间/组内秩信息分解、两腿协方差、尾部宽度敏感性与个股贡献集中度。主日报与展示版必须同时存在，才能进入看板索引。

## 生成

```powershell
python scripts/build_model_report_20260918.py --input artifacts/model-report-2026-09-18/input --audit <研究仓库的2026-09-18-rankic-sharpe-audit-evidence目录>
python -m pytest tests/test_model_report_20260918.py -q
python build.py
```

输入目录不提交 Git。训练源为服务器 `ml-single-fit-benchmark/ml-single-fit-cpu-l2-20260918-r04`，test 源为 `ml-single-fit-test/ml-single-fit-cpu-l2-test-lssharpe-i0659-20260918-r01`。生成器读取既有文件，无数据库查询、因子计算或训练调用。源文件哈希见 JSON 的 `source_files`；训练脚本、依赖、模型身份另列在对应字段。

## 浏览器验证

在仓库根目录启动 `python -m http.server 8019 --bind 127.0.0.1`，再运行 `node scripts/verify_model_report_20260918.cjs` 与 `node scripts/verify_model_report_readout_20260918.cjs`。使用本机 Chrome 无头模式，检查 1440px / 390px 视口、图表数量、放大、因子检索、下载、控制台及横向溢出。截图写入忽略的 `test-results/`。

图表编号由模板中 `@@key@@` 的出现顺序自动推导，移动图表位置即可，不需手工维护编号。正文分为 10 个章节：`setup / validation / test / explain / deciles-view / rankic / portfolio / audit / performance / evidence`，导航链接与章节顺序必须一一对应，单个章节最多 6 张图（由 `tests/test_model_report_20260918.py` 约束）。图表使用透明画布，直接落在页面纸色上，不再套白底边框；导出到 `figures/` 的 PNG 会补上纸色。图表样式集中在 `scripts/report_charts.py`：刻度使用 nice-number 分档，内存、核数、耗时等非负量的坐标轴从 0 起；每张内联 SVG 的元素 id 加图表前缀，避免同一页面内冲突。

## 统计定义

正式组合：先按进场可选基数取比例，边界同分全纳入，再执行方向封板过滤；对有效标签计算均值。十分组诊断：同一基数按平均秩分组，不执行方向封板过滤；先算每日组内均值、中位数和截面样本标准差，再对日期等权。超额序列减去同日可选基数内有效标签的等权收益。各层统计不得混作同一指标。

RankIC 三种口径不可混用：**子池 RankIC** 把横截面限制到指定分组后重新排名，口径与全体完全一致，可直接与 0.0220 比较；**贡献分解**是每只股票的分数秩偏差乘收益秩偏差除以同一归一化分母，按分组求和后十组之和精确等于当日 RankIC，单位不是相关系数；**组内 RankIC** 只在该组内部重新排名，与贡献不可相加。子池口径受范围效应影响（去掉中段会抬高秩相关），页面已声明该层未排除，等间隔对照 D1∪D5∪D10 一并发布。十分组的日均收益误差棒为 Newey-West 标准误（Bartlett 核，lag = 4）乘 1.96，衡量均值估计精度，不是个股收益范围。

时间划分：2024H1 的 117 日为起始训练期，其后逐自然月扩张验证，2024-07 至 2025-09 共 15 折、308 个 validation 交易日；test 为 2025-10-09 至 2026-06-30 的 176 日。本次结果只来自第 15 折，其余 14 折未运行，图表与正文必须保持这一区分。

## 悬停读数

27 张图都可以把鼠标停在图上读出光标处的数值，放大对话框里的副本同样可用。读数不改图：SVG 仍是 matplotlib 出的那张，页面在上面盖一层 `div`，画十字线、band 高亮、圆点和数值框。

每张图的读数内容由 `scripts/build_model_report_20260918.py` 里紧跟 `publish(...)` 的 `readout(...)` 给出，写进页面的 `#readout-data`。规格里只有数据坐标和已经排好版的字符串，没有像素：

- `mode: 'x'` — 折线图。共用一条 x 轴，按最近的 x 取值，所有序列一次读出（validation 三条曲线、累计收益、日度 RankIC、内存、CPU）。
- `mode: 'point'` — 散点图，取离光标最近的点（RankIC 与多空收益）。
- `mode: 'bandx'` / `'bandy'` — 柱状图与条形图，落在哪个类别区间就读哪一类。
- `axes` — 由 `rc.render()` 在画完之后回填的各 Axes 数据范围；`tail-breadth` 的 Sharpe 线走第二条 y 轴，靠 `marks` 里的轴序号定位。

像素换算全部发生在浏览器里：matplotlib 把每个 Axes 的背景矩形写在该 Axes 分组的最前面，页面量这个 `path` 的 `getBoundingClientRect()` 得到绘图区，再配合 `axes` 的数据范围做线性映射。因此改图尺寸、窗口缩放、手机上横向滚动都不需要重算规格。新增图表若忘了写 `readout(...)`，构建时的 `assert set(readouts) == set(FIGURE_ORDER)` 会直接失败。

读数的落点精度由 `node scripts/verify_model_report_readout_20260918.cjs` 校验：把规格换算出的坐标与 SVG 里 matplotlib 实际画出的散点、双轴标记逐一比对，同时逐图悬停核对数值框的标题，并在 390px 视口把图横向滚到底再测一次。
