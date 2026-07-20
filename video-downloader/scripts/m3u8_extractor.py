# -*- coding: utf-8 -*-
"""
m3u8视频链接提取工具
通过Playwright加载视频解析页面，拦截网络请求获取m3u8链接

增强功能:
  - master playlist多码率解析与选择
  - 下载大小预估（根据m3u8分段数×平均段大小）
  - VIP/付费内容检测
  - 解析站可用性健康监测

用法（命令行）:
  python m3u8_extractor.py <视频URL> [--timeout 20] [--api 0]
  python m3u8_extractor.py --health-check         # 检查解析站可用性
  python m3u8_extractor.py --estimate <m3u8_url>   # 预估下载大小

用法（模块导入）:
  from m3u8_extractor import extract_m3u8, auto_extract
  result = asyncio.run(auto_extract("https://v.qq.com/x/cover/xxx/xxx.html"))
"""

import sys
import json
import asyncio
import re
import time
from urllib.parse import quote

# 解析接口列表 (名称, 前缀, 成功率估计)
# 成功率基于: Playwright实测m3u8拦截 > HTTP连通性+播放器特征 > 历史经验
# 标记: ★=Playwright实测m3u8成功, ●=HTTP PASS+播放器, ○=HTTP WEAK(仅页面加载)
PARSE_APIS = [
    # ── 第一梯队: Playwright实测m3u8提取成功 ──
    ("虾米解析-主线路",     "https://jx.xmflv.com/?url=",                 0.95),  # ★ 经典稳定
    ("虾米解析-备用",       "https://jx.xmflv.cc/?url=",                 0.90),  # ★ 主线路备份
    ("playm3u8",           "https://www.playm3u8.cn/jiexi.php?url=",      0.88),  # ★ 实测成功,公益无广告
    ("ckplayer",           "https://www.ckplayer.vip/jiexi/?url=",        0.85),  # ★ 实测成功
    ("盘古解析-com",        "https://www.pangujiexi.com/jiexi/?url=",      0.85),  # ★ 实测成功(.com非.cc)
    ("8090g-稳定线路",      "https://www.8090g.cn/?url=",                 0.85),  # ★ 历史验证
    ("m3u8TV",             "https://jx.m3u8.tv/jiexi/?url=",              0.80),  # ★ 历史验证
    # ── 第二梯队: HTTP连通+播放器特征检测通过(需Playwright验证) ──
    ("yparse-ik9",         "https://yparse.ik9.cc/index.php?url=",        0.78),  # ● 26KB页面,含播放器
    ("yparse-com",         "https://jx.yparse.com/index.php?url=",         0.78),  # ● 26KB页面,含播放器
    ("剖元pouyun",          "https://www.pouyun.com/?url=",                 0.75),  # ● 5.8KB,含播放器
    ("m1907",              "https://im1907.top/?jx=",                      0.75),  # ● 1.4KB,含播放器
    ("qianqi",             "https://api.qianqi.net/vip/?url=",             0.72),  # ● 2.3KB,含播放器
    ("pakou-全民解析",      "https://www.pakou.cn/?url=",                   0.70),  # ● 8.5KB,含播放器
    ("vps6-全网视频",       "https://v.vps6.cn/?url=",                      0.70),  # ● 10KB+,含播放器
    ("47jx",               "https://www.47jx.com/?url=",                   0.68),  # ● 6.7KB,含播放器
    ("ejiafarm",           "https://ejiafarm.com/jx.php?url=",             0.65),  # ● 3KB,含播放器(HTTP PASS)
    # ── 第三梯队: HTTP WEAK(页面加载但未检测到播放器特征) ──
    ("618g",               "https://jx.618g.com/?url=",                   0.55),  # ○ 页面可加载,1.2KB
    ("jqaaa",              "https://jqaaa.com/jx.php?url=",               0.55),  # ○ 页面可加载,4.5KB
    ("daidaitv",           "https://api.daidaitv.com/index/?url=",         0.50),  # ○ 页面可加载,4.5KB
    ("662820",             "https://api.662820.com/xnflv/index.php?url=",  0.50),  # ○ 页面可加载,4.5KB
    # ── 已失效(保留注释供参考) ──
    # ("盘古解析-cc",        "https://www.pangujiexi.cc/jiexi.php?url=",    0.10),  # 超时
    # ("okjx",               "https://okjx.cc/?url=",                       0.10),  # SSL错误
    # ("2s0",                "https://jx.2s0.cn/player/?url=",              0.05),  # 解析失败
    # ("parwix",             "https://jx.parwix.com:4433/player/?url=",     0.05),  # 超时
    # ("apii全能VIP",        "http://api.apii.top/?v=",                     0.05),  # 超时
    # ("svip.bljiex",        "https://svip.bljiex.cc/?v=",                  0.05),  # SSL错误
]

