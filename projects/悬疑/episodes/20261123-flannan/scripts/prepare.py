"""Build reviewed offline plans from the episode's authored narration and facts."""
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path

EP = Path(__file__).resolve().parents[1]
FPS = 24
RATE = 3.6
LOCATION = {
    "lamp": ("塔顶灯室", "cast-iron stair gate, tall Fresnel lens on a rubbed brass pedestal, salt-streaked sea windows",
             "Worn rail paint, salt crust on glass seams, used oil rag by the service shelf."),
    "quarters": ("守塔人宿舍", "three narrow iron bunks, chipped wash basin, coat pegs",
                 "Rust on iron joints, chipped basin glazing, work blankets with visible repairs."),
    "pier": ("栈桥与船侧", "tarred mooring rope, weathered loading bollard, two-deck steam tender",
             "Nicked rail paint and worn dock planks, crew's used wool wraps and coiled rope."),
    "desk": ("值班室", "scarred oak desk, low oil lamp, frosted square window",
             "Scuffed oak grain and yellowed lamp chimney, open pen box beside used journals."),
    "stairs": ("灯塔铁梯", "iron stair curve and railing, rubbed upper door jamb, narrow draft window",
               "Peeling paint on stair rail, salt stains, folded lamp-room servicing cloth."),
    "window": ("海面与灯塔外景", "steep stone island, coastal reef, wind-cut grey horizon or used tender railing",
               "Scuffed railing and salt marks, tarred lines on attended vessel."),
    "cabin": ("船舱", "brass porthole, scratched oak chart table",
               "Wear on doorway varnish and tarnished porthole, used chart tubes and wool seat cushion."),
}
ROLE = {
    "evan": ("埃文", "A", "early-30s Scottish relief keeper, dark wavy hair, charcoal navy work coat, muted brick scarf"),
    "iain": ("伊恩", "B", "young black-haired Scottish keeper, slate waistcoat and white work shirt, slim face"),
    "ross": ("罗斯", "B", "light-brown short-haired keeper with trimmed moustache, ochre vest and cream sleeves"),
    "andrew": ("安德鲁", "B", "older keeper with silver temples and dark olive knitted cardigan"),
    "captain": ("船长", "B", "middle-aged steam tender captain, salt-grey full beard, dark grey wool cap"),
}
SINGLE_MIDS = {1: "母题定装：主灯熄灭与入口方位", 20: "母题定装：四道人影的独立证据",
               22: "精密结构：同一人物与透镜动作错位", 29: "母题定装：启灯后完整透镜与安全站位",
               32: "精密结构：两个埃文与同一支笔的手位",
               39: "精密结构：门侧目击者、亮带边界与跨步者",
               46: "精密结构：玻璃外与里面三个角色分层",
               54: "母题定装：主灯熄后的匹配回收镜"}
TEXT = {
    9: {"layer": "private_diary", "date": "1900年12月14日", "body": "罗斯在楼下。灯室的门却响了三下。"},
    14: {"layer": "private_diary", "date": "1900年12月14日", "body": "我上楼接班。伊恩问，我是不是来过一次。"},
    21: {"layer": "private_diary", "date": "1900年12月14日", "body": "玻璃里的人先伸手拿杯。我的杯还在桌上。"},
    23: {"layer": "duty_log", "body": "补给船灯号：三下，停一拍，再一下。"},
    25: {"layer": "side_by_side_logs", "left": "塔上记录　22:08", "right": "船上记录　22:15", "body": "三下，停一拍，再一下"},
    30: {"layer": "external_clock", "body": "23:10:00"},
    31: {"layer": "external_clock_and_light", "body": "23:10", "groups": [2, 5, 3], "target": "lens_only"},
    33: {"layer": "duty_log", "body": "两下／五下／三下"},
    35: {"layer": "external_clock_and_light", "body": "23:17", "groups": [2, 5, 3], "target": "open_sea_only"},
    36: {"layer": "ship_log", "body": "掷骰：二、五、三", "outer_time": "23:16"},
    38: {"layer": "private_diary", "date": "1900年12月14日", "body": "我只慢了一步，光过去，人就没了。"},
    44: {"layer": "private_diary", "date": "1900年12月16日", "body": "他们都在玻璃后面。我再上去一次。"},
    58: {"layer": "private_diary", "date": "1900年12月27日", "body": "我熄了灯。他们还在等人接班。"},
}
FRICTION = {9: .6, 16: .7, 25: .9, 31: 1.0, 35: .85, 43: .65, 47: .65, 54: .9, 58: 2.1}
INTRO = [
    {"id": "I01", "visual": "Wide 16:9 from the departing 1900 steam tender, unnervingly close lighthouse on the steep Scottish island. Scuffed ship rail and salt-crusted rope in foreground, worn stone and rubbed window mullions. Exactly four distinct human silhouettes separated by bright lantern glazing high in frame; do not reveal their faces and no people in foreground.", "cast": []},
    {"id": "I02", "visual": "16:9 angled medium-wide empty lighthouse duty room, old scarred desk in warm sidelight with exactly three clearly separate closed private journals in grey cloth, brown leather and dark green cloth. Stained window, chipped enamel bowl, well-used oil lamp. Nobody in the room. No readable marks on any books.", "cast": []},
]
INTRO_CUE = [
    "岛上只有三个守塔人。补给船离岛那晚，船长却在灯室窗口数出了四个人。",
    "我来接班时，三个守塔人全不见了。他们的日记还在桌上。",
]

