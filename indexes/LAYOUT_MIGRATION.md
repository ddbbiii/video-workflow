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

## 线路收敛与根目录清理（2026-11-10）

用户确认当前只保留五条视频线：助眠解说、悬疑、小球、人生体验、萌宠。

| 原位置 | 新位置 | 说明 |
| --- | --- | --- |
| `projects/猎奇/`、`assets/猎奇/`、`shared/workflows/猎奇/` | `shared/archive/retired-lines-20261110/猎奇/{project,assets,workflows}/` | 整线归档冻结 |
| `projects/音乐线/`、`assets/音乐线/` | `shared/archive/retired-lines-20261110/音乐线/{project,assets}/` | 空壳线归档 |
| `projects/抖音特效/`、`assets/抖音特效/` | `shared/archive/retired-lines-20261110/抖音特效/{project,assets}/` | 空壳线归档 |
| `projects/unassigned/外卖之谜/`、`projects/unassigned/archive/外卖之谜/` | `shared/archive/retired-lines-20261110/外卖之谜/{project,archive-v1}/` | 未分配项目归档 |
| `projects/unassigned/potato-grow-test/` | `shared/archive/retired-lines-20261110/potato-grow-test/` | 测试工程归档 |
| `projects/unassigned/potato-staircase-test/` | `projects/小球/episodes/potato-staircase-test/` | 提升为小球线首个工程 |
| `4/` | `projects/助眠解说/episodes/glacier-river/` | 只改名移动，未改文件内容 |
| `编剧3/` | `projects/助眠解说/episodes/life-manual/` | 只改名移动，未改文件内容 |
| `5/` | `projects/助眠解说/episodes/birthday-paradox/` | 只改名移动；新增 README |
| `助眠/INPUT_shopping_100_yuan.md`、`助眠/NARRATION_shopping_100_yuan.txt` | `projects/助眠解说/episodes/shopping-100-yuan/`（后者在 `story/`） | 输入稿归位，`助眠/` 清空删除 |

- 逐条移动记录：`shared/archive/retired-lines-20261110/moves.json`。
- 未删除任何线路数据；归档区在 `shared/archive/` 下，按 `.gitignore` 不入库。
- **路径处理**：`glacier-river`、`life-manual` 单集脚本、concat 清单、配置与报告中原 `video\4\...`、`video\编剧3\...` 绝对路径，以及小球工程的 `projects\unassigned\potato-staircase-test` 路径，已按新目录批量替换（68 个文件，UTF-8 无 BOM）；仅 `PROJECT_STATE` 的历史说明保留旧位置文字。搬家同盘完成，媒体文件内容与 mtime 未变。
- 迁移后根目录为 `projects/ assets/ rules/ indexes/ shared/ todos/ README.md` 六项，`4/5/编剧3/助眠` 已不存在。
