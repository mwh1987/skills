#!/usr/bin/env python3
"""
迅雷MCP下载客户端 - 通过MCP SSE协议与迅雷云盘交互
支持：列出设备、验证链接、创建下载任务、查询任务状态、操作任务
"""

import requests
import json
import sys
import threading
import time
import argparse
import os
from urllib.parse import urljoin, urlparse


class XunleiMCPClient:
    """迅雷MCP SSE客户端"""

    def __init__(self, sse_url):
        self.sse_url = sse_url
        self.session = requests.Session()
        self.post_url = None
        self.responses = {}
        self.response_lock = threading.Lock()
        self.running = False
        self.request_id = 0
        self.connected = False
        self.server_request_id = 100000  # 服务器请求ID从大数开始，避免与客户端ID冲突

    def _next_id(self):
        self.request_id += 1
        return self.request_id

    def _resolve_url(self, url):
        if url.startswith("http"):
            return url
        parsed = urlparse(self.sse_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        return urljoin(base, url)

    def _sse_listener(self):
        """后台线程监听SSE事件流，使用原始字节解析避免编码截断"""
        try:
            resp = self.session.get(
                self.sse_url,
                headers={"Accept": "text/event-stream"},
                stream=True,
                timeout=300,
            )
            buffer = b""

            for chunk in resp.iter_content(chunk_size=4096):
                if not self.running:
                    break
                if not chunk:
                    continue
                buffer += chunk

                # SSE事件以双换行分隔（兼容 \r\n\r\n 和 \n\n）
                while b"\r\n\r\n" in buffer or b"\n\n" in buffer:
                    if b"\r\n\r\n" in buffer:
                        event_raw, buffer = buffer.split(b"\r\n\r\n", 1)
                    else:
                        event_raw, buffer = buffer.split(b"\n\n", 1)
                    self._parse_sse_event(event_raw.decode("utf-8", errors="replace"))
        except Exception as e:
            with self.response_lock:
                self.responses[-1] = {"error": f"SSE连接错误: {e}"}

    def _parse_sse_event(self, event_text):
        """解析单个SSE事件"""
        event_type = None
        data_lines = []

        for line in event_text.split("\n"):
            line = line.rstrip("\r")
            if line.startswith("event:"):
                event_type = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].lstrip())
            elif line.startswith(":"):
                pass  # SSE comment/heartbeat
            elif line.strip():
                # 不带前缀的行，可能是多行data的续行
                data_lines.append(line)

        if not data_lines:
            return

        data = "\n".join(data_lines)

        if event_type == "endpoint":
            self.post_url = self._resolve_url(data.strip())
        elif event_type == "message" or event_type is None:
            try:
                msg = json.loads(data)
                if "method" in msg:
                    # 服务器发起的请求（如ping），自动响应
                    req_id = msg.get("id")
                    if req_id is not None:
                        self._send_response(req_id, {})
                elif "id" in msg:
                    # 这是我们请求的响应
                    with self.response_lock:
                        self.responses[msg["id"]] = msg
            except json.JSONDecodeError:
                pass

    def connect(self, timeout=30):
        """连接MCP服务器并完成初始化握手"""
        self.running = True
        self.sse_thread = threading.Thread(target=self._sse_listener, daemon=True)
        self.sse_thread.start()

        start = time.time()
        while self.post_url is None and time.time() - start < timeout:
            with self.response_lock:
                if -1 in self.responses:
                    err = self.responses.pop(-1)
                    raise ConnectionError(err.get("error", "连接失败"))
            time.sleep(0.1)

        if self.post_url is None:
            raise TimeoutError("等待MCP endpoint超时")

        # 发送 initialize 请求
        resp = self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "TeleAgent-XunleiMCP", "version": "1.0.0"},
        })

        # 发送 initialized 通知
        self._send_notification("notifications/initialized", {})
        self.connected = True
        return resp

    def _send_request(self, method, params=None, timeout=30):
        """发送JSON-RPC请求并等待响应"""
        req_id = self._next_id()
        payload = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params:
            payload["params"] = params

        try:
            self.session.post(self.post_url, json=payload, timeout=10)
        except Exception:
            pass

        start = time.time()
        while time.time() - start < timeout:
            with self.response_lock:
                if req_id in self.responses:
                    return self.responses.pop(req_id)
                if -1 in self.responses:
                    err = self.responses.pop(-1)
                    raise ConnectionError(err.get("error", "连接错误"))
            time.sleep(0.1)

        raise TimeoutError(f"等待 {method} 响应超时")

    def _send_response(self, req_id, result):
        """发送JSON-RPC响应给服务器（如ping响应）"""
        payload = {"jsonrpc": "2.0", "id": req_id, "result": result}
        try:
            self.session.post(self.post_url, json=payload, timeout=10)
        except Exception:
            pass

    def _send_notification(self, method, params=None):
        """发送JSON-RPC通知（不等待响应）"""
        payload = {"jsonrpc": "2.0", "method": method}
        if params:
            payload["params"] = params
        try:
            self.session.post(self.post_url, json=payload, timeout=10)
        except Exception:
            pass

    def list_tools(self):
        """列出所有可用的MCP工具"""
        return self._send_request("tools/list")

    def call_tool(self, name, arguments=None):
        """调用指定的MCP工具"""
        return self._send_request("tools/call", {
            "name": name,
            "arguments": arguments or {},
        })

    def close(self):
        """关闭连接"""
        self.running = False
        if hasattr(self, "sse_thread") and self.sse_thread:
            self.sse_thread.join(timeout=3)


