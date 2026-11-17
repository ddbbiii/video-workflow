# 悬疑视觉规则

> 2026-11-12 重整 v2。本次只做三件事：把风格做成**可直接复制、不可改写**的提示词块；把"破败"与"构图"写成可执行的词表和硬要求；明确**本地文生图废弃**。
> 技术约定（三镜法、运镜白名单、2×2 裁格、manifest）仍复用 `rules/助眠解说/visual.md`，本文件不复制。
> 历史版本已不作为执行依据；当前规则以本文件和共享规则链接为准。

## 一、口径（一页判据）

**低饱和破败调查漫画空间 + 成熟简化赛璐璐人物。**

- 调查漫画：画面是"证据—空间—人"的关系图，不是电影剧照。观众看的是"哪儿不对劲"，不是"拍得多好看"。
- 破败：旧、用旧、有损耗；**不做废墟化**。
- 赛璐璐：平涂色块、硬边阴影、干净线稿、比例成熟；不是写实、不是厚涂插画、不是 3D。

三个不许：

1. 不许照片感、写实渲染、3D/CG 质感；
2. 不许新装修、样板间、无使用痕迹；
3. 不许废墟化（塌墙、瓦砾、破洞、植物入侵、烧焦）。

判据：

- 抽一帧给没看过剧情的人，能否说出"这是哪儿、有什么物件、谁来过"；说不出即构图失败。
- 人物帧：像照片、像厚涂、像 3D，都算偏离。

## 二、风格块（唯一真源）

**规则**：每镜提示词 = `STYLE_POS` + 本镜内容；`STYLE_NEG` 原样带入负向。两块**只能整段复制**，不得改写、翻译、缩写、增删形容词。单集不得自写风格串；需要偏离必须先经用户批准，并在该集 `PROJECT_STATE` 登记为局部覆盖。

`STYLE_POS`：

```text
desaturated graphic-novel panel, mature simplified cel-shaded anime characters, flat color
blocks with hard-edged cel shadows, clean ink linework, cold grey-blue palette, one
controlled warm practical light, ordinary Chinese urban interior or street, worn and
lived-in surfaces, legible horror staging, clear foreground subject and evidence prop,
slightly off-center composition, deep focus, layered foreground occlusion in wide shots,
volumetric dust in cold window light, 16:9
```

`STYLE_NEG`：

```text
photograph, photorealistic, 3d render, cgi, live action, film still, cinematic still,
35mm, shallow depth of field, bokeh, motion blur, glossy skin, hyperreal texture,
clean new building, spotless, pristine, showroom, symmetrical centered hero shot,
chibi, big eyes, text, letters, numbers, labels, watermark, UI, logo, gore, monster,
jump-scare face
```

**正向提示词禁词**（出现即改写）：`photoreal`、`photographic`、`cinematic`、`film still`、`movie still`、`35mm`、`bokeh`、`shallow depth of field`、`hyperreal`、`3d render`、`CG`、`semi-realistic`、`painterly`、`matte painting`、`concept art`、`glossy`。

这些词会把画面拉回摄影或厚涂；2026-11-12 两集即由此漂移（见文末事故记录）。

`CEL_BOOST`（含人物、手部或近景时，追加在 `STYLE_POS` 之后）：

```text
2D cel animation key visual, flat unshaded color areas, hard-edged shadow shapes,
no gradients on fabric or walls, clean black linework, anime screencap
```

组合规则：

- 环境/空镜：`STYLE_POS` + 本镜内容；
- 含人物、手部、证据特写：`STYLE_POS` + `CEL_BOOST` + 本镜内容；
- GPT 图片 API **没有独立负向参数**：`STYLE_NEG` 以 `Avoid: ...` 追加在整条正向末尾，一次生成一条 prompt。

2026-11-12 校准：`dkl2` 空镜是动漫背景美术、破败足；人物镜加 `CEL_BOOST` 后达到赛璐璐（见 `shared/image-api/runs/20261112-133807-style-calib/`）。

## 三、破败（每镜都要写）

| 级别 | 定义 | 词表 |
|---|---|---|
| 旧（必须） | 用旧、有生活痕迹 | 掉漆、水渍、灯罩发黄、划痕、贴补、锈、积灰、杂物、晾衣、塑料凳、旧日历 |
| 破败（上限） | 局部损耗 | 墙皮起翘/剥落、瓷砖缺角、门框变形、电线外露、地砖污渍、胶带补丁 |
| 废墟（禁止） | 结构性崩坏 | 塌墙、瓦砾、破洞、植物入侵、烧焦、荒废多年 |

