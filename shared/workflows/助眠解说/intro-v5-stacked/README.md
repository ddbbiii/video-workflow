# 片头 v5 · 三句堆叠（短标题型）执行件

> 2026-11-04 定稿，来源 glacier-river v1.1。**规则看 `rules/助眠解说/intro.md` §6**；本文件只写执行步骤。

## 适用

需要片名感/主题句、时长 10–12 秒、正文已由助手烧录字幕的单集。不用于快钩/慢钩的文字卡型。

## 资产

| 资源 | 路径 |
|---|---|
| 手写字体（OFL 1.1） | `assets/助眠解说/intro/fonts/BaoCanMouHuiTing-Regular.ttf` |
| 基准成片 | glacier-river `runs/20261103-gla-b01/intro_v2/clean-intro.mp4`（10.59 s） |
| 实现 | 本目录 `reference_build_intro_v2.py`、`reference_realign_subtitles.py`、`template_tts_job.json` |

## 步骤

1. 锁三句文案（≤10/12/8 字，场景→事实→定性），用户定稿。
2. 生成三条 TTS：同一已批准声线/seed/cfg，`gen_shots.py` 三个 shot；trim（−45 dB/20 ms/0.10/0.15）+ atempo（见 `rules/助眠解说/audio.md`）。
3. 拼片头音轨：head 0.60 s + L1 + 0.55 s + L2 + 0.60 s + L3 + tail 1.60 s；记录 `intro_timeline.json` 每句 `start_s/end_s`。
4. 渲染：复制 `reference_build_intro_v2.py`，改顶部 CONFIG（字体、背景、三句、路径）后运行。
5. 接正文：正文起点＝片头实测时长；重拼 clean + narration，不沿用旧偏移。
6. 重做字幕：复制 `reference_realign_subtitles.py`，改 CONFIG；对最终 body 音轨做逐单元 DP 字符对齐，再加用户校准的全局偏移。**禁止只对旧 cues 做整体平移。**
7. QA：逐句状态帧、黑帧/白帧、音视差 ≤1 帧、字幕首条落在正文第一句、总时长＝片头＋正文＋尾留白。

## 坑位

- 描边必须整行先描边再整行填字；逐字描边会压掉相邻笔画。
- 文字只做整行 y 位移与 alpha，不做缩放/旋转；逐帧 scale 会抖。
- 手写体只用于片头，正文烧录仍用 Source Han Sans SC Heavy。
- 片头时长变化后字幕必须重对齐；用户说“偏早/偏晚”时只调全局偏移。
- 字体 22 MB，不要打进正文渲染，只在片头帧渲染时用。

## 产物命名

```text
episodes/<episode>/runs/<run>/intro_v2/{intro.wav,intro_timeline.json,clean-intro.mp4,frames/}
episodes/<episode>/runs/<run>/subtitles/r4/{cues.json,body.srt,body.ass,burn/}
```
