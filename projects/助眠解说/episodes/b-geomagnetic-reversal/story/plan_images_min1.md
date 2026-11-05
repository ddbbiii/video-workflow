# 生图审批计划：地球的磁场会翻转 第 1 章「第一分钟试做」场景参考 + 首帧（2026-10-01）

> 状态：draft，待批 | 负责人：助眠解说 | 更新：2026-10-01 11:25（北京时间）
> 线：助眠解说（B 线） | 发给：老大（私聊，不经视频号规划转达） | 状态：**待批**（还没有生任何图，也没配音）
> 依据：老大 11:16「先做第一分钟试试」；剧本 `script_v3_ch1.md`（第 2 步待审稿）；规则 `docs/rules/image-approval.md`、`docs/rules/production-flow.md`；格式按 `docs/templates/image-approval-request.md`；画风按 `profiles/b-sleep.yaml` 的 `stills.style_prefix`。

- **用途**：第 1 章 v3 只做开头约 60 秒的试做段，看「信息密 + 开头一句一图」的效果。先出 1 张场景参考图，再出 9 张首帧。
- **统一流程第几步**：6（分镜参考图，1 张）+ 7（首帧，9 张）。出图后先过 `still_gate`，首帧交老大审（🔒）。之后按流程先配音（第 8 步），再做 c02 的图生视频（第 9 步）。
- **说明**：第 2 步剧本 `script_v3_ch1.md` 老大还没明确批。这一分钟的口播就按 v3 原文；老大要改字，先改剧本再出图。

## 1. 第一分钟的范围

- **镜头**：c01–c08 加 c09a，共 9 镜。为了让试做停在一个完整句子上，原来的 c09 拆成两镜：c09a 是沈括一段，c09b 是吉尔伯特一段。`script_v3_ch1.md` 的分镜表已经同步改了。
- **口播（逐字）**：从「带一只罗盘，回到八十万年前。」到「他还说，莫可原其理，没人讲得清原因。」，共 **155 字**（只数汉字）。
- **时长估算**（含 8 个镜间停顿，每个 0.5 秒）：

| 语速 | 时长 |
|---|---|
| 2.8 字/秒 | 约 **59.4 秒** |
| 2.5 字/秒 | 约 66.0 秒 |
| 3.0 字/秒 | 约 55.7 秒 |
| V1b 自然语速 3.81 字/秒 | 约 44.7 秒（语速问题还没定，见 `script_v3_ch1.md` 文末） |

- **备选**：多带一句「后来，人们给过三种主要答案。」（167 字，2.8 字/秒约 64 秒），结尾更像在钩下一段。这样 c09b 要从「第一种」开始，默认不用。

| 镜 | 口播 | 字数 | 估时（2.8 字/秒） | 动法 |
|---|---|---|---|---|
| c01 | 带一只罗盘，回到八十万年前。 | 12 | 4.8 秒 | 剪辑模板：极慢推近 |
| c02 | 标着北的那一端，会指向南方。 | 12 | 4.8 秒 | **AI 图生视频**（LTX-2.3）：指针转向南 |
| c03 | 罗盘没有坏。 | 5 | 2.3 秒 | 剪辑模板：景深，焦点从玻璃移到指针 |
| c04 | 那时地球磁场的南北，和今天相反。 | 14 | 5.5 秒 | 剪辑模板：极慢拉远 |
| c05 | 这样的翻转，地球经历过很多次。 | 13 | 5.1 秒 | 剪辑模板：慢慢上摇 |
| c06 | 这一期，分六个问题来讲。 | 10 | 4.1 秒 | 剪辑模板：极慢横移（左→右） |
| c07 | 罗盘为什么指北？凭什么说磁场翻过身？多久翻一次？ | 21 | 8.0 秒 | 剪辑模板：慢推 |
| c08 | 一次翻多久？差点翻过去，会怎样？现在会不会翻？ | 19 | 7.3 秒 | 剪辑模板：极慢推近 |
| c09a | 先问第一个问题。九百多年前，沈括写道，磁针指南，却常微微偏东。这个偏差，就是磁偏角。他还说，莫可原其理，没人讲得清原因。 | 50 | 17.9 秒（末镜，不加停顿） | 剪辑模板：慢推，焦点从握笔的手移到悬针 |

