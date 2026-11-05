$ErrorActionPreference = 'Continue'
$trainPy = 'E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe'
$SdScriptsDir = 'E:\program\1project\video\shared\project-tools\lora\sd-scripts'
$ProjectRoot = 'E:\program\1project\video\shared\project-tools\lora\jiaoli-home-v1'
$TrainDataDir = Join-Path $ProjectRoot 'dataset\img'
$OutputDir = Join-Path $ProjectRoot 'output'
$BaseCkpt = 'E:\program\1project\video\shared\runtime\comfy\models\models\checkpoints\animagine-xl-4.0-opt.safetensors'
$LogFile = Join-Path $ProjectRoot 'train.log'
$LoraDestDir = 'E:\program\1project\video\shared\runtime\comfy\models\models\loras'
$SrcTgz = 'E:\program\1project\video\xfer\home-lora-dataset.tgz'
$OutputName = 'jiaoli-home-sdxl-v1'
$WrapperSrc = 'E:\program\1project\video\xfer\run_sdxl_train.py'
$WrapperDst = Join-Path $SdScriptsDir 'run_sdxl_train.py'
$TokCache = 'E:\program\1project\video\shared\project-tools\lora\chengwu-v1\tokenizer-cache'

New-Item -ItemType Directory -Force -Path $ProjectRoot,$OutputDir,$LoraDestDir,(Join-Path $ProjectRoot 'dataset') | Out-Null
Copy-Item -Force $WrapperSrc $WrapperDst

$imgFolder = Join-Path $TrainDataDir '15_jiaoli_home'
if (-not (Test-Path (Join-Path $imgFolder '01-living-day.png'))) {
  tar -xzf $SrcTgz -C (Join-Path $ProjectRoot 'dataset')
}
$png = @(Get-ChildItem $imgFolder -Filter *.png -ErrorAction SilentlyContinue).Count
Write-Host "Dataset png=$png tok=$TokCache"

$env:PYTHONPATH = $SdScriptsDir
$env:HF_ENDPOINT = 'https://hf-mirror.com'
$env:HUGGINGFACE_HUB_CACHE = 'E:\program\1project\video\shared\runtime\comfy\cache\hf'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:PYTHONUTF8 = '1'
Set-Location $SdScriptsDir

if (Test-Path $LogFile) { Remove-Item $LogFile -Force }
Add-Content $LogFile "START $(Get-Date -Format o) imgs=$png offline_tok=$TokCache"

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
  '--max_train_epochs', '30',
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

$p = Start-Process -FilePath $trainPy -ArgumentList $argList -WorkingDirectory $SdScriptsDir -NoNewWindow -Wait -PassThru `
  -RedirectStandardOutput (Join-Path $ProjectRoot 'train-stdout.log') `
  -RedirectStandardError (Join-Path $ProjectRoot 'train-stderr.log')
$code = $p.ExitCode
Get-Content (Join-Path $ProjectRoot 'train-stdout.log') -ErrorAction SilentlyContinue | Add-Content $LogFile
Get-Content (Join-Path $ProjectRoot 'train-stderr.log') -ErrorAction SilentlyContinue | Add-Content $LogFile
Add-Content $LogFile "EXIT_CODE=$code TIME=$(Get-Date -Format o)"
Get-ChildItem $OutputDir -Filter "$OutputName*.safetensors" -ErrorAction SilentlyContinue | ForEach-Object {
  Copy-Item $_.FullName (Join-Path $LoraDestDir $_.Name) -Force
  Add-Content $LogFile "COPIED $($_.Name)"
}
