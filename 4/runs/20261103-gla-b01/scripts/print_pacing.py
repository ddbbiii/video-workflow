# -*- coding: utf-8 -*-
import json
p = r"E:\program\1project\video\4\runs\20261103-gla-b01\manifests\pacing_plan.json"
d = json.load(open(p, encoding="utf-8"))
for q in d["paragraphs"]:
    segs = " | ".join("%s:%.1fs/%s" % (s["sid"], s["dur_s"], s["profile"]) for s in q["segments"])
    print("%s %.1fs -> %s" % (q["pid"], q["dur_s"], segs))
print("use_count>2", {k: v for k, v in d["use_count"].items() if v > 2})
print("nseg", sum(len(q["segments"]) for q in d["paragraphs"]))
