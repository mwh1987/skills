# -*- coding: utf-8 -*-
"""
视频下载工具 - 使用 N_m3u8DL-CLI 下载m3u8视频
支持批量下载、自动重试、真实分辨率/编码提取、进度汇总

增强功能:
  - 下载前磁盘空间检查
  - 下载进度实时监控
  - 断点续传支持
  - 流水线批量下载
  - OVA/特别篇命名规则

用法:
  python video_downloader.py <m3u8_url> --name "影片名" --episode 1 --output "D:\\Videos"
  python video_downloader.py --batch batch_config.json --output "D:\\Videos"
  python video_downloader.py --disk-check "D:\\Downloads\\Videos" --need-size 5000

命名规则（影视资源通用命名）:
  影片名.S01E01.1080p.WEB-DL.H264.mp4         (电视剧)
  影片名.2024.1080p.WEB-DL.H264.mp4           (电影)
  影片名.S00E01.1080p.WEB-DL.H264.mp4         (OVA/特别篇)
  影片名.SP01.1080p.WEB-DL.H264.mp4           (SP特别篇)
  影片名.S00E01-OVA1.1080p.WEB-DL.H264.mp4   (多OVA)
"""

import os
import sys
import json
import subprocess
import re
import argparse
import time
import shutil
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Thread
from queue import Queue

# N_m3u8DL 工具路径
N_M3U8DL_CLI = r"D:\App\N_m3u8DL-CLI_v3.0.2_with_ffmpeg_and_SimpleG\N_m3u8DL-CLI_v3.0.2.exe"
N_M3U8DL_RE = r"D:\App\N_m3u8DL-CLI\N_m3u8DL-RE.exe"
FFMPEG_PATH = r"D:\App\N_m3u8DL-CLI_v3.0.2_with_ffmpeg_and_SimpleG\ffmpeg.exe"

# 默认下载目录
DEFAULT_DOWNLOAD_DIR = r"D:\Downloads\Videos"

# 临时文件目录（断点续传用）
TEMP_DIR_NAME = ".m3u8dl_temp"


# ─── 磁盘空间检查 ────────────────────────────────────────

def check_disk_space(output_dir: str, needed_mb: float = 0) -> dict:
    """
    检查目标磁盘的可用空间

    参数:
        output_dir:  输出目录路径
        needed_mb:   需要的空间(MB)，0表示只查询

    返回:
        dict: { drive, free_gb, needed_gb, sufficient, message }
    """
    # 获取目标驱动器
    drive = os.path.splitdrive(os.path.abspath(output_dir))[0]
    if not drive:
        drive = "C:"

    try:
        usage = shutil.disk_usage(drive)
        free_gb = round(usage.free / (1024 ** 3), 2)
        needed_gb = round(needed_mb / 1024, 2) if needed_mb > 0 else 0

        sufficient = True
        message = f"磁盘 {drive} 可用 {free_gb:.1f}GB"
        if needed_mb > 0:
            sufficient = usage.free >= (needed_mb * 1024 * 1024)
            if sufficient:
                # 建议预留10%空间
                safe_needed = needed_mb * 1.1
                if usage.free < safe_needed * 1024 * 1024:
                    message += f"，但下载{needed_gb:.1f}GB后剩余空间不足10%，建议清理磁盘"
                else:
                    message += f"，下载{needed_gb:.1f}GB后空间充足"
            else:
                message += f"，不足以下载{needed_gb:.1f}GB的内容"

        return {
            "drive": drive,
            "free_bytes": usage.free,
            "free_gb": free_gb,
            "needed_gb": needed_gb,
            "sufficient": sufficient,
            "message": message,
        }
    except Exception as e:
        return {
            "drive": drive,
            "free_gb": 0,
            "needed_gb": round(needed_mb / 1024, 2) if needed_mb > 0 else 0,
            "sufficient": False,
            "message": f"无法检查磁盘空间: {e}",
        }


def estimate_batch_size(episode_count: int, avg_episode_mb: float = 400) -> float:
    """
    估算批量下载所需空间

    参数:
        episode_count:  集数
        avg_episode_mb: 每集平均大小(MB)，默认400MB(1080p约40分钟)

    返回:
        float: 预估总大小(MB)
    """
    return episode_count * avg_episode_mb


# ─── 下载进度监控 ─────────────────────────────────────────

