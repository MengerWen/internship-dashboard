# 研究日志：全部链条默认展示

用户反馈：「都不好。我还是想要一打开‘研究日志’页面就能看到全部的链条的展示形式」。进一步询问首屏或纵向滚动后，用户要求「做出各种demo」。

本轮五版都必须默认绘制全部48条链，无须先选择方向、月份、日期或链。搜索只能高亮，不能让其他链消失。可以点击工作点或链读取详情，但详情不承担首次展示链条的职责。默认覆盖全历史，日期范围操作也不能减少链条身份的展示。横向滚动不作为阅读步骤。

| 方案 | 结构 | 取舍 |
|---|---|---|
| A 全链竖轴图谱 | 保持日期纵轴、48链同列，以响应式宽度收紧整个图面 | 接近原有图谱；保留全链并置，链名采用竖排短名 |
| B 全链横轴年表 | 48链各占一行，日期横轴适配页面宽度 | 全链默认展开，完整链名和日期更容易对应，允许上下滚动 |
| C 七区平铺图谱 | 七个方向在同一页平铺，各区所有链默认画出 | 链名空间更多，跨区关系通过高亮与文字承接说明 |
| D 全链研究墙 | 一屏尽量平铺48个链身份及真实日期分布 | 优先同时辨认全部链；选择后再读具体进展 |
| E 链与月份矩阵 | 48链各占一行，6—11月构成固定六列 | 月度分布清楚，单元格可展开真实日期与工作点 |

五版共用上一轮已修订的真实内容、站点字体与纸墨色。数据为48链、114个记录日、401个工作点，截止2026-11-02。上一轮五版作为被否决的探索保留，本轮尚未选定正式方案。

## 共用接口

复用 `../2026-11-03-journal-layouts/data.js`、`shared.js`、`shared.css`，不修改它们。`config.js` 改写本轮五版名称；每版只写自己 `variants/` 下的 JS/CSS。

注册 `window.JournalVariants.A` 至 E，为 `function(root, api)`。`api.data` 含 tracks/chains/days/handoffs；`api.points({chainId,trackId,from,to,query,reverse})` 返回 `{date,note,chain,day,outcome}`；`api.chain(id)`、`track(id)`、`dayTasks(day)`、`esc(text)`、`chainLink(id,text)`、`pointLink(point,text)`、`openChain(id)`、`openPoint(date,id)`、`openDay(date)` 可用。`api.points({reverse:false})` 按日期正序。日期数和统计全部从数据计算。

每条链最外层身份元素必须标 `data-all-chain="链ID"`，每条恰好一个，方便核对初始是否全部呈现。时间图的工作点标 `data-open-point` 和 `data-open-date`，以使用共同阅读层。`data-all-chain` 不意味着选中或归属变更。

CSS均以 `body[data-variant="A"]` 等限定范围。可复用 `.button`、`.subtle-button`、`.toolbar`、`.field`、`.chain-link`、`.point-link`、`.date-label`、`.muted`、`.page-heading`。新布局不能引用上一轮的方向展开或隐藏逻辑。正文不少于14px，标签不少于12px；密集日期图可以用小定位点，但链名要能读。窄屏允许重新排成多段纵向展示，禁止页面横滚。

本轮按项目要求只做必要代码和资源检查，不增加浏览器验收或截图，不重试此前被策略拦截的本地服务启动。交付同页切版入口与无服务对话预览，提交并核对远端包含目标提交。临时证据默认放 `.local/runs/journal-all-chains/`；本轮不清理其他任务。

`index.html` 为总览，`demo.html?variant=A` 至 E 为完整可操作版本。运行 `python build_inline.py --output 完整输出路径` 可从相同代码生成对话预览。检查范围和五版48个初始链ID的对照结果见 `checks.json`。本轮尚无用户选定方向，保留至2026-11-10复查。
