# -*- coding: utf-8 -*-
"""Build glacier-river 预览版 SHOT_PLAN v0.1(片头+第一章+第二章前九段)。

2026-11-03 用户要求"按现有视频流做前 5 分钟先看效果"。
依据 story/NARRATION_MASTER.md v0.1(片头5段+ch01 11段+ch02 9段,1200 可配音字)。
视觉:真实摄影风高山冰川,冷蓝白;零图表、零文字、零人物。
镜头按段落显式映射(不靠均匀分布猜),22+ 镜;取景与运镜对齐 shared/visual-motion 白名单 P1/P2。
"""
from __future__ import annotations
import hashlib, json
from datetime import date
from pathlib import Path

EP = Path(__file__).resolve().parents[3]      # 4/
OUT = EP / "visual" / "SHOT_PLAN.json"
PROMPTS_MD = EP / "visual" / "ALL_SHOT_PROMPTS.md"
SRC = EP / "story" / "NARRATION_MASTER.md"
CPS = 3.45

STYLE = ("Photorealistic cinematic still, cold blue-white high-alpine glacier world, natural soft "
         "light, extremely fine ice and snow texture, calm slow bedtime documentary mood, subtle "
         "film grain, no HDR glow, 16:9. ")
BAN = ("No text, no letters, no numbers, no readable labels, no charts, no diagrams, no maps, "
       "no arrows, no collage, no split screen, no borders, no watermark, no logo, no people, "
       "no hands, no faces, no buildings, no warm daylight, no oversaturated colors, no fantasy "
       "glowing magic. ")

PALETTE = {
    "ch01": ("High alpine night and blue hour: moonlit snow slopes, dark rock ridges, faint stars, "
             "thin clouds hugging the ridge, deep indigo and pale blue-grey whites"),
    "ch02": ("Extreme close textures of snow turning to ice: fluffy new snow, rounded firn grains, "
             "translucent blue-grey ice, trapped air bubbles, soft diffused cold light"),
}