class DownloadProgressMonitor:
    """
    监控N_m3u8DL-CLI的下载进度

    通过解析控制台输出来跟踪下载进度:
      N_m3u8DL-CLI v3 输出格式:
        [下载] 1/128  →  [下载] 128/128
      或百分比形式:
        1.2% ... 50.3% ... 100%
    """

    def __init__(self):
        self.progress = 0.0        # 0.0 ~ 100.0
        self.current_ts = 0        # 已下载TS分段数
        self.total_ts = 0          # 总TS分段数
        self.speed = ""            # 下载速度
        self.status = "pending"    # pending/downloading/merging/done/error

    def parse_line(self, line: str):
        """解析N_m3u8DL的一行输出"""
        line = line.strip()

        # 匹配 "N/M" 格式的分段进度
        seg_match = re.search(r'\[(?:下载|download)\]\s*(\d+)/(\d+)', line, re.IGNORECASE)
        if seg_match:
            self.current_ts = int(seg_match.group(1))
            self.total_ts = int(seg_match.group(2))
            if self.total_ts > 0:
                self.progress = round(self.current_ts / self.total_ts * 100, 1)
            self.status = "downloading"
            return

        # 匹配百分比格式
        pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%', line)
        if pct_match:
            self.progress = float(pct_match.group(1))
            self.status = "downloading"
            return

        # 匹配合并阶段
        if any(kw in line.lower() for kw in ['合并', 'merge', 'mux']):
            self.progress = 100.0
            self.status = "merging"
            return

        # 匹配完成
        if any(kw in line.lower() for kw in ['完成', 'done', 'success']):
            self.progress = 100.0
            self.status = "done"
            return

        # 匹配速度信息
        speed_match = re.search(r'(\d+(?:\.\d+)?)\s*(MB/s|KB/s|Mbit/s|Kbit/s)', line)
        if speed_match:
            self.speed = speed_match.group(0)

    def get_summary(self) -> dict:
        """获取当前进度摘要"""
        return {
            "progress": self.progress,
            "current_ts": self.current_ts,
            "total_ts": self.total_ts,
            "speed": self.speed,
            "status": self.status,
        }


def download_with_progress_monitor(m3u8_url: str, save_dir: str, save_name: str,
                                    max_threads: int = 32, headers: str = None,
                                    validate_first: bool = True,
                                    progress_callback=None) -> dict:
    """
    使用 N_m3u8DL-CLI 下载，带实时进度监控

    参数:
        progress_callback: 回调函数 callback(progress_dict)
    """
    exe = N_M3U8DL_CLI
    if not os.path.exists(exe):
        return {"success": False, "error": f"未找到N_m3u8DL-CLI: {exe}"}

    # 验证m3u8链接
    if validate_first:
        validation = validate_m3u8_url(m3u8_url)
        if not validation["valid"]:
            return {
                "success": False,
                "error": f"m3u8链接不可用: {validation.get('error', 'unknown')}",
                "validation": validation
            }

    cmd = [
        exe,
        m3u8_url,
        "--workDir", save_dir,
        "--saveName", save_name,
        "--enableMuxFastStart",
        "--enableDelAfterDone",
        "--maxThreads", str(max_threads),
    ]

    if headers:
        cmd.extend(["--headers", headers])

    monitor = DownloadProgressMonitor()

    try:
        # 使用Popen实时读取输出
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace',
            bufsize=1
        )

        output_lines = []
        for line in process.stdout:
            output_lines.append(line)
            monitor.parse_line(line)

            # 每5%或每10秒汇报一次
            if progress_callback:
                progress_callback(monitor.get_summary())

        process.wait(timeout=60)
        full_output = ''.join(output_lines)

        # 从输出提取分辨率/编码
        metadata = parse_resolution_from_output(full_output)

        # 检查输出文件
        output_file = None
        for ext in ['.mp4', '.mkv', '.ts']:
            candidate = os.path.join(save_dir, save_name + ext)
            if os.path.exists(candidate):
                output_file = candidate
                break

        if output_file:
            fsize = os.path.getsize(output_file)

            # 如果从N_m3u8DL输出无法提取分辨率，用ffmpeg检测
            if not metadata.get("resolution_label"):
                probe_meta = probe_video_file(output_file)
                if probe_meta.get("resolution_label"):
                    metadata["resolution_label"] = probe_meta["resolution_label"]
                    metadata["width"] = probe_meta["width"]
                    metadata["height"] = probe_meta["height"]
                if probe_meta.get("codec_label") and not metadata.get("codec_label"):
                    metadata["codec_label"] = probe_meta["codec_label"]
                metadata["detected"] = metadata.get("resolution_label") is not None or metadata.get("codec_label") is not None

            return {
                "success": True,
                "file": output_file,
                "size_mb": round(fsize / 1024 / 1024, 1),
                "metadata": metadata,
                "progress": monitor.get_summary(),
                "output": full_output[-500:] if len(full_output) > 500 else full_output
            }
        else:
            return {
                "success": False,
                "error": "下载完成但未找到输出文件",
                "metadata": metadata,
                "progress": monitor.get_summary(),
                "output": full_output[-500:] if len(full_output) > 500 else full_output
            }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "下载超时(30分钟)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 链接验证 ───────────────────────────────────────────

