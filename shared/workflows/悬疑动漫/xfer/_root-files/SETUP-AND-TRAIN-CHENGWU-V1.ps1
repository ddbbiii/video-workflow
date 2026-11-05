#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot: unpack chengwu dataset, install kohya sd-scripts, train SDXL LoRA, copy to Comfy loras.

.NOTES
  Target: ddbbi (Windows). Run via parent Shell with machineId
  681ffa39-7c25-4986-9259-a5efe42ff20a
  Do NOT touch Mac. Do NOT kill active Comfy/H3 renders.
#>
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

# ========== Paths ==========
$ProjectRoot   = 'E:\program\1project\video\shared\project-tools\lora\chengwu-v1'
$DatasetRoot   = Join-Path $ProjectRoot 'dataset'
$TrainDataDir  = Join-Path $DatasetRoot 'img'          # contains 10_chengwu
$ImgFolder     = Join-Path $TrainDataDir '10_chengwu'
$OutputDir     = Join-Path $ProjectRoot 'output'
$LogFile       = Join-Path $ProjectRoot 'train.log'
$LauncherPs1   = Join-Path $ProjectRoot 'train-chengwu-v1.ps1'
$SdScriptsDir  = 'E:\program\1project\video\shared\project-tools\lora\sd-scripts'
$VenvDir       = Join-Path $SdScriptsDir 'venv'
$BaseCkpt      = 'E:\program\1project\video\shared\runtime\comfy\models\models\checkpoints\animagine-xl-4.0-opt.safetensors'
$LoraDestDir   = 'E:\program\1project\video\shared\runtime\comfy\models\models\loras'
$SrcTgz        = 'E:\program\1project\video\xfer\chengwu-lora-dataset.tgz'
$OutputName    = 'chengwu-sdxl-v1'

function Write-Step([string]$msg) {
  $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
  Write-Host "[$ts] $msg"
}

function Get-RealPython {
  $candidates = @(
    'E:\program\language\python\Python-3.11.0\python.exe',
    'C:\Users\10060\AppData\Local\Python\bin\python.exe',
    'C:\Users\10060\AppData\Local\Programs\Python\Python311\python.exe',
    'C:\Users\10060\AppData\Local\Programs\Python\Python312\python.exe',
    'E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe',
    'E:\program\1project\video\python_embeded\python.exe'
  )
  foreach ($p in $candidates) {
    if (Test-Path $p) {
      # Skip WindowsApps stub
      if ($p -match 'WindowsApps') { continue }
      try {
        $ver = & $p -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($LASTEXITCODE -eq 0 -and $ver) {
          Write-Step "Found Python $ver at $p"
          return $p
        }
      } catch { }
    }
  }
  # where.exe fallback, exclude WindowsApps
  $where = & where.exe python 2>$null
  foreach ($line in $where) {
    if ($line -and ($line -notmatch 'WindowsApps') -and (Test-Path $line)) {
      Write-Step "where.exe Python: $line"
      return $line
    }
  }
  throw 'No real Python found. Install Python 3.11+ or point to embeded Comfy python.'
}

function Test-GpuIdleEnough {
  # Return hashtable: freeMiB, usedByComfy, recommendStopIdleComfy
  $info = @{ freeMiB = -1; comfyPids = @(); h3Likely = $false; nvidiaOk = $false }
  try {
    $q = & nvidia-smi --query-gpu=memory.free,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits 2>$null
    if ($q) {
      $parts = ($q -split ',') | ForEach-Object { $_.Trim() }
      $info.freeMiB = [int]$parts[0]
      $info.usedMiB = [int]$parts[1]
      $info.totalMiB = [int]$parts[2]
      $info.util = [int]$parts[3]
      $info.nvidiaOk = $true
    }
  } catch { }
  $comfy = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match 'python|ComfyUI' -and $_.CommandLine -match 'ComfyUI|main\.py' }
  foreach ($p in $comfy) {
    $info.comfyPids += [pscustomobject]@{ Pid = $p.ProcessId; Cmd = ($p.CommandLine.Substring(0, [Math]::Min(180, $p.CommandLine.Length))) }
    if ($p.CommandLine -match '8189|MiniMax|H3') { $info.h3Likely = $true }
  }
  return $info
}

# ========== 0. Preconditions ==========
Write-Step '=== chengwu SDXL LoRA v1 setup+train ==='
if (-not (Test-Path $SrcTgz)) { throw "Dataset tgz missing: $SrcTgz" }
if (-not (Test-Path $BaseCkpt)) { throw "Base checkpoint missing: $BaseCkpt" }