# (id, section, para, beat, scene_zh, class, strategy, mode, single_cat, prompt_core)
ROWS = [
    # ---------- 第一章 落在山上的那一片雪 ----------
    ("c1-s01", "ch01", "ch01-p01", "平静的冬夜", "星夜下的雪山,雪坡泛着极淡蓝光,山脊沉在暗色里",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A wide quiet winter night in the high mountains: a long snow slope glowing faintly blue under "
     "starlight, dark rock ridges fading into indigo darkness, thin cold haze, absolute stillness"),
    ("c1-s02", "ch01", "ch01-p02", "云贴着山脊", "低云沿黑色山脊缓慢移动,雪面被云影切出层次",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Low clouds sliding along a dark mountain ridge above a high snow basin, long soft cloud "
     "shadows crossing the snow, cold blue hour light, distant peaks almost dissolved in haze"),
    ("c1-s03", "ch01", "ch01-p02", "云里的冰晶", "微距六角雪晶悬在深蓝夜色里,结构清晰,边缘微融",
     "image_camera_motion", "P2", "single", "关键特写",
     "Macro photograph of a single six-armed snow crystal suspended against deep blue night, "
     "delicate branching arms, faint rime, shallow depth of field, one tiny ice crystal in a vast "
     "cold sky, museum-grade clarity"),
    ("c1-s04", "ch01", "ch01-p03", "一片雪花落下", "雪面极近特写,一片雪花刚刚落定;远处虚化成蓝色雪坡",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Extreme close view of one fresh snowflake resting on a smooth snow surface, its fine arms "
     "still intact, the slope behind melting into soft blue bokeh, quiet moment of arrival"),
    ("c1-s05", "ch01", "ch01-p04", "平凡的降雪", "整片雪坡与山体,新雪覆盖,云隙透出一点冷光",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A whole mountainside covered by fresh snow at blue hour, smooth snowfields between dark rock "
     "bands, one break in the clouds letting a pale cold glow fall on the upper slope"),
    ("c1-s06", "ch01", "ch01-p05", "留不住的雪", "春季雪坡边缘,细流从雪下渗出,流过湿黑的岩石",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Spring melt at the edge of a mountain snowfield: a thin clear rivulet slipping out from under "
     "the snow and running over wet dark rock, snow crystals collapsing at the margin, cold "
     "overcast light"),
    ("c1-s07", "ch01", "ch01-p05", "被风带走的雪", "风把表层雪吹成细密的波纹与雪雾,低角度侧光",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Wind-carved sastrugi ripples on a high snow plateau, fine snow dust streaming low across the "
     "surface, raking low side light revealing every groove, one continuous cold wind"),
    ("c1-s08", "ch01", "ch01-p05", "留在原处", "背风凹地里的积雪,比周围更厚,安静地存着",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A deep lee hollow holding a thicker drift of old snow while the exposed slope around it is "
     "thin and wind-scoured, smooth pale drift lines, blue shadows, snow that stayed"),
    ("c1-s09", "ch01", "ch01-p06", "第二个冬天", "雪坡剖面:新雪盖在旧雪上,层与层之间一条细暗线",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A natural snow-pit wall showing fresh white snow resting on a slightly denser older layer, a "
     "thin dark seam between them, fine crystal texture in both layers, soft cold daylight from "
     "the side, no tools no text"),
    ("c1-s10", "ch01", "ch01-p07", "被压紧的旧雪", "深雪剖面特写:下部雪层致密发青,上部仍松白,层层可辨",
     "image_camera_motion", "P1", "single", "精密结构",
     "Close photograph of a deep snowpack cross-section: loose white surface snow above, dense "
     "blue-grey layers below, faint annual bands and thin ice lenses visible, crystalline texture, "
     "soft directional cold light, a natural archive of winters"),
    ("c1-s11", "ch01", "ch01-p08", "天空写的书", "风吹出的雪面纹路像一页页纸,斜光扫过",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Wind-written patterns on a snowfield resembling the edges of many pale pages, shallow "
     "step-like ridges, low warm-grey light raking across so each line casts a hair-thin shadow, "
     "a book only the sky can write"),
    ("c1-s12", "ch01", "ch01-p09", "足够厚重的冰体", "雪坡下部与冰的交界,厚雪层过渡到带蓝调的密实冰",
     "image_camera_motion", "P2", "2x2_tile", None,
     "The lower edge of a thick snowfield where white firn grades into dense blue-tinted ice, a "
     "smooth transition zone with faint crystal boundaries, cold diffuse light, weight made visible"),
    ("c1-s13", "ch01", "ch01-p10", "真正的冰川", "远处山间的冰川舌, Blue-white ice tongue between dark peaks",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A distant glacier tongue winding between dark mountain peaks, blue-white ice surface with "
     "soft flow lines, moraine edges in shadow, cold clear air, the whole landform seen from a high "
     "quiet viewpoint"),
    ("c1-s14", "ch01", "ch01-p11", "雪在变成另一种东西", "雪坡尽头露出第一片淡蓝的冰面,雪与冰相接",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Where a snow slope ends and the first pale blue ice appears, a soft boundary of white grains "
     "over glassy ice, tiny melt channels, one quiet threshold between snow and ice"),

    # ---------- 第二章 雪没有融化,却慢慢失去原来的模样 ----------
    ("c2-s01", "ch02", "ch02-p01", "新雪是轻盈的", "新雪表层极近特写:蓬松、洁白、带细小星芒反光",
     "image_camera_motion", "P2", "single", "关键特写",
     "Extreme macro of freshly fallen powder snow, loose feathery crystal clusters, tiny star-like "
     "specular glints, deep airy shadows between grains, the lightness of new snow made visible"),
    ("c2-s02", "ch02", "ch02-p02", "一捧雪的空隙", "雪堆断面:颗粒之间大量黑色空隙,结构像泡沫",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Cross-section of a hand-packed snowball-sized mass of snow, many dark air voids between "
     "crystals, porous like white foam, macro detail, cool soft light, no hands in frame"),
    ("c2-s03", "ch02", "ch02-p02", "雪晶之间的空气", "更近的雪晶网络:枝晶交错,空隙清晰可见",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Even closer view into a network of snow crystals, delicate branched grains touching at a few "
     "points, visible air pockets between them, translucent edges, cold blue-white palette"),
    ("c2-s04", "ch02", "ch02-p03", "不能一直蓬松", "层层新雪堆叠,底层被压出平直的变形带",
     "image_camera_motion", "P2", "2x2_tile", None,
     "Layered fresh snow under its own weight, lower layers flattened into subtle horizontal "
     "deformation bands, upper crystals still loose, soft shadowed pit wall, quiet pressure"),
    ("c2-s05", "ch02", "ch02-p04", "像砂糖的雪", "粒雪微距:圆钝颗粒紧密堆在一起,像粗砂糖",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Macro of firn: rounded, closely packed ice grains resembling coarse sugar, frosted surfaces, "
     "small gaps, soft cold light, the exact moment snow stops looking like a feather"),
    ("c2-s06", "ch02", "ch02-p05", "粒雪层", "雪坑壁上一段明显的粒雪层,上下都是雪,中间颗粒更粗",
     "image_camera_motion", "P1", "single", "精密结构",
     "A clear firn layer exposed in a snow-pit wall, coarser rounded grains between finer snow "
     "above and denser ice below, natural stratigraphy, cold side light, scientific beauty without "
     "any diagram"),
    ("c2-s07", "ch02", "ch02-p06", "继续重结晶", "冰粒之间长出新的晶面,边界变得透亮",
     "image_camera_motion", "P2", "2x2_tile", None,
     "Close view of firn grains recrystallizing, new flat crystal faces growing between them, "
     "translucent boundaries catching a thin rim of light, the slow welding of grains"),
    ("c2-s08", "ch02", "ch02-p06", "密度越来越大", "同一视线的更深处:颗粒几乎挤成连续冰,只剩少量暗隙",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Deeper in the same snow wall, grains pressed almost into continuous ice, only a few dark "
     "pores left, glassy blue-grey translucency, density increasing with depth"),
    ("c2-s09", "ch02", "ch02-p07", "被封住的气泡", "蓝冰内部微距:一串微小气泡被封在透明冰里,光从背后透入",
     "image_camera_motion", "P2", "single", "关键特写",
     "Macro inside clear blue glacier ice: a scattering of tiny air bubbles sealed in the ice, "
     "backlit by soft cold light so the bubbles glow pale, faint crystal boundaries, ancient air "
     "held still"),
    ("c2-s10", "ch02", "ch02-p07", "连续的冰体", "冰壁特写:冰晶彼此结合成整块,内部有淡淡流纹",
     "image_camera_motion", "P1", "2x2_tile", None,
     "A wall of dense glacier ice where crystals have grown into one continuous body, faint flow "
     "bands and hairline fractures, deep blue in the thick parts, cold diffuse light"),
    ("c2-s11", "ch02", "ch02-p08", "六角轮廓消失", "雪粒残骸微距:曾经六角的枝晶只剩圆钝的轮廓",
     "image_camera_motion", "P1", "2x2_tile", None,
     "Macro of a vanishing snow crystal: the six-armed outline almost gone, only a rounded, "
     "slightly translucent grain remains on the snow surface, soft focus around it, quiet "
     "transformation rather than disappearance"),
    ("c2-s12", "ch02", "ch02-p09", "它只是改变了形态", "整片淡蓝冰面,极简,几乎抽象,安静收束",
     "image_camera_motion", "P2", "2x2_tile", None,
     "A calm expanse of pale blue glacier ice filling the frame, minimal composition, soft "
     "gradients from white to blue, a few fine cracks, almost abstract, a quiet closing image"),
]


