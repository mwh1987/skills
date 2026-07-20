---
name: everything-cli
description: "Windows file search via Everything CLI (es.exe). Lightning-fast file, folder, and path search using Everything's NTFS index. Use when the user asks to search files, find files by name/extension/size/date, locate folders, count files, check disk usage, or any file-system query on Windows. Triggers: '搜文件', '找文件', '搜索文件', '查找', 'locate file', 'find file', 'search file', 'es搜索', 'Everything搜索', '文件搜索', '找一下', '帮我找', '哪个文件', '文件在哪'."
name_cn: Everything文件搜索
description_cn: 基于Everything CLI的毫秒级文件搜索工具，支持按名称、扩展名、大小、日期、属性等条件搜索文件和文件夹
create_source: super-agent-skill-creator
---

# Everything CLI 文件搜索

## 前提条件

- Everything 搜索客户端必须在后台运行，否则 ES 报错 `No Everything IPC window`
- `es.exe` 已安装并在 PATH 中（默认位置：`D:\Everything-1.4.1.935.x64\es.exe`）

## 决策树

```
用户要搜索文件/文件夹？
├─ 简单搜索（按名称/关键词）→ 基础搜索
├─ 按扩展名/类型筛选 → 扩展名搜索
├─ 按大小/日期/属性筛选 → 条件搜索（查看 references/search-syntax.md）
├─ 限定目录范围 → 加 -path 参数
├─ 需要导出结果 → 加 -export-* 参数
├─ 统计数量/总大小 → -get-result-count / -get-total-size
└─ 管理 Everything → -reindex / -exit / -save-db
```

## 基础搜索

```powershell
# es.exe 的完整路径（当前 PATH 未生效时使用）
$es = "D:\Everything-1.4.1.935.x64\es.exe"

# 搜文件名
& $es "关键词"

# 限定返回数量
& $es "关键词" -n 20

# 只搜文件夹
& $es "项目名" /ad

# 只搜文件
& $es "关键词" /a-d

# 限定目录
& $es "*.pdf" -path "D:\工作文档"

# 显示完整路径+大小+修改时间
& $es "报告" -full-path-and-name -size -date-modified
```

## 扩展名搜索

```powershell
& $es "ext:pdf"                    # 所有PDF
& $es "ext:docx;xlsx;pptx"        # Office文档
& $es "ext:mp4;mkv;avi"           # 视频文件
& $es "ext:py" -path "D:\项目"    # 指定目录下的Python文件
```

## 搜索修饰符

| 选项 | 作用 | 示例 |
|------|------|------|
| `-r` | 正则搜索 | `& $es -r "202[0-9]年报"` |
| `-i` | 区分大小写 | `& $es -i README` |
| `-w` | 全词匹配 | `& $es -w test` |
| `-p` | 匹配完整路径 | `& $es -p "D:\工作"` |

## 文件属性筛选

```powershell
& $es "关键词" /ad       # 只搜文件夹
& $es "关键词" /a-d      # 只搜文件
& $es "关键词" /aH       # 隐藏文件
& $es "关键词" /aS       # 系统文件
& $es "关键词" /aC       # 压缩文件
& $es "关键词" /aE       # 加密文件
```

属性字母：R只读 H隐藏 S系统 D目录 A存档 V设备 N正常 T临时 P稀疏 L重解析 C压缩 O脱机 I未索引 E加密

## 排序

```powershell
& $es "*.pdf" -sort-size-descending              # 按大小降序
& $es "*.log" -sort-date-modified-descending      # 按修改时间降序
& $es "*.docx" -sort-name-ascending               # 按名称升序
```

排序字段：`name` `path` `size` `extension` `date-created` `date-modified` `date-accessed` `date-run`

## 输出控制

```powershell
# 控制显示列
& $es "报告" -full-path-and-name -size -date-modified
& $es "*.exe" -name -size -attributes

# 输出格式
& $es "报告" -csv            # CSV格式
& $es "报告" -json           # JSON格式
& $es "报告" -tsv            # TSV格式

# 大小/日期格式
& $es "*.pdf" -size -size-format 2     # 大小显示KB
& $es "*.pdf" -dm -date-format 1      # 日期ISO-8601
```

## 导出结果

```powershell
& $es "*.pdf" -export-csv "文件列表.csv"
& $es "*.mp3" -export-m3u "播放列表.m3u"
& $es "报告" -export-json "结果.json"
& $es "*.log" -export-txt "日志列表.txt"
```

## 统计与管理

```powershell
& $es "*.pdf" -get-result-count           # 统计结果数量
& $es "*.log" -path "C:\" -get-total-size # 统计总大小
& $es -get-run-count "D:\报告.docx"       # 查看文件打开次数
& $es -reindex                            # 重建索引
& $es -get-everything-version             # 查看Everything版本
& $es -version                            # 查看ES版本
```

## 高级搜索语法

详见 [references/search-syntax.md](references/search-syntax.md)，包含：
- 逻辑运算符（AND / OR / NOT）
- Everything 内容过滤器（size: / dm: / ext: 等）
- 与 PowerShell 管道结合的高级用法

## PowerShell 注意事项

1. **管道符冲突**：PowerShell 中 `|` 是管道符，搜索 OR 时必须加引号：`& $es "报告|总结"`
2. **尖括号转义**：`< >` 在 PowerShell 中是重定向，搜索分组需加引号：`& $es "<报告|总结> 2024"`
3. **调用方式**：必须用 `& $es` 调用，不能直接写 `es.exe 参数`
4. **大文件筛选**：ES CLI 不支持 Everything 的 `size:` 过滤器，需用 PowerShell 二次过滤：
   ```powershell
   & $es "ext:mp4" -full-path-and-name -size -sort-size-descending -csv -no-header |
     ConvertFrom-Csv -Header Path,Size |
     Where-Object { [long]$_.Size -gt 100MB }
   ```
5. **当前会话**：新终端可直接用 `es`，当前终端需完整路径 `$es`
