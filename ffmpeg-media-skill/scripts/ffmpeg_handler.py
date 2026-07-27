"""
FFmpeg Skill Core Handler
=========================
该模块提供完整的 FFmpeg 多媒体处理能力封装，支持格式转换、音频提取、视频剪辑、
高品质 GIF 制作、分辨率缩放、多视频合并及批量处理等。
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union


class FFmpegSkill:
    """FFmpeg 技能核心处理类"""

    def __init__(self, custom_ffmpeg_path: Optional[str] = None):
        """
        初始化 FFmpegSkill 实例。
        
        :param custom_ffmpeg_path: 可选的 FFmpeg 可执行文件绝对路径或名称
        """
        self.ffmpeg_cmd = self._resolve_ffmpeg_path(custom_ffmpeg_path)

    def _resolve_ffmpeg_path(self, custom_path: Optional[str]) -> str:
        """解析系统中 FFmpeg 可执行文件的实际路径"""
        if custom_path and os.path.isfile(custom_path):
            return custom_path
        
        # 查找系统环境变量中的 ffmpeg
        system_path = shutil.which("ffmpeg")
        if system_path:
            return system_path
        
        # 检查常见 Windows 默认路径
        possible_paths = [
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\tools\ffmpeg\bin\ffmpeg.exe"
        ]
        for path in possible_paths:
            if os.path.isfile(path):
                return path

        return "ffmpeg"  # 默认回退名

    def check_ffmpeg_installed(self) -> Dict[str, Union[bool, str]]:
        """检查系统中是否已正确安装并可用 FFmpeg"""
        try:
            result = subprocess.run(
                [self.ffmpeg_cmd, "-version"],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                first_line = result.stdout.splitlines()[0] if result.stdout else "FFmpeg 已安装"
                return {"installed": True, "version": first_line}
            else:
                return {"installed": False, "error": result.stderr}
        except FileNotFoundError:
            return {
                "installed": False,
                "error": f"未能在路径 '{self.ffmpeg_cmd}' 或系统 PATH 中找到 FFmpeg。请先安装 FFmpeg 并添加至系统环境变量。"
            }

    def _run_command(self, cmd: List[str]) -> Dict[str, Union[bool, str]]:
        """安全执行 FFmpeg 命令行并返回结构化结果"""
        check_res = self.check_ffmpeg_installed()
        if not check_res["installed"]:
            return {"success": False, "error": check_res["error"]}

        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            if process.returncode == 0:
                return {
                    "success": True,
                    "message": "处理完成",
                    "command": " ".join(cmd)
                }
            else:
                return {
                    "success": False,
                    "error": process.stderr or process.stdout,
                    "command": " ".join(cmd)
                }
        except Exception as e:
            return {"success": False, "error": str(e), "command": " ".join(cmd)}

    def convert_format(
        self,
        input_path: str,
        output_path: str,
        video_codec: str = "libx264",
        crf: int = 23,
        preset: str = "medium"
    ) -> Dict[str, Union[bool, str]]:
        """
        基础音视频格式转换。
        
        :param input_path: 输入文件路径
        :param output_path: 输出文件路径
        :param video_codec: 视频编码器 (默认 libx264)
        :param crf: 画质恒定速率因子 (0-51, 越小质量越高，默认 23)
        :param preset: 编码速度预设 (ultrafast, medium, slow 等)
        """
        cmd = [
            self.ffmpeg_cmd, "-y",
            "-i", str(input_path),
            "-c:v", video_codec,
            "-preset", preset,
            "-crf", str(crf),
            str(output_path)
        ]
        return self._run_command(cmd)

    def extract_audio(
        self,
        video_path: str,
        audio_path: str,
        audio_codec: str = "libmp3lame",
        bitrate: str = "192k"
    ) -> Dict[str, Union[bool, str]]:
        """
        从视频中抽取音频轨。
        
        :param video_path: 源视频文件路径
        :param audio_path: 目标音频文件路径
        :param audio_codec: 音频编码器 (例如 libmp3lame, pcm_s16le, aac)
        :param bitrate: 音频比特率 (如 192k, 320k)
        """
        cmd = [
            self.ffmpeg_cmd, "-y",
            "-i", str(video_path),
            "-vn",  # 禁用视频
            "-c:a", audio_codec,
            "-b:a", bitrate,
            str(audio_path)
        ]
        return self._run_command(cmd)

    def resize_video(
        self,
        input_path: str,
        output_path: str,
        width: int = 1280,
        height: int = 720
    ) -> Dict[str, Union[bool, str]]:
        """
        调整视频分辨率。
        
        :param input_path: 源视频路径
        :param output_path: 输出视频路径
        :param width: 目标宽度 (若为 -1 则按比例自适应)
        :param height: 目标高度 (若为 -1 则按比例自适应)
        """
        filter_str = f"scale={width}:{height}"
        cmd = [
            self.ffmpeg_cmd, "-y",
            "-i", str(input_path),
            "-vf", filter_str,
            "-c:v", "libx264",
            "-crf", "23",
            str(output_path)
        ]
        return self._run_command(cmd)

    def clip_video(
        self,
        input_path: str,
        output_path: str,
        start_time: str = "00:00:00",
        duration: Optional[float] = None
    ) -> Dict[str, Union[bool, str]]:
        """
        时间切片裁剪视频。
        
        :param input_path: 输入文件路径
        :param output_path: 输出文件路径
        :param start_time: 开始时间 (格式 "HH:MM:SS" 或秒数)
        :param duration: 截取持续时间 (秒)
        """
        cmd = [self.ffmpeg_cmd, "-y", "-ss", str(start_time), "-i", str(input_path)]
        if duration is not None:
            cmd.extend(["-t", str(duration)])
        cmd.extend(["-c", "copy", str(output_path)])
        return self._run_command(cmd)

    def create_gif(
        self,
        video_path: str,
        gif_path: str,
        start_time: str = "00:00:00",
        duration: float = 5.0,
        fps: int = 12,
        width: int = 480
    ) -> Dict[str, Union[bool, str]]:
        """
        利用 palettegen 和 paletteuse 双路滤镜算法从视频生成高品质 GIF。
        
        :param video_path: 输入视频路径
        :param gif_path: 输出 GIF 路径
        :param start_time: 开始时间
        :param duration: 截取时长 (秒)
        :param fps: GIF 帧率
        :param width: GIF 宽度
        """
        filter_complex = (
            f"[0:v] fps={fps},scale={width}:-1:flags=lanczos,"
            f"split [a][b];[a] palettegen [p];"
            f"[b][p] paletteuse"
        )
        cmd = [
            self.ffmpeg_cmd, "-y",
            "-ss", str(start_time),
            "-t", str(duration),
            "-i", str(video_path),
            "-filter_complex", filter_complex,
            str(gif_path)
        ]
        return self._run_command(cmd)

    def merge_videos(
        self,
        video_list: List[str],
        output_path: str
    ) -> Dict[str, Union[bool, str]]:
        """
        拼接合并多个视频文件 (使用 concat 混解器)。
        
        :param video_list: 待合并的视频文件绝对/相对路径列表
        :param output_path: 输出合并视频路径
        """
        if not video_list:
            return {"success": False, "error": "待合并视频列表为空"}

        concat_txt_path = Path(output_path).parent / "temp_concat_list.txt"
        try:
            with open(concat_txt_path, "w", encoding="utf-8") as f:
                for v_path in video_list:
                    abs_p = Path(v_path).resolve().as_posix()
                    f.write(f"file '{abs_p}'\n")

            cmd = [
                self.ffmpeg_cmd, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_txt_path),
                "-c", "copy",
                str(output_path)
            ]
            result = self._run_command(cmd)
            return result
        finally:
            if concat_txt_path.exists():
                try:
                    os.remove(concat_txt_path)
                except OSError:
                    pass

    def batch_process(
        self,
        input_dir: str,
        output_dir: str,
        operation: str = "convert",
        target_ext: str = "mp4",
        **kwargs
    ) -> Dict[str, Union[bool, int, List[str]]]:
        """
        批量处理指定目录下的音视频文件。
        
        :param input_dir: 输入文件夹
        :param output_dir: 输出文件夹
        :param operation: 操作类型 ('convert', 'resize', 'extract_audio')
        :param target_ext: 目标文件扩展名 (如 'mp4', 'mp3', 'gif')
        """
        in_path = Path(input_dir)
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        supported_exts = {".mp4", ".avi", ".mov", ".mkv", ".flv", ".webm", ".mp3", ".wav"}
        processed_files = []
        failed_files = []

        for item in in_path.iterdir():
            if item.is_file() and item.suffix.lower() in supported_exts:
                dest_file = out_path / f"processed_{item.stem}.{target_ext.lstrip('.')}"
                if operation == "convert":
                    res = self.convert_format(str(item), str(dest_file), **kwargs)
                elif operation == "extract_audio":
                    res = self.extract_audio(str(item), str(dest_file), **kwargs)
                elif operation == "resize":
                    res = self.resize_video(str(item), str(dest_file), **kwargs)
                else:
                    res = {"success": False, "error": f"不支持的批量操作类型: {operation}"}

                if res.get("success"):
                    processed_files.append(str(dest_file))
                else:
                    failed_files.append(str(item))

        return {
            "success": len(failed_files) == 0,
            "processed_count": len(processed_files),
            "failed_count": len(failed_files),
            "processed_files": processed_files,
            "failed_files": failed_files
        }
