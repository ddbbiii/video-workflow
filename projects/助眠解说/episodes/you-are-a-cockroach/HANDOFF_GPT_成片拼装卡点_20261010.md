# HANDOFF · 《你是一只蟑螂》成片拼装卡点（给 GPT 商讨方案）

日期：2026-10-10 03:42（Asia/Shanghai）  
发送方：助眠解说（Grok）  
读者：GPT / 视频号规划 / 老大  
目的：说明当前资产状态、成片拼装主要耗时卡在哪里、为何日历时间越来越长，便于商讨加速或改流程。

---

## 1. 当前状态（截至交接时）

| 环节 | 状态 | 备注 |
|------|------|------|
| 静帧 | **176/176 齐** | gpt-image 2×2 批量（后半程）；落盘 `image/stills/` |
| 配音 raw | **156/156 齐** | VoxCPM2 b2-warm-male；`audio/vo-raw/seed7/` |
| vo_gate | 跑完；4 段 ASR 例外已收下 | 例外见 `audio/vo_gate/ACCEPTED_ASR_EXCEPTIONS.md`（鞘/蠊等生僻字） |
| 变速处理 | **齐** | 去静音 + `atempo=0.7304`；`audio/vo-processed/atempo07304/`；合计约 **44.4 分钟** 口播 |
| 图生视频 LTX | **90/90 齐** | 试点+全量；`runs/20261009-i2v-batch-b01/`（lanczos 1080p）；约 01:56 跑完 |
| 静帧 affine 推拉 | **86 镜齐** | `runs/20261009-affine-b01/out/`；media_candidate=affine / intro |
| 成片拼装 | **未开始** | 时间轴 / 混音 / 字幕 / 片头 / 整片编码尚未做 |
| 地磁集 | 已归档，勿动 | 只做本集 `episodes/you-are-a-cockroach/` |

