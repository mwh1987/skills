---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '84264d19-6b6d-4139-a6d4-270805a7943f'
  PropagateID: '84264d19-6b6d-4139-a6d4-270805a7943f'
  ReservedCode1: '0fcdcb59-ea15-48d4-9af9-a8e0d86fd3c4'
  ReservedCode2: '0fcdcb59-ea15-48d4-9af9-a8e0d86fd3c4'
---

# 天翼云 CLI 配置与安全

## 目录

- [安装](#安装)
- [认证配置](#认证配置)
- [输出格式](#输出格式)
- [日志](#日志)
- [安全注意事项](#安全注意事项)

## 安装

官方安装文档：https://www.ctyun.cn/document/11095072/11096343

支持 Windows / Linux / macOS 三平台。

**验证安装：**
```bash
ctyun-cli version
```

Windows 若命令未找到，添加 PATH：
```powershell
$env:Path = "$HOME\.ctyun-cli\bin;$env:Path"
```

## 认证配置

认证优先级：**命令行参数 > 配置文件 > 环境变量**

### 交互式配置

```bash
ctyun-cli configure
```

按提示输入 AccessKey / SecretKey。AccessKey 获取地址：https://iam.ctyun.cn/myAccessKey

配置保存到 `~/.ctyun-cli.yaml`（Windows 为 `%USERPROFILE%\.ctyun-cli.yaml`）。

### 环境变量

适合 CI/CD 和自动化场景：

PowerShell:
```powershell
$env:CTYUN_AK="your-access-key"
$env:CTYUN_SK="your-secret-key"
```

Bash:
```bash
export CTYUN_AK="your-access-key"
export CTYUN_SK="your-secret-key"
```

### 命令行参数

```bash
ctyun-cli vpc ListVpc --regionID <id> -a <access-key> -s <secret-key>
```

此方式会将密钥暴露在进程列表和 Shell 历史中，仅用于临时调试。

## 输出格式

```bash
# JSON（默认）
ctyun-cli vpc ListVpc --regionID <id>

# 表格
ctyun-cli vpc ListVpc --regionID <id> -o table

# JMESPath 过滤
ctyun-cli vpc ListVpc --regionID <id> --cli-query "data.vpcs[*].{name:name,id:vpcID}"
```

## 日志

默认关闭。开启后记录命令调用和 HTTP 请求：

```bash
ctyun-cli vpc ListVpc --regionID <id> --log true                        # 输出到 stderr
ctyun-cli vpc ListVpc --regionID <id> --log true --log-file ./cli.log   # 写入文件
```

日志不会记录 AccessKey、SecretKey 或签名 Header。

## 安全注意事项

- 优先使用配置文件或环境变量传凭证，不要硬编码在脚本中
- 不要在 Shell 命令中明文传入密钥，Shell 历史会保存
- 配置文件建议设置仅当前用户可读权限
- PowerShell 中 JSON 字符串的引号需正确转义

> AI生成