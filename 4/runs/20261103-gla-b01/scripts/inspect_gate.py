# -*- coding: utf-8 -*-
import json
p = r"E:\program\1project\video\4\runs\20261103-gla-b01\subtitles\gate1\fixed.ass"
L = [l for l in open(p, encoding="utf-8-sig") if l.startswith("Dialogue")]
two = [l for l in L if "\\N" in l]
print("cues", len(L), "two_line", len(two))
for x in two[:8]:
    print(x.strip()[:120])
q = r"E:\program\1project\video\4\runs\20261103-gla-b01\subtitles\gate1\flagged.json"
print(json.load(open(q, encoding="utf-8")))
