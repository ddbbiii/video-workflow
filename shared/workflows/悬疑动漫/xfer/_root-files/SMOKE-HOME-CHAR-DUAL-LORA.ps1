#Requires -Version 5.1
<#
.SYNOPSIS
  Dual-LoRA smoke: Chengwu (char ep10) + jiaoli_home (scene) on Portable ComfyUI :8188.
  NO browser. Serial jobs. Stages to Desktop xfer + smoke dir.

.NOTES
  Parent:
    CopyFromBox → E:\program\1project\video\shared\work\scratch\legacy-numbered\home-char-smoke\SMOKE-HOME-CHAR-DUAL-LORA.ps1
    Shell(machineId=681ffa39-7c25-4986-9259-a5efe42ff20a, block_until_ms=900000,
      command=powershell -NoProfile -ExecutionPolicy Bypass -File "E:\program\1project\video\shared\work\scratch\legacy-numbered\home-char-smoke\SMOKE-HOME-CHAR-DUAL-LORA.ps1")
#>
param(
  [string]$Api = 'http://127.0.0.1:8188',
  [double]$CharStrengthModel = 0.88,
  [double]$CharStrengthClip  = 0.82,
  [double]$SceneStrengthModel = 0.78,
  [double]$SceneStrengthClip  = 0.70,
  [int]$Steps = 28,
  [double]$Cfg = 5.3,
  [switch]$SkipOptionalD
)

$ErrorActionPreference = 'Stop'
$ROOT = 'E:\program\1project\video'
$SmokeDir = Join-Path $ROOT 'shared\work\scratch\legacy-numbered\home-char-smoke'
$XferDir  = 'E:\program\1project\video\xfer\home-char-smoke'
$Stamp    = Get-Date -Format 'yyyyMMdd-HHmmss'
$ReportPath = Join-Path $SmokeDir ("SMOKE-REPORT-{0}.json" -f $Stamp)
$CkptPrefer = 'animagine-xl-4.0-opt.safetensors'
$CharPrefer = 'chengwu-sdxl-v1-000010.safetensors'
$CharFinal  = 'chengwu-sdxl-v1.safetensors'
$ScenePrefer = 'jiaoli-home-sdxl-v1.safetensors'
$LoraDir = Join-Path $ROOT 'shared\runtime\comfy\models\models\loras'
$CkptDir = Join-Path $ROOT 'shared\runtime\comfy\models\models\checkpoints'

