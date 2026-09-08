# 2026-09-08 盘口深度匹配全历史交付

601 日面板、标签核验、24 列完整评价、独立复算、离线报告和 24 个 notebooks 全部完成。结果状态为 **accepted**，已封存，未同步到其他账户。

[离线报告](<D:/MG/_GitLinked/Quant_Research-Trading/26 Summer/❗思瑞投资/sirui-quant-research/.local-output/depth-match-implementation/full-history-review/2026-09-08-depth-match-factor-evaluation.show.html>) · [完整本地阅读包 ZIP](<D:/MG/_GitLinked/Quant_Research-Trading/26 Summer/❗思瑞投资/sirui-quant-research/.local-output/depth-match-implementation/2026-09-08-depth-match-full-history-review.zip>) · [封存结果](<D:/MG/_GitLinked/Quant_Research-Trading/26 Summer/❗思瑞投资/sirui-quant-research/reports/2026-09/2026-09-08-depth-match-full-history-evidence/DM_RESULT.json>) · [独立审计](<D:/MG/_GitLinked/Quant_Research-Trading/26 Summer/❗思瑞投资/sirui-quant-research/reports/2026-09/2026-09-08-depth-match-full-history-evidence/evaluation/independent_ic_audit.json>)

## 1. 业务版本

因子、新评价、报告和 notebook 的业务 revision 均为 `147ab55c38939f3754ced42576c1b82c0b2d60f0`。沿用已通过 27.162803735 秒单日验收的计算路径，研究参数与资源合同没有变更。

601 日标签均复用已核验产物，源业务 revision 为 `9d2a97aeefaff710736a51ead5a01bf5d374f179`。源逐日 manifest、spec、股票键、输入来源和文件 hash 已验证，并确定性投影到本次股票池；未新算标签。源路径及 601 日清单见 labels/label_inventory.json。

## 2. 服务器状态

wangly 在最终检查 `2026-09-08T12:54:33.102255+00:00`（UTC）时 HEAD=`147ab55c38939f3754ced42576c1b82c0b2d60f0`、branch=`main`、checkout clean。主 launcher PID 1757813 正常退出，四个业务阶段 guard 全部 exit=0；额外 notebook guard 也正常退出，scope 已 inactive。

## 3. 本地提交

本任务业务代码与交付记录位于本地 `main`。业务 revision 见第 1 节；本报告和封存核验副本作为独立交付提交，提交号见交付消息。

## 4. 正确性和研究结果

日期为 2024-01-02—2026-06-30，共 601 日：2024 年 242 日、2025 年 243 日、2026H1 116 日。逐日股票池完整，24 列始终保留原始方向。面板共 1,719,612 个唯一股票日；有效同日收益标签 1,710,977 个，空标签 8,635 个，未填零，未用标签有效性提前筛选股票池。

14,424 个因子日均可评价，独立复算全部通过：相关最大绝对差 `3.8857805861880479e-16`，阈值 atol=1e-12、rtol=1e-10；整数计数、组别和 NaN 模式一致。组内/组间方差分解最大误差 `8.9785492408955836e-20`，无失败项。正式因子分母、分子、可观测/未知数量及范围校验均通过。

下表为全期日度等权结果，全部保留，不按方向自动翻转。NW 使用 Bartlett lag=1；这些是同一历史样本的观察性筛查，未校正多重比较，不作为交易收益或因果结论。

