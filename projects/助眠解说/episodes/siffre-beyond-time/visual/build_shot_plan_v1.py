# -*- coding: utf-8 -*-
"""siffre-beyond-time SHOT_PLAN v1 builder.

Basis: story/OUTLINE.md (大纲 v1, 口播未锁定).
Shots are keyed to chapter beats, not narration paragraphs; after NARRATION_MASTER
locks, rerun the 01/02/04 pipeline to re-map paragraph_id/narration/timeline.
Writes: visual/SHOT_PLAN.json + visual/ALL_SHOT_PROMPTS.md
"""
import json
from datetime import date
from pathlib import Path

EP = Path(r"E:\program\1project\video\projects\助眠解说\episodes\siffre-beyond-time")
OUT_JSON = EP / "visual" / "SHOT_PLAN.json"
OUT_MD = EP / "visual" / "ALL_SHOT_PROMPTS.md"

PREFIX = ("Cinematic science-fantasy documentary, deep teal-blue night palette with controlled "
          "amber highlights, monumental subject, photorealistic materials, volumetric atmosphere, "
          "layered depth, reflective surfaces, asymmetrical cinematic composition, subtle surrealism, "
          "rich environmental detail, calm dreamlike mood, 16:9 widescreen, no text, no labels, "
          "no arrows, no diagrams, no UI, no PPT layout, no watermark")

NEG_TEXT = "Strictly no readable text, no numbers, no letters; any handwriting appears only as soft unfocused brush strokes."

SECTION_TITLES = {
    "bridge": "故事由来", "ch01": "一、一个研究石头的人，把表留在了地上",
    "ch02": "二、两个时钟", "ch03": "三、时间开始变黏", "ch04": "四、灯最暗的那几周",
    "ch05": "五、你的“一天”，比一天长", "ch06": "六、他以为是8月20日",
    "ch07": "七、十年后，他又下去了，这次六个月", "ch08": "八、接过火把的人",
    "ch09": "九、一直住在洞里的人", "ch10": "十、今晚，你的钟也在走", "epilogue": "尾声：回到洞口",
}

DUR = {"P1": 16, "P2": 18, "V1": 12, "V3": 15, "V5C": 20}

# (sid, beat, scene, cls(P/V), strat, mode(single/2x2_tile), prompt_body, motion, reason, extra_neg)
S = []
def add(section, sid, beat, scene, cls, strat, mode, prompt, motion, reason, extra_neg=None):
    S.append(dict(section=section, sid=sid, beat=beat, scene=scene, cls=cls, strat=strat,
                  mode=mode, prompt=prompt, motion=motion, reason=reason, extra_neg=extra_neg))

# ---------------- bridge 故事由来 ----------------
add("bridge", "brg-s01", "预叙：黑暗里的一盏灯", "洞穴黑暗深处一盏暖黄营地灯亮起，照亮粗糙岩壁与小帐篷一角，细小尘埃在光柱中缓慢漂浮；画面绝大部分是无边青黑，灯光是唯一暖色", "V", "V3", "single",
    "Vast pitch-dark limestone cavern; a single warm amber camp lamp glows on the wall beside a small canvas tent corner; fine dust motes drift through the light beam; wet rock textures glisten faintly at the light edge; immense darkness beyond",
    "灯焰轻微摇曳，尘埃在光柱中缓慢漂浮，其余一切静止", "有生命运动（焰与尘埃）→i2v；作为全片第一个画面定下暖/冷双色温", NEG_TEXT)
add("bridge", "brg-s02", "预告叙事契约：日记与还原", "灯下木桌上摊开的旧日记本与一支钢笔，纸页边缘微卷，字迹完全虚化不可读；旁边一盏黄铜座油灯", "P", "P2", "single",
    "Close still life on a rough wooden table: an open vintage diary with curling page edges, a fountain pen resting on it, a brass oil lamp with glass chimney burning steady at side; handwriting rendered as soft unfocused strokes only; warm amber lamplight, deep shadows",
    {"direction": "push_in", "reference_scale": [1.02, 1.12], "endpoint_hold_seconds": 2.5},
    "静物、无内部运动必要→推拉； Endpoint 停留安放", NEG_TEXT)
add("bridge", "brg-s03", "从一点暖到整片黑", "从油灯特写缓缓拉远，灯光缩成黑暗洞窟中的一点暖光，四周岩壁层层退入青黑", "P", "P1", "2x2_tile",
    "Extreme pull-back view inside an immense dark cave: the warm brass oil lamp shrinks to a single glowing point surrounded by layered black rock walls receding into teal darkness; tiny tent silhouette nearby",
    {"direction": "pull_out", "reference_scale": [1.18, 1.02], "endpoint_hold_seconds": 0},
    "氛围停留与大空间感→拉；无运动内容不需 i2v", None)

# ---------------- ch01 下洞 ----------------
add("ch01", "c1-s01", "1962年，出发的清晨", "1962年清晨的山间公路，一辆老式汽车停在路肩，车顶行李架上绑着帆布背包与木箱，晨雾贴着山谷，远处雪山淡青", "P", "P1", "2x2_tile",
    "Early morning 1962 alpine road, a vintage sedan parked on the shoulder, canvas rucksacks and wooden crates strapped to the roof rack, low fog drifting over the valley, pale distant snow peaks in teal-blue dawn light, cinematic depth",
    {"direction": "push_in", "reference_scale": [1.02, 1.10], "endpoint_hold_seconds": 0},
    "环境定场→缓推；常规环境走 2x2 批量", None)
add("ch01", "c1-s02", "行囊细节", "车顶帆布背包与铝制水壶特写，绳圈打着结，一支地质锤插在侧袋，晨光斜照", "P", "P2", "2x2_tile",
    "Close-up of a canvas climbing rucksack and aluminum canteen on a car roof, rope coils tied in knots, a geology hammer tucked in the side pocket, slanting pale morning light, worn fabric texture",
    {"direction": "pan_right", "reference_scale": [1.06, 1.06], "endpoint_hold_seconds": 2.0},
    "静物细节→平移+停留；交代人物身份（地质）", None)
add("ch01", "c1-s03", "冰川表面，融水流", "冰川表面的融水在冰裂缝之间缓慢流动，冰面泛着冷青反光，远处雪山与低云", "V", "V3", "2x2_tile",
    "Glacier surface with meltwater streams slowly flowing between deep crevasses, polished ice reflecting cold cyan light, distant snow mountains and low clouds, vast quiet scale",
    "融水在冰裂缝间缓慢流动，云影极缓移动，其余静止", "水流=自然内部运动→i2v；本章的“外部世界”基调", None)
add("ch01", "c1-s04", "通往地下的裂隙", "冰川裂隙边缘，一条登山绳垂入黑暗，冰晶在绳边反光，下方深不见底", "P", "P1", "single",
    "Edge of a glacier crevasse, a climbing rope dropping into utter darkness, ice crystals glinting along the rim, the void below swallowing light, cold cyan and deep black contrast",
    {"direction": "push_in", "reference_scale": [1.02, 1.14], "endpoint_hold_seconds": 0},
    "关键构图+明显推近→独立生图；向下坠视暗示下洞", None)
add("ch01", "c1-s05", "23岁的他（剪影）", "青年的背影站在裂隙边缘，深色羊毛帽与旧呢大衣，呼出的白气，逆光，不见正脸", "P", "P2", "single",
    "Backlit silhouette of a young man in a dark wool cap and worn wool coat standing at the crevasse edge, breath visible as faint white vapor, rim light on his shoulder, face not visible, immense glacier behind",
    {"direction": "push_in", "reference_scale": [1.02, 1.08], "endpoint_hold_seconds": 2.0},
    "人物母题定装（帽+大衣，全程不见正脸）→独立生图保连续性", None)
add("ch01", "c1-s06", "母题①：摘表（关键帧）", "一只手正把一块银壳棕带机械手表从腕上摘下，放在石块上的背包旁，表盘朝上，阳光落在表蒙上", "P", "P1", "single",
    "A hand removing a silver-cased mechanical wristwatch with brown leather strap from a wrist, placing it on a flat stone beside a canvas rucksack, watch face up, sunlight glinting on the crystal; glacier blurred in background; the single watch is the clear subject",
    {"direction": "push_in", "reference_scale": [1.02, 1.12], "endpoint_hold_seconds": 0},
    "母题①登场的关键特写→独立生图；精密结构→静态推近", "no readable watch brand, dial markers kept vague and unfocused")
add("ch01", "c1-s07", "母题①：表的静物", "同一块银壳棕带机械表特写静物，表盘刻度虚化，背景是虚化的冰川轮廓，光线从左上来", "P", "P2", "single",
    "Still-life close-up of the same silver mechanical wristwatch with brown leather strap resting on the stone, dial markers soft and unfocused, blurred glacier outlines behind, gentle key light from upper left",
    {"direction": "push_in", "reference_scale": [1.03, 1.10], "endpoint_hold_seconds": 2.5},
    "精密结构禁动画→P2 停留；同一块表与 c1-s06 完全一致", NEG_TEXT)
add("ch01", "c1-s08", "表被留在地上", "从手表拉开：画面里人影已走到远处裂隙边缘，表独自留在近景石块上，一小片阳光", "P", "P1", "single",
    "Pull-back from the wristwatch on its stone: the small figure of the young man now far away at the crevasse edge, the watch alone in the foreground catching a patch of sunlight, vast cold landscape between them",
    {"direction": "pull_out", "reference_scale": [1.14, 1.02], "endpoint_hold_seconds": 0},
    "外部时间被留在光里——本章题眼，用构图而非动画表达", None)
add("ch01", "c1-s09", "头灯进入黑暗", "头灯的光锥缓慢扫过粗糙湿润的洞壁，光斑移动处岩面纹理与水珠反光显现，光外全黑", "V", "V1", "2x2_tile",
    "Inside absolute cave darkness, the cone of a headlamp sweeping slowly across rough wet limestone, revealing grain and glistening droplets only where light falls, everything beyond the beam pitch black",
    "头灯光锥缓慢平移扫过洞壁，光斑之外完全静止", "光移动=内部运动→i2v；“进入黑暗”的体感镜头", None)
