# 当前工作流总览

> 建立：2026-11-06　用途：拆解到 Mac 前的现状基线
> 真源：`rules/shared/video-workflow.md`（固定顺序与门禁）、`rules/助眠解说/*`（线路细则）、`shared/workflows/`（可复用执行件）

## 1. 线路现状：只有一条在产

| 线路 | 状态 | 说明 |
|---|---|---|
| **助眠解说** | **active，生产维护** | 唯一在产线；8 部成片已交付或待验收 |
| 悬疑动漫 | planning，暂停产出 | 2026-10-01 起暂停；仅保留规则、资产、历史项目 |
| 猎奇 | planning | 参考风格策划；旧项目（tudou）已归档，不自动恢复 |
| 创意 | archived | 不排期，保留规则与恢复入口 |
| 音乐线 | testing-preparation | 未进入正式生产 |
| 抖音特效 | ready-for-task | 工具就绪，尚未开始工程 |

结论：**当前实际只有助眠解说一条工作流**。其余五条是登记状态，没有在跑的生产动作。

## 2. 在产工作流：助眠解说

固定顺序见 `rules/shared/video-workflow.md` §1，三道人工门禁不可取消。

| # | 阶段 | 输入 | 产出 | 工具 / 端口 | 机器倾向 | 门禁 |
|---|---|---|---|---|---|---|
| A | 剧本锁定 | 原稿/选题 | 完整旁白、逐镜节拍、角色表、连续性、foley 需求 | 人工 + LLM | 中性 | 用户确认 |
| B | 声线配置 | 剧本 | 每角色 `voice_id`、clone prompt、seed | voxcpm2 / Qwen3-TTS | **Windows GPU** | 用户确认声线 |
| C | 静态分镜 | 事实约束卡 | 全部静帧 + 运行清单 | GPT 图片 API 优先；ComfyUI 8188/8190 辅助 | **Windows**（API 可在任一端） | 不拦主流程 |
| D | 动态镜头 | 静帧 + 选型 | I2V 片段（H3 8189 / Wan / LTX） | ComfyUI 8189、EasyCache | **Windows GPU** | 选型与回退清单需报备 |
| E | 关键动态审核 | D 产出 | 锁定 hash 的镜头 | 人工 | 用户 | **门禁 1** |
| F | 正文视觉成片 | 已锁镜头 + 静帧 | 无音无字幕的视觉母版 + manifest | FFmpeg | 中性（可迁 Mac） | — |
| G | 正文成片审核 | F 产出 | 锁定时间线 | 人工 | 用户 | **门禁 2** |
| H | 片头文案 | 用户 | 钩子文案 | 人工 | 用户 | — |
| I | 片头生成 | 文案 + 声线 | 片头视频（ASS 矢量卡 / 分句卡） | TTS + ASS + FFmpeg 两层渲染 | **可迁 Mac** | **门禁 3** |
| K | 拼接 | 片头 + 正文 | 完整画面 | FFmpeg | 可迁 Mac | — |
| L | 配音/字幕/混音 | 画面 + 母带 | narration.wav、SRT/ASS、烧录版 | TTS(GPU) + FunASR/Whisper + FFmpeg | **混合** | 用户手动混音 |
| M | 交付 | 全部 | clean + narration 两件 | FFmpeg + 校验 | 可迁 Mac | 用户终审后登记 |

## 3. 两代管线并存

| | 主生产流程 | kepu 薄管线 |
|---|---|---|
| 定义 | `video-workflow.md` A→M，8 部成片都走这条 | `script → tts → stills → compose` 四段 MVP |
| 入口 | `shared/workflows/助眠解说/` | `shared/exchange/sync/mac-deploy/kepu-pipeline-mac-thin.tgz` |
| 特点 | 环节多、门禁全、人工介入多 | 松耦合、可拆、已备 Mac 部署包 |
| 用途 | 正式出片 | **最适合作为 Mac 分流的骨架** |

## 4. 初步可拆分边界

**适合迁 Mac（CPU/IO 密集，M 系列有优势）**
- ASR 词级对齐（FunASR / Faster-Whisper，`vo_gate.py`、`asr_check.py`）
- 字幕 DP 对齐与 ASS/SRT 生成（`realign_subtitles.py`、`subtitles/`）
- FFmpeg 合成、烧录、编码（VideoToolbox 硬编）
- QA：黑帧/白帧、音视差、帧数核对、联系表
- 文档、清单、manifest 校验

**必须留 Windows（CUDA）**
- ComfyUI 8188/8189/8190：静帧、H3/Wan/LTX 图生视频
- TTS 生成（voxcpm2 / Qwen3-TTS）
- VSR 超分、LoRA 训练

**中性（两端都能跑，按调度排）**
- 剧本/文案/分镜表、事实约束卡
- GPT 图片 API 调用（网络任务）

## 5. 已有的跨机基础

- Syncthing：`shared/exchange/sync`（`.stfolder` 在位，10-03 有 Mac 回环冒烟）
- Tailscale：两端都已装，ddbbi 为 `100.121.104.65`，LAN 直连 `192.168.5.4`
- GPU 队列：`shared/gpu-queue/`（单卡串行，请求文件制）
- Mac 部署包：`kepu-pipeline-mac-thin.tgz`（含 tts/compose/vo_gate/asr_check）

## 6. 拆解前要定的三件事

1. **谁做调度**：沿用 gpu-queue 的请求文件，还是新设 `job/` 目录双机轮询。
2. **传什么不传什么**：静帧/I2V 片段体积大（单集十几 GB），是否只传结果不传中间件。
3. **门禁怎么落**：E/G/片头三道人工审核在哪台机器上看片、确认结果写回哪里。
