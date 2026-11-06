# video-rules

规则库入口。原则：**不要一次读完**，按当前阶段取用；冲突时 `video-workflow.md` 与用户最新指令优先。

## 按阶段加载

| 当前在做什么 | 必读 | 按需 |
|---|---|---|
| 接单/续跑（助眠） | `../助眠解说/input-spec.md` | `../助眠解说/README.md` |
| 任何生产动作 | `video-workflow.md` | — |
| 写稿/改稿 | `script-workflow.md` ＋ `../助眠解说/narrative.md` | — |
| 分镜/生图 | `image-grid-generation.md` ＋ `../助眠解说/visual.md` | `visual/cover-and-intro.md` |
| 配音/混音 | `../助眠解说/audio.md` | `audio/voice-and-subtitles.md`、`audio/manual-post-production.md` |
| 字幕 | `../助眠解说/subtitles.md` | `audio/manual-post-production.md` |
| 片头 | `../助眠解说/intro.md` ＋ skill `sleep-aid-intro` | `../../shared/workflows/助眠解说/` 的 runbook |
| 交付 | `delivery/final-delivery.md` ＋ `../助眠解说/delivery.md` | — |
| 评估成本 | `cost-evaluation.md` | — |
| 整理文档 | `document-organization.md` | — |
| 权限/会话边界 | `governance/session-governance.md` | — |
| 项目记忆 | `memory/project-rules.md`（索引，指向各真源） | — |

## 文件清单

| 文件 | 管什么 | 加载时机 |
|---|---|---|
| `video-workflow.md` | A→M 固定流程与三道人工门禁 | 每次生产 |
| `script-workflow.md` | 剧本编排（时代可理解性、悬念预算、复杂度） | 写稿时 |
| `image-grid-generation.md` | 网格生图、逐格提示词、连续性验收 | 生图时 |
| `document-organization.md` | 文档分层、MD 拆分时机、引用规则 | 整理文档时 |
| `cost-evaluation.md` | 成本口径（只算机器时间与 token） | 被问成本时 |
| `douyin成品.md` | 已发布成片登记 | 交付登记时 |
| `visual/cover-and-intro.md` | 封面与片头的跨线路约束 | 做封面/片头时 |
| `audio/voice-and-subtitles.md` | 声线与字幕的跨线路通用约束 | 配音/字幕时 |
| `audio/manual-post-production.md` | 手动混音与字幕分工 | 后期交接时 |
| `delivery/final-delivery.md` | 交付两件套与像素级 QA | 交付时 |
| `governance/session-governance.md` | 会话职责与规则写权限 | 改规则/跨会话时 |
| `memory/project-rules.md` | 项目级持久规则索引 | 需要口径时 |

## 优先级

1. 用户最新明确指令
2. `video-workflow.md`（最高优先级流程）
3. 线路规则（`rules/<线路>/`）
4. 通用规则（本目录）
5. 项目 `PROJECT_STATE` / 运行日志（局部覆盖，需登记）

## 修改规则

- 除非用户明确要求“持久化/写回工作流/设为长期规则”，不改本目录。
- 单集特例写进该集 `PROJECT_STATE` 或运行日志。
- 每次写回在本节记一行，只留最近 5 条。

## 归档

- 2026-11-06：悬疑动漫视觉提案（12 份）与音乐线规划（2 份）移至 `../../shared/archive/proposals/`——它们是提案/规划而非生效规则，线路未在产。开工时搬回 `rules/<线路>/` 并在本节登记。

## 最近写回

- 2026-11-07：强化偏离审批与字幕样式一致性——`rules/助眠解说/subtitles.md` 新增“样式唯一真源与改动纪律”（片头/正文同一常量、预烧层必须随样式重建、全片一致性检查、偏离先获批）；`video-workflow.md` §3 增加第 10 条“任何违反规则/工作流必须先获用户确认”；`README.md` 增加执行前加载规则与资产的要求；事故复盘补“片头/正文样式分裂”。
- 2026-11-06：助眠事故复盘落盘 `rules/助眠解说/incidents-20261106.md`；新增白边门禁（`visual.md`）、字幕 G7（`subtitles.md`）、E 版片头与字体/首帧约束（`intro.md`）、交付前白边与 G7 终检（`delivery.md`）；`video-workflow.md` §2.K/L/M 同步引用。
- 2026-11-06：助眠默认配音换线为 **CosyVoice3 0.5B**（声线 `b2-warm-male-cosy3`）：逐单元 `speed=0.90`、3.8 字/秒句间留白、−42 dB 紧裁、24k→48k，取消 atempo；新执行件 `shared/workflows/助眠解说/voice-cosy3/`。旧 VoxCPM2 轻语链转历史复现，已交付成片不回灌。
- 2026-11-06：新增助眠输入契约 `rules/助眠解说/input-spec.md` 与填写单 `shared/workflows/助眠解说/EPISODE_INPUT_TEMPLATE.md`；定义 A/B 门禁授权、默认值表、8 条硬停与 A→M 映射。
- 2026-11-06：助眠线路规则重组为 8 份（入口 `rules/助眠解说/README.md`）；新增本文件“按阶段加载”表与文件加载时机；`project-rules.md` 由摘要改为索引；原文备份 `shared/archive/rules-premerge-20261106/`。
- 2026-11-05：新增 `cost-evaluation.md`；成本只算本机占用时间与 token。
- 2026-09-17：`video-workflow.md` §4 改为 H3 关键 / Wan 微动 / LTX 特殊；`script-workflow.md` v1.3 对齐「静态不强制人审」。
