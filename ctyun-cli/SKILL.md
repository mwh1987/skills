---
name: ctyun-cli
description: "Manage CTYun cloud resources via ctyun-cli. Use when managing ECS/VPC/EIP/NAT/ELB/EVS, performing cloud resource inspection or security audits, querying resource status/quotas, or automating CTYun operations. Triggers: 天翼云/ctyun/云主机/安全组/巡检/云资源"
name_cn: 天翼云CLI
description_cn: "通过天翼云CLI工具管理云资源，支持ECS/VPC/EIP/NAT/ELB/EVS等产品的查询与操作，以及云资源巡检和安全审计"
create_source: super-agent-skill-creator
---

## 前置条件

使用本技能前须确认：

1. **ctyun-cli 已安装** — 安装方式见 https://www.ctyun.cn/document/11095072/11096343
2. **认证已配置** — 通过 `ctyun-cli configure` 或环境变量 `CTYUN_AK`/`CTYUN_SK` 完成认证

验证：`ctyun-cli version`。若命令未找到，Windows 需添加 PATH：`$env:Path = "$HOME\.ctyun-cli\bin;$env:Path"`

详细配置说明见 [references/configuration.md](references/configuration.md)。

## 工作流决策树

```
用户意图
├─ 资源巡检/盘点/日报
│   └─ → 云资源巡检流程
├─ 安全检查/风险排查/高危端口/ACL/安全组
│   └─ → 安全智能巡检流程
├─ 查询/列出/查看资源
│   └─ → 单资源查询（查 API 速查后执行）
├─ 创建/修改/删除资源
│   └─ → 资源变更（先 --help 确认必填参数）
└─ 登录/认证/配额/区域
    └─ → 参考 configuration.md
```

### 云资源巡检

按区域分步执行，汇总后生成报告：

1. `ctyun-cli common GetCustomerRegionResources --regionID <id>` — 资源概览
2. `ctyun-cli common GetCustomerRegionQuotas --regionID <id>` — 配额
3. `ctyun-cli ecs GetEcsInstanceStatistics --regionID <id>` — ECS 统计
4. 分页查询各资源（ECS/EIP/EVS/ELB/NAT/VPC），汇总数量和状态
5. 标记异常（关机/未绑定/未挂载/长期闲置）
6. 输出 Markdown 或 table 格式日报

### 安全智能巡检

逐项排查，输出风险清单和修复建议：

1. 安全组 → 检测 0.0.0.0/0 开放的 SSH(22)/RDP(3389)/数据库(3306/5432) 端口及过宽规则
2. EIP → 检测关键 ECS 直接暴露公网
3. NAT SNAT → 检测覆盖过大网段；DNAT → 检测高危端口映射公网
4. ELB 监听器 → 检测公网敏感端口开放
5. 子网 ACL → 检测过宽规则
6. 生成风险清单，给出最小权限修复建议；用户确认后可执行修复命令

### 资源变更

创建/修改/删除资源前，务必先通过 `--help` 确认必填参数：

```bash
ctyun-cli <product> <action> --help       # 确认必填参数
ctyun-cli <product> <action> --body '<json>'  # 复杂参数用 --body
```

## API 速查

常用产品命令和参数见 [references/api_commands.md](references/api_commands.md)。

## 安全与配置详情

认证方式、环境变量、输出格式、日志等详见 [references/configuration.md](references/configuration.md)。
