# -*- coding: utf-8 -*-
"""Build mariana-descent SHOT_PLAN v1 (pilot: ch01-ch03 detailed; ch04-ch10 skeleton counts).

2026-10-19。用户授权自主推进。依据 OUTLINE v1(十章重构版)+ 锁定口播 v1.1。
2x2 规则(rules/shared/image-grid-generation.md 2026-10-19 修订):
- image_mode 默认 2x2_tile;single 仅四类例外且逐镜注明类别(本批:母题定装/精密结构/关键特写推近)。
- API 预算写头部,批次后报账。风格头/禁项统一注入,逐镜 prompt 独立完整。
"""
from __future__ import annotations
import hashlib, json, re
from datetime import datetime
from pathlib import Path

EP = Path(__file__).resolve().parents[3]
UTT = EP / "audio" / "utterances.json"
OUT = EP / "visual" / "SHOT_PLAN.json"
PROMPTS_MD = EP / "visual" / "ALL_SHOT_PROMPTS.md"
SRC = EP / "story" / "NARRATION_MASTER.md"
CPS = 3.5
GAPS = dict(head=0.3774, unit=0.19, para=0.4245, chap=0.7547)

STYLE = ("Cinematic deep-sea documentary still, photorealistic, volumetric light, layered depth, "
         "fine material detail, asymmetrical cinematic composition, subtle surrealism, calm and slow mood. ")
BAN = ("No text, no letters, no numbers, no labels, no watermark, no charts, no graphs, no UI elements, "
       "no borders, no split screen, no collage. ")

PALETTE = {
    "ch01": "Moonlit teal-blue ocean surface at night with silver highlights; historical amber lantern warmth for 1870s ship scenes",
    "ch02": "Bright transparent blue water fading downward into deep cobalt; last warm tones vanishing with depth",
    "ch03": "Deep indigo water turning near-black; scattered bioluminescent green and blue points like underwater stars",
    "ch04": "Dusk cobalt water around five hundred metres, faint blue remaining above, whale bodies in grey-blue, warm interior lights of habitats and submarines like isolated islands",
    "ch05": "Near-black midnight water below one thousand metres, cold four-degree clarity, white marine snow drifting, only faint blue-grey gradients",
    "ch06": "Absolute black water over a volcanic seafloor, white crab clusters and pale-orange tube worm colonies as the only warm colour, shimmering vent water",
    "ch07": "Dim blue-grey abyssal light, rust-amber tones of ship steel and whale bones, soft sediment beige under lamp light",
    "ch08": "Blue-grey trench wall in near darkness, translucent pinkish snailfish glow, pale sediment slopes",
    "ch09": "Absolute darkness with a single warm white headlight cone, flour-soft pale silt, ghostly pale deep-sea life at the lamp edge",
    "ch10": "Reverse gradient climbing from black back up to moonlit teal-blue, growing silver-blue light, ending at a bright moonlit surface",
    "epilogue": "Calm moonlit night sea closing the journey, deep teal and silver, gentle darkness below",
    "bridge": "Calm dusk-to-night sea horizon in teal-blue, a vertical slice of ocean from bright surface into dark depth",
}