每镜写提示词时必须包含：

- **≥2 处损耗证据**：`peeling paint` / `water stain` / `rust` / `cracked tile` / `scuffed skirting` / `yellowed plastic` / `taped repair` / `chipped enamel`；
- **≥1 处生活痕迹**：`drying laundry` / `stacked bowls` / `slippers` / `wall calendar` / `plastic stool` / `thermos` / `mended tape` / `worn cushion`；
- 两者都写在**前景或焦平面**，不能交给背景虚化（STYLE 已禁浅景深）；
- 不写 `clean / new / pristine / tidy / minimal / spotless / fresh paint`。

## 四、构图与逐镜提示词

### 4.1 构图（调查漫画，不是电影剧照）

- 平视或轻微俯仰，单点透视，深焦；前后景都可读；
- 主体偏置：主体中心落在 1/3 线附近，不居中、不对称；
- 前景遮挡至少一层（门框、椅背、晾衣杆、帘子、货架），形成"在门外看"的调查视角；
- 证据占画面高或宽 ≥1/6，在焦平面，不被人物完全挡住；
- 空间类异常用固定机位长镜；
- 一镜只承担一次信息增量，同一镜不反复推拉；
- 禁：35mm、浅景深、bokeh、对称居中、英雄机位、浓雾糊主体。

### 4.1.1 构图语法（2026-11-14 起，与人生体验线共用）

真源：`../shared/shot-composition.md` §五。本线沿用它的四参数（机位/焦段/站位/前景）与三层信息，只调默认档位：

| 参数 | 本线默认 |
|---|---|
| 机位 | **中/远**：门外、走廊尽端、楼梯下、隔窗、隔帘 |
| 焦段 | **24–28mm 广角深焦**（§4.1 已禁 35mm 与浅景深） |
| 站位 | 左/右三分之一线，不居中；调查者可背对或侧对镜头 |
| 前景 | 至少一层遮挡（门框/帘子/晾衣杆/货架/栏杆），压住画面边角 |

- **人物尺度**：以同画面的门为参照，人物高 ≈ 门高的 0.55–0.65；**不得为压占比把人画小**。
- **占比**：E ≤1/5、M 约 1/3、C ≥1/2，靠机位与前景实现，不写百分比指令。
- **三层信息**：前景遮挡物、中景人物与在用家具、远景走廊/窗/门洞，三层各写**具体物件**（本线的前景常常同时是"损耗痕迹"的落点，按 §三 写）。
- **验收**：联系表人工过；像素占比类自动指标只作参考。

### 4.2 逐镜提示词顺序

1. `STYLE_POS`（原文）
2. 主体与数量、姿态
3. **构图语法**：机位（近/中/远）+ 焦段（24–28mm 深焦）+ 站位（三分线）+ 前景遮挡物（见 §4.1.1）
4. 前中后景与遮挡关系（三层各写具体物件）
5. 光线来源与方向（全画面只留一处暖光落点）
6. 证据、位置与占比
7. `fact`：这一镜观众必须看懂的一件事（与分镜表同字段；空则删/并，不硬拍）
8. 本镜禁止项（含文书类"无可辨字形"）

### 4.3 写完自检（人工过一遍，不设风格门禁）

- [ ] `STYLE_POS` 原文照抄，`STYLE_NEG` 已带
- [ ] 无禁词
- [ ] ≥2 损耗 + ≥1 生活痕迹，且在前景/焦平面
- [ ] 主体偏置 + 一层前景遮挡
- [ ] **构图四件套齐**（机位/焦段/站位/前景），**人物高 ≈ 门高 0.55–0.65**，没有被压小
- [ ] 三层信息各写具体物件，不只写"背景是一条走廊"
- [ ] 证据 ≥1/6、不被挡
- [ ] 人物镜有 `character_id` 与锚点
- [ ] 画面内无可读文字
- [ ] `fact` 一句话写得具体，且不与同场其他镜重复

**`fact` 与呼吸镜（2026-11-15）**：

