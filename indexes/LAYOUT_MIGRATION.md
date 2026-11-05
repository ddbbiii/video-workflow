# 目录迁移记录

- 完成日期：2026-10-07。
- 目标布局：projects/、assets/、rules/ 按线路分层，shared/ 继续承载工具与工作流。
- 备份：E:/codex-backups/video-layout-20261007-091120/（迁移前文本备份、文件清单及 move-map）。
- 最终迁移批次：E:/codex-backups/video-layout-20261007-091447/。
- 已迁移组数：31；迁移前清单：10,096 个文件。
- 核验：清单中所有文件在映射后路径存在；7,698 个常见二进制与媒体文件大小相同。文本文件更新了迁移前绝对/相对路径引用。
- 线路根级目录已移除；未建立指向旧路径的 junction 或符号链接。
- 外卖之谜移入 projects/unassigned/。
- 遇到的运行中 GPU 作业及播放器文件锁已等待/解除后再搬，不更改其队列状态。

恢复文本原件时先参考备份目录；不得直接把旧目录整体覆盖回新布局。

## 根目录收敛（2026-10-07）

- 根目录统一为 `projects/`、`assets/`、`rules/`、`indexes/`、`shared/` 与 `README.md`。
- 运行环境、模型、缓存、Syncthing 交换目录、临时目录、迁移脚本和根级启动器已归入 `shared/`；线路记忆归入 `rules/shared/memory/`。
- 迁移备份及原始清单：`E:/codex-backups/video-root-20261007-093236/`。
- 核验报告：`indexes/ROOT_MIGRATION_RESULT.json`，共 454,384 个文件，453,139 个文件大小复核，无缺失。
- Syncthing folder ID `grokbot-xfer` 已指向 `shared/exchange/sync/`，服务恢复且 folder 未暂停。
- `indexes/` 只保留索引、规范、迁移记录和机器可读核验结果；执行脚本归档到 `shared/project-tools/archive/layout-migration/`。
- 唯一 GPU 锁主路径为 `shared/work/cache/gpu.lock`；`shared/runtime/comfy/cache/gpu.lock` 仅保留为兼容性保护检查，两者不是 Junction 或同一文件。
