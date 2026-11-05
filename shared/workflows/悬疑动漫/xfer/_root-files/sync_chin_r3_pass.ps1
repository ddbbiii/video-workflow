$ErrorActionPreference = "Stop"
$xfer = "E:\program\1project\video\xfer\keyframes-2026-09-29\chengwu-hoodie-male-chin-r3"
$e = "E:\program\1project\video\shared\work\scratch\legacy-numbered\chengwu-hoodie-male-v1-chin-r3"
$passX = Join-Path $xfer "PASS"
$passE = Join-Path $e "PASS"
New-Item -ItemType Directory -Force -Path $passX | Out-Null
New-Item -ItemType Directory -Force -Path $passE | Out-Null
$names = @("H1-living-night.png","H4-window-day.png","H5-doorway.png","R2-H3-sofa.png","R2-H6-living-night.png","R2-H7-window-close.png")
foreach ($n in $names) {
  Copy-Item -Force (Join-Path $xfer $n) (Join-Path $passX $n)
  Copy-Item -Force (Join-Path $e $n) (Join-Path $passE $n)
}
Copy-Item -Force (Join-Path $xfer "PASS-REPORT.json") (Join-Path $e "PASS-REPORT.json")
# also copy script already there
Write-Output "---PASS XFER---"
Get-ChildItem $passX | Select-Object Name,Length
Write-Output "---PASS E---"
Get-ChildItem $passE | Select-Object Name,Length
Write-Output ("REPORT_E=" + (Test-Path (Join-Path $e "PASS-REPORT.json")))
Write-Output ("REPORT_X=" + (Test-Path (Join-Path $xfer "PASS-REPORT.json")))
Write-Output ("SCRIPT=" + (Test-Path "E:\program\1project\video\shared\work\scratch\legacy-numbered\smoke_chengwu_hoodie_male_v1_chin_r3.py"))
