#Requires -Version 5.1
<#
.SYNOPSIS
  Phase A male hoodie fullbody proportion fix + Phase B Chengwu+sweater same-frame 定妆.
  Starts Portable Comfy on 8188 WITHOUT opening browser. Serial API smokes.

.NOTES
  Parent one-shot on ddbbi (machineId 681ffa39-7c25-4986-9259-a5efe42ff20a):
    powershell -NoProfile -ExecutionPolicy Bypass -File "E:\program\1project\video\shared\work\scratch\legacy-numbered\phase-ab-2026-09-23\RUN-PHASE-AB.ps1"
#>
param(
  [string]$Api = 'http://127.0.0.1:8188',
  [switch]$SkipA,
  [switch]$SkipB
)

$ErrorActionPreference = 'Stop'
$ROOT = 'E:\program\1project\video'
$Work = Join-Path $ROOT 'shared\work\scratch\legacy-numbered\phase-ab-2026-09-23'
$PyCandidates = @(
  'E:\program\language\python\Python-3.11.0\python.exe',
  'E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe',
  'E:\program\1project\video\shared\runtime\comfy\installs\ComfyUI_windows_portable\python_embeded\python.exe',
  'python.exe'
)
$StartBats = @(
  (Join-Path $ROOT 'shared\runtime\comfy\installs\portable\start-portable-8188.bat'),
  (Join-Path $ROOT 'shared\runtime\comfy\installs\ComfyUI_windows_portable\run_nvidia_gpu.bat'),
  (Join-Path $ROOT 'shared\project-tools\production\start-portable-sdxl.ps1')
)
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$Log = Join-Path $Work ("RUN-{0}.log" -f $Stamp)
$Status = Join-Path $Work 'STATUS.md'

function L([string]$m) {
  $line = '[{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'), $m
  Write-Host $line
  Add-Content -Path $Log -Value $line -Encoding UTF8
}

New-Item -ItemType Directory -Force -Path $Work | Out-Null
"START $Stamp Asia/Shanghai" | Set-Content $Status -Encoding UTF8
L "work=$Work"

function Test-ComfyUp {
  try {
    Invoke-WebRequest -Uri "$Api/system_stats" -UseBasicParsing -TimeoutSec 3 | Out-Null
    return $true
  } catch { return $false }
}

function Ensure-8188 {
  if (Test-ComfyUp) { L '8188 already up'; return }
  L '8188 down — starting Portable WITHOUT browser'
  $started = $false
  foreach ($s in $StartBats) {
    if (-not (Test-Path $s)) { continue }
    L "start via $s"
    if ($s -like '*.ps1') {
      Start-Process -FilePath 'powershell.exe' -ArgumentList @(
        '-NoProfile','-ExecutionPolicy','Bypass','-File', $s
      ) -WindowStyle Minimized
    } else {
      Start-Process -FilePath $s -WorkingDirectory (Split-Path $s) -WindowStyle Minimized
    }
    $started = $true
    break
  }
  if (-not $started) {
    $portable = Join-Path $ROOT 'shared\runtime\comfy\installs\ComfyUI_windows_portable'
    $pyEmb = Join-Path $portable 'python_embeded\python.exe'
    $main = Join-Path $portable 'ComfyUI\main.py'
    if ((Test-Path $pyEmb) -and (Test-Path $main)) {
      L "fallback Start-Process main.py --port 8188"
      Start-Process -FilePath $pyEmb -ArgumentList @('-s',$main,'--listen','127.0.0.1','--port','8188') `
        -WorkingDirectory $portable -WindowStyle Hidden
      $started = $true
    }
  }
  if (-not $started) { throw 'No Comfy start script found' }
  for ($i = 0; $i -lt 90; $i++) {
    if (Test-ComfyUp) { L "Comfy up after ${i}s"; return }
    Start-Sleep -Seconds 2
  }
  throw 'ComfyUI 8188 not reachable after start'
}

function Resolve-Py {
  foreach ($p in $PyCandidates) {
    if ($p -eq 'python.exe') {
      $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
      if ($cmd) { return $cmd.Source }
      continue
    }
    if (Test-Path $p) { return $p }
  }
  throw 'No python.exe found'
}

# Inventory prior consistency outs (Phase A context)
$Cons = 'E:\program\1project\video\xfer\soft-continue-2026-09-22\smoke\charb_hoodie_male_consistency'
L "inventory consistency: $Cons"
if (Test-Path $Cons) {
  Get-ChildItem $Cons -Filter '*.png' | Sort-Object Name | ForEach-Object {
    L ("  {0}  {1} bytes" -f $_.Name, $_.Length)
  }
} else {
  L 'consistency folder missing on Desktop xfer'
}

Ensure-8188
$Py = Resolve-Py
L "python=$Py"

$A = Join-Path $Work 'smoke_hoodie_male_fullbody_fix.py'
$B = Join-Path $Work 'smoke_chengwu_sweater_sameframe.py'
if (-not (Test-Path $A)) { throw "missing $A — CopyFromBox first" }
if (-not (Test-Path $B)) { throw "missing $B — CopyFromBox first" }

if (-not $SkipA) {
  L '=== PHASE A male fullbody fix ==='
  & $Py $A 2>&1 | Tee-Object -FilePath (Join-Path $Work 'phase-a.log') -Append
  if ($LASTEXITCODE -ne 0) { throw "Phase A exit $LASTEXITCODE" }
  'PHASE_A_OK' | Add-Content $Status
  L 'Phase A OK'
} else {
  L 'SkipA'
}

# free VRAM between phases
try {
  $body = '{"unload_models":true,"free_memory":true}'
  Invoke-WebRequest -Uri "$Api/free" -Method Post -Body $body -ContentType 'application/json' -UseBasicParsing -TimeoutSec 30 | Out-Null
  Start-Sleep -Seconds 2
} catch { L "free warn: $_" }

if (-not $SkipB) {
  L '=== PHASE B Chengwu+sweater same-frame ==='
  & $Py $B 2>&1 | Tee-Object -FilePath (Join-Path $Work 'phase-b.log') -Append
  if ($LASTEXITCODE -ne 0) { throw "Phase B exit $LASTEXITCODE" }
  'PHASE_B_OK' | Add-Content $Status
  L 'Phase B OK'
} else {
  L 'SkipB'
}

L '=== DONE ==='
$outs = @(
  'E:\program\1project\video\xfer\soft-continue-2026-09-22\smoke\charb_hoodie_male_fullbody_fix',
  'E:\program\1project\video\xfer\keyframes-2026-09-23\male-fullbody-fix-best',
  'E:\program\1project\video\xfer\keyframes-2026-09-23\chengwu-sweater',
  'E:\program\1project\video\xfer\keyframes-2026-09-23\chengwu-sweater-best'
)
foreach ($d in $outs) {
  if (Test-Path $d) {
    L "OUT $d"
    Get-ChildItem $d -Filter '*.png' -ErrorAction SilentlyContinue | ForEach-Object { L ("  {0}" -f $_.Name) }
  }
}
'ALL_OK ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') | Add-Content $Status
L 'ALL_OK'