add("ch01", "c1-s10", "营地首夜", "岩洞平地上首次搭起的小帐篷，一盏灯挂在洞壁，暖光照亮帐篷与一小圈地面，四周黑暗", "P", "P1", "2x2_tile",
    "First night camp inside the cavern: a small canvas tent pitched on flat rock, a lamp hung on the cave wall casting warm amber light over the tent and a small circle of floor, surrounding darkness immense and quiet",
    {"direction": "push_in", "reference_scale": [1.02, 1.10], "endpoint_hold_seconds": 0},
    "营地定场→缓推；暖冷对比的“家”建立", None)
add("ch01", "c1-s11", "帐篷内：两个月的家", "帐篷内景：睡袋、成箱的罐头、成摞的书，灯光温暖，物品摆放整洁", "P", "P2", "2x2_tile",
    "Inside the small tent: a bedroll, wooden crates of canned food, neat stacks of books, a warm lantern glow making the canvas glow softly, orderly and habitable, deep shadows at the edges",
    {"direction": "pan_left", "reference_scale": [1.06, 1.06], "endpoint_hold_seconds": 2.5},
    "静物群→平移+停留；为后面“秩序→失序”存底", NEG_TEXT)

# ---------------- ch02 两个时钟 ----------------
add("ch02", "c2-s01", "洞内营地全景（定场）", "洞内营地全景：帐篷、木箱、木桌，黑色胶皮电话线从上方岩缝垂到桌上的老式电话机，灯光稳定明亮", "P", "P1", "2x2_tile",
    "Wide establishing view of the cave camp: canvas tent, wooden crates, a rough table; a black rubber-sheathed telephone wire descends from a high rock crevice to an old black dial telephone on the table; the brass oil lamp burns steady and bright; warm pool of light inside vast darkness",
    {"direction": "push_in", "reference_scale": [1.02, 1.10], "endpoint_hold_seconds": 0},
    "章首定场→缓推；母题③（电话线）首次完整亮相", NEG_TEXT)
add("ch02", "c2-s02", "母题③：电话机", "老式黑色拨盘电话机特写，听筒搁在叉簧上，机身漆面微反灯光，电话线垂出画面", "P", "P2", "single",
    "Close-up of a vintage black dial telephone resting on the wooden table, handset on its cradle, lacquer surface catching a warm lamplight reflection, the black cord dropping out of frame; precise, calm, silent",
    {"direction": "push_in", "reference_scale": [1.03, 1.12], "endpoint_hold_seconds": 2.5},
    "母题③特写→独立生图；精密静物→P2 停留", NEG_TEXT)
add("ch02", "c2-s03", "地面营地（对照世界）", "山谷草坡上的地面营地帐篷，晨光斜照，风把帐篷布吹得微微鼓动，远处的冰川与云", "V", "V3", "2x2_tile",
    "Surface camp on an alpine meadow: canvas tents in slanting morning light, tent fabric breathing gently in the wind, the glacier and clouds far behind; bright airy contrast to the cave",
    "帐篷布在风里轻微鼓动，草叶微晃，其余静止", "帐篷布风动=自然内部运动→i2v；地面/洞内对照", None)
add("ch02", "c2-s04", "地面的记录员", "地面帐篷内，一位穿浅色衬衫的记录员在桌灯下伏案，桌上一沓方格记录纸与一只闹钟，字迹不可读", "P", "P2", "single",
    "Inside a surface tent, a recorder in a light shirt working under a desk lamp at a table, a stack of gridded log sheets and a small mechanical alarm clock on the desk; handwriting as soft unfocused strokes; quiet diligent atmosphere",
    {"direction": "push_in", "reference_scale": [1.03, 1.10], "endpoint_hold_seconds": 2.0},
    "地面=有钟的世界；人物+钟同框，静态叙事足够", NEG_TEXT)
add("ch02", "c2-s05", "记录在生长", "笔尖在方格记录纸上逐字书写，墨迹向前延伸，字迹虚化，灯光暖", "V", "V1", "single",
    "Macro view of a pen nib writing across gridded log paper, ink strokes extending line by line, handwriting rendered as soft unfocused strokes, warm lamplight, shallow depth of field",
    "笔尖沿纸面缓慢书写一行，墨迹延伸，其余静止", "书写=内部运动→i2v；“他的时钟”在地面生长", NEG_TEXT)
add("ch02", "c2-s06", "洞内：他的日记（母题②灯登场）", "洞内木桌上摊开的日记本，旁边黄铜座油灯玻璃罩内火焰笔直明亮（母题②定装），他戴表的那只手腕空着", "P", "P1", "single",
    "On the cave camp table an open diary next to a brass oil lamp with glass chimney, its flame tall, straight and bright; the man's bare wrist without a watch resting by the page; handwriting soft and unfocused; the lamp is the second clear subject",
    {"direction": "push_in", "reference_scale": [1.02, 1.10], "endpoint_hold_seconds": 0},
    "母题②（黄铜油灯）定装帧→独立生图；与摘表形成“无表”呼应", NEG_TEXT)
add("ch02", "c2-s07", "罐头与物资", "木箱上整齐排列的罐头与开罐器、水壶，金属罐身反灯光，标签空白无字", "P", "P2", "2x2_tile",
    "Neat rows of unlabeled tin cans, a can opener and a flask arranged on a wooden crate, metal surfaces reflecting warm lamplight, tidy camp order, deep shadows around",
    {"direction": "pan_right", "reference_scale": [1.06, 1.06], "endpoint_hold_seconds": 2.0},
    "静物→平移停留；“秩序期”的物资底图（后文见底对照）", "all can labels strictly blank, no text")
add("ch02", "c2-s08", "他的勘察工作", "头灯光锥下，他用粉笔在岩壁上画下一道短痕，手部与岩面细节清晰，粉痕无线条组合", "V", "V3", "single",
    "Under the headlamp beam, a hand drawing a single short chalk mark on rough limestone, chalk dust drifting, rock grain crisp in the light, darkness beyond; one mark only, no diagrams",
    "手用粉笔在岩面划出一道短痕，粉屑轻落，其余静止", "手部动作→i2v；短痕=他对“天”的私人刻度（第五章复用）", "only one short chalk stroke, no lines forming shapes, no readable marks")
add("ch02", "c2-s09", "洞窟的尺度", "洞室纵深拉远：他在远处头灯小光点旁工作，洞窟层层叠叠退入黑暗，人极小", "P", "P1", "2x2_tile",
    "Deep perspective inside the enormous cavern: the man a tiny figure by a small headlamp glow, chamber after chamber of rock receding into layered blackness, scale overwhelming and still",
    {"direction": "pull_out", "reference_scale": [1.16, 1.02], "endpoint_hold_seconds": 0},
    "空间感与渺小感→拉；环境无内部运动", None)
add("ch02", "c2-s10", "保持身体的锻炼", "灯光把他在洞内原地活动的影子投在岩壁上，影子拉长，姿态安静有力", "P", "P2", "2x2_tile",
    "The man exercising calmly in place by the camp light, his elongated shadow cast on the cave wall, posture quiet and disciplined, warm light against dark rock",
    {"direction": "push_in", "reference_scale": [1.03, 1.08], "endpoint_hold_seconds": 2.0},
    "自律期→影子的静态构图；不强调剧烈动作（低刺激）", None)
add("ch02", "c2-s11", "他的“夜”：灯熄", "灯熄后近乎全黑的洞内，只剩电话线的轮廓与岩面极微弱反光", "P", "P1", "2x2_tile",
    "Near-total darkness after the lamp is out: the faint outline of the telephone wire descending through blackness, the barest suggestion of rock surfaces, a frame almost entirely deep blue-black",
    {"direction": "push_in", "reference_scale": [1.02, 1.06], "endpoint_hold_seconds": 0},
    "极暗帧做章尾；短暂的近黑符合低刺激（渐入而非闪烁）", None)

# ---------------- ch03 时间变黏 ----------------
add("ch03", "c3-s01", "日记：行距正常（前期）", "日记本前段的纸页特写：行距正常、笔画密实，字迹完全虚化不可读，灯光暖而稳", "P", "P1", "single",
    "Macro view of early diary pages: evenly spaced lines of soft unfocused handwriting, pages flat and neat under steady warm lamplight; the rhythm of the lines is the subject, not any readable text",
    {"direction": "push_in", "reference_scale": [1.02, 1.10], "endpoint_hold_seconds": 0},
    "母题“行距”的基准帧→独立生图；文字禁令最严的一镜", NEG_TEXT)
add("ch03", "c3-s02", "翻页", "手指翻动日记纸页的一瞬，纸页在灯下弯出弧度，下一页虚化", "V", "V1", "single",
    "A hand turning a diary page, the paper curving through lamplight mid-turn, next page still soft and unfocused, warm amber tones",
    "手指翻过一页纸，纸页弯动落定，其余静止", "翻页=动作→i2v；轻、短、安静", NEG_TEXT)
add("ch03", "c3-s03", "日记：行距变大（后期）", "同一本日记后段的纸页：同样的纸与笔，行与行之间空隙明显变大，笔画松散虚化", "P", "P1", "single",
    "The same diary much later: identical paper and pen, but the spaces between lines have grown visibly wide, strokes sparse and loose (all unreadable), lamplight slightly dimmer; the widening gaps are the subject",
    {"direction": "push_in", "reference_scale": [1.02, 1.12], "endpoint_hold_seconds": 0},
    "行距变大=有据的真实细节，全章题眼；与 c3-s01 同机位渊源", NEG_TEXT)
add("ch03", "c3-s04", "录音机转轮", "盘式磁带录音机的两个大盘缓缓转动，磁带从一盘卷向另一盘，面板指示灯微红", "V", "V3", "single",
    "A vintage reel-to-reel tape recorder, two large reels turning slowly as tape winds from one to the other, a small red pilot lamp glowing on the brushed metal face; mechanical, patient, quiet",
    "两个磁带大盘匀速缓转，磁带平稳卷动，指示灯恒亮", "转轮=匀速机械运动→i2v；时间被录下来的意象", "no readable labels or numbers on the machine face")