$gpu = Test-GpuIdleEnough
Write-Step ("GPU: free={0}MiB used={1}MiB total={2}MiB util={3}% nvidiaOk={4}" -f $gpu.freeMiB, $gpu.usedMiB, $gpu.totalMiB, $gpu.util, $gpu.nvidiaOk)
if ($gpu.comfyPids.Count -gt 0) {
  Write-Step 'Comfy-related processes:'
  $gpu.comfyPids | ForEach-Object { Write-Step ("  PID {0}: {1}" -f $_.Pid, $_.Cmd) }
}
# Only stop clearly-idle Comfy if VRAM tight (<10GB free) and util low and NOT H3
if ($gpu.nvidiaOk -and $gpu.freeMiB -ge 0 -and $gpu.freeMiB -lt 10000 -and $gpu.util -lt 5 -and -not $gpu.h3Likely) {
  Write-Step 'VRAM tight + GPU idle — attempting to stop idle ComfyUI (not H3)...'
  foreach ($c in $gpu.comfyPids) {
    if ($c.Cmd -match '8189|MiniMax|H3') {
      Write-Step "SKIP (H3/active protect): PID $($c.Pid)"
      continue
    }
    # Only kill if util stays low — prefer main.py on 8188 portable
    if ($c.Cmd -match '8188|ComfyUI\\main|AI\\ComfyUI') {
      try {
        Stop-Process -Id $c.Pid -Force -ErrorAction Stop
        Write-Step "Stopped idle Comfy PID $($c.Pid)"
      } catch {
        Write-Step "Could not stop PID $($c.Pid): $_"
      }
    }
  }
  Start-Sleep -Seconds 3
  $gpu = Test-GpuIdleEnough
  Write-Step ("GPU after cleanup: free={0}MiB util={1}%" -f $gpu.freeMiB, $gpu.util)
} elseif ($gpu.h3Likely) {
  Write-Step 'H3/8189 detected — will NOT kill. Train may OOM if VRAM shared; prefer wait.'
}

# ========== 1. Dataset unpack ==========
Write-Step "Create $ProjectRoot"
New-Item -ItemType Directory -Force -Path $ProjectRoot, $DatasetRoot, $OutputDir, $LoraDestDir | Out-Null

Write-Step "Unpack $SrcTgz -> $DatasetRoot"
# tar on Win10+ ; fall back to tar.exe
Push-Location $DatasetRoot
try {
  if ((Test-Path (Join-Path $ImgFolder '01-style-lock.png')) -eq $false) {
    & tar.exe -xzf $SrcTgz
    if ($LASTEXITCODE -ne 0) { throw "tar extract failed exit=$LASTEXITCODE" }
  } else {
    Write-Step 'Dataset already present, skip extract'
  }
} finally { Pop-Location }

$pngs = @(Get-ChildItem -Path $ImgFolder -Filter '*.png' -File -ErrorAction Stop)
$txts = @(Get-ChildItem -Path $ImgFolder -Filter '*.txt' -File -ErrorAction Stop)
Write-Step "Verify: $($pngs.Count) png, $($txts.Count) txt in $ImgFolder"
if ($pngs.Count -ne 14 -or $txts.Count -ne 14) {
  throw "Expected 14 png + 14 txt, got $($pngs.Count)/$($txts.Count)"
}
# Ensure each png has matching txt
foreach ($p in $pngs) {
  $t = Join-Path $ImgFolder ($p.BaseName + '.txt')
  if (-not (Test-Path $t)) { throw "Missing caption for $($p.Name)" }
}
Write-Step 'Dataset OK (14+14)'

# ========== 2. Install sd-scripts ==========
$py = Get-RealPython
Write-Step "Using base Python: $py"

