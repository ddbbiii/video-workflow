# -*- coding: utf-8 -*-
"""全片 SHOT_PLAN v1（ch01..ch12 + epilogue，约 150 镜）。

- ch01/ch02 沿用预览版 26 镜（图已生成，id/prompt 不变），只按全片重新分配段落；
- ch03..epilogue 新增，按章主题给镜头，段落按字数均匀分配；
- 视觉弧：星夜雪山→雪晶→雪层→蓝冰→冰川流动→裂隙→U 形谷→冰碛石→融水→末端冰山→冰芯→后退→回到雪夜。
- 零图表、零文字、零人物；P1/P2 单向运镜；i2v 预留 0（本轮全部静帧 affine）。
"""
from __future__ import annotations
import json
from pathlib import Path

EP = Path(__file__).resolve().parents[3]
OLD = EP / "visual" / "SHOT_PLAN.json"
UTT = EP / "audio" / "utterances.json"
OUT = EP / "visual" / "SHOT_PLAN_FULL.json"
CPS = 3.45

STYLE = ("Photorealistic cinematic still, cold blue-white high-alpine glacier world, natural soft "
         "light, extremely fine ice and snow texture, calm slow bedtime documentary mood, subtle "
         "film grain, no HDR glow, 16:9. ")
BAN = ("No text, no letters, no numbers, no readable labels, no charts, no diagrams, no maps, "
       "no arrows, no collage, no split screen, no borders, no watermark, no logo, no people, "
       "no hands, no faces, no buildings, no warm daylight, no oversaturated colors, no fantasy "
       "glowing magic. ")

PALETTE = {
    "ch03": ("Pale blue hour light on glacier ice: white snowfields, translucent blue ice walls, "
             "crevasses and ice caves, soft beams, clean cold air"),
    "ch04": ("Deep glacier ice and dark rock: dense blue ice with flow bands, wet bedrock, "
             "crystal textures under pressure, low soft light"),
    "ch05": ("Wide glacier survey views: aerial ice fields, marker stakes, curved flow lines, "
             "blue-grey shadow, quiet scientific patience"),
    "ch06": ("Aerial and close crevasse fields: blue cracks cutting white ice, snow bridges, "
             "deep shadowed fissures, cold high-altitude light"),
    "ch07": ("Alpine valleys shaped by ice: V-shaped stream valleys, broad U-shaped troughs, "
             "polished bedrock, hanging waterfalls, distant fjords"),
    "ch08": ("Glacial debris and moraine: dark rock stripes on white ice, boulders on green "
             "meadow, milky turquoise lake, coarse gravel, low evening light"),
    "ch09": ("Summer glacier melt: clear streams on ice, meltwater channels, blue moulins, "
             "glacier portal, milky river and lake, soft daylight"),
    "ch10": ("Glacier terminus and sea: calving ice cliffs, floating icebergs, fjord water, "
             "sediment plumes, cold overcast dusk"),
    "ch11": ("Greenland and Antarctic ice sheet: vast white plains, ice core cylinders, trapped "
             "air bubbles, dust layers, cold laboratory blue"),
    "ch12": ("Retreating glacier edge: newly exposed bedrock, moraine ridges, young lakes, "
             "wide valley scale, muted blue-grey light"),
    "epilogue": ("Night returns: starlit snow mountains, one snow crystal, deep indigo calm, "
                 "the same valley as the opening"),
}