def validate_m3u8_url(m3u8_url: str, timeout: int = 10) -> dict:
    """验证m3u8链接是否仍可用"""
    try:
        resp = requests.head(m3u8_url, timeout=timeout, allow_redirects=True)
        if resp.status_code == 200:
            return {"valid": True, "status_code": 200}
        else:
            return {"valid": False, "status_code": resp.status_code,
                    "error": f"HTTP {resp.status_code}"}
    except requests.RequestException as e:
        return {"valid": False, "status_code": None, "error": str(e)}


# ─── 元数据解析 ─────────────────────────────────────────

def parse_resolution_from_output(output: str) -> dict:
    """
    从N_m3u8DL-CLI输出中提取分辨率和编码
    """
    width, height = 0, 0
    codec = None

    res_match = re.search(r'分辨率[：:]\s*(\d+)\s*x\s*(\d+)', output)
    if res_match:
        width, height = int(res_match.group(1)), int(res_match.group(2))

    if 'H265' in output or 'HEVC' in output or 'hvc1' in output:
        codec = "H265"
    elif 'AV1' in output or 'av01' in output:
        codec = "AV1"
    elif 'H264' in output or 'AVC' in output or 'avc1' in output:
        codec = "H264"

    res_label = None
    codec_label = None

    if height > 0 or width > 0:
        if height >= 2160 or width >= 3840:
            res_label = "2160p"
        elif height >= 1080 or width >= 1920:
            res_label = "1080p"
        elif height >= 720 or width >= 1280:
            res_label = "720p"
        else:
            res_label = "480p"

    if codec:
        codec_label = codec

    return {
        "resolution_label": res_label,
        "codec_label": codec_label,
        "width": width,
        "height": height,
        "detected": res_label is not None or codec_label is not None,
    }


def parse_codec_from_m3u8(m3u8_url: str) -> str:
    """从m3u8文件内容中解析编码信息"""
    try:
        resp = requests.get(m3u8_url, timeout=10)
        if resp.status_code == 200:
            content = resp.text.upper()
            codecs_match = re.search(r'CODECS="([^"]+)"', content, re.IGNORECASE)
            if codecs_match:
                codecs_str = codecs_match.group(1).upper()
                if "AV01" in codecs_str:
                    return "AV1"
                elif "HEV" in codecs_str or "HVC" in codecs_str:
                    return "H265"
                elif "AVC" in codecs_str:
                    return "H264"
    except Exception:
        pass
    return "H264"


def probe_video_file(file_path: str) -> dict:
    """
    使用ffmpeg检测已下载视频文件的分辨率和编码
    """
    if not os.path.exists(FFMPEG_PATH):
        return {"resolution_label": None, "codec_label": None, "width": 0, "height": 0}

    try:
        cmd = [FFMPEG_PATH, "-i", file_path, "-hide_banner"]
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=30, encoding='utf-8', errors='replace'
        )
        output = result.stderr

        res_match = re.search(r'(\d{3,4})x(\d{3,4})', output)
        width, height = 0, 0
        if res_match:
            width, height = int(res_match.group(1)), int(res_match.group(2))

        codec_label = None
        codec_match = re.search(r'Video:\s*(\S+)', output)
        if codec_match:
            codec_name = codec_match.group(1).lower()
            if codec_name in ("hevc", "h265", "libx265"):
                codec_label = "H265"
            elif codec_name in ("av1", "libaom-av1", "libsvtav1"):
                codec_label = "AV1"
            elif codec_name in ("h264", "avc", "libx264"):
                codec_label = "H264"

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
            "codec_label": codec_label,
            "width": width,
            "height": height,
        }
    except Exception:
        return {"resolution_label": None, "codec_label": None, "width": 0, "height": 0}


# ─── 断点续传支持 ─────────────────────────────────────────

