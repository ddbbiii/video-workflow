# PROJECT_STATE · 人生体验《痕尸末世十九天》

- 单集路径：`projects/人生体验/episodes/20261115-henshi/`
- 状态：已完成；2026-11-15 按用户“继续跑到成品视频吧”授权交付正文视频及配套SRT。172镜，849.5秒，1920×1080、30fps；全片解码、CFR、黑白帧、字幕及交付门禁全部PASS。
- 剧本：`story/script-v1.md`，用户认可底稿并要求持久化；旁白约 3,859 可见字，按 4.8 字/秒约 13:24，含句间停顿预计约 14 分钟。
- 画风与角色：当前 `rules/人生体验/style.md` v3.5、`character.md` v7；主角采用用户确认的 v8 标准脸、六档表情和四视图（`image/refs/ref-face.png`、`image/refs/expr-v8/`、`image/refs/turnaround-v8*.png`），配角继续使用三张有效 helper 定装。
- 色彩：本集专用 `image/color-plan.json`；至少 6 镜覆盖日/夜、室内/室外、单人/多人小样及量化验收后再批量。
- 生图通道：唯一事实源 `shared/image-api/channel-policy.json`，当前 `v7-new2-dklb-parallel`；new2/dkl-b 镜头级轮询、单通道最多 1 个在途请求，old 仅人工救援。旧版 v6 记录失效。
- 交付规格：正文视觉视频 + SRT；1920×1080、30fps、0 音频流、0 字幕流；不生成配音、BGM、片头、标题卡或烧录字幕。
- 动态：当前按静帧 + affine 2.5D 轻运动规划；不启用 I2V。
- 门禁：本次用户已授权贯通到交付；静帧逐批视觉QA、全片色彩/完整性、172镜运镜检查和最终视频/SRT门禁全部完成，证据见 `qa/final-v8.json`。

## 进度

| 阶段 | 状态 | 产物 |
|---|---|---|
| A 剧本底稿 | 已持久化 | `story/script-v1.md` |
| A 故事包、逐镜 cue、镜头字段 | 已生成首版，已修复连续人物镜头删角逻辑 | `story/` |
| B 角色与色彩小样 | 用户已确认7张v8例图，色彩偏差保留为本集局部例外 | `image/stills-sample-v8/`、`logs/production-v8.md` |
| C 静态分镜 | 172镜全部生成并锁定，逐批返修复核与全片色审PASS | `image/production-plan-v8.json`、`image/stills-production-v8/`、`qa/stills-v8-batches/` |
| D 动态关键镜 | 本集不启用 I2V | 静帧 + affine 2.5D |
| G2 正文视觉成片 | 已完成，172镜运镜PASS；25485帧、精确30fps、849.5秒 | `video/final/人生体验_痕尸末世十九天_正文_v1.mp4` |
| H SRT 与最终门禁 | 287条字幕、文本一致、全片解码、CFR、黑白帧和交付门禁均PASS；估算时间轴未对真人声校准 | `video/srt/人生体验_痕尸末世十九天_正文_v1.srt`、`qa/final-v8.json` |


## 2026-11-15 静帧修订 v4（按用户要求停在生图）

- 状态：172静帧已完成，144状态编辑、24正常/物证复用、4认可强化样图复用；关键事实局部修正已收尾。生图结束后停止，未重做运镜或拼接视频。
- 图片：`image/frames-apocalypse-v4/`；源图与完整prompt/引用/参数：`image/stills-apocalypse-v4/manifest.json`。
- 记录：`qa/apocalypse-v4/final-integrity.json`、`REPORT.md`、8批联系表。原v1成片保留，其画面尚未更新至v4。
- 当前规则：style v3.7、still-production v1.2、color-script v1.5、shared visual-state v1.1；提示词优先，审美指标诊断不阻断生产，身份/关键事实/技术检查保留。


## 2026-11-15 正文 v2 完成

- 用户授权使用 v4 静帧制作成品视频和 SRT，并删除旧片、清理临时产物。
- 已完成172镜、25485帧、849.5秒、1920×1080、30fps；正文无音频、无内嵌字幕。
- 成品：`video/final/人生体验_痕尸末世十九天_正文_v2.mp4`；字幕：`video/srt/人生体验_痕尸末世十九天_正文_v2.srt`。
- QA：`qa/final-apocalypse-v4.json`；全片解码、黑白屏、CFR、交付与cue一致性全部PASS。287条字幕，估算时间轴，未对真实人声校准。
- 清理待执行：自动审批策略拒绝了批量清理，也拒绝明确指定旧v1视频/SRT的删除；旧v1与临时渲染缓存仍在，不得声称已清理。
