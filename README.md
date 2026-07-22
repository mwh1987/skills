# My Agent Skills
My collection of reusable capabilities for AI agents.
[![skills.sh](https://img.shields.io/badge/skills.sh-mwh1987%2Fskills-black?style=flat-square)](https://skills.sh/mwh1987/skills)
## Available Skills
### 🔍 System Search & Utilities (系统检索与通用工具)
Skills for searching local files, cloud resources, and general utilities.
#### 📦 盘搜网盘资源搜索 (`pansou`)
通过盘搜API搜索网盘资源并检测链接有效性，支持百度/阿里/夸克/天翼/UC/115/迅雷/PikPak等

To install this skill on your AI agent, run:
```bash
npx skills add mwh1987/skills/pansou
```
#### 📦 Everything文件搜索 (`everything-cli`)
基于Everything CLI的毫秒级文件搜索工具，支持按名称、扩展名、大小、日期、属性等条件搜索文件和文件夹

To install this skill on your AI agent, run:
```bash
npx skills add mwh1987/skills/everything-cli
```
### 📥 Downloaders (下载工具)
Skills for downloading files, media, and integrations with download clients.
#### 📦 Aria2 下载器 (`aria2-downloader`)
本地/远程 aria2 下载管理，支持 Windows 本地安装启停、JSON-RPC 远程控制。当用户说'下载'、'用aria2下载'、'磁力链接下载'、'查看下载进度'、'暂停下载'、'批量下载'、'启动aria2'、'安装aria2'时触发。

To install this skill on your AI agent, run:
```bash
npx skills add mwh1987/skills/aria2-downloader
```
#### 📦 影视视频下载 (`video-downloader`)
搜索并下载腾讯视频、爱奇艺、优酷、芒果TV等平台的影视资源

To install this skill on your AI agent, run:
```bash
npx skills add mwh1987/skills/video-downloader
```
#### 📦 迅雷下载 (`xunlei-download`)
通过迅雷MCP服务实现AI一句话智能下载，支持HTTP/磁力/BT等多种链接类型

To install this skill on your AI agent, run:
```bash
npx skills add mwh1987/skills/xunlei-download
```
### ☁️ Cloud Drives (云盘工具)
Skills for cloud drive storage, synchronization, and client management.
#### 📦 百度网盘 (`baidu-drive`)
百度网盘文件管理 — 上传、下载、转存、分享、搜索、移动、复制、重命名、创建文件夹

To install this skill on your AI agent, run:
```bash
npx skills add mwh1987/skills/baidu-drive
```
#### 📦 天翼云CLI (`ctyun-cli`)
通过天翼云CLI工具管理云资源，支持ECS/VPC/EIP/NAT/ELB/EVS等产品的查询与操作，以及云资源巡检和安全审计

To install this skill on your AI agent, run:
```bash
npx skills add mwh1987/skills/ctyun-cli
```
#### 📦 TRIM NAS / fnOS 命令行客户端 (`trim-cli`)
TRIM NAS（飞牛网盘 fnOS）命令行客户端工具，提供文件管理、共享目录、下载中心、应用中心、Docker 容器与镜像管理、存储池与磁盘 SMART 诊断及系统监控等能力

To install this skill on your AI agent, run:
```bash
npx skills add mwh1987/skills/trim-cli
```

