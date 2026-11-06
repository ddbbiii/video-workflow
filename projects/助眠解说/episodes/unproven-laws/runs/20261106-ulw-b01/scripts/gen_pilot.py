# -*- coding: utf-8 -*-
"""Pilot generator for unproven-laws c0. Reads key from HKCU\\Environment IMAGE_RELAY_KEY_1K.
Never prints or writes the key. Raw API image only; cropping is a separate step."""
import base64, hashlib, json, threading, time, urllib.error, urllib.request, winreg
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RUN = Path(r"E:\program\1project\video\projects\助眠解说\episodes\unproven-laws\runs\20261106-ulw-b01")
ENDPOINT = "https://dklapi.com/v1/images/generations"
MODEL = "gpt-image-2.5-sunburst"
SIZE = "2048x1152"
LOCK = threading.Lock()
STOP = {"flag": False, "consec_fail": 0}


def log(msg):
    line = time.strftime("%Y-%m-%d %H:%M:%S") + " " + msg
    with LOCK:
        with open(RUN / "gen.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
        print(line, flush=True)


def get_key():
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
        return winreg.QueryValueEx(k, "IMAGE_RELAY_KEY_1K")[0]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run_job(job, key):
    if STOP["flag"]:
        log("SKIP %s (stop flag)" % job["job_id"])
        return
    name = job["job_id"]
    out = RUN / "raw" / (name + ".png")
    res_path = RUN / "results" / (name + ".json")
    if out.exists() or res_path.exists():
        log("SKIP %s exists (no overwrite)" % name)
        return
    text = job["final_request_text"]
    payload = {"model": MODEL, "size": SIZE, "n": 1, "prompt": text}
    result = {
        "job_id": name, "kind": job["kind"], "scope": job.get("scope"),
        "attempts": [], "request_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
    }
    for attempt in (1, 2):
        t0 = time.time()
        log("CALL %s attempt %d" % (name, attempt))
        att = {"attempt": attempt, "started": time.strftime("%Y-%m-%d %H:%M:%S")}
        result["attempts"].append(att)
        try:
            req = urllib.request.Request(
                ENDPOINT, data=json.dumps(payload).encode("utf-8"),
                headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
                method="POST")
            try:
                with urllib.request.urlopen(req, timeout=900) as r:
                    raw, status = r.read(), r.status
            except urllib.error.HTTPError as e:
                raw, status = e.read(), e.code
            att["http_status"] = status
            att["elapsed_s"] = round(time.time() - t0, 1)
            if not 200 <= status < 300:
                att["error"] = raw[:400].decode("utf-8", "replace").replace(key, "[redacted]")
                log("HTTP %d %s %s" % (status, name, att["error"][:200]))
                if status in (401, 402, 403, 429):
                    STOP["flag"] = True
                    log("STOP flag set: HTTP %d" % status)
                    break
                low = att["error"].lower()
                time.sleep(90 if ("rate limit" in low or "rpm" in low or "unavailable" in low) else 20)
                continue
            data = json.loads(raw.decode("utf-8"))
            item = data["data"][0]
            if item.get("b64_json"):
                img = base64.b64decode(item["b64_json"])
            else:
                with urllib.request.urlopen(item["url"], timeout=600) as r:
                    img = r.read()
            out.parent.mkdir(exist_ok=True)
            out.write_bytes(img)
            result.update(status="ok", raw=str(out), raw_sha256=sha(out), usage=data.get("usage"))
            log("OK %s %.1fs" % (name, att["elapsed_s"]))
            break
        except Exception as e:
            att["error"] = (type(e).__name__ + ": " + str(e)).replace(key, "[redacted]")[:400]
            att["elapsed_s"] = round(time.time() - t0, 1)
            log("ERR %s %s" % (name, att["error"][:200]))
            time.sleep(20)
    result.setdefault("status", "failed")
    with LOCK:
        if result["status"] == "ok":
            STOP["consec_fail"] = 0
        else:
            STOP["consec_fail"] += 1
            if STOP["consec_fail"] >= 2:
                STOP["flag"] = True
    result["api_calls"] = len(result["attempts"])
    res_path.parent.mkdir(exist_ok=True)
    res_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    import sys
    wanted = sys.argv[1:] or ["G01", "G02", "S01", "S02"]
    m = json.loads((RUN / "grid-manifest.json").read_text(encoding="utf-8"))
    jobs = {j["job_id"]: j for j in m["jobs"]}
    sel = [jobs[w] for w in wanted if w in jobs]
    log("START jobs=%s concurrency=2" % ",".join(j["job_id"] for j in sel))
    key = get_key()
    with ThreadPoolExecutor(max_workers=2) as ex:
        list(ex.map(lambda j: run_job(j, key), sel))
    log("DONE")


if __name__ == "__main__":
    main()