| 正式列 | Pearson IC 均值 | Rank IC 均值 | Rank IC NW t | 有效日 |
|---|---:|---:|---:|---:|
| `dm01_exact_buy` | 0.004692 | 0.004954 | 1.0222 | 601 |
| `dm01_exact_sell` | -0.011468 | -0.011185 | -2.2059 | 601 |
| `dm02_confirmed_buy` | 0.004677 | 0.004950 | 1.0216 | 601 |
| `dm02_confirmed_sell` | -0.011480 | -0.011183 | -2.2054 | 601 |
| `dm03_price_room_buy` | 0.002493 | -0.005174 | -1.0272 | 601 |
| `dm03_price_room_sell` | 0.007360 | -0.002550 | -0.5092 | 601 |
| `dm04_price_cap_buy` | 0.004963 | 0.007175 | 1.5590 | 601 |
| `dm04_price_cap_sell` | -0.017541 | -0.014622 | -2.9736 | 601 |
| `dm05_lot_floor_buy` | 0.004916 | 0.005184 | 1.0694 | 601 |
| `dm05_lot_floor_sell` | -0.011388 | -0.011089 | -2.1877 | 601 |
| `dm06_soft_under_buy` | 0.004794 | 0.005056 | 1.0443 | 601 |
| `dm06_soft_under_sell` | -0.011483 | -0.011223 | -2.2147 | 601 |
| `dm07_fresh_match_buy` | -0.004089 | 0.004766 | 1.3134 | 601 |
| `dm07_fresh_match_sell` | -0.015779 | -0.007459 | -1.7812 | 601 |
| `dm08_adaptive_repeat_buy` | 0.009513 | -0.000848 | -0.2052 | 601 |
| `dm08_adaptive_repeat_sell` | -0.006405 | -0.014687 | -3.3152 | 601 |
| `dm09_two_level_buy` | 0.002674 | -0.009400 | -2.2248 | 601 |
| `dm09_two_level_sell` | 0.005512 | -0.004620 | -1.0753 | 601 |
| `dm10_excess_cancel_buy` | -0.000891 | -0.003809 | -1.5258 | 601 |
| `dm10_excess_cancel_sell` | -0.004694 | -0.006758 | -2.5380 | 601 |
| `dm11_recent_buy` | 0.012436 | 0.009354 | 1.9682 | 601 |
| `dm11_recent_sell` | -0.014932 | -0.019543 | -3.9970 | 601 |
| `dm12_persistent_buy` | 0.005990 | 0.002774 | 0.5464 | 601 |
| `dm12_persistent_sell` | -0.009661 | -0.012839 | -2.4158 | 601 |

已生成全期、年/半年、10 季度、30 月共 44 个分期；十分组均值/NW 区间、组内离散度、收益排名/中位数/缩尾/尾部贡献、端点差、OLS、分布、内部相关和有效秩均保存为独立评价文件。每个因子全范围及放大散点均输入全部 1,710,977 个成对有限样本，不抽样；放大仅改变显示范围。

## 5. 实测性能

| 阶段 | guard wall 秒 | CPU 秒 | 峰值 GiB |
|---|---:|---:|---:|
| evaluation | 187.666 | 124.032 | 8.127 |
| labels | 112.523 | 17.989 | 1.843 |
| panel | 8317.326 | 63102.085 | 11.886 |
| report | 108.798 | 54.755 | 6.645 |
| notebooks | 154.029 | 19.670 | 0.295 |

面板阶段 guard 实测 8,317.33 秒，约 2 小时 18 分钟；panel 内部记录 8,220.24 秒。label inventory 记录的复用处理 wall 为 60.74 秒，新标签计算 wall 为 0；不可把复用读取称为新标签计算性能。报告绘制/生成段为 45.02 秒，其 guard 还包含输入核验与加载。各阶段独立记录，不用重叠阶段相加冒充完整 wall。

所有 guard 均保持 100G、账户 memory.high=120 GiB、16 核配额、16 worker、每批 32 只、委托/成交/撤单分片 4/3/1、内部线程 1。阶段均无 OOM、swap 或 CPU 限流，最高内存约 11.89 GiB。进度、JIT、notebook runtime 和计算临时文件均使用已批准的 /tmp tmpfs。

五轮单日性能证据保留：29.710029 秒（业务未完成，不作基线）、44.865165、45.111377、39.363653、27.162804 秒（最后四轮完整正确，第五轮达标）。详见 2026-09-08-depth-match-single-day-acceptance.md 及其 PERFORMANCE_COMPARISON.json。

## 6. 实际验证与边界

