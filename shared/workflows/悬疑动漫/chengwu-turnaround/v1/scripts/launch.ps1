param([Parameter(Mandatory=$true)][string]$Jobs)
$W = 'E:\program\1project\video\projects\悬疑动漫\drafts\chengwu-turnaround-history\v1'
$py = 'E:\program\1project\video\shared\runtime\engines\stills-runtime\ComfyUI_windows_portable\python_embeded\python.exe'
$name = [IO.Path]::GetFileNameWithoutExtension($Jobs)
New-Item -ItemType Directory -Force "$W\logs" | Out-Null
Start-Process -FilePath $py -ArgumentList '-u', "$W\scripts\run_ctv1.py", "`"$Jobs`"" -WorkingDirectory $W -WindowStyle Hidden -RedirectStandardOutput "$W\logs\runner_$name.out.log" -RedirectStandardError "$W\logs\runner_$name.err.log"
"launched $name"
