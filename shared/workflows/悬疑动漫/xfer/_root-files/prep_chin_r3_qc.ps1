$src = "E:\program\1project\video\xfer\keyframes-2026-09-29\chengwu-hoodie-male-chin-r3"
$e = "E:\program\1project\video\shared\work\scratch\legacy-numbered\chengwu-hoodie-male-v1-chin-r3"
Write-Output "---XFER---"
Get-ChildItem $src | Select-Object Name,Length
Write-Output "---E---"
Get-ChildItem $e -Filter "*.png" | Select-Object Name,Length
# ensure xfer has all pngs (script should have copied)
$names = @("H1-living-night.png","H4-window-day.png","H5-doorway.png","R2-H2-living-day.png","R2-H3-sofa.png","R2-H6-living-night.png","R2-H7-window-close.png")
foreach ($n in $names) {
  $from = Join-Path $e $n
  $to = Join-Path $src $n
  if ((Test-Path $from) -and -not (Test-Path $to)) { Copy-Item $from $to }
  # also refresh
  if (Test-Path $from) { Copy-Item -Force $from $to }
}
# also copy previous PASS for chin compare refs into a side folder on xfer
$prev = "E:\program\1project\video\xfer\keyframes-2026-09-28\chengwu-hoodie-male-v1\PASS"
$cmp = "E:\program\1project\video\xfer\keyframes-2026-09-29\chengwu-hoodie-male-chin-r3\_prev_pass"
New-Item -ItemType Directory -Force -Path $cmp | Out-Null
foreach ($n in $names) {
  $p = Join-Path $prev $n
  if (Test-Path $p) { Copy-Item -Force $p (Join-Path $cmp $n) }
}
Write-Output "---CMP---"
Get-ChildItem $cmp | Select-Object Name
