---
name: ffmpeg-media-skill
description: 专业的 FFmpeg 多媒体处理技能，支持视频/音频格式转换、截取、剪辑、高品质 GIF 制作、分辨率调整与多视频合并等操作。
---

# FFmpeg Media Skill (多媒体处理技能)

本技能将开源多媒体引擎 FFmpeg 封装为标准化的 Agent 技能模块。使得 AI 智能体可以理解用户的自然语言需求（例如“提取音频”、“视频转 GIF”、“截取前10秒”、“合并这两个视频”），并安全、自动地调用底层 `FFmpegSkill` 处理逻辑。

## 目录架构

```text
ffmpeg_skill/
├── SKILL.md                 # 技能规范与 Agent 导引文档
├── config.json              # 技能配置与默认参数
├── scripts/
│   └── ffmpeg_handler.py    # 核心 FFmpeg 处理 Python 模块
├── prompts/
│   └── main_prompt.txt      # 提示词模板
├── examples/
│   └── basic_usage.md       # 使用示例
└── tests/
    └── test_ffmpeg_handler.py # 单元测试
```

## 功能特性

1. **格式转换 (Convert)**：支持 MP4, AVI, MOV, MKV, FLV, WMV, MP3, AAC, WAV 等常见的视频与音频格式互转。
2. **音频提取 (Extract Audio)**：无损或高品质抽取视频中的背景音乐/音轨。
3. **分辨率调整 (Resize)**：按自定义宽高（如 1920x1080, 1280x720）或比例缩放视频。
4. **视频剪辑 (Clip)**：根据开始时间与持续时间裁剪视频。
5. **高品质 GIF 制作 (Create GIF)**：采用 `palettegen` 和 `paletteuse` 双路滤镜算法生成无色彩断层的调色板 GIF。
6. **视频拼接 (Merge/Concat)**：通过 `concat` demuxer 将多个同格式或异格式视频合成为单一文件。
7. **批量自动化处理 (Batch Process)**：支持对整个文件夹内的视频进行批量转换或调整。

## 调用指南

### 1. 基础 Python 代码调用

```python
from scripts.ffmpeg_handler import FFmpegSkill

# 初始化 Skill 处理器（自动检测系统 PATH 中的 ffmpeg）
handler = FFmpegSkill()

# 视频转 GIF 示例
result = handler.create_gif(
    video_path="input.mp4",
    gif_path="output.gif",
    start_time="00:00:02",
    duration=5,
    fps=15,
    width=480
)
print(result)
```

### 2. 交互与安全约束

* **环境拦截**：执行前检测系统是否正确安装 FFmpeg。若未检测到，返回明确的安装与配置引导说明。
* **参数安全**：对输入与输出路径进行严格防注入检查与格式校验。
* **错误处理**：捕捉标准错误输出（`stderr`），在任务失败时提供调试日志信息。
