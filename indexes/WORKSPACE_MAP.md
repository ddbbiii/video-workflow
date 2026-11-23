# 工作区地图（2026-11-14 快照）

> 本文件只做现状快照，不改规范；目录真源是 `DIRECTORY_STRUCTURE.md`。
> 体积为 2026-11-14 估算，会随生产变化。

## 1 顶层

| 目录 | 体积（约） | 定位 |
|---|---:|---|
| `shared/` | 507 GB | 运行时、模型、工具、工作流、交换区 |
| `projects/` | 27 GB | 五条线路与单集 |
| `models/` | 14 GB | 本地模型 |
| `assets/` | 1.2 GB | 可复用素材 |
| `work/` | 2.2 GB | 多会话临时工作区（过渡） |
| `FindCity_AI_Photo_Library/` + `.7z` | 2 GB | 城市照片库（非视频线） |
| `音效库/` | 0.4 GB | 音效切片 |
| `rules/` `indexes/` `todos/` | <1 MB | 规则、索引、待办 |

## 2 空间构成

| 块 | 体积（约） | 说明 |
|---|---:|---|
| `shared/runtime` | 358 GB | comfy 258、engines 99（stills 49.5 / tts 49.2，tts 已不参与生产）、envs 1 |
| `shared/lip-tools` | 128 GB | 口型/换脸工具链，已不参与生产 |
| `shared/project-tools` | 14 GB | 工具、训练脚本、参考 |
| `shared/archive` | 3 GB | 旧退役线路归档（工作区内保留） |
| `projects/助眠解说` | 21 GB | `catching-a-second` 为主 |
| `projects/悬疑` | 3 GB | 两集 |
| `projects/人生体验` | 2 GB | 一集 |
| `shared/delivery` | 0.6 GB | **旧成品库，已废止**，待归档 |

## 3 成品与归档

- 成品：每集 `video/final/` 下同基名的正文 MP4 + SRT。
- `shared/delivery/finals/` 已废止；其中的旧文件不再维护，属于历史成品。
- 历史规则与工具归档在仓库旁：`../video-archive/20261114-body-only/`。

## 4 待处理

| 项 | 情况 |
|---|---|
| `shared/runtime/engines/tts`（49.2 GB） | 配音已由用户负责，可归档或删除；需单独决定 |
| `shared/lip-tools`（128 GB） | 不对口型，可归档或删除；需单独决定 |
| `shared/delivery`（0.6 GB） | 旧成品库，待整体归档 |
| `work/`（2.2 GB） | 一次性目录待清理 |
| `FindCity_AI_Photo_Library` + `.7z` | 非视频线，去留待定 |

## 5 历史

2026-11-05 至 11-13 的整理、迁移与删除记录见 `LAYOUT_MIGRATION.md`、`MIGRATION_MAP.md` 与 `shared/archive/`。本文件不重复。
