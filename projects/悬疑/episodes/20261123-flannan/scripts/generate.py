"""Run the approved episode image plan through the configured repository routes."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
import fcntl
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import urllib.request
from threading import Lock
from collections import Counter

from PIL import Image, ImageOps
from prepare import EP, ROLE

ROOT = EP.parents[3]
spec = importlib.util.spec_from_file_location("image_api", ROOT / "projects/悬疑/visual-tests/20261114-pilot-8shots/gen_pilot.py")
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)
api.TIMEOUT_S = 300
# The host system proxy closes the configured relay TLS connection; the normal direct HTTPS route works.
urllib.request.install_opener(urllib.request.build_opener(urllib.request.ProxyHandler({})))
POL = json.loads((ROOT / "shared/image-api/channel-policy.json").read_text())
ACTIVE = POL["policies"][POL["active"]]
CHANNELS = ACTIVE["parallel_channels"]
POS, NEG, CEL = (api.read_block(k) for k in ("STYLE_POS", "STYLE_NEG", "CEL_BOOST"))
PLAN = json.loads((EP / "storyboard/SHOT_PLAN.json").read_text())
DEST = EP / "image"
LOG = EP / "logs"
for directory in (LOG, DEST/"raw", DEST/"anchors", DEST/"plates", DEST/"final", DEST/"references"):
    directory.mkdir(parents=True, exist_ok=True)
api.HERE = EP
api.RAW = DEST/"raw"
api.CROPS = EP/"qa"/"crops"
api.CROPS.mkdir(exist_ok=True)
base = EP.parents[1]/"visual-tests/20261123-flannan-diary-layout/lamp-room.png"
LIMIT = PLAN["budget"]["approved_limit_requested"]
BLOCKED = set(filter(None,os.environ.get("FLANNAN_UNAVAILABLE_ROUTES","").split(",")))
LEDGER = LOG/"api-requests.jsonl"
STYLE = ("Historical Scottish stone lighthouse on Eilean Mor, winter circa 1900; replace all generic modern urban subject matter with this period island setting. "
         "Angular flat fills, firm shadows, dry clear lines. Scuffed paint and salt indicate routine wear, not abandonment. "
         "Keep a clear lower fifth for external captions, keep foreground and evidence readable. No modern electronics or lettering. Interior windows show open ocean only, never another lighthouse or an island with a second lighthouse; this is the only lighthouse on this island.")
PANEL_ORDER = ("upper left", "upper right", "lower left", "lower right")
ROWS = {r["id"]:r for r in PLAN["shots"]}
PRESET_QUALITY = "Respect the reference only for identity and compatible architecture. Never copy an attached thumbnail or graphic layout into the actual output."

def record(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2)+"\n")

def acquire_budget(tag, route):
    with LEDGER.open("a+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.seek(0)
        used=sum(1 for x in stream if x.strip())
        if used>=LIMIT:
            raise RuntimeError(f"Approved image limit reached: {used} calls")
        stream.seek(0,2)
        stream.write(json.dumps(dict(number=used+1,tag=tag,channel=route))+"\n")
        stream.flush()
        os.fsync(stream.fileno())
        return used+1

def submit(tag, content, assigned, ref=None, *, cel=False):
    p=DEST/"raw"/f"{tag}.png"
    meta=LOG/f"{tag}.json"
    if p.is_file() and meta.is_file() and json.loads(meta.read_text()).get("ok"):
        return p
    prompt="\n".join(filter(None, [POS, CEL if cel else None, STYLE, content, "Avoid: "+NEG]))
    completed=[]
    for route in [assigned,*[n for n in CHANNELS if n!=assigned]]:
        if route in BLOCKED:
            continue
        channel=dict(POL["channels"][route],name=route)
        for attempt in (1,2):
            with (Path("/tmp")/f"video-workflow-image-{route}.lock").open("a") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                if route in BLOCKED:
                    break
                if not os.environ.get(channel["key_env"], "").strip():
                    BLOCKED.add(route)
                    print("DISABLED",route,"missing provisioned credential",flush=True)
                    break
                request=acquire_budget(tag,route)
                native_tag=f"request-{request:03}-{tag}"
                print("REQUEST",request,tag,route,flush=True)
                try:
                    detail=api.call(channel,prompt,{"tag":native_tag},ref,1)
                except KeyError:
                    detail=dict(ok=False,http_status=401)
            response=api.RAW/f"{native_tag}-a1-response.json"
            response.unlink(missing_ok=True) # Responses can contain signed asset URLs.
            result=dict(request=request, channel=route, model=channel["model"], endpoint="edits" if ref else "generations",
                        state="ok" if detail.get("ok") else "failed", http_status=detail.get("http_status"),
                        elapsed_s=detail.get("elapsed_s"), dims=detail.get("dims"), price_cny=channel["price_cny"])
            if detail.get("ok"):
                native_path=EP/detail["file"]
                result["metrics"]=api.measure(native_path)
                concerns=api.gate({**detail,"metrics":result["metrics"]},channel)
                if not concerns:
                    native_path.replace(p)
                    record(meta,dict(ok=True,tag=tag, prompt=prompt,file=str(p.relative_to(EP)),
                                     reference=str(ref) if ref else None, fallback_from=assigned if route!=assigned else None,
                                     attempts=[*completed,result],sha256=hashlib.sha256(p.read_bytes()).hexdigest(),**result))
                    print("READY",tag,route,detail.get("elapsed_s"),flush=True)
                    return p
                result["gate"]=concerns
                native_path.unlink(missing_ok=True)
            else:
                err=detail.get("error")
                if isinstance(err,dict) and isinstance(err.get("error"),dict):
                    raw_code=err["error"].get("code")
                    if isinstance(raw_code,str) and raw_code.replace("_","").replace("-","").isalnum():
                        result["error_code"]=raw_code[:80]
                elif isinstance(err,str) and ":" in err:
                    result["error_type"]=err.split(":",1)[0][:40]
            completed.append(result)
            record(meta,dict(ok=False,tag=tag,attempts=completed))
            print("FAILED",tag,result,flush=True)
            if detail.get("http_status") in (401,403):
                BLOCKED.add(route)
                break
            if detail.get("http_status") in (400,404,422):
                break
    raise RuntimeError(f"Image job failed: {tag}")

def fit(path, size):
    with Image.open(path) as im:
        return ImageOps.fit(im.convert("RGB"),size,method=Image.Resampling.LANCZOS)

def save(im,dest):
    dest.parent.mkdir(parents=True,exist_ok=True)
    im.save(dest)

def split(path):
    with Image.open(path) as im:
        im=im.convert("RGB")
        w,h=im.size
        for col,row in ((0,0),(1,0),(0,1),(1,1)):
            yield im.crop((col*w//2+4,row*h//2+4,(col+1)*w//2-4,(row+1)*h//2-4))

def anchor(name, channel):
    if name=="evan":
        layout=("Strict 2x2 matching model sheet. Top left full figure directly front, top right full figure exact side, bottom left full figure directly from back, bottom right front face close-up. "
                "The same one keeper in every panel, full boot soles visible in full-length panels. Very light cool blue-grey background, no dividers or labels. Strong value separation: the charcoal jacket and hair must read dark against the pale background; show sharp ink silhouettes across the whole sheet, without keeping large areas dark-on-dark. "
                "Clean cel drawing with hard dark outlines, angular readable hard light; dark ink hair and the brick-red scarf are consistent.")
    else:
        layout=("One large three-quarter figure portrait from boots to head, turned slightly, solid light cool grey background with dark clothes sharply separated from it. "
                "Clean cel drawing with strong hard shadow boundaries and no separate panels. No other people. Composition fills space from head to upper knee and subject is large. Crisp strong nearly black contours along clothing folds and outline, clear repeated knit edges and facial features, firm shadow boundaries. Focus on distinct face contour, hair and working clothes.")
    p=submit("anchor-"+name,layout+" Person specification: "+ROLE[name][2]+". Clothes are salt worn. Use plain period leather boots and wool.",channel,cel=True)
    if name=="evan":
        for view, image in zip(("front","side","back","face"),split(p)):
            save(image,DEST/"anchors"/name/f"{view}.png")
        save(fit(p,(1600,900)),DEST/"anchors"/name/"three-view.png")
    else:
        save(fit(p,(1600,900)),DEST/"anchors"/f"{name}.png")
    return p

def preflight():
    return anchor("evan","dkl-b")

def parallel(items, method):
    buckets=[[],[]]
    open_routes=[r for r in CHANNELS if r not in BLOCKED]
    if not open_routes:
        raise RuntimeError("No working image routes remain")
    if len(open_routes)==1:
        for item in items:
            method(item,open_routes[0])
        return
    for index, item in enumerate(items):
        buckets[index%2].append(item)
    def work(channel, bucket):
        for item in bucket:
            method(item,channel)
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes=[pool.submit(work,ch,b) for ch,b in zip(CHANNELS,buckets)]
        for f in outcomes:
            f.result()

def style_row(row, actors):
    visual=row["visual"]
    names=[v["id"] for v in row["character_state"]]
    layout={"E":"Wide environmental frame, off-center action; establish rooms or geography.",
            "M":"Mid-distance eyeline coverage with off-center subject and clear foreground.",
            "C":"Tight readable detail, evidence large in the frame; no crop of its essential edges."}[row["shot_type"]]
    if actors:
        population="Cast identity and clothing: "+ "; ".join(f"{r} = {ROLE[r][2]}" for r in names) + "."
    elif names:
        population=("EMPTY ARCHITECTURE PLATE for the setup below. Completely omit people, hands and reflected human outlines, "
                    "but keep their intended spacing and preserve the camera position. Place non-held evidence in its planned position. "
                    "Actor notes tell you only where empty space is needed; they are not a request to draw anyone.")
    else:
        population="No human characters or visible hands unless the fact explicitly requires anonymous silhouettes inside the far lantern window."
    position=("At the lantern room, keep the stair entrance left, large revolving lens right, and sea behind. "
              "Natural darkness stays pale enough to see the hardware, darker than the lighting on insets. "
              "Do not introduce an artificial portal, hole, mirror frame or special effects.") if row["scene_id"]=="lamp" else ""
    return " ".join([layout,visual,population,position,"Preserve scene cues: "+row["location_anchors"]+".",
                     row["environment_state"],row["negative"],
                     "Paper and watches remain without legible shapes or numbers; editable text and glints will be added later." if row.get("overlay") else ""])

def reference(ident):
    if ident=="evan":
        return DEST/"anchors"/"evan/front.png"
    return DEST/"anchors"/f"{ident}.png"

def assembly_reference(name, plate, cast, *, is_grid=False):
    with Image.open(plate) as im:
        background=im.convert("RGB")
        background.thumbnail((1536,864),Image.Resampling.LANCZOS)
    output=Image.new("RGB",(background.width,background.height+300),"#596572")
    output.paste(background,(0,0))
    from PIL import ImageDraw
    drawer=ImageDraw.Draw(output)
    step=output.width//max(1,len(cast))
    for idx,ident in enumerate(cast):
        with Image.open(reference(ident)) as inp:
            character=inp.convert("RGB")
            character.thumbnail((step-15,265),Image.Resampling.LANCZOS)
            x=idx*step+(step-character.width)//2
            output.paste(character,(x,background.height+5))
        drawer.text((idx*step+8,background.height+274),ident,fill="white")
    fname=DEST/"references"/f"{name}.png"
    save(output,fname)
    return fname

def grid_text(rows, actors=False):
    global_hint=("Draw an exact 2 by 2 contact sheet. Each cell is a DIFFERENT illustrated scene with its own complete 16:9 composition; "
                 "each cell meets its neighbour at the geometric half of the width/height. No outlines, dividers, bevels, inscriptions, labels, blank spaces; "
                 "images fill each quadrant edge to edge. Never span a person or scenery across cells.")
    items=[f"{pos}: {style_row(row, actors)}" for pos,row in zip(PANEL_ORDER,rows)]
    for pos in PANEL_ORDER[len(rows):]:
        items.append(pos+": repeat a quiet empty Scottish island sea establishing view; usable shots end above.")
    return "\n".join([global_hint,*items])

def write_frame(src, name):
    save(fit(src,(1920,1080)),DEST/"final"/f"{name}.png")

def make_single(name, route):
    row=ROWS[name]
    if name in ("S20","S36","S54"):
        return  # Matching stills are built from the corresponding source in batch().
    cast=row["character_ids"]
    shared_plates = {"S01":"S32", "S07":"S09", "S22":"S32", "S39":"S32", "S46":"S32", "S47":"S32", "S52":"S43", "S58":"S09", "S24":"S48", "S27":"S48"}
    shared = DEST/"plates"/f"{shared_plates.get(name, name)}.png"
    if name in shared_plates and shared.exists():
        raw=shared
        if not (DEST/"plates"/f"{name}.png").exists():
            shutil.copyfile(raw,DEST/"plates"/f"{name}.png")
    elif name=="S29" and base.exists():
        # Keep the established room reference as composition guidance while adding the character.
        plate=base
        if not (DEST/"plates"/f"{name}.png").is_file():
            shutil.copyfile(plate,DEST/"plates"/f"{name}.png")
        raw=plate
    else:
        raw=submit(name+"-plate",style_row(row,False),route,cel=row["shot_type"]=="C")
        save(fit(raw,(1920,1080)),DEST/"plates"/f"{name}.png")
    if cast:
        sheet=assembly_reference(name,raw,cast)
        shot=submit(name+"-cast","Attached large upper image is the EMPTY scene plate; small labeled bottom pictures show character reference ONLY. "
                    +PRESET_QUALITY+" Return a single widescreen illustrated frame only.\n"+style_row(row,True),route,sheet,cel=True)
    else:
        shot=raw
    write_frame(shot,name)

def make_grid(group, route):
    ident=group["id"]
    rows=[ROWS[n] for n in group["shots"]]
    p=submit(ident+"-plates",grid_text(rows),route,cel=False)
    shot=p
    if group["needs_cast"]:
        cast=list(dict.fromkeys(x for row in rows for x in row["character_ids"]))
        ref=assembly_reference(ident,p,cast)
        shot=submit(ident+"-cast","Attached top area is 2 by 2 EMPTY scene layout to preserve. Reference thumbs under it correspond to named roles only. "
                    "Render the four illustrated frames in exactly the same geometric positions. Never draw a reenactment of the thumbs, names or reference footer. "
                    +PRESET_QUALITY+"\n"+grid_text(rows,True),route,ref,cel=True)
    for row,tile in zip(rows,split(shot)):
        image=ImageOps.fit(tile,(1920,1080),method=Image.Resampling.LANCZOS)
        save(image,DEST/"final"/f"{row['id']}.png")
    for row,tile in zip(rows,split(p)):
        save(tile,DEST/"plates"/f"{row['id']}.png")

def intro(item,route):
    fname=DEST/"intro/v1"/f"悬疑_第四位守塔人_引入_{item['id'][-2:]}_v1.png"
    p=submit(item["id"],item["visual"]+" No words. Clean readable staged panel, single image. "
             +("Give the four heads daylight between them. Primary evidence is a clearly countable four dark human figures." if item["id"]=="I01" else ""),
             route,cel=True)
    save(fit(p,(1920,1080)),fname)

def run_job(item,route):
    kind,value=item
    {"single":make_single,"grid":make_grid,"intro":intro}[kind](value,route)

def jobs(select=None):
    output=[]
    for item in PLAN["intro"]:
        if select is None or item["id"] in select:
            output.append(("intro", item))
    for row in PLAN["shots"]:
        if row["step"]=="single" and (select is None or row["id"] in select):
            output.append(("single",row["id"]))
    for group in PLAN["grids"]:
        if select is None or set(group["shots"]) & select:
            output.append(("grid",group))
    return output

def contact(paths, out, width=400):
    from PIL import ImageDraw
    n=4
    height=width*9//16
    im=Image.new("RGB",(n*width,((len(paths)+n-1)//n)*(height+29)),"#191f26")
    d=ImageDraw.Draw(im)
    for i,(name,path) in enumerate(paths):
        x,y=(i%n)*width,(i//n)*(height+29)
        if path.exists():
            im.paste(fit(path,(width,height)),(x,y))
        d.text((x+11,y+height+6),name,fill="white")
    save(im,out)

def pilot():
    samples=["I01","I02","S09","S16","S32","S43","S50"]
    parallel(jobs(set(samples)),run_job)
    thumbs=[]
    for name in samples:
        shot=DEST/"intro/v1"/f"悬疑_第四位守塔人_引入_{name[-2:]}_v1.png" if name.startswith("I") else DEST/"final"/f"{name}.png"
        thumbs.append((name,shot))
    contact(thumbs,EP/"qa"/"pilot.jpg")

def batch():
    if not (EP/"qa/pilot-checked.md").is_file():
        raise RuntimeError("Verify production samples before batch")
    parallel(jobs(),run_job)
    for dst,src in {
        "S20":DEST/"intro/v1/悬疑_第四位守塔人_引入_01_v1.png",
        "S35":DEST/"final/S30.png", "S36":DEST/"final/S25.png", "S54":DEST/"plates/S01.png",
    }.items():
        write_frame(src,dst)
    contact([(row["id"],DEST/"final"/f"{row['id']}.png") for row in PLAN["shots"]],EP/"qa"/"body-contact.jpg",width=380)

def anchors():
    if not reference("captain").exists():
        anchor("captain","new2")
    parallel([name for name in ROLE if name not in ("evan","captain")],anchor)
    contact([("Evan "+n,DEST/"anchors/evan"/f"{n}.png") for n in ("front","side","back","face")]+
            [(name,reference(name)) for name in ROLE if name!="evan"],EP/"qa/anchors.jpg")

if __name__=="__main__":
    {"preflight":preflight,"anchors":anchors,"pilot":pilot,"batch":batch}[sys.argv[1]]()
