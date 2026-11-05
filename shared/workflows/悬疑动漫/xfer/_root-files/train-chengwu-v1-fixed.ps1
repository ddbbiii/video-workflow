$ErrorActionPreference = 'Continue'
$trainPy = 'E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe'
$SdScriptsDir = 'E:\program\1project\video\shared\project-tools\lora\sd-scripts'
$TrainDataDir = 'E:\program\1project\video\shared\project-tools\lora\chengwu-v1\dataset\img'
$OutputDir = 'E:\program\1project\video\shared\project-tools\lora\chengwu-v1\output'
$BaseCkpt = 'E:\program\1project\video\shared\runtime\comfy\models\models\checkpoints\animagine-xl-4.0-opt.safetensors'
$LogFile = 'E:\program\1project\video\shared\project-tools\lora\chengwu-v1\train.log'
$LoraDestDir = 'E:\program\1project\video\shared\runtime\comfy\models\models\loras'
$OutputName = 'chengwu-sdxl-v1'

New-Item -ItemType Directory -Force -Path $OutputDir,$LoraDestDir | Out-Null
Set-Location $SdScriptsDir
$env:PYTHONPATH = $SdScriptsDir
$env:HF_ENDPOINT = 'https://hf-mirror.com'
$env:PYTHONUTF8 = '1'

# ensure library importable
& $trainPy -m pip install -e . --quiet 2>$null

if (Test-Path $LogFile) { Remove-Item $LogFile -Force }

$argLine = @(
  'sdxl_train_network.py',
  '--pretrained_model_name_or_path', $BaseCkpt,
  '--train_data_dir', $TrainDataDir,
  '--output_dir', $OutputDir,
  '--output_name', $OutputName,
  '--network_module', 'networks.lora',
  '--network_dim', '16',
  '--network_alpha', '8',
  '--resolution', '1024,1024',
  '--train_batch_size', '1',
  '--max_train_epochs', '20',
  '--save_every_n_epochs', '5',
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

Add-Content $LogFile "START $(Get-Date -Format o) PYTHONPATH=$env:PYTHONPATH"
# Launch via cmd to avoid PowerShell native stderr abort
$cmd = '"' + $trainPy + '" ' + ($argLine | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join ' '
Add-Content $LogFile "CMD $cmd"
cmd /c "$cmd >> `"$LogFile`" 2>&1"
$code = $LASTEXITCODE
Add-Content $LogFile "EXIT_CODE=$code TIME=$(Get-Date -Format o)"
Get-ChildItem $OutputDir -Filter "$OutputName*.safetensors" -ErrorAction SilentlyContinue | ForEach-Object {
  Copy-Item $_.FullName (Join-Path $LoraDestDir $_.Name) -Force
  Add-Content $LogFile "COPIED $($_.Name)"
}
