# 全部因子的 601 日评价证据

归档日期：2026-09-16。评价完成日期：2026-09-17。

`evaluation_result.json` 记录本次收益评价：601 日、284 列正式因子、4 列诊断指标、1,719,612 个股票日和 1,710,977 个有效收益股票日。复用标签的文件身份见 `label_inventory.json`，导入验收见 `_IMPORT_VERIFIED.json`；逐日股票日键与有效收益数量见 `label_alignment.json`。

`guard.json` 为本次评价的实际资源记录。退出码为 0，计算结束后 scope 已清空；8 核上限、24 GiB 内存上限、禁用交换区，实测峰值内存 3,190,628,352 字节。评价业务耗时 124.5 秒，守护进程记录的完整运行耗时 126.2 秒。原始因子生产守护进程的最终汇总超时与本次评价正常退出分开记录。

`factor-output-verification.json` 和 `factor-completed-handoff.json` 记录全部 601 日因子数值的独立输出检查与完成状态。`factor_preregister.yaml` 保存本批因子使用的冻结注册表；注册表文件哈希为 `4c11186ccf556a3a183da60f513defbd0f6a8cbdbb2864aabad8a9a5ef929c4b`。R19 参数内容哈希为 `40513893b34f31abf82ea5c7e54aa5d3be15456169e05ef0a52cd84f68826f27`，本次没有按收益标签重新定标。

`evaluate.py` 调用现有 `daily_cross_sectional_ics`、`quantile_groups`、`shape_bins` 和 `mean_uncertainty` 函数。每日至少 30 个成对样本才计算 IC；常数截面 IC 缺失。分组使用平均秩，保持相同值同组，空组不填零。收益先按每日组内股票等权，再按有效日期等权；超额收益减去该因子当日成对样本均值。普通误差线为均值 ± 2 日度标准误；NW t 使用 Bartlett lag 1。NW 统计按有效日期序列计算。

每列完整精度的数据放在相邻 `factors/` 目录，报告按需加载，并提供 JSON 下载。统计数组的顺序是：`mean, ordinary_se, nw_se_lag1, nw_t, valid_days, icir, positive_fraction`。`periods` 包含全期、年度、季度、月度共 44 个区间；`groups` 前 10 项是 G1—G10，后 40 项是 G1—G40，每组依次保存毛收益与超额收益统计。`daily_health` 的顺序为全部股票数、有限因子数、零值数、成对股票数、成对因子不同取值数。`daily_spread` 依次为 G10−G1、G40−G1、最高 20%−最低 20%。

本评价为历史样本内观测结果。多个定义共享证据，未做多重比较调整；毛收益未扣交易成本，未构成独立样本外验证或可执行策略回测。
