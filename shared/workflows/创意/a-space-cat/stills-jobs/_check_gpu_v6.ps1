$ErrorActionPreference = 'Continue'
Write-Host '=== GPU LOCK (05-cache) ==='
$lock = 'E:\program\1project\video\shared\work\cache\gpu.lock'
if (Test-Path $lock) {
  Write-Host 'LOCK EXISTS:'
  Get-Content $lock -Raw
  Get-Item $lock | Select-Object FullName, Length, LastWriteTime | Format-List
} else {
  Write-Host 'gpu.lock absent (empty/free)'
}

Write-Host '=== Competing python processes ==='
Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object {
  $_.CommandLine -match 'shared\runtime\engines\tts|voxcpm|index-tts|gen_shots|indextts|ComfyUI|run_stills|comfy-stills'
} | ForEach-Object {
  $cmd = $_.CommandLine
  if ($cmd.Length -gt 240) { $cmd = $cmd.Substring(0,240) + '...' }
  Write-Host ("PID={0} NAME={1}" -f $_.ProcessId, $_.Name)
  Write-Host ("  CMD={0}" -f $cmd)
}

Write-Host '=== nvidia-smi compute apps ==='
& nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv
Write-Host '=== nvidia-smi util ==='
& nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv

Write-Host '=== Existing firstframes ==='
$ffDir = 'E:\program\1project\video\projects\创意\episodes\a-space-cat\image\firstframes'
if (Test-Path $ffDir) {
  Get-ChildItem $ffDir -Filter 'shot*.png' | Sort-Object Name | ForEach-Object {
    Write-Host ("{0}  {1} bytes  {2}" -f $_.Name, $_.Length, $_.LastWriteTime)
  }
} else {
  Write-Host "firstframes dir missing: $ffDir"
}

Write-Host '=== Jobs count ==='
$j = Get-Content 'E:\program\1project\video\shared\workflows\创意\a-space-cat\stills-jobs\missing31_v6.json' -Raw | ConvertFrom-Json
Write-Host ("tag={0} jobs={1} raw_dir={2} pull_zip={3}" -f $j.tag, $j.jobs.Count, $j.raw_dir, $j.pull_zip)
Write-Host ("sample size w={0} h={1}" -f $j.jobs[0].w, $j.jobs[0].h)
