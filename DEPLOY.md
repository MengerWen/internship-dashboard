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
4. Cloudflare Workers Builds 直接连接 `internship-dashboard` 仓库,网站发布只取决于 dashboard 子仓库的 push,与父仓库 submodule 指针是否更新无关。
5. 重新 clone 父仓库时使用:

```powershell
git clone --recurse-submodules <父仓库地址>
```

已 clone 的父仓库可执行:

```powershell
git submodule update --init
```

6. 权限边界提醒:如果父仓库是 public,submodule 会暴露子仓库 URL 和 commit hash,但不会暴露 private 子仓库内容。子仓库必须保持 private。

## 2. Cloudflare Workers 静态资产

1. 进入 Cloudflare Dashboard -> Workers & Pages -> 导入 Git 仓库,选择 `internship-dashboard` private repo。
2. Build command 填:

```bash
pip install -r requirements.txt && python build.py
```

3. Deploy command 填:

```bash
npx wrangler deploy
```

`wrangler.jsonc` 已经声明 `assets.directory = "./dist"`,所以不需要在表单里重复写 `--assets ./dist`。

4. 如果开启 preview/non-production branch builds,Non-production branch deploy command 填:

```bash
npx wrangler versions upload
```

5. Path 填:

```text
/
```

6. 如果界面要求 Output directory,填:

```text
dist
```

7. Environment variables 中设置 `PYTHON_VERSION`。本地版本可用以下命令查询:

```powershell
D:\MG\anaconda3\python.exe --version
```

8. 保存后,每次 `git push` 都会触发 Workers Builds 自动构建,并通过 `npx wrangler deploy` 发布 `dist/` 静态资产。

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

1. 进入 Workers 项目 -> Settings -> Domains & Routes -> workers.dev -> Enable Cloudflare Access。
2. 在 Zero Trust -> Access -> Applications 中确认对应应用已创建并指向 Worker 的 workers.dev 域名。
3. Domain 使用 Worker 的生产 workers.dev 域名。
4. Policy 选择 Allow。
5. Include 选择 Emails 或 Email domain,填入白名单。
6. Login methods 建议启用 One-time PIN。
7. Session duration 建议设置 7 days。
8. 必须确认 preview 版本 URL(`<version>-<name>.<subdomain>.workers.dev`)在保护范围内。preview URL 未保护等于后门。
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

## 5. 在线标签存储

`wrangler.jsonc` 已配置生产入口 `worker/index.mjs`、`ASSETS` 静态资源绑定和 `REPORT_TAGS` SQLite Durable Object。首次部署通过 `report-tags-v1` migration 建立持久存储，不需要手工创建数据库 ID。后续发布不会用仓库快照覆盖已保存标签。

Cloudflare Workers Builds 需安装 `package-lock.json` 对应的 Node 依赖。平台自动检测 `package.json` 时会安装；如配置过跳过依赖安装，Build command 应改为：

```bash
npm ci && pip install -r requirements.txt && python build.py
```

Deploy command 仍为 `npx wrangler deploy`。SQLite Durable Object 使用事务检查版本号，整批操作只写入一次；重复操作 ID 支持在响应丢失后重试。每次请求最多 512 KB，最多 200 个标签和 10000 篇汇报归属。

`GET /api/report-tags` 和 `PUT /api/report-tags` 都验证 Access JWT 的签名、签发者、应用 audience、有效期和邮箱。写入另外校验同源 Origin，并拒绝跨站请求。浏览器携带现有 Access 登录状态，不保存管理密码或 API 密钥。

当前配置：

- `ACCESS_ISSUER`：本站实际使用的 Cloudflare Access 团队域名。
- `ACCESS_AUD`：本站 Access 应用 audience，从生产域名的 Access 登录重定向核实。
- `TAG_EDITORS="*"`：所有通过本站 Access 登录的邮箱均可编辑，按 2026-09-07 用户要求设置。`*` 不代表允许匿名或任意未验证邮箱。

如果更换 Access 应用，需要同步 issuer/audience，否则标签 API 会拒绝访问。如果之后需要限制编辑者，可将 `TAG_EDITORS` 改为逗号分隔的邮箱，其余已登录访问者只读。保留原有 Cloudflare Access 站点保护，包括 preview 域名；API 自身校验不能代替静态正文的访问保护。

保存失败或冲突处理、导入导出和离线快照见 README。生产存储和仓库快照独立；需要最新离线分类时，应先从网页导出 JSON，再使用 `--tags-snapshot` 构建。

实现依据：[Cloudflare Access JWT 验证](https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/)、[SQLite Durable Objects 存储](https://developers.cloudflare.com/durable-objects/best-practices/access-durable-objects-storage/)。
