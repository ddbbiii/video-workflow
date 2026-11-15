param(
  [string]$Groups = "g02,g03,g04,g05,g06,g07,g08,g09,g10,g11,g12,g13,g14,g15,g16,g17,g18,g19,g20,g21,g22,g23,g24",
  [string]$BatchDir = ""
)
$ErrorActionPreference = "Continue"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$ep = Resolve-Path (Join-Path $here "..\..\..")
$spec = Join-Path $here "..\shots\groups.json"
$logDir = Join-Path $ep "runs\20261112-cas-b01\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
foreach ($g in $Groups.Split(",")) {
  $g = $g.Trim()
  if (-not $g) { continue }
  $log = Join-Path $logDir "img-$g.log"
  Write-Output "[start] $g"
  & python (Join-Path $here "02_gen_shots.py") $spec $g *> $log
  $code = $LASTEXITCODE
  Write-Output "[done]  $g exit=$code"
}
Write-Output "[all] finished"
