# GPU queue for zhumian b-geomagnetic-reversal ch2-6 TTS (VoxCPM2 via the deployed gen_shots.py, same env as run_shots.ps1).
# Per batch: wait for E:\program\1project\video\shared\work\cache\gpu.lock (live pid) / other TTS or ComfyUI python / busy VRAM, take the lock
# (atomic CreateNew), run every job of the batch, release the lock (only if it is still ours), pause 90 s so queued jobs can take it.
# Never kills anything. Usage: -Batches "tag1=a.json+b.json;tag2=c.json"
param([Parameter(Mandatory=$true)][string]$Batches)
$B = 'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\audio\vo-raw\ch2-6_A_v4'
$Q = "$B\logs\gpu_queue.log"
$lock = 'E:\program\1project\video\shared\work\cache\gpu.lock'
$env:HF_ENDPOINT = "https://hf-mirror.com"; $env:PYTHONIOENCODING = "utf-8"
$env:MODELSCOPE_CACHE = "E:\program\1project\video\shared\runtime\engines\tts\modelscope-cache"; $env:HF_HOME = "E:\program\1project\video\shared\runtime\engines\tts\hf-cache"
function Log($m) { Add-Content -Path $Q -Value ("[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m) -Encoding UTF8 }
function Busy() {
  $r = @()
  if (Test-Path $lock) {
    try { $l = Get-Content $lock -Raw | ConvertFrom-Json; if ($l.pid -and (Get-Process -Id $l.pid -ErrorAction SilentlyContinue)) { $r += "lock:$($l.owner) pid $($l.pid) since $($l.started)" } } catch { $r += "lock unreadable" }
  }
  $p = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'gen_shots|gen_tts|main\.py|launch_h3|run_stills|gen_a3|infer' }
  foreach ($x in $p) { $r += "proc $($x.ProcessId): $($x.CommandLine.Substring(0, [Math]::Min(140, $x.CommandLine.Length)))" }
  try { $mem = [int]((nvidia-smi --query-gpu=memory.used --format=csv,noheader,nounits) | Select-Object -First 1) } catch { $mem = 0 }
  if ($mem -gt 7000) { $r += "vram used $mem MiB" }
  return ,$r
}
function Take($tag) {
  $waited = 0
  while ($true) {
    $b = Busy
    if ($b.Count -eq 0) {
      try {
        if (Test-Path $lock) { Remove-Item $lock -Force }   # stale (dead pid) lock only: Busy() reported nothing
        $fs = [System.IO.File]::Open($lock, 'CreateNew', 'Write')
        $txt = (@{ owner = "tts:zhumian:b-geomagnetic-reversal:$tag"; pid = $PID; started = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') } | ConvertTo-Json -Compress)
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($txt); $fs.Write($bytes, 0, $bytes.Length); $fs.Close()
        Log "gpu.lock acquired for $tag (waited ${waited}s) $txt"; return
      } catch { Log "lock race: $($_.Exception.Message)" }
    } elseif ($waited % 300 -eq 0) { Log "WAIT ($tag): $($b -join ' | ')" }
    Start-Sleep 30; $waited += 30
  }
}
function Release($tag) {
  try { $l = Get-Content $lock -Raw | ConvertFrom-Json; if ($l.pid -eq $PID) { Remove-Item $lock -Force; Log "gpu.lock released ($tag)" } else { Log "lock not ours at release ($tag): $($l.owner)" } } catch { Log "release error ($tag): $($_.Exception.Message)" }
}
Set-Location E:\program\1project\video\shared\runtime\engines\tts\voxcpm
Log "=== queue start pid $PID batches=$Batches"
$first = $true
foreach ($bt in $Batches.Split(';')) {
  $tag, $jl = $bt.Split('=', 2)
  if (-not $first) { Start-Sleep 90 }; $first = $false
  Take $tag
  try {
    foreach ($j in $jl.Split('+')) {
      $jp = "$B\jobs\$j"; $lg = "$B\logs\tts-" + [IO.Path]::GetFileNameWithoutExtension($j) + ".log"
      Log "run $j"
      & { "=== START $(Get-Date) jobs=$jp"; .venv\Scripts\python.exe gen_shots.py $jp 2>&1; "=== END $(Get-Date) exit=$LASTEXITCODE" } *>> $lg
      Log "done $j exit=$LASTEXITCODE"
    }
  } finally { Release $tag }
}
Log "=== queue end"
