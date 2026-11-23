# 规则库入口（纯正文版）

> 2026-11-14 起：每集只交**正文视频 + SRT**，不做片头/标题/字幕/配音。规则库已按此收敛；旧规则原文在 `../video-archive/20261114-body-only/rules-obsolete/`，**默认不读**。
> 原则：不要一次读完，按当前阶段取用；冲突时用户最新指令 > `video-workflow.md` > 线路规则 > 本目录。

## 按阶段加载

| 当前在做什么 | 必读 | 按需 |
|---|---|---|
| 标题创作/改标题（任何线路） | `title.md` | 对应单集内容与事实 |
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
| `title.md` | 所有内容线通用标题写法：短、单一钩子、不拆成两段 |
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

- 2026-11-23：根据《你先吃，我马上回来》的结构复盘，在悬疑输入契约的悬念预算中增加可选“关系落点”检查；不要求每集煽情或温情，不设为门槛。
- 2026-11-23：用户放开悬疑线结尾情绪限制，允许温情收尾；温情主题须符合中国本土文化与生活经验，不直接采用外国素材主题。同步更新悬疑结尾、叙事、选材和线路入口规则。
- 2026-11-22：用户调整悬疑恐怖故事时长与结尾偏好：故事总时长原则上不超过 25 分钟、不设 5 分钟最低要求；10 分钟以内短篇优先留白但保留理解线索，超过 10 分钟长篇优先讲通因果、回应核心悬念并回收前文。同步更新悬疑选材、输入、叙事、结尾、生产、知乎推荐规则及现行汇总。
- 2026-11-20：用户要求直接删除火柴人及细肢比较方案，不再归档；已删除对应规则快照与两组实验样图，线路只保留圆头手绘（默认）和猫头人（可选），同步所有当前入口。
- 2026-11-20：用户要求所有内容线标题简短、单一表达，不做两段式标题；新增共享标题规则 `title.md`。
- 2026-11-20：用户确认人生体验人物改为《末日独存》参考方向的白灰圆头手绘人物，完整着装身体、简洁表情及克制明暗，替代细肢火柴人；同步线路画风、角色、参考、静帧规程及状态入口。
- 2026-11-20：用户要求人生体验与悬疑恐怖线统一采用简短、强烈的引入：一般1～2画面，每画面1～2短段，默认共两段；开头允许更激进，以吸引观众继续观看。固定入口 `intro.md`，两线分别引用，交付范围保持各线现行规则。
