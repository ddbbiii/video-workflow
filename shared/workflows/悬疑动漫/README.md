# 悬疑动漫 · workflows

2026-10-10 视频号规划从 `projects\悬疑动漫\archive\legacy-line`、`archive\production` 迁来，属于 legacy 退役，见 `indexes\LEGACY_RETIREMENT.md`。
脚本里的路径已经按搬迁映射和时代替换改过，但**还没有重跑过**。

## 结构

- 共迁入 **125** 个脚本/配置。
- `xfer\`：原 `legacy-xfer`（夹克 LoRA、程午训练冒烟、overnight 等）
- `chengwu-turnaround\`：三视图 v1/v2 脚本与 jobs（含 xfer 侧副本）
- `mirror-who-are-you\`：assemble / audio / trial-plot
- `urban-anomaly\`：UA001/UA002 规划脚本与旧 return-bus 生成器

## 路径改写

- 依据 `projects\悬疑动漫\logs\legacy-migration-manifest.csv` 与 `legacy-migration-moves.log`。
- `archive\legacy-line`、`archive\production`、`series\` 下的素材指向 `episodes\` / `assets\悬疑动漫\` / `drafts\`。
- `comfy-stills` → `shared\runtime\engines\stills-runtime`
- GPU 锁 → `shared\work\cache\gpu.lock`
- 桌面 `grok-bot-xfer` 前缀 → `xfer\`（能对上 moves 的再落到 drafts/assets）
- `video\xuanyi`、根下散落的 `chengwu-turnaround-v*` → `projects\悬疑动漫\...`
- box `/workspace/chengwu-turnaround-v2`、`/workspace/chengwu-refs` → `drafts\chengwu-turnaround-history\`

改写统计：约 102 个文件有替换，合计约 260 处；另补修了 jobs.json 的 workspace 路径与注释里的 comfy-stills。

## 已知没解决的引用

1. `xfer\_move.ps1` 里生成 MOVE-LOG 标题仍写着历史字符串 `grok-bot-xfer -> xuanyi\legacy-xfer`（日志文案，不影响路径）。
2. `xfer\phase-ab-2026-09-23\RUN-V3-SPLIT.ps1` 注释里仍提到把脚本拷到桌面 `grok-bot-xfer\phase-ab-...` 的旧操作说明。
3. 许多冒烟脚本原先读桌面 `grok-bot-xfer\...` 素材；已改成 `xfer\...` 前缀，但 `E:\program\1project\video\xfer` 目录本身未必有这些文件（多已进 `drafts\` / `assets\`）。重跑前要按文件名在 drafts/assets 里核对。
4. `chengwu-turnaround\v1\scripts\run_ctv1.py`（及 xfer 副本）注释写「用 stills-runtime 的 python_embeded」；实际解释器路径以脚本内绝对路径为准。

## 说明

- 历史日志/报告里的旧路径未改。
- hardcoded 清单里 category=draft/episode/asset 的文件不在本目录，未改。
- 废稿已登记 LGCY-XY-001～010 后删除。
