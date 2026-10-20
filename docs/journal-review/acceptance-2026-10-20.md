# 研究日志实施与验收

日期：2026-10-20。按 `PLAN/2026-10-20-journal-column.md` 完成 P0–P4。实现基线为 `777bfa4c995b9a8a610717891557690dee19c63e`；后续设计文档、验收记录与证据换行约束不改变部署代码。

线上入口：[研究日志](https://internship-dashboard.mengerwenjie.workers.dev/#/journal)。发布收据、资产哈希和浏览器结果保存在 `artifacts/journal-column/release-receipt.json`。

## 各期结果

| 阶段 | 实测结果 |
|---|---|
| P0 证据采集 | 88 个 JSON；固定三个仓库版本；父仓库先限定目录再统计；重复采集及 `--check` 字节比较差异为 0。采集器不改链条注册表和日志 Markdown。源证据有 1 个文件名触发隐去，输出已替换，后扫描剩余配置敏感片段为 0。原计划“redact 命中 0”这一字面条件未达到，不能记作零命中。 |
| P1 构建与清单 | 干净检出构建 88 天、34 篇已跟踪日报、6 阶段，零告警、零 mtime 降级；清单查找、汇报跳转、窄屏排版通过。构建单元检查禁止调用外仓采集，仍能生成日志、索引和离线内联。 |
| P2 图谱 | 真实日期比例检查通过：9-23 至10-7 的空档为相邻一日距离的14倍；28 条链各有不同纵坐标；四类交接线型、收口、汇报刻度及直接标注已核对。1440、390 截图无整页横溢出。 |
| P3 交互 | 四种深链、证据首次展开才请求、仓库默认折起、悬停卡边界、日期窗、链条明暗、连续键盘翻日、焦点环及 Esc 通过。近1个月＋早期链条的0天状态没有伪选中带，并说明链条卡展示全部历史。Pagefind 搜“回测”能找到日志。导出的离线文件展开3个仓库，HTTP请求0、运行错误0。 |
| P4 内容审阅 | 88 天均为已撰写的一句话，原66条草稿已补齐；原55条推断逐条核对并确认或改写，构建结果剩余 inferred 为0。28条链、26条交接逐项记录，审阅者为Codex，没有冒称用户逐条签字。 |

逐日原始提交、计划与归属处置见同目录的 `2026-06.md` 至 `2026-10.md`。交接变更及其日期见 `chains-and-handoffs.md`。修正包括6-29文献工作、8月ML与撤单工作归属、9月模型报告、10-16存储交接；未把初次报告倒接为后续实验的成果。

全站34篇已跟踪日报中，有33篇与真实日志日期关联。计划里的35篇包含本地尚未提交的10-10日报；它没有纳入发布。旧工作区直接构建会因这份未提交材料出现时间降级告警，因此零告警结论来自只含已跟踪文件的隔离检出。

## 复现配置

采集起点为2026-06-01，证据快照固定于：

| 仓库 | revision |
|---|---|
| sirui-quant-research | `e488eaa6a3fe547c871ea396cfeef7761e6d8883` |
| Quant_Research-Trading | `ee956d57ef3bd8e8c3290ba84a294b0409f824c8` |
| internship-dashboard | `ae6efaa7b1f59851598364d1ab4b28ceb946bbc1` |

证据JSON通过`.gitattributes`固定LF。已在当前`core.autocrlf=true`环境模拟重新检出全部88个文件，逐个比较字节一致，避免Windows换行转换导致`--check`误报。

固定版本避免看板自己的采集提交不断使证据过期。刷新要显式更新配置中的 revision。服务器和 Cloudflare 构建均不运行采集器。

正式构建的 manifest 为127955字节，gzip为22467字节。它高于原方案约70KB的估计；没有新增前端依赖，完整提交证据仍按需加载。做了什么的前三条回退摘要在构建时写入轻量数据。

执行记录：

| 检查 | 结果 |
|---|---|
| `python scripts/collect_journal_evidence.py --check` | 88天、差异0、隐去1、待写0 |
| `python -m pytest -q tests` | 100 passed；最终一次29.69秒 |
| `npm test` | 11 passed |
| `npm run test:browser` | 8 passed |
| `npm run test:browser:embedded` | 3 passed |
| `python build.py`、`python build.py --offline`，干净检出 | 各34日报、88日志、0草稿、0告警 |
| `scripts/verify_journal.cjs`，隔离构建 | 1440/390各88天，overflow=false，errors=[]；离线requests=[]、errors=[] |
| 已导出离线副本 | 日期10-14，仓库3个，HTTP请求0，错误0 |

两条旧浏览器断言在实际运行后修正：标签种子本来已有未选中的归属；定标报告已含Total/Buy/Sell三方向。修改只使断言符合当前已提交内容，没有改标签产品或旧报告逻辑。

## 设计收尾

按已批准方向三扩展原有研究编辑台，沿用纸底、墨色和字体。原有网格与全站身份保留；日志中的珊瑚只表示当前选中或聚焦。没有重新发起风格选择。

已核对全局、项目及插件技能清单，并读取已知设计技能和新增的 `sites-remix`、`writing-shape`、`improve-codebase-architecture`、已安装的artifact-template系列。与本次静态日志扩展无关的图片、演示和模板工作流没有启动；没有调用技能示例中的外部模型。独立审阅和文档整理按 impeccable 的明确要求派生，两个子会话及主会话的原始 turn_context 均为 `gpt-6.1-sol / xhigh`。

唯一一次机械检测后的旧壳提示见 `design-system-audit.md`。新日志小字对比度、日卡摘要回退、键盘焦点和空窗口状态已修正。独立复核返回 **ship**，范围为新日志源码、有效截图和本地浏览器记录；它没有代替线上检查。现有产品事实及视觉规范已写入根目录 `PRODUCT.md`、`DESIGN.md` 和 `.impeccable/design.json`。

截图见 `artifacts/journal-column/`：`first-viewport-1440.png`、`first-viewport-390.png`、两宽度的day-evidence、chain和window-empty。Chrome整张超过16384px的长图会回卷；手机完整清单改为 `mobile-full-1.png`、`mobile-full-2.png`，位置写入 `mobile-capture.json`，主 `mobile.png` 为有效首屏。原型保留作审计对照；正式站点不引用原型文件。

## 提交、发布与现场

契约采集、构建、清单、图谱、交互、隐私修正、五个月内容复核、交接复核及收尾修正已分别提交并推送，每次均核对远端main包含该提交。本记录所在提交继续按同一规则推送。

GitHub推送记录与Cloudflare部署分别核对。发布前最新部署为 `df29ce26-b538-4d10-9656-7cb6514c1af2`，记录未提供可验证的Git SHA对应关系，不能据此声称本轮自动构建已发布。此次用干净隔离构建显式发布：

- 源码提交：`777bfa4c995b9a8a610717891557690dee19c63e`。
- Cloudflare版本：`ca4b52d2-ca24-446a-a7de-2e2f8d475d9a`，部署ID：`1720a2ad-ed9b-4bfe-8a63-c491de93bf70`。
- 发布时间：2026-10-20 06:59:34 UTC（上海14:59:34）；100%流量指向该版本。
- Wrangler tag：`journal-20261020`；message含完整源提交。使用`--keep-vars`，Worker、Access与标签存储代码均无变更。

已连接Chrome的线上现场：`#/journal`有88个日期列、88天/33篇汇报，无页面横溢出；`#/journal/2026-10-14`正确选中，展开3个证据仓库；`#/journal?chain=szse-model328`显示5天链卡；`#/journal?view=list`有88行。实际窗口2560×1305截图为 `production-2560.png`。已读日志中站点来源错误0条，另有1条已安装Chrome扩展的content_script报错。

追加线上空窗口组合时操作通道多次超时，未取得返回，不列作线上通过；相同组合已在本地两宽度完成验收。没有写入线上标签、改访问权限或运行公司服务器计算。

离线副本位于本工作区 `artifacts/journal-column/offline/index.html`，已核对与验收构建的入口、manifest、JS、CSS哈希一致，并重新从该副本实测证据展开。该生成目录和本地原始发布输出不入库；可复现代码、内容、收据、验收JSON和截图入库。

临时detached验证目录的三个源码文件与main已保存版本一致，未有独有提交；需要的离线产物已复制回主目录。清理结果在计划第7节记录。原工作区10-10材料、grouped-kernel产物及exports等未跟踪内容保留，没有暂存。
