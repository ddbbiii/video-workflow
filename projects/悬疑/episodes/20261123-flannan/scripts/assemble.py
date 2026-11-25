"""Render and check the silent episode. Subtitle delivery follows review of the picture cut."""
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from pathlib import Path
from tempfile import TemporaryDirectory
import hashlib
import json
import re
import shutil
import subprocess
import sys

from PIL import Image
from compose import EP, phases, render_still

ROOT = EP.parents[3]
QA = EP/"qa"
LOG = EP/"logs"
PLAN_PATH = EP/"storyboard/SHOT_PLAN.json"
PLAN = json.loads(PLAN_PATH.read_text())
REVIEW = EP/"video/review/悬疑_第四位守塔人_正文_v1.mp4"
FINAL = EP/"video/final"/REVIEW.name
FPS = PLAN["fps"]

def run(*args):
    p=subprocess.run(list(map(str,args)),capture_output=True,text=True)
    if p.returncode:
        raise RuntimeError(f"{args[0]}: {p.stderr[-4000:]}\n{p.stdout[-1500:]}")
    return p

def record(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def encode(work,row,targets):
    sid=row["id"]
    off=work/f"{sid}-base.png"
    render_still(row,off)
    args=["ffmpeg","-hide_banner","-loglevel","error","-xerror","-loop",1,"-framerate",FPS,"-i",off]
    data=row.get("overlay") or {}
    if data.get("groups"):
        lit=work/f"{sid}-lit.png"
        render_still(row,lit,lit=True,xy=targets[sid])
        args+=["-loop",1,"-framerate",FPS,"-i",lit]
        f=0
        spans=[]
        for active,count in phases(row["frames"],data["groups"]):
            if active:
                spans.append(f"between(n,{f},{f+count-1})")
            f+=count
        args+=["-filter_complex_threads",1,"-filter_complex",
               "[0:v][1:v]overlay=enable='"+"+".join(spans)+"'[v]","-map","[v]"]
    else:
        args+=["-map","0:v:0"]
    run(*args,"-frames:v",row["frames"],"-an","-sn","-c:v","libx264","-preset","veryfast","-tune","stillimage",
        "-crf",17,"-pix_fmt","yuv420p","-threads",2,"-x264-params","keyint=240:min-keyint=240:scenecut=0",
        "-color_primaries","bt709","-color_trc","bt709","-colorspace","bt709","-video_track_timescale","24000",
        work/f"{sid}.mp4")
    return {"id":sid,"frames":row["frames"],"start_frame":row["start_frame"],"cue":row["cue"],"fact":row["fact"],
            "source_sha256":sha256(EP/"image/final"/f"{sid}.png"),"end":row["end"],"start":row["start"]}

def video_qa(path):
    frames=PLAN["frames"]
    metadata=json.loads(run("ffprobe","-v","error","-show_streams","-show_format","-of","json",path).stdout)
    streams=metadata["streams"]
    assert len(streams)==1 and streams[0]["codec_type"]=="video"
    v,=streams
    assert (v["width"],v["height"],v["codec_name"],v["pix_fmt"])==(1920,1080,"h264","yuv420p")
    assert Fraction(v["avg_frame_rate"])==FPS and int(v["nb_frames"])==frames
    assert abs(float(metadata["format"]["duration"])-frames/FPS)<=1/FPS
    ptsdata=json.loads(run("ffprobe","-v","error","-select_streams","v:0","-show_frames","-show_entries",
                           "frame=best_effort_timestamp","-of","json",path).stdout)["frames"]
    step=Fraction(1,FPS)/Fraction(v["time_base"])
    pts=[int(f["best_effort_timestamp"]) for f in ptsdata]
    assert len(pts)==frames and pts[0]==0
    assert max(abs(n-i*step) for i,n in enumerate(pts))==0, "CFR timestamp drift"
    intervals={}
    for k,prefix in (("black",""),("white","negate,")):
        result=run("ffmpeg","-v","info","-xerror","-i",path,"-vf",prefix+"blackdetect=d=0.95:pix_th=0.10:pic_th=0.98",
                   "-an","-f","null","-").stderr
        intervals[k]=re.findall(r"black_start:(\S+) black_end:(\S+) black_duration:(\S+)",result)
    metadata.update(black_white_intervals=intervals, frame_count=frames, picture_sha256=sha256(path))
    record(QA/"video.json",metadata)
    assert not any(intervals.values()),intervals

def render():
    rows=PLAN["shots"]
    assert PLAN["script_sha256"]==sha256(EP/"story/script.md")
    assert (QA/"body-reviewed-art.md").is_file(), "Inspect shot artwork and check plot-critical facts first"
    assert shutil.disk_usage(EP).free>12*1024**3
    targets=json.loads((QA/"flash-targets.json").read_text())
    for row in rows:
        assert (EP/"image/final"/f"{row['id']}.png").is_file()
    REVIEW.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix="flannan-encode-",dir=REVIEW.parent) as area:
        work=Path(area)
        with ThreadPoolExecutor(max_workers=4) as pool:
            manifest=list(pool.map(lambda s:encode(work,s,targets),rows))
        concat=work/"input.ffconcat"
        concat.write_text("ffconcat version 1.0\n"+"".join(
            f"file '{s['id']}.mp4'\nduration {s['frames']/FPS:.9f}\n" for s in rows))
        output=work/"review.mp4"
        run("ffmpeg","-hide_banner","-v","error","-xerror","-f","concat","-safe",0,"-i",concat,"-map","0:v:0",
            "-c:v","copy","-frames:v",PLAN["frames"],"-an","-sn","-video_track_timescale","24000","-movflags","+faststart",output)
        video_qa(output)
        output.replace(REVIEW)
    record(LOG/"render-manifest.json",{"video":str(REVIEW.relative_to(EP)),"shots":manifest,"fps":FPS,
                                       "frames":PLAN["frames"],"video_sha256":sha256(REVIEW)})
    print(REVIEW)

