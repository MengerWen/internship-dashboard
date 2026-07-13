# 量化实习成果看板

这是一个纯静态、零前端框架的实习成果展示站点。日常只需要维护 `content/` 下的 Markdown 文件,再运行构建命令即可生成网页。

## 本地预览

```powershell
D:\MG\anaconda3\python.exe build.py --serve
```

命令会先构建 `dist/`,再启动本地 `http.server`。如果 8000 端口被占用,脚本会自动尝试下一个端口。

## 写一篇日报

在 `content/daily/` 下新增 `YYYY-MM-DD.md`:

```markdown
---
title: "日报标题"
date: 2026-07-08
stage: algo-footprint
summary: "一句话摘要,会显示在时间轴上。"
# 可选: published: 2026-07-08 21:34:12
---

# 日报标题

## 今日目标

正文内容。
```

`stage` 必须使用 `config.json` 中已有的阶段 id。缺失或未知时构建不会中断,但会打印警告并归入 `unclassified`。

发布时间默认来自 git 历史:首次提交时间作为发布时间,最后一次提交时间作为更新时间。若 Cloudflare 浅克隆或历史不可得,构建会降级到文件 mtime 并打印警告。需要稳定控制首次发布时间时,在 frontmatter 中手填 `published: YYYY-MM-DD HH:MM:SS`。

## 为某天写展示版

每篇日报最多配一个展示版,与主日报放在同一目录:

```text
content/daily/2026-07-08.md
content/daily/2026-07-08.show.md
content/daily/2026-07-08.show.html
```

`.show.md` 和 `.show.html` 二选一。两者同时存在时 `.show.html` 生效。

标准写法使用 `.show.md`,每个 H2 是一幕:

```markdown
---
title: "当日成果展示"
---

## 幕一:问题

正文。

## 幕二:构建

??? note "细节"
    折叠内容。
```

完全定制写法使用 `.show.html`,会通过 iframe `srcdoc` 隔离运行,脚本可以执行。定制页应自包含,不要依赖 `<head>` 中的外部引用,也不要引用外部 CDN。模板在 `templates/show-html-starter.html`。

## 更新正式成果页

正式成果放在 `content/showcase/`。每个文件的 frontmatter 至少包含:

```yaml
---
title: "阶段标题"
stage: lv2-snapshot
status: active
---
```

`status` 可用值为 `done`、`active`、`planned`。正文支持表格、代码块、Mermaid 图表、`??? note` 折叠块和 `!!! warning` 提示块。Mermaid 使用标准围栏写法：

````markdown
```mermaid
flowchart LR
    A[输入] --> B[输出]
```
````

## 发布流程

```powershell
D:\MG\anaconda3\python.exe build.py
git add content config.json README.md DEPLOY.md DECISIONS.md build.py site requirements.txt .gitignore
git commit -m "update dashboard content"
git push
```

Cloudflare Workers Builds 连接 dashboard 仓库后,每次 push 会自动重新构建并部署静态资产。

## 导出离线版

```powershell
D:\MG\anaconda3\python.exe build.py --offline
```

生成的 `dist-offline/` 可以直接打包发送。对方解压后双击 `index.html` 即可浏览。离线版不包含全文搜索,其它内容、路由、Showcase 和 Daily 交互均可用。
