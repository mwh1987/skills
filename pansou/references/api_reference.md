---
AIGC:
  ContentProducer: '001191110102MAD55U9H0F10002'
  ContentPropagator: '001191110102MAD55U9H0F10002'
  Label: '1'
  ProduceID: '72625664-9a67-4b4e-a476-4edeca50ef6c'
  PropagateID: '72625664-9a67-4b4e-a476-4edeca50ef6c'
  ReservedCode1: 'b088994f-fae2-490e-9504-8bfa4ebaf57f'
  ReservedCode2: 'b088994f-fae2-490e-9504-8bfa4ebaf57f'
---

# PanSou API Reference

## Base URL

`https://so.252035.xyz`

## Authentication

Currently disabled. No token required.

## Endpoints

### POST /api/search

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| kw | string | Yes | Search keyword |
| channels | string[] | No | TG channel list; defaults to server config |
| conc | number | No | Concurrency; auto if omitted |
| refresh | boolean | No | Force refresh, skip cache |
| res | string | No | Result type: `all` / `results` / `merge` (default `merge`) |
| src | string | No | Source: `all` / `tg` / `plugin` (default `all`) |
| plugins | string[] | No | Plugin list to search |
| cloud_types | string[] | No | Cloud types to return |
| ext | object | No | Extension params for plugins, e.g. `{"title_en":"..."}` |
| filter | object | No | Filter: `{"include":["4K"],"exclude":["预告"]}` (OR logic) |

### Supported cloud_types

`baidu`, `aliyun`, `quark`, `uc`, `tianyi`, `115`, `xunlei`, `mobile`, `pikpak`, `123`, `guangya`, `magnet`, `ed2k`

### Response (res=merge, default)

```json
{
  "code": 0,
  "data": {
    "total": 7,
    "merged_by_type": {
      "quark": [
        {"url": "...", "password": "", "note": "...", "datetime": "...", "source": "plugin:wanou"}
      ]
    }
  }
}
```

### POST /api/check/links

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| items | object[] | Yes | Links to check |
| items[].disk_type | string | Yes | Cloud type: baidu/quark/xunlei/115/mobile |
| items[].url | string | Yes | Full share link |
| items[].password | string | No | Extraction code |
| view_token | string | No | View batch identifier |

**Response states:** `ok` / `bad` / `locked` / `unsupported` / `uncertain`

### GET /api/health

Returns service status, channel list, plugin info, auth status.

### POST /api/auth/login

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| username | string | Yes | Username |
| password | string | Yes | Password |

Returns JWT token. Currently auth is disabled.

### Error Codes

| Code | Meaning |
|------|---------|
| 400 | Parameter error |
| 429 | Rate limited |
| 500 | Server error |

> AI生成