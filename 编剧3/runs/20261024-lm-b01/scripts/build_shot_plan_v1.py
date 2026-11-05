# -*- coding: utf-8 -*-
"""Build life-manual(编剧3) SHOT_PLAN v1(全集一次成型).

2026-10-24。用户授权"直接开始做直到完成"。依据 OUTLINE v1 + 锁定口播 v1(793b6a8c)。
2x2 规则(image-grid-generation.md 2026-10-19 修订):默认 2x2_tile;single 仅四类例外
(本集用:母题定装/精密结构/关键特写推近;无人物正脸类——全集无脸无手)。
视觉基线:真实摄影风夜晚住宅内景(剧本制作备注指定),四母题:钥匙盘/冰箱/夜雨窗/台灯。
i2v 仅选自然内部运动(水/汽/雨/摆/屏),全集 13 镜;其余 P1/P2 推拉。
"""
from __future__ import annotations
import hashlib, json, re
from datetime import date
from pathlib import Path

EP = Path(__file__).resolve().parents[3]
UTT = EP / "audio" / "utterances.json"
OUT = EP / "visual" / "SHOT_PLAN.json"
PROMPTS_MD = EP / "visual" / "ALL_SHOT_PROMPTS.md"
SRC = EP / "story" / "NARRATION_MASTER.md"
CPS = 3.5
GAPS = dict(head=0.3774, unit=0.19, para=0.4245, chap=0.7547)

STYLE = ("Photorealistic cinematic night-interior still, warm dim practical lamps, wood and "
         "warm-gray home tones, soft rain-light through windows, fine material detail, calm "
         "slow bedtime mood, subtle film grain. ")
BAN = ("No text, no letters, no numbers, no readable labels or screens, no watermark, no logos, "
       "no charts, no UI elements, no borders, no split screen, no collage, no faces, no hands, "
       "no people, no daylight, no bright saturated colors. ")

PALETTE = {
    "bridge":  "Dim night apartment with one warm lamp and dark blue rainy windows, quiet lived-in home",
    "ch01":    "Warm wood entryway at night, brass key tray and cream tones, gentle lamp pools, rain-wet umbrella green",
    "ch02":    "Night kitchen around a quiet white refrigerator, cool fridge light mixing with warm room tones",
    "ch03":    "Warm amber kitchen task light over wooden counter, ceramic and steel, dark rainy window beyond",
    "ch04":    "Clean cool-gray bathroom and kitchen sink tones with warm accents, water highlights in dim light",
    "ch05":    "Soft laundry-room blues and pale wood, folded fabric whites, dim utility light, faint steam",
    "ch06":    "Misty bathroom glass and humid air, blue-gray night tones, condensation highlights, gentle fog",
    "ch07":    "Warm study corner under a brass reading lamp, wooden shelves, calm tidy stillness",
    "ch08":    "Neutral warm-gray storage and shopping scenes, paper and cardboard textures, soft lamp shade",
    "ch09":    "Dark room with small cool screen glows against one warm lamp, deep night bokeh",
    "ch10":    "Deep night bedroom, low warm lamp, heavy soft textiles, rain-lit window edge, restful dimness",
    "epilogue":"Nearly dark apartment held by one low lamp and rainy window glow, black-blue calm",
}

