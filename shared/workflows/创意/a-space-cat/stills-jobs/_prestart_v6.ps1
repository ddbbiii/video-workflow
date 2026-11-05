$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName System.Drawing
$ffDir = 'E:\program\1project\video\projects\创意\episodes\a-space-cat\image\firstframes'
$sample = @(Get-ChildItem $ffDir -Filter 'shot*.png' | Select-Object -First 3)
foreach ($f in $sample) {
  $img = [System.Drawing.Image]::FromFile($f.FullName)
  Write-Host ("{0}: {1}x{2}" -f $f.Name, $img.Width, $img.Height)
  $img.Dispose()
}

Write-Host '=== run_stills.ps1 head ==='
Get-Content 'E:\program\1project\video\shared\runtime\engines\stills-runtime\scripts\run_stills.ps1' -TotalCount 80

Write-Host '=== log dir ==='
if (-not (Test-Path 'E:\program\1project\video\shared\runtime\engines\stills-runtime\logs')) { New-Item -ItemType Directory -Path 'E:\program\1project\video\shared\runtime\engines\stills-runtime\logs' | Out-Null }
Get-ChildItem 'E:\program\1project\video\shared\runtime\engines\stills-runtime\logs' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 5 Name, Length, LastWriteTime