if (-not (Test-Path (Join-Path $SdScriptsDir 'sdxl_train_network.py'))) {
  Write-Step "Clone/install kohya sd-scripts -> $SdScriptsDir"
  New-Item -ItemType Directory -Force -Path (Split-Path $SdScriptsDir) | Out-Null
  $cloned = $false
  $gitUrls = @(
    'https://github.com/kohya-ss/sd-scripts.git',
    'https://ghproxy.com/https://github.com/kohya-ss/sd-scripts.git',
    'https://mirror.ghproxy.com/https://github.com/kohya-ss/sd-scripts.git'
  )
  foreach ($url in $gitUrls) {
    try {
      if (Test-Path $SdScriptsDir) { Remove-Item -Recurse -Force $SdScriptsDir }
      Write-Step "git clone $url"
      & git clone --depth 1 $url $SdScriptsDir 2>&1 | Out-Host
      if ((Test-Path (Join-Path $SdScriptsDir 'sdxl_train_network.py'))) { $cloned = $true; break }
    } catch {
      Write-Step "clone failed: $_"
    }
  }
  if (-not $cloned) {
    Write-Step 'git clone failed — try zip download'
    $zip = Join-Path $env:TEMP 'sd-scripts-main.zip'
    $zipUrls = @(
      'https://github.com/kohya-ss/sd-scripts/archive/refs/heads/main.zip',
      'https://ghproxy.com/https://github.com/kohya-ss/sd-scripts/archive/refs/heads/main.zip'
    )
    $got = $false
    foreach ($zu in $zipUrls) {
      try {
        Invoke-WebRequest -Uri $zu -OutFile $zip -UseBasicParsing
        $got = $true; break
      } catch { Write-Step "zip dl fail: $zu :: $_" }
    }
    if (-not $got) { throw 'Could not obtain sd-scripts (git+zip failed)' }
    $unpackParent = Split-Path $SdScriptsDir
    Expand-Archive -Path $zip -DestinationPath $unpackParent -Force
    $extracted = Get-ChildItem $unpackParent -Directory | Where-Object { $_.Name -match 'sd-scripts' } | Select-Object -First 1
    if (-not $extracted) { throw 'zip extract: sd-scripts folder not found' }
    if ($extracted.FullName -ne $SdScriptsDir) {
      if (Test-Path $SdScriptsDir) { Remove-Item -Recurse -Force $SdScriptsDir }
      Rename-Item $extracted.FullName (Split-Path $SdScriptsDir -Leaf)
    }
  }
} else {
  Write-Step 'sd-scripts already present'
}

if (-not (Test-Path (Join-Path $SdScriptsDir 'sdxl_train_network.py'))) {
  throw "sdxl_train_network.py missing under $SdScriptsDir"
}

# Create venv
$venvPy = Join-Path $VenvDir 'Scripts\python.exe'
if (-not (Test-Path $venvPy)) {
  Write-Step "Create venv at $VenvDir"
  & $py -m venv $VenvDir
  if (-not (Test-Path $venvPy)) { throw 'venv creation failed' }
}

$pip = Join-Path $VenvDir 'Scripts\pip.exe'
Write-Step 'Upgrade pip'
& $venvPy -m pip install -U pip setuptools wheel

# Torch CUDA — prefer cu128 for 50-series; fall back cu124/cu121
Write-Step 'Detect existing torch in venv'
$torchInfo = & $venvPy -c "import torch; print(torch.__version__, getattr(torch.version,'cuda',None), torch.cuda.is_available())" 2>$null
if ($LASTEXITCODE -ne 0 -or -not $torchInfo -or $torchInfo -notmatch 'True') {
  Write-Step 'Install torch with CUDA (try cu128 then cu124)'
  $torchOk = $false
  foreach ($index in @(
    'https://download.pytorch.org/whl/cu128',
    'https://download.pytorch.org/whl/cu124',
    'https://download.pytorch.org/whl/cu121'
  )) {
    try {
      Write-Step "pip install torch torchvision --index-url $index"
      & $venvPy -m pip install --upgrade torch torchvision --index-url $index
      $check = & $venvPy -c "import torch; assert torch.cuda.is_available(); print(torch.__version__, torch.version.cuda, torch.cuda.get_device_name(0))"
      Write-Step "Torch OK: $check"
      $torchOk = $true
      break
    } catch {
      Write-Step "torch index failed ($index): $_"
    }
  }
  if (-not $torchOk) { throw 'Failed to install CUDA torch' }
} else {
  Write-Step "Torch already usable: $torchInfo"
}

# HF mirror for any model downloads during deps
$env:HF_ENDPOINT = 'https://hf-mirror.com'
$env:PIP_DISABLE_PIP_VERSION_CHECK = '1'

Write-Step 'pip install -r requirements.txt'
Push-Location $SdScriptsDir
try {
  & $venvPy -m pip install -r requirements.txt
  # bitsandbytes optional on Windows
  & $venvPy -m pip install bitsandbytes 2>&1 | Out-Host
  & $venvPy -m pip install prodigyopt lion-pytorch 2>&1 | Out-Host
} finally { Pop-Location }

# Verify bnb
$use8bit = $false
$bnbCheck = & $venvPy -c "import bitsandbytes; print('ok')" 2>$null
if ($LASTEXITCODE -eq 0 -and $bnbCheck -match 'ok') {
  $use8bit = $true
  Write-Step 'bitsandbytes OK -> AdamW8bit'
} else {
  Write-Step 'bitsandbytes not usable -> AdamW'
}

