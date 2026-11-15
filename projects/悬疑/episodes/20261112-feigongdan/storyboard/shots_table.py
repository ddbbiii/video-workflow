# -*- coding: utf-8 -*-
"""《废弃工单》正文镜头表（48 镜）。cue_start 用句子前缀对齐 utterances.json。

字段：id, cue_start（本镜第一句）, move（push/pull/wide/static）, prompt（英文生图）
风格：手绘感动画电影静帧（半写实插画），冷青灰；不用照片质感。
"""
import re

STYLE = ("2D animated film still, hand-painted anime background art, mature semi-realistic illustration, "
         "visible brush texture, cel-shaded lighting with soft gradients, desaturated cold teal and grey palette, "
         "old 1990s Chinese residential building, lived-in grime and dust, volumetric dust, shallow depth of field, "
         "16:9 composition, ")

CHAR = ("a lean Chinese man in his late thirties, short black buzz cut, light stubble, "
        "dark navy work jacket with a blank rectangular badge patch on the left chest, dark grey work trousers, "
        "black grip gloves")

NEG = ("photograph, photorealistic, 3d render, cgi, live action, hyperreal, text, letters, numbers, watermark, UI, "
       "logo, gore, blood, monster, ghost, creature, corpse, chibi, childish cartoon, extra fingers, deformed hands, "
       "six fingers, blurry, low quality, oversaturated, daylight, cozy warm, clean new building, smiling")