# (id, section, beat, scene_zh, class, strategy, mode, single_category, prompt_core_en)
ROWS = [
    # ---- bridge 故事由来(4,2026-10-22 补:原计划漏配桥段镜头) ----
    ("brg-s01", "bridge", "说好三件事", "稳定夜海平线,初星,青蓝基调,平缓涌", "image_camera_motion", "P2", "2x2_tile", None,
     "A calm night sea horizon under deep teal-blue sky, first stars appearing, long gentle swells rolling toward the viewer, steady and honest atmosphere like a promise"),
    ("brg-s02", "bridge", "假想的下潜", "垂直剖面:亮水面渐入深蓝再到暗", "image_camera_motion", "P1", "2x2_tile", None,
     "A vertical slice of the ocean seen from the side: bright sunlit surface at the top fading through cobalt into darkness below, one continuous water column, an imagined descent preview"),
    ("brg-s03", "bridge", "真实的历史", "昏暗深处微光,海雪稀疏,沉静", "image_camera_motion", "P1", "2x2_tile", None,
     "Dim deep water with sparse drifting marine snow and a faint distant glow, quiet and still, the feeling of real places reached by only a few"),
    ("brg-s04", "bridge", "记住此刻的蓝", "亮蓝透光层从下仰视水面,光柱洒落", "image_camera_motion", "P1", "2x2_tile", None,
     "Looking up from inside bright transparent blue water at the rippling surface, sun rays slanting down in soft columns, the vivid blue to remember before the long dark"),

    # ---- ch01 海面之夜·用麻绳量出来的深渊(11) ----
    ("c1-s01", "ch01", "月海定场", "夜海面,月光铺出一条碎银,涌浪均匀,远景无岸", "image_camera_motion", "P2", "single", "母题定装镜",
     "Wide establishing shot of a calm night ocean under a full moon, a long broken path of silver moonlight stretching toward the horizon, gentle even swells, deep teal-black water, no land in sight"),
    ("c1-s02", "ch01", "挑战者号出航", "1870s 三桅科考帆船在开阔海面,帆与蒸汽烟囱并存,黄昏", "image_camera_motion", "P1", "2x2_tile", None,
     "A 1870s three-masted corvette research ship under sail with a small steam funnel, on open ocean at amber dusk, cream sails taut, wooden deck busy with ropes and barrels, seen from low off the bow quarter"),
    ("c1-s03", "ch01", "放绳测深", "甲板上水手与学者用木质绞盘把麻绳铅锤放入海中,绳盘整齐", "image_camera_motion", "P1", "2x2_tile", None,
     "On the wooden deck of a 1870s sailing research ship, sailors and a naturalist lower a lead weight on a thick hemp line into the sea, a large coiled rope pile and a hand-turned wooden winch beside them, dawn haze"),
    ("c1-s04", "ch01", "铅锤垂入深蓝", "麻绳与铅锤没入深蓝水面,涟漪一圈圈扩散", "image_camera_motion", "P2", "2x2_tile", None,
     "Close view of a heavy lead sounding weight on a taut hemp rope disappearing into deep blue water, spreading circular ripples catching soft light, dark sea beyond"),
    ("c1-s05", "ch01", "舱内记录", "油灯下的记录本、六分仪与标本瓶,学者的手正在书写", "image_camera_motion", "P1", "2x2_tile", None,
     "Inside a 1870s ship cabin at night, an oil lantern lighting an open leather logbook, a brass sextant, glass specimen jars with dark liquid, a scholar's hand writing with a fountain pen, warm amber pool of light in shadowed wood interior"),
    ("c1-s06", "ch01", "回到今晚·夜海", "现代夜海面,月光,远处涌浪发亮", "image_camera_motion", "P2", "2x2_tile", None,
     "A calm modern night seascape, moonlight glinting on low swells, faint mist above the water, deep quiet atmosphere"),
    ("c1-s07", "ch01", "下潜器入水", "白色科研深潜器从支援船甲板滑入海中,溅起发亮的水花", "image_to_video", "V1", "single", "精密结构",
     "A compact white deep-sea research submersible with thick portholes and external lights sliding off a support ship stern into dark water, a bright splash of glowing droplets, night scene"),
    ("c1-s08", "ch01", "舱内关闭", "舱内视角,舱门关闭,仪表微光亮起,水面在舷窗外", "image_camera_motion", "P2", "2x2_tile", None,
     "Interior of a deep-sea submersible cabin seen from behind two empty seats, hatch closing, soft instrument glow in blue darkness, water light patterns moving across metal walls through the thick viewport"),
    ("c1-s09", "ch01", "气泡向上", "第一串气泡从壳体边缘滑出,摇摇晃晃升向月光", "image_to_video", "V1", "2x2_tile", None,
     "A trail of silver air bubbles rising from the edge of a submersible hull toward a moonlit surface far above, wobbling and merging, dark blue water columns of light"),
    ("c1-s10", "ch01", "海面合拢", "从水下仰视,海面在头顶合拢,月光透过水面成网状光斑", "image_to_video", "V1", "2x2_tile", None,
     "Looking straight up from underwater as the surface seals overhead, moonlight filtering through the rippling surface into a net of bright wobbling patterns, bubbles drifting upward past the lens"),
    ("c1-s11", "ch01", "开始下坠", "深潜器全貌悬停在微光层,缓缓下坠,上方光斑渐远", "image_to_video", "V3", "2x2_tile", None,
     "Full side view of a small white submersible hanging in dim blue open water beginning its descent, fading surface glow above, particles drifting down around it, sense of vast vertical space"),

    # ---- ch02 血是绿色的(13) ----
    ("c2-s01", "ch02", "亮蓝水柱", "浅层透明亮蓝,阳光光柱斜插,悬浮微粒缓慢漂", "image_camera_motion", "P1", "2x2_tile", None,
     "Clear sunlit upper ocean, slanted shafts of sunlight penetrating bright transparent blue water, tiny particles drifting, weightless serenity"),
    ("c2-s02", "ch02", "红色还在", "十几米内,红衣潜水员剪影,红色仍然鲜明", "image_camera_motion", "P1", "2x2_tile", None,
     "A freediver in a bright red wetsuit gliding in vivid blue water near the surface, the red fabric still saturated and warm-toned, sunbeams behind"),
    ("c2-s03", "ch02", "红色褪去", "更深几十米,同一红衣剪影,红色变成暗绿灰", "image_camera_motion", "P1", "2x2_tile", None,
     "The same red-suited freediver now deeper in cobalt water, the suit reading as muted dark green-grey, cool monochrome-blue ambience, faint surface glow far above"),
    ("c2-s04", "ch02", "颜色交出领地", "水体渐变:上方残暖,下方全冷蓝", "image_camera_motion", "P2", "2x2_tile", None,
     "A vertical gradient of open ocean water, faint warm tones dissolving into pure cold blue as the eye travels down, drifting motes, no visible bottom"),
    ("c2-s05", "ch02", "透光层的富饶", "珊瑚礁浅景,鱼群穿行,光柱与鱼影交错", "image_camera_motion", "P1", "2x2_tile", None,
     "A lively shallow coral reef scene, schools of small fish weaving between coral heads, crisscrossing sunbeams and fish shadows, turquoise clarity"),
    ("c2-s06", "ch02", "珊瑚产卵之夜", "夜晚珊瑚同步释放粉色卵云,像反向的雪上升", "image_to_video", "V1", "single", "关键特写推近",
     "Night coral spawning, dozens of coral branches releasing soft pink pearl-like egg clouds that drift slowly upward like inverted snow, dark blue background, dreamlike glow"),
    ("c2-s07", "ch02", "一口气的人", "自由潜水者收拢身体垂直下坠,单串气泡", "image_to_video", "V3", "2x2_tile", None,
     "A freediver in a dark wetsuit folding into a vertical head-down descent, one clean ribbon of bubbles trailing upward, relaxed face, deep blue surroundings"),
    ("c2-s08", "ch02", "身体换活法", "潜水者剪影在深蓝中变小,头顶光柱遥远", "image_camera_motion", "P2", "2x2_tile", None,
     "A tiny human silhouette descending in immense blue water, one distant shaft of light from the surface, immense negative space conveying depth"),
    ("c2-s09", "ch02", "古老的拷贝", "近景:潜水者面部放松,耳畔气泡,心跳般的宁静", "image_camera_motion", "P1", "2x2_tile", None,
     "Close portrait of a calm freediver underwater, eyes closed, thin bubbles at the lips, skin lit by soft blue ambient light, meditative stillness"),
    ("c2-s10", "ch02", "鲸的纪念碑", "一群抹香鲸垂直悬浮,头朝上尾朝下,互相靠近", "image_to_video", "V1", "2x2_tile", None,
     "A pod of sperm whales hanging vertically head-up tail-down in dark blue water, perfectly still like sunken monuments, close together, faint light from above"),
    ("c2-s11", "ch02", "鲸睡特写", "其中一头鲸的巨大头部,眼睑闭合,皮肤纹理清晰", "image_camera_motion", "P2", "single", "母题定装镜",
     "Close view of a sleeping sperm whale's huge blunt head, eye gently closed, weathered skin texture with faint scars, suspended in deep blue silence"),
    ("c2-s12", "ch02", "最后的蓝", "薄暮般最后一层蓝光,水体将黑未黑", "image_camera_motion", "P1", "2x2_tile", None,
     "The last veil of blue twilight light in water on the edge of darkness, gradient from faint navy glow above to black below, lonely calm"),
    ("c2-s13", "ch02", "两百米界面", "明暗分界:上方微亮天窗,下方深蓝黑,潜器正穿过", "image_to_video", "V1", "2x2_tile", None,
     "A submersible crossing a visible light boundary in the water, dim pale ceiling above and deep blue-black below, the craft silhouetted at the threshold"),

    # ---- ch03 会消失的海底(14) ----
    ("c3-s01", "ch03", "二战声呐舱", "1940s 军舰声呐舱,暗绿单色屏微光,士兵侧影", "image_camera_motion", "P1", "2x2_tile", None,
     "A 1940s naval sonar room at night, a sailor's silhouette watching a round dark-green phosphor scope glow, cramped metal interior, cigarette haze, dramatic low-key lighting"),
    ("c3-s02", "ch03", "屏上的假海底", "绿色磷光屏上一条起伏的回声层,抽象波形无字符", "image_camera_motion", "P2", "2x2_tile", None,
     "Extreme close view of a vintage green phosphor cathode screen with a slowly undulating echo band, abstract glowing trace, scanline texture, no readable characters"),
    ("c3-s03", "ch03", "夜晚上浮的亿万", "夜晚中上层,亿万小鱼剪影整体向上,像倒置的星图", "image_to_video", "V1", "2x2_tile", None,
     "An immense school of tiny fish rising through dim water at dusk, thousands of dark silhouettes moving upward together like a reversed starfield, faint blue backlight"),
    ("c3-s04", "ch03", "灯笼鱼的光带", "灯笼鱼群微光点连成浮动光带", "image_to_video", "V5-C", "2x2_tile", None,
     "Lanternfish with rows of tiny glowing photophores swimming in loose formation, their light points drawing drifting constellations in black water"),
    ("c3-s05", "ch03", "穿过迁徙层", "下潜器与迁徙鱼群交错,剪影上下各行其道", "image_to_video", "V1", "2x2_tile", None,
     "A small submersible drifting through a vertical migration layer, fish silhouettes streaming upward around it on both sides, layered movement in deep indigo water"),
    ("c3-s06", "ch03", "蓝光熄灭", "最后的蓝耗尽,水体转为近黑", "image_camera_motion", "P1", "2x2_tile", None,
     "The moment blue light dies in deep water: a readable vertical gradient from faint navy at the top through deep indigo to near-black at the bottom, sparse pale marine snow specks catching the last light, the darkness still reading as water rather than void, still and silent"),
    ("c3-s07", "ch03", "第一枚绿光", "黑暗中远处一点幽绿,亮了一下,背景有微弱深蓝渐变", "image_to_video", "V1", "2x2_tile", None,
     "A single emerald bioluminescent point glowing softly in near-black water, surrounded by a faint midnight-blue gradient haze and sparse dim marine snow particles, a soft halo bloom around the light, immense dark space"),
    ("c3-s08", "ch03", "眨眼的蓝点", "几枚蓝色光点,明灭交替,靛蓝水雾背景", "image_to_video", "V5-C", "2x2_tile", None,
     "Several scattered sapphire light dots glowing at different rhythms in deep indigo water haze, gentle bloom and fade like distant eyes, faint blue gradient background with drifting particles"),
    ("c3-s09", "ch03", "头顶的灯", "鮟鱇鱼,头顶一盏诱饵灯,大颌微张", "image_to_video", "V1", "2x2_tile", None,
     "A deep-sea anglerfish with a glowing lantern lure hanging before its jaw, softly lit teeth and translucent fin edges in blackness, patient and still"),
    ("c3-s10", "ch03", "防盗警报", "虾被抓住瞬间喷出光云,蓝雾在水中扩散", "image_to_video", "V1", "2x2_tile", None,
     "An ostracod shrimp bursting a cloud of luminous blue particles into the water like an underwater firework, the glowing mist expanding and swirling in darkness"),
    ("c3-s11", "ch03", "影子消失术", "腹面布满小灯的鱼,从下方看轮廓融入微光", "image_camera_motion", "P1", "2x2_tile", None,
     "A hatchetfish seen from below, its belly lined with tiny dim photophores matching the faint downwelling light, its outline barely distinguishable, clever camouflage"),
    ("c3-s12", "ch03", "看不见的红手电", "巨口鱼眼下红光器官,射出人眼不见的暗红锥形光", "image_to_video", "V1", "single", "关键特写推近",
     "A dragonfish with a glowing red photophore under its eye casting a faint crimson cone of light through black water, the only red light in a blue-black world, secretive"),
    ("c3-s13", "ch03", "深海星象", "远景:发光生物连成一片星海,与真正的星空互文", "image_camera_motion", "P1", "2x2_tile", None,
     "A wide abyssal vista where countless faint bioluminescent specks fill black water like a night sky underwater, serene and immense"),
    ("c3-s14", "ch03", "两种光的交界", "下潜器探照灯的暖白锥与冷色生物光各自为域", "image_camera_motion", "P2", "2x2_tile", None,
     "A submersible's warm white headlight cone cutting through darkness while cool blue-green bioluminescent points glow outside the beam, two kinds of light sharing the frame"),

    # ---- ch04 人的门槛(11) ----
    ("c4-s01", "ch04", "悬停暂停", "下潜器悬在昏蓝水层,静止,像在等待", "image_camera_motion", "P2", "2x2_tile", None,
     "A small white submersible hovering perfectly still in dim cobalt open water, faint gradient above, motionless and patient, suspended quiet"),
    ("c4-s02", "ch04", "一口气的极限", "自由潜水员侧影在深蓝中垂直下探,身体收紧", "image_camera_motion", "P1", "2x2_tile", None,
     "A trained freediver in a dark wetsuit descending head-first in deep cobalt water, body streamlined and folded, single bubble ribbon rising, sense of a depth record"),
    ("c4-s03", "ch04", "背气瓶的尽头", "技术潜水员身挂多支气瓶与灯,在近黑水中沿绳下潜", "image_camera_motion", "P1", "2x2_tile", None,
     "A technical diver carrying multiple scuba tanks and bright helmet lamps descending along a weighted line in near-dark water, gear-heavy silhouette, deep blue gloom"),
    ("c4-s04", "ch04", "漫长上浮", "减压停留:潜水员挂在垂线旁等待,气泡慢慢升起", "image_camera_motion", "P2", "2x2_tile", None,
     "A diver hanging motionless at a decompression stop beside a vertical line in dark open water, slow small bubbles rising past, patient stillness, hours-long pause"),
    ("c4-s05", "ch04", "海底实验室", "饱和潜水居住舱内,暖灯下潜水员休息,管道与舷窗", "image_camera_motion", "P2", "2x2_tile", None,
     "Inside a seafloor saturation habitat, divers resting in a warm-lit metal chamber with portholes showing dark water, bunk beds and pipes, cozy isolation"),
    ("c4-s06", "ch04", "鸭子嗓对讲", "居住舱内潜水员对着老式对讲机说话,面容认真", "image_camera_motion", "P1", "2x2_tile", None,
     "A saturation diver in a warm habitat interior speaking into a vintage intercom handset, slight smile, helmet clipped beside, amber lamplight on metal walls"),
    ("c4-s07", "ch04", "潜艇的承诺", "军用潜艇巨大钢壳剪影在昏蓝深处巡航", "image_camera_motion", "P2", "2x2_tile", None,
     "A large military submarine silhouette cruising in deep dusk-blue water, massive steel hull, no insignia, immense scale against empty water"),
    ("c4-s08", "ch04", "喙鲸下扎", "喙鲸尾叶扬起,开始一次深潜", "image_to_video", "V1", "2x2_tile", None,
     "A beaked whale arching at the dim surface at dusk, fluke lifting as it begins a vertical dive, ripples spreading, soon to be a thousand metres down"),
    ("c4-s09", "ch04", "抹香鲸追猎", "抹香鲸庞大身躯斜向深渊下潜,一串气泡", "image_to_video", "V3", "2x2_tile", None,
     "A sperm whale's huge blocky body angled steeply downward into darkness on a hunt, one column of bubbles drifting up, slow immense descent"),
    ("c4-s10", "ch04", "古老的反射", "鲸眼特写,平静,时间感的停顿", "image_camera_motion", "P1", "2x2_tile", None,
     "Close view of a whale's calm eye in soft blue light, weathered skin folds around it, ancient unhurried intelligence, meditative stillness"),
    ("c4-s11", "ch04", "隔着舷窗见证", "舱内视角:手贴舷窗,窗外近黑,仪表微光映在玻璃上", "image_camera_motion", "P1", "2x2_tile", None,
     "From inside a submersible cabin, a human hand resting against the thick viewport, near-black water outside, faint instrument glow reflecting on the glass, witness not experience"),

    # ---- ch05 午夜区的三件不可思议(13) ----
    ("c5-s01", "ch05", "午夜定场", "一千米下,水体近乎全黑,只剩可读的深浅层次", "image_camera_motion", "P2", "2x2_tile", None,
     "Midnight-zone open water, a readable gradient of near-black blues from faint grey-navy above to true black below, empty and immense, no visible floor or surface"),
    ("c5-s02", "ch05", "极地来路", "极地冬海:碎冰与深色冷水,风雪感", "image_camera_motion", "P2", "2x2_tile", None,
     "A polar winter sea with brash ice chunks drifting on dark cold water, snow haze, pale sky, the birthplace of the deep ocean's cold"),
    ("c5-s03", "ch05", "几百年的旅程", "深渊冷水缓缓铺展,如慢速河流在黑暗中行进", "image_camera_motion", "P1", "2x2_tile", None,
     "An immense slow mass of dark cold water drifting through blackness like an underwater river, subtle layered currents visible only by faint suspended particles"),
    ("c5-s04", "ch05", "海雪落下", "白色碎屑斜斜缓缓下沉,像倒放的慢雪", "image_to_video", "V1", "2x2_tile", None,
     "Marine snow: white organic flecks drifting slowly and diagonally downward through black water in a faint lamp glow, like snow falling in slow motion underwater"),
    ("c5-s05", "ch05", "深渊的口粮", "微距:数片白色海雪颗粒,纤维与尘絮质感", "image_camera_motion", "P1", "2x2_tile", None,
     "Macro view of individual marine snow particles, delicate white fibrous flakes and dust aggregates suspended in dark water, fine texture like falling nourishment"),
    ("c5-s06", "ch05", "阿尔文号沉睡", "1968 年事故:白色小潜器歪在斜坡海底,缆绳断落", "image_camera_motion", "P2", "2x2_tile", None,
     "A small white research submersible lying tilted and abandoned on a dark silty seafloor slope, broken cable trailing, cold stillness, 1960s design"),
    ("c5-s07", "ch05", "没吃的午餐", "舱内静物:纸包三明治、两只苹果、两保温瓶汤", "image_camera_motion", "P1", "single", "关键特写推近",
     "Inside a drowned submersible cabin, an untouched lunch of waxed-paper sandwiches, two apples and two vacuum thermoses arranged on a bench, preserved in cold dark water, still-life museum quiet"),
    ("c5-s08", "ch05", "连腐烂都懒得走", "近一年后舱内无扰动,物件几乎如初,幽暗冷清", "image_camera_motion", "P2", "2x2_tile", None,
     "The same drowned cabin interior after a year: food and objects nearly unchanged, no decay, no scattering, faint silt dusting, cold dark preservation like a paused clock"),
    ("c5-s09", "ch05", "绝食冠军定装", "巨型等足虫:盔甲分节,拳大,如活化石", "image_camera_motion", "P1", "single", "母题定装镜",
     "A giant isopod resting on dark aquarium gravel, segmented pale armour like a helmet, compound eyes, size of a fist, ancient living-fossil presence, museum portrait lighting"),
    ("c5-s10", "ch05", "管理员换花样", "水族馆暗缸中,饲养员的手投下食物,等足虫不动", "image_camera_motion", "P1", "2x2_tile", None,
     "In a dim aquarium tank, a keeper's hand offering food above a giant isopod that stays curled and uninterested, patient unhurried refusal, soft blue tank light"),
    ("c5-s11", "ch05", "看不见的声道", "抽象:两头相距极远的鲸,之间水面下有极淡涟漪线", "image_camera_motion", "P2", "2x2_tile", None,
     "Two distant whale silhouettes far apart in dark open water, connected only by extremely faint concentric ripple rings travelling between them, an invisible highway made barely visible, subtle surrealism"),
    ("c5-s12", "ch05", "冷战水听器", "海底缆线与水听器阵列躺在泥面,年代感", "image_camera_motion", "P2", "2x2_tile", None,
     "A Cold-War era hydrophone array: thick black cables and cylinder microphones lying on grey deep-sea mud, 1960s military hardware reclaimed by stillness, dim lamp view"),
    ("c5-s13", "ch05", "互道晚安", "夜里近水面,鲸浮起低吟,歌声将走进声道", "image_to_video", "V1", "2x2_tile", None,
     "A whale rising slowly near the night surface, head breaking dim water, beginning a low song, gentle ripples, its voice about to travel thousands of kilometres"),

    # ---- ch06 不吃太阳的生命(12) ----
    ("c6-s01", "ch06", "按理该荒凉", "两三千米水柱,近乎空无,偶有微粒", "image_camera_motion", "P2", "2x2_tile", None,
     "Deep open water at two-three kilometres, almost empty, a few suspended particles, expectation of desolation, vast black vertical space"),
    ("c6-s02", "ch06", "去加拉帕戈斯", "阿尔文号下潜,海底裂缝方向,黑暗中灯锥向前", "image_camera_motion", "P1", "2x2_tile", None,
     "The white research submersible Alvin descending toward a dark seafloor rift, headlight beam reaching forward over volcanic rock, anticipation in blackness, 1977 expedition feel"),
    ("c6-s03", "ch06", "灯亮的一刻", "探照灯打开,白蟹群突然铺满视野", "image_to_video", "V1", "2x2_tile", None,
     "The instant a submersible's headlights switch on over a hydrothermal field: a dense carpet of pale crabs revealed on black basalt, brightness blooming out of darkness"),
    ("c6-s04", "ch06", "白茫茫的蟹群", "成片白蟹在黑色岩面爬动,密而不乱", "image_camera_motion", "P1", "2x2_tile", None,
     "Hundreds of pale white crabs crawling closely packed over black volcanic seafloor, organised chaos, high contrast of bone-white shells on basalt"),
    ("c6-s05", "ch06", "管虫丛定装", "橘红管虫丛,两米长管,顶端红羽,无叶之花", "image_camera_motion", "P1", "single", "母题定装镜",
     "A colony of giant tube worms, bright orange-red tubes up to two metres tall topped with crimson plumes like leafless flowers, standing in blackness, iconic deep-sea portrait"),
    ("c6-s06", "ch06", "无叶之花轻摇", "管虫红羽在水流中缓缓开合摇晃", "image_to_video", "V1", "2x2_tile", None,
     "Giant tube worm plumes slowly swaying and unfurling in a gentle current, crimson fans against black water, garden-like calm rhythm"),
    ("c6-s07", "ch06", "体内房客", "超现实:管虫体内器官中细菌如微光尘海", "image_camera_motion", "P1", "2x2_tile", None,
     "Subtle surreal inner view inside a tube worm's body: a specialised organ chamber packed with dense symbiotic bacteria rendered as a sea of faint warm dust motes, tenant farmers housed within, no anatomy-chart look"),
    ("c6-s08", "ch06", "黑烟囱喷口", "热液喷口涌出滚烫闪动的水,黑岩衬托", "image_to_video", "V5-C", "2x2_tile", None,
     "A black smoker hydrothermal vent pouring a shimmering column of superheated water from a mineral chimney on the seafloor, heat refraction rippling like liquid glass in blackness"),
    ("c6-s09", "ch06", "冰与火的缝隙", "喷口旁几十厘米即近零度,虾贴着缝住", "image_camera_motion", "P2", "2x2_tile", None,
     "Vent shrimp crowded in a narrow band beside a shimmering hot plume, cold dark water inches away, life packed along the thin seam between ice and fire"),
    ("c6-s10", "ch06", "另一套记账", "海底裂缝暗光,硫化物如微弱矿脉纹理", "image_camera_motion", "P1", "2x2_tile", None,
     "A dark seafloor fissure with faint mineral veins glowing dimly in cracked rock, chemically fed life suggested as subtle warm traces, an alternate ledger of energy, subtle surrealism"),
    ("c6-s11", "ch06", "抬头看冰卫星", "木星冰卫星悬在黑暗太空,冰壳裂纹下暗示海洋", "image_camera_motion", "P2", "2x2_tile", None,
     "A Jupiter-like gas giant with an icy moon in the foreground, the moon's cracked white shell showing hints of a dark subsurface ocean beneath the fractures, deep space stillness"),
    ("c6-s12", "ch06", "冰壳下的海", "近景:冰壳裂隙,其下幽暗海水,似有微光", "image_camera_motion", "P1", "2x2_tile", None,
     "Close view of a thick icy crust with deep cracks, dark ocean water visible beneath the fractures with a suggestion of faint warmth, a hidden sea under ice, hopeful darkness"),

    # ---- ch07 正在被吃掉的沉船,与三十年的宴席(15) ----
    ("c7-s01", "ch07", "巨影漂过", "昏暗中船头巨影缓缓显形,像从时间里来", "image_to_video", "V3", "2x2_tile", None,
     "The enormous bow of a rusted great ship emerging slowly from black gloom as a submersible approaches, railings and anchors materialising out of darkness, a ghost arriving from time"),
    ("c7-s02", "ch07", "船头静置", "泰坦尼克船头全貌卧在海底,灯光仅照亮局部", "image_camera_motion", "P2", "2x2_tile", None,
     "The famous bow section of a great ocean liner resting on the deep seafloor, rusted hull half-lit by a distant lamp, teeming stillness, monument and ruin at once"),
    ("c7-s03", "ch07", "铁锈冰凌", "特写:挂满钢板的锈色冰凌,如钟乳石垂落", "image_camera_motion", "P1", "single", "关键特写推近",
     "Close view of rusticles: icicle-like ropes of rust hanging densely from steel plating like stalactites, textured orange-brown mineral growth, softly lit, beautiful and devouring"),
    ("c7-s04", "ch07", "它们是活的", "微距:锈凌表面微生物聚落的绒面质感", "image_camera_motion", "P1", "2x2_tile", None,
     "Macro view of rusticle surface: a velvet-textured living colony of countless microbes on rust fibres, faint damp sheen, life at the scale of dust eating a ship"),
    ("c7-s05", "ch07", "一层层吃掉", "钢板边缘变薄剥落,锈屑悬浮周围", "image_camera_motion", "P2", "2x2_tile", None,
     "A steel hull edge thinned and flaking after decades underwater, rust particles drifting suspended around it, slow consumption made visible"),
    ("c7-s06", "ch07", "鲸落开始", "鲸尸缓缓下沉,黑暗从下方迎接", "image_to_video", "V3", "2x2_tile", None,
     "A dead whale's immense body sinking slowly and silently through black deep water toward the unseen seafloor, dust of decay drifting off, a falling gift from the sunlit world"),
    ("c7-s07", "ch07", "热闹的散场", "食腐者围拢鲸尸:鱼、蟹、盲鳗,几个月的宴席", "image_camera_motion", "P1", "2x2_tile", None,
     "A whale fall on the seafloor crowded with scavengers: hagfish coiling, crabs climbing, dark fish circling, efficient busy feast under dim light, undignified and magnificent"),
    ("c7-s08", "ch07", "骨缝里的岁月", "骨架骨缝间,食骨虫如细雪管立", "image_camera_motion", "P2", "2x2_tile", None,
     "A whale skeleton's vertebral gaps colonised by bone-eating worms, delicate feathery tubes rising from the bones like pale roots, years of patient harvesting in the sediment"),
    ("c7-s09", "ch07", "慢蜡烛", "骨架深处脂类微光渗出,数十年不灭", "image_camera_motion", "P1", "2x2_tile", None,
     "An old whale skeleton in darkness, a faint warm seep of lipids glowing subtly from deep within the bones like a buried slow candle, decades-long afterglow, subtle surrealism"),
    ("c7-s10", "ch07", "骨架花园", "整副鲸骨密布小生命,如花园生态", "image_camera_motion", "P2", "2x2_tile", None,
     "A complete whale skeleton on the seafloor densely colonised by small corals, anemones and worms, a garden planted in bone, thriving decades after death"),
    ("c7-s11", "ch07", "石头田", "锰结核如土豆铺满软泥平原,望不到边", "image_camera_motion", "P2", "2x2_tile", None,
     "An endless abyssal plain carpeted with potato-sized manganese nodules on soft pale sediment, rows upon rows to the lamp's edge, a stone field millions of years old"),
    ("c7-s12", "ch07", "百万年几毫米", "单颗结核特写:泥尘、生长纹理", "image_camera_motion", "P1", "2x2_tile", None,
     "A single manganese nodule in close view: dark metallic lump with fine concentric growth texture, dusted with pale sediment, patient geology in one object"),
    ("c7-s13", "ch07", "海参成群", "软泥平原上海参成群缓慢爬行,拖出细痕", "image_to_video", "V1", "2x2_tile", None,
     "A group of plump pale sea cucumbers crawling very slowly across silty abyssal mud, leaving faint trails, unhurried commuters of the deep plain"),
    ("c7-s14", "ch07", "海百合轻摇", "海百合附在石上,羽臂在流水里缓缓摇", "image_camera_motion", "P2", "2x2_tile", None,
     "Sea lilies crinoids anchored on a stone, feathery arms swaying gracefully in a faint current, prehistoric elegance in dim blue light"),
    ("c7-s15", "ch07", "大地站起来", "平原尽头,海沟壁陡然升起,黑暗切竖", "image_camera_motion", "P1", "2x2_tile", None,
     "Where the flat plain ends, a colossal trench wall rises abruptly into darkness, vertical rock face disappearing upward and downward, the earth standing up, dramatic scale"),

    # ---- ch08 鱼到此为止(12) ----
    ("c8-s01", "ch08", "陡壁边缘", "六千米:平原收尾,竖直陡壁切进裂缝", "image_camera_motion", "P1", "2x2_tile", None,
     "A submersible hovering at the lip of a huge vertical trench wall, the seafloor dropping away into a dark gash, scale vertigo in blue-black light"),
    ("c8-s02", "ch08", "板块相撞", "超现实:两块岩体缓缓相叠,伤口深切入暗", "image_camera_motion", "P2", "2x2_tile", None,
     "Subtle surreal view of two immense rock masses meeting, one sliding beneath the other, the collision line cutting deep into darkness, planetary slow-motion geology, no diagram look"),
    ("c8-s03", "ch08", "超深渊带", "海沟内壁延伸,幽暗纵深,偶有沉积滑落", "image_camera_motion", "P2", "2x2_tile", None,
     "The inside face of a hadal trench wall receding into black depth, layered rock and pale sediment streaks, a rare white fleck of drifting debris, immense and lonely"),
    ("c8-s04", "ch08", "狮子鱼定装", "超深渊狮子鱼:半透明水滴身,无鳞,柔弱", "image_camera_motion", "P1", "single", "母题定装镜",
     "A hadal snailfish portrait: translucent pinkish tadpole-shaped body, no scales, delicate fins, gelatinous and soft-looking yet holding seven hundred atmospheres, gentle creature portrait in darkness"),
    ("c8-s05", "ch08", "水滴悬停", "狮子鱼在坡前安静悬停,尾鳍微摆", "image_to_video", "V1", "2x2_tile", None,
     "A translucent snailfish hovering calmly before the trench slope, tail fin waving gently, body glowing faintly pink against dark rock, serene resilience"),
    ("c8-s06", "ch08", "抗压的化学", "特写:半透明组织内细密微粒支撑", "image_camera_motion", "P1", "2x2_tile", None,
     "Extreme close view of the snailfish's translucent flank, dense fine particles shimmering within gelatinous tissue like salt dissolved for balance, inner strength made visible, subtle surrealism"),
    ("c8-s07", "ch08", "八千三百三十六米", "2023 伊豆小笠原:坡前一条狮子鱼,创纪录深度", "image_camera_motion", "P1", "2x2_tile", None,
     "A lone snailfish holding position above pale slope sediment in absolute darkness near the edge of its world, deep trench wall behind, the deepest fish ever seen, quiet record"),
    ("c8-s08", "ch08", "冠军家族", "两条狮子鱼同框,幽灵般淡粉", "image_camera_motion", "P2", "2x2_tile", None,
     "Two ghostly pale-pink snailfish sharing the dark water near the slope, faintly luminous, a family dynasty of depth champions, calm companionship"),
    ("c8-s09", "ch08", "没有了", "更深处水体空无鱼,黑暗连续可读", "image_camera_motion", "P2", "2x2_tile", None,
     "The water below eight thousand metres: no fish anywhere, a readable gradient of dark blues fading into black emptiness, absence itself as the subject, still heavy water"),
    ("c8-s10", "ch08", "泥里的皮", "坡壁沉积表膜,微生物致密如薄皮", "image_camera_motion", "P1", "2x2_tile", None,
     "The trench slope's sediment surface covered with a dense microbial mat, a thin skin of life sheening faintly over pale mud, microscopically crowded yet appearing empty"),
    ("c8-s11", "ch08", "钩虾赶集", "饵笼围满钩虾,从坡壁各处聚拢", "image_to_video", "V1", "2x2_tile", None,
     "Amphipods swarming from all directions across the trench slope toward a bait cage on the mud, dozens of pale crustaceans converging like a market crowd, lively gathering in the dark"),
    ("c8-s12", "ch08", "替它们走", "下潜器沿坡继续下行,灯光渐小", "image_camera_motion", "P2", "2x2_tile", None,
     "The submersible's lamp glow shrinking down the trench wall into greater darkness as it continues the descent alone, a small island of light on an endless slope"),

    # ---- ch09 杯子、鱼与七秒钟(15) ----
    ("c9-s01", "ch09", "坐底", "万米海底:细泥如面粉,灯锥外无边黑暗", "image_camera_motion", "P1", "2x2_tile", None,
     "The deepest seafloor under a single warm lamp cone: impossibly fine pale silt like flour, ripples delicate as dust, beyond the light an edgeless black, the bottom of the world"),
    ("c9-s02", "ch09", "的里雅斯特号", "1960 悬浮舱+钢球潜水器,钢缆与舱室细节", "image_camera_motion", "P1", "single", "精密结构",
     "The bathyscaphe Trieste: a huge gasoline-filled float hull shaped like a blimp, suspended beneath it a thick white spherical pressure cabin with a single small porthole, 1950s engineering, historical portrait at sea"),
    ("c9-s03", "ch09", "两米钢球", "舱内:两人对坐,仪表与舷窗,幽闭但平静", "image_camera_motion", "P2", "2x2_tile", None,
     "Inside the two-metre steel sphere cabin: two men seated face to face in cramped calm, analogue gauges and one small porthole, 1960 winter clothing, dim instrument glow, historical quiet"),
    ("c9-s04", "ch09", "五小时下沉", "钢球潜水器缓缓沉入连续黑暗", "image_to_video", "V3", "2x2_tile", None,
     "The bathyscaphe descending slowly and steadily through endless black water, faint surface glow long gone, patient five-hour fall, dust-like particles rising past"),
    ("c9-s05", "ch09", "舷窗的平鱼", "舷窗视角:泥面上一条扁白影子,似鱼非鱼", "image_camera_motion", "P1", "2x2_tile", None,
     "Through a small porthole: a pale flat shape resting on fine mud below, ambiguous between fish and sea cucumber, blurred by murk and excitement, an unverified sighting rendered honestly"),
    ("c9-s06", "ch09", "造气球的父亲", "1930s 平流层气球:巨球悬在云海之上", "image_camera_motion", "P2", "2x2_tile", None,
     "A 1930s stratospheric balloon: a vast spherical envelope floating above an endless cloud sea, tiny pressurised gondola hanging beneath, dawn light, the father who went highest before going deepest"),
    ("c9-s07", "ch09", "红色深潜器", "2012 卡梅伦:单人红色艇坐底,灯锥前的荒凉", "image_camera_motion", "P2", "2x2_tile", None,
     "A sleek single-seat deep-sea submersible in signature red sitting on pale silt at the bottom, its lamp cone revealing empty moon-like desolation around, modern and alone"),
    ("c9-s08", "ch09", "走成航线", "2019 起:多艘深潜器灯点散布海底线", "image_camera_motion", "P2", "2x2_tile", None,
     "A wide view of the deepest seafloor with several small submersible lamp points scattered far apart across the mud plain, a former frontier become a route, quiet traffic in the abyss"),
    ("c9-s09", "ch09", "画好的杯子", "出发前:画满涂鸦的白色发泡杯,人手系绳", "image_camera_motion", "P1", "single", "关键特写推近",
     "A white foam cup hand-decorated with friendly drawings and signatures, being tied with string to a submersible's hull by a human hand, pre-dive ritual, soft daylight above water"),
    ("c9-s10", "ch09", "小酒盅", "上来后:拇指大的压缩杯,画仍在,邮票大", "image_camera_motion", "P1", "2x2_tile",
     None,
     "The same foam cup after the dive: compressed to thimble size, its drawings shrunk to stamp scale but intact, crumpled dense foam texture, held beside a human thumb for scale, honest souvenir of pressure"),
    ("c9-s11", "ch09", "面粉泥雾", "坐底搅起的细泥雾,几分钟才缓缓沉回", "image_to_video", "V5-C", "2x2_tile", None,
     "A cloud of ultra-fine pale silt billowing slowly around a landed submersible and settling back grain by grain, dust in still air rhythm, hypnotic slowness"),
    ("c9-s12", "ch09", "世界最深处的住户", "灯锥边缘一只指甲盖大钩虾安静爬行", "image_to_video", "V1", "2x2_tile", None,
     "At the lamp's edge on pale mud, a single thumbnail-sized amphipod crawling calmly, antennae testing the silt, unaware it lives at the world's deepest address, gentle intimacy"),
    ("c9-s13", "ch09", "一个细胞的虫", "砂壳虫:巴掌大的一小朵,泥面上如微型海绵", "image_camera_motion", "P1", "2x2_tile", None,
     "A xenophyophore on the deep mud: a palm-sized delicate dome of fine sediment grains glued into a soft rounded form by a single cell, strange gentle architecture, one being one cell"),
    ("c9-s14", "ch09", "泥都是活的", "泥面微距:孔隙间微生物微光痕迹", "image_camera_motion", "P2", "2x2_tile", None,
     "Macro view across deep-sea mud surface: countless tiny pores and tracks hinting at hundreds of thousands of microbes per gram, faint life texture everywhere in apparent emptiness"),
    ("c9-s15", "ch09", "十四秒", "垂直水柱全景,一线声波涟漪往返于远处海面", "image_camera_motion", "P1", "2x2_tile", None,
     "A full vertical ocean column seen from the bottom: distant faint surface glimmer far above, a single subtle ripple band travelling upward through black water, fourteen seconds of echo made visible, subtle surrealism"),

    # ---- ch10 上来的时候(13) ----
    ("c10-s01", "ch10", "抛掉压载", "压载物脱落,艇身一轻,泥雾中开始上浮", "image_to_video", "V1", "2x2_tile", None,
     "Ballast weights dropping away from the submersible's base into silt haze as the craft lightens and begins to rise, release and lift-off in one gesture, dust falling away"),
    ("c10-s02", "ch10", "开始上升", "艇身上行,坡壁缓缓下沉退场", "image_camera_motion", "P2", "2x2_tile", None,
     "The submersible rising steadily as the trench wall slides slowly downward out of frame, world rewinding, subtle upward motion feeling, black water streaming past"),
    ("c10-s03", "ch10", "弯腰病", "1900s 岸边:沉箱工人弯腰忍痛,油灯夜", "image_camera_motion", "P2", "2x2_tile", None,
     "A 1900s riverside work camp at lamplight: caisson workers bent double in pain outside a wooden compression chamber, companions supporting them, dignified suffering, historical amber tones"),
    ("c10-s04", "ch10", "倒带·鱼家门口", "上行中:狮子鱼水滴身影留在坡上变小", "image_camera_motion", "P2", "2x2_tile", None,
     "Seen from the rising submersible, a translucent snailfish silhouette receding downward on the slope, growing smaller and fainter, a farewell at eight thousand metres"),
    ("c10-s05", "ch10", "倒带·绿洲", "管虫丛淡白掠过,裂缝渐远", "image_camera_motion", "P2", "2x2_tile", None,
     "During ascent, a faint pale tube worm colony and its dark rift passing by outside and slipping below, the oasis waving goodbye, dim and dreamlike"),
    ("c10-s06", "ch10", "倒带·宴席", "远处泰坦尼克方向,暗影一闪而过", "image_camera_motion", "P2", "2x2_tile", None,
     "Far off in the gloom during ascent, the rusted hull silhouette of the great ship briefly visible and then gone, a milestone passing on the way up, continuing feast implied"),
    ("c10-s07", "ch10", "倒带·鲸歌上路", "声道上,一头鲸的歌声正走几千公里", "image_camera_motion", "P2", "2x2_tile", None,
     "A whale silhouette suspended in dim water mid-song, extremely faint concentric rings of its voice travelling away into the dark highway, a letter in transit"),
    ("c10-s08", "ch10", "蓝回来了", "上方出现第一层薄薄蓝光,渐渐增亮", "image_to_video", "V1", "2x2_tile", None,
     "The first veil of blue reappearing in the water above the rising submersible, faint navy brightening gradually toward cobalt, light returning like a held breath released"),
    ("c10-s09", "ch10", "留着的灯", "近水面:暖调微光像门口留的一盏灯", "image_camera_motion", "P1", "2x2_tile", None,
     "Just below the surface at night, a soft warm-edged glow waiting above like a lamp left on for someone coming home, gentle silver-blue water, emotional threshold"),
    ("c10-s10", "ch10", "破水月光", "破出水面一瞬,月光倾泻,全片最亮一帧", "image_to_video", "V1", "single", "关键特写推近",
     "The submersible breaking through the night surface: a burst of silver moonlight flooding the frame, spray droplets glowing, the whole journey's brightness released in one instant, the brightest frame of the film"),
    ("c10-s11", "ch10", "知道的少", "夜海无际,远处一点科考船灯光", "image_camera_motion", "P2", "2x2_tile", None,
     "A vast night ocean under moonlight stretching unmeasured to the horizon, one tiny research vessel light far away, how little we have mapped made serene and humbling"),
    ("c10-s12", "ch10", "留下的多", "微距:钩虾体内一根微塑料纤维,幽微但清楚", "image_camera_motion", "P1", "2x2_tile", None,
     "Macro view of a pale deep-sea amphipod with one fine man-made microfibre visible within its translucent body, subtle and undeniable, quiet evidence at the world's deepest floor"),
    ("c10-s13", "ch10", "起风了", "夜海起风,浪脊在月光下发亮,层层远去", "image_to_video", "V5-C", "2x2_tile", None,
     "A night sea rising with wind: wave crests lighting up silver in moonlight and rolling away in ranks, lively but calm, the surface alive again"),

    # ---- 尾声 你身体里的海(5) ----
    ("e-s01", "epilogue", "同一片夜", "垂直全景:月光海面到深处黑暗同框", "image_camera_motion", "P2", "2x2_tile", None,
     "A single vertical view holding the whole night ocean at once: moonlit silver surface at top fading through blue layers to black depth at the bottom, all depths in one breath, subtle surrealism"),
    ("e-s02", "epilogue", "借来的水", "超现实:一道柔光水脉与温热暗红渐层相融", "image_camera_motion", "P1", "2x2_tile", None,
     "Subtle surreal blend: a ribbon of clear sea water and a faint warm dark-red gradient folding softly into each other, ancient borrowed elements on a journey, no anatomy, abstract and calm"),
    ("e-s03", "epilogue", "浪替黑暗醒着", "海面夜浪轻涌,月光路径稳定", "image_to_video", "V1", "2x2_tile", None,
     "Gentle night waves rolling under a steady path of moonlight, the surface keeping watch above ten thousand metres of sleeping dark, soft endless rhythm"),
    ("e-s04", "epilogue", "深处仍在", "暗部小景:雪落、泥沉、钩虾爬,同片安静", "image_camera_motion", "P2", "2x2_tile", None,
     "A quiet composite of the deep still going on: marine snow drifting, silt settling, a small amphipod crawling, all in one dim frame, uninterrupted life below"),
    ("e-s05", "epilogue", "晚安", "最终帧:平静夜海与月光,与开场互文", "image_camera_motion", "P2", "2x2_tile", None,
     "The final frame: a calm night sea with an unbroken path of moonlight to the horizon, echoing the journey's first image, silence and safety, good night"),
]


