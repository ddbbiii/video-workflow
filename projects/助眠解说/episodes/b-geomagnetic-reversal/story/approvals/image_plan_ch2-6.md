# 生图审批计划：地球的磁场会翻转 第 2–6 章首帧（2026-10-02，草稿）
> 线：助眠解说（B 线） | 发给：老大（私聊） | 状态：**老大 2026-10-02 01:07（北京时间）已批；G2、G3 已出图（2 次调用，0.32 元），已切格、做审阅图，等老大挑格。没有放大。**（原草稿状态：待老大批，未调用接口）
> 负责人：助眠解说 | 写于：2026-10-02 01:0x（北京时间）
> 依据：`docs/rules/image-approval.md` 第 0 节（B 线全程不出单图，只用 4×4 宫格和复用，老大 2026-10-02 00:32 定）、`docs/rules/production-flow.md`、格式照 `approvals/image_plan_ch1_v4.md`；剧本 `script_v4_ch2-6.md`（老大经主线预先认可）；第 1 章已有图：`stills/test/`、`stills/min1/`、G1 宫格 `stills/ch1_v4/`（G1 还在等老大审）。

---

## 0. 一句话
第 2–6 章共 46 镜：**20 镜复用已有的图**（第 1 章首帧 + G1 格子 + 本集内重复用），**26 个新画面放进 2 张 4×4 宫格（G2、G3），共 2 次调用**，多出的 6 格给最长、最难的镜各出一个候选。基本花费 **2 × 0.16 = 0.32 元**；加上每张宫格各 1 次整张重画的预留，**上限 4 次、0.64 元**。不出单图，不出封面。

## 1. 基本信息（按模板）

- **用途**：第 2–6 章（约 24 分钟）的首帧。
- **统一流程第几步**：7 首帧（出图前先批本计划；出图后跑 `still_gate`，🔒 老大审）。不另出分镜参考图：B 线没有固定角色；同一张宫格里的格子本来就同一次生成、同一套配色。
- **是否新角色**：否。没有人物（ch5-c07 只有洞穴、火光、赭石和骨针，不出人）。不做三视图。
- **配音时长**：还没配（配音是下一个单独的活）。下表按「字数 ÷ 3.4」估，全部 46 镜约 1458 秒；其中新格画面撑约 911 秒（62%），复用画面撑约 547 秒。时长变了只影响推拉速度，不影响出几张图。
- **AI 图生视频**：0 镜（全部剪辑模板）。

### 1.1 复用哪些现有图

| 图 | 文件（box） | 本计划用在 |
|---|---|---|
| 第 1 章 c06（六个光点） | `stills/min1/c06.png` | 每章开头的问句镜：ch2-c01、ch3-c01、ch4-c01、ch5-c01、ch6-c01（第 N 章后期把第 N 颗调亮，不重出图） |
| 第 1 章 c05（层状岩壁） | `stills/min1/c05.png` | ch2-c05（松山） |
| 第 1 章 c04（太空地球） | `stills/min1/c04.png` | ch4-c09、ch6-c04 |
| 第 1 章 c08（地球 + 三颗卫星） | `stills/min1/c08.png` | ch5-c09 |
| 第 1 章 c01（荒原罗盘） | `stills/test/c01.png` | ch6-c09（全片收尾，首尾呼应） |
| G1 格10 / 11 / 12 / 13 / 15 / 16 | `stills/ch1_v4/cells/G1_cell*.png` | 格15→ch2-c02，格16→ch3-c04、ch5-c08，格13→ch4-c04，格12→ch4-c07，格11→ch6-c06（要压暗），格10→ch6-c08 |
| 本集新格重复用 | G2/G3 切出后 | N06→ch2-c10，N15→ch5-c03，N17→ch5-c05 |

- **G1 还在等老大审**。如果格10–16 里有不能用的，对应镜改用：ch3-c04 / ch5-c08 → 第 1 章 c04 换裁切；ch4-c04 / ch4-c07 → 第 1 章 c14 最终用的那一格；ch6-c06 / ch6-c08 → 第 1 章 c13 最终用的那一格；ch2-c02 → 第 1 章 c15 用的那一格。都还是复用，不加调用。

## 2. 宫格清单

