# 视频工作区

整个工作区采用 `projects/`、`assets/`、`rules/` 分层布局，目录真源：`indexes/DIRECTORY_STRUCTURE.md`。

- `projects/对应线路/`：项目、单集、草稿、日志、归档。
- `assets/对应线路/`：可复用角色、场景和道具。
- `rules/对应线路/`：线路规则；`rules/shared/`：全局规则。
- `shared/`：工具、工作流、运行时、GPU 队列、交换与工作目录。
- `indexes/`：线路、文档、资产索引。
- `todos/`：全部线路和共用事项的统一待办入口。

## 交付口径（2026-11-14 起）

**每集只交两件：正文视频 + 同基名 SRT。**

- 视频：`projects/<线路>/episodes/<集>/video/final/<线路>_<中文剧名>_正文_vN.mp4`，只含完整正文，无片头、无标题、无字幕、无文字层、无音轨、无字幕流。
- SRT：同集 `video/srt/`，覆盖正文、`00:00:00,000` 起、每条 ≤20 字、估算时间轴。
- 配音、混音、BGM、字幕烧录、封面、发布全部由用户手动。
- 不落成品库、不写成品卡、不登记索引。
- 规则见 [`rules/shared/delivery.md`](rules/shared/delivery.md)、[`rules/shared/srt.md`](rules/shared/srt.md)；流程见 [`rules/shared/video-workflow.md`](rules/shared/video-workflow.md)。

线路为助眠解说、悬疑、小球、人生体验、萌宠；状态见各项目 `LINE_STATE.md`。退役线路（猎奇、音乐线、抖音特效）与外卖之谜、potato-grow-test 已整体归档到 `shared/archive/retired-lines-20261110/`，不再维护。

历史规则、旧片头/TTS/烧录工具链归档在工作区外：`E:\program\1project\video-archive\20261114-body-only\`。默认不读，只有用户点名才恢复。

根目录规范包含 `projects/`、`assets/`、`rules/`、`indexes/`、`shared/`、`todos/` 和本文件。完整职责见 `indexes/DIRECTORY_STRUCTURE.md`。
