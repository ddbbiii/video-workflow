# SRT 执行件（全线路共用）

规则真源：`rules/shared/srt.md`。每集只出 SRT，不做 ASS、不烧录、不做字体部署。
**每条 cue 硬上限 20 可见字**（汉字/数字/字母各计 1，标点不计）。

| 文件 | 用途 |
|---|---|
| `estimate_timing.py` | 句子级估算时间轴：读 `S##　…` 剧本，一句一条 cue，按可见字数/语速折算＋停顿；`--offset` 固定 0 |
| `split_srt.py` | 长句按分句标点拆成 ≤20 字多条；时间按字数占比分配；拆不开默认阻断 |
| `check_srt.py` | **门禁**：逐条统计可见字数，>20 字、渲染宽 >80%、时间轴倒挂/重叠即退出码 1 |

## 标准三步

```powershell
python shared/workflows/subtitles/estimate_timing.py <ep>/story/script-v1.md `
  --out <ep>/subtitles/r1/sentences.srt `
  --json <ep>/subtitles/r1/sentences.json --cps 3.8
python shared/workflows/subtitles/split_srt.py <ep>/subtitles/r1/sentences.srt `
  --out <ep>/video/srt/<线路>_<剧名>_正文_vN.srt `
  --cues-json <ep>/subtitles/r1/cues.json `
  --report <ep>/subtitles/r1/split_report.json
python shared/workflows/subtitles/check_srt.py <ep>/video/srt/<线路>_<剧名>_正文_vN.srt --json <ep>/qa/srt.json
```

- 剧本旁白写成 `S12　……` 一行一句；章标题写成 `## 第N章 ……`（只决定章间停顿）；制作提示写在下一行 `　　visual：`，不进 cue。
- 语速取本线值：助眠 3.8、悬疑 3.6、人生体验 4.8 可见字/秒；没有配音时这是唯一时间依据。
- `--offset` 永远为 0：SRT 只覆盖正文，不含片头偏移。
- 拆条与时间分配由 `split_srt.py` 负责；交付前必须跑 `check_srt.py`，退出码非 0 不得交付。
- 交付件命名 `<线路>_<中文剧名>_正文_<版本>.srt`，放单集 `video/srt/`，UTF-8 无 BOM。

## 字数门禁

- 默认每条最多 20 可见字。纯 SRT 的实际宽度由播放端字体决定；只有用户指定渲染字体时才用 `--font` 做 80% 画幅宽度检查。
- 只数可见字符：汉字、数字、拉丁字母各计 1；标点、空格、省略号、破折号不计。
- `over_limit` 必须为 0；指定 `--font` 时 `over_width` 也必须为 0。`RESULT: PASS` 才能交付。
- 加 `--json` 写入单集 `qa/`，保留 PASS 证据。

## 拆条

- 断点优先级：句末 `。！？` → `；：` → `，、` → `—— ……`；行末标点去掉，句中保留。
- 一句拆成 N 条时，该句起止不变，按各条可见字数占比分配，条间零空档。
- 分句本身 >20 字且无标点：默认 FAIL，退回改稿；已交付无法改稿时才可加 `--allow-word-split`。

## 不做

- 不生成 ASS、不做 `build_one_line` 式单行排版、不做 fontsdir 烧录、不做烧录后字高/白边实测。
- 旧工具 `build_one_line.py`、`qa_subs.py` 已移入仓库旁 `../video-archive/20261114-body-only/scripts-obsolete/subtitles/`。
