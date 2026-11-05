# HANDOFF · 《你是一只蟑螂》当前进度（供 GPT 优化）

- 时间：2026-10-10 03:52（Asia/Shanghai）
- 作者：助眠解说（Grok）
- 读者：GPT（优化拼装/流程）；老大拍板
- 工程根：`E:\program\1project\video\projects\助眠解说\episodes\you-are-a-cockroach\`
- 相关：同目录 `HANDOFF_GROK_你是一只蟑螂.md`、`HANDOFF_GPT_成片拼装卡点_20261010.md`

---

## 0. 一句话

**静帧、配音（含变速）、90 镜 LTX、86 镜 affine 均已齐；成片时间轴/混音/字幕/片头/整片编码尚未开始。** 请 GPT 基于「资产已齐、拼装未开」给可执行优化方案。

---

## 1. 进度总表

| 模块 | 进度 | 路径 / 证据 |
|------|------|-------------|
| SHOT_PLAN | 176 镜（正文 168 + 片头 8） | `visual/SHOT_PLAN.json` |
| 媒体意图 | real_video 90 / affine 78 / intro_affine 8 | 同上 `media_candidate` |
| 静帧 | **176/176** | `image/stills/*.jpg`（gpt-image 2×2 为主） |
| 配音 raw | **156/156** | `audio/vo-raw/seed7/*.wav` |
| gate picks | 分章 final | `audio/vo-raw/seed7-final/<章>/` |
| 门禁例外 | 4 段收下 | `audio/vo_gate/ACCEPTED_ASR_EXCEPTIONS.md` |
| 处理后口播 | **156 段，fail=0** | `audio/vo-processed/atempo07304/`；`manifest.json` **total_seconds=2661.5（≈44.4 min）** |
| I2V 试点 | 6/6 ok | `runs/20261009-i2v-pilot-b01/` |
| I2V 全量 | **90/90 ok**（约 01:56 完成） | `runs/20261009-i2v-batch-b01/i2v_manifest.json`；lanczos 在 `.../lanczos/` |
| Affine 推拉 | **86 mp4** | `runs/20261009-affine-b01/out/` + `manifest.json` |
| 片头第三句分钟数 | **未 resolve** | 需 body 实测秒后再 `prepare_handoff.py --body-seconds` |
| 时间轴 / EDL | **无** | — |
| BGM 混音 stems | **无** | 曲目已定：见 AUDIO_LOCK |
| 字幕 | **无** | — |
| delivery 成片 | **无** | 目标见原 HANDOFF |

地磁集已归档，**不要**再动。

---

## 2. 已锁定的生产参数（勿擅自改）

- 声线：`b2-warm-male`；VoxCPM2 continuation；seed7 / cfg2 / 10 steps  
- 口播处理：去静音后 **`atempo=0.7304`**（只乘一次）；见 `audio/PROCESSING_DEFAULTS.json`、`rules/助眠解说/audio-pace.md`  
- I2V：LTX-2.3 distilled；约 **121 帧 @24fps ≈5s**；**禁止**拉长/倒放/循环充数  
- Affine：默认 backend；参考幅度见 `shared/camera-motion/MOTION_GUIDELINES.md`  
- BGM：统一曲目，线性增益 ×1.30；**片头无 BGM**  
- 成片：1920×1080、30fps；clean + sub；抖音字幕风格（大字、白字黑描边）  
- GPU：助眠线路可自管本线请求；不改共享管线代码（改动提视频号规划）

---

## 3. 资产怎么拼（现状约束）

- 口播 **~44.4 min** ≫ 单条 I2V **~5s** / affine **~7s**  
- 规则：短动态原速用；缺口用 **新构图静帧 affine** 或新窗口 `原id-x01`，不抻视频  
- I2V 的 `visual_qa` 均为 **pending**（解码 ok ≠ 人验）  
- 争议镜头正式版默认回退 affine  

因此拼装核心问题是：**生成 utterance→镜头→媒体路径→入出点的可复现 timeline**，而不是再生成素材。

---

## 4. 已知坑（优化时避开）

1. **vo_gate + run_shots 死锁**：父进程若占着 `gpu.lock`，`run_shots.ps1` 会一直 WAIT。重配时不要由父进程长期占锁。  
2. **E: 路径与 CopyToBox**：跨机拷贝勿直读 `E:\...`，先落到 `C:\Users\10060\`。  
3. **生图吞吐**：builtin 逐张极慢；本集后半用 gpt-image 2×2 才补齐。  
4. **I2V 串行**：约 4–8 min/镜 ×90 ≈ 一夜；扩窗会线性加长。  

---

## 5. 请 GPT 优化的目标

请给出**可落地**方案（步骤、脚本职责、目录约定、是否改规则），优先回答：

1. **在现有资产下，最短路径出「可审成片草稿」**（是否允许 pending I2V 先入轨）？  
2. **timeline 最小生成集**：从哪些文件自动生成 EDL（建议输入输出 schema）？  
3. **I2V / affine 选用策略**：按镜优先、按时长配额、还是先全 affine 再替换？  
4. **片头分钟数 resolve** 插在哪一步最不返工？  
5. **预估剩余工时**（人审 / 不人审两档）与并行点（CPU 混音字幕 vs 等 GPU）？  
6. 若要提高「成片中真实动态播放占比」，最小改动是加窗还是加长——代价表？

---

## 6. 建议 GPT 输出格式

请直接给：

1. 推荐方案（1 页内）  
2. 逐步 checklist（执行层可照做）  
3. 需要新增/改动的文件列表（本集目录 vs 必须规划改的共享规则）  
4. 风险与回退  

---

## 7. 执行层默认（方案未定前）

若短期无新指令，助眠解说默认：生成处理后口播时间轴 → media map（I2V lanczos 优先，否则 affine）→ 可播无字幕/粗字幕草稿 → BGM/字幕/片头 resolve → 一次编码 clean+sub。

---

*本文件描述 2026-10-10 03:52 进度快照，供 GPT 针对「当前进度」优化拼装与流程。*