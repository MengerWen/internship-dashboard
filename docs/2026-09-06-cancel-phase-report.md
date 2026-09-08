# 撤单相位因子 601 日报告：构建与核验

交付文件为 `content/daily/2026-09-06.html`，全部图表和汇总数据内嵌，约 12 MB，可直接离线阅读。站点通过同日期 Markdown 日报与 `.show.html` 展示入口发现报告；展示版从 `content/assets/cancel-phase-2026-09-06/` 加载同源图片。

报告从 2026-08-24 的撤单等待时间预检引出七类、24 列因子的构造，说明相位、年龄周期、核尺度和不同分母的业务含义。收益标签为同日 09:35 前最后成交价至 [09:44,09:45) VWAP 的收益。全区间、年份、半年、季度、月份共 45 个统计入口；因子检索支持定义族、周期、核尺度和正式列名。

## 输入与计算

- 预检源：`content/daily/2026-08-24.show.html` 中的 `visual-data`；本页重绘 50ms 每日标准化分布、601 日热力图与月度轨迹。峰位、月度中位数和频带份额沿用源数据的消息权重；分期形状图先对每日归一，再对交易日等权。
- 正式数值：wangly 封存结果中的 601 个因子分片、601 个标签分片、10 个评价文件，共 1,212 个文件、479,143,970 bytes。逐文件路径及 SHA-256 见资产目录的 `input-manifest.json`。
- 原始输入只下载到被 Git 忽略的 `data/cancel-phase-2026-09-06/raw/`，不写回服务器，也不修改研究仓库代码。
- 本地补算展示所需的完整十分组、收益排名诊断、原值分布、全量散点 OLS 和配对定义数值差。分组使用成对有效样本的平均秩百分位，不拆并列值；每日组内股票等权、区间内有效交易日等权。
- 对 14,424 个日期与因子组合逐一比较正式评价中的最高组、最低组人数与收益差，最大收益差绝对误差为 0。共 1,080 条区间 NW t 也与正式 Rank IC 统计核对一致。
- 全部 1,719,612 个股票日期键一对一匹配，1,710,977 个收益标签有效；并验证有效价格对应的收益公式。

`report.json` 保存汇总数字、逐日日度 IC 和报告审计信息，不含股票代码或逐笔行情。126 张静态图使用 Matplotlib 绘制并保存为 WebP；各因子的散点图与 OLS 使用全部成对有效股票日，十分组交互图使用同一份已核验的区间汇总数据，可导出 SVG 与 CSV。

## 构建

只重建 HTML，无需服务器与原始股票日数据：

```powershell
python -X utf8 tools/build_cancel_phase_report_20260906.py --render-only
```

重新读取面板、核验并生成图表：

```powershell
python -X utf8 tools/fetch_cancel_phase_report_inputs.py `
  --manifest '<本地已验收的 CANCEL_PHASE_2024_2026Q2_RESULT.json>' `
  --destination data/cancel-phase-2026-09-06/raw
python -X utf8 tools/build_cancel_phase_report_20260906.py
```

构建依赖 Python、NumPy、pandas、PyArrow、Matplotlib、Pillow；Windows 下使用微软雅黑绘图，其他环境需有可显示中文的 Matplotlib 字体。`--render-only` 直接复用提交的图表，不受绘图字体影响。

## 核验

```powershell
python -X utf8 -m unittest discover -s tests -p test_cancel_phase_report.py
npx playwright test -c tests/cancel-phase-report.config.cjs
D:\MG\anaconda3\python.exe build.py --offline
```

数值测试覆盖并列值、缺失标签、样本守恒、独立 IC/Rank IC 复算、累计和及含截距 OLS。浏览器测试覆盖单文件离线加载全部 126 张图、因子筛选、六主题切换与键盘导航、区间选择、人工相位示意、下载、图片放大和手机宽度，禁止离线页发出 HTTP 请求；另检查站点展示版同源图片。

## 阅读边界

预检与评价共用历史区间，属于历史筛查。全期 Rank IC 较弱与部分因子负的 G10−G1 毛收益并存；报告保留原始方向，没有把负信号翻转成策略收益。六组事件对／跨订单对配对的差异仅约 10⁻¹⁶，不能把严格不相等误读为新信息。原始末位差异保留，不擅自舍入后重算正式 IC。

顶部六个标签页支持横向切换详情主题。图表区间选择更新指标、覆盖率、十分组及诊断表；日度、月度、原值分布和 OLS 散点保留全历史，并在图注中明示。研究结果封存状态、阶段 revision、实测时间与执行／样本外限制均放在报告附录。报告仓库的提交不改变封存研究数值。

分组与诊断页同时展示两类误差棒：日内组内方差平均值的平方根，以及组日均收益序列的 95% Newey–West 均值区间（lag 1）。日期选择更新全部 45 个区间的误差棒与数据下载。可用 `python -X utf8 tools/build_cancel_phase_report_20260906.py --dispersion-only` 从已核验面板补算该部分，完整构建也会自动计算。