# (id, section, beat, scene_zh, class, strategy, mode, single_cat, prompt_core)
NEW_ROWS = [
    # ---------------- ch03 白色的冰,为什么有时会变成蓝色 ----------------
    ("c3-s01", "ch03", "白色冰面", "蓝调时刻的冰川表面,风吹出的细纹,阳光斜照像凝固的海",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A wide glacier surface at pale blue hour, wind-carved ripples across white snow, low sun "
     "grazing the ice so it looks like a frozen sea, distant peaks, calm and luminous"),
    ("c3-s02", "ch03", "裂隙里的蓝", "冰裂隙内部,两侧冰壁透出安静深蓝,顶部一线天光",
     "image_camera_motion", "P1", "single", "关键特写",
     "Inside a narrow glacier crevasse, deep clear blue ice walls on both sides, one thin line of "
     "pale daylight far above, faint frost dust in the air, silent cathedral of ice"),
    ("c3-s03", "ch03", "光穿过冰", "一束柔和冷光穿过厚冰,冰体内部发出淡蓝辉光",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A soft beam of cold light passing through a thick slab of clear glacier ice, the interior "
     "glowing pale blue, tiny bubbles suspended, dark rock behind"),
    ("c3-s04", "ch03", "被吸收的红光", "冰壁边缘,暖色光在冰里迅速衰减,只剩蓝调",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Edge of a thick ice wall where a faint warm glimmer dies within centimeters and only blue "
     "light survives deeper in, natural gradient inside the ice, no diagram"),
    ("c3-s05", "ch03", "乳白色的冰", "含气泡与细泥沙的冰体,乳白偏灰,裂缝散射光线",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Milky grey-white glacier ice crowded with tiny bubbles and fine sediment, light scattering "
     "inside, frosted uneven surface, cold diffuse daylight, opaque and soft"),
    ("c3-s06", "ch03", "一线蓝", "整片沉静白雪中,一条窄缝露出极深的蓝",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A vast calm white snowfield interrupted by one narrow crack revealing deep blue ice, "
     "extreme contrast of white and blue, quiet minimal composition"),
    ("c3-s07", "ch03", "冰洞", "冰川内部冰洞,穹顶透蓝,底部有融水细流",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A natural glacier ice cave, blue translucent ceiling arching overhead, thin meltwater "
     "threading the floor, soft light entering from the mouth, hushed and cold"),
    ("c3-s08", "ch03", "不同年代的冰", "冰壁层理:不同年龄的冰层颜色深浅不一,夹着细尘带",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A glacier ice wall showing bands of ice from different ages, subtle tonal layers and thin "
     "dust seams, blue-grey translucency, fine crystalline texture, soft side light"),
    ("c3-s09", "ch03", "沙尘与晶体", "冰内密密麻麻的晶体与暗色沙尘颗粒,微距",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Macro inside glacier ice: dense interlocking crystals and scattered dark mineral dust "
     "grains, tiny bubbles, translucent blue-grey depth, cold precise detail"),
    ("c3-s10", "ch03", "白与蓝之间", "雪坡尽头露出蓝色冰面,白色与蓝色柔和过渡",
     "image_camera_motion", "P2", "2x2_tile", None,
     "Where a white snow slope gives way to exposed blue glacier ice, a soft natural boundary "
     "of white grains over glassy blue, faint melt channels, calm transition"),
    ("c3-s11", "ch03", "冰的对话", "整块蓝冰占据画面,极简,内部有细密气泡与裂纹",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A minimal frame filled by one mass of clear blue glacier ice, delicate bubble chains and "
     "hairline fractures inside, soft backlight, almost abstract and very calm"),
    ("c3-s12", "ch03", "山谷不简单", "从高处俯瞰整条冰川,蓝白相间,山谷深处有阴影",
     "image_camera_motion", "P2", "2x2_tile", None,
     "High viewpoint over a whole glacier valley, blue and white ice filling the trough, deep "
     "shadows in the side valleys, layered ridges receding into cold haze"),

    # ---------------- ch04 坚硬的冰,竟然可以像面团一样变形 ----------------
    ("c4-s01", "ch04", "冰箱里的冰", "一块透明冰块放在深色石面上,表面有细裂纹",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A single clear ice block resting on a dark wet stone surface, fine internal cracks catching "
     "light, cold condensation, deep shadow background, still life"),
    ("c4-s02", "ch04", "清脆的裂", "冰块上一道新鲜裂纹,冰屑散落",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Extreme close view of a fresh fracture line across a clear ice block, tiny ice chips "
     "scattered, sharp crystalline edges, cold side light, brittle and bright"),
    ("c4-s03", "ch04", "坚硬的错觉", "一整面冰壁像岩石一样矗立,纹理粗粝",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A towering glacier ice wall standing like rock, rough weathered surface, vertical fracture "
     "lines, deep blue shadows, scale and apparent solidity"),
    ("c4-s04", "ch04", "答案藏在时间里", "厚冰层在长久压力下的流纹,像被慢慢推弯",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Thick glacier ice with gentle flow bands bending around a buried ridge, pressure made "
     "visible in slow curves, blue-grey translucency, soft light"),
    ("c4-s05", "ch04", "冰晶的微小形变", "冰晶微距:晶粒被拉长,边界模糊,像缓慢流动的糖浆",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Macro of glacier ice crystals elongated and blurred at their boundaries under pressure, "
     "translucent grains sliding past each other, cold blue-white palette"),
    ("c4-s06", "ch04", "内部变形", "冰体内部横截面,晶体排列方向被剪切改变",
     "image_camera_motion", "P2", "2x2_tile", None,
     "Cross-section of dense glacier ice where crystal alignments bend in a shear direction, "
     "fine foliation, subtle color bands, no diagram no lines, natural texture only"),
    ("c4-s07", "ch04", "底部滑动", "冰川底部与湿润岩石接触,一层极薄融水反光",
     "image_camera_motion", "P2", "2x2_tile", None,
     "The base of a glacier where blue ice meets wet bedrock, a thin film of meltwater shining "
     "between them, dark stone and clear ice in contact, cold low light"),
    ("c4-s08", "ch04", "柔软的沉积物", "冰下的砂砾层被压出流动的褶皱",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Subglacial gravel and sand squeezed into soft flow folds beneath blue ice, wet dark grains, "
     "fine sediment layers, cold shadow, geological softness"),
    ("c4-s09", "ch04", "冻结在岩石上", "寒冷冰川底部与岩石冻在一起,几乎无缝",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Very cold glacier ice frozen fast to bedrock, an almost seamless bond of blue ice and dark "
     "stone, frost crystals at the contact, still and rigid"),
    ("c4-s10", "ch04", "重力牵引", "整条冰川沿山谷缓缓下倾,冰面流线指向低处",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A long glacier descending a mountain valley, flow lines in the ice pointing downhill, "
     "gravity implied by the whole landform, cold clear air"),
    ("c4-s11", "ch04", "没有水声的河", "冰川表面安静,没有水,却有河流一样的形态",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A glacier surface with river-like meanders frozen into the ice, no flowing water, silent "
     "blue-white curves, soft overcast light, a river that makes no sound"),

    # ---------------- ch05 它一天只走一点点 ----------------
    ("c5-s01", "ch05", "像山一样稳固", "冰川边缘的巨大冰壁,纹路纵横,远处山谷",
     "image_camera_motion", "P2", "2x2_tile", None,
     "The massive edge of a glacier seen from a safe distance, towering ice wall with deep "
     "vertical textures, valley below, immense and apparently motionless"),
    ("c5-s02", "ch05", "第二天还是一样", "同一处冰壁的另一种构图,光线略变",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A second quiet view of the same glacier edge under slightly different light, identical "
     "shapes, subtle shadow shift, the patience of a day"),
    ("c5-s03", "ch05", "测量标尺", "冰面上插着一根无字测量杆,周围空旷",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A plain unmarked survey stake planted in glacier ice, empty white expanse around it, fine "
     "snow drift at its base, cold diffuse light, no text no numbers"),
    ("c5-s04", "ch05", "定位仪器", "三脚架上的测量设备对准冰川,无屏幕文字",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A survey instrument on a tripod aimed across a glacier, dark metal against white ice, no "
     "screens no text, distant peaks, quiet scientific patience"),
    ("c5-s05", "ch05", "卫星的眼睛", "高空俯瞰冰川,像一条蓝白色的河",
     "image_camera_motion", "P2", "2x2_tile", None,
     "High aerial view of a glacier winding like a blue-white river between ridges, long smooth "
     "curves, cold haze, the scale of a satellite's calm gaze"),
    ("c5-s06", "ch05", "颜料线", "冰面上一条弯曲的染色线,顺着流动方向弯折",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A thin dyed line curving across a glacier surface, bent by slow flow, vivid but natural "
     "color against white ice, no text, gentle daylight"),
    ("c5-s07", "ch05", "不同的速度", "冰川中部与边缘的流线差异,横向纹理弯曲",
     "image_camera_motion", "P2", "2x2_tile", None,
     "Transverse flow lines on a glacier bending more strongly near the center than the edges, "
     "subtle speed difference written in the ice, aerial angle, cold light"),
    ("c5-s08", "ch05", "冰瀑", "陡坡上的冰瀑,冰块堆叠,流动感最强",
     "image_camera_motion", "P2", "2x2_tile", None,
     "An icefall on a steep glacier section, jumbled blue ice blocks and towers, chaotic but slow "
     "movement, deep shadows in the crevasses, cold alpine light"),
    ("c5-s09", "ch05", "慢得看不见", "固定机位的冰川一角,冰面细节,极静",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A fixed quiet corner of glacier ice, close detail of wind texture and tiny crystals, no "
     "motion visible, soft flat light, contemplative stillness"),
    ("c5-s10", "ch05", "边界在后退", "冰川末端与裸露岩石,冰缘退缩留下的新鲜岩面",
     "image_camera_motion", "P2", "2x2_tile", None,
     "The retreating edge of a glacier against freshly exposed dark rock, a clean line between "
     "ice and stone, bare ground recently uncovered, muted cold light"),
    ("c5-s11", "ch05", "向下,却变短", "冰川末端湖,冰山漂浮,远处冰舌继续向下",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A proglacial lake at the end of a glacier, small icebergs floating, the ice tongue still "
     "descending from the valley behind, blue-grey calm"),
    ("c5-s12", "ch05", "两种时间", "同一画面里静止的岩石与缓慢的冰,长曝光般的安静",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Dark stable rock in the foreground and pale glacier ice beyond, two timescales in one "
     "frame, soft long light, quiet contrast of motion and stillness"),

    # ---------------- ch06 裂缝,是冰川写在自己身上的纹路 ----------------
    ("c6-s01", "ch06", "不平整的冰面", "从高处看冰川表面,平整雪原与裂隙交错",
     "image_camera_motion", "P2", "2x2_tile", None,
     "Aerial view of a glacier surface where smooth snowfields alternate with dark crevasses, "
     "organic pattern, cold blue shadows, vast and quiet"),
    ("c6-s02", "ch06", "像地图的裂隙", "冰川裂隙网络像河流支流,细长蓝线延伸",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A network of blue crevasses branching across white ice like the tributaries of a map, fine "
     "lines receding into the distance, high viewpoint, cold clear air"),
    ("c6-s03", "ch06", "为什么裂开", "坡度突变处的横向裂隙,冰体被拉扯",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Transverse crevasses opening where the glacier steepens, ice stretched across the slope, "
     "sharp blue walls, tension visible in the shapes"),
    ("c6-s04", "ch06", "绕过硬岩", "冰川绕着一块黑色岩石障碍,两侧裂隙张开",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A glacier flowing around a dark bedrock obstacle, crevasses opening on both sides of the "
     "rock, blue ice bending around black stone, cold light"),
    ("c6-s05", "ch06", "裂口深处", "单条裂隙的近景,内部深蓝,底部看不见",
     "image_camera_motion", "P1", "single", "关键特写",
     "Close view into one deep glacier crevasse, walls of clear blue ice descending into darkness, "
     "faint frost on the edges, no bottom visible, quiet danger"),
    ("c6-s06", "ch06", "雪桥", "一层薄雪盖住裂隙,表面看不出危险",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A thin snow bridge spanning a crevasse, the surface almost smooth and innocent, a faint "
     "depression showing the void beneath, soft flat light"),
    ("c6-s07", "ch06", "弯曲的裂缝", "弧形裂隙群,像巨大的笔画在冰面展开",
     "image_camera_motion", "P2", "2x2_tile", None,
     "Curving arc-shaped crevasses spreading across a glacier like giant brush strokes, rhythmic "
     "pattern, blue shadows, high aerial view"),
    ("c6-s08", "ch06", "冰脊与阳光", "远处阳光照在冰脊上,裂隙内部是更深的蓝",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Sunlight touching the raised ice ridges while the crevasses between them stay deep blue, "
     "strong but soft tonal contrast, cold clean air"),
    ("c6-s09", "ch06", "无人读懂的文字", "整片裂隙纹理,像一页写满字的冰面,但没有一个字",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A vast field of crevasses and ridges resembling lines of writing on white paper, no actual "
     "letters or symbols, natural abstract texture, aerial view"),
    ("c6-s10", "ch06", "冰川留下的证据", "裂隙边缘的冰层断面,层理清晰",
     "image_camera_motion", "P1", "2x2_tile", None,
     "The layered cross-section exposed along a crevasse edge, annual bands and bubble-rich ice, "
     "fine detail, cold side light, evidence written in the ice"),
    ("c6-s11", "ch06", "远远地看", "安全距离外的冰川全景,裂隙像细纹",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A distant safe view of the whole glacier, crevasses reduced to fine lines on a white body, "
     "mountain scale, calm and untouchable"),
    ("c6-s12", "ch06", "文字之外", "视线拉远,冰川、山谷、湖泊同框",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A wide view pulling back from the glacier to include valley walls and a small lake below, "
     "the ice only one part of the landscape, cold hazy light"),

    # ---------------- ch07 一条河,怎样把 V 形山谷变成 U 形 ----------------
    ("c7-s01", "ch07", "山间溪流", "普通山溪在 V 形谷底流淌,两侧山坡向中间收拢",
     "image_camera_motion", "P2", "2x2_tile", None,
     "An ordinary mountain stream running along a V-shaped valley floor, slopes closing in on "
     "both sides, clear water over stones, green-grey alpine light"),
    ("c7-s02", "ch07", "水切开岩石", "溪水冲刷岩层,水花与湿石",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Clear stream water cutting across layered rock, small rapids and wet stone, fine spray, "
     "afternoon alpine light, patient erosion"),
    ("c7-s03", "ch07", "谷地被冰雪填满", "同一山谷被厚雪覆盖,只露出黑色山脊",
     "image_camera_motion", "P2", "2x2_tile", None,
     "The same kind of valley filled with deep snow and ice, only dark ridges emerging, the V "
     "hidden beneath a white mass, cold overcast light"),
    ("c7-s04", "ch07", "冰不是一条水线", "厚冰体充满谷底,接触并挤压两侧谷壁",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A thick glacier filling a valley from wall to wall, ice pressing against both sides, "
     "abrasion marks high on the rock, massive and slow"),
    ("c7-s05", "ch07", "冰与岩石的较量", "冰川底部,冰里夹着碎屑,贴着岩石磨蚀",
     "image_camera_motion", "P1", "2x2_tile", None,
     "The grinding contact at a glacier base, debris-laden ice dragging over bedrock, wet rock "
     "surface, fine rock flour in the melt film, dark cold detail"),
    ("c7-s06", "ch07", "擦痕", "基岩表面细长平行的冰川擦痕,像被刻过",
     "image_camera_motion", "P1", "single", "精密结构",
     "Bedrock surface scored with long parallel glacial striations, fine grooves catching low "
     "light, polished stone, no text, natural geological detail"),
    ("c7-s07", "ch07", "岩石被带走", "冰面上散落的岩块,棱角被磨圆",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Rounded rock fragments resting on glacier ice, corners worn smooth, dark stone against "
     "white, cold side light, cargo in transit"),
    ("c7-s08", "ch07", "U 形谷", "宽阔的 U 形谷,谷底平缓,两侧陡壁",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A broad U-shaped glacial valley, flat wide floor and steep walls, soft green and grey "
     "tones, a small river threading the middle, calm aerial view"),
    ("c7-s09", "ch07", "悬谷瀑布", "支谷高出主谷,水从崖口落下成瀑布",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A hanging valley ending in a tall waterfall dropping into the main trough, thin white water "
     "against dark rock, mist at the base, cold daylight"),
    ("c7-s10", "ch07", "峡湾", "狭长深邃的峡湾,两侧陡壁入水",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A narrow deep fjord between steep rock walls, dark calm water reflecting the cliffs, low "
     "cloud, blue-grey northern light"),
    ("c7-s11", "ch07", "绿色的谷底", "从空中看没有冰川的 U 形谷,草地与小河",
     "image_camera_motion", "P2", "2x2_tile", None,
     "Aerial view of a green U-shaped valley without ice, meadow on the wide floor, a small river "
     "winding through, steep walls rising on both sides, soft evening light"),
    ("c7-s12", "ch07", "早已离去的冰河", "谷壁上的冰川遗迹与远处的雪山,暗示来路",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Glacial marks on a valley wall with distant snow peaks beyond, polished rock and moraine "
     "patches, the memory of ice in the landscape, muted light"),

    # ---------------- ch08 一块石头,如何走完一生中最漫长的旅行 ----------------
    ("c8-s01", "ch08", "山壁崩落", "岩壁上一块新鲜崩落的岩块,尘屑未散",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A fresh rockfall scar on a high cliff, broken stone and dust on the slope below, sharp "
     "fracture faces, cold mountain light"),
    ("c8-s02", "ch08", "落在冰川上", "一块深色岩石落在白色冰面,周围有撞击碎屑",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A dark boulder resting on white glacier ice, impact debris scattered around it, stark "
     "contrast, cold soft light, a traveler arrived"),
    ("c8-s03", "ch08", "冰里的石头", "冰体内部包裹的碎石,半透明冰中露出暗色棱角",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Rock fragments embedded inside translucent blue glacier ice, dark angular shapes suspended, "
     "bubbles around them, cold internal light"),
    ("c8-s04", "ch08", "两条冰川汇合", "两条冰流在远处汇合,中间夹着深色岩屑带",
     "image_camera_motion", "P2", "2x2_tile", None,
     "Two glacier streams converging in the distance, a dark debris stripe forming between them, "
     "blue-white ice and black rock, high viewpoint"),
    ("c8-s05", "ch08", "冰碛条纹", "白色冰面上一条长长的灰黑色冰碛带,像画上去的线",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A long grey-black medial moraine running down the middle of a white glacier, like a drawn "
     "line, rock debris on ice, cold clear light"),
    ("c8-s06", "ch08", "侧碛", "冰川边缘隆起的深色侧碛垄,碎石堆叠",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A raised lateral moraine ridge along the glacier edge, stacked angular debris, dark against "
     "pale ice, sharp shadows, cold afternoon"),
    ("c8-s07", "ch08", "石头留在陌生地方", "冰川退去后,草地上孤零零一块巨石",
     "image_camera_motion", "P2", "single", "母题定装镜",
     "A single large glacial erratic boulder alone on a green meadow, no other rocks nearby, soft "
     "evening light, quiet and improbable"),
    ("c8-s08", "ch08", "冰川漂砾", "巨石表面覆着地衣,纹理与周围山岩不同",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Close view of a glacial erratic boulder covered in pale lichen, its rock texture unlike the "
     "surrounding ground, fine detail, low warm-grey light"),
    ("c8-s09", "ch08", "坐在石头旁", "巨石旁一片被坐过的草地,远处山影(无人)",
     "image_camera_motion", "P1", "2x2_tile", None,
     "The sheltered grassy patch beside the boulder, faint flattening of grass, distant mountain "
     "shadow, no person, quiet human absence, dusk light"),
    ("c8-s10", "ch08", "岩粉", "冰川融水里的灰白色细粉,水呈乳白",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Glacial meltwater carrying fine grey-white rock flour, milky opaque water, tiny suspended "
     "particles catching light, close detail"),
    ("c8-s11", "ch08", "乳白的湖", "冰川湖,水色乳白偏蓝绿,远处冰舌",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A glacier lake with milky turquoise water, distant ice tongue feeding it, soft overcast "
     "light, calm opaque surface"),
    ("c8-s12", "ch08", "大小的证据", "从巨大漂砾到细小砂粒的过渡,同一片冰碛地",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A moraine field showing the range from large boulders to fine gravel and sand, one continuous "
     "debris sheet, cold low light, evidence of a slow journey"),
    ("c8-s13", "ch08", "比一生更远", "漂砾与远山同框,尺度对比,安静收束",
     "image_camera_motion", "P2", "2x2_tile", None,
     "The lone erratic boulder in the foreground with distant snow mountains behind, vast scale, "
     "soft dusk, a journey longer than a life"),

    # ---------------- ch09 冰河的身体里,也藏着真正的流水 ----------------
    ("c9-s01", "ch09", "夏天的冰川", "夏日冰川表面,局部融化,细小水流出现",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A glacier surface in summer, patches of melting snow, thin streams starting to run over the "
     "ice, bright soft daylight, blue and white"),
    ("c9-s02", "ch09", "冰面溪流", "细流沿冰面浅槽汇合,水清见底",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Clear meltwater streams joining in shallow channels cut into glacier ice, transparent water "
     "over blue ice, fine ripples, daylight"),
    ("c9-s03", "ch09", "冰川锅穴", "冰面上一个圆形深洞,融水旋转流入",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A round moulin hole in glacier ice, meltwater spiraling down into darkness, smooth blue "
     "walls, cold light from above"),
    ("c9-s04", "ch09", "冰内通道", "冰洞内部的水道,蓝光,水声仿佛可见",
     "image_camera_motion", "P1", "2x2_tile", None,
     "An internal meltwater channel inside a glacier cave, blue translucent walls, dark water "
     "running through, soft light from the entrance"),
    ("c9-s05", "ch09", "冰川之门", "冰川前缘的冰洞口,浑浊溪水流出",
     "image_camera_motion", "P2", "2x2_tile", None,
     "The portal at a glacier's edge where a silty stream flows out from under the ice, dark ice "
     "arch, milky water, cold overcast light"),
    ("c9-s06", "ch09", "浑浊的溪", "冰川前缘溪流,水色灰白,携带岩粉",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A silty grey-white stream leaving the glacier, fine suspended sediment, smooth opaque water, "
     "stones at the banks, soft daylight"),
    ("c9-s07", "ch09", "奔向山谷", "溪流穿过砾石谷地,汇入更大的河",
     "image_camera_motion", "P2", "2x2_tile", None,
     "The milky stream running through a gravel outwash plain toward a larger river, braided "
     "channels, distant valley, cool light"),
    ("c9-s08", "ch09", "冰湖的颜色", "乳蓝绿色的冰川湖,岸边浅滩",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A milky blue-green glacier lake with a pale shallow shore, opaque water, soft reflections, "
     "cold calm"),
    ("c9-s09", "ch09", "储存与释放", "雪层下的冰体与流出的水,同框",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Thick snow and ice above, a clear stream leaving from beneath it, storage and release in one "
     "frame, cold blue and white"),
    ("c9-s10", "ch09", "慢与快", "静止的冰壁与快速流动的水,一静一动",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A still blue ice wall beside fast-moving meltwater, motion and stillness side by side, fine "
     "spray, soft cool light"),
    ("c9-s11", "ch09", "下游的河", "冰川水汇入宽阔河谷,远处湿地",
     "image_camera_motion", "P2", "2x2_tile", None,
     "Glacier meltwater joining a broad valley river, wetlands in the distance, milky water mixing "
     "with clearer water, wide calm view"),
    ("c9-s12", "ch09", "水声", "溪流近景,水花与石头,声音感强",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Close view of the milky stream over stones, small ripples and soft spray, the visual texture "
     "of water sound, cool daylight"),
    ("c9-s13", "ch09", "安静的脚步", "回到冰川本体,表面无流水,只有冰",
     "image_camera_motion", "P2", "2x2_tile", None,
     "The glacier body itself, no visible running water, only quiet blue-white ice and wind "
     "texture, soft light, silent footsteps"),

    # ---------------- ch10 一条冰河,最后会走向哪里 ----------------
    ("c10-s01", "ch10", "冰川末端", "山谷冰川末端,冰体变薄,融水成溪",
     "image_camera_motion", "P2", "2x2_tile", None,
     "The end of a valley glacier where the ice thins and becomes a stream, gentle terminus, "
     "grey moraine, cold overcast light"),
    ("c10-s02", "ch10", "止于湖边", "冰川直接伸入高山湖,冰崖临水",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A glacier terminating directly in a high mountain lake, blue ice cliff meeting still water, "
     "small floating ice, soft light"),
    ("c10-s03", "ch10", "伸向海边", "海洋终止型冰川,冰崖临海,远处冰山",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A tidewater glacier reaching the sea, tall blue ice cliff above dark water, distant icebergs, "
     "cold coastal light"),
    ("c10-s04", "ch10", "冰崩", "冰崖上一块冰正在断裂坠落,水花溅起",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A block of ice breaking away from a glacier cliff and falling toward the sea, splash and "
     "spray below, raw natural force, cold light"),
    ("c10-s05", "ch10", "漂浮的冰山", "海面上漂浮的冰山,水面下隐约可见体积",
     "image_camera_motion", "P2", "2x2_tile", None,
     "An iceberg floating on calm polar sea, pale blue above and a faint submerged mass below the "
     "surface, soft overcast light, quiet scale"),
    ("c10-s06", "ch10", "冰崖细节", "冰崖近景,层理与蓝色深浅",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Close view of a tidewater ice cliff, layered blue ice, vertical fracture lines, wet dark "
     "band at the waterline, cold detail"),
    ("c10-s07", "ch10", "峡湾里的冰山", "峡湾水面,几座冰山散布,山壁倒影",
     "image_camera_motion", "P2", "2x2_tile", None,
     "Several icebergs scattered across a fjord, steep walls and soft reflections, low cloud, "
     "blue-grey northern calm"),
    ("c10-s08", "ch10", "泥沙羽流", "冰川融水入海,灰白色泥沙在水下扩散",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A pale sediment plume spreading from a glacier outlet into darker sea water, milky swirls "
     "below the surface, aerial view, cold light"),
    ("c10-s09", "ch10", "浮冰与陆地冰", "海面浮冰与小冰山,远处陆地冰川",
     "image_camera_motion", "P2", "2x2_tile", None,
     "Sea ice and small bergs floating in front of a distant land glacier, the difference between "
     "floating and land ice visible in the scene, cold calm"),
    ("c10-s10", "ch10", "水的循环", "冰川融水汇入大海,海面广阔",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Glacier meltwater meeting the open sea, wide horizon, pale water and grey sky, the long "
     "journey ending in the ocean, soft dusk"),
    ("c10-s11", "ch10", "黄昏的末端", "黄昏的冰川末端,水面反光,安静",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A glacier terminus at dusk, still water reflecting the last pale light, ice and rock in "
     "muted blue, very quiet"),
    ("c10-s12", "ch10", "不是终点", "冰川、河流、湖泊、海洋连成一线,远景",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A wide view connecting glacier, river, lake and distant sea in one line, the water cycle "
     "made landscape, cold hazy light"),

    # ---------------- ch11 冰里藏着一封来自古老天空的信 ----------------
    ("c11-s01", "ch11", "格陵兰冰盖", "广袤的白色冰盖,几乎无边界,极简",
     "image_camera_motion", "P2", "2x2_tile", None,
     "The vast Greenland ice sheet stretching to a featureless horizon, subtle wind texture, pale "
     "blue shadows, immense and empty"),
    ("c11-s02", "ch11", "南极冰盖", "南极冰盖边缘,蓝色冰崖与白色高原",
     "image_camera_motion", "P2", "2x2_tile", None,
     "The edge of the Antarctic ice sheet, blue ice cliffs below a white plateau, cold clear air, "
     "austere scale"),
    ("c11-s03", "ch11", "雪一层层压下", "冰盖表层雪层剖面,细密层理",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A shallow snow pit on an ice sheet showing fine annual layers, compacted snow, subtle "
     "tonal bands, cold flat light"),
    ("c11-s04", "ch11", "钻取冰芯", "冰芯钻机与细长冰柱,无人,设备简洁",
     "image_camera_motion", "P1", "2x2_tile", None,
     "An ice-core drilling setup on a vast ice sheet, a long thin ice core being raised, simple "
     "metal equipment, no people, cold overcast light"),
    ("c11-s05", "ch11", "一根冰芯", "冰芯横放在深色布上,透明,细长",
     "image_camera_motion", "P2", "single", "母题定装镜",
     "A single long ice core resting on dark cloth, clear translucent ice with faint layers, "
     "delicate and precious, soft cold light, museum stillness"),
    ("c11-s06", "ch11", "气泡", "冰芯内部微距:一串被封住的空气泡",
     "image_camera_motion", "P1", "single", "关键特写",
     "Macro inside an ice core: tiny air bubbles sealed in clear ancient ice, backlit so they glow "
     "pale, faint layer boundaries, precise and quiet"),
    ("c11-s07", "ch11", "尘埃与火山灰", "冰芯里的暗色薄层,细颗粒",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Dark dust and volcanic ash bands inside a clear ice core, fine particulate layers, subtle "
     "color, cold side light, a record of ancient air"),
    ("c11-s08", "ch11", "实验室", "冷光实验室里的冰芯段,金属台面,无文字",
     "image_camera_motion", "P2", "2x2_tile", None,
     "Sections of ice core laid out on a cold metal laboratory bench, blue-white light, clean "
     "surfaces, no labels no text, scientific care"),
    ("c11-s09", "ch11", "同位素", "冰样在玻璃器皿中的细节,冷光折射",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Small ice samples in clear glass vessels under cool light, refraction and pale blue "
     "reflections, precise laboratory stillness, no text"),
    ("c11-s10", "ch11", "古老天空", "冰芯薄片透光,内部纹理像云层",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A thin section of ice core lit from behind, internal textures resembling ancient cloud "
     "layers, pale blue glow, abstract and quiet"),
    ("c11-s11", "ch11", "不是魔法", "冰芯与手套、工具的静物,真实工作痕迹(无人)",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Ice core sections beside insulated gloves and simple tools on a cold bench, real working "
     "traces, no people, no text, muted blue light"),
    ("c11-s12", "ch11", "一小段冰", "冰芯端面特写,年轮般的层理",
     "image_camera_motion", "P1", "2x2_tile", None,
     "The end face of an ice core showing annual layers like rings, fine bubbles and dust, cold "
     "light, the whole sky in a small cylinder"),
    ("c11-s13", "ch11", "风停了", "冰盖上的雪面,风纹静止,极简",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A quiet snow surface on the ice sheet, wind ripples frozen in place, no wind visible, pale "
     "blue shadow, immense stillness"),

    # ---------------- ch12 冰川还在前进,它的边缘却正在后退 ----------------
    ("c12-s01", "ch12", "回到山谷", "回到开篇的冰川山谷,全景,安静",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A return to the opening glacier valley, wide calm view, snow and blue ice between dark "
     "peaks, the same quiet composition"),
    ("c12-s02", "ch12", "新雪", "冰川表面新落的雪,细纹被覆盖",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Fresh snow on the glacier surface covering the old wind texture, soft new layer, pale and "
     "even, cold diffuse light"),
    ("c12-s03", "ch12", "边缘的岩石", "冰川边缘新露出的岩石,潮湿,无冰",
     "image_camera_motion", "P2", "2x2_tile", None,
     "Freshly exposed bedrock at a glacier edge, wet dark stone, clean ice boundary, bare ground "
     "recently uncovered, muted light"),
    ("c12-s04", "ch12", "变薄的冰", "冰川末端变薄,冰体低矮,裂缝增多",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A thinning glacier terminus, low ice body, more crevasses and exposed rock, fragile edge, "
     "cold overcast light"),
    ("c12-s05", "ch12", "新的湖", "冰川退去后形成的年轻湖泊,水色灰蓝",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A young lake formed behind a retreating glacier, grey-blue water, fresh moraine shores, "
     "soft light, a new landscape"),
    ("c12-s06", "ch12", "冰碛垄", "冰川退去留下的弧形冰碛垄,像年轮",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Curved moraine ridges left by a retreating glacier, arcs of debris like growth rings, dark "
     "stone on pale ground, aerial view"),
    ("c12-s07", "ch12", "山谷的变化", "同一山谷的远景,冰川比记忆中短",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A distant view of the valley where the glacier now ends higher up, bare rock in the "
     "foreground, the shape of retreat, hazy cold light"),
    ("c12-s08", "ch12", "质量平衡", "雪线附近的积雪与裸露冰,对比",
     "image_camera_motion", "P1", "2x2_tile", None,
     "The snowline on a glacier, bright accumulation snow above and bare blue ice below, a natural "
     "balance line, cold clear light"),
    ("c12-s09", "ch12", "仍然向下", "冰川中部仍在向下流动的纹理",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Flow lines in the middle of the glacier still pointing downhill, slow motion unchanged, "
     "blue-grey ice, cold light"),
    ("c12-s10", "ch12", "慢慢变短", "冰川末端与上游的对比,冰舌缩短",
     "image_camera_motion", "P2", "2x2_tile", None,
     "The glacier tongue seen from above, shorter than the valley it carved, bare ground beyond "
     "the ice, the river still flowing, muted light"),
    ("c12-s11", "ch12", "很久以前", "古冰川留下的谷地与湖盆,今日无冰",
     "image_camera_motion", "P2", "2x2_tile", None,
     "An ancient glacial valley and lake basin now free of ice, smooth U-shaped slopes, quiet "
     "water, soft evening light"),
    ("c12-s12", "ch12", "一把尺", "冰川与远山,尺度感,安静的收束",
     "image_camera_motion", "P2", "2x2_tile", None,
     "The glacier and distant peaks in one calm frame, a slow ruler across the land, cold haze, "
     "still and vast"),
    ("c12-s13", "ch12", "不会加快", "冰面细节,极静,时间感",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A still detail of glacier ice, tiny crystals and wind marks, no motion, quiet patience, "
     "pale blue light"),
    ("c12-s14", "ch12", "读懂一点", "冰面裂隙与层理,像可读的痕迹",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Crevasses and ice layers forming readable natural traces, no letters, cold clear light, "
     "the surface as a record"),

    # ---------------- 尾声 ----------------
    ("e-s01", "epilogue", "回到雪花", "夜色中一片雪花,背景虚化的雪山",
     "image_camera_motion", "P2", "single", "关键特写",
     "One snow crystal suspended in deep indigo night, soft out-of-focus snow mountains behind, "
     "delicate and quiet, the story returning to its beginning"),
    ("e-s02", "epilogue", "雪落在山坡", "雪坡近景,细雪覆盖,星光微弱",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A quiet snow slope at night with faint starlight on the surface, fine new snow, deep blue "
     "shadows, calm"),
    ("e-s03", "epilogue", "山风", "雪面被风轻轻吹起的细雪,低角度",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Fine snow drifting low across a night snowfield, soft wind texture, starlight, gentle and "
     "slow"),
    ("e-s04", "epilogue", "星光落在雪上", "星空下的雪山全景,安静,极简",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A wide night view of snow mountains under stars, deep indigo sky, pale snow glow, immense "
     "quiet"),
    ("e-s05", "epilogue", "冰河仍在走", "夜色里的冰川全景,几乎看不见移动",
     "image_camera_motion", "P2", "2x2_tile", None,
     "The glacier valley at night, ice barely visible under starlight, still and endless, quiet "
     "presence"),
    ("e-s06", "epilogue", "山不着急", "黑色山脊与雪,极简剪影",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Dark mountain ridges with snow in simple silhouette against a deep blue night sky, minimal "
     "and patient, faint stars"),
    ("e-s07", "epilogue", "雪不着急", "雪面微距,细雪颗粒,夜色",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Macro of fine snow grains at night, tiny crystals catching faint starlight, dark blue "
     "shadows, soft and quiet"),
    ("e-s08", "epilogue", "可以先睡了", "夜色中的山谷,最后一点微光,画面渐暗",
     "image_camera_motion", "P2", "2x2_tile", None,
     "The valley at the very end of night, last faint glow on snow, deep indigo darkness closing "
     "in, a place to rest"),
]