| 宫格编号 | 3×3 / 4×4 | 角色 / 场景 | 参考图 | 每格分别给哪一镜 |
|---|---|---|---|---|
| G2 | **4×4**（B 线默认） | 第 2–3 章 13 个空场景 + 3 个候选 | **无**（0 张） | 格1→ch2-c03（N01），格2→ch2-c04（N02），格3→ch2-c06（N03），格4→ch2-c07（N04），格5→ch2-c08（N05），格6→ch2-c09（N06），格7→ch3-c02（N07），格8→ch3-c03（N08），格9→ch3-c05（N09），格10→ch3-c06（N10），格11→ch3-c07（N11），格12→ch3-c08（N12），格13→ch3-c09（N13），格14→ch2-c07 候选（N04-B），格15→ch2-c09 候选（N06-B），格16→ch3-c08 候选（N12-B） |
| G3 | **4×4**（B 线默认） | 第 4–6 章 13 个空场景 + 3 个候选 | **无**（0 张） | 格1→ch4-c02（N14），格2→ch4-c03（N15），格3→ch4-c05（N16），格4→ch4-c06（N17），格5→ch4-c08（N18），格6→ch5-c02（N19），格7→ch5-c04（N20），格8→ch5-c06（N21），格9→ch5-c07（N22），格10→ch6-c02（N23），格11→ch6-c03（N24），格12→ch6-c05（N25），格13→ch6-c07（N26），格14→ch4-c06 候选（N17-B），格15→ch5-c07 候选（N22-B），格16→ch6-c05 候选（N25-B） |

- 为什么按章分两张：同一章的画面在同一张里，配色前后一致；某一张出问题，只影响两三章。
- 候选格给谁：G2 给 ch2-c07 岩样条（最怕冒字）、ch2-c09 洋中脊（本章最长镜，又在 ch2-c10 复用）、ch3-c08 地幔（全章最长镜）；G3 给 N17 多极地球（用在两章）、ch5-c07 洞穴（主体近景）、ch6-c05 南大西洋（地图类最容易画错大陆形状）。
- 宫格怎么出、怎么切：和 G1 一样。一次调用 `POST /v1/images/generations`，`size=1024x1536`，`n=1`，不带参考图；切图用项目里已有的 `gen/cut_grid.py`（按白线自动找分隔）；放大照 `docs/runbooks/upscale.md` 到 1188×2112。
- 风险（G1 已经遇到过）：行高不均（G1 是 374/370/349/422）、个别格冒类数字的字形、亮度超门槛。处理：能用的格照用，不能用的那镜先换同镜候选格或改成复用；超过一半的格不能用，才动用重画预留，先停下来报老大。

**提示词草稿（英文，实际发送 = 画风前缀 + 这段 + 结尾）**

画风前缀（照 `profiles/b-sleep.yaml` `stills.style_prefix`，和 G1 一样）：`Minimal calm night concept illustration for a sleep-aid science video. Dark, calm, soft and sparse: deep indigo and navy palette, low contrast, soft diffuse glow, large dark negative space, gentle film grain, quiet and soothing.`

**G2**

```
One single image laid out as a 4 by 4 grid of 16 separate panels of equal size, each panel vertical (2:3), all four rows exactly the same height, separated by thin plain white lines, no outer border, no captions. Every panel is its own independent scene in the same calm dark style. Panels from left to right, top row first:
1. A small old stone observatory hut on the summit of a dark volcanic dome at night, one window glowing faint warm amber; far below, a chain of rounded cone volcano silhouettes; no city lights, no people.
2. A moonlit roadside cliff outcrop beside a small old stone arch bridge over a dark stream: an upper layer of dark grey basalt resting on a lower layer of brick-red baked clay, the boundary clear.
3. A dim laboratory wooden bench at night: a small electric furnace with a dull red glow at its mouth, a small pale piece of pumice inside, a few loops of copper wire coil around the furnace; no people, no dials or readouts.
4. On a long dark table, a row of small cylindrical rock core samples lying side by side, alternating dark and light in colour like a long barcode, lit by one very weak warm desk lamp; no labels.
5. A small old research ship on a calm dark sea at night, a long cable trailing from its stern down into the water; deep below the surface, faint long parallel stripes of lighter and darker seafloor.
6. Looking down on a mid-ocean ridge on the deep seafloor: a central rift valley with a faint dull red glow, and on both sides symmetric parallel bands of lighter and darker rock stretching outward.
7. One long horizontal band across a dark background made of irregular alternating light and dark blocks: wide and few blocks at the left end, becoming narrower and denser toward the right end; abstract, no text, no numbers.
8. An empty rural bus shelter at night: one street lamp, one wooden bench, an empty road disappearing into darkness; the shelter has no sign boards and no writing anywhere.
9. A Cretaceous night: far away by a quiet river, the dark silhouette of a long-necked sauropod dinosaur standing still, a starry sky above, a little starlight reflected on the water.
10. Looking across the deep seafloor: in the foreground a strip of alternating light and dark bands, fading into a vast smooth dark plain of seabed with no stripes at all in the distance.
11. A dark rocky sea coast at night with low basalt cliffs and slow gentle waves, very faint moonlight.
12. A corner of a planetary cross-section: a dark brown-red mantle with a few slow rising plumes of dull red heat and sinking cooler patches, wrapped around a glowing orange liquid outer core below.
13. A small pot on a kitchen stove at night, the flame very low, the soup surface calm, one thin wisp of steam rising; everything around is dark.
14. The same rock samples seen closer, only a few cylinders, alternating dark and light.
15. The same mid-ocean ridge seen from a lower angle, the glowing rift in the centre and symmetric bands receding into darkness.
16. The same mantle plumes seen wider, more of the glowing outer core visible.
In every panel keep the main subject inside the central 80% of the panel width, few elements, nothing bright or busy.
```
**G3**

