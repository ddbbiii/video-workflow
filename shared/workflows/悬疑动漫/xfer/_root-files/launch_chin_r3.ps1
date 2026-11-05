$ErrorActionPreference = "Stop"
$py = "E:\program\language\python\Python-3.11.0\python.exe"
$src = "E:\program\1project\video\xfer\smoke_chengwu_hoodie_male_v1_chin_r3.py"
$dst = "E:\program\1project\video\shared\work\scratch\legacy-numbered\smoke_chengwu_hoodie_male_v1_chin_r3.py"
$outDir = "E:\program\1project\video\shared\work\scratch\legacy-numbered\chengwu-hoodie-male-v1-chin-r3"
$xfer = "E:\program\1project\video\xfer\keyframes-2026-09-29\chengwu-hoodie-male-chin-r3"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $xfer "PASS") | Out-Null
Copy-Item -Force $src $dst
Write-Output ("SCRIPT=" + $dst)
Write-Output ("PY_EXISTS=" + (Test-Path $py))
# verify queue still empty
$q = Invoke-WebRequest -Uri "http://127.0.0.1:8188/queue" -UseBasicParsing -TimeoutSec 5
Write-Output ("QUEUE=" + $q.Content)
$log = "E:\program\1project\video\shared\work\scratch\legacy-numbered\chengwu-hoodie-male-v1-chin-r3\smoke-chin-r3.log"
$err = "E:\program\1project\video\shared\work\scratch\legacy-numbered\chengwu-hoodie-male-v1-chin-r3\smoke-chin-r3.err.log"
# also mirror logs to xfer
$log2 = Join-Path $xfer "smoke-chin-r3.log"
$err2 = Join-Path $xfer "smoke-chin-r3.err.log"
$p = Start-Process -FilePath $py -ArgumentList $dst -WorkingDirectory "E:\program\1project\video\shared\work\scratch\legacy-numbered" -RedirectStandardOutput $log -RedirectStandardError $err -PassThru -WindowStyle Hidden
Write-Output ("PID=" + $p.Id)
Start-Sleep -Seconds 3
Write-Output "---LOG_HEAD---"
if (Test-Path $log) { Get-Content $log -TotalCount 20 }
Write-Output "---ERR_HEAD---"
if (Test-Path $err) { Get-Content $err -TotalCount 20 }
Write-Output ("PROC_ALIVE=" + (-not $p.HasExited))
