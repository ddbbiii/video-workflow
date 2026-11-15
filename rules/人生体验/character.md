# 人生体验 · 角色规则 v7（主角猫头猫爪 + 配角简笔圆头小人 · 2026-11-15）

> v1 空白头 → v2 整只橘猫 → v3 矮个子人形 + 橘猫头 → **v4 锁定为「用户家那只折耳橘虎斑」** → v5 生图配方去色板 → **v6 猫手猫脚 + 单档表情参考图**。
> 2026-11-13 用户给了一张自家猫的照片（`ref-cat-user-20261113.png`）与一张目标观感图，并确认画风走**首集的 2D 手绘（线稿+平涂）**。
> **2026-11-14 v6（用户指令「改成猫手猫脚试试」→「画风就按照这版持久化下来」）**：
> 手/脚由人手人脚改为**猫爪**；不穿鞋；表情改为**每镜只取一档**并配单档参考图（六格表整张会跑脸）。
> 头身比、头型、毛色、耳折、眼型、白围兜一律不变——头是唯一保留细节的部位。
> **v7（2026-11-15 用户指令）**：① 定装换成 `turnaround-v7-2d.png`（只把手改成猫爪，其余不动）；② **配角改为简笔圆头小人**（圆头、点眼、短线嘴、白手套手），不再画写实真人——起因：写实配角与猫头同框显 3D、且每镜换脸。
> EP01 的定装（`routeB-B2-sheet.png`、`cat-sheet-final.png`、`CHARACTER_LOCK.md`）随 `episodes/20261110-biye/` 目录一起丢失，本文件 + `assets/人生体验/characters/catman-20261113/` 是唯一现存真源。

## 一、定位

**一个矮个子的人形身体，顶着一颗折耳橘虎斑猫头，手脚是猫爪。**
身体仍是人的结构（肩、躯干、双腿直立行走），头是同一只猫的脸，**手和脚换成猫爪**；不穿衣扮猫、不拟猫、不留尾巴。

## 二、身份锚点（缺一即废片）

| 项 | 规格 |
|---|---|
| 品种 | 折耳橘虎斑（Scottish Fold），圆脸厚颊、短口鼻 |
| 头身比 | **约 3–3.2 头身**；头宽略大于肩宽；**脖子极短，头直接坐在窄肩上**（不许长脖子、不许悬空） |
| 耳 | 小、向前折贴颅顶，正面只露折边；**不得立耳** |
| 眼 | 大圆黑瞳、只留一圈窄琥珀金边、一点高光；上眼皮略压 |
| 鼻/口鼻 | 粉鼻头、鼻缘略深；宽奶油口鼻垫、三排胡须点、白胡须 |
| 毛色 | 浅奶油橘底；额头 M 纹与脸颊/腿部软虎斑；胸口白围兜 |
| 手 | **猫爪**：圆润短爪、三趾线、一点粉色肉垫；**无人手手指、无毛手** |
| 脚 | **猫爪**：同上，**不穿鞋**，裤脚收在踝上 |
| 尾 | **无尾巴**（v6 仍保留此条） |
| 服饰 | 灰连帽衫 + 黑裤（日常）；白安全帽 + 橙色反光背心（工地，赤爪） |

## 三、画风（与 `style.md` v3.5 一致）

- **人物简填色**：单一线宽（深灰蓝）、平色块、身体/衣服每个物件最多 2–3 个色调、无渐变、无颗粒、无纸纹；环境画法按 `style.md` v3.5 §2.1，不套人物禁渐变约束。
- **头是唯一保留细节的部位**：毛用 2–3 个平色 + 几笔短线表现，保留额头 M 纹、脸颊虎斑、白围兜、折耳边、粉鼻、白胡须。
- 身体和衣服是大色块；环境可有手绘层次。主角不做写实毛、不做照片感、不做 3D、不做吉祥物玩偶感。

## 四、定装资产（2026-11-15 第 2 次修订：只认三份）

**参考图口径见 `references.md`（唯一真源）**，本节只列结论：

| 文件 | 用途 |
|---|---|
| `reference-v8/identity-source-original.png` | 用户于 2026-11-15 新提供的身份来源（那只猫本猫） |
| `reference-v8/ref-face.png` | 标准脸（1024²，已验收） |
| `ref-look-user-20261113.png` | 目标观感，只给人看，不进生图 |
| `reference-v8/turnaround-v8.png` 及 front/three/side/back 裁片 | 四视图，已验收 |
| `reference-v8/ref-expr-*.png` | 六档单张表情，已验收 |

- `turnaround-v6-2d.png`、`turnaround-v7-2d.png`：**作废**（人手 + 黑鞋，与 v6「猫爪、不穿鞋」冲突）。
- `express-v1.png`、`ref-canonical.png`、`ref-v3-*.png`、`v7-front/v7-three.png`、`ref-hand-cat.png`：**作废**；旧文件只在 EP03 的 `_deprecated-20261115/` 归档中留作追溯。`ref-helper-a/b/c.png` 仍是有效配角定装，不得标为作废。
- 2026-11-15 早前那套「ref-v3 双面板 / 只发该档表情 / 配角简笔圆头小人」的写法一并作废。


## 五、生图配方（每镜）

