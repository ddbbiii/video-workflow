$ErrorActionPreference='Continue'
$py='E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe'
$script='E:\program\1project\video\shared\workflows\创意\a-space-cat\i2v\run_a_space_cat_i2v_ltx_draft.py'
$stdout='E:\program\1project\video\projects\创意\episodes\a-space-cat\logs\i2v\ltx_draft_stdout.log'
$exitf='E:\program\1project\video\projects\创意\episodes\a-space-cat\logs\i2v\ltx_draft.exit'
New-Item -ItemType Directory -Force -Path (Split-Path $stdout) | Out-Null
if (Test-Path $stdout) { Remove-Item $stdout -Force }
if (Test-Path $exitf) { Remove-Item $exitf -Force }
& $py -u $script *>&1 | ForEach-Object { $_ | Out-File -FilePath $stdout -Append -Encoding utf8; $_ }
$code=$LASTEXITCODE
if($null -eq $code){ $code=0 }
Set-Content -Path $exitf -Value $code -Encoding ascii