function Write-Info($m) { Write-Host ("[home-char {0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m) }
function Ensure-Dir($p) { New-Item -ItemType Directory -Force -Path $p | Out-Null; return $p }
function Get-Json($url) { Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 30 }
function Post-Json($url, $obj) {
  $body = $obj | ConvertTo-Json -Depth 40 -Compress
  return Invoke-RestMethod -Uri $url -Method Post -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -ContentType 'application/json; charset=utf-8' -TimeoutSec 120
}

Ensure-Dir $SmokeDir | Out-Null
Ensure-Dir $XferDir  | Out-Null

$report = [ordered]@{
  ok = $false
  stamp = $Stamp
  timezone = 'Asia/Shanghai'
  comfy_was_running = $false
  comfy_started = $false
  ckpt = $null
  char_lora = $null
  scene_lora = $null
  strengths = @{
    char_model = $CharStrengthModel; char_clip = $CharStrengthClip
    scene_model = $SceneStrengthModel; scene_clip = $SceneStrengthClip
  }
  steps = $Steps; cfg = $Cfg; sampler = 'euler_ancestral'; scheduler = 'normal'
  resolution = '832x1216'
  trigger_char = 'chengwu / 程雾'
  trigger_scene = 'jiaoli_home'
  shots = @()
  image_paths = @()
  xfer_paths = @()
  errors = @()
  note = 'Dual LoRA smoke: Chengwu ep10 + jiaoli_home — no IP-Adapter / OpenPose'
}

# ---------- 0) Resolve files on disk ----------
$ckptCandidates = @(
  (Join-Path $CkptDir $CkptPrefer),
  (Join-Path $CkptDir 'animagine-xl-4.0.safetensors'),
  (Join-Path $CkptDir 'animagineXL40_v4Opt.safetensors')
)
$ckptPath = $ckptCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $ckptPath) {
  $found = Get-ChildItem $CkptDir -Filter 'animagine*.safetensors' -ErrorAction SilentlyContinue | Select-Object -First 5
  $report.errors += "Animagine ckpt missing under $CkptDir. Found: $(($found | ForEach-Object Name) -join ', ')"
  $report | ConvertTo-Json -Depth 8 | Set-Content $ReportPath -Encoding UTF8
  throw $report.errors[-1]
}

$charPath = @(
  (Join-Path $LoraDir $CharPrefer),
  (Join-Path $ROOT 'shared\project-tools\lora\chengwu-v1\output\chengwu-sdxl-v1-000010.safetensors'),
  (Join-Path $LoraDir $CharFinal)
) | Where-Object { Test-Path $_ } | Select-Object -First 1

$scenePath = @(
  (Join-Path $LoraDir $ScenePrefer),
  (Join-Path $ROOT 'shared\project-tools\lora\jiaoli-home-v1\jiaoli-home-sdxl-v1.safetensors'),
  (Join-Path $ROOT 'shared\project-tools\lora\jiaoli-home-v1\output\jiaoli-home-sdxl-v1.safetensors')
) | Where-Object { Test-Path $_ } | Select-Object -First 1

# ep20/25 fallback for scene
if (-not $scenePath) {
  $scenePath = Get-ChildItem $LoraDir -Filter 'jiaoli-home*.safetensors' -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending | Select-Object -First 1 -ExpandProperty FullName
}

if (-not $charPath) {
  $report.errors += "Character LoRA missing (want $CharPrefer). Loras dir listing:"
  Get-ChildItem $LoraDir -Filter 'chengwu*.safetensors' -EA SilentlyContinue | ForEach-Object { Write-Info $_.Name }
  $report | ConvertTo-Json -Depth 8 | Set-Content $ReportPath -Encoding UTF8
  throw 'Character LoRA not found'
}
if (-not $scenePath) {
  $report.errors += "Scene LoRA missing (want $ScenePrefer)"
  Get-ChildItem $LoraDir -Filter 'jiaoli*.safetensors' -EA SilentlyContinue | ForEach-Object { Write-Info $_.Name }
  $report | ConvertTo-Json -Depth 8 | Set-Content $ReportPath -Encoding UTF8
  throw 'Scene LoRA not found'
}

# Ensure both under Comfy loras/
foreach ($src in @($charPath, $scenePath)) {
  $dest = Join-Path $LoraDir ([IO.Path]::GetFileName($src))
  if ($src -ne $dest -and -not (Test-Path $dest)) {
    Copy-Item $src $dest -Force
    Write-Info "Copied into Comfy loras: $dest"
  }
}
$charName = [IO.Path]::GetFileName($charPath)
$sceneName = [IO.Path]::GetFileName($scenePath)
$ckptName = [IO.Path]::GetFileName($ckptPath)
Write-Info "ckpt=$ckptName char=$charName scene=$sceneName"

# Caption trigger check (optional)
$cap = Join-Path $ROOT 'shared\project-tools\lora\jiaoli-home-v1\dataset\img\15_jiaoli_home\01-living-day.txt'
if (Test-Path $cap) {
  $capText = Get-Content $cap -Raw -EA SilentlyContinue
  Write-Info "Caption sample: $($capText.Trim().Substring(0, [Math]::Min(120, $capText.Trim().Length)))"
  if ($capText -match 'jiaoli_home') { $report.trigger_scene = 'jiaoli_home' }
}

# ---------- 1) GPU ----------
try {
  $gpu = & nvidia-smi --query-gpu=name,memory.used,memory.free,utilization.gpu --format=csv,noheader 2>$null
  Write-Info "GPU: $gpu"
  $report.gpu = "$gpu"
} catch { Write-Info 'nvidia-smi unavailable' }

# ---------- 2) Comfy 8188 (no browser) ----------
function Test-ComfyUp {
  try { $null = Get-Json "$Api/system_stats"; return $true } catch { return $false }
}

if (Test-ComfyUp) {
  $report.comfy_was_running = $true
  Write-Info 'ComfyUI 8188 already up'
} else {
  Write-Info '8188 down — starting Portable WITHOUT browser'
  $startScripts = @(
    (Join-Path $ROOT 'shared\runtime\comfy\installs\portable\start-portable-8188.bat'),
    (Join-Path $ROOT 'shared\runtime\comfy\installs\portable\start-first-round.ps1'),
    (Join-Path $ROOT 'shared\runtime\comfy\installs\portable\run_nvidia_gpu.bat'),
    'E:\program\1project\video\tools\start-first-round.ps1'
  )
  $started = $false
  foreach ($s in $startScripts) {
    if (-not (Test-Path $s)) { continue }
    Write-Info "Start via: $s"
    if ($s -match '\.ps1$') {
      Start-Process -FilePath 'powershell.exe' -ArgumentList @(
        '-NoProfile','-ExecutionPolicy','Bypass','-File',$s
      ) -WindowStyle Minimized
    } else {
      Start-Process -FilePath $s -WindowStyle Minimized
    }
    $started = $true
    $report.comfy_started = $true
    break
  }
  if (-not $started) {
    $report.errors += 'No Comfy start script found'
    $report | ConvertTo-Json -Depth 8 | Set-Content $ReportPath -Encoding UTF8
    throw $report.errors[-1]
  }
  $deadline = (Get-Date).AddMinutes(5)
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 5
    if (Test-ComfyUp) { Write-Info 'ComfyUI up on 8188'; break }
  }
  if (-not (Test-ComfyUp)) {
    $report.errors += 'ComfyUI 8188 not reachable after start'
    $report | ConvertTo-Json -Depth 8 | Set-Content $ReportPath -Encoding UTF8
    throw $report.errors[-1]
  }
}

