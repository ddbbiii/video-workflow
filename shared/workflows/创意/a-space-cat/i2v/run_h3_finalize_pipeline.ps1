# a-space-cat: H3 key shots then finalize v6. Releases gpu.lock via H3 runner finally.
$ErrorActionPreference = "Continue"
$base = "E:\program\1project\video\projects\创意\episodes\a-space-cat"
$PY = "E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe"
$log = "E:\program\1project\video\projects\创意\episodes\a-space-cat\logs\h3_finalize_pipeline.log"
function L($m){ $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $m"; $line | Out-File -FilePath $log -Append -Encoding utf8; Write-Host $line }

L "=== H3+finalize pipeline start pid $PID"
L "step1 H3 key shots"
& $PY -u "E:\program\1project\video\shared\workflows\创意\a-space-cat\i2v\run_a_space_cat_i2v_h3_key.py" 2>&1 | ForEach-Object { "$_" ; $_ | Out-File -FilePath "E:\program\1project\video\projects\创意\episodes\a-space-cat\logs\i2v\h3_key_stdout.log" -Append -Encoding utf8 }
$h3exit = $LASTEXITCODE
L "step1 H3 exit=$h3exit"
if ($h3exit -ne 0) {
  L "STOP: H3 incomplete; skip finalize. Check E:\program\1project\video\projects\创意\episodes\a-space-cat\logs\i2v_h3_key_status.txt"
  exit $h3exit
}
L "step2 finalize"
& $PY -u "E:\program\1project\video\shared\workflows\创意\a-space-cat\finalize_a_space_cat_v6.py" 2>&1 | ForEach-Object { "$_" ; $_ | Out-File -FilePath "E:\program\1project\video\projects\创意\episodes\a-space-cat\logs\finalize_v6.log" -Append -Encoding utf8 }
$fexit = $LASTEXITCODE
L "step2 finalize exit=$fexit"
L "=== pipeline end"
exit $fexit