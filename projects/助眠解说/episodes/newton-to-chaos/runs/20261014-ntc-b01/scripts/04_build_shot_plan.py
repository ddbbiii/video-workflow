# -*- coding: utf-8 -*-
"""Build visual/SHOT_PLAN.json + visual/ALL_SHOT_PROMPTS.md from beats + utterances.

Estimated timing: voiced chars / 3.42 chars-per-final-second (b2 raw 4.42 cps x
0.774224 atempo), plus per-utterance gaps. All estimates are replaced by actual
sample counts after audio is processed (mode: planned_estimate).
"""
from __future__ import annotations
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EP = HERE.parents[2]
sys.path.insert(0, str(HERE))
from importlib import import_module as _im
BEATS = {}
for mod, attr in (("02_beats_a", "BEATS_A"), ("02_beats_b", "BEATS_B")):
    BEATS.update(_im(mod).__dict__[attr])

SIMS = _im("03_sim_specs").SIMS

SKEL = ("Cinematic science-fantasy documentary, deep teal-blue night palette with "
        "controlled amber highlights, monumental subject, photorealistic materials, "
        "volumetric atmosphere, layered depth, reflective surfaces, asymmetrical "
        "cinematic composition, subtle surrealism, rich environmental detail, calm "
        "dreamlike mood, 16:9 widescreen, no text, no labels, no arrows, no diagrams, "
        "no UI, no PPT layout, no watermark")
BASE_NEG = ("No text, letters, numbers, captions, labels, arrows, diagrams, UI, PPT "
            "layout, watermark, cartoon style, flat illustration, split-screen panels, "
            "collage.")
HIST_NEG = (" No modern clothing or modern objects; any paper, dial or instrument "
            "markings must be indistinct fine engraving, strictly illegible; no "
            "readable writing anywhere in the image.")
MACH_NEG = (" No screens with characters or code; any display glow must be abstract "
            "light without glyphs; no UI elements.")
SPACE_NEG = (" Do not add spacecraft, satellites, planets or moons beyond those "
             "explicitly described; keep celestial body counts exact.")

HIST_KEYS = ("黄铜","书房","沙龙","仪器","档案","巴黎","天文钟","节拍器","沙漏","卷轴","抽屉","气象站","象限仪","手稿","太阳系仪","天平","卡尺","静物","桌面","记录簿","望远镜目镜")
MACH_KEYS = ("机房","格构","气象中心","机械计算","计算装置","机柜")

CPS_FINAL = 3.42          # voiced chars per final second (4.42 raw x 0.774224)
INTRA_GAP = 0.19          # intra-paragraph utterance gap (0.2/1.06)
PARA_GAP = 0.4245         # inter-paragraph gap
CHAP_GAP = 0.7547         # inter-chapter gap

MOTION_SCALE = {
    "push_in":      dict(direction="push_in",  reference_scale=[1.02, 1.14]),
    "push_in_hold": dict(direction="push_in",  reference_scale=[1.02, 1.12], hold=True),
    "pull_out":     dict(direction="pull_out", reference_scale=[1.14, 1.02]),
    "pan_left":     dict(direction="pan_left", reference_scale=None),
    "pan_right":    dict(direction="pan_right", reference_scale=None),
    "pan_up":       dict(direction="pan_up",   reference_scale=None),
    "diag_drift":   dict(direction="diag_drift", reference_scale=None),
}

def neg_for(shot):
    neg = BASE_NEG
    blob = (shot.get("sc") or "") + (shot.get("cp") or "")
    if any(k in blob for k in HIST_KEYS):
        neg += HIST_NEG
    if any(k in blob for k in MACH_KEYS):
        neg += MACH_NEG
    if shot.get("m") == "V" or any(k in blob for k in ("深空","星空","轨道","天体","月亮","行星","太阳","星野","云海","流星")):
        neg += SPACE_NEG
    return neg

