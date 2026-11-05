#Requires -Version 5.1
$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'

$ProjectRoot   = 'E:\program\1project\video\shared\project-tools\lora\chengwu-v1'
$DatasetRoot   = Join-Path $ProjectRoot 'dataset'
$TrainDataDir  = Join-Path $DatasetRoot 'img'
$ImgFolder     = Join-Path $TrainDataDir '10_chengwu'
$OutputDir     = Join-Path $ProjectRoot 'output'
$LogFile       = Join-Path $ProjectRoot 'train.log'
$LauncherPs1   = Join-Path $ProjectRoot 'train-chengwu-v1.ps1'
$SdScriptsDir  = 'E:\program\1project\video\shared\project-tools\lora\sd-scripts'
$VenvDir       = Join-Path $SdScriptsDir 'venv'
$BaseCkpt      = 'E:\program\1project\video\shared\runtime\comfy\models\models\checkpoints\animagine-xl-4.0-opt.safetensors'
$LoraDestDir   = 'E:\program\1project\video\shared\runtime\comfy\models\models\loras'
$SrcTgz        = 'E:\program\1project\video\xfer\chengwu-lora-dataset.tgz'
$SdTgz         = 'E:\program\1project\video\xfer\sd-scripts.tgz'
$OutputName    = 'chengwu-sdxl-v1'
$ConsoleLog    = Join-Path $ProjectRoot 'setup-console.log'

function Write-Step([string]$msg) {
  $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
  $line = "[$ts] $msg"
  Write-Host $line
  Add-Content -Path $ConsoleLog -Value $line -Encoding UTF8
}

function Invoke-Py([string]$exe, [string]$code) {
  $out = & $exe -c $code 2>&1 | Out-String
  return @{ ExitCode = $LASTEXITCODE; Text = $out.Trim() }
}

New-Item -ItemType Directory -Force -Path $ProjectRoot,$OutputDir,$LoraDestDir | Out-Null
Write-Step '=== chengwu SDXL LoRA v2 setup+train ==='

# GPU
$gpu = nvidia-smi --query-gpu=memory.used,memory.free,utilization.gpu --format=csv,noheader 2>$null
Write-Step "GPU: $gpu"

# Dataset
if (-not (Test-Path (Join-Path $ImgFolder '01-style-lock.png'))) {
  Write-Step "Unpack dataset $SrcTgz"
  New-Item -ItemType Directory -Force -Path $DatasetRoot | Out-Null
  tar -xzf $SrcTgz -C $DatasetRoot
}
$png = (Get-ChildItem $ImgFolder -Filter *.png).Count
$txt = (Get-ChildItem $ImgFolder -Filter *.txt).Count
Write-Step "Dataset: $png png / $txt txt"
if ($png -lt 14 -or $txt -lt 14) { throw "Dataset incomplete" }

# Prefer portable Comfy python (already has CUDA torch)
$portablePy = 'E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe'
$sysPy = 'E:\program\language\python\Python-3.11.0\python.exe'
$py = $null
$useVenv = $true

if (Test-Path $portablePy) {
  $r = Invoke-Py $portablePy "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"
  Write-Step "portable torch probe: $($r.Text)"
  if ($r.ExitCode -eq 0 -and $r.Text -match 'True') {
    $py = $portablePy
    $useVenv = $false
    Write-Step 'Using portable ComfyUI python (CUDA torch ready)'
  }
}
if (-not $py) {
  if (-not (Test-Path $sysPy)) { throw 'No usable Python' }
  $py = $sysPy
  Write-Step "Using system Python: $py"
}

# sd-scripts from local tgz (avoid GitHub from Windows)
if (-not (Test-Path (Join-Path $SdScriptsDir 'sdxl_train_network.py'))) {
  if (-not (Test-Path $SdTgz)) { throw "Missing $SdTgz" }
  Write-Step "Unpack sd-scripts from $SdTgz"
  $parent = Split-Path $SdScriptsDir
  New-Item -ItemType Directory -Force -Path $parent | Out-Null
  if (Test-Path $SdScriptsDir) { Remove-Item -Recurse -Force $SdScriptsDir }
  tar -xzf $SdTgz -C $parent
  if (-not (Test-Path (Join-Path $SdScriptsDir 'sdxl_train_network.py'))) { throw 'sd-scripts unpack failed' }
} else {
  Write-Step 'sd-scripts already present'
}

