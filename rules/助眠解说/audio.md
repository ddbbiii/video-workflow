# 助眠音频规则

> 合并自 `audio-pace.md`、`background-music.md`，以及 `rules/shared/audio/voice-and-subtitles.md` 的声线部分（2026-11-06）。
> 混音执行真源仍是 `../../rules/shared/audio/manual-post-production.md`；原文备份在 `shared/archive/rules-premerge-20261106/`。

## 语速与语气

2026-10-13 用户批准：轻语气候选，整体提高至 **1.06 倍速**，适用于后续片头与正文，不自动重制已完成视频。

- 听感目标：平静自然、略带好奇、转折和疑问起伏。“情感减半”是听感描述；模型没有精确百分比控制。
- 用户批准的处理链：头尾静音裁剪 → 每句 `atempo=0.7304` → 留白拼接 → 整体 `atempo=1.06`，音高不变。
- 从 raw 重建可对有声部分只做一次 `atempo=0.774224`（0.7304 × 1.06），旧留白同步除以 1.06：头部约 0.3774 s、句间约 0.4245 s、尾部约 0.7547 s。
- 裁剪标准：RMS −45 dB、20 ms 帧、有声段前 0.10 s 与后 0.15 s。
- 已按 0.7304 处理的版本只额外加速一次 1.06；已采用新速度的文件不得再次加速。
- 记录输入处理状态、因子与实际时长；音频确定后重新对齐画面、字幕与 BGM 循环长度。
- 固定配置：`shared/runtime/engines/tts/voice-assets/b2-warm-male/light-expression-profile.json`。
- 续写节奏参考：同目录 `refs/light-expression-20261013/prompt.wav`，逐字稿“你脚下的地球，藏着一个看不见的磁场。”；VoxCPM2、seed 7、CFG 2、10 steps、`desc_in_text=false`、`optimize=False`、`load_denoiser=False`。
- 新文本仍须检查声线与语气自然度；未经试听确认，不替换正式参考音或声线登记。

## 声线

- 剧本锁定后先确认可听角色数量、叙述者与各自 `voice_id`。
- 同一角色同集及跨集延续：同一声线锚点、clone prompt、模型、`do_sample=false`、固定 seed。
- 不因分段批量生成而换音色、换随机 seed、换模型或用变速修节奏。
- 需要电话、广播、梦境、情绪失控等特殊音色时，必须明确适用镜头与原因；效果结束后回到基础声线。
- 没有已批准声线时必须说明，不能暗中使用随机新声线。

## BGM

- 统一使用 **`SLEEP-BGM-UNIFIED-001`**；资产真源 `assets/助眠解说/audio/bgm/sleep-unified-v1/CURRENT.md`。
- 不按集选曲、不生成新音乐。特殊题材不适配时先询问用户，不擅自换曲。
- 片头节点默认只放口播，无 BGM/音效；用户明确要求片头加 BGM 时仍用统一曲目。
- 每集可调整增益；循环需处理接缝，不变速、不覆盖原曲。许可核验以资产记录为准，批准选曲不等同于核实商业使用权。
- 历史增益参考 ×1.30（约 +2.279 dB）仅备查，不自动套用。
- **扩展位**：后续建立 BGM 库（每曲一份 md 供检索）后，本节只保留选型原则与索引入口，不在规则里列曲目清单。

## 混音分工

- 默认由用户手动完成配音与 BGM 混音；助手交付独立音轨与统一曲目，不自动铺曲、循环或调增益。
- 旁白、拟声、BGM 均为独立 stem；BGM 未明确要求时不混入。执行细节见 `../../rules/shared/audio/manual-post-production.md`。
