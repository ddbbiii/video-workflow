$ErrorActionPreference = 'Continue'
Write-Output "=== NOW ==="
Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Write-Output "=== PID FILE ==="
$pidFile = 'E:\program\1project\video\xfer\soft-continue-2026-09-22\v2-retrain\logs\train-soft.pid'
if (Test-Path $pidFile) {
  $pidText = (Get-Content $pidFile -Raw).Trim()
  Write-Output "pidfile=$pidText"
  $p = Get-Process -Id ([int]$pidText) -ErrorAction SilentlyContinue
  if ($p) { Write-Output "PID_ALIVE name=$($p.ProcessName) cpu=$($p.CPU)" } else { Write-Output "PID_DEAD" }
} else { Write-Output "NO_PIDFILE" }
Write-Output "=== PYTHON CMDS ==="
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | ForEach-Object {
  Write-Output ("PID=" + $_.ProcessId)
  Write-Output ("CMD=" + $_.CommandLine)
  Write-Output "---"
}
Write-Output "=== STDERR TAIL ==="
$se = 'E:\program\1project\video\shared\project-tools\lora\charb-hoodie-male-v2\train-stderr.log'
if (Test-Path $se) {
  Get-Item $se | Format-List FullName,Length,LastWriteTime
  Get-Content $se -Tail 60
}
Write-Output "=== STDOUT ==="
$so = 'E:\program\1project\video\shared\project-tools\lora\charb-hoodie-male-v2\train-stdout.log'
if (Test-Path $so) {
  Get-Item $so | Format-List FullName,Length,LastWriteTime
  Get-Content $so -Tail 40
}
Write-Output "=== OUTER LOG ==="
$outer = 'E:\program\1project\video\xfer\soft-continue-2026-09-22\v2-retrain\logs\train-soft-outer-20260923-164357.log'
if (Test-Path $outer) {
  Get-Item $outer | Format-List Length,LastWriteTime
  Get-Content $outer -Tail 40
}
Write-Output "=== TRAIN SCRIPT MAX EPOCH HINT ==="
$script = 'E:\program\1project\video\xfer\soft-continue-2026-09-22\v2-retrain\logs\run-train-v2-soft.ps1'
if (Test-Path $script) {
  Select-String -Path $script -Pattern 'max_train|epoch|save_every|output_name|num_train' | ForEach-Object { $_.Line }
}
