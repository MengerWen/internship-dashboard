# 2026-11-27 研究日志迁移至 T3 Code (Neon High) 与全量重审记录

本次操作由 Gemini 4 Neon (High) 在 T3 Code 中执行，完成了每日更新链路迁移、T3 Code 会话数据源补齐以及全历史链条与日卡重审。

## 1. 定时任务与模型迁移

- **停用旧任务**：将 Codex 旧定时任务 `C:\Users\19927\.codex\automations\automation-2\automation.toml` 状态由 `ACTIVE` 改为 `PAUSED`（保留历史配置和 `memory.md`）。
- **新建 T3 Code 定时任务**：在「汇报」项目（`66953ad6-0c85-492b-806f-7646ce767d9a`）设置默认模型为 `antigravity / gemini-4-neon`（`thought_level: high`），并创建每日北京时间 09:00 新建独立线程运行的定时任务 `研究日志每日更新（Neon High）`（`scheduled-task:command:mcp:caf38d9e-7f7b-4126-8652-29dfd3d506cb:schedule-task:journal-daily-neon-high-2026-11-27`）。
- **精简维护规则**：更新 `docs/journal-review/daily-update-rules.md`，去除 Codex 硬绑定与低效的全量历史归档盘点仪式，聚焦目标日及近 7 天真实提交、T3 全量会话、`shuorenhua` 写作口径、测试构建与本机增量发布。

## 2. T3 Code 会话数据源接入与补漏

- 更新 `scripts/journal_sessions.json`、`scripts/collect_journal_sessions.py` 和 `tests/test_journal_sessions.py`：
  - 新增 `t3-code` 数据源（只读扫描 `~/.t3/userdata/statev2.sqlite`），按项目根目录自动覆盖 `Antigravity / Codex / Claude` 全 provider 线程与独立 worktree；
  - 将 `D:/MG/_TaskRuntime/sirui` 和 `~/.t3/worktrees` 加入 `project_roots`；自动排除当前 `T3CODE_THREAD_ID`。
- 实测补采 `2026-11-24` 至 `2026-11-26`：共采出 T3 线程 **173 个（2,585 条消息）**，含 23 个此前 100% 漏采的 Antigravity (Neon) 核心总控、答疑与报告改写线程；将其中关键研究决策与进展补回 `2026-11-24.md`、`2026-11-25.md` 与 `2026-11-26.md`。

## 3. 全量链条与 136 篇日卡 Neon (High) 重审

- **链条与交接（`content/chains.json`）**：
  - 将 1 天短链 `factor-incremental-workflow` 合并入 `corrected-factor-344`，同步迁移 `_attribution/2026-11-01.json`、`scripts/journal_attribution_rules.json` 与来源登记，链条由 61 条收敛为 **60 条**，交接由 85 条收敛为 **84 条**；
  - 将 17 条已收尾仍错标 `active` 的链校准为 `done`；
  - 按 `shuorenhua` 规范重写全部被 GPT 拼接流水账和审计黑话污染的 `label`、`purpose`、`fate_note` 及 `handoffs[].note`。
- **全部 136 篇日卡（`content/journal/2026-06-23.md` 至 `2026-11-26.md`）**：
  - 全量由 Gemini 4 Neon (High) 逐篇复查并按 `shuorenhua` 规范精修，重点彻底重写 11 月 10–26 日 15 篇纯 GPT 日卡与 10 月 25 日–11 月 9 日 16 篇旧日卡，同时通审 6 月 23 日–10 月 24 日全部历史日卡；
  - 全部原始数据、日期、研究保留意见、GitHub 固定链接和会话摘录托管区原样保留。
