# 单集状态

标题:下潜一万米——从海面到世界最深处(工作标题,候选待定稿)

| 字段 | 值 |
|---|---|
| episode | mariana-descent |
| planning_state | narration_locked(v1.1,2026-10-19 用户授权"自主推进直到做出最终视频") |
| execution_state | in_production(试点生图在跑,TTS 编排器待 GPU) |
| active_run | runs/20261019-mdb-b01 |
| outline | story/OUTLINE.md v1(2026-10-18 交付;10-19 章节重构十章+尾声,同日修香槟泉/鲸睡归属两处事实性结构问题) |
| narration | story/NARRATION_MASTER.md v1.1 锁定(169 单元/7,902 可配音字,快钩片头 20s,【正文实测分钟数】占位待回填) |
| fact_notes | story/FACT_NOTES.md v1(已核 6 组+常识级清单+待精核 7 项) |
| shot_plan | visual/SHOT_PLAN.json v1(试点 ch01-ch03 38 镜:5 single+33 tile,api_budget 头部 14 次;全片骨架 132 镜/约 46 次;ch04-ch10 详图试点验收后补齐) |
| audio_plan | runs/20261019-mdb-b01/scripts/AUDIO_PLAN.py(b2-warm-male 轻语气,newton/siffre 连续先例;atempo 0.774224;BGM -10dB) |
| updated | 2026-10-19 23:05 |

## GPU 协调(2026-10-19)

- 现状:siffre-beyond-time 的 i2v 批量 running(PID 41572,优先级 90,预计 8 小时),其 TTS 已排队且显式依赖 i2v 完成;GPU 满载(99%,12.6/16.3GB)。
- 本集策略:文本/规划阶段零 GPU;TTS 与 i2v 按锁协议+请求文件提交,并在请求 JSON 里写 `dependencies` 指向 siffre 两任务;生图为远程 API 不占本地 GPU(预算按 image-grid-generation.md 前置报批)。启动任何 GPU 任务前执行占用检查(三处锁 + nvidia-smi + 8188/8189/8191 端口),与 siffre 会话同款 pre-grant 检查。

## 成片位置（2026-11-06）

成片已统一移至 `shared/delivery/finals/`，本文件内旧的 `video/final/` 路径仅作历史记录。

