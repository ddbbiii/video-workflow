# 助眠交付规则（本线特例）

> 通用交付口径见 `../shared/delivery.md`；本文件只写助眠线的差异。
> 2026-11-14：本线只交正文视频 + SRT，不做片头、不做封面、不做字幕烧录、不产配音。

## 规格

- 1920×1080 / 30 fps；H.264 + `yuv420p` + `+faststart`；**0 音频流、0 字幕流、无烧录文字**。
- 成片从正文第一帧开始；不含引入、标题、章节卡、账号名。

## 必跑门禁

- 像素级 QA：白/黑屏 ≥1 s 为 0；CFR 均匀；时长 = 帧数 / 30，误差 ≤1 帧。
- **白边检测**：抽开头/中段/结尾及原白边镜头，四边 2 px 按 `visual.md` 白边门禁判定；FAIL 则内裁 4 px 重出，不带白边交付。
- 分镜计划完整性：`motion_plan.json` 已过 `shared/camera-motion/validate_plan.py`（PASS 日志在 run 目录）；缺源、黑/纯色源、幅度低于下限不得交付。
- SRT：`check_srt.py` PASS；首条 0.000；每条 ≤20 字；注明估算时间轴。

## 路径

- 视频：`projects/助眠解说/episodes/<slug>/video/final/助眠_<中文剧名>_正文_vN.mp4`
- SRT：与视频同目录 `video/final/助眠_<中文剧名>_正文_vN.srt`（独立文件，不烧录）
- 不落 `shared/delivery/`，不写成品卡，不登记索引。
