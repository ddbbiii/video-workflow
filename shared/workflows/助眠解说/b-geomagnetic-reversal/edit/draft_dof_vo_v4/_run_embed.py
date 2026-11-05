import subprocess, sys
from pathlib import Path
log = Path(r"E:\\program\\1project\\video\\projects\\助眠解说\\episodes\\b-geomagnetic-reversal\\audio\\draft_dof_vo_v4\\logs\\embed.log")
script = Path(r"E:\\program\\1project\\video\\shared\\workflows\\助眠解说\\b-geomagnetic-reversal\\edit\\draft_dof_vo_v4\\_tools\\embed_select_v1_v4.py")
py = r"E:\\program\\language\\python\\Python-3.11.0\\python.exe"
log.parent.mkdir(parents=True, exist_ok=True)
with log.open("w", encoding="utf-8") as f:
    f.write(f"START embed\n")
    f.flush()
    p = subprocess.Popen([py, "-u", str(script)], stdout=f, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    code = p.wait()
    f.write(f"\nEXIT_CODE={code}\n")
sys.exit(code)
