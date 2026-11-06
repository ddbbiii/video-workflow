# 助眠解说 TTS 换线调研 · 2026-11-06

> 目的：VoxCPM2 的“合成换气 + 22.6% 变速”两个病根已确认无法用后期修好。
> 本文只做选型与试点计划，未安装、未改规则、未动已交付成片。
> 价格/许可均为 2026-11-06 查到的官方仓库原文，落地前建议再核一次 LICENSE。

## 一、结论先行

1. **不要再在 VoxCPM2 上修气声**。它的换气是模型生成的噪声，参考音本身也是 TTS 输出，没有真人换气可替换。
2. **换线的真正收益是“原生变速 + 显式换气控制”**，不是 CER。VoxCPM2 的 CER（3.88）本来就比新一代（0.8–1.2）差。
3. 推荐两位主候选：
   - **Qwen3-TTS 1.7B**（Apache-2.0，2026-01）：安装最省事、中文强、支持 instruct 控制语速，适合先跑通。
   - **CosyVoice 3 0.5B**（Apache-2.0，2025-12）：**支持 `[breath]` 显式换气 token + `speed` 参数**，最贴合“不要机械换气”的诉求。
4. 备选 **LongCat-AudioDiT 1B**（MIT）：中文相似度 0.812，非自回归、稳定性好，但新、工具链少。

## 二、候选对比

| 模型 | 许可 | 参数 | 中文 CER / 相似度 | 原生变速 | 换气控制 | 输出 | 16 GB 可行性 | Windows 风险 |
|---|---|---|---|---|---|---|---|---|
| **Qwen3-TTS 1.7B Base** | Apache-2.0 | 1.7B | 1.22 / 0.770（Seed-ZH）；长文 zh 2.36 | instruct 控制语速 | 无专用 token，靠 instruct | 24 kHz | 高（bf16 ~3.5 GB） | 低（纯 pip） |
| **CosyVoice 3 0.5B** | Apache-2.0 | 0.5B | 1.21 / 78.0（RL 0.81 / 77.4） | `speed=` 参数 | **`[breath]` token** | 24 kHz | 高（~1 GB） | 中（torch 版本需改） |
| LongCat-AudioDiT 1B | MIT | 1B | 1.18 / **0.812** | `duration` 控制 | 无 | 24 kHz | 高 | 中（新，依赖少） |
| GLM-TTS 1.5B | Apache-2.0 | 1.5B | 1.03 / 0.761（RL 0.89） | 无 | 无 | 24 kHz | 中高 | 中 |
| IndexTTS 2.5 0.8B | bilibili 许可 | 0.8B | 4.36 / 0.771 | `duration_factor` 0.5–2.0 | 无 | 24 kHz | 高 | 低 |
| GPT-SoVITS V5 | MIT | ~1B | 零样本一般，微调后好 | 有 | 无 | **48 kHz** | 高 | 低（整合包） |
| VoxCPM2（现用） | Apache-2.0 | 2B | 3.88 / 0.750 | 无（靠 atempo） | 无 | 48 kHz | 中 | 低 |

> CER/相似度来自各自论文或官方对比表，测试集不完全一致，只作方向参考。

### 为什么是这两位

**Qwen3-TTS 1.7B**
- 2026-01 开源，Apache-2.0，商用无门槛。
- 生态最顺：`pip install qwen-tts`，无需 pynini/sox 折腾；新 torch（cu128）可支持 5060 Ti。
- 支持 voice design → 生成参考音 → 再克隆复用，正好接现有“先定声线再批量”的流程。
- 长文一致性官方数据比 VoxCPM 好一倍（2.36 vs 4.84）。
- 短板：没有 `[breath]` 这种硬控制，换气只能靠 instruct 描述。

**CosyVoice 3 0.5B**
- Apache-2.0，0.5B，跑得快、显存低。
- **`inference_zero_shot(..., speed=0.8)` 原生减速**，不需要 atempo；`inference_cross_lingual` 支持 `[breath]` 显式标记换气位置。
- 中文 CER 1.21（RL 0.81），相似度 78.0，比 VoxCPM2 高一档。
- 支持粤语/四川话等 18 种口音，后续做方言集不用换引擎。
- 短板：requirements 把 torch 钉在 2.3.1（cu121），Blackwell 显卡需要手动换 torch 2.7+/cu128，可能要调；否则走 Docker/WSL。

## 三、明确排除