# VIP/付费内容关键词（用于在视频页面上检测）
VIP_KEYWORDS = [
    "VIP", "vip", "会员", "付费", "付费观看", "独播",
    "VIP免费", "VIP用", "黄金会员", "白金会员",
    "超前点播", "星钻", "体育会员", "试看",
]

# 各平台VIP标识的CSS/文本特征
VIP_PLATFORM_INDICATORS = {
    "iqiyi":    [".iqp-player-vip", ".mod-vip", "iqp-tip-vip"],
    "qq":       [".txp_vip_label", ".mod_vip_tag", "txp-icon-vip"],
    "youku":    [".vip-icon", ".control-vip", "youku-vip"],
    "mgtv":     [".vip-label", ".m-vip", "芒果VIP"],
    "bilibili": [".vip-icon", ".bangumi-badge-vip", "大会员"],
}


def validate_m3u8_url(m3u8_url: str) -> dict:
    """
    验证m3u8链接是否仍可用（过期检查）

    返回:
        dict: { valid, status_code, error }
    """
    import requests
    try:
        resp = requests.head(m3u8_url, timeout=10, allow_redirects=True)
        if resp.status_code == 200:
            return {"valid": True, "status_code": 200, "error": None}
        else:
            return {"valid": False, "status_code": resp.status_code,
                    "error": f"HTTP {resp.status_code}"}
    except requests.RequestException as e:
        return {"valid": False, "status_code": None, "error": str(e)}


def parse_resolution_and_codec(m3u8_content: str, n_m3u8dl_output: str = "") -> dict:
    """
    从m3u8内容和N_m3u8DL输出中提取分辨率和编码

    参数:
        m3u8_content:    m3u8文件内容
        n_m3u8dl_output: N_m3u8DL-CLI的控制台输出

    返回:
        dict: { resolution_label, codec_label, width, height }
    """
    width, height = 0, 0
    codec = "H264"

    # 1. 从N_m3u8DL输出提取分辨率
    if n_m3u8dl_output:
        res_match = re.search(r'分辨率[：:]\s*(\d+)\s*x\s*(\d+)', n_m3u8dl_output)
        if res_match:
            width, height = int(res_match.group(1)), int(res_match.group(2))

    # 2. 从m3u8内容提取CODECS
    if m3u8_content:
        codecs_match = re.search(r'CODECS="([^"]+)"', m3u8_content, re.IGNORECASE)
        if codecs_match:
            codecs_str = codecs_match.group(1).upper()
            if "AV01" in codecs_str:
                codec = "AV1"
            elif "HEV" in codecs_str or "HVC" in codecs_str:
                codec = "H265"
            elif "AVC" in codecs_str:
                codec = "H264"

    # 3. 分辨率标签
    res_label = None
    if height > 0 or width > 0:
        if height >= 2160 or width >= 3840:
            res_label = "2160p"
        elif height >= 1080 or width >= 1920:
            res_label = "1080p"
        elif height >= 720 or width >= 1280:
            res_label = "720p"
        else:
            res_label = "480p"

    return {
        "resolution_label": res_label,
        "codec_label": codec,
        "width": width,
        "height": height,
        "detected": res_label is not None,
    }


# ─── Master Playlist 多码率解析 ────────────────────────────

