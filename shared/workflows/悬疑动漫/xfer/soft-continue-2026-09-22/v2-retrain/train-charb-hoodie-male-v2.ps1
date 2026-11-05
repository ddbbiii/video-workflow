# train-charb-hoodie-male-v2.ps1 — FRESH male hoodie LoRA (stronger identity vs Chengwu)
# soft expand user-approved — do NOT require hard-masc seed; T05/T06 VOID
# Do NOT start until expand produced >=20 PNGs and 01-seed-masc passed eye-check.
# Do NOT run dual-frame until solo smoke passes.
$ErrorActionPreference = 'Continue'
$trainPy = 'E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe'
$SdScriptsDir = 'E:\program\1project\video\shared\project-tools\lora\sd-scripts'
$ProjectRoot = 'E:\program\1project\video\shared\project-tools\lora\charb-hoodie-male-v2'
$TrainDataDir = Join-Path $ProjectRoot 'dataset\img'
$ImgFolder = Join-Path $TrainDataDir '10_charb_hoodie_male'
$OutputDir = Join-Path $ProjectRoot 'output'
$BaseCkpt = 'E:\program\1project\video\shared\runtime\comfy\models\models\checkpoints\animagine-xl-4.0-opt.safetensors'
$LogFile = Join-Path $ProjectRoot 'train.log'
$LoraDestDir = 'E:\program\1project\video\shared\runtime\comfy\models\models\loras'
$OutputName = 'charb-hoodie-male-sdxl-v2'
$WrapperSrcCandidates = @(
  (Join-Path $SdScriptsDir 'run_sdxl_train.py'),
  'E:\program\1project\video\xfer\run_sdxl_train.py',
  'E:\program\1project\video\shared\project-tools\lora\jiaoli-home-v1\run_sdxl_train.py'
)
$WrapperDst = Join-Path $SdScriptsDir 'run_sdxl_train.py'
$TokCache = 'E:\program\1project\video\shared\project-tools\lora\chengwu-v1\tokenizer-cache'

New-Item -ItemType Directory -Force -Path $ProjectRoot, $OutputDir, $LoraDestDir, (Join-Path $ProjectRoot 'dataset'), (Join-Path $ProjectRoot 'logs') | Out-Null

$wrapperOk = $false
foreach ($cand in $WrapperSrcCandidates) {
  if (Test-Path $cand) {
    if ($cand -ne $WrapperDst) { Copy-Item -Force $cand $WrapperDst }
    $wrapperOk = $true
    break
  }
}
if (-not $wrapperOk) { Write-Error "Missing run_sdxl_train.py"; exit 2 }
if (-not (Test-Path $trainPy)) { Write-Error "Missing python: $trainPy"; exit 2 }
if (-not (Test-Path $BaseCkpt)) { Write-Error "Missing base ckpt: $BaseCkpt"; exit 2 }
if (-not (Test-Path $TokCache)) { Write-Error "Missing tokenizer cache: $TokCache"; exit 2 }

$png = @(Get-ChildItem $ImgFolder -Filter *.png -ErrorAction SilentlyContinue).Count
$txt = @(Get-ChildItem $ImgFolder -Filter *.txt -ErrorAction SilentlyContinue).Count
Write-Host "Dataset png=$png txt=$txt folder=$ImgFolder"

# Gate: need >=20 PNGs. Soft expand (user-approved 2026-09-23) is valid train seed; hard redesign VOID.
if ($png -lt 20) {
  Write-Error "BLOCKED: need >=20 training PNGs (have $png). Run expand_hoodie_male_v2_masc.py + eye-check first."
  exit 3
}

# Caption hygiene gate
$bad = Select-String -Path (Join-Path $ImgFolder '*.txt') -Pattern '1girl|chengwu|bob cut|grey-blue|choker|teal scoop|pretty boy|bishounen|lean neck' -SimpleMatch -ErrorAction SilentlyContinue
if ($bad) {
  Write-Error "BLOCKED: forbidden caption tokens found. Run rewrite_captions_v2.ps1"
  $bad | Select-Object -First 10 | ForEach-Object { Write-Host $_.Path ':' $_.Line }
  exit 4
}

$env:PYTHONPATH = $SdScriptsDir
$env:HF_ENDPOINT = 'https://hf-mirror.com'
$env:HUGGINGFACE_HUB_CACHE = 'E:\program\1project\video\shared\runtime\comfy\cache\hf'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:PYTHONUTF8 = '1'
$env:PYTHONUNBUFFERED = '1'
$env:PYTORCH_CUDA_ALLOC_CONF = 'expandable_segments:True'
Set-Location $SdScriptsDir

if (Test-Path $LogFile) { Remove-Item $LogFile -Force }
Add-Content $LogFile "START $(Get-Date -Format o) imgs=$png offline_tok=$TokCache output=$OutputName dim=32 fresh-v2"

$argList = @(
  $WrapperDst,
  '--pretrained_model_name_or_path', $BaseCkpt,
  '--train_data_dir', $TrainDataDir,
  '--output_dir', $OutputDir,
  '--output_name', $OutputName,
  '--tokenizer_cache_dir', $TokCache,
  '--network_module', 'networks.lora',
  '--network_dim', '32',
  '--network_alpha', '16',
  '--resolution', '1024,1024',
  '--train_batch_size', '1',
  '--max_train_epochs', '20',
  '--save_every_n_epochs', '4',
  '--learning_rate', '1e-4',
  '--unet_lr', '1e-4',
  '--text_encoder_lr', '5e-5',
  '--lr_scheduler', 'cosine',
  '--lr_warmup_steps', '40',
  '--optimizer_type', 'AdamW8bit',
  '--mixed_precision', 'bf16',
  '--lowram',
  '--save_precision', 'bf16',
  '--caption_extension', '.txt',
  '--shuffle_caption',
  '--keep_tokens', '1',
  '--cache_latents',
  '--cache_latents_to_disk',
  '--skip_cache_check',
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
