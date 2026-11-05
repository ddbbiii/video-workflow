#Requires -Version 5.1
<#
  镜子半拍 · 最终 LoRA 静帧 v1（分镜板已过审）
  LoRA: chengwu-sdxl-v1b.safetensors
  服装锁: 青绿船领长袖 + 黑项圈 + 灰蓝短发
  动效: 停
  Batch: -Batch priority|all|rest
#>
param(
  [string]$Api = 'http://127.0.0.1:8188',
  [double]$LoraStrength = 0.9,
  [int]$Steps = 28,
  [double]$Cfg = 5.5,
  [ValidateSet('priority','all','rest')]
  [string]$Batch = 'priority'
)

$ErrorActionPreference = 'Stop'
$ROOT = 'E:\program\1project\video'
$OutDir = Join-Path $ROOT 'shared\project-tools\lora\chengwu-v1\smoke\mirror-halfbeat\final'
$XferDir  = 'E:\program\1project\video\xfer\mirror-halfbeat-final'
$Stamp    = Get-Date -Format 'yyyyMMdd-HHmmss'
$ReportPath = Join-Path $OutDir ("FINAL-REPORT-{0}.json" -f $Stamp)
$CkptPath = Join-Path $ROOT 'shared\runtime\comfy\models\models\checkpoints\animagine-xl-4.0-opt.safetensors'
$LoraName = 'chengwu-sdxl-v1b.safetensors'
$LoraPath = Join-Path (Join-Path $ROOT 'shared\runtime\comfy\models\models\loras') $LoraName

function Write-Info($m) { Write-Host ("[mirror-final {0}] {1}" -f (Get-Date -Format 'HH:mm:ss'), $m) }
function Ensure-Dir($p) { New-Item -ItemType Directory -Force -Path $p | Out-Null; return $p }
function Get-Json($url) { Invoke-RestMethod -Uri $url -Method Get -TimeoutSec 30 }
function Post-Json($url, $obj) {
  $body = $obj | ConvertTo-Json -Depth 40 -Compress
  return Invoke-RestMethod -Uri $url -Method Post -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -ContentType 'application/json; charset=utf-8' -TimeoutSec 120
}

Ensure-Dir $OutDir | Out-Null
Ensure-Dir $XferDir  | Out-Null

