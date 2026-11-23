# PROJECT_STATE · 人生体验《你只是很会领奖》

- 单集路径：`projects/人生体验/episodes/20261117-tianshaonian/`
- 状态：正文 MP4 与 SRT 已生成；联合交付门禁、旁白 lint、SRT 检查及逐帧像素/CFR QA 均 PASS。31 镜静帧齐全，S03、S20、S29 的手部问题均已返修并复核。成片为无音轨纯正文；当前按无配音估算时长 311.033 秒（5 分 11 秒），比约 6 分钟目标短约 49 秒。
- 题材来源：基于规划稿 `projects/人生体验/planning/大纲-你只是很会领奖-v0.1.md` 扩写；按虚构人物处理，不指向真实未成年人或具体家庭。
- 目标时长：约 6 分钟；线路语速 4.8 字/秒，目标正文约 1,728 字。当前 SRT 按可见字数估算为 311.02 秒（5 分 11 秒），未对真人声校准，低于目标约 49 秒。
- 当前规则：人生体验线 `README.md`、`style.md` v3.7、`character.md` v7、`color-script.md` v1.5、共享剧本规则 v2.5 与正文视频流程。
- 交付边界：正文视频 + SRT；不做片头、配音、烧录、封面或成品库。

## 阶段状态

| 阶段 | 状态 | 产物 |
|---|---|---|
| A 剧本 | 制作稿 v1；旁白 lint PASS；画面描述已修正无人镜冲突 | `story/script-v1.md` |
| B 镜头规划 | 31 镜 shot-plan 与剧本字段对齐、fact 完整；连续无 E / 含人物镜均最长 4；E/M/C 为 25.8/51.6/22.6%，机器检查因 E 超参考上限 0.8pp 返回 FAIL，但按当前规则只作诊断；本集 helper-a/b/c 参考均已生成 | `image/shot-plan.json`、`image/refs-v1/`、`story/script-v1.md` |
| C 静帧 | 完成：31/31 镜；S03、S20、S29 返修后通过手部规则复核。成功图片估算 ¥1.062；69 次失败请求按单价暂估 ¥1.242，是否计费未核；初始 55 次调用计划已超出 | `image/refs-v1/`、`image/env-v1/`、`image/stills-v1/`、`image/manifest-v1.json` |
| D 正文视频 | 完成：31 镜 affine 推拉/拉远，1920×1080、30fps、9,331 帧、311.033 秒、无音轨；最终联合交付门禁 PASS | `video/人生体验_你只是很会领奖_正文_v1.mp4`、`video/render-v1/`、`video/motion-plan-v1.json`、`video/delivery-report-v1.json` |
| H SRT | 完成：31 句拆为 95 条；`check_srt.py` 与视频联合交付检查通过；时长按可见字数估算，未对真人声校准 | `video/srt/人生体验_你只是很会领奖_正文_v1.srt`、`subtitles/v1/` |
| I 像素 QA | 完成：9,331 帧解码、无 ≥1 秒黑/白屏、CFR 通过 | `qa/pixel_scan-v1.json` |

## 生产阻塞

- 主角正式参考 `face-style-D.png`、`turnaround.png` 与本集引用的 10 张表情图已从 LFS 恢复到工作区。`image/refs-v1/ref-helper-a/b/c.png` 是本集专用定装，未修改共享角色资产；helper-c 明确覆盖本稿学生/儿子角色，不沿用全局女邻居参考。
- `shared/image-api/channel-policy.json` active 为 `v8-new2-dklb-parallel`。Keychain 两边 `/v1/models` 均 HTTP 200；本次 XXC 生图请求返回 HTTP 502 `openai_error` 和 HTTP 429 服务繁忙，策略回退到 DKL 后 3 张参考均以 2048×1152 成功返回。当前 3 张首轮成功图估算费用 ¥0.054。
- 正式静帧留在 `image/env-v1/`、`image/stills-v1/`，逐请求记录于 `image/sidecars-v1/` 与 `image/manifest-v1.json`。成功图片估算 ¥1.062；69 次失败请求的 ¥1.242 是按通道单价推算的未确认费用，实际账单状态未验证；成功费用已超过首轮 ¥0.99 调用计划约 ¥0.072。
- 正文 MP4 与 SRT 已通过 `check_delivery.py`；时长仍为无配音字数估算 311.033 秒，较目标约短 49 秒。交付前没有真人配音可供对轨；若后续加入配音，应以真实音轨重排字幕和镜头时长。
- 附加逐帧 ECC 运镜测量运行约 6 分钟仍未完成，因高 CPU 开销而停止；这不覆盖或改变逐镜渲染时的帧数/尺寸/完整解码检查及全片交付门禁结果。