```
One single image laid out as a 4 by 4 grid of 16 separate panels of equal size, each panel vertical (2:3), all four rows exactly the same height, separated by thin plain white lines, no outer border, no captions. Every panel is its own independent scene in the same calm dark style. Panels from left to right, top row first:
1. A dark wall of layered black lava rock at night with a neat row of small round drilled sampling holes; very dim, no people.
2. A polar ice sheet at night: tiny faint specks of light falling slanting from high in the sky; the lower half cut away to show many thin pale-blue layers of ice beneath the surface.
3. A single vertical sediment core standing upright against a dark background, with fine thin layers stacked from top to bottom, colours changing slowly with depth, weak side light.
4. Planet Earth at night in space: faint magnetic field lines no longer arching neatly from pole to pole but tangled into small loops in several places, with three or four tiny warm and cool glowing points scattered over the globe.
5. A dim experimental hall: a large horizontal stainless steel cylinder with an impeller at each end and one small round window in its side, silvery liquid metal churning behind the window; no people, no labels.
6. At night, a line of rounded grassy volcanic cones in a chain across the landscape; in the foreground a long-cooled black ancient lava flow; very faint moonlight.
7. A small wooden spinning top on a dark wooden table, tilted strongly to one side but still spinning and not falling, a little warm side light.
8. A prehistoric European night: low valleys and grassland under a faint green aurora curtain, one lone tree on the land, no people.
9. The mouth of a cave at night with a small fire glowing inside; on a stone ledge in the foreground a small lump of red ochre and one thin bone needle; no people.
10. A seventeenth-century night by a river: on a wooden table a large mariner's compass and a brass quadrant, an oil lamp beside them; the compass card has no letters and no numbers.
11. At night, the silhouette of an old domed observatory building on a hilltop; in the foreground grass, a small compass lying flat with a long slim needle; no letters on the compass.
12. Looking down from space at the dark South Atlantic between the faint dark outlines of South America and Africa, a soft dim violet glow hovering over the ocean between them; no city lights, no text.
13. The dark silhouette of a cylindrical space telescope gliding high above the night-side Earth, and below it a soft dim violet glow over the South Atlantic.
14. The same tangled multi-pole Earth seen from further away, smaller in the frame.
15. The same cave mouth seen from inside the cave looking out at the night sky.
16. The South Atlantic weak region seen at a more oblique angle near the Earth's limb.
In every panel keep the main subject inside the central 80% of the panel width, few elements, nothing bright or busy.
```
结尾（profile `style_suffix` + `no_text_clause`，加强版，同 G1）：`Few elements, nothing bright or busy. No text, no letters, no numbers, no labels, no signs, no map labels, no watermark anywhere in any panel.`

比 G1 多加了两处：要求四行等高（G1 行高不均）；结尾加了 no signs / no map labels（N08 车站、N25 南大西洋最容易冒字）。

## 3. 参考图（最多 1 张 / 次）

- **G2、G3：0 张。** 没有罗盘近景（N23、N24 里的罗盘很小、表盘不写字，不需要 R1）；没有地球特写需要对齐 c04。
- 如果老大要 N24 的罗盘和第 1 章罗盘长得一样，可以给 G3 带 R1 当参考图（同价，`/v1/images/edits`），代价是整张 16 格都会被拉向罗盘的色调。默认不带。

## 4. 单图

- **不出。** 按第 0 节第 5 条（老大 00:32 定）B 线一律不单独出 1024×1536，只用宫格和复用。第 1 章那种「c13 / c10 看过再说」的单图口子，这里也不开。
- 最怕糊的几格：N06 洋中脊（约 64 秒屏上时间，ch2-c09 + c10）、N12 地幔（约 61 秒）、N17 多极地球（两章共约 50 秒）、N18 液态钠圆筒（约 51 秒）。都是暗场、低细节，放大 5–6 倍后靠慢推和景深撑；不够清楚就用同镜候选格或改成复用，不另出单图。

## 5. 逐个镜头（每行标来源；只有「新格」花钱）

时长 = 字数 ÷ 3.4（估）。放大目标 1188×2112（合成时出 1080×1920）；暗场 / 虚化默认 lanczos，主体近景用 ultrasharp。