- 225 项相关业务回归、17 项标签回归、79 项读取/调度回归通过；补充小块读取测试后读取模块 34 项通过。未运行全仓库所有测试。
- 24 个真实 notebooks 的全部代码单元已用 Python kernel 执行，无错误；输出、单元执行计数、文件 hash、执行审计及额外 guard 证据已保存。
- 真实离线 HTML 已在浏览器打开，120 张图全部加载；24 因子详情、编号检索、44 分期切换、日期过滤均通过。2026H1 日度过滤为 116 行。
- JSON、CSV、PNG 各实际下载一个并核对 hash；139 个内嵌下载产物已逐一校验，评价 CSV/JSON 与评价 manifest 一致。
- 自选日期筛选日度明细，时期选择切换预计算统计；静态图与 OLS 明确保持全期范围。此显示口径在页面中标明。
- 没有剩余的本计划必需验收项；未进行交易策略回测、身份识别、参数寻优或跨账户同步，它们不属于本任务。

## 7. 外推

未用单日乘以 601 估计全历史性能。本报告所有阶段耗时均来自本次实际运行；不承诺其他日期、负载或后续重跑一定达到相同速度。

## 8. 参数批准

数量网格 100 股、软匹配容差 1%、严格 1 秒深度滞后、相邻间隔 ≤1 秒、撤余量 ≤100ms、半衰期 60 秒、5 个一分钟持续性箱，以及混合未知聚合规则和当前资源配置，均随本次全历史批准合同沿用，没有新增未经批准的研究参数。批准记录保存在 approval/approval_record.json。

## 9. 产物与证据路径

完整 RUN_ROOT：`/home/wangly/hdd-store/outputs/sirui/published/open5m-depth-match/20260908T100452Z-full-history-i01-147ab55`。实际 HOT_ROOT：`/tmp/sirui-wangly/open5m-depth-match/20260908T100452Z-full-history-i01-147ab55`。

```text
launcher.sh / launcher.pid / launcher.log / launcher_exit_code.txt
panel.log / labels.log / evaluation.log / report.log / notebooks.log
panel_guard_manifest.json / labels_guard_manifest.json
evaluation_guard_manifest.json / report_guard_manifest.json / notebooks_guard_manifest.json
guard_finalized.json / progress_final.json / orphan_inventory.json
approval/approval_record.json / approval/hot_path_approval.json
panel/run_manifest.json / panel/days/<601 dates>/{factors.parquet,diagnostics.parquet,manifest.json,telemetry.json,COMPLETE.json}
labels/label_inventory.json / labels/days/<601 dates>.parquet
evaluation/evaluation_manifest.json / evaluation/<CSV,Parquet,JSON>
report/2026-09-08-depth-match-factor-evaluation.show.html / report/assets/<120 PNG>
report/report.json / report/REPORT_AUDIT.json / report/BROWSER_AUDIT.json
notebooks/<24 executed ipynb> / notebooks/NOTEBOOK_INDEX.json
notebooks/EXECUTION_AUDIT.json / notebooks/GUARD_FINALIZED.json
DM_RESULT.json / evidence/SHA256SUMS / RUN_SEAL.json
```

本地封存核验副本：`D:/MG/_GitLinked/Quant_Research-Trading/26 Summer/❗思瑞投资/sirui-quant-research/reports/2026-09/2026-09-08-depth-match-full-history-evidence`。阅读包位于 `D:/MG/_GitLinked/Quant_Research-Trading/26 Summer/❗思瑞投资/sirui-quant-research/.local-output/depth-match-implementation/full-history-review`，包含离线 HTML、全部下载 CSV/JSON、120 图、24 个执行后的 notebooks 和 notebook 所需 daily_ic.parquet。该阅读包是便于审阅的子集，完整 601 日原始因子/诊断及标签分片仍保存在服务器 RUN_ROOT。阅读包 ZIP 可直接解压后使用，notebooks 从其 notebooks/ 目录启动。

## 10. 封存与监控

封存时刻 `2026-09-08T12:55:04.278153+00:00`（UTC），状态 accepted；SHA256SUMS 覆盖 3820 个文件，result hash=`94680836377dbf9fb5c3084fb42e9ac9e1c3a78b96ea3ddb03c4f87a6230eadc`，inventory hash=`a8206c157c16dd1acdc92bb9b5a8f091ef50bf5bb73c9078a9961f463a30faab`。本地已按 seal 与 inventory 核对所复制文件，保留原始字节。

远程结果封存后不再修改。没有删除 output、scratch 或任一运行证据。全项交付后停止 dm-601 监控；未同步至 wenjie。
