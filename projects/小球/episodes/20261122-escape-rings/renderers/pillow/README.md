# Pillow 轨迹回放基线

本目录是 Python/Pillow 逐帧绘制基线。它读取 `../../simulation/trace.json`，不再计算物理，也不修改球的轨迹或破环时刻；输出写入 `../../video/candidates/escape-rings-pillow-reversal.mp4`。

从仓库根目录运行：

```sh
.venv/bin/python projects/小球/episodes/20261122-escape-rings/renderers/pillow/render.py
```

输出使用系统 FFmpeg 编码为 H.264/yuv420p、1080x1920、30 fps。当前实验基线没有音频、字幕流或烧录文字。
