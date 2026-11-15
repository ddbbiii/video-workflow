# 助眠解说线路状态

- 状态：active；最新单集 `episodes/catching-a-second`（《捕捉一秒钟》），旧口径 v1 已出（含片头），不回改。
- 更新：2026-11-14（规则收敛为纯正文）。

## 规则现状

| 文件 | 状态 |
|---|---|
| `README.md` | 已按纯正文重写：无片头/配音/烧录/成品库模块 |
| `input-spec.md` | v2.0：四项必填；交付 = 正文视频 + SRT |
| `production.md` | 账号、调度、检查点；门禁只剩两道 |
| `narrative.md` / `language-style.md` / `visual.md` | 可用 |
| `audio.md` | 只留 3.8 字/秒语速与停顿 |
| `delivery.md` | 30 fps、白边门禁、路径 |

## 现有单集

- `catching-a-second`：旧口径成片与 SRT 留在 `video/final/`、`video/srt/`；`intro/`、`runs/.../delivery`、`audio` 为历史产物，不移动、不回改。
- `antikythera-mechanism`、`banach-tarski`、`birthday-paradox`、`infinite-hotel`、`sky-boundary`：空壳占位，未开工。

## 下一步

1. 新单按 `input-spec.md` v2.0 填单（标题/主题/引入/章节大纲）；
2. 按 3.8 字/秒排镜头与 SRT；
3. 交付只放 `video/final/` 与 `video/srt/`。

## 明确不做

- 片头（E 版/Hook 版）、标题卡、交棒句；片头规则与执行件已归档。
- 配音、混音、BGM、字幕烧录、封面、成品库、成品卡。
