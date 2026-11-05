# 单集状态

标题：知道所有规律，就能预测未来吗？从牛顿力学到混沌

2026-10-14（接手执行）：以口播审阅稿 v1（SHA-256 96e8e346…8ae854d）为制作基稿开始执行。规划已完成：

- audio/utterances.json：200段 / 209配音单元 / 9405可配音字；intro-p05 占位段 tts_blocked。
- audio/AUDIO_PLAN.md：b2-warm-male 轻语气（2026-10-13批准配置），raw 单步 atempo=0.774224，留白 0.3774/0.19/0.4245/0.7547。
- visual/SHOT_PLAN.json + ALL_SHOT_PROMPTS.md：200个正文镜头（118 P1、36 P2、12 I2V、34 受控模拟），正文估算46.6分钟（未实测）。
- 运行目录 runs/20261014-ntc-b01；续跑真源 CHECKPOINT.json。

当前阶段：**完结**(用户 2026-10-18 确认)。

## 完结记录(2026-10-18)

最终成片(总长 2456.567s = 40.94min,台词"四十一分钟"成立):

| 版本 | 路径 | 说明 |
|---|---|---|
| 无字幕版 | `runs/20261014-ntc-b01/watch/newton-to-chaos_with_audio.mp4` | 配音+BGM(-10dB) |
| 烧字幕版 | `runs/20261014-ntc-b01/watch/newton-to-chaos_with_subs_r1.mp4` | style_r4 硬烧,775 条,音频 copy |

- **母片两件套**(final-delivery.md 口径):`video/final/newton-to-chaos_clean.mp4`(无音轨无字幕)+ `newton-to-chaos_narration.wav`(纯旁白),2435s 正文 + 21.567s 片头。
- **片头 v4.4**:C3 文案(4 句,末句含"今天我们来讲讲")21.562s;逗号级 8 卡常显艺术字轨道(0.35s 交叉换字);背景按句切换、0.45s 叠化精确落在句间停顿(朗读期零切画);主题句星河驻留至片尾。批次 `intro/batch-20261018-short/`。
- **BGM**:用户委托混音,-10dB(低于旁白 RMS),片头无 BGM,峰值 0.825 无削顶。
- **字幕 r1**:用户委托,style_r4,锁定稿+单元锚点+FunASR 字级对齐(775 条,匹配率 99.7%),烧录规范见 subtitles.md。产物 `runs/20261014-ntc-b01/subtitles/r1/`。
- **QA 门禁**:两版均 PASS(白屏 0/黑屏 0/音视差 ≤0.021s/解码帧序 CFR);记录 `runs/.../logs/qa_scan/`。
- **已否决项**(有据可查):34 个模拟镜头辉光/彗尾样式增强(样片 `runs/.../sim_style_sample/`,用户评估后维持现版)、1.1x 整体倍速、句级切卡方案。
- douyin 成品索引**未登记**(需用户明确指定终版版本后按 final-delivery.md 登记)。
- 制作全程、四轮片头迭代史与踩坑记录:`runs/20261014-ntc-b01/HANDOVER.md`;片头工艺已固化为用户级 skill `sleep-aid-intro`。

2026-10-14 14:41 全流程跑通，最终交付物已生成于 video/final/：
- newton-to-chaos_clean.mp4（H.264 1920×1080 30fps 74550帧，**无音轨无字幕**，2485.000s = 41.42min）
- newton-to-chaos_narration.wav（PCM16 48kHz mono 纯旁白，2484.969s）
- 音视时长差 0.031s（≤1帧）。

片头分钟数回填"41"（正文40.6min+片头0.83min=41.4min，未回环重测）。完整 QA 见 qa/QA_REPORT.md。BGM 混音与正文字幕由用户手动完成。

## 成片位置（2026-11-06）

成片已统一移至 `shared/delivery/finals/`，本文件内旧的 `video/final/` 路径仅作历史记录。

