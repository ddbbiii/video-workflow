#Requires -Version 5.1
<#
  镜子半拍关键静帧冒烟：S07 离镜回头 / S08 灰指甲 / S09 抢拍笑
  LoRA: chengwu-sdxl-v1b.safetensors
  Comfy :8188 — 不自动开浏览器
#>
param(
  [string]$Api = 'http://127.0.0.1:8188',
  [double]$LoraStrength = 0.9,
  [int]$Steps = 28,
  [double]$Cfg = 5.5
)

$ErrorActionPreference = 'Stop'
$ROOT = 'E:\program\1project\video'
$SmokeDir = Join-Path $ROOT 'shared\project-tools\lora\chengwu-v1\smoke\mirror-halfbeat'
$XferDir  = 'E:\program\1project\video\xfer\mirror-halfbeat-smoke'
$Stamp    = Get-Date -Format 'yyyyMMdd-HHmmss'
$ReportPath = Join-Path $SmokeDir ("SMOKE-REPORT-{0}.json" -f $Stamp)
$CkptPath = Join-Path $ROOT 'shared\runtime\comfy\models\models\checkpoints\animagine-xl-4.0-opt.safetensors'
$LoraName = 'chengwu-sdxl-v1b.safetensors'
$LoraPath = Join-Path (Join-Path $ROOT 'shared\runtime\comfy\models\models\loras') $LoraName