def main():
    old = json.loads(OLD.read_text(encoding="utf-8"))
    utt = json.loads(UTT.read_text(encoding="utf-8"))
    chars = {}
    for u in utt["utterances"]:
        chars[u["paragraph_id"]] = chars.get(u["paragraph_id"], 0) + len(u["text"])
    sec_paras = {}
    for pid in utt["paragraph_order"]:
        sec = pid.rsplit("-", 1)[0]
        sec_paras.setdefault(sec, []).append(pid)

    # 1. 预览版 ch01/ch02 镜头原样保留
    rows = []
    for s in old["shots"]:
        if s["section"] in ("ch01", "ch02"):
            rows.append({
                "id": s["id"], "section": s["section"], "beat": s["beat"],
                "scene": s["scene"], "cls": s["shot_class"], "strategy": s["strategy"],
                "mode": s["image_mode"], "cat": s.get("single_category"),
                "prompt": s["image_prompt"],
            })
    # 2. 新章节
    for r in NEW_ROWS:
        sid, sec, beat, scene, cls, strat, mode, cat, core = r
        rows.append({
            "id": sid, "section": sec, "beat": beat, "scene": scene, "cls": cls,
            "strategy": strat, "mode": mode, "cat": cat,
            "prompt": STYLE + PALETTE[sec] + ". " + core + ". " + BAN,
        })

    # 3. 段落分配：每章按镜头顺序、按段落字数分位点均匀落位
    by_sec = {}
    for r in rows:
        by_sec.setdefault(r["section"], []).append(r)
    shots = []
    for sec in ["ch01", "ch02", "ch03", "ch04", "ch05", "ch06", "ch07", "ch08",
                "ch09", "ch10", "ch11", "ch12", "epilogue"]:
        rs = by_sec.get(sec, [])
        plist = sec_paras.get(sec, [])
        if not plist:
            raise SystemExit("no paragraphs for " + sec)
        total = sum(chars.get(p, 30) for p in plist)
        cum = []
        acc = 0
        for p in plist:
            acc += chars.get(p, 30)
            cum.append(acc / total)
        n = len(rs)
        for i, r in enumerate(rs):
            q = (i + 0.5) / n
            idx = min(len(plist) - 1, max(0, next((j for j, c in enumerate(cum) if q <= c), len(plist) - 1)))
            pid = plist[idx]
            est = max(3.0, chars.get(pid, 30) / CPS)
            shots.append({
                "id": r["id"], "paragraph_id": pid, "section": sec, "beat": r["beat"],
                "scene": r["scene"],
                "est_seconds": round(est, 1),
                "status": "planned_full_v1",
                "timing": {"mode": "planned_estimate", "note": "字数估算;TTS 后由 timeline.json 实测回填"},
                "shot_class": r["cls"], "strategy": r["strategy"], "image_mode": r["mode"],
                "image_prompt": r["prompt"],
                **({"single_category": r["cat"]} if r["mode"] == "single" else {}),
            })

    singles = sum(1 for s in shots if s["image_mode"] == "single")
    tiles = len(shots) - singles
    calls = singles + (tiles + 3) // 4
    doc = {
        "schema_version": 1, "episode": "glacier-river", "scope": "full_episode",
        "basis": "story/NARRATION_MASTER.md 全片 v1.0(7951字)",
        "created_at": "2026-11-03", "updated_at": "2026-11-03",
        "fps": 30, "width": 1920, "height": 1080, "cps_final": CPS,
        "intra_gap_s": 0.19, "para_gap_s": 0.4245, "chap_gap_s": 0.7547,
        "counts": {"total": len(shots), "single": singles, "2x2_tile": tiles,
                   "image_to_video": 0,
                   "by_section": {sec: sum(1 for s in shots if s["section"] == sec)
                                  for sec in ["ch01", "ch02", "ch03", "ch04", "ch05", "ch06",
                                              "ch07", "ch08", "ch09", "ch10", "ch11", "ch12",
                                              "epilogue"]}},
        "api_budget": {"est_calls": calls, "note": "全集 single + ⌈tile/4⌉；ch01/ch02 的 26 镜已生成"},
        "notes": ("全片一次成型。视觉弧：星夜雪山→雪晶→雪层→蓝冰→冰川流动→裂隙→U 形谷→冰碛石→"
                  "融水→末端冰山→冰芯→后退→回到雪夜。零图表/零文字/零人物；全部 P1/P2 单向运镜。"
                  "ch01/ch02 沿用已验收的 26 张，不重生成。"),
        "shots": shots,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"shots={len(shots)} singles={singles} tiles={tiles} est_calls={calls}")
    print("by section:", doc["counts"]["by_section"])


if __name__ == "__main__":
    main()
