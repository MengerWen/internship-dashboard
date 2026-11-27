param([switch]$DryRun, [switch]$FullAssets)

$ErrorActionPreference = 'Stop'
# 仓库路径含非 GBK 字符（❗），按 UTF-8 读取 git 等命令的输出，避免路径被替换成 ?
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$total = [Diagnostics.Stopwatch]::StartNew()
$lock = $null
$previousCopyManifest = $env:DASHBOARD_ASSET_COPY_MANIFEST
$previousNativeBinDir = $env:DASHBOARD_NATIVE_BIN_DIR

function Assert-MainCommit([string]$Commit) {
    $branch = git -C $repo symbolic-ref --quiet --short HEAD
    if ($LASTEXITCODE -ne 0 -or $branch -cne 'main') {
        throw '请从主工作区的 main 发布。'
    }

    $headCommit = git -C $repo rev-parse --verify HEAD
    if ($LASTEXITCODE -ne 0 -or $headCommit -ne $Commit) {
        throw '发布期间主工作区 HEAD 已变化，请从目标提交重新运行。'
    }

    $remoteRef = git -C $repo ls-remote --exit-code origin refs/heads/main
    if ($LASTEXITCODE -ne 0 -or $remoteRef -ne ("{0}{1}refs/heads/main" -f $Commit, [char]9)) {
        throw 'HEAD 必须与 GitHub main 一致，请核对并推送目标提交。'
    }
}

function Get-WorkingChanges([string]$Directory) {
    git -C $Directory status --porcelain=v1 --untracked-files=all
    if ($LASTEXITCODE -ne 0) { throw "无法检查工作区状态 $Directory" }
}

function Get-IgnoredSources([string]$Directory) {
    git -C $Directory ls-files --others --ignored --exclude-standard -- content site ':(exclude)content/assets/**'
    if ($LASTEXITCODE -ne 0) { throw "无法检查忽略的站点源码 $Directory" }
}

function Assert-OrdinaryDirectory([string]$Directory) {
    $item = Get-Item -LiteralPath $Directory -Force -ErrorAction SilentlyContinue
    if ($item -and (!$item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint))) {
        throw "发布路径必须是普通目录 $Directory"
    }
}

function Assert-ReleaseWorktree {
    $paths = git -C $releaseDir rev-parse --path-format=absolute --show-toplevel --git-common-dir
    if ($LASTEXITCODE -ne 0 -or $paths.Count -ne 2 -or
        [IO.Path]::GetFullPath($paths[0]) -ne $releaseDir -or
        [IO.Path]::GetFullPath($paths[1]) -ne $gitCommonDir) {
        throw "发布目录不是本仓库的专用 worktree $releaseDir"
    }
    git -C $releaseDir symbolic-ref --quiet HEAD | Out-Null
    if ($LASTEXITCODE -ne 1) { throw '发布 worktree 必须处于 detached HEAD。' }
}

function Assert-ReleaseSource([string]$Commit) {
    Assert-OrdinaryDirectory $localDir
    Assert-OrdinaryDirectory $releaseDir
    Assert-ReleaseWorktree
    foreach ($directory in @($localDir, $releaseDir)) {
        if (Get-Item -LiteralPath (Join-Path $directory 'node_modules') -Force -ErrorAction SilentlyContinue) {
            throw "发布工作区的依赖必须从主仓解析，请核对 $directory/node_modules"
        }
    }
    $headCommit = git -C $releaseDir rev-parse --verify HEAD
    if ($LASTEXITCODE -ne 0 -or $headCommit -ne $Commit) {
        throw '隔离 worktree 的 HEAD 与发布提交不一致。'
    }
    if (Get-WorkingChanges $releaseDir) { throw '隔离 worktree 中仍有未提交或未跟踪文件。' }
    if (Get-IgnoredSources $releaseDir) { throw '隔离 worktree 中存在未入库的忽略源码。' }
}

