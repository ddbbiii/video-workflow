from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[3]
SCRIPT = EP / "story/script-v1.md"

SCENES = {
    "living-room": "A modest Chinese apartment living room, low scratched dark-wood coffee table, two mismatched fabric sofas, a small cream ceramic house ornament with a chipped red roof corner and tiny blue door on the table, stacked bowls near the sofa, an old floor lamp as the only warm light, peeling blue-grey wall paint and water stains, worn cushion and slippers, ordinary lived-in home, no people, no text.",
    "tabletop": "The same living room coffee table from a close oblique angle, black unbranded smartphone, the same small cream ceramic house ornament with chipped red roof corner and tiny blue door, two used tea cups, scratched veneer and water rings, worn sofa edge and a folded dishcloth in the background, no people, no text, no UI.",
    "kitchen": "A compact Chinese apartment kitchen opening onto the same living room, chipped pale-green cupboard, stacked bowls, enamel basin, worn tile grout and a water stain under the window, folded dishcloth, foreground door jamb, one small warm bulb, no people, no labels or readable text.",
    "window": "The same apartment window and balcony view at night, old aluminium frame with peeling paint and rain marks, faded curtain edge, one plastic stool and a drying towel, distant residential street with dim lamps and no visible person, foreground curtain partly occluding the view, no signs or text.",
    "doorway": "The same apartment entrance viewed from inside, scuffed steel door and worn threshold, peeling pale-green corridor paint, rust at the hinge, two pairs of used slippers and a plastic stool, a weak warm light from the apartment behind the camera, empty corridor, no door number or notice.",
    "police-station": "A small ordinary neighborhood police station reception area at night, scratched laminate counter, old plastic chairs, faded wall paint, scuffed tile and a water-stained notice board with no legible marks, a thermos and tissue box, fluorescent cool light with one warm desk lamp, no logos or readable text.",
    "friends-home": "A modest spare room in a friend's apartment before dawn, narrow bed with rumpled grey blanket, worn wooden bedside table, chipped ceramic cup, peeling wall paint and a water stain, slippers and folded clothes, cold window light with one dim warm lamp, no people, no text.",
    "bedroom": "A lived-in bedroom at night, rumpled cotton bedding, worn bedside table, old window frame with peeling paint, water stain near the sill, slippers and a hanging jacket, dim cool light with a single warm bedside lamp, no people, no text.",
    "phone-photo": "A close view of a black unbranded smartphone held above a scratched coffee table, screen showing only one large uncaptioned news photograph with a thin neutral margin and no readable interface, no icons, no letters, no numbers, the same cream ceramic house ornament visible in the real room beside the phone, no people outside the photo.",
    "hall-monitor": "An old apartment building hallway security monitor on a scuffed wall, screen filled with soft grey analog snow rather than a person, worn plastic stool below, peeling paint and rusty conduit, dim corridor light, no text, no numbers, no logo.",
}