def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def print_result(result):
    """格式化输出结果"""
    if "error" in result:
        print(f"错误: {result['error']}")
        if "message" in result:
            print(f"   详情: {result['message']}")
        return
    if "result" in result:
        r = result["result"]
        if isinstance(r, dict) and "content" in r:
            for item in r["content"]:
                if item.get("type") == "text":
                    try:
                        parsed = json.loads(item["text"])
                        print(json.dumps(parsed, ensure_ascii=False, indent=2))
                    except (json.JSONDecodeError, TypeError):
                        print(item["text"])
                else:
                    print(json.dumps(item, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


def find_tool(tools, keywords):
    """根据关键词匹配工具"""
    for t in tools:
        name = t.get("name", "").lower()
        desc = t.get("description", "").lower()
        for kw in keywords:
            if kw in name or kw in desc:
                return t
    return None


def main():
    parser = argparse.ArgumentParser(
        description="迅雷MCP下载客户端",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python xunlei_mcp.py tools                        # 列出所有可用工具
  python xunlei_mcp.py devices                      # 列出下载设备
  python xunlei_mcp.py verify <链接>                # 验证下载链接
  python xunlei_mcp.py download <链接> -d <设备ID>  # 创建下载任务（需指定设备）
  python xunlei_mcp.py tasks -d <设备ID>            # 查询下载任务列表
  python xunlei_mcp.py operate <设备ID> <任务ID> <action>  # 操作任务(running/pause/delete)
  python xunlei_mcp.py call <工具名> <JSON参数>     # 调用任意MCP工具
        """,
    )

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("tools", help="列出所有可用MCP工具")
    sub.add_parser("devices", help="列出下载设备")

    verify = sub.add_parser("verify", help="验证下载链接")
    verify.add_argument("urls", nargs="+", help="下载链接（支持多个）")

    download = sub.add_parser("download", help="创建下载任务")
    download.add_argument("urls", nargs="+", help="下载链接（支持多个）")
    download.add_argument("-d", "--device", required=True, help="目标设备ID（必填）")
    download.add_argument("-n", "--names", nargs="*", help="任务名称（可选，需与urls数量一致）")

    tasks = sub.add_parser("tasks", help="查询下载任务列表")
    tasks.add_argument("-d", "--device", required=True, help="目标设备ID（必填）")

    operate = sub.add_parser("operate", help="操作下载任务")
    operate.add_argument("device", help="目标设备ID")
    operate.add_argument("task_id", help="任务ID")
    operate.add_argument("action", choices=["running", "pause", "delete"], help="操作类型")

    call = sub.add_parser("call", help="调用任意MCP工具")
    call.add_argument("tool_name", help="工具名称")
    call.add_argument("args_json", nargs="?", default="{}", help="JSON格式参数")

    parser.add_argument("--url", help="MCP SSE URL（覆盖配置文件）")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # 获取MCP URL
    config = load_config()
    sse_url = args.url or config.get("mcp_url")
    if not sse_url:
        print("错误: 未配置MCP URL。请在 config.json 中设置 mcp_url，或使用 --url 参数。")
        sys.exit(1)

    # 连接
    client = XunleiMCPClient(sse_url)
    try:
        client.connect()
    except Exception as e:
        print(f"错误: 连接MCP服务器失败: {e}")
        sys.exit(1)

    try:
        if args.command == "tools":
            result = client.list_tools()
            print_result(result)

        elif args.command == "devices":
            result = client.call_tool("xunlei_download_list_device")
            print_result(result)

        elif args.command == "verify":
            result = client.call_tool("xunlei_download_check_urls", {"urls": args.urls})
            print_result(result)

        elif args.command == "download":
            tool_args = {"target": args.device, "urls": args.urls}
            if args.names:
                tool_args["names"] = args.names
            result = client.call_tool("xunlei_download_create", tool_args)
            print_result(result)

        elif args.command == "tasks":
            result = client.call_tool("xunlei_download_list", {"target": args.device})
            print_result(result)

        elif args.command == "operate":
            result = client.call_tool("xunlei_download_operate", {
                "target": args.device,
                "task_id": args.task_id,
                "action": args.action,
            })
            print_result(result)

        elif args.command == "call":
            try:
                tool_args = json.loads(args.args_json)
            except json.JSONDecodeError:
                print("错误: 参数JSON格式错误")
                sys.exit(1)
            result = client.call_tool(args.tool_name, tool_args)
            print_result(result)

    except Exception as e:
        print(f"错误: 执行失败: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    main()