工程根：`E:\program\1project\video\projects\助眠解说\episodes\you-are-a-cockroach\`  
交接真源仍以本集 `HANDOFF_GROK_你是一只蟑螂.md` + `AUDIO_LOCK.md` + `SHOT_PLAN.json` 为准。

---

## 2. 成片拼装时间主要卡在哪里？

按依赖顺序，**真正吃日历时间**的不是「点一下导出」，而是下面几块（越靠前越容易拖总工期）：

### 2.1 时间轴对齐（最大逻辑卡点，CPU 为主）

- 口播已是 **~44 分钟** 变速后 WAV；镜头是 **~5s I2V** + **~7s affine**，不能拉长/倒放/循环同一条五秒充数（交接硬规则）。
- 因此每段口播往往要：**若干条短动态 + 静帧推拉补足**，或新增关联静帧窗口（`原id-x01`），并写清实际起止。
- 字幕、BGM 循环、分镜切点都必须跟**实测音轨**走，禁止按字数估切点。
- **卡点本质**：资产种类多、时长单位不一致 → 需要一版可复现的 timeline / EDL（段落→utterance→镜头→媒体路径→入出点）。

### 2.2 混音与母线（中等，CPU）

- 片头：纯旁白，**无 BGM**。
- bridge 起：统一 BGM ×1.30（相对旧基准），交叉淡化循环。
- 要分别交付 `narration-dry.wav` / `bgm-stem.wav` / `mix-master.wav`。
- 卡点：响度对齐、循环接缝、intro 与 body 分轨策略；通常小时级，不是通宵级。

### 2.3 字幕（中等，CPU）

- 抖音习惯：字号偏大、白字黑描边、无底条（地磁已定过风格可复用）。
- 必须用处理后音轨 timing；ASS/SRT + clean/sub 双版本。
- 卡点：整片 40+ 分钟字幕校准与抽检，而非渲染本身。

### 2.4 片头 op4（中小，依赖 VO 切点）

- 沿助眠 op4：错峰四格→放大→叠化→艺术字；片头第三句分钟数要等 **body 实测秒数** 再 resolve（`prepare_handoff.py --body-seconds`）。
- 卡点：body 未拼出实测时长前，第三句不能定死；可能多一轮短 TTS。

### 2.5 整片编码（中等，偏 CPU/NVENC）

- 目标：1920×1080 / 30fps / CRF16–18 级 / AAC；`delivery/*_clean.mp4` + `*_sub.mp4`。
- 40+ 分钟一次编码通常 **数十分钟到一两小时**；反复有损转码会拖更久，应尽量一次定稿。

### 2.6 视觉验收（政策卡点，不是算力）

- I2V 现均为 `visual_qa=pending`：自动解码通过 ≠ 人验通过。
- 规则：争议回退 affine；不能拿自动指标冒充人验。
- 若坚持「先人验再进时间轴」，会在拼装前再插一轮审核等待。

---

## 3. 为什么「时间越来越久」？

不是单步变慢，而是**串行长尾叠在一起**：

1. **前半静帧**：曾一张张 GenerateImage，吞吐极低；后改 gpt-image 2×2 才追上。
2. **配音**：整集一次 GPU；vo_gate 重配时曾出现「父进程占锁、run_shots 等锁」死锁，空转约二十分钟。
3. **I2V**：90 镜 × 约 4–8 分钟/镜 **串行** ≈ 一整夜（实际约 19:56→01:56）。
4. **成片阶段**：短视频素材 vs 长口播的对齐是**新的组合复杂度**，前面生成再快，这里仍要做 timeline 工程。
5. 用户感知上「越来越久」，往往是：**看得见的大块（生图/出片）刚完，看不见的拼装依赖才浮出水面**。

粗日历（本集这种强度）：静帧半天 + 配音/门禁半天 + I2V 一夜 + affine 数小时 + **拼装混音字幕半天到一天** → 整集常见 **1.5～2.5 天**。

---

## 4. 关键路径速查

```
episodes/you-are-a-cockroach/
  HANDOFF_GROK_你是一只蟑螂.md
  visual/SHOT_PLAN.json
  image/stills/                          # 176 jpg
  audio/vo-raw/seed7/                    # raw
  audio/vo-raw/seed7-final/              # gate picks
  audio/vo-processed/atempo07304/        # 处理后口播
  audio/vo_gate/ACCEPTED_ASR_EXCEPTIONS.md
  audio/AUDIO_LOCK.md
  audio/PROCESSING_DEFAULTS.json
  runs/20261009-i2v-pilot-b01/           # 6 试点
  runs/20261009-i2v-batch-b01/           # 90 I2V + i2v_manifest.json
  runs/20261009-affine-b01/out/          # 86 affine mp4
```

口播总长参考：`vo-processed/atempo07304/manifest.json` → `total_seconds` ≈ 2661.5（~44.4 min）。

---

## 5. 请 GPT 一起商讨的问题（方案选项）

请围绕「缩短成片拼装日历时间、降低对齐复杂度」给方案，并标清利弊：

1. **时间轴策略**  
   - A. 严格按现规则：I2V 原速短窗 + affine 补足，必要时加 `x01` 新静帧。  
   - B. 提高 I2V 覆盖播放时长（更长窗/更多窗）——算力与失败率代价？  
   - C. 先拼「全 affine 可播草稿」再逐步替换合格 I2V（并行验收）。  

2. **验收闸门**  
   - 是否允许「pending_review 的 I2V 先入轨，争议镜头默认 affine」以先出可审成片？  
   - 人验抽检比例建议？

3. **工程交付物最小集**  
   - 拼装前最小需要哪些机器可读文件（utterance timeline、shot EDL、media map）？  
   - 是否应由脚本从 `atempo07304` + `SHOT_PLAN` + i2v/affine manifest **一次生成**？

4. **编码与预览**  
   - 是否先出 5–10 分钟竖/横预览再全片编码？  
   - NVENC vs CRF 软件编对「一次定稿」的建议。

5. **流程改动能不能动**  
   - 管线/规则代码只能视频号规划改；本集执行层可改为「先草稿后替换」而不改共享规则吗？

---

## 6. 执行层建议的下一步（供拍板，非最终）

在方案未定前，执行层默认倾向：

1. 用处理后口播生成 **utterance/paragraph 时间轴**；  
2. 写 **media map**（每镜优先 I2V lanczos，缺则 affine）；  
3. 拼一版 **无字幕或粗字幕的可播草稿**；  
4. 再上 BGM/字幕/片头分钟数 resolve；  
5. 一次编码 clean + sub。

若 GPT/老大决定「必须先人验 I2V」，则在步骤 2 前插入抽检清单。

---

## 7. 不要做的事

- 不要拉长/倒放/循环五秒 I2V 充数。  
- 不要动地磁归档资产。  
- 不要改共享管线代码（有想法提视频号规划）。  
- 不要伪造 visual_qa=passed。

---

*本文件由助眠解说根据 2026-10-09～10 实际生产情况整理，供 GPT 商讨方案用。*