# Python for training
if ($useVenv) {
  $venvPy = Join-Path $VenvDir 'Scripts\python.exe'
  if (-not (Test-Path $venvPy)) {
    Write-Step "Create venv $VenvDir"
    & $py -m venv $VenvDir
  }
  $trainPy = $venvPy
  Write-Step 'Upgrade pip'
  & $trainPy -m pip install -U pip setuptools wheel
  $tr = Invoke-Py $trainPy "import torch; print(torch.__version__, torch.cuda.is_available())"
  Write-Step "venv torch: $($tr.Text)"
  if ($tr.ExitCode -ne 0 -or $tr.Text -notmatch 'True') {
    Write-Step 'Install torch cu128/cu124'
    $ok = $false
    foreach ($idx in @('https://download.pytorch.org/whl/cu128','https://download.pytorch.org/whl/cu124')) {
      Write-Step "pip torch $idx"
      & $trainPy -m pip install --upgrade torch torchvision --index-url $idx
      $c = Invoke-Py $trainPy "import torch; assert torch.cuda.is_available(); print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0))"
      Write-Step $c.Text
      if ($c.ExitCode -eq 0 -and $c.Text -match 'True|CUDA|GeForce|RTX') { $ok = $true; break }
    }
    if (-not $ok) { throw 'CUDA torch install failed' }
  }
} else {
  $trainPy = $py
}

$env:HF_ENDPOINT = 'https://hf-mirror.com'
Write-Step 'pip install sd-scripts requirements (may take a while)'
Push-Location $SdScriptsDir
try {
  & $trainPy -m pip install -r requirements.txt
  & $trainPy -m pip install bitsandbytes 2>&1 | Out-Null
} finally { Pop-Location }

$use8bit = $false
$bnb = Invoke-Py $trainPy "import bitsandbytes; print('ok')"
if ($bnb.ExitCode -eq 0 -and $bnb.Text -match 'ok') { $use8bit = $true; Write-Step 'AdamW8bit' } else { Write-Step 'AdamW' }

$useBf16 = $false
$bf = Invoke-Py $trainPy "import torch; x=torch.zeros(1,device='cuda',dtype=torch.bfloat16); print('bf16ok')"
if ($bf.ExitCode -eq 0 -and $bf.Text -match 'bf16ok') { $useBf16 = $true; Write-Step 'bf16' } else { Write-Step 'fp16' }

$opt = if ($use8bit) { 'AdamW8bit' } else { 'AdamW' }
$mp = if ($useBf16) { 'bf16' } else { 'fp16' }

# Write launcher
$launcher = @"
# Auto-generated train launcher
`$ErrorActionPreference = 'Continue'
`$trainPy = '$trainPy'
`$SdScriptsDir = '$SdScriptsDir'
`$TrainDataDir = '$TrainDataDir'
`$OutputDir = '$OutputDir'
`$BaseCkpt = '$BaseCkpt'
`$LogFile = '$LogFile'
`$OutputName = '$OutputName'
`$opt = '$opt'
`$mp = '$mp'

Set-Location `$SdScriptsDir
`$env:HF_ENDPOINT = 'https://hf-mirror.com'
`$argsList = @(
  'sdxl_train_network.py',
  '--pretrained_model_name_or_path', `$BaseCkpt,
  '--train_data_dir', `$TrainDataDir,
  '--output_dir', `$OutputDir,
  '--output_name', `$OutputName,
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
  '--optimizer_type', `$opt,
  '--mixed_precision', `$mp,
  '--save_precision', `$mp,
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
  '--max_data_loader_n_workers', '0',
  '--persistent_data_loader_workers'
)
Write-Host 'Starting training...'
& `$trainPy @argsList *>> `$LogFile
`$code = `$LASTEXITCODE
Add-Content `$LogFile "EXIT_CODE=`$code"
# copy latest
New-Item -ItemType Directory -Force -Path '$LoraDestDir' | Out-Null
Get-ChildItem `$OutputDir -Filter "`$OutputName*.safetensors" | ForEach-Object {
  Copy-Item `$_.FullName (Join-Path '$LoraDestDir' `$_.Name) -Force
}
"@
Set-Content -Path $LauncherPs1 -Value $launcher -Encoding UTF8
Write-Step "Wrote $LauncherPs1"

# Start train in background
Write-Step 'Start training (background)'
$pidFile = Join-Path $ProjectRoot 'train.pid'
$p = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',$LauncherPs1) -WorkingDirectory $SdScriptsDir -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $ProjectRoot 'train-stdout.log') -RedirectStandardError (Join-Path $ProjectRoot 'train-stderr.log')
$p.Id | Set-Content $pidFile
Write-Step "Train PID=$($p.Id) log=$LogFile"
Write-Step '=== setup done; training launched ==='
