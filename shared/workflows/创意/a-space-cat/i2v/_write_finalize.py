from pathlib import Path
fin = r'''# a-space-cat v6 compose: same method as lieqi finalize_lieqi_v3.py
# Prefer clips_v6_h3 for key shots when present; else clips_v6_ltx_draft.
# Normalize each shot to 1080x1920/24fps, swap in VoxCPM2 VO, concat. No subtitles.
import os, json, time, subprocess, shutil
from pathlib import Path

BASE = Path(r"E:\program\1project\video\projects\创意\episodes\a-space-cat")
CLIPS_H3 = BASE / "video" / "clips" / "h3"
CLIPS_LTX = BASE / "video" / "clips" / "ltx_draft"
AUDIO = BASE / "audio" / "vo_v6_final"
SHOTLIST = BASE / "storyboard" / "shotlist_v6.json"
OUT = BASE / "video"
WORK = BASE / "video" / "clips" / "compose_v6"
OUT.mkdir(exist_ok=True)
WORK.mkdir(exist_ok=True)

shots = json.loads(SHOTLIST.read_text(encoding="utf-8"))["shots"]
ids = [s["id"] for s in shots]


def dur(sid, s):
    w = AUDIO / (sid + ".wav")
    if w.exists():
        q = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(w)],
            capture_output=True, text=True,
        )
        try:
            return float(q.stdout.strip())
        except Exception:
            pass
    return float(s.get("duration_hint_sec") or 2.0)


def pick_clip(sid):
    h3 = CLIPS_H3 / (sid + ".mp4")
    ltx = CLIPS_LTX / (sid + ".mp4")
    if h3.exists() and h3.stat().st_size > 10000:
        return h3, "h3"
    if ltx.exists() and ltx.stat().st_size > 10000:
        return ltx, "ltx_draft"
    return None, None


missing = []
sources = {}
for sid in ids:
    src, tier = pick_clip(sid)
    if src is None:
        missing.append(sid)
    else:
        sources[sid] = (src, tier)
if missing:
    raise SystemExit("missing clips: %s" % missing)

h3_used = sorted(sid for sid, (_, t) in sources.items() if t == "h3")
print("H3 clips used:", ",".join(h3_used) if h3_used else "(none)", flush=True)
print("Total shots:", len(ids), flush=True)

lst = []
for s in shots:
    sid = s["id"]
    d = dur(sid, s)
    seg = WORK / (sid + ".mp4")
    lst.append(seg)
    src, tier = sources[sid]
    wav = AUDIO / (sid + ".wav")
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=24,format=yuv420p"
    cmd = [
        "ffmpeg", "-y", "-i", str(src), "-i", str(wav), "-t", f"{d:.3f}",
        "-vf", vf, "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "1",
        "-shortest", str(seg),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(sid + " normalize failed " + (r.stderr or "")[-1000:])
    print("SEG", sid, "%.2fs" % d, tier, flush=True)

concat = WORK / "concat.txt"
concat.write_text("\n".join("file '%s'" % str(x).replace("\\", "/") for x in lst), encoding="utf-8")
final = OUT / "a_space_cat_final_v6.mp4"
subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(final)], check=True)

ff = BASE / "image" / "firstframes" / "shot01.png"
if ff.exists():
    shutil.copy2(ff, BASE / "image" / "cover_v6.png")

meta = {
    "final": str(final),
    "shots": len(ids),
    "h3_shots": h3_used,
    "h3_count": len(h3_used),
    "ltx_draft_count": sum(1 for _, t in sources.values() if t == "ltx_draft"),
    "finished": time.strftime("%Y-%m-%d %H:%M:%S+08:00"),
}
(OUT / "final_v6_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height,r_frame_rate", "-of", "compact", str(final)],
    check=False,
)
print("FINAL", final, flush=True)
print("META", meta, flush=True)
'''
Path(r"E:\program\1project\video\shared\workflows\创意\a-space-cat\finalize_a_space_cat_v6.py").write_text(fin, encoding="utf-8")
# strip BOM from H3 runner if any
p = Path(r"E:\program\1project\video\shared\workflows\创意\a-space-cat\i2v\run_a_space_cat_i2v_h3_key.py")
b = p.read_bytes()
if b.startswith(b"\xef\xbb\xbf"):
    p.write_bytes(b[3:])
    print("stripped BOM")
import ast
ast.parse(p.read_text(encoding="utf-8"))
ast.parse(fin)
print("syntax OK")