def build():
    utt_doc = json.loads((EP / "audio" / "utterances.json").read_text(encoding="utf-8"))
    from collections import defaultdict
    para_utts = defaultdict(list)
    for u in utt_doc["utterances"]:
        para_utts[u["paragraph_id"]].append(u)
    paras = {}
    for pid in utt_doc["paragraph_order"]:
        us = para_utts[pid]
        paras[pid] = dict(section=us[0]["section"], text="".join(x["text"] for x in us),
                          n_utts=len(us))

    shots, doc_parts = [], []
    doc_parts.append("# 全量镜头提示词（牛顿到混沌）\n\n机器真源为 SHOT_PLAN.json。"
                     "受控模拟镜头无生图提示词，仅登记模拟键名与意图。")
    order = [pid for pid in utt_doc["paragraph_order"] if not pid.startswith("intro-")]
    # running estimate offsets within body
    t = 0.0
    prev_section = None
    stats = defaultdict(int)
    for pid in order:
        p = paras[pid]
        if prev_section is not None and p["section"] != prev_section:
            t += CHAP_GAP
        prev_section = p["section"]
        voice_s = len(p["text"]) / CPS_FINAL
        para_s = voice_s + (p["n_utts"] - 1) * INTRA_GAP
        beats = BEATS[pid]
        n = len(beats)
        shot_s = para_s / n
        for i, b in enumerate(beats, 1):
            sid = f"{pid}-s{i:02d}"
            common = dict(id=sid, paragraph_id=pid, section=p["section"],
                          narration=p["text"], scene=b["sc"],
                          est_seconds=round(shot_s, 2),
                          est_body_offset_s=round(t, 2),
                          status="planned",
                          timing=dict(mode="planned_estimate",
                                      note="估算值，音轨完成后按实际采样回填"))
            if b["m"] == "S":
                sim = SIMS[b["sim"]]
                rec = dict(common, shot_class="controlled_simulation",
                           strategy="V1", sim_key=b["sim"],
                           sim_intent=sim["intent"],
                           sim_duration_s=sim["duration_s"],
                           image_prompt=None, image_mode=None,
                           loop_allowed=False, tail_extension_seconds=0)
                stats["sim"] += 1
                doc_parts.append(f"\n## {sid}\n\n对应口播：{p['text']}\n\n"
                                 f"组合：受控模拟 {b['sim']}（{sim['intent']}）\n")
            elif b["m"] == "V":
                neg = neg_for(b)
                prompt = f"{SKEL}. {b['sc']} {b['cp']} {neg}"
                rec = dict(common, shot_class="image_to_video", strategy=b.get("st", "V3"),
                           image_prompt=prompt, image_mode="single" if b.get("md") == "single" else "2x2_tile",
                           motion_prompt=b["mp"], loop_allowed=False, tail_extension_seconds=2.5,
                           image_motion=None)
                stats["i2v"] += 1
                doc_parts.append(f"\n## {sid}\n\n对应口播：{p['text']}\n\n组合：{b.get('st','V3')}；{b.get('md','single')}\n\n图片：{prompt}\n\n动态：{b['mp']}\n")
            else:
                neg = neg_for(b)
                prompt = f"{SKEL}. {b['sc']} {b['cp']} {neg}"
                mo = MOTION_SCALE[b.get("mo", "push_in")]
                strategy = "P2" if mo.get("hold") else "P1"
                rec = dict(common, shot_class="image_camera_motion", strategy=strategy,
                           image_prompt=prompt, image_mode="single" if b.get("md") == "single" else "2x2_tile",
                           motion_prompt=None, loop_allowed=False, tail_extension_seconds=0,
                           image_motion=dict(direction=mo["direction"],
                                             reference_scale=mo["reference_scale"],
                                             endpoint_hold_seconds=1.2 if mo.get("hold") else 0))
                stats["p1" if strategy == "P1" else "p2"] += 1
                doc_parts.append(f"\n## {sid}\n\n对应口播：{p['text']}\n\n组合：{strategy}；{b.get('md','tile')}\n\n图片：{prompt}\n\n动态：不生成模型动态（静帧运镜 {mo['direction']}）\n")
            shots.append(rec)
        t += para_s + PARA_GAP
    body_est_s = t - PARA_GAP  # last para gap not appended at very end
    plan = dict(
        schema_version=1,
        episode="newton-to-chaos",
        source_sha256=utt_doc["source_sha256"],
        created_at="2026-10-14",
        fps=30, width=1920, height=1080,
        body_est_seconds=round(body_est_s, 1),
        body_est_minutes=round(body_est_s / 60, 1),
        cps_final=CPS_FINAL, intra_gap_s=INTRA_GAP, para_gap_s=PARA_GAP, chap_gap_s=CHAP_GAP,
        counts=dict(total=len(shots), **stats),
        notes=[
            "镜头数由内容与段落结构决定；估算时长用 chars/3.42，音轨完成后回填实际起止。",
            "受控模拟镜头：可复现数值模拟，初条件/算法/单位写入 run manifest；不交给I2V自由发挥。",
            "片头(正文引入之前的'片头'章节)单独走 intro-node 流程，不在本表。",
            "2x2_tile 仅为批量生产方式，裁后逐格验收，最终每镜为独立16:9画面；复杂几何与关键特写独立生成。",
        ],
        shots=shots,
    )
    (EP / "visual" / "SHOT_PLAN.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    (EP / "visual" / "ALL_SHOT_PROMPTS.md").write_text("\n".join(doc_parts) + "\n", encoding="utf-8")
    print("shots:", len(shots), "counts:", dict(stats))
    print("body est:", round(body_est_s, 1), "s =", round(body_est_s / 60, 1), "min")
    # sanity: every body paragraph covered
    missing = [pid for pid in order if pid not in BEATS]
    extra = [pid for pid in BEATS if pid not in order]
    print("missing beats:", missing)
    print("extra beats:", extra)

if __name__ == "__main__":
    build()