| 镜 | 字数 · 时长 | 来源 | 动法 | 画面要点 | 放大 |
|---|---|---|---|---|---|
| ch2-c01 | 14 字 · 4.1 秒 | 复用：第1章 c06（stills/min1/c06.png） | 剪辑模板：极慢推近第二颗光点 | 夜色地平线上六颗等距暖色小光点（第 1 章 c06b 同图），这次只让左起第二颗略亮（后期调光，不重出图）。 | lanczos |
| ch2-c02 | 94 字 · 27.6 秒 | 复用：G1 格15（stills/ch1_v4/cells/G1_cell15.png；第 1 章 c15 若用格14 收尾，这里换格15 的宽景） | 剪辑模板：极慢下摇 | 地面下层层黑色玄武岩剖面，岩石里散着极淡的小光点，像被冻住的小指针；顶上一条夜空和地平线。 | lanczos |
| ch2-c03 | 85 字 · 25.0 秒 | **新格 N01**：G2 格1 | 剪辑模板：慢推近窗口暖灯 | 夜色火山顶上一座小石屋天文台，窗口一盏暖灯；山下远处一串圆锥形火山的剪影，没有城市灯光、没有人。 | lanczos |
| ch2-c04 | 190 字 · 55.9 秒 | **新格 N02**：G2 格2 | 剪辑模板：先慢推交界处，后段极慢上摇到玄武岩 | 月光下小石拱桥旁的崖壁露头：上层深灰色玄武岩，下层砖红色烤过的黏土，交界清楚；溪水很暗。 | lanczos |
| ch2-c05 | 83 字 · 24.4 秒 | 复用：第1章 c05（stills/min1/c05.png） | 剪辑模板：慢慢横移（c05 原来是上摇，这里换方向） | 月光下层状岩壁（第 1 章 c05 同图）。 | lanczos |
| ch2-c06 | 105 字 · 30.9 秒 | **新格 N03**：G2 格3 | 剪辑模板：慢推 + 景深（线圈渐虚、炉口渐实） | 昏暗实验室木桌上一只小电炉，炉口透出暗红光，里面一小块浅色浮石，炉外绕着几圈铜线圈；没有人、没有表盘读数。 | ultrasharp |
| ch2-c07 | 169 字 · 49.7 秒 | **新格 N04**：G2 格4（候选 G2 格14） | 剪辑模板：极慢横移（左→右，沿着岩样） | 暗色长桌上一排圆柱形岩样，深浅两种颜色交替排开，像一条长长的条形码；一盏台灯很弱的暖光。不写字、不写数字。 | lanczos |
| ch2-c08 | 86 字 · 25.3 秒 | **新格 N05**：G2 格5 | 剪辑模板：慢慢下摇（从船到水下条纹） | 夜色海面上一艘旧式科考船，船尾拖着一根长缆伸进水里；水下深处隐约透出明暗相间的长条纹。 | lanczos |
| ch2-c09 | 190 字 · 55.9 秒 | **新格 N06**：G2 格6（候选 G2 格15） | 剪辑模板：极慢拉远（从裂谷拉到两侧条带） | 海底洋中脊俯视：中间一道暗红微光的裂谷，两侧对称的明暗条带平行向外延伸。 | lanczos |
| ch2-c10 | 48 字 · 14.1 秒 | 复用：本章 N06（ch2-c09 同图） | 剪辑模板：接着 c09 继续极慢拉远，末尾淡出 | 同 ch2-c09 的洋中脊条纹，拉得更远。 | lanczos |
| ch3-c01 | 10 字 · 2.9 秒 | 复用：第1章 c06 | 剪辑模板：极慢推近第三颗光点 | 六颗等距暖色小光点（第 1 章 c06 同图），左起第三颗略亮。 | lanczos |
| ch3-c02 | 134 字 · 39.4 秒 | **新格 N07**：G2 格7 | 剪辑模板：极慢横移（左→右，越往右越密） | 暗色背景里一条长长的水平条带，明暗两色不规则交替（极性年表的抽象画）；左端色块又宽又少，右端越来越窄、越来越密。不写字、不写数字。 | lanczos |
| ch3-c03 | 86 字 · 25.3 秒 | **新格 N08**：G2 格8 | 剪辑模板：极慢推近长椅 | 夜里空荡荡的乡间车站：一盏路灯、一条长椅，远处的路上没有车。站牌和任何地方都不写字。 | lanczos |
| ch3-c04 | 154 字 · 45.3 秒 | 复用：G1 格16（若第 1 章 c06a 选了格16，这里改用第 1 章 c04 + 换裁切） | 剪辑模板：极慢推近弧线 | 轨道上看地球夜侧边缘：一条细细的深蓝弧线贴着黑色太空，极淡的浅蓝磁力线，没有城市灯光（G1 格16）。 | lanczos |
| ch3-c05 | 100 字 · 29.4 秒 | **新格 N09**：G2 格9 | 剪辑模板：极慢拉远 | 白垩纪的夜晚：远处河边一只长颈蜥脚类恐龙的剪影，静静站着，头顶星空，河面有一点星光倒影。 | lanczos |
| ch3-c06 | 76 字 · 22.4 秒 | **新格 N10**：G2 格10 | 剪辑模板：慢推（从条纹推向平整海床） | 海底俯视，必须明确是水下地形而不是海面：前景是嵌在海底沉积物里的明暗磁条带，远处过渡到平整、无条纹的深海底，表面哑光、没有波纹、没有天空倒影、没有海平线。 | lanczos |
| ch3-c07 | 102 字 · 30.0 秒 | **新格 N11**：G2 格11 | 剪辑模板：慢慢横移 | 夜色中的海边暗色岩石海岸，低矮崖壁和缓缓的海浪，月光很弱。 | lanczos |
| ch3-c08 | 272 字 · 80.0 秒 | **新格 N12**：G2 格12（候选 G2 格16） | 剪辑模板：一次缓慢下摇后停住 | 地球剖面的一角：上方暗褐红半固态地幔，几股缓慢上升的热流与下沉冷色块；下方是清楚、连续、不过曝的液态外核边界。外核只用暗橙色低亮度表示，不能成为发光主体，也不能像火焰或熔岩。保持地幔、外核的空间层次稳定，不用反复景深。 | lanczos |
| ch3-c09 | 49 字 · 14.4 秒 | **新格 N13**：G2 格13 | 剪辑模板：极慢推近汤面 | 夜里厨房炉子上一口小锅，火苗很小，汤面平静，飘着一缕热气；四周很暗。 | lanczos |
| ch4-c01 | 10 字 · 2.9 秒 | 复用：第1章 c06 | 剪辑模板：极慢推近第四颗光点 | 六颗等距暖色小光点（第 1 章 c06 同图），左起第四颗略亮。 | lanczos |
| ch4-c02 | 82 字 · 24.1 秒 | **新格 N14**：G3 格1 | 剪辑模板：极慢横移（沿着取样孔） | 夜色里的黑色熔岩崖壁，壁上一排整齐的小圆形取样钻孔；很暗，没有人。 | lanczos |
| ch4-c03 | 56 字 · 16.5 秒 | **新格 N15**：G3 格2 | 剪辑模板：慢慢下摇（从夜空到冰层） | 极地冰原夜空，极细的淡光点从高空斜落；下半部像剖面一样透进冰层，一层层浅蓝冰纹。 | lanczos |
| ch4-c04 | 144 字 · 42.4 秒 | 复用：G1 格13 | 剪辑模板：极慢推近（第 1 章 c14 若用格12 做图生视频，这里用格13，不再做 AI） | 黑暗中半透明的虚拟地核，被许多发光磁力线包着，线比较乱，一极暖琥珀、一极冷蓝（G1 格13）。 | lanczos |
| ch4-c05 | 130 字 · 38.2 秒 | **新格 N16**：G3 格3 | 剪辑模板：慢慢下摇（沿岩芯往下） | 一根竖直摆放的沉积岩芯剖面，细细的层理一层层叠着，从上到下颜色慢慢变化；暗背景，弱侧光。 | lanczos |
| ch4-c06 | 122 字 · 35.9 秒 | **新格 N17**：G3 格4（候选 G3 格14） | 剪辑模板：极慢推近，保持整体清晰 | 太空中的夜色地球，磁力线不再从一极弯到另一极，而是在三处明确位置形成少量大尺度、方向不同的弧线，球面上对应三四个很小的冷暖极区。禁止大量小圆圈、装饰性光点和无空间关系的线团；画面要能看出“多极结构”，不是噪声。 | lanczos |
| ch4-c07 | 207 字 · 60.9 秒 | 复用：G1 格12 | 剪辑模板：慢推 + 轻微景深（不做图生视频） | 黑暗中半透明的虚拟地核，被许多发光磁力线包着，上暖琥珀、下冷蓝，居中（G1 格12，第 1 章 c14 同图的静帧）。 | lanczos |
| ch4-c08 | 185 字 · 54.4 秒 | **新格 N18**：G3 格5 | 剪辑模板：慢推近小窗，内部保持静态可读 | 昏暗实验大厅里一只横放的不锈钢圆筒，两端各有一个叶轮，筒身开一扇小窗。窗口内是连续、平滑、低亮度的银色液态金属流体，流向清楚但不做剧烈翻涌；外壳、叶轮和窗口必须保持完整，不增加刻度、数字或第二个装置。 | ultrasharp |
| ch4-c09 | 41 字 · 12.1 秒 | 复用：第1章 c04 | 剪辑模板：极慢拉远 | 太空中的夜色地球 + 淡磁力线，北暖南冷（第 1 章 c04 同图）。 | lanczos |
| ch5-c01 | 13 字 · 3.8 秒 | 复用：第1章 c06 | 剪辑模板：极慢推近第五颗光点 | 六颗等距暖色小光点（第 1 章 c06 同图），左起第五颗略亮。 | lanczos |
| ch5-c02 | 88 字 · 25.9 秒 | **新格 N19**：G3 格6 | 剪辑模板：慢慢横移（沿着火山链） | 夜色中一串圆锥形火山连成一线，覆着草；近处一道早已冷却的黑色古熔岩流，月光很弱。 | lanczos |
| ch5-c03 | 113 字 · 33.2 秒 | 复用：本集 N15（ch4-c03 同图） | 剪辑模板：慢推（ch4-c03 是下摇，这里换动法） | 极地冰原夜空 + 冰层剖面（ch4-c03 同图）。 | lanczos |
| ch5-c04 | 82 字 · 24.1 秒 | **新格 N20**：G3 格7 | 剪辑模板：极慢推近 | 暗色木桌上一只小木陀螺在转，明显倾斜，却没有倒下；一点侧面暖光。 | ultrasharp |
| ch5-c05 | 102 字 · 30.0 秒 | 复用：本集 N17（ch4-c06 同图） | 剪辑模板：极慢拉远（ch4-c06 是推近） | 多个小磁极的夜色地球（ch4-c06 同图）。必须同时看出：整体磁场很弱、磁极不止两个、其中一个磁极已经偏到接近赤道；不要只画成几个装饰性小光点。 | lanczos |
| ch5-c06 | 89 字 · 26.2 秒 | **新格 N21**：G3 格8 | 剪辑模板：慢慢上摇（从草原到极光） | 远古欧洲的夜：低矮山谷和草原上方，挂着一条淡绿色的极光，地上只有一棵孤树，没有人。 | lanczos |
| ch5-c07 | 204 字 · 60.0 秒 | **新格 N22**：G3 格9（候选 G3 格15） | 剪辑模板：慢推 + 景深（火光渐虚、赭石和骨针渐实） | 夜里的洞穴口，里面一小堆火光；近处石台上放着一小块红赭石、一根细骨针和一小片带缝孔的粗糙皮革，暗示针、保暖衣物和防晒习惯。洞外天空有一层极淡的紫外线危险感，但不画光束、不画文字；不出人。画面只表达“可能相关”，不要画成确定因果。 | ultrasharp |
| ch5-c08 | 144 字 · 42.4 秒 | 复用：G1 格16（换裁切） | 剪辑模板：极慢横移 | 轨道上看地球夜侧边缘，细细的深蓝大气弧线（G1 格16；ch3-c04 若已用格16，这里换更紧的裁切，只留大气弧线）。 | lanczos |
| ch5-c09 | 128 字 · 37.6 秒 | 复用：第1章 c08 | 剪辑模板：极慢推近卫星 | 同一颗地球，更小，三颗小卫星排队掠过（第 1 章 c08 同图）。 | lanczos |
| ch6-c01 | 12 字 · 3.5 秒 | 复用：第1章 c06 | 剪辑模板：极慢拉远，六颗光点一起微亮 | 六颗等距暖色小光点（第 1 章 c06 同图），六颗一起慢慢变亮。 | lanczos |
| ch6-c02 | 103 字 · 30.3 秒 | **新格 N23**：G3 格10 | 剪辑模板：慢推近罗盘 | 十七世纪的夜，河边木桌上一只大型航海罗盘和一架黄铜象限仪，旁边一盏油灯；表盘不写字母和数字。 | ultrasharp |
| ch6-c03 | 141 字 · 41.5 秒 | **新格 N24**：G3 格11 | 剪辑模板：焦点从罗盘慢慢移到圆顶（景深） | 夜里山坡上一座带圆顶的老天文台剪影，前景草地上平放着一只罗盘，指针细长；不写刻度字母。 | ultrasharp |
| ch6-c04 | 76 字 · 22.4 秒 | 复用：第1章 c04 | 剪辑模板：极慢推近，亮度缓缓降一点 | 太空中的夜色地球 + 淡磁力线（第 1 章 c04 同图），后期整体压暗一点，暗示变弱。 | lanczos |
| ch6-c05 | 112 字 · 32.9 秒 | **新格 N25**：G3 格12（候选 G3 格16） | 剪辑模板：极慢推近弱区，宇宙远景大范围清晰 | 太空俯视南大西洋：南美洲和非洲的暗色轮廓必须可辨但不做地图标签，弱区位于两者之间的海面上方，呈一片低亮度、边缘柔和的暗紫色区域，不能画成城市灯光、火焰、圆形光环或地图定位点。地球边缘、海洋和弱区保持稳定几何关系。 | lanczos |
| ch6-c06 | 195 字 · 57.4 秒 | 复用：G1 格11（压暗） | 剪辑模板：慢推 | 地球剖面：外核和淡金内核的近景（G1 格11，后期压暗到 B 线亮度以内）。 | lanczos |
| ch6-c07 | 59 字 · 17.4 秒 | **新格 N26**：G3 格13 | 剪辑模板：极慢横移（跟着望远镜） | 黑暗太空里一台圆筒形太空望远镜的剪影，掠过地球上空；下方是那片暗紫色弱区。 | lanczos |
| ch6-c08 | 128 字 · 37.6 秒 | 复用：G1 格10 | 剪辑模板：极慢拉远 | 地球剖面：薄外壳、厚地幔、翻卷的外核、淡金内核（G1 格10）。 | lanczos |
| ch6-c09 | 145 字 · 42.6 秒 | 复用：第1章 c01（stills/test/c01.png） | 剪辑模板：极慢拉远，末尾淡出到黑 | 收尾，回到开头：银河星空下的荒原，罗盘在火山岩上（第 1 章 c01 同图）。在远处上方保留三颗极小、稳定的卫星剪影，和开头罗盘形成“今天仍在观测”的回收；不得加入文字、数字或明亮科技感。 | lanczos |