add("ch03", "c3-s05", "录音机与话筒", "录音机与立式话筒的静物，金属面板与网罩反灯光，桌面深色木纹", "P", "P2", "2x2_tile",
    "Still life of the reel-to-reel recorder beside a vintage stand microphone, metal mesh and panel catching warm reflections, dark wood table grain, studio-like quiet",
    {"direction": "pan_left", "reference_scale": [1.06, 1.06], "endpoint_hold_seconds": 2.5},
    "精密静物→平移停留", "no readable labels or numbers")
add("ch03", "c3-s06", "醒来，不知时候", "他在睡袋里睁着眼，头灯未开，一只手伸向桌上的油灯方向，黑暗里只有轮廓", "P", "P1", "2x2_tile",
    "Inside the dark tent the man lies awake in his bedroll, eyes open toward nothing, one arm reaching slowly toward the direction of the table lamp, shapes barely resolved in deep blue darkness",
    {"direction": "push_in", "reference_scale": [1.02, 1.08], "endpoint_hold_seconds": 0},
    "情境镜头；无内部运动必要→推近不安感（幅度仍缓）", None)
add("ch03", "c3-s07", "母题②：火焰（盛期）", "黄铜油灯玻璃罩内的火焰特写：笔直明亮，只有极轻微的摇曳，灯罩洁净", "V", "V3", "single",
    "Macro of the brass oil lamp flame inside its clean glass chimney: tall, bright, almost perfectly still with only the faintest breathing sway; warm amber core against surrounding darkness; the flame is the only subject",
    "火焰极轻微地缓缓摇曳，几乎静止，其余无变化", "母题②状态基准（盛期）→i2v 微焰；后文对比用", None)
add("ch03", "c3-s08", "腕上的表痕", "他手腕上被表带勒出的浅痕特写，皮肤与光，无表", "P", "P2", "single",
    "Close-up of a faint strap mark pressed into the bare wrist skin where a watch once sat, soft warm light, no watch, quiet intimacy",
    {"direction": "push_in", "reference_scale": [1.03, 1.10], "endpoint_hold_seconds": 2.5},
    "母题①的“缺席”变体；身体记住时间的小证据", None)
add("ch03", "c3-s09", "水滴的石窝", "洞壁渗水在地面石凹里积出一小汪水，一圈极缓的涟漪，灯光的反光浮在水面", "P", "P1", "2x2_tile",
    "A small stone hollow on the cave floor holding a pool of seep water, a faint ring of ripples spreading, the lamp's warm reflection floating on the surface, darkness all around",
    {"direction": "push_in", "reference_scale": [1.02, 1.10], "endpoint_hold_seconds": 0},
    "滴水的“巢”定场；下一镜才是滴落瞬间", None)
add("ch03", "c3-s10", "一滴坠落", "一滴水从岩壁坠落，水面涟漪扩散，灯光反射被涟漪揉碎又复原", "V", "V1", "single",
    "A single water drop falling from the rock toward the small pool, ripples radiating outward, the warm lamplight reflection wobbling softly on the water; nothing else moves",
    "一滴水落下激起涟漪，反光轻晃后复平静", "滴落=瞬间内部运动→i2v；钟摆/节拍的意象", None)
add("ch03", "c3-s11", "空罐头", "一只吃空的罐头开口朝向黑暗摆在岩台上，罐口边缘暗反光，旁边粉笔痕", "P", "P2", "2x2_tile",
    "An empty opened tin can placed on a rock ledge, its open mouth facing the darkness, dull glint on the cut edge, a short chalk mark beside it; minimal still life about time consumed",
    {"direction": "pan_right", "reference_scale": [1.06, 1.06], "endpoint_hold_seconds": 2.0},
    "时间消耗的静物；极简", "label strictly blank, no text")
add("ch03", "c3-s12", "秩序仍在，黑暗更浓", "从灯下拉开到营地全景：帐篷、木箱、桌的秩序未变，但四周黑暗显得更浓、更近", "P", "P1", "2x2_tile",
    "Pulling back from the lamp to the whole camp: tent, crates and table still in their tidy places, but the surrounding darkness feels denser and closer, the warm circle smaller",
    {"direction": "pull_out", "reference_scale": [1.14, 1.02], "endpoint_hold_seconds": 0},
    "章尾：环境未变而心理变了——用画框里的黑/暖比例表达", None)

# ---------------- ch04 灯最暗 ----------------
add("ch04", "c4-s01", "火焰矮了", "油灯火焰比此前明显矮了一截，灯罩内壁熏出暗色，灯光圈缩小", "P", "P1", "single",
    "The same brass oil lamp, flame now visibly shorter, the glass chimney smoked dark on the inside, its circle of warm light on the rock shrunk; quiet decline",
    {"direction": "push_in", "reference_scale": [1.02, 1.10], "endpoint_hold_seconds": 0},
    "母题②衰落的静态基准帧→独立生图", None)
add("ch04", "c4-s02", "焰在衰（唯一 i2v 焰）", "灯焰缓慢摇曳、光弱，岩壁上的光影随之轻轻晃动，整体亮度缓缓下降", "V", "V3", "single",
    "The lamp flame wavering slowly and weakly, shadows on the cave wall breathing with it, overall glow gently fading; slow, continuous, never flickering fast",
    "火焰缓慢摇曳变弱，墙上光影轻晃，亮度缓降，无快闪", "焰衰=核心内部运动→i2v；motion 明确禁快闪（低刺激红线）", None)
add("ch04", "c4-s03", "备件将尽", "木箱上半开的零件盒：几枚旧电池与备用灯泡零散躺着，盒内大半空", "P", "P2", "2x2_tile",
    "A half-empty supply box on the crate: a few old batteries and spare bulbs lying loose, most of the box empty, dim warm light, worn cardboard texture",
    {"direction": "push_in", "reference_scale": [1.03, 1.08], "endpoint_hold_seconds": 2.0},
    "消耗的静物证据", "no readable text on batteries or box")
add("ch04", "c4-s04", "湿岩壁", "大面积湿岩壁，水珠密布，反光微弱青冷，岩面纹理向下流淌的水痕", "P", "P1", "2x2_tile",
    "A broad wall of wet limestone dense with beads of moisture, faint cold cyan glints, thin trails of water running down the grain; texture-heavy, chill, still",
    {"direction": "push_in", "reference_scale": [1.02, 1.10], "endpoint_hold_seconds": 0},
    "环境压迫感→缓推贴面；无运动", None)
add("ch04", "c4-s05", "帐篷内侧的潮", "帐篷布内侧凝着一层水汽，睡袋边缘颜色变深，微光", "P", "P2", "2x2_tile",
    "Inside the tent: condensation beading on the canvas inner side, the bedroll's edge darkened with damp, faint light, claustrophobic hush",
    {"direction": "pan_down", "reference_scale": [1.06, 1.06], "endpoint_hold_seconds": 2.0},
    "潮=状态静物；下移镜头缓沉", None)
add("ch04", "c4-s06", "抱膝的呼吸（剪影）", "他抱膝坐在睡袋上静止不动，背光剪影，只有呼吸的缓慢起伏，灯光极弱", "V", "V1", "single",
    "The man sitting still on his bedroll, knees drawn up, seen as a dark silhouette against a very weak lamp glow; only the slow rise and fall of his breathing moves; profound stillness",
    "剪影随呼吸极缓起伏，其余完全静止", "呼吸=活物运动→i2v；低谷期的唯一“生命迹象”", None)
add("ch04", "c4-s07", "沉默的电话", "电话机特写：听筒安静搁着，机身漆面暗淡，电话线垂入黑暗深处", "P", "P1", "single",
    "The black telephone in close-up, handset silent on its cradle, lacquer dulled, its cord dropping away into the black depth of the cave; a connection holding still",
    {"direction": "push_in", "reference_scale": [1.02, 1.12], "endpoint_hold_seconds": 0},
    "母题③低谷帧；与地面的紧张用“沉默”表达", NEG_TEXT)
add("ch04", "c4-s08", "地面：凝重的核对", "地面帐篷夜里，两三名记录员围着桌灯核对成沓记录，无人说话，桌上钟面反光", "P", "P2", "2x2_tile",
    "Night in the surface tent: two or three recorders around a desk lamp checking thick stacks of log sheets in silence, the alarm clock's face catching a glint; subdued, weighty atmosphere",
    {"direction": "push_in", "reference_scale": [1.03, 1.08], "endpoint_hold_seconds": 2.0},
    "地面视角插镜；静态群像", NEG_TEXT)
add("ch04", "c4-s09", "仍在记录", "弱光下他仍坐到木桌前写日记，笔动得很慢，字迹虚化，灯只剩一小粒亮", "V", "V3", "single",
    "Under a shrunken weak lamp the man still writes his diary at the table, pen moving slowly, strokes soft and unfocused, the flame a small stubborn point of amber in the dark",
    "笔尖缓慢书写，灯光微弱稳定，其余静止", "“仍然按协议记录”的关键行为→i2v 书写（弱光版）", NEG_TEXT)
add("ch04", "c4-s10", "库存见底", "木箱里只剩两三个罐头，箱底木纹外露，灯光斜照", "P", "P2", "2x2_tile",
    "The supply crate nearly empty: two or three cans left at the bottom, bare wood grain exposed, lamplight raking across; scarcity as still life",
    {"direction": "push_in", "reference_scale": [1.03, 1.08], "endpoint_hold_seconds": 2.0},
    "与 c2-s07 同机位渊源的对照帧", "labels blank")
add("ch04", "c4-s11", "一点暖", "极弱光下的营地全景：所有轮廓还在，灯只剩一粒暖点，黑暗占满画面", "P", "P1", "2x2_tile",
    "The whole camp in failing light: every outline still in place — tent, table, crates — but the lamp now a single warm point, darkness filling the frame almost entirely",
    {"direction": "pull_out", "reference_scale": [1.12, 1.02], "endpoint_hold_seconds": 0},
    "全片最接近黑的帧之一；渐变不闪烁", None)
