# 当前目录结构

本文件是整个 E:/program/1project/video 的目录真源。

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

## 目录职责

- `projects/`：按线路存放项目、剧集、草稿、日志和项目归档；未分配项目存入 `projects/unassigned/`。
- `assets/`：按线路存放可复用资产；跨线路共用资产存入 `assets/shared/`。
- `rules/`：按线路存放规则；跨线路规则及项目记忆存入 `rules/shared/`。
- `indexes/`：只存目录真源、线路/资产索引、迁移和核验报告等入口文档，不存执行脚本或生产资产。
- `shared/`：共用工具、工作流、服务、运行时、模型、缓存、交换目录、临时工作区和共用归档。
- `todos/`：所有线路及共用事项的待办唯一真源；总入口为 `todos/README.md`，按线路或主题按需拆分任务文件。
- 根 `README.md`：仅作工作区总入口并链接本目录真源。

线路索引是线路清单的事实来源，不在本文件重复维护线路名称。

项目内采用 README.md、LINE_STATE.md、episodes/、drafts/、logs/ 及按需的 archive/；项目内 characters/、assets/ 仅用于局部资料和引用，全线复用资产存 `assets/<线路>/`，不重复存储。

单集按需分 story/、storyboard/、image/、audio/、video/、qa/、logs/ 和 archive/。归档只改变状态，不改变目录职责。

共用素材在 `assets/shared/`；工具、服务、运行环境、模型、缓存、交换与临时目录均在 `shared/` 下按职责归类。不得建立指向已迁移旧路径的 Junction、符号链接或额外根目录。

MD 拆分由维护助手主动执行，见 `rules/shared/document-organization.md`。迁移记录见 `indexes/LAYOUT_MIGRATION.md`。