**本次重制的运动选择记录（按助眠线路规则）**：

- `ch2-c03/c04/c05/c07/c08/c09/c10`：静态首帧加一次缓慢推、摇或拉；这些是岩石、船和海底环境展示，运动只负责引导视线，不改变科学结构。
- `ch3-c02/c03/c05/c06/c07/c09`：静态或单向轻微平移；条带密度、车站和海床的关键数量必须保持稳定，不使用图生视频。
- `ch3-c08`：静态剖面加一次缓慢下摇；地幔与外核边界是科学事实，保持几何和亮度稳定优先。
- `ch4-c02/c03/c05/c06/c08`：静态或一次慢推；多极磁场和液态金属装置属于精密结构，不让线条、叶轮或物件增减。
- `ch5-c02/c03/c04/c05/c06/c07`：静态或轻微推拉；火山链、陀螺倾角、多磁极和洞穴道具都需要保持数量与形状稳定。
- `ch6-c02/c03/c05/c07`：静态或轻微推近/平移；罗盘、天文台、南大西洋轮廓和卫星是关键资产，宇宙远景保持大范围清晰。
- 只有正文明确要求“内部变化”的镜头才保留候选运动：`c02` 罗盘指针转动、`c14` 磁力线换向。两者优先受控动画；出现闪烁、亮度跳变、突然加速、漂移或结构增减时，回退静态首帧加极慢推近。