function Assert-Dependencies {
    $releaseLock = Join-Path $releaseDir 'package-lock.json'
    $mainLock = Join-Path $repo 'package-lock.json'
    $installedLock = Join-Path $repo 'node_modules/.package-lock.json'
    $hint = '请按发布提交的 package-lock.json 在主工作区运行 npm ci。'
    if ((Get-FileHash -LiteralPath $releaseLock).Hash -ne (Get-FileHash -LiteralPath $mainLock).Hash) {
        throw "主工作区与发布提交的依赖锁不一致。$hint"
    }
    if (-not (Test-Path -LiteralPath $installedLock -PathType Leaf)) {
        throw "缺少已安装依赖的锁文件。$hint"
    }

    # npm 的安装锁只记录本机安装的包，不能直接与跨平台的源码锁比较哈希。
    @'
const { readFileSync } = require('node:fs');
const [releaseLock, installedLock] = process.argv.slice(2);
const readPackages = file => JSON.parse(readFileSync(file, 'utf8')).packages;
const expected = readPackages(releaseLock);
const installed = readPackages(installedLock);
for (const [name, pkg] of Object.entries(installed)) {
    const target = expected[name];
    if (!target || ['version', 'integrity', 'resolved'].some(key => pkg[key] !== target[key])) {
        throw new Error('Installed dependency differs from the release lockfile: ' + name);
    }
}
for (const [name, pkg] of Object.entries(expected)) {
    if (!name || installed[name]) continue;
    if (pkg.optional && ((pkg.os && !pkg.os.includes(process.platform)) ||
                         (pkg.cpu && !pkg.cpu.includes(process.arch)))) continue;
    throw new Error('Missing installed dependency from the release lockfile: ' + name);
}
'@ | node - $releaseLock $installedLock
    if ($LASTEXITCODE -ne 0) { throw "本机安装的 Node 依赖与发布提交不一致。$hint" }
}

