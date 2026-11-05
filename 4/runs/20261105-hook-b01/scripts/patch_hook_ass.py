# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(r"E:\program\1project\video\4\runs\20261105-hook-b01\scripts\hook_intro.py")
s = p.read_text(encoding="utf-8")

NEW_RENDER = '''def render_intro(meta, cues):
    """背景 + 音轨 + ASS 矢量大字；不做逐帧位图缩放，避免边缘爬行/颤抖。"""
    D = round(meta["intro_seconds"] * FPS) / FPS
    bg = build_bg(meta)
    av = RUN / "intro_av.mp4"
    subprocess.run([FF, "-y", "-i", str(bg), "-i", str(RUN / "intro.wav"),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", str(av)],
                   check=True, capture_output=True)
    assdir = RUN / "preview" / "burn"
    (assdir / "fonts").mkdir(parents=True, exist_ok=True)
    for f in Path(r"E:\\program\\1project\\video\\assets\\助眠解说\\subtitles\\style-r4\\fonts").glob("*"):
        (assdir / "fonts" / f.name).write_bytes(f.read_bytes())
    for f in Path(r"E:\\program\\1project\\video\\assets\\助眠解说\\intro\\fonts").glob("MaShanZheng*"):
        (assdir / "fonts" / f.name).write_bytes(f.read_bytes())
    ass = assdir / "hook.ass"
    write_hook_ass(meta, cues, ass)
    out = RUN / "intro_sub.mp4"
    burn(av, RUN / "intro.wav", ass, out)
    return out
'''

a = s.index("def render_intro")
b = s.index("SUBFONT =", a)
s = s[:a] + NEW_RENDER + "\n\n" + s[b:]

# main: 替换旧的两段式 mux/burn
start = s.index("    silent = render_intro(meta, cues)")
end = s.index("    # A: 现有成片 30s", start)
s = s[:start] + "    intro_sub = render_intro(meta, cues)\n" + s[end:]
s = s.replace('str(RUN / "intro_sub.mp4")', 'str(intro_sub)')

WRITE_HOOK = '''def write_hook_ass(meta, cues, path):
    hdr = (
        "[Script Info]\\nScriptType: v4.00+\\nPlayResX: 1920\\nPlayResY: 1080\\n"
        "WrapStyle: 2\\nScaledBorderAndShadow: yes\\n\\n[V4+ Styles]\\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
        "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\\n"
        "Style: Big,Ma Shan Zheng,132,&H00E9F1F6,&H000000FF,&H00180F0A,"
        "&H80000000,0,0,0,0,100,100,0,0,1,5,2,5,0,0,0,1\\n"
        "Style: Title,Ma Shan Zheng,110,&H00E9F1F6,&H000000FF,&H00180F0A,"
        "&H80000000,0,0,0,0,100,100,0,0,1,5,2,5,0,0,0,1\\n"
        "Style: B,Source Han Sans SC Heavy,96,&H00FFFFFF,&H000000FF,&H00000000,"
        "&H80000000,0,0,0,0,100,100,0,0,1,5,2,2,96,96,118,1\\n\\n[Events]\\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\\n")

    def at(t):
        h = int(t // 3600); m = int(t % 3600 // 60); s = int(t % 60)
        cs = int(round((t % 1) * 100))
        if cs == 100:
            s += 1; cs = 0
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    u = meta["units"]
    s1, e1 = VT["head_s"] - 0.10, u[1]["start_s"] - 0.30
    s2, e2 = u[1]["start_s"] - 0.10, u[2]["start_s"] - 0.35
    text1 = "".join(CFG["display_text_1"])
    text2 = "".join(CFG["display_text_2"])

    def anim(ss, ee):
        ms = max(1, int(round((ee - ss) * 1000)))
        out0 = max(0, ms - 400)
        return (f"{{\\\\an5\\\\move(960,548,960,540,0,{ms})"
                f"\\\\fscx72\\\\fscy72\\\\alpha&HFF&"
                f"\\\\t(0,140,\\\\fscx106\\\\fscy106)"
                f"\\\\t(0,100,\\\\alpha&H00&)"
                f"\\\\t(140,440,\\\\fscx100\\\\fscy100)"
                f"\\\\t(440,{ms},\\\\fscx107\\\\fscy107)"
                f"\\\\t({out0},{ms},\\\\alpha&HFF&)}}")

    with path.open("w", encoding="utf-8") as f:
        f.write("\\ufeff" + hdr)
        f.write(f"Dialogue: 0,{at(s1)},{at(e1)},Big,,0,0,0,,{anim(s1, e1)}{text1}\\n")
        f.write(f"Dialogue: 0,{at(s2)},{at(e2)},Big,,0,0,0,,{anim(s2, e2)}{text2}\\n")
        ct = CFG.get("center_title")
        if ct:
            ts = u[2]["start_s"] + float(CFG.get("center_title_delay_s", 0.15))
            cd = float(CFG.get("center_title_s", 3.2))
            ms = int(round(cd * 1000))
            f.write(f"Dialogue: 0,{at(ts)},{at(ts + cd)},Title,,0,0,0,,"
                    f"{{\\\\an5\\\\pos(960,540)\\\\alpha&HFF&"
                    f"\\\\t(0,450,\\\\alpha&H00&)\\\\t({max(0, ms - 400)},{ms},\\\\alpha&HFF&)}}{ct}\\n")
        for c in cues:
            f.write(f"Dialogue: 0,{at(c['start_s'])},{at(c['end_s'])},B,,0,0,0,,{sub_br(c['text'])}\\n")


'''
# 插到 write_ass 之前
idx = s.index("def write_ass(")
s = s[:idx] + WRITE_HOOK + s[idx:]

p.write_text(s, encoding="utf-8")
print("patched", len(s))