SHOTS = [
    ("S01", "工单灰在列表底端", "push",
     "close-up of a gloved hand holding a rugged handheld dispatch terminal inside a dark van at night, "
     "the screen is a blank pale glow, dashboard lights blurred behind, rain-flecked window, no readable content"),
    ("S02", "巷口信号时断时续", "pull",
     "narrow alley between old six-storey apartment blocks at night, a steel unit door standing slightly ajar, "
     "one dim sodium lamp far at the alley mouth, wet concrete, tangled overhead cables, no people"),
    ("S03", "他捏紧手电", "push",
     "medium shot from behind: " + CHAR + " steps over the threshold of the ajar steel door into a pitch-dark "
     "stairwell, a hard beam of light from his off-frame hand cutting through dust and cold haze, worn concrete floor"),
    ("S04", "楼道里没有风", "static",
     "dim fourth-floor corridor of an old apartment building, no wind, dust suspended in the air, dead sensor lamp, "
     "one faint grey window glow at the far end, peeling green wall paint, no people"),
    ("S05", "手电扫过去", "push",
     "close-up of a dusty beige metal junction box mounted on an old corridor wall, its flat lid hanging open at an "
     "angle from one broken hinge, the inside is completely empty and dark, no wires, a hard beam of light from "
     "off-frame right, dust in the air, no people"),
    ("S06", "锁扣是从里面顶开的", "push",
     "extreme close-up of the junction box latch: the steel plate is bent outward and torn, the hinge buckled, "
     "rusted metal curled away from the box as if pushed from inside, cold raking light, empty dark inside"),
    ("S07", "箱子里没有光纤", "push",
     "looking into the open compartment of a dusty beige metal junction box on a corridor wall, the compartment is "
     "empty, bare grey metal backplate, a few screws, no wires at all, a beam of light from off-frame dies in the dark"),
    ("S08", "一卷旧铜线盘在箱底", "push",
     "close-up inside the empty metal junction box: a coil of old copper wire lies on the bottom, the copper core "
     "gleams unnaturally bright, dust and dark red soil beneath it, a beam of light from off-frame"),
    ("S09", "铜芯泛着亮光", "push",
     "macro shot of the copper wire core, unnaturally bright polished copper catching the light, the rest of the "
     "coil dull and oxidized, dark box interior behind"),
    ("S10", "亮得不对劲", "push",
     "extreme macro of the bright copper strand against dull dusty metal, the gleam looks fresh and wrong, "
     "cold light, shallow focus, dark box interior"),
    ("S11", "铜线下面垫着一层土", "push",
     "close-up: under the copper coil lies a layer of dark red soil, dry and pale-crusted on the surface, "
     "the box bottom gritty, cold raking light across it"),
    ("S12", "他用指背蹭了蹭", "push",
     "close-up: a gloved knuckle brushes the dark red soil, the crust breaks and the soil underneath is dark and damp, "
     "red clay smeared on the glove, cold light"),
    ("S13", "潮意新鲜", "push",
     "extreme close-up of the disturbed red soil: the damp patch glistens, freshly turned, a few pale crumbs of dry "
     "crust beside it, cold light, shallow focus"),
    ("S14", "手电继续往深处探", "push",
     "close-up: a beam of light pushed into the deep end of the open junction box, the light sinks into blackness and "
     "does not reach the bottom, dust motes, the box looks far deeper than it should"),
    ("S15", "箱里响了一声", "static",
     "static shot of the open junction box in a dark corridor, interior almost black, a thin edge of light on the rim, "
     "dust hanging still, no people"),
    ("S16", "隔了两秒", "static",
     "the same dark corridor, the open junction box barely visible, a hint of cold light on the torn latch, dust, "
     "empty space, tension, no people"),
    ("S17", "这一下他听真切了", "push",
     "the open junction box seen very close in the dark, a faint pale glimmer deep inside the box like distant screen "
     "light, dust drifting in the beam, no visible device"),
    ("S18", "握着手电的那只手", "push",
     "close-up of a gloved hand gripping a black metal flashlight, knuckles pale, grip rigid, the beam pointing away "
     "from camera onto the wall, cold light"),
    ("S19", "他在心里跟自己说", "wide",
     "medium shot: " + CHAR + " stands small in the corridor before the open junction box, a beam of light on the box, "
     "the corridor stretching into darkness around him, isolation"),
    ("S20", "然后他转头回望", "push",
     "over-the-shoulder shot from behind: " + CHAR + " turns his head back over his shoulder, face mostly in shadow, "
     "only the edge of his jaw lit, eyes searching the dark corridor behind"),
    ("S21", "身后空空荡荡", "static",
     "the empty corridor behind him: long perspective, all doors shut, dead sensor lamps, a single cold window at the "
     "end, dust, absolutely no people"),
    ("S22", "感应灯灭了", "static",
     "near-black frame: the corridor lamp has gone dark, only a faint spill of pale light on the floor and wall, "
     "shapes of doors barely legible, heavy stillness"),
    ("S23", "铁门漆皮剥落大半", "push",
     "medium shot: " + CHAR + " squeezes sideways through a heavy iron stairwell door, paint peeling off in large "
     "flakes, rust bleeding through, cold light from the corridor behind him"),
    ("S24", "楼梯间比外面更冷", "wide",
     "wide low-angle view of an old concrete stairwell, cold grey walls, iron handrail, paint flaking, empty and silent, "
     "a faint draft of dust, no people"),
    ("S25", "不是深夜那种寒凉", "push",
     "detail shot: a bare hand touches the cold painted stairwell wall, condensation and grime, fingers tense, "
     "cold blue light, the wall looks damp and chilled"),
    ("S26", "他踏上第三级台阶", "wide",
     "wide shot: " + CHAR + " stands on the third step of the stairwell, looking up; far above, a fluorescent lamp "
     "flickers on at the fourth-floor landing, cold halo in the dark"),
    ("S27", "灯管两端发黑", "push",
     "close-up of an old fluorescent tube: both ends blackened and burnt, yet it is lit, flickering cold white, "
     "dust and dead insects on the diffuser, dark ceiling around"),
    ("S28", "他咳了一声", "push",
     "medium close-up from the side: " + CHAR + " coughs into his fist, eyes narrowed, half his face in shadow, "
     "cold lamp light from above, dust in the air"),
    ("S29", "声响撞在墙面上", "static",
     "static shot of a bare corridor wall, flat painted concrete, no seams, no hollows, faint dust, cold light raking "
     "from the side, unnaturally solid and mute"),
    ("S30", "他抬手，在墙上敲了两下", "push",
     "close-up: a gloved fist knocks twice on the corridor wall, knuckles against paint, small flakes of paint falling, "
     "cold light"),
    ("S31", "墙体是实的", "push",
     "close-up: a gloved palm pressed flat against the wall, listening, fingers spread, the wall solid and cold, "
     "faint grime under the glove"),
    ("S32", "老楼的墙不该是这样", "push",
     "detail of an old wall where plaster has fallen away, revealing bundled electrical conduit and a rusted pipe "
     "inside the cavity, the hollow gap visible, cold light, no text"),
    ("S33", "他收回手", "push",
     "medium shot from behind: " + CHAR + " lowers his hand from the wall, light sweeping down toward the steps, "
     "dust in the beam, cold stairwell"),
    ("S34", "台阶正中留着一道痕迹", "wide",
     "wide shot of the stairwell steps: a dark wet drag mark runs down the centre of the steps from above, narrow, "
     "one palm wide, glistening faintly, ending at the bottom near the junction box below"),
    ("S35", "他蹲下身细看", "push",
     "medium shot: " + CHAR + " crouches at the bottom of the stairs beside the wet drag mark, light held low over "
     "the stain, one knee down, tool bag on the step"),
    ("S36", "痕迹不宽", "push",
     "close-up of the wet drag mark on a concrete step: about one palm wide, edges unnaturally neat, dark damp "
     "concrete, a few red-brown grains, cold raking light"),
    ("S37", "像是一捆线缆拖行时蹭出来的印子", "push",
     "close-up: the wet trail continues past the last step and stops exactly beneath the open junction box, "
     "the box's shadow above, damp concrete, no people"),
    ("S38", "四零四的房门紧闭", "wide",
     "wide shot: at the end of a dim old apartment corridor, one single solid dark-red steel apartment door, "
     "scratched and peeling paint, one small round peephole, a small blank nameplate above, the door seam is black, "
     "no light behind it, cold dim light, no people"),
    ("S39", "门缝不漏一点光", "push",
     "close-up of the door seam: pitch black gap, no light leaking, chipped dark red paint, cold light from the side, "
     "absolute silence"),
    ("S40", "他把手掌贴上门板", "push",
     "close-up: a gloved palm pressed flat against the cold dark-red steel door, condensation, chipped paint, "
     "the cold seeping through, no face"),
    ("S41", "他敲了两下门", "push",
     "close-up: gloved knuckles knocking twice on the dark-red steel door, paint flakes, the door seam dark, "
     "cold light from the side"),
    ("S42", "门内传来一声轻响", "static",
     "static shot of the closed dark-red steel door, the corridor dark around it, dust in the cold light, "
     "the door seam perfectly black, no people"),
    ("S43", "他顿住脚步", "push",
     "medium close-up from behind and slightly to the side: " + CHAR + " freezes before the door, fist half raised, "
     "breath held, shoulders tense, dark corridor behind"),
    ("S44", "里面再没有动静", "static",
     "the closed dark-red steel door again, utterly still, a faint scuff of dust on the floor, cold corridor light, "
     "silence"),
    ("S45", "他把耳朵凑近门缝", "push",
     "close-up: " + CHAR + " presses his ear close to the black door seam, eyes shut, jaw tight, cold light from below, "
     "face partly in shadow, tension"),
    ("S46", "门缝底下飘来一丝微风", "push",
     "macro shot near the bottom of the steel door: a bare hand back held close to the seam, a thin thread of dust "
     "drifting outward, faint moisture on the concrete, cold light"),
    ("S47", "他调出工单上的号码", "push",
     "close-up: a gloved thumb tapping a phone screen in the dark corridor, the screen glow cold on the glove, "
     "no readable content, the steel door blurred behind"),
    ("S48", "空号", "push",
     "medium close-up: " + CHAR + " holds the phone to his ear, face turned three-quarters away from camera, lit only "
     "by the cold screen and corridor light, the closed dark-red steel door behind him, silence"),
]

NUM = re.compile(r"^S\d{2}$")