# Probe bf16
$useBf16 = $false
$bf = & $venvPy -c "import torch; x=torch.zeros(1,device='cuda',dtype=torch.bfloat16); y=x+1; print('bf16ok')" 2>$null
if ($LASTEXITCODE -eq 0 -and $bf -match 'bf16ok') {
  $useBf16 = $true
  Write-Step 'bf16 supported'
} else {
  Write-Step 'bf16 not supported / failed — use fp16'
}

$mixedPrecision = if ($useBf16) { 'bf16' } else { 'fp16' }
$optimizer = if ($use8bit) { 'AdamW8bit' } else { 'AdamW' }

# ========== 3. Write launcher ==========
Write-Step "Writing train-chengwu-v1.ps1"

$launcherBody = @'
# train-chengwu-v1.ps1
$ErrorActionPreference = 'Stop'
$SdScripts = 'E:\program\1project\video\shared\project-tools\lora\sd-scripts'
$VenvPython = 'E:\program\1project\video\shared\project-tools\lora\sd-scripts\venv\Scripts\python.exe'
$ProjectRoot = 'E:\program\1project\video\shared\project-tools\lora\chengwu-v1'
$Log = Join-Path $ProjectRoot 'train.log'
$env:HF_ENDPOINT = 'https://hf-mirror.com'
$env:PYTHONUNBUFFERED = '1'
Set-Location $SdScripts
New-Item -ItemType Directory -Force -Path (Join-Path $ProjectRoot 'output'), (Join-Path $ProjectRoot 'logs') | Out-Null

$mixed = '__MIXED__'
$opt = '__OPT__'

function Invoke-Train([string[]]$extra) {
  $a = @(
    'sdxl_train_network.py',
    '--pretrained_model_name_or_path', 'E:\program\1project\video\shared\runtime\comfy\models\models\checkpoints\animagine-xl-4.0-opt.safetensors',
    '--train_data_dir', 'E:\program\1project\video\shared\project-tools\lora\chengwu-v1\dataset\img',
    '--output_dir', 'E:\program\1project\video\shared\project-tools\lora\chengwu-v1\output',
    '--output_name', 'chengwu-sdxl-v1',
    '--network_module', 'networks.lora',
    '--network_dim', '16',
    '--network_alpha', '8',
    '--resolution', '1024,1024',
    '--train_batch_size', '1',
    '--gradient_accumulation_steps', '1',
    '--mixed_precision', $mixed,
    '--save_precision', $mixed,
    '--learning_rate', '1e-4',
    '--unet_lr', '1e-4',
    '--text_encoder_lr', '5e-5',
    '--lr_scheduler', 'cosine',
    '--lr_warmup_steps', '50',
    '--max_train_epochs', '20',
    '--save_every_n_epochs', '5',
    '--caption_extension', '.txt',
    '--shuffle_caption',
    '--keep_tokens', '1',
    '--cache_latents',
    '--cache_latents_to_disk',
    '--optimizer_type', $opt,
    '--seed', '42',
    '--min_snr_gamma', '5',
    '--enable_bucket',
    '--bucket_reso_steps', '64',
    '--max_data_loader_n_workers', '0',
    '--gradient_checkpointing',
    '--logging_dir', (Join-Path $ProjectRoot 'logs'),
    '--log_prefix', 'chengwu-v1'
  ) + $extra
  Write-Host ("[{0}] START train extras={1}" -f (Get-Date -Format 'HH:mm:ss'), ($extra -join ' '))
  Write-Host ("CMD: {0} {1}" -f $VenvPython, ($a -join ' '))
  & $VenvPython @a 2>&1 | Tee-Object -FilePath $Log -Append
  return $LASTEXITCODE
}

