# PROJECT_STATE · 人生体验 EP03「你第三次重复就死了」

- 单集路径：`projects/人生体验/episodes/20261114-sanzhong/`
- 线路规则：`rules/人生体验/README.md`、`style.md` v3.2、`character.md` v6、`color-script.md` v1.2；共用 `rules/shared/video-workflow.md`（纯正文版 v2）、`delivery.md`、`srt.md`
- 起始：2026-11-14 ｜ 状态：**已清空旧产物，待按 v3.4（两层画风）整集重出**（2026-11-15 03:50 用户指令：废弃件与本期成品图/成品视频一律删除）

## 0 当前状态

- **无成片**：v1 / v2 / v3 正文视频与 SRT、全部静帧与切片，已于 2026-11-15 03:50 按用户指令删除（废弃件不留在工作区）。
- 保留的只有可重建的数据与工具：`story/`（cues / visuals / cast / shot-types / expressions / props）、`image/color-plan.json`、`image/refs/`（v7 裁切、六档平涂表情、三个通用配角）、`video/timeline-v3.json`、`subtitles/r3/`、生成与合成脚本。
- 重建入口：`python story/build_v3.py`（cues + visuals + cast + shot-types → `story/script-v3.md`，220 镜，`lint_narration` PASS）。
- 下一步：按 `style.md` v3.4 / `character.md` v7 / `color-script.md` v1.3 整集重出（无人镜一遍、人物镜两遍、24 镜一锁）。

## 1 本期授权与决策（用户当次指令即授权，只对本期有效）

| 日期 | 指令 / 决策 | 影响 |
|---|---|---|
| 2026-11-14 | 「人生体验做新的一期」＋《三重死则》末世故事大纲（13 天、原定 30 分钟、写实 Bad End） | 本期题材、结构、结局由用户定 |
| 2026-11-14 | 「做到二十分钟左右就行」 | 基准时长从 30 min 改为约 20 min；剧本按 4.8 字/秒压到 5,197 可见字（18:57） |
| 2026-11-14 | 动态方式：全片静帧 + 2.5D 轻推拉，**不启用 I2V** | 无「关键动态」镜，门禁 1 只审静帧与运动方式；此项在门禁 1 交用户确认 |
| 2026-11-14 | 「把执行顺序换成先做 A 和 B，出图给我看再继续」 | A（220 镜视觉重写）+ B（3 张标准脸候选）先交，用户挑定 **候选 B** 后继续 C–G |
| 2026-11-14 | 「用 dkl-b 来提高并发」 | 整批 220 张改走 dkl-b 单通道、32 并发，7 分钟出齐；new2 那批 16 张移入 `image/stills-v3b-new2/`，不进成片 |
| 2026-11-14 | 「不止这几个图片有问题…看下什么原因、怎么优化规则」 | 定位到三条根因（缺 cast 字段 / 老陈无定装参考 / 参考图带柔光），按方案 1 落地：`script-workflow.md` v2.3 §15.1 三字段 + `check_cast.py`、`character.md` v6.1 §4.1/4.2、`style.md` v3.3、通道 `style_fit_gate`；重建参考图；重出 53 镜 |

## 2 规格

| 项 | 值 |
|---|---|
| 正文 | 220 镜 / 5,339 可见字 / 35,077 帧 / 19:29.23 |
| 视频 | 1920×1080、30 fps、H.264、`yuv420p`、`+faststart`、**0 音频流 / 0 字幕流** |
| SRT | 427 条，`00:00:00,000` 起，≤20 可见字，估算时间轴（4.8 字/秒），未对真实人声校准 |
| 生图 | `dkl-b`（2048×1152，0.018 元/张）：`new2` 在途并发上限 4、达不到批量速率，按策略整批降级；同一集未混通道 |
| 主角参考 | `image/refs/ref-canonical.png`（候选 B，1024²，平涂）+ `image/refs/ref-v3-<档>.png`（左标准脸 / 右该档表情） |

## 3 阶段与门禁

| 阶段 | 状态 | 证据 |
|---|---|---|
| A 剧本锁定 | **v3 视觉重写完成**（cue/配比未动） | `story/script-v3.md`（220 镜九字段）；`lint_narration.py` PASS；`check_shot_mix.py` PASS |
| B 角色资产 | **v3 标准脸定版** | `image/refs/ref-canonical.png`；`image/refs/expr-v3/*.png`（六档平涂）；六档 2-up `ref-v3-<档>.png` |
| C 静态分镜 | **完成 220/220** | `image/stills-v3b/`（dkl-b 单通道）；`image/frames-v3/`（严格 16:9 1080p）；`qa/sheets-v3/` 10 张联系表 |
| D 动态关键镜头 | 本期不启用 I2V（见 §1） | — |
| E 门禁 1 | 静帧目检：10 张联系表全过 + 两轮返工（31 + 2 镜） | `qa/sheets-v3/rework-01.jpg` |
| F 正文视觉成片 | **完成** | `video/motion-v3-1..4/`（affine 60 fps）→ `video/clips-v4/`（30 fps）→ 成片 |
| G 门禁 2 | 像素扫描 PASS、交付门禁 PASS | `qa/pixel_scan_v3.json`、`qa/delivery_v3.json` |
| H SRT | **完成** | `video/srt/…_正文_v3.srt`；`check_srt.py` PASS；G1 PASS |
| I 交付 | **已交付** | §0 |

## 4 时间轴

- 语速 4.8 可见字/秒、句间 0.24 s、章间 0.90 s；`subtitles/r1/sentences.json` → `video/timeline.json`（帧对齐，34,120 帧）。
- 视频按 `timeline.json` 的帧数建段，SRT 由同一份时间轴拆条，首末一致。

## 5 本期已知偏差

0. **色彩 v1 全片泛黄**：v1 静帧 210 张平均色相 30.1°、0–60° 占 98.5%、R/B 1.67。已改规则（`style.md` v3 / `color-script.md` v1.2）并重出。
0b. **v3 已修**：v2 成片的三条实测问题——人物中位占高 79%、场景空墙、`zoompan` 整数抖动——在 v3 分别改为九字段构图语法、三层信息与 `env_by_scene`、affine 60 fps 浮点后端。v3 实测：成片 R/B 1.017、黑/白屏 0、CFR 30 fps、推近 12% / 横移 6%。
1. **构图比例未落地（2026-11-14 18:20 实测）**：`style.md` §三 要求「人物占画面 1/6–1/2」，但**提示词里从未写过景别/占比**，
   实测 69 张中 65 张人物占高 >1/2（中位 0.78），只有 3 张合规。头身比本身合规（约 3.3 头身）。
   2026-11-14 18:25 用户指令：**这些图全部废弃**。重出前必须先补 `story/framing.json` + 生成器构图行 + `qa/audit_ratio.py` 验收。
2. 配角老陈：单镜生成时出现过写实 3D 感 / 偶像脸 / 六十岁，已在 `HUMAN` 提示块里锁「三十多岁、普通真人、同款线稿平涂」。
3. 运动方式：全片 2.5D，无 I2V；若用户要求关键动作动起来，需另开 I2V 轮次并重跑门禁 1。