- 空 `fact` 先删镜或并镜，不靠"手要扶门框"这类单镜修辞补；门禁见 `../shared/shot-composition.md` §六。
- 构图按 3–4 镜一组验收（全景 → 人在界线上 → 他看到的东西），不按单帧判"讲不讲得清"；单帧只判风格与破败。
- 呼吸镜（不承担信息的人物镜）**暂不设配额**：目前只有 2026-11-14 小批的 2 个样本，等有 2–3 个正式集的样本再定，不从单张图反推规则。

### 4.4 示例（照这个密度写，不要只写名词）

环境镜：

```text
dim fourth-floor corridor of an old Chinese apartment building, peeling green paint along
the skirting, a dark water stain spreading down from the window frame, one dead sensor lamp,
a plastic stool and a stack of old newspapers beside the door, cold grey window light from
the far end, no people, no readable text
```

人物镜（背影）：

```text
medium shot from behind: a lean Chinese man in his late thirties, short black buzz cut,
dark navy work jacket with a blank rectangular badge patch, dark grey trousers, black
gloves, standing before an open metal junction box, his shadow thrown long across the
scuffed wall, rust bleeding from the box hinge, a coiled extension cord on the floor, cold
corridor light from behind, face not visible
```

## 五、恐怖度与证据

（原 §二 与原 §五 加工项；编号沿用，便于旧文档引用。）

- 恐怖来源排序：**空间不合理 > 生活痕迹 > 人物缺失 > 动作领先 > 怪物现身**；怪物最后出现，甚至不出现。
- 恐怖感来自构图、空旷、冷色、异常物件、生活痕迹与空间不合理，**不来自压黑**；暗部保留细节，关键物件一眼看清。
- 后期只允许轻微压抑：冷灰蓝、低饱和、适度对比与锐化；不得重暗角、重颗粒、糊化、全局低亮度。
- 人物风格保持成熟简化动漫方向；偏离需先经用户批准并记为单集局部覆盖。

本线加工项：

1. 证据特写独立生图，不进网格；
2. 证据最小占位：不小于画面高或宽的 1/6，且不被前景人物完全遮挡；
3. `manifest` 增 `evidence_id`，与 `narrative.md` 证据链编号绑定；
4. 反转镜备两版：同构图、揭示前后两种状态差（光线、物件位置、人物在场）；
5. 空间类异常优先固定机位长镜；
6. 禁止同一镜反复推拉充当新信息；
7. 文书类证据不硬抽：病历、告知书、预约卡、工单、门禁记录等优先后期排版道具卡；生图只负责场景、手部与纸面质感；每件最多重抽 2 次；100% 裁切下不得有可辨字形，伪文字必须糊掉或遮住。

全片禁止项：

- 怪物化（尖牙、多肢、腐肉）、像素溶解、无意义故障条、镜头噪点特效；
- 写实脸、幼态 Q 版、出戏简笔画；
- 画面内文字、水印、伪文字、UI 面板、分栏排版；
- 用黑场或纯色块代替画面；
- 同一装饰母题反复使用。

## 六、人物一致性（三视图前置，2026-11-08 强化）

原则：**一致性靠参考图驱动，不靠文字描述**。三视图只是标准角度锚点，不是保险；每次生成必须喂同一套锚点图。

**赛璐璐是硬约束**：人物必须是平涂色块 + 硬边阴影 + 干净线稿；服装块面化（大色块 + 少量褶线），不做布料微纹理。即使只露背影、手或剪影，也必须带 `character_id` 与锚点图。

**硬前置：主角三视图与 `CHARACTER_SPEC.md` 未锁定，不得进入批量生图/生视频。** 配角按档位处理，不要求全套。

### 6.0 默认精简档（2026-11-08 二次收窄）

- 主角默认 **1 张 2×2 角色拼版**：左上正面全身、右上侧面全身（90°）、左下背面全身、右下正面面部特写；一次生成，按 `rules/shared/image-grid-generation.md` 裁格（内缩 3–4 px），得到 `front` / `side` / `back` / `face` 四张。
- 面部特写不单独生成；拼版面部格不够用时，从正面格裁切放大，仍不够才单补 1 张。
- 拼版内任一格漂移，只单补该格（用正面格做参考），不整版重抽；每资产整版最多重抽 2 次，单格补图最多 2 次。
- B 档门槛提高到 **≥5 镜、与主角同框、或承担证据/关键动作**；只建 **1 张正面或 3/4 参考**，不要求正+侧两张；每角色最多 2 次生成。
- 批量前选**前 3 个含主角的正式分镜**兼作试生（尽量覆盖正面、侧面、同框），不额外调用；只看锚点是否漂移，漂移就回修锚点再继续。
- 跨集复用主角只建一次；后续集只做状态变体（换装/受伤/湿身/年龄）1 张，最多 2 次。
- 预计增量：新建主角 + 1 个 B 档约 **2–4 次**；+2 个 B 档约 **3–6 次**；复用主角 **0–2 次**（无变化 0，状态变体 1–2）；复用主角 + 1 个 B 档约 **1–4 次**。完整档只在 6.1 例外时使用。

