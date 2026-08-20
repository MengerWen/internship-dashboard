# 视觉方向确认

- 用户原始选择：`我要方案C`
- 确认方向：方案 C｜高密度证据墙
- 确认日期：2026-08-20
- 桌面截图：`screenshots-c/desktop.png`
- 移动截图：`screenshots-c/mobile.png`
- 正式输出：`content/daily/2026-08-16.show.html`

初版实施约束：沿用方案 C 的高数据墨水比、白底证据墙和沪深颜色对照。下述研究图改稿确认覆盖初版图表清单。

## 2026-08-20研究图改稿确认

- 用户参考：西部证券研报式“10秒内撤单数量统计”原生频数折线图。
- 用户确认原话：`同意。开始实施`
- 本次属于已选定方向后的改稿，不重新走三方向门。
- 正文核心改为：沪市与深市0–10秒原生10ms日均频数分面图、每日等权每百万条标准化对照、逐日50ms热力图、1–6月小多图、局部峰强度与持续率表。
- 累计分布退出正文，仅允许整体分位数进入附录文字。
- 视觉系统：白底、黑色规则线、研究报告排版；红色表示沪市，深蓝表示深市；不使用装饰卡片和抽象视觉隐喻。
- 视觉母题：原生时间格点形成的“针状峰”和逐日热力图中的“竖向时钟条纹”。
- 桌面主图截图：`screenshots-v2/desktop/02-section.png`
- 桌面热力图截图：`screenshots-v2/desktop/04-section.png`
- 移动端主图截图：`screenshots-v2/mobile/02-section.png`

## 2026-08-20横向分节交互改稿确认

- 用户确认原话：`都做成.html了怎么还是完全上下滚动的样式？？我要最好是分section，能左右切换着查看的那种`
- 本次属于已选定方案 C 和研究图语法后的交互改稿，不重新走三方向门。
- 正式展示改为固定视口的10节横向研究播放器：结论、沪市频数、深市频数、标准化、沪市逐日、深市逐日、沪市月度、深市月度、峰值证据、解释边界。
- 全局页面禁止纵向滚动；每个研究主题独立一屏。峰值表仅在自身容器内保留必要的二维滚动。
- 支持顶部章节标签、上一节/下一节按钮、键盘方向键、Home/End、移动端左右滑动；当前位置写入 `localStorage`，刷新后保留。
- 网站真实路由截图：`screenshots-v3/desktop/site-embedded.png`
- 桌面单屏截图：`screenshots-v3/desktop/01-cover.png`、`02-sse-raw.png`、`05-sse-heat.png`、`07-sse-monthly.png`、`09-peak-table.png`、`10-boundary.png`
- 移动单屏截图：`screenshots-v3/mobile/01-cover.png`、`02-sse-raw.png`、`07-sse-monthly.png`、`09-peak-table.png`

## 2026-08-20沪深对照合并改稿确认

- 用户确认原话：`沪市频数↔深市频数，沪市逐日↔深市逐日，沪市月度↔深市月度；放在一起，不要单独每张图设一个section`
- 本次仍属于方案 C 内部的章节重组，不重新走三方向门。
- 原10节收敛为7节：结论、沪深原生频数、标准化、沪深逐日结构、沪深月度变化、峰值证据、解释边界。
- 三组沪深图均在同一章节内并列或上下成对呈现；桌面优先并列直接比较，窄屏在同一章节内上下排列，不拆成两个章节。
- 网站真实路由截图：`screenshots-v4/desktop/site-embedded-paired.png`
- 桌面对照截图：`screenshots-v4/desktop/02-frequency-pair.png`、`04-daily-pair.png`、`05-monthly-pair.png`
- 移动端对照截图：`screenshots-v4/mobile/02-frequency-pair.png`、`04-daily-pair.png`、`05-monthly-pair.png`

## 2026-08-20频数与逐日上下排列修正确认

- 用户纠正原话：`“原生频数”和“逐日结构”部分的深市↔沪市的图要上下排列啊！！！`
- 上一版将“同一section”误实现为桌面左右并排；本次明确修正为：原生频数与逐日结构在所有视口均为沪市上、深市下，两图各自占满章节宽度。
- 月度变化不在本次纠正范围，保持同一章节的双市场对照布局。
- 网站真实路由截图：`screenshots-v5/desktop/site-frequency-vertical.png`
- 桌面上下排列截图：`screenshots-v5/desktop/02-frequency-vertical.png`、`04-daily-vertical.png`
- 移动端上下排列截图：`screenshots-v5/mobile/02-frequency-vertical.png`、`04-daily-vertical.png`