# One visual state per locked narration cue. The story facts stay in Chinese; prompt detail stays visual and concrete.
ROWS = [
    ("tabletop", "C", ["zhouning", "chenyi"], "E01", "手机评论区刚出现‘车祸’，两人笑意同时停住。", "Close evidence view: an unbranded phone lies between two tea cups; two women's hands have stopped mid-gesture on either side. The screen shows one short dark comment bar with no legible characters, icons, or platform branding; their tense faces are reflected faintly in the glass."),
    ("living-room", "M", ["zhouning", "chenyi"], "", "深夜客厅里两人围着茶几闲聊，电视无声亮着。", "Wide establishing view from behind a worn sofa: two women sit on opposite sides of the coffee table, bowls and cups left from dinner, dark television in the background, one warm lamp against cold window light."),
    ("living-room", "M", ["zhouning", "chenyi"], "", "陈意把一个关于死者如何回答死因的问题发到网上。", "Chen Yi leans over the table holding her phone while Zhou Ning watches from the sofa; relaxed shoulders and an unposed late-night conversation, phone screen angled away with no readable content."),
    ("tabletop", "E", [], "E01", "无头像的新账号只留下‘车祸’两个字。", "Wide view from the doorway: a black unbranded phone glows alone on the coffee table between two used cups; its screen has one blank profile circle and one short dark comment bar as abstract shapes, no letters or logo."),
    ("living-room", "M", ["zhouning", "chenyi"], "", "两人把留言当成即兴编故事，陈意追问对方证据。", "Chen Yi turns the phone toward Zhou Ning with a skeptical half-smile; Zhou Ning gestures casually toward the screen, both seated in the same worn living room, no extra people."),
    ("phone-photo", "C", [], "E01", "账号发来一篇数月前的外地车祸旧闻。", "A black unbranded phone lies on the worn coffee table; its screen shows a damaged compact car beside a roadside tree at night, no readable headline, text, logo or hand."),
    ("phone-photo", "E", [], "E01", "旧闻照片里的车撞在树旁，暂时看不出與两人有關。", "The same uncaptioned news photograph: a compact car with a crushed front beside a thick roadside tree, photographed from a distant angle; phone bezel and worn coffee table establish this is a screen, with no readable text."),
    ("living-room", "M", ["zhouning", "chenyi"], "", "两人放下手机，话题回到工作和周末安排。", "The phone rests face down while Zhou Ning and Chen Yi resume their conversation over leftover bowls; their posture loosens, television light remains faint, ordinary domestic details stay readable."),
    ("tabletop", "M", ["chenyi"], "E01", "账号又写下‘很冷，也很黑’，陈意的笑意淡了。", "Chen Yi's fingers tighten around the phone; her smile has faded and the screen carries only a dim unlettered image area, cold light from the window, chipped ceramic cup in sharp focus."),
    ("living-room", "M", ["zhouning", "chenyi"], "", "陳意追問對方位置，對方沒有再回覆。", "Chen Yi types with one hand and waits, Zhou Ning watches her from the other side of the table; the unbranded phone stays between them, both faces visible, no readable screen content."),
    ("living-room", "E", [], "", "屋内没有来电或门外动静，一切看似如常。", "Empty living room after both women have stepped just outside frame; two cups, slightly askew chair, silent dark television, closed door and undisturbed curtain, no person or supernatural figure."),
    ("tabletop", "C", ["zhouning"], "E01", "周宁重新打开新闻，发现标题和地点似乎变了。", "Over Zhou Ning's shoulder, one hand reloads the article; the screen photograph remains dominant while the small unlettered layout blocks subtly differ from the earlier image, no legible characters or icons."),
    ("phone-photo", "C", ["zhouning"], "E01", "新闻地点变成另一座城市，照片里的车也换了颜色。", "The phone fills the frame with a second uncaptioned news photograph: same kind of roadside tree, a different-color compact car and changed landscape; Zhou Ning's thumb hovers beside the screen."),
    ("tabletop", "M", ["zhouning", "chenyi"], "E01", "实时页面与刚才保存的旧图出现兩處明確差異。", "Both women compare the lit phone with a second phone showing the earlier saved car photograph; the two image areas clearly differ in car color and roadside setting, all screens free of readable UI."),
    ("living-room", "M", ["zhouning", "chenyi"], "", "陈意提出缓存或网站更新的解释，两人暂时不再点开链接。", "Chen Yi sets her phone down and explains with a small shrug; Zhou Ning nods but keeps glancing toward the dark screen, the same table and ornament anchor continuity."),
    ("tabletop", "M", ["zhouning", "chenyi"], "E01", "陌生账号问她们是否看了新闻，兩人意識到对方似乎知道。", "The phone lights between the women; both lean toward it and exchange a wary look, the screen shows only an abstract comment bar with no letters, no platform logo."),
    ("living-room", "M", ["zhouning", "chenyi"], "E01", "新聞地点已變成同城，車型也像周宁的车。", "Chen Yi holds the phone while Zhou Ning recognizes the familiar car shape in a city-night news photograph; their faces are tense, the car image is visible but contains no caption or readable text."),
    ("living-room", "M", ["zhouning"], "", "周宁试着用自己公开过的停车场和出行照片解释异常。", "Zhou Ning sits forward alone, looking at a small stack of her own travel prints beside the phone; she studies them as a possible explanation, no readable text or identifiable real address."),
    ("window", "E", [], "", "窗外小区道路空着，路灯下没有可疑的人影。", "Wide view through a half-drawn curtain toward a quiet Chinese apartment entrance and empty road under two streetlamps; no people or cars, chipped window frame and drying towel in foreground."),
    ("tabletop", "M", ["zhouning", "chenyi"], "", "陈意保存账号信息，周宁报警称有人收集她们的住址。", "Zhou Ning speaks on a phone while Chen Yi saves evidence on a second device; both sit at the coffee table, worried but controlled, screens turned away or abstract, no readable content."),
    ("doorway", "E", [], "", "两人守在反锁的屋内，等待物业查看楼道。", "View from inside the apartment toward the closed scuffed steel door and empty corridor beyond the peephole perspective; two pairs of slippers at the threshold, no person outside, no door number."),
    ("phone-photo", "M", ["chenyi"], "E02", "新闻照片已出现熟悉的小区门岗和快递柜。", "Chen Yi holds the phone at chest level; the uncaptioned photo shows a neighborhood guard booth and parcel lockers from across the street, with no readable signs, numbers, labels, or people."),
    ("living-room", "M", ["zhouning", "chenyi"], "", "周宁转身碰倒茶几上的小房子摆件。", "Zhou Ning's elbow has just clipped the coffee table; the small cream ceramic house ornament tips onto its side beside the phone while Chen Yi turns toward the sound, no exaggerated motion blur."),
    ("phone-photo", "C", [], "E02", "新闻照片里出现刚刚倒下的同一只小房子摆件。", "The large uncaptioned phone photograph shows the same cream ceramic house ornament lying on its side, chipped red roof corner and tiny blue door matching the physical ornament at frame edge; identical orientation and pale water ring, no people or text."),
    ("tabletop", "C", [], "E02", "现实中的摆件與屏幕照片方向、裂口和水印完全一致。", "Evidence close-up with the real ceramic house ornament beside the phone photo; both lie in matching orientation, same chipped red roof corner, tiny blue door and curved water mark, both sharp and unobstructed."),
    ("living-room", "M", ["zhouning", "chenyi"], "E02", "两人检查公开笔记和相册，确认从未拍过这间客厅。", "Zhou Ning and Chen Yi search through their phones and a small photo album; the private room is absent from all visible prints, they exchange frightened looks, phone screens show no legible UI."),
    ("living-room", "M", ["zhouning"], "E02", "周宁第一次認定新闻正在记录她们当下的生活。", "Zhou Ning freezes beside the fallen ornament, gaze fixed on the phone image; Chen Yi is just outside frame, the chipped little house remains visible between phone and real tabletop."),
    ("hall-monitor", "C", [], "E03", "门锁边出现新划痕，楼道监控同时变成雪花。", "A narrow fresh scratch beside the apartment lock fills the left foreground while an old corridor monitor in the background shows grey static; no intruder, no readable numbers, no glitch effects beyond natural monitor snow."),
    ("police-station", "E", [], "", "警方没有发现明确撬门痕迹，也未找到楼道里的人。", "Wide establishing view of a small neighborhood police station reception at night, empty plastic chairs, scratched counter and cool fluorescent light; no uniforms or readable notices dominate."),
    ("window", "E", ["zhouning", "chenyi"], "", "两人带上手机离开住处，当晚预告中的袭击没有发生。", "Exterior wide view from across the apartment entrance as two women leave under dim streetlights and walk toward a parked car; faces not prominent, quiet ordinary block, no pursuer."),
    ("police-station", "M", ["zhouning", "chenyi"], "E01", "派出所查看的新闻已恢复成最初那篇旧车祸报道。", "At a scratched reception counter, Zhou Ning and Chen Yi show two phones to an off-frame officer; both screens now display the same old car photograph, no captions or readable interface."),
    ("friends-home", "E", [], "", "天亮前，两人在朋友家暂住，等到白天再回去取东西。", "Quiet spare room before dawn with two used blankets and two cups on the bedside table, dim blue window light, no people in frame, lived-in household details."),
    ("bedroom", "C", ["zhouning"], "E03", "下一个周日凌晨，周宁被胸口刺痛惊醒，锁骨下有一道细红痕。", "Zhou Ning sits on the bed in a dark grey sleep shirt, one hand hovering near a thin red scratch below the collarbone; no blood, no wound detail, restrained expression, no other person."),
    ("bedroom", "M", ["zhouning"], "E03", "几周里，同一时间的刺痛和同一位置红痕反复出现。", "Zhou Ning sits at the bedside recording dates in a closed notebook, sleeve raised to show the same faint scratch; calendar-like pages have no legible marks, the bedside clock face is turned away."),
    ("living-room", "M", ["zhouning", "chenyi"], "", "周宁和陈意约定每个周日互相确认平安。", "Zhou Ning holds a phone to her ear in the same living room while Chen Yi appears only as a small unidentifiable portrait silhouette on a second device; Zhou Ning looks relieved but guarded, no readable UI."),
    ("tabletop", "C", ["chenyi"], "E01", "几周后，陈意收到一张新笔记截图，但没有点开陌生链接。", "Chen Yi's hand holds a phone with a text-free post layout: one blank profile circle, a dark image rectangle and a few empty comment bars; no readable text, no logo, no link preview."),
    ("living-room", "E", [], "E01", "新发帖者住在远处，评论区暂时只有空白位置。", "An unoccupied coffee table with a phone screen facing up; the distant residential lights reflect in the glass, empty comment bars are abstract shapes without words, no other person in the room."),
    ("tabletop", "C", ["chenyi"], "E01", "无头像账号再次回复‘车祸’，陈意问周宁要不要点开新闻。", "Chen Yi's thumb stops above the phone; one short dark comment strip is visible but contains no letters, her reflection is tense, the ceramic house ornament sits upright at the far edge."),
]