def parse_master_playlist(m3u8_content: str, base_url: str = "") -> list:
    """
    解析master playlist，提取所有可用的码率/分辨率变体

    参数:
        m3u8_content: m3u8文件内容
        base_url:     基础URL，用于拼接相对路径

    返回:
        list: 变体列表，每项 { bandwidth, resolution, codecs, url, label }
              按bandwidth降序排列（最高画质在前）
    """
    variants = []
    lines = m3u8_content.strip().split('\n')

    # 检测是否为master playlist（包含 #EXT-X-STREAM-INF）
    if '#EXT-X-STREAM-INF' not in m3u8_content:
        # 不是master playlist，只有一个分辨率
        return []

    current_variant = {}
    for line in lines:
        line = line.strip()
        if line.startswith('#EXT-X-STREAM-INF'):
            current_variant = {}
            # 解析属性
            bandwidth_match = re.search(r'BANDWIDTH=(\d+)', line)
            if bandwidth_match:
                current_variant["bandwidth"] = int(bandwidth_match.group(1))

            resolution_match = re.search(r'RESOLUTION=(\d+)x(\d+)', line)
            if resolution_match:
                current_variant["width"] = int(resolution_match.group(1))
                current_variant["height"] = int(resolution_match.group(2))

            codecs_match = re.search(r'CODECS="([^"]+)"', line, re.IGNORECASE)
            if codecs_match:
                current_variant["codecs"] = codecs_match.group(1)

            # 生成可读标签
            label_parts = []
            if "height" in current_variant:
                h = current_variant["height"]
                if h >= 2160:
                    label_parts.append("4K")
                elif h >= 1080:
                    label_parts.append("1080P")
                elif h >= 720:
                    label_parts.append("720P")
                else:
                    label_parts.append("480P")
            else:
                # 根据比特率推算
                bw = current_variant.get("bandwidth", 0)
                if bw > 8000000:
                    label_parts.append("4K")
                elif bw > 3000000:
                    label_parts.append("1080P")
                elif bw > 1500000:
                    label_parts.append("720P")
                else:
                    label_parts.append("480P")

            bitrate_mbps = round(current_variant.get("bandwidth", 0) / 1000000, 1)
            label_parts.append(f"{bitrate_mbps}Mbps")
            current_variant["label"] = " ".join(label_parts)

        elif line and not line.startswith('#') and current_variant:
            # 这是变体的URL
            if base_url and not line.startswith('http'):
                # 拼接相对路径
                if line.startswith('/'):
                    from urllib.parse import urlparse
                    parsed = urlparse(base_url)
                    current_variant["url"] = f"{parsed.scheme}://{parsed.netloc}{line}"
                else:
                    current_variant["url"] = base_url.rsplit('/', 1)[0] + '/' + line
            else:
                current_variant["url"] = line

            # 编码标签映射
            codecs_str = current_variant.get("codecs", "").upper()
            if "AV01" in codecs_str:
                current_variant["codec_label"] = "AV1"
            elif "HEV" in codecs_str or "HVC" in codecs_str:
                current_variant["codec_label"] = "H265"
            elif "AVC" in codecs_str:
                current_variant["codec_label"] = "H264"
            else:
                current_variant["codec_label"] = "H264"

            # 分辨率标签
            h = current_variant.get("height", 0)
            if h >= 2160:
                current_variant["resolution_label"] = "2160p"
            elif h >= 1080:
                current_variant["resolution_label"] = "1080p"
            elif h >= 720:
                current_variant["resolution_label"] = "720p"
            elif h > 0:
                current_variant["resolution_label"] = "480p"
            else:
                current_variant["resolution_label"] = None

            variants.append(current_variant)
            current_variant = {}

    # 按bandwidth降序排列
    variants.sort(key=lambda v: v.get("bandwidth", 0), reverse=True)
    return variants


# ─── 下载大小预估 ────────────────────────────────────────