def check_intro():
    expected=[EP/"image/intro/v1"/f"悬疑_第四位守塔人_引入_{i:02}_v1.png" for i in (1,2)]
    for art in expected:
        with Image.open(art) as im:
            assert im.size==(1920,1080) and im.format=="PNG"
            im.verify()

def finalize():
    assert (QA/"review-approved.md").is_file(), "Review cut must be approved before exporting SRT"
    assert REVIEW.is_file()
    assert json.loads((QA/"video.json").read_text())["picture_sha256"]==sha256(REVIEW)
    check_intro()
    subs=ROOT/"shared/workflows/subtitles"
    sys.path.insert(0,str(subs))
    from split_srt import fmt_ts, normalize, read_srt, visible_len
    run(sys.executable,ROOT/"shared/workflows/script-qa/lint_narration.py",PLAN_PATH,"--json",QA/"narration-lint-final.json")
    FINAL.parent.mkdir(parents=True,exist_ok=True)
    with TemporaryDirectory(prefix="flannan-srt-",dir=FINAL.parent) as area:
        temp=Path(area)
        sentences=temp/"sentences.srt"
        sentences.write_text("\n\n".join(f"{i}\n{fmt_ts(s['start'])} --> {fmt_ts(s['end'])}\n{s['cue']}"
                                            for i,s in enumerate(PLAN["shots"],1))+"\n")
        out=temp/FINAL.with_suffix(".srt").name
        run(sys.executable,subs/"split_srt.py",sentences,"--out",out,"--report",QA/"srt-split.json")
        verdict=run(sys.executable,subs/"check_srt.py",out,"--json").stdout
        (QA/"srt-check.json").write_text(verdict)
        blocks=read_srt(out)
        assert normalize("".join(s["cue"] for s in PLAN["shots"]))==normalize("".join(x["text"] for x in blocks))
        assert blocks[0]["start"]==0 and abs(blocks[-1]["end"]-PLAN["duration"])<.001
        tmp_video=out.with_suffix(".mp4")
        shutil.copy2(REVIEW,tmp_video)
        run(sys.executable,ROOT/"shared/workflows/body-only/check_delivery.py","--video",tmp_video,"--srt",out,
            "--json",QA/"delivery.json")
        out.replace(FINAL.with_suffix(".srt"))
        tmp_video.replace(FINAL)
    (QA/"srt_qa.md").write_text(f"# 正文字幕验收\n\n{len(blocks)} 条，最长 {max(visible_len(b['text']) for b in blocks)} 字；"
        f"{fmt_ts(blocks[0]['start'])} 至 {fmt_ts(blocks[-1]['end'])}。估算时间轴，未对真实人声校准。\n")
    REVIEW.unlink()
    print(FINAL)

if __name__=="__main__":
    {"render":render,"finalize":finalize,"check-intro":check_intro}[sys.argv[1]]()
