$ErrorActionPreference='Continue'
$env:PYTHONUTF8='1'
$night='E:\program\1project\video\xfer\overnight-2026-09-22'
$py='E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe'
$log=Join-Path $night 'logs\overnight-runner.log'
function L($m){ $t=Get-Date -Format o; $line="$t $m"; Add-Content $log $line; Write-Host $line }
function Ensure-Comfy {
  try { Invoke-WebRequest http://127.0.0.1:8188/system_stats -UseBasicParsing -TimeoutSec 2 | Out-Null; return } catch {}
  $portable='E:\program\1project\video\shared\runtime\comfy\installs\portable'
  Start-Process -FilePath "$portable\python_embeded\python.exe" -ArgumentList @('-s','ComfyUI\main.py','--listen','127.0.0.1','--port','8188') -WorkingDirectory $portable -WindowStyle Hidden -RedirectStandardOutput (Join-Path $night 'logs\comfy.out') -RedirectStandardError (Join-Path $night 'logs\comfy.err')
  for($i=0;$i -lt 60;$i++){ try { Invoke-WebRequest http://127.0.0.1:8188/system_stats -UseBasicParsing -TimeoutSec 2 | Out-Null; L 'comfy up'; return } catch { Start-Sleep 2 } }
  throw 'comfy failed to start'
}
function Stop-Comfy {
  $lines = netstat -ano | findstr 'LISTENING' | findstr ':8188'
  foreach($line in $lines){
    if($line -match '\s+(\d+)\s*$'){ $procId=[int]$Matches[1]; L "stop comfy $procId"; Stop-Process -Id $procId -Force -EA SilentlyContinue }
  }
  Start-Sleep 4
}
function Update-Status($t){ Add-Content (Join-Path $night 'STATUS.md') ("`n" + $t) }

New-Item -ItemType Directory -Force -Path (Join-Path $night 'logs'),(Join-Path $night 'smoke') | Out-Null
L 'OVERNIGHT START'
$stamp = Get-Date -Format o
Set-Content (Join-Path $night 'STATUS.md') "# Overnight STATUS`nStarted $stamp`nJacket: DONE charb-jacket-sdxl-v1 (stylelock-v2 default)`n" -Encoding UTF8

try {
  L 'SWEATER expand'
  Ensure-Comfy
  & $py -u 'E:\program\1project\video\shared\project-tools\lora\charb-sweater-v1\expand_sweater.py' *>> (Join-Path $night 'logs\sweater-expand.log')
  $png=@(Get-ChildItem 'E:\program\1project\video\shared\project-tools\lora\charb-sweater-v1\dataset\img\10_charb_sweater\*.png' -EA SilentlyContinue).Count
  Update-Status "- sweater expand exit=$LASTEXITCODE png=$png"
  L 'SWEATER train'
  Stop-Comfy
  powershell -NoProfile -ExecutionPolicy Bypass -File 'E:\program\1project\video\shared\project-tools\lora\charb-sweater-v1\train-charb-sweater-v1.ps1' *>> (Join-Path $night 'logs\sweater-train.log')
  Update-Status "- sweater train exit=$LASTEXITCODE"
  L 'SWEATER smoke'
  Ensure-Comfy
  $src='E:\program\1project\video\shared\project-tools\lora\charb-jacket-v1\smoke_charb_jacket_stylelock_v2.py'
  $c=Get-Content $src -Raw -Encoding UTF8
  $c=$c.Replace('charb-jacket-sdxl-v1.safetensors','charb-sweater-sdxl-v1.safetensors')
  $c=$c.Replace('charb_jacket','charb_sweater')
  $c=$c.Replace('black oversized jacket, open jacket, white t-shirt','cream knit sweater, soft sweater')
  $c=$c.Replace('black oversized jacket, white t-shirt','cream knit sweater, soft sweater')
  $c=$c.Replace('charb-jacket-smoke-stylelock-v2','charb-sweater-smoke')
  $c=$c.Replace('charb-jacket-stylelock','charb-sweater-smoke')
  $smokeOut='E:\program\1project\video\xfer\overnight-2026-09-22\smoke\charb_sweater'
  $c=[regex]::Replace($c,'XFER = Path\(r".*?"\)','XFER = Path(r"E:\\program\\1project\\video\\xfer\\overnight-2026-09-22\\smoke\\charb_sweater")')
  $c=[regex]::Replace($c,'OUT = Path\(r".*?"\)','OUT = Path(r"E:\\program\\1project\\video\\shared\\work\\scratch\\legacy-numbered\\charb-sweater-smoke")')
  Set-Content 'E:\program\1project\video\shared\project-tools\lora\charb-sweater-v1\smoke_sweater_stylelock.py' $c -Encoding UTF8
  New-Item -ItemType Directory -Force -Path $smokeOut | Out-Null
  & $py -u 'E:\program\1project\video\shared\project-tools\lora\charb-sweater-v1\smoke_sweater_stylelock.py' *>> (Join-Path $night 'logs\sweater-smoke.log')
  Update-Status "- sweater smoke exit=$LASTEXITCODE dir=$smokeOut"
} catch {
  L ("SWEATER FAIL " + $_.Exception.Message)
  Update-Status ("- SWEATER FAIL: " + $_.Exception.Message)
}

try {
  L 'HOODIE expand'
  Ensure-Comfy
  & $py -u 'E:\program\1project\video\shared\project-tools\lora\charb-hoodie-v1\expand_hoodie.py' *>> (Join-Path $night 'logs\hoodie-expand.log')
  $png=@(Get-ChildItem 'E:\program\1project\video\shared\project-tools\lora\charb-hoodie-v1\dataset\img\10_charb_hoodie\*.png' -EA SilentlyContinue).Count
  Update-Status "- hoodie expand exit=$LASTEXITCODE png=$png"
  L 'HOODIE train'
  Stop-Comfy
  powershell -NoProfile -ExecutionPolicy Bypass -File 'E:\program\1project\video\shared\project-tools\lora\charb-hoodie-v1\train-charb-hoodie-v1.ps1' *>> (Join-Path $night 'logs\hoodie-train.log')
  Update-Status "- hoodie train exit=$LASTEXITCODE"
  L 'HOODIE smoke'
  Ensure-Comfy
  $src='E:\program\1project\video\shared\project-tools\lora\charb-jacket-v1\smoke_charb_jacket_stylelock_v2.py'
  $c=Get-Content $src -Raw -Encoding UTF8
  $c=$c.Replace('charb-jacket-sdxl-v1.safetensors','charb-hoodie-sdxl-v1.safetensors')
  $c=$c.Replace('charb_jacket','charb_hoodie')
  $c=$c.Replace('black oversized jacket, open jacket, white t-shirt','hoodie, casual hoodie, hooded sweatshirt')
  $c=$c.Replace('black oversized jacket, white t-shirt','hoodie, casual hoodie, hooded sweatshirt')
  $c=$c.Replace('charb-jacket-smoke-stylelock-v2','charb-hoodie-smoke')
  $c=$c.Replace('charb-jacket-stylelock','charb-hoodie-smoke')
  $smokeOut='E:\program\1project\video\xfer\overnight-2026-09-22\smoke\charb_hoodie'
  $c=[regex]::Replace($c,'XFER = Path\(r".*?"\)','XFER = Path(r"E:\\program\\1project\\video\\xfer\\overnight-2026-09-22\\smoke\\charb_hoodie")')
  $c=[regex]::Replace($c,'OUT = Path\(r".*?"\)','OUT = Path(r"E:\\program\\1project\\video\\shared\\work\\scratch\\legacy-numbered\\charb-hoodie-smoke")')
  Set-Content 'E:\program\1project\video\shared\project-tools\lora\charb-hoodie-v1\smoke_hoodie_stylelock.py' $c -Encoding UTF8
  New-Item -ItemType Directory -Force -Path $smokeOut | Out-Null
  & $py -u 'E:\program\1project\video\shared\project-tools\lora\charb-hoodie-v1\smoke_hoodie_stylelock.py' *>> (Join-Path $night 'logs\hoodie-smoke.log')
  Update-Status "- hoodie smoke exit=$LASTEXITCODE dir=$smokeOut"
} catch {
  L ("HOODIE FAIL " + $_.Exception.Message)
  Update-Status ("- HOODIE FAIL: " + $_.Exception.Message)
}

$done = Get-Date -Format o
Update-Status "`n## DONE @ $done"
L 'OVERNIGHT COMPLETE'
