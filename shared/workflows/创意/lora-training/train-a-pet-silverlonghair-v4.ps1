# train-a-pet-silverlonghair-v4.ps1 — character LoRA v4 (webtoon-all-v1 approved 5 cels; mirror v3 recipe)
$ErrorActionPreference = 'Continue'
$trainPy = 'E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe'
$SdScriptsDir = 'E:\program\1project\video\shared\project-tools\lora\sd-scripts'
$ProjectRoot = 'E:\program\1project\video\shared\project-tools\lora\a-pet-silverlonghair-v4'
$TrainDataDir = Join-Path $ProjectRoot 'dataset\img'
$ImgFolder = Join-Path $TrainDataDir '27_sks_silverlonghair'
$OutputDir = Join-Path $ProjectRoot 'output'
$BaseCkpt = 'E:\program\1project\video\shared\runtime\comfy\models\models\checkpoints\animagine-xl-4.0-opt.safetensors'
$LogFile = Join-Path $ProjectRoot 'train.log'
$LoraDestDir = 'E:\program\1project\video\shared\runtime\comfy\models\models\loras'
$OutputName = 'a-pet-silverlonghair-sdxl-v4'
$WrapperDst = Join-Path $SdScriptsDir 'run_sdxl_train.py'
$TokCache = 'E:\program\1project\video\shared\project-tools\lora\chengwu-v1\tokenizer-cache'

New-Item -ItemType Directory -Force -Path $ProjectRoot, $OutputDir, $LoraDestDir, (Join-Path $ProjectRoot 'logs') | Out-Null

if (-not (Test-Path $WrapperDst)) { Write-Error "Missing run_sdxl_train.py"; exit 2 }
if (-not (Test-Path $trainPy)) { Write-Error "Missing python: $trainPy"; exit 2 }
if (-not (Test-Path $BaseCkpt)) { Write-Error "Missing base ckpt: $BaseCkpt"; exit 2 }
if (-not (Test-Path $TokCache)) { Write-Error "Missing tokenizer cache: $TokCache"; exit 2 }

$png = @(Get-ChildItem $ImgFolder -Filter *.png -ErrorAction SilentlyContinue).Count
$txt = @(Get-ChildItem $ImgFolder -Filter *.txt -ErrorAction SilentlyContinue).Count
Write-Host "Dataset png=$png txt=$txt folder=$ImgFolder"
if ($png -lt 5) { Write-Error "BLOCKED: need >=5 training PNGs (have $png)"; exit 3 }
if ($png -ne $txt) { Write-Error "BLOCKED: png/txt mismatch $png vs $txt"; exit 4 }

$missingTrig = @()
Get-ChildItem $ImgFolder -Filter *.txt | ForEach-Object {
  $c = Get-Content $_.FullName -Raw
  if ($c -notmatch 'sks_silverlonghair') { $missingTrig += $_.Name }
}
if ($missingTrig.Count -gt 0) {
  Write-Error "BLOCKED: missing trigger in $($missingTrig -join ',')"
  exit 5
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

# 5 imgs * 27 repeats * 12 epochs ~= 1620 steps; dim=16 alpha=8; UNet+TE; webtoon-all-v1 approved set
if (Test-Path $LogFile) { Remove-Item $LogFile -Force }
Add-Content $LogFile "START $(Get-Date -Format o) imgs=$png repeats=27 epochs=12 dim=16 alpha=8 te_lr=5e-5 ~1620steps output=$OutputName dataset=webtoon-all-v1-approved-5"

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
  '--max_train_epochs', '12',
  '--save_every_n_epochs', '3',
  '--learning_rate', '1e-4',
  '--unet_lr', '1e-4',
  '--text_encoder_lr', '5e-5',
  '--lr_scheduler', 'cosine',
  '--lr_warmup_steps', '50',
  '--optimizer_type', 'AdamW8bit',
  '--mixed_precision', 'bf16',
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
}
$latest = Get-ChildItem $OutputDir -Filter "$OutputName*.safetensors" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1
if ($latest) {
  Copy-Item $latest.FullName (Join-Path $LoraDestDir "$OutputName.safetensors") -Force
  Add-Content $LogFile "COPIED_LATEST $($latest.Name) -> $OutputName.safetensors"
}

Write-Host "EXIT_CODE=$code"
exit $code
