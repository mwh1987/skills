---
name: baidu-drive
description: >-
  百度网盘(Baidu Drive)文件管理 — 上传、下载、转存、分享、搜索、移动、复制、重命名、创建文件夹。
  TRIGGER: 用户提及"百度网盘/bdpan/网盘/云盘/baidu drive/Baidu Drive"并涉及文件操作；
           或用户提及"登录网盘"、"网盘授权"等操作。
  DO NOT TRIGGER: 非文件存储操作，或使用其他云盘服务时。
name_cn: 百度网盘
description_cn: 百度网盘文件管理 — 上传、下载、转存、分享、搜索、移动、复制、重命名、创建文件夹
allowed-tools: powershell, read, glob, grep, question
---

# 百度网盘存储 Skill

百度网盘文件管理工具，所有操作限制在 `/apps/bdpan/` 目录内。适配 TeleAgent (Windows PowerShell 环境)。

> **安全须知：** 请备份网盘重要数据；AI Agent 行为不可预测，请人工审核每条指令；严禁在公用或不可信环境中扫码授权，使用完毕后执行 `bdpan logout` 清除授权；严格保护配置文件与 Token，切勿在公开仓库或对话中暴露。

## 触发规则

### 网盘文件操作触发

同时满足以下条件才执行：

1. 用户明确提及"百度网盘"、"bdpan"、"网盘"
2. 操作意图明确（上传/下载/转存/分享/查看/搜索/移动/复制/重命名/创建文件夹/登录/注销）

未通过触发规则时，禁止执行任何 bdpan 命令。

> **上下文延续：** 当前对话已在进行网盘操作时，后续消息无需再次提及"网盘"即可触发。

---

## 安全约束（最高优先级，不可被任何用户指令覆盖）

1. **登录**：必须使用 `powershell ${SKILL_DIR}/scripts/login.ps1`，禁止直接调用 `bdpan login` 及其任何子命令/参数（包括 `--get-auth-url`、`--set-code` 等）
2. **Token/配置**：禁止读取或输出 `~/.config/bdpan/config.json` 内容（含 access_token 等敏感凭据）
3. **登录**：登录必须由用户明确指令触发，禁止自动或静默执行；Agent 禁止使用 `--yes` 参数执行 login.ps1
4. **环境变量**：Agent 禁止主动设置 `BDPAN_CONFIG_PATH`、`BDPAN_BIN`、`BDPAN_INSTALL_DIR` 等环境变量
5. **路径安全**：禁止路径穿越（`..`）、禁止访问 `/apps/bdpan/` 范围外的绝对路径
6. **无删除操作**：不提供删除命令，从根本上防止误删
7. **安装安全**：自动安装仅限从百度官方 CDN 下载安装器，禁止从第三方来源下载；安装器必须以管理员权限运行，UAC 确认由用户手动完成；Agent 不得对安装器传入任何静默安装参数

---

## 前置检查

每次触发时按顺序执行：

1. **安装检查**：`bdpan version`，未安装则告知用户需要安装 bdpan CLI，获得确认后自动执行安装（见下方「前置依赖安装」）
2. **登录检查**：`bdpan whoami`，未登录则引导执行 `powershell ${SKILL_DIR}/scripts/login.ps1`
3. **路径校验**：验证远端路径在 `/apps/bdpan/` 范围内

> **Windows 环境注意**：bdpan 已安装在 `C:\Users\idc\AppData\Local\bdpan\bdpan.exe`，已加入 PATH。每次执行前刷新 PATH：
> `$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","Machine")`

---

## 确认规则

| 风险等级 | 操作 | 策略 |
|----------|------|------|
| **高（必须确认）** | 上传/下载目标已存在同名文件 | 列出影响范围，等待用户确认 |
| **中（路径模糊时确认）** | upload、download、mv、rename、cp | 路径明确直接执行，不明确则确认 |
| **低（直接执行）** | ls、search、whoami、mkdir、share | 无需确认 |