**统计**：46 镜 = 新格 26 镜（N01–N26，各 1 格）+ 复用 20 镜（第 1 章首帧 10 镜次、G1 格子 7 镜次、本集新格重复用 3 镜次）。新格 26 + 候选 6 = 32 格 = 2 张 4×4，正好用满。

## 6. 模型、张数上限、花费

- **模型**：和 G1 一样，中转站 `https://dklapi.com/v1`，`gpt-image-2.5-sunburst`，key 只从环境变量 `IMAGE_RELAY_KEY_1K` 读，不打印、不写进文件。每次固定 0.16 元。不试别的模型名。
- **接口**：`/v1/images/generations`，1024×1536，n=1，无参考图。
- **调用次数和花费**

| 项 | 调用次数 | 花费 | 说明 |
|---|---|---|---|
| G2 4×4（第 2–3 章） | 1 | 0.16 元 | 基本项 |
| G3 4×4（第 4–6 章） | 1 | 0.16 元 | 基本项 |
| 重画预留 | 0–2 | 0–0.32 元 | 每张宫格最多整张重出 1 次（格数不对 / 冒字 / 一半以上的格不能用）。单格不好先用候选格或复用，不算重画 |
| **合计** | **基本 2 次；上限 4 次** | **基本 0.32 元；上限 0.64 元** | |

