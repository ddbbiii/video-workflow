# SRT 规范（纯正文版）

> 2026-11-14：SRT 只覆盖正文，时间轴从 0 开始，不再有片头偏移。旧字幕规范（style_r4、ASS、fontsdir、烧录、G1–G7）已归档；本文件只保留 SRT 必需的规则。

## 一、范围

- 只覆盖**正文**：第一条 `00:00:00,000` 开始，末条结束于正文最后一帧附近。
- 不含片头、引言、标题、章节名、账号名、片尾；画面里也不出现这些文字。
- 文本只取锁定稿的旁白字段 `cue`；画面提示、镜头备注、制作术语一律不进 SRT。
- 出 SRT 前必须跑 `python shared/workflows/script-qa/lint_narration.py <script.md> --json`，0 命中才继续。

## 二、字数与断句

- **每条 ≤20 可见字**：汉字、数字、拉丁字母各计 1；标点、空格、省略号、破折号不计。
- 单行，不换行；渲染宽度 ≤画幅 80%。
- 只在分句标点处拆：`。！？` → `；：` → `，、` → `—— ……`；不按字符硬切。
- 一句拆成多条时，该句起止不变，按各条可见字数占比分时，条间零空档、零重叠。
- 全部 cue 去标点按序拼接，必须与锁定正文完全一致（G1）。

## 三、时间轴

- 没有配音可对齐，时间轴按**估算语速**排：助眠 3.8 字/秒、悬疑约 3.6、人生体验 4.8。
- 句间停顿默认 0.24 s，章间 0.90 s，单句最短 0.90 s；按各线 `audio.md`（只留语速）取当前值。
- 与画面共用同一份 `timeline.json` / `cues.json`，保证 SRT 与镜头互相对得上。
- 交付时必须注明「估算时间轴，未对真实人声校准」；不得声称已对轨。
- 用户配音后若改总时长，SRT 需按实测重排；这属于可选委托，不自动执行。

## 四、命令

```powershell
# 1) 句子级估算时间轴（--offset 固定为 0）
python shared/workflows/subtitles/estimate_timing.py <ep>/story/script-v1.md `
  --out <ep>/subtitles/r1/sentences.srt `
  --json <ep>/subtitles/r1/sentences.json --cps 3.8

# 2) 拆到 ≤20 字
python shared/workflows/subtitles/split_srt.py <ep>/subtitles/r1/sentences.srt `
  --out <ep>/video/srt/<线路>_<剧名>_正文_vN.srt `
  --cues-json <ep>/subtitles/r1/cues.json `
  --report <ep>/subtitles/r1/split_report.json

# 3) 门禁
python shared/workflows/subtitles/check_srt.py <ep>/video/srt/<线路>_<剧名>_正文_vN.srt --json <ep>/qa/srt.json
```

- `check_srt.py` 退出码非 0 不得交付；`over_limit`、`over_width`、时间轴倒挂/重叠必须为 0。
- 分句本身 >20 字且无标点：默认 FAIL，退回改稿；已锁定无法改稿时才可加 `--allow-word-split`，并在报告披露。

## 五、验收与留档

- 单集 `qa/srt_qa.md` 至少写：cue 数、锁定句数、最大字数、最大渲染宽、`check_srt.py` PASS 输出、首末条时间、估算说明。
- SRT 与视频同基名、分目录：视频 `video/final/`，SRT `video/srt/`。
- 不生成 ASS；不做烧录；不做字体部署；不跑 ASR。
- 用户委托对轨/烧录时，按当次委托单独处理，不沿用估算时间轴，也不恢复旧 style_r4 默认流程。
