# 2026-10-23 沪市原始委托还原 HTML 交付

正式内容为 `content/daily/2026-10-23.show.html`，并以同日 Markdown 登记汇报站标题、日期、摘要和文字入口。采用已选择的分页主线与案例结构：11 个主题、6 个案例、14 条术语短解；字段、完整定义、统计口径、参数规则与原始地址按需展开。

页面解释前序深市订单规则与共享因子引擎提供什么、本项公开事实与适配器交付什么，以及后续独立沪市定参、参数包、因子面板和 IC 的依赖顺序。隐藏属性研究、公开定义变化、固定时钟适配正确性与 Q_equity 误差分别陈述。并行结构任务的状态不归入本项成果。

## 来源与重建

研究依据固定为 `2a0dac94c750eed237207a6bc7d288a81d428130`，352 列误差和最差 20 列机制取自该版本原始报告；输入文件身份保存在 authoring data 与页面证据中。8 个报告路径均已在该版本核对存在。没有读取真实沪市输入、运行服务器计算、查 Doris、定参、生产因子或计算 IC。

本地重建：

```powershell
python scripts/build_sse_reconstruction_report_20261023.py
python scripts/build_sse_reconstruction_report_20261023.py --check
python scripts/verify_sse_reconstruction_report_20261023.py --preview
```

作者源文件在 `scripts/sse_reconstruction_report_20261023/`。HTML 内嵌脚本、图解、汇总数据和两字重字体子集；运行无需 CDN、外部字体、同源权限或持久存储。字体复用须同时满足源字体哈希和字符覆盖检查。

## 已执行的检查

- JavaScript 语法与静态契约检查通过；生成文件与 authoring source 一致。
- 11 个主线页、6 个案例、案例回到主线、订单消息与盘口联动、匹配规则切换均可操作。
- 同一时钟的输入 / 引擎比较、更换时钟的误差、白名单与证据入口分别可用。
- 六核距离维度、F40 依赖链、误差列选择、最差 20 列、6 个零尺度列、秩相关分布可展开核对。
- 当前内置浏览器中检查独立页、`sandbox=allow-scripts` 的站内 srcdoc 展示、短展示栏目录、键盘翻页和放大展示；不授予同源权限。
- 390 像素视口下逐项检查 11 页与 6 案例；页面无全局横向溢出，当前章节在横向目录中保持可见。检查后恢复浏览器默认尺寸。
- 最终禁用按钮文本对比度实测约 6.19，透明度为 1；独立页未观测到 console error / warn。
- 已有导航测试 24 项通过。

在线与离线登记使用原站点 `Builder` 定向生成，验证 manifest、展示资源注入及离线内嵌内容。其他日期、约 701.7 MiB 无关内容资产和 Pagefind 未重复构建。临时副本在验收后移除，保留哈希、计数、截图和删除回执。

浏览器工具只允许 HTTP / HTTPS，`file://` 直接打开未验收；离线构建的交互是在既有 localhost 预览中核对，不能将它称为本地双击离线文件已通过。设计检查脚本另用自身 Chromium 做过一次外观测量，最终交互及禁用文字颜色在当前内置浏览器复核，该测量不作为 `file://` 直开验收。

## 状态与证据

本项交付包括正式 HTML、重建源与验收材料。同日 Markdown 由另一任务维护，本项发布不修改或暂存该文件。提交范围、远端 SHA、Cloudflare 构建和上线后的交互验收另记在 `artifacts/sse-reconstruction-report-20261023/publication.json`，以实际回执区分提交、推送和上线。页面中的 GitHub、wenjie 与业务运行版本属于原研究验收历史，不能解释为这次文档工作重新运行了业务。

`artifacts/sse-reconstruction-report-20261023/` 保留 `contract-check.json`、`browser-checks.json`、截图及清理回执。报告代码保持在主工作目录的 main，其他任务的未跟踪文件与成果未修改。
