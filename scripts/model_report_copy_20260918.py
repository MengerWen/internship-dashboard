"""Refresh the original report's result text without changing its layout or controls."""

from __future__ import annotations

import numpy as np


def refresh(report, evidence, positions):
    summary = evidence['test_summary']
    overall = summary['overall_metrics']
    selection = evidence['selection']
    selected = selection['selected_validation_row']
    full = evidence['training_summary']['final_validation_metrics']
    training = evidence['training_summary']
    times = training['timings_seconds']
    train_resources = training['resources']
    test_resources = summary['resources']
    identity = evidence['model_identity']
    code = evidence['code_identity']
    extra = evidence['extra_analysis']
    audit = evidence['audit']
    daily = evidence['test_daily']
    deciles = evidence['deciles']
    diag = evidence['diagnostics']
    iteration = selection['selected_iteration']
    count = summary['feature_count']
    ls = overall['long_short_sharpe']
    ic = overall['mean_daily_rank_ic']
    ls_mean_bp = overall['long_short_mean_daily_return'] * 1e4
    long_mean_bp = overall['pure_long_mean_daily_return'] * 1e4
    short_mean_bp = overall['pure_short_mean_daily_return'] * 1e4
    ls_daily = np.array([row['long_short_return'] for row in daily], dtype=float)
    long_daily = np.array([row['pure_long_return'] for row in daily], dtype=float)
    short_daily = np.array([row['pure_short_return'] for row in daily], dtype=float)
    one_leg_compound = (np.prod(1 + ls_daily) - 1) * 100
    half_legs_compound = (np.prod(1 + ls_daily / 2) - 1) * 100
    variance = diag['variance_decomposition']
    december = next(month for month in summary['monthly_metrics'] if month['month'] == '2026-03')
    february = next(month for month in summary['monthly_metrics'] if month['month'] == '2026-02')
    ls_positions = positions[positions.portfolio.isin(['long_short_long', 'long_short_short'])]
    tail_1 = ls_positions.loc[ls_positions.underlying_return.abs() > .01, 'portfolio_contribution'].sum() / len(daily) * 1e4
    tail_5 = ls_positions.loc[ls_positions.underlying_return.abs() > .05, 'portfolio_contribution'].sum() / len(daily) * 1e4
    status = audit['position_status_counts']
    gib = 2 ** 30

    def swap(old, new):
        nonlocal report
        occurrences = report.count(old)
        if occurrences != 1:
            raise ValueError(f'expected one original report claim, found {occurrences}: {old[:100]}')
        report = report.replace(old, str(new), 1)

    def metric_row(label, item):
        return (f'<tr><td>{label}</td><td>{int(item["iteration"])}</td>'
                f'<td>{item["validation_mean_rank_ic"]:.6f}</td>'
                f'<td>{item["validation_daily_equal_mse"]:.6f}</td>'
                f'<td>{item["long_short_sharpe"]:.3f}</td>'
                f'<td>{item["pure_long_sharpe"]:.3f} / {item["pure_short_sharpe"]:.3f}</td></tr>')

    swap('330 因子 CPU LightGBM：15 折扩张验证中已运行的第 15 折、第 659 轮的选择过程',
         f'{count} 因子 CPU LightGBM：15 折扩张验证中已运行的第 15 折、第 {iteration} 轮的选择过程')
    swap('<title>从 330 个因子到一个回归模型', f'<title>从 {count} 个因子到一个回归模型')
    swap('结果整理 2026.09.19', '结果整理 2026.09.21')
    swap('<h1>从 330 个因子，', f'<h1>从 {count} 个因子，')
    swap('冻结 validation 选出的第 659 轮', f'冻结 validation 选出的第 {iteration} 轮')
    swap('<div class="big">7.30</div>', f'<div class="big">{ls:.2f}</div>')
    swap('日均 RankIC 只有 0.0220。换成多空真正交易的 D1∪D10 池子，同一口径下是 0.0448。',
         f'日均 RankIC 只有 {ic:.4f}。换成多空真正交易的 D1∪D10 池子，同一口径下是 {next(p for p in evidence["rank_ic_pools"] if p["key"] == "long_short")["mean_rank_ic"]:.4f}。')
    swap('<strong>330</strong>输入因子', f'<strong>{count}</strong>输入因子')
    swap('<strong>659 / 1000</strong>', f'<strong>{iteration} / 1000</strong>')
    swap('第 659 轮是在这一折', f'第 {iteration} 轮是在这一折')
    swap('<h3>330 列输入：', f'<h3>{count} 列输入：')
    swap('<b>258</b>旧因子', '<b>256</b>旧因子')
    swap('f96、f97 保留，缺失值保留 NaN', 'f96 保留，f97 买卖两列均排除；缺失值保留 NaN')
    swap('f87、f88、f89、f90、f93、f94、f95、f129、f130、f135 的买卖两侧，共 20 列',
         'f87、f88、f89、f90、f93、f94、f95、f97、f129、f130、f135 的买卖两侧，共 22 列')
    swap('共 6 列；另排除 f22–f25 诊断列。正式 284 列减去 26 列，得到 258 列。完整 330 列映射',
         '共 6 列；另排除 f22–f25 诊断列。正式 284 列减去 28 列，得到 256 列。完整 328 列映射')
    swap('使用 validation 的第 659 轮', f'使用 validation 的第 {iteration} 轮')
    swap('截取前 659 轮', f'截取前 {iteration} 轮')
    old_rows = ('<tr><td>validation 选用</td><td>659</td><td>0.016604</td><td>2.388807</td><td>10.500</td><td>4.235 / −1.208</td></tr>'
                '<tr><td>validation 完整模型</td><td>1000</td><td>0.014269</td><td>2.392587</td><td>8.597</td><td>3.978 / −1.373</td></tr>'
                '<tr><td>test 冻结模型</td><td>659</td><td>0.022040</td><td>2.329553</td><td>7.301</td><td>3.014 / 0.576</td></tr>')
    test_row = (f'<tr><td>test 冻结模型</td><td>{iteration}</td><td>{ic:.6f}</td>'
                f'<td>{overall["daily_equal_mse"]:.6f}</td><td>{ls:.3f}</td>'
                f'<td>{overall["pure_long_sharpe"]:.3f} / {overall["pure_short_sharpe"]:.3f}</td></tr>')
    swap(old_rows, metric_row('validation 选用', selected) + metric_row('validation 完整模型', full) + test_row)
    swap('<b>7.30</b><small>日均 13.01bp；日波动 28.29bp</small>',
         f'<b>{ls:.2f}</b><small>日均 {ls_mean_bp:.2f}bp；日波动 {np.std(ls_daily, ddof=1) * 1e4:.2f}bp</small>')
    swap('<b>3.01</b><small>日均 7.36bp；日波动 38.76bp</small>',
         f'<b>{overall["pure_long_sharpe"]:.2f}</b><small>日均 {long_mean_bp:.2f}bp；日波动 {np.std(long_daily, ddof=1) * 1e4:.2f}bp</small>')
    swap('<b>0.58</b><small>日均 1.40bp；日波动 38.68bp</small>',
         f'<b>{overall["pure_short_sharpe"]:.2f}</b><small>日均 {short_mean_bp:.2f}bp；日波动 {np.std(short_daily, ddof=1) * 1e4:.2f}bp</small>')
    swap('每日选股基数为因子交集内、未停牌且进场分钟有成交的股票，不预先按出场标签筛选。',
         '09:35 前的因子交集与可得日线状态确定选股基数，先排序并锁定每腿预算；进场分钟成交和出场标签都不参与选股。')
    swap('再去掉不可做对应方向的封板样本，不补位。no_long / no_short 要求进场分钟每笔成交都在对应涨跌停价 ±0.005 元内；日线无限价信息时不判封板。',
         '随后按进场成交及方向封板状态判断是否执行，失败预算留现金、不补位。no_long / no_short 要求进场分钟每笔成交都在对应涨跌停价 ±0.005 元内；日线无限价信息时不判封板。')
    swap('入选股票等额，组合均值仅用有效标签；入选但缺标签的只数另记。',
         '入选股票按锁定预算等额计权；未进场记现金 0 收益，已进场而出场分钟无成交的持仓保留在账本，并按 09:46 前最后可得成交估值。')
    swap('空组合记 0，多空任何一腿为空则整日记 0。', '空组合记 0；所有入选预算每天都进入固定分母。')
    swap('机械复合值为 25.62%；上图改为多空各 50%、总名义敞口 100%，机械复合值为 12.11%',
         f'机械复合值为 {one_leg_compound:.2f}%；上图改为多空各 50%、总名义敞口 100%，机械复合值为 {half_legs_compound:.2f}%')
    swap('2026 年 3 月的日均 RankIC 为 −0.00378，多空 Sharpe 仍为 5.09；2026 年 2 月多空 Sharpe 降至 2.57。',
         f'2026 年 3 月的日均 RankIC 为 {december["mean_daily_rank_ic"]:.5f}，多空 Sharpe 仍为 {december["long_short_sharpe"]:.2f}；2026 年 2 月多空 Sharpe 为 {february["long_short_sharpe"]:.2f}。')
    swap('本次日均 RankIC 只有 0.0220，但它与每日多空收益的相关系数为 0.862',
         f'本次日均 RankIC 只有 {ic:.4f}，但它与每日多空收益的相关系数为 {extra["daily_ic_ls_corr"]:.3f}')
    swap('年化 ICIR 为 4.84，而多空 Sharpe 为 7.30',
         f'年化 ICIR 为 {extra["ic_ir"]:.2f}，而多空 Sharpe 为 {ls:.2f}')
    swap('每天约有 2,875 只股票进入选股基数，多空各有约 287 只有效收益。',
         f'每天约有 {extra["mean_rank_base"]:,.0f} 只股票进入选股基数，多空每腿平均约有 {len(ls_positions) / (2 * len(daily)):,.0f} 只锁定预算。')
    swap('D9 约 3.9bp，D10 约 10.6bp',
         f'D9 约 {deciles[8]["mean"] * 1e4:.1f}bp，D10 约 {deciles[9]["mean"] * 1e4:.1f}bp')
    swap('日均 Pearson IC 为 0.0417，高于 RankIC 0.0220',
         f'日均 Pearson IC 为 {extra["mean_pearson_ic"]:.4f}，高于 RankIC {ic:.4f}')
    swap('报告里那个 0.0220，是在<strong>全体约 2,875 只股票</strong>上算的。',
         f'报告里那个 {ic:.4f}，是在<strong>每日有标签的约 {next(p for p in evidence["rank_ic_pools"] if p["key"] == "all")["mean_count"]:,.0f} 只股票</strong>上算的。')
    swap('约为全体 ' + f'{next(p for p in evidence["rank_ic_pools"] if p["key"] == "all")["mean_rank_ic"]:.5f}' + ' 的两倍',
         '高于全体同口径')
    swap('这十个数加起来仍然正好是 0.022040', f'这十个数加起来仍然正好是 {ic:.6f}')
    swap('D9 的样本均值为 −0.00364，正值日占 46.0%',
         f'D9 的样本均值为 {deciles[8]["inner_rank_ic"]:+.5f}，正值日占 {deciles[8]["inner_rank_ic_positive"]:.1%}')
    swap('正式口径的 3.01 / 0.58 / 7.30 只差方向封板过滤',
         f'正式口径的 {overall["pure_long_sharpe"]:.2f} / {overall["pure_short_sharpe"]:.2f} / {ls:.2f} 有所差异；正式账本还纳入进场失败与未退出估值')
    swap('十行相加等于日均 RankIC 0.022040', f'十行相加等于日均 RankIC {ic:.6f}')
    swap('<mn>13.0094</mn><mn>28.2881</mn></mfrac><mo>=</mo><mn>7.3005</mn>',
         f'<mn>{variance["long_short_mean_bp"]:.4f}</mn><mn>{variance["long_short_std_bp"]:.4f}</mn></mfrac><mo>=</mo><mn>{ls:.4f}</mn>')
    swap('多头 10% 日均 10.7879bp，空头 10% 日均盈利 2.2215bp。两篮子原始收益相关为 0.7354',
         f'多头 10% 日均 {variance["long_mean_bp"]:.4f}bp，空头 10% 日均盈利 {-variance["short_underlying_mean_bp"]:.4f}bp。两篮子原始收益相关为 {variance["underlying_leg_correlation"]:.4f}')
    swap('超过 1% 的部分贡献约 11.50bp，占多空日均收益约 88.4%；超过 5% 的部分贡献约 2.97bp。',
         f'超过 1% 的入选股票日合计贡献约 {tail_1:.2f}bp，占多空日均收益约 {tail_1 / ls_mean_bp:.1%}；超过 5% 的入选股票日合计贡献约 {tail_5:.2f}bp。')
    swap('该股票当日原始收益除以该腿有效持仓数', '该股票当日账本收益乘以事前锁定预算权重')
    swap('名称按 2026-09-20 的证券元数据快照展示',
         '名称尽量沿用 2026-09-20 的证券元数据快照，未核验的新股票只显示代码')
    swap('不能仅凭 RankIC 0.022', f'不能仅凭 RankIC {ic:.3f}')

    old_audit = ('<tr><td>独立重算全部 176 日评价</td><td>三类组合收益与 MSE 最大差为 0；RankIC 差约 2.8×10⁻¹⁷</td><td>支持现有预测与评价口径一致</td></tr>'
                 '<tr><td>全部 507,460 行重新聚合成交</td><td>505,403 个有效收益一致，最大差约 3.8×10⁻¹⁵；缺失/封板/基数无差异</td><td>支持同一数据库内标签计算一致</td></tr>'
                 '<tr><td>极端收益查逐笔，分钟价比日线范围</td><td>9 个股票日逐笔核验一致；全 test 窗口价无超出日线高低价</td><td>不是对行情供应商源数据的外部认证</td></tr>'
                 '<tr><td>3 日原始因子 → 标准化 → 预测</td><td>保存分数、原模型前 659 轮、659 轮文件一致</td><td>抽查预测路径，未重算上游因子</td></tr>'
                 '<tr><td>模型选择与日期、键</td><td>validation 最优仍为 659；train/validation 与 test 无日期交集，test 键唯一</td><td>不代表不存在其他形式的信息泄漏</td></tr>'
                 '<tr><td>每日随机打乱分数，100 条序列</td><td>Sharpe 中位数 0.064，95% 分位 1.898，最大 2.392</td><td>流程负对照，不是正式显著性检验；无新增 fit</td></tr>')
    new_audit = (
        f'<tr><td>176 日账本独立归并</td><td>逐日多空与正式结果最大差 {audit["ledger_daily_reconciliation_max_abs"]:.1e}</td><td>检验固定预算、入场失败和未退出持仓均进入归因</td></tr>'
        f'<tr><td>持仓状态逐笔保留</td><td>{status["exited"]:,} 笔退出；{status["entry_unfilled"]:,} 笔未进场；{status["open_marked"]:,} 笔未退出并估值</td><td>状态计数含三个组合，非独立股票日</td></tr>'
        f'<tr><td>未进场预算计现金</td><td>该状态绝对收益贡献最大 {audit["entry_unfilled_contribution_max_abs"]:.1f}</td><td>未把其余持仓权重事后放大</td></tr>'
        f'<tr><td>分钟 VWAP 原始成交核对</td><td>样本 {audit["sample_trade_vwap_consistency"]["date"]} / {audit["sample_trade_vwap_consistency"]["code"]} 的进出场 SQL 与项目聚合一致</td><td>单样本检查，非全量外部行情认证</td></tr>'
        f'<tr><td>模型身份与选轮</td><td>validation 在 {iteration} 轮取峰；冻结模型 {identity["selected_model_num_trees"]} 棵树，{count} 列</td><td>test 未重新训练，也未据 test 另选轮数</td></tr>'
        '<tr><td>尚未完成的外部复核</td><td>全量因子截断重算、逐笔执行与随机打乱负对照未执行</td><td>不能据本次报告断言端到端无未来信息</td></tr>')
    swap(old_audit.replace('</tr><tr>', '</tr>\n<tr>'), new_audit.replace('</tr><tr>', '</tr>\n<tr>'))
    swap('入选后按有效出场标签重算均值带有事后可得性口径；262 个入选股票日缺失标签。改成缺失计 0 后 Sharpe 为 7.303，当前样本影响很小，但仍应说明。',
         f'已进场而未在出场分钟成交的 {status["open_marked"]:,} 笔组合持仓保留并估值，没有从分母抹掉；后续实际退出的价格和时间仍未模拟。')
    swap('进场有成交、整分钟是否封板等信息到分钟结束才完整可知，而收益使用同一分钟 VWAP；这是研究定义，不是逐笔执行模拟。',
         '09:35 的选股名单先于 09:36 才完整可知的成交与封板状态锁定；实际进场使用同一分钟 VWAP，仍只是研究成交基准，不是逐笔执行模拟。')
    swap('约 13bp 的名义多空日均毛收益', f'约 {ls_mean_bp:.2f}bp 的名义多空日均毛收益')

    old_performance = ('<tr><td>读取与标签准备 / 对齐、标准化、矩阵</td><td>415.87 秒 / 16.99 秒</td></tr><tr><td>Dataset 与分箱</td><td>12.84 秒，仅训练样本构建分箱</td></tr><tr><td>train 调用（含评价）</td><td>66.25 秒，1000 轮</td></tr><tr><td>其中逐轮评价 / 剩余含框架开销</td><td>13.78 秒（20.81%）/ 52.47 秒</td></tr><tr><td>训练后预测核对 / 模型及结果保存 / 绘图报告</td><td>0.54 / 1.28 / 17.07 秒</td></tr><tr><td>业务全流程 / guard 启动收尾 / guard 总墙钟</td><td>534.40 / 9.86 / 544.27 秒</td></tr><tr><td>训练 CPU / 平均等效核数</td><td>463.56 CPU 秒 / 7.00 核</td></tr><tr><td>全流程 CPU / 平均等效核数</td><td>626.38 CPU 秒 / 1.17 核</td></tr><tr><td>训练采样 cgroup 峰值 / 全流程 cgroup 峰值</td><td>13.10 / 13.14 GiB；全流程进程树 RSS 采样峰值约 9.87 GiB</td></tr><tr><td>训练输出 / 输入因子逻辑字节</td><td>7,590,126 字节（清单生成前）/ 4,509,244,710 字节；无大矩阵缓存</td></tr><tr><td>冻结模型 test 全流程</td><td>179.00 秒，平均 0.38 核，cgroup 峰值约 2.38 GiB</td></tr>')
    r = train_resources
    train_input_bytes = sum(training['input_logical_bytes'].values())
    new_performance = (
        f'<tr><td>读取与标签准备 / 对齐、标准化、矩阵</td><td>{times["data_read_and_label_prepare"]:.2f} 秒 / {times["alignment_standardization_matrix"]:.2f} 秒</td></tr>'
        f'<tr><td>Dataset 与分箱</td><td>{times["lightgbm_dataset_construct_and_binning"]:.2f} 秒，仅训练样本构建分箱</td></tr>'
        f'<tr><td>train 调用（含评价）</td><td>{times["train_call_total"]:.2f} 秒，1000 轮</td></tr>'
        f'<tr><td>其中逐轮评价 / 剩余含框架开销</td><td>{times["train_internal_per_round_evaluation"]:.2f} 秒（{training["evaluation_share_of_train_call"]:.2%}）/ {times["train_call_minus_evaluation_including_framework_overhead"]:.2f} 秒</td></tr>'
        f'<tr><td>训练后预测核对 / 模型及结果保存 / 绘图报告</td><td>{times["post_train_prediction_verification"]:.2f} / {times["model_and_result_save"]:.2f} / {times["plot_and_report_seconds"]:.2f} 秒</td></tr>'
        f'<tr><td>训练业务全流程 / test 业务全流程</td><td>{times["whole_business_flow"]:.2f} / {summary["timings_seconds"]["whole_business_flow"]:.2f} 秒</td></tr>'
        f'<tr><td>训练 CPU / 平均等效核数</td><td>{r["train_cpu_seconds"]:.2f} CPU 秒 / {r["train_average_equivalent_cores"]:.2f} 核</td></tr>'
        f'<tr><td>全流程 CPU / 平均等效核数</td><td>{r["whole_flow_cpu_seconds"]:.2f} CPU 秒 / {r["whole_flow_average_equivalent_cores"]:.2f} 核</td></tr>'
        f'<tr><td>训练采样 cgroup 峰值 / 全流程 cgroup 峰值</td><td>{r["train_sampled_peak_task_cgroup_memory_bytes"] / gib:.2f} / {r["whole_flow_memory_peak_cgroup_bytes"] / gib:.2f} GiB；全流程进程树 RSS 采样峰值约 {r["whole_flow_sampled_peak_process_tree_rss_bytes"] / gib:.2f} GiB</td></tr>'
        f'<tr><td>训练输出 / 输入因子逻辑字节</td><td>{training["output_logical_bytes_before_manifest"]:,} 字节（清单生成前）/ {train_input_bytes:,} 字节；无大矩阵缓存</td></tr>'
        f'<tr><td>冻结模型 test 全流程</td><td>{summary["timings_seconds"]["whole_business_flow"]:.2f} 秒，平均 {test_resources["average_equivalent_cores"]:.2f} 核，cgroup 峰值约 {test_resources["task_memory_peak_bytes"] / gib:.2f} GiB</td></tr>')
    swap(old_performance, new_performance)
    swap('因子 parquet 读取占业务时间约 49.8%，成交标签查询约 27.5%',
         f'因子 parquet 读取占业务时间约 {times["factor_parquet_read_seconds"] / times["whole_business_flow"]:.1%}，成交标签查询约 {times["label_trade_query_seconds"] / times["whole_business_flow"]:.1%}')
    swap('训练阶段接近使用 7 个等效核，逐轮评价占 train 调用约五分之一',
         f'训练阶段平均使用 {r["train_average_equivalent_cores"]:.2f} 个等效核，逐轮评价占 train 调用约 {training["evaluation_share_of_train_call"]:.1%}')
    swap('内存额度为 60GiB / 52GiB', '内存上限为 100GiB，memory.high 为 32GiB')
    swap('检索完整 330 列映射', f'检索完整 {count} 列映射')
    swap('例如 f97 / cancel_buy / depth', '例如 f96 / cancel_buy / depth')
    swap('下载 330 列映射 JSON', f'下载 {count} 列映射 JSON')
    old_identity = ('训练 RUN_ID：ml-single-fit-cpu-l2-20260918-r04<br>test RUN_ID：ml-single-fit-cpu-l2-test-lssharpe-i0659-20260918-r01<br>'
                    'repository revision：71b710ed8778e7939fb06b4b0888683ba9659c6f<br>'
                    '659 轮模型 SHA-256：4ab899d71ee7f4c119cf60c14a4e9a25331610035f8534e6f0bb7a60aada2e1a<br>'
                    '完整模型 SHA-256：ca542f0cb54d0d9001117d20b98a1de602c1a43447a0fcea2ff7dabaa55d8c05')
    new_identity = (f'训练 RUN_ID：ml-causal-328-20260921-r03-train<br>test RUN_ID：ml-causal-328-20260921-r03-test<br>'
                    f'repository revision：{code["repo_revision"]}<br>'
                    f'{iteration} 轮模型 SHA-256：{identity["selected_model_sha256"]}<br>'
                    f'完整模型 SHA-256：{identity["model_sha256"]}')
    swap(old_identity, new_identity)
    swap('执行时服务器仓库记录为 detached HEAD、无修改条目', '执行时服务器仓库记录为 main 且无修改条目')
    swap('已检查的标签、预测与评价环节未发现造成 Sharpe 虚高的实现错误；上游完整因果性及实际可交易性仍未验收。',
         '选股时点与持仓分母已按因果口径改正，未成交退出持仓仍在账本；毛收益 Sharpe 仍偏高。上游完整因果性及实际可交易性仍未验收。')
    swap('结果整理于 2026-09-20', '结果整理于 2026-09-21')
    swap("rows.length+' / 330 列'", "rows.length+' / 328 列'")
    swap('2026-09-18-feature-mapping-330.json', '2026-09-18-feature-mapping-328.json')
    return report
