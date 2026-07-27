# FFmpeg Media Skill 基础使用样例

本文档提供各种典型场景下的代码调用与 API 样例。

## 场景 1：视频转 GIF 动图

将视频中从第 2 秒开始，时长 5 秒的代码演示片段转化为 15 帧/秒、宽度为 480 像素的高品质 GIF：

```python
from scripts.ffmpeg_handler import FFmpegSkill

skill = FFmpegSkill()
res = skill.create_gif(
    video_path="demo.mp4",
    gif_path="demo.gif",
    start_time="00:00:02",
    duration=5,
    fps=15,
    width=480
)
print("处理结果:", res)
```

---

## 场景 2：提取视频中的音频为 MP3

```python
res = skill.extract_audio(
    video_path="interview.mp4",
    audio_path="output_audio.mp3",
    bitrate="192k"
)
print("提取音频:", res)
```

---

## 场景 3：合并多个视频文件

```python
video_list = ["intro.mp4", "main_part.mp4", "outro.mp4"]
res = skill.merge_videos(
    video_list=video_list,
    output_path="final_video.mp4"
)
print("视频合并:", res)
```

---

## 场景 4：批量将文件夹内的 MOV 格式转换为 MP4

```python
res = skill.batch_process(
    input_dir="./raw_videos",
    output_dir="./processed_videos",
    operation="convert",
    target_ext="mp4",
    crf=22
)
print(f"批量处理完成: 成功 {res['processed_count']} 个，失败 {res['failed_count']} 个")
```
