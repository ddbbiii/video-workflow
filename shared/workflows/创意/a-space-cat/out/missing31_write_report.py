# -*- coding: utf-8 -*-
import json
from pathlib import Path
from datetime import datetime
from PIL import Image

OUT = Path(r"E:\program\1project\video\projects\创意\episodes\a-space-cat\qa")
FF = Path(r"E:\program\1project\video\projects\创意\episodes\a-space-cat\image\firstframes")
picks = json.loads((OUT/"missing31_picks.json").read_text(encoding="utf-8"))
logs = []
for line in (OUT.parent/"logs"/"missing31_upscale_log.jsonl").read_text(encoding="utf-8").splitlines():
    if line.strip():
        logs.append(json.loads(line))
by_shot = {int(j["shot"]): j for j in logs if j.get("ok")}
PROTECTED = [2,3,4,8,9,10,13,14,19,21,25,29,30,31,34,38,41,42,45,47]
MISSING = [1,5,6,7,11,12,15,16,17,18,20,22,23,24,26,27,28,32,33,35,36,37,39,40,43,44,46,48,49,50,51]

rows = []
fails = []
for n in MISSING:
    e = picks["shots"][f"{n:02d}"]
    j = by_shot.get(n)
    p = FF / f"shot{n:02d}.png"
    size = list(Image.open(p).size) if p.exists() else None
    if not j or not p.exists() or size != [1080,1920]:
        fails.append({"shot": n, "log": j, "exists": p.exists(), "size": size})
    rows.append({
        "shot": n,
        "pick": e["pick"],
        "reason": e["reason"],
        "src": e["picked_path"],
        "out": str(p),
        "device": j.get("device") if j else None,
        "sec": j.get("sec") if j else None,
        "bytes": j.get("bytes") if j else None,
        "crop_box": j.get("crop_box") if j else None,
        "out_size": size,
    })

prot_meta = []
for n in PROTECTED:
    p = FF / f"shot{n:02d}.png"
    i = p.stat()
    prot_meta.append(f"| {n:02d} | {p.name} | {i.st_size} | {datetime.fromtimestamp(i.st_mtime).strftime('%Y-%m-%d %H:%M:%S')} |")

lines = []
lines.append("# a-space-cat missing31 pick + upscale report")
lines.append("")
lines.append(f"- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} Asia/Shanghai")
lines.append("- Batch: `a-space-cat_missing31_v6` (62 candidates → 31 picks → 31 firstframes)")
lines.append("- Target: `1080×1920` PNG into `E:\\program\\1project\\video\\projects\\创意\\episodes\\a-space-cat\\image\\firstframes\\shotXX.png`")
lines.append("- Method: `realesrgan-anime` (`RealESRGAN_x4plus_anime_6B.pth`, sha256 `f872d837…99da`)")
lines.append("- Fit: center crop to 9:16 then 4× then Lanczos → 1080×1920 (src 928×1664 → crop `[0,7,928,1657]`)")
lines.append("- i2v: **NOT started**")
lines.append("")
lines.append("## Summary")
lines.append("")
lines.append(f"- Placed into firstframes: **{len(rows) - len(fails)} / 31**")
lines.append(f"- Failures: **{len(fails)}**")
lines.append(f"- Picks: c1={sum(1 for r in rows if r['pick']=='c1')}, c2={sum(1 for r in rows if r['pick']=='c2')}")
lines.append(f"- Devices used: cpu={sum(1 for r in rows if r['device']=='cpu')}, cuda={sum(1 for r in rows if r['device']=='cuda')}")
lines.append(f"- Protected existing 20: **not overwritten** (mtimes still pre-batch except shot30 historical fix)")
lines.append("")
lines.append("## Lock interactions")
lines.append("")
lines.append("- At start: `E:\\program\\1project\\video\\shared\\work\\cache\\gpu.lock` held by **助眠解说** (b-geomagnetic TTS). Upscale ran on **CPU** to avoid contention.")
lines.append("- Mid-run: lock freed; attempted CUDA resume → **shot44 OK on cuda (15.1s)** then **GPU OOM** (~12.5GB alloc) on next frame; lock released.")
lines.append("- Remaining finished on **CPU**. Final lock state: **empty / released**.")
lines.append("- Did not kill 助眠 jobs.")
lines.append("")
lines.append("## Pick rules (documented in `missing31_picks.json`)")
lines.append("")
lines.append("1. Prefer safer composition (larger subject margin / lower edge-hug).")
lines.append("2. Else prefer silver/gray look (low sat, mid-high value; penalize warm/orange).")
lines.append("3. Else higher total = composition×1.4 + silver×1.2 + detail×0.6; tie → c1.")
lines.append("4. **Visual QA note:** agent could not reliably view candidates on this machine (CopyToBox root blocked). Heuristic picks need **视频号规划 visual accept**.")
lines.append("")
lines.append("## Pick + upscale table")
lines.append("")
lines.append("| shot | pick | device | sec | bytes | out_size | reason | src |")
lines.append("|---:|:---:|:---:|---:|---:|:---:|---|---|")
for r in rows:
    lines.append(
        f"| {r['shot']:02d} | {r['pick']} | {r['device']} | {r['sec']} | {r['bytes']} | {r['out_size']} | {r['reason']} | `{r['src']}` |"
    )
lines.append("")
lines.append("## Failures")
lines.append("")
if not fails:
    lines.append("None.")
else:
    lines.append("```json")
    lines.append(json.dumps(fails, ensure_ascii=False, indent=2))
    lines.append("```")
lines.append("")
lines.append("## Protected firstframes (untouched)")
lines.append("")
lines.append("| shot | file | bytes | mtime Asia/Shanghai |")
lines.append("|---:|---|---:|---|")
lines.extend(prot_meta)
lines.append("")
lines.append("## Artifacts")
lines.append("")
lines.append("- Picks JSON: `E:\\program\\1project\\video\\projects\\创意\\episodes\\a-space-cat\\qa\\missing31_picks.json`")
lines.append("- Inventory: `E:\\program\\1project\\video\\projects\\创意\\episodes\\a-space-cat\\qa\\missing31_candidates_inventory.json`")
lines.append("- Upscale log: `E:\\program\\1project\\video\\projects\\创意\\episodes\\a-space-cat\\logs\\missing31_upscale_log.jsonl`")
lines.append("- This report: `E:\\program\\1project\\video\\projects\\创意\\episodes\\a-space-cat\\qa\\missing31_pick_upscale_report.md`")
lines.append("")
lines.append("## Candidate roots")
lines.append("")
lines.append("- Raw (used): `E:\\program\\1project\\video\\shared\\runtime\\engines\\stills-runtime\\out\\a-space-cat\\a-space-cat_missing31_v6\\sXX\\sXX_cY.png`")
lines.append("- Shared mirror: `E:\\program\\1project\\video\\shared\\runtime\\engines\\stills-runtime\\stills_comfy_output\\stills\\a-space-cat\\sXX_cY_00001_.png`")
lines.append("")

report = OUT / "missing31_pick_upscale_report.md"
report.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("WROTE", report)
print("placed", len(rows)-len(fails), "fails", len(fails))