# ---------- 3) Resolve API names ----------
$ckptInfo = Get-Json "$Api/object_info/CheckpointLoaderSimple"
$ckptList = @($ckptInfo.CheckpointLoaderSimple.input.required.ckpt_name[0])
$ckptApi = $ckptList | Where-Object { $_ -eq $ckptName -or $_ -match 'animagine-xl-4\.0-opt' } | Select-Object -First 1
if (-not $ckptApi) { $ckptApi = $ckptList | Where-Object { $_ -match 'animagine' } | Select-Object -First 1 }
if (-not $ckptApi) { throw "Animagine not in Comfy list. Sample: $(($ckptList | Select-Object -First 8) -join ', ')" }
$report.ckpt = $ckptApi
Write-Info "API ckpt=$ckptApi"

$loraInfo = Get-Json "$Api/object_info/LoraLoader"
$loraList = @($loraInfo.LoraLoader.input.required.lora_name[0])
$charApi = $loraList | Where-Object { $_ -eq $charName -or $_ -match 'chengwu-sdxl-v1-000010' } | Select-Object -First 1
if (-not $charApi) { $charApi = $loraList | Where-Object { $_ -match 'chengwu-sdxl-v1' } | Select-Object -First 1 }
$sceneApi = $loraList | Where-Object { $_ -eq $sceneName -or $_ -match 'jiaoli-home-sdxl-v1\.safetensors$' } | Select-Object -First 1
if (-not $sceneApi) { $sceneApi = $loraList | Where-Object { $_ -match 'jiaoli-home' } | Select-Object -First 1 }

if (-not $charApi) {
  $report.errors += "Char LoRA not in Comfy list. Sample: $(($loraList | Where-Object { $_ -match 'chengwu|jiaoli' } | Select-Object -First 20) -join ', ')"
  $report | ConvertTo-Json -Depth 8 | Set-Content $ReportPath -Encoding UTF8
  throw $report.errors[-1]
}
if (-not $sceneApi) {
  $report.errors += "Scene LoRA not in Comfy list. Sample jiaoli*: $(($loraList | Where-Object { $_ -match 'jiaoli' }) -join ', ')"
  $report | ConvertTo-Json -Depth 8 | Set-Content $ReportPath -Encoding UTF8
  throw $report.errors[-1]
}
$report.char_lora = $charApi
$report.scene_lora = $sceneApi
Write-Info "API char=$charApi scene=$sceneApi"

$Neg = 'lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, jpeg artifacts, signature, watermark, blurry, loli, child, photorealistic, extra people, crowd, multiple girls, deformed face, mutated hands'

