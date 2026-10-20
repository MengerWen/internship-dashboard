# 新栏目「研究日志」实施计划

**Goal:** 在看板上新增第三个主视图「研究日志」，把 2026-06-23 以来 88 个有记录的日子按真实日期画成一张推进图谱，每天可读到一句话总结、它属于哪条任务链、从哪里接住、交给了谁，以及支持这句话的提交、计划与产出；窄屏和无障碍场景下提供等价的清单视图。

**Architecture:** 三层数据（机器采集的证据 / 人写的每日记录 / 人维护的链条注册表）+ 两个视图（图谱 / 清单）。采集只在本地跑，产物提交进本仓；`build.py` 只读已提交的 JSON，构建期不访问其它仓库。前端沿用现有零框架壳：新增 `site/js/journal.js`、`site/css/journal.css`，在 `router.js` 增一个分支，顶栏增第三个 tab，不动既有路由、搜索、标签与展示模式。

**Tech Stack:** Python 3（`D:\MG\anaconda3\python.exe`）、`python-frontmatter`、`markdown`；原生 HTML/CSS/JS，无框架无打包器；Pagefind 做全文索引；Playwright 做浏览器验收。

设计依据：`docs/plans/2026-10-20-journal-column-design.md`（尤其第 5 节链条判定、第 6.5 节定稿规格、第 8 节配色实测）、`design-demos/journal-prototype/`（方向三原型与真实数据）、`direction-approved.md`（2026-10-20 方向选定记录）。

---

## 0. 范围与已核对现场

已在本机核对、构成本计划前提的事实：

- **仓库与构建边界。** `DEPLOY.md` 第 1 节第 4 条：Cloudflare Workers Builds 只 clone `internship-dashboard`。研究主仓 `sirui-quant-research`、父仓 `Quant_Research-Trading` 在构建环境里不存在。因此采集必须本地跑、产物必须入库。
- **素材规模。** 三仓 2026-06 起共约 2715 次提交（研究主仓 2455、父仓 142、看板仓 118）；研究仓 `PLAN/` 有 129 个带日期计划文件；`content/daily/` 有 35 篇日报。过滤后有记录的日子 **88 天，2026-06-23 → 2026-10-20**。
- **链条并发。** 修订后 28 条链条草案、26 条交接，同时在跑最多 **5 条**（2026-09-07），月均 2 条。纵轴六条轨道够用。
- **每日汇报的日期是归档标签，不是做事的日子。** 逐篇比对报告日期与该文件首次入库日：35 篇里 11 篇晚 2 天以上，`2026-06-25` 晚 18 天、`2026-06-26` 晚 55 天、`2026-07-05` 是建站 init 带进来的示例占位。另外 `2026-08-01`（区间扩展）实际工作在 07-30／07-31、发布在 08-02；`2026-09-16`（601 日全部因子评价）正文自述「实际评价完成日期为 2026-09-17」，后台计算 09-12 启动、09-17 发布。**所以日志必须把工作记在真正做事的那天，而不是汇报的名义日期。**
- **单日提交 1–243 次。** 提交只能做证据层，每日正文必须是人写的一句话。
- **链条显式互链指望不上。** 157 个 PLAN 里只有 1 例用 markdown 链接指回前一份计划（`2026-10-16-szse-model328-four-minute-continuation.md`）。33 个文件命中「延续／续跑／承接」但逐个看过，绝大多数是领域术语（指恢复一次中断的计算），不是计划之间的引用。
- **现有阶段色不能当链条色。** 按分类色六项检查实测（纸底 `#f2eee4`）：`#7c8581`、`#4d7c8b`、`#477d75`、`#9a705d` 四个在饱和度下限之下，2px 线上读成灰；`#477d75` 与 `#4d7c8b` 正常视力下 ΔE 3.7（门槛 15）；`#9a705d` 与 `#d9654f` 红色盲下 ΔE 3.0。**链条不上色**。
- **hash query 已有先例。** `site/js/report-tags.js` 用 `new URLSearchParams(location.hash.split("?")[1] || "")`，`router.js` 的 `parseHash` 用 `.split("?")[0]` 取路径。本栏目沿用同一套写法，不新造。
- **索引页机制已有。** `Builder.build_index_pages` 往 `dist/_index-pages/` 写带 `redirect_hash` 的静态页供 Pagefind 抓取；离线版用 `Builder.inline_offline_data` 把 manifest 与各页内容塞进 `index.html` 的 `<!-- INLINE_DATA -->`。两者都直接扩展，不重写。
- **已修一处既有数据问题。** `content/daily/2026-06-26.md` 的 `stage` 原为 `server-l2-factor-pipeline-complete`，不在 `config.json` 的六个阶段里，构建会告警并归入 `unclassified`。已按用户指示改为 `lv2-snapshot`（该篇讲的是订单簿重建能力的复用）。改后全部日报的 `stage` 都落在六个阶段内。
- **`config.json` 的六个阶段不需要改。** 逐项核过：`strategy` 尚无工作属于「planned」是正常的；「看板与交付」这条线本来就不属于任何研究阶段，用 `stage: null` 表达即可；「因子与定标」8 条链是最满的一条轨道，靠轨道高度随链条数变化已经容下，拆成两个阶段会牵动 21 篇日报的 `stage` 与正式成果页，代价不值。唯一可选的小改动：`data-processing` 的 label「数据处理」没有覆盖实际落在这条线上的服务器与存储工作，可改成「数据与服务器」——只动 label、不动 id，零连带影响。是否改由用户定。