```text
通道：见 shared/image-api/channel-policy.json 当前 active 策略；角色镜走 /images/edits，并逐镜记录实际通道
参考图：脸部/表情镜一律使用 image/refs/ref-face.png（唯一脸部参考，表情写在提示词里）；站姿/全身镜需要 v8 四视图，未出前暂停该类镜；配角使用对应 ref-helper-<型>.png
prompt = 风格块（style.md §四，无色名）
       + 场景事实卡（中文：环境/动作/服装/道具/光位）
       + 色彩与光线行（必填，色值取该集 image/color-plan.json）
       + "Draw the head and the body as ONE drawing by the same hand: same dark grey outline weight, same flat
          colour treatment. The head keeps the reference cat's identity (head shape, round cheeks, short muzzle,
          small ears folded forward, big round black eyes with a thin amber rim and one highlight, pink nose,
          cream muzzle, white whiskers, white chest bib, cream-orange tabby fur with the M stripe on the forehead),
          fur painted as two or three flat tones plus a few short strokes, NOT photorealistic fur.
          He stands upright on two legs, short stocky build about 3.2 head-heights, very short neck, but his
          HANDS and FEET are CAT PAWS: rounded furry paws with three short toe lines and a hint of pink pads.
          NO human fingers, NO human toes, NO shoes, no tail. Grey hoodie one flat tone, black trousers one flat
          tone, trouser hems just above the bare paws. Only the protagonist is a cat-headed, cat-pawed person;
          every other person is a very simple round-headed cartoon figure: round head, two dot eyes, short line mouth, white mitten hands with no fingers, plain dark clothes — deliberately simpler than the protagonist."
       + "The face reference locks only facial identity, markings and this one expression. The v7 turnaround
          reference locks body proportions, silhouette, paws and clothing. Neither reference sets the colour
          grade, background colours or lighting."
       + 表情行：表情（只动眼皮、瞳孔、嘴角，不张嘴大喊、不哭变形）：<档位>——<幅度描述>。
```

> **v2 修正**：删掉 `muted desaturated earth palette`（整片泛黄来源之一）；参考图不得锁定色调。
> **v6 修正**：人手改为猫爪；**表情参考图只发该镜那一档**，六格整张会让模型把六张脸平均成新脸（实测 S47/S60/S166/S196 跑偏）。
> **v6.1 修正（2026-11-14）**：① 人物在场改由 `cast / closeup_part / view_angle` 字段决定，不再从 `visual` 中文猜（EP03 有 16 镜因此没发参考图、猫被画成灰白猫）；② 老陈必须有定装参考（§4.1）；③ 侧面/背面不做脸部特写（§4.2）；④ 手部特写必须发手部参考。
> **道具归属**：谁拿什么写进该集 `story/props.json`，并加「不要把道具塞进另一个人手里」；绷带、伤口这类状态同样要写清属于谁。

## 六、表情（6 档，只动眼皮/瞳孔/嘴角）

平静（默认）／疲惫（上眼皮压一半、视线微垂）／发愣（瞳孔略放大、视偏、嘴微张一点）／难堪（视线偏开、嘴角压平）／勉强笑（单侧嘴角抬起一点）／发憋（眉压低、嘴角下压、下唇抿住）。
**每镜只取一档**，写在该集 `story/expressions.json`；参考图只发这一档。
**不做**：张嘴大喊、哭变形、龇牙、夸张惊讶、爱心眼、卖萌。

## 七、验收（任一不过重出）

- [ ] 只有主角是猫头猫爪；**配角是简笔圆头小人**（点眼、短线嘴、白手套手，见 §4.1），不是写实真人、不是 3D；
- [ ] **每个在场角色都对得上 `cast` 字段**，且该角色这一镜发过参考图（缺图即返工）；
- [ ] 配角与 `ref-helper-<型>.png` 并排看是同一型（发型/胡子/体型一致），年龄不漂移；
- [ ] **人脸角度合规**：`side` / `back` 镜没有脸部情绪特写（§4.2）；
- [ ] **手部合规**：主角是猫爪（三趾线、肉垫），老陈是正常人手（五指、指甲、无关节缝、无木偶感）；
- [ ] 参考图本身合规：每部位 ≤3 平色、无喷枪过渡、无柔光边（`style.md` §六）；
- [ ] 站姿镜同时使用 `ref-face.png` 与 v8 全身角度参考；配角镜使用对应 `ref-helper-a/b/c.png`；
- [ ] 折耳向前折贴、无立耳；黑瞳+窄琥珀边+高光；与 `ref-face.png` 并排看是同一只猫；
- [ ] 约 3–3.2 头身、脖子极短直接坐窄肩、头宽略大于肩；
- [ ] **手/脚是猫爪**：三趾线、肉垫、无人手手指、不穿鞋；无尾巴；
- [ ] 头是唯一保留细节的部位，身体与场景是 2–3 个平色块，无渐变无颗粒无纸纹；
- [ ] 表情落在该镜指定档位，1080p 下能分辨；
- [ ] 画面无文字、水印、logo、漫画音效符号；
- [ ] 跨镜一致（头型、眼距、毛色、服装、爪）。

## 关联

- 画风：`style.md` v3 ｜ 色彩：`color-script.md` v1.1 ｜ 交付：`../shared/delivery.md`
- 定装：`assets/人生体验/characters/catman-20261113/`
- 角色锁：同目录 `CHARACTER_LOCK.md`（v6：手/脚条目已由本文件取代）
