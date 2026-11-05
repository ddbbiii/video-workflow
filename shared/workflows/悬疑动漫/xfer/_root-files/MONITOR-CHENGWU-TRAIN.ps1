# Quick status for chengwu LoRA train on ddbbi
$ErrorActionPreference = 'Continue'
$ProjectRoot = 'E:\program\1project\video\shared\project-tools\lora\chengwu-v1'
$Log = Join-Path $ProjectRoot 'train.log'
$PidFile = Join-Path $ProjectRoot 'train.pid'
$Out = Join-Path $ProjectRoot 'output'
Write-Host "=== chengwu train monitor $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==="
if (Test-Path $PidFile) {
  $trainPid = [int](Get-Content $PidFile | Select-Object -First 1)
  $p = Get-Process -Id $trainPid -EA SilentlyContinue
  Write-Host "PID file: $trainPid alive=$([bool]$p)"
} else { Write-Host 'No train.pid' }
Get-Process python*,powershell* -EA SilentlyContinue | Where-Object {
  try { (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)").CommandLine -match 'sdxl_train_network|train-chengwu' } catch { $false }
} | ForEach-Object { Write-Host "TRAIN PROC: PID=$($_.Id) CPU=$($_.CPU)" }
if (Test-Path $Log) {
  Write-Host '--- train.log tail ---'
  Get-Content $Log -Tail 40
} else { Write-Host 'no train.log yet' }
Write-Host '--- output safetensors ---'
Get-ChildItem $Out -Filter '*.safetensors' -EA SilentlyContinue | Format-Table Name, Length, LastWriteTime -AutoSize
Write-Host '--- Comfy loras copies ---'
Get-ChildItem 'E:\program\1project\video\shared\runtime\comfy\models\models\loras\chengwu*' -EA SilentlyContinue | Format-Table Name, Length, LastWriteTime -AutoSize
try {
  & nvidia-smi --query-gpu=memory.used,memory.free,utilization.gpu --format=csv
} catch {}
