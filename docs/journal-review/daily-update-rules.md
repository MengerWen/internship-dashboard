# 研究日志每日更新规则

每天北京时间（Asia/Shanghai）上午 9 点，由 T3 Code 定时任务新建独立线程执行研究日志每日更新。执行模型为 **Gemini 4 Neon (High)**（`antigravity / gemini-4-neon`, `thought_level: high`）。更新对象是本仓库的 `content/journal/` 与 `content/chains.json`，线上入口为 [研究日志](https://internship-dashboard.mengerwenjie.workers.dev/#/journal)。

## 一、日期范围与补漏

- 目标日为运行日的前一天（北京时间 00:00 至次日 00:00，左闭右开）。9 点只是整理时间，工作归属以实际发生日期为准。
- 顺带复查近 7 天的迟到提交、补写报告和未闭合缺口；如果某天漏跑，按时间顺序补齐。
- 某天确实没有新增研究工作，保留空白，不硬凑占位日卡；如果关键来源不可读，在核对记录里如实注明。

## 二、来源核对范围（轻量且不漏）

每轮直接核对目标日及近 7 天的真实一手来源，不再做全量历史归档翻页或数万旧文件的机械盘点：

| 来源 | 核对方式与内容 |
|---|---|
| `sirui-quant-research` | 核对本地 HEAD、远端 `origin/main` 与目标时间窗内全部 Git 提交及关键 diff，查看 `PLAN/`、`reports/`、`docs/`、`decisions/` 及相关未提交改动。只读，不修改源仓库、不触发计算或服务器操作。 |
| `Quant_Research-Trading` | 仅限 `scripts/journal_repos.json` 白名单路径（`26 Summer/❗思瑞投资/`），与子模块 SHA 去重，不重复计功。 |
| `internship-dashboard` | 日报、展示页、研究日志及站点代码改动。每日自动更新自身只在产生独立工程成果时记入，不每天自我循环记一条。 |
| **T3 Code 全量会话 + Codex/Claude 物理会话** | 运行 `D:\MG\anaconda3\python.exe scripts/collect_journal_sessions.py --since <7天前> --until <目标日> --output data/journal-sessions/<运行日>.json`。脚本自动从 T3 Code 的 `statev2.sqlite` 按项目和 worktree 采集 Antigravity / Codex / Claude 全部线程，并合并本机 Codex/Claude 物理 JSONL（按消息北京时间筛选，自动排除当前日志维护线程自身）。 |

事实判别原则：
- 用户在会话里的原话可直接证明研究目标、取舍、停止与转向；完成状态、性能耗时、收益指标和线上验收必须以真实报告、机器证据或原始工具回执为准，不能只凭一句“已完成”。
- 构思、计划、代码实现、运行结束、验收通过分别说清；不把计划或启动当成完成。
- 凭据、邮箱、内网地址、服务器绝对路径和私人内容不得入站；候选会话全文仅留本机 `data/`（已被 Git 忽略）。

## 三、归链与交接原则

先梳理当天各项工作的目标、实际动作、结果和遗留问题，再对照 `content/chains.json`：

- 同一研究问题下的实现、排障、提速、验收和收尾，归入同一条链，不要按单日或小波次把同一主线拆成零散短链。
- 确实是独立新研究方向时才建新链，给出稳定 `id`、平实的 `label` / `purpose` / `fate_note` 和真实 `source_refs`。
- 只有存在真实输入、产出、方法或决策承接时才登记 `handoffs`；`source_date` 与 `date` 必须分别是来源链和目标链实际存在的日点，且附带固定 GitHub 链接（完整 40 位 SHA）。
- 链已收尾或不再推进时，及时把 `status` 改为 `done`，并把 `fate_note` 更新成“这条链做成了什么、当前结论是什么”的完整平话，不要整段替换成最后一天流水账。

## 四、写作标准（严格按 `shuorenhua`）

日卡写给读研究日志的人看，不写给审计系统看。动笔前读 `shuorenhua` 技能，并遵守以下口径：

1. **`headline`**：40 字以内，一句话先说当天最重要的研究结论或硬成果，不要把 commit 标题拼成一串。
2. **逐链 `note`**：24 字以内，写清当天在这条链上具体做了什么、结果怎样，不用空洞套话。
3. **`highlights`**：1–3 条，讲清做了什么、得出什么结论、做了什么决定、还剩什么问题，数字标清对象。
4. **正文“补充说明”**：按主题分段，加粗短语点题，篇幅控制在 1,500 字左右。
   - **先写研究结果，再写工程进度**。
   - **说人话，去翻译腔与审计黑话**：不用“签收、改签、准入、有界验收、身份、合同、退役载荷、回读、不得冒记为、不能写成”等绕口写法；直接写“验收通过、门槛、规格、不再需要的文件、写后核对”。只做了计划就写“写了计划”，不用加免责声明。
   - **项目代号与精度**：阶段代号（如 W10、S2c、E5、B6、r08）默认改写成它指代的事；必须出现时首次解释。耗时写整秒或两位小数，容量写 MB/GB，不抄哈希值或十几位小数。
   - **保留真实限制**：样本内/样本外口径、未扣成本、未测全期等真实研究保留意见，用一句平话讲清。
5. **原始依据与摘录**：
   - `## 原始依据` 只列当天（或前后一天入库）的核心报告、关键文档与代表提交（固定 40 位 SHA 链接）。
   - 如加入经过核对的会话摘录，经 `collect_journal_sessions.py --verify ... --render` 校验原始哈希后写入。
   - `reports_covering` 只填确实覆盖当天工作的正式日报日期，不乱填演示页。

## 五、核对、测试、提交与发布

1. **归属与证据校验**：同步更新 `scripts/journal_repos.json` 的固定版本、`content/journal/_evidence/` 与 `content/journal/_attribution/`（及必要时的 `scripts/journal_attribution_rules.json`），运行：
   - `D:\MG\anaconda3\python.exe scripts/collect_journal_attribution.py --check`
   - `D:\MG\anaconda3\python.exe -m pytest tests/test_journal_build.py tests/test_journal_evidence.py tests/test_journal_provenance.py tests/test_journal_attribution.py tests/test_journal_sessions.py tests/test_journal_point_evidence.py -q`
   - `D:\MG\anaconda3\python.exe build.py`
2. **核对记录**：在 `docs/journal-review/daily-updates/YYYY-MM-DD.md` 记录简明的本轮核对摘要（覆盖日期、三仓版本、会话来源统计、归链调整、校验和发布结果）。
3. **收尾与发布**：
   - 运行 `npm run workspace:audit`，确保无意外未跟踪文件和临时体积异常。
   - 只暂存本项改动，在 `main` 提交并 `git push`，核对远端含目标 SHA。
   - 有站点内容变更时，按 `DEPLOY.md` 执行本机增量发布 `npm run deploy`，记录生产版本 ID；无实质内容变更（仅核对记录或无新工作）时不触发发布。
4. **通知原则**：有实质更新时简报覆盖日期、核心进展、链条变化与发布版本；无新增且无异常时保持简短；遇到采集失败、测试不过或发布失败时直接说明具体原因，不绕过门禁。

## 六、工作点的证据类型

构建从逐条提交归属和固定来源登记输出 `chain_evidence`：
- 有同日同链的已归属提交或带写入回执的主要文档，显示实心；
- 仅有带定位和时间戳的会话交流登记时，显示空心并标「仅见交流」；
- 两类均未补齐时显示虚线轮廓并标「证据待核」。
