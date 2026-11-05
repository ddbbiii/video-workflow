#Requires -Version 5.1
<#
  镜子半拍 · FINAL LoRA img2img priority v1
  Anchors: approved storyboard boards (composition)
  LoRA: chengwu-sdxl-v1b.safetensors
  Costume lock: teal scoop/boat-neck LONG SLEEVE + black choker + ash-blue bob
  Usage: -Batch priority [-Denoise 0.55] [-Only S08] [-SeedOffset 0]
#>
param(
  [string]$Api = 'http://127.0.0.1:8188',
  [double]$LoraStrength = 0.9,
  [int]$Steps = 28,
  [double]$Cfg = 5.5,
  [double]$Denoise = 0.55,
  [ValidateSet('priority')]
  [string]$Batch = 'priority',
  [string]$Only = '',
  [int]$SeedOffset = 0,
  [int]$Width = 1280,
  [int]$Height = 720
)

$ErrorActionPreference = 'Stop'
$ROOT = 'E:\program\1project\video'
$OutDir = Join-Path $ROOT 'shared\project-tools\lora\chengwu-v1\smoke\mirror-halfbeat\final'
$XferDir = 'E:\program\1project\video\xfer\mirror-halfbeat-final'
$BoardRefDir = Join-Path $ROOT 'shared\project-tools\lora\chengwu-v1\smoke\mirror-halfbeat\board-refs'
$ComfyInput = Join-Path $ROOT 'shared\runtime\comfy\installs\portable\ComfyUI\input'
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$ReportPath = Join-Path $OutDir ("FINAL-I2I-REPORT-{0}.json" -f $Stamp)
$CkptPath = Join-Path $ROOT 'shared\runtime\comfy\models\models\checkpoints\animagine-xl-4.0-opt.safetensors'
$LoraName = 'chengwu-sdxl-v1b.safetensors'
$LoraPath = Join-Path (Join-Path $ROOT 'shared\runtime\comfy\models\models\loras') $LoraName

