# 部署与安全手册

## 1. GitHub private repo 与 submodule

1. 在 GitHub 新建独立 private repo,例如 `MengerWen/internship-dashboard`。这个仓库就是 dashboard 的真实仓库,包含本项目全部文件。
2. 在父仓库 `Quant_Research-Trading` 中把 dashboard 作为 submodule 挂载:

```powershell
cd "D:\MG\_GitLinked\Quant_Research-Trading\26 Summer\❗思瑞投资"
git submodule add https://github.com/MengerWen/internship-dashboard.git dashboard
git commit -m "add dashboard submodule"
git push
```

3. 日常日报的 commit/push 发生在 `dashboard` 子仓库内。父仓库中的 submodule 指针不会自动前进;如果希望父仓库记录最新 dashboard 版本,再到父仓库执行 `git add dashboard && git commit`。
4. Cloudflare Pages 直接连接 `internship-dashboard` 仓库,网站发布只取决于 dashboard 子仓库的 push,与父仓库 submodule 指针是否更新无关。
5. 重新 clone 父仓库时使用:

```powershell
git clone --recurse-submodules <父仓库地址>
```

已 clone 的父仓库可执行:

```powershell
git submodule update --init
```

6. 权限边界提醒:如果父仓库是 public,submodule 会暴露子仓库 URL 和 commit hash,但不会暴露 private 子仓库内容。子仓库必须保持 private。

## 2. Cloudflare Pages

1. 进入 Cloudflare Dashboard -> Workers & Pages -> Create application -> Pages -> Connect to Git。
2. 选择 `internship-dashboard` private repo。
3. Build command 填:

```bash
pip install -r requirements.txt && python build.py
```

4. Deploy command 填:

```bash
npx wrangler deploy
```

`wrangler.jsonc` 已经声明 `assets.directory = "./dist"`,所以不需要在表单里重复写 `--assets ./dist`。

5. 如果开启 preview/non-production branch builds,Non-production branch deploy command 填:

```bash
npx wrangler versions upload
```

6. Path 填:

```text
/
```

7. 如果界面要求 Output directory,填:

```text
dist
```

8. Environment variables 中设置 `PYTHON_VERSION`。本地版本可用以下命令查询:

```powershell
D:\MG\anaconda3\python.exe --version
```

9. 保存后,每次 `git push` 都会触发 Cloudflare Pages 自动构建和发布。

### Git 时间与浅克隆

日报的 `published_at` 和 `updated_at` 默认来自 git 历史。Cloudflare 构建环境可能是浅克隆,导致首次提交时间不可得。`build.py` 会检测 `.git/shallow` 并尝试 `git fetch --unshallow`;失败时不会中断构建,但对应日报会降级到 mtime 并打印警告。

如果你需要在 Cloudflare 上稳定获得 git 时间,可以把 Build command 改成:

```bash
git fetch --unshallow || true && pip install -r requirements.txt && python build.py
```

更稳妥的做法是在日报 frontmatter 中手填:

```yaml
published: 2026-07-07 21:34:12
```

## 3. 门禁与防索引

构建产物会自动生成 `_headers`:

```text
/*
  X-Robots-Tag: noindex, nofollow
  X-Frame-Options: DENY
```

也会生成 `robots.txt`:

```text
User-agent: *
Disallow: /
```

Cloudflare Access 配置:

1. 进入 Cloudflare Zero Trust -> Access -> Applications。
2. Add an application -> Self-hosted。
3. Domain 填 Pages 生产域名。
4. Policy 选择 Allow。
5. Include 选择 Emails 或 Email domain,填入白名单。
6. Login methods 建议启用 One-time PIN。
7. Session duration 建议设置 7 days。
8. 必须同时保护 preview 部署:在 Pages 项目设置里启用 Access integration 或为 preview 域名添加同样的 Access 应用。preview URL 未保护等于后门。
9. 增删白名单:Zero Trust -> Access -> Applications -> 对应应用 -> Policies -> Include。
10. 查看访问日志:Zero Trust -> Logs -> Access。

## 4. 日常发布流程

```powershell
# 1. 写日报
notepad content\daily\2026-07-08.md

# 2. 本地预览
D:\MG\anaconda3\python.exe build.py --serve

# 3. 提交发布
git add content
git commit -m "add daily report 2026-07-08"
git push

# 4. 导出离线版
D:\MG\anaconda3\python.exe build.py --offline
```

正常情况下 push 后 1-2 分钟线上页面会更新。
