$src = "E:\program\1project\video\xfer\keyframes-2026-09-28\chengwu-hoodie-male-v1\PASS"
$dst = "E:\program\1project\video\xfer\keyframes-2026-09-29\chengwu-hoodie-male-chin-r3\_prev_pass"
New-Item -ItemType Directory -Force -Path $dst | Out-Null
$names = @("H4-window-day.png","H5-doorway.png","R2-H2-living-day.png","R2-H3-sofa.png","R2-H6-living-night.png")
foreach ($n in $names) {
  Copy-Item -Force (Join-Path $src $n) (Join-Path $dst $n)
  Write-Output ("OK " + $n + " " + (Test-Path (Join-Path $dst $n)))
}
