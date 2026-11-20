# 悬疑恐怖线规则 · 入口

> 本目录是悬疑恐怖线路规则的唯一真源。2026-11-07 新建；2026-11-14 按「纯正文」口径收敛；2026-11-15 更名为「悬疑恐怖线」。
> 设计原则：**只写本线特有的东西**；能复用助眠线的一律复用，不能复用的明确写"不适用"，不写空话。

## 继承与处置矩阵

| 环节 | 来源 | 本线处置 |
|---|---|---|
| 流程与门禁 | `rules/shared/video-workflow.md` | **直接继承**：剧本锁定 → 分镜 → 动态 → 门禁 1/2 → SRT → QA → 交付 |
| SRT | `rules/shared/srt.md` | **直接复用**：每条 ≤20 字、0 起点、估算时间轴；本线不设覆盖 |
| 交付 | `rules/shared/delivery.md` | **直接复用**：正文视频 + SRT；不产配音、不混音、不烧录、不落库、不写卡、不登记 |
| 像素 QA | `rules/shared/delivery.md` §四 | **照跑**；白边门禁不适用 |
| 三镜法、运镜白名单、生图约定、manifest | `rules/助眠解说/visual.md` | **复用 + 加工**；加工项见 `visual.md` §五 |
| 静帧推拉 / 平移 | `shared/camera-motion/camera_motion.py` | **直接复用**：浮点亚像素逐帧仿射；禁止 ffmpeg `zoompan` |
| GPT 生图管线 | `shared/image-api/channel-policy.json` ＋`visual.md` §二 | **只走 GPT 图片 API**；本地文生图禁用 |
| 角色一致性 / 三视图 / 弱复用 | —— | **本线自定**：`visual.md` §六（2×2 拼版精简档、主角弱复用、`CHARACTER_LOCK.md`） |
| 语速 | `audio.md` | **只保留 3.6 字/秒**，用于排镜头与 SRT；不产音频 |
| 剧本编排最高规则 | `rules/shared/script-workflow.md` | **继承**（线路无关） |
| 文档组织、成本口径 | `rules/shared/` | **直接复用** |

## 本线定义的五件事

1. 选题来源与授权状态（`input-spec.md`）；
2. 悬疑叙事结构与时长换算（`narrative.md`）；
3. 画面风格块与破败/构图口径（`visual.md` §二–§四）、可读性恐怖与证据（§五）、人物三视图/弱复用（§六）；
4. 语速（`audio.md`）；
5. 账号与单集时长目标（`production.md`）。

## 线路定位（2026-11-15）

- 正式名称：**悬疑恐怖线**（原「悬疑线」）。
- 每一期都必须包含明确、可感知的恐怖元素；不能只做谜题、推理或一般悬疑氛围。恐怖应进入事件机制、证据或人物遭遇，并推动主线。
- 恐怖表达不等于血腥或跳吓；遵守 `narrative.md` 的禁用项，以异常、压迫、身体/空间威胁及后果建立恐惧。

## 加载顺序

0. 新单/续跑：先 `input-spec.md` §0，用 `../../shared/workflows/悬疑/EPISODE_INPUT_TEMPLATE.md` 填单；
1. 全局流程：`../shared/video-workflow.md`；
2. 剧本：`../shared/script-workflow.md` + 本目录 `narrative.md`；
3. 引入文案与画面先读 `../shared/intro.md`（一般1～2画面、默认共两短段，开头强化吸引力）；按阶段：`visual.md`（先取 §二 风格块、判主角契合度、锁 2×2 三视图与 `CHARACTER_LOCK.md`，之后才批量生图）、`audio.md`（只取语速）；
4. 镜头配比与构图：`../shared/shot-composition.md`（E/M/C = 22/53/25、进场三连、场地锚点、**§五 构图语法与序列验收**、**§六 `fact` 字段**），本线默认档位见 `visual.md` §4.1.1；门禁 `shared/workflows/body-only/check_shot_mix.py --require-fact`；
5. 执行件：推拉 `shared/camera-motion/`；生图只走 `shared/image-api/`；SRT `shared/workflows/subtitles/`。

## 边界

- 本目录不复制助眠规则原文，需要细节时回到真源。
- 冲突裁决：用户最新指令 > `video-workflow.md` > 本目录 > `rules/shared/` > 单集 `PROJECT_STATE`。
- 单集特例写进该集 `PROJECT_STATE`。
- 修改本目录需用户明确要求，改动记入 `rules/shared/README.md` 的"最近写回"。

## 明确不做的

- 不做片头、钩子、标题卡、账号卡；成片第一帧就是正文。
- 不做两件套（clean + 配音）：不产配音、不混音、不烧录、不落成品库、不写卡、不登记。
- 不做封面、发布文案。
- 不用本地文生图（ComfyUI / Qwen-Image / Z-Image / 内置 Codex）。
- 不靠事后门禁纠风格：风格由 §二 风格块、§三 破败词表、§四 构图约束在提示词阶段锁死。
