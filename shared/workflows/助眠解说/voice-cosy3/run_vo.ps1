param(
  [Parameter(Mandatory=$true)][string]$Episode,
  [Parameter(Mandatory=$true)][string]$RunId,
  [string]$Sections = "",
  [string]$Tag = "",
  [int]$MaxUnits = 0,
  [switch]$SkipAssemble
)

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Resolve-Path (Join-Path $Here "..\..\..")
$Profile = Join-Path $Root "runtime\engines\tts\voice-assets\b2-warm-male-cosy3\profile.json"
$VenvPy = Join-Path $Root "runtime\engines\tts\cosyvoice3\.venv\Scripts\python.exe"

if (-not (Test-Path $VenvPy)) { throw "CosyVoice venv not found: $VenvPy" }
if (-not (Test-Path $Profile)) { throw "voice profile not found: $Profile" }

Write-Host "[1/3] generate units (CosyVoice3, speed=0.90)" -ForegroundColor Cyan
$genArgs = @((Join-Path $Here "gen_units.py"), "--episode", $Episode, "--profile", $Profile, "--sections", $Sections, "--tag", $Tag)
if ($MaxUnits -gt 0) { $genArgs += @("--max-units", "$MaxUnits") }
& $VenvPy @genArgs
if ($LASTEXITCODE -ne 0) { throw "gen_units failed: $LASTEXITCODE" }

Write-Host "[2/3] trim + fade + 48 kHz" -ForegroundColor Cyan
& python (Join-Path $Here "post_process.py") --episode $Episode --profile $Profile --tag $Tag
if ($LASTEXITCODE -ne 0) { throw "post_process failed: $LASTEXITCODE" }

if ($SkipAssemble) {
  Write-Host "[3/3] assemble skipped" -ForegroundColor Yellow
  exit 0
}

Write-Host "[3/3] assemble chapters + timeline" -ForegroundColor Cyan
$asmArgs = @((Join-Path $Here "assemble.py"), "--episode", $Episode, "--run-id", $RunId, "--profile", $Profile, "--tag", $Tag)
if ($Sections) { $asmArgs += @("--sections", $Sections) }
& python @asmArgs
if ($LASTEXITCODE -ne 0) { throw "assemble failed: $LASTEXITCODE" }

Write-Host "done: $Episode\runs\$RunId\timeline.json" -ForegroundColor Green
