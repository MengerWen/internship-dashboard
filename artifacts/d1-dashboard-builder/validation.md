# D1 看板构建验收

输入仓库为 `汇报`，基准提交为 `fcfac725b3bba5aa1d40455c57b362292b6050eb`。Windows x64，Visual Studio 2019 C++ 生成工具，Release 构建。冻结参考由 `C:/Python313/python.exe build.py --release` 生成。复测只覆盖输出目录，调用同一份 `build.py` 的命令行入口。

| 构建 | 墙钟耗时 | 缓存状态 |
| --- | ---: | --- |
| 冻结 Python 全量 | 89.90 秒 | 新输出目录 |
| C++ 直接全量 | 34.47 秒 | 新输出目录，未传附件和日报缓存 |
| 冻结 Python 全量复测 | 54.03 秒 | 新输出目录 |
| C++ 发布构建入口 | 22.97 秒 | 紧接 Python 复测，新输出目录，缓存记录从零生成 |
| C++ 发布构建入口复跑 | 6.87 秒 | 复用 8,204 个附件、55 份 Markdown 渲染、81 条 Git 时间记录 |

耗时从启动构建到 Pagefind 完成，含文件复制和 Git 时间查询。编译、安装、逐文件核对及 Wrangler 耗时均在计时区间外。

全量和增量复跑分别用 `dashboard_compare` 与冻结产物核对。两次均为 9,136 个文件、2,367,372,518 字节全部一致，差异、缺少和新增均为 0。覆盖 52 篇日报、6 个阶段、133 天日志、133 份证据 JSON、104 个下载文件、194 个搜索页和 252 个 Pagefind 文件。首页资产版本与清单构建时间采用冻结参考当次的值，其余路径和字节直接比较。8,204 条复制记录的源文件与目标文件签名均和 Wrangler 使用的 Node 签名规则相符。

增量复跑能重新复制被改动的生成附件并清理孤立的生成附件。实测复用 8,203 个附件、重新复制 1 个，恢复文件与冻结产物逐字节相同。

`dumpbin /DEPENDENTS` 仅列出 Windows 系统 DLL 与 MSVC 运行库。独立构建时 `PATH` 只有 `D:\MG\Git\cmd` 和 `C:\WINDOWS\System32`。已检查 `python`、`python3`、`py` 和 `node` 均无法从该 `PATH` 解析。Pagefind 1.6.0 直接以本机二进制运行。

## 复验命令

从仓库根目录执行。首次准备依赖与本机发布工具时运行 `npm ci` 和 `npm run workspace:build`。

```powershell
cmake -S scripts/native -B .local-build/native -G "Visual Studio 16 2019" -A x64
cmake --build .local-build/native --config Release --parallel 4
ctest --test-dir .local-build/native -C Release --output-on-failure
dumpbin /DEPENDENTS .local-build/native/Release/dashboard_builder.exe

$env:PATH = 'D:\MG\Git\cmd;C:\WINDOWS\System32'
if (Get-Command python,python3,py,node -ErrorAction SilentlyContinue) { throw 'Unexpected interpreter on PATH' }
& .local-build/native/Release/dashboard_builder.exe --release --output .local-build/d1/native-final --build-time 2026-11-24T21:39:08+08:00 --asset-version 20261124213805
& .local-build/native/Release/dashboard_compare.exe .local-build/d1/oracle .local-build/d1/native-final
```

依赖导入表、逐文件核对和计时原始记录保存在本次 worktree 的 `.local-build/d1/`。原生测试 3 项和 Node 测试 55 项通过，既有 `journal_sources` 目标也在相同工具链下编译通过。验收覆盖本次输入使用的 Markdown 和 Windows x64 发布环境。

后续人工发布前，从与 `origin/main` 一致的干净 `main` 执行以下检查。生产发布沿用 [部署手册](../../DEPLOY.md)。

```powershell
npm ci
npm run workspace:build
npm run build:release -- --output .local-build/release-check
npm test
npm run workspace:audit
npm run deploy -- -DryRun
```