| 项目 | 原因 |
|---|---|
| **VibeVoice TTS** | 2025-09 官方已从仓库移除 TTS 代码，模型页标注 Disabled，且声明仅研究用途、不建议商用。 |
| **Fish-Speech / S2** | 社区许可：年收入 <50 万美元才可商用，Hosted Service 另需授权；对本项目没必要。 |
| **Chatterbox** | 2026-08 起停止维护，仅存档；中文单语包质量未知。 |
| **IndexTTS 2.5** | 许可可用（<1 亿 MAU、<10 亿营收），但中文 CER 4.36 明显落后；只在需要“精确时长控制”时才有优势。 |
| **FireRedTTS-2** | Apache-2.0，但零样本克隆声明“仅学术研究”，且输出 24 kHz；不作为主线。 |

## 四、推荐路线（三步，先零成本验听）

### 第 0 步：官方 Demo 试听（0 安装，约 15 分钟）
用同一段 77 字 + 现有 16s 参考音，在官方在线 Demo 各跑一次：
- Qwen3-TTS：ModelScope Studio / HF Space（`Qwen/Qwen3-TTS`）
- CosyVoice3：ModelScope `FunAudioLLM/Fun-CosyVoice3-0.5B-2512` Space

重点听：句末换气、齿音、“下/雪”这类字头。若 Demo 就明显更自然，再装本地。

### 第 1 步：本地试点（先 Qwen3，约 30–45 分钟）
- 独立 venv（Python 3.12 + torch cu128），模型与缓存全部放 E 盘（C 盘只剩 6.7 GB）。
- 生成：77 字段落 + 3 分钟章节 + 片头三句；instruct 写“平静、缓慢、像睡前讲故事、换气轻”。
- 验收：FunASR 回识 CER、实测字/秒、显存峰值、RTF，并与 L7 做 A/B。

### 第 2 步：若 Qwen3 换气仍不满意，再上 CosyVoice3
- 用 `speed=0.78` 直接生成目标语速，**不再 atempo**。
- 换气：默认不写 `[breath]`；需要时只在句号后手动插一个，位置可控。
- 若 torch 2.3.1 与 5060 Ti 冲突，方案 A 换 torch 2.8/cu128 试跑；方案 B 用 Docker Desktop（已安装）跑 Linux 容器。

### 第 3 步：接入现有流水线
- 新增 `tts_provider` 适配层：`generate(text, ref_wav, ref_text, speed, seed) -> wav`。
- 时间轴仍以实测 wav 为准；因为不再变速，`atempo` 从链路移除。
- 片头/字幕沿用现有 G1–G6 门禁。

## 五、成本与风险

| 项 | 估算 |
|---|---|
| Demo 试听 | 15 分钟，0 GPU |
| Qwen3 本地安装 + 首次生成 | 30–45 分钟（下载约 4 GB） |
| CosyVoice3 本地安装（含 torch 调整） | 1–2 小时 |
| 35 分钟正文生成 | 视 RTF 而定，预计 10–30 分钟（需实测；现 VoxCPM2 约 44 分钟） |
| 磁盘 | 模型 + 缓存约 8–12 GB，全部放 E 盘 |

主要风险：
1. **24 kHz 输出**：主流新模型都是 24 kHz，需要升采样到 48 kHz；对助眠人声影响很小，但交付前要听。
2. **换气仍可能合成**：`[breath]` 是“可控”不是“真人”；如果仍不满意，最终解是录一段真人旁白做参考/微调。
3. **许可再核**：Qwen3/CosyVoice 为 Apache-2.0，商用最稳；IndexTTS/Fish 有营收门槛，不建议混用。

## 六、参考链接

- Qwen3-TTS 仓库：https://github.com/QwenLM/Qwen3-TTS
- Qwen3-TTS 模型卡（Apache-2.0）：https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base
- CosyVoice 仓库：https://github.com/FunAudioLLM/CosyVoice
- Fun-CosyVoice3-0.5B 模型卡（Apache-2.0）：https://huggingface.co/FunAudioLLM/Fun-CosyVoice3-0.5B-2512
- LongCat-AudioDiT-1B（MIT）：https://huggingface.co/meituan-longcat/LongCat-AudioDiT-1B
- GLM-TTS（Apache-2.0）：https://github.com/zai-org/GLM-TTS
- IndexTTS（bilibili 许可）：https://github.com/index-tts/index-tts
- GPT-SoVITS（MIT）：https://github.com/RVC-Boss/GPT-SoVITS
- VibeVoice（TTS 已移除）：https://github.com/microsoft/VibeVoice
- Fish Audio 许可：https://github.com/fishaudio/fish-speech
