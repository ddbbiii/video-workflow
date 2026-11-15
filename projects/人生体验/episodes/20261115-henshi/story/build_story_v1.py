# -*- coding: utf-8 -*-
"""Build cue, shot, cast and first-pass visual data from the approved narration."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

EP = Path(__file__).resolve().parent.parent
STORY = EP / "story"
SOURCE = STORY / "script-v1.md"

TARGET = {"E": 0.22, "M": 0.53, "C": 0.25}
SCENE_ANCHORS = {
    "office": ("写字楼玻璃门", "刷卡闸机", "夜色中的办公楼窗格"),
    "commute": ("车厢门边", "不锈钢扶手", "隧道灯带"),
    "apartment": ("掉皮墙角", "折叠木桌", "窗帘缝"),
    "corridor": ("防火门", "水泥楼梯", "应急灯"),
    "street": ("楼体墙根", "停放的电动车", "湿水泥路"),
    "store": ("歪斜货架", "收银台", "碎玻璃门"),
    "route": ("居民楼外墙", "横在路边的旧车", "雾中的路口"),
}
LIGHT = {
    "第一章": "阴天冷白天光或楼道冷白应急灯，按 cue 中时段执行，暗部偏青灰",
    "第二章": "中性阴天窗光与冷青楼道灯，笔记本处可有小片暖台灯",
    "第三章": "潮湿冷灰天光与室内弱暖灯并存，玻璃和路面只留低亮反光",
    "第四章": "凌晨雾前冷灰窗光，门外压暗但保留人形和空间层次",
}
PUNCT = "。！？"


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", "", text)
    text = text.replace(
        "晚上九点四十分，你拎着帆布包走出写字楼，晚高峰的地铁晃了四十分钟，回到出租屋时已经十点半。",
        "晚上九点四十分，你拎着帆布包走出写字楼。晚高峰的地铁晃了四十分钟。回到出租屋时已经十点半。",
    )
    out, start = [], 0
    for i, ch in enumerate(text):
        if ch in PUNCT:
            part = text[start:i + 1].strip()
            if part:
                out.append(part)
            start = i + 1
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return out


def parse_source():
    chapter = ""
    day = ""
    shots = []
    for raw in SOURCE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("## "):
            chapter = line[3:].strip()
            continue
        if line.startswith("### "):
            day = line[4:].strip()
            continue
        if not line or line.startswith(("#", ">")):
            continue
        for sentence in split_sentences(line):
            shots.append({"cue": sentence, "chapter": chapter, "day": day})
    return shots


def scene_for(shot):
    cue, day = shot["cue"], shot["day"]
    if "写字楼" in cue or "公司" in cue:
        return "office"
    if "地铁" in cue:
        return "commute"
    if any(x in cue for x in ("超市", "收银台", "货架", "购物袋")):
        return "store"
    if any(x in cue for x in ("体育馆", "五公里", "路口", "路线", "赶到", "街道")):
        return "route"
    if any(x in cue for x in ("楼道", "猫眼", "门外", "门板", "门把手", "钥匙串", "楼梯", "老刘", "防火门")):
        return "corridor"
    if any(x in cue for x in ("楼下", "墙根", "窗外", "整栋楼", "楼顶", "小区外墙")):
        return "street"
    return "apartment"


def assign_types(shots):
    n = len(shots)
    goal = {"E": round(n * TARGET["E"]), "C": round(n * TARGET["C"])}
    goal["M"] = n - goal["E"] - goal["C"]
    first_by_scene = defaultdict(list)
    for i, shot in enumerate(shots):
        first_by_scene[shot["scene_id"]].append(i)
    forced = set()
    for indices in first_by_scene.values():
        forced.update(indices[:2])
    counts = Counter()
    run_e = 0
    types = []
    for i in range(n):
        if i in forced and counts["E"] < goal["E"]:
            choice = "E"
        else:
            candidates = [k for k in ("E", "M", "C") if counts[k] < goal[k]]
            if run_e >= 5 and "E" in candidates:
                choice = "E"
            else:
                choice = max(candidates, key=lambda k: (TARGET[k] * (i + 1) - counts[k], -"EMC".index(k)))
        types.append(choice)
        counts[choice] += 1
        run_e = 0 if choice == "E" else run_e + 1
    return types


def classify(shot, shot_type):
    cue = shot["cue"]
    sees_others = any(x in cue for x in ("老刘", "丧尸", "那些人", "门外的人", "几个人", "人群", "人影", "他们"))
    sees_cat = "你" in cue
    if shot_type == "E":
        if sees_cat and sees_others:
            cast = "catman+chen"
        elif sees_cat:
            cast = "catman"
        elif sees_others:
            cast = "chen"
        else:
            cast = "none"
        return {"cast": cast, "closeup_part": "none", "view_angle": "front" if cast != "none" else "none"}
    if sees_cat and sees_others:
        cast = "catman+chen"
    elif sees_cat:
        cast = "catman"
    elif sees_others:
        cast = "chen"
    else:
        cast = "none"
    if cast == "none":
        part, angle = "none", "none"
    elif shot_type == "E":
        part, angle = "none", "front"
    elif cast in ("catman", "catman+chen") and any(x in cue for x in ("手", "握", "擦", "钥匙", "把手", "指节", "门缝")):
        part, angle = "paw", "front"
    elif shot_type == "C":
        part, angle = "face", "three-quarter"
    else:
        part, angle = "none", "front"
    return {"cast": cast, "closeup_part": part, "view_angle": angle}


def visual_for(shot, shot_type, scene, cast):
    anchors = SCENE_ANCHORS[scene]
    cue = shot["cue"]
    if shot_type == "E":
        camera, focal = "远，相机略高，从入口看向空间深处", "24mm"
        person = "远处有老陈型简笔丧尸群，人物很小，空间和路径关系清楚" if "chen" in cast else "无人，空间和路径关系清楚"
    elif shot_type == "C":
        camera, focal = "近，相机与主体视线齐平，背景适度虚化", "85mm"
        if cast == "catman+chen":
            person = "猫头人占画面右侧；老陈型简笔配角留在次焦点，保持平涂比例"
        elif "catman" in cast:
            person = "猫头人占画面右侧，保持标准头身与平涂比例"
        else:
            person = "老陈型配角的头肩或关键物件近景"
    else:
        camera, focal = "中，相机视平线，从场地一侧斜看主体与环境", "35mm"
        if cast == "catman+chen":
            person = "猫头人位于画面右侧；老陈型简笔圆头配角位于左侧或远处"
        elif cast == "catman":
            person = "猫头人位于画面左或右三分之一，不居中"
        elif cast == "chen":
            person = "老陈型简笔圆头配角，衣着和姿态按 cue 区分，不画写实五官"
        else:
            person = "无人，突出道具和场地关系"
    foreground = {
        "office": "玻璃门框或闸机压住画面边缘",
        "commute": "扶手立柱压住画面左下边缘",
        "apartment": "门框、桌角或椅背压住一侧边缘",
        "corridor": "门框或楼梯扶手压住画面边角",
        "street": "窗框、路沿或停放车辆压住画面下缘",
        "store": "歪斜货架边缘压住画面一侧",
        "route": "近处车窗框或路牌背面压住边角",
    }[scene]
    background = "、".join(anchors)
    action = cue.rstrip("。！？")
    action = action[:54] + ("…" if len(action) > 54 else "")
    chapter_key = "第四章" if shot["chapter"].startswith("第四章") else "第三章" if shot["chapter"].startswith("第三章") else "第二章" if shot["chapter"].startswith("第二章") else "第一章"
    return (
        f"机位：{camera}；焦段：{focal}；人物：{person}；前景：{foreground}；"
        f"中景：具体呈现“{action}”；远景：{background}，空间结构可读；"
        f"光：{LIGHT[chapter_key]}；环境色：按 {scene} 场地色板，冷灰青为主、背景保留中性灰与环境辅色；"
        f"动作：只表现 cue 中这一刻，物件位置与动作方向明确。"
    )


def fact_for(cue):
    fact = cue.rstrip("。！？")
    if len(fact) > 38:
        for sep in ("，", "；", "："):
            if sep in fact:
                head = fact.split(sep, 1)[0]
                if len(head) >= 8:
                    fact = head
                    break
    return fact[:40]


def main():
    shots = parse_source()
    if not shots:
        raise SystemExit("no narration parsed")
    for shot in shots:
        shot["scene_id"] = scene_for(shot)
    types = assign_types(shots)
    cue_data, type_rows, cast_data, expr_data, props_data = {}, [], {}, {}, {}
    md = [
        "# 痕尸末世十九天 · 逐镜剧本 v2",
        "",
        "> cue 原文取自已确认的 `script-v1.md`，按自然句拆镜；视觉描述为第一轮生产约束，批次目检后只返工必要镜头。",
        "> 画风：`rules/人生体验/style.md` v3.5；角色：`character.md` v7；色彩：`image/color-plan.json`。",
        "",
    ]
    current_chapter = None
    character_run = 0
    for i, (shot, shot_type) in enumerate(zip(shots, types), 1):
        sid = f"S{i:03d}"
        scene, cue = shot["scene_id"], shot["cue"]
        role = classify(shot, shot_type)
        character_run = character_run + 1 if role["cast"] != "none" else 0
        visual = visual_for(shot, shot_type, scene, role["cast"])
        fact = fact_for(cue)
        if current_chapter != shot["chapter"]:
            current_chapter = shot["chapter"]
            md.extend(["## " + current_chapter, ""])
        md.extend([
            f"{sid}　{cue}",
            f"　　visual：{visual}",
            f"　　shot_type：{shot_type}",
            f"　　scene_id：{scene}",
            f"　　has_character：{'true' if role['cast'] != 'none' else 'false'}",
            f"　　fact：{fact}",
            f"　　cast：{role['cast']}",
            f"　　closeup_part：{role['closeup_part']}",
            f"　　view_angle：{role['view_angle']}",
            "",
        ])
        cue_data[sid] = cue
        type_rows.append({"id": sid, "shot_type": shot_type, "scene_id": scene,
                          "has_character": role["cast"] != "none", "chapter": shot["chapter"], "day": shot["day"]})
        cast_data[sid] = role
        if "catman" in role["cast"]:
            if any(x in cue for x in ("害怕", "凉意", "吓", "心头一沉")):
                expr_data[sid] = "发愣"
            elif any(x in cue for x in ("累", "疲惫", "躺", "睡")):
                expr_data[sid] = "疲惫"
            elif any(x in cue for x in ("不敢", "犹豫", "难堪")):
                expr_data[sid] = "难堪"
            else:
                expr_data[sid] = "平静"
        if any(x in cue for x in ("钥匙", "塑料瓶", "布料", "抹布", "笔记本", "收音机", "背包", "床单")):
            props_data[sid] = cue

    counts = Counter(types)
    shot_types = {"episode": "20261115-henshi", "total": len(shots),
                  "counts": dict(counts), "ratios": {k: round(counts[k] / len(shots), 4) for k in "EMC"},
                  "shots": type_rows}
    files = {
        "cues.json": cue_data,
        "shot-types.json": shot_types,
        "cast.json": cast_data,
        "expressions.json": expr_data,
        "props.json": props_data,
    }
    for name, data in files.items():
        (STORY / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (STORY / "script-v2.md").write_text("\n".join(md), encoding="utf-8")
    visible = sum(sum(1 for ch in shot["cue"] if ch.isalnum()) for shot in shots)
    print(f"shots={len(shots)} visible={visible} counts={dict(counts)}")
    print("scenes=" + json.dumps(dict(Counter(s['scene_id'] for s in shots)), ensure_ascii=False))


if __name__ == "__main__":
    main()