function Write-Info($m) { Write-Host ("[mirror-smoke {0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m) }
function Ensure-Dir($p) { New-Item -ItemType Directory -Force -Path $p | Out-Null; return $p }
function Get-Json($url) { Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 30 }
function Post-Json($url, $obj) {
  $body = $obj | ConvertTo-Json -Depth 40 -Compress
  return Invoke-RestMethod -Uri $url -Method Post -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -ContentType 'application/json; charset=utf-8' -TimeoutSec 120
}

Ensure-Dir $SmokeDir | Out-Null
Ensure-Dir $XferDir  | Out-Null

$report = [ordered]@{
  ok = $false; stamp = $Stamp; lora = $LoraName
  shots = @(); image_paths = @(); xfer_paths = @(); errors = @()
  note = 'Mirror Halfbeat key stills S07/S08/S09 — atmosphere v1.4 locked'
}

if (-not (Test-Path $CkptPath)) { throw "Missing ckpt: $CkptPath" }
if (-not (Test-Path $LoraPath)) { throw "Missing LoRA: $LoraPath" }

try {
  $gpu = & nvidia-smi --query-gpu=name,memory.used,memory.free,utilization.gpu --format=csv,noheader
  Write-Info "GPU: $gpu"
} catch { Write-Info 'nvidia-smi unavailable' }

function Test-ComfyUp {
  try { $null = Get-Json "$Api/system_stats"; return $true } catch { return $false }
}

if (-not (Test-ComfyUp)) {
  Write-Info '8188 down — starting Portable without browser'
  $startScripts = @(
    (Join-Path $ROOT 'shared\runtime\comfy\installs\portable\start-portable-8188.bat'),
    (Join-Path $ROOT 'shared\runtime\comfy\installs\portable\start-first-round.ps1'),
    (Join-Path $ROOT 'shared\runtime\comfy\installs\portable\run_nvidia_gpu.bat')
  )
  $started = $false
  foreach ($s in $startScripts) {
    if (-not (Test-Path $s)) { continue }
    Write-Info "Start via: $s"
    if ($s -match '\.ps1$') {
      Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',$s) -WindowStyle Minimized
    } else {
      Start-Process -FilePath $s -WindowStyle Minimized
    }
    $started = $true; break
  }
  if (-not $started) { throw 'No Comfy start script found' }
  $deadline = (Get-Date).AddMinutes(5)
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 5
    if (Test-ComfyUp) { Write-Info 'ComfyUI up'; break }
  }
  if (-not (Test-ComfyUp)) { throw 'ComfyUI 8188 not reachable after start' }
} else {
  Write-Info 'ComfyUI 8188 already up'
}

$ckptInfo = Get-Json "$Api/object_info/CheckpointLoaderSimple"
$ckptList = @($ckptInfo.CheckpointLoaderSimple.input.required.ckpt_name[0])
$ckptApi = $ckptList | Where-Object { $_ -match 'animagine-xl-4\.0-opt' } | Select-Object -First 1
if (-not $ckptApi) { $ckptApi = $ckptList | Where-Object { $_ -match 'animagine' } | Select-Object -First 1 }
if (-not $ckptApi) { throw "Animagine not in list" }
Write-Info "ckpt=$ckptApi"

$loraInfo = Get-Json "$Api/object_info/LoraLoader"
$loraList = @($loraInfo.LoraLoader.input.required.lora_name[0])
$loraApi = $loraList | Where-Object { $_ -eq $LoraName -or $_ -match 'chengwu-sdxl-v1b\.safetensors' } | Select-Object -First 1
if (-not $loraApi) { $loraApi = $loraList | Where-Object { $_ -match 'chengwu-sdxl-v1b' -and $_ -notmatch '0000' } | Select-Object -First 1 }
if (-not $loraApi) { throw "LoRA v1b not visible. Sample: $(($loraList | Select-Object -First 20) -join ', ')" }
Write-Info "lora=$loraApi strength=$LoraStrength"

$Neg = 'lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, jpeg artifacts, signature, watermark, blurry, loli, child, scanlines, heavy fog, dirty wall grime streaks, abandoned ruins, pitch black crushed blacks, both faces smiling, sweet smile, only one face, no reflection, dirty real nails, clean mirror nails, off-shoulder, bare shoulders, strapless, crew-neck mismatch, short sleeves, different outfits'

$Atm = 'clean small apartment bathroom 2am, cold cyan fluorescent tube, readable face light but corners darker, misted cloudy mirror water streaks, low saturation blue-gray, high contrast, oppressive midnight solitude pressure, empty hollow stiff eyes, anime cel sharp lineart, NO abandoned grime, NO scanlines, NO fog filter, masterpiece'
$Char = 'chengwu, 1girl, short ash-blue bob hair wispy bangs, brown hollow stiff eyes, pale skin, thin black choker with small silver ring, teal cyan-green SCOOP boat-neck long-sleeve top covering shoulders, collarbone slight, consistent costume'

$shots = @(
  @{
    id = 'S08'; title = 'nail-dirt-proof'
    w = 832; h = 1216; seed = 2026093028
    pos = "$Char, extreme close-up fingertip touching bathroom mirror glass meeting reflection fingertip, REAL nails CLEAN pink no dirt, MIRROR nails CLEAR grey grit dirt under fingernail beds macro readable, teal scoop-neck sleeve cuff visible, $Atm"
  },
  @{
    id = 'S09'; title = 'mirror-smiles-first'
    w = 832; h = 1216; seed = 2026093029
    pos = "$Char, dual face same frame over bathroom mirror, LEFT real face STIFF blank mouth closed NO smile, RIGHT mirror reflection COLD short smirk mouth corner raised first, both faces large and readable, same teal scoop-neck long-sleeve and black choker on both, $Atm"
  },
  @{
    id = 'S07'; title = 'leave-and-lookback'
    w = 832; h = 1216; seed = 2026093027
    pos = "$Char, wide shot, she stands at doorframe LEFT looking back over shoulder having LEFT the sink, RIGHT misted mirror shows reflection STILL at sink alone head tilted looking at empty space, two different positions, same teal scoop-neck long-sleeve costume, $Atm"
  }
)

function Build-Workflow($loraName, $strength, $pos, $neg, $w, $h, $seed, $steps, $cfg, $prefix) {
  return [ordered]@{
    '1' = @{ class_type = 'CheckpointLoaderSimple'; inputs = @{ ckpt_name = $ckptApi } }
    '2' = @{ class_type = 'LoraLoader'; inputs = @{ model = @('1',0); clip = @('1',1); lora_name = $loraName; strength_model = $strength; strength_clip = $strength } }
    '3' = @{ class_type = 'CLIPTextEncode'; inputs = @{ text = $pos; clip = @('2',1) } }
    '4' = @{ class_type = 'CLIPTextEncode'; inputs = @{ text = $neg; clip = @('2',1) } }
    '5' = @{ class_type = 'EmptyLatentImage'; inputs = @{ width = $w; height = $h; batch_size = 1 } }
    '6' = @{ class_type = 'KSampler'; inputs = @{ seed = $seed; steps = $steps; cfg = $cfg; sampler_name = 'euler_ancestral'; scheduler = 'normal'; denoise = 1.0; model = @('2',0); positive = @('3',0); negative = @('4',0); latent_image = @('5',0) } }
    '7' = @{ class_type = 'VAEDecode'; inputs = @{ samples = @('6',0); vae = @('1',2) } }
    '8' = @{ class_type = 'SaveImage'; inputs = @{ filename_prefix = $prefix; images = @('7',0) } }
  }
}

function Queue-And-Wait($wf, $clientId, $label) {
  $queued = Post-Json "$Api/prompt" @{ prompt = $wf; client_id = $clientId }
  $nodeErrProps = @($queued.node_errors.PSObject.Properties); if ($nodeErrProps.Count -gt 0) { throw ("node_errors ${label}: " + ($queued.node_errors | ConvertTo-Json -Compress)) }
  $promptId = $queued.prompt_id
  if (-not $promptId) { throw "No prompt_id $label" }
  Write-Info "Queued $label → $promptId"
  $deadline = (Get-Date).AddMinutes(15)
  while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 3
    $hist = Get-Json "$Api/history/$promptId"
    if (-not $hist.$promptId) { continue }
    $entry = $hist.$promptId
    $st = $entry.status
    if ($st -and $st.status_str -eq 'error') { throw "Comfy error $label : $($st.messages | ConvertTo-Json -Compress)" }
    if (($st -and $st.completed) -or ($entry.outputs -and $entry.outputs.PSObject.Properties.Name.Count -gt 0)) {
      $imgs = @()
      foreach ($nid in $entry.outputs.PSObject.Properties.Name) {
        if ($entry.outputs.$nid.images) { $imgs += $entry.outputs.$nid.images }
      }
      if (-not $imgs) { throw "No images $label" }
      return @{ prompt_id = $promptId; images = $imgs }
    }
  }
  throw "Timeout $label"
}

