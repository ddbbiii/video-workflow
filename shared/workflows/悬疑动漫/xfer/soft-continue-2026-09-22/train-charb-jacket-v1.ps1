# train-charb-jacket-v1.ps1 — Char B jacket SDXL LoRA (Animagine XL 4.0)
# Mirror of jiaoli-home-v1 recipe: portable python + sd-scripts wrapper + offline tokenizer cache.
# Do NOT start while TTS audition holds GPU. Requires >=10 PNGs in 10_charb_jacket.
$ErrorActionPreference = 'Continue'
$trainPy = 'E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe'
$SdScriptsDir = 'E:\program\1project\video\shared\project-tools\lora\sd-scripts'
$ProjectRoot = 'E:\program\1project\video\shared\project-tools\lora\charb-jacket-v1'
$TrainDataDir = Join-Path $ProjectRoot 'dataset\img'
$ImgFolder = Join-Path $TrainDataDir '10_charb_jacket'
$OutputDir = Join-Path $ProjectRoot 'output'
$BaseCkpt = 'E:\program\1project\video\shared\runtime\comfy\models\models\checkpoints\animagine-xl-4.0-opt.safetensors'
$LogFile = Join-Path $ProjectRoot 'train.log'
$LoraDestDir = 'E:\program\1project\video\shared\runtime\comfy\models\models\loras'
$OutputName = 'charb-jacket-sdxl-v1'
$WrapperSrcCandidates = @(
  (Join-Path $SdScriptsDir 'run_sdxl_train.py'),
  'E:\program\1project\video\xfer\run_sdxl_train.py',
  'E:\program\1project\video\shared\project-tools\lora\jiaoli-home-v1\run_sdxl_train.py'
)
$WrapperDst = Join-Path $SdScriptsDir 'run_sdxl_train.py'
$TokCache = 'E:\program\1project\video\shared\project-tools\lora\chengwu-v1\tokenizer-cache'

New-Item -ItemType Directory -Force -Path $ProjectRoot, $OutputDir, $LoraDestDir, (Join-Path $ProjectRoot 'dataset'), (Join-Path $ProjectRoot 'logs') | Out-Null

# Ensure wrapper exists (jiaoli copies from Desktop; reuse if already in sd-scripts)
$wrapperOk = $false
foreach ($cand in $WrapperSrcCandidates) {
  if (Test-Path $cand) {
    if ($cand -ne $WrapperDst) { Copy-Item -Force $cand $WrapperDst }
    $wrapperOk = $true
    break
  }
}
if (-not $wrapperOk) {
  Write-Error "Missing run_sdxl_train.py (checked sd-scripts / Desktop xfer / jiaoli-home-v1). Abort."
  exit 2
}

if (-not (Test-Path $trainPy)) { Write-Error "Missing python: $trainPy"; exit 2 }
if (-not (Test-Path $BaseCkpt)) { Write-Error "Missing base ckpt: $BaseCkpt"; exit 2 }
if (-not (Test-Path $TokCache)) { Write-Error "Missing tokenizer cache: $TokCache"; exit 2 }
if (-not (Test-Path (Join-Path $SdScriptsDir 'sdxl_train_network.py')) -and -not (Test-Path $WrapperDst)) {
  Write-Error "sd-scripts incomplete: $SdScriptsDir"; exit 2
}

$png = @(Get-ChildItem $ImgFolder -Filter *.png -ErrorAction SilentlyContinue).Count
$txt = @(Get-ChildItem $ImgFolder -Filter *.txt -ErrorAction SilentlyContinue).Count
Write-Host "Dataset png=$png txt=$txt folder=$ImgFolder tok=$TokCache"

if ($png -lt 10) {
  Write-Error "BLOCKED: need >=10 training PNGs (have $png). Expand refs first — see EXPAND-PLAN.md. Not starting kohya."
  exit 3
}

$env:PYTHONPATH = $SdScriptsDir
$env:HF_ENDPOINT = 'https://hf-mirror.com'
$env:HUGGINGFACE_HUB_CACHE = 'E:\program\1project\video\shared\runtime\comfy\cache\hf'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:PYTHONUTF8 = '1'
$env:PYTHONUNBUFFERED = '1'
Set-Location $SdScriptsDir

if (Test-Path $LogFile) { Remove-Item $LogFile -Force }
Add-Content $LogFile "START $(Get-Date -Format o) imgs=$png offline_tok=$TokCache output=$OutputName"

$argList = @(
  $WrapperDst,
  '--pretrained_model_name_or_path', $BaseCkpt,
  '--train_data_dir', $TrainDataDir,
  '--output_dir', $OutputDir,
  '--output_name', $OutputName,
  '--tokenizer_cache_dir', $TokCache,
  '--network_module', 'networks.lora',
  '--network_dim', '16',
  '--network_alpha', '8',
  '--resolution', '1024,1024',
  '--train_batch_size', '1',
  '--max_train_epochs', '25',
  '--save_every_n_epochs', '5',
  '--learning_rate', '1e-4',
  '--unet_lr', '1e-4',
  '--text_encoder_lr', '5e-5',
  '--lr_scheduler', 'cosine',
  '--lr_warmup_steps', '40',
  '--optimizer_type', 'AdamW8bit',
  '--mixed_precision', 'bf16',
  '--save_precision', 'bf16',
  '--caption_extension', '.txt',
  '--shuffle_caption',
  '--keep_tokens', '1',
  '--cache_latents',
  '--cache_latents_to_disk',
  '--enable_bucket',
  '--min_bucket_reso', '256',
  '--max_bucket_reso', '2048',
  '--bucket_reso_steps', '64',
  '--gradient_checkpointing',
  '--sdpa',
  '--seed', '42',
  '--min_snr_gamma', '5',
  '--max_data_loader_n_workers', '0'
)

$stdoutLog = Join-Path $ProjectRoot 'train-stdout.log'
$stderrLog = Join-Path $ProjectRoot 'train-stderr.log'
$p = Start-Process -FilePath $trainPy -ArgumentList $argList -WorkingDirectory $SdScriptsDir -NoNewWindow -Wait -PassThru `
  -RedirectStandardOutput $stdoutLog `
  -RedirectStandardError $stderrLog
$code = $p.ExitCode
Get-Content $stdoutLog -ErrorAction SilentlyContinue | Add-Content $LogFile
Get-Content $stderrLog -ErrorAction SilentlyContinue | Add-Content $LogFile
Add-Content $LogFile "EXIT_CODE=$code TIME=$(Get-Date -Format o)"

Get-ChildItem $OutputDir -Filter "$OutputName*.safetensors" -ErrorAction SilentlyContinue | ForEach-Object {
  Copy-Item $_.FullName (Join-Path $LoraDestDir $_.Name) -Force
  Add-Content $LogFile "COPIED $($_.Name) -> $LoraDestDir"
  if ($_.BaseName -match '-(\d+)$') {
    $epName = "{0}-ep{1}.safetensors" -f $OutputName, $Matches[1]
    Copy-Item $_.FullName (Join-Path $LoraDestDir $epName) -Force
    Add-Content $LogFile "COPIED_EP $epName"
  }
}
$latest = Get-ChildItem $OutputDir -Filter "$OutputName*.safetensors" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1
if ($latest) {
  Copy-Item $latest.FullName (Join-Path $LoraDestDir "$OutputName.safetensors") -Force
  Add-Content $LogFile "COPIED_LATEST $($latest.Name) -> $OutputName.safetensors"
}

Write-Host "EXIT_CODE=$code"
exit $code