### 6.1 分级与前置

| 档 | 适用 | 必须维护 | 前置 |
|---|---|---|---|
| A 主角 | 每集叙事核心、跨集出现 | 默认 1 张 2×2 拼版三视图（正/侧/背/面部四格）+ 固定提示词段 + `CHARACTER_SPEC.md`；表情/服装变体按需；完整档仅按 6.1 例外 | 拼版与面部格锁定后才可批量 |
| B 重要配角 | 本集 ≥5 镜、与主角同框、或承担证据/关键动作 | 1 张正面或 3/4 参考 + 固定提示词段 | 首次批量前确认，不要求三视图 |
| C 一次性 | 只出现 1–2 场、不承担连续性 | 不建资产，同批次生成，靠提示词约束 | 无 |

- 完整档（独立正/侧/背 + 单独面部特写）只用于：脸是剧情关键、大量特写、或拼版连续两次不合格；需在 `CHARACTER_SPEC.md` 写理由并经用户确认。
- 主角每集都要有锁定资产；新建主角按本节建，跨集复用同一角色沿用同一 `character_id`，不重画；
- 首个新建主角建成后，在 `CHARACTER_SPEC.md` 标 `series-reusable` 候选；后续每单按 6.6 判契合度，不自动复用；
- 配角是否升级按“出现镜数 / 是否与主角同框 / 是否承担证据”判断，不按戏份感觉；
- 换装、受伤、湿身、年龄变化建 `state` 变体，不覆盖基础三视图。

### 6.2 三视图规格

- **默认 2×2 拼版**：左上正面全身、右上侧面全身（90°）、左下背面全身、右下正面面部特写；四格同一角色、同一比例、同一站姿、同一服装与发型；素底（深灰或浅灰）；无文字、编号、边框、水印、UI；不裁成半身。
- 每格写独立文案（正面/侧面/背面/面部），符合 `rules/shared/image-grid-generation.md`；不把“三视图”三个字当布局说明丢给模型。
- 一次生成后按 2×2 裁格（内缩 3–4 px）得到 `front.png` / `side.png` / `back.png` / `face.png`；`three-view.png` 保留拼版原图。
- 拼版内任一格漂移，只单补该格（用正面格做参考），不整版重抽；面部特写优先从拼版裁切放大，不够再单补。
- 完整档（仅 6.1 例外）：三张独立全身 + 面部特写，同一提示词与参考链；侧/背优先用正面图做参考生成，不靠纯文字重抽。
- 面部特写：正面、平光，锁眼型、眉形、鼻梁、唇形、发际线、痣/疤。

### 6.3 资产与登记

`assets/悬疑/characters/<character_id>/`，随目录一份 `CHARACTER_SPEC.md`，至少登记：

- `character_id`、姓名、档位、适用故事/集；
- 人物设定：身份/职业/城市/年代、性格、说话方式、固定服装逻辑、随身物、可用/禁用故事类型；
- 复用：`reuse-policy: soft`、`reuse-mode: face-only / same-person`、`reused-in`、`portrayed-as`、每次契合度判定结果；
- 固定提示词段（中/英）、负面词；
- 模型、seed、参考图路径、LoRA 名称与权重（如有）；
- 批准日期、批准人、复用范围（`episode-only` / `series-reusable`）；
- 禁止漂移项：发型、发际线、眼型、眉形、鼻梁、唇形、体型、服装主色与领口/袖口、鞋、配饰、痣/疤；
- 变体列表（表情、服装、受伤/湿身等 state）。

### 6.4 每集锁定与核对