本计划**不做**：不改 `content/daily/` 任何正文，不改 `content/showcase/`，不动标签系统与 Worker，不引入前端框架或 npm 运行时依赖，不在构建期访问其它仓库，不改 `config.json` 的六个阶段 id。

---

## 1. 数据契约

### 1.1 `content/chains.json`（人写，链条逻辑的唯一权威）

**这个文件已经生成好了**（28 条链条、26 条交接），Codex 直接读，不要重建。
每条链条带一个 `review` 块记录审阅状态：

```json
"review": {"days": 14, "span": ["2026-08-06", "2026-09-04"], "unreviewed_days": ["2026-08-08", "…"]}
```

`unreviewed_days` 里的日子，归属还是脚本推断的。用户逐条看过之后把那天从列表里删掉，
列表清空即这条链确认完毕。构建**不依赖** `review`，它只是审阅进度，可以整块删掉而不影响任何功能。
`span` 同理，是生成时的快照，权威的起止仍然由引用该链条的日子推出来。


```json
{
  "schemaVersion": 1,
  "tracks": [
    {"id": "infra",     "label": "数据与服务器", "stage": "data-processing"},
    {"id": "snapshot",  "label": "快照与回放",   "stage": "lv2-snapshot"},
    {"id": "footprint", "label": "算法痕迹",     "stage": "algo-footprint"},
    {"id": "factor",    "label": "因子与定标",   "stage": "factor"},
    {"id": "model",     "label": "模型",         "stage": "model"},
    {"id": "delivery",  "label": "看板与交付",   "stage": null}
  ],
  "chains": [
    {
      "id": "szse-model328",
      "track": "factor",
      "label": "深市 328 列因子：重算到签收",
      "short": "深市 328",
      "purpose": "把 328 列因子在 601 个交易日上算完、验收、封存并评价表现",
      "status": "done",
      "closes_into": {"showcase": "factor", "daily": ["2026-10-16", "2026-10-18"]}
    }
  ],
  "handoffs": [
    {"from": "old-factor-bank", "to": "szse-model328", "type": "延续", "confidence": "confirmed"}
  ]
}
```

约束：

- `tracks[].id` 自定义；`tracks[].stage` 必须是 `config.json` 里存在的阶段 id 或 `null`。构建时校验，不匹配就告警并把该轨道的 `stage` 视为 `null`。
- 链条的起止**不写在这里**，由实际有记录的日子推出来（首个到最后一个引用它的日子）。这样改一天的归属不用同时改两个地方。
- `handoffs[].type` 取 `延续｜派生｜依赖解除｜收口` 四值之一；`confidence` 取 `confirmed｜inferred`。
- `short` 用于图上的直接标注与窄列，控制在 6 个汉字以内。
- 一条轨道的链条数超过 10 条时构建告警：要么拆轨道，要么合并链条。当前最满的「因子与定标」是 8 条。

### 1.2 `content/journal/YYYY-MM-DD.md`（人写）