def main():
    text = SRC.read_text(encoding="utf-8")
    sha = hashlib.sha256(SRC.read_bytes()).hexdigest()
    import json as _json
    utt = _json.loads((EP / "audio" / "utterances.json").read_text(encoding="utf-8"))
    chars = {}
    for u in utt["utterances"]:
        chars[u["paragraph_id"]] = chars.get(u["paragraph_id"], 0) + len(u["text"])
    by_para = {}
    for r in ROWS:
        by_para.setdefault(r[2], []).append(r)

    shots = []
    for r in ROWS:
        sid, sec, pid, beat, scene, cls, strat, mode, cat, core = r
        n = chars.get(pid, 30)
        est = round(max(4.0, n / CPS) / max(1, len(by_para[pid])), 1)
        shot = {
            "id": sid, "paragraph_id": pid, "section": sec, "beat": beat, "scene": scene,
            "est_seconds": est, "status": "planned_preview_v0",
            "timing": {"mode": "planned_estimate", "note": "字数估算;TTS 后由 timeline.json 实测回填"},
            "shot_class": cls, "strategy": strat, "image_mode": mode,
            "image_prompt": STYLE + PALETTE[sec] + ". " + core + ". " + BAN,
        }
        if mode == "single":
            shot["single_category"] = cat
        shots.append(shot)

    singles = sum(1 for s in shots if s["image_mode"] == "single")
    tiles = len(shots) - singles
    calls = singles + (tiles + 3) // 4
    doc = {
        "schema_version": 1, "episode": "glacier-river", "scope": "preview_5min",
        "basis": "story/NARRATION_MASTER.md v0.1 预览(~1200字)",
        "source_sha256": sha,
        "created_at": str(date.today()), "updated_at": str(date.today()),
        "fps": 30, "width": 1920, "height": 1080, "cps_final": CPS,
        "intra_gap_s": 0.19, "para_gap_s": 0.4245, "chap_gap_s": 0.7547,
        "counts": {"total": len(shots), "single": singles, "2x2_tile": tiles,
                   "image_to_video": 0,
                   "by_section": {sec: sum(1 for s in shots if s["section"] == sec)
                                  for sec in ("ch01", "ch02")}},
        "api_budget": {"est_calls": calls, "note": "预览版:single + ⌈tile/4⌉"},
        "notes": ("预览版一次成型。视觉弧:星夜雪山→雪晶→雪坡积雪→风雪与融水→雪层剖面→粒雪→蓝冰气泡。"
                  "片头 5 段背景从本池选取(14 号脚本 PARA_BG),不另生图。零图表/零文字/零人物;"
                  "全部 P1/P2 单向推拉,不做往返运镜。"),
        "shots": shots,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    lines = ["# ALL_SHOT_PROMPTS(预览版 v0.1)", "",
             f"- 总镜数 {len(shots)}(single {singles} / 2x2_tile {tiles})",
             f"- 预计 API 调用 {calls} 次", ""]
    for s in shots:
        lines += [f"## {s['id']} · {s['beat']}({s['paragraph_id']})",
                  f"- 画面:{s['scene']}",
                  f"- 类别/策略:{s['shot_class']} / {s['strategy']};image_mode={s['image_mode']}",
                  f"- prompt:`{s['image_prompt']}`", ""]
    PROMPTS_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"shots={len(shots)} singles={singles} tiles={tiles} est_calls={calls}")
    print("by section:", doc["counts"]["by_section"])


if __name__ == "__main__":
    main()
