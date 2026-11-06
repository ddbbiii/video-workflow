# -*- coding: utf-8 -*-
"""Append S03 (replacement for c0-s05: blank page, no writing) to the pilot manifest."""
import json
from pathlib import Path

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")
STYLE = (
    "cinematic historical science documentary, photorealistic, deep teal-blue shadows with "
    "controlled warm amber highlights, volumetric light, fine material texture, layered depth, "
    "asymmetrical cinematic composition, calm dreamlike mood, 16:9 widescreen"
)
S03 = "\n\n".join([
    "A single 2048x1152 cinematic photograph, candlelit wooden desk, close shot. A single hand "
    "with a dark wool cuff and a white lace cuff (no face, no head) holds a white quill just "
    "above a blank sheet of aged paper. The paper is completely blank: no writing, no ink "
    "marks, no letters, no lines, no symbols. A small glass ink pot and a brass candlestick "
    "with a lit candle sit at the right. Warm candlelight from the right, deep teal shadows, "
    "faint dust in the air, shallow depth of field. No text, no letters, no numbers, no labels, "
    "no watermark. " + STYLE + ".",
])
p = RUN / "grid-manifest.json"
m = json.loads(p.read_text(encoding="utf-8"))
m["jobs"] = [j for j in m["jobs"] if j["job_id"] != "S03"]
m["jobs"].append({"job_id": "S03", "kind": "single", "scope": "c0-s05(replacement)",
                  "final_request_text": S03})
m["planned_calls"] = m.get("planned_calls", 0) + 1
p.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
print("jobs", [(j["job_id"], j["kind"]) for j in m["jobs"]])
