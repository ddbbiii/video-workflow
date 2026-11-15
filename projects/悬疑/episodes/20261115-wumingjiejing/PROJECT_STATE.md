# PROJECT_STATE — 《无名捷径》

- 日期：2026-11-15
- 状态：已交付正文 MP4 + SRT；正式文件最终 QA 全部 PASS
- 来源：用户确认的原创剧本《无名捷径》终修版
- 旁白锁定：以对话中用户确认的终修版为准，落盘于 `story/script-v1.md`；68 句、1,727 可见字，lint PASS（`画面里`按原文 literal 标注）
- 画幅：16:9；悬疑线风格使用 `rules/悬疑/visual.md` 原始风格块
- 角色：`linxu-20261115-episode`，本集新建成年男性，复用检查见 `storyboard/REUSE_FIT_CHECK.md`
- 视觉素材：独立 GPT 图片 API；内置/本地文生图均不作替代
- UI 处理：导航界面、路线、时间、门禁通知均以无字抽象屏幕图形表达，具体文字和轨迹在后期确定性合成
- 分镜数据：`storyboard/SHOT_PLAN.json`；比例预检 E/M/C = 12/24/12（25/50/25%）
- 当前结果：48/48 镜静帧通过像素门禁；S46 使用 `S46-retry4.png`，native lap_var 84.7、1080p delivery lap_var 99.3
- 时间线：3.6 字/秒估算 496.387 秒；48 镜 affine 60fps；7 镜（S05/S28/S30/S32/S36/S47/S48）确定性定位点动态
- 正式交付：`video/final/悬疑_无名捷径_正文_v1.mp4` + `video/srt/悬疑_无名捷径_正文_v1.srt`
- 正文视频：496.375 秒 / 11,913 帧 / 24fps / H.264 1920x1080；1 视频流、0 音频流、0 字幕流；CFR PASS，连续黑白屏均为 0
- SRT：68 句原文拆为 125 条；最大 20 字、宽度/时间/首末时间均 PASS；一条锁定原文无断句标点，按词边界例外拆分，G1 文本一致
- 当前报告：`image/qa/REPORT.md`、`image/qa/FINAL_QA.json`、`qa/video.json`、`qa/pixel_scan.json`、`qa/delivery.json`、`qa/srt.json`、`qa/srt_qa.md`、`qa/dynamic-motion.json`
- 生成节奏：人物锚点 → 6 镜平涂度小样 → 批次静帧 → 定位点动态 → 正文合成；自动化交付门禁全部通过

## 资产目录

- `image/anchors/`：人物 turn sheet 与参考裁格
- `image/backgrounds/`：含人物镜先生成的无人环境底图
- `image/stills-raw/`：最终静帧原图与 API 响应 sidecar
- `image/composites/`：场景底图与人物参考的临时合成输入
- `image/qa/`：联系表、报告和像素门禁结果
- `video/motion-v1/`、`video/motion-ui-v1/`：affine 镜头与关键定位点动态；`video/review/`：待审核候选
- `qa/`：旁白 lint、动态镜头和候选视频 QA 报告

## 关键待验

- 静帧门禁：48/48 PASS；S46 旧尝试保留，当前 `image/manifest.json` 指向通过的 retry4
- 正文门禁：正文候选已按用户“继续跑到出成品”指示推进并完成正式交付；定格镜头的抽象 UI 仅以无字图形和确定性定位点表达
- 当前无待交付项；候选与中间文件保留在 `video/review/` 以供追溯
