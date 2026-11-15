# 人生体验 · 角色参考图（唯一口径，2026-11-15 第 2 次修订）

> 背景：2026-11-15 凌晨那批参考图（`ref-v3-*.png`、`ref-canonical.png`、`ref-helper-a/b/c.png`、`v7-front/v7-three.png`）
> 用户明确「不是我想要参考的」——它们是 AI 重绘/写实对比/通用卡通人，**与那只猫不是同一张脸**。
> 本文件只定「哪些图算数」；外形规格仍看 `character.md` §二/§三。

## 一、身份来源与正式参考

| 文件 | 用途 | 说明 |
|---|---|---|
| `assets/人生体验/characters/catman-20261113/reference-v8/identity-source-original.png` | **身份来源**（那只猫本猫） | 用户于 2026-11-15 新提供的脸部参考；原图及去边裁切版均留存在 v8 目录 |
| `assets/人生体验/characters/catman-20261113/reference-v8/ref-face.png` | **标准脸** | 1024² 单脸身份参考；已验收 |
| `assets/人生体验/characters/catman-20261113/reference-v8/turnaround-v8.png` 与 front/three/side/back 裁片 | **四视图/站姿参考** | 已验收；细节 QA 见 manifest |
| `assets/人生体验/characters/catman-20261113/reference-v8/ref-expr-<档>.png` | **六档表情参考** | 已验收；联系表及 QA 见 manifest |
| `assets/人生体验/characters/catman-20261113/ref-look-user-20261113.png` | **目标观感**（只给人看，不进生图） | 画风/气质基准，不作参考图提交 |

- 生图时脸部使用 `ref-face.png`；有明确表情时另附对应单档 `ref-expr-<档>.png`，不得发送整张六格联系表。
- 表情提示仍写明：`表情（只动眼皮、瞳孔、嘴角）：<档位>——<幅度>`。

## 二、正式角色资产（v8）

| 项 | 状态 |
|---|---|
| 标准脸 | `reference-v8/ref-face.png`，1024² 单脸，已验收 |
| 四视图 | `reference-v8/turnaround-v8.png` 与 front/three/side/back 裁片，已验收 |
| 六档表情（单张） | `reference-v8/ref-expr-<档>.png`，已验收 |

联系表、逐张 prompt、通道/尺寸记录和 QA 结论见 `assets/人生体验/characters/catman-20261113/reference-v8/manifest.json` 与 `expressions-contact.jpg`。

> 昨晚 22:40 那批 `ref-v3-<档>.png` 是「写实脸 + 矢量脸」双面板，用户已明确不采用，保持归档。

## 三、已作废（2026-11-15 归档，勿再引用）

`ref-v3-平静/疲惫/发愣/难堪/勉强笑/发憋.png`、`ref-canonical.png`、`ref-hand-cat.png`、
`turnaround-v6-2d.png`、`turnaround-v7-2d.png`、`express-v1.png`。

> 旧名 `v7-front.png` / `v7-three.png` 与临时 `v8-front.png` / `v8-three.png` 均已退出生产目录；当前正式 v8 参考见上表及各集 `image/refs/`。

> `ref-helper-a/b/c.png` **不作废**：它们是配角定装（青年男/中年男/女邻居），与猫的身份参考无关。

归档位置：`projects/人生体验/episodes/20261114-sanzhong/image/refs/_deprecated-20261115/`，只做追溯，不再使用。新一集不复制这些旧主角参考。

## 四、配角

- 配角是**普通真人**，用文字事实卡约束（年龄/发型/衣着/伤情）；定装参考固定为 `ref-helper-a.png`（青年男）/ `ref-helper-b.png`（中年男）/ `ref-helper-c.png`（女邻居）。
- 这三张只锁配角，**不得拿来当主角的脸或身体参考**。
- 需要跨镜稳定时，先做 1 张该角色的正面参考（2×2 拼版按 `rules/shared/image-grid-generation.md` 裁格），编 `character_id` 后复用。

## 五、生图时怎么提交

| 镜头类型 | 提交的参考图 |
|---|---|
| 近景/情绪/表情镜 | `ref-face.png` + 对应单档 `ref-expr-<档>.png` |
| 中景/全身/站姿镜 | `ref-face.png` + v8 对应角度（合成一张，sidecar 记录两源路径） |
| 空镜/环境镜 | 不提交角色参考 |

- 合成参考必须有清晰分区与用途标注，sidecar 记录每一张源图路径与用途；只记合成图路径不算可追溯。
