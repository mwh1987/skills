#!/usr/bin/env python3
"""PanSou - 网盘资源搜索与链接检测工具"""

import argparse
import json
import ssl
import sys
import urllib.request
import urllib.error

BASE_URL = "https://so.252035.xyz"
TIMEOUT = 30

# Create SSL context that works with Cloudflare
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


def _post(path, body_dict):
    """Send POST request and return parsed JSON."""
    data = json.dumps(body_dict, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=_ssl_ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        print(f"HTTP Error {e.code}: {body_text}", file=sys.stderr)
        sys.exit(1)


def _get(path):
    """Send GET request and return parsed JSON."""
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
        method="GET"
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=_ssl_ctx) as resp:
        return json.loads(resp.read().decode("utf-8"))


def search(kw, cloud_types=None, plugins=None, channels=None,
           res="merge", src="all", conc=None, refresh=False,
           filter_include=None, filter_exclude=None, ext=None,
           raw=False):
    """Search for cloud drive resources."""
    body = {"kw": kw}
    if cloud_types:
        body["cloud_types"] = [c.strip() for c in cloud_types.split(",")]
    if plugins:
        body["plugins"] = [p.strip() for p in plugins.split(",")]
    if channels:
        body["channels"] = [ch.strip() for ch in channels.split(",")]
    if res:
        body["res"] = res
    if src:
        body["src"] = src
    if conc:
        body["conc"] = int(conc)
    if refresh:
        body["refresh"] = True
    if filter_include or filter_exclude:
        body["filter"] = {}
        if filter_include:
            body["filter"]["include"] = [x.strip() for x in filter_include.split(",")]
        if filter_exclude:
            body["filter"]["exclude"] = [x.strip() for x in filter_exclude.split(",")]
    if ext:
        try:
            body["ext"] = json.loads(ext)
        except json.JSONDecodeError:
            print("Error: ext must be valid JSON", file=sys.stderr)
            sys.exit(1)

    result = _post("/api/search", body)

    if raw:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Pretty print
    data = result.get("data", result)
    total = data.get("total", 0)
    print(f"\n搜索关键词: {kw}")
    print(f"结果总数: {total}\n")

    # merged_by_type mode (default)
    merged = data.get("merged_by_type", {})
    if merged:
        for disk_type, links in merged.items():
            print(f"--- {disk_type.upper()} ({len(links)} 条) ---")
            for i, link in enumerate(links, 1):
                note = link.get("note", "")
                url = link.get("url", "")
                pwd = link.get("password", "")
                source = link.get("source", "")
                dt = link.get("datetime", "")
                pwd_str = f"  提取码: {pwd}" if pwd else ""
                print(f"  [{i}] {note}")
                print(f"      链接: {url}{pwd_str}")
                if source:
                    print(f"      来源: {source}")
                if dt and dt != "0001-01-01T00:00:00Z":
                    print(f"      时间: {dt}")
            print()

    # results mode
    results = data.get("results", [])
    if results and not merged:
        for i, r in enumerate(results, 1):
            title = r.get("title", "")
            content = r.get("content", "")
            channel = r.get("channel", "")
            dt = r.get("datetime", "")
            links = r.get("links", [])
            print(f"[{i}] {title or content[:60]}")
            if channel:
                print(f"    频道: {channel}")
            if dt:
                print(f"    时间: {dt}")
            for j, lk in enumerate(links, 1):
                lk_type = lk.get("type", "")
                lk_url = lk.get("url", "")
                lk_pwd = lk.get("password", "")
                pwd_str = f" 提取码:{lk_pwd}" if lk_pwd else ""
                print(f"    链接{j} [{lk_type}]: {lk_url}{pwd_str}")
            print()