- 剧本锁定后、批量生图前，落 `storyboard/CHARACTER_LOCK.md`：`character_id` / 档位 / 来源（新建或复用自哪集）/ 出现镜号 / 服装状态 / 参考图路径；
- 每个含角色的镜头提示词必须引用 `character_id` 与锚点；manifest 增 `character_ids`；
- 批量前选**前 3 个含主角的正式分镜**兼作试生（尽量覆盖正面、侧面、同框），不额外生成；通过再铺量，任一镜脸型/发型/服装/体型漂移，回修锚点，不带病批量；
- 整版重抽 ≤2 次，单格补图 ≤2 次；超限改用裁切、局部修或换表现方式，不无限重抽；
- 三视图锚点确认后再批量生产，锚点未过不铺量；
- 成片抽查：同一角色跨镜抽 5 帧，按 6.3 的禁止漂移项逐项核对。

### 6.5 边界

- 助眠线资产不自动继承为悬疑角色；需要复用时，按本线三视图重建并登记；
- 简化赛璐璐风格对参考图更敏感（特征少、易漂移），锚点图必须比写实风更严格地锁同一张；
- 不为“统一感”强行让不同故事共用同一张脸；角色复用范围在剧本锁定时声明；
- 本节生效前已完成的单集不自动返工；用户点名补做时按本节建资产，不覆盖已成片。

### 6.6 主角弱复用（soft reuse，2026-11-08）

原则：**复用是成本优化，不是叙事强制**。新单先判断“已有主角的脸/气质能不能演这个故事的主角”；契合度高才复用，不为了省图改剧本、改年龄/性别/职业，也不强行让每集同一张脸。

**两种复用模式；需要复用时默认同脸复用（是否复用仍先过契合度表）**：

| 模式 | 是什么 | 适用 | 记录 |
|---|---|---|---|
| 同脸复用（默认） | 沿用同一套三视图/脸，故事里是**新姓名/新身份**；观众不被告知是同一人 | 单元剧、不同故事、类型契合 | `reuse-mode: face-only`；`portrayed-as` 列不同角色 |
| 同人复用 | 同一 `character_id`、同一姓名/身份，跨集连续 | 续集、系列化 | `reuse-mode: same-person`；`reused-in` |

- 同脸复用是“同一演员演不同角色”，不是同一人；不建立共享宇宙、不写跨集前情；同一张脸不得在同一集或同一连续故事里同时出现两个角色。
- 同脸不得用于“长相是谜底/双胞胎/换脸/整容”剧情；用户明确要新脸时一律新建。
- 新单先查 `assets/悬疑/characters/REUSE_POOL.md`，逐单填 `_TEMPLATE/REUSE_FIT_CHECK.md`；通过契合度表才复用。

**契合度表**：硬条件 4 条全过 + 软条件 ≥3/4 → 复用；否则新建。

| 类型 | 条件 |
|---|---|
| 硬 1 | 性别/年龄段/体型同一档，可由同一“演员”出演 |
| 硬 2 | 脸型/五官/气质类型一致，不靠换脸/特效/大幅化妆 |
| 硬 3 | 世界观/年代/城市/阶层不冲突，服装逻辑能落地 |
| 硬 4 | 故事不要求“新面孔”：没有换脸、双胞胎、整容、长相是谜底；也不要求与已出集是同一人 |
| 软 1 | 性格/说话方式可兼容（能演） |
| 软 2 | 职业/身份不需要改脸就能成立 |
| 软 3 | 与已出集不撞名、不撞关系、不产生时间线矛盾 |
| 软 4 | 观众不会误认成另一个已知角色；会误认就换装/换发型/换气质，仍不行则新建 |

上表用于**同脸复用**；同人复用是续集，按同一身份/时间线连续性判断，不套硬 4。

**一票否决**：故事核心依赖主角外貌/身份秘密；需要不同年龄/性别；与已出集同名不同人；用户明确要新脸。

**复用集的做法**：

- 不新建三视图；直接用 `assets/悬疑/characters/<id>/three-view.png` 与 `face.png`；
- 换姓名/身份只改 `CHARACTER_SPEC.md` 的 `portrayed-as` 和服装/发型 state，不做新脸；
- 无换装/状态变化：0 张新图；有换装/发型/受伤/湿身：只做 1 张 `state/` 或 `costume/` 变体，最多 2 次；
- `CHARACTER_LOCK.md` 标 `reused`、`reuse-mode`、`source_episode`；`CHARACTER_SPEC.md` 的 `reused-in` / `portrayed-as` 追加本集；
- 变体脸漂移时用基础拼版做参考修，不重画整套。

