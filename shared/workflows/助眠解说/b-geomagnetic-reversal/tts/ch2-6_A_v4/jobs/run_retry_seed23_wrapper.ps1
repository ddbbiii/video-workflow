$ErrorActionPreference = "Continue"
$logW = "E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\audio\vo-raw\ch2-6_A_v4\logs\retry_seed23_wrapper.log"
$lock = "E:\program\1project\video\shared\work\cache\gpu.lock"
$jobs = "E:\program\1project\video\shared\runtime\engines\tts\jobs\qa_takes-seed7_retry_seed23.json"
$ttsLog = "E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\audio\vo-raw\ch2-6_A_v4\logs\tts-retry_seed23.log"
function WLog($m){ Add-Content $logW (("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m)) -Encoding UTF8 }
Set-Content $logW (("[{0}] wrapper seed23 start pid={1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $PID)) -Encoding UTF8
$waited=0
while($true){
  $reasons=@()
  if(Test-Path $lock){
    try{
      $l=Get-Content $lock -Raw|ConvertFrom-Json
      if($l.pid -and (Get-Process -Id $l.pid -EA SilentlyContinue)){ $reasons += "lock:$($l.owner) pid $($l.pid)" }
      elseif($l.pid){ Remove-Item $lock -Force -EA SilentlyContinue }
    } catch { $reasons += "lock unreadable" }
  }
  $busy=Get-CimInstance Win32_Process -Filter "Name='python.exe'" -EA SilentlyContinue | Where-Object { $_.CommandLine -match 'gen_shots|gen_tts|main\.py|launch_h3|run_stills|gen_a3|infer|upscale' }
  foreach($x in $busy){ $reasons += ("proc "+$x.ProcessId) }
  try{ $mem=[int]((nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits)|Select-Object -First 1) } catch { $mem=99999 }
  if($mem -gt 7000){ $reasons += "vram $mem" }
  if($reasons.Count -eq 0){ break }
  if($waited % 120 -eq 0){ WLog ("WAIT: "+($reasons -join " | ")) }
  Start-Sleep 30; $waited+=30
}
WLog "GPU free after ${waited}s; launching run_shots"
Set-Location E:\program\1project\video\shared\runtime\engines\tts\voxcpm
Set-Content $ttsLog "" -Encoding UTF8
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\program\1project\video\shared\runtime\engines\tts\voxcpm\run_shots.ps1" -Jobs $jobs -Log $ttsLog
WLog "run_shots exit=$LASTEXITCODE"
WLog "wrapper seed23 done"