**88 个文件已经生成好了**，覆盖 2026-06-23 → 2026-10-20 每个有记录的日子。Codex 直接读。


```yaml
---
date: 2026-10-14
headline: "沪市委托 v2 全流程提速，深市 328 列进四分钟档"
chains: [sse-v2, szse-model328, storage-cleanup]
chains_reviewed: true              # false 表示这天的 chains 还是脚本推断的，未经人确认
headline_source: report            # written | report | plan —— 这句话是人写的还是草稿
highlights:
  - "沪市原始委托 v2 从解析到面板跑通，热副本清理同步做完"
  - "深市 328 列单日基线换成 2025-11-18，240 秒硬门写进计划"
reports_covering: [2026-10-14]     # 这天的工作最终写进了哪几篇汇报（可留空）
---

（可选正文。没有就不写，构建不报错。）
```

- `highlights` 不超过 3 条，超了构建告警（不中断）。
- `headline` 的 40 字硬限**只对 `headline_source: written` 生效**——那是人写的，该守住。
  `report` 与 `plan` 来源的是草稿，直接取自日报标题或计划标题，构建只在汇总行统计
  「还有 N 天的一句话是草稿、其中 M 天超过 40 字」，不逐条告警。
  当前 88 天里 22 天是人写的（全部 ≤40 字），32 天取自日报标题，34 天取自计划标题，
  其中 13 天超过 40 字，随手改短即可，不阻塞实现。
  这是日志不长成第二套日报的防线。
- `chains` **压过采集脚本的任何推断**。实测里 91 天有 3 天只能靠人指定（2026-07-05、2026-08-01、2026-09-16，都是当天只发了日报、没有提交也没有计划文件），这条通路是必需的。
- `reports_covering` 填写时构建校验 `content/daily/<值>.md` 存在，不存在就告警并忽略。
  这个字段解决「汇报日期 ≠ 工作日期」：默认一篇汇报覆盖它自己那天，核对下来不是的就在这里写实际工作日。
  **当前已确认的三处例外**：`2026-07-05` 是建站带进来的示例占位，不覆盖任何研究日；
  `2026-08-01` 覆盖 `2026-07-30`、`2026-07-31`；`2026-09-16` 覆盖 `2026-09-12`、`2026-09-17`。
- 与之配对的 `reports_published`（这天把哪几篇汇报写出来／发出去）**不写在这里**，
  由采集脚本从 `git log --diff-filter=A` 取 `content/daily/<date>.md` 的首次入库日自动得出，是客观事实。
- 一个只是某篇汇报名义日期、当天既没有提交也没有计划、既不发布也不被覆盖的日子，**不算工作日**，不进日志。
  按这条规则 `2026-07-05`、`2026-08-01`、`2026-09-16` 三天从 91 天里移出，剩 88 天。
- 文件缺失不是错误：该天用采集到的证据生成草稿条目，`headline` 回落到当天第一条提交信息，前端标「待写」。实测 88 天里 32 天可用日报标题、34 天可用计划标题、22 天需要人写——**这 22 条已经写完**，
见 `design-demos/journal-prototype/headlines.py`，每条都是读过当天全部提交后写的，全部不超过 40 字。

### 1.3 `content/journal/_evidence/YYYY-MM-DD.json`（脚本生成，不手改）

```json
{
  "date": "2026-10-14",
  "weekday": "周三",
  "repos": [{
    "repo": "sirui-quant-research",
    "commits": 161,
    "commit_url": "https://github.com/MengerWen/sirui-quant-research/commit/{sha}",
    "top_paths": [["因子/algobench", 278], ["reports/2026-10", 102]],
    "items": [{"sha": "a1b2c3d", "subject": "并行执行完整订单验收与日清单编码"}]
  }],
  "plans": [{"file": "PLAN/2026-10-14-szse-model328-four-minute-performance.md",
             "title": "深市 328 列单日四分钟性能验收实施计划"}],
  "reports_published": ["2026-10-14"],
  "suggest": {"chains": ["sse-v2", "szse-model328"], "how": {"sse-v2": "plan-token"}}
}
```

- `items` 每仓每天最多 10 条，按提交顺序取前 10；`commits` 是真实总数，前端显示「161 次（列出前 10 条）」。
- `suggest` 是脚本的归属建议和依据，**只供人审阅**，构建不使用。
- 文件可随时整体重算，重算结果应当逐字节稳定（同一份 git 历史 → 同一份 JSON），便于 diff 审阅。

