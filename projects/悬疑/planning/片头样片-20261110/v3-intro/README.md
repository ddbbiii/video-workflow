# 悬疑片头 V3（2026-11-10）

> 用途：给用户看「引入沿用旧艺术字、标题换新艺术字、BGM 换 2026-11-10 定版」的样片。文案与时间轴沿用 V2，未锁定。

## 这一版改了什么

| 段 | 字体 | 字号 | 说明 |
|---|---|---|---|
| 引入（3 句钩子） | **Ma Shan Zheng**（旧） | 96 px，单行 | 回到 V1 观感：骨白、带标点、单行、140/120 ms 淡入淡出 |
| 标题（夜跑路线） | **香萃积雪宋**（新） | 450 px | 保留 V2 的压印 `fscx/fscy 120→100` + 100 ms alpha |
| 副标（第 一 集） | **Source Han Sans SC Heavy** | 88 px | V2 里用香萃字距过大、抢标题，这版换成正文字体 |

- 时间轴：0.35 / 4.00 / 7.79 s 三句钩子，10.79 s 标题，总长 13.917 s / 334 帧 / 24 fps。
- 背景沿用 V2 的 4 段 affine 运动与同一 GRADE，未重跑。
- BGM：`The Depths of Hell`（HPF 120）+ `ua006`（LPF 90），打击层手机频段 −10.5 dB rel 人声；保留 45 Hz + 140 Hz 棕噪的标题落墨冲击与标题处下压曲线。混后 −20.2 LUFS / TP −1.0。
- 音效：本版只有 VO + 标题冲击 + BGM，没有加低语/惊喘/尖叫层。

## 文件

- `sample_V3_intro.mp4`（13.917 s，1920×1080 / 24 fps / H.264 + AAC）
- `frame_hook1|2|3.png`、`frame_title.png`、`frame_slam.png`
- `timeline.json`：字体分配、BGM 参数、混音实测
- `build/intro_v3.ass`：ASS 源（Hook / Title / Sub 三个样式分别锁字体）

## 已知问题

1. **标题卡 10.79–13.92 s 没有口播**，与 `rules/shared/visual/cover-and-intro.md` §标题与口播的全线路硬规则冲突（当前悬疑线仍写「不做片头」，属规则例外；一旦这条片头定版，就必须补一句标题口播或让第三句钩子压进标题窗）。
2. 标题 450 px 单行占宽约 82%，略超 80% 的经验线，但不溢出安全区。
3. 文案是样片文案。

## 复现

```powershell
& 'E:\program\language\python\Python-3.11.0\python.exe' work/intro-sample-s1/build_v3.py
```

脚本只读 V2 的 `intro_bg.mp4`（背景运动）、`%TEMP%\intro-sample-s1\vo\hook{1,2,3}.wav`（旁白）与 BGM 库两条源曲，输出到本目录。
