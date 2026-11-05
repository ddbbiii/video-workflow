$ErrorActionPreference = 'Continue'
Write-Host '=== launch verify ==='
Get-CimInstance Win32_Process -Filter "Name like 'python%'" | Where-Object {
  $_.CommandLine -match 'run_stills|ComfyUI'
} | ForEach-Object {
  $cmd = $_.CommandLine
  if ($cmd.Length -gt 220) { $cmd = $cmd.Substring(0,220) + '...' }
  Write-Host ("PID={0}" -f $_.ProcessId)
  Write-Host ("  {0}" -f $cmd)
}
$lock = 'E:\program\1project\video\shared\work\cache\gpu.lock'
Write-Host '=== lock after launch ==='
if (Test-Path $lock) { Get-Content $lock -Raw } else { Write-Host 'no lock yet' }
$log = 'E:\program\1project\video\shared\runtime\engines\stills-runtime\logs\stills_a-space-cat_missing31_v6.log'
$out = 'E:\program\1project\video\shared\runtime\engines\stills-runtime\logs\runner_stills_a-space-cat_missing31_v6.out.log'
$err = 'E:\program\1project\video\shared\runtime\engines\stills-runtime\logs\runner_stills_a-space-cat_missing31_v6.err.log'
foreach ($p in @($log,$out,$err)) {
  Write-Host ("--- {0} exists={1} ---" -f $p, (Test-Path $p))
  if (Test-Path $p) {
    Get-Content $p -Tail 30 -ErrorAction SilentlyContinue
  }
}