- **张数上限**：本计划 4 次调用；用满就停下来私聊老大，不擅自加。失败但可能扣费的请求也算进上限。
- **建议执行顺序**：先只出 G2（1 次），老大看过效果再出 G3（和第 1 章 00:19「先只生一张图看看」的做法一致）。
- **全集累计（参考）**：第 1 章已花约 1.52–1.68 元（含 G1 0.16 元，见 `approvals/image_plan_ch1_v4.md` 第 6 节）；加本计划基本 0.32 元 → 约 1.84–2.00 元；上限 0.64 元 → 约 2.16–2.32 元（第 1 章自己的剩余上限另计）。以中转站实际扣费为准。

## 7. 待老大定的选项

1. **G2、G3 一起出，还是先出 G2 看效果**（建议先 G2）。
2. **每章开头的问句镜都复用 c06 六个光点**（5 次，后期调亮第 N 颗）：建议这样做，像章节标记；嫌重复的话可以在 G2/G3 的候选格里换掉，但会少候选。
3. **ch6-c09 全片收尾复用 c01 荒原罗盘**（首尾呼应），还是用 G1 格15 的岩层 + 夜空。建议 c01。
4. **N24 要不要带 R1 当参考图**（第 3 节），默认不带。
5. **本地出图**：默认不用。G2/G3 里的空场景（N05、N06、N07、N10、N12、N15、N17、N25 等）都适合 ddbbi 本地 Qwen-Image 试做，0 元、每张 1056×1584 更清楚，但和 API 图画风不一致、容易冒字、要和配音抢 GPU（理由同 `image_plan_ch1_v4.md` 第 8 节）。老大选了本地，我再补本地的 job 清单。