def find_partial_download(save_dir: str, save_name: str) -> dict:
    """
    查找是否存在部分下载（断点续传）

    N_m3u8DL-CLI的临时文件存储在 --workDir 下的临时目录中。
    如果发现未完成的下载，可以继续。

    参数:
        save_dir:  保存目录
        save_name: 保存文件名(不含扩展名)

    返回:
        dict: { has_partial, temp_dir, partial_files, can_resume }
    """
    temp_dir = os.path.join(save_dir, TEMP_DIR_NAME)

    if not os.path.exists(temp_dir):
        # 检查其他可能的临时目录命名
        for item in os.listdir(save_dir):
            item_path = os.path.join(save_dir, item)
            if os.path.isdir(item_path) and save_name in item and item != save_name + ".mp4":
                temp_dir = item_path
                break

    if not os.path.exists(temp_dir):
        return {"has_partial": False, "temp_dir": None, "partial_files": [], "can_resume": False}

    # 统计临时文件
    partial_files = []
    for root, dirs, files in os.walk(temp_dir):
        for f in files:
            if f.endswith(('.ts', '.tmp', '.part')):
                partial_files.append(os.path.join(root, f))

    # 也检查目标目录下是否有部分mp4
    for ext in ['.mp4', '.mkv', '.ts']:
        target = os.path.join(save_dir, save_name + ext)
        if os.path.exists(target):
            fsize = os.path.getsize(target)
            # 小于1MB的mp4可能是上次合并失败的残留
            if fsize < 1024 * 1024:
                partial_files.append(target)

    can_resume = len(partial_files) > 0

    return {
        "has_partial": True,
        "temp_dir": temp_dir,
        "partial_files": partial_files,
        "partial_count": len(partial_files),
        "can_resume": can_resume,
    }


def clean_partial_download(save_dir: str, save_name: str) -> bool:
    """
    清理部分下载的临时文件，从头重新下载

    返回:
        bool: 是否成功清理
    """
    info = find_partial_download(save_dir, save_name)

    try:
        # 删除临时目录
        if info["temp_dir"] and os.path.exists(info["temp_dir"]):
            shutil.rmtree(info["temp_dir"], ignore_errors=True)

        # 删除残留的小文件
        for f in info.get("partial_files", []):
            if os.path.exists(f) and os.path.getsize(f) < 1024 * 1024:
                try:
                    os.remove(f)
                except Exception:
                    pass

        return True
    except Exception:
        return False


# ─── 文件名生成（含OVA/SP命名） ──────────────────────────

def generate_filename(title: str, episode: str = None, season: str = None,
                      year: str = None, resolution: str = "1080p",
                      source: str = "WEB-DL", codec: str = "H264",
                      ext: str = "mp4", content_type: str = "episode",
                      ova_number: str = None, sp_number: str = None) -> str:
    """
    生成影视资源通用命名格式的文件名

    电视剧:   片名.S01E03.1080p.WEB-DL.H264.mp4
    电影:     片名.2024.1080p.WEB-DL.H264.mp4
    OVA:      片名.S00E01.1080p.WEB-DL.H264.mp4  (content_type="ova")
    多OVA:    片名.S00E01-OVA1.1080p.WEB-DL.H264.mp4  (ova_number="1")
    SP特别篇: 片名.SP01.1080p.WEB-DL.H264.mp4  (content_type="sp")
    番外:     片名.S00E01-番外.1080p.WEB-DL.H264.mp4  (content_type="extra")

    参数:
        content_type: "episode"(常规剧集), "ova", "sp", "extra", "movie"
        ova_number:   OVA序号（当有多部OVA时）
        sp_number:    SP序号
    """
    # 清理标题中的非法文件名字符
    title = re.sub(r'[<>:"/\\|?*]', '', title).strip()
    title = re.sub(r'\s+', '.', title)

    parts = [title]

    if content_type == "sp":
        # SP特别篇: 片名.SP01.1080p.WEB-DL.H264.mp4
        sp_num = sp_number or "1"
        parts.append(f"SP{int(sp_num):02d}")
    elif content_type == "ova":
        # OVA: 片名.S00E01-OVA1.1080p.WEB-DL.H264.mp4
        ep_suffix = ""
        if ova_number:
            ep_suffix = f"-OVA{ova_number}"
        if episode:
            parts.append(f"S00E{int(episode):02d}{ep_suffix}")
        else:
            parts.append(f"S00E01{ep_suffix}")
    elif content_type == "extra":
        # 番外: 片名.S00E01-番外.1080p.WEB-DL.H264.mp4
        if episode:
            parts.append(f"S00E{int(episode):02d}-番外")
        else:
            parts.append("S00E01-番外")
    elif episode and content_type == "episode":
        # 常规电视剧集
        if season:
            parts.append(f"S{int(season):02d}E{int(episode):02d}")
        else:
            parts.append(f"E{int(episode):02d}")
    elif year:
        parts.append(str(year))

    if resolution:
        parts.append(resolution)
    if source:
        parts.append(source)
    if codec:
        parts.append(codec)

    filename = ".".join(parts) + f".{ext}"
    return filename


# ─── 单集下载 ─────────────────────────────────────────────

