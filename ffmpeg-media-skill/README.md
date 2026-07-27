# FFmpeg Media AI Skill

[![skills.sh](https://skills.sh/b/mwh1987/skills)](https://skills.sh/mwh1987/skills)

专业的 FFmpeg 多媒体处理技能模块，属于 `mwh1987/skills` 集合。专为 AI Agent（如 Claude Code, Cursor, Antigravity, Coze 等）设计。支持音视频格式转换、音频抽取、视频剪辑、高品质 GIF 制作、分辨率调整与多视频合并。

---

## 🚀 在 skills.sh 中安装与使用

本技能托管于公开仓库 `mwh1987/skills` 中。任何用户均可通过以下命令直接安装：

```bash
npx skills add mwh1987/skills/ffmpeg-media-skill
```

或安装整套 `mwh1987/skills` 技能集合：

```bash
npx skills add mwh1987/skills
```

---

## 🛠️ 目录结构

```text
skills/
└── ffmpeg-media-skill/
    ├── SKILL.md                 # 核心技能定义规范 (YAML Frontmatter + Prompt 指引)
    ├── config.json              # 技能参数预设与配置
    ├── README.md                # 技能说明
    ├── scripts/
    │   └── ffmpeg_handler.py    # FFmpeg 核心 Python 处理类
    ├── prompts/
    │   └── main_prompt.txt      # AI Agent 系统提示词模板
    ├── examples/
    │   └── basic_usage.md       # 多场景使用样例
    └── tests/
        └── test_ffmpeg_handler.py # 自动化单元测试套件
```

---

## 💻 基础 Python 调用

```python
from scripts.ffmpeg_handler import FFmpegSkill

skill = FFmpegSkill()

# 视频转 GIF 动图
res = skill.create_gif("demo.mp4", "demo.gif", start_time="00:00:02", duration=5, fps=15, width=480)
print(res)

# 音频提取
res = skill.extract_audio("video.mp4", "audio.mp3", bitrate="192k")
print(res)
```

---

## 🧪 单元测试

在技能目录下运行测试套件：

```bash
python -m unittest discover -s tests -p "test_*.py"
```
