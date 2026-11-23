# CHARACTER_SPEC — zhouning-20261118-xinwen

- 姓名：周宁
- 档位：A 主角
- 资产形态：2×2 拼版（正面 / 侧面 / 背面 / 面部）
- 适用：episode-only
- 首次出现：20261118-xinwen-gengxin 第 1 镜
- reuse-policy：soft；本集新建，不跨集复用

## 固定提示词

- 中文：28 岁中国女性，身形匀称偏瘦，齐肩直黑发、中分，偏长脸、窄眼、直眉；穿暗红色薄家居外套、深灰针织上衣、黑色长裤、黑色布鞋；无首饰、无眼镜、无痣疤。
- English: one Chinese woman aged 28, lean average adult build, straight shoulder-length black hair with a center part, long oval face, narrow dark eyes, straight brows, muted dark-red home cardigan over a charcoal knit top, black trousers, plain black cloth shoes, no jewelry, no glasses, no distinctive marks.
- 负面词：按 `rules/悬疑/visual.md` 的 `STYLE_NEG` 原文。
- 模型 / seed：gpt-image-2.5-sunburst；seed 未由服务端提供。
- 参考图：`image/anchors/zhouning-three-view.png` 及四张裁格。
- 禁止漂移项：脸型、窄眼和直眉、齐肩中分直发、体型、暗红外套、深灰上衣、黑裤黑鞋。
- 变体：离家镜头加一件旧黑外套；不改变内搭与人物外观。
- 核对记录：2026-11-18，锚点与 S01 / S02A / S02B 目检通过；脸型、发型和暗红服装一致。

## 人物设定

- 身份/职业：普通城市上班族；不补充会改变剧情的信息。
- 城市/年代：当代中国城市。
- 性格：谨慎、重视现实解释；恐惧逐步累积，不大喊大叫。
- 固定服装逻辑：室内穿暗红家居外套与深灰针织上衣；离开住处时只加旧黑外套。
- 随身物：无固定个人物件；故事证据均为场景道具。
- 禁用故事类型：不适用；仅本集使用。