**不复用时**：新建 `character_id` 和 2×2 拼版，不改旧角色的基础图；旧角色保留，供以后契合的故事复用。

**成本**：复用主角 0–2 次/集（无变化 0，换装 1–2），新建 2–4 次/集；B 档另计 1–2 次/人。

## 七、技术约定与通道

**复用项**（细节回 `rules/助眠解说/visual.md`，不复制）：三镜法、镜头分类与尾帧延长、镜头组合白名单、图生视频与推拉分工、生图约定（含 2×2 裁格内缩 3–4 px）、manifest 字段。

**执行件**：推拉/平移一律走 `shared/camera-motion/camera_motion.py`（浮点亚像素、帧数精确），禁止 ffmpeg `zoompan`；motion plan 过 `shared/camera-motion/validate_plan.py`。

**生图只走 GPT 图片 API**：

- 路由唯一事实源：`shared/image-api/channel-policy.json`；当前 `v8-new2-dklb-parallel`：`new2`（1672×941）与 `dkl-b`（2048×1152）镜头级轮询并发，同一集允许混用；单次请求固定一个通道，失败只转移失败镜头；`old` 已于 2026-11-15 退役，不再调用。
- 角色锚点按 `channel-policy.json` 的镜头级轮询分配；关键角色先做小样验收，禁止路由到已退役通道。证据、手部、推近 >6% 用 single；环境与人物全身/中景用 2×2。
- 赛璐璐稳定性按当前启用通道分别验收：`dkl-b` 批量前执行 6 镜画风小样门禁；`new2` 固定 1672×941。具体尺寸与退役状态以 `channel-policy.json` 为准；尺寸断言只判技术合格，不判风格。
- 记录：manifest 增 `channel`、`attempts`、`qa`、`fallback_from`、`fact`（抽检可读性用）；交付报告出通道构成。

**本地文生图禁用（2026-11-12 用户指令）**：ComfyUI / Qwen-Image / Z-Image / 内置 Codex 出图一律不得用于分镜、试生、风格测试或兜底。原因：本地模型没有赛璐璐锚点约束，2026-11-12 两集用 Qwen-Image 2512 全量出图，风格直接漂成照片/半写实。

## 八、风格资产

- 旧 SDXL LoRA 已归档到 `../video-archive/20261117-retired-assets/assets/悬疑/styles/rainnight/`；与现用图片 API 不兼容，**不再用于生产**。
- 风格锚点：以 2026-11-10 已验收的赛璐璐资产为准，例 `assets/悬疑/characters/zhouxu-20261110-pool/three-view.png`；2026-11-12 两集不作为风格基准。
- 每个新故事可新建主角；长期复用的角色再单独立规范。

## 九、验收（人工）

- **风格**：抽 3 帧盲测，并与锚点图并排看；不像赛璐璐或不够破败 → 整集重抽，不逐镜打补丁。
- **人物**：同一角色跨镜抽 5 帧，按 §6.3 的禁止漂移项核对；主角三视图未锁定的集不得进入验收。
- **画面**：闪烁、跳变、漂移、变形、穿帮按助眠线标准检查。
- **可读性**：抽 3 帧给不了解剧情的人看，能否说出画面里有什么物件、在哪里、和谁有关。
- **序列可读性**（2026-11-15）：按 3–4 镜一组抽看，能否读出"这是哪 → 人在干什么 → 他看到了什么"；单帧不问"他在干什么"（会让铺垫镜背锅）。

## 附：2026-11-12 风格漂移事故

- 《脱水超重》：`STYLE` 写成 `photoreal cinematic film still ... 35mm, shallow depth of field`，负向词含 `cartoon, anime`；`PROJECT_STATE` 自记“局部覆盖 visual.md 赛璐璐默认，待用户确认”，但未获批即全量出 46 镜；本地 Qwen-Image 2512（cfg 1.0 / 4-step）。
- 《废弃工单》：`STYLE` 写成 `mature semi-realistic illustration`（`cel` 只用于 lighting）；未建三视图（`PROJECT_STATE` 偏离 2）；同样走本地 Qwen-Image 2512。
- 共同点：没用本文件 §二 风格块、没建角色锚点、绕开 GPT 通道；事后只查尺寸与锐度，风格无人核对。
- 结论：风格只能靠“整段复制的风格块 + 破败词表 + 构图约束”保证，不靠模型自觉，也不靠事后门禁。
