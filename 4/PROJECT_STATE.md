# 单集状态｜glacier-river（冰川是一条缓慢的河）

| 字段 | 值 |
|---|---|
| episode | glacier-river（工作区 `E:\program\1project\video\4\`） |
| 范围 | 全片 v1.1：三句手写体片头 + 十二章 + 尾声 |
| 状态 | full_delivered_v1.1，待用户验收 |
| active_run | `runs/20261103-gla-b01/`（`REPORT_full.md`） |
| 成片 | **2128.667s = 35:28.7**；clean 390MB / narration 195MB / with_narration 433MB / sub 504MB |
| 片头 v2 | 10.59s / 318f；BaoCanMou HuiTing 144px；三句堆叠上移；b2-warm-male 配音 |
| 正文 | 2108.1s；7951 字 / 207 单元；声线 seed 7 + atempo 0.774224 |
| 字幕 | r5 门禁版：685 条 ASR 逐字对齐（-0.504s）+ 46 条词边界双行；行级坏断点 0 |
| QA | 20 号 PASS（白0/黑0/音视差 −0.001s）；182/182 段帧数精确 |
| 旧版 | `final_43s/`（43.03s 片头四件）归档 |
| 未做 | i2v、BGM（已披露） |
| updated | 2026-11-04 12:20 |

## 环境处理

- TTS：voxcpm→librosa→numba 懒加载在默认 temp 下卡死；06 号脚本把 TMP/NUMBA_CACHE_DIR 指到 run 内 `logs/tmp`。
- 共享 GPU 锁/队列目录在沙箱外不可写：改本地锁 + 只读检查共享锁。
- camera_motion 依赖 cv2：渲染用系统 Python。

## 已维护进工作流（2026-11-05｜Hook 型片头）

- 规则：`rules/助眠解说/intro-node.md` §2 新增「Hook 型（此后助眠科普新单集默认）」+ §3「2026-11-05 定稿」。
- 模板：`shared/workflows/助眠解说/hook-intro-v1/`（README / reference_hook_intro.py CLI / reference_hook_asr.py / config_example_glacier.json）。
- 配置：`configs/hook_intro_glacier.json`，`enabled` 总开关，false 回退旧片头。
- Skill：`~/.agents/skills/sleep-aid-intro/SKILL.md` 增补 §7 Hook v1.0。
- 首测批次：`runs/20261105-hook-b01/`（33.13s；两张图；ASS 矢量大字；四字标题“冰川之河”450px）。
- 注意：本集正片仍用 10.59s 三句片头；Hook 版仅预览，未替换已发布成片。

## 已维护进工作流（2026-11-04）

- 规则：`rules/助眠解说/intro-node.md` 新增「短标题型」分型 + §3「2026-11-04 定稿：短标题型三句堆叠」+ §4 字幕必须 DP 重对齐。
- 模板：`shared/workflows/助眠解说/intro-v5-stacked/`（README / reference_build_intro_v2.py / reference_realign_subtitles.py / template_tts_job.json）。
- 字体：`assets/助眠解说/intro/fonts/BaoCanMouHuiTing-Regular.ttf` + OFL + 字体 README。
- Skill：`~/.agents/skills/sleep-aid-intro/SKILL.md` 增补 §6 v5 工艺。

## 待用户

1. 验收新片头（10.59s、三句节奏）与全片衔接；
2. BGM 风格确认后混音；
3. 是否补 i2v 3—5 镜；
4. 封面自制；终版确认后登记成品。

## 成片位置（2026-11-06）

成片已统一移至 `shared/delivery/finals/`，本文件内旧的 `video/final/` 路径仅作历史记录。