def para_ids_by_section(doc):
    m = {}
    for u in doc["utterances"]:
        pid = u["id"].rsplit("-u", 1)[0]
        m.setdefault(u["section"], []).append(pid)
    return {s: sorted(set(v), key=lambda x: int(re.search(r"p(\d+)", x).group(1))) for s, v in m.items()}


def narration_chars(doc):
    chars = {}
    for u in doc["utterances"]:
        pid = u["id"].rsplit("-u", 1)[0]
        chars[pid] = chars.get(pid, 0) + len(u["text"])
    return chars


def main():
    doc = json.loads(UTT.read_text(encoding="utf-8"))
    paras = para_ids_by_section(doc)
    chars = narration_chars(doc)
    sha = hashlib.sha256(SRC.read_bytes()).hexdigest()
    shots = []
    cursor = {}   # section -> paragraph cursor
    t = GAPS["head"]
    for (sid, sec, beat, scene, cls, strat, mode, cat, core) in ROWS:
        plist = paras.get(sec) or paras["ch01"]
        i = cursor.get(sec, 0)
        if i >= len(plist):
            i = len(plist) - 1
        cursor[sec] = i + 1
        pid = plist[i]
        n = chars.get(pid, 30)
        est = round(max(4.0, n / CPS), 1)
        shot = {
            "id": sid, "paragraph_id": pid, "section": sec, "beat": beat,
            "scene": scene,
            "est_seconds": est, "est_body_offset_s": round(t, 2),
            "status": "planned_narration_basis",
            "timing": {"mode": "planned_estimate", "note": "锁定稿字数估算;音轨完成后由 timeline.json 实测回填"},
            "shot_class": cls, "strategy": strat,
            "image_mode": mode,
            "image_prompt": STYLE + PALETTE[sec] + ". " + core + ". " + BAN,
        }
        if mode == "single":
            shot["single_category"] = cat
        shots.append(shot)
        t += est
    singles = sum(1 for s in shots if s["image_mode"] == "single")
    tiles = len(shots) - singles
    i2v = sum(1 for s in shots if s["shot_class"] == "image_to_video")
    est_calls = singles + (tiles + 3) // 4
    plan = {
        "schema_version": 1,
        "episode": "mariana-descent",
        "basis": "story/OUTLINE.md v1(2026-10-19 重构) + NARRATION_MASTER.md 锁定稿 v1.1",
        "source_sha256": sha,
        "created_at": "2026-10-19", "updated_at": "2026-10-20",
        "fps": 30, "width": 1920, "height": 1080,
        "cps_final": CPS,
        "intra_gap_s": GAPS["unit"], "para_gap_s": GAPS["para"], "chap_gap_s": GAPS["chap"],
        "api_budget": {
            "rule": "rules/shared/image-grid-generation.md 2026-10-19 修订:默认 2x2,single 仅四类例外;预计 API 调用数 = single 镜数 + ⌈批量镜数/4⌉",
            "authorization": "2026-10-19 用户授权自主推进至成片,预算控制在 60-85 次参考带内;批次后报消耗账目;遇余额类 403 立即停手",
            "full_episode": {"shots": len(shots), "single": singles, "tile": tiles,
                             "est_calls": est_calls,
                             "spent_so_far": 74, "spent_note": "全片已花 74 次(含试点/502重试);2026-10-22 桥段补 4 镜 +1 次 2x2",
                             "remaining_estimate": est_calls - 14,
                             "note": "2026-10-20 补齐 ch04-尾声;c3-s06 过黑重做已在 pending 中,可与 ch04 批同格"},
        },
        "counts": {"total": len(shots), "single": singles, "2x2_tile": tiles,
                   "image_to_video": i2v,
                   "by_section": {sec: sum(1 for s in shots if s["section"] == sec)
                                  for sec in dict.fromkeys(s["section"] for s in shots)}},
        "section_titles": {
            "ch01": "用麻绳量出来的深渊", "ch02": "血是绿色的", "ch03": "会消失的海底",
            "ch04": "人的门槛", "ch05": "午夜区的三件不可思议", "ch06": "不吃太阳的生命",
            "ch07": "正在被吃掉的沉船,与三十年的宴席", "ch08": "鱼到此为止",
            "ch09": "杯子、鱼与七秒钟", "ch10": "上来的时候", "epilogue": "你身体里的海"},
        "notes": "全片计划 = ch01-ch10 + 尾声(2026-10-20 补齐 ch04-尾声)。2x2 组图由 07_gen_stills.py 按同章或相邻章自动凑 4;single 例外类别逐镜标注于 single_category。深度阶梯即叙事:ch01 海面月光青蓝 → ch02 亮蓝渐深 → ch03 靛蓝转近黑+生物光点 → ch04 昏蓝悬停 → ch05 近黑+海雪 → ch06 黑底+橘红管虫暖色回归 → ch07 锈琥珀+平原灰蓝 → ch08 沟壁蓝灰+狮子鱼淡粉 → ch09 纯黑+暖白灯锥 → ch10 反向渐变回月光(全片最亮一帧给 c10-s10 破水) → 尾声 月光收束。",
        "shots": shots,
    }
    OUT.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["# ALL_SHOT_PROMPTS(全片 v1:ch01-ch10+尾声)", "",
             f"- 总镜数 {len(shots)}(single {singles} / 2x2_tile {tiles} / i2v {i2v})",
             f"- 整集预计调用 {est_calls} 次(已花 17 次含试点,60-85 带内)", ""]
    for s in shots:
        lines += [f"## {s['id']} · {s['beat']}({s['paragraph_id']})",
                  f"- 画面:{s['scene']}",
                  f"- 类别/策略:{s['shot_class']} / {s['strategy']};image_mode={s['image_mode']}"
                  + (f"(例外:{s['single_category']})" if s["image_mode"] == "single" else ""),
                  f"- prompt:`{s['image_prompt']}`", ""]
    PROMPTS_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"shots={len(shots)} singles={singles} tiles={tiles} i2v={i2v} "
          f"est_calls={est_calls}")
    print(f"body_est(all sections)≈{t:.0f}s")


if __name__ == "__main__":
    main()