def estimate_download_size(m3u8_url: str, sample_count: int = 3) -> dict:
    """
    预估m3u8视频的下载文件大小

    策略:
      1. 下载m3u8内容，统计TS分段数量和总时长
      2. 下载前N个TS分段，获取实际大小
      3. 根据分段平均大小 × 总分段数 = 预估总大小
      4. 如果无法下载TS分段，根据总时长和分辨率估算

    参数:
        m3u8_url:    m3u8链接
        sample_count: 采样的TS分段数量

    返回:
        dict: { estimated_bytes, estimated_mb, segment_count,
                total_duration_sec, confidence, method }
    """
    import requests

    try:
        resp = requests.get(m3u8_url, timeout=15, allow_redirects=True)
        if resp.status_code != 200:
            return {"estimated_mb": 0, "confidence": "low", "error": f"HTTP {resp.status_code}"}
        content = resp.text
    except Exception as e:
        return {"estimated_mb": 0, "confidence": "low", "error": str(e)}

    # 如果是master playlist，取最高码率变体
    if '#EXT-X-STREAM-INF' in content:
        variants = parse_master_playlist(content, m3u8_url)
        if variants:
            # 选择最高码率的变体
            m3u8_url = variants[0]["url"]
            try:
                resp = requests.get(m3u8_url, timeout=15, allow_redirects=True)
                if resp.status_code == 200:
                    content = resp.text
            except Exception:
                pass

    # 统计TS分段数量和总时长
    segment_urls = []
    total_duration = 0.0
    base_url = m3u8_url.rsplit('/', 1)[0] + '/'

    lines = content.strip().split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith('#EXTINF'):
            # 提取时长: #EXTINF:10.000,
            dur_match = re.match(r'#EXTINF:([\d.]+)', line)
            if dur_match:
                total_duration += float(dur_match.group(1))
        elif line and not line.startswith('#'):
            # 这是分段URL
            if line.startswith('http'):
                segment_urls.append(line)
            else:
                segment_urls.append(base_url + line)

    segment_count = len(segment_urls)

    if segment_count == 0:
        return {
            "estimated_mb": 0,
            "segment_count": 0,
            "total_duration_sec": round(total_duration, 1),
            "confidence": "low",
            "method": "no_segments",
            "error": "m3u8中未找到TS分段",
        }

    # 方法1: 采样前N个TS分段的实际大小
    sample_size = 0
    sampled = 0
    for url in segment_urls[:sample_count]:
        try:
            head_resp = requests.head(url, timeout=10, allow_redirects=True)
            if head_resp.status_code == 200 and 'Content-Length' in head_resp.headers:
                sample_size += int(head_resp.headers['Content-Length'])
                sampled += 1
            else:
                # HEAD不返回长度，尝试GET前1KB
                get_resp = requests.get(url, timeout=10, allow_redirects=True,
                                        headers={"Range": "bytes=0-1023"})
                if get_resp.status_code in (200, 206):
                    # 估算整个分段大小（根据总时长/分段数 × 比特率）
                    sampled += 1
        except Exception:
            pass

    if sampled > 0:
        avg_segment_bytes = sample_size / sampled
        total_bytes = avg_segment_bytes * segment_count
        return {
            "estimated_bytes": int(total_bytes),
            "estimated_mb": round(total_bytes / 1024 / 1024, 1),
            "segment_count": segment_count,
            "total_duration_sec": round(total_duration, 1),
            "sampled_segments": sampled,
            "avg_segment_kb": round(avg_segment_bytes / 1024, 1),
            "confidence": "high",
            "method": "sampled_ts",
        }

    # 方法2: 根据总时长和默认比特率估算
    # 参考比特率: 480p~2Mbps, 720p~4Mbps, 1080p~8Mbps, 4K~20Mbps
    bitrate_map = {"2160p": 20e6, "1080p": 8e6, "720p": 4e6, "480p": 2e6}

    # 尝试从m3u8内容推断分辨率
    res_label = None
    if '#EXT-X-STREAM-INF' in content:
        variants = parse_master_playlist(content, m3u8_url)
        if variants:
            res_label = variants[0].get("resolution_label")

    # 从CODECS字段或m3u8 URL推断分辨率
    if not res_label:
        bandwidth_match = re.search(r'BANDWIDTH=(\d+)', content)
        if bandwidth_match:
            bw = int(bandwidth_match.group(1))
            if bw > 8000000:
                res_label = "2160p"
            elif bw > 3000000:
                res_label = "1080p"
            elif bw > 1500000:
                res_label = "720p"
            else:
                res_label = "480p"

    if not res_label:
        res_label = "1080p"  # 默认猜测

    bitrate = bitrate_map.get(res_label, 8e6)
    total_bytes = (bitrate / 8) * total_duration

    return {
        "estimated_bytes": int(total_bytes),
        "estimated_mb": round(total_bytes / 1024 / 1024, 1),
        "segment_count": segment_count,
        "total_duration_sec": round(total_duration, 1),
        "assumed_resolution": res_label,
        "confidence": "medium",
        "method": "bitrate_estimate",
    }


