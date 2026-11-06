# Hook Intro v1.0 · 执行件

> Hook 型片头（两拍钩子 ＋ 过渡旁白 ＋ 四字标题），2026-11-05 首测 glacier-river。
> **规则看 `rules/助眠解说/intro.md` §7**；本文件只写配置与命令。

## 文件

| 文件 | 作用 |
|---|---|
| `reference_hook_intro.py` | 主模块，用法 `python reference_hook_intro.py <config.json>`；内部调 ASR 做过渡旁白对齐 |
| `reference_hook_asr.py` | 过渡旁白字级时间戳（venv: funasr） |
| `config_example_glacier.json` | 配置样例 |
| `template_tts_job.json` | 三句 TTS 作业模板 |

## 配置字段

| 字段 | 说明 |
|---|---|
| `enabled` | 开关；false 时下游跳过 hook，用旧片头 |
| `hook_line_1/2` | 两句钩子（配音用） |
| `display_text_1/2` | 两屏短文字，数组＝多行 |
| `transition_narration` | 过渡旁白（配音＋常规字幕），时长须与正文承诺一致 |
| `intro_assets` | **至少 2 张**背景图；每项含 `path`、`switch_s`、`zoom_start`、`zoom_end` |
| `bg_xfade_s` | 图片间叠化；0＝硬切（两张都有月亮/强主体时用硬切避免重影） |
| `font` / `font_size` / `font_size_1` / `font_size_2` / `text_color` / `stroke_color` / `stroke` | 字体与样式；`font_size_1/2` 为分屏字号 |
| `text_animation` | `scale_start`、`scale_end`、`whoosh_scale`、`whoosh_s`、`settle_s`、`zoom_ms`、`fade_in_ms`、`fade_out_s`、`y_drift_px` |
| `center_title` | 四字标题；空则不出 |
| `center_title_delay_s` / `center_title_s` | 标题相对过渡开口的延迟 / 停留秒数 |
| `voice_timing` | `head_s`、`gap1_s`、`gap2_s`、`tail_s` |
| `intro_duration` | `"auto"` 或手动秒数；auto＝三句实际时长＋留白 |
| `bgm` | 预留，当前 null |

## 命令

```powershell
# 0) 新单集：复制两个 reference 脚本到 run/scripts/
#    按 template_tts_job.json 改三句文案，生成 TTS
& $venvPy ...\gen_shots.py <run>\config\tts_job.json

# 1) 写本集 config（episode_ep + out + 文案/图/字号/标题）
# 2) 生成片头 + A/B 预览
$env:TMP='<run>\logs\tmp'
python <run>\scripts\hook_intro.py <ep>\configs\hook_intro_<episode>.json

# 3) 接入全片（不改默认片头）
$env:INTRO_VID='<run>\intro_av.mp4'
$env:INTRO_AUDIO='<run>\intro.wav'
python <run>\scripts\15_assemble.py
```

`15_assemble.py` 的 `INTRO_VID` / `INTRO_AUDIO` 默认指向 `intro_v2/`，不设环境变量即回退旧片头。

## 时间结构（glacier 实测）

| 段 | 时间 | 说明 |
|---|---|---|
| Hook1 大字 | 0.25–3.1 s | 语音 0.35–2.93 s；0.35 s 浮现 96%→100%，**不停顿**直接 1.7 s 到 110%，定格到句末；淡入 300 ms；不裁字 |
| Hook2 大字 | 3.28–9.35 s | 语音 3.38–9.12 s；3.3 s 背景硬切第二张 |
| 过渡旁白 | 9.67–32.82 s | 常规字幕，23.15 s；大字已退场 |
| 进入正文 | 33.13 s | 与正文 0.5 s 叠化 |

总长 33.13 s（Hook 型区间 30–35 s），过渡旁白不截断。

## 复用清单

- 只改 `configs/hook_intro_<episode>.json`：两句钩子、两屏短文字、过渡旁白、背景图、字号/动画/留白。
- `intro_duration` 随 TTS 变化；正文接入时字幕偏移必须按新片头时长重算，**不得全局平移**。
- 背景图必须来自本集已验收正文池或已授权静帧，不新生成。