## 2. 要不要场景参考图

- 这一段没有角色，不做三视图。
- **要 1 张：R1 罗盘。**同一只罗盘会出现在 c01（远景）、c02（俯视特写，还是 AI 镜的首帧）、c03（特写）、c07（放在岩石上）四镜，后面 c09b、c15 也要用，造型和配色必须一致。
- **地球不另做参考图。**只有 c04、c08 两镜出现地球，c08 直接把 c04 选中的那张当参考图传进去。
- **其他镜不用参考图：**c05 岩壁、c06 地平线光点、c09a 书桌，各自只出现一次，没有一致性要求。
- R3 地球剖面这一分钟用不到，等后面整章出图时再申请。

## 3. 统一画风和格式

- **画风前缀**（照 `profiles/b-sleep.yaml` 的 `stills.style_prefix`，每张都加）：`Minimal calm night concept illustration for a sleep-aid science video. Dark, calm, soft and sparse: deep indigo and navy palette, low contrast, soft diffuse glow, large dark negative space, gentle film grain, quiet and soothing.`
- **画幅说明**（首帧都加）：`Vertical portrait image (2:3, it will be cropped to 9:16): keep the main subject inside the central 80% of the width, nothing important near the left or right edges.`
- **结尾**（每张都加，照 profile 的 `style_suffix` + `no_text_clause`）：`Few elements, nothing bright or busy. No text, no letters, no numbers, no watermark.`
- **罗盘统一描述**（下文写作【罗盘】）：`an old brass pocket compass: round and palm-sized, a worn brass rim, a dark navy dial marked only with fine thin tick marks (no letters, no numbers, no symbols), a slim needle whose one end is a soft warm amber-red and whose other end is pale silver, a small brass pivot cap in the centre, a clear glass cover`。表盘不写 N / S，「标着北的那一端」用暖红色的针尖表示。
- **版权和肖像**：
  - 不用任何现成作品或照片做参考。
  - 地球不画可辨认的城市灯光，卫星没有标志。
  - 沈括不露脸，只画一只手和衣袖。
  - 纸上只有虚化、认不出的墨迹，避免生成乱码汉字，也过得了 `still_gate` 的 OCR 检查。

## 4. 逐张清单

### 张数和参考图

| # | 镜 | 内容 | 参考图 | 尺寸（请求） | 动法 | 张数（候选） |
|---|---|---|---|---|---|---|
| 1 | R1（参考图，不进成片） | 同一只罗盘，俯视一张 + 低角度四分之三侧一张，纯深色背景 | 无 | 1536×1024（横版，两视图并排） | — | 1 |
| 2 | c01 | 远古荒原的夜，罗盘小小地放在黑色火山岩上，头顶星空 | R1 | 1024×1536 | 剪辑模板 | 1 |
| 3 | c02 | 罗盘俯视特写，暖红针尖朝画面上方（北），这是图生视频的首帧 | R1 | 1024×1536 | **AI 图生视频** | 1 |
| 4 | c03 | 罗盘斜角特写，玻璃完好，映着几颗星；暖红针尖朝下（南） | R1 | 1024×1536 | 剪辑模板 | 1 |
| 5 | c04 | 太空里的夜色地球，几条淡磁力线；两极一冷一暖 | 无 | 1024×1536 | 剪辑模板 | 1 |
| 6 | c05 | 月光下的黑色岩壁，一层层明暗交替的薄岩层 | 无 | 1024×1536 | 剪辑模板 | 1 |
| 7 | c06 | 低平地平线上一排六个等距的小暖光点 | 无 | 1024×1536 | 剪辑模板 | 1 |
| 8 | c07 | 罗盘放在层叠火山岩上，旁边一盏小陶油灯 | R1 | 1024×1536 | 剪辑模板 | 1 |
| 9 | c08 | 同一颗地球，更小、更低；上方三颗无标志的小卫星排成一行掠过 | c04 选中图 | 1024×1536 | 剪辑模板 | 1 |
| 10 | c09a | 夜里的宋代书桌：丝线悬着的细针；只露手和衣袖握毛笔，纸上只有虚化墨迹；小油灯 | 无 | 1024×1536 | 剪辑模板 | 1 |