function Save-ComfyImage($imgMeta, $destPath) {
  $viewUrl = "{0}/view?filename={1}&subfolder={2}&type={3}" -f $Api, [uri]::EscapeDataString($imgMeta.filename), [uri]::EscapeDataString($(if ($imgMeta.subfolder) { $imgMeta.subfolder } else { '' })), $(if ($imgMeta.type) { $imgMeta.type } else { 'output' })
  Invoke-WebRequest -Uri $viewUrl -OutFile $destPath -TimeoutSec 120 -UseBasicParsing
  return $destPath
}

foreach ($s in $shots) {
  $prefix = "mirror-halfbeat/$($s.id)-$Stamp"
  $wf = Build-Workflow $loraApi $LoraStrength $s.pos $Neg $s.w $s.h $s.seed $Steps $Cfg $prefix
  try {
    $res = Queue-And-Wait $wf "mirror-$($s.id)-$Stamp" $s.id
    $destName = "mirror-{0}-{1}.png" -f $s.id, $Stamp
    $destSmoke = Join-Path $SmokeDir $destName
    $destXfer  = Join-Path $XferDir $destName
    Save-ComfyImage $res.images[0] $destSmoke | Out-Null
    Copy-Item $destSmoke $destXfer -Force
    $report.shots += [ordered]@{ id = $s.id; title = $s.title; prompt_id = $res.prompt_id; smoke_path = $destSmoke; xfer_path = $destXfer }
    $report.image_paths += $destSmoke
    $report.xfer_paths += $destXfer
    Write-Info "OK $($s.id) → $destXfer"
  } catch {
    $report.errors += "$($s.id): $($_.Exception.Message)"
    Write-Info "FAIL $($s.id): $($_.Exception.Message)"
  }
}

$report.ok = ($report.errors.Count -eq 0 -and $report.shots.Count -eq $shots.Count)
$report | ConvertTo-Json -Depth 8 | Set-Content $ReportPath -Encoding UTF8
Copy-Item $ReportPath (Join-Path $XferDir ("SMOKE-REPORT-{0}.json" -f $Stamp)) -Force
Write-Info ("DONE ok={0} shots={1} errors={2}" -f $report.ok, $report.shots.Count, $report.errors.Count)
if (-not $report.ok) { exit 1 }


