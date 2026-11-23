# 《她只会叫我开门》项目状态

- 阶段：完成，当前有效交付为两张引入图片、正文视频、正文字幕。
- 引入：`story/INTRO.md`；图片在 `image/intro/v2/`，1920×1080，无文字，不剪入正文，不制作引入字幕。
- 正文：`video/final/悬疑_她只会叫我开门_正文_v2.mp4`，1920×1080、24fps、38镜、17,127帧、11:53.625，无音频和字幕流。
- 正文字幕：与视频同目录、同基名，170条，零起点；估算时间轴，未对真实人声校准。
- 正文稿：`story/script-body-v2.md`；分镜：`storyboard/SHOT_PLAN-body-v2.json`；角色：`storyboard/CHARACTER_LOCK.md`。
- 画面：低饱和赛璐璐；怪物多嘴仅在脸部。使用静帧与浮点 affine 运镜，未使用 I2V。
- QA：`qa/v2/delivery.json`、`pixel_scan.json`、`final-integrity.json` 与 `qa/intro-v2.json` 通过。
- 生产依赖：当前正文逐镜素材、角色参考及 `logs/current-assets.json`；被替代版本、候选和废弃稿已清除。
- 交付规则：`rules/悬疑/delivery.md`。