### 中文要点 + 英文提示词草稿

每条实际发送时都是：画风前缀 + 下面的内容 + 画幅说明（R1 不加）+ 结尾。

**R1 罗盘参考图**
- 要点：同一只罗盘画两次。左边俯视，右边放在平面上的低角度四分之三侧视。纯深藏青背景，光线柔和均匀，没有别的东西。
- 英文：`Object reference sheet for one single object, shown twice side by side on a plain very dark navy background with even soft dim light: on the left seen straight from above, on the right resting on a flat surface seen from a low three-quarter angle. The object is {【罗盘】}. Both views show exactly the same compass with identical proportions and colours. No other objects, no shadows except a faint contact shadow.`

**c01**
- 要点：远古荒原夜色。前景黑色平坦火山岩，地平线很低很暗，没有人和建筑，最多一两棵远处的稀疏树影。罗盘很小，放在画面中下部。上方三分之二是星空。
- 英文：`A prehistoric wilderness at night, long before any people: flat black volcanic rock in the foreground, a faint dark horizon low in the frame, at most one or two sparse distant tree silhouettes, no people, no buildings, no roads. Resting on the rock in the lower middle of the frame, small in the scene, lies the compass from the reference image ({【罗盘】}), catching a soft glint of starlight. Above it a deep starry sky with a faint band of stars fills the upper two thirds. The reference image shows the exact compass to draw: keep its shape, brass colour, dial and needle identical.`

**c02（AI 图生视频首帧）**
- 要点：罗盘俯视特写，占画面中部，放在黑色火山岩上。暖红针尖朝画面上方，银白一端朝下。玻璃上有一点柔和星光反光。指针要完整清楚、不被遮挡，后面要让它动。
- 英文：`Top-down close-up of the compass from the reference image ({【罗盘】}), lying on dark volcanic rock and filling the central part of the frame. The warm amber-red end of the needle points to the top of the frame, the pale silver end to the bottom. The needle is complete, sharp and unobstructed. A soft starlight reflection on the glass, dark surroundings. The reference image shows the exact compass to draw: keep its shape, brass colour, dial and needle identical.`
- 图生视频动作提示（第 9 步用，这次不跑）：`The compass needle slowly swings about 180 degrees until its warm amber-red end points to the bottom of the frame, wobbles gently twice and settles. The compass, the rock and the camera stay completely still. No other motion, no light changes.`

**c03**
- 要点：同一只罗盘，稍斜角特写。玻璃完好、干净、没有裂纹，映着几颗星。暖红针尖朝画面下方（接 c02 转完以后的样子）。浅景深，背景很暗。
- 英文：`Close-up at a slight angle of the same compass from the reference image ({【罗盘】}). The glass cover is intact and clean, not cracked, reflecting a few soft stars. The warm amber-red end of the needle now points to the bottom of the frame. Shallow depth of field: the front of the glass rim softly in focus, the needle just behind it. Very dark background. Keep the compass identical to the reference image.`

**c04**
- 要点：太空中的夜色地球，深蓝，没有城市灯光。在画面中上部，在大片星空里显得很小。几条很细很淡的浅蓝磁力线从一极绕到另一极。北极附近一点暖琥珀光，南极附近一点冷蓝光。不画箭头、不写字。
- 英文：`Planet Earth seen from space, its night side a dark deep-blue globe with no city lights, centred slightly above the middle and small within a large black starfield. A few very faint, thin, pale-blue magnetic field lines loop from one pole around to the other like a delicate glowing cage. Near the north pole a faint warm amber glow, near the south pole a faint cool blue glow. No arrows, no labels, no diagrams.`

