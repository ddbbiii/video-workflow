# 人生体验 · 角色参考图（唯一口径）

> 2026-11-17：主角素材统一维护在 `assets/人生体验/characters/catman-20261113/character-reference/`。三视图采用用户选定的轻微面部加强稿；24 格表情保持原样。旧探索稿不再作为生产参考。

> 背景：2026-11-15 凌晨那批参考图（`ref-v3-*.png`、`ref-canonical.png`、`ref-helper-a/b/c.png`、`v7-front/v7-three.png`）
> 用户明确「不是我想要参考的」——它们是 AI 重绘/写实对比/通用卡通人，**与那只猫不是同一张脸**。
> 本文件只定「哪些图算数」；外形规格仍看 `character.md` §二/§三。

## 一、身份来源与正式参考

当前生产使用以下唯一目录中的文件。原猫照片仅用于核对身份，不作为风格参考图。

| 文件 | 用途 |
|---|---|
| `character-reference/identity-source-original.png` | 用户提供的原猫身份来源 |
| `character-reference/ref-face.png` | 原猫标准脸，供身份核对 |
| `character-reference/turnaround.png` | 正面、左侧面、背面三视图，轻微面部加强 |
| `character-reference/face-style-D.png` | 当前平涂画风的单脸基准 |
| `character-reference/expressions/<情绪>.png` | 24 张单档表情；每镜只取所需的一张 |
| `character-reference/expressions-24-contact.jpg` | 表情浏览表，不送入生图 |

生图时以 `turnaround.png` 锁定全身比例、服装和角度，以对应的单张 `expressions/<情绪>.png` 锁定表情。原猫标准脸用于人工核对毛色、纹样和折耳身份。三视图仍需逐镜检查条纹漂移与衣服褶皱变化。

## 二、配角

- 配角统一画成**简笔圆头小人**：圆头、点眼、短线嘴、白手套手（无手指）、简单纯色衣服；与主角共用 2D 手绘线稿和平涂语言，不画写实五官、真人皮肤或写实身体细节。
- `ref-helper-a.png`（青年男）/ `ref-helper-b.png`（中年男）/ `ref-helper-c.png`（女邻居）只用于辅助识别角色类型、年龄、发型和服装轮廓；参考图中的写实质感不得带入成图，配角必须转成上述简笔风格。
- 配角参考**不得拿来当主角的脸或身体参考**。
- 需要跨镜稳定时，先做 1 张该角色的正面参考（2×2 拼版按 `rules/shared/image-grid-generation.md` 裁格），编 `character_id` 后复用。

## 三、生图时怎么提交

| 镜头类型 | 提交的参考图 |
|---|---|
| 近景/情绪/表情镜 | `face-style-D.png` + `expressions/` 中对应单档表情 |
| 中景/全身/站姿镜 | `turnaround.png` 中对应角度；必要时加单张表情 |
| 空镜/环境镜 | 不提交角色参考 |

- 合成参考必须有清晰分区与用途标注，sidecar 记录每一张源图路径与用途；只记合成图路径不算可追溯。