$CHAR = 'chengwu, 程雾, 1girl, young adult, short grey-blue bob hair, brown eyes, pale skin, thin black choker with silver ring, teal long-sleeve scoop-neck top, anime style, masterpiece, best quality'

$shots = @(
  @{
    id = 'A-living-night-3q'
    w = 832; h = 1216; seed = 2026092001
    pos = "$CHAR, upper body, three-quarter view, looking at viewer, jiaoli_home, indoor home interior, living room, night, sofa, floor lamp, city lights through window, cozy atmosphere"
  },
  @{
    id = 'B-living-day-half'
    w = 832; h = 1216; seed = 2026092002
    pos = "$CHAR, half body, standing, looking at viewer, jiaoli_home, indoor home interior, living room, daytime, sofa, window, soft daylight"
  },
  @{
    id = 'C-sitting-reading'
    w = 832; h = 1216; seed = 2026092003
    pos = "$CHAR, sitting, reading a book, looking down slightly, jiaoli_home, indoor home interior, bedroom or living room, soft indoor light, cozy home"
  }
)
if (-not $SkipOptionalD) {
  $shots += @{
    id = 'D-living-night-alt'
    w = 896; h = 1152; seed = 2026092004
    pos = "$CHAR, upper body, side three-quarter, slight smile, looking at viewer, jiaoli_home, indoor home interior, living room, night, warm lamp light, city night window"
  }
}

function Build-DualLoraWorkflow($charLora, $sceneLora, $pos, $neg, $w, $h, $seed, $steps, $cfg, $prefix) {
  return [ordered]@{
    '1' = @{
      class_type = 'CheckpointLoaderSimple'
      inputs = @{ ckpt_name = $ckptApi }
    }
    '2' = @{
      class_type = 'LoraLoader'
      inputs = @{
        model = @('1', 0)
        clip  = @('1', 1)
        lora_name = $charLora
        strength_model = $CharStrengthModel
        strength_clip  = $CharStrengthClip
      }
    }
    '3' = @{
      class_type = 'LoraLoader'
      inputs = @{
        model = @('2', 0)
        clip  = @('2', 1)
        lora_name = $sceneLora
        strength_model = $SceneStrengthModel
        strength_clip  = $SceneStrengthClip
      }
    }
    '4' = @{
      class_type = 'CLIPTextEncode'
      inputs = @{ text = $pos; clip = @('3', 1) }
    }
    '5' = @{
      class_type = 'CLIPTextEncode'
      inputs = @{ text = $neg; clip = @('3', 1) }
    }
    '6' = @{
      class_type = 'EmptyLatentImage'
      inputs = @{ width = $w; height = $h; batch_size = 1 }
    }
    '7' = @{
      class_type = 'KSampler'
      inputs = @{
        seed = $seed
        steps = $steps
        cfg = $cfg
        sampler_name = 'euler_ancestral'
        scheduler = 'normal'
        denoise = 1.0
        model = @('3', 0)
        positive = @('4', 0)
        negative = @('5', 0)
        latent_image = @('6', 0)
      }
    }
    '8' = @{
      class_type = 'VAEDecode'
      inputs = @{ samples = @('7', 0); vae = @('1', 2) }
    }
    '9' = @{
      class_type = 'SaveImage'
      inputs = @{ filename_prefix = $prefix; images = @('8', 0) }
    }
  }
}

function Queue-And-Wait($wf, $clientId, $label) {
  $queued = Post-Json "$Api/prompt" @{ prompt = $wf; client_id = $clientId }
  if ($queued.node_errors) {
    throw ("node_errors $($label): " + ($queued.node_errors | ConvertTo-Json -Compress))
  }
  $promptId = $queued.prompt_id
  if (-not $promptId) { throw "No prompt_id for $label : $($queued | ConvertTo-Json -Compress)" }
  Write-Info "Queued $label → $promptId"
  $deadline = (Get-Date).AddMinutes(15)
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 3
    $hist = Get-Json "$Api/history/$promptId"
    if (-not $hist.$promptId) { continue }
    $entry = $hist.$promptId
    $st = $entry.status
    if ($st -and $st.status_str -eq 'error') {
      $msg = ($st.messages | ConvertTo-Json -Compress)
      throw "Comfy error $label : $msg"
    }
    if (($st -and $st.completed) -or ($entry.outputs -and $entry.outputs.PSObject.Properties.Name.Count -gt 0)) {
      $imgs = @()
      foreach ($nid in $entry.outputs.PSObject.Properties.Name) {
        if ($entry.outputs.$nid.images) { $imgs += $entry.outputs.$nid.images }
      }
      if (-not $imgs) { throw "Finished but no images: $label" }
      return @{ prompt_id = $promptId; images = $imgs }
    }
  }
  throw "Timeout waiting for $label ($promptId)"
}

