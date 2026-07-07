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
---

# 日报标题

## 今日目标

正文内容。
```

`stage` 必须使用 `config.json` 中已有的阶段 id。缺失或未知时构建不会中断,但会打印警告并归入 `unclassified`。

## 更新正式成果页

正式成果放在 `content/showcase/`。每个文件的 frontmatter 至少包含:

```yaml
---
title: "阶段标题"
stage: lv2-snapshot
status: active
---
```

`status` 可用值为 `done`、`active`、`planned`。正文支持表格、代码块、`??? note` 折叠块和 `!!! warning` 提示块。

## 发布流程

```powershell
D:\MG\anaconda3\python.exe build.py
git add content config.json README.md DEPLOY.md DECISIONS.md build.py site requirements.txt .gitignore
git commit -m "update dashboard content"
git push
```

Cloudflare Pages 连接 dashboard 仓库后,每次 push 会自动重新构建发布。

## 导出离线版

```powershell
D:\MG\anaconda3\python.exe build.py --offline
```

生成的 `dist-offline/` 可以直接打包发送。对方解压后双击 `index.html` 即可浏览。离线版不包含全文搜索,其它内容、路由、Showcase 和 Daily 交互均可用。