def download_with_cli(m3u8_url: str, save_dir: str, save_name: str,
                      max_threads: int = 32, headers: str = None,
                      validate_first: bool = True) -> dict:
    """
    使用 N_m3u8DL-CLI (v3.0.2 .NET版) 下载

    参数:
        m3u8_url:       m3u8链接
        save_dir:       保存目录
        save_name:      保存文件名(不含扩展名)
        max_threads:    最大线程数
        headers:        自定义请求头
        validate_first: 是否先验证链接可用性
    """
    exe = N_M3U8DL_CLI
    if not os.path.exists(exe):
        return {"success": False, "error": f"未找到N_m3u8DL-CLI: {exe}"}

    # 验证m3u8链接
    if validate_first:
        validation = validate_m3u8_url(m3u8_url)
        if not validation["valid"]:
            return {
                "success": False,
                "error": f"m3u8链接不可用: {validation.get('error', 'unknown')}",
                "validation": validation
            }

    cmd = [
        exe,
        m3u8_url,
        "--workDir", save_dir,
        "--saveName", save_name,
        "--enableMuxFastStart",
        "--enableDelAfterDone",
        "--maxThreads", str(max_threads),
    ]

    if headers:
        cmd.extend(["--headers", headers])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=1800, encoding='utf-8', errors='replace'
        )
        output = result.stdout + result.stderr

        metadata = parse_resolution_from_output(output)

        output_file = None
        for ext in ['.mp4', '.mkv', '.ts']:
            candidate = os.path.join(save_dir, save_name + ext)
            if os.path.exists(candidate):
                output_file = candidate
                break

        if output_file:
            fsize = os.path.getsize(output_file)

            if not metadata.get("resolution_label"):
                probe_meta = probe_video_file(output_file)
                if probe_meta.get("resolution_label"):
                    metadata["resolution_label"] = probe_meta["resolution_label"]
                    metadata["width"] = probe_meta["width"]
                    metadata["height"] = probe_meta["height"]
                if probe_meta.get("codec_label") and not metadata.get("codec_label"):
                    metadata["codec_label"] = probe_meta["codec_label"]
                metadata["detected"] = metadata.get("resolution_label") is not None or metadata.get("codec_label") is not None

            return {
                "success": True,
                "file": output_file,
                "size_mb": round(fsize / 1024 / 1024, 1),
                "metadata": metadata,
                "output": output[-500:] if len(output) > 500 else output
            }
        else:
            return {
                "success": False,
                "error": "下载完成但未找到输出文件",
                "metadata": metadata,
                "output": output[-500:] if len(output) > 500 else output
            }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "下载超时(30分钟)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def download_with_re(m3u8_url: str, save_dir: str, save_name: str,
                     thread_count: int = 4) -> dict:
    """使用 N_m3u8DL-RE (Rust版) 下载"""
    exe = N_M3U8DL_RE
    if not os.path.exists(exe):
        return {"success": False, "error": f"未找到N_m3u8DL-RE: {exe}"}

    cmd = [
        exe,
        m3u8_url,
        "--save-dir", save_dir,
        "--save-name", save_name,
        "--thread-count", str(thread_count),
        "--del-after-done",
        "--auto-select",
    ]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=1800, encoding='utf-8', errors='replace'
        )
        output = result.stdout + result.stderr

        metadata = parse_resolution_from_output(output)

        output_file = None
        for ext in ['.mp4', '.mkv', '.ts']:
            candidate = os.path.join(save_dir, save_name + ext)
            if os.path.exists(candidate):
                output_file = candidate
                break

        if output_file:
            fsize = os.path.getsize(output_file)

            if not metadata.get("resolution_label"):
                probe_meta = probe_video_file(output_file)
                if probe_meta.get("resolution_label"):
                    metadata["resolution_label"] = probe_meta["resolution_label"]
                    metadata["width"] = probe_meta["width"]
                    metadata["height"] = probe_meta["height"]
                if probe_meta.get("codec_label") and not metadata.get("codec_label"):
                    metadata["codec_label"] = probe_meta["codec_label"]
                metadata["detected"] = metadata.get("resolution_label") is not None or metadata.get("codec_label") is not None

            return {
                "success": True,
                "file": output_file,
                "size_mb": round(fsize / 1024 / 1024, 1),
                "metadata": metadata,
                "output": output[-500:] if len(output) > 500 else output
            }
        else:
            return {
                "success": False,
                "error": "下载完成但未找到输出文件",
                "metadata": metadata,
                "output": output[-500:] if len(output) > 500 else output
            }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "下载超时(30分钟)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── 主下载入口 ───────────────────────────────────────────

