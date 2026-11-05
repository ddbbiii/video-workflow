$ErrorActionPreference = 'Continue'
$py = 'E:\program\language\python\Python-3.11.0\python.exe'
$script = 'E:\program\1project\video\shared\workflows\助眠解说\b-geomagnetic-reversal\edit\draft_dof_vo_v4\_tools\embed_select_v1_v4.py'
$log = 'E:\program\1project\video\projects\助眠解说\episodes\b-geomagnetic-reversal\audio\draft_dof_vo_v4\logs\embed.log'
& $py -u $script *>> $log
$code = $LASTEXITCODE
Add-Content -Path $log -Value ("EXIT_CODE=" + $code) -Encoding UTF8
exit $code