# ─── VIP内容检测 ──────────────────────────────────────────

def detect_vip_from_page(page_text: str, platform: str = "") -> dict:
    """
    从视频页面文本中检测VIP/付费内容标识

    参数:
        page_text:  页面文本内容（从snapshot或HTML提取）
        platform:   平台标识 (iqiyi/qq/youku/mgtv/bilibili)

    返回:
        dict: { is_vip, vip_type, indicators, platform }
              vip_type: "full" (完全付费), "advanced" (超前点播), "free_preview" (试看), None
    """
    indicators_found = []
    text_lower = page_text.lower()

    for keyword in VIP_KEYWORDS:
        if keyword.lower() in text_lower:
            indicators_found.append(keyword)

    # 平台特定检测
    platform_key = ""
    if "iqiyi" in platform or "爱奇艺" in platform:
        platform_key = "iqiyi"
    elif "qq.com" in platform or "腾讯" in platform:
        platform_key = "qq"
    elif "youku" in platform or "优酷" in platform:
        platform_key = "youku"
    elif "mgtv" in platform or "芒果" in platform:
        platform_key = "mgtv"
    elif "bilibili" in platform or "哔哩" in platform:
        platform_key = "bilibili"

    # 判断VIP类型
    vip_type = None
    if any(kw in indicators_found for kw in ["超前点播"]):
        vip_type = "advanced"
    elif any(kw in indicators_found for kw in ["试看"]):
        vip_type = "free_preview"
    elif indicators_found:
        vip_type = "full"

    return {
        "is_vip": len(indicators_found) > 0,
        "vip_type": vip_type,
        "indicators": indicators_found,
        "platform": platform_key,
    }


def detect_vip_from_url(video_url: str) -> dict:
    """
    根据视频URL的平台特征，提示可能需要VIP检测

    注意：这只是根据URL判断平台，实际VIP检测需要在页面加载后通过
    detect_vip_from_page() 执行。
    """
    platform = ""
    if "iqiyi.com" in video_url:
        platform = "iqiyi"
    elif "v.qq.com" in video_url:
        platform = "qq"
    elif "youku.com" in video_url:
        platform = "youku"
    elif "mgtv.com" in video_url:
        platform = "mgtv"
    elif "bilibili.com" in video_url:
        platform = "bilibili"

    return {
        "platform": platform,
        "should_check": bool(platform),
        "message": f"检测到平台: {platform}，建议在视频页面加载后检查VIP标识" if platform else "无法识别平台",
    }


# ─── 解析站可用性监测 ──────────────────────────────────────

def check_parse_site_health(timeout: int = 10) -> list:
    """
    检查所有解析接口的可用性

    参数:
        timeout: 请求超时时间(秒)

    返回:
        list: 每个接口的健康状态 { name, url, status, response_time_ms, error }
              status: "healthy" / "degraded" / "down"
    """
    import requests

    results = []
    for name, url_prefix, _ in PARSE_APIS:
        start = time.time()
        try:
            resp = requests.get(url_prefix, timeout=timeout, allow_redirects=True,
                                headers={"User-Agent": "Mozilla/5.0"})
            elapsed_ms = round((time.time() - start) * 1000)

            if resp.status_code == 200:
                # 检查是否被重定向到无关页面（如域名停放）
                content_lower = resp.text.lower()
                is_parking = any(kw in content_lower for kw in
                                ["domain parking", "此域名出售", "buy this domain"])

                if is_parking:
                    status = "down"
                elif elapsed_ms > 5000:
                    status = "degraded"
                else:
                    status = "healthy"

                results.append({
                    "name": name,
                    "url": url_prefix,
                    "status": status,
                    "response_time_ms": elapsed_ms,
                    "error": "域名已停用" if is_parking else None,
                })
            else:
                elapsed_ms = round((time.time() - start) * 1000)
                results.append({
                    "name": name,
                    "url": url_prefix,
                    "status": "down",
                    "response_time_ms": elapsed_ms,
                    "error": f"HTTP {resp.status_code}",
                })
        except requests.Timeout:
            elapsed_ms = round((time.time() - start) * 1000)
            results.append({
                "name": name,
                "url": url_prefix,
                "status": "down",
                "response_time_ms": elapsed_ms,
                "error": "请求超时",
            })
        except Exception as e:
            elapsed_ms = round((time.time() - start) * 1000)
            results.append({
                "name": name,
                "url": url_prefix,
                "status": "down",
                "response_time_ms": elapsed_ms,
                "error": str(e)[:100],
            })

    return results


# ─── Playwright m3u8 提取 ─────────────────────────────────

async def extract_m3u8(video_url: str, api_index: int = 0, timeout: int = 20) -> dict:
    """
    通过Playwright网络拦截提取m3u8链接

    参数:
        video_url:  流媒体网站视频URL
        api_index:  解析接口序号
        timeout:    等待最长时间(秒)

    返回:
        dict: { success, m3u8_url, all_m3u8_urls, parse_api, video_url, ts_count,
                master_playlist_variants, estimated_size }
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"success": False, "error": "playwright未安装，请运行: pip install playwright && playwright install chromium"}

    if api_index >= len(PARSE_APIS):
        return {"success": False, "error": f"接口索引超出范围(共{len(PARSE_APIS)}个)"}

    api_name, api_prefix, _ = PARSE_APIS[api_index]
    parse_url = api_prefix + quote(video_url, safe='')

    m3u8_urls = []
    ts_urls = []
    m3u8_contents = {}  # url -> content

    async def handle_request(route, request):
        url = request.url
        if '.m3u8' in url:
            m3u8_urls.append(url)
        elif '.ts' in url and (url.endswith('.ts') or '.ts?' in url):
            ts_urls.append(url)
        await route.continue_()

    async def handle_response(response):
        url = response.url
        if '.m3u8' in url and response.status == 200:
            try:
                content = await response.text()
                m3u8_contents[url] = content
            except Exception:
                pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        await context.route("**/*", handle_request)
        page = await context.new_page()
        page.on("response", handle_response)

        try:
            await page.goto(parse_url, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(timeout)
        except Exception:
            pass  # 超时也检查已捕获的链接

        # 探测VIP标识
        vip_result = None
        try:
            page_text = await page.inner_text("body")
            vip_result = detect_vip_from_page(page_text, video_url)
        except Exception:
            pass

        await browser.close()

    if m3u8_urls:
        # 优先选择非index的m3u8（主播放列表）
        main_m3u8 = None
        for url in m3u8_urls:
            if 'index' not in url.lower():
                main_m3u8 = url
                break
        main_m3u8 = main_m3u8 or m3u8_urls[0]

        result = {
            "success": True,
            "m3u8_url": main_m3u8,
            "all_m3u8_urls": m3u8_urls,
            "parse_api": api_name,
            "video_url": video_url,
            "ts_count": len(ts_urls),
        }

        # 解析master playlist（如果有多个码率变体）
        main_content = m3u8_contents.get(main_m3u8, "")
        if main_content and '#EXT-X-STREAM-INF' in main_content:
            variants = parse_master_playlist(main_content, main_m3u8)
            if variants:
                result["master_playlist_variants"] = variants
                result["has_multiple_qualities"] = True

        # 预估下载大小
        if main_content:
            size_est = estimate_download_size_main(main_content, main_m3u8,
                                                    len(ts_urls))
            if size_est["estimated_mb"] > 0:
                result["estimated_size"] = size_est

        # VIP检测结果
        if vip_result and vip_result["is_vip"]:
            result["vip_warning"] = vip_result

        return result
    else:
        result = {
            "success": False,
            "error": "未捕获到m3u8链接",
            "parse_api": api_name,
            "video_url": video_url,
        }
        if vip_result and vip_result["is_vip"]:
            result["vip_warning"] = vip_result
            result["error"] += "（可能是VIP内容）"
        return result


def estimate_download_size_main(m3u8_content: str, m3u8_url: str,
                                 ts_count: int = 0) -> dict:
    """
    从已获取的m3u8内容预估下载大小（不额外请求网络）

    参数:
        m3u8_content: m3u8文件内容
        m3u8_url:     m3u8链接（用于拼接相对路径）
        ts_count:     已知的TS分段数量

    返回:
        dict: { estimated_mb, segment_count, total_duration_sec, confidence, method }
    """
    # 统计分段数和总时长
    segment_count = 0
    total_duration = 0.0

    lines = m3u8_content.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('#EXTINF'):
            dur_match = re.match(r'#EXTINF:([\d.]+)', line)
            if dur_match:
                total_duration += float(dur_match.group(1))
        elif line and not line.startswith('#'):
            segment_count += 1

    if ts_count > 0:
        segment_count = max(segment_count, ts_count)

    if segment_count == 0:
        return {"estimated_mb": 0, "confidence": "low", "method": "no_segments"}

    # 根据总时长和分辨率估算（不额外请求网络）
    bitrate_map = {"2160p": 20e6, "1080p": 8e6, "720p": 4e6, "480p": 2e6}

    # 尝试推断分辨率
    res_label = None
    if '#EXT-X-STREAM-INF' in m3u8_content:
        variants = parse_master_playlist(m3u8_content, m3u8_url)
        if variants:
            res_label = variants[0].get("resolution_label")

    if not res_label:
        # 从CODECS推断
        metadata = parse_resolution_and_codec(m3u8_content)
        # 从带宽推断
        bandwidth_match = re.search(r'BANDWIDTH=(\d+)', m3u8_content)
        if bandwidth_match:
            bw = int(bandwidth_match.group(1))
            if bw > 8000000:
                res_label = "2160p"
            elif bw > 3000000:
                res_label = "1080p"
            elif bw > 1500000:
                res_label = "720p"
            else:
                res_label = "480p"

    if not res_label:
        res_label = "1080p"

    bitrate = bitrate_map.get(res_label, 8e6)
    total_bytes = (bitrate / 8) * total_duration

    return {
        "estimated_bytes": int(total_bytes),
        "estimated_mb": round(total_bytes / 1024 / 1024, 1),
        "segment_count": segment_count,
        "total_duration_sec": round(total_duration, 1),
        "assumed_resolution": res_label,
        "confidence": "medium",
        "method": "bitrate_estimate",
    }


async def auto_extract(video_url: str, max_attempts: int = 3,
                       validate: bool = False) -> dict:
    """
    按成功率从高到低自动尝试多个解析接口

    参数:
        video_url:    流媒体网站视频URL
        max_attempts: 最多尝试几个接口
        validate:     是否验证m3u8链接可用性

    返回:
        dict: { success, m3u8_url, ... }
    """
    sorted_apis = sorted(enumerate(PARSE_APIS), key=lambda x: x[1][2], reverse=True)

    for attempt, (orig_idx, (name, _, rate)) in enumerate(sorted_apis[:max_attempts]):
        result = await extract_m3u8(video_url, api_index=orig_idx, timeout=15)
        if result["success"]:
            if validate:
                validation = validate_m3u8_url(result["m3u8_url"])
                if not validation["valid"]:
                    result["warning"] = f"m3u8链接可能已过期: {validation['error']}"
            return result

    return {
        "success": False,
        "error": f"已尝试{max_attempts}个接口均未获取到m3u8链接",
        "video_url": video_url
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "用法: python m3u8_extractor.py <视频URL> [--timeout N] [--api N] [--validate] [--health-check] [--estimate <m3u8_url>]"
        }, ensure_ascii=False))
        sys.exit(1)

    # 健康检查模式
    if sys.argv[1] == "--health-check":
        results = check_parse_site_health()
        for r in results:
            status_icon = {"healthy": "OK", "degraded": "!!", "down": "XX"}[r["status"]]
            print(f"  [{status_icon}] {r['name']:20s} {r['response_time_ms']:6d}ms  {r.get('error') or ''}")
        sys.exit(0)

    # 大小预估模式
    if sys.argv[1] == "--estimate":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "请提供m3u8链接"}, ensure_ascii=False))
            sys.exit(1)
        result = estimate_download_size(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 正常提取模式
    url = sys.argv[1]
    timeout = 20
    api_idx = 0
    do_validate = False

    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--timeout" and i + 1 < len(sys.argv):
            timeout = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--api" and i + 1 < len(sys.argv):
            api_idx = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--validate":
            do_validate = True
            i += 1
        else:
            i += 1

    result = asyncio.run(extract_m3u8(url, api_index=api_idx, timeout=timeout))

    if result["success"] and do_validate:
        validation = validate_m3u8_url(result["m3u8_url"])
        result["validation"] = validation

    print(json.dumps(result, ensure_ascii=False))