def download_video(m3u8_url: str, title: str, episode: str = None,
                   season: str = None, year: str = None,
                   resolution: str = "1080p", source: str = "WEB-DL",
                   codec: str = "H264", output_dir: str = None,
                   use_re: bool = False, validate_first: bool = True,
                   retry: int = 1, content_type: str = "episode",
                   ova_number: str = None, sp_number: str = None,
                   progress_callback=None, resume: bool = True) -> dict:
    """
    下载视频的主入口

    新增参数:
        content_type:     内容类型 "episode"/"ova"/"sp"/"extra"/"movie"
        ova_number:       OVA序号(多OVA时使用)
        sp_number:        SP序号
        progress_callback: 进度回调
        resume:           是否尝试断点续传
    """
    # 影片名文件夹
    folder_name = re.sub(r'[<>:"/\\|?*]', '', title).strip()
    if output_dir is None:
        output_dir = DEFAULT_DOWNLOAD_DIR
    save_dir = os.path.join(output_dir, folder_name)
    os.makedirs(save_dir, exist_ok=True)

    # 尝试从m3u8内容检测编码
    detected_codec = parse_codec_from_m3u8(m3u8_url)
    if detected_codec != "H264":
        codec = detected_codec

    # 生成文件名
    save_name = generate_filename(
        title=title, episode=episode, season=season,
        year=year, resolution=resolution, source=source,
        codec=codec, ext="mp4", content_type=content_type,
        ova_number=ova_number, sp_number=sp_number
    )
    save_name_no_ext = os.path.splitext(save_name)[0]

    # 断点续传检查
    if resume:
        partial = find_partial_download(save_dir, save_name_no_ext)
        if partial["can_resume"]:
            # 有可续传的部分，直接继续下载
            # N_m3u8DL-CLI会自动处理temp目录中的残留
            pass
        elif partial["has_partial"]:
            # 有残留但不可续传，清理后重新下载
            clean_partial_download(save_dir, save_name_no_ext)

    # 检查是否已存在完成的文件
    for ext in ['.mp4', '.mkv']:
        existing = os.path.join(save_dir, save_name_no_ext + ext)
        if os.path.exists(existing):
            fsize = os.path.getsize(existing)
            if fsize > 1024 * 1024:  # 大于1MB视为有效文件
                return {
                    "success": True,
                    "file": existing,
                    "size_mb": round(fsize / 1024 / 1024, 1),
                    "filename": save_name,
                    "save_dir": save_dir,
                    "metadata": probe_video_file(existing),
                    "skipped": True,
                    "message": "文件已存在，跳过下载",
                }

    # 下载（含重试）
    last_result = None
    for attempt in range(retry + 1):
        if use_re:
            result = download_with_re(m3u8_url, save_dir, save_name_no_ext)
        elif progress_callback:
            result = download_with_progress_monitor(
                m3u8_url, save_dir, save_name_no_ext,
                validate_first=validate_first,
                progress_callback=progress_callback
            )
        else:
            result = download_with_cli(
                m3u8_url, save_dir, save_name_no_ext,
                validate_first=validate_first
            )

        if result["success"]:
            if "metadata" in result and result["metadata"]:
                meta = result["metadata"]
                actual_res = meta.get("resolution_label") or resolution
                actual_codec = meta.get("codec_label") or codec

                if actual_res != resolution or actual_codec != codec:
                    new_name = generate_filename(
                        title=title, episode=episode, season=season,
                        year=year, resolution=actual_res, source=source,
                        codec=actual_codec, ext="mp4", content_type=content_type,
                        ova_number=ova_number, sp_number=sp_number
                    )
                    new_name_no_ext = os.path.splitext(new_name)[0]

                    old_file = result["file"]
                    new_file = os.path.join(save_dir, new_name_no_ext + ".mp4")

                    if old_file != new_file and os.path.exists(old_file):
                        try:
                            os.rename(old_file, new_file)
                            result["file"] = new_file
                            save_name = new_name
                        except OSError:
                            pass

                    resolution = actual_res
                    codec = actual_codec

            result["filename"] = save_name
            result["save_dir"] = save_dir
            return result

        last_result = result
        if attempt < retry:
            print(f"  重试 {attempt + 1}/{retry}...", file=sys.stderr)
            time.sleep(2)

    last_result["filename"] = save_name
    last_result["save_dir"] = save_dir
    return last_result


# ─── 批量下载（含流水线模式） ─────────────────────────────