### 1.4 `scripts/journal_repos.json`（人写，采集配置）

```json
{
  "since": "2026-06-01",
  "repos": [
    {"name": "sirui-quant-research",
     "path": "D:/MG/_GitLinked/Quant_Research-Trading/26 Summer/❗思瑞投资/sirui-quant-research",
     "commit_url": "https://github.com/MengerWen/sirui-quant-research/commit/{sha}",
     "plan_dirs": ["PLAN"]},
    {"name": "Quant_Research-Trading",
     "path": "D:/MG/_GitLinked/Quant_Research-Trading",
     "commit_url": "https://github.com/MengerWen/Quant_Research-Trading/commit/{sha}",
     "only_under": "26 Summer/❗思瑞投资/"},
    {"name": "internship-dashboard",
     "path": ".",
     "commit_url": "https://github.com/MengerWen/internship-dashboard/commit/{sha}",
     "plan_dirs": ["docs/plans", "PLAN"]}
  ],
  "exclude_plan_slugs": ["dating-", "wenjie-ide"],
  "redact": ["C:/Users/", "/home/", "@", "jumpserver"]
}
```

`only_under` 是按仓库限定子树的白名单——父仓是个大杂烩，只有思瑞那棵子树算本实习。实测这条规则把 2026-06-04 整天（别家公司的笔试提交加一个仓库根 `.gitignore`）正确地排除掉了，91 天的起点因此是 06-23 而不是 06-04。

---

## 2. 采集脚本 `scripts/collect_journal_evidence.py`

**只在本地运行，永不在构建期调用。**

```powershell
D:\MG\anaconda3\python.exe scripts\collect_journal_evidence.py            # 重算全部
D:\MG\anaconda3\python.exe scripts\collect_journal_evidence.py --check    # 只检查，落后时返回非零
D:\MG\anaconda3\python.exe scripts\collect_journal_evidence.py --since 2026-10-01
```

行为：

1. 对每个仓库跑 `git log --date=short --pretty=format:... --name-only --since=<since>`，按作者日期归集。`only_under` 仓库先按前缀过滤路径再剥前缀；过滤后 `top_paths` 为空的仓库条目整条丢弃（这一步才真正排掉只碰了范围外文件的提交）。
2. 收集各仓 `plan_dirs` 下匹配 `YYYY-MM-DD-*.md` 的计划文件，标题取文件里第一个 `# ` 标题，取不到就用文件名；命中 `exclude_plan_slugs` 的跳过。
3. 读 `content/daily/*.md`（排除 `.show.md`）的 `title`、`summary`、`stage`。
4. 丢弃既没有计划、也没有日报、也没有任何在范围内提交的日子。
5. 按下列顺序给出归属建议，并记录依据：
   - PLAN 文件名首词族／两词族命中链条关键词 → `plan-token`
   - 当天触及路径命中链条的路径特征 → `path`
   - 当天有日报时，日报 `stage` 映射到轨道，取该轨道上当时在跑的链条 → `stage`
   - 都不命中 → 空，前端显示「未归类」
6. 写 `content/journal/_evidence/*.json`；对没有对应 `content/journal/*.md` 的日子，另外打印一份待写清单（日期、建议链条、可用作初稿的标题）。
7. `redact` 里的片段出现在任何将要写入的文本中时，整条替换为 `<已隐去>` 并计数告警。本机绝对路径、邮箱、服务器主机名不进站点。

脚本不写 `content/chains.json`，也不写 `content/journal/*.md`。

原型里的 `design-demos/journal-prototype/build_data.py` 已经实现了上面 1–6 的全部逻辑并在真实数据上跑通（88 天、0 天未归类、70 条确认归属 / 55 条推断归属），可以直接作为实现参考，但不要原样搬运：原型把链条表硬编码在脚本里，正式版必须从 `content/chains.json` 读。

---

## 3. 构建接入 `build.py`

新增 `Builder.build_journal()`，在 `build()` 里排在 `build_daily()` 之后、`manifest()` 之前。

