# APPLY-CHARB-JACKET-PREP.ps1 — create charb-jacket-v1 project on ddbbi
# Safe: does NOT start ComfyUI, does NOT start kohya, does NOT kill processes.
$ErrorActionPreference = 'Stop'
$Stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Write-Host "=== APPLY charb-jacket-v1 prep @ $Stamp (Asia/Shanghai local) ==="

$ProjectRoot = 'E:\program\1project\video\shared\project-tools\lora\charb-jacket-v1'
$ImgDir = Join-Path $ProjectRoot 'dataset\img\10_charb_jacket'
$XferDir = 'E:\program\1project\video\xfer\charb-jacket-prep'
$SeedCandidates = @(
  'E:\program\1project\video\xfer\overnight-2026-09-21\charB\04-jacket.png',
  (Join-Path $XferDir '01-seed.png'),
  (Join-Path $PSScriptRoot 'dataset\img\10_charb_jacket\01-seed.png'),
  (Join-Path $PSScriptRoot 'xfer-seed\01-seed.png')
)

New-Item -ItemType Directory -Force -Path $ProjectRoot,
  (Join-Path $ProjectRoot 'dataset\img'),
  $ImgDir,
  (Join-Path $ProjectRoot 'output'),
  (Join-Path $ProjectRoot 'logs'),
  $XferDir | Out-Null

$seedSrc = $null
foreach ($c in $SeedCandidates) {
  if (Test-Path -LiteralPath $c) { $seedSrc = $c; break }
}
if (-not $seedSrc) {
  throw "SEED MISSING. Expected overnight 04-jacket.png or xfer 01-seed.png"
}

$seedDst = Join-Path $ImgDir '01-seed.png'
Copy-Item -Force -LiteralPath $seedSrc $seedDst
Write-Host "Seed: $seedSrc -> $seedDst"

$caption = @'
charb_jacket, 1girl, solo, young adult woman, short hair, black hair, bob cut, bangs, red hair clip, dark eyes, pale skin, black oversized jacket, open jacket, white t-shirt, upper body, three-quarter view, looking at viewer, anime style, simple grey background
'@
$captionPath = Join-Path $ImgDir '01-seed.txt'
Set-Content -LiteralPath $captionPath -Value $caption.Trim() -Encoding UTF8
Write-Host "Caption: $captionPath"

# Copy docs/scripts from same folder as this APPLY if present; else write embedded fallbacks
function Copy-Or-Write([string]$Name, [string]$DestDir, [scriptblock]$Fallback) {
  $fromApply = Join-Path $PSScriptRoot $Name
  $dest = Join-Path $DestDir $Name
  if (Test-Path -LiteralPath $fromApply) {
    Copy-Item -Force -LiteralPath $fromApply $dest
    Write-Host "Copied $Name"
  } else {
    & $Fallback $dest
    Write-Host "Wrote embedded $Name"
  }
}

# Prefer sibling files shipped with APPLY
$ship = @(
  'README.md',
  'EXPAND-PLAN.md',
  'STATUS.md',
  'train-charb-jacket-v1.ps1'
)
foreach ($f in $ship) {
  $src = Join-Path $PSScriptRoot $f
  if (Test-Path -LiteralPath $src) {
    Copy-Item -Force -LiteralPath $src (Join-Path $ProjectRoot $f)
    Copy-Item -Force -LiteralPath $src (Join-Path $XferDir $f)
  }
}

# Ensure train script exists even if sibling missing (minimal pointer)
$trainPath = Join-Path $ProjectRoot 'train-charb-jacket-v1.ps1'
if (-not (Test-Path -LiteralPath $trainPath)) {
  throw "train-charb-jacket-v1.ps1 missing next to APPLY. Re-copy full prep folder."
}

# Desktop review package
Copy-Item -Force $seedDst (Join-Path $XferDir '01-seed.png')
Copy-Item -Force $captionPath (Join-Path $XferDir '01-seed.txt')
Copy-Item -Force $seedDst (Join-Path $XferDir '04-jacket-seed-ref.png')

# Light README for xfer if missing
$xferReadme = Join-Path $XferDir 'README.md'
if (-not (Test-Path $xferReadme)) {
  Set-Content -LiteralPath $xferReadme -Encoding UTF8 -Value @"
# charb-jacket-prep (user review)

Seed for Char B jacket LoRA. Trigger: ``charb_jacket``.

Project (train when expanded): ``E:\program\1project\video\shared\project-tools\lora\charb-jacket-v1\``

**Blocked:** need ~12–20 multi-angle images before train; wait for TTS/voice audition GPU free. Do not start Comfy/kohya yet.
"@
}

# Verify prerequisites (report only)
$checks = [ordered]@{
  'project_root' = (Test-Path $ProjectRoot)
  'seed_png' = (Test-Path $seedDst)
  'seed_txt' = (Test-Path $captionPath)
  'train_ps1' = (Test-Path $trainPath)
  'readme' = (Test-Path (Join-Path $ProjectRoot 'README.md'))
  'expand_plan' = (Test-Path (Join-Path $ProjectRoot 'EXPAND-PLAN.md'))
  'status' = (Test-Path (Join-Path $ProjectRoot 'STATUS.md'))
  'xfer_dir' = (Test-Path $XferDir)
  'base_ckpt' = (Test-Path 'E:\program\1project\video\shared\runtime\comfy\models\models\checkpoints\animagine-xl-4.0-opt.safetensors')
  'sd_scripts' = (Test-Path 'E:\program\1project\video\shared\project-tools\lora\sd-scripts')
  'tok_cache' = (Test-Path 'E:\program\1project\video\shared\project-tools\lora\chengwu-v1\tokenizer-cache')
  'python' = (Test-Path 'E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe')
  'overnight_seed' = (Test-Path 'E:\program\1project\video\xfer\overnight-2026-09-21\charB\04-jacket.png')
}
$pngCount = @(Get-ChildItem $ImgDir -Filter *.png -EA SilentlyContinue).Count

Write-Host "--- checks ---"
$checks.GetEnumerator() | ForEach-Object { Write-Host ("{0}={1}" -f $_.Key, $_.Value) }
Write-Host "png_count=$pngCount (need >=10 to train; expansion still blocked)"
Write-Host "DONE. Project=$ProjectRoot"
Write-Host "Xfer=$XferDir"
Write-Host "BLOCKER: expand images + wait GPU free before train/Comfy."