# These second states split the narration at existing sentence boundaries; no wording is added or removed.
INSERTS = {
    "S02": ("S02B", "living-room", "M", ["zhouning", "chenyi"], "", "两人饭后坐到客厅，手机和碗筷留在茶几上。", "Chen Yi settles on the sofa and puts her phone beside the leftover bowls; Zhou Ning takes the opposite seat, both relaxed before the strange post."),
    "S08": ("S08B", "tabletop", "M", ["zhouning", "chenyi"], "E01", "手机在两人闲聊时再次亮起。", "A sudden pool of phone light falls between the two women as they turn back toward the table; the screen contains only abstract shapes, no readable words or icons."),
    "S15": ("S15B", "tabletop", "E", [], "E01", "链接关闭后，桌上只剩没有变化的旧截图。", "The phone lies dark beside a separate saved image of the earlier car photograph; the empty living room and ceramic house ornament remain in the background, no people and no legible UI."),
    "S19": ("S19B", "window", "M", ["zhouning", "chenyi"], "", "两人拉开窗帘确认楼下没有人，也没有車经过。", "Zhou Ning and Chen Yi stand side by side behind the curtain, scanning the empty road and apartment gate below; no figure, headlights, signs, or readable text."),
    "S25": ("S25B", "living-room", "E", [], "E02", "手机里的摆件照片与现实茶几落在同一方向。", "From the far end of the living room, the fallen ceramic house and the phone photograph are visible together on the coffee table, aligned in the same orientation; no people, no text."),
    "S30": ("S30B", "window", "M", ["zhouning", "chenyi"], "", "两人離開後沒有遭到襲擊，也沒有再打開链接。", "The two women walk toward a parked car on the quiet residential street, each holding a phone down at her side with the screen dark; no pursuer or other person."),
}

