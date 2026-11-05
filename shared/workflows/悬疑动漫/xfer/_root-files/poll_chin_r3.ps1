$log = "E:\program\1project\video\shared\work\scratch\legacy-numbered\chengwu-hoodie-male-v1-chin-r3\smoke-chin-r3.log"
$err = "E:\program\1project\video\shared\work\scratch\legacy-numbered\chengwu-hoodie-male-v1-chin-r3\smoke-chin-r3.err.log"
Write-Output "---LOG---"
if (Test-Path $log) { Get-Content $log }
Write-Output "---ERR---"
if (Test-Path $err) { Get-Content $err }
Write-Output "---OUT_FILES---"
Get-ChildItem "E:\program\1project\video\shared\work\scratch\legacy-numbered\chengwu-hoodie-male-v1-chin-r3\*.png" -ErrorAction SilentlyContinue | Select-Object Name,Length,LastWriteTime
$proc = Get-Process -Id 32632 -ErrorAction SilentlyContinue
Write-Output ("PROC_ALIVE=" + [bool]$proc)
$q = Invoke-WebRequest -Uri "http://127.0.0.1:8188/queue" -UseBasicParsing -TimeoutSec 5
Write-Output ("QUEUE=" + $q.Content)
