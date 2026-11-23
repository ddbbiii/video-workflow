# CHARACTER_SPEC — chenyi-20261118-xinwen

- 姓名：陈意
- 档位：B 重要配角
- 资产形态：单张正面全身参考
- 适用：episode-only
- 首次出现：20261118-xinwen-gengxin 第 1 镜
- reuse-policy：soft；本集新建，不跨集复用

## 固定提示词

- 中文：29 岁中国女性，身形普通，黑色低马尾，侧分碎发，圆脸、深色眼睛、眉尾略弯；穿米白针织衫、深绿色居家长裤、浅灰拖鞋；无首饰、无眼镜、无痣疤。
- English: one Chinese woman aged 29, average adult build, black hair tied in a low ponytail with a few side-parted wisps, round face, dark eyes, gently curved brow tails, ivory knit sweater, dark-green home trousers, light-grey slippers, no jewelry, no glasses, no distinctive marks.
- 负面词：按 `rules/悬疑/visual.md` 的 `STYLE_NEG` 原文。
- 模型 / seed：gpt-image-2.5-sunburst；seed 未由服务端提供。
- 参考图：`image/anchors/chenyi-front.png`。
- 禁止漂移项：圆脸、低马尾与侧分碎发、普通体型、米白针织衫、深绿长裤。
- 核对记录：2026-11-18，正面参考与 S01 / S02A / S02B 目检通过；低马尾、圆脸和米白服装一致。S02B r1 性别漂移已拒收，r2 通过。

## 人物设定

- 身份/职业：周宁的朋友；不补充会改变剧情的信息。
- 城市/年代：当代中国城市。
- 性格：反应敏锐，最初愿意相信现实解释；遇险时行动克制。
- 固定服装逻辑：全片维持米白针织衫、深绿长裤。
- 随身物：黑色无标识手机。
- 禁用故事类型：不适用；仅本集使用。
