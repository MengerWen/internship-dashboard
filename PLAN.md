# PLAN — 量化实习成果看板(Internship Showcase Dashboard)

> **本文档是完整实施规格。实施者(Codex)应按第 12 节的里程碑顺序执行,每完成一个里程碑对照第 11 节验收标准自检。**
> 遇到本文档未定义的细节,遵循第 1.2 节的技术原则自行决策,并在 `DECISIONS.md` 中记录一行说明。

---

## 0. 环境约定(先读这一节)

- **操作系统**:Windows。所有路径、脚本须兼容 Windows(路径拼接一律用 `pathlib`,禁止硬编码 `/` 或 `\`)。
- **Python 环境**:固定使用 `D:\MG\anaconda3` 这个 Anaconda 环境。
  - 调用方式:`D:\MG\anaconda3\python.exe`(不要假设 `python` 在 PATH 里指向它)。
  - 安装依赖:`D:\MG\anaconda3\python.exe -m pip install <package>`。缺什么装什么,装完把精确版本写入项目根目录 `requirements.txt`。
  - 预计需要的库:`python-frontmatter`、`markdown`、`pymdown-extensions`、`pygments`。如实现中发现需要别的,自行安装并同步进 `requirements.txt`。
- **Node**:仅用于搜索索引(`npx -y pagefind`)。本地若无 Node,搜索索引这一步允许跳过(build.py 打印警告即可),云端构建时由 Cloudflare Pages 环境执行。**项目本身不引入任何 npm 前端依赖,没有 package.json 里的框架。**
- **编码**:所有文件读写显式 `encoding="utf-8"`。内容大量为中文,这一点是硬约束。
- **项目根目录(submodule 形态)**:dashboard 是一个**独立的 private repo**,以 git submodule 挂载在既有仓库 `Quant_Research-Trading` 的 `26 Summer/❗思瑞投资/dashboard/` 路径下。本地开发路径即
  `D:\MG\！Internship\BUILD\汇报`。
  - 所有脚本必须容忍**含空格与 emoji 的父路径**(pathlib + 不假设 cwd);
  - 本地路径含 emoji 可能导致 `npx pagefind` 等 Node 工具异常,属已知风险:本地构建允许跳过 Pagefind(build.py 已有降级逻辑),搜索索引以云端构建为准;若需本地验证搜索,可将 dashboard 仓库单独 clone 到一个纯 ASCII 路径操作。

---

## 1. 项目概述

### 1.1 这是什么

一个**纯静态、零框架**的私人成果看板网站,包含两个视图:

1. **正式成果展示板(Showcase)**——项目各阶段的正式成果,整屏翻页式浏览,面向审阅者(导师/面试官/招生官);
2. **每日工作文档陈列板(Daily)**——上百篇 Markdown 日报渲染成网页,带目录、时间轴、全文搜索,面向日常汇报与自我沉淀。

内容主题:中国 A 股 Level-2 高频数据研究(订单簿快照构建 → 算法交易痕迹检测 → 因子构建 → 模型 → 策略)。

部署目标:GitHub 私有仓库 → Cloudflare Pages 自动构建 → Cloudflare Access 邮箱白名单门禁。同时支持导出**完全离线**的单文件夹版本(双击 index.html 可用)。

### 1.2 技术原则(所有未定义细节按此裁决)

1. **零前端框架**:原生 HTML/CSS/JS。不用 React/Vue/构建打包器(Vite/Webpack)。唯一的"构建"是 `build.py` + Pagefind。
2. **内容与展示分离**:所有内容以 Markdown 存放,前端壳(HTML/CSS/JS)不含实质内容。改内容永远不需要碰前端代码。
3. **单一数据源**:时间轴、阶段映射、页面清单等全部由 `build.py` 从 Markdown frontmatter 自动生成(`manifest.json`),**禁止**要求用户手动维护任何索引文件。
4. **离线优先**:`--offline` 模式下产物在 `file://` 协议下完整可用(内容内联,不依赖 fetch、不依赖 CDN)。在线模式可以用 fetch。
5. **可维护性优先于炫技**:JS 总量控制在几个职责清晰的文件内;不引入超过必要的抽象。

---

## 2. 仓库目录结构

```
internship-dashboard/
├── content/                        # ★ 用户唯一日常接触的目录
│   ├── showcase/                   # 正式成果,每阶段一个 md,文件名前缀决定顺序
│   │   ├── 01-lv2-snapshot.md
│   │   ├── 02-algo-footprint.md
│   │   ├── 03-factor.md            # 占位
│   │   ├── 04-model.md             # 占位
│   │   └── 05-strategy.md          # 占位
│   └── daily/                      # 日报,文件名 = YYYY-MM-DD.md
│       ├── 2026-07-06.md
│       └── 2026-07-07.md
├── site/                           # 前端壳(手写,构建时拷贝进 dist)
│   ├── index.html
│   ├── css/
│   │   ├── tokens.css              # 设计 token(见第 7 节)
│   │   ├── base.css
│   │   ├── showcase.css
│   │   └── daily.css
│   └── js/
│       ├── router.js               # hash 路由 + Tab 切换
│       ├── showcase.js             # 翻页/stepper/折叠
│       ├── daily.js                # 文档加载/TOC/时间轴
│       └── search.js               # Pagefind UI 挂载
├── templates/                      # build.py 用的 HTML 片段模板
├── build.py                        # ★ 唯一构建入口
├── config.json                     # 阶段定义、站点标题等(见 3.3)
├── requirements.txt
├── .gitignore
├── DECISIONS.md                    # 实施过程中的自主决策记录
├── DEPLOY.md                       # 部署操作手册(build.py 之外的人工步骤,见第 9 节)
├── README.md                       # 面向用户的日常使用说明(如何写日报、如何发布)
└── dist/                           # 构建产物,git 忽略
```

---

## 3. 内容层规范

### 3.1 日报 frontmatter

每篇 `content/daily/YYYY-MM-DD.md` 顶部:

```yaml
---
title: "算法足迹指标 v0.2:撤单生存时间分布"   # 可省略,省略时取文内第一个 H1,再没有则取日期
date: 2026-07-07                              # 可省略,省略时从文件名解析
stage: algo-footprint                          # 必填,取值见 config.json 的 stages
summary: "完成撤单延迟分布指标,初步区分出两类挂撤模式"  # 可选,时间轴悬停提示用
---
```

`build.py` 对缺 `stage` 的文件:打印醒目警告并归入 `unclassified` 阶段,**不中断构建**。

### 3.2 Showcase 文档结构约定

每个阶段 md 内部用标准 Markdown 层级。约定两个扩展语法(由 pymdown-extensions 提供,配置见 3.4):

- **折叠块**:`??? note "论文来源:Sato & Kanazawa (2023)"` 语法(pymdownx.details),渲染为 `<details>`。这是审阅者"点开-收起"的主要机制。折叠块可嵌套(指标 A/B/C 各一个折叠,内部再折论文/构建方法/运行结果)。
- **提示块**:`!!! warning "数据已脱敏"`(admonition),用于标注脱敏说明等。

frontmatter:

```yaml
---
title: "逐笔数据中的算法交易痕迹检测"
stage: algo-footprint        # 与 config.json stages 对应,驱动左侧 stepper
status: active               # done / active / planned,stepper 上显示不同状态样式
---
```

### 3.3 config.json

```json
{
  "site_title": "…(用户自填)",
  "stages": [
    {"id": "data-processing",  "label": "数据处理"},
    {"id": "lv2-snapshot",     "label": "快照构建"},
    {"id": "algo-footprint",   "label": "算法痕迹检测"},
    {"id": "factor",           "label": "因子构建"},
    {"id": "model",            "label": "模型搭建"},
    {"id": "strategy",         "label": "交易策略"}
  ]
}
```

stages 的顺序即 stepper 与时间轴配色的顺序。每个 stage 自动分配主题色(见第 7 节),Showcase stepper 与 Daily 时间轴共用同一套颜色。

### 3.4 Markdown 渲染配置

`markdown` 库启用扩展:`extra`(含 tables/fenced_code)、`toc`(生成锚点,`slugify` 需兼容中文标题——用 pymdownx.slugs 的 uslugify)、`pymdownx.details`、`pymdownx.superfences`、`admonition`、`codehilite`(Pygments,生成静态高亮 CSS,主题选与整体设计协调的一款)。数学公式暂不做(如内容出现 LaTeX 再加 KaTeX,记入 DECISIONS.md)。

---

## 4. build.py 规格

### 4.1 CLI

```
D:\MG\anaconda3\python.exe build.py            # 在线版,输出 dist/
D:\MG\anaconda3\python.exe build.py --offline  # 离线版,输出 dist-offline/
D:\MG\anaconda3\python.exe build.py --serve    # 构建后 http.server 起本地预览(默认 8000 端口)
```

### 4.2 构建步骤(在线模式)

1. 清空并重建 `dist/`;拷贝 `site/` 全部内容;
2. 渲染 `content/showcase/*.md` → `dist/showcase/<stage-id>.html`(**内容片段**,不含 `<html>` 壳,供前端 fetch 注入);同时输出 `dist/showcase/index-data.json`(阶段列表:id、label、title、status、顺序);
3. 渲染 `content/daily/*.md` → `dist/daily/<date>.html`(内容片段);
4. 生成 `dist/manifest.json`:
   ```json
   {
     "built_at": "2026-07-07T21:00:00+08:00",
     "stages": [...],                    // 透传 config.json
     "daily": [
       {"date": "2026-07-07", "title": "…", "stage": "algo-footprint", "summary": "…", "path": "daily/2026-07-07.html"}
     ]                                    // 按日期降序
   }
   ```
5. 为 Pagefind 生成**可索引页**:每篇日报和每个 showcase 阶段额外输出一个带最小 HTML 壳的完整页面到 `dist/_index-pages/`(含 `data-pagefind-body`、`data-pagefind-meta` 标注 title/date/stage),搜索结果点击跳转回 SPA 对应 hash(在壳里放一段跳转脚本:`location.replace('/#/daily/2026-07-07')`)。这样 SPA 结构与搜索索引解耦;
6. 若检测到 `npx` 可用:执行 `npx -y pagefind --site dist`(索引输出到 `dist/pagefind/`);不可用则打印警告跳过;
7. 输出 `dist/_headers`(内容见 9.3)与 `dist/robots.txt`(`Disallow: /`);
8. 打印构建摘要:N 篇日报 / M 个阶段 / 警告列表。

### 4.3 离线模式差异

- 所有内容片段与 manifest **内联**进单一 `index.html`(JSON 放 `<script type="application/json" id="...">`,HTML 片段放 `<template>`),JS 检测内联数据存在则不 fetch;
- 跳过 Pagefind(离线版不带搜索,搜索按钮隐藏);
- 产物 `dist-offline/` 整个文件夹可 zip 直接发人,`file://` 双击可用。**验收硬标准。**

### 4.4 健壮性

- 单篇 md 渲染失败:打印文件名+异常,跳过该篇,继续构建;
- 日期解析失败、frontmatter 非法:同上;
- 全程无交互输入(CI 环境可跑)。

---

## 5. 前端规格 — 全局壳

- **双 Tab**:右上角「正式成果展示」「每日汇报文档」。hash 路由:
  - `#/showcase` 与 `#/showcase/<stage-id>` (定位到某阶段屏)
  - `#/daily` 与 `#/daily/<date>` (定位到某篇日报)
  - 无 hash 默认 `#/showcase`。前进后退键可用(hashchange 驱动)。
- 顶栏另含:站点标题(左)、搜索按钮(右上,Tab 旁,点击展开 Pagefind 搜索浮层)。
- 响应式:桌面为主要目标;≤900px 时左侧 stepper 收为顶部横条、Daily 时间轴收为可展开抽屉。不必像素级打磨移动端,但不能坏。
- 无障碍底线:箭头按钮有 aria-label;折叠用原生 details 语义;键盘可操作翻页(↑/↓/PgUp/PgDn);`prefers-reduced-motion` 时关闭平滑滚动动画。

## 6. 前端规格 — 两大视图

### 6.1 Showcase(整屏翻页)

- 每个阶段一个 `<section>`,容器 `scroll-snap-type: y mandatory`,section `scroll-snap-align: start`,高度 100vh(减顶栏);
- **右下角固定上下箭头按钮** + 键盘方向键,`scrollIntoView({behavior:'smooth'})` 切换;首屏时上箭头禁用态,末屏时下箭头禁用态;
- **左侧固定 stepper**:垂直排列全部 stages(含 planned 占位阶段,置灰 + "规划中"标记);`IntersectionObserver` 监听当前 section,点亮对应节点;节点可点击跳转;当前节点与 URL hash 同步;
- section 内部:标题区(阶段名 + status 徽标)+ 内容区。**内容超出一屏时 section 内部滚动**(`overflow-y:auto`),内部滚动到底/顶后箭头键才切换 section(处理好滚动事件边界,这是本视图最容易做坏的交互,需重点测试);
- 折叠块(details)默认收起,提供「全部展开/收起」小按钮(打印或整体审阅用)。

### 6.2 Daily(文档 + 时间轴)

- 布局:左侧主文档区(约 70%)+ 右侧时间轴(约 30%,`position:sticky`);
- **时间轴**:读 manifest,按日期降序垂直排列;节点 = 日期 + 标题 + 阶段色点;按月份分组显示分隔;当前选中项高亮;悬停显示 summary;点击加载对应文档并更新 hash;超长列表自身可滚动;
- **文档区**:fetch 对应 HTML 片段注入;注入后扫描 `h2~h4` 生成**文档内 TOC**,呈现为文档区左缘的浮动细目录(或文档顶部可折叠目录,实施者选定后记录),点击平滑滚到锚点,滚动时当前小节高亮(scroll-spy);
- 默认加载最新一篇;
- 相邻日报「上一篇 / 下一篇」按钮在文档底部。

### 6.3 搜索(Pagefind)

- 顶栏搜索按钮展开浮层,挂 Pagefind 自带 UI(`/pagefind/pagefind-ui.js`,样式覆盖为本站 token);
- 结果项显示 title/date/stage(来自 data-pagefind-meta),点击经 `_index-pages` 跳转脚本回到 SPA 对应位置;
- 中文分词:构建时给可索引页 `<html lang="zh-CN">`,Pagefind 对 CJK 有内建处理,验证中文关键词(如"撤单")能命中。

---

## 7. 视觉设计规范

实施者在写 CSS 前先在 `site/css/tokens.css` 顶部注释里落一版 token 方案再动手。约束:

- **主题气质**:严肃、克制、数据密度高——这是量化研究成果的审阅界面,不是营销页。参考"交易终端/学术论文"的混合气质,避免营销页式大 hero 和花哨渐变;
- **主题模式**:**先只做深色版**。浅色版不在本期(第 10 节同步生效),但 token 全部走 CSS 变量,为未来加浅色留结构;
- **配色(定稿,写入 tokens.css)**:
  - 背景基底:`#111827`(深夜黑);
  - 正文主色:`#E5E7EB`(钛银);
  - 强调/高亮:`#FFF6D6`(极昼黄)——用于当前 stepper 节点、时间轴选中项、链接 hover、搜索命中等"当前焦点"语义,**克制使用**,它是暗底上唯一的暖色发光点;
  - 次级文字/辅助信息:`#8A95A5`(金属灰)——用于日期、meta、TOC 未激活项、占位说明;
  - 派生色由实施者从上述色板同色系推导(卡片面色取比背景略浅的 `#111827` 邻近灰阶、边框再浅一档、代码块底色略深一档),整体**低饱和 + 同色系**,禁止引入色板外的高饱和彩色;
  - 6 个 stage 的阶段色带:在低饱和前提下从冷灰-青-黄谱系内取彼此可区分的 6 色(极昼黄可作为其中"当前活跃阶段"的一色),深底上保证与背景对比度 ≥ 3:1,方案落进 tokens.css 注释并记录 DECISIONS.md;
- **布局质感**:内容区**切成卡片**组织——Showcase 每个折叠块/证据单元、Daily 的文档容器与时间轴节点均为卡片;卡片用「略浅面色 + 1px 同系边框 + 柔和投影」在深底上叠出层次(暗色主题下阴影效果弱,以"面色分层"为主、阴影为辅,投影用大模糊低透明度的黑,避免生硬);
- **字体(定稿)**:标题与正文采用衬线双拼:**Libre Baskerville(西文/数字)+ Noto Serif SC(中文)**,font-family 顺序:`"Libre Baskerville", "Noto Serif SC", serif`;代码与数据表仍用等宽栈 `ui-monospace, "Cascadia Mono", Consolas, monospace`;
  - **字体文件自托管**:两款字体均为 OFL 开源,下载 woff2 放入 `site/fonts/`,`@font-face` 本地引用,**禁止**使用 Google Fonts 等任何 CDN(离线硬约束的新形态);
  - Noto Serif SC 体积大,只引入实际用到的字重(建议 400/700 两档),并做子集化(如 pyftsubset 按常用汉字集裁剪,方案记录 DECISIONS.md);离线模式构建须把字体一并拷入 `dist-offline/`,断网验收时字体正常加载;
  - 衬线体作正文的可读性依赖行高与字号,正文 `line-height ≥ 1.8`、字号 ≥ 16px,数据表内数字保持 `font-variant-numeric: tabular-nums`(Libre Baskerville 数字表格对齐需实测,若对不齐则表格数字降级用等宽栈);
- **签名元素**:左侧 stepper 与右侧时间轴共用的"阶段色轴"贯穿两个视图,让整站有一个统一的视觉母题。把打磨预算集中在这里;
- 表格、代码块、折叠块是内容主力,优先保证这三者在深色底上的阅读体验(代码高亮选深色 Pygments 主题,与色板协调)。

---

## 8. 示例内容(构建可跑通的最低内容集)

为验收需要,创建**占位示例内容**(标注"示例,待替换"):

- `content/showcase/`:5 个阶段文件。01、02 写出完整结构示范(含嵌套折叠块:指标 → 论文来源/构建方法/运行结果示例,内容用无害占位文字 + 假数据表),03–05 为 `status: planned` 的占位;
- `content/daily/`:3 篇示例日报,日期取近三天,stage 各不同,内部含 h2/h3 层级、代码块、表格(测 TOC 与渲染);
- **禁止**在示例中编造任何看似真实的研究结论、收益数字或公司信息。示例数据一律明显虚构(如 `0.00 / 占位`)。

---

## 9. 部署与安全(写入 DEPLOY.md 的内容规格)

`DEPLOY.md` 是给用户的人工操作手册,须包含以下逐步说明(实施者写清楚每一步在哪个界面点什么):

### 9.1 GitHub(submodule 结构)

- 新建**独立 private repo**(如 `MengerWen/internship-dashboard`),这是 dashboard 的真身,含本 PLAN 定义的全部内容;
- 在父仓库 `Quant_Research-Trading` 中以 submodule 挂载:
  ```
  cd "D:\MG\_GitLinked\Quant_Research-Trading\26 Summer\❗思瑞投资"
  git submodule add https://github.com/MengerWen/internship-dashboard.git dashboard
  git commit -m "add dashboard submodule"
  git push
  ```
  形成结构:
  ```
  Quant_Research-Trading/
  └── 26 Summer/
      └── ❗思瑞投资/
          └── dashboard/   # → private repo internship-dashboard 的 submodule
  ```
- **DEPLOY.md 须写明 submodule 的日常须知**:
  - 日报的 commit/push 发生在 dashboard 子仓库内;父仓库里 submodule 指针不会自动前进,若希望父仓库记录最新版本,需在父仓库 `git add dashboard && git commit` 一次(不做也不影响网站发布——**Cloudflare Pages 直连 dashboard 仓库,发布只取决于子仓库的 push**);
  - 重新 clone 父仓库时需 `git clone --recurse-submodules`(或事后 `git submodule update --init`);
  - **权限边界提醒**:若父仓库 `Quant_Research-Trading` 是 public,submodule 只暴露子仓库的 URL 与 commit 哈希,不暴露内容(无权限者 clone 时该目录为空),内容安全由子仓库 private 属性保证——但子仓库**必须**保持 private,这一条在手册中加粗;
- Cloudflare Pages 连接的是 `internship-dashboard` 这个仓库本身(与 submodule 结构无关),9.2 节配置不变;
- `.gitignore`(dashboard 仓库内)至少含:`dist/`、`dist-offline/`、`__pycache__/`、`*.zip`、`node_modules/`,以及数据文件防御规则块(`*.csv`、`*.parquet`、`*.h5`、`*.pkl`、`data/`)——防止真实数据手滑入库。


### 9.2 Cloudflare Pages

- 连接该仓库;构建命令:
  `pip install -r requirements.txt && python build.py && npx -y pagefind --site dist`
- 输出目录 `dist`;环境变量 `PYTHON_VERSION` 设为与本地一致的大版本(写明查询本地版本的命令);
- 说明每次 `git push` 后自动重新构建发布。

### 9.3 门禁与防索引

- `_headers` 文件内容:
  ```
  /*
    X-Robots-Tag: noindex, nofollow
    X-Frame-Options: DENY
  ```
- Cloudflare Zero Trust → Access → 添加 self-hosted 应用,域名填 Pages 域名;策略:Allow,include = Emails(白名单)或 Email domain;认证方式 One-time PIN;会话时长建议 7 天;
- **必须**同时勾选保护 preview 部署(Pages 项目设置里的 Access 集成开关),并在手册里加粗提醒这一步——preview URL 未保护等于后门;
- 增删白名单、查看访问日志的操作路径。

### 9.4 日常发布流程(写入 README.md)

```
写 content/daily/2026-07-08.md → git add/commit/push → 1~2 分钟后线上更新
本地预览:D:\MG\anaconda3\python.exe build.py --serve
导出离线版:D:\MG\anaconda3\python.exe build.py --offline → 打包 dist-offline/
```

---

## 10. 明确不做(防止范围膨胀)

- 不做后端、数据库、评论、统计埋点;
- 不做深浅主题切换、多语言，浅色主题不在本期;
- 不做 Showcase 的"演示模式/PPT 模式"(未来可选,不在本期);
- 不引入 React/Vue/Tailwind/任何打包器;
- 不做数学公式渲染(除非示例内容确有需要,若加则用 KaTeX 且离线内联)。

---

## 11. 验收标准

逐条自检,全部通过才算完成:

1. `build.py` 在 Windows、`D:\MG\anaconda3\python.exe` 下无报错跑通,构建摘要正确;
2. 新增一篇合法日报后重新构建:时间轴、manifest、（若有 npx）搜索索引自动包含它,**全程未手改任何索引/前端文件**;
3. Showcase:箭头/键盘翻页顺滑;stepper 随滚动高亮且可点击;超一屏的 section 内部滚动与翻页不互相误触发;折叠块展开收起正常且可"全部展开";
4. Daily:时间轴按月分组、阶段配色正确;点击日期加载文档并更新 hash;TOC 自动生成、scroll-spy 高亮;直接访问 `…/#/daily/2026-07-07` 深链可达;
5. 搜索:中文关键词能命中日报正文,点击结果落到 SPA 内正确位置;
6. 离线版:`dist-offline/index.html` 在**断网 + file:// 双击**下,除搜索外全部功能可用;
7. 浏览器 console 无报错(两种模式);
8. `robots.txt`、`_headers` 存在于产物;`.gitignore` 含数据文件防御规则;
9. `DEPLOY.md`/`README.md`/`DECISIONS.md` 齐全,DEPLOY.md 覆盖 9.1–9.4 全部步骤且含 preview 保护的加粗提醒;
10. 全部文本文件 UTF-8,中文无乱码。

---

## 12. 实施里程碑(按序执行)

- **M1 构建管线**:目录骨架、config、示例内容、build.py(渲染 + manifest + 摘要),`--serve` 可本地预览裸内容;
- **M2 全局壳 + Daily**:tokens/base CSS、双 Tab 路由、Daily 三件套(文档区/TOC/时间轴);
- **M3 Showcase**:整屏翻页 + stepper + 折叠交互(含 6.1 的滚动边界处理);
- **M4 搜索**:_index-pages 生成、Pagefind 集成、搜索浮层;
- **M5 离线模式**:`--offline` 内联构建,断网验收;
- **M6 交付文档**:DEPLOY.md、README.md、_headers/robots、.gitignore 收尾,对照第 11 节全量自检。

每个里程碑完成后跑一次完整构建确认无回归。
