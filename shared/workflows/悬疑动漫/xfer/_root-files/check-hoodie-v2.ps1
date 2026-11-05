Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Write-Host '=== PROCESSES ==='
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'hoodie-male-v2|charb-hoodie-male-v2|train_network' } | ForEach-Object {
  $cmd = if ($_.CommandLine.Length -gt 180) { $_.CommandLine.Substring(0,180) } else { $_.CommandLine }
  Write-Host ("{0} | {1} | {2}" -f $_.ProcessId, $_.Name, $cmd)
}
Write-Host '=== OUTPUT ==='
$out = 'E:\program\1project\video\shared\project-tools\lora\charb-hoodie-male-v2\output'
if (Test-Path $out) {
  Get-ChildItem $out | Sort-Object LastWriteTime -Descending | Select-Object -First 20 | ForEach-Object {
    Write-Host ("{0} | {1} | {2}" -f $_.Name, $_.Length, $_.LastWriteTime)
  }
} else { Write-Host 'output MISSING' }
Write-Host '=== LORAS MATCH ==='
$loras = 'E:\program\1project\video\shared\runtime\comfy\models\models\loras'
if (Test-Path $loras) {
  Get-ChildItem $loras -Filter '*hoodie*' -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host ("{0} | {1} | {2}" -f $_.Name, $_.Length, $_.LastWriteTime)
  }
} else { Write-Host 'loras MISSING' }
Write-Host '=== TRAIN.LOG ==='
$log = 'E:\program\1project\video\shared\project-tools\lora\charb-hoodie-male-v2\train.log'
if (Test-Path $log) {
  $i = Get-Item $log
  Write-Host ("size={0} mtime={1}" -f $i.Length, $i.LastWriteTime)
  Get-Content $log -Tail 50
} else { Write-Host 'train.log MISSING' }
Write-Host '=== DESKTOP LOGS DIR ==='
$dlog = 'E:\program\1project\video\xfer\soft-continue-2026-09-22\v2-retrain\logs'
if (Test-Path $dlog) {
  Get-ChildItem $dlog | Sort-Object LastWriteTime -Descending | Select-Object -First 15 | ForEach-Object {
    Write-Host ("{0} | {1} | {2}" -f $_.Name, $_.Length, $_.LastWriteTime)
  }
} else { Write-Host 'desktop logs MISSING' }
Write-Host '=== V2 DIR LIST ==='
$v2 = 'E:\program\1project\video\shared\project-tools\lora\charb-hoodie-male-v2'
if (Test-Path $v2) {
  Get-ChildItem $v2 -Recurse -Depth 2 -ErrorAction SilentlyContinue | Select-Object -First 40 | ForEach-Object {
    Write-Host ("{0} | {1}" -f $_.FullName, $_.LastWriteTime)
  }
} else { Write-Host 'v2 dir MISSING' }