add("ch04", "c4-s12", "睡去（章尾安放）", "他在灯旁睡去，灯焰矮而稳，睡袋轮廓安静，黑暗围拢但不再逼近", "P", "P2", "single",
    "The man asleep beside the low steady lamp, the bedroll a calm shape, darkness gathered around but holding its distance; the frame breathes out and settles",
    {"direction": "push_in", "reference_scale": [1.02, 1.06], "endpoint_hold_seconds": 3.0},
    "低谷章必须稳收（基调红线）；P2 长停留安放", None)

# ---------------- ch05 一天比一天长 ----------------
add("ch05", "c5-s01", "纸上的竖痕", "灯下一沓厚方格纸，纸面上手绘的一道道短竖痕排开、间距不均，无坐标无文字", "P", "P1", "single",
    "A thick stack of gridded log paper under lamplight, rows of short hand-drawn tick marks spaced unevenly across the pages — spacing itself telling the story; strictly no axes, no labels, no readable marks",
    {"direction": "push_in", "reference_scale": [1.02, 1.12], "endpoint_hold_seconds": 0},
    "数据意象的“可拍摄化”替代图表（全线原则）；间距=信息", "no axes, no gridline numbers, marks must look hand-drawn and abstract")
add("ch05", "c5-s02", "记录在变厚", "记录员把新的一页压上纸堆，纸堆的厚度与毛边在灯下清晰", "P", "P2", "2x2_tile",
    "A recorder pressing a fresh sheet onto the growing stack, the pile's thickness and soft edges catching lamplight; accumulation as gesture",
    {"direction": "push_in", "reference_scale": [1.03, 1.08], "endpoint_hold_seconds": 2.0},
    "地面数据的体量感", NEG_TEXT)
add("ch05", "c5-s03", "世界的钟：昼夜轮转", "同一山谷机位的昼夜循环：晨光、正午、黄昏、星空依次叠化呈现，雾与光变化，山谷静", "V", "V5C", "2x2_tile",
    "The same alpine valley view cycling through morning light, noon, dusk and starlight; mist and illumination shifting gently, the valley itself unchanged; a clock made of landscape",
    "同机位山谷由晨光经正午黄昏叠化入夜再叠化回晨，完成一次循环，节奏极缓", "昼夜循环=周期运动→V5-C 一次叠化循环（世界的钟）；仅此一镜用循环", None)
add("ch05", "c5-s04", "夜空（世界侧）", "同机位山谷的夜：星空清冷呈现，山谷成为剪影，银河微光", "P", "P1", "2x2_tile",
    "The same valley at night: cold starfield above, the valley a quiet silhouette, a faint milky band of stars; immense and regular",
    {"direction": "pull_out", "reference_scale": [1.10, 1.02], "endpoint_hold_seconds": 0},
    "世界之钟的夜半帧；静态星空", None)
add("ch05", "c5-s05", "他的钟：灯亮起", "洞内灯亮起——他“的一天”开始，暖光在岩壁与帐篷上缓缓铺开", "V", "V3", "single",
    "Inside the cave the oil lamp comes alive as 'his day' begins, warm light blooming slowly across rock and canvas; darkness retreating a step then holding",
    "灯亮起，暖光在岩壁上缓缓铺开至稳定，其余静止", "灯=他的钟，亮起对位世界镜头；光铺开→i2v", None)
add("ch05", "c5-s06", "长觉", "睡袋随呼吸缓慢起伏，灯光已稳定，帐篷内安静", "V", "V1", "2x2_tile",
    "The bedroll rising and falling with slow breathing inside the dim tent, lamplight steady; a long sleep rendered as gentle motion",
    "被子随呼吸极缓起伏，其余静止", "睡眠时长感的唯一表达=呼吸；i2v", None)
add("ch05", "c5-s07", "粉痕的间距", "洞壁上一列他画的粉笔短痕，从密到疏、间距渐变，头灯侧照出立体感，无文字无图形", "P", "P1", "single",
    "A vertical column of short chalk marks on the cave wall, spacing gradually widening from bottom to top, raking headlamp light giving them relief; marks only, no shapes, no words",
    {"direction": "push_in", "reference_scale": [1.02, 1.12], "endpoint_hold_seconds": 0},
    "“他以为的天”与真实天数的偏差=间距；母题复用 c2-s08", "marks must remain abstract strokes, never forming diagrams")
add("ch05", "c5-s08", "母题①回：表仍在走", "草叶间那块银壳棕带机械表，阳光移过表蒙，微光一闪，周围草叶轻风", "P", "P2", "single",
    "The same silver wristwatch with brown strap resting between grass blades above the cave, sunlight sliding across its crystal with a soft glint; the outside world's time going on without him",
    {"direction": "push_in", "reference_scale": [1.03, 1.10], "endpoint_hold_seconds": 2.5},
    "母题①中段回收；精密静物", "dial markers vague and unfocused")
add("ch05", "c5-s09", "节拍：滴水位", "融水按稳定节拍滴进石窝，水面一圈圈涟漪扩散，灯光反光随之轻晃", "V", "V1", "single",
    "Meltwater dripping into the stone pool at a steady patient rhythm, each drop spreading one ring of ripples, the lamp reflection trembling softly; a clock made of water",
    "水滴以稳定节拍落下，涟漪一圈圈扩散，反光轻晃", "滴答=钟的听觉转视觉→i2v", None)
add("ch05", "c5-s10", "巨大黑暗里的一盏", "从石窝水滴拉开：洞窟巨大黑暗中只有营地灯光一点暖，比例悬殊", "P", "P1", "2x2_tile",
    "Pulling back from the dripping pool to reveal the cavern's full darkness with the camp lamp one small warm point; the ratio of dark to light is the story",
    {"direction": "pull_out", "reference_scale": [1.16, 1.02], "endpoint_hold_seconds": 0},
    "尺度对比章法：内小外大", None)
add("ch05", "c5-s11", "地面的校准", "地面桌上，一只腕表与一只挂钟同框，指针位置一致，灯光暖白", "P", "P2", "single",
    "On the surface desk a wristwatch and a wall clock in the same frame, hands aligned, warm white light; a calibrated world where clocks agree with each other",
    {"direction": "push_in", "reference_scale": [1.03, 1.08], "endpoint_hold_seconds": 2.5},
    "地面=被校准的世界（对照他的自由运转）；精密→静", "faces readable-free, no numbers in focus")
add("ch05", "c5-s12", "晨光第一线", "洞外清晨，第一线日光爬上山脊，雾气在光里流动", "V", "V3", "2x2_tile",
    "First light of morning climbing a mountain ridge outside, mist flowing through the beams of light; the day arriving exactly on time",
    "晨光沿山脊缓缓爬升，雾气缓慢流动", "光移=自然运动→i2v；“校钟的手”首次出现", None)
add("ch05", "c5-s13", "恒定的线", "洞窟深处，电话线沿岩壁延伸进黑暗，线是画面里唯一连续的线条", "P", "P1", "2x2_tile",
    "Deep in the cavern the black telephone wire running along the rock wall into darkness, the only continuous line in the frame; rock textures passing into black",
    {"direction": "push_in", "reference_scale": [1.02, 1.10], "endpoint_hold_seconds": 0},
    "母题③中段：无论他几点醒，线都通着", None)
add("ch05", "c5-s14", "章尾安放", "木桌上油灯稳定燃烧，旁边摊开的日记与一罐食物，弱光匀净", "P", "P2", "single",
    "Chapter-closing still life: the oil lamp steady on the wooden table beside the open diary and a single can; even weak light, composed and calm",
    {"direction": "pull_out", "reference_scale": [1.08, 1.03], "endpoint_hold_seconds": 3.0},
    "三镜法收尾的安放帧", NEG_TEXT)

# ---------------- ch06 出洞 ----------------
add("ch06", "c6-s01", "铃响前的一瞬", "电话机特写：一切静止，铃锤悬停的位置与听筒，灯光微弱", "P", "P2", "single",
    "The black telephone in extreme close-up, utterly still: the handset, the bell hammer at rest, weak lamplight on the lacquer; the moment before the ring",
    {"direction": "push_in", "reference_scale": [1.03, 1.12], "endpoint_hold_seconds": 2.5},
    "高潮前的静——用静止制造等待", NEG_TEXT)
add("ch06", "c6-s02", "铃响", "电话铃响起：机身与听筒线随铃声极轻微地震动，灰尘在光里跳了一下", "V", "V1", "single",
    "The telephone ringing: the body and its cord trembling very slightly with each ring, a mote of dust stirring in the lamplight; vibration only, nothing else moves",
    "机身与电话线随铃声轻微震颤，其余静止", "震动=瞬间内部运动→i2v；低刺激（微震非猛震）", None)
add("ch06", "c6-s03", "摘下听筒", "他摘下听筒贴到耳边，侧影在弱光里，肩背微微松下来", "P", "P1", "single",
    "The man lifting the handset to his ear, his profile in weak light, shoulders loosening slightly; two months ending in one gesture",
    {"direction": "push_in", "reference_scale": [1.02, 1.08], "endpoint_hold_seconds": 0},
    "关键情节帧→独立生图；静态足够", None)
add("ch06", "c6-s04", "收拾营地", "收拾中的营地：罐头箱已空并捆好，书摞齐，灯仍在燃", "P", "P2", "2x2_tile",
    "The camp being packed: empty crate lashed shut, books stacked and tied, the lamp still burning; departure prepared but not yet made",
    {"direction": "pan_left", "reference_scale": [1.06, 1.06], "endpoint_hold_seconds": 2.0},
    "过渡静物；秩序的回归", None)
add("ch06", "c6-s05", "向上", "头灯光锥朝上，他开始沿绳攀爬，岩壁向上消失在黑暗里，光点渐小", "V", "V3", "single",
    "The headlamp beam angled upward as he begins climbing the rope, rock wall receding into darkness above, his small light rising slowly; the ascent begins",
    "人物沿绳缓慢向上攀爬，头灯光点缓缓上移", "攀爬=人物运动→i2v；上升动势必要", None)
