# CHARACTER_SPEC — zhounian-20261110-pool

- character_id：`zhounian-20261110-pool`
- 姓名：周念（本集 8 岁，妹妹）
- 档位：A 主角（叙事核心，出现镜数最多）
- 资产形态：2×2 拼版（正/侧/背/面部）
- 适用：`series-reusable` 候选（仅同年龄段、同气质的单元剧可同脸复用）
- 首次出现：`20261110-pool` S02

## 固定提示词

- 固定提示词段（中文）：8 岁中国女孩，矮小，118 cm，圆脸，黑色齐刘海齐耳短发，深棕大眼，小鼻子，小嘴，白皙；奶白色小碎花长袖睡衣，赤脚；无发夹（发夹是第 4 段后的状态变体）。
- 固定提示词段（English）：8-year-old Chinese girl, small and thin, 118 cm, round face, chin-length black bob with straight bangs, large dark brown eyes, small nose, small mouth, fair skin; cream-white long-sleeve pajamas with tiny faded floral pattern, bare feet; no hair clip, no accessories.
- 负面词：photorealistic, 3D render, chibi, big eyes, different outfits, different hairstyles, different faces, text, watermark, gore, adult proportions.
- 模型 / seed：`gpt-image-2.5-sunburst` / 无 seed
- LoRA / 权重：无
- 参考图：`three-view.png` / `front.png` / `side.png` / `back.png` / `face.png`
- 变体：`state/red-clip.png`（第 4 段后戴红色五瓣塑料发夹；未单独生成，靠提示词 + 参考图控制）
- 禁止漂移项：发型（黑色齐耳短发 + 齐刘海）、发际线、眼型（大而圆）、眉形（细平）、鼻梁（小）、唇形（小）、体型（矮小）、服装主色（奶白 + 小碎花）、领口（小翻领）、袖口（收口）、鞋（赤脚）、配饰（第 4 段前无，之后红发夹）
- 批准：2026-11-10 / 助手自检，待用户验收
- 备注：四格一致性好；赤脚是本集关键连续性（湿脚印、水泥灰）。

## 人物设定

- 身份/职业：小学二年级，随父母租房
- 城市/年代：南方小城，当代
- 性格：安静、不怕、会把听到的事当真；对“姐姐”没有恐惧，只有亲近
- 说话方式：短句，直接，不解释
- 固定服装逻辑：在家穿奶白碎花长袖睡衣，赤脚
- 随身物：旧布娃娃；第 4 段后红色塑料发夹
- 可用故事类型：儿童视角异象、家庭旧屋、被“记住”的孩子
- 禁用故事类型：需要成熟台词、动作戏、喜剧

## 复用（弱复用）

- reuse-policy：soft
- reuse-mode：face-only（默认）
- 契合度判定：硬 1–4 待判；软 1–4 待判；结果：本集新建
- portrayed-as：周念（8 岁，妹妹）
- reused-in：`20261110-pool`

## 核对记录

| 日期 | 试生镜号 | 结果 | 处理 |
|---|---|---|---|
| 2026-11-10 | S02 | 四格同脸、同服装、同体型；赤脚一致 | 接受 |
