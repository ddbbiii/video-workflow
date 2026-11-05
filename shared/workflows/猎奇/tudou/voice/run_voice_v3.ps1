# lieqi tudou v3 voice: VoxCPM2 seed 42 for all 34 lines (jobs voice\seed42_v2_jobs.json -> voice\seed42_v2\).
# GPU queue (视频号规划 2026-10-02 01:00): wait for E:\program\1project\video\shared\work\cache\gpu.lock; take it as owner 'lieqi:voice-seed42-v2'
# (same JSON format as other lines: pid/owner/started), run, delete it right after. run_shots.ps1 would wait on our own lock,
# so this wrapper runs the same backend (shared\runtime\engines\tts\voxcpm gen_shots.py, same venv, same env vars) directly.
$base='E:\program\1project\video\projects\猎奇\episodes\tudou'; $log="E:\program\1project\video\projects\猎奇\episodes\tudou\logs\voice\seed42_v2.log"; $lock='E:\program\1project\video\shared\work\cache\gpu.lock'
$jobs="E:\program\1project\video\shared\workflows\猎奇\tudou\voice\seed42_v2_jobs.json"
function L($m){ "[$(Get-Date -Format 'MM-dd HH:mm:ss')] $m" | Out-File -FilePath $log -Append -Encoding utf8 }
function Busy {
  if (Test-Path $lock) {
    try { $l = Get-Content $lock -Raw | ConvertFrom-Json } catch { return 'lock unreadable (retry)' }
    if ($l.pid -and $l.pid -ne $PID -and (Get-Process -Id $l.pid -ErrorAction SilentlyContinue)) { return "lock $($l.owner) pid $($l.pid) since $($l.started)" }
  }
  $g = @(Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object { $_.CommandLine -match 'gen_shots\.py|run_i2v|i2v_cmp|run_lieqi_i2v|run_stills' })
  if ($g.Count) { return 'gpu python running: ' + (($g | ForEach-Object { "$($_.ProcessId)" }) -join ',') }
  return $null
}
L "=== voice v3 wrapper start pid $PID jobs=$jobs"
$n=0
while ($true) {
  $b = Busy
  if (-not $b) {
    $me = @{pid=$PID; owner='lieqi:voice-seed42-v2'; started=(Get-Date -Format 'yyyy-MM-ddTHH:mm:sszzz')} | ConvertTo-Json -Compress
    [IO.File]::WriteAllText($lock, $me, (New-Object Text.UTF8Encoding $false))
    Start-Sleep 3
    try { $chk = Get-Content $lock -Raw | ConvertFrom-Json } catch { $chk = $null }
    if ($chk -and $chk.pid -eq $PID) { L "gpu.lock acquired: $me"; break }
    L "lock race lost, waiting again"
  } elseif ($n % 5 -eq 0) { L "WAIT $b" }
  $n++; Start-Sleep 60
}
$code = -1
try {
  $env:HF_ENDPOINT = "https://hf-mirror.com"; $env:PYTHONIOENCODING = "utf-8"
  $env:MODELSCOPE_CACHE = "E:\program\1project\video\shared\runtime\engines\tts\modelscope-cache"; $env:HF_HOME = "E:\program\1project\video\shared\runtime\engines\tts\hf-cache"
  Set-Location E:\program\1project\video\shared\runtime\engines\tts\voxcpm
  L "=== START gen_shots $(Get-Date)"
  $t0 = Get-Date
  & .venv\Scripts\python.exe gen_shots.py $jobs 2>&1 | ForEach-Object { "$_" } | Out-File -FilePath $log -Append -Encoding utf8
  $code = $LASTEXITCODE
  L "=== END gen_shots exit=$code elapsed=$([int]((Get-Date)-$t0).TotalSeconds)s"
} finally {
  try { $l = Get-Content $lock -Raw | ConvertFrom-Json; if ($l.pid -eq $PID) { Remove-Item $lock -Force; L 'gpu.lock released' } } catch { L "lock release error $_" }
  "$code" | Out-File -FilePath "E:\program\1project\video\projects\猎奇\episodes\tudou\logs\voice\seed42_v2.exit" -Encoding ascii
}