**c05**
- 要点：正对着的黑色岩壁，许多水平薄层玄武岩。明暗只是微微交替，像淡淡的条纹。侧面月光，没有植物和人，上方大片暗部。
- 英文：`A dark basalt cliff face at night seen straight on, made of many thin horizontal rock layers; the layers alternate very subtly between slightly lighter and slightly darker bands, like faint stripes. Dim moonlight grazes it from one side. No plants, no people. Large dark empty space above the cliff.`

**c06**
- 要点：开阔安静的夜色原野，地平线又低又平，在画面下三分之一。地平线上六个等距的小暖光点排成一行，像远处的小灯。天空深藏青，星很少。
- 英文：`A wide, calm, dark night landscape with a low flat horizon in the lower third. Along the horizon, exactly six small warm amber points of light stand evenly spaced in one row, like distant lanterns with a soft glow. The sky above is deep navy with only a few stars. Nothing else.`

**c07**
- 要点：同一只罗盘放在一叠层层的暗色火山岩上。旁边一盏小陶油灯，小火苗安静，暖光很柔。低角度四分之三侧，暖红针尖朝远处。上方大片留白。
- 英文：`The same compass from the reference image ({【罗盘】}) resting on a small stack of layered dark volcanic rocks, seen from a low three-quarter angle, the warm amber-red end of its needle pointing away from the viewer. Beside it a tiny clay oil lamp with a small calm flame gives a soft warm glow. Dark surroundings with large empty space above. Keep the compass identical to the reference image.`

**c08**
- 要点：用 c04 选中的那张当参考，同一颗地球。这次地球更小，在画面下部。上方三颗很小的卫星松散地排成一行掠过，只有暗暗的剪影和一点反光，没有标志。
- 英文：`The same planet Earth as in the reference image (seen from space, dark deep-blue night side, faint thin pale-blue field lines), this time smaller and lower in the frame. Three tiny satellites in a loose line pass through the dark space above it, each only a small dim silhouette with a faint glint, no logos, no markings, no flags. Large black starfield.`

**c09a**
- 要点：夜里宋代风格的书桌近景。右边一根细钢针用一根细丝线挂在小木架上，针身相对桌面预先画出的木条南北基准线轻微偏向东方，明确表现“磁针指南、微微偏东”，不出现文字或罗盘字母。左边只露一只手和小臂，穿朴素的深蓝布衣袖，不露脸、不出现人，握着毛笔停在浅色纸上。纸上只有几笔虚化、认不出的墨迹。旁边有砚台，一盏小油灯给出柔和暖光。
- 英文：`A dim Song-dynasty-style scholar's desk at night, seen close. On the right, a slim steel needle hangs from one fine silk thread tied to a small wooden stand. Beneath it, a simple straight wooden north-south reference line is visible on the desk with no letters, no numbers and no labels; the needle points south while its axis is visibly a few degrees east of that reference line, making the historical magnetic declination visible without text. On the left, only a hand and forearm in a plain dark-blue cotton sleeve (no face, no person visible) hold a calligraphy brush resting above a sheet of pale paper; the paper shows only a few soft, blurred, out-of-focus ink strokes that cannot be read, no legible characters. An ink stone nearby and a small oil lamp giving a soft warm glow. Very dark surroundings, quiet low contrast, no diagram or writing.`

## 5. 模型、接口、放大