$report = [ordered]@{
  ok = $false; stamp = $Stamp; lora = $LoraName; batch = $Batch
  shots = @(); image_paths = @(); xfer_paths = @(); errors = @()
  note = 'Mirror Halfbeat FINAL stills — board passed; motion paused; costume lock teal scoop + choker'
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
    (Join-Path $ROOT 'shared\runtime\comfy\installs\portable\start-portable-8188.bat'),
    (Join-Path $ROOT 'shared\runtime\comfy\installs\portable\start-first-round.ps1')
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

$Neg = 'lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, jpeg artifacts, signature, watermark, blurry, loli, child, scanlines, heavy fog, dirty wall grime streaks, abandoned ruins, pitch black crushed blacks, both faces smiling, sweet smile, only one face, no reflection, dirty real nails, clean mirror nails, off-shoulder, bare shoulders, strapless, crew-neck mismatch, short sleeves, different outfits, male, man, long hair, black cloth gag, tape over mouth, hand covering mouth, wiping mirror with towel covering glass'

$Atm = 'clean small apartment bathroom 2am, cold cyan fluorescent tube, readable face light but corners darker, misted cloudy mirror water streaks, low saturation blue-gray, high contrast, oppressive midnight solitude pressure, empty hollow stiff eyes, anime cel sharp lineart, NO abandoned grime, NO scanlines, NO fog filter, masterpiece'
$Char = 'chengwu, 1girl, young woman, short ash-blue bob hair wispy bangs, brown hollow stiff eyes, pale skin, thin black choker with small silver ring, teal cyan-green SCOOP boat-neck long-sleeve top covering shoulders, collarbone slight, consistent costume lock same outfit'

$allShots = @(
  @{ id='S01'; title='entry-keys'; batch='rest'; w=832; h=1216; seed=2026093101
    pos="$Char, dark apartment entry night almost no light, keys dropped in bowl, silhouette feet at door, oppressive blackness, tiny grey window light, midnight return, $Atm" }
  @{ id='S02'; title='bath-light-on'; batch='rest'; w=832; h=1216; seed=2026093102
    pos="$Char, bathroom light just on, standing at sink starting toothpaste on toothbrush, misted mirror ahead, clean small bathroom darker corners, $Atm" }
  @{ id='S03'; title='hand-lag'; batch='rest'; w=832; h=1216; seed=2026093103
    pos="$Char, over-shoulder view into misted mirror, REAL foamy toothbrush hand RAISED higher, MIRROR reflection hand CLEARLY half-beat LOWER lagging readable delay, same woman same costume in mirror, $Atm" }
  @{ id='S04'; title='blink-lag'; batch='rest'; w=832; h=1216; seed=2026093104
    pos="$Char, dual face real left mirror right, REAL eyelids half-closed mid-blink, MIRROR eyes still more OPEN blink late one beat asymmetry obvious, short hair both, $Atm" }
  @{ id='S05'; title='triple-blink-test'; batch='rest'; w=832; h=1216; seed=2026093105
    pos="$Char, close eyes dual, testing blinks readable lag pattern one-two-three vs one-two-pause-three, mid-blink asymmetry, $Atm" }
  @{ id='S06'; title='brush-freeze'; batch='rest'; w=832; h=1216; seed=2026093106
    pos="$Char, mid shot at sink, REAL toothbrush FROZEN mid-air stopped foam, MIRROR toothbrush still slightly higher or still moving stops half-beat LATE, NOT hand pressing glass, NOT wiping, $Atm" }
  @{ id='S07'; title='leave-and-lookback'; batch='priority'; w=832; h=1216; seed=2026093027
    pos="$Char, wide shot, she stands at doorframe LEFT looking back over shoulder having LEFT the sink, RIGHT misted mirror shows reflection STILL at sink alone head tilted looking at empty space, two different positions, same teal scoop-neck long-sleeve costume on both, $Atm" }
  @{ id='S08'; title='nail-dirt-proof'; batch='priority'; w=832; h=1216; seed=2026093028
    pos="$Char, extreme close-up fingertip touching bathroom mirror glass meeting reflection fingertip, REAL nails CLEAN pink no dirt, MIRROR nails CLEAR grey grit dirt under fingernail beds macro readable, SAME teal scoop-neck sleeve cuff on real AND mirror reflection, $Atm" }
  @{ id='S09'; title='mirror-smiles-first'; batch='priority'; w=832; h=1216; seed=2026093029
    pos="$Char, dual face same frame over bathroom mirror, LEFT real face STIFF blank mouth closed NO smile, RIGHT mirror reflection COLD short smirk mouth corner raised first, both faces large and readable, same teal scoop-neck long-sleeve and black choker on both, $Atm" }
  @{ id='S10'; title='towel-hesitate'; batch='rest'; w=832; h=1216; seed=2026093110
    pos="$Char, mid shot, towel raised halfway then lowering putting down, NOT covering mirror, NOT wiping glass, mirror still fully visible misted, hesitant hollow eyes, $Atm" }
  @{ id='S11'; title='ear-foreshadow'; batch='rest'; w=832; h=1216; seed=2026093111
    pos="$Char, mid shot facing sink, REAL body FROZEN shoulders still NOT looking back at door, MIRROR reflection already tilting ear listening toward dark door gap while she has not moved, foreshadow, $Atm" }
  @{ id='S12'; title='false-sync-flash'; batch='rest'; w=832; h=1216; seed=2026093112
    pos="$Char, dual face bathroom real left mirror right BOTH faces visible PERFECTLY matched same open eyes same shoulder height identical blank pose readable full sync during cold cyan tube flash slight overexposure, $Atm" }
  @{ id='S13'; title='she-blinks-he-does-not'; batch='priority'; w=832; h=1216; seed=2026093113
    pos="$Char, extreme close-up eyes split, LEFT real eye mid-blink lids half shut, RIGHT mirror eye WIDE OPEN unblinking stare, bare face NO gag NO black cloth NO tape, short ash-blue bangs, $Atm" }
  @{ id='S14'; title='nose-to-glass'; batch='rest'; w=832; h=1216; seed=2026093114
    pos="$Char, extreme close-up nose tip almost touching misted mirror, pupils deeper darker as if something stares from inside glass outward, forehead and eyes readable, not full face crush, $Atm" }
  @{ id='S15'; title='pressed-to-mirror'; batch='rest'; w=832; h=1216; seed=2026093115
    pos="$Char, face pressed close to misted mirror oppressive, aware of wrong sync, hollow stiff eyes, closer than S14 fuller face, $Atm" }
  @{ id='S16'; title='lights-off'; batch='rest'; w=832; h=1216; seed=2026093116
    pos="$Char, bathroom lights off, she leans back against door, grey silhouette, mirror deeper black, tiny grey window light, eyes open dry, $Atm" }
  @{ id='S17'; title='blackout-blink'; batch='rest'; w=832; h=1216; seed=2026093117
    pos="mostly black frame slight grey, extremely dark bathroom after lights off, maybe faintest eye white glint hint of a blink unknown who, oppressive silence, anime still, masterpiece, NO text" }
)

if ($Batch -eq 'priority') {
  $shots = @($allShots | Where-Object { $_.batch -eq 'priority' })
} elseif ($Batch -eq 'rest') {
  $shots = @($allShots | Where-Object { $_.batch -eq 'rest' })
} else {
  $shots = $allShots
}
Write-Info ("Batch={0} count={1} ids={2}" -f $Batch, $shots.Count, (($shots | ForEach-Object { $_.id }) -join ','))

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
  $prefix = "mirror-halfbeat-final/$($s.id)-$Stamp"
  $wf = Build-Workflow $loraApi $LoraStrength $s.pos $Neg $s.w $s.h $s.seed $Steps $Cfg $prefix
  try {
    $res = Queue-And-Wait $wf "mirror-final-$($s.id)-$Stamp" $s.id
    $destName = "final-{0}-{1}.png" -f $s.id, $Stamp
    $destOut = Join-Path $OutDir $destName
    $destXfer  = Join-Path $XferDir $destName
    Save-ComfyImage $res.images[0] $destOut | Out-Null
    Copy-Item $destOut $destXfer -Force
    $report.shots += [ordered]@{ id = $s.id; title = $s.title; prompt_id = $res.prompt_id; out_path = $destOut; xfer_path = $destXfer }
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
Copy-Item $ReportPath (Join-Path $XferDir ("FINAL-REPORT-{0}.json" -f $Stamp)) -Force
Write-Info ("DONE ok={0} shots={1} errors={2}" -f $report.ok, $report.shots.Count, $report.errors.Count)
if (-not $report.ok) { exit 1 }
