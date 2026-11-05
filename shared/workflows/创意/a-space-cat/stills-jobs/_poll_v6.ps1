$ErrorActionPreference = 'Continue'
$log = 'E:\program\1project\video\shared\runtime\engines\stills-runtime\logs\stills_a-space-cat_missing31_v6.log'
$status = 'E:\program\1project\video\projects\创意\episodes\a-space-cat\logs\stills-jobs\_poll_status_v6.txt'
$deadline = (Get-Date).AddHours(4)
$n = 0
while ((Get-Date) -lt $deadline) {
  $n++
  $tail = ''
  $ended = $false
  if (Test-Path $log) {
    $lines = Get-Content $log -ErrorAction SilentlyContinue
    if ($lines) {
      $tail = ($lines | Select-Object -Last 8) -join "`n"
      $last = $lines[-1]
      if ($last -like '=== END*') { $ended = $true }
    }
  }
  $rawDir = 'E:\program\1project\video\shared\runtime\engines\stills-runtime\out\a-space-cat\a-space-cat_missing31_v6'
  $pngCount = 0
  if (Test-Path $rawDir) {
    $pngCount = @(Get-ChildItem $rawDir -Recurse -Filter '*.png' -ErrorAction SilentlyContinue).Count
  }
  $alive = $false
  $p = Get-CimInstance Win32_Process -Filter "ProcessId=42496" -ErrorAction SilentlyContinue
  if ($p) { $alive = $true }
  $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
  $msg = @"
[$stamp] poll#$n alive=$alive pngs=$pngCount ended=$ended
$tail
"@
  Set-Content -Path $status -Value $msg -Encoding UTF8
  if ($ended) {
    Add-Content -Path $status -Value 'POLL_DONE_END_FOUND' -Encoding UTF8
    break
  }
  if (-not $alive -and $n -gt 3) {
    # runner may have exited; check once more for END
    Start-Sleep -Seconds 5
    if (Test-Path $log) {
      $last2 = (Get-Content $log -Tail 1 -ErrorAction SilentlyContinue)
      if ($last2 -like '=== END*') {
        Add-Content -Path $status -Value 'POLL_DONE_END_FOUND' -Encoding UTF8
        break
      }
    }
    Add-Content -Path $status -Value ("POLL_DONE_RUNNER_DEAD last={0}" -f $last2) -Encoding UTF8
    break
  }
  Start-Sleep -Seconds 60
}