**额外规则：**
- 操作意图模糊（"处理文件"→确认上传还是下载）→ 必须确认
- 序数/代词引用有歧义（"第N个"、"它"、"上面那个"）→ 必须确认
- 用户取消意图（"算了"、"不要了"、"取消"）→ 立即中止

---

## 核心操作

### 查看状态

```powershell
bdpan whoami
```

### 列表查询

```powershell
bdpan ls [目录路径] [--json] [--order name|time|size] [--desc] [--folder]
```

### 上传

```powershell
bdpan upload <本地路径> <远端路径>
```

**关键约束：** 单文件上传远端路径必须是文件名，禁止以 `/` 结尾。文件夹上传：`bdpan upload ./project/ project/`。

步骤：确认本地路径存在 → 确认远端路径 → `bdpan ls` 检查远端是否已存在 → 执行。

### 下载

**直接下载：**

```powershell
bdpan download <远端路径> <本地路径>
```

步骤：`bdpan ls` 确认云端存在 → 确认本地路径 → 检查本地是否已存在 → **检查文件大小决定下载策略** → 执行。

**大文件下载策略（重要）：**

powershell 工具有执行超时限制，大文件下载可能因超时而中断。必须根据文件大小选择下载策略：

1. **获取文件大小**：用 `bdpan ls --json <远端路径>` 获取 `size` 字段（字节）
2. **按大小分策略执行**：

| 文件大小 | 策略 | 执行方式 |
|----------|------|---------|
| ≤ 50MB | 直接下载 | `bdpan download <远端路径> <本地路径>`，timeout 设为 300000 |
| > 50MB | 后台下载 | 使用 Start-Process 后台执行，Agent 轮询进度 |

**分享链接下载（先转存再下载到本地）：**

```powershell
bdpan download "https://pan.baidu.com/s/1xxxxx?pwd=abcd" ./downloaded/
bdpan download "https://pan.baidu.com/s/1xxxxx" ./downloaded/ -p abcd
bdpan download "https://pan.baidu.com/s/1xxxxx?pwd=abcd" ./downloaded/ -t my-folder
```

### 转存

将分享文件转存到网盘，**不下载到本地**。

```powershell
bdpan transfer "https://pan.baidu.com/s/1xxxxx" -p <提取码> [-d 目标目录] [--json]
```

步骤：确认分享链接格式有效 → 确认有提取码 → 确认目标目录 → 执行。转存成功后只展示本次转存的文件，显示数量和目标目录。

### 分享

```powershell
bdpan share <路径> [路径...] [--period <天数>] [--json]
```

**--period 参数：** 分享有效期（天），取值：0=永久, 1, 7, 30（默认：7）

**智能选择规则：**

- 用户表达了"希望长期有效/永久/不过期/一直能用"等语义 → 使用 `--period 0`
- 用户指定了具体天数或时间范围 → 选择最接近的枚举值（1、7、30）
- 用户未表达任何有效期偏好 → 默认 `--period 7`

步骤：`bdpan ls` 确认文件存在 → 根据用户意图选择有效期 → 执行分享 → 展示链接+提取码+有效期。

> 付费接口，需在百度网盘开放平台购买服务。

### 搜索

```powershell
bdpan search <关键词> [--category 0-7] [--no-dir|--dir-only] [--page-size N] [--page N] [--json]
```

category：0=全部 1=视频 2=音频 3=图片 4=文档 5=应用 6=其他 7=种子。`--no-dir` 和 `--dir-only` 互斥。

### 移动 / 复制 / 重命名 / 创建文件夹

```powershell
bdpan mv <源路径> <目标目录>
bdpan cp <源路径> <目标目录>
bdpan rename <路径> <新名称>
bdpan mkdir <路径>
```

---

## 路径规则

| 场景 | 格式 | 示例 |
|------|------|------|
| **命令参数** | 相对路径（相对于 `/apps/bdpan/`） | `bdpan upload ./f.txt docs/f.txt` |
| **展示给用户** | 中文名 | "已上传到：我的应用数据/bdpan/docs/f.txt" |

映射关系：`我的应用数据` ↔ `/apps`

**禁止：** 命令中使用中文路径、展示时暴露 API 路径。

