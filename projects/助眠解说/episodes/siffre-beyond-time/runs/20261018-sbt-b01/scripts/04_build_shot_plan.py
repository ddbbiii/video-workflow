# -*- coding: utf-8 -*-
"""Rebuild siffre-beyond-time visual/SHOT_PLAN.json: 段落->镜头映射 + 估算时间轴回填。

与 newton 04 的区别:siffre 镜头 v1 已先行定稿并在生图(build_shot_plan_v1.py 按
大纲节拍编制)。本脚本在口播锁定后运行,做三件事:
1. 校验 02_beats_a/b 的 段落->镜头 映射(完整性/唯一性/顺序);
2. 用 utterances 实测字数 + SHOT_PLAN 的 cps/gap 口径重算每镜 est_seconds 与
   est_body_offset_s(段落内按镜头 est 权重分摊);
3. 回填 paragraph_id / narration,状态 planned_outline_basis -> planned_narration_basis。
   image_prompt / motion_prompt / strategy / image_mode / tail_extension_seconds /
   image_motion 等生产字段原样保留(只读,不重生成)。

前置:01_parse_narration.py 已跑(audio/utterances.json 为锁定稿);
     02_beats_a/b.py 已编排映射。
注意:本脚本只更新 JSON;visual/ALL_SHOT_PROMPTS.md 为人读索引,真源是 JSON,
     改镜头请改 visual/build_shot_plan_v1.py 重跑。
估算值在 09_build_chapter_audio.py 产出实测 timeline 后全部作废,以实测为准。
"""
from __future__ import annotations
import json, sys
from collections import defaultdict
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
EP = HERE.parents[2]
sys.path.insert(0, str(HERE))
from importlib import import_module as _im

PLAN_JSON = EP / "visual" / "SHOT_PLAN.json"
UTT_JSON = EP / "audio" / "utterances.json"
BODY_SECTIONS = ["bridge", "ch01", "ch02", "ch03", "ch04", "ch05",
                 "ch06", "ch07", "ch08", "ch09", "ch10", "epilogue"]


def main():
    # 0. 输入
    if not UTT_JSON.exists():
        raise SystemExit("audio/utterances.json 不存在:先跑 01_parse_narration.py(口播锁定后)。")
    utt = json.loads(UTT_JSON.read_text(encoding="utf-8"))
    beats = {}
    for mod, attr in (("02_beats_a", "BEATS_A"), ("02_beats_b", "BEATS_B")):
        beats.update(_im(mod).__dict__[attr])
    if not beats:
        raise SystemExit("02_beats_a/b 映射为空:口播锁定后先在 02_beats_a/b.py 编排 段落->镜头 映射。")

    plan = json.loads(PLAN_JSON.read_text(encoding="utf-8"))
    shots = plan["shots"]
    by_id = {s["id"]: s for s in shots}

    # 1. 校验映射(同 02_beats_a.validate)
    ok, problems = _im("02_beats_a").validate(verbose=True)
    if not ok:
        raise SystemExit("beats 映射校验未通过,拒绝重建:\n  " + "\n  ".join(problems))

    # 2. 段落文本与估算时长(cps/gap 沿用 SHOT_PLAN v1 口径)
    cps = plan.get("cps_final", 3.5)
    intra = plan.get("intra_gap_s", 0.19)
    para_gap = plan.get("para_gap_s", 0.4245)
    chap_gap = plan.get("chap_gap_s", 0.7547)
    para_utts = defaultdict(list)
    for u in utt["utterances"]:
        para_utts[u["paragraph_id"]].append(u)
    order = [pid for pid in utt["paragraph_order"] if not pid.startswith("intro-")]
    paras = {}
    for pid in order:
        us = [u for u in para_utts[pid] if not u.get("tts_blocked")]
        paras[pid] = dict(section=us[0]["section"] if us else para_utts[pid][0]["section"],
                          text="".join(u["text"] for u in us), n_utts=len(us))
    missing_map = [pid for pid in order if pid not in beats]
    extra_map = [pid for pid in beats if pid not in paras]
    if missing_map or extra_map:
        raise SystemExit(f"映射与段落不一致 missing={missing_map} extra={extra_map}")

    # 3. 重排:按段落顺序展开镜头,est 加权分摊段落估算时长
    t = 0.0
    prev_section = None
    new_shots = []
    for pid in order:
        p = paras[pid]
        if prev_section is not None and p["section"] != prev_section:
            t += chap_gap
        prev_section = p["section"]
        voice_s = len(p["text"]) / cps
        para_s = voice_s + max(0, p["n_utts"] - 1) * intra
        sids = beats[pid]
        ests = [by_id[s].get("est_seconds") or 1 for s in sids]
        total_est = sum(ests)
        for sid, my_est in zip(sids, ests):
            rec = dict(by_id[sid])  # 生产字段原样保留
            shot_s = para_s * (my_est / max(total_est, 1e-6))
            rec.update(paragraph_id=pid, section=p["section"], narration=p["text"],
                       est_seconds=round(shot_s, 2), est_body_offset_s=round(t, 2),
                       status="planned_narration_basis",
                       timing=dict(mode="planned_estimate",
                                   note="口播锁定稿字数估算;音轨完成后由 timeline.json 实测回填"))
            new_shots.append(rec)
            t += shot_s
        t += para_gap
    body_est_s = t - para_gap

    # 4. 写回(备份 v1)
    backup = PLAN_JSON.with_suffix(".json.bak-pre-rebuild")
    if not backup.exists():
        backup.write_text(PLAN_JSON.read_text(encoding="utf-8"), encoding="utf-8")
    counts = defaultdict(int)
    for s in new_shots:
        counts[s["shot_class"]] += 1
        counts[f"strategy_{s['strategy']}"] += 1
    plan.update(shots=new_shots, source_sha256=utt["source_sha256"],
                basis=f"story/NARRATION_MASTER.md 锁定稿 (sha {utt['source_sha256'][:8]}…) + beats 映射",
                rebuilt_at=str(date.today()),
                body_est_seconds=round(body_est_s, 1),
                body_est_minutes=round(body_est_s / 60, 1),
                counts=dict(total=len(new_shots), **counts),
                )
    plan["notes"] = [n for n in plan.get("notes", [])
                     if "narration/paragraph_id 为空" not in n] + [
        f"{date.today()} 口播锁定后重建:段落映射与估算时间轴已回填(narration_basis);"
        "生产提示词字段未动。实测时间轴以 runs/20261018-sbt-b01/timeline.json 为准。"]
    PLAN_JSON.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    print("shots:", len(new_shots), "counts:", dict(counts))
    print("body est:", round(body_est_s, 1), "s =", round(body_est_s / 60, 1), "min")
    print("backup v1 ->", backup.name)


if __name__ == "__main__":
    main()