$repo = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $repo
try {
    $gitCommonDir = git rev-parse --path-format=absolute --git-common-dir
    if ($LASTEXITCODE -ne 0) { throw '无法定位 Git 公共目录。' }
    $gitCommonDir = [IO.Path]::GetFullPath($gitCommonDir)
    try {
        $lock = [IO.File]::Open((Join-Path $gitCommonDir 'dashboard-publish.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    } catch [IO.IOException] {
        throw '无法锁定发布，请检查是否已有发布正在运行。'
    }

    $commit = git rev-parse --verify HEAD
    if ($LASTEXITCODE -ne 0) { throw '无法读取发布提交。' }
    Assert-MainCommit $commit
    $changeCount = @(Get-WorkingChanges $repo).Count + @(Get-IgnoredSources $repo).Count
    if ($changeCount) {
        Write-Warning "主工作区有 $changeCount 项未提交、未跟踪或忽略的源码改动，已自动隔离。本次严格只发布 origin/main 提交 $commit。"
    }
    Write-Host "发布提交 $commit"

    $nativeBinDir = Join-Path $repo '.local/native/bin'
    $wrangler = Join-Path $repo 'node_modules/.bin/wrangler.cmd'
    $wranglerJs = Join-Path $repo 'node_modules/wrangler/bin/wrangler.js'
    if (-not (Test-Path -LiteralPath (Join-Path $nativeBinDir 'dashboard_builder.exe') -PathType Leaf)) {
        throw '缺少 dashboard_builder，请先运行 npm run workspace:build。'
    }
    if (!(Test-Path -LiteralPath $wrangler -PathType Leaf) -or !(Test-Path -LiteralPath $wranglerJs -PathType Leaf)) {
        throw '缺少 Wrangler，请先运行 npm ci。'
    }

    $localDir = Join-Path $repo '.local'
    $releaseDir = Join-Path $localDir 'release-worktree'
    $distDir = Join-Path $releaseDir 'dist'
    Assert-OrdinaryDirectory $localDir
    Assert-OrdinaryDirectory $releaseDir
    Assert-OrdinaryDirectory $distDir
    if (Test-Path -LiteralPath $releaseDir) {
        Assert-ReleaseWorktree
        git -C $releaseDir checkout --detach --force $commit
        if ($LASTEXITCODE -ne 0) { throw '无法更新隔离发布 worktree。' }
        git -C $releaseDir clean -fd -e dist -e .wrangler
        if ($LASTEXITCODE -ne 0) { throw '无法清理隔离发布 worktree。' }
    } else {
        git worktree add --detach --force $releaseDir $commit
        if ($LASTEXITCODE -ne 0) { throw '无法创建隔离发布 worktree。' }
    }
    Assert-ReleaseSource $commit
    Assert-OrdinaryDirectory $distDir

    $arch = node -p 'process.arch'
    if ($LASTEXITCODE -ne 0) { throw '无法读取 Node.js 架构。' }
    Assert-Dependencies
    $pagefindBin = Join-Path $repo "node_modules/@pagefind/windows-$arch/bin"
    $pagefind = Join-Path $pagefindBin 'pagefind_extended.exe'
    if (-not (Test-Path -LiteralPath $pagefind -PathType Leaf)) {
        $pagefind = Join-Path $pagefindBin 'pagefind.exe'
    }
    if (-not (Test-Path -LiteralPath $pagefind -PathType Leaf)) {
        throw '缺少 Pagefind 二进制，请先运行 npm ci。'
    }

    Set-Location -LiteralPath $releaseDir
    $env:DASHBOARD_NATIVE_BIN_DIR = $nativeBinDir
    $env:DASHBOARD_ASSET_COPY_MANIFEST = $null
    $build = [Diagnostics.Stopwatch]::StartNew()
    $buildArgs = @('scripts/workspace_inventory.cjs', '--dashboard', '--release', '--pagefind', $pagefind)
    if (-not $FullAssets) {
        $env:DASHBOARD_ASSET_COPY_MANIFEST = Join-Path $gitCommonDir 'dashboard-release-asset-copies.json'
        $buildArgs += @('--asset-copy-manifest', $env:DASHBOARD_ASSET_COPY_MANIFEST)
        $buildArgs += @('--daily-cache', (Join-Path $gitCommonDir 'dashboard-release-daily-cache.json'))
    }
    node @buildArgs
    if ($LASTEXITCODE -ne 0) { throw "站点构建失败，退出码 $LASTEXITCODE。" }
    Assert-OrdinaryDirectory $distDir
    foreach ($asset in @('dist/index.html', 'dist/manifest.json', 'dist/pagefind/pagefind-entry.json', 'dist/pagefind/pagefind-ui.js')) {
        if (-not (Test-Path -LiteralPath $asset -PathType Leaf)) { throw "缺少构建产物 $asset" }
    }
    Write-Host ('构建耗时 {0:F1} 秒' -f $build.Elapsed.TotalSeconds)

    Assert-MainCommit $commit
    Assert-ReleaseSource $commit
    $deployArgs = @('deploy', '--config', './wrangler.jsonc', '--strict', '--keep-vars', '--tag', "git-$commit", '--message', "Git $commit")
    if ($DryRun) { $deployArgs += '--dry-run' }
    $deploy = [Diagnostics.Stopwatch]::StartNew()
    if ($FullAssets) {
        & $wrangler @deployArgs
    } else {
        node --require ./scripts/publish-assets.cjs $wranglerJs @deployArgs
    }
    if ($LASTEXITCODE -ne 0) { throw "Wrangler 失败，退出码 $LASTEXITCODE。" }
    Write-Host ('Wrangler 耗时 {0:F1} 秒' -f $deploy.Elapsed.TotalSeconds)
} finally {
    $env:DASHBOARD_ASSET_COPY_MANIFEST = $previousCopyManifest
    $env:DASHBOARD_NATIVE_BIN_DIR = $previousNativeBinDir
    if ($lock) { $lock.Dispose() }
    Pop-Location
    Write-Host ('总耗时 {0:F1} 秒' -f $total.Elapsed.TotalSeconds)
}