| 复用入口 | 决定 |
| --- | --- |
| `Builder.render_markdown_file` | 直接复用解析 `content/journal/*.md` 的 frontmatter 与可选正文 |
| `Builder.read_json` / `write_text` | 读 `chains.json` 与各天证据，写输出，全部显式 utf-8 |
| `Builder.manifest` | 增 `journal`（每日摘要）与 `chains`（轨道、链条、交接）两个键 |
| `Builder.build_index_pages` | 增一段：为每天写 `_index-pages/journal-<date>.html`，`redirect_hash` 为 `../#/journal/<date>`，`meta` 含 `{"date": …, "type": "journal"}`；正文用一句话 + 要点 + 计划标题 + 提交信息，供 Pagefind 抓 |
| `Builder.inline_offline_data` | 增一段：把每天的证据 JSON 作为 `<script type="application/json" id="journal-ev-<date>">` 一并内联；离线版没有 fetch |
| `Builder.run_pagefind` | 不改，新索引页自动被抓到 |
| `Builder.warnings` | 新校验全部走告警，不中断构建，沿用既有风格 |

**manifest 的 journal 条目**（保持小，首屏就要用）：

```json
{"date": "2026-10-14", "weekday": "周三", "headline": "…", "headline_source": "report|plan|commit",
 "chains": ["sse-v2", "szse-model328"], "chain_confidence": {"sse-v2": "confirmed"},
 "highlights": ["…"], "commits": {"sirui-quant-research": 161}, "total_commits": 168,
 "report": "2026-10-14", "has_body": false, "evidence_path": "journal/_evidence/2026-10-14.json"}
```

详细证据（逐条提交、路径分布）**不进 manifest**，按天放 `dist/journal/_evidence/<date>.json`，前端展开时才取。实测 91 天证据合计约 240 KB；manifest 现在是 35 KB，加上 journal 摘要后预计 70 KB 以内。

构建期校验（全部走 `self.warnings`）：
- `chains.json` 的 `tracks[].stage` 不在 `config.json` 里；
- 某天引用了 `chains.json` 里不存在的链条 id；
- `report` 指向的日报文件不存在；
- `headline` 超过 40 字或 `highlights` 超过 3 条；
- 某条轨道的链条数超过 10；
- 有证据文件但没有 `content/journal/*.md` 的天数（打印总数，提醒还有多少天待写）。

---

## 4. 前端

### 4.1 挂载点

- `site/index.html`：顶栏 `.tabs` 增 `<a id="tab-journal" class="tab" href="#/journal">研究日志</a>`，放在「每日汇报」之后；`<main>` 增 `<section id="view-journal" class="view journal-view">` 骨架；增 `journal.css` 与 `journal.js` 的引用（沿用现有 `?v=` 版本串写法）。
- `site/js/router.js`：`parseHash` 增 `if (view === "journal") return {view: "journal", key, subview};`；`route()` 增对应分支调 `window.JournalView.show(key)`。查询串沿用 `report-tags.js` 的写法，`URLSearchParams(location.hash.split("?")[1] || "")`。
- 路由：`#/journal`、`#/journal/<date>`（选中并滚到那天）、`#/journal?chain=<id>`（聚焦一条链）、`#/journal?view=list`（清单）。三个查询参数可叠加，写回地址栏用 `history.replaceState`，与标签链接的做法一致。

### 4.2 图谱（默认，≥860px）

一张 SVG，`viewBox` 固定 `0 0 1240 H`，容器 `min-width: 1120px` 放在横向滚动容器里。

| 元素 | 编码 |
| --- | --- |
| 横轴 | **真实日期**，窗口首日到末日等比。停下来的日子占真实宽度 |
| 纵轴 | 轨道，高度 `36 + 9 × 该轨道链条数` |
| 轨道内 | 每条链一个固定偏移，`(i/(n-1) - 0.5) * 2 * (bh/2 - 11)` |
| 点 | `r = clamp(2.1 + 0.46 * sqrt(提交数), 2.1, 7)` |
| 点的填充 | 实心 = 当天有每日汇报；空心 = 没有 |
| 折线 | 相邻活跃日间隔 ≤1 天画实线；跨空档画虚线并降到 `--muted` |
| 交接弧 | 跨轨三次贝塞尔，默认 `opacity: 0.26`；延续实线、派生 `4 3`、依赖解除 `1 3` |
| 收口 | 链条末点上 7×7 实心方块 |
| 每日汇报行 | 轨道下方单独一行墨色竖刻度，左端标「每日汇报 N 篇」 |
| 周末 | 竖向浅底纹，`--bg-deep` @ `opacity: 0.3` |
| 月分隔 | **实线**细线 + 月份标签（虚线在图表里表示预测或阈值，当网格用是噪音） |
| 链名 | 活跃 ≥3 天的链在折线起点直接标注，文字 `paint-order: stroke` + 3px 纸色描边；同轨道内 x 相距 <76px 时上移 10px 避让 |