def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")

def main():
    shots = []
    for line_no, line in enumerate((EP / "storyboard/beats.tsv").read_text().splitlines(), 1):
        kind, beat, scene, cast, fact, visual, cue = line.split("\t")
        cast = [] if cast == "-" else cast.split(",")
        cast_spec = [dict(id=c, description=ROLE[c][2]) for c in cast]
        visible = sum(c.isalnum() for c in cue)
        if any(sum(c.isalnum() for c in part) > 20 for part in re.split(r"[。！？；：，、]", cue)):
            raise ValueError(f"S{line_no:02} has a subtitle phrase over 20 characters")
        sentence_pauses = .18 * max(0, len(re.findall(r"[。！？]", cue)) - 1)
        frames = math.ceil(FPS * (visible / RATE + .13 + sentence_pauses + FRICTION.get(line_no, 0)))
        anchors, wear = LOCATION[scene][1:]
        mode = ("reuse" if line_no in (35,) else
                "single" if (kind == "C" or line_no in SINGLE_MIDS) else "grid")
        shot = dict(id=f"S{line_no:02}", line="悬疑", shot_type=kind,
                    scene_id=scene, beat=beat, cue=cue, fact=fact, visual=visual,
                    step=mode, has_character=bool(cast), character_ids=cast, character_state=cast_spec,
                    location_anchors=anchors, environment_state=wear,
                    negative="No printed captions, logo, cameras, modern electricity or electronics; no gratuitous extra people or props.",
                    motion="matched_overlay" if line_no in (31,35) else "static",
                    time_stage={"登岛":"1900年12月，白日","日记":"12月14日夜与登岛当日交替","目击":"登岛白日、此前离岛夜","对时":"登岛日到入夜","试验":"登岛夜；船簿事后补证","末页":"12月14至16日，旧夜","离岛":"登岛夜，过路船通过之后","回船":"翌晨"}[beat],
                    foley_requirement="仅制作记录；全片不产音轨。",
                    match_from="S30" if line_no==35 else None,
                    single_reason=(SINGLE_MIDS.get(line_no, "精密结构：证据道具与准确可读的画面留区") if mode=="single" else None),
                    evidence_id=f"E{line_no:02}" if line_no in TEXT or line_no in (16,20,27,32,39,43,46,47,52,54) else None,
                    overlay=TEXT.get(line_no),
                    visible_chars=visible, frames=frames)
        shots.append(shot)
    cursor = 0
    for shot in shots:
        shot.update(start_frame=cursor, start=cursor/FPS, end=(cursor+shot["frames"])/FPS)
        cursor+=shot["frames"]
    body=EP/"story/script.md"
    body.write_text("# 《第四位守塔人》正文旁白\n\n" + "\n\n".join(s["cue"] for s in shots)+"\n")
    grouped=defaultdict(list)
    for shot in shots:
        if shot["step"] == "grid":
            grouped["cast" if shot["has_character"] else "empty"].append(shot)
    grids=[]
    for role, items in grouped.items():
        for i in range(0,len(items),4):
            group=items[i:i+4]
            gid=f"G{len(grids)+1:02}"
            grids.append(dict(id=gid, shots=[s["id"] for s in group], needs_cast=role=="cast", spare_panels=4-len(group)))
            for panel, shot in zip(("top-left","top-right","bottom-left","bottom-right"),group):
                shot.update(grid_id=gid,panel=panel)
    singles=[s for s in shots if s["step"]=="single"]
    boards=[s for s in shots if s["step"]=="grid"]
    planned_cast=sum(s["has_character"] for s in singles)+sum(g["needs_cast"] for g in grids)
    main_calls=len(singles)+len(grids)
    anchors=len(ROLE)
    final_planned=main_calls+planned_cast+anchors+len(INTRO)
    with_reserve=final_planned+8
    budget=dict(required_formula=f"single {len(singles)} + ceil(网格镜 {len(boards)}/4) = {len(singles)+math.ceil(len(boards)/4)}",
                actual_main_plan=main_calls, grid_groups=len(grids), cast_composites=planned_cast, anchors=anchors,
                intro=len(INTRO), pilot_charge="前六正式镜小样计入对应镜头调用；首张定装作额度预检",
                planned=final_planned, retry_reserve=8, approved_limit_requested=with_reserve,
                cost_ceiling_cny=round(with_reserve*.018,2))
    for i,r in enumerate(INTRO):
        r.update(cue=INTRO_CUE[i], title=f"引入 {i+1}", mode="single",
                 reason="独立交付构图；四道影子用可控图层保证数量" if i==0 else "独立交付构图；恰好三本日记")
    dump(EP/"storyboard/SHOT_PLAN.json",dict(budget=budget,fps=FPS,frames=cursor,duration=cursor/FPS,
          visible_chars=sum(s["visible_chars"] for s in shots), script_sha256=hashlib.sha256(body.read_bytes()).hexdigest(),
          intro=INTRO,grids=grids,shots=shots))
    dump(EP/"image/color-plan.json",{"locations":{k:{"label":v[0],"anchors":v[1],"wear":v[2]} for k,v in LOCATION.items()},
                                    "palette":"低饱和冷灰蓝；灯火用少量暖金；海面暗部保留层次。"})
    cast_lines=["# 人物定装安排","", "当前状态：待出图验证，所有角色为本集新建，不复用其他故事的脸。","","|角色|档|服装/外形|参考路径|镜头|","|---|---|---|---|---|"]
    for r,(name,tier,look) in ROLE.items():
        used="、".join(s["id"] for s in shots if r in s["character_ids"])
        reference="image/anchors/evan/three-view.png + face.png" if tier=="A" else f"image/anchors/{r}.png"
        cast_lines.append(f"|{name} / {r}|{tier}|{look}|{reference}|{used}|")
    (EP/"storyboard/CHARACTER_LOCK.md").write_text("\n".join(cast_lines)+"\n")
    with (EP/"storyboard/REVIEW.md").open("w") as f:
        print("# 《第四位守塔人》分镜与出图预算\n",file=f)
        print(f"- 正文 {len(shots)} 镜、{cursor/FPS/60:.1f} 分钟，另有独立引入图 2 张。",file=f)
        print(f"- 首轮：正文画面 {main_calls} 次（独立 {len(singles)} + 四格 {len(grids)}），人物合成 {planned_cast} 次，定装 {anchors} 次，引入 {len(INTRO)} 次，合计 **{final_planned} 次**。",file=f)
        print(f"- 另留 8 次用于质检后返修，请审阅的上限 **{with_reserve} 次**（按当前单价约 ¥{budget['cost_ceiling_cny']:.2f}）。",file=f)
        print("- 先做角色定装，再用六个正式镜检查：海岛、两船、日记、透镜、拿杯、空绳。小样通过后直接复用，费用已计入。",file=f)
        print("- 两次船灯信号由后期合成精确控制脉冲；时间码只落在关键证据镜。日记字由清松手寫體 2 后期排版。",file=f)
        print("\n|序号|段落|景别|画面信息|估秒|\n|---|---|---|---|---:|",file=f)
        for s in shots:
            print(f"|{s['id']}|{s['beat']}|{s['shot_type']}|{s['fact']}|{s['frames']/FPS:.1f}|",file=f)
    print(json.dumps(budget,ensure_ascii=False)); print(f"{len(shots)} shots: {cursor/FPS:.1f} s")

if __name__=="__main__":
    main()
