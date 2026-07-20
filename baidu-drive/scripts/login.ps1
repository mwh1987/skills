# bdpan OOB 登录脚本 (PowerShell 版)
# 用于 Windows 环境下的手动授权登录

param(
    [switch]$Yes,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

if ($Help) {
    Write-Host "用法: powershell login.ps1 [选项]"
    Write-Host ""
    Write-Host "选项:"
    Write-Host "  -Yes    跳过安全确认（自动化场景）"
    Write-Host "  -Help   显示帮助信息"
    exit 0
}

# 刷新 PATH
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")

function Log-Info($msg)  { Write-Host "[INFO] $msg" -ForegroundColor Green }
function Log-Warn($msg)  { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
function Log-Error($msg) { Write-Host "[ERROR] $msg" -ForegroundColor Red }

# 检查 bdpan 是否已安装
if (-not (Get-Command bdpan -ErrorAction SilentlyContinue)) {
    Log-Error "bdpan 未安装，请从 https://github.com/baidu-netdisk/bdpan-storage 手动安装 bdpan CLI"
    exit 1
}

# 检查当前登录状态
Log-Info "检查登录状态..."

$BDPAN_VERSION = (bdpan version 2>$null | Select-Object -First 1)
if (-not $BDPAN_VERSION) { $BDPAN_VERSION = "unknown" }

$whoamiOutput = bdpan whoami 2>&1 | Out-String
if ($whoamiOutput -match "已登录") {
    Log-Warn "已经登录，无需重复登录"
    Write-Host $whoamiOutput
    exit 0
}

Log-Info "未登录，开始 OOB 授权流程..."

# 安全免责声明
Write-Host ""
Write-Host "==============================================================" -ForegroundColor Red
Write-Host "              WARNING  baidu drive 安全须知 & 免责声明          " -ForegroundColor Red
Write-Host "==============================================================" -ForegroundColor Red
Write-Host " 1. 请备份网盘重要数据，谨慎操作。                              " -ForegroundColor Red
Write-Host " 2. [行为负责] AI Agent 行为具有不可预测性，请实时              " -ForegroundColor Red
Write-Host "    [人工审核] 指令执行过程，对执行后果负责。                   " -ForegroundColor Red
Write-Host " 3. [安全提醒] 严禁在他人、公用或不可信的环境中                 " -ForegroundColor Red
Write-Host "    扫码授权，以免网盘数据被窃取！                              " -ForegroundColor Red
Write-Host "    在公共环境使用完毕后，请务必执行 [bdpan logout] 清除授权。 " -ForegroundColor Red
Write-Host " 4. [严禁泄露] 请严格保护配置文件与 Token，                    " -ForegroundColor Red
Write-Host "    切勿在公开仓库或对话中暴露！                                " -ForegroundColor Red
Write-Host "==============================================================" -ForegroundColor Red
Write-Host ""

# 用户确认
if ($Yes) {
    Log-Info "自动模式，跳过安全确认"
} else {
    $reply = Read-Host "已阅读上述安全须知，确认继续登录? [y/N]"
    if ($reply -notmatch '^[Yy]$') {
        Log-Info "已取消登录"
        exit 0
    }
}

# 获取授权链接
Log-Info "正在获取授权链接..."

# 检查是否支持 --get-auth-url 参数
$loginHelp = bdpan login --help 2>&1 | Out-String
if ($loginHelp -match "get-auth-url") {
    $AUTH_URL = (bdpan login --get-auth-url 2>$null)
    if (-not $AUTH_URL) {
        Log-Error "获取授权链接失败"
        exit 1
    }
} else {
    Log-Warn "当前版本可能不支持 --get-auth-url"
    Log-Error "当前 bdpan 版本: $BDPAN_VERSION"
    Log-Error "请升级到支持 --get-auth-url 的 bdpan 版本（>= 3.0.0）"
    exit 1
}

# 显示授权链接
Write-Host ""
Write-Host "========================================" -ForegroundColor Blue
Write-Host "请在浏览器中打开以下链接完成授权:" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""
Write-Host $AUTH_URL -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Blue
Write-Host "提示:" -ForegroundColor Yellow
Write-Host "1. 复制上方链接到浏览器打开" -ForegroundColor Yellow
Write-Host "2. 链接有效期为 10 分钟" -ForegroundColor Yellow
Write-Host "3. 授权成功后，浏览器会显示一个 32 位授权码" -ForegroundColor Yellow
Write-Host "4. 请复制授权码并粘贴到下方" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# 提示用户输入授权码
$AUTH_CODE = Read-Host "请输入浏览器中显示的授权码 (32 位十六进制字符)"

if (-not $AUTH_CODE) {
    Log-Error "授权码不能为空"
    exit 1
}

# 校验授权码格式：32 位十六进制字符
if ($AUTH_CODE -notmatch '^[a-fA-F0-9]{32}$') {
    Log-Error "授权码格式不正确（应为 32 位十六进制字符）"
    Log-Error "当前输入: $AUTH_CODE"
    exit 1
}

# 使用授权码完成登录
Log-Info "正在使用授权码完成登录..."

# 通过 stdin 安全传递授权码
if ($loginHelp -match "set-code-stdin") {
    $AUTH_CODE | bdpan login --set-code-stdin
} else {
    $AUTH_CODE = $null
    Log-Error "当前 bdpan 版本不支持 --set-code-stdin（安全授权码传递）"
    Log-Error "当前 bdpan 版本: $BDPAN_VERSION"
    Log-Error "请升级到 >= 3.6.2"
    exit 1
}

# 立即清除内存中的授权码
$AUTH_CODE = $null

# 验证登录
$whoamiResult = bdpan whoami 2>&1 | Out-String
if ($LASTEXITCODE -eq 0) {
    Log-Info "登录成功！"
    Write-Host $whoamiResult
} else {
    Log-Error "登录失败，请检查授权码是否正确"
    exit 1
}
