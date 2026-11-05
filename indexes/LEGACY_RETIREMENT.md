# legacy 目录退役方案

老大 2026-10-08 定：各线 legacy 目录统一整理后不再保留。本文件是这次搬迁的唯一规则，由视频号规划维护。

## 要退役的目录

- `projects\助眠解说\legacy-source\`
- `projects\创意\legacy-source\`（2026-10-08 已退役删除）
- `projects\猎奇\legacy-source\`（2026-10-08 已退役删除）
- `projects\悬疑动漫\archive\legacy-line\`、`projects\悬疑动漫\archive\legacy-series\`、`projects\悬疑动漫\archive\production\`（2026-10-10 一并退役）

## 东西放哪

| 类别 | 目标位置 |
|---|---|
| 一集的成片、通过抽验的版本、当前草稿 | `projects\<线>\episodes\<集>\video\` |
| 被取代的旧版本 | `projects\<线>\episodes\<集>\archive\` |
| 脚本、文案、时间轴 | `episodes\<集>\story\` |
| 分镜、镜头表 | `episodes\<集>\storyboard\` |
| 首帧、静帧、封面 | `episodes\<集>\image\` |
| 配音、字幕、音效 | `episodes\<集>\audio\` |
| i2v 和运镜镜头片段 | `episodes\<集>\video\clips\` |
| 质检报告、人工听看清单 | `episodes\<集>\qa\` |
| 运行日志 | `episodes\<集>\logs\` |
| 集的状态文档 PROJECT_STATE.md | `episodes\<集>\` 根目录 |
| 成不了一集的试验 | `projects\<线>\drafts\<名字>\` |
| 跨集复用的声线、角色、风格参考、BGM | `assets\<线>\` |
| 脚本代码、配置、workflow json | 不自己搬，列进清单，由视频号规划移进 `shared\workflows\<线>\` 并改路径 |
| 临时文件、缓存、失败的半成品 | 不自己删，列进清单，由视频号规划登记 DISCARDS 后删 |

集名用英文短名，沿用 legacy 里原来的目录名（例如 `b-geomagnetic-reversal`、`tudou`、`a-space-cat`、`mirror-who-are-you`）。

## 流程

1. 各线把自己的 legacy 目录列成清单，放在 `projects\<线>\logs\legacy-migration-manifest.csv`，列：源路径、目标路径、类别（episode / asset / draft / script / discard）、大小。
2. 视频号规划看过清单后回复可以搬。
3. 各线自己搬，只用同盘移动，不复制、不建链接。正在跑的任务先跑完再搬。
4. 搬完把 PROJECT_STATE.md、LINE_STATE.md 里的路径改过来，核对没缺东西，在群里报一声。
5. 视频号规划处理 script 和 discard 两类，确认 legacy 目录已空后删掉空目录。

## 已完成

2026-10-08 视频号规划已经先把四条线通过抽验的成片挪进 episodes：

- `projects\悬疑动漫\episodes\mirror-who-are-you\video\mirror_no_lip_i2v_v1.mp4`、`mirror_no_lip_v1.mp4`
- `projects\猎奇\episodes\tudou\video\lieqi_tudou_final_v3.mp4`
- `projects\创意\episodes\a-space-cat\video\a_space_cat_final_v6.mp4`

原位置各留了一个 MOVED.txt 说明去向。
2026-10-08 创意、猎奇的 legacy-source 已清空删除：脚本移进 `shared\workflows\创意\`、`shared\workflows\猎奇\`（路径已改，未重跑，未解决的引用见各自 README.md），废稿登记为 LGCY-CY-001～025、LGCY-LQ-001～046 后删除，共释放约 1.45 GB。
2026-10-08 助眠解说的 legacy-source 已基本清空。
- 脚本移进 `shared\workflows\助眠解说\`，路径已改，还没重跑，未解决的引用见该目录的 README.md。
- 口播检查环境移到 `shared\runtime\envs\vo-gate\`。
- 废稿和重复件登记为 LGCY-ZM-001～024 后删除，释放约 11.49 GB。
- 目录暂时保留，里面只剩 PotPlayer 占用的 2 个成片（等助眠补搬到本集 `video\`）和 1 份 GPU 请求记录原件。

2026-10-10 悬疑动漫 `archive\legacy-line`、`archive\legacy-series`、`archive\production` 与 `series\` 已退役：
- episode/asset/draft 由悬疑搬完（见 `projects\悬疑动漫\logs\legacy-migration-exec-report.md`）。
- 脚本 125 个移进 `shared\workflows\悬疑动漫\`（路径已改，未重跑，见该目录 README.md）。
- 废稿登记为 LGCY-XY-001～010 后删除，释放约 1.91 GB。
- `archive\legacy-line`、`archive\production`、`series\` 空目录已清；`legacy-series` 此前已删。

2026-10-10 助眠解说 legacy-source 空目录链已删（成片已在 episodes\\b-geomagnetic-reversal\\video\\）。
