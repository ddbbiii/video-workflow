# a-space-cat: H3 expand-v1 (9 shots) then finalize v6. Do NOT start until lock-order step3 悬疑mirror少动嘴i2v released gpu.lock (after 助眠嵌ch1 + 地磁精选i2v).
$ErrorActionPreference = "Continue"
$base = "E:\program\1project\video\projects\创意\episodes\a-space-cat"
$PY = "E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe"
$lock = "E:\program\1project\video\shared\work\cache\gpu.lock"
$log = "E:\program\1project\video\projects\创意\episodes\a-space-cat\logs\h3_expand_v1_pipeline.log"
function L($m){ $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $m"; $line | Out-File -FilePath $log -Append -Encoding utf8; Write-Host $line }

L "=== H3 expand-v1 pipeline start pid $PID"
if (Test-Path $lock) {
  L "ABORT: gpu.lock present:"; Get-Content $lock | ForEach-Object { L $_ }
  exit 2
}
L "step1 H3 expand-v1 shots s06,s20,s23,s24,s28,s33,s36,s39,s46"
& $PY -u "E:\program\1project\video\shared\workflows\创意\a-space-cat\i2v\run_a_space_cat_i2v_h3_expand_v1.py" 2>&1 | ForEach-Object { "$_" ; $_ | Out-File -FilePath "E:\program\1project\video\projects\创意\episodes\a-space-cat\logs\i2v\h3_expand_v1_stdout.log" -Append -Encoding utf8 }
$h3exit = $LASTEXITCODE
L "step1 H3 exit=$h3exit"
if ($h3exit -ne 0) {
  L "STOP: H3 incomplete; skip finalize. Check E:\program\1project\video\projects\创意\episodes\a-space-cat\logs\i2v_h3_expand_v1_status.txt"
  exit $h3exit
}
L "step2 finalize"
& $PY -u "E:\program\1project\video\shared\workflows\创意\a-space-cat\finalize_a_space_cat_v6.py" 2>&1 | ForEach-Object { "$_" ; $_ | Out-File -FilePath "E:\program\1project\video\projects\创意\episodes\a-space-cat\logs\finalize_v6.log" -Append -Encoding utf8 }
$fexit = $LASTEXITCODE
L "step2 finalize exit=$fexit"
L "=== pipeline end"
exit $fexit

