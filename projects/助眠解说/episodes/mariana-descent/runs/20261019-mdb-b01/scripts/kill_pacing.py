import subprocess, sys
pat = sys.argv[1] if len(sys.argv) > 1 else "build_pacing"
ps = ("Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
      "Where-Object {$_.CommandLine -like '*" + pat + "*'} | "
      "Select-Object -ExpandProperty ProcessId")
out = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                     capture_output=True).stdout.decode("utf-8", "replace")
pids = [int(x) for x in out.split() if x.strip().isdigit()]
print("pids:", pids)
for p in pids:
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Stop-Process -Id %d -Force" % p], capture_output=True)
print("done")