function Save-ComfyImage($imgMeta, $destPath) {
  $viewUrl = "{0}/view?filename={1}&subfolder={2}&type={3}" -f `
    $Api,
    [uri]::EscapeDataString($imgMeta.filename),
    [uri]::EscapeDataString($(if ($imgMeta.subfolder) { $imgMeta.subfolder } else { '' })),
    $(if ($imgMeta.type) { $imgMeta.type } else { 'output' })
  Invoke-WebRequest -Uri $viewUrl -OutFile $destPath -TimeoutSec 120 -UseBasicParsing
  return $destPath
}

# Free VRAM between jobs if free endpoint exists (best-effort)
function Try-Unload {
  try {
    Invoke-RestMethod -Uri "$Api/free" -Method Post -Body '{"unload_models":true,"free_memory":true}' -ContentType 'application/json' -TimeoutSec 30 | Out-Null
    Write-Info 'Called /free unload'
    Start-Sleep -Seconds 2
  } catch {
    Write-Info 'No /free endpoint or failed (ok)'
  }
}

$clientId = [guid]::NewGuid().ToString()
$okCount = 0
foreach ($s in $shots) {
  $prefix = "home-char-smoke/$($s.id)-$Stamp"
  $shotRec = [ordered]@{
    id = $s.id; seed = $s.seed; w = $s.w; h = $s.h; pos = $s.pos; prompt_id = $null
    comfy_meta = $null; local_png = $null; xfer_png = $null; error = $null
  }
  try {
    Write-Info "=== SERIAL $($s.id) seed=$($s.seed) $($s.w)x$($s.h) ==="
    $wf = Build-DualLoraWorkflow $charApi $sceneApi $s.pos $Neg $s.w $s.h $s.seed $Steps $Cfg $prefix
    $res = Queue-And-Wait $wf $clientId $s.id
    $shotRec.prompt_id = $res.prompt_id
    $shotRec.comfy_meta = $res.images[0]
    $fname = "home-char-$($s.id)-$Stamp.png"
    $local = Join-Path $SmokeDir $fname
    $xfer  = Join-Path $XferDir $fname
    Save-ComfyImage $res.images[0] $local | Out-Null
    Copy-Item $local $xfer -Force
    $shotRec.local_png = $local
    $shotRec.xfer_png = $xfer
    $report.image_paths += $local
    $report.xfer_paths += $xfer
    $okCount++
    Write-Info "OK $local ($((Get-Item $local).Length) bytes)"
    Try-Unload
  } catch {
    $shotRec.error = "$_"
    $report.errors += "$($s.id): $_"
    Write-Info "FAIL $($s.id): $_"
    # Stop early if first fails badly (dual LoRA graph issue)
    if ($okCount -eq 0) {
      $report.shots += $shotRec
      $report | ConvertTo-Json -Depth 10 | Set-Content $ReportPath -Encoding UTF8
      Copy-Item $ReportPath (Join-Path $XferDir (Split-Path $ReportPath -Leaf)) -Force -EA SilentlyContinue
      throw "First shot failed — dual LoRA may be broken. Stopping. $_"
    }
  }
  $report.shots += $shotRec
}

$report.ok = ($okCount -ge 3)
$report | ConvertTo-Json -Depth 10 | Set-Content $ReportPath -Encoding UTF8
Copy-Item $ReportPath (Join-Path $XferDir (Split-Path $ReportPath -Leaf)) -Force
Write-Info "DONE ok=$($report.ok) count=$okCount report=$ReportPath"
Write-Host ($report | ConvertTo-Json -Depth 6)
if (-not $report.ok) { exit 2 }
