$ErrorActionPreference='Continue'
$bg = 'E:\program\1project\video\shared\workflows\创意\a-space-cat\i2v\run_ltx_draft_bg.ps1'
$log = 'E:\program\1project\video\projects\创意\episodes\a-space-cat\logs\i2v\ltx_draft_bg_launch.log'
"LAUNCH $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File $log -Encoding utf8
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $bg *>&1 | Tee-Object -FilePath $log -Append
$c = $LASTEXITCODE
"EXIT $c $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File $log -Append -Encoding utf8
