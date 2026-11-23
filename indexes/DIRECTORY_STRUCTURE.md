# 当前目录结构

本文件是整个 video 仓库的目录真源（2026-11-14 纯正文版）。

```text
video/
  projects/
  assets/
  rules/
  indexes/
  shared/
  todos/
  README.md
```

根目录只允许以上六个目录和 `README.md`。不得在根目录保留运行时、缓存、归档、交换、临时目录或兼容别名。

隐藏目录 `.git/`、`.acl-reports/`、`.codex-memory/`、`.workbuddy/` 属工具与审计。`work/` 为既存过渡目录（2026-11-10 起），任务结束后并入 `shared/work/`；`FindCity_AI_Photo_Library/` 与其 `.7z` 为非视频线照片库，去留待定。除这些之外不得新增根级目录。

## 目录职责

- `projects/`：按线路存放项目、单集、草稿、日志和项目归档。
- `assets/`：按线路存放可复用资产；跨线路共用资产存入 `assets/shared/`。
- `rules/`：按线路存放规则；跨线路规则存入 `rules/shared/`。
- `indexes/`：只存目录真源、线路/资产索引、迁移和核验报告等入口文档，不存执行脚本或生产资产。
- `shared/`：共用工具、工作流、运行时、模型、缓存、交换目录与临时工作区。
- `todos/`：所有线路及共用事项的待办唯一真源；总入口 `todos/README.md`。
- 根 `README.md`：工作区总入口并链接本目录真源。

## 单集目录

```text
projects/<线路>/episodes/<集>/
  PROJECT_STATE.md     当前阶段、已完成、下一步
  story/               锁定稿、大纲、事实笔记、旁白
  storyboard/          分镜表、事实约束卡、角色锁
  image/               静帧、参考图、贴片、联系表
  video/
    final/             正文 MP4 与对应的同基名 SRT（两件交付物）
    motion/            动态分段与轨迹
    *.py / *.json      拼装脚本、motion_plan、timeline
  qa/                  交付级 QA：ffprobe、像素扫描、SRT 报告
  logs/                运行日志、manifest
```

- 单集不再产出 `audio/`、`intro/`、`subtitles/`、`delivery/`；如用户自己放入配音，放 `audio/` 即可，助手不读写。
- 旧单集里既存的 `audio/`、`intro/`、`subtitles/` 保持原样，不回改、不移动。

## 成品与归档

- 每集只有两件成品：`video/final/` 下同基名 `<线路>_<中文剧名>_正文_vN.mp4` 与 `.srt`。
- 不再有 `shared/delivery/finals/` 成品库、成品卡与成品索引。
- 历史归档在仓库旁：`../video-archive/`。`shared/archive/` 只保留旧退役线路，默认不读。

## 维护

- `rules/` 的拆分与引用见 `rules/shared/document-organization.md`。
- 线路清单见 `LINE_INDEX.md`；资产入口见 `ASSET_REGISTRY.md`；迁移记录见 `LAYOUT_MIGRATION.md`。