def batch_download(episode_list: list, title: str, season: str = "1",
                   output_dir: str = None, max_workers: int = 1,
                   retry: int = 1, pipeline: bool = False,
                   m3u8_extractor_func=None,
                   progress_callback=None,
                   check_disk: bool = True) -> dict:
    """
    批量下载多集视频

    增强功能:
      - 下载前磁盘空间检查
      - 流水线模式：边下载当前集，边提取下一集的m3u8
      - 跳过已存在的文件
      - 实时进度汇报

    参数:
        episode_list:       列表，每项 { episode, m3u8_url, [year], [content_type], [ova_number], [sp_number] }
        title:              影片名称
        season:             季数
        output_dir:         输出根目录
        max_workers:        并发数（建议1）
        retry:              单集重试次数
        pipeline:           是否启用流水线模式
        m3u8_extractor_func: 流水线模式下的m3u8提取函数 callback(video_url) -> m3u8_url
        progress_callback:   总进度回调 callback(batch_progress_dict)
        check_disk:          是否检查磁盘空间

    返回:
        dict: { total, success, failed, results, total_size_mb, skipped }
    """
    # 磁盘空间检查
    if check_disk:
        estimated_size = estimate_batch_size(len(episode_list))
        disk_info = check_disk_space(output_dir or DEFAULT_DOWNLOAD_DIR, estimated_size)
        if not disk_info["sufficient"]:
            return {
                "total": len(episode_list),
                "success": 0,
                "failed": 0,
                "skipped": 0,
                "total_size_mb": 0,
                "results": [],
                "disk_warning": disk_info["message"],
                "error": f"磁盘空间不足: {disk_info['message']}",
            }

    results = []
    total_size = 0
    skipped_count = 0
    total_episodes = len(episode_list)

    if pipeline and m3u8_extractor_func:
        # ── 流水线模式 ──
        # 预提取第一集的m3u8
        next_m3u8_cache = {}
        ep0 = episode_list[0]
        if not ep0.get("m3u8_url"):
            cached = m3u8_extractor_func(ep0.get("video_url", ""))
            if cached:
                next_m3u8_cache[0] = cached

        for i, ep_info in enumerate(episode_list):
            ep_num = ep_info.get("episode", "?")
            content_type = ep_info.get("content_type", "episode")

            # 使用缓存的m3u8或列表中的m3u8
            m3u8_url = next_m3u8_cache.get(i, ep_info.get("m3u8_url", ""))

            # 验证m3u8链接
            if m3u8_url:
                validation = validate_m3u8_url(m3u8_url)
                if not validation["valid"]:
                    # 重新提取
                    video_url = ep_info.get("video_url", "")
                    if video_url and m3u8_extractor_func:
                        m3u8_url = m3u8_extractor_func(video_url) or m3u8_url

            # 边下载当前集，边提取下一集的m3u8
            next_m3u8_future = None
            if i + 1 < total_episodes and m3u8_extractor_func:
                next_ep = episode_list[i + 1]
                if not next_ep.get("m3u8_url"):
                    next_video_url = next_ep.get("video_url", "")
                    if next_video_url:
                        # 在另一个线程中提取下一集m3u8
                        def _extract(url):
                            return m3u8_extractor_func(url)
                        import threading
                        result_holder = [None]
                        def _worker(url, holder):
                            holder[0] = m3u8_extractor_func(url)
                        t = threading.Thread(target=_worker, args=(next_video_url, result_holder))
                        t.start()
                        next_m3u8_future = (t, result_holder)

            print(f"下载第{ep_num}集 ({i+1}/{total_episodes})...", file=sys.stderr)

            # 下载当前集
            result = download_video(
                m3u8_url=m3u8_url,
                title=title,
                episode=str(ep_num),
                season=season,
                year=ep_info.get("year"),
                output_dir=output_dir,
                retry=retry,
                content_type=content_type,
                ova_number=ep_info.get("ova_number"),
                sp_number=ep_info.get("sp_number"),
            )

            results.append({
                "episode": ep_num,
                "success": result.get("success", False),
                "file": result.get("file"),
                "size_mb": result.get("size_mb", 0),
                "skipped": result.get("skipped", False),
                "error": result.get("error"),
            })

            if result.get("success") and not result.get("skipped"):
                total_size += result.get("size_mb", 0)
            if result.get("skipped"):
                skipped_count += 1

            # 等待下一集m3u8提取完成
            if next_m3u8_future:
                t, holder = next_m3u8_future
                t.join(timeout=60)
                if holder[0]:
                    next_m3u8_cache[i + 1] = holder[0]

            # 进度回调
            if progress_callback:
                progress_callback({
                    "completed": i + 1,
                    "total": total_episodes,
                    "current_episode": ep_num,
                    "total_size_mb": round(total_size, 1),
                })
    else:
        # ── 串行模式（默认） ──
        for i, ep_info in enumerate(episode_list):
            ep_num = ep_info.get("episode", "?")
            m3u8_url = ep_info.get("m3u8_url", "")
            content_type = ep_info.get("content_type", "episode")

            print(f"下载第{ep_num}集 ({i+1}/{total_episodes})...", file=sys.stderr)

            result = download_video(
                m3u8_url=m3u8_url,
                title=title,
                episode=str(ep_num),
                season=season,
                year=ep_info.get("year"),
                output_dir=output_dir,
                retry=retry,
                content_type=content_type,
                ova_number=ep_info.get("ova_number"),
                sp_number=ep_info.get("sp_number"),
            )

            results.append({
                "episode": ep_num,
                "success": result.get("success", False),
                "file": result.get("file"),
                "size_mb": result.get("size_mb", 0),
                "skipped": result.get("skipped", False),
                "error": result.get("error"),
            })

            if result.get("success") and not result.get("skipped"):
                total_size += result.get("size_mb", 0)
            if result.get("skipped"):
                skipped_count += 1

            # 进度回调
            if progress_callback:
                progress_callback({
                    "completed": i + 1,
                    "total": total_episodes,
                    "current_episode": ep_num,
                    "total_size_mb": round(total_size, 1),
                })

    success_count = sum(1 for r in results if r["success"])
    failed_count = len(results) - success_count

    return {
        "total": len(results),
        "success": success_count,
        "failed": failed_count,
        "skipped": skipped_count,
        "total_size_mb": round(total_size, 1),
        "results": results,
    }


