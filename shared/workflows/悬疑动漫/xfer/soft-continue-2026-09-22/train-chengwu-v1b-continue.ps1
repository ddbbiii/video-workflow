$ErrorActionPreference = 'Continue'
$trainPy = 'E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe'
$SdScriptsDir = 'E:\program\1project\video\shared\project-tools\lora\sd-scripts'
$ProjectRoot = 'E:\program\1project\video\shared\project-tools\lora\chengwu-v1b'
$TrainDataDir = Join-Path $ProjectRoot 'dataset\img'
$OutputDir = Join-Path $ProjectRoot 'output'
$BaseCkpt = 'E:\program\1project\video\shared\runtime\comfy\models\models\checkpoints\animagine-xl-4.0-opt.safetensors'
$NetworkWeights = 'E:\program\1project\video\shared\runtime\comfy\models\models\loras\chengwu-sdxl-v1-000010.safetensors'
$TokCache = 'E:\program\1project\video\shared\project-tools\lora\chengwu-v1\tokenizer-cache'
$LogFile = Join-Path $ProjectRoot 'train.log'
$LoraDestDir = 'E:\program\1project\video\shared\runtime\comfy\models\models\loras'
$SrcTgz = 'E:\program\1project\video\xfer\chengwu-lora-v1b-dataset.tgz'
$WrapperSrc = 'E:\program\1project\video\xfer\run_sdxl_train.py'
$WrapperDst = Join-Path $SdScriptsDir 'run_sdxl_train.py'
$OutputName = 'chengwu-sdxl-v1b'

New-Item -ItemType Directory -Force -Path $ProjectRoot,$OutputDir,$LoraDestDir,(Join-Path $ProjectRoot 'dataset') | Out-Null
if (Test-Path $WrapperSrc) { Copy-Item -Force $WrapperSrc $WrapperDst }

$imgFolder = Join-Path $TrainDataDir '10_chengwu'
if (-not (Test-Path (Join-Path $imgFolder '15-chin-natural.png'))) {
  if (-not (Test-Path $SrcTgz)) { throw "Missing $SrcTgz" }
  tar -xzf $SrcTgz -C (Join-Path $ProjectRoot 'dataset')
}
$png = @(Get-ChildItem $imgFolder -Filter *.png -EA SilentlyContinue).Count
if (-not (Test-Path $NetworkWeights)) { throw "Missing continue weights $NetworkWeights" }
Write-Host "v1b continue imgs=$png from=$NetworkWeights"

$env:PYTHONPATH = $SdScriptsDir
$env:HF_ENDPOINT = 'https://hf-mirror.com'
$env:HUGGINGFACE_HUB_CACHE = 'E:\program\1project\video\shared\runtime\comfy\cache\hf'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:PYTHONUTF8 = '1'
Set-Location $SdScriptsDir

if (Test-Path $LogFile) { Remove-Item $LogFile -Force }
Add-Content $LogFile "START $(Get-Date -Format o) continue_from_ep10 imgs=$png"

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

$p = Start-Process -FilePath $trainPy -ArgumentList $argList -WorkingDirectory $SdScriptsDir -NoNewWindow -Wait -PassThru `
  -RedirectStandardOutput (Join-Path $ProjectRoot 'train-stdout.log') `
  -RedirectStandardError (Join-Path $ProjectRoot 'train-stderr.log')
$code = $p.ExitCode
Get-Content (Join-Path $ProjectRoot 'train-stdout.log') -EA SilentlyContinue | Add-Content $LogFile
Get-Content (Join-Path $ProjectRoot 'train-stderr.log') -EA SilentlyContinue | Add-Content $LogFile
Add-Content $LogFile "EXIT_CODE=$code TIME=$(Get-Date -Format o)"
Get-ChildItem $OutputDir -Filter "$OutputName*.safetensors" -EA SilentlyContinue | ForEach-Object {
  Copy-Item $_.FullName (Join-Path $LoraDestDir $_.Name) -Force
  Add-Content $LogFile "COPIED $($_.Name)"
}
