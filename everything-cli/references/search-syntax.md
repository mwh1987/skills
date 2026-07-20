---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '786e46c1-4998-4e91-9038-e3efd4fe0a3c'
  PropagateID: '786e46c1-4998-4e91-9038-e3efd4fe0a3c'
  ReservedCode1: '1ad3ecb0-3059-4326-a497-2b4dabd6929f'
  ReservedCode2: '1ad3ecb0-3059-4326-a497-2b4dabd6929f'
---

# Everything 高级搜索语法与模式

## 逻辑运算符

| 语法 | 含义 | 示例 |
|------|------|------|
| 空格 | AND | `报告 2024` = 同时包含"报告"和"2024" |
| `\|` | OR | `"报告\|总结"` = 包含"报告"或"总结" |
| `!` | NOT | `报告 !草稿` = 包含"报告"但不包含"草稿" |
| `<>` | 分组 | `"<报告\|总结> 2024"` |
| `" "` | 转义 | `"C:\Program Files"` |

**PowerShell 注意**：`|` 和 `<>` 必须用双引号包裹。

## Everything 内容过滤器

以下过滤器在 Everything GUI 中有效，但 ES CLI 中**部分不支持**（如 `size:`），需用 PowerShell 二次过滤。

### 支持的过滤器

| 过滤器 | 作用 | 示例 |
|--------|------|------|
| `ext:` | 扩展名 | `ext:pdf;docx` |
| `path:` | 限定路径 | `path:D:\工作` |
| `ad` | 仅文件夹 | `关键词 ad` |
| `a-d` | 仅文件 | `关键词 a-d` |
| `a[RHSDAVNTPLCOIE]` | 文件属性 | `aH` 隐藏文件 |

### 需要 PowerShell 辅助的过滤器

| 过滤器 | Everything语法 | PowerShell替代方案 |
|--------|----------------|-------------------|
| 按大小 | `size:>100mb` | `es ext:mp4 -csv -no-header \| ConvertFrom-Csv \| Where-Object { ... }` |
| 按修改日期 | `dm:today` | `es 关键词 -dm -csv \| Where-Object { ... }` |
| 按创建日期 | `dc:thisweek` | `es 关键词 -dc -csv \| Where-Object { ... }` |

## PowerShell 管道结合模式

### 模式1：大小筛选

```powershell
$es = "D:\Everything-1.4.1.935.x64\es.exe"

# 大于100MB的MP4
& $es "ext:mp4" -full-path-and-name -size -sort-size-descending -csv -no-header |
  ConvertFrom-Csv -Header Path,Size |
  Where-Object { [long]$_.Size -gt 100MB } |
  ForEach-Object { "$($_.Path)  $([math]::Round($_.Size/1MB,1)) MB" }

# 小于1KB的日志文件
& $es "ext:log" -full-path-and-name -size -csv -no-header |
  ConvertFrom-Csv -Header Path,Size |
  Where-Object { [long]$_.Size -lt 1KB }
```

### 模式2：日期筛选

```powershell
# 最近7天修改的文件
$cutoff = (Get-Date).AddDays(-7).ToString("yyyy/MM/dd")
& $es "ext:docx" -full-path-and-name -date-modified -csv -no-header |
  ConvertFrom-Csv -Header Path,DateModified |
  Where-Object { [datetime]$_.DateModified -gt $cutoff }
```

### 模式3：结果导出再处理

```powershell
# 搜索并导出JSON，然后用PowerShell解析
& $es "报告" -export-json "$env:TEMP\search_result.json"
$data = Get-Content "$env:TEMP\search_result.json" | ConvertFrom-Json
$data | Where-Object { $_.Size -gt 10MB } | Select-Object Name, Size
```

### 模式4：批量操作搜索结果

```powershell
# 删除所有 .tmp 文件
& $es "ext:tmp" -full-path-and-name -n 100 |
  ForEach-Object { Remove-Item $_ -Force; "Deleted: $_" }

# 复制所有 2024年报告 到指定目录
& $es "2024年报 ext:pdf" -full-path-and-name |
  ForEach-Object { Copy-Item $_ "D:\归档\" -Force }
```

## 常用搜索场景速查

| 场景 | 命令 |
|------|------|
| 搜文件名 | `es 关键词` |
| 搜指定扩展名 | `es ext:pdf` |
| 限定目录 | `es 关键词 -path D:\工作` |
| 只搜文件夹 | `es 关键词 /ad` |
| 按大小排序 | `es 关键词 -sort-size-descending` |
| 限制结果数 | `es 关键词 -n 20` |
| 统计数量 | `es 关键词 -get-result-count` |
| 统计总大小 | `es 关键词 -get-total-size` |
| 导出CSV | `es 关键词 -export-csv out.csv` |
| 导出JSON | `es 关键词 -export-json out.json` |
| 正则搜索 | `es -r "pattern"` |
| 大小写敏感 | `es -i Keyword` |
| 全词匹配 | `es -w word` |

> AI生成