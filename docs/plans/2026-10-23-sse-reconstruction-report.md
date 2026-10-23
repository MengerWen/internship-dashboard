# 2026-10-23 沪市原始委托还原汇报

采用已评审的分页主线与六案例入口。正式汇报名义日期为 2026-10-23，说明前序深市规则、原始属性研究、公开适配、分层认证、C1–C5 收尾、真实沪市冒烟及后续独立定参与因子生产的交接。历史数字绑定各自样本与版本，不用当前仓库 HEAD 代替历史运行版本。

## 复用决定

|已有能力|调用链与实测|本次决定|
|---|---|---|
|prototype 的 orderDiagram / ambiguityDiagram / matchingDiagram|renderers → sceneMarkup / laboratory；已实际操作订单两步、兼容解释及匹配切换|复用图解与状态逻辑，统一进入正式主线和案例入口|
|proofDiagram / routeDiagram / fixesDiagram / clockDiagram / nextDiagram|共享输入数据，11 页与案例切换已在桌面和手机检查|复用；补齐定义差异比较、白名单入口、零尺度列、统计分母及下游职责|
|source-content.json 与 q-equity-errors.csv|已核实报告正文、352 列汇总和机制表|冻结为小型 authoring data；保留来源哈希，不复制完整因子向量|
|Builder.load_daily / renderShow / prepareIsolatedHtml|Markdown 登记 → manifest → iframe srcdoc，sandbox=allow-scripts|沿用现有接口，不修改共享构建器与路由；页面不依赖同源权限、CDN、持久存储或外部字体|
|已有 Noto Serif SC 字体|site/fonts 的两字重，字体子集工具本地可用|按报告字符集子集化并内嵌，兼顾字体一致、离线与体积|
|共享 scrollspy|适用于多 section 的锚点长页；本页是按钮控制的单页状态|不注入；由当前章节状态设置 aria-current 并保持手机选中项可见|

## 实现与验收

1. 将已评审图解整合为单一正式入口；按主题和案例双向导航。
2. 补齐术语、公开定义、研究边界、三种比较、性能与凭证限制；技术证据按需展开。
3. 生成 content/daily/2026-10-23.show.html 和精简主日报，使用现有构建器构建在线及离线目录。
4. 在真实内置浏览器检查独立页、站点沙箱和离线入口；检查全部主题、案例、关键控件、窄屏、键盘及证据窗口；保存有界截图和记录。

不新增公司服务器计算、Doris、定参、因子生产或 IC。此处的日报说明沿用既有业务证据。正式页面不把设计文件、演示版本或本地网页验收记作研究进展。
