$ErrorActionPreference = 'Continue'
$trainPy = 'E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe'
$SdScriptsDir = 'E:\program\1project\video\shared\project-tools\lora\sd-scripts'
$ProjectRoot = 'E:\program\1project\video\shared\project-tools\lora\charb-jacket-v1b'
$TrainDataDir = Join-Path $ProjectRoot 'dataset\img'
$ImgFolder = Join-Path $TrainDataDir '10_charb_jacket'
$OutputDir = Join-Path $ProjectRoot 'output'
$BaseCkpt = 'E:\program\1project\video\shared\runtime\comfy\models\models\checkpoints\animagine-xl-4.0-opt.safetensors'
$NetworkWeights = 'E:\program\1project\video\shared\runtime\comfy\models\models\loras\charb-jacket-sdxl-v1.safetensors'
$TokCache = 'E:\program\1project\video\shared\project-tools\lora\chengwu-v1\tokenizer-cache'
$LogFile = Join-Path $ProjectRoot 'train.log'
$LoraDestDir = 'E:\program\1project\video\shared\runtime\comfy\models\models\loras'
$OutputName = 'charb-jacket-sdxl-v1b'
$WrapperDst = Join-Path $SdScriptsDir 'run_sdxl_train.py'
$WrapperSrcCandidates = @($WrapperDst, 'E:\program\1project\video\xfer\run_sdxl_train.py', 'E:\program\1project\video\shared\project-tools\lora\jiaoli-home-v1\run_sdxl_train.py')
New-Item -ItemType Directory -Force -Path $ProjectRoot,$OutputDir,$LoraDestDir,(Join-Path $ProjectRoot 'dataset'),(Join-Path $ProjectRoot 'logs') | Out-Null
$wrapperOk = $false
foreach ($cand in $WrapperSrcCandidates) {
  if (Test-Path $cand) {
    if ($cand -ne $WrapperDst) { Copy-Item -Force $cand $WrapperDst }
    $wrapperOk = $true
    break
  }
}
if (-not $wrapperOk) { Write-Error 'Missing run_sdxl_train.py'; exit 2 }
if (-not (Test-Path $trainPy)) { Write-Error "Missing python"; exit 2 }
if (-not (Test-Path $BaseCkpt)) { Write-Error 'Missing ckpt'; exit 2 }
if (-not (Test-Path $TokCache)) { Write-Error 'Missing tok'; exit 2 }
if (-not (Test-Path $NetworkWeights)) { Write-Error "Missing $NetworkWeights"; exit 2 }
$png = @(Get-ChildItem $ImgFolder -Filter *.png -EA SilentlyContinue).Count
Write-Host "soft-continue png=$png from=$NetworkWeights out=$OutputName"
if ($png -lt 10) { Write-Error "need >=10 png have $png"; exit 3 }
Get-ChildItem $ImgFolder -Filter *.npz -EA SilentlyContinue | Remove-Item -Force
$env:PYTHONPATH = $SdScriptsDir
$env:HF_ENDPOINT = 'https://hf-mirror.com'
$env:HUGGINGFACE_HUB_CACHE = 'E:\program\1project\video\shared\runtime\comfy\cache\hf'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:PYTHONUTF8 = '1'
$env:PYTHONUNBUFFERED = '1'
Set-Location $SdScriptsDir
if (Test-Path $LogFile) { Remove-Item $LogFile -Force }
Add-Content $LogFile "START $(Get-Date -Format o) soft-continue from=$NetworkWeights imgs=$png"
$argList = @(
  $WrapperDst,
  '--pretrained_model_name_or_path', $BaseCkpt,
  '--train_data_dir', $TrainDataDir,
  '--output_dir', $OutputDir,
  '--output_name', $OutputName,
  '--network_weights', $NetworkWeights,
  '--tokenizer_cache_dir', $TokCache,
  '--network_module', 'networks.lora',
  '--network_dim', '16',
  '--network_alpha', '8',
  '--resolution', '1024,1024',
  '--train_batch_size', '1',
  '--max_train_epochs', '10',
  '--save_every_n_epochs', '2',
  '--learning_rate', '6e-5',
  '--unet_lr', '6e-5',
  '--text_encoder_lr', '3e-5',
  '--lr_scheduler', 'cosine',
  '--lr_warmup_steps', '20',
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
$p = Start-Process -FilePath $trainPy -ArgumentList $argList -WorkingDirectory $SdScriptsDir -NoNewWindow -Wait -PassThru -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog
$code = $p.ExitCode
Get-Content $stdoutLog -EA SilentlyContinue | Add-Content $LogFile
Get-Content $stderrLog -EA SilentlyContinue | Add-Content $LogFile
Add-Content $LogFile "EXIT_CODE=$code TIME=$(Get-Date -Format o)"
Get-ChildItem $OutputDir -Filter "$OutputName*.safetensors" -EA SilentlyContinue | ForEach-Object {
  Copy-Item $_.FullName (Join-Path $LoraDestDir $_.Name) -Force
  Add-Content $LogFile "COPIED $($_.Name)"
}
$latest = Get-ChildItem $OutputDir -Filter "$OutputName*.safetensors" -EA SilentlyContinue | Sort-Object LastWriteTime | Select-Object -Last 1
if ($latest) {
  Copy-Item $latest.FullName (Join-Path $LoraDestDir "$OutputName.safetensors") -Force
  Add-Content $LogFile "COPIED_LATEST $($latest.Name)"
}
Write-Host "EXIT_CODE=$code"
exit $code