add("ch06", "c6-s06", "高处的小光斑", "从黑暗中向上望：高处岩缝间一个越来越亮的小光斑，岩壁剪影两侧夹出通道", "P", "P1", "single",
    "Looking up from inside the darkness: a small brightening spot of daylight high between rock silhouettes, the walls framing a rough vertical channel toward it",
    {"direction": "push_in", "reference_scale": [1.02, 1.14], "endpoint_hold_seconds": 0},
    "“向光”构图；推近光斑=靠近出口", None)
add("ch06", "c6-s07", "手与绳", "攀爬的手与绳特写，冰晶在绳上闪，指节用力，岩缘", "V", "V1", "single",
    "Close on a climbing hand gripping the rope, ice crystals glittering along the fibers, knuckles firm, rock edge passing; effort made quiet",
    "手抓紧绳向上换位一次，冰屑轻落", "手部运动→i2v；具体而安静的努力", None)
add("ch06", "c6-s08", "走出光幕", "洞口边缘，白光涌入，人影小小一个走进光里，轮廓被光晕包住", "P", "P1", "single",
    "At the cave mouth: white light flooding in, the small figure stepping into it, his silhouette wrapped in bloom; the frame almost entirely light at the edges",
    {"direction": "push_in", "reference_scale": [1.02, 1.10], "endpoint_hold_seconds": 0},
    "过曝起步帧；独立生图控制光晕", None)
add("ch06", "c6-s09", "全片最亮一帧", "正午雪山与冰川全景，他站在洞口平台上极小，天空巨大清冽", "P", "P1", "2x2_tile",
    "Full noon panorama of snow mountains and glacier, the man a tiny figure on the ledge by the cave mouth, sky immense and clean; the brightest frame of the film, exposure high but gentle",
    {"direction": "pull_out", "reference_scale": [1.18, 1.02], "endpoint_hold_seconds": 0},
    "唯一“拉+最亮”释放帧（情绪曲线顶点）；大环境批量", None)
add("ch06", "c6-s10", "地面：日期揭示", "地面帐篷前白天，记录员们起身望向他，其中一人抬腕看向手表，光线明亮", "P", "P2", "2x2_tile",
    "Bright day outside the surface tents: recorders rising and turning toward him, one lifting his wrist to look at his watch; the world that kept the date",
    {"direction": "push_in", "reference_scale": [1.03, 1.08], "endpoint_hold_seconds": 2.0},
    "日期落差由“看表”动作承担；群像静态", "watch dial not readable")
add("ch06", "c6-s11", "母题①：表与掌心", "他把那块银壳棕带表拿回掌心，阳光充满表壳，秒针位置与出发时不同", "P", "P2", "single",
    "The silver wristwatch with brown strap back in his open palm, sunlight filling the polished case, the second hand in a different place than departure; time kept by everyone else",
    {"direction": "push_in", "reference_scale": [1.03, 1.12], "endpoint_hold_seconds": 3.0},
    "母题①高潮回收；精密→静；表是“世界走了一个月”的证人", "dial markers soft, no readable numbers")

# ---------------- ch07 午夜洞 ----------------
add("ch07", "c7-s01", "得州荒漠黄昏", "得州荒漠黄昏：低矮灌木与红岩台地，远处一个小小洞口，暮色青蓝发紫", "P", "P1", "2x2_tile",
    "Texas high desert at dusk: low scrub and red-rock mesas, a small cave opening far away, violet-teal twilight; a new decade, a new cave",
    {"direction": "push_in", "reference_scale": [1.02, 1.10], "endpoint_hold_seconds": 0},
    "第二幕定场；环境批量", None)
add("ch07", "c7-s02", "这次有队伍", "洞口营地：白色工作帐篷、仪器箱、天线杆，几个人影在搬箱，车灯", "P", "P2", "2x2_tile",
    "A scientific camp at the cave mouth: white work tents, instrument crates, an antenna mast, a few figures unloading a truck; organization replacing solitude",
    {"direction": "pan_right", "reference_scale": [1.06, 1.06], "endpoint_hold_seconds": 2.0},
    "与 1962 的“一个人”对照；群像", None)
add("ch07", "c7-s03", "午夜洞营地", "洞内营地更大更装备化：行军床、货架、仪器架、更亮的灯组，电话线换成信号线缆", "P", "P1", "2x2_tile",
    "The 1972 cave camp, larger and technical: cot beds, shelving, instrument racks, brighter lamp clusters, the old telephone wire replaced by signal cables along the wall; ten years of progress",
    {"direction": "push_in", "reference_scale": [1.02, 1.10], "endpoint_hold_seconds": 0},
    "营地升级定场；母题③变体（线缆）", NEG_TEXT)
add("ch07", "c7-s04", "仪器架", "仪器架特写：旋钮、开关与无刻度表盘，指示灯微亮，金属面板哑光", "P", "P2", "single",
    "Close-up of an instrument rack: knobs, toggles and blank-faced gauges, small pilot lamps glowing, matte metal panels; precision without any readable markings",
    {"direction": "push_in", "reference_scale": [1.03, 1.10], "endpoint_hold_seconds": 2.5},
    "精密仪器→静态；1972 的科学感", "no readable numbers or labels anywhere")
add("ch07", "c7-s05", "摆针记录", "滚筒记录仪的摆针在纸带上缓慢划线，摆动稳定，纸带缓缓前移", "V", "V3", "single",
    "A chart recorder: its pen arm swinging in a slow steady rhythm across moving paper, drawing a continuous line; the body's signals translated to ink; no readable scales",
    "摆针匀速摆动，纸带缓慢前移，其余静止", "摆针=节律运动的最佳 i2v 主体（替代曲线图）", "no axes, no scale numbers, paper mostly featureless")
add("ch07", "c7-s06", "监测下的睡眠", "他在行军床上熟睡，胸口随呼吸起伏，床头一盏小灯，电极线隐约可见", "V", "V1", "single",
    "The man asleep on a camp cot, chest rising and falling slowly, a small bedside lamp glowing, faint electrode leads trailing from the headboard; sleep under observation",
    "胸口随呼吸缓慢起伏，其余静止", "呼吸 i2v；“被记录的睡眠”", None)
add("ch07", "c7-s07", "十年后的脸", "同一角度侧脸：33 岁的他胡须长而乱，眼下暗影，头灯光弱", "P", "P1", "single",
    "The same man ten years later in profile: long unkempt beard, shadowed eyes, wearing a headlamp now dim; a face carrying 205 days; identity continuous with the 1962 silhouette",
    {"direction": "push_in", "reference_scale": [1.02, 1.08], "endpoint_hold_seconds": 0},
    "人物连续性关键帧→独立生图；岁月用脸讲", None)
add("ch07", "c7-s08", "空罐之山", "一角堆起的空罐头数量众多，反射不同的微光，秩序已乱", "P", "P2", "2x2_tile",
    "A corner pile of many empty cans catching assorted dim glints, order gone from the stacking; time counted in tin",
    {"direction": "pan_up", "reference_scale": [1.06, 1.06], "endpoint_hold_seconds": 2.0},
    "时间量的静物（与 c4-s10 对照）", "labels blank")
add("ch07", "c7-s09", "数数自测", "他在灯下闭眼坐着做数数自测，一只手的指尖在膝上缓慢轻点，神情专注而平静", "V", "V1", "single",
    "Seated under the lamp with eyes closed, doing his counting self-test, fingertips of one hand tapping slowly on his knee; calm concentration, intimate small motion in stillness",
    "指尖缓慢轻点，呼吸均匀，其余静止", "自测动作=小内部运动→i2v；对应实测细节：数一百二十个数实际用时五分钟（他以为只有两分钟）", None)
add("ch07", "c7-s10", "只有他能打给地面", "他拿起听筒拨动拨盘，信号线缆沿壁延伸向上；唯一主动通话的一方是他", "P", "P2", "single",
    "He lifts the handset and dials; signal cables run along the wall upward; only he may call the surface, never the reverse; a solitary active connection",
    {"direction": "push_in", "reference_scale": [1.03, 1.08], "endpoint_hold_seconds": 2.5},
    "母题③交互帧（1972 通讯规则）；静态足够", NEG_TEXT)
add("ch07", "c7-s11", "巨大洞厅里的一个人", "洞厅更深处：他独自站在巨大空旷的岩厅里，头灯一点，四周黑暗的回声感", "P", "P1", "2x2_tile",
    "Deeper in an enormous rock hall the man stands alone, one point of headlamp light, the void pressing in from all sides; solitude at maximum scale",
    {"direction": "push_in", "reference_scale": [1.02, 1.08], "endpoint_hold_seconds": 0},
    "孤独的最大空间表达", None)
add("ch07", "c7-s12", "缓慢的笔迹", "他在日记上写字，笔画缓慢，纸页行距很大（虚化），灯稳定", "V", "V3", "single",
    "Writing in the diary again, pen moving slowly across widely-spaced unfocused lines, lamp steady; the hand remembers 1962 but slower",
    "笔尖缓慢书写一行，其余静止", "书写 i2v（1972 版）；与 c4-s09 同族", NEG_TEXT)
add("ch07", "c7-s13", "两种记录同框", "桌上：仪器输出的纸带与他的日记并排，客观与主观两份记录，灯光各半", "P", "P2", "single",
    "On the table side by side: the machine's chart paper and his open diary — two records of the same nights, one precise, one personal; lamplight split evenly",
    {"direction": "push_in", "reference_scale": [1.03, 1.10], "endpoint_hold_seconds": 2.5},
    "本章题眼构图：两台时钟同框（呼应 ch02 标题）", NEG_TEXT)
add("ch07", "c7-s14", "黑暗的百分比", "从营地拉开，洞厅巨幅黑暗里灯光群微小，电缆沿壁如细丝", "P", "P1", "2x2_tile",
    "Pulling back until the camp's lamp cluster shrinks inside the cavern's immense black volume, cables thin as threads along the walls; darkness winning the ratio again",
    {"direction": "pull_out", "reference_scale": [1.18, 1.02], "endpoint_hold_seconds": 0},
    "第二幕的空间压迫复现", None)
