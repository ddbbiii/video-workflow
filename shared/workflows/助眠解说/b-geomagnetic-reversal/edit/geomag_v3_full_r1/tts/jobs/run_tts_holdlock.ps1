param([string]$Jobs, [string]$Tag = 'seed7')
$ErrorActionPreference = 'Continue'
$O = 'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal'  # 2026-10-08 迁移后单集根
$Lock = 'E:\program\1project\video\shared\work\cache\gpu.lock'
$OldLock = 'E:\program\1project\video\shared\work\cache\gpu.lock'
$Req = 'E:\program\1project\video\shared\gpu-queue\requests\zhumian-geomag-full-r1-tts-20261008.json'
$Log = Join-Path $O "logs\full_r1\run_tts_$Tag.log"
$env:PYTHONIOENCODING = 'utf-8'; $env:HF_ENDPOINT = 'https://hf-mirror.com'
$env:MODELSCOPE_CACHE = 'E:\program\1project\video\shared\runtime\engines\tts\modelscope-cache'
$env:HF_HOME = 'E:\program\1project\video\shared\runtime\engines\tts\hf-cache'
$env:PYTORCH_CUDA_ALLOC_CONF = 'expandable_segments:True'
$env:TEMP = 'E:\program\1project\video\shared\work\scratch\zhumian-geomag-full_r1-tmp'; $env:TMP = $env:TEMP; New-Item -ItemType Directory -Force $env:TEMP | Out-Null
$enc = New-Object Text.UTF8Encoding $false
function Log($m){ $l = ('[{0}] {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $m); [IO.File]::AppendAllText($Log, $l + "`r`n", $enc); Write-Host $l }
function SetReq($st, $extra){ $j = Get-Content $Req -Raw -Encoding UTF8 | ConvertFrom-Json; $j.status = $st; foreach($k in $extra.Keys){ $j | Add-Member -NotePropertyName $k -NotePropertyValue $extra[$k] -Force }; [IO.File]::WriteAllText($Req, ($j | ConvertTo-Json -Depth 5), $enc) }
function Busy($p){ if(-not (Test-Path $p)){ return $false }; try { $l = Get-Content $p -Raw | ConvertFrom-Json; if($l.pid -and (Get-Process -Id $l.pid -ErrorAction SilentlyContinue)){ return $true } } catch {}; return $true }
$t0 = Get-Date
while ((Busy $Lock) -or (Busy $OldLock)) { if(((Get-Date)-$t0).TotalMinutes -gt 60){ Log 'ABORT: lock busy > 60 min'; SetReq 'queued' @{ note = 'lock busy, waited 60 min' }; exit 9 }; Log 'lock present, waiting 30s'; Start-Sleep 30 }
SetReq 'granted' @{ granted_at = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss+08:00'); granted_by = '助眠解说自管（老大授权）' }
try { $fs = [IO.File]::Open($Lock, 'CreateNew', 'Write'); $txt = (@{ owner = '助眠解说'; holder = '助眠解说'; purpose = "geomag full r1 TTS $Tag"; pid = $PID; started = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'); request = 'zhumian-geomag-full-r1-tts-20261008' } | ConvertTo-Json -Compress); $b = $enc.GetBytes($txt); $fs.Write($b, 0, $b.Length); $fs.Close(); Log "gpu.lock acquired $txt" } catch { Log "lock fail: $($_.Exception.Message)"; SetReq 'queued' @{ note = 'lock create failed' }; exit 5 }
SetReq 'running' @{ pid = $PID; started_at = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss+08:00') }
Set-Location 'E:\program\1project\video\shared\runtime\engines\tts\voxcpm'
Log "=== START $Tag jobs=$Jobs"
& 'E:\program\1project\video\shared\runtime\engines\tts\voxcpm\.venv\Scripts\python.exe' 'E:\program\1project\video\shared\runtime\engines\tts\voxcpm\gen_shots.py' $Jobs *>> $Log
$ec = $LASTEXITCODE
Log "=== END $Tag exit=$ec"
try { $l = Get-Content $Lock -Raw | ConvertFrom-Json; if ($l.pid -eq $PID) { Remove-Item $Lock -Force; Log 'gpu.lock released' } else { Log 'lock not ours at release' } } catch { Log "release err: $($_.Exception.Message)" }
SetReq ($(if($ec -eq 0){'completed'}else{'failed'})) @{ finished_at = (Get-Date).ToString('yyyy-MM-ddTHH:mm:ss+08:00'); exit_code = $ec; pid = $PID }
exit $ec