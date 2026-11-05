# Launch the lieqi runner hidden in the background (returns immediately). Log: E:\program\1project\video\projects\猎奇\logs\lieqi_<tag>.log
param([Parameter(Mandatory=$true)][string]$Jobs)
$root = 'E:\program\1project\video\projects\猎奇'
$py = 'E:\program\1project\video\shared\runtime\engines\stills-runtime\ComfyUI_windows_portable\python_embeded\python.exe'
$tag = (Get-Content $Jobs -Raw -Encoding UTF8 | ConvertFrom-Json).tag
New-Item -ItemType Directory -Force "$root\logs" | Out-Null
Start-Process -FilePath $py -ArgumentList '-u', "E:\program\1project\video\shared\workflows\猎奇\scripts\run_lieqi.py", "`"$Jobs`"" -WorkingDirectory $root -WindowStyle Hidden `
  -RedirectStandardOutput "$root\logs\runner_$tag.out.log" -RedirectStandardError "$root\logs\runner_$tag.err.log"
"launched lieqi runner tag=$tag log=$root\logs\lieqi_$tag.log"