### 4.3 交互

1. **整列命中**：每天一个透明 `rect`（宽度至少 7px），覆盖整个绘图高度。不要求命中圆点本身。
2. **悬停读数**：灰色竖线对位 + 绝对定位的小纸卡（日期、星期、有无汇报、那句话、链条、提交数）。贴近右边缘时翻到鼠标左侧。
3. **选中**：珊瑚竖线 + 淡带；下方日卡更新；日卡上方「前一天／后一天」两个按钮，带相邻日的日期与截断到 28 字的一句话。
4. **链条聚焦**：下拉（按轨道 `optgroup` 分组）、点折线、或点日卡里的链名三种入口。其余 `opacity: 0.1`；该链与其上下游转珊瑚；日卡换成**链条卡**：上下游（承接谁／交给谁／类型）、落成了哪几篇汇报、这条链上的每一天（两列，可点）。
5. **时间窗**：全部 / 近 3 个月 / 近 1 个月。切换后整图重绘，横轴端点标签与汇报篇数跟随窗口，选中日不在窗内时落到窗内第一天。
6. **键盘**：SVG `tabindex="0"`，←→ 换一天，Esc 取消聚焦，可见焦点环。
7. **动效**：只有高亮与展开两处，`120ms` / `220ms`，`cubic-bezier(0.23, 1, 0.32, 1)`；`prefers-reduced-motion` 下保留透明度、去掉位移。不做逐元素滚动入场。

### 4.4 清单（<860px 默认，宽屏可切）

一张表：日期（含星期）、这天做了什么、链条、提交数、汇报。有汇报的行换 `--surface` 底、`inset 3px 0 0 var(--line)` 左边。带关键词查找（匹配日期、一句话、链名）。点一行回到图谱并选中那天。

这张表同时是图表的无障碍孪生体：图里能读到的信息表里都能读到，不存在只能靠悬停才拿得到的值。

### 4.5 日卡（三层信息的第二、三层）

- 顶部：日期、星期、提交数、一句话（`headline_source` 为 `commit` 时降为次要色并加「待写」角标）、「每日汇报 ↗」链接（墨色加下划线，**不用珊瑚**）。
- 链名做成按钮，点击即聚焦该链。
- 左列「做了什么」：`highlights`；没有就退回当天的计划标题；再没有就退回前若干条提交信息。
- 左列「脉络」：承接谁 / 交给谁（带类型）、同一条链的上一天 / 下一天，全部可点跳转。
- 右列「根据」：按仓库折叠的提交（默认折起，显示次数与触及路径分布，展开才列条目，hash 带 GitHub 链接）、计划文件名、每日汇报标题与摘要。提交证据在 `evidence_path` 第一次展开时 `fetch`，离线版改读内联的 `<script id="journal-ev-…">`。

### 4.6 视觉约束

- 颜色全部取自 `site/css/tokens.css`，**不新增颜色令牌**。
- **珊瑚 `--focus` 只表示「当前选中或聚焦」**。有每日汇报靠材质与字体区分（纸色底、墨色边、衬线标题、实心点），不占颜色。
- 链条**不上色**：身份靠轨道内位置 + 文字标签。理由见第 0 节的配色实测。
- 字体沿用 `--font-serif` / `--font-body`，不引入第三种。

---

## 5. 分期与各期验收

