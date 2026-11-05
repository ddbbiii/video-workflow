$ErrorActionPreference = 'Continue'
$ProjectRoot = 'E:\program\1project\video\shared\project-tools\lora\charb-hoodie-male-v2'
$DeskLogs = 'E:\program\1project\video\xfer\soft-continue-2026-09-22\v2-retrain\logs'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$outerLog = Join-Path $DeskLogs ("train-soft-outer-$stamp.log")
$pidFile = Join-Path $DeskLogs 'train-soft.pid'
$exitFile = Join-Path $DeskLogs 'train-soft.exit'
$env:PYTORCH_CUDA_ALLOC_CONF = 'expandable_segments:True'
"START $(Get-Date -Format o) soft-approved soft-21 dim32/a16 no-lowram" | Tee-Object -FilePath $outerLog
Add-Type -Namespace Win32 -Name Native -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);' -ErrorAction SilentlyContinue
try { [void][Win32.Native]::SetThreadExecutionState([uint32]0x80000003) } catch {}
$self = $PID
$self | Set-Content $pidFile
"WRAPPER_PID=$self" | Tee-Object -FilePath $outerLog -Append
try {
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ProjectRoot 'train-charb-hoodie-male-v2.ps1') *>&1 | Tee-Object -FilePath $outerLog -Append
  $code = $LASTEXITCODE
} catch {
  "EXCEPTION: $_" | Tee-Object -FilePath $outerLog -Append
  $code = 99
}
"EXIT_CODE=$code TIME=$(Get-Date -Format o)" | Tee-Object -FilePath $outerLog -Append
$code | Set-Content $exitFile
Copy-Item (Join-Path $ProjectRoot 'train.log') (Join-Path $DeskLogs 'train.log') -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $ProjectRoot 'train-stdout.log') (Join-Path $DeskLogs 'train-stdout.log') -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $ProjectRoot 'train-stderr.log') (Join-Path $DeskLogs 'train-stderr.log') -Force -ErrorAction SilentlyContinue
try { [void][Win32.Native]::SetThreadExecutionState([uint32]0x80000000) } catch {}
exit $code