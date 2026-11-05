param([Parameter(Mandatory=$true)][string]$Batches)
$B = 'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\audio\vo-raw\ch2-6_A_v4'
New-Item -ItemType Directory -Force "$B\logs" | Out-Null
$p = Start-Process powershell -WindowStyle Hidden -PassThru -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',"$B\jobs\gpu_queue.ps1",'-Batches',$Batches
"launched pid $($p.Id)"