add("ch07", "c7-s15", "线缆（母题③变体）", "信号线缆沿岩壁延伸进黑暗，比 1962 的电话线更粗更多，仍是一条通向地面的线", "P", "P2", "2x2_tile",
    "Signal cables running along the rock into darkness — thicker and more numerous than the old telephone wire, still a single direction: up and out; continuity with 1962",
    {"direction": "push_in", "reference_scale": [1.03, 1.08], "endpoint_hold_seconds": 2.0},
    "母题③十年后的形态；章尾静态", None)

# ---------------- ch08 接过火把 ----------------
add("ch08", "c8-s01", "德国掩体：走廊", "地下掩体走廊尽头一盏冷白灯，混凝土墙面与管线，无人，冷灰青色调", "P", "P1", "2x2_tile",
    "An underground bunker corridor ending in one cold white lamp, raw concrete walls and ceiling conduits, nobody there; the palette shifts from amber to clinical grey-teal; institutional stillness",
    {"direction": "push_in", "reference_scale": [1.02, 1.10], "endpoint_hold_seconds": 0},
    "科学线开卷；色彩转冷（章法）", None)
add("ch08", "c8-s02", "掩体居室", "掩体内室：一张床、一盏壁灯、无窗，居住过的痕迹（毛衣、水杯），安静", "P", "P2", "2x2_tile",
    "A bunker dwelling room: single bed, wall lamp, no windows, traces of habitation — a folded sweater, a cup; quiet voluntary confinement",
    {"direction": "pan_right", "reference_scale": [1.06, 1.06], "endpoint_hold_seconds": 2.0},
    "“志愿者也把自己埋进地下”的居所", None)
add("ch08", "c8-s03", "一排门", "走廊透视：一排相似的门延伸，灯光均匀，极静", "P", "P1", "2x2_tile",
    "Down the corridor a row of identical doors receding in even lamplight, absolute quiet; many rooms, many nights, many volunteers implied",
    {"direction": "pull_out", "reference_scale": [1.14, 1.02], "endpoint_hold_seconds": 0},
    "复数实验的暗示；冷", None)
add("ch08", "c8-s04", "脑内的钟：一点暖光", "超现实：深蓝近黑的内部空间中央，一枚极小的暖光点，四周如深海", "P", "P1", "single",
    "Subtle surreal interior: a deep blue-black space like an inner ocean, at its center one tiny warm point of light — smaller than a grain, patient, alive; nothing else",
    {"direction": "push_in", "reference_scale": [1.02, 1.14], "endpoint_hold_seconds": 0},
    "SCN 的美学替身（禁解剖图）；独立生图控制纯度", None)
add("ch08", "c8-s05", "光点呼吸", "那枚暖光点像呼吸一样缓慢地明暗，明灭幅度极小，节奏稳定", "V", "V3", "single",
    "The tiny warm point slowly brightening and dimming like a breath, amplitude small, rhythm steady; the body's metronome visualized",
    "光点极缓地明暗呼吸一次循环，幅度小，无闪烁", "脉动=内部运动→i2v；全片核心隐喻镜", "no flicker, brightness change must be slow and small")
add("ch08", "c8-s06", "发丝般的光线", "黑暗中许多发丝般的微光从各方向汇聚向同一点，如河流入湖", "P", "P2", "single",
    "In darkness, many hair-thin threads of faint light converging from all directions toward one point, like rivers into a still lake; elegant, subtle, structural",
    {"direction": "pull_out", "reference_scale": [1.10, 1.03], "endpoint_hold_seconds": 2.5},
    "神经通路的抽象美；静态构图足够", None)
add("ch08", "c8-s07", "眼睛（暗处）", "一只眼睛的特写：虹膜纹理与放大的瞳孔，极暗环境，微光反射", "P", "P2", "single",
    "Extreme close-up of one human eye in darkness: iris texture detailed, pupil wide open, a faint catchlight; intimate and still",
    {"direction": "push_in", "reference_scale": [1.03, 1.12], "endpoint_hold_seconds": 2.5},
    "眼睛=报时器官（黑视蛋白章）开场；精密→静", None)
add("ch08", "c8-s08", "光进入眼睛", "一线晨光从侧面进入睁开的眼睛，瞳孔缓缓收缩，虹膜色彩显现", "V", "V3", "single",
    "A thin ray of morning light entering an open eye from the side, the pupil slowly contracting, iris color revealing itself; calibration happening in flesh",
    "光线进入，瞳孔缓慢收缩一次，其余静止", "瞳孔光反应→i2v；“校钟的手”抵达身体", None)
add("ch08", "c8-s09", "窗台第一线", "卧室窗台：晨光第一线落在窗框与地板，尘埃浮在光带边缘", "P", "P2", "2x2_tile",
    "A bedroom windowsill: the day's first light landing on the frame and floorboards, dust motes floating at the edge of the light band; morning as a gentle mechanism",
    {"direction": "push_in", "reference_scale": [1.03, 1.08], "endpoint_hold_seconds": 2.0},
    "光的实用帧（连到 ch10 的卧室世界）", None)
add("ch08", "c8-s10", "光在地板上移动", "一线光在木地板上缓慢移动，尘埃在光带里浮动，房间其余在暗处", "V", "V1", "2x2_tile",
    "A line of light creeping slowly across wooden floorboards, dust drifting inside the bright band, the rest of the room in soft shadow; time made visible on a floor",
    "光带沿地板极缓移动，尘埃浮动，其余静止", "光移=最贴 i2v 的运动；“钟走”的日常化身", None)
add("ch08", "c8-s11", "机械表内部", "超近距离静物：机械表机芯的齿轮与游丝，金属光泽，完全静止", "P", "P2", "single",
    "Macro still life of a mechanical watch movement: gears and hairspring in metallic luster, utterly still, museum-quiet; the finest clock humans build",
    {"direction": "push_in", "reference_scale": [1.03, 1.10], "endpoint_hold_seconds": 3.0},
    "精密之最→静态长停留；与脑内光点互为镜像", "no readable text or numbers")
add("ch08", "c8-s12", "严格光照实验", "一间无窗暗室：单人床与仪器，门缝漏进一线受控的光，极简", "P", "P1", "2x2_tile",
    "A windowless experiment room: single bed and instruments, a controlled line of light through the door gap; minimalism where 24.18 hours was measured",
    {"direction": "push_in", "reference_scale": [1.02, 1.08], "endpoint_hold_seconds": 0},
    "现代精测的冷感；环境批量", None)
add("ch08", "c8-s13", "深空（静）", "深空星野：无数星点，缓慢呈现的深度，无轨道无连线", "P", "P2", "2x2_tile",
    "Deep starfield: countless points across layered depth, no lines, no orbits, no planets prominent; the quietest clock face of all",
    {"direction": "pull_out", "reference_scale": [1.10, 1.02], "endpoint_hold_seconds": 2.5},
    "宇宙尺度钟面；静态（星野禁增强）", "no orbit lines, no constellation diagrams")
add("ch08", "c8-s14", "红色的点", "深空里一颗微红的小星点，星光极缓地变化，周围星野静", "V", "V3", "2x2_tile",
    "In the deep starfield one small reddish point of light, its glow shifting almost imperceptibly; a neighboring day of 24.65 hours waiting",
    "红点星光极缓变化，星野其余静止", "火星意象→i2v 微光变；为 ch10 铺垫", "no orbit lines, no motion trails")

# ---------------- ch09 活在洞里的人 ----------------
add("ch09", "c9-s01", "手抚窗台", "清晨将亮的卧室，一位盲人的手平稳地抚过窗台木板，姿态安稳", "P", "P2", "single",
    "A dim early-morning bedroom: a blind man's hand resting and moving calmly along the windowsill wood, gesture settled and unafraid; dignity in the dark",
    {"direction": "push_in", "reference_scale": [1.03, 1.08], "endpoint_hold_seconds": 2.0},
    "医学章的人物定装帧；触觉=他的光", None)
add("ch09", "c9-s02", "指尖与叶", "手指停在一盆绿植的叶沿，轻触叶尖，叶子弹了一下", "V", "V1", "single",
    "Fingertips pausing at the leaf edge of a potted plant, touching the tip; the leaf springs back gently; contact as confirmation",
    "指尖轻触叶尖，叶片轻轻弹回，其余静止", "触碰+叶弹=小内部运动→i2v", None)
add("ch09", "c9-s03", "药瓶与水杯", "窗台上小药瓶与水杯的静物，晨光未到，室内很暗，轮廓温和", "P", "P2", "single",
    "Still life on the sill: a small medicine bottle and a glass of water, dawn not yet arrived, the room very dark, outlines gentle; treatment as quiet routine",
    {"direction": "push_in", "reference_scale": [1.03, 1.10], "endpoint_hold_seconds": 2.5},
    "褪黑素意象；标签必须无字", "label strictly blank, no text")
add("ch09", "c9-s04", "墙上的光在走", "窗帘缝的一线街灯/月光在墙上极缓慢地移动，家具剪影静止", "V", "V1", "2x2_tile",
    "A thin line of streetlamp light crossing a bedroom wall extremely slowly, furniture silhouettes still; for some, the clock is only this",
    "墙上光线极缓平移，其余完全静止", "光移→i2v；看不见钟的人的时间", None)
add("ch09", "c9-s05", "城市之夜", "城市屋顶群夜景，灯火稀疏，青蓝色，一层薄雾", "P", "P1", "2x2_tile",
    "A city's rooftops at night: scattered lit windows, teal-blue haze, calm; millions of clocks and some without light",
    {"direction": "pull_out", "reference_scale": [1.12, 1.02], "endpoint_hold_seconds": 0},
    "从个人到人群的拉开", None)
add("ch09", "c9-s06", "有序的日常", "门边靠着一根盲杖，外套挂好，鞋摆正，一切有序安静", "P", "P2", "2x2_tile",
    "By the door: a white cane leaning, coat hung, shoes aligned; an ordered quiet life; acceptance arranged like still life",
    {"direction": "pan_right", "reference_scale": [1.06, 1.06], "endpoint_hold_seconds": 2.0},
    "生活秩序的静物；不煽情", None)