- **模型和分组**：中转站 `https://dklapi.com/v1`，「原生1k」分组 `gpt-image-2-1K`，0.04 元/张。key 只从环境变量 `IMAGE_RELAY_KEY_1K` 读，不打印、不写进文件。11:2x 检查过，变量在。
- **接口**：
  - 带参考图的 6 张（c01、c02、c03、c07 用 R1；c08 用 c04）：走太空猫线已经跑通的 `POST /v1/images/edits`（multipart，`image[]` 传 PNG，`n=1`）。参考图按长边 1024 缩成 PNG。
  - 不带参考图的 5 张（R1、c04、c05、c06、c09a）：打算用 `POST /v1/images/generations`。这个接口在中转站上还没用过；第一张（R1）就当验证，不通就停下来报告，不自己换工具或模型。
  - 竖版尺寸 `1024x1536` 也是第一次用（太空猫线只用过 `1536x1024`）。如果被拒或出图比例不对，同样停下来报告。
- **全模型组 / 本地 ComfyUI**：不用。
- **放大**：首帧要放大到 1080×1920（1k 出图约 1024×1536）。
  - 建议照 profile 的 `out_size`，用 Lanczos 等比放大到高 2112（×1.375），左右裁成 1188×2112，留 10% 给剪辑模板推拉；合成时再出 1080×1920。左右各裁掉约 8%，所以提示词里要求主体在中间 80%。
  - 暗、柔、颗粒感的画面，Lanczos 放大 1.4 倍左右问题不大。放大工具规则里还没定，**请老大确认用 Lanczos**。
  - c02 的首帧交给 LTX-2.3 时，用的是工作流自带的输入尺寸（352×640 → 704×1280），出片后合成时再放大到 1080×1920。
- **质检**：出图后照 `profiles/b-sleep.yaml` 的阈值跑 `scripts/still_gate.py`，要先给这一段写 shotlist。没过的才重出。R1 只看罗盘造型对不对，不跑亮度门槛。

## 6. 张数和花费

- **方案 A（建议）：每张 1 个候选。**
  - 10 张（参考图 1 + 首帧 9）× 1.3 重试余量 = 13 → 调用上限 **13 次**。
  - 预估最多 **0.52 元**；一次就过只要 0.40 元。
  - 什么情况重出：`still_gate` 没过、出现文字或乱码、罗盘和 R1 不一致、c02 指针不清楚。每重出一张算一次，用满 13 次就停下来报告。
- **方案 B：每张 2 个候选**（profile 的 `candidates: 2`），不建议，c09a 等单张场景用不着。R1 仍出 1 张：(9×2 + 1) × 1.3 = 24.7 → 上限 25 次，最多约 1.00 元。
- **失败处理**：失败的请求如果也收费，也算进上限。遇到报错、效果不对、要改方案，一律停下来私聊老大。

## 7. 这一分钟要的图生视频（第 9 步，这次不跑，先报预估）

- **AI 镜**：只有 c02（罗盘指针转向南）。按 2.8 字/秒约 4.8 秒，占这一分钟的 8%。
- **LTX-2.3 两段式**（`docs/runbooks/i2v-local.md`，组件 40）：每段 5 秒，需要 **1 段**。实测一段约 280 秒，所以本地 GPU 约 **4.7 分钟**；重做一次是 9.4 分钟。
- **顺序**：按「先配音再图生视频」，c02 的实际时长要等配音过了 `vo_gate` 再定。超过 5 秒就让最后一帧停住，不多出一段。
- **备选**：指针转动如果变形或不听提示，可以改用 MiniMax H3（关键镜头用的，一段约 1001 秒，约 16.7 分钟）。要换的话先报老大。
- **其余 8 镜**都是剪辑模板（推、拉、摇、景深），不占 GPU 生成时间。

## 8. 其他

- **是否新角色**：否，没有角色。
- **存档**：
  - 本文件放在项目目录 `plan_images_min1.md`，同一份也放在 `approvals/2026-10-01-第1章第一分钟首帧.md`。老大批复的原话和时间两边都补上。
  - 出图后放 ddbbi `E:\program\1project\video\zhumian\b-geomagnetic-reversal\stills\`（参考图放 `refs\`）。
- **老大批复（原话、时间）**：（待批）
