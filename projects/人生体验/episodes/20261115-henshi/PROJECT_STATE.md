# PROJECT_STATE · 人生体验《痕尸末世十九天》

- 单集路径：`projects/人生体验/episodes/20261115-henshi/`
- 状态：生产中；用户于 2026-11-15 指示启动全流程。
- 剧本：`story/script-v1.md`，用户认可底稿并要求持久化；旁白约 3,859 可见字，按 4.8 字/秒约 13:24，含句间停顿预计约 14 分钟。
- 画风与角色：当前 `rules/人生体验/style.md` v3.5、`character.md` v7；主角采用用户确认的 v8 标准脸、六档表情和四视图（`image/refs/ref-face.png`、`image/refs/expr-v8/`、`image/refs/turnaround-v8*.png`），配角继续使用三张有效 helper 定装。
- 色彩：本集专用 `image/color-plan.json`；至少 6 镜覆盖日/夜、室内/室外、单人/多人小样及量化验收后再批量。
- 生图通道：唯一事实源 `shared/image-api/channel-policy.json`，当前 `v7-new2-dklb-parallel`；new2/dkl-b 镜头级轮询、单通道最多 1 个在途请求，old 仅人工救援。旧版 v6 记录失效。
- 交付规格：正文视觉视频 + SRT；1920×1080、30fps、0 音频流、0 字幕流；不生成配音、BGM、片头、标题卡或烧录字幕。
- 动态：当前按静帧 + affine 2.5D 轻运动规划；不启用 I2V。
- 门禁：G0 剧本/分镜数据；静帧逐 24 镜验收；G2 正文视觉成片由用户审核后再生成 SRT 与交付。

## 进度

| 阶段 | 状态 | 产物 |
|---|---|---|
| A 剧本底稿 | 已持久化 | `story/script-v1.md` |
| A 故事包、逐镜 cue、镜头字段 | 已生成首版，已修复连续人物镜头删角逻辑 | `story/` |
| B 角色与色彩小样 | v3 六镜已生成，未验收；亮度和章级色相门禁失败，等待用户审阅 | `image/refs/ref-face.png`、`image/refs/expr-v8/`、`image/refs/turnaround-v8*.png`、`image/stills-v3-pilot/`、`image/frames-v3-pilot/`、`qa/pilot-v3-contact.jpg` |
| C 静态分镜 | 暂停在小样门禁，未启动全片 | `image/stills-v3-pilot/` |
| D 动态关键镜 | 本集不启用 I2V | 静帧 + affine 2.5D |
| G2 正文视觉成片审核 | 待开始，需用户审核 | `video/final/` 临时审核版本 |
| H SRT 与最终门禁 | 待 G2 通过 | `video/srt/`、`qa/` |

