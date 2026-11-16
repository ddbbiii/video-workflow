# 规则库入口（纯正文版）

> 2026-11-14 起：每集只交**正文视频 + SRT**，不做片头/标题/字幕/配音。规则库已按此收敛；旧规则原文在 `E:\program\1project\video-archive\20261114-body-only\rules-obsolete\`，**默认不读**。
> 原则：不要一次读完，按当前阶段取用；冲突时用户最新指令 > `video-workflow.md` > 线路规则 > 本目录。

## 按阶段加载

| 当前在做什么 | 必读 | 按需 |
|---|---|---|
| 接单/续跑（助眠） | `../助眠解说/input-spec.md` | `../助眠解说/README.md` |
| 接单/续跑（悬疑） | `../悬疑/input-spec.md` ＋ `../../shared/workflows/悬疑/EPISODE_INPUT_TEMPLATE.md` | `../悬疑/README.md` |
| 让我推荐（选题/方案） | `recommendation.md` | 线路选题准入（如 `../助眠解说/input-spec.md` §2.1） |
| 拿参考片（抖音链接/拆解） | `douyin-reference.md` | `../../shared/tools/douyin-ref/fetch_ref.py` |
| 任何生产动作 | `video-workflow.md` | — |
| 写稿/改稿 | `script-workflow.md` ＋ 本线 `narrative.md` ＋ `language-style.md`（悬疑用 `../悬疑/narrative.md`） | — |
| 旁白 lint（写稿后 / 出 SRT 前） | `script-workflow.md` §12 | `../../shared/workflows/script-qa/lint_narration.py` |
| 分镜/生图 | `image-grid-generation.md` ＋ 本线 `visual.md` | 通道 `../../shared/image-api/channel-policy.json` |
| 镜头类型配比（悬疑 / 人生体验） | `shot-composition.md`（E/M/C 22/53/25 ＋ `fact`） | `../../shared/workflows/body-only/check_shot_mix.py` |
| SRT | `srt.md` | `../../shared/workflows/subtitles/` |
| 交付 | `delivery.md` | `../../shared/workflows/body-only/check_delivery.py` |
| 评估成本 | `cost-evaluation.md` | — |
| 整理文档 | `document-organization.md` | — |
| 权限/会话边界 | `governance/session-governance.md` | — |
| 规则/资产清理 | `governance/cleanup-policy.md` | 删除前做精确引用核查与 Git checkpoint |
| 项目记忆 | `memory/project-rules.md`（索引） | `../../.codex-memory/project-rules.md` |

## 文件清单

| 文件 | 管什么 |
|---|---|
| `video-workflow.md` | 剧本→分镜→动态→两道门禁→SRT→QA→交付的固定顺序 |
| `delivery.md` | 每集两件、路径、命名、技术规格、交付门禁 |
| `srt.md` | SRT 的唯一规范：正文、0 起点、≤20 字、估算时间轴 |
| `script-workflow.md` | 剧本编排（时代可理解性、悬念预算、复杂度、cue 规范、旁白语言清晰度） |
| `image-grid-generation.md` | 网格生图、逐格提示词、连续性验收 |
| `shot-composition.md` | 镜头类型 E/M/C、配比 22/53/25、进场三连、场地锚点、`fact` 与序列验收 |
| `recommendation.md` | 推荐输出规则（一次 10 条、每条一行） |
| `douyin-reference.md` | 抖音参考片的获取、验收与合规 |
| `document-organization.md` | 文档分层、MD 拆分时机、引用规则 |
| `cost-evaluation.md` | 成本口径（只算机器时间与 token） |
| `governance/session-governance.md` | 会话职责与规则写权限 |
| `governance/cleanup-policy.md` | 旧规则、实验产物与临时文件的主动清理流程 |
| `memory/project-rules.md` | 项目级持久规则索引 |

## 优先级

1. 用户最新明确指令
2. `video-workflow.md`（最高优先级流程）
3. 线路规则（`rules/<线路>/`）
4. 通用规则（本目录）
5. 单集 `PROJECT_STATE` / 运行日志（局部覆盖，需登记）

## 修改规则

- 除非用户明确要求"持久化/写回工作流/设为长期规则"，不改本目录。
- 单集特例写进该集 `PROJECT_STATE` 或运行日志。
- 每次写回在本节记一行，只留最近 5 条。

## 最近写回

- 2026-11-16：**全线路新增旁白语言清晰度要求**。用户指令：「提升到公共规则」。落地：`script-workflow.md` §16 要求自然、直白、首听即懂；锁稿前逐段朗读，难解比喻、不自然搭配与需要脑内翻译的句子必须改写。
- 2026-11-15：**悬疑恐怖线补充中国大陆语境校验**。用户明确账号面向中国大陆抖音观众。落地：`narrative.md` §六与项目记忆要求对白有交谈目的，店铺/机构流程、证据来源、行业工具和生活细节符合当代本地经验；不把不现实的记录或服务当作惯例。
- 2026-11-15：**悬疑线正式更名为「悬疑恐怖线」**。用户明确要求每一期都必须带有恐怖元素。落地：线路入口、叙事规则、生产规则、线路状态与项目记忆统一名称；叙事硬约束要求恐怖明确可感知并参与事件因果/证据链，不以纯谜题或氛围代替，也不等同于血腥/跳吓。
- 2026-11-15：**构图可读性改为「fact ＋ 删并 ＋ 序列验收」**。用户指令：「行，你的改法比较合理，持久化吧」（起因：悬疑 8 镜小批 B2 背影镜读不出"他在干什么"）。落地：`shot-composition.md` 新增 §5.3 每场脚手架、§5.4 序列验收（3–4 镜一组，单帧只判风格）、§六 `fact` 字段与门禁、§八「不把单镜修辞写成规则」；`script-workflow.md` §15 增 `fact` 与 `--require-fact`（v2.4）；`check_shot_mix.py` 支持 `fact`/`--require-fact`；悬疑线 `visual.md`/`production.md`/`README.md` 同步。门禁已实跑：编译通过、构造样例与 `script-v3`（软模式 PASS；`--require-fact` 只报缺 fact）。顺带修两处既有问题：未标 `has_character` 不再被判成"连续含人物"（原会把整本 220 镜判 FAIL），配比边界加 1e-9 容差（4/8 的 M=50% 原先会误报）。
- 2026-11-14：**构图占比改口径 + 悬疑线同步**。用户指令：「悬疑线也考虑参考这个构图行为」。落地：shot-composition.md 新增 §五「构图语法」作为两条线共用真源（机位/焦段/站位/前景 + 人物高≈门高 0.6）；悬疑/visual.md 新增 §4.1.1（本线默认 24–28mm 深焦、中/远机位、门外与走廊尽端），README 加载顺序同步。
- 2026-11-14：**构图占比改口径（人生体验线）**。用户指令：「人高也需要符合常理，关键是构图的人物占比，不应该通过控制人物的绝对大小来控制」「把规则持久化下来」。落地：`shot-composition.md` §三.3 改为「占比靠机位/焦段/站位/前景，人物高约为门高 0.55–0.65，不得压小」；`shot-composition.md` §三.4 要求三层信息各写具体物件。人生体验线同步：`style.md` v3.2 新增「构图语法」「三层信息清单」，`color-script.md` v1.2 新增「每场至少两个色相」，并明确继承 `shared/camera-motion/MOTION_GUIDELINES.md`、禁用 `zoompan`。
- 2026-11-14：**悬疑线 / 人生体验线启用镜头配比 E/M/C = 22/53/25**。用户指令：「针对悬疑线和人生副本线，你都按这个规则改好比例」。落地：新建 `shot-composition.md`（三类镜头定义、配额、进场三连、连续镜限制、场地锚点、验收），新增门禁脚本 `shared/workflows/body-only/check_shot_mix.py`，两条线的 README 已登记。已交付成片不回改。
- 2026-11-14：**全线路改为纯正文交付**。用户指令：「成品视频只包括完整的正文，不包含引入+标题+字幕+配音，只输出一个视频+对应的SRT文件就行」「配音我自己解决」「旧成品不用再改，只改规则和脚本」。落地：重写 `video-workflow.md`、新建 `delivery.md` 与 `srt.md`、重写 `README.md` 与两份 `project-rules.md`；三条线规则去掉片头/TTS/烧录/成品库；新增交付门禁 `shared/workflows/body-only/check_delivery.py`；旧规则与工具链移入工作区外归档 `E:\program\1project\video-archive\20261114-body-only\`。已交付成品不回改。