# Try with sdpa (PyTorch) first — more reliable than xformers on new GPUs
$code = Invoke-Train @('--sdpa')
if ($code -ne 0) {
  Add-Content $Log "`nRETRY without sdpa / with fp16 fallback notes`n"
}
# OOM / fail heuristics: retry 768 + dim 8
$logTail = ''
if (Test-Path $Log) { $logTail = Get-Content $Log -Tail 80 -ErrorAction SilentlyContinue | Out-String }
if ($code -ne 0 -and ($logTail -match 'out of memory|CUDA out of memory|OOM')) {
  Write-Host 'OOM detected — retry resolution 768, network_dim 8'
  $a2 = @(
    'sdxl_train_network.py',
    '--pretrained_model_name_or_path', 'E:\program\1project\video\shared\runtime\comfy\models\models\checkpoints\animagine-xl-4.0-opt.safetensors',
    '--train_data_dir', 'E:\program\1project\video\shared\project-tools\lora\chengwu-v1\dataset\img',
    '--output_dir', 'E:\program\1project\video\shared\project-tools\lora\chengwu-v1\output',
    '--output_name', 'chengwu-sdxl-v1',
    '--network_module', 'networks.lora',
    '--network_dim', '8',
    '--network_alpha', '4',
    '--resolution', '768,768',
    '--train_batch_size', '1',
    '--gradient_accumulation_steps', '1',
    '--mixed_precision', $mixed,
    '--save_precision', $mixed,
    '--learning_rate', '1e-4',
    '--unet_lr', '1e-4',
    '--text_encoder_lr', '5e-5',
    '--lr_scheduler', 'cosine',
    '--lr_warmup_steps', '50',
    '--max_train_epochs', '20',
    '--save_every_n_epochs', '5',
    '--caption_extension', '.txt',
    '--shuffle_caption',
    '--keep_tokens', '1',
    '--cache_latents',
    '--cache_latents_to_disk',
    '--optimizer_type', $opt,
    '--seed', '42',
    '--min_snr_gamma', '5',
    '--enable_bucket',
    '--max_data_loader_n_workers', '0',
    '--gradient_checkpointing',
    '--sdpa'
  )
  & $VenvPython @a2 2>&1 | Tee-Object -FilePath $Log -Append
  $code = $LASTEXITCODE
}

# Copy latest safetensors to Comfy loras
$outDir = 'E:\program\1project\video\shared\project-tools\lora\chengwu-v1\output'
$destDir = 'E:\program\1project\video\shared\runtime\comfy\models\models\loras'
New-Item -ItemType Directory -Force -Path $destDir | Out-Null
$safes = @(Get-ChildItem $outDir -Filter 'chengwu-sdxl-v1*.safetensors' -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime)
foreach ($s in $safes) {
  if ($s.Name -match 'chengwu-sdxl-v1-([0-9]+)\.safetensors' -or $s.Name -match 'chengwu-sdxl-v1-ep([0-9]+)') {
    $ep = $Matches[1]
    Copy-Item $s.FullName (Join-Path $destDir ("chengwu-sdxl-v1-ep{0}.safetensors" -f $ep)) -Force
  }
}
$latest = $safes | Select-Object -Last 1
if ($latest) {
  Copy-Item $latest.FullName (Join-Path $destDir 'chengwu-sdxl-v1.safetensors') -Force
  Write-Host "Copied latest -> $destDir\chengwu-sdxl-v1.safetensors ($($latest.Name))"
}

Write-Host "Exit code: $code"
exit $code
'@

$launcherBody = $launcherBody.Replace('__MIXED__', $mixedPrecision).Replace('__OPT__', $optimizer)
Set-Content -Path $LauncherPs1 -Value $launcherBody -Encoding UTF8
Write-Step "Wrote launcher $LauncherPs1 (mixed=$mixedPrecision opt=$optimizer)"

# Also write a tiny status json
$status = [ordered]@{
  time = (Get-Date -Format 'o')
  mixed_precision = $mixedPrecision
  optimizer = $optimizer
  train_data_dir = $TrainDataDir
  output_dir = $OutputDir
  sd_scripts = $SdScriptsDir
  venv_python = $venvPy
  base_ckpt = $BaseCkpt
  png_count = $pngs.Count
  txt_count = $txts.Count
}
$status | ConvertTo-Json | Set-Content (Join-Path $ProjectRoot 'setup-status.json') -Encoding UTF8

# ========== 4. Start training (background) ==========
Write-Step 'Starting training in background...'
if (Test-Path $LogFile) { Add-Content $LogFile "`n==== NEW RUN $(Get-Date -Format o) ====`n" }

$arg = "-NoProfile -ExecutionPolicy Bypass -File `"$LauncherPs1`""
$proc = Start-Process -FilePath 'powershell.exe' -ArgumentList $arg -WorkingDirectory $ProjectRoot -WindowStyle Hidden -PassThru
Write-Step "Training started PID=$($proc.Id)"
Start-Sleep -Seconds 8

# Quick health
$alive = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
$tail = if (Test-Path $LogFile) { Get-Content $LogFile -Tail 30 | Out-String } else { '(no log yet)' }
Write-Step "Process alive=$([bool]$alive)"
Write-Host '--- log tail ---'
Write-Host $tail

# Write PID file
$proc.Id | Set-Content (Join-Path $ProjectRoot 'train.pid')

Write-Step 'SETUP+TRAIN launch complete. Monitor train.log / output/*.safetensors'
Write-Output "PID=$($proc.Id)"
Write-Output "LOG=$LogFile"
Write-Output "OUT=$OutputDir"