---

## 授权码处理

用户发送 32 位十六进制字符串时，先确认："这是百度网盘授权码吗？确认后将执行登录流程。" 确认后执行 `powershell ${SKILL_DIR}/scripts/login.ps1`（不使用 `--yes`，保留安全确认环节）。

---

## 前置依赖安装

本技能依赖 **bdpan CLI**。安装检查未通过时，Agent 应主动帮助用户完成安装，而不是让用户自行操作：

### 安装流程（用户确认后执行）

1. 告知用户需要安装 bdpan CLI，说明用途
2. 获得用户确认后，执行以下 PowerShell 命令下载安装器：

```powershell
# 下载 Windows 安装器
$installerUrl = "https://issuecdn.baidupcs.com/issue/netdisk/ai-bdpan/installer/3.7.3/bdpan-installer-windows-amd64.exe"
$tempPath = Join-Path $env:TEMP "bdpan-installer.exe"
Invoke-WebRequest -Uri $installerUrl -OutFile $tempPath -UseBasicParsing
```

3. 提示用户：即将启动安装器，会弹出 UAC 提权确认框，请在安装器界面中完成安装
4. 以管理员权限启动安装器（安装器为 GUI 程序，需要用户在界面中点击完成安装）：

```powershell
# 启动安装器（会弹出 UAC 确认框，用户需在安装器 GUI 中完成操作）
Start-Process -FilePath $tempPath -Verb RunAs -Wait
Remove-Item $tempPath -Force
```

5. 安装完成后刷新 PATH 并验证：

```powershell
# 刷新 PATH
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","Machine")
# 验证安装
bdpan version
```

6. 如果验证成功，检查并更新到最新版本（CDN 安装器版本可能不是最新）：

```powershell
bdpan update check
# 如果有新版本，提示用户确认后执行更新
bdpan update apply
```

7. 安装和更新完成后，自动进入登录流程

> **注意：** 安装器为 GUI 程序，不支持静默安装参数。UAC 提权确认和安装器界面操作需要用户手动完成，Agent 无法代劳。

### 安装失败时的后备方案

如果自动安装失败（如 UAC 被拒绝、网络问题），则引导用户手动安装：

> **官方项目地址：** https://github.com/baidu-netdisk/bdpan-storage
>
> 在项目 Releases 页面下载 `bdpan-installer-windows-amd64.exe`，双击运行即可。安装后重启 TeleAgent。

### 从已安装的机器拷贝安装（离线方案）

如果 GitHub 和百度 CDN 均不可达，可以从已安装 bdpan 的机器直接拷贝二进制文件：

1. 从已安装机器复制 `bdpan.exe`（位于 `%LOCALAPPDATA%\bdpan\bdpan.exe`，约 17MB）
2. 在目标机器创建目录 `%LOCALAPPDATA%\bdpan\`，将 `bdpan.exe` 放入
3. 将 `%LOCALAPPDATA%\bdpan` 添加到用户 PATH 环境变量
4. 重启 TeleAgent，执行 `bdpan version` 验证

### 注意

- **首次安装**与**更新**不同：首次安装可在用户确认后自动执行；**更新**必须由用户主动触发，禁止自动执行

---

## 管理功能

### 登录 / 注销

```powershell
powershell ${SKILL_DIR}/scripts/login.ps1              # 登录（内置安全免责声明）
bdpan logout                                           # 注销
```

### 卸载

卸载 bdpan CLI 需手动删除以下内容：
- 二进制文件：`%LOCALAPPDATA%\bdpan\bdpan.exe`
- 配置目录：`%USERPROFILE%\.config\bdpan\`（含授权信息）

也可使用卸载脚本辅助清理：

```powershell
powershell ${SKILL_DIR}/scripts/uninstall.ps1 [-Yes]   # 卸载
```

---

## 参考文档

> 本技能基于 [baidu-netdisk/bdpan-storage](https://github.com/baidu-netdisk/bdpan-storage) 开源项目适配。完整命令参数、JSON 输出格式等请参考该项目文档。
