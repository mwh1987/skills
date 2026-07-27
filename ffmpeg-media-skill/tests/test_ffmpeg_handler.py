"""
FFmpegSkill Handler 单元测试
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# 将项目根目录加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.ffmpeg_handler import FFmpegSkill


class TestFFmpegSkill(unittest.TestCase):

    def setUp(self):
        self.skill = FFmpegSkill(custom_ffmpeg_path="ffmpeg")

    @patch("scripts.ffmpeg_handler.subprocess.run")
    def test_check_ffmpeg_installed_success(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ffmpeg version 6.0", stderr="")
        res = self.skill.check_ffmpeg_installed()
        self.assertTrue(res["installed"])
        self.assertIn("ffmpeg version 6.0", res["version"])

    @patch("scripts.ffmpeg_handler.subprocess.run")
    def test_convert_format_command_structure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        res = self.skill.convert_format("input.avi", "output.mp4", crf=20)
        self.assertTrue(res["success"])
        self.assertIn("-c:v libx264", res["command"])
        self.assertIn("-crf 20", res["command"])

    @patch("scripts.ffmpeg_handler.subprocess.run")
    def test_extract_audio_command_structure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        res = self.skill.extract_audio("input.mp4", "output.mp3", bitrate="320k")
        self.assertTrue(res["success"])
        self.assertIn("-vn", res["command"])
        self.assertIn("-b:a 320k", res["command"])

    @patch("scripts.ffmpeg_handler.subprocess.run")
    def test_create_gif_palette_filters(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        res = self.skill.create_gif("input.mp4", "output.gif", fps=15, width=640)
        self.assertTrue(res["success"])
        self.assertIn("palettegen", res["command"])
        self.assertIn("paletteuse", res["command"])

    @patch("scripts.ffmpeg_handler.subprocess.run")
    def test_merge_videos(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        res = self.skill.merge_videos(["v1.mp4", "v2.mp4"], "merged.mp4")
        self.assertTrue(res["success"])
        self.assertIn("-f concat", res["command"])


if __name__ == "__main__":
    unittest.main()
