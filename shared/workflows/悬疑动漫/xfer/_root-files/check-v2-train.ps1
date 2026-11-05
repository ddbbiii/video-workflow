Continue='Continue'
Write-Output '=== TRAIN.LOG ==='
='E:\program\1project\video\shared\project-tools\lora\charb-hoodie-male-v2\train.log'
if (Test-Path ) {
  Get-Item  | Select-Object FullName,Length,LastWriteTime | Format-List
  Get-Content  -Tail 60
} else { Write-Output 'MISSING train.log' }
Write-Output '=== DESKTOP LOGS ==='
='E:\program\1project\video\xfer\soft-continue-2026-09-22\v2-retrain\logs'
if (Test-Path ) {
  Get-ChildItem  -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 20 FullName,Length,LastWriteTime | Format-Table -AutoSize
} else { Write-Output 'MISSING desktop logs dir' }
Write-Output '=== PROJECT TREE ==='
='E:\program\1project\video\shared\project-tools\lora\charb-hoodie-male-v2'
if (Test-Path ) {
  Get-ChildItem  -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 40 FullName,Length,LastWriteTime | Format-Table -AutoSize
} else { Write-Output 'MISSING project root' }
Write-Output '=== LORAS MATCH ==='
='E:\program\1project\video\shared\runtime\comfy\models\models\loras'
if (Test-Path ) {
  Get-ChildItem  -File | Where-Object { .Name -like '*hoodie*' -or .Name -like '*charb*' } | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize
} else { Write-Output 'MISSING loras dir' }
Write-Output '=== TRAIN PROCS ==='
Get-CimInstance Win32_Process -Filter " Name=python.exe OR Name=pythonw.exe\ -ErrorAction SilentlyContinue |
 Where-Object { .CommandLine -like '*hoodie*' -or .CommandLine -like '*train_network*' -or .CommandLine -like '*sd-scripts*' -or .CommandLine -like '*charb*' -or .CommandLine -like '*accelerate*' } |
 ForEach-Object {
 =.CommandLine; if ( -ne -and .Length -gt 260) { =.Substring(0,260) }
 [PSCustomObject]@{PID=.ProcessId; Created=.CreationDate; Cmd=}
 } | Format-List
Write-Output '=== DONE ==='
