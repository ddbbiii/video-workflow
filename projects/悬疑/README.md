# 悬疑线 · 项目入口

> 规则真源在 `rules/悬疑/`，本目录只放单集、planning 与视觉测试。

当前选材入口：[`planning/CURRENT.md`](planning/CURRENT.md)。2026-11-19 用户已废弃全部旧的未开做故事，旧候选与旧 shortlist 不再作为制作输入；归档见 [`archive/未开做故事废弃-20261119/README.md`](archive/未开做故事废弃-20261119/README.md)。

## 目录

```
projects/悬疑/
  README.md          本文件
  LINE_STATE.md      线路当前状态
  planning/          大纲、素材候选
  visual-tests/      画风、滤镜、分镜切换测试
  episodes/          正式单集
```

## 开工顺序

1. 选素材先按 `../../rules/悬疑/story-selection.md` 判定素材类型、完成 100 分评分并选定叙述视角；再读 `../../rules/悬疑/input-spec.md`，填 8 项必填；
2. 读 `../../rules/shared/video-workflow.md`（最高优先级）；
3. 读 `../../rules/悬疑/production.md`，建单集目录；
4. 写稿前先出「故事主线大纲 + 悬念预算表 + 总字数预算」，过门禁 A；
5. 分镜批量前锁 2×2 拼版三视图与 `storyboard/CHARACTER_LOCK.md`；
6. 交付范围先读 `../../rules/悬疑/delivery.md`；正文 SRT 与技术 QA 按 `../../rules/shared/srt.md`、`../../rules/shared/delivery.md`。

## 当前

- `episodes/20261112-tuoshui/`：《脱水超重》旧口径 v5 已出（271 MB），不回改。
- `episodes/20261112-feigongdan/`：《废弃工单》旧口径 v1 已出（114 MB），不回改。
- 旧成品在 `shared/delivery/finals/`，属于历史文件，不移动、不重制、不再当模板。
- 早期各集（病历/镜子/夜跑/泳池/旧熊）的工程已不在工作区，只在旧记录里存在，不再维护。

## 边界

- 新集交付引入图片、正文视频、正文字幕；引入不做字幕、不剪入正文视频。规则真源：`../../rules/悬疑/delivery.md`。不做配音、混音、烧录、封面、成品库。
- 单集特例写进该集 `PROJECT_STATE`。