def visible(text: str) -> int:
    return sum(1 for ch in text if ch.isalnum())

def main() -> None:
    rows = []
    for line in SCRIPT.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^(S\d{2})\s+(.+)$", line.strip())
        if m:
            rows.append((m.group(1), m.group(2)))
    if len(rows) != len(ROWS):
        raise SystemExit(f"script cues={len(rows)} but visual rows={len(ROWS)}")
    shots = []
    cursor = 0
    for (sid, cue), (scene, shot_type, cast, evidence_id, fact, visual) in zip(rows, ROWS):
        split = sid in INSERTS
        parts = sentence_split(cue) if split else [cue]
        if split and len(parts) < 2:
            raise SystemExit(f"cannot split {sid} at sentence boundary")
        midpoint = sum(visible(p) for p in parts) / 2
        cut = min(range(1, len(parts)), key=lambda k: abs(sum(visible(p) for p in parts[:k]) - midpoint)) if split else len(parts)
        cue_parts = ["".join(parts[:cut]), "".join(parts[cut:])] if split else [cue]
        states = [(sid + "A" if split else sid, scene, shot_type, cast, evidence_id, fact, visual, cue_parts[0])]
        if split:
            insert = INSERTS[sid]
            states.append((*insert[:7], cue_parts[1]))
        for shot_id, shot_scene, kind, shot_cast, eid, shot_fact, shot_visual, shot_cue in states:
            chars = visible(shot_cue)
            duration = chars / 3.6 + (0.24 / len(states))
            frames = round(duration * 24)
            character_ids = [f"{name}-20261118-xinwen" for name in shot_cast]
            shots.append({
                "id": shot_id, "beat_id": sid, "line": "悬疑", "step": "single",
                "scene_id": shot_scene, "shot_type": kind, "cast": shot_cast,
                "character_ids": character_ids, "has_character": bool(shot_cast),
                "character_closeup": kind == "C" and bool(shot_cast),
                "closeup_part": "hand" if kind == "C" and "zhouning" in shot_cast else ("face" if kind == "C" and shot_cast else "none"),
                "hands_visible": "hand" in shot_fact or "手" in shot_fact or "finger" in shot_visual or "thumb" in shot_visual,
                "view_angle": "俯拍近景" if kind == "C" else ("门外/隔窗观察" if kind == "E" else "平视三分线"),
                "evidence_id": eid, "subject_class": "person" if shot_cast else "environment",
                "push_ratio": 0.10 if kind == "C" else (0.09 if kind == "M" else 0),
                "needs_2048": True, "single_reason": "关键证据或人物动作单图" if kind == "C" else "场景连续性单图",
                "fact": shot_fact, "visual": shot_visual, "cue": shot_cue,
                "start_frame": cursor, "end_frame": cursor + frames, "frames": frames,
                "duration_s": frames / 24, "motion": "affine_push" if kind == "C" else "static",
                "foley_requirement": "document-only-no-audio",
            })
            cursor += frames
    target_frames = round((sum(visible(cue) for _, cue in rows) / 3.6 + 0.24 * len(rows)) * 24)
    final_adjustment = target_frames - cursor
    shots[-1]["frames"] += final_adjustment
    shots[-1]["end_frame"] += final_adjustment
    shots[-1]["duration_s"] = shots[-1]["frames"] / 24
    cursor = target_frames
    plan = {
        "title": "新闻更新前", "fps": 24, "duration_s": cursor / 24, "frames": cursor,
        "visible_chars": sum(visible(cue) for _, cue in rows), "scenes": SCENES, "shots": shots,
        "source": "本土化结构改编；不使用原帖原句或图片。",
    }
    out = EP / "storyboard/SHOT_PLAN-v1.json"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    if "".join(s["cue"] for s in shots) != "".join(cue for _, cue in rows):
        raise SystemExit("shot cues do not reconstruct the locked script")
    md = ["# 《新闻更新前》分镜表 v1", "", f"共 {len(shots)} 镜；{plan['visible_chars']} 可见字；估算 {plan['duration_s']:.2f}s（约 {plan['duration_s']/60:.1f} 分钟），未对真实人声校准。", "", "| 镜号 | 景别 | 场景 | 人物 | 事实 / 画面职责 | 旁白 | 时长 |", "|---|---|---|---|---|---|---:|"]
    for s in shots:
        cast = "、".join(s["cast"]) if s["cast"] else "无"
        md.append(f"| {s['id']} | {s['shot_type']} | {s['scene_id']} | {cast} | {s['fact']} | {s['cue']} | {s['duration_s']:.2f}s |")
    (EP / "storyboard/SHOT_PLAN-v1.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    lock_path = EP / "story/LOCK.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["sha256"] = hashlib.sha256(SCRIPT.read_bytes()).hexdigest()
    lock["estimated_duration_s"] = plan["duration_s"]
    lock_path.write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"shots={len(shots)} frames={cursor} duration={plan['duration_s']:.3f}s chars={plan['visible_chars']}")

def sentence_split(text: str) -> list[str]:
    return re.findall(r".+?[。！？](?:[”’])?|.+$", text)

if __name__ == "__main__":
    main()
