# 深市328列因子的601日收益评价报告

日期：2026-10-18。用本次分组定标后重新计算的328列因子，沿用2026-09-16展示页的同日收益、日度等权、44区间及完整样本诊断。交付当日看板展示页和Markdown，核心为IC/Rank IC与分组收益。

## 数据与实现

研究入口为 `scripts/evaluate_szse_model328_factors.py`，601日既有标签规格为 `638fa8814eaf79199adc1680500ecf1ec9a3e743ad9b5fbf47344b7cb441172c`。输入为新参数面板，完整验收SHA为 `fc0f323dca7c222f0ec6dbe44e472447b2e4139aee76c67318d42a71c64bbd83`。全部因子统计在wangly重新计算，报告只发布研究聚合，不传出逐股原值。

| 复用入口 | 覆盖范围与决定 |
| --- | --- |
| `build.py / Builder` | Markdown/frontmatter、展示页、路由、资产、下载沙箱原样复用 |
| `scripts/add_nav_scrollspy.py` | 原章节结构及粘性导航、末节定位和窄屏滚动原样复用 |
| `2026-09-16.show.html` | 直接读取已批准的排版及五节结构，更换研究对象、实际数值与来源身份 |
| `rawbank_report_view.js` | 复用原日度/月度/分组/OLS/分布/分期/定义七类明细、按需加载、Buy/Sell对照、筛选和CSV/JSON/SVG下载；将来源目录、定义键、层次、列数和参数说明配置化，旧页默认行为保持 |
| `rawbank_explorer.html/css` | 复用层次→定义→方向浏览器、双侧详情、标签页和手机布局 |
| `model328_definitions.metadata` | 从冻结清单和注册表构造中文定义、公式、分母与MathML；原有函数移到独立模块供本报告生成器调用 |
| `build_model328_report_20261018.py` | 只消费已验收的日度/区间聚合，验证全部328列来源、完整密度/OLS计数和资产哈希后生成报告；不发SQL或训练 |

每个因子的完整统计gzip后作为独立JS资产按需加载，主HTML内嵌全部328列×44区间相关/组差摘要。单资产不超过25MiB，原始浮点精度进入下载，表格仅格式化显示。普通收益均值、NW标准误、组内离散度、汇集OLS和日均IC分别标注。并列同组、空组不填零、原始方向和至少30个IC配对等合同不改。

再生成：`python -X utf8 tools/build_model328_report_20261018.py --research-root <研究仓库> --input <服务器聚合下载目录>`。输入目录含 `report-data.json.gz`、`evaluation-result.json`、guard和资源/并发凭证；完整原始聚合仅用于本地生成，不重复提交。资产里的逐列JSON统计、全部区间CSV和输入身份支持复核。

## 验收与发布

1. 主摘要、328份按需资产和CSV逐项核对列序、601日期、44区间、成对数、有效日数、OLS/密度样本数及输入SHA。
2. 桌面1440px和手机390px验证结果范围、排序、逐因子七类明细、两侧对照、日期同步、空筛选、下载和放大；核对数据与图形对应，无横向溢出或控制台错误。
3. 只提交本报告及必要公共入口变动；保留其他任务修改。GitHub推送后核对Cloudflare线上版本和发布回执。

## 技能核对

沿用本会话2026-10-18 03:01—03:05 UTC已逐项读取的全局和插件设计技能，重新检索当前安装清单。当前documents、pdf、presentations、spreadsheets和template-creator版本为26.1017.11052；与已读26.1013.11914正文逐行比对，补读全部差异。documents、pdf和template-creator仅末尾换行变化；presentations增加Spaces目的地流程；spreadsheets调整交付引用。本次只交付既有看板日报，不调用上述文档创建流程。旧缓存google-slides与当前插件前缀均已核对。

直接应用shuorenhua的事实保护和技术说明语域，frontend-design的用户参考优先规则，huashu-design的既定方向迭代规则，impeccable的Read模式与有界验收，以及现有站点可访问性和响应式约定。其余图片、幻灯片、原型、宠物、系统与领域设计技能不启动各自的创建流程。已有视觉规范优先于通用反模板建议，不改动旧页的纸色、标题、数字栏和章节结构。
