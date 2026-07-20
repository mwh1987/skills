---
name: pansou
description: >-
  Search cloud drive resources and check link validity via PanSou (so.252035.xyz) API.
  Use when user mentions "盘搜", "网盘搜索", "搜资源", "找电影", "搜网盘",
  "pansou", "cloud drive search", "resource search", or needs to find shareable
  links on Baidu/Alibaba/Quark/Tianyi/UC/115/Xunlei/PikPak etc. Supports keyword
  search with cloud type filtering, include/exclude keyword filtering, and link
  validity checking.
name_cn: 盘搜网盘资源搜索
description_cn: 通过盘搜API搜索网盘资源并检测链接有效性，支持百度/阿里/夸克/天翼/UC/115/迅雷/PikPak等
create_source: super-agent-skill-creator
---

# 盘搜网盘资源搜索

## Quick Start

Run the bundled script to search or check links:

```bash
python scripts/pansou.py search "关键词"
python scripts/pansou.py search "关键词" -c quark,aliyun
python scripts/pansou.py check '[{"disk_type":"quark","url":"https://pan.quark.cn/s/xxx"}]'
```

## Workflow

1. **Search**: User provides keyword + optional filters → run `scripts/pansou.py search` → format results for user
2. **Check links**: User provides share links → run `scripts/pansou.py check` → report validity
3. **Advanced**: Use API directly via PowerShell `Invoke-RestMethod` when script doesn't cover the need

## Search

### Basic

```
python scripts/pansou.py search "三体"
```

### Filter by cloud type

```
python scripts/pansou.py search "三体" -c quark,aliyun
```

Supported types: `baidu`, `aliyun`, `quark`, `uc`, `tianyi`, `115`, `xunlei`, `mobile`, `pikpak`, `123`, `guangya`, `magnet`, `ed2k`

### Keyword filtering

```
python scripts/pansou.py search "电影名" --include "4K,高码" --exclude "预告,抢先"
```

include = OR (match any), exclude = OR (exclude any).

### Other flags

- `--res all|results|merge` — result format (default: merge)
- `--src all|tg|plugin` — data source (default: all)
- `--refresh` — force refresh, skip cache
- `--conc N` — concurrency
- `--plugins p1,p2` — specific plugins
- `--channels ch1,ch2` — specific TG channels
- `--ext '{"title_en":"..."}'` — extension params as JSON
- `--raw` — output raw JSON

## Check Links

```
python scripts/pansou.py check '[{"disk_type":"quark","url":"https://pan.quark.cn/s/xxx"}]'
```

States: `ok`(有效) / `bad`(失效) / `locked`(被锁) / `unsupported` / `uncertain`

## Direct API Calls

When the script doesn't cover a scenario, call the API directly:

```powershell
# Search
$body = '{"kw":"关键词","cloud_types":["quark"]}'
[Text.Encoding]::UTF8.GetBytes($body) | Invoke-RestMethod -Uri "https://so.252035.xyz/api/search" -Method POST -ContentType "application/json" -Body {$_}
```

For full API parameter details, read `references/api_reference.md`.

## Response Formatting

Present results to user in a clear, grouped format:

1. Show total count
2. Group by cloud type (e.g. 夸克 / 阿里 / 百度)
3. For each result: note(title), link, password(if any), source, time
4. When user picks a link, offer to check validity or save/transfer to cloud drive

## Tips

- Use specific keywords for better results; movie titles work better than generic terms
- Use `cloud_types` to narrow results to user's preferred drives
- Use `filter.include` / `filter.exclude` to refine by quality (4K, 高码) or exclude bad results (预告, 抢先)
- Search results are cached; use `--refresh` for latest data
- health endpoint may return 400 under Cloudflare; this is normal and doesn't affect search