# (id, section, beat, scene_zh, class, strategy, mode, single_category, prompt_core_en)
ROWS = [
    # ---- bridge 引入(4) ----
    ("brg-s01", "bridge", "夜雨之窗", "夜雨窗玻璃,水流痕蜿蜒,窗外城市光斑虚化,室内暗", "image_camera_motion", "P2", "single", "母题定装镜",
     "A tall night window streaked with slow rain trails, blurred blue city lights bokeh outside, dark warm room in foreground with the faint reflection of a lamp, the quiet frame of a whole evening"),
    ("brg-s02", "bridge", "回家的门厅", "暗门厅一盏暖灯,伞滴着水立在垫上,玄关轮廓", "image_camera_motion", "P1", "2x2_tile", None,
     "A dim apartment hallway at night, one warm lamp just reaching a doormat where a rain-wet dark green umbrella stands dripping, coat hooks and shoe shadows along the wall, sense of arriving home"),
    ("brg-s03", "bridge", "普通的日常", "静物小品:叠好的毛巾、碗架上倒扣的碗、一书角", "image_camera_motion", "P1", "2x2_tile", None,
     "A quiet domestic still-life cluster: neatly folded towels on a shelf, clean bowls upside down on a drying rack, the corner of a half-read book on wood, soft warm side light, ordinary things kept with care"),
    ("brg-s04", "bridge", "小事的分量", "夜厨房一角微光,远处冰箱轮廓,桌角手机充电微亮", "image_camera_motion", "P1", "2x2_tile", None,
     "A night kitchen corner in faint light, the white refrigerator silhouette glowing faintly by the doorway, a phone charging on the table edge with a soft cool glow, small domestic presences filling the dark"),
    ("brg-s05", "bridge", "从小事开始", "俯拍小物阵列:毛巾角/碗/抹布/钥匙尖", "image_camera_motion", "P1", "2x2_tile", None,
     "A soft overhead still-life grid of small domestic things on wood: the folded corner of a towel, an upturned bowl, a folded cloth, the edge of brass keys, each object given equal quiet weight, lamp warmth from one side"),
    ("brg-s06", "bridge", "今晚的房子", "从玄关望向屋内:走廊灯一盏盏远去,深处微亮", "image_camera_motion", "P2", "2x2_tile", None,
     "The view from the entry into the apartment at night: a hallway with warm lamps receding one after another toward a softly glowing living room, the whole home waiting ahead like tonight's route"),

    # ---- ch01 玄关(10) ----
    ("c1-s01", "ch01", "钥匙盘定装", "玄关柜:木托盘+黄铜钥匙串,墙上挂钩挂包", "image_camera_motion", "P2", "single", "母题定装镜",
     "An entry console in warm lamp light: a small wooden tray holding a bunch of brass keys with a dark ring, two simple wall hooks with a canvas bag, wood grain and quiet order, the anchor image of coming home"),
    ("c1-s02", "ch01", "门口的夜晚", "木地板门口,湿鞋在垫上,门缝夜色", "image_camera_motion", "P1", "2x2_tile", None,
     "Shoes on a wood-floor doormat at night, faint wet shine on their surfaces, the front door edge with a sliver of dark blue rainy night beyond, warm interior lamp glow from one side"),
    ("c1-s03", "ch01", "一秒钟的安放", "托盘近景:钥匙落在木盘里,景深虚化", "image_camera_motion", "P1", "2x2_tile", None,
     "Close view of brass keys resting in a shallow wooden tray, shallow depth of field with the dark hallway melting into warm bokeh, the small ritual of putting keys down"),
    ("c1-s04", "ch01", "早晨的翻找", "杂乱台面:信件小盒下压着的钥匙,半开的包", "image_camera_motion", "P1", "2x2_tile", None,
     "A cluttered console surface in morning-cool dim light: keys half buried under unopened mail and a small carton, a bag gaping open, mild disorder that costs time, still no readable text anywhere"),
    ("c1-s05", "ch01", "固定的住处", "墙钩上的帆布包与外套,同一位置", "image_camera_motion", "P2", "2x2_tile", None,
     "A calm wall of two sturdy hooks holding a canvas shoulder bag and a soft grey coat at night, exactly where they always live, warm pool of lamp light, wood floor shadow below"),
    ("c1-s06", "ch01", "暂住的小盒", "门口小纸盒:票据回执叠放(字迹全虚化)", "image_camera_motion", "P1", "2x2_tile", None,
     "A small open cardboard box on the entry shelf holding a few paper receipts and tickets with completely soft blurred strokes, a pencil resting beside, a waiting-room for undecided things"),
    ("c1-s07", "ch01", "湿物晾开", "门边敞开的伞面水珠,通风的鞋", "image_camera_motion", "P1", "2x2_tile", None,
     "An opened dark green umbrella leaning to dry beside the door, fine water beads on its canopy, wet shoes airing on newspaper with gentle ventilation space, dampness given somewhere to leave"),
    ("c1-s08", "ch01", "秩序的玄关", "从屋内看玄关:灯、托盘、挂钩,一切归位", "image_camera_motion", "P2", "2x2_tile", None,
     "The entry corner seen from inside the quiet apartment at night: lamp, key tray, hooks and doormat each in place, warm light fading into the dark hallway beyond, small stable order"),
    ("c1-s09", "ch01", "水珠滑落", "伞面上水珠缓缓下滑,其余静止", "image_to_video", "V1", "2x2_tile", None,
     "Macro view of fine rain droplets on dark green umbrella fabric, a few beads slowly sliding down and merging, everything else perfectly still, dim warm light from the side"),
    ("c1-s10", "ch01", "走向厨房", "暗走廊尽头厨房微光,冰箱轮廓发光", "image_camera_motion", "P1", "2x2_tile", None,
     "A dark hallway leading toward the kitchen where a faint glow outlines the white refrigerator by the counter, the next room waiting quietly at night"),


    ("c1-s11", "ch01", "钥匙的第二眼", "木盘近景另一构图:黄铜钥匙与门禁卡并排", "image_camera_motion", "P1", "2x2_tile", None,
     "A closer alternate angle of the wooden entry tray: brass keys lying beside a plain access card, wood grain warm under lamp light, the same home seen twice"),
    ("c1-s12", "ch01", "门垫的夜", "椰棕门垫特写,纤维上一点湿意,灯光斜照", "image_camera_motion", "P1", "2x2_tile", None,
     "Macro shot of a coir doormat at night, damp sheen on coarse fibers, warm lamp light raking low across, the threshold that catches everything"),

    ("c1-s13", "ch01", "鞋柜里的秩序", "鞋柜一层:两双鞋摆正,格内干净", "image_camera_motion", "P2", "2x2_tile", None,
     "One shelf of the shoe cabinet holding two pairs set straight with breathing room between, wood interior clean and dim, small civilized geometry"),
    # ---- ch02 冰箱(11) ----
    ("c2-s01", "ch02", "安静的白色箱子", "夜里关着的白色冰箱,厨房暗", "image_camera_motion", "P2", "2x2_tile", None,
     "A white single-door refrigerator standing closed in a dim night kitchen, its clean rounded surface catching one warm lamp edge, dark rainy window behind, reliable and quiet like a sleeping box"),
    ("c2-s02", "ch02", "开门的光", "冰箱开门:暖白内灯,玻璃盒排列,冷雾", "image_to_video", "V1", "single", "精密结构",
     "An open refrigerator at night, warm interior light on glass storage containers neatly on shelves, a faint wisp of cold vapor drifting slowly near the lower shelf, everything else still"),
    ("c2-s03", "ch02", "玻璃盒", "冷藏层:玻璃保鲜盒带盖,食物整齐", "image_camera_motion", "P1", "2x2_tile", None,
     "Two shelves of clear glass containers with lids holding simple leftovers, arranged with small gaps for air, condensation dots on the glass, cool fridge light from the side"),
    ("c2-s04", "ch02", "浅盘散热", "台面上的浅口干净容器盛着剩食,微弱热气", "image_camera_motion", "P1", "2x2_tile", None,
     "A shallow wide clean container of warm rice and dishes set on the wooden counter near the fridge, one thin wisp of steam rising, a ladle resting, food on its way to being chilled quickly"),
    ("c2-s05", "ch02", "生熟各就位", "冰箱下层:密封盒装的生肉在下,蔬果在上层", "image_camera_motion", "P1", "2x2_tile", None,
     "Inside the fridge: a sealed leak-proof clear box holding raw chicken resting on the lowest shelf, washed fruit in an open bowl on the shelf above, safe separation visible in placement"),
    ("c2-s06", "ch02", "小标签", "容器盖上贴空白质感小标签,铅笔在旁(无可读字)", "image_camera_motion", "P2", "2x2_tile", None,
     "A small blank paper label with soft unreadable pencil strokes taped on a glass container lid, a short pencil lying on the fridge shelf beside, the habit of remembering without readable words"),
    ("c2-s07", "ch02", "真实的温度", "架上挂一只冰箱温度计,表盘虚化无数字", "image_camera_motion", "P1", "2x2_tile", None,
     "A small round refrigerator thermometer hanging beside a shelf, its dial face softly out of focus with no readable numbers, glass containers blurred behind, cool light and honest instruments"),
    ("c2-s08", "ch02", "被忘记的角落", "门格深处一小瓶酱料被新买的菜挡住", "image_camera_motion", "P1", "2x2_tile", None,
     "Deep in the fridge door rack a small jar of sauce hidden behind newer grocery bags of vegetables, half forgotten in shadow, the quiet corner where food goes to be lost"),
    ("c2-s09", "ch02", "先吃这里", "前层显眼处摆着临近食用的食材,后面留空", "image_camera_motion", "P2", "2x2_tile", None,
     "The front edge of a fridge shelf holding tomorrow's ingredients clearly in reach, a cleared space behind them, an eat-first zone made visible by simple placement"),
    ("c2-s10", "ch02", "空气要流动", "七八分满的冰箱,食物之间有空隙", "image_camera_motion", "P1", "2x2_tile", None,
     "A moderately filled refrigerator interior with visible air gaps between containers, cold light falling through open space, not packed tight, breathing room kept on purpose"),
    ("c2-s11", "ch02", "合门之后", "冰箱合上,厨房只剩一点指示微光", "image_camera_motion", "P2", "2x2_tile", None,
     "The refrigerator door closed again in the dark kitchen, only a faint indicator point of light, the room settling back into night quiet, decisions made and containers sleeping"),


    ("c2-s12", "ch02", "冷冻层的呼吸", "冷冻抽屉拉开,白色冷气极淡地漫出", "image_camera_motion", "P1", "2x2_tile", None,
     "A freezer drawer pulled open with a faint wisp of cold air sliding over its rim, frost-white interior against dim kitchen night, quiet exhale of a cold place"),
    ("c2-s13", "ch02", "分装两盒", "两只浅盒分装的剩菜并排,一深一浅", "image_camera_motion", "P2", "2x2_tile", None,
     "Two shallow glass containers of leftovers packed side by side on the counter, one fuller one lighter, lids resting at an angle, the tidy arithmetic of not wasting food"),
    ("c2-s14", "ch02", "门格的秩序", "冰箱门内侧格子里调味瓶高低排列", "image_camera_motion", "P1", "2x2_tile", None,
     "The fridge door's inner racks holding small jars and bottles arranged by height, labels turned to soft blur, cool light grazing glass, a small library of flavors"),
    ("c2-s15", "ch02", "保鲜抽屉", "果蔬抽屉半开:青椒与苹果安稳躺着", "image_camera_motion", "P2", "2x2_tile", None,
     "A half-open crisper drawer with a green pepper and an apple resting among soft leaves, humidity beads on the drawer wall, produce sleeping in its cool drawer"),

    ("c2-s16", "ch02", "冰箱的头顶", "冰箱顶上放一只藤编收纳篮,墙上挂历虚化", "image_camera_motion", "P1", "2x2_tile", None,
     "The top of the refrigerator with a woven basket of seldom-used things resting on it, a blurred calendar shape on the wall beyond, the appliance as furniture"),
    # ---- ch03 厨房(11) ----
    ("c3-s01", "ch03", "夜厨房全景", "料理台、砧板、刀架、暖光,雨夜窗外", "image_camera_motion", "P2", "2x2_tile", None,
     "A night kitchen wide view: wooden counter with a clean cutting board, a knife block, ceramic bowls, warm amber task light, dark rainy window above the sink, the quiet stage of cooking"),
    ("c3-s02", "ch03", "清水冲果", "水流过滤网里的番茄,水珠溅细", "image_to_video", "V1", "2x2_tile", None,
     "Clear water streaming steadily over ripe tomatoes resting in a steel colander, fine splashes catching warm light, water running off and draining, everything gentle and slow"),
    ("c3-s03", "ch03", "生肉不冲洗", "陶瓷盘上完整的生鸡肉,旁边干燥的水槽", "image_camera_motion", "P1", "2x2_tile", None,
     "Raw chicken pieces whole on a ceramic plate beside an empty dry sink, deliberately not under the tap, a clean calm counter, the safety of leaving it unwashed"),
    ("c3-s04", "ch03", "两块砧板", "并排两块砧板:一块沾生肉痕迹,一块干净待切水果", "image_camera_motion", "P1", "2x2_tile", None,
     "Two wooden cutting boards side by side on the counter: one bearing faint raw-meat juices and moving to the sink, the other clean with a whole fruit waiting, roles kept apart"),
    ("c3-s05", "ch03", "刀痕深处", "用旧的砧板特写:深深浅浅的刀痕纹理", "image_camera_motion", "P1", "2x2_tile", None,
     "Close texture of a well-used wooden cutting board, many deep and shallow knife grooves crossing like tree rings, warm side light raking across, history of a thousand meals"),
    ("c3-s06", "ch03", "洗手的一刻", "水龙头细流+皂液瓶,不锈钢槽反光(无手)", "image_camera_motion", "P2", "2x2_tile", None,
     "A fine steady stream from the kitchen tap with a soap dispenser standing ready on the steel sink edge, soft reflections on brushed metal, the plain honest moment before touching food"),
    ("c3-s07", "ch03", "先备后火", "料理台一字排开的备料小碗与厨具", "image_camera_motion", "P1", "2x2_tile", None,
     "Mise en place on the wooden counter: small bowls of prepped vegetables, sliced aromics and seasonings in a neat line, spatula and plates standing ready, everything arranged before the flame"),
    ("c3-s08", "ch03", "中心温度", "食物温度计插进烤鸡腿,表盘无数字", "image_camera_motion", "P1", "2x2_tile", None,
     "A food thermometer probe inserted into a golden roasted chicken thigh on a pan, its dial face angled away unreadable, soft steam, warm kitchen light, trust placed in the center of the meat"),
    ("c3-s09", "ch03", "锅上的汽", "锅中蒸汽缓缓上升,盖子斜搭", "image_to_video", "V1", "2x2_tile", None,
     "Soft steam rising continuously from a pot on the stove with its lid ajar, wisps curling upward through warm amber light, handles and tiles still, only the vapor moving slowly"),
    ("c3-s10", "ch03", "洗好的碗", "碗架上倒扣沥干的碗,夜灯下整齐", "image_camera_motion", "P1", "2x2_tile", None,
     "Washed bowls and plates upside down drying on a rack at night, water droplets gathered at edges, warm lamp behind making the ceramics glow, the meal responsibly finished"),
    ("c3-s11", "ch03", "从容的收尾", "收拾后的料理台:一盏灯、一杯水、静", "image_camera_motion", "P2", "2x2_tile", None,
     "The kitchen after cooking, counter wiped clean, one glass of water on the wood under a single warm light, dimness beyond, the calm of a meal taken in good order"),


    ("c3-s12", "ch03", "一枚蛋", "小碗里一枚完整生蛋,瓷白对深色台面", "image_camera_motion", "P1", "2x2_tile", None,
     "A single raw egg resting in a small ceramic bowl on dark wood counter, shell glow under warm task light, complete and unhurried"),
    ("c3-s13", "ch03", "待命的厨具", "锅铲汤勺一排挂在灶台边挂钩", "image_camera_motion", "P1", "2x2_tile", None,
     "A row of kitchen tools hanging from a rail beside the stove, spatula ladle and tongs in order, steel catching warm light, instruments ready before the fire"),
    ("c3-s14", "ch03", "干净的水槽", "不锈钢水槽与滤网,残余水珠将干", "image_camera_motion", "P2", "2x2_tile", None,
     "A clean stainless sink with its strainer emptied, last water drops about to dry, dark rainy window reflected faintly in the metal, the kitchen closing its eyes"),

    ("c3-s15", "ch03", "刀在木架上", "木质刀架里的两把刀,刃口向下", "image_camera_motion", "P2", "2x2_tile", None,
     "Two knives resting blade-down in a wooden knife block on the counter, steel sheen under warm light, edges safely asleep"),
    ("c3-s16", "ch03", "瓷盘叠放", "干净瓷盘三只叠起,边缘一线光", "image_camera_motion", "P1", "2x2_tile", None,
     "Three clean ceramic plates stacked with a soft rim of light between each, glaze catching the amber task lamp, a small tower of ready"),
    # ---- ch04 清洁(11) ----
    ("c4-s01", "ch04", "三种脏", "三联小品:灶上油斑/龙头水垢/架上一层灰", "image_camera_motion", "P2", "2x2_tile", None,
     "A triptych-like domestic still life: a greasy shimmer spot on the stovetop, white limescale crust ringing the faucet, a fine layer of dust on a shelf edge, three different kinds of dirty in dim light"),
    ("c4-s02", "ch04", "一滴洗洁精", "海绵上一滴洗洁精与细泡沫", "image_camera_motion", "P1", "2x2_tile", None,
     "A drop of dish soap on a damp kitchen sponge with fine bubbles beginning to form, macro warmth, wood counter blurred behind, chemistry doing quiet work"),
    ("c4-s03", "ch04", "白色的垢", "龙头出水口白色矿物垢特写", "image_camera_motion", "P1", "2x2_tile", None,
     "Extreme close view of white mineral limescale crusting a chrome faucet aerator, hard water deposits in pale patterns, cool bathroom light, patience required"),
    ("c4-s04", "ch04", "湿布集尘", "半擦过的搁板:一半干净一半浮灰,微湿抹布搭在旁", "image_camera_motion", "P1", "2x2_tile", None,
     "A half-dusted shelf in one frame: one end clean and dark wood, the other end still holding a fine grey film, a slightly damp cloth resting at the boundary, dust collected not scattered"),
    ("c4-s05", "ch04", "各司其职", "清洁提篮:几瓶清洁剂分开放好", "image_camera_motion", "P1", "2x2_tile", None,
     "A cleaning caddy on the floor with a few bottles standing apart from each other, each shape and color muted, brushes folded in their own slot, products that keep their own company"),
    ("c4-s06", "ch04", "不混合", "一瓶漂白剂单独放在独立小篮,与其他瓶分开", "image_camera_motion", "P2", "2x2_tile", None,
     "One white bleach bottle standing alone inside a separate small basket at the cabinet's far end, other cleaning bottles grouped elsewhere, a quiet deliberate distance between them"),
    ("c4-s07", "ch04", "读它的说明", "瓶身标签特写:完全虚化的字块与色带", "image_camera_motion", "P1", "2x2_tile", None,
     "Close view of a cleaning bottle's label rendered as completely soft blurred color blocks and unreadable shapes, fingers of warm light on the plastic, instructions honored without being read here"),
    ("c4-s08", "ch04", "抹布晾干", "抹布平整搭在横杆上通风,不再团着", "image_camera_motion", "P1", "2x2_tile", None,
     "Clean rags hung flat and open over a rail above the sink to air-dry, no longer crumpled, faint window light, different colors for different duties kept apart"),
    ("c4-s09", "ch04", "今天的一小块", "擦净的一小块桌面,其余仍暗着", "image_camera_motion", "P2", "2x2_tile", None,
     "One freshly wiped patch of tabletop reflecting warm lamplight while the rest of the room stays dim and untouched, a small completed victory, enough for tonight"),
    ("c4-s10", "ch04", "水流带走泡沫", "水冲过盘碟,泡沫渐渐散去", "image_to_video", "V1", "2x2_tile", None,
     "Warm water rinsing over stacked plates with white foam slowly dissolving and sliding off, water running clear in the steel sink, steady gentle motion, dishes coming clean"),
    ("c4-s11", "ch04", "工具归位", "清洁用品收进柜内,夜里的房间安顿", "image_camera_motion", "P1", "2x2_tile", None,
     "The cleaning caddy tucked back inside a closed cupboard, hallway quiet at night, one lamp low, today's small mess not traveling to tomorrow"),


    ("c4-s12", "ch04", "拖把歇着", "拖把斜倚墙角,桶里水已清", "image_camera_motion", "P1", "2x2_tile", None,
     "A mop leaning against the corner wall above its bucket of clear water, floor around it damp-shining and done, tools at rest after work"),
    ("c4-s13", "ch04", "瓷砖的水珠", "浴室白瓷砖上几颗水珠缓慢待干", "image_camera_motion", "P1", "2x2_tile", None,
     "Several clear water droplets on pale bathroom tiles slowly drying at their own pace, soft light pooling in each bead, patience made visible"),
    ("c4-s14", "ch04", "海绵的家", "两块海绵立在皂液架上前倾靠着", "image_camera_motion", "P2", "2x2_tile", None,
     "Two sponges propped upright to dry on a soap dish rack, one for dishes one for surfaces, tilted together like colleagues off duty"),

    ("c4-s15", "ch04", "纸巾架", "厨房纸巾架上卷纸垂下一角", "image_camera_motion", "P1", "2x2_tile", None,
     "A kitchen roll holder with paper towel hanging one folded corner, chrome post in dim warm light, ordinary provision standing by"),
    ("c4-s16", "ch04", "空着的桶", "清洁桶倒扣沥干,搁在瓷砖角", "image_camera_motion", "P2", "2x2_tile", None,
     "A cleaning bucket turned upside down to drip-dry in the tiled corner, water beading off its rim, the pause between cleans"),
    # ---- ch05 洗衣(10) ----
    ("c5-s01", "ch05", "洗衣角", "夜里洗衣区的滚筒洗衣机与置物架", "image_camera_motion", "P2", "2x2_tile", None,
     "A front-loading washing machine in a dim utility corner at night, soft blue-grey machine light on the round door, detergent shelf and folded cloths beside, laundry day at its quietest"),
    ("c5-s02", "ch05", "滚筒转动", "滚筒内衣物随筒缓缓翻滚", "image_to_video", "V1", "single", "精密结构",
     "Inside the washing machine drum: clothes and soft water tumbling slowly in rotation behind the round glass door, suds and fabric moving gently, steady machine calm, no spinning blur"),
    ("c5-s03", "ch05", "不多的一勺", "量杯里浅浅的洗衣液,瓶立在旁", "image_camera_motion", "P1", "2x2_tile", None,
     "A measuring cup holding only a shallow pour of liquid detergent beside the bottle on the machine top, the modest right amount, soft light on amber liquid, restraint as method"),
    ("c5-s04", "ch05", "洗护标签", "衣物内标特写:只有符号,无可读文字", "image_camera_motion", "P1", "2x2_tile", None,
     "Macro shot of a garment care label showing only woven pictogram symbols, no readable characters, fabric texture and stitching in soft focus, the small tag worth a glance"),
    ("c5-s05", "ch05", "深浅分开", "两只洗衣篮:深色一堆,浅色一堆", "image_camera_motion", "P1", "2x2_tile", None,
     "Two woven laundry baskets side by side at night: one holding dark jeans and navy shirts, the other pale whites and light greys, the sorting done before any water runs"),
    ("c5-s06", "ch05", "洗衣袋", "网袋里的针织衫,拉链收口", "image_camera_motion", "P1", "2x2_tile", None,
     "A soft grey knit sweater folded inside a white mesh laundry bag, zip closed, resting on the machine, delicate protection for fragile stitches"),
    ("c5-s07", "ch05", "留出风的缝", "晾衣杆上衬衫间隔挂着,空气能穿过", "image_camera_motion", "P2", "2x2_tile", None,
     "Shirts hanging on an indoor drying rack with clear hand-width gaps between them, air able to pass through, faint window light behind the fabric, drying given room to happen"),
    ("c5-s08", "ch05", "衬衫轻摆", "白衬衫在衣架上极缓地轻摆", "image_to_video", "V1", "2x2_tile", None,
     "A white shirt on a wooden hanger swaying almost imperceptibly in a slow air current, fabric breathing in and out, everything else still, dim warm room behind"),
    ("c5-s09", "ch05", "毛巾展开", "毛巾平整搭在杆上晾干,角落有团着的旧巾对比", "image_camera_motion", "P1", "2x2_tile", None,
     "A towel stretched flat and open over a bar drying evenly in moving air, while in the shadowed corner an old crumpled damp towel sits rolled tight, two futures for the same cloth"),
    ("c5-s10", "ch05", "机器的保养", "洗衣机门封胶圈与洗涤剂盒特写,干净", "image_camera_motion", "P1", "2x2_tile", None,
     "Close view of the washing machine door gasket and the pulled-out detergent drawer, both clean and dry, faint blue machine light, the machine itself cared for"),


    ("c5-s11", "ch05", "空了的篮", "洗衣篮空了,歪在洗衣机旁", "image_camera_motion", "P2", "2x2_tile", None,
     "An empty laundry basket resting tilted beside the washing machine, its woven shadow long in utility light, the day's washing all sent out into the air"),
    ("c5-s12", "ch05", "叠好的衬衫", "叠好的衬衫两件在搁板上,领口整齐", "image_camera_motion", "P1", "2x2_tile", None,
     "Two folded shirts stacked neatly on an open shelf, collars aligned, fabric soft in dim warm light, laundry that made it all the way home"),
    ("c5-s13", "ch05", "完成的灯", "洗衣机完成指示的小灯静静亮着", "image_camera_motion", "P1", "2x2_tile", None,
     "The washing machine's small done-indicator light glowing steady in the dim utility corner, drum still behind glass, a quiet announcement nobody needs to hear twice"),

    ("c5-s14", "ch05", "晾衣夹的布袋", "挂着的布袋里插满木夹", "image_camera_motion", "P1", "2x2_tile", None,
     "A cloth bag hanging on the drying rack filled with wooden clothespins, a few clipped to its edge, utility corner in dim light"),
    ("c5-s15", "ch05", "第二根杆", "另一根晾杆上搭着浴巾,留空一半", "image_camera_motion", "P2", "2x2_tile", None,
     "A second drying rail with one bath towel folded over it and half the rod left empty for air, window glow behind, room to spare on purpose"),
    # ---- ch06 空气(8) ----
    ("c6-s01", "ch06", "镜上的雾", "夜浴室镜子蒙着水汽,水痕蜿蜒", "image_camera_motion", "P2", "2x2_tile", None,
     "A bathroom mirror at night fogged with vapor, slow condensation trails wandering down the glass, a warm bulb glowing at the frame edge, humid blue-grey air"),
    ("c6-s02", "ch06", "水汽成珠", "玻璃上小水珠渐凝并缓缓滑下", "image_to_video", "V1", "2x2_tile", None,
     "On a cool glass surface small condensation droplets slowly growing, merging and sliding downward leaving clear trails, fog thickening at the edges, utterly calm and slow"),
    ("c6-s03", "ch06", "湿度计", "墙上一只机械湿度计,表盘虚化无数字", "image_camera_motion", "P1", "2x2_tile", None,
     "A round analog hygrometer hanging on a pale wall, its dial soft and unreadable, needle at rest, bathroom tile catching cool light, feeling measured instead of guessed"),
    ("c6-s04", "ch06", "排风扇", "浴室排风扇格栅特写,安静", "image_camera_motion", "P1", "2x2_tile", None,
     "A bathroom exhaust fan grille in slight low-angle view, clean slats, soft ambient hum implied by stillness, steam threaded faintly toward it in the dim light"),
    ("c6-s05", "ch06", "窗台的积水", "窗框上一线积水映着夜色,雨点落痕", "image_camera_motion", "P1", "2x2_tile", None,
     "A windowsill at night holding a thin line of pooled rainwater reflecting blue window light, droplet paths down the glass above, the small plumbing of a rainy evening"),
    ("c6-s06", "ch06", "墙角的潮痕", "墙角一小片淡淡的水痕阴影,极轻", "image_camera_motion", "P1", "2x2_tile", None,
     "A faint damp shadow blooming subtly on a wall corner near the skirting, paint slightly darker, nothing dramatic, moisture leaving its quiet signature"),
    ("c6-s07", "ch06", "窗帘呼吸", "纱帘在微风里极缓地鼓动", "image_to_video", "V1", "2x2_tile", None,
     "A sheer white curtain breathing in and out very slowly by a cracked night window, fabric swelling and settling like sleep, dark blue outside, gentle and hypnotic"),
    ("c6-s08", "ch06", "雾散之后", "窗上雾气渐散,屋内回暖的夜", "image_camera_motion", "P2", "2x2_tile", None,
     "The window fog thinning at the edges, room beyond warm and dim, rain trails outside slowing, air finding its way out and the room settling into comfort"),


    ("c6-s09", "ch06", "门半开", "浴室门半开着,雾气正往外走", "image_camera_motion", "P2", "2x2_tile", None,
     "A bathroom door left half open after a shower, faint vapor drifting out into the darker hallway, lamp glow meeting mist, humidity given an exit"),
    ("c6-s10", "ch06", "窗台绿植", "窗台上一小盆绿植,叶面有潮气", "image_camera_motion", "P1", "2x2_tile", None,
     "A small potted plant on a windowsill at night, faint moisture on its leaves, rain window behind it blurred blue, something alive keeping the air company"),

    ("c6-s11", "ch06", "毛巾架", "浴室毛巾架上两巾分层搭开", "image_camera_motion", "P1", "2x2_tile", None,
     "A bathroom towel rail with two towels hung flat on separate levels, both dry and open to the air, tiles cool and quiet"),
    ("c6-s12", "ch06", "排水的低语", "地漏格栅安静,边上一圈浅水痕", "image_camera_motion", "P1", "2x2_tile", None,
     "A bathroom floor drain grille at rest with a faint ring of dried water around it, tile light soft, everything finding its way down and out"),
    # ---- ch07 收纳(8) ----
    ("c7-s01", "ch07", "桌面定装", "台灯下的书桌:半读的书、笔、充电线、几页纸", "image_camera_motion", "P2", "single", "母题定装镜",
     "A wooden desk under a warm brass reading lamp at night: a half-read book face down, one pen, a charging cable coiled, a few blank papers, the honest archeology of an evening"),
    ("c7-s02", "ch07", "塞进去的整齐", "抽屉半开:挤满缠在一起的杂物", "image_camera_motion", "P1", "2x2_tile", None,
     "A half-open drawer packed tight with tangled cables, adapters and small tools, everything wedged, a clean surface bought by hiding, warm light raking the mess"),
    ("c7-s03", "ch07", "常用的近处", "剪刀插在桌边专属小筒里,伸手可及", "image_camera_motion", "P1", "2x2_tile", None,
     "Scissors standing in a small dedicated cup at the desk's near corner, within arm's reach, warm lamp glow on steel blades, the daily tool living where the hand expects it"),
    ("c7-s04", "ch07", "不常用的远处", "高柜顶层:收起来的旧纸箱与储物盒", "image_camera_motion", "P1", "2x2_tile", None,
     "The top shelf of a tall cabinet holding folded old cartons and sealed storage boxes far above daily reach, dim and patient, things that wait years between uses"),
    ("c7-s05", "ch07", "就三类", "架上三只筐:常用/偶尔/暂存", "image_camera_motion", "P1", "2x2_tile", None,
     "A shelf with exactly three woven bins in a row, one holding daily essentials, one occasional tools, one papers waiting to be decided, a system small enough to keep"),
    ("c7-s06", "ch07", "留一块空白", "桌面中央空着,只有灯与一本书在角上", "image_camera_motion", "P2", "2x2_tile", None,
     "The desk with its middle left deliberately empty, warm lamp at one corner and a single closed book at the other, bare wood breathing in between, space kept for tomorrow"),
    ("c7-s07", "ch07", "原位太远", "深柜里需要搬开两盒才能拿到的位置", "image_camera_motion", "P1", "2x2_tile", None,
     "Inside a deep cabinet: two stacked boxes blocking a small item pushed far back in shadow, the effort of retrieval visible in geometry, a home that argues with habit"),
    ("c7-s08", "ch07", "生活的痕迹", "沙发上搭着毯子,书翻开扣着,半杯水", "image_camera_motion", "P2", "2x2_tile", None,
     "A lived-in corner: soft blanket draped over the sofa arm, a book left open face-down on the cushion, a half-finished glass of water on the side table, warm low light, a home allowed to look inhabited"),


    ("c7-s09", "ch07", "书架一角", "书架一角:竖排的书与一只小木盒", "image_camera_motion", "P2", "2x2_tile", None,
     "One shelf corner with books standing upright beside a small wooden box, warm brass lamp light catching paper edges, a tidy paragraph of a room"),
    # ---- ch08 购物(8) ----
    ("c8-s01", "ch08", "三把一样的", "抽屉里并排三件几乎相同的小工具", "image_camera_motion", "P1", "2x2_tile", None,
     "A drawer lying open with three nearly identical small metal utility tools resting side by side, their similarities almost comic in the warm light, purchases that forgot each other"),
    ("c8-s02", "ch08", "想象中的生活", "墙角堆着纸箱,一只还未拆封", "image_camera_motion", "P2", "2x2_tile", None,
     "A quiet corner where cardboard boxes stack, one still sealed with tape unbroken, soft lamplight on the flaps, the imagined life inside still waiting"),
    ("c8-s03", "ch08", "一张清单", "冰箱贴着小记事本与铅笔(笔画全虚化)", "image_camera_motion", "P1", "2x2_tile", None,
     "A small notepad pinned to the refrigerator door beside a hanging pencil, its pages holding only soft unreadable pencil strokes, a list that saves trips, gentle kitchen light"),
    ("c8-s04", "ch08", "库存一眼", "储物架上常备品排得清楚,缺不缺一眼看出", "image_camera_motion", "P1", "2x2_tile", None,
     "A pantry shelf with staples lined in loose rows, grains and paper goods at a glance, one obvious gap where something runs out, inventory visible without opening anything"),
    ("c8-s05", "ch08", "真正的单价", "货架价签特写:完全虚化的色块", "image_camera_motion", "P1", "2x2_tile", None,
     "Close view of shelf price tags as pure blurred color blocks with no readable figures, products standing behind them in soft focus, arithmetic happening somewhere calmer"),
    ("c8-s06", "ch08", "大与小", "台面上一大一小两只瓶子并立", "image_camera_motion", "P1", "2x2_tile", None,
     "Two bottles side by side on the counter, one large one small, warm light questioning which truly costs less, simple comparison still life"),
    ("c8-s07", "ch08", "要出门的袋子", "门边备好的购物布袋,钥匙盘在旁", "image_camera_motion", "P2", "2x2_tile", None,
     "A folded canvas shopping tote ready by the door near the key tray, night rain coat hanging behind, the next errand already half prepared"),
    ("c8-s08", "ch08", "从容的抽屉", "收好的抽屉:只留一把工具,躺在分隔格里", "image_camera_motion", "P2", "2x2_tile", None,
     "The drawer closed and at peace, one small tool resting in a felt-lined compartment, two outlines in the fabric where brothers once lay, warm wood and knowing what you own"),


    ("c8-s09", "ch08", "带回来的菜", "布袋口露出青椒与纸包的面包", "image_camera_motion", "P1", "2x2_tile", None,
     "A canvas tote on the counter with a green pepper and a paper-wrapped loaf peeking from its open mouth, shopping just home in warm light"),
    ("c8-s10", "ch08", "软木小板", "墙上一块软木留言板,夹着几张空白纸条", "image_camera_motion", "P1", "2x2_tile", None,
     "A small cork board on the kitchen wall holding a few blank paper notes and a receipt with unreadable soft strokes, one corner curled, thoughts parked for later"),
    # ---- ch09 手机(9) ----
    ("c9-s01", "ch09", "充电的手机", "床头柜上充电的手机,屏上柔光图形", "image_camera_motion", "P2", "2x2_tile", None,
     "A phone charging on a wooden nightstand at night, its screen showing only a soft abstract glow of blurred shapes, cable curling to the socket, dark bedroom bokeh behind"),
    ("c9-s02", "ch09", "屏幕暗下去", "手机屏光缓缓变暗直到熄灭", "image_to_video", "V1", "2x2_tile", None,
     "A phone screen glowing softly then slowly dimming down to dark over several seconds, its light halo shrinking gently on the wooden surface, room barely changing, a device going to sleep"),
    ("c9-s03", "ch09", "安静的通知", "暗木桌上的手机,只有一枚微小呼吸灯", "image_camera_motion", "P1", "2x2_tile", None,
     "A dark phone lying on wood in a dim room, one tiny notification light breathing alone, everything else silent, the night keeping only what matters"),
    ("c9-s04", "ch09", "另一份存在", "外置硬盘与手机并放,备份的形状", "image_camera_motion", "P1", "2x2_tile", None,
     "A small external hard drive sitting beside the phone on the desk, its quiet LED steady, two devices like original and echo, warm lamp and cool glow sharing the frame"),
    ("c9-s05", "ch09", "钥匙的规矩", "玄关钥匙盘近景重现,手机放在钥匙旁", "image_camera_motion", "P2", "single", "关键特写推近",
     "The entry key tray seen again up close at night, brass keys in the wooden tray and a phone resting right beside them, warm lamp glow, important things knowing where they live"),
    ("c9-s06", "ch09", "陌生的光", "屏上一条模糊的链接状光条,无字可读", "image_camera_motion", "P1", "2x2_tile", None,
     "A dark screen showing one soft elongated glow bar like an unread message with a faint link-shaped shimmer, everything unreadable, curiosity and caution balanced in blue light"),
    ("c9-s07", "ch09", "各管各的锁", "抽屉里一本上了小锁的皮面小册", "image_camera_motion", "P1", "2x2_tile", None,
     "A small leather booklet closed with a tiny brass lock resting in a desk drawer, different keys for different doors implied, warm wood, secrets kept responsibly"),
    ("c9-s08", "ch09", "离床远一点", "手机放在房间另一头的矮柜上充电", "image_camera_motion", "P1", "2x2_tile", None,
     "A phone charging on a low dresser at the far side of the dark bedroom, bed soft and distant in the background, a small distance that protects sleep"),
    ("c9-s09", "ch09", "灯还亮着", "台灯与暗屏手机,夜深了", "image_camera_motion", "P2", "2x2_tile", None,
     "The brass desk lamp still warm over the now-dark phone, room folding into night, one pool of light holding the desk, digital life safely asleep"),


    ("c9-s10", "ch09", "路由器的夜", "暗处路由器指示灯几粒微光", "image_camera_motion", "P1", "2x2_tile", None,
     "A router in the dark corner with a few tiny lights breathing, room black around it, the invisible plumbing of the night internet"),
    ("c9-s11", "ch09", "盘好的线", "充电线整齐盘在浅木碟里", "image_camera_motion", "P1", "2x2_tile", None,
     "A charging cable coiled neatly in a shallow wooden dish beside the bed, no tangle, lamp light warm on the weave, small engineering before sleep"),

    ("c9-s12", "ch09", "插线板", "床头插线板两枚插头,其余空着", "image_camera_motion", "P2", "2x2_tile", None,
     "A small power strip by the bed with exactly two plugs in use and the rest empty, cable dressed along the wall, minimal electric life"),
    ("c9-s13", "ch09", "耳机的窝", "无线耳机盒合着,躺在书旁", "image_camera_motion", "P1", "2x2_tile", None,
     "A closed wireless earbuds case resting beside a book on the nightstand, its small LED dark, sounds put away for the night"),
    # ---- ch10 睡前(10) ----
    ("c10-s01", "ch10", "卧室的门", "从门口看卧室:床、低灯、夜静", "image_camera_motion", "P2", "2x2_tile", None,
     "The bedroom seen from its doorway at night: bed made, one low lamp, curtains drawn, deep quiet, the last room of the evening waiting"),
    ("c10-s02", "ch10", "明天的衣服", "椅背上搭好的一身明天衣服", "image_camera_motion", "P1", "2x2_tile", None,
     "Tomorrow's clothes laid neatly over a chair back: soft shirt, trousers folded once, socks tucked at the edge, warm low light, the morning already cared for"),
    ("c10-s03", "ch10", "收好的包", "床头收好的包立在地板上", "image_camera_motion", "P1", "2x2_tile", None,
     "A packed bag standing closed on the bedroom floor by the dresser, strap coiled, keys already in it, night lamp glow along its canvas edge"),
    ("c10-s04", "ch10", "一件重要的小事", "床头小本子摊开,柔软铅笔痕(不可读),笔搁上", "image_camera_motion", "P1", "2x2_tile", None,
     "A small notebook open on the nightstand with one line of soft unreadable pencil strokes and the pencil resting in the fold, one important thing noted for tomorrow, lamp light low"),
    ("c10-s05", "ch10", "床头三件", "一杯水、一本合上的书、一盏灯", "image_camera_motion", "P2", "single", "关键特写推近",
     "The nightstand's three quiet residents in one frame: a glass of water catching lamplight, a closed book, the warm brass lamp above them, the complete equipment of a good night"),
    ("c10-s06", "ch10", "挡住光", "厚窗帘拉拢,只余一线极暗的夜光边", "image_camera_motion", "P1", "2x2_tile", None,
     "Heavy curtains drawn closed across the bedroom window, only a hairline of deep blue night light at their meeting edge, the room kept soft and dark"),
    ("c10-s07", "ch10", "床在等", "枕头拍松,被角翻开一角", "image_camera_motion", "P2", "2x2_tile", None,
     "The bed ready: pillows plumped and slightly dented, duvet corner folded back in invitation, low warm light from the nightstand, sleep arranged and waiting"),
    ("c10-s08", "ch10", "灯调低了", "床头台灯光缓缓调暗一档", "image_to_video", "V1", "2x2_tile", None,
     "The bedside lamp's warm glow easing gradually dimmer over several seconds, its halo softly contracting on the wall, no flicker, the room exhaling toward sleep"),
    ("c10-s09", "ch10", "雨还在落", "暗卧室里窗上的雨痕,极缓", "image_to_video", "V1", "2x2_tile", None,
     "Rain trails sliding very slowly down the dark bedroom window, street-less night blue outside, room nearly black with only faint lamp warmth at the frame edge, patient unhurried rain"),
    ("c10-s10", "ch10", "明天的约定", "小纸条压在灯座下,灯只剩一点暖", "image_camera_motion", "P1", "2x2_tile", None,
     "A small folded paper note tucked under the lamp base, the lamp at its lowest warm ember, worries left on paper for the daylight, the bargain of a good sleeper"),


    ("c10-s11", "ch10", "灯的开关", "床头灯旋钮特写,停在低位", "image_camera_motion", "P1", "2x2_tile", None,
     "Close view of the bedside lamp's brass dimmer knob resting at its low end, warm metal worn smooth, light just above a whisper"),
    ("c10-s12", "ch10", "帘后的微光", "厚帘边缘透进一线极暗的夜蓝", "image_camera_motion", "P1", "2x2_tile", None,
     "The thick curtain's edge letting in one thread of deep night blue, fabric folds in near darkness, the world outside kept soft"),
    ("c10-s13", "ch10", "床边的拖鞋", "一双拖鞋并排摆在床边地板", "image_camera_motion", "P2", "2x2_tile", None,
     "A pair of slippers side by side on the wood floor by the bed, pointing home, low lamp glow, tomorrow's first step already arranged"),
    ("c10-s14", "ch10", "无数字的钟", "床头小闹钟完全虚化,无数字可读", "image_camera_motion", "P1", "2x2_tile", None,
     "A small bedside clock rendered entirely soft and out of focus, its face unreadable, hands dissolving into glow, time present but not insisting"),
    # ---- 尾声(4) ----
    ("e-s01", "epilogue", "整间屋子", "暗客厅全景:一盏低灯,远处夜雨窗", "image_camera_motion", "P2", "2x2_tile", None,
     "The whole dark living room held in one wide view: one low lamp still on, rain window glowing faint blue beyond, every small order of the evening still in place"),
    ("e-s02", "epilogue", "小事的回声", "静物组:钥匙盘/叠好的毛巾/晾着的衬衫同景深", "image_camera_motion", "P1", "2x2_tile", None,
     "A still-life echo arranged along one shelf line: the wooden key tray with brass keys, folded towels, a dried shirt on a small hanger, all the evening's small victories in one soft frame"),
    ("e-s03", "epilogue", "雨要停了", "窗上雨痕渐稀,屋内几近全暗", "image_to_video", "V1", "2x2_tile", None,
     "Rain trails on the night window thinning and slowing, drops arriving less often, the room behind almost fully dark with one ember of lamp warmth, the night settling into stillness"),
    ("e-s04", "epilogue", "晚安", "最终帧:床边一点最低的暖光,雨夜将息", "image_camera_motion", "P2", "single", "母题定装镜",
     "The final frame: the bedroom's last ember of warm lamplight beside the bed, rain beyond the curtain edge almost over, deep restful darkness holding the room, good night"),
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
    cursor = {}
    sec_total = {}
    for r in ROWS:
        sec_total[r[1]] = sec_total.get(r[1], 0) + 1
    t = GAPS["head"]
    for (sid, sec, beat, scene, cls, strat, mode, cat, core) in ROWS:
        plist = paras.get(sec)
        if not plist:
            raise SystemExit(f"section {sec} not in utterances")
        # 均匀分布:超额镜头分散到全章段落(旧 clamp 堆积章末导致复用超标)
        n = len(plist)
        k = cursor.get(sec, 0)
        i = min(int(k * n / sec_total[sec]), n - 1)
        cursor[sec] = k + 1
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
        "episode": "life-manual",
        "basis": "story/OUTLINE.md v1 + NARRATION_MASTER.md 锁定稿 v1(793b6a8c)",
        "source_sha256": sha,
        "created_at": str(date.today()), "updated_at": str(date.today()),
        "fps": 30, "width": 1920, "height": 1080,
        "cps_final": CPS,
        "intra_gap_s": GAPS["unit"], "para_gap_s": GAPS["para"], "chap_gap_s": GAPS["chap"],
        "api_budget": {
            "rule": "rules/shared/image-grid-generation.md 2026-10-19 修订:默认 2x2,single 仅四类例外;预计 API 调用数 = single 镜数 + ⌈批量镜数/4⌉",
            "authorization": "2026-10-24 用户授权直接制作直到成片;预算控制在 60-85 次参考带内;批次后报消耗账目;遇余额类 403 立即停手",
            "full_episode": {"shots": len(shots), "single": singles, "tile": tiles,
                             "est_calls": est_calls, "spent_so_far": 0,
                             "note": "全集一次成型(无试点批次);single 例外=母题定装4+精密结构2+关键特写2"},
        },
        "counts": {"total": len(shots), "single": singles, "2x2_tile": tiles,
                   "image_to_video": i2v,
                   "by_section": {sec: sum(1 for s in shots if s["section"] == sec)
                                  for sec in dict.fromkeys(s["section"] for s in shots)}},
        "section_titles": {
            "bridge": "引入·长大以后", "ch01": "进门以后,先给东西一个家",
            "ch02": "冰箱不是时间暂停器", "ch03": "一顿饭里,最容易忽略的不是味道",
            "ch04": "打扫房间,先弄清楚脏东西是什么", "ch05": "衣服洗完了,为什么还是不清爽",
            "ch06": "房间里的空气,也需要有人照顾", "ch07": "收纳不是把东西都藏起来",
            "ch08": "买东西之前,先给自己一点时间", "ch09": "手机里的生活,也要留一把备用钥匙",
            "ch10": "在睡前,为明天留一条容易走的路", "epilogue": "灯还亮着,但今晚已经足够了"},
        "notes": ("全集计划=引入+ch01-ch10+尾声,一次成型。母题连续性:钥匙盘(木盘+黄铜钥匙串)c1-s01定装→c9-s05回收;"
                  "冰箱(白色单开门)c2;夜雨窗 brg-s01定装→c6/c10/e 再现;台灯(黄铜灯颈米白罩)c7-s01定装→c9/c10/e-s04 收束。"
                  "调性曲线:引入暗暖→ch01-03 厨房暖光最暖→ch04-05 清洁冷一档→ch06 浴室青灰雾→ch07-08 低饱和静物→"
                  "ch09 屏冷光+灯暖光对比→ch10-尾声逐档调暗收于台灯余烬。i2v 仅自然内部运动(水珠/冷雾/水流/蒸汽/滚筒/轻摆/"
                  "凝珠/纱帘/屏暗/灯暗/雨痕),全集 13 镜;全集无脸无手,文字禁令全域。"),
        "shots": shots,
    }
    OUT.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["# ALL_SHOT_PROMPTS(全集 v1)", "",
             f"- 总镜数 {len(shots)}(single {singles} / 2x2_tile {tiles} / i2v {i2v})",
             f"- 整集预计调用 {est_calls} 次(60-85 带内)", ""]
    for s in shots:
        lines += [f"## {s['id']} · {s['beat']}({s['paragraph_id']})",
                  f"- 画面:{s['scene']}",
                  f"- 类别/策略:{s['shot_class']} / {s['strategy']};image_mode={s['image_mode']}"
                  + (f"(例外:{s['single_category']})" if s["image_mode"] == "single" else ""),
                  f"- prompt:`{s['image_prompt']}`", ""]
    PROMPTS_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"shots={len(shots)} singles={singles} tiles={tiles} i2v={i2v} est_calls={est_calls}")
    print(f"body_est(all sections)≈{t:.0f}s")


if __name__ == "__main__":
    main()
