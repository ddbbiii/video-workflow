# voice-cosy3 · 助眠旁白生成（CosyVoice3）

> 2026-11-06 用户确认，作为助眠线**新单集默认配音**。
> 规则真源：`rules/助眠解说/audio.md`；声线资产：`shared/runtime/engines/tts/voice-assets/b2-warm-male-cosy3/`。

## 它做什么

```
<episode>/audio/utterances.json
  │ gen_units.py        （CosyVoice3，逐单元，speed=0.90，断点续跑）
  ▼
<episode>/audio/vo-raw/<tag>/<id>.wav         24 kHz
  │ post_process.py     （−42 dB 紧裁 + 20 ms 淡入淡出 + 升采样 48 kHz）
  ▼
<episode>/audio/vo-processed/<tag>/<id>.wav   48 kHz
  │ assemble.py         （按 3.8 字/秒反算句间留白，写 timeline）
  ▼
<episode>/runs/<run-id>/chapters/*.wav + body_narration.wav + timeline.json + REPORT_audio.md
```

`timeline.json` 字段与旧 `09_build_chapter_audio.py` 一致，镜头、字幕、片头继续读同一个时间真源。

## 环境（已就位）

- `shared/runtime/engines/tts/cosyvoice3/repo`：官方仓库 + Matcha-TTS 子模块
- `shared/runtime/engines/tts/cosyvoice3/model`：Fun-CosyVoice3-0.5B
- `shared/runtime/engines/tts/cosyvoice3/.venv`：Python 3.11 + torch 2.8.0+cu128

从零复现：

```powershell
# 1) 仓库（含子模块）
git clone --recursive https://github.com/FunAudioLLM/CosyVoice.git repo
# 2) 模型
python -c "from modelscope import snapshot_download; snapshot_download('FunAudioLLM/Fun-CosyVoice3-0.5B-2512', local_dir='model')"
# 3) venv：官方 requirements 钉 torch 2.3.1，不支持 RTX 50 系，必须覆盖为 2.8+cu128
uv venv --python 3.11 .venv
uv pip install --python .venv\Scripts\python.exe torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
uv pip install --python .venv\Scripts\python.exe "setuptools<81" wheel
# requirements 去掉 torch/torchaudio/linux-only 后安装
uv pip install --python .venv\Scripts\python.exe -r requirements-win.txt
# openai-whisper 需旧 setuptools + 关构建隔离
uv pip install --python .venv\Scripts\python.exe "openai-whisper==20231117" --no-build-isolation
```

## 用法

```powershell
# 全量（默认 = 除 intro 外的所有段落，按 utterances.json 实际章数）
.\run_vo.ps1 -Episode E:\program\1project\video\4 -RunId 20261106-gla-cosy3

# 只跑某几章
.\run_vo.ps1 -Episode E:\program\1project\video\4 -RunId 20261106-gla-cosy3 -Sections ch01,ch02

# 冒烟：只生成 3 个单元（不装配）
.\run_vo.ps1 -Episode E:\program\1project\video\4 -RunId smoke -Sections ch01 -MaxUnits 3 -SkipAssemble
```

也可以分步跑：

```powershell
& ..\..\runtime\engines\tts\cosyvoice3\.venv\Scripts\python.exe gen_units.py --episode <ep> --sections ch01
python post_process.py --episode <ep>
python assemble.py --episode <ep> --run-id <run-id> --sections ch01
```

## 参数与红线

| 项 | 值 | 说明 |
|---|---|---|
| speed | 0.90 | **不得 ≤0.85**；0.85/0.78 会出电音沙沙 |
| 节奏 | 3.8 字/秒 | 由句间留白反算，不用 atempo |
| 裁剪 | −42 dB / 20 ms | 前 0.05 s、后 0.08 s，20 ms 淡入淡出 |
| 输出 | 48 kHz / 16-bit | 模型原生 24 kHz，统一升采样 |
| 留白夹限 | 0.35–2.5 s | 超限会在报告里标 `夹限` |

## 已知问题

1. **无 seed**：`inference_zero_shot` 不接受 seed，同一句每次略有差异；批量后必须抽检（建议 Whisper/FunASR 回识 + 人工听 3–5 处）。
2. **wetext 前端**：首次加载会尝试下载，ModelScope 无 token 时回退；日志 `no frontend is avaliable` 可忽略，中文标点正常。
3. **ONNX CPU**：speech tokenizer 走 CPU，首次加载约 10–30 s；不影响生成速度（RTF ≈ 0.6–1.2）。
4. **长文**：一次喂整段长文可能出现重复/漏字；本工具**逐单元**生成，天然规避。
5. **24 kHz**：升采样到 48 kHz 后要听一次高频，确认没有异常。
6. **片头未切换**：`gen_units.py` 默认跳过 `intro`；片头仍走 `intro-v5-stacked/` 与 `hook-intro-v1/` 的旧 TTS 配置，音色会与正文略有差异。下一步再把片头模板的 TTS 指向本声线。

## 迁移说明

- 旧 `b2-warm-male/light-expression-profile.json` 与 VoxCPM2 脚本保留，仅用于复现 2026-11-06 前的成片；新单集不再走 atempo。
- 已交付成片不回灌、不重制。
- 字幕必须按新 `timeline.json` 重建（G1–G6 门禁不变）。
