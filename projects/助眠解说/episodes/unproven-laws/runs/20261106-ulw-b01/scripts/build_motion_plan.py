# -*- coding: utf-8 -*-
"""Build motion_plan.json for the subpixel affine renderer from timeline.json."""
import json
from pathlib import Path
from PIL import Image

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")
CROPS = RUN / "crops_full"
REUSE = {
    "c0-s11": "c0-s01", "c1-s18": "c1-s17", "c1-s19": "c1-s17", "c1-s20": "c1-s17",
    "c2-s22": "c2-s21", "c3-s10": "c3-s09", "c5-s08": "c5-s07",
    "c6-s15": "c6-s14", "c8-s09": "c8-s08",
}
BLACK = {"c3-s18", "c5-s21", "c6-s16", "c7-s14", "c8-s10"}

black = RUN / "black.png"
if not black.exists():
    Image.new("RGB", (1920, 1080), (0, 0, 0)).save(black)


def view(z, x=0.5):
    w = 1.0 / z
    return [round(x - w / 2, 6), round((1 - w) / 2, 6), round(w, 6), round(w, 6)]


def main():
    tl = json.loads((RUN / "timeline.json").read_text(encoding="utf-8"))
    shots = []
    for sec in tl["sections"]:
        for s in sec["shots"]:
            nf = int(round(s["end"] * 30)) - int(round(s["start"] * 30))
            nf = max(2, nf)
            dur = nf / 30.0
            m = s.get("motion") or ""
            long = dur > 25
            if s["id"] in BLACK:
                src, sv, ev = black, view(1.0), view(1.0)
            else:
                src = CROPS / (REUSE.get(s["id"], s["id"]) + ".png")
                if "拉" in m:
                    sv, ev = view(1.06), view(1.0)
                elif "横移" in m:
                    w = 1 / 1.05
                    sv = [0.0, (1 - w) / 2, w, w]
                    ev = [1 - w, (1 - w) / 2, w, w]
                elif "静" in m:
                    sv = ev = view(1.0)
                else:
                    z1 = 1.04 if long else 1.06
                    sv, ev = view(1.0), view(z1)
            shots.append({"id": s["id"], "source": str(src), "duration_s": dur,
                          "start_view": sv, "end_view": ev,
                          "curve": {"type": "ramped_linear", "ramp_s": 0.6}})
    plan = {"schema_version": 1, "backend": "affine",
            "output": {"width": 1920, "height": 1080, "fps": 30},
            "transition_s": 0,
            "overview": "unproven-laws 20261106 affine motion, 159 shots",
            "shots": shots}
    out = RUN / "motion_plan.json"
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    print("shots", len(shots), "total_s", round(sum(s["duration_s"] for s in shots), 2))


if __name__ == "__main__":
    main()
