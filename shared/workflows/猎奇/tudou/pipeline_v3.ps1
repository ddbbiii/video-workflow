# lieqi tudou v3 pipeline (no image API): voice (seed 42) -> wait frame_map_v3 ready flag -> i2v (LTX) -> compose.
$base='E:\program\1project\video\projects\猎奇\episodes\tudou'; $log="E:\program\1project\video\projects\猎奇\episodes\tudou\logs\pipeline_v3.log"
$PY='E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe'
function L($m){ "[$(Get-Date -Format 'MM-dd HH:mm:ss')] $m" | Out-File -FilePath $log -Append -Encoding utf8 }
L "=== pipeline v3 start pid $PID"
$wavs = @(Get-ChildItem "E:\program\1project\video\projects\猎奇\episodes\tudou\audio\vo_seed42_v2\s*.wav" -ErrorAction SilentlyContinue).Count
if ($wavs -lt 34) {
  L 'step1 voice: start'
  & powershell -NoProfile -ExecutionPolicy Bypass -File "E:\program\1project\video\shared\workflows\猎奇\tudou\voice\run_voice_v3.ps1"
  $wavs = @(Get-ChildItem "E:\program\1project\video\projects\猎奇\episodes\tudou\audio\vo_seed42_v2\s*.wav" -ErrorAction SilentlyContinue).Count
  L "step1 voice: done, wavs=$wavs exit=$(Get-Content "E:\program\1project\video\projects\猎奇\episodes\tudou\logs\voice\seed42_v2.exit" -ErrorAction SilentlyContinue)"
  if ($wavs -lt 34) { L 'STOP: voice incomplete'; exit 1 }
}
while (-not (Test-Path "E:\program\1project\video\projects\猎奇\episodes\tudou\image\plot_grids_v2\frame_map_v3_ready.flag")) { L 'waiting for frame_map_v3_ready.flag'; Start-Sleep 120 }
$clips = @(Get-ChildItem "E:\program\1project\video\projects\猎奇\episodes\tudou\video\clips\s*.mp4" -ErrorAction SilentlyContinue).Count
if ($clips -lt 34) {
  L 'step2 i2v: start'
  & $PY -u "E:\program\1project\video\shared\workflows\猎奇\tudou\i2v\run_lieqi_i2v_v3.py" 2>&1 | ForEach-Object { "$_" } | Out-File -FilePath "E:\program\1project\video\projects\猎奇\episodes\tudou\logs\i2v_v3\v3_stdout.log" -Append -Encoding utf8
  $clips = @(Get-ChildItem "E:\program\1project\video\projects\猎奇\episodes\tudou\video\clips\s*.mp4" -ErrorAction SilentlyContinue).Count
  L "step2 i2v: done, clips=$clips"
  if ($clips -lt 34) { L 'STOP: i2v incomplete'; exit 2 }
}
L 'step3 compose: start'
& $PY -u "E:\program\1project\video\shared\workflows\猎奇\tudou\finalize_lieqi_v3.py" 2>&1 | ForEach-Object { "$_" } | Out-File -FilePath "E:\program\1project\video\projects\猎奇\episodes\tudou\logs\finalize_v3.log" -Append -Encoding utf8
L "step3 compose: exit=$LASTEXITCODE"
L '=== pipeline v3 end'
