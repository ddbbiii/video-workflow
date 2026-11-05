#Requires -Version 5.1
<#
.SYNOPSIS
  Chengwu+sweater v3 SPLIT COMPOSITE smoke. Starts 8188 WITHOUT browser if needed.
.NOTES
  Parent on ddbbi (machineId 681ffa39-7c25-4986-9259-a5efe42ff20a):
    1) CopyFromBox scripts to Desktop grok-bot-xfer\phase-ab-2026-09-23\
    2) Shell-copy into E:\program\1project\video\shared\work\scratch\legacy-numbered\phase-ab-2026-09-23\
    3) powershell -NoProfile -ExecutionPolicy Bypass -File "E:\program\1project\video\shared\work\scratch\legacy-numbered\phase-ab-2026-09-23\RUN-V3-SPLIT.ps1"
#>
param(
  [string]$Api = 'http://127.0.0.1:8188'
)

$ErrorActionPreference = 'Stop'
$ROOT = 'E:\program\1project\video'
$Work = Join-Path $ROOT 'shared\work\scratch\legacy-numbered\phase-ab-2026-09-23'
$DesktopPhase = 'E:\program\1project\video\xfer\phase-ab-2026-09-23'
$ScriptName = 'smoke_chengwu_sweater_v3_split.py'
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
$Log = Join-Path $Work ("RUN-V3-{0}.log" -f $Stamp)
$Status = Join-Path $Work 'STATUS-V3.md'

function L([string]$m) {
  $line = '[{0}] {1}' -f (Get-Date -Format 'HH:mm:ss'), $m
  Write-Host $line
  Add-Content -Path $Log -Value $line -Encoding UTF8
}

New-Item -ItemType Directory -Force -Path $Work | Out-Null
New-Item -ItemType Directory -Force -Path $DesktopPhase | Out-Null
"START-V3 $Stamp Asia/Shanghai" | Set-Content $Status -Encoding UTF8
L "work=$Work"

# Prefer Desktop-staged script, then E scratch
$Script = Join-Path $Work $ScriptName
if (-not (Test-Path $Script)) {
  $alt = Join-Path $DesktopPhase $ScriptName
  if (Test-Path $alt) {
    Copy-Item -Force $alt $Script
    L "copied script from Desktop xfer"
  }
}
if (-not (Test-Path $Script)) { throw "Missing $ScriptName under $Work or $DesktopPhase" }

# Ensure runner itself is mirrored
$Runner = Join-Path $Work 'RUN-V3-SPLIT.ps1'
if (-not (Test-Path $Runner)) {
  $altR = Join-Path $DesktopPhase 'RUN-V3-SPLIT.ps1'
  if (Test-Path $altR) { Copy-Item -Force $altR $Runner }
}

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
  for ($i=0; $i -lt 90; $i++) {
    if (Test-ComfyUp) { L "8188 up after $($i*2)s"; return }
    Start-Sleep -Seconds 2
  }
  throw '8188 failed to come up'
}

function Find-Python {
  foreach ($p in $PyCandidates) {
    if ($p -eq 'python.exe') {
      $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
      if ($cmd) { return $cmd.Source }
      continue
    }
    if (Test-Path $p) { return $p }
  }
  throw 'No python found'
}

Ensure-8188
$Py = Find-Python
L "python=$Py"
L "running $Script"

# Free VRAM before long job
try {
  Invoke-WebRequest -Uri "$Api/free" -Method POST -ContentType 'application/json' `
    -Body '{"unload_models":true,"free_memory":true}' -UseBasicParsing -TimeoutSec 30 | Out-Null
  L 'freed VRAM'
} catch { L "free skip: $_" }

$proc = Start-Process -FilePath $Py -ArgumentList @('-u', $Script) `
  -WorkingDirectory $Work -NoNewWindow -PassThru -RedirectStandardOutput (Join-Path $Work "v3-stdout-$Stamp.txt") `
  -RedirectStandardError (Join-Path $Work "v3-stderr-$Stamp.txt")
Wait-Process -Id $proc.Id
$code = $proc.ExitCode
L "exit=$code"
Get-Content (Join-Path $Work "v3-stdout-$Stamp.txt") -Tail 40 -ErrorAction SilentlyContinue | ForEach-Object { L $_ }
Get-Content (Join-Path $Work "v3-stderr-$Stamp.txt") -Tail 40 -ErrorAction SilentlyContinue | ForEach-Object { L "ERR $_" }

$Out = Join-Path $ROOT 'shared\work\scratch\legacy-numbered\keyframes-2026-09-23\chengwu-sweater-v3-split'
$Xfer = 'E:\program\1project\video\xfer\keyframes-2026-09-23\chengwu-sweater-v3-split'
L "OUT exists=$(Test-Path $Out) XFER exists=$(Test-Path $Xfer)"
if (Test-Path (Join-Path $Out 'last-report.json')) {
  Copy-Item -Force (Join-Path $Out 'last-report.json') (Join-Path $Work 'last-report-v3.json')
  L (Get-Content (Join-Path $Out 'last-report.json') -Raw)
}
"END-V3 exit=$code $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') Asia/Shanghai" | Add-Content $Status -Encoding UTF8
if ($code -ne 0) { exit $code }