def check_links(items_json, raw=False):
    """Check if cloud drive share links are still valid."""
    try:
        items = json.loads(items_json)
    except json.JSONDecodeError:
        print("Error: items must be a JSON array", file=sys.stderr)
        sys.exit(1)

    if not isinstance(items, list):
        items = [items]

    body = {"items": items}
    try:
        result = _post("/api/check/links", body)
    except urllib.error.HTTPError as e:
        print(f"Error: link check API returned {e.code}", file=sys.stderr)
        sys.exit(1)

    if raw:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    results = result.get("data", result).get("results", [])
    if not results:
        results = result.get("results", [])

    state_labels = {
        "ok": "有效",
        "bad": "失效",
        "locked": "被锁",
        "unsupported": "不支持检测",
        "uncertain": "不确定",
    }

    print("\n--- 链接检测结果 ---\n")
    for i, r in enumerate(results, 1):
        disk_type = r.get("disk_type", "")
        url = r.get("url", "")
        state = r.get("state", "")
        summary = r.get("summary", "")
        label = state_labels.get(state, state)
        print(f"  [{i}] [{disk_type}] {label}")
        print(f"      链接: {url}")
        if summary:
            print(f"      说明: {summary}")
    print()


def health(raw=False):
    """Check API service health."""
    try:
        result = _get("/api/health")
    except urllib.error.HTTPError:
        print("Warning: health endpoint unavailable (this is normal)", file=sys.stderr)
        return

    if raw:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    data = result.get("data", result)
    status = data.get("status", "unknown")
    channels = data.get("channels", [])
    plugins = data.get("plugins", [])
    auth_enabled = data.get("auth_enabled", False)
    print(f"\n服务状态: {status}")
    print(f"频道数: {len(channels)}")
    print(f"插件数: {len(plugins)}")
    print(f"认证: {'已启用' if auth_enabled else '未启用'}")
    if plugins:
        print(f"插件列表: {', '.join(plugins)}")
    print()


def main():
    parser = argparse.ArgumentParser(description="PanSou - 网盘资源搜索")
    sub = parser.add_subparsers(dest="command")

    # search
    s = sub.add_parser("search", help="搜索网盘资源")
    s.add_argument("kw", help="搜索关键词")
    s.add_argument("--cloud-types", "-c", help="网盘类型，逗号分隔 (baidu,aliyun,quark,uc,tianyi,115,xunlei,mobile,pikpak,123,guangya,magnet,ed2k)")
    s.add_argument("--plugins", "-p", help="插件列表，逗号分隔")
    s.add_argument("--channels", help="频道列表，逗号分隔")
    s.add_argument("--res", default="merge", choices=["all", "results", "merge"], help="结果类型 (默认merge)")
    s.add_argument("--src", default="all", choices=["all", "tg", "plugin"], help="数据来源 (默认all)")
    s.add_argument("--conc", type=int, help="并发数")
    s.add_argument("--refresh", action="store_true", help="强制刷新缓存")
    s.add_argument("--include", help="包含关键词，逗号分隔 (OR)")
    s.add_argument("--exclude", help="排除关键词，逗号分隔 (OR)")
    s.add_argument("--ext", help="扩展参数 JSON")
    s.add_argument("--raw", action="store_true", help="输出原始JSON")

    # check
    ck = sub.add_parser("check", help="检测链接有效性")
    ck.add_argument("items", help='JSON数组，如 [{"disk_type":"quark","url":"https://pan.quark.cn/s/xxx"}]')
    ck.add_argument("--raw", action="store_true", help="输出原始JSON")

    # health
    sub.add_parser("health", help="检查服务状态")

    args = parser.parse_args()
    if args.command == "search":
        search(args.kw, cloud_types=args.cloud_types, plugins=args.plugins,
               channels=args.channels, res=args.res, src=args.src,
               conc=args.conc, refresh=args.refresh,
               filter_include=args.include, filter_exclude=args.exclude,
               ext=args.ext, raw=args.raw)
    elif args.command == "check":
        check_links(args.items, raw=args.raw)
    elif args.command == "health":
        health()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
