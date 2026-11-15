# 人生体验线路状态

- 状态：active；EP03「三重死则」**旧成片与静帧已全部删除**（2026-11-15），待按 style v3.4（两层画风）/ character v7（配角简笔圆头小人）/ color v1.3（三色相）整集重出。
- EP02「土木工程」正文 v5 是旧口径（含 15.9 s 片头 + 标题页），按 2026-11-14 指令不回改、不重制。
- 更新：2026-11-15 03:50（清空旧产物 + 画风定稿 v3.4）。

## 规则现状

| 文件 | 状态 |
|---|---|
| `README.md` | 纯正文口径；已登记镜头配比规则 |
| `style.md` | **v3.5**：两层画风（人物平涂 / 环境允许渐变材质多光源）+ 去人读图/锚点/负向清单 |
| `character.md` | **v7**：主角 v7 四视图（猫爪赤脚）+ 配角简笔圆头小人 |
| `color-script.md` | **v1.4**：色相按章统计（章均 ≥3、不许整片单色、可 muted），R/B ≤1.15 |
| `../shared/shot-composition.md` | E/M/C 22/53/25，门禁 `check_shot_mix.py` |

## 现有单集

- `episodes/20261114-sanzhong/`（EP03「你第三次重复就死了」）：**无成片**，数据与工具保留，待重出。
- `episodes/20261113-tumu/`：`video/final/人生体验_奖励自己一个土木工程_成片_v5.mp4` + `video/srt/…_成片_v5.srt`；`video/archive/`、`video/intro-v*.mp4`、`subtitles/r*` 为历史产物，保持原样。
- EP01 `20261110-biye/` 目录已丢失，只在旧记录里存在，不再维护。

## 下一步

1. 新集按 `rules/shared/video-workflow.md`：剧本 → 分镜 → 动态 → 门禁 1/2 → SRT → 交付；
2. 成片从正文第一帧开始，不做片头、标题页、章节卡；
3. 画风按 `style.md`，主角按 `character.md`，SRT 按 4.8 字/秒估算。

## 明确不做

- 片头、标题页、章节卡、账号卡、配音、混音、BGM、字幕烧录、封面、成品库、成品卡。
- 旧片头规则、`slice_intro.py`、`intro_mix.py`、`check_slice_intro.py` 已归档。