| 期 | 范围 | 验收 |
| --- | --- | --- |
| **P0** | `chains.json` 与 88 个 journal 文件**已就位**，这期只需写 `journal_repos.json` 与 `collect_journal_evidence.py` | 88 天证据 JSON 生成；`--check` 幂等；`redact` 命中数为 0；重复运行结果逐字节一致；脚本不写 `chains.json`、不写 `journal/*.md` |
| **P1** | `build_journal()` + manifest + 顶栏 tab + 路由 + **清单视图** | `python build.py` 零告警（`2026-06-26` 的 stage 已修，不再有豁免项）；`#/journal` 列出 88 天；有汇报的行可跳 `#/daily/<date>`；查找可用；窄屏可读 |
| **P2** | 图谱：时间轴、轨道、点、折线与虚线段、交接弧、收口、汇报刻度行、直接标注 | 设计文档 `docs/plans/2026-10-20-journal-column-design.md` 第 5.3 节的四类交接在图上一眼可分辨；`因子与定标` 8 条链不重叠；1440 与 390 两个宽度截图核对 |
| **P3** | 悬停读数、日卡与前后导航、链条聚焦与链条卡、时间窗、键盘换日、深链、索引页与离线内联 | 四个路由可直接打开；键盘可换日且焦点可见；离线版展开证据正常；Pagefind 能搜到日志正文 |
| **P4** | 逐条确认 28 条链条与 26 条交接（22 天的一句话已在 P0 前写完） | `chain_confidence` 里 `inferred` 的 55 条逐条过目后转 `confirmed` 或改写 |

P1 结束就已经有价值：现在只有 35 天在站点上露面，P1 之后是 88 天。

### 浏览器验收（P2 起每期跑）

```powershell
npx playwright install chromium
node design-demos/journal-prototype/shots.cjs   # 原型基线，比对用
```

正式版另写 `scripts/verify_journal.cjs`，沿用 `scripts/verify_nav_scrollspy.cjs` 的写法：1440 与 390 两个宽度，检查无横向溢出、无控制台错误、四个路由直接打开正确、键盘换日生效、清单与图谱的天数一致。

---

## 6. 需要人确认的事（实现前）

1. ~~栏目名~~ **已定「研究日志」**。实现时只在 `site/index.html` 一处落字。
2. **28 条链条与 26 条交接**已经写进 `content/chains.json`，88 个 journal 文件也已生成。
   待确认的是其中的推断部分：**88 天里 51 天归属已确认、37 天待过目**，
   逐条清单见 `design-demos/journal-prototype/chains-review.md`（每条链条列出它的每一天、
   归属是确认还是推断、支撑它的计划文件）。
   审阅只改两处：`content/chains.json` 里该链条 `review.unreviewed_days` 删掉那一天，
   以及该天 journal 文件的 `chains_reviewed` 改 true（归属要改的话同时改 `chains`）。
   **这件事和 Codex 的实现可以并行**——改的是数据，不是代码。
3. ~~三天的人工归属~~ **已按「恢复实际工作日」处理**：那三天不再作为工作日存在，
   改为把汇报挂到真正做事的日子上（见 §0 与 §1.2）。需要确认的是这三处对应关系是否准确。
4. ~~2026-06-26 的 stage~~ **已改为 `lv2-snapshot`**。附带结论：`config.json` 的六个阶段不必改；
   可选的小改动是把 `data-processing` 的 label 改成「数据与服务器」，只动 label。
5. ~~回填范围~~ **22 天已全部写完**，见 `headlines.py`。需要确认的是这 22 条的措辞。

---

## 7. 完成验收（实施者填写）

- [ ] P0–P4 各期验收项逐条记录结果，未通过的明确写出来，不以「应该没问题」代替实测。
- [ ] 每个完整改动单独 commit 并 push：契约与采集脚本、构建接入、清单视图、图谱、交互、回填内容分开，不积攒到最后一次提交。
- [ ] 只暂存本项改动涉及的文件，保留仓库里其它未提交材料（当前工作区有 `2026-10-10-沪市开盘空窗原因与G4核查.md`、`artifacts/grouped-kernel-report-2026-10-09/`、`content/daily/2026-10-10.md`、`exports/` 等未跟踪内容，不要顺带提交）。
- [ ] 推送后核对 GitHub 已含目标 commit，再核对 Cloudflare 构建与线上版本；三者分别记录，推送成功不等于线上已更新。
- [ ] 采集脚本确认只在本地运行过，构建日志中没有访问其它仓库的痕迹。
- [ ] `design-demos/journal-prototype/` 是一次性原型，正式版上线并验收后可以整目录删除；删除前确认 `content/chains.json` 已经承接了链条草案。
