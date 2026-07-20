# bdpan CLI 卸载脚本 (PowerShell 版)
# 清除 bdpan 二进制文件、配置文件和授权信息

param(
    [switch]$Yes,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

if ($Help) {
    Write-Host "用法: powershell uninstall.ps1 [选项]"
    Write-Host ""
    Write-Host "选项:"
    Write-Host "  -Yes    跳过确认提示（自动化场景）"
    Write-Host "  -Help   显示帮助信息"
    exit 0
}

function Log-Info($msg)  { Write-Host "[INFO] $msg" -ForegroundColor Green }
function Log-Warn($msg)  { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Log-Error($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red }

# 刷新 PATH
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")

# 确定实际路径
$INSTALL_DIR = if ($env:BDPAN_INSTALL_DIR) { $env:BDPAN_INSTALL_DIR } else { "$env:LOCALAPPDATA\bdpan" }
$CONFIG_DIR = if ($env:BDPAN_CONFIG_DIR) { $env:BDPAN_CONFIG_DIR } else { "$env:USERPROFILE\.config\bdpan" }
$BINARY_PATH = Join-Path $INSTALL_DIR "bdpan.exe"

# 检测要清理的内容
Write-Host ""
Write-Host "========================================" -ForegroundColor Yellow
Write-Host "  bdpan CLI 卸载" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""

$foundItems = 0

# 检查二进制文件
$bdpanCmd = Get-Command bdpan -ErrorAction SilentlyContinue
if ($bdpanCmd) {
    $BINARY_PATH = $bdpanCmd.Source
    $binaryVersion = (bdpan version 2>$null | Select-Object -First 1)
    Write-Host "  二进制文件: $BINARY_PATH ($binaryVersion)" -ForegroundColor Green
    $foundItems++
} elseif (Test-Path $BINARY_PATH) {
    $binaryVersion = (& $BINARY_PATH version 2>$null | Select-Object -First 1)
    Write-Host "  二进制文件: $BINARY_PATH ($binaryVersion)" -ForegroundColor Green
    $foundItems++
} else {
    Write-Host "  二进制文件: 未找到" -ForegroundColor Yellow
}

# 检查配置目录
if (Test-Path $CONFIG_DIR) {
    $configFiles = (Get-ChildItem -Path $CONFIG_DIR -File -Recurse -ErrorAction SilentlyContinue).Count
    Write-Host "  配置目录:   $CONFIG_DIR\ ($configFiles 个文件)" -ForegroundColor Green
    $foundItems++

    # 检查登录状态
    $configFile = Join-Path $CONFIG_DIR "config.json"
    if (Test-Path $configFile) {
        if ($bdpanCmd) {
            $whoamiOutput = bdpan whoami 2>&1 | Out-String
            if ($whoamiOutput -match "已登录") {
                Write-Host "  登录状态:   已登录（将清除授权信息）" -ForegroundColor Red
            }
        }
    }
} else {
    Write-Host "  配置目录:   未找到" -ForegroundColor Yellow
}

Write-Host ""

if ($foundItems -eq 0) {
    Log-Info "未检测到 bdpan 安装，无需卸载"
    exit 0
}

# 用户确认
if (-not $Yes) {
    Write-Host "以上内容将被永久删除，此操作不可逆！" -ForegroundColor Red
    Write-Host ""
    $reply = Read-Host "确认卸载 bdpan CLI? [y/N]"
    if ($reply -notmatch '^[Yy]$') {
        Log-Info "已取消卸载"
        exit 0
    }
}

Write-Host ""

# 1. 注销登录
if ($bdpanCmd) {
    $whoamiOutput = bdpan whoami 2>&1 | Out-String
    if ($whoamiOutput -match "已登录") {
        Log-Info "正在注销登录..."
        try { bdpan logout 2>$null | Out-Null } catch {}
        Log-Info "已注销登录"
    }
}

# 2. 删除配置目录
if (Test-Path $CONFIG_DIR) {
    Log-Info "正在删除配置目录: $CONFIG_DIR\"
    Remove-Item -Path $CONFIG_DIR -Recurse -Force
    Log-Info "配置目录已删除"
}

# 3. 删除二进制文件
if (Test-Path $BINARY_PATH) {
    Log-Info "正在删除二进制文件: $BINARY_PATH"
    Remove-Item -Path $BINARY_PATH -Force
    Log-Info "二进制文件已删除"
}

# 4. 清理版本目录
$versionDir = "$env:USERPROFILE\.local\bdpan"
if (Test-Path $versionDir) {
    Log-Info "正在删除版本目录: $versionDir"
    Remove-Item -Path $versionDir -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  bdpan CLI 已完全卸载" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
