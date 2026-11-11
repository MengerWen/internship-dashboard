param([switch]$DryRun, [switch]$FullAssets)

$ErrorActionPreference = 'Stop'
# 仓库路径含非 GBK 字符（❗），按 UTF-8 读取 git 等命令的输出，避免路径被替换成 ?
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$OutputEncoding = [Text.Encoding]::UTF8
$total = [Diagnostics.Stopwatch]::StartNew()
$lock = $null
$previousCopyManifest = $env:DASHBOARD_ASSET_COPY_MANIFEST

function Assert-ReleaseSource([string]$Commit) {
    $branch = git symbolic-ref --quiet --short HEAD
    if ($LASTEXITCODE -ne 0 -or $branch -ne 'main') {
        throw '请切换到 main 后发布。'
    }

    $headCommit = git rev-parse --verify HEAD
    if ($LASTEXITCODE -ne 0 -or $headCommit -ne $Commit) {
        throw '发布期间 HEAD 已变化，请从目标提交重新运行。'
    }

    $changes = git status --porcelain=v1 --untracked-files=all
    if ($LASTEXITCODE -ne 0 -or $changes) {
        throw '请先处理工作区改动，再从干净的 main 发布。'
    }
    $ignoredSources = git ls-files --others --ignored --exclude-standard -- content site ':(exclude)content/assets/**'
    if ($LASTEXITCODE -ne 0 -or $ignoredSources) {
        throw '站点源码中存在未入库的忽略文件，请核对后再发布。'
    }

    $remoteRef = git ls-remote --exit-code origin refs/heads/main
    if ($LASTEXITCODE -ne 0 -or $remoteRef -ne "$Commit`trefs/heads/main") {
        throw 'HEAD 必须与 GitHub main 一致，请核对并推送目标提交。'
    }
}

Push-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
try {
    $gitDir = git rev-parse --absolute-git-dir
    if ($LASTEXITCODE -ne 0) { throw '无法定位 Git 目录。' }
    try {
        $lock = [IO.File]::Open((Join-Path $gitDir 'dashboard-publish.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    } catch [IO.IOException] {
        throw '无法锁定发布，请检查是否已有发布正在运行。'
    }

    $commit = git rev-parse --verify HEAD
    if ($LASTEXITCODE -ne 0) { throw '无法读取发布提交。' }
    Assert-ReleaseSource $commit
    Write-Host "发布提交 $commit"

    $wrangler = Join-Path $PWD 'node_modules/.bin/wrangler.cmd'
    if (-not (Test-Path -LiteralPath $wrangler -PathType Leaf)) {
        throw '缺少 Wrangler，请先运行 npm ci。'
    }
    $dist = Get-Item -LiteralPath 'dist' -ErrorAction SilentlyContinue
    if ($dist -and ($dist.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'dist 是链接，请使用普通目录构建。'
    }

    $python = 'python'
    if ($env:DASHBOARD_PYTHON) { $python = $env:DASHBOARD_PYTHON }
    $build = [Diagnostics.Stopwatch]::StartNew()
    $buildArgs = @('build.py', '--release')
    if (-not $FullAssets) {
        $env:DASHBOARD_ASSET_COPY_MANIFEST = Join-Path $gitDir 'dashboard-asset-copies.json'
        $buildArgs += @('--asset-copy-manifest', $env:DASHBOARD_ASSET_COPY_MANIFEST)
        $buildArgs += @('--daily-cache', (Join-Path $gitDir 'dashboard-daily-cache.json'))
    }
    & $python @buildArgs
    if ($LASTEXITCODE -ne 0) { throw "站点构建失败，退出码 $LASTEXITCODE。" }
    foreach ($asset in @('dist/index.html', 'dist/manifest.json', 'dist/pagefind/pagefind-entry.json', 'dist/pagefind/pagefind-ui.js')) {
        if (-not (Test-Path -LiteralPath $asset -PathType Leaf)) { throw "缺少构建产物 $asset" }
    }
    Write-Host ('构建耗时 {0:F1} 秒' -f $build.Elapsed.TotalSeconds)

    Assert-ReleaseSource $commit
    $deployArgs = @('deploy', '--strict', '--keep-vars', '--tag', "git-$commit", '--message', "Git $commit")
    if ($DryRun) { $deployArgs += '--dry-run' }
    $deploy = [Diagnostics.Stopwatch]::StartNew()
    if ($FullAssets) {
        & $wrangler @deployArgs
    } else {
        node --require ./scripts/publish-assets.cjs ./node_modules/wrangler/bin/wrangler.js @deployArgs
    }
    if ($LASTEXITCODE -ne 0) { throw "Wrangler 失败，退出码 $LASTEXITCODE。" }
    Write-Host ('Wrangler 耗时 {0:F1} 秒' -f $deploy.Elapsed.TotalSeconds)
} finally {
    $env:DASHBOARD_ASSET_COPY_MANIFEST = $previousCopyManifest
    if ($lock) { $lock.Dispose() }
    Pop-Location
    Write-Host ('总耗时 {0:F1} 秒' -f $total.Elapsed.TotalSeconds)
}