# ─── 命令行入口 ───────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="视频下载工具")
    parser.add_argument("m3u8_url", nargs="?", help="m3u8链接")
    parser.add_argument("--name", help="影片名称")
    parser.add_argument("--episode", help="集数")
    parser.add_argument("--season", help="季数")
    parser.add_argument("--year", help="年份(电影)")
    parser.add_argument("--resolution", default="1080p", help="分辨率(可被自动覆盖)")
    parser.add_argument("--source", default="WEB-DL", help="来源标识")
    parser.add_argument("--codec", default="H264", help="编码(可被自动覆盖)")
    parser.add_argument("--output", default=DEFAULT_DOWNLOAD_DIR, help="输出目录")
    parser.add_argument("--use-re", action="store_true", help="使用Rust版下载器")
    parser.add_argument("--validate", action="store_true", help="下载前验证m3u8链接")
    parser.add_argument("--retry", type=int, default=1, help="失败重试次数")
    parser.add_argument("--batch", help="批量下载配置文件(JSON)")
    parser.add_argument("--content-type", default="episode",
                        choices=["episode", "ova", "sp", "extra", "movie"],
                        help="内容类型")
    parser.add_argument("--ova-number", help="OVA序号")
    parser.add_argument("--sp-number", help="SP序号")
    parser.add_argument("--disk-check", nargs="?", const="check",
                        help="检查磁盘空间，可指定路径或使用默认")
    parser.add_argument("--need-size", type=float, default=0,
                        help="磁盘检查时指定所需空间(MB)")
    parser.add_argument("--no-resume", action="store_true",
                        help="不禁用断点续传")

    args = parser.parse_args()

    # 磁盘空间检查模式
    if args.disk_check:
        target_dir = args.disk_check if args.disk_check != "check" else args.output
        disk_info = check_disk_space(target_dir, args.need_size)
        print(json.dumps(disk_info, ensure_ascii=False, indent=2))
        sys.exit(0)

    # 批量下载模式
    if args.batch:
        if not os.path.exists(args.batch):
            print(json.dumps({"success": False, "error": f"配置文件不存在: {args.batch}"}, ensure_ascii=False))
            sys.exit(1)
        with open(args.batch, "r", encoding="utf-8") as f:
            batch_config = json.load(f)

        result = batch_download(
            episode_list=batch_config.get("episodes", []),
            title=batch_config.get("title", "未知"),
            season=batch_config.get("season", "1"),
            output_dir=args.output,
            retry=args.retry,
            check_disk=True,
        )
        try:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except UnicodeEncodeError:
            print(json.dumps(result, ensure_ascii=True, indent=2))
        sys.exit(0)

    # 单集下载模式
    if not args.m3u8_url:
        print(json.dumps({"success": False, "error": "请提供m3u8链接或--batch配置文件"}, ensure_ascii=False))
        sys.exit(1)

    result = download_video(
        m3u8_url=args.m3u8_url,
        title=args.name or "未知",
        episode=args.episode,
        season=args.season,
        year=args.year,
        resolution=args.resolution,
        source=args.source,
        codec=args.codec,
        output_dir=args.output,
        use_re=args.use_re,
        validate_first=args.validate,
        retry=args.retry,
        content_type=args.content_type,
        ova_number=args.ova_number,
        sp_number=args.sp_number,
        resume=not args.no_resume,
    )
    try:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except UnicodeEncodeError:
        print(json.dumps(result, ensure_ascii=True, indent=2))