add("ch09", "c9-s07", "2021：深时营地", "比利牛斯山洞大厅，十几顶小帐篷围着一盏中央大灯，人影安静走动", "V", "V3", "2x2_tile",
    "A vast Pyrenean cave hall in 2021: a dozen small tents arranged around one large central lamp, quiet human silhouettes moving between them; fifteen people, forty days, no clocks",
    "灯光稳定，人影极缓走动，其余静止", "人群微动→i2v；历史照进当代", None)
add("ch09", "c9-s08", "公共木桌", "洞内公共木桌：茶壶、茶杯、一截打结的绳，灯光暖", "P", "P1", "2x2_tile",
    "The communal wooden table inside the cave: teapot, cups, a length of rope tied in knots; the knot-rope as their calendar; warm communal light",
    {"direction": "push_in", "reference_scale": [1.02, 1.08], "endpoint_hold_seconds": 0},
    "绳结=计日的实物（禁文字日历）；静物", "no text, no paper calendar, knots only")
add("ch09", "c9-s09", "一排头灯", "一排头灯挂在绳索上，灯都熄着，像一排睡着的星", "P", "P2", "2x2_tile",
    "A row of headlamps hanging from a line, all switched off, like a sleeping constellation; tools of many individual lights at rest",
    {"direction": "push_in", "reference_scale": [1.03, 1.08], "endpoint_hold_seconds": 2.0},
    "群像的物件化；静", None)
add("ch09", "c9-s10", "水潭倒影", "洞内小水潭，水面映着灯的倒影，一圈极缓的涟漪让倒影轻晃", "V", "V1", "2x2_tile",
    "A small pool inside the cave reflecting the camp lamp, one slow ring of ripples making the reflection tremble softly; stillness with a pulse",
    "水面涟漪极缓扩散，灯的倒影轻晃后复原", "倒影微动→i2v；1962 石窝的回声", None)
add("ch09", "c9-s11", "人群如小星", "从洞厅拉开：帐篷与灯光缩成一小片光点群，四周巨大岩壁黑暗", "P", "P1", "2x2_tile",
    "Pulling back in the great hall: tents and lamps shrinking into a small cluster of light points against immense dark rock; a tiny temporary galaxy of people",
    {"direction": "pull_out", "reference_scale": [1.16, 1.02], "endpoint_hold_seconds": 0},
    "当代集体版“黑暗里一点暖”", None)
add("ch09", "c9-s12", "诊室里的两只手", "诊室里，医生的手与患者的手在桌面轻触，无器械前景，色调暖白", "P", "P2", "single",
    "In a clinic room, a doctor's hand and a patient's hand resting lightly together on the desk, no instruments in the foreground, warm neutral light; medicine as accompaniment",
    {"direction": "push_in", "reference_scale": [1.03, 1.10], "endpoint_hold_seconds": 2.5},
    "医学的温度帧；手部关系准确→独立生图", None)
add("ch09", "c9-s13", "安睡（自由运转的人）", "盲人安睡的侧影剪影，被子随呼吸缓慢起伏，房间极暗而安稳", "V", "V1", "single",
    "The blind man asleep, side profile in silhouette, blanket rising and falling with slow breathing, the room deeply dark and secure; rest despite the drifting clock",
    "被子随呼吸极缓起伏，其余静止", "呼吸 i2v 收束人物线；“漂着的钟也能安睡”", None)

# ---------------- ch10 今晚你的钟 ----------------
add("ch10", "c10-s01", "你的房间（深夜）", "现代听众卧室深夜：城市光透过窗帘缝，床与被子的暗轮廓，安静", "P", "P1", "2x2_tile",
    "A modern bedroom late at night: city light seeping through the curtain gap, dark soft shapes of bed and blanket; the listener's own room, utterly calm",
    {"direction": "push_in", "reference_scale": [1.02, 1.08], "endpoint_hold_seconds": 0},
    "章法定场：镜头回到“你”；无人物特征（普适）", None)
add("ch10", "c10-s02", "呼吸", "被子随呼吸缓慢起伏的特写，光线极暗，只有轮廓的明暗变化", "V", "V1", "2x2_tile",
    "Close-up of a blanket rising and falling with slow breathing in near darkness, only the subtle shading of contours changing; the body keeping its time",
    "被子随呼吸极缓起伏，明暗微变，其余静止", "呼吸=钟的肉身证据→i2v", None)
add("ch10", "c10-s03", "扣下的手机", "床头柜上屏幕朝下扣着的手机，一小片充电微光，木纹", "P", "P2", "single",
    "On the nightstand a phone lying face-down, a small charging glow beneath it, wood grain soft; the modern watch put down like his, on the surface",
    {"direction": "push_in", "reference_scale": [1.03, 1.10], "endpoint_hold_seconds": 2.5},
    "母题①的现代对应物（摘表=扣手机）；静物", "screen shows no text, no icons, no glowing content")
add("ch10", "c10-s04", "晨光爬进", "窗帘缝的一线晨光沿地板缓慢移动，落上床沿，尘埃浮动", "V", "V3", "2x2_tile",
    "A line of dawn light through the curtain gap crawling across the floor and up onto the bed's edge, dust motes drifting; the hand that winds you",
    "晨光线沿地板极缓移动至床沿，尘埃浮动", "光移 i2v；上发条的手（正用）", None)
add("ch10", "c10-s05", "光抵达床沿", "晨光已爬上床沿与被角的一瞬，房间仍大半在暗里", "P", "P2", "2x2_tile",
    "The moment dawn light has reached the bed's edge and the corner of the blanket, most of the room still in shadow; arrival without alarm",
    {"direction": "push_in", "reference_scale": [1.03, 1.08], "endpoint_hold_seconds": 2.5},
    "上一镜的静帧版；安放", None)
add("ch10", "c10-s06", "星空（你的）", "清冷星空，银河微光，山影地平线，极静", "P", "P1", "2x2_tile",
    "A cold clear starfield with a faint galactic band above a mountain horizon; the same sky over every sleeper; immense calm",
    {"direction": "pull_out", "reference_scale": [1.10, 1.02], "endpoint_hold_seconds": 0},
    "尺度升维；静", None)
add("ch10", "c10-s07", "火星的黄昏", "红色沙丘与岩丘的黄昏，天空淡青，太阳小小一颗，静", "P", "P2", "2x2_tile",
    "Dusk on red dunes and rocky hills under a pale teal sky, a small low sun; a day twenty-four point six five hours long, nobody home yet",
    {"direction": "pan_right", "reference_scale": [1.06, 1.06], "endpoint_hold_seconds": 2.5},
    "火星的一天；无轨道线无探测器", "no rovers, no machinery, no flags")
add("ch10", "c10-s08", "灯旋钮", "手指拧动床头灯旋钮，灯光缓缓变暗直至将熄，房间沉入蓝黑", "V", "V1", "single",
    "A hand turning the bedside lamp's dimmer, the glow easing down toward almost nothing, the room sinking into blue-black; choosing the dark gently",
    "旋钮转动，灯光缓慢平滑变暗至熄，无闪烁", "光暗渐变→i2v；主动关灯=呼应片头", None)
add("ch10", "c10-s09", "只剩窗外微光", "灯熄后从床头拉开：整个房间安静的轮廓，只剩窗外一线微光", "P", "P1", "2x2_tile",
    "After the lamp dies, pulling back from the bed: the whole room's quiet shapes, one thin line of window light remaining; darkness as a room, not a void",
    {"direction": "pull_out", "reference_scale": [1.12, 1.02], "endpoint_hold_seconds": 0},
    "回到全片统一的暗琥珀/夜蓝", None)
add("ch10", "c10-s10", "床头的旧闹钟", "床头的旧式双铃闹钟静物，指针位置任意，窗光微照", "P", "P2", "single",
    "A vintage twin-bell alarm clock on the nightstand in still life, hands in no particular position, faint window light; your own small machine, resting tonight",
    {"direction": "push_in", "reference_scale": [1.03, 1.12], "endpoint_hold_seconds": 3.0},
    "母题①的卧室变体；精密→静", "dial markers vague, no readable numbers")
add("ch10", "c10-s11", "一杯温水", "床头柜上一杯温水，水面极缓地晃动，灯光反射轻摇", "V", "V1", "single",
    "A glass of warm water on the nightstand, its surface swaying almost imperceptibly, the lamp's reflection trembling on the meniscus; tiny live detail in the still room",
    "水面极缓晃动，反射轻摇后趋静", "微动 i2v；房间里的“活着”", None)
add("ch10", "c10-s12", "被窝（安放）", "被窝一角温暖隆起的构图，几乎全静，光只剩最微弱一层", "P", "P2", "2x2_tile",
    "A corner of the blanket warmly risen, the frame almost entirely still, light down to its faintest layer; rest completed",
    {"direction": "push_in", "reference_scale": [1.02, 1.06], "endpoint_hold_seconds": 3.0},
    "章尾安放；与 c4-s12 呼应但暖", None)

# ---------------- epilogue 尾声 ----------------
add("epilogue", "ep-s01", "母题①终：表", "同一块银壳棕带机械表在晨/月光下，表盘朝上，秒针又在不同位置", "P", "P2", "single",
    "Final appearance of the silver wristwatch with brown strap, face up in soft morning light, the second hand in yet another position; time kept, always, by someone",
    {"direction": "push_in", "reference_scale": [1.03, 1.10], "endpoint_hold_seconds": 3.0},
    "母题三连收之一；精密静物长停留", "dial markers soft")
add("epilogue", "ep-s02", "母题②终：灯睡去", "黄铜油灯的火焰缓缓降低、趋于安静，灯光圈缩小至稳定的一点", "V", "V3", "single",
    "The brass oil lamp's flame easing lower and quieter, its circle of light shrinking to one steady point; the lamp allowed to sleep",
    "火焰缓慢均匀降低至小而稳定，无快变", "母题三连收之二；焰的谢幕（缓变不闪烁）", "no flicker, slow smooth dimming only")
