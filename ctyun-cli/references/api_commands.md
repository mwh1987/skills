---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '760224e7-325e-49f4-873f-a50d9182f1ce'
  PropagateID: '760224e7-325e-49f4-873f-a50d9182f1ce'
  ReservedCode1: 'ce7d8ae6-e309-4735-9e6a-1665a8a7547f'
  ReservedCode2: 'ce7d8ae6-e309-4735-9e6a-1665a8a7547f'
---

# 天翼云 CLI 常用 API 速查

## 目录

- [命令格式](#命令格式)
- [产品列表](#产品列表)
- [常用 API 命令](#常用-api-命令)
  - [公共查询](#公共查询)
  - [ECS 云主机](#ecs-云主机)
  - [VPC](#vpc)
  - [EIP 弹性公网 IP](#eip-弹性公网-ip)
  - [NAT 网关](#nat-网关)
  - [ELB 负载均衡](#elb-负载均衡)
  - [EVS 云硬盘](#evs-云硬盘)
- [区域 ID](#区域-id)
- [全局参数](#全局参数)

## 命令格式

```
ctyun-cli <product> <action> --regionID <regionID> [flags]
```

- 产品名和 Action 名区分大小写，与 `--help` 输出一致
- 必填参数在 `--help` 中标注 `(必填)`
- 复杂类型参数传入 JSON 字符串
- `--body` / `-b` 可直接传入完整 JSON 请求体，优先级最高

```bash
ctyun-cli --help                    # 列出所有产品
ctyun-cli vpc --help                # 列出产品下所有操作
ctyun-cli vpc ListVpc --help        # 列出操作的所有参数
```

## 产品列表

| 产品标识 | 说明 |
|---------|------|
| common  | 公共查询（区域、配额等）|
| ecs     | 云主机 |
| vpc     | 虚拟私有云 |
| eip     | 弹性公网 IP |
| nat     | NAT 网关 |
| elb     | 弹性负载均衡 |
| evs     | 云硬盘 |
| sds     | 云硬盘备份 |
| firewall| 防火墙 |
| monitor | 云监控 |
| ims     | 镜像服务 |

## 常用 API 命令

### 公共查询

```bash
ctyun-cli common GetCustomerRegionResources --regionID <regionID>  # 区域资源概览
ctyun-cli common GetCustomerRegionQuotas --regionID <regionID>     # 区域配额
ctyun-cli common DescribeRegions                                   # 区域列表
```

### ECS 云主机

```bash
ctyun-cli ecs GetEcsInstanceStatistics --regionID <regionID>                         # 实例统计
ctyun-cli ecs ListInstance --regionID <regionID> --pageNo 1 --pageSize 50            # 列出实例
ctyun-cli ecs DescribeInstance --regionID <regionID> --instanceID <instanceID>       # 实例详情
ctyun-cli ecs CreateInstance --regionID <regionID> --body '<json>'                   # 创建实例
ctyun-cli ecs StartInstance --regionID <regionID> --instanceID <instanceID>          # 启动
ctyun-cli ecs StopInstance --regionID <regionID> --instanceID <instanceID>           # 停止
```

### VPC

```bash
ctyun-cli vpc ListVpc --regionID <regionID>                                          # 列出 VPC
ctyun-cli vpc CreateVpc --regionID <id> --name "my-vpc" --CIDR "172.31.0.0/16" --clientToken "<uuid>"  # 创建 VPC
ctyun-cli vpc ListSubnet --regionID <regionID>                                       # 列出子网
ctyun-cli vpc QueryVpcSecurityGroupsNew --regionID <regionID> --pageNo 1 --pageSize 50  # 安全组
ctyun-cli vpc ListAclNew --regionID <regionID> --pageNo 1 --pageSize 200             # ACL
```

### EIP 弹性公网 IP

```bash
ctyun-cli eip ListEip --regionID <regionID>                          # 列出 EIP
ctyun-cli eip ApplyEip --regionID <regionID> --body '<json>'         # 申请 EIP
ctyun-cli eip BindEip --regionID <regionID> --body '<json>'          # 绑定
ctyun-cli eip UnbindEip --regionID <regionID> --body '<json>'        # 解绑
```

### NAT 网关

```bash
ctyun-cli nat DescribeInternetnatGateways --regionID <regionID>                          # 列出 NAT 网关
ctyun-cli nat ListInternetnatSnats --regionID <regionID> --natGatewayID <natGatewayID>   # SNAT 规则
ctyun-cli nat ListInternetnatDnats --regionID <regionID> --natGatewayID <natGatewayID>   # DNAT 规则
```

### ELB 负载均衡

```bash
ctyun-cli elb ListLoadbalancers --regionID <regionID>                               # 列出负载均衡
ctyun-cli elb ListListeners --regionID <regionID> --loadbalancerID <lbID>           # 监听器
ctyun-cli elb ListMembers --regionID <regionID> --listenerID <listenerID>           # 后端服务器
```

### EVS 云硬盘

```bash
ctyun-cli evs ListVolume --regionID <regionID> --pageNo 1 --pageSize 50   # 列出云硬盘
ctyun-cli evs CreateVolume --regionID <regionID> --body '<json>'          # 创建
ctyun-cli evs AttachVolume --regionID <regionID> --body '<json>'          # 挂载
ctyun-cli evs DetachVolume --regionID <regionID> --body '<json>'          # 卸载
```

## 区域 ID

| 区域名称 | regionID |
|---------|----------|
| 华南2   | 200000002530 |
| 华东1   | bb9fdb42056f11eda1610242ac110002 |

完整列表：`ctyun-cli common DescribeRegions`

## 全局参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `-c, --config` | 配置文件路径 | `~/.ctyun-cli.yaml` |
| `-o, --output` | 输出格式 (json/table) | json |
| `--cli-query` | JMESPath 过滤表达式 | — |
| `-a, --access-key` | AccessKey | — |
| `-s, --secret-key` | SecretKey | — |
| `--log` | 开启日志 | 关闭 |
| `--log-file` | 日志文件路径 | stderr |
| `--log-format` | 日志格式 (text/json) | text |

> AI生成