---
name: aria2-downloader
description: "Remote control aria2 via JSON-RPC API. Add downloads (magnet/HTTP/FTP), check progress, pause/resume/remove tasks, batch download from text. Support local aria2 installation and service management on Windows. Trigger: download magnet link, check download progress, aria2 download, pause/resume download, batch download."
name_cn: Aria2 下载器
description_cn: "本地/远程 aria2 下载管理，支持 Windows 本地安装启停、JSON-RPC 远程控制。当用户说'下载'、'用aria2下载'、'磁力链接下载'、'查看下载进度'、'暂停下载'、'批量下载'、'启动aria2'、'安装aria2'时触发。"
---

# aria2 Downloader

本地/远程双模式 aria2 下载管理。支持 Windows 本地安装、RPC 服务启停，以及远程 aria2 实例连接。

## 决策树

```
用户提到下载/aria2
├─ aria2c 已安装？ → 否 → 执行「安装 aria2」
├─ aria2 服务已运行？ → 否 → 执行「启动服务」
├─ .aria2-config.json 存在？ → 否 → 执行「配置连接」
└─ 执行下载操作（add/list/pause/unpause/remove/batch）
```

## 安装 aria2（Windows）

仅当 `aria2c` 未安装时执行。

### 1. 下载

从 GitHub 下载 Windows 64-bit 版本（需代理访问）：

```powershell
$aria2Dir = "$env:LOCALAPPDATA\aria2"
New-Item -ItemType Directory -Path $aria2Dir -Force | Out-Null
curl.exe -fsSL -x http://127.0.0.1:7890 "https://github.com/aria2/aria2/releases/download/release-1.37.0/aria2-1.37.0-win-64bit-build1.zip" -o "$aria2Dir\aria2.zip"
```

### 2. 解压安装

```powershell
Expand-Archive -Path "$aria2Dir\aria2.zip" -DestinationPath "$aria2Dir" -Force
Copy-Item "$aria2Dir\aria2-1.37.0-win-64bit-build1\aria2c.exe" "$aria2Dir\" -Force
```

### 3. 加入 PATH

```powershell
$currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($currentPath -notlike "*$aria2Dir*") {
    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$aria2Dir", "User")
}
```

新开终端后 `aria2c --version` 验证。

## 启动/停止 RPC 服务

### 启动

1. 创建配置文件 `%LOCALAPPDATA%\aria2\aria2.conf`：

```ini
dir=<下载目录>
log=%LOCALAPPDATA%\aria2\aria2.log
log-level=warn
enable-rpc=true
rpc-listen-port=6800
rpc-listen-all=true
rpc-secret=<自定义token>
max-concurrent-downloads=5
max-connection-per-server=16
min-split-size=1M
split=16
continue=true
enable-dht=true
bt-enable-lpd=true
enable-peer-exchange=true
seed-ratio=1.0
seed-time=60
```

2. 后台启动：

```powershell
Start-Process -FilePath "$env:LOCALAPPDATA\aria2\aria2c.exe" -ArgumentList "--conf-path=`"$env:LOCALAPPDATA\aria2\aria2.conf`"" -WindowStyle Hidden
```

3. 验证（PowerShell）：

```powershell
$body = @{jsonrpc="2.0";id="1";method="aria2.getVersion";params=@("token:<你的token>")} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:6800/jsonrpc" -Method Post -Body $body -ContentType "application/json"
```

### 停止

```powershell
Stop-Process -Name aria2c -Force
```

### 开机自启（可选）

将以下内容保存为 `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\aria2.vbs`：

```vb
Set ws = CreateObject("Wscript.Shell")
ws.Run """%LOCALAPPDATA%\aria2\aria2c.exe"" --conf-path=""%LOCALAPPDATA%\aria2\aria2.conf""", 0, False
```

## 配置技能连接

在工作空间根目录（即当前工作目录）创建 `.aria2-config.json`：

> **关键**：必须使用 **UTF-8 无 BOM** 编码写入，否则 JSON 解析会报错。PowerShell 的 `Set-Content` 默认带 BOM，须用以下方式：

```powershell
$config = '{"url":"http://localhost:6800/jsonrpc","token":"<你的token>"}'
[System.IO.File]::WriteAllText("$PWD\.aria2-config.json", $config, [System.Text.UTF8Encoding]::new($false))
```

配置文件格式：

```json
{
  "url": "http://localhost:6800/jsonrpc",
  "token": "your-secret-token"
}
```

**配置文件读取优先级**：
1. `ARIA2_CONFIG` 环境变量指向的路径
2. 当前工作目录下的 `.aria2-config.json`
3. 用户主目录下的 `.aria2-config.json`

对于远程 aria2 服务，将 `url` 改为远程地址即可（如 `https://your-server.com/jsonrpc`），其余操作完全相同。

## 下载操作

所有操作通过 `scripts/aria2.js` 执行。

### 添加下载

```bash
node scripts/aria2.js add "magnet:?xt=urn:btih:..."
node scripts/aria2.js add "https://example.com/file.zip"
```

### 查看任务

```bash
node scripts/aria2.js list
```

### 暂停/恢复/删除

```bash
node scripts/aria2.js pause <gid>
node scripts/aria2.js unpause <gid>
node scripts/aria2.js remove <gid>
```

### 批量下载

```powershell
# Pipeline 方式
"magnet:?xt=...`nhttps://example.com/file.zip" | node scripts/aria2.js batch

# 或从文件读取
Get-Content links.txt | node scripts/aria2.js batch
```

## 故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| 配置文件格式错误 `Unexpected token` | PowerShell `Set-Content` 写入带 BOM | 用 `[System.IO.File]::WriteAllText` + UTF8Encoding($false) 重写 |
| `aria2c` 命令不存在 | PATH 未生效 | 新开终端，或重启 TeleAgent |
| RPC 连接被拒 | aria2 服务未启动 | 执行启动步骤，检查端口 6800 |
| 下载速度慢 | 连接数不足 | 调大 `max-connection-per-server` 和 `split` |
| GitHub 下载失败 | 网络不通 | 使用 `-x http://127.0.0.1:7890` 代理 |

## 注意事项

- 不轮询：只在用户请求时查看进度
- 不硬编码：URL 和 Token 由用户配置
- 链接类型：支持 magnet、http、https、ftp
- 依赖：Node.js（无需额外 npm 包，使用原生 http/https 模块）
- aria2 服务重启后电脑后需重新启动（除非配置了开机自启）