add("epilogue", "ep-s03", "母题③终：线仍通", "电话线垂入黑暗的最后构图，线外一切安静，微微反光", "P", "P1", "single",
    "Final composition of the telephone wire descending into darkness, everything else hushed, a faint sheen along the line; the connection that outlasted the story",
    {"direction": "push_in", "reference_scale": [1.02, 1.10], "endpoint_hold_seconds": 0},
    "母题三连收之三；静态", None)
add("epilogue", "ep-s04", "回到洞口", "冰川洞口远景：一线天光落在雪坡上，融水细流闪着流下，世界照常", "V", "V3", "2x2_tile",
    "The glacier cave mouth from afar: a shaft of daylight on the snow slope, a thin meltwater stream glinting as it runs; the world going on above the dark",
    "融水细流缓慢流动，天光稳定，其余静止", "开场的地理闭环；水流 i2v", None)
add("epilogue", "ep-s05", "你的黑暗", "卧室：黑暗里窗帘缝的一线微光，极安静，与片头同族构图", "P", "P1", "2x2_tile",
    "The bedroom again in darkness: one thin thread of light at the curtain gap, immense quiet; the same family of frame as the cold open — you, not buried, just resting",
    {"direction": "pull_out", "reference_scale": [1.08, 1.02], "endpoint_hold_seconds": 0},
    "与片头 B 版同族画面；首尾闭环", None)
add("epilogue", "ep-s06", "安睡的侧影", "睡者的侧影剪影，安稳，房间只剩最微光，呼吸不可察觉", "P", "P2", "single",
    "A sleeper's silhouette in profile, at rest, the room down to its faintest light, breathing almost imperceptible; good night",
    {"direction": "push_in", "reference_scale": [1.02, 1.06], "endpoint_hold_seconds": 3.0},
    "晚安帧；静态（呼吸已在 c10 用过，这里留静）", None)
add("epilogue", "ep-s07", "一线光（终帧）", "全暗画面里唯一的一线极微光，构图为留白，等待明晨", "P", "P2", "2x2_tile",
    "The final frame: near-total darkness holding one thread of faint light, composition mostly rest and space; waiting, without hurry, for morning",
    {"direction": "push_in", "reference_scale": [1.02, 1.05], "endpoint_hold_seconds": 3.5},
    "终帧=“等明早一线光”；长停留收束全片", None)

# ---------------- build ----------------
CLSMAP = {"P": "image_camera_motion", "V": "image_to_video"}
def strat_cls(st): return CLSMAP["P" if st.startswith("P") else "V"]

sec_order = ["bridge", "ch01", "ch02", "ch03", "ch04", "ch05", "ch06", "ch07", "ch08", "ch09", "ch10", "epilogue"]
by_sec = {k: [] for k in sec_order}
for s in S: by_sec[s["section"]].append(s)

shots = []
t = 0.0
INTRA, CHAP = 0.19, 0.7547
for sec in sec_order:
    for i, s in enumerate(by_sec[sec]):
        strat = s["strat"]
        dur = DUR["V5C"] if strat == "V5-C" else DUR[strat]
        cls = CLSMAP["P" if strat.startswith("P") else "V"]
        full_prompt = PREFIX + " " + s["prompt"] + (" " + s["extra_neg"] if s["extra_neg"] else "")
        shot = {
            "id": s["sid"], "paragraph_id": None, "section": sec,
            "beat": s["beat"], "narration": None,
            "scene": s["scene"],
            "est_seconds": dur, "est_body_offset_s": round(t, 2),
            "status": "planned_outline_basis",
            "timing": {"mode": "planned_estimate", "note": "按节拍估算；口播锁定后由 01/02/04 管线重排并回填 narration/paragraph_id/时间轴"},
            "shot_class": cls, "strategy": strat,
            "image_prompt": full_prompt, "image_mode": s["mode"],
            "motion_prompt": None, "loop_allowed": False,
            "tail_extension_seconds": 0.0, "image_motion": None,
            "motion_reason": s["reason"],
        }
        if cls == "image_to_video":
            mp = "One continuous original-speed calm shot. " + s["motion"] + ". Slow gentle motion only. No cuts, no shake, no camera move, no flicker."
            if strat == "V5-C":
                mp += " Loop: one cross-faded repeat of the full cycle is allowed."
            shot["motion_prompt"] = mp
            shot["loop_allowed"] = (strat == "V5-C")
            shot["tail_extension_seconds"] = 2.5
        else:
            shot["image_motion"] = {"direction": s["motion"]["direction"],
                                    "reference_scale": s["motion"]["reference_scale"],
                                    "endpoint_hold_seconds": s["motion"]["endpoint_hold_seconds"]}
        shots.append(shot)
        t += dur + (INTRA if i < len(by_sec[sec]) - 1 else 0.0)
    t += CHAP
body_est = t - CHAP

import collections
cnt_cls = collections.Counter(x["shot_class"] for x in shots)
cnt_strat = collections.Counter(x["strategy"] for x in shots)
cnt_mode = collections.Counter(x["image_mode"] for x in shots)

plan = {
    "schema_version": 1,
    "episode": "siffre-beyond-time",
    "basis": "story/OUTLINE.md 大纲 v1（口播未锁定）",
    "source_sha256": None,
    "created_at": str(date.today()),
    "fps": 30, "width": 1920, "height": 1080,
    "body_est_seconds": round(body_est, 1), "body_est_minutes": round(body_est / 60, 1),
    "cps_final": 3.5,
    "intra_gap_s": INTRA, "para_gap_s": 0.4245, "chap_gap_s": CHAP,
    "counts": {"shots": len(shots), "image_camera_motion": cnt_cls["image_camera_motion"],
               "image_to_video": cnt_cls["image_to_video"], "controlled_simulation": 0,
               "by_strategy": dict(cnt_strat), "by_image_mode": dict(cnt_mode)},
    "section_titles": SECTION_TITLES,
    "notes": [
        "编制基础：大纲 v1 十章节拍；口播（NARRATION_MASTER）未锁定，narration/paragraph_id 为空，锁定后必须经 01 解析→02 节拍→04 重建映射，镜头增删≤20% 属正常。",
        "片头背景不单独生产：按 intro-node 慢钩型流程，从本计划验收后的 image_camera_motion 池中选取（5 句背景）。",
        "全集无 controlled_simulation 类（2026-10-18 全线原则：禁代码图表画面；数据全部实物化——记录纸竖痕、粉笔间距、绳结、摆针、水滴节拍）。",
        "母题连续性（跨镜同物）：①手表=银壳机械表棕皮带（c1-s06/07/08、c5-s08、c6-s11、ep-s01）；②灯=黄铜座油灯玻璃罩（brg、c2-s06、c3-s07、c4-s01/02、c5-s05、c7、ep-s02）；③线=1962 黑胶皮电话线→1972 信号线缆（c2、c4-s07、c5-s13、c7-s15、ep-s03）。",
        "人物连续性：1962=23岁男，深色羊毛帽+旧呢大衣，全程不见正脸（仅剪影/背影/侧影）；1972=同一人33岁长须（c7-s07 唯一正侧脸）；ch09 盲人与 ch10 听众卧室均为独立人物，无面部特写。",
        "日记/记录纸/仪器镜头一律无可读文字与数字，笔迹以虚化笔触呈现（各镜 extra_neg 已注明）。",
        "推拉方向语义：推=深入（下洞/低谷/内心），拉=抽离（尺度/释放/空间）；c6-s09 为全片唯一最亮帧；情绪曲线=渐紧→出洞释放→再紧→渐宽至卧室。",
        "i2v 仅用于自然内部运动（焰、水、呼吸、书写、攀爬、摆针、光移、微动），每镜保留验收静帧，失败回退 P1（visual-motion 2026-10-18 全线原则）。",
        "本计划为大纲阶段文档，不提交 GPU、不生成媒体；执行侧生产另按授权启动。",
    ],
    "shots": shots,
}

OUT_JSON.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")

# ---------- human-readable ----------
lines = ["# siffre-beyond-time 分镜计划 v1（大纲基础）", "",
         f"依据：story/OUTLINE.md（大纲 v1，口播未锁定）。共 {len(shots)} 镜，正文估时 {body_est/60:.1f} 分钟（节拍估算，锁定后回填）。",
         f"类别：image_camera_motion {cnt_cls['image_camera_motion']} / image_to_video {cnt_cls['image_to_video']} / controlled_simulation 0。",
         "提示词前缀沿用 sleep-aid-visual-style 骨架，已并入每镜 image_prompt；生成选型（single/2x2_tile）已按 2026-10-06 规则逐镜标注。", "",
         "注：完整提示词以 SHOT_PLAN.json 为真源；本表为一行索引。", ""]
for sec in sec_order:
    lines.append(f"## {SECTION_TITLES[sec]}")
    lines.append("")
    lines.append("| 镜头 | 类别/策略 | 生图 | 节拍 |")
    lines.append("|---|---|---|---|")
    for x in by_sec[sec]:
        st = x["strat"]; cls_short = "i2v" if st.startswith("V") else "P"
        lines.append(f"| {x['sid']} | {cls_short}·{st} | {x['mode']} | {x['beat']} |")
    lines.append("")
lines.append("## 连续性与红线速查")
lines.append("")
lines.append("- 母题①表 / ②灯 / ③线 的跨镜清单见 SHOT_PLAN.json notes。")
lines.append("- 所有纸面、仪器、表盘：无可读文字数字。")
lines.append("- i2v 运动只允许 motion_prompt 声明的单一温和运动；焰与光变必须缓变无闪烁。")
lines.append("- 口播锁定后：重跑 01/02/04 管线重建 paragraph_id/narration/时间轴，镜头可±20% 调整。")
OUT_MD.write_text("\n".join(lines), encoding="utf-8")

print("shots:", len(shots))
print("by_section:", {sec: len(by_sec[sec]) for sec in sec_order})
print("by_class:", dict(cnt_cls), "| by_strategy:", dict(cnt_strat))
print("body_est_s:", round(body_est, 1), "=", round(body_est / 60, 1), "min")
print("i2v share: {:.0%}".format(cnt_cls['image_to_video'] / len(shots)))
print("written:", OUT_JSON)
print("written:", OUT_MD)