## 8. 和规则对不上的地方（我没改任何规则或代码）

1. **复用依赖 G1 审批**：G1 还没过老大的审，本计划有 7 镜次复用 G1 格子。第 1.1 节写了每格不能用时的替代（都还是复用、不加调用）。
2. **格11 亮度 0.29 超 B 线门槛 0.25**：ch6-c06 复用时后期压暗，不重出。
3. **同一张图跨章复用的次数**：c06 用了 5 次（加上第 1 章共 6 次），c04 加第 1 章共 4 次。规则只说「近似镜头只用一张图」，没有上限；老大嫌多可以从候选格里换。
4. **文件命名**：按交代用 `approvals/image_plan_ch2-6.md`（不是规则第 2 节的日期命名习惯）。
5. **发送**：这份文件只是草稿，**还没发**给老大；按第 0 节第 1 条，由出图的线私聊老大发计划。

## 9. 批了之后才做

1. 按老大选的顺序调用 G2（/ G3），记进 `gen/calls_ledger_ch2-6.json`（只记分组、模型、张数、单价、花费、输出路径；不记 key）。
2. 用 `gen/cut_grid.py` 切 16 格，跑 OCR / 亮度检查（同 `gen/check_cells_ch1_v4.py`），人眼查冒字。
3. 做审阅图放 ddbbi `E:\program\1project\video\zhumian\b-geomagnetic-reversal\stills\ch2-6\`，私聊老大审（🔒）。
4. 没选中的格登记进 `discards.yaml`，删除前老大逐批确认。
5. 有任何问题（报错、格数不对、冒字、超上限），先停下私聊老大。

- **老大批复（原话、时间）**：2026-10-02 01:07（北京时间）批准本计划；老大要睡了，交代不要卡流程 → G2、G3 一起出（第 7 节第 1 条因此没按「先 G2」走）。其余选项（第 7 节 2–5）按计划默认：问句镜复用 c06、ch6-c09 用 c01、N24 不带参考图、不本地出图。（原话经主线转达，此处未逐字记录。）

## 10. 实际执行记录（2026-10-02，北京时间）

| # | 宫格 | 发出时间 | 用时 | HTTP | 模型 | 参考图 | tokens（入 / 出 / 合计） | 花费 |
|---|---|---|---|---|---|---|---|---|
| 1 | G2 | 01:08:41 | 59.1 秒 | 200 | gpt-image-2.5-sunburst | 0 | 889 / 1079 / 1968 | 0.16 元 |
| 2 | G3 | 01:09:41 | 62.6 秒 | 200 | gpt-image-2.5-sunburst | 0 | 835 / 1071 / 1906 | 0.16 元 |
| | **合计** | | | | | | | **2 次，0.32 元**（上限 4 次 / 0.64 元；重画预留 2 次没用） |

- 接口 `/v1/images/generations`，key 变量 `IMAGE_RELAY_KEY_1K`，1024×1536，n=1；提示词 = 第 2 节画风前缀 + G2/G3 原文 + 结尾，脚本从本文件直接读。价格按 0.16 元 / 次计（中转站不返回扣费）。
- 记录：`gen/calls_ledger_ch2-6.json`、`gen/run_log_ch2-6.txt`；脚本 `gen/gen_g23_ch2_6.py`、`gen/cut_grid.py`（复用）、`gen/check_cells_ch2-6.py`、`gen/contact_g23_ch2-6.py`。
- 产出：box `stills/ch2-6_v4/`（G2_grid、G3_grid、cells/ 32 格、两张审阅图、NOTES.md）；ddbbi `E:\program\1project\video\zhumian\b-geomagnetic-reversal\stills\ch2-6_v4\`（第 9 节第 3 条原写 `stills\ch2-6\`，按交代改用 `ch2-6_v4`）。
- 结果：两张都 16 格齐全、不串格、没有文字或类数字。G2 格16（N12-B）亮度 0.29 超门槛；G2 格12（N12）0.24 贴近门槛；G2 格10（N10）远处像海面、海床意思弱。逐格评估和建议的格→镜见 `stills/ch2-6_v4/NOTES.md`。
- 第 9 节第 4 条（discards.yaml）等老大挑完格再做。
