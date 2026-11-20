# 人生体验线路状态

- 状态：active；人物风格仅保留圆头手绘（默认）与猫头人（保留可选），背景保留原手绘画风。
- 更新：2026-11-20，按用户决定删除火柴人方案的规则、样图和比较实验，仅保留猫头人和圆头手绘。
- 旧成片不自动重制；重新开启视觉制作时采用当前规则。

## 规则现状

当前规则唯一入口：`rules/人生体验/README.md`。画风 v5.0、角色 v9.0、参考 v3.0、色彩 v2.2、静帧规程 v3.0。共享镜头与交付规则继续继承。

人物画法基准：`planning/refs/主角-多角度.jpg`及`planning/refs/画风-六格.jpg`；单集角色参考按身份、服装与动作准备。猫头人素材原位保留于 `assets/人生体验/characters/catman-20261113/`，保留为另一种可选风格，不自动与本集圆头人物混用；旧规则见 `archive/catman-visual-rules-20261118/ARCHIVE.md`。

《清理垃圾屋》圆头手绘新版已完成，54人物镜更新，76段原文、9分24.5秒、76镜，逐帧QA通过；正文 `episodes/20261120-qingli-lajuwu/video/final/人生体验_清理垃圾屋_正文_v2.mp4` 及同名SRT（估算时间轴）；两张独立引入图在该集`image/intro/v2/`，未剪入正文。

## 现有单集

- `episodes/20261115-henshi/`《痕尸末世十九天》：2026-11-15已完成，172镜/14:09.5，QA全PASS；正文 `video/final/人生体验_痕尸末世十九天_正文_v2.mp4`，独立字幕 `video/srt/人生体验_痕尸末世十九天_正文_v2.srt`（估算时间轴）。
- `episodes/20261117-tianshaonian/`《你只是很会领奖》：正文 v1 已完成，31 镜/5:11.033；MP4 + SRT 联合门禁、旁白 lint、SRT 检查及逐帧像素/CFR QA 均 PASS。时长按 4.8 字/秒估算，低于约 6 分钟目标 49 秒，未对真人配音校准。文件：`video/人生体验_你只是很会领奖_正文_v1.mp4`、`video/srt/人生体验_你只是很会领奖_正文_v1.srt`；QA：`qa/pixel_scan-v1.json`、`video/delivery-report-v1.json`。
- `episodes/20261117-aotai/`《鳌太线凌晨进山》：正文 v1 已完成，53 镜/8:34.433；单视频流、无音频/字幕流，交付、SRT、15,433 帧解码、逐帧像素及 CFR QA 均 PASS。SRT 167 条，估算时间轴未对真人声校准；低于底稿 12–14 分钟目标，未为凑时长加无来源内容。ECC 运镜配准因计算耗时未完成，详见单集 `qa/motion-v1.md`。文件：`video/final/人生体验_鳌太线凌晨进山_正文_v1.mp4`、同目录 SRT；QA：`qa/delivery-v1.json`、`qa/pixel_scan-v1.json`、`qa/srt_qa-v1.md`。
- `episodes/20261114-sanzhong/`（EP03「你第三次重复就死了」）：**无成片**，数据与工具保留，待重出。
- `episodes/20261113-tumu/`：`video/final/人生体验_奖励自己一个土木工程_成片_v5.mp4` + `video/srt/…_成片_v5.srt`；`video/archive/`、`video/intro-v*.mp4`、`subtitles/r*` 为历史产物，保持原样。
- EP01 `20261110-biye/` 目录已丢失，只在旧记录里存在，不再维护。

## 下一步

1. 新集按 `rules/shared/video-workflow.md`：剧本 → 分镜 → 动态 → 门禁 1/2 → SRT → 交付；
2. 成片从正文第一帧开始，不做片头、标题页、章节卡；
3. 画风按 `style.md`，主角按 `character.md`，SRT 按 4.8 字/秒估算。

## 明确不做

- 片头、标题页、章节卡、账号卡、配音、混音、BGM、字幕烧录、封面、成品库、成品卡。
- 旧片头规则、`slice_intro.py`、`intro_mix.py`、`check_slice_intro.py` 已归档。