function Write-Info($m) { Write-Host ("[mirror-i2i {0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m) }
function Ensure-Dir($p) { New-Item -ItemType Directory -Force -Path $p | Out-Null; return $p }
function Get-Json($url) { Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 30 }
function Post-Json($url, $obj) {
  $body = $obj | ConvertTo-Json -Depth 40 -Compress
  return Invoke-RestMethod -Uri $url -Method Post -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -ContentType 'application/json; charset=utf-8' -TimeoutSec 120
}

Ensure-Dir $OutDir | Out-Null
Ensure-Dir $XferDir | Out-Null
Ensure-Dir $BoardRefDir | Out-Null
Ensure-Dir $ComfyInput | Out-Null

$report = [ordered]@{
  ok = $false; stamp = $Stamp; lora = $LoraName; batch = $Batch
  denoise = $Denoise; width = $Width; height = $Height; mode = 'img2img-board'
  shots = @(); image_paths = @(); xfer_paths = @(); errors = @()
  note = 'Mirror Halfbeat FINAL img2img from approved boards; costume lock teal scoop LS + choker'
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
    (Join-Path $ROOT 'shared\runtime\comfy\installs\portable\run_nvidia_gpu.bat'),
    (Join-Path $ROOT 'shared\runtime\comfy\installs\portable\start-portable-8188.bat')
  )
  $started = $false
  foreach ($s in $startScripts) {
    if (-not (Test-Path $s)) { continue }
    Write-Info "Start via: $s"
    Start-Process -FilePath $s -WindowStyle Minimized
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
if (-not $ckptApi) { throw 'Animagine not in list' }
Write-Info "ckpt=$ckptApi"

$loraInfo = Get-Json "$Api/object_info/LoraLoader"
$loraList = @($loraInfo.LoraLoader.input.required.lora_name[0])
$loraApi = $loraList | Where-Object { $_ -eq $LoraName -or $_ -match 'chengwu-sdxl-v1b\.safetensors' } | Select-Object -First 1
if (-not $loraApi) { $loraApi = $loraList | Where-Object { $_ -match 'chengwu-sdxl-v1b' -and $_ -notmatch '0000' } | Select-Object -First 1 }
if (-not $loraApi) { throw "LoRA v1b not visible" }
Write-Info "lora=$loraApi strength=$LoraStrength denoise=$Denoise"

$Neg = 'lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, jpeg artifacts, signature, watermark, blurry, loli, child, scanlines, heavy fog, dirty wall grime streaks, abandoned ruins, pitch black crushed blacks, both faces smiling, sweet smile, only one face, single face portrait, no reflection, no mirror, dirty real nails, clean mirror nails, off-shoulder, bare shoulders, strapless, crew-neck mismatch, short sleeves, sleeveless, tank top, camisole, white t-shirt, white tee, selfie, phone selfie, different outfits, male, man, long hair, black cloth gag, tape over mouth, hand covering mouth, wiping mirror with towel covering glass, storyboard text, caption, UI labels, Chinese text overlay, English text overlay'

$Atm = 'clean small apartment bathroom 2am, cold cyan fluorescent tube, readable face light but corners darker, misted cloudy mirror water streaks, low saturation blue-gray, high contrast, oppressive midnight solitude pressure, empty hollow stiff eyes, anime cel sharp lineart, NO abandoned grime, NO scanlines, NO fog filter, masterpiece'

$Char = 'chengwu, 1girl, young woman, short ash-blue bob hair wispy bangs, brown hollow stiff eyes, pale skin, thin black choker with small silver ring, teal cyan-green SCOOP boat-neck LONG-SLEEVE top covering shoulders fully, collarbone slight, consistent costume lock SAME teal long sleeve outfit on real AND mirror, NO white shirt, NO short sleeves, NO sleeveless'

$allShots = @(
  @{ id='S07'; title='leave-and-lookback'; boardFile='board-S07-lookback-v3.jpg'; seed=2026093087
    pos="$Char, wide bathroom composition keep board layout, LEFT real woman at dark doorframe looking back over shoulder having LEFT the sink, RIGHT misted mirror shows reflection STILL standing alone at sink different pose head tilted toward empty space, TWO different body positions real vs mirror, SAME teal scoop-neck long-sleeve + black choker on both, $Atm" }
  @{ id='S08'; title='nail-dirt-proof'; boardFile='board-S08-nail-v3.jpg'; seed=2026093088
    pos="$Char, extreme close-up keep board layout fingertip touching bathroom mirror glass meeting reflection fingertip, REAL nails CLEAN pink healthy no dirt, MIRROR nails CLEAR grey grit dirt under fingernail beds macro readable contrast, SAME teal scoop-neck LONG sleeve cuff visible on real AND mirror arm, black choker visible on mirror figure, $Atm" }
  @{ id='S09'; title='mirror-smiles-first'; boardFile='board-S09-smile-v3.jpg'; seed=2026093089
    pos="$Char, dual face SAME frame over bathroom mirror keep board layout, LEFT real face STIFF blank mouth closed NO smile hollow eyes, RIGHT mirror reflection COLD short asymmetric smirk mouth corner raised first, BOTH faces large readable side by side, same teal scoop-neck long-sleeve and black choker on both, $Atm" }
  @{ id='S13'; title='she-blinks-he-does-not'; boardFile='board-S13-v2.jpg'; seed=2026093093
    pos="$Char, extreme close-up eyes split keep board layout vertical divide, LEFT real eye mid-blink lids HALF SHUT she blinks, RIGHT mirror eye WIDE OPEN unblinking stare he does not blink, bare face NO gag NO black cloth NO tape, short ash-blue bangs across forehead, NO text NO captions, $Atm" }
)

$shots = @($allShots)
if ($Only) {
  $shots = @($allShots | Where-Object { $_.id -eq $Only })
  if ($shots.Count -eq 0) { throw "Only shot not found: $Only" }
}
Write-Info ("Batch={0} count={1} ids={2} only={3}" -f $Batch, $shots.Count, (($shots | ForEach-Object { $_.id }) -join ','), $Only)

# Ensure boards exist in Comfy input (filename only for LoadImage)
foreach ($s in $shots) {
  $src = Join-Path $BoardRefDir $s.boardFile
  $dst = Join-Path $ComfyInput $s.boardFile
  if (-not (Test-Path $src)) { throw "Missing board ref: $src — copy boards first" }
  Copy-Item $src $dst -Force
  Write-Info "Board ready in Comfy input: $($s.boardFile)"
}

function Build-I2I-Workflow($loraName, $strength, $pos, $neg, $boardName, $w, $h, $seed, $steps, $cfg, $denoise, $prefix) {
  return [ordered]@{
    '1' = @{ class_type = 'CheckpointLoaderSimple'; inputs = @{ ckpt_name = $ckptApi } }
    '2' = @{ class_type = 'LoraLoader'; inputs = @{ model = @('1',0); clip = @('1',1); lora_name = $loraName; strength_model = $strength; strength_clip = $strength } }
    '3' = @{ class_type = 'CLIPTextEncode'; inputs = @{ text = $pos; clip = @('2',1) } }
    '4' = @{ class_type = 'CLIPTextEncode'; inputs = @{ text = $neg; clip = @('2',1) } }
    '5' = @{ class_type = 'LoadImage'; inputs = @{ image = $boardName } }
    '6' = @{ class_type = 'ImageScale'; inputs = @{ image = @('5',0); upscale_method = 'lanczos'; width = $w; height = $h; crop = 'disabled' } }
    '7' = @{ class_type = 'VAEEncode'; inputs = @{ pixels = @('6',0); vae = @('1',2) } }
    '8' = @{ class_type = 'KSampler'; inputs = @{ seed = $seed; steps = $steps; cfg = $cfg; sampler_name = 'euler_ancestral'; scheduler = 'normal'; denoise = $denoise; model = @('2',0); positive = @('3',0); negative = @('4',0); latent_image = @('7',0) } }
    '9' = @{ class_type = 'VAEDecode'; inputs = @{ samples = @('8',0); vae = @('1',2) } }
    '10' = @{ class_type = 'SaveImage'; inputs = @{ filename_prefix = $prefix; images = @('9',0) } }
  }
}

function Queue-And-Wait($wf, $clientId, $label) {
  $queued = Post-Json "$Api/prompt" @{ prompt = $wf; client_id = $clientId }
  $neProps = @()
  if ($queued.node_errors) { $neProps = @($queued.node_errors.PSObject.Properties) }
  if ($neProps.Count -gt 0) { throw ("node_errors ${label}: " + ($queued.node_errors | ConvertTo-Json -Compress)) }
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
    if ($st -and $st.status_str -eq 'error') { throw "Comfy error ${label}: $($st.messages | ConvertTo-Json -Compress)" }
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
  $seed = [int]($s.seed + $SeedOffset)
  $prefix = "mirror-halfbeat-final/$($s.id)-i2i-$Stamp"
  $wf = Build-I2I-Workflow $loraApi $LoraStrength $s.pos $Neg $s.boardFile $Width $Height $seed $Steps $Cfg $Denoise $prefix
  try {
    $res = Queue-And-Wait $wf "mirror-i2i-$($s.id)-$Stamp" $s.id
    $destName = "final-{0}-i2i-{1}.png" -f $s.id, $Stamp
    $destOut = Join-Path $OutDir $destName
    $destXfer = Join-Path $XferDir $destName
    Save-ComfyImage $res.images[0] $destOut | Out-Null
    Copy-Item $destOut $destXfer -Force
    $report.shots += [ordered]@{ id = $s.id; title = $s.title; board = $s.boardFile; seed = $seed; denoise = $Denoise; prompt_id = $res.prompt_id; out_path = $destOut; xfer_path = $destXfer }
    $report.image_paths += $destOut
    $report.xfer_paths += $destXfer
    Write-Info "OK $($s.id) → $destXfer"
  } catch {
    $report.errors += "$($s.id): $($_.Exception.Message)"
    Write-Info "FAIL $($s.id): $($_.Exception.Message)"
  }
}

$report.ok = ($report.errors.Count -eq 0 -and $report.shots.Count -eq $shots.Count)
$report | ConvertTo-Json -Depth 8 | Set-Content $ReportPath -Encoding UTF8
Copy-Item $ReportPath (Join-Path $XferDir ("FINAL-I2I-REPORT-{0}.json" -f $Stamp)) -Force
Write-Info ("DONE ok={0} shots={1} errors={2} stamp={3}" -f $report.ok, $report.shots.Count, $report.errors.Count, $Stamp)
if (-not $report.ok) { exit 1 }
