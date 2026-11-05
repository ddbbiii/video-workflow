$ErrorActionPreference='Continue'
$py='E:\program\1project\video\shared\runtime\comfy\installs\portable\python_embeded\python.exe'
$script='E:\program\1project\video\shared\workflows\猎奇\tudou\i2v\run_lieqi_i2v_v3_lip_pilot.py'
$stdout='E:\program\1project\video\projects\猎奇\drafts\tudou-lip-pilot-ltx\logs\v3_lip_pilot_stdout.log'
$exitf='E:\program\1project\video\projects\猎奇\drafts\tudou-lip-pilot-ltx\logs\v3_lip_pilot.exit'
& $py -u $script *>&1 | ForEach-Object { $_ | Out-File -FilePath $stdout -Append -Encoding utf8; $_ }
$code=$LASTEXITCODE
if($null -eq $code){ $code=0 }
Set-Content -Path $exitf -Value $code -Encoding ascii