---
name: xunlei-download
description: "迅雷MCP下载技能：通过迅雷云盘MCP服务实现AI智能下载。支持列出下载设备、验证下载链接、创建下载任务、查询任务状态、操作任务（开始/暂停/删除）。当用户说'帮我下载'、'用迅雷下载'、'下载这个链接'、'迅雷下载'、'xunlei download'、'磁力链接下载'、'BT下载'、'创建下载任务'、'查看下载任务'、'暂停下载'、'删除下载任务'时触发。"
name_cn: "迅雷下载"
description_cn: "通过迅雷MCP服务实现AI一句话智能下载，支持HTTP/磁力/BT等多种链接类型"
create_source: super-agent-skill-creator
---

# 迅雷下载

通过迅雷MCP（Model Context Protocol）SSE服务，让AI直接操控迅雷进行远程下载。

## 前置条件

- 迅雷客户端已开启「远程下载」（设置 → 下载设置 → 勾选开启远程下载），或已安装NAS版迅雷
- MCP链接已配置在 `scripts/config.json` 中（字段 `mcp_url`）

## 核心工具

迅雷MCP提供5个工具，通过 `scripts/xunlei_mcp.py` 调用：

| 工具名 | 功能 | 必需参数 |
|--------|------|----------|
| `xunlei_download_list_device` | 列出下载设备 | 无 |
| `xunlei_download_check_urls` | 验证下载链接 | `urls`（链接数组） |
| `xunlei_download_create` | 创建下载任务 | `target`（设备ID），`urls`（链接数组） |
| `xunlei_download_list` | 查询任务列表 | `target`（设备ID） |
| `xunlei_download_operate` | 操作任务 | `target`，`task_id`，`action`（running/pause/delete） |

## 脚本用法

```bash
python scripts/xunlei_mcp.py tools                              # 列出所有可用MCP工具
python scripts/xunlei_mcp.py devices                            # 列出下载设备
python scripts/xunlei_mcp.py verify <链接1> [链接2...]           # 验证下载链接
python scripts/xunlei_mcp.py download <链接> -d <设备ID>         # 创建下载任务（必须指定设备）
python scripts/xunlei_mcp.py download <链接> -d <设备ID> -n <名称>  # 创建任务并命名
python scripts/xunlei_mcp.py tasks -d <设备ID>                   # 查询下载任务列表
python scripts/xunlei_mcp.py operate <设备ID> <任务ID> <action>  # 操作任务(running/pause/delete)
python scripts/xunlei_mcp.py call <工具名> '<JSON参数>'          # 调用任意MCP工具
```

脚本路径：`C:\Users\idc\.config\TeleAgent\skills\xunlei-download\scripts\xunlei_mcp.py`

## 工作流程

### 1. 列出下载设备（必须先执行）

```bash
python scripts/xunlei_mcp.py devices
```

返回设备列表，记录 `target` 值（设备ID）和设备名称。所有后续操作都需要 `target`。

### 2. 验证下载链接（创建任务前必须执行）

```bash
python scripts/xunlei_mcp.py verify "https://example.com/file.zip" "magnet:?xt=urn:btih:xxxxx"
```

支持的链接类型：HTTP/HTTPS、FTP、磁力链接（magnet）、迅雷专用链（thunder）、ed2k链接。

### 3. 创建下载任务

```bash
python scripts/xunlei_mcp.py download "https://example.com/file.zip" -d "device_id#xxxxx"
```

创建成功后返回任务ID、文件名、大小、状态等信息。

### 4. 查询下载任务

```bash
python scripts/xunlei_mcp.py tasks -d "device_id#xxxxx"
```

返回当前所有下载任务及其状态（等待中、进行中、已完成、已暂停等）。

### 5. 操作下载任务

```bash
python scripts/xunlei_mcp.py operate "device_id#xxxxx" "task_id" running   # 开始/恢复下载
python scripts/xunlei_mcp.py operate "device_id#xxxxx" "task_id" pause     # 暂停下载
python scripts/xunlei_mcp.py operate "device_id#xxxxx" "task_id" delete    # 删除任务
```

## 常见问题处理

- **连接失败**：检查迅雷客户端是否在线、远程下载是否开启、网络是否正常
- **无可用设备**：确保迅雷客户端已登录且开启了远程下载，或NAS版迅雷正在运行
- **链接无效**：先用 verify 命令验证，确认链接格式正确且资源可用
- **MCP URL过期**：访问 https://pan.xunlei.com/mcp 重新获取或创建新应用，更新 `scripts/config.json`

## 安全提醒

- MCP链接是专属凭证，等同于下载遥控器，切勿泄露给他人
- 迅雷可能自动禁用已公开泄露的MCP链接
- 如需更换链接，编辑 `scripts/config.json` 中的 `mcp_url` 字段即可
