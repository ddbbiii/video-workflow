# -*- coding: utf-8 -*-
"""为片头 5 个呼吸段各渲染一条 22s 的背景运镜片段(media/affine/<shot>.mp4)。

为什么单独渲染:片头段长 6-15s,而正文按段落分配的 affine 镜头时长可能不足
(14_build_intro 要求 bg 时长 ≥ 段渲染时长 + 0.05s)。这里用同一批正文静帧、
同一 P1 单向运镜模板,按片头需要的长度直接渲染,画面来源仍是正文已验收静帧池。

用法:python 12c_build_intro_bgs.py
"""
from __future__ import annotations
import json, shutil, subprocess, sys
from pathlib import Path

EP = Path(__file__).resolve().parents[3]
RUN = EP / "runs" / "20261103-gla-b01"
STILLS16 = EP / "image" / "stills_16x9"
OUT = RUN / "media" / "affine"
CM = Path(r"E:\program\1project\video\shared\camera-motion\camera_motion.py")
FF = shutil.which("ffmpeg") or r"C:\Users\10060\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg.Shared_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build-shared\bin\ffmpeg.exe"
FP = str(Path(FF).with_name("ffprobe.exe"))
FPS = 30
DUR = 22.0

# (shot_id, profile) —— profile 取自 build_pacing 同一套白名单运镜
SHOTS = [
    ("c1-s13", "pout"),   # 片头1:山间冰川舌,缓慢拉远
    ("c1-s01", "pin"),    # 片头2:星夜雪山,静止感的长推
    ("c1-s10", "panR"),   # 片头3:雪层剖面,横向缓移
    ("c1-s14", "pin"),    # 片头4:雪与冰的边界
    ("c1-s03", "diag"),   # 片头5:雪晶(主题句驻留)
]
PROFILES = {
    "pin":   ([0.010, 0.010, 0.980, 0.980], [0.055, 0.055, 0.870, 0.870]),
    "pout":  ([0.055, 0.055, 0.870, 0.870], [0.010, 0.010, 0.980, 0.980]),
    "panR":  ([0.010, 0.045, 0.900, 0.900], [0.085, 0.045, 0.900, 0.900]),
    "panL":  ([0.085, 0.045, 0.900, 0.900], [0.010, 0.045, 0.900, 0.900]),
    "diag":  ([0.010, 0.010, 0.940, 0.940], [0.065, 0.065, 0.850, 0.850]),
}


def nframes(p):
    r = subprocess.run([FP, "-v", "error", "-select_streams", "v:0",
                        "-show_entries", "stream=nb_frames", "-of", "csv=p=0", str(p)],
                       capture_output=True, text=True)
    v = r.stdout.strip()
    return int(v) if v.isdigit() else -1


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    want = round(DUR * FPS)
    for sid, prof in SHOTS:
        src = STILLS16 / f"{sid}.jpg"
        if not src.exists():
            raise SystemExit(f"missing still: {src}")
        dst = OUT / f"{sid}.mp4"
        if dst.exists() and nframes(dst) == want:
            print(f"skip {sid} ({want}f)")
            continue
        sv, ev = PROFILES[prof]
        plan = {"schema_version": 1, "backend": "affine",
                "output": {"width": 1920, "height": 1080, "fps": FPS},
                "transition_s": 0,
                "shots": [{"id": sid, "source": str(src), "duration_s": DUR,
                           "start_view": sv, "end_view": ev,
                           "curve": {"type": "ramped_linear", "ramp_s": 0.6}}]}
        tmp = OUT / f"_tmp_{sid}"
        if tmp.exists():
            shutil.rmtree(tmp)
        tmp.mkdir(parents=True)
        pp = tmp / "plan.json"
        pp.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run([sys.executable, str(CM), str(pp), "--out", str(tmp)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or r.stdout)[-800:])
        produced = tmp / f"{sid}.mp4"
        if not produced.exists():
            raise RuntimeError(f"camera_motion produced nothing for {sid}")
        shutil.move(str(produced), str(dst))
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"ok {sid} {nframes(dst)}f {prof}")


if __name__ == "__main__":
